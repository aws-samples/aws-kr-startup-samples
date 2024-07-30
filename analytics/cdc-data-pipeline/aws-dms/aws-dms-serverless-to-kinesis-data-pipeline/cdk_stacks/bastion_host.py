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

  def __init__(self, scope: Construct, construct_id: str, vpc, sg_rds_client, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    sg_bastion_host = aws_ec2.SecurityGroup(self, 'BastionHostSG',
      vpc=vpc,
      allow_all_outbound=True,
      description='security group for an bastion host',
      security_group_name='bastion-host-sg'
    )
    cdk.Tags.of(sg_bastion_host).add('Name', 'bastion-host-sg')

    #TODO: SHOULD restrict IP range allowed to ssh acces
    sg_bastion_host.add_ingress_rule(peer=aws_ec2.Peer.ipv4("0.0.0.0/0"),
      connection=aws_ec2.Port.tcp(22), description='SSH access')

    bastion_host_role = aws_iam.Role(self, 'MySQLClientEC2InstanceRole',
      role_name=f'MySQLClientEC2InstanceRole-{self.stack_name}',
      assumed_by=aws_iam.ServicePrincipal('ec2.amazonaws.com'),
      managed_policies=[
        aws_iam.ManagedPolicy.from_aws_managed_policy_name('AmazonSSMManagedInstanceCore'),
        #XXX: EC2 instance should be able to access S3 for user data
        # aws_iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3ReadOnlyAccess')
      ]
    )

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

    # test data generator script in S3 as Asset
    user_data_asset = aws_s3_assets.Asset(self, 'BastionHostUserData',
      path=os.path.join(os.path.dirname(__file__), '../utils/gen_fake_mysql_data.py'))
    user_data_asset.grant_read(bastion_host.role)

    USER_DATA_LOCAL_PATH = bastion_host.user_data.add_s3_download_command(
      bucket=user_data_asset.bucket,
      bucket_key=user_data_asset.s3_object_key
    )

    commands = '''
yum -q update -y
yum -q install -y jq
yum -q install -y mysql

yum groupinstall "Development Tools" -y
yum install -y epel
yum erase -y openssl-devel
yum install -y openssl11-devel
cd /home/ec2-user
wget https://www.python.org/ftp/python/3.11.8/Python-3.11.8.tgz
tar xvf Python-3.11.8.tgz
cd Python-3.11.8/
sed -i 's/PKG_CONFIG openssl /PKG_CONFIG openssl11 /g' configure
./configure --enable-optimizations --with-ensurepip=install
make install
cd /home/ec2-user

su -c "/usr/local/bin/python3.11 -m pip install boto3 --user" -s /bin/sh ec2-user
curl -s "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install

echo 'alias aws2=/usr/local/bin/aws' >> .bash_profile
'''

    commands += f'''
su -c "/home/ec2-user/.local/bin/pip3 install dataset==1.5.2 Faker==13.3.1 PyMySQL==1.0.2 --user" -s /bin/sh ec2-user
cp {USER_DATA_LOCAL_PATH} /home/ec2-user/gen_fake_mysql_data.py & chown -R ec2-user /home/ec2-user/gen_fake_mysql_data.py
'''

    bastion_host.user_data.add_commands(commands)

    self.sg_bastion_host = sg_bastion_host

    cdk.CfnOutput(self, f'{self.stack_name}-EC2InstancePublicDNS',
      value=bastion_host.instance_public_dns_name,
      export_name=f'{self.stack_name}-EC2InstancePublicDNS')
    cdk.CfnOutput(self, f'{self.stack_name}-EC2InstanceId',
      value=bastion_host.instance_id,
      export_name=f'{self.stack_name}-EC2InstanceId')
    cdk.CfnOutput(self, f'{self.stack_name}-EC2InstanceAZ',
      value=bastion_host.instance_availability_zone,
      export_name=f'{self.stack_name}-EC2InstanceAZ')

