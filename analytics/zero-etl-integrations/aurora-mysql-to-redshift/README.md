
# Amazon Aurora MySQL Zero-ETL integrations with Amazon Redshift Serverless

This repository provides you cdk scripts and sample code to create an Amazon RDS zero-ETL integration with Amazon Redshift Serverless.

An Amazon RDS zero-ETL integration with Amazon Redshift enables near real-time analytics and machine learning (ML) using Amazon Redshift on petabytes of transactional data from RDS.

![aurora-mysql-zero-etl-integration-with-redsfhit-serverless](./aurora-mysql-zero-etl-integration-with-redsfhit-serverless.svg)

The `cdk.json` file tells the CDK Toolkit how to execute your app.

This project is set up like a standard Python project.  The initialization
process also creates a virtualenv within this project, stored under the `.venv`
directory.  To create the virtualenv it assumes that there is a `python3`
(or `python` for Windows) executable in your path with access to the `venv`
package. If for any reason the automatic creation of the virtualenv fails,
you can create the virtualenv manually.

To manually create a virtualenv on MacOS and Linux:

```
$ git clone --depth=1 https://github.com/aws-samples/aws-kr-startup-samples.git
$ cd aws-kr-startup-samples
$ git sparse-checkout init --cone
$ git sparse-checkout set analytics/zero-etl-integrations/aurora-mysql-to-redshift
$ cd analytics/zero-etl-integrations/aurora-mysql-to-redshift

$ python3 -m venv .venv
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
(.venv) $ source .venv/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```
(.venv) % .venv\Scripts\activate.bat
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

Before synthesizing the CloudFormation, you need to prepare the cdk context configuration file, `cdk.context.json`:

For example,

