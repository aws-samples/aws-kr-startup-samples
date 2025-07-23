#!/usr/bin/env python3
import os
import aws_cdk as cdk
from cdk_stacks import (
    VpcStack,
    S3Stack,
    GlueDatabaseStack,
    GlueCrawlerStack,
    AuroraMysqlStack,
    LambdaStack,
    EC2VSCodeStack,  # 활성화
    DmsIAMRolesStack,
    DmsStack,
    SyntheticsStack
)

APP_ENV = cdk.Environment(
    account=os.getenv('CDK_DEFAULT_ACCOUNT'),
    region=os.getenv('CDK_DEFAULT_REGION')
)

app = cdk.App()

# 파라미터 설정 (context에서 가져오거나 기본값 사용)
my_assets_bucket_name = app.node.try_get_context("myAssetsBucketName") or "your-assets-bucket"
my_assets_bucket_prefix = app.node.try_get_context("myAssetsBucketPrefix") or "assets/"
user_role_name = app.node.try_get_context("userRoleName") or "WSParticipantRole"
user_session_name = app.node.try_get_context("userSessionName") or "Participant"
raw_data_s3_prefix = "raw_data"
transformed_data_s3_prefix = "transformed_data"

# 1. VPC Stack
vpc_stack = VpcStack(
    app, 'VpcStack',
    env=APP_ENV
)

# 2. S3 Stack
s3_stack = S3Stack(
    app, 'S3Stack',
    env=APP_ENV
)

# 3. Glue Database Stack
glue_database_stack = GlueDatabaseStack(
    app, 'GlueDatabaseStack',
    env=APP_ENV
)

# 4. Glue Crawler Stack
glue_crawler_stack = GlueCrawlerStack(
    app, 'GlueCrawlerStack',
    athena_data_lake_bucket=s3_stack.athena_data_lake,
    raw_data_database_name=glue_database_stack.raw_data_database.ref,
    raw_data_s3_prefix=raw_data_s3_prefix,
    env=APP_ENV
)
glue_crawler_stack.add_dependency(s3_stack)
glue_crawler_stack.add_dependency(glue_database_stack)

# 5. Aurora MySQL Stack
aurora_mysql_stack = AuroraMysqlStack(
    app, 'AuroraMysqlStack',
    vpc=vpc_stack.vpc,
    env=APP_ENV
)
aurora_mysql_stack.add_dependency(vpc_stack)

# 6. Lambda Stack
lambda_stack = LambdaStack(
    app, 'LambdaStack',
    vpc=vpc_stack.vpc,
    aurora_hostname=aurora_mysql_stack.db_hostname,
    aurora_secret_arn=aurora_mysql_stack.db_secret.secret_arn,
    env=APP_ENV
)
lambda_stack.add_dependency(vpc_stack)
lambda_stack.add_dependency(aurora_mysql_stack)

# 7. EC2 VS Code Stack (보안 강화 버전)
ec2_vscode_stack = EC2VSCodeStack(
    app, 'EC2VSCodeStack',
    vpc=vpc_stack.vpc,
    env=APP_ENV
)
ec2_vscode_stack.add_dependency(vpc_stack)

# 8. DMS IAM Roles Stack
dms_iam_roles_stack = DmsIAMRolesStack(
    app, 'DmsIAMRolesStack',
    env=APP_ENV
)

# 9. DMS Stack
dms_stack = DmsStack(
    app, 'DmsStack',
    vpc=vpc_stack.vpc,
    mysql_client_sg=aurora_mysql_stack.sg_mysql_client,
    db_secret=aurora_mysql_stack.db_secret,
    source_database_hostname=aurora_mysql_stack.db_hostname,
    athena_data_lake_bucket=s3_stack.athena_data_lake,
    env=APP_ENV
)
dms_stack.add_dependency(vpc_stack)
dms_stack.add_dependency(aurora_mysql_stack)
dms_stack.add_dependency(s3_stack)
dms_stack.add_dependency(dms_iam_roles_stack)

# 10. QuickSight Stack - 제거
# quicksight_stack = QuickSightStack(
#     app, 'QuickSightStack',
#     quicksight_user_email=quicksight_user_email,
#     user_role_name=user_role_name,
#     user_session_name=user_session_name,
#     env=APP_ENV
# )

# 11. Synthetics Stack
synthetics_stack = SyntheticsStack(
    app, 'SyntheticsStack',
    canary_artifact_bucket=s3_stack.canary_artifact_bucket,
    env=APP_ENV
)
synthetics_stack.add_dependency(s3_stack)
# synthetics_stack.add_dependency(quicksight_stack)  # QuickSight 의존성 제거

app.synth()
