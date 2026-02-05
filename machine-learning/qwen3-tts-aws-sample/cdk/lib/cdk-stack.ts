import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';
import * as targets from 'aws-cdk-lib/aws-elasticloadbalancingv2-targets';
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';
import * as origins from 'aws-cdk-lib/aws-cloudfront-origins';
import { Construct } from 'constructs';
import * as fs from 'fs';
import * as path from 'path';

export class Qwen3TtsVoiceCloningStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Custom header for CloudFront-ALB verification
    const customHeaderName = 'X-Origin-Verify';
    const customHeaderValue = cdk.Fn.select(2, cdk.Fn.split('/', this.stackId));

    // VPC with NAT Gateway for Private Subnet outbound
    const vpc = new ec2.Vpc(this, 'Vpc', {
      maxAzs: 2,
      natGateways: 1,
      subnetConfiguration: [
        { name: 'Public', subnetType: ec2.SubnetType.PUBLIC, cidrMask: 24 },
        { name: 'Private', subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS, cidrMask: 24 },
      ],
    });

    // ALB Security Group - CloudFront Prefix List only
    const albSg = new ec2.SecurityGroup(this, 'AlbSG', {
      vpc,
      description: 'ALB SG - CloudFront prefix list only',
      allowAllOutbound: true,
    });
    albSg.addIngressRule(
      ec2.Peer.prefixList('pl-22a6434b'), // CloudFront prefix list (ap-northeast-2)
      ec2.Port.tcp(80),
      'CloudFront only'
    );

    // EC2 Security Group - ALB only
    const ec2Sg = new ec2.SecurityGroup(this, 'Ec2SG', {
      vpc,
      description: 'EC2 SG - ALB only',
      allowAllOutbound: true,
    });
    ec2Sg.addIngressRule(albSg, ec2.Port.tcp(7860), 'ALB only');

    // CloudWatch Log Group
    const logGroup = new logs.LogGroup(this, 'LogGroup', {
      logGroupName: '/qwen3-tts-voice-cloning/model-setup',
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // IAM Role
    const role = new iam.Role(this, 'Role', {
      assumedBy: new iam.ServicePrincipal('ec2.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSSMManagedInstanceCore'),
        iam.ManagedPolicy.fromAwsManagedPolicyName('CloudWatchAgentServerPolicy'),
      ],
    });
    logGroup.grantWrite(role);

    // Allow EC2 to read CloudFormation outputs
    role.addToPolicy(new iam.PolicyStatement({
      actions: ['cloudformation:DescribeStacks'],
      resources: [this.stackId],
    }));

    // Scripts
    const setupScript = fs.readFileSync(path.join(__dirname, '../../scripts/setup.sh'), 'utf8');
    const serverScript = fs.readFileSync(path.join(__dirname, '../../scripts/server.py'), 'utf8');

    const cloudWatchAgentConfig = {
      logs: {
        logs_collected: {
          files: {
            collect_list: [
              { file_path: '/var/log/model-setup.log', log_group_name: '/qwen3-tts-voice-cloning/model-setup', log_stream_name: '{instance_id}/model-setup', timezone: 'UTC' },
              { file_path: '/var/log/gradio-server.log', log_group_name: '/qwen3-tts-voice-cloning/model-setup', log_stream_name: '{instance_id}/gradio-server', timezone: 'UTC' },
            ],
          },
        },
      },
    };

    const userData = ec2.UserData.forLinux();
    userData.addCommands(
      '#!/bin/bash',
      'set -e',
      'wait_for_apt() { local max=600 w=0; while fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1; do [ $w -ge $max ] && return 1; sleep 10; w=$((w+10)); done; }',
      'wait_for_apt',
      'wget -q https://amazoncloudwatch-agent.s3.amazonaws.com/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb',
      'for i in 1 2 3; do wait_for_apt && dpkg -i amazon-cloudwatch-agent.deb && break; sleep 30; done',
      'rm -f amazon-cloudwatch-agent.deb',
      `cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << 'EOF'\n${JSON.stringify(cloudWatchAgentConfig, null, 2)}\nEOF`,
      '/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -s -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json',
      'mkdir -p /opt/app /opt/huggingface',
      `cat > /opt/app/server.py << 'EOF'\n${serverScript}\nEOF`,
      // Gradio service with GRADIO_ROOT_PATH from environment file
      `cat > /etc/systemd/system/gradio-server.service << 'EOF'
[Unit]
Description=Qwen3-TTS Gradio Server
After=network-online.target model-setup.service
[Service]
Type=simple
User=root
WorkingDirectory=/opt/app
EnvironmentFile=/opt/app/gradio.env
Environment="HF_HOME=/opt/huggingface"
Environment="CUDA_VISIBLE_DEVICES=0"
ExecStart=/opt/pytorch/bin/python /opt/app/server.py
Restart=on-failure
RestartSec=30
StandardOutput=append:/var/log/gradio-server.log
StandardError=append:/var/log/gradio-server.log
[Install]
WantedBy=multi-user.target
EOF`,
      `cat > /opt/setup.sh << 'EOF'\n${setupScript}\nEOF`,
      'chmod +x /opt/setup.sh',
      `cat > /etc/systemd/system/model-setup.service << 'EOF'
[Unit]
Description=Qwen3-TTS Model Setup
After=network-online.target
Before=gradio-server.service
[Service]
Type=oneshot
ExecStart=/opt/setup.sh
RemainAfterExit=yes
[Install]
WantedBy=multi-user.target
EOF`,
      // Fetch CloudFront URL from CloudFormation and create env file
      `cat > /opt/app/fetch-cloudfront-url.sh << 'FETCHEOF'
#!/bin/bash
REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region)
STACK_NAME="Qwen3TtsVoiceCloningStack"
for i in {1..30}; do
  CF_URL=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==\`CloudFrontUrl\`].OutputValue' --output text 2>/dev/null)
  if [ -n "$CF_URL" ] && [ "$CF_URL" != "None" ]; then
    echo "GRADIO_ROOT_PATH=$CF_URL" > /opt/app/gradio.env
    echo "CloudFront URL: $CF_URL"
    exit 0
  fi
  echo "Waiting for CloudFront URL... ($i/30)"
  sleep 10
done
echo "GRADIO_ROOT_PATH=" > /opt/app/gradio.env
FETCHEOF`,
      'chmod +x /opt/app/fetch-cloudfront-url.sh',
      '/opt/app/fetch-cloudfront-url.sh',
      'systemctl daemon-reload',
      'systemctl enable model-setup.service gradio-server.service',
      'systemctl start model-setup.service --no-block',
      'systemctl start gradio-server.service --no-block',
    );

    const machineImage = ec2.MachineImage.lookup({
      name: 'Deep Learning OSS Nvidia Driver AMI GPU PyTorch 2.6* (Ubuntu 22.04)*',
      owners: ['amazon'],
    });

    // EC2 in Private Subnet
    const instance = new ec2.Instance(this, 'Instance', {
      vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS },
      instanceType: ec2.InstanceType.of(ec2.InstanceClass.G4DN, ec2.InstanceSize.XLARGE),
      machineImage,
      securityGroup: ec2Sg,
      role,
      userData,
      blockDevices: [{ deviceName: '/dev/sda1', volume: ec2.BlockDeviceVolume.ebs(100, { volumeType: ec2.EbsDeviceVolumeType.GP3, encrypted: true }) }],
      requireImdsv2: true,
    });

    // ALB in Public Subnet
    const alb = new elbv2.ApplicationLoadBalancer(this, 'ALB', {
      vpc,
      internetFacing: true,
      securityGroup: albSg,
    });

    const listener = alb.addListener('Listener', { port: 80 });
    
    // Default action: fixed 403 response
    listener.addAction('Default', {
      action: elbv2.ListenerAction.fixedResponse(403, {
        contentType: 'text/plain',
        messageBody: 'Forbidden',
      }),
    });

    // Target group with custom header condition
    const targetGroup = new elbv2.ApplicationTargetGroup(this, 'TG', {
      vpc,
      port: 7860,
      protocol: elbv2.ApplicationProtocol.HTTP,
      targets: [new targets.InstanceTarget(instance, 7860)],
      healthCheck: { path: '/', healthyHttpCodes: '200,302' },
    });

    listener.addAction('ValidHeader', {
      priority: 1,
      conditions: [elbv2.ListenerCondition.httpHeader(customHeaderName, [customHeaderValue])],
      action: elbv2.ListenerAction.forward([targetGroup]),
    });

    // CloudFront Origin Request Policy (exclude Host header)
    const originRequestPolicy = new cloudfront.OriginRequestPolicy(this, 'ORP', {
      queryStringBehavior: cloudfront.OriginRequestQueryStringBehavior.all(),
      cookieBehavior: cloudfront.OriginRequestCookieBehavior.all(),
      headerBehavior: cloudfront.OriginRequestHeaderBehavior.allowList(
        'Accept', 'Accept-Language', 'Content-Type', 'Origin', 'Referer',
        'Sec-WebSocket-Key', 'Sec-WebSocket-Version', 'Sec-WebSocket-Extensions', 'Sec-WebSocket-Protocol'
      ),
    });

    // CloudFront
    const distribution = new cloudfront.Distribution(this, 'CF', {
      defaultBehavior: {
        origin: new origins.HttpOrigin(alb.loadBalancerDnsName, {
          protocolPolicy: cloudfront.OriginProtocolPolicy.HTTP_ONLY,
          customHeaders: { [customHeaderName]: customHeaderValue },
        }),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        allowedMethods: cloudfront.AllowedMethods.ALLOW_ALL,
        cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
        originRequestPolicy,
      },
    });

    // Outputs
    new cdk.CfnOutput(this, 'CloudFrontUrl', { value: `https://${distribution.distributionDomainName}` });
    new cdk.CfnOutput(this, 'InstanceId', { value: instance.instanceId });
    new cdk.CfnOutput(this, 'SsmConnect', { value: `aws ssm start-session --target ${instance.instanceId}` });
    new cdk.CfnOutput(this, 'LogGroupUrl', { value: `https://${this.region}.console.aws.amazon.com/cloudwatch/home?region=${this.region}#logsV2:log-groups/log-group/$252Fqwen3-tts-voice-cloning$252Fmodel-setup` });
  }
}
