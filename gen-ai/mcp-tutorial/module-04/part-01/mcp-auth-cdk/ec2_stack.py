from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_iam as iam,
    CfnOutput,
    Tags,
    CfnParameter,
    Aws
)
from constructs import Construct

class EC2InstanceStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # VPC ID를 파라미터로 받기
        vpc_id_param = CfnParameter(
            self, "VpcId",
            type="String",
            description="ID of the VPC where the subnet is located"
        )

        # Public Subnet ID를 파라미터로 받기
        subnet_id_param = CfnParameter(
            self, "PublicSubnetId",
            type="String",
            description="ID of the public subnet where the EC2 instance will be launched"
        )

        # 가용 영역을 파라미터로 받기
        az_param = CfnParameter(
            self, "AvailabilityZone",
            type="String",
            description="Availability Zone of the subnet"
        )

        # VPC 참조
        vpc = ec2.Vpc.from_vpc_attributes(
            self, "VPC",
            vpc_id=vpc_id_param.value_as_string,
            availability_zones=[az_param.value_as_string],
            public_subnet_ids=[subnet_id_param.value_as_string]
        )
        
        # 서브넷 참조 - 가용 영역 포함
        subnet = ec2.Subnet.from_subnet_attributes(
            self, "PublicSubnet",
            subnet_id=subnet_id_param.value_as_string,
            availability_zone=az_param.value_as_string
        )

        # Systems Manager를 위한 IAM 역할 생성
        ssm_role = iam.Role(
            self, "EC2SSMRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            description="IAM role for EC2 instance to use Systems Manager Session Manager"
        )

        # Systems Manager 관리형 인스턴스 정책 추가
        ssm_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore")
        )

        # CloudWatch Logs 정책 추가
        ssm_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("CloudWatchAgentServerPolicy")
        )

        # Bedrock 권한 추가
        ssm_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:Converse",
                    "bedrock:InvokeModelWithResponseStream"
                ],
                resources=["*"]
            )
        )

        # 보안 그룹 생성
        security_group = ec2.SecurityGroup(
            self, "EC2SecurityGroup",
            vpc=vpc,
            description="Security group for MCP EC2 instance",
            allow_all_outbound=True
        )

        # 초기 보안 그룹 규칙 추가 - 임시로 특정 포트 허용
        security_group.add_ingress_rule(
            ec2.Peer.ipv4("10.0.0.0/16"),  # VPC CIDR 또는 안전한 IP 범위
            ec2.Port.tcp(8080),
            "Allow access to MCP server port (temporary)"
        )
        security_group.add_ingress_rule(
            ec2.Peer.ipv4("10.0.0.0/16"),  # VPC CIDR 또는 안전한 IP 범위
            ec2.Port.tcp(8501),
            "Allow access to Streamlit port (temporary)"
        )

        # EC2 인스턴스 생성
        instance = ec2.Instance(
            self, "MCPInstance",
            vpc=vpc,
            availability_zone=az_param.value_as_string,
            instance_type=ec2.InstanceType("c5.large"),
            machine_image=ec2.AmazonLinuxImage(
                generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2023
            ),
            security_group=security_group,
            role=ssm_role,
            block_devices=[
                ec2.BlockDevice(
                    device_name="/dev/xvda",
                    volume=ec2.BlockDeviceVolume.ebs(
                        volume_size=30,
                        volume_type=ec2.EbsDeviceVolumeType.GP3,
                        delete_on_termination=True
                    )
                )
            ]
        )

        # 인스턴스에 태그 추가
        Tags.of(instance).add("Name", "MCP-Auth-Instance")
        Tags.of(instance).add("Environment", "Production")
        Tags.of(instance).add("Project", "MCP-Auth")

        # 출력값 설정
        CfnOutput(
            self, "InstancePublicDNS",
            value=instance.instance_public_dns_name,
            description="Public DNS of the instance"
        )
        CfnOutput(
            self, "InstancePublicIP",
            value=instance.instance_public_ip,
            description="Public IP of the instance (Use this as MCP Server IP)"
        )
        CfnOutput(
            self, "InstanceId",
            value=instance.instance_id,
            description="Instance ID"
        )
        CfnOutput(
            self, "SSMConnectCommand",
            value=f"aws ssm start-session --target {instance.instance_id} --region {Aws.REGION}",
            description="Command to connect to the instance using Session Manager"
        )
        CfnOutput(
            self, "ClientConnectionCommand",
            value=f"python app/streamlit-app/client.py http://{instance.instance_public_ip}:8080/sse UserID Password",
            description="Command to connect MCP Client to this instance"
        )
        CfnOutput(
            self, "SecurityGroupUpdateCommand",
            value=f"aws ec2 authorize-security-group-ingress --group-id {security_group.security_group_id} --protocol tcp --port 8080 --cidr {instance.instance_public_ip}/32 --region {Aws.REGION}",
            description="Command to update security group to allow access from instance's public IP to port 8080"
        )
        CfnOutput(
            self, "SecurityGroupUpdateCommand2",
            value=f"aws ec2 authorize-security-group-ingress --group-id {security_group.security_group_id} --protocol tcp --port 8501 --cidr {instance.instance_public_ip}/32 --region {Aws.REGION}",
            description="Command to update security group to allow access from instance's public IP to port 8501"
        )