
# Build Data Analytics using Amazon Data Migration Service(DMS)

This repository provides you cdk scripts and sample code on how to implement end to end data pipeline for replicating transactional data from MySQL DB to Amazon OpenSearch Service through Amazon Kinesis using Amazon Data Migration Service(DMS).

## Streaming Pipeline

Below diagram shows what we are implementing.

![aws-dms-cdc-analytics-arch](./aws-dms-cdc-analytics-arch.svg)

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

**Create a key pair using Amazon EC2**

For this project, you'll need to create a key pair for Amazon EC2 if you don't already have one.

- Open the Amazon EC2 console at [https://console.aws.amazon.com/ec2/](https://console.aws.amazon.com/ec2/),
- Follow the instructions below to create a key pair and save it to **your local PC**.
  - [Create a key pair using Amazon EC2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/create-key-pairs.html#having-ec2-create-your-key-pair)

:warning: You will need to keep the Amazon EC2 key pair on **your local PC** to complete this project.

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
  "kinesis_stream_name": "<i>your-dms-target-kinesis-stream-name</i>",
  "opensearch_domain_name": "<i>your-opensearch-domain-name</i>",
  "opensearch_index_name": "<i>your-opensearch-index-name</i>",
  "ec2_key_pair_name": "<i>your-ec2-key-pair-name(exclude .pem extension)</i>"
}
</pre>

:warning: `ec2_key_pair_name` option should be entered without the `.pem` extension.

**Bootstrap AWS environment for AWS CDK app**

Also, before any AWS CDK app can be deployed, you have to bootstrap your AWS environment to create certain AWS resources that the AWS CDK CLI (Command Line Interface) uses to deploy your AWS CDK app.

Run the `cdk bootstrap` command to bootstrap the AWS environment.

```
(.venv) $ cdk bootstrap
```

Now you can deploy the CloudFormation template for this code.

## List all CDK Stacks

```
(.venv) $ cdk list
VpcStack
AuroraMysqlStack
AuroraMysqlBastionHost
DMSTargetKinesisDataStreamStack
DMSRequiredIAMRolesStack
DMSAuroraMysqlToKinesisStack
OpenSearchStack
FirehoseStack
```

## Create Aurora MySQL cluster

  <pre>
  (.venv) $ cdk deploy VpcStack AuroraMysqlStack AuroraMysqlBastionHost
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
    Welcome to the MariaDB monitor.  Commands end with ; or \g.
    Your MySQL connection id is 20
    Server version: 8.0.23 Source distribution

    Copyright (c) 2000, 2018, Oracle, MariaDB Corporation Ab and others.

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

## Create Amazon Kinesis Data Streams for AWS DMS target endpoint

  <pre>
  (.venv) $ cdk deploy DMSTargetKinesisDataStreamStack
  </pre>

## Create AWS DMS Replication Task
  In the previous step we already created the sample database (i.e. `testdb`) and table (`retail_trans`).

  Now let's create a migration task.
  <pre>
  (.venv) $ cdk deploy DMSRequiredIAMRolesStack DMSAuroraMysqlToKinesisStack
  </pre>

## Create Amazon OpenSearch Service

1. :warning: Create a Service-Linked Role for Amazon OpenSearch Service

   If you do not already have a Service-Linked Role (SLR) for Amazon OpenSearch Service named `AWSServiceRoleForAmazonOpenSearchService`,
   you will need to create one for this project.

   Check to see if `AWSServiceRoleForAmazonOpenSearchService` exists by running the following command:

   ```
   aws iam get-role --role-name AWSServiceRoleForAmazonOpenSearchService
   ```

   If it does not exist, you will seea message like this:
   ```
   An error occurred (NoSuchEntity) when calling the GetRole operation: The role with name AWSServiceRoleForAmazonOpenSearchService cannot be found.
   ```
   If it does, we recommend that you create the required Service Link Role (`AWSServiceRoleForAmazonOpenSearchService`) using the AWS CLI:
   ```
   aws iam create-service-linked-role --aws-service-name opensearchservice.amazonaws.com
   ```

   Some cluster configurations (e.g VPC access) require the existence of the `AWSServiceRoleForAmazonOpenSearchService` Service-Linked Role.

   When performing such operations via the AWS Console, this SLR is created automatically when needed.
   However, this is not the behavior when using CloudFormation.
   If an SLR(Service-Linked Role) is needed, but doesn’t exist, you will encounter a failure message simlar to:

   <pre>
   11:11:30 AM | CREATE_FAILED        | AWS::OpenSearchService::Domain      | OpenSearch587998CD
   Resource handler returned message: "Invalid request provided: Before you can proceed, you must enable a service-linked role to give Amazon OpenSearch Service permissions to access your VPC. (Servi
   ce: OpenSearch, Status Code: 400, Request ID: 8e9618af-1554-4605-93a2-8c4cc22e2412)" (RequestToken: ccad0316-8daa-5c2a-89a1-056e1e88f23a, HandlerErrorCode: InvalidRequest)
   </pre>

   To resolve this, you need to [create](https://docs.aws.amazon.com/IAM/latest/UserGuide/using-service-linked-roles.html#create-service-linked-role) the SLR as described above.

   :information_source: For more information, see [here](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/slr.html).

2. Create an Amazon OpenSearch Service domain

  <pre>
  (.venv) $ cdk deploy OpenSearchStack
  </pre>

## Create Amazon Kinesis Data Firehose

  <pre>
  (.venv) $ cdk deploy FirehoseStack
  </pre>

## Remotely access your Amazon OpenSearch Cluster using SSH tunnel from local machine
#### Access to your Amazon OpenSearch Dashboards with web browser
1. To access the OpenSearch Cluster, add the ssh tunnel configuration to the ssh config file of the personal local PC as follows

    <pre>
    # OpenSearch Tunnel
    Host opstunnel
        HostName <i>EC2-Public-IP-of-Bastion-Host</i>
        User ec2-user
        IdentitiesOnly yes
        IdentityFile <i>Path-to-SSH-Public-Key</i>
        LocalForward 9200 <i>OpenSearch-Endpoint</i>:443
    </pre>

    ex)

    ```
    ~$ ls -1 .ssh/
    config
    my-ec2-key-pair.pem

    ~$ tail .ssh/config
    # OpenSearch Tunnel
    Host opstunnel
        HostName 214.132.71.219
        User ec2-user
        IdentitiesOnly yes
        IdentityFile ~/.ssh/my-ec2-key-pair.pem
        LocalForward 9200 vpc-search-domain-qvwlxanar255vswqna37p2l2cy.us-east-1.es.amazonaws.com:443

    ~$
    ```

    You can find the bastion host's public ip address as running the commands like this:

    <pre>
    $ BASTION_HOST_ID=$(aws cloudformation describe-stacks --stack-name <i>AuroraMysqlBastionHost</i> \
    | jq -r '.Stacks[0].Outputs | .[] | select(.OutputKey | endswith("EC2InstanceId")) | .OutputValue')

    $ aws ec2 describe-instances --instance-ids ${BASTION_HOST_ID} | jq -r '.Reservations[0].Instances[0].PublicIpAddress'
    </pre>

