
# Migrating Data from Aurora MySQL to S3 with AWS DMS Serverless

![dms_serverless-mysql-to-s3-arch](./dms_serverless-mysql-to-s3-arch.svg)

This is a data pipeline project using AWS DMS Serverless for Python development with CDK.

The `cdk.json` file tells the CDK Toolkit how to execute your app.

This project is set up like a standard Python project.  The initialization
process also creates a virtualenv within this project, stored under the `.venv`
directory.  To create the virtualenv it assumes that there is a `python3`
(or `python` for Windows) executable in your path with access to the `venv`
package. If for any reason the automatic creation of the virtualenv fails,
you can create the virtualenv manually.

To manually create a virtualenv on MacOS and Linux:

```
$ python3 -m venv .venv
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .venv/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```
% .venv\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```
(.venv) $ pip install -r requirements.txt
```

To add additional dependencies, for example other CDK libraries, just add
them to your `setup.py` file and rerun the `pip install -r requirements.txt`
command.

## Prerequisites

**Set up `cdk.context.json`**

Then, before deploying the CloudFormation, you should set approperly the cdk context configuration file, `cdk.context.json`.

For example,
<pre>
{
  "db_cluster_name": "<i>db-cluster-name</i>",
  "dms_data_source": {
    "database_name": "<i>testdb</i>",
    "table_name": "<i>retail_trans</i>"
  },
  "dms_data_target": {
    "s3_bucket_name": "<i>target-s3-bucket</i>",
    "s3_bucket_folder_name": "<i>target-s3-prefix</i>"
  }
}
</pre>

**Bootstrap AWS environment for AWS CDK app**

Also, before any AWS CDK app can be deployed, you have to bootstrap your AWS environment to create certain AWS resources that the AWS CDK CLI (Command Line Interface) uses to deploy your AWS CDK app.

Run the `cdk bootstrap` command to bootstrap the AWS environment.

```
(.venv) $ cdk bootstrap
```

Now you can deploy the CloudFormation template for this code.

## List all CDK Stacks

```
(.venv) $ export CDK_DEFAULT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
(.venv) $ export CDK_DEFAULT_REGION=$(curl -s 169.254.169.254/latest/dynamic/instance-identity/document | jq -r .region)
(.venv) $ cdk list
DMSAuroraMysqlToS3VPCStack
AuroraMysqlStack
AuroraMysqlBastionHost
DMSServerlessTargetS3Stack
DMSRequiredIAMRolesStack
DMSServerlessAuroraMysqlToS3Stack
```

At this point you can now synthesize the CloudFormation template for this code.

<pre>
(.venv) $ cdk synth --all
</pre>

We can provision each CDK stack shown above one at a time like this:

## Create Aurora MySQL cluster

  <pre>
  (.venv) $ cdk deploy DMSAuroraMysqlToS3VPCStack AuroraMysqlStack AuroraMysqlBastionHost
  </pre>

## Confirm that binary logging is enabled

<b><em>In order to set up the Aurora MySQL, you need to connect the Aurora MySQL cluster on an EC2 Bastion host.</em></b>

