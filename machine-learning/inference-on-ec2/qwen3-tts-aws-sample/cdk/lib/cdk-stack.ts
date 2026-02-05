import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';
import * as fs from 'fs';
import * as path from 'path';

export class Qwen3TtsVoiceCloningStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // VPC: 2 Public + 2 Private Subnets
    const vpc = new ec2.Vpc(this, 'Qwen3TtsVoiceCloningVpc', {
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
    const securityGroup = new ec2.SecurityGroup(this, 'Qwen3TtsVoiceCloningSG', {
      vpc,
      description: 'Security group for Qwen3-TTS Voice Cloning EC2 instance',
      allowAllOutbound: true,
    });

    // Allow Gradio UI access (restricted to specific IP)
    const allowedIp = this.node.tryGetContext('allowedIp') || '0.0.0.0/0';
    securityGroup.addIngressRule(
      ec2.Peer.ipv4(allowedIp),
      ec2.Port.tcp(7860),
      'Gradio UI'
    );

    // CloudWatch Log Group
    const logGroup = new logs.LogGroup(this, 'ModelSetupLogGroup', {
      logGroupName: '/qwen3-tts-voice-cloning/model-setup',
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // IAM Role for EC2
    const role = new iam.Role(this, 'Qwen3TtsVoiceCloningRole', {
      assumedBy: new iam.ServicePrincipal('ec2.amazonaws.com'),
      description: 'IAM Role for Qwen3-TTS Voice Cloning EC2 instance',
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSSMManagedInstanceCore'),
        iam.ManagedPolicy.fromAwsManagedPolicyName('CloudWatchAgentServerPolicy'),
      ],
    });

    logGroup.grantWrite(role);

    // Read setup script (for system packages and model pre-loading only)
    const setupScriptPath = path.join(__dirname, '../../scripts/setup.sh');
    const setupScript = fs.readFileSync(setupScriptPath, 'utf8');

    // Read server script
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
                log_group_name: '/qwen3-tts-voice-cloning/model-setup',
                log_stream_name: '{instance_id}/model-setup',
                timezone: 'UTC',
              },
              {
                file_path: '/var/log/gradio-server.log',
                log_group_name: '/qwen3-tts-voice-cloning/model-setup',
                log_stream_name: '{instance_id}/gradio-server',
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
      '# Function to wait for apt/dpkg locks with timeout',
      'wait_for_apt() {',
      '    local max_wait=600',
      '    local waited=0',
      '    while fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1 || \\',
      '          fuser /var/lib/dpkg/lock >/dev/null 2>&1 || \\',
      '          fuser /var/lib/apt/lists/lock >/dev/null 2>&1 || \\',
      '          fuser /var/cache/apt/archives/lock >/dev/null 2>&1; do',
      '        if [ $waited -ge $max_wait ]; then',
      '            echo "Timeout waiting for apt locks after ${max_wait}s"',
      '            return 1',
      '        fi',
      '        echo "Waiting for apt/dpkg locks... (${waited}s)"',
      '        sleep 10',
      '        waited=$((waited + 10))',
      '    done',
      '    echo "All apt/dpkg locks released"',
      '}',
      '',
      '# Wait for apt locks before any package operation',
      'wait_for_apt',
      '',
      '# Install CloudWatch Agent with retry',
      'wget -q https://amazoncloudwatch-agent.s3.amazonaws.com/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb',
      'for i in 1 2 3; do',
      '    wait_for_apt',
      '    if dpkg -i amazon-cloudwatch-agent.deb; then',
      '        break',
      '    fi',
      '    echo "dpkg failed, retrying in 30s..."',
      '    sleep 30',
      'done',
      'rm -f amazon-cloudwatch-agent.deb',
      '',
      '# Configure CloudWatch Agent',
      `cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << 'CWCONFIG'`,
      JSON.stringify(cloudWatchAgentConfig, null, 2),
      'CWCONFIG',
      '',
      '# Start CloudWatch Agent',
      '/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -s -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json',
      '',
      '# Create directories',
      'mkdir -p /opt/app',
      'mkdir -p /opt/huggingface',
      '',
      '# Create server.py (independent of setup.sh)',
      `cat > /opt/app/server.py << 'SERVERSCRIPT'`,
      serverScript,
      'SERVERSCRIPT',
      '',
      '# Create gradio-server.service (independent of setup.sh)',
      `cat > /etc/systemd/system/gradio-server.service << 'GRADIOEOF'`,
      '[Unit]',
      'Description=Qwen3-TTS Gradio Server',
      'After=network-online.target model-setup.service',
      'Wants=network-online.target',
      '',
      '[Service]',
      'Type=simple',
      'User=root',
      'WorkingDirectory=/opt/app',
      'Environment="HF_HOME=/opt/huggingface"',
      'Environment="CUDA_VISIBLE_DEVICES=0"',
      'ExecStart=/opt/pytorch/bin/python /opt/app/server.py',
      'Restart=on-failure',
      'RestartSec=30',
      'StandardOutput=append:/var/log/gradio-server.log',
      'StandardError=append:/var/log/gradio-server.log',
      '',
      '[Install]',
      'WantedBy=multi-user.target',
      'GRADIOEOF',
      '',
      '# Create setup script (for system packages and model pre-loading)',
      `cat > /opt/setup.sh << 'SETUPSCRIPT'`,
      setupScript,
      'SETUPSCRIPT',
      '',
      'chmod +x /opt/setup.sh',
      '',
      '# Create model-setup.service (oneshot for pre-loading)',
      `cat > /etc/systemd/system/model-setup.service << 'ONESHOTEOF'`,
      '[Unit]',
      'Description=Qwen3-TTS Model Setup (System packages and model pre-loading)',
      'After=network-online.target',
      'Wants=network-online.target',
      'Before=gradio-server.service',
      '',
      '[Service]',
      'Type=oneshot',
      'ExecStart=/opt/setup.sh',
      'RemainAfterExit=yes',
      'StandardOutput=journal',
      'StandardError=journal',
      '',
      '[Install]',
      'WantedBy=multi-user.target',
      'ONESHOTEOF',
      '',
      '# Enable all services',
      'systemctl daemon-reload',
      'systemctl enable model-setup.service',
      'systemctl enable gradio-server.service',
      '',
      '# Start model-setup first (non-blocking), then gradio-server will start after',
      'systemctl start model-setup.service --no-block',
      'systemctl start gradio-server.service --no-block',
    );

    // AMI lookup
    const machineImage = ec2.MachineImage.lookup({
      name: 'Deep Learning OSS Nvidia Driver AMI GPU PyTorch 2.6* (Ubuntu 22.04)*',
      owners: ['amazon'],
    });

    // EC2 Instance in Public Subnet
    const instance = new ec2.Instance(this, 'Qwen3TtsVoiceCloningInstance', {
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
      value: `https://${this.region}.console.aws.amazon.com/cloudwatch/home?region=${this.region}#logsV2:log-groups/log-group/$252Fqwen3-tts-voice-cloning$252Fmodel-setup`,
      description: 'CloudWatch Log Group URL',
    });

    new cdk.CfnOutput(this, 'VpcId', {
      value: vpc.vpcId,
      description: 'VPC ID',
    });
  }
}