2. Run `ssh -N opstunnel` in Terminal.
3. Connect to `https://localhost:9200/_dashboards/app/login?` in a web browser.
4. Enter the master user and password that you set up when you created the Amazon OpenSearch Service endpoint. The user name and password of the master user are stored in the [AWS Secrets Manager](https://console.aws.amazon.com/secretsmanager/listsecrets) as a name such as `OpenSearchMasterUserSecret1-xxxxxxxxxxxx`.
5. In the Welcome screen, click the toolbar icon to the left side of **Home** button. Choose **Stack Managerment**
   ![ops-dashboards-sidebar-menu](./assets/ops-dashboards-sidebar-menu.png)
6. After selecting **Advanced Settings** from the left sidebar menu, set **Timezone** for date formatting to `Etc/UTC`.
   Since the log creation time of the test data is based on UTC, OpenSearch Dashboard’s Timezone is also set to UTC.
   ![ops-dashboards-stack-management-advanced-setting.png](./assets/ops-dashboards-stack-management-advanced-setting.png)
7. If you would like to access the OpenSearch Cluster in a termial, open another terminal window, and then run the following commands: (in here, <i>`your-cloudformation-stack-name`</i> is `OpensearchStack`)

    <pre>
    $ MASTER_USER_SECRET_ID=$(aws cloudformation describe-stacks --stack-name <i>OpenSearchStack</i> \
    | jq -r '.Stacks[0].Outputs | map(select(.OutputKey == "MasterUserSecretId")) | .[0].OutputValue')

    $ export OPS_SECRETS=$(aws secretsmanager get-secret-value --secret-id ${MASTER_USER_SECRET_ID} \
    | jq -r '.SecretString | fromjson | "\(.username):\(.password)"')

    $ export OPS_DOMAIN=$(aws cloudformation describe-stacks --stack-name <i>OpenSearchStack</i> \
    | jq -r '.Stacks[0].Outputs | map(select(.OutputKey == "OpenSearchDomainEndpoint")) | .[0].OutputValue')

    $ curl -XGET --insecure -u "${OPS_SECRETS}" https://localhost:9200/_cluster/health?pretty=true
    $ curl -XGET --insecure -u "${OPS_SECRETS}" https://localhost:9200/_cat/nodes?v
    $ curl -XGET --insecure -u "${OPS_SECRETS}" https://localhost:9200/_nodes/stats?pretty=true
    </pre>

#### Enable Kinesis Data Firehose to ingest records into Amazon OpenSearch
Kinesis Data Firehose uses the delivery role to sign HTTP (Signature Version 4) requests before sending the data to the Amazon OpenSearch Service endpoint.
You manage Amazon OpenSearch Service fine-grained access control permissions using roles, users, and mappings.
This section describes how to create roles and set permissions for Kinesis Data Firehose.

Complete the following steps:

1. Navigate to the OpenSearch Dashboards (you can find the URL on the Amazon OpenSearch Service console) in a web browser.
2. Enter the master user and password that you set up when you created the Amazon OpenSearch Service endpoint. The user and password are stored in the [AWS Secrets Manager](https://console.aws.amazon.com/secretsmanager/listsecrets) as a name such as `OpenSearchMasterUserSecret1-xxxxxxxxxxxx`.
3. In the Welcome screen, click the toolbar icon to the left side of **Home** button. Choose **Security**.
   ![ops-dashboards-sidebar-menu-security](./assets/ops-dashboards-sidebar-menu-security.png)
4. Under **Security**, choose **Roles**.
5. Choose **Create role**.
6. Name your role; for example, `firehose_role`.
7. For cluster permissions, add `cluster_composite_ops` and `cluster_monitor`.
8. Under **Index permissions**, choose **Index Patterns** and enter <i>index-name*</i>; for example, `retail-trans*`.
9. Under **Permissions**, add three action groups: `crud`, `create_index`, and `manage`.
10. Choose **Create**.
    ![ops-create-firehose_role](./assets/ops-create-firehose_role.png)

In the next step, you map the IAM role that Kinesis Data Firehose uses to the role you just created.

10. Choose the **Mapped users** tab.
    ![ops-role-mappings](./assets/ops-role-mappings.png)
11. Choose **Manage mapping** and under **Backend roles**,
12. For **Backend Roles**, enter the IAM ARN of the role Kinesis Data Firehose uses:
    `arn:aws:iam::123456789012:role/firehose_stream_role_name`.
    ![ops-entries-for-firehose_role](./assets/ops-entries-for-firehose_role.png)
13. Choose **Map**.
  > **Note**: After OpenSearch Role mapping for Kinesis Data Firehose, you would not be supposed to meet a data delivery failure with Kinesis Data Firehose like this:

    Error received from the Amazon OpenSearch Service cluster or OpenSearch Serverless collection.
    If the cluster or collection is behind a VPC, ensure network configuration allows connectivity.

    {
      "error": {
        "root_cause": [
          {
            "type": "security_exception",
            "reason": "no permissions for [indices:data/write/bulk] and User [name=arn:aws:iam::123456789012:role/KinesisFirehoseServiceRole-retail-trans-us-east-1, backend_roles=[arn:aws:iam::123456789012:role/KinesisFirehoseServiceRole-retail-trans-us-east-1], requestedTenant=null]"
          }
        ],
        "type": "security_exception",
        "reason": "no permissions for [indices:data/write/bulk] and User [name=arn:aws:iam::123456789012:role/KinesisFirehoseServiceRole-retail-trans-us-east-1, backend_roles=[arn:aws:iam::123456789012:role/KinesisFirehoseServiceRole-retail-trans-us-east-1], requestedTenant=null]"
      },
      "status": 403
    }

## Run Test

1. Start the DMS Replication task by replacing the ARN in below command.
   <pre>
   (.venv) $ DMS_TASK_ARN=$(aws cloudformation describe-stacks --stack-name <i>DMSAuroraMysqlToKinesisStack</i> \
   | jq -r '.Stacks[0].Outputs | map(select(.OutputKey == "DMSReplicationTaskArn")) | .[0].OutputValue')
   (.venv) $ aws dms start-replication-task --replication-task-arn <i>${DMS_TASK_ARN}</i> --start-replication-task-type start-replication
   </pre>

2. Generate test data.
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
    [ec2-user@ip-172-31-7-186 ~]$ python3 utils/gen_fake_mysql_data.py \
                   --database <i>your-database-name</i> \
                   --table <i>your-table-name</i> \
                   --user <i>user-name</i> \
                   --password <i>password</i> \
                   --host <i>db-cluster-name</i>.cluster-<i>xxxxxxxxxxxx</i>.<i>region-name</i>.rds.amazonaws.com \
                   --max-count 200
   </pre>
   In the Data Viewer in the Amazon Kinesis Management Console, you can see incomming records.
   ![amazon-kinesis-data-viewer](./assets/amazon-kinesis-data-viewer.png)

3. Check the Amazon OpenSearch Discover Dashboard `5~10` minutes later, and you will see data ingested from the Aurora MySQL.<br/>
  For example,
   <pre>
   {
    "_index": "trans",
    "_type": "_doc",
    "_id": "49627593537354623426044597072248245532118434881168474130.0",
    "_version": 1,
    "_score": null,
    "_source": {
      "data": {
        "trans_id": 1274,
        "customer_id": "958474449243",
        "event": "purchase",
        "sku": "HM4387NUZL",
        "amount": 100,
        "device": "pc",
        "trans_datetime": "2022-03-14T14:17:40Z"
      },
      "metadata": {
        "timestamp": "2022-03-14T14:18:11.104009Z",
        "record-type": "data",
        "operation": "insert",
        "partition-key-type": "primary-key",
        "schema-name": "testdb",
        "table-name": "retail_trans",
        "transaction-id": 8590392498
      }
    },
    "fields": {
      "data.trans_datetime": [
        "2022-03-14T14:17:40.000Z"
      ],
      "metadata.timestamp": [
        "2022-03-14T14:18:11.104Z"
      ]
    },
    "sort": [
      1647267460000
    ]
   }
   </pre>

## Clean Up

1. Stop the DMS Replication task by replacing the ARN in below command.
   <pre>
   (.venv) $ DMS_TASK_ARN=$(aws cloudformation describe-stacks --stack-name <i>DMSAuroraMysqlToKinesisStack</i> \
   | jq -r '.Stacks[0].Outputs | map(select(.OutputKey == "DMSReplicationTaskArn")) | .[0].OutputValue')
   (.venv) $ aws dms stop-replication-task --replication-task-arn <i>${DMS_TASK_ARN}</i>
   </pre>

2. Delete the CloudFormation stack by running the below command.
   <pre>
   (.venv) $ cdk destroy --all
   </pre>

## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

Enjoy!

## References

 * [aws-dms-deployment-using-aws-cdk](https://github.com/aws-samples/aws-dms-deployment-using-aws-cdk) - AWS DMS deployment using AWS CDK (Python)
 * [aws-dms-msk-demo](https://github.com/aws-samples/aws-dms-msk-demo) - Streaming Data to Amazon MSK via AWS DMS
 * [How to troubleshoot binary logging errors that I received when using AWS DMS with Aurora MySQL as the source?(Last updated: 2019-10-01)](https://aws.amazon.com/premiumsupport/knowledge-center/dms-binary-logging-aurora-mysql/)
 * [AWS DMS - Using Amazon Kinesis Data Streams as a target for AWS Database Migration Service](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Target.Kinesis.html)
 * [Specifying task settings for AWS Database Migration Service tasks](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Tasks.CustomizingTasks.TaskSettings.html#CHAP_Tasks.CustomizingTasks.TaskSettings.Example)
 * [Identity and access management for AWS Database Migration Service](https://docs.aws.amazon.com/dms/latest/userguide/security-iam.html#CHAP_Security.APIRole)
 * [How AWS DMS handles open transactions when starting a full load and CDC task (2022-12-26)](https://aws.amazon.com/blogs/database/how-aws-dms-handles-open-transactions-when-starting-a-full-load-and-cdc-task/)
 * [AWS DMS key troubleshooting metrics and performance enhancers (2023-02-10)](https://aws.amazon.com/blogs/database/aws-dms-key-troubleshooting-metrics-and-performance-enhancers/)
 * [Windows SSH / Tunnel for Kibana Instructions - Amazon Elasticsearch Service](https://search-sa-log-solutions.s3-us-east-2.amazonaws.com/logstash/docs/Kibana_Proxy_SSH_Tunneling_Windows.pdf)
 * [Use an SSH Tunnel to access Kibana within an AWS VPC with PuTTy on Windows](https://amazonmsk-labs.workshop.aws/en/mskkdaflinklab/createesdashboard.html)
 * [OpenSearch Popular APIs](https://opensearch.org/docs/latest/opensearch/popular-api/)
 * [Using Data Viewer in the Kinesis Console](https://docs.aws.amazon.com/streams/latest/dev/data-viewer.html)
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
 * [aws-dms-serverless-to-kinesis-data-pipeline](https://github.com/aws-samples/aws-dms-serverless-to-kinesis-data-pipeline)
   ![aws-dms-serverless-to-kinesis-data-pipeline-arch](https://raw.githubusercontent.com/aws-samples/aws-dms-serverless-to-kinesis-data-pipeline/main/dms_serverless-mysql-to-kinesis-arch.svg)
 * [aws-dms-serverless-mysql-to-s3-migration](https://github.com/aws-samples/aws-dms-serverless-mysql-to-s3-migration)
   ![aws-dms-serverless-mysql-to-s3-migration-arch](https://raw.githubusercontent.com/aws-samples/aws-dms-serverless-mysql-to-s3-migration/main/dms_serverless-mysql-to-s3-arch.svg)

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

