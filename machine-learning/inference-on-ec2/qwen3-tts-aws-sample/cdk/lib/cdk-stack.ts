import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';
import * as fs from 'fs';
import * as path from 'path';

export class Qwen3TtsStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // VPC: 2 Public + 2 Private Subnets
    const vpc = new ec2.Vpc(this, 'Qwen3TtsVpc', {
      maxAzs: 2,
      natGateways: 0,
      subnetConfiguration: [
        {
          name: 'Public',
          subnetType: ec2.SubnetType.PUBLIC,
          cidrMask: 24,
        },
        {
          name: 'Private',
          subnetType: ec2.SubnetType.PRIVATE_ISOLATED,
          cidrMask: 24,
        },
      ],
    });

    // Security Group
    const securityGroup = new ec2.SecurityGroup(this, 'Qwen3TtsSG', {
      vpc,
      description: 'Security group for Qwen3-TTS EC2 instance',
      allowAllOutbound: true,
    });

    // Allow Gradio UI access
    securityGroup.addIngressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(7860),
      'Gradio UI'
    );

    // CloudWatch Log Group
    const logGroup = new logs.LogGroup(this, 'ModelSetupLogGroup', {
      logGroupName: '/qwen3-tts/model-setup',
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // IAM Role for EC2
    const role = new iam.Role(this, 'Qwen3TtsRole', {
      assumedBy: new iam.ServicePrincipal('ec2.amazonaws.com'),
      description: 'IAM Role for Qwen3-TTS EC2 instance',
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSSMManagedInstanceCore'),
        iam.ManagedPolicy.fromAwsManagedPolicyName('CloudWatchAgentServerPolicy'),
      ],
    });

    logGroup.grantWrite(role);

    // Read setup script and server script
    const setupScriptPath = path.join(__dirname, '../../scripts/setup.sh');
    const setupScript = fs.readFileSync(setupScriptPath, 'utf8');
    const serverScriptPath = path.join(__dirname, '../../scripts/server.py');
    const serverScript = fs.readFileSync(serverScriptPath, 'utf8');

    // CloudWatch Agent config
    const cloudWatchAgentConfig = {
      logs: {
        logs_collected: {
          files: {
            collect_list: [
              {
                file_path: '/var/log/model-setup.log',
                log_group_name: '/qwen3-tts/model-setup',
                log_stream_name: '{instance_id}/model-setup',
                timezone: 'UTC',
              },
            ],
          },
        },
      },
    };

    // UserData
    const userData = ec2.UserData.forLinux();
    userData.addCommands(
      '#!/bin/bash',
      'set -e',
      '',
      '# Install CloudWatch Agent',
      'wget -q https://amazoncloudwatch-agent.s3.amazonaws.com/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb',
      'dpkg -i amazon-cloudwatch-agent.deb || apt-get install -f -y',
      'rm amazon-cloudwatch-agent.deb',
      '',
      '# Configure CloudWatch Agent',
      `cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << 'CWCONFIG'`,
      JSON.stringify(cloudWatchAgentConfig, null, 2),
      'CWCONFIG',
      '',
      '# Start CloudWatch Agent',
      '/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -s -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json',
      '',
      '# Create setup script',
      `cat > /opt/setup.sh << 'SETUPSCRIPT'`,
      setupScript,
      'SETUPSCRIPT',
      '',
      '# Create server script',
      'mkdir -p /opt/app',
      `cat > /opt/app/server.py << 'SERVERSCRIPT'`,
      serverScript,
      'SERVERSCRIPT',
      '',
      'chmod +x /opt/setup.sh',
      '',
      '# Run setup script',
      '/opt/setup.sh',
    );

    // AMI lookup
    const machineImage = ec2.MachineImage.lookup({
      name: 'Deep Learning OSS Nvidia Driver AMI GPU PyTorch 2.7 (Ubuntu 22.04)*',
      owners: ['amazon'],
    });

    // EC2 Instance in Public Subnet
    const instance = new ec2.Instance(this, 'Qwen3TtsInstance', {
      vpc,
      vpcSubnets: {
        subnetType: ec2.SubnetType.PUBLIC,
      },
      instanceType: ec2.InstanceType.of(ec2.InstanceClass.G4DN, ec2.InstanceSize.XLARGE),
      machineImage,
      securityGroup,
      role,
      userData,
      associatePublicIpAddress: true,
      blockDevices: [
        {
          deviceName: '/dev/sda1',
          volume: ec2.BlockDeviceVolume.ebs(100, {
            volumeType: ec2.EbsDeviceVolumeType.GP3,
            encrypted: true,
          }),
        },
      ],
      requireImdsv2: true,
    });

    // Outputs
    new cdk.CfnOutput(this, 'InstanceId', {
      value: instance.instanceId,
      description: 'EC2 Instance ID',
    });

    new cdk.CfnOutput(this, 'GradioUrl', {
      value: `http://${instance.instancePublicIp}:7860`,
      description: 'Gradio UI URL',
    });

    new cdk.CfnOutput(this, 'SsmConnectCommand', {
      value: `aws ssm start-session --target ${instance.instanceId}`,
      description: 'SSM connection command',
    });

    new cdk.CfnOutput(this, 'LogGroupUrl', {
      value: `https://${this.region}.console.aws.amazon.com/cloudwatch/home?region=${this.region}#logsV2:log-groups/log-group/$252Fqwen3-tts$252Fmodel-setup`,
      description: 'CloudWatch Log Group URL',
    });

    new cdk.CfnOutput(this, 'VpcId', {
      value: vpc.vpcId,
      description: 'VPC ID',
    });
  }
}
