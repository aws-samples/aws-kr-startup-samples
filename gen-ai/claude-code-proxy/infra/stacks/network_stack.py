from aws_cdk import Stack, aws_ec2 as ec2
from constructs import Construct


class NetworkStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        self.vpc = ec2.Vpc(
            self,
            "ProxyVpc",
            max_azs=2,
            nat_gateways=1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public", subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24,
                ),
            ],
        )

        # ECS tasks security group
        self.ecs_sg = ec2.SecurityGroup(
            self, "EcsSg", vpc=self.vpc, description="ECS tasks"
        )

        # VPC Link security group — API Gateway uses this to reach ECS
        self.vpclink_sg = ec2.SecurityGroup(
            self, "VpcLinkSg", vpc=self.vpc, description="API Gateway VPC Link"
        )
        self.ecs_sg.add_ingress_rule(
            self.vpclink_sg, ec2.Port.tcp(8000), "API Gateway VPC Link to ECS"
        )

        # Database security group
        self.db_sg = ec2.SecurityGroup(self, "DbSg", vpc=self.vpc)
        self.db_sg.add_ingress_rule(self.ecs_sg, ec2.Port.tcp(5432))
