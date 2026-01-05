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

        # Separate ALB security group.
        # Note: CloudFront prefix list (pl-22a6434b) exceeds default SG rule limit (~130 rules).
        # Security is enforced via X-Origin-Verify header validation in ComputeStack.
        # To use prefix list, increase "Inbound rules per security group" quota to 200+.
        self.alb_sg = ec2.SecurityGroup(
            self,
            "AlbSg",
            vpc=self.vpc,
            description="ALB Security Group - Protected by X-Origin-Verify header",
        )

        # Allow HTTP/HTTPS from anywhere (security enforced by X-Origin-Verify header)
        self.alb_sg.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(443),
            "HTTPS (protected by X-Origin-Verify header)",
        )
        self.alb_sg.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(80),
            "HTTP (protected by X-Origin-Verify header)",
        )

        self.ecs_sg = ec2.SecurityGroup(self, "EcsSg", vpc=self.vpc)
        self.ecs_sg.add_ingress_rule(self.alb_sg, ec2.Port.tcp(8000))

        self.db_sg = ec2.SecurityGroup(self, "DbSg", vpc=self.vpc)
        self.db_sg.add_ingress_rule(self.ecs_sg, ec2.Port.tcp(5432))
