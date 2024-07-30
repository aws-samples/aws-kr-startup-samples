#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_ec2,
  aws_iam,
  aws_s3_assets
)
from constructs import Construct


class BastionHostEC2InstanceStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, vpc, sg_rds_client, sg_msk_client, msk_cluster_name, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    sg_bastion_host = aws_ec2.SecurityGroup(self, "BastionHostSG",
      vpc=vpc,
      allow_all_outbound=True,
      description='security group for an bastion host',
      security_group_name=f'bastion-host-sg-{self.stack_name}'
    )
    cdk.Tags.of(sg_bastion_host).add('Name', 'bastion-host-sg')

    #TODO: SHOULD restrict IP range allowed to ssh acces
    sg_bastion_host.add_ingress_rule(peer=aws_ec2.Peer.ipv4("0.0.0.0/0"),
      connection=aws_ec2.Port.tcp(22), description='SSH access')

    #XXX: For more information, see https://docs.aws.amazon.com/msk/latest/developerguide/create-iam-role.html
    kafka_client_iam_policy = aws_iam.Policy(self, 'KafkaClientIAMPolicy',
      statements=[
        aws_iam.PolicyStatement(**{
          "effect": aws_iam.Effect.ALLOW,
          "resources": [ f"arn:aws:kafka:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:cluster/{msk_cluster_name}/*" ],
          "actions": [
            "kafka-cluster:Connect",
            "kafka-cluster:AlterCluster",
            "kafka-cluster:DescribeCluster"
          ]
        }),
        aws_iam.PolicyStatement(**{
          "effect": aws_iam.Effect.ALLOW,
          "resources": [ f"arn:aws:kafka:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:topic/{msk_cluster_name}/*" ],
          "actions": [
            "kafka-cluster:*Topic*",
            "kafka-cluster:WriteData",
            "kafka-cluster:ReadData"
          ]
        }),
        aws_iam.PolicyStatement(**{
          "effect": aws_iam.Effect.ALLOW,
          "resources": [ f"arn:aws:kafka:{cdk.Aws.REGION}:{cdk.Aws.ACCOUNT_ID}:group/{msk_cluster_name}/*" ],
          "actions": [
            "kafka-cluster:AlterGroup",
            "kafka-cluster:DescribeGroup"
          ]
        })
      ]
    )
    kafka_client_iam_policy.apply_removal_policy(cdk.RemovalPolicy.DESTROY)

    bastion_host_role = aws_iam.Role(self, 'MySQLClientEC2InstanceRole',
      role_name=f'MySQLClientEC2InstanceRole-{self.stack_name}',
      assumed_by=aws_iam.ServicePrincipal('ec2.amazonaws.com'),
      managed_policies=[
        aws_iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSSMManagedInstanceCore'),
        #XXX: EC2 instance should be able to access S3 for user data
        # aws_iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3ReadOnlyAccess')
      ]
    )
    kafka_client_iam_policy.attach_to_role(bastion_host_role)

    #XXX: https://docs.aws.amazon.com/cdk/api/latest/python/aws_cdk.aws_ec2/InstanceClass.html
    #XXX: https://docs.aws.amazon.com/cdk/api/latest/python/aws_cdk.aws_ec2/InstanceSize.html#aws_cdk.aws_ec2.InstanceSize
    ec2_instance_type = aws_ec2.InstanceType.of(aws_ec2.InstanceClass.BURSTABLE3, aws_ec2.InstanceSize.MEDIUM)

    bastion_host = aws_ec2.Instance(self, 'BastionHostEC2Instance',
      instance_type=ec2_instance_type,
      machine_image=aws_ec2.MachineImage.latest_amazon_linux2(),
      instance_name=f'{self.stack_name}/BastionHost',
      role=bastion_host_role,
      security_group=sg_bastion_host,
      vpc=vpc,
      vpc_subnets=aws_ec2.SubnetSelection(subnet_type=aws_ec2.SubnetType.PUBLIC),
    )
    bastion_host.add_security_group(sg_rds_client)
    bastion_host.add_security_group(sg_msk_client)

    # test data generator script in S3 as Asset
    user_data_asset = aws_s3_assets.Asset(self, 'BastionHostUserData',
      path=os.path.join(os.path.dirname(__file__), '../utils/gen_fake_mysql_data.py'))
    user_data_asset.grant_read(bastion_host.role)

    USER_DATA_LOCAL_PATH = bastion_host.user_data.add_s3_download_command(
      bucket=user_data_asset.bucket,
      bucket_key=user_data_asset.s3_object_key
    )

    commands = '''
yum update -y
yum install -y python3.7
yum install -y jq
yum install -y mysql

cd /home/ec2-user
wget https://bootstrap.pypa.io/get-pip.py
su -c "python3.7 get-pip.py --user" -s /bin/sh ec2-user
su -c "/home/ec2-user/.local/bin/pip3 install boto3 --user" -s /bin/sh ec2-user
'''

    commands += f'''
su -c "/home/ec2-user/.local/bin/pip3 install dataset==1.5.2 Faker==13.3.1 PyMySQL==1.0.2 --user" -s /bin/sh ec2-user
cp {USER_DATA_LOCAL_PATH} /home/ec2-user/gen_fake_mysql_data.py & chown -R ec2-user /home/ec2-user/gen_fake_mysql_data.py
'''

    commands += '''
yum update -y
yum install -y java-11

mkdir -p /home/ec2-user/opt
cd /home/ec2-user/opt
wget https://archive.apache.org/dist/kafka/2.8.1/kafka_2.12-2.8.1.tgz
tar -xzf kafka_2.12-2.8.1.tgz
ln -nsf kafka_2.12-2.8.1 kafka

cd /home/ec2-user/opt/kafka/libs
wget https://github.com/aws/aws-msk-iam-auth/releases/download/v1.1.1/aws-msk-iam-auth-1.1.1-all.jar

chown -R ec2-user /home/ec2-user/opt
chgrp -R ec2-user /home/ec2-user/opt

cd /home/ec2-user
cat <<EOF > msk_serverless_client.properties
security.protocol=SASL_SSL
sasl.mechanism=AWS_MSK_IAM
sasl.jaas.config=software.amazon.msk.auth.iam.IAMLoginModule required;
sasl.client.callback.handler.class=software.amazon.msk.auth.iam.IAMClientCallbackHandler
EOF

ln -nsf msk_serverless_client.properties client.properties
chown -R ec2-user /home/ec2-user/msk_serverless_client.properties
chown -R ec2-user /home/ec2-user/client.properties

echo 'export PATH=$HOME/opt/kafka/bin:$PATH' >> .bash_profile
'''

    bastion_host.user_data.add_commands(commands)


    cdk.CfnOutput(self, f'{self.stack_name}-EC2InstancePublicDNS',
      value=bastion_host.instance_public_dns_name,
      export_name=f'{self.stack_name}-EC2InstancePublicDNS')
    cdk.CfnOutput(self, f'{self.stack_name}-EC2InstanceId',
      value=bastion_host.instance_id,
      export_name=f'{self.stack_name}-EC2InstanceId')
    cdk.CfnOutput(self, f'{self.stack_name}-EC2InstanceAZ',
      value=bastion_host.instance_availability_zone,
      export_name=f'{self.stack_name}-EC2InstanceAZ')