<pre>
{
  "rds_cluster_name": "zero-etl-source-rds",
  "redshift": {
    "db_name": "zero-etl-target-rs",
    "namespace": "zero-etl-target-rs-ns",
    "workgroup": "zero-etl-target-rs-wg"
  },
  "zero_etl_integration": {
    "data_filter": "include: demodb.retail_trans",
    "integration_name": "zero-etl-rss"
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
(.venv) $ export CDK_DEFAULT_REGION=$(aws configure get region)
(.venv) $ cdk list
AuroraMySQLVpcStack
AuroraMySQLStack
AuroraMySQLClientHostStack
RedshiftServerlessStack
ZeroETLfromRDStoRSS
```

## Create Aurora MySQL cluster

  <pre>
  (.venv) $ cdk deploy AuroraMySQLVpcStack AuroraMySQLStack AuroraMySQLClientHostStack
  </pre>

## Create a sample database and table

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
    $ BASTION_HOST_ID=$(aws cloudformation describe-stacks --stack-name <i>AuroraMySQLClientHostStack</i> | \
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

   > :information_source: `AuroraMySQLClientHostStack` is a CDK Stack to create the bastion host.

   > :information_source: You can connect to an EC2 instance using the EC2 Instance Connect CLI: `aws ec2-instance-connect ssh`.
   For more information, see [Connect using the EC2 Instance Connect CLI](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-connect-methods.html#ec2-instance-connect-connecting-ec2-cli).

2. Run the below command to create the sample database named `demodb`.
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

    MySQL [(none)]> CREATE DATABASE IF NOT EXISTS demodb;
    Query OK, 1 row affected (0.01 sec)

    MySQL [(none)]> USE demodb;
    Database changed
    MySQL [demodb]> SHOW TABLES;
    Empty set (0.00 sec)
   </pre>
3. Also run this to create the sample table named `retail_trans`
   <pre>
    MySQL [demodb]> CREATE TABLE IF NOT EXISTS demodb.retail_trans (
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

    MySQL [demodb]> SHOW TABLES;
    +------------------+
    | Tables_in_demodb |
    +------------------+
    | retail_trans     |
    +------------------+
    1 row in set (0.00 sec)

    MySQL [demodb]> DESC retail_trans;
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

    MySQL [demodb]>
   </pre>

<b><em>After setting up the Aurora MySQL, you should come back to the terminal where you are deploying stacks.</em></b>

## Create Redshift Serverless cluster

  <pre>
  (.venv) $ cdk deploy RedshiftServerlessStack
  </pre>

## Configure authorization for your Amazon Redshift data warehouse

  Before you create a zero-ETL integration, you must create a source database and a target Amazon Redshift data warehouse.
  You also must allow replication into the data warehouse by adding the database as an authorized integration source.

  You can configure authorized integration sources from the **Resource Policy** tab on the Amazon Redshift console or using the Amazon Redshift `PutResourcePolicy` API operation.

  To control the source that can create an inbound integration into the namespace, create a resource policy and attach it to the namespace. With the resource policy, you can specify the source that has access to the integration.

  The following is a sample resource policy (e.g., `rs-rp.json`).

  <pre>
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "Service": "redshift.amazonaws.com"
        },
        "Action": "redshift:AuthorizeInboundIntegration",
        "Resource": "arn:aws:redshift-serverless:<i>{region}</i>:<i>{account-id}</i>:namespace/<i>namespace-uuid</i>",
        "Condition": {
          "StringEquals": {
            "aws:SourceArn": "arn:aws:rds:<i>{region}</i>:<i>{account-id}</i>:cluster:<i>{rds-cluster-name}</i>"
          }
        }
      }
    ]
  }
  </pre>

  :information_source: You can find out the Amazon Redshift namespace ARN by running the following.
  <pre>
  aws cloudformation describe-stacks --stack-name <i>RedshiftServerlessStack</i> | \
  jq -r '.Stacks[0].Outputs | .[] | select(.OutputKey | endswith("NamespaceNameArn")) | .OutputValue'
  </pre>

  To put a resource policy on your Amazon Redshift namespace ARN for a Aurora MySQL source,
  run a AWS CLI command similar to the following.

  <pre>
  (.venv) $ export CDK_DEFAULT_REGION=$(aws configure get region)
  (.venv) $ export RSS_RESOURCE_ARN=$(aws cloudformation describe-stacks --stack-name <i>RedshiftServerlessStack</i> | \
  jq -r '.Stacks[0].Outputs | .[] | select(.OutputKey | endswith("NamespaceNameArn")) | .OutputValue')
  (.venv) $ aws redshift put-resource-policy \
                --region ${CDK_DEFAULT_REGION} \
                --policy file://rs-rp.json \
                --resource-arn ${RSS_RESOURCE_ARN}
  </pre>

## Create Zero ETL Integration with filters

  In this example we only want to replicate data from the MySQL table `demodb.retail_trans` to Redshift.
  So we add the data filtering option to `cdk.context.json` like this:
  <pre>
   {
     ...
     "zero_etl_integration": {
       "data_filter": "include: demodb.retail_trans",
       "integration_name": "zero-etl-rss"
     }
   }
  </pre>
  > :information_source: [Data filtering for Amazon RDS zero-ETL integrations with Amazon Redshift](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/zero-etl.filtering.html)

  Now let's create the Zero-ETL integration.
  It takes a few minutes to change the status of the Zero-ETL integration from **Creating** to **Active**.
  The time varies depending on size of the dataset already available in the source.
  <pre>
  (.venv) $ cdk deploy ZeroETLfromRDStoRSS
  </pre>

## Test Zero-ETL Integration

#### (1) Load Data Into Amazon Aurora MySQL Cluster

  <pre>
    $ export BASTION_HOST_ID=$(aws cloudformation describe-stacks --stack-name <i>AuroraMySQLClientHostStack</i> | jq -r '.Stacks[0].Outputs | .[] | select(.OutputKey | endswith("EC2InstanceId")) | .OutputValue')

    $ aws ec2-instance-connect ssh --instance-id ${BASTION_HOST_ID} --os-user ec2-user

    [ec2-user@ip-172-31-7-186 ~]$ python3 gen_fake_mysql_data.py \
                                    --database <i>your-database-name</i> \
                                    --table <i>your-table-name</i> \
                                    --user <i>user-name</i> \
                                    --password <i>password</i> \
                                    --host <i>db-cluster-name</i>.cluster-<i>xxxxxxxxxxxx</i>.<i>region-name</i>.rds.amazonaws.com \
                                    --max-count 10
  </pre>

  After filling data into the MySQL table, connect to the Aurora cluster writer node and run some queries.

  For example, retrieve some records.
   <pre>
    $ mysql -h<i>db-cluster-name</i>.cluster-<i>xxxxxxxxxxxx</i>.<i>region-name</i>.rds.amazonaws.com -uadmin -p
    Enter password:
    Welcome to the MariaDB monitor.  Commands end with ; or \g.
    Your MySQL connection id is 20
    Server version: 8.0.23 Source distribution

    Copyright (c) 2000, 2018, Oracle, MariaDB Corporation Ab and others.

    Type 'help;' or '\h' for help. Type '\c' to clear the current input statement.

    MySQL [(none)]> USE demodb;
    Database changed

    MySQL [demodb]> SELECT count(*) FROM retail_trans;
    +----------+
    | count(*) |
    +----------+
    |      10  |
    +----------+
    1 row in set (0.01 sec)

    MySQL [demodb]> SELECT * FROM retail_trans LIMIT 10;
    +----------+--------------+----------+------------+--------+--------+---------------------+
    | trans_id | customer_id  | event    | sku        | amount | device | trans_datetime      |
    +----------+--------------+----------+------------+--------+--------+---------------------+
    |        1 | 460104780596 | cart     | IQ6879MMTB |      8 | mobile | 2023-01-16 06:08:06 |
    |        2 | 758933025159 | like     | RL1573WWLT |      1 | tablet | 2023-01-16 06:17:21 |
    |        3 | 754384589074 | like     | PX4135DYNT |      1 | mobile | 2023-01-16 06:08:52 |
    |        4 | 602811489876 | purchase | PI7913TREO |     66 | pc     | 2023-01-16 06:01:07 |
    |        5 | 222732129586 | like     | AS6987HGLN |      1 | mobile | 2023-01-16 06:09:06 |
    |        6 | 387378799012 | list     | AI6161BEFX |      1 | pc     | 2023-01-16 06:10:27 |
    |        7 | 843982894991 | cart     | DA7930CJBR |     81 | pc     | 2023-01-16 06:11:41 |
    |        8 | 818177069814 | like     | JS6166YPTE |      1 | pc     | 2023-01-16 06:17:08 |
    |        9 | 248083404876 | visit    | AS8552DVOO |      1 | pc     | 2023-01-16 06:24:39 |
    |       10 | 731184658511 | visit    | XZ9997LSJN |      1 | tablet | 2023-01-16 06:12:18 |
    +----------+--------------+----------+------------+--------+--------+---------------------+
    10 rows in set (0.00 sec)
   </pre>

#### (2) Create a database from the integration in Amazon Redshift

To create your database, complete the following steps:

1. On the Redshift Serverless dashboard, navigate to the `zero-etl-target-rs-ns` namespace.
2. Choose **Query data** to open Query Editor v2.
  ![](./assets/choose-reshift-serverless-query-data.jpg)
3. Connect to the Redshift Serverless data warehouse by choosing **Create connection**.
  ![](./assets/create-redshift-serverless-connection.jpg)
4. Obtain the `integration_id` from the `svv_integration` system table:
   ```
   ---- copy this result, use in the next sql
   SELECT integration_id FROM svv_integration;
   ```
5. Use the `integration_id` from the previous step to create a new database from the integration:
   ```
   CREATE DATABASE aurora_zeroetl FROM INTEGRATION '<result from above>';
   ```
   The integration is now complete, and an entire snapshot of the source will reflect as is in the destination. Ongoing changes will be synced in near-real time.

6. On the Redshift Serverless dashboard, open Query Editor v2 using the database you created as part of the integration setup. Use the following query to get information about checkpoint, snaphost, and subsequent CDC data replication:
   ```
   SELECT * FROM SYS_INTEGRATION_ACTIVITY
   WHERE TRUNC(INTEGRATION_START_TIME)= CURRENT_DATE
   ORDER BY INTEGRATION_START_TIME;
   ```

## Clean Up

1. To delete a zero-ETL integration, run the below command.
   <pre>
   (.venv) $ cdk destroy --force -e ZeroETLfromRDStoRSS
   </pre>

    When you delete a zero-ETL integration, your transactional data isn’t deleted from Aurora or Amazon Redshift, but Aurora doesn’t send new data to Amazon Redshift.

2. If you want to delete all CloudFormation stacks, run the below command.
   <pre>
   (.venv) $ cdk destroy --force --all
   </pre>

## Useful commands

#### CDK CLI Installation

 * `npm install -g aws-cdk`          install the AWS CDK Toolkit (the `cdk` command).
 * `npm install -g aws-cdk@latest`   install the latest AWS CDK Toolkit (the `cdk`command).

#### CDK CLI commands

 * `cdk init app --language python`  create a new, empty CDK Python project.
 * `cdk bootstrap --profile <AWS Profile>` Deploys the CDK Toolkit staging stack; see [Bootstrapping](https://docs.aws.amazon.com/cdk/v2/guide/bootstrapping.html)
 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

Enjoy!

## References

 * [(User Guide) Aurora zero-ETL integrations with Amazon Redshift](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/zero-etl.html)
   * [Data filtering for Aurora zero-ETL integrations with Amazon Redshift](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/zero-etl.filtering.html)
   * [Aurora zero-ETL integrations with Amazon Redshift - Limitations](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/zero-etl.html#zero-etl.reqs-lims)
 * [(Management Guide) Amazon Redshift - Zero-ETL integrations](https://docs.aws.amazon.com/redshift/latest/mgmt/zero-etl-using.html)
   * [Configure authorization for your Amazon Redshift data warehouse](https://docs.aws.amazon.com/redshift/latest/mgmt/zero-etl-using.redshift-iam.html)
 * [(AWS Blog) Getting started guide for near-real time operational analytics using Amazon Aurora zero-ETL integration with Amazon Redshift (2023-06-28)](https://aws.amazon.com/blogs/big-data/getting-started-guide-for-near-real-time-operational-analytics-using-amazon-aurora-zero-etl-integration-with-amazon-redshift/)
 * [(AWS Blog) Unlock insights on Amazon RDS for MySQL data with zero-ETL integration to Amazon Redshift (2024-03-21)](https://aws.amazon.com/blogs/big-data/unlock-insights-on-amazon-rds-for-mysql-data-with-zero-etl-integration-to-amazon-redshift/)
 * [(Workshop) Zero ETL Integration](https://catalog.us-east-1.prod.workshops.aws/workshops/fc6069e2-a3a7-475c-9592-9f62843b3ffb)
 * [(Workshop) Achieve near real-time data analytics with Zero-ETL on AWS](https://catalog.us-east-1.prod.workshops.aws/workshops/692aa2ab-7c66-41f4-a8fd-92a8c93f5b9a)
 * [AWS CDK Toolkit (cdk command)](https://docs.aws.amazon.com/cdk/v2/guide/cli.html)
