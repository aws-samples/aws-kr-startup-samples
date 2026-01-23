from aws_cdk import Stack, Duration, aws_ec2 as ec2, aws_rds as rds
from constructs import Construct


class DatabaseStack(Stack):
    def __init__(
        self, scope: Construct, id: str, vpc: ec2.Vpc, db_sg: ec2.SecurityGroup, **kwargs
    ) -> None:
        super().__init__(scope, id, **kwargs)

        self.cluster = rds.DatabaseCluster(
            self,
            "ProxyDb",
            engine=rds.DatabaseClusterEngine.aurora_postgres(
                version=rds.AuroraPostgresEngineVersion.VER_17_4
            ),
            serverless_v2_min_capacity=0.5,
            serverless_v2_max_capacity=4,
            writer=rds.ClusterInstance.serverless_v2("writer"),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            security_groups=[db_sg],
            storage_encrypted=True,
            backup=rds.BackupProps(retention=Duration.days(7)),
            credentials=rds.Credentials.from_generated_secret("postgres"),
            default_database_name="proxy",  # 초기 데이터베이스 생성
        )

        self.db_secret = self.cluster.secret