:information_source: The Aurora MySQL `username` and `password` are stored in the [AWS Secrets Manager](https://console.aws.amazon.com/secretsmanager/listsecrets) as a name such as `DatabaseSecret-xxxxxxxxxxxx`.

**To retrieve a secret (AWS console)**

- (Step 1) Open the Secrets Manager console at [https://console.aws.amazon.com/secretsmanager/](https://console.aws.amazon.com/secretsmanager/).
- (Step 2) In the list of secrets, choose the secret you want to retrieve.
- (Step 3) In the **Secret value** section, choose **Retrieve secret value**.<br/>
Secrets Manager displays the current version (`AWSCURRENT`) of the secret. To see [other versions](https://docs.aws.amazon.com/secretsmanager/latest/userguide/getting-started.html#term_version) of the secret, such as `AWSPREVIOUS` or custom labeled versions, use the [AWS CLI](https://docs.aws.amazon.com/secretsmanager/latest/userguide/retrieving-secrets.html#retrieving-secrets_cli).

**To confirm that binary logging is enabled**

1. Connect to the Aurora cluster writer node.
   <pre>
    $ BASTION_HOST_ID=$(aws cloudformation describe-stacks --stack-name <i>AuroraMysqlBastionHost</i> | \
    jq -r '.Stacks[0].Outputs | .[] | select(.OutputKey | endswith("EC2InstanceId")) | .OutputValue')

    $ aws ec2-instance-connect ssh --instance-id ${BASTION_HOST_ID} --os-user ec2-user

    [ec2-user@ip-172-31-7-186 ~]$ mysql -h<i>db-cluster-name</i>.cluster-<i>xxxxxxxxxxxx</i>.<i>region-name</i>.rds.amazonaws.com -uadmin -p
    Enter password:
    Welcome to the MySQL monitor.  Commands end with ; or \g.
    Your MySQL connection id is 947748268
    Server version: 5.7.12-log MySQL Community Server (GPL)

    Copyright (c) 2000, 2020, Oracle and/or its affiliates. All rights reserved.

    Oracle is a registered trademark of Oracle Corporation and/or its
    affiliates. Other names may be trademarks of their respective
    owners.

    Type 'help;' or '\h' for help. Type '\c' to clear the current input statement.

    MySQL [(none)]>
   </pre>

   > :information_source: `AuroraMysqlBastionHost` is a CDK Stack to create the bastion host.

   > :information_source: You can connect to an EC2 instance using the EC2 Instance Connect CLI: `aws ec2-instance-connect ssh`.
   For more information, see [Connect using the EC2 Instance Connect CLI](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-connect-methods.html#ec2-instance-connect-connecting-ec2-cli).


2. At SQL prompt run the below command to confirm that binary logging is enabled:
   <pre>
    MySQL [(none)]> SHOW GLOBAL VARIABLES LIKE "log_bin";
    +---------------+-------+
    | Variable_name | Value |
    +---------------+-------+
    | log_bin       | ON    |
    +---------------+-------+
    1 row in set (0.00 sec)
   </pre>

3. Also run this to AWS DMS has bin log access that is required for replication
   <pre>
    MySQL [(none)]> CALL mysql.rds_set_configuration('binlog retention hours', 24);
    Query OK, 0 rows affected (0.01 sec)
   </pre>

## Create a sample database and table

1. Run the below command to create the sample database named `testdb`.
   <pre>
    MySQL [(none)]> SHOW DATABASES;
    +--------------------+
    | Database           |
    +--------------------+
    | information_schema |
    | mysql              |
    | performance_schema |
    | sys                |
    +--------------------+
    4 rows in set (0.00 sec)

    MySQL [(none)]> CREATE DATABASE IF NOT EXISTS testdb;
    Query OK, 1 row affected (0.01 sec)

    MySQL [(none)]> USE testdb;
    Database changed
    MySQL [testdb]> SHOW TABLES;
    Empty set (0.00 sec)
   </pre>
2. Also run this to create the sample table named `retail_trans`
   <pre>
    MySQL [testdb]> CREATE TABLE IF NOT EXISTS testdb.retail_trans (
             trans_id BIGINT(20) AUTO_INCREMENT,
             customer_id VARCHAR(12) NOT NULL,
             event VARCHAR(10) DEFAULT NULL,
             sku VARCHAR(10) NOT NULL,
             amount INT DEFAULT 0,
             device VARCHAR(10) DEFAULT NULL,
             trans_datetime DATETIME DEFAULT CURRENT_TIMESTAMP,
             PRIMARY KEY(trans_id),
             KEY(trans_datetime)
           ) ENGINE=InnoDB AUTO_INCREMENT=0;
    Query OK, 0 rows affected, 1 warning (0.04 sec)

    MySQL [testdb]> SHOW TABLES;
    +------------------+
    | Tables_in_testdb |
    +------------------+
    | retail_trans     |
    +------------------+
    1 row in set (0.00 sec)

    MySQL [testdb]> DESC retail_trans;
    +----------------+-------------+------+-----+-------------------+-------------------+
    | Field          | Type        | Null | Key | Default           | Extra             |
    +----------------+-------------+------+-----+-------------------+-------------------+
    | trans_id       | bigint      | NO   | PRI | NULL              | auto_increment    |
    | customer_id    | varchar(12) | NO   |     | NULL              |                   |
    | event          | varchar(10) | YES  |     | NULL              |                   |
    | sku            | varchar(10) | NO   |     | NULL              |                   |
    | amount         | int         | YES  |     | 0                 |                   |
    | device         | varchar(10) | YES  |     | NULL              |                   |
    | trans_datetime | datetime    | YES  | MUL | CURRENT_TIMESTAMP | DEFAULT_GENERATED |
    +----------------+-------------+------+-----+-------------------+-------------------+
    7 rows in set (0.00 sec)

    MySQL [testdb]>
   </pre>

<b><em>After setting up the Aurora MySQL, you should come back to the terminal where you are deploying stacks.</em></b>

## Create Amazon S3 bucket for AWS DMS target endpoint

  <pre>
  (.venv) $ cdk deploy DMSServerlessTargetS3Stack
  </pre>

## Create AWS DMS Replication Task
  In the previous step we already created the sample database (i.e. `testdb`) and table (`retail_trans`).

  Now let's create a migration task.
  <pre>
  (.venv) $ cdk deploy DMSRequiredIAMRolesStack DMSServerlessAuroraMysqlToS3Stack
  </pre>

## Run Test

1. Generate test data.
   <pre>
    $ BASTION_HOST_ID=$(aws cloudformation describe-stacks --stack-name <i>AuroraMysqlBastionHost</i> \
    | jq -r '.Stacks[0].Outputs | .[] | select(.OutputKey | endswith("EC2InstanceId")) |.OutputValue')

    $ aws ec2-instance-connect ssh --instance-id ${BASTION_HOST_ID} --os-user ec2-user

    [ec2-user@ip-172-31-7-186 ~]$ cat <&ltEOF >requirements-dev.txt
    > boto3
    > dataset==1.5.2
    > Faker==13.3.1
    > PyMySQL==1.0.2
    > EOF
    [ec2-user@ip-172-31-7-186 ~]$ pip install -r requirements-dev.txt
    [ec2-user@ip-172-31-7-186 ~]$ python3 gen_fake_mysql_data.py \
                   --database <i>your-database-name</i> \
                   --table <i>your-table-name</i> \
                   --user <i>user-name</i> \
                   --password <i>password</i> \
                   --host <i>db-cluster-name</i>.cluster-<i>xxxxxxxxxxxx</i>.<i>region-name</i>.rds.amazonaws.com \
                   --max-count 200
   </pre>

2. Start the DMS Replication task by replacing the ARN in below command.<br/>
   <b><em>After ingesting data, you need to come back to the terminal where you are deploying stacks.</em></b>
   <pre>
   (.venv) $ DMS_REPLICATION_CONFIG_ARN=$(aws cloudformation describe-stacks --stack-name <i>DMSServerlessAuroraMysqlToS3Stack</i> \
   | jq -r '.Stacks[0].Outputs | map(select(.OutputKey == "DMSReplicationConfigArn")) | .[0].OutputValue')
   (.venv) $ aws dms start-replication \
                     --replication-config-arn <i>${DMS_REPLICATION_CONFIG_ARN}</i> \
                     --start-replication-type start-replication
   </pre>

3. Check s3 and you will see data in the s3 location such as:
   <pre>
    s3://{<i>target-s3-bucket</i>}/{<i>target-s3-prefix</i>}/{<i>your-database-name</i>}/{<i>your-table-name</i>}/
   </pre>

## Clean Up
1. Stop the DMS Replication task by replacing the ARN in below command.
   <pre>
   (.venv) $ DMS_REPLICATION_CONFIG_ARN=$(aws cloudformation describe-stacks --stack-name <i>DMSServerlessAuroraMysqlToS3Stack</i> \
   | jq -r '.Stacks[0].Outputs | map(select(.OutputKey == "DMSReplicationConfigArn")) | .[0].OutputValue')
   (.venv) $ aws dms stop-replication \
                     --replication-config-arn <i>${DMS_REPLICATION_CONFIG_ARN}</i>
   </pre>
2. Delete the CloudFormation stack by running the below command.
   <pre>
   (.venv) $ cdk destroy --force --all
   </pre>

## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

Enjoy!

## References

 * [AWS DMS Serverless: Automatically Provisions and Scales Capacity for Migration and Data Replication (2023-06-01)](https://aws.amazon.com/blogs/aws/new-aws-dms-serverless-automatically-provisions-and-scales-capacity-for-migration-and-data-replication/)
 * [aws-dms-deployment-using-aws-cdk](https://github.com/aws-samples/aws-dms-deployment-using-aws-cdk) - AWS DMS deployment using AWS CDK (Python)
 * [aws-dms-msk-demo](https://github.com/aws-samples/aws-dms-msk-demo) - Streaming Data to Amazon MSK via AWS DMS
 * [How to troubleshoot binary logging errors that I received when using AWS DMS with Aurora MySQL as the source?(Last updated: 2019-10-01)](https://aws.amazon.com/premiumsupport/knowledge-center/dms-binary-logging-aurora-mysql/)
 * [AWS DMS - Using Amazon Kinesis Data Streams as a target for AWS Database Migration Service](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Target.Kinesis.html)
 * [Specifying task settings for AWS Database Migration Service tasks](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Tasks.CustomizingTasks.TaskSettings.html#CHAP_Tasks.CustomizingTasks.TaskSettings.Example)
 * [Working with AWS DMS Serverless](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Serverless.html)
 * [How AWS DMS handles open transactions when starting a full load and CDC task (2022-12-26)](https://aws.amazon.com/blogs/database/how-aws-dms-handles-open-transactions-when-starting-a-full-load-and-cdc-task/)
 * [AWS DMS key troubleshooting metrics and performance enhancers (2023-02-10)](https://aws.amazon.com/blogs/database/aws-dms-key-troubleshooting-metrics-and-performance-enhancers/)
 * [Connect using the EC2 Instance Connect CLI](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-connect-methods.html#ec2-instance-connect-connecting-ec2-cli)
   <pre>
   $ sudo pip install ec2instanceconnectcli
   $ mssh ec2-user@i-001234a4bf70dec41EXAMPLE # ec2-instance-id
   </pre>

## Related Works

 * [aws-msk-serverless-cdc-data-pipeline-with-debezium](https://github.com/aws-samples/aws-msk-serverless-cdc-data-pipeline-with-debezium)
   ![aws-msk-serverless-cdc-data-pipeline-arch](https://raw.githubusercontent.com/aws-samples/aws-msk-serverless-cdc-data-pipeline-with-debezium/main/aws-msk-connect-cdc-data-pipeline-arch.svg)
 * [aws-msk-cdc-data-pipeline-with-debezium](https://github.com/aws-samples/aws-msk-cdc-data-pipeline-with-debezium)
   ![aws-msk-cdc-data-pipeline-arch](https://raw.githubusercontent.com/aws-samples/aws-msk-cdc-data-pipeline-with-debezium/main/aws-msk-connect-cdc-data-pipeline-arch.svg)
 * [aws-dms-cdc-data-pipeline](https://github.com/aws-samples/aws-dms-cdc-data-pipeline)
   ![aws-dms-cdc-data-pipeline-arch](https://raw.githubusercontent.com/aws-samples/aws-dms-cdc-data-pipeline/main/aws-dms-cdc-analytics-arch.svg)
 * [aws-dms-serverless-to-kinesis-data-pipeline](https://github.com/aws-samples/aws-dms-serverless-to-kinesis-data-pipeline)
   ![aws-dms-serverless-to-kinesis-data-pipeline-arch](https://raw.githubusercontent.com/aws-samples/aws-dms-serverless-to-kinesis-data-pipeline/main/dms_serverless-mysql-to-kinesis-arch.svg)

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.
