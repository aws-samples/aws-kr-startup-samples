
# Transactional Data Lake using Apache Iceberg with AWS Glue Streaming and MSK Connect (Debezium)

This repository provides you cdk scripts and sample code on how to implement end to end data pipeline for transactional data lake by ingesting stream change data capture (CDC) from MySQL DB to Amazon S3 in Apache Iceberg format through Amazon MSK using Amazon MSK Connect and Glue Streaming.

## Stream CDC into an Amazon S3 data lake in Apache Iceberg format with AWS Glue Streaming and MSK Connect (Debezium)

Below diagram shows what we are implementing.

![transactional-datalake-arch](./transactional-datalake-arch.svg)

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

Before synthesizing the CloudFormation,

1. Create a custom plugin

   (a) Download the MySQL connector plugin for the latest stable release from the [Debezium](https://debezium.io/releases/) site.<br/>
   (b) Download and extract the [AWS Secrets Manager Config Provider](https://www.confluent.io/hub/jcustenborder/kafka-config-provider-aws).<br/>
   (c) Compress the directory that you created in the previous step into a ZIP file and then upload the ZIP file to an S3 bucket.<br/>
    ```
    $ mkdir -p debezium-connector-mysql
    $ tar -xzf debezium-connector-mysql-2.4.0.Final-plugin.tar.gz -C debezium-connector-mysql
    $ unzip jcustenborder-kafka-config-provider-aws-0.1.2.zip -d debezium-connector-mysql
    $ cd debezium-connector-mysql/jcustenborder-kafka-config-provider-aws-0.1.2/lib
    $ wget https://repo1.maven.org/maven2/com/google/guava/guava/31.1-jre/guava-31.1-jre.jar
    $ cd ../../
    $ zip -9 -r ../debezium-connector-mysql-v2.4.0.zip *
    $ cd ..
    $ aws s3 cp debezium-connector-mysql-v2.4.0.zip s3://my-bucket/path/
    ```
   (d) Copy the following JSON and paste it in a file. For example, `debezium-source-custom-plugin.json`.<br/>
    ```json
    {
      "name": "debezium-connector-mysql-v2-4-0",
      "contentType": "ZIP",
      "location": {
          "s3Location": {
            "bucketArn": "arn:aws:s3:::<my-bucket>",
            "fileKey": "<path>/debezium-connector-mysql-v2.4.0.zip"
        }
      }
    }
    ```
   (e) Run the following AWS CLI command from the folder where you saved the JSON file to create a plugin.
    <pre>
    aws kafkaconnect create-custom-plugin --cli-input-json file://<i>debezium-source-custom-plugin.json</i>
    </pre>

2. Create a custom worker configuration with information about your configuration provider.

   (a) Copy the following worker configuration properties into a file.<br/>
      To learn more about the configuration properties for the AWS Secrets Manager Config Provider, see [SecretsManagerConfigProvider](https://jcustenborder.github.io/kafka-connect-documentation/projects/kafka-config-provider-aws/configProviders/SecretsManagerConfigProvider.html) in the plugin's documentation.
      <pre>
      key.converter=<i>org.apache.kafka.connect.storage.StringConverter</i>
      key.converter.schemas.enable=<i>false</i>
      value.converter=<i>org.apache.kafka.connect.json.JsonConverter</i>
      value.converter.schemas.enable=<i>false</i>
      config.providers.secretManager.class=com.github.jcustenborder.kafka.config.aws.SecretsManagerConfigProvider
      config.providers=secretManager
      config.providers.secretManager.param.aws.region=<i>us-east-1</i>
      </pre>
    (b) Run the following AWS CLI command to create your custom worker configuration.<br/>
        Replace the following values:

     - `my-worker-config-name` - a descriptive name for your custom worker configuration (e.g., `AuroraMySQLSource` )
     - `encoded-properties-file-content-string` - a base64-encoded version of the plaintext properties that you copied in the previous step

      <pre>
      aws kafkaconnect create-worker-configuration \
          --name <i>&lt;my-worker-config-name&gt;</i> \
          --properties-file-content <i>&lt;encoded-properties-file-content-string&gt;</i>
      </pre>
      You should see output similar to the following example on the AWS Web console.
      ![msk-connect-worker-configurations](assets/msk-connect-worker-configurations.png)

  :information_source: To learn more about how to create a Debezium source connector, see [Debezium source connector with configuration provider](https://docs.aws.amazon.com/msk/latest/developerguide/mkc-debeziumsource-connector-example.html)

3. **Set up Apache Iceberg connector for AWS Glue to use Apache Iceberg with AWS Glue jobs.** (For more information, see [References](#references) (2)). Then `glue_connections_name` of `cdk.context.json` configuration file should be set by Apache Iceberg connector name like this:
   <pre>
   { "glue_connections_name": "iceberg-connection" }
   </pre>

4. **Create a S3 bucket for a glue job script and upload the glue job script file into the s3 bucket.** Then `glue_assets_s3_bucket_name` and `glue_job_script_file_name` of `cdk.context.json` configuration file should be set by the S3 bucket name and the glue job script file name like this:
   <pre>
   {
      "glue_assets_s3_bucket_name": "aws-glue-assets-123456789012-us-east-1",
      "glue_job_script_file_name": "spark_sql_merge_into_iceberg.py"
   }
   </pre>

5. Set up the cdk context configuration file, `cdk.context.json`.

Then you set other remaining configurations of the cdk context configuration file `cdk.context.json` accordingly.

For example:
<pre>
{
  "vpc_name": "default",
  "db_cluster_name": "retail",
  "msk_cluster_name": "retail-trans",
  "msk_connector_worker_configuration_name": "AuroraMySQLSource",
  "msk_connector_custom_plugin_name": "debezium-connector-mysql-v2-4-0",
  "msk_connector_name": "retail-changes",
  "msk_connector_configuration": {
    "tasks.max": "1",
    "database.include.list": "testdb",
    "topic.prefix": "retail-server",
    "topic.creation.default.partitions": "3",
    "topic.creation.default.replication.factor": "2",
    "include.schema.changes": "true",
    "schema.history.internal.kafka.topic": "schema-changes.testdb"
  },
  "glue_assets_s3_bucket_name": "aws-glue-assets-123456789012-us-east-1",
  "glue_job_script_file_name": "spark_sql_merge_into_iceberg.py",
  "glue_job_name": "cdc_based_upsert_to_iceberg_table",
  "glue_job_input_arguments": {
    "--catalog": "job_catalog",
    "--database_name": "cdc_iceberg_demo_db",
    "--table_name": "retail_trans_iceberg",
    "--primary_key": "trans_id",
    "--kafka_topic_name": "retail-server.testdb.retail_trans",
    "--starting_offsets_of_kafka_topic": "earliest",
    "--iceberg_s3_path": "s3://glue-iceberg-demo-us-east-1/cdc_iceberg_demo_db",
    "--lock_table_name": "iceberg_lock",
    "--aws_region": "us-east-1",
    "--window_size": "100 seconds",
    "--extra-jars": "s3://aws-glue-assets-123456789012-us-east-1/extra-jars/aws-sdk-java-2.17.224.jar",
    "--user-jars-first": "true"
  },
  "glue_connections_name": "iceberg-connection"
}
</pre>

:information_source: `--primary_key` of `glue_job_input_arguments` should be set by Iceberg table's primary column name. So, it is better to set the primary key of RDS table.

:information_source: `--extra-jars` and `--user-jars-first` of `glue_job_input_arguments` is used in the 4th step of [Set up Glue Streaming Job](#set-up-glue-streaming-job).

## Deployment

Now you can now synthesize the CloudFormation template for this code.

<pre>
(.venv) $ export CDK_DEFAULT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
(.venv) $ export CDK_DEFAULT_REGION=$(aws configure get region)
(.venv) $ cdk synth --all
</pre>


Now let's try to deploy.

#### Listing all CDK Stacks

```
(.venv) $ cdk list
TrxDataLakeVpc
AuroraMysqlAsDataSource
MSKAsGlueStreamingJobDataSource
TrxDataLakeBastionHost
GlueStreamingCDCtoIcebergS3Path
GlueMSKConnection
GlueStreamingMSKtoIcebergJobRole
GlueIcebergDatabase
GrantLFPermissionsOnGlueJobRole
GlueStreamingJobMSKtoIceberg
KafkaConnectorStack
```

#### (Step 1) Creating Aurora MySQL cluster

Create an Aurora MySQL Cluster

   <pre>
   (.venv) $ cdk deploy TransactionalDataLakeVpc AuroraMysqlAsDMSDataSource
   </pre>

#### (Step 2) Creating Kafka cluster

(1) Create a MSK Cluster

   <pre>
   (.venv) $ cdk deploy MSKAsGlueStreamingJobDataSource
   </pre>

Once MSK cluster has been successfully created,
you should update the MSK cluster configuration by running the following python scripts
in order to grant Kinesis Data Firehose to access Amazon MSK cluster.

It will take at least `20~25` minutes to update the settings.
Please wait until the MSK cluster status is `ACTIVE`.

(2) Update **Network settings**

<pre>
import boto3

cluster_name = '{<i>msk-cluster-name</i>}'
region = '{<i>region</i>}'

client = boto3.client('kafka', region_name=region)

cluster_info_list = client.list_clusters_v2(ClusterNameFilter=cluster_name)['ClusterInfoList']
cluster_info = [elem for elem in cluster_info_list if elem['ClusterName'] == cluster_name][0]

cluster_arn = cluster_info['ClusterArn']
current_version = cluster_info['CurrentVersion']

connectivity_info = {
  "VpcConnectivity": {
    "ClientAuthentication": {
      "Sasl": {
        "Scram": {
          "Enabled": False
        },
        "Iam": {
          "Enabled": True
        }
      }
    }
  }
}

response = client.update_connectivity(ClusterArn=cluster_arn,
                                      ConnectivityInfo=connectivity_info,
                                      CurrentVersion=current_version)

</pre>

Once MSK cluster **Security**, and **Network settings** has been successfully updated, you should see client information similar to the following example.

![msk-bootstrap-servers-info](assets/msk-bootstrap-servers-info.png)

#### (Step 3) Confirm that binary logging is enabled

<b><em>In order to set up the Aurora MySQL, you need to connect the Aurora MySQL cluster on either your local PC or a EC2 instance.</em></b>

1. (Optional) Create an EC2 Instance

   <pre>
    (.venv) $ cdk deploy TrxDataLakeBastionHost
   </pre>

2. Connect to the Aurora cluster writer node.
   <pre>
    $ sudo pip install ec2instanceconnectcli
    $ export BASTION_HOST_ID=$(aws cloudformation describe-stacks --stack-name <i>TrxDataLakeBastionHost</i> | jq -r '.Stacks[0].Outputs | .[] | select(.OutputKey | endswith("EC2InstanceId")) | .OutputValue')
    $ mssh --region "<i>your-region-name (e.g., us-east-1)</i>" ec2-user@${BASTION_HOST_ID}
    [ec2-user@ip-172-31-7-186 ~]$ mysql -h<i>db-cluster-name</i>.cluster-<i>xxxxxxxxxxxx</i>.<i>region-name</i>.rds.amazonaws.com -uadmin -p
    Enter password:
    Welcome to the MariaDB monitor.  Commands end with ; or \g.
    Your MySQL connection id is 20
    Server version: 8.0.23 Source distribution

    Copyright (c) 2000, 2018, Oracle, MariaDB Corporation Ab and others.

    Type 'help;' or '\h' for help. Type '\c' to clear the current input statement.

    MySQL [(none)]>
   </pre>

   > :information_source: `TrxDataLakeBastionHost` is a CDK Stack to create the bastion host.

   > :information_source: You can also connect to an EC2 instance using the EC2 Instance Connect CLI.
   For more information, see [Connect using the EC2 Instance Connect CLI](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-connect-methods.html#ec2-instance-connect-connecting-ec2-cli).
   For example,
       <pre>
       $ sudo pip install ec2instanceconnectcli
       $ mssh ec2-user@i-001234a4bf70dec41EXAMPLE # ec2-instance-id
       </pre>

3. At SQL prompt run the below command to confirm that binary logging is enabled:
   <pre>
    MySQL [(none)]> SHOW GLOBAL VARIABLES LIKE "log_bin";
    +---------------+-------+
    | Variable_name | Value |
    +---------------+-------+
    | log_bin       | ON    |
    +---------------+-------+
    1 row in set (0.00 sec)
   </pre>

4. Also run this to AWS DMS has bin log access that is required for replication
   <pre>
    MySQL [(none)]> CALL mysql.rds_set_configuration('binlog retention hours', 24);
    Query OK, 0 rows affected (0.01 sec)
   </pre>

#### (Step 4) Create a sample database and table

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
    MySQL [testdb]> SHOW tables;
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

    MySQL [testdb]> SHOW tables;
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

#### (Step 5) Set up Glue Streaming Job
1. Make sure **Apache Iceberg connector for AWS Glue** ready to use Apache Iceberg with AWS Glue jobs.
2. Create a S3 bucket for Apache Iceberg table
   <pre>
   (.venv) $ cdk deploy GlueStreamingCDCtoIcebergS3Path
   </pre>

3. Upload **AWS SDK for Java 2.x** jar file into S3
   <pre>
   (.venv) $ wget https://repo1.maven.org/maven2/software/amazon/awssdk/aws-sdk-java/2.17.224/aws-sdk-java-2.17.224.jar
   (.venv) $ aws s3 cp aws-sdk-java-2.17.224.jar s3://aws-glue-assets-123456789012-us-east-1/extra-jars/aws-sdk-java-2.17.224.jar
   </pre>
   A Glue Streaming Job might fail because of the following error:
   <pre>
   py4j.protocol.Py4JJavaError: An error occurred while calling o135.start.
   : java.lang.NoSuchMethodError: software.amazon.awssdk.utils.SystemSetting.getStringValueFromEnvironmentVariable(Ljava/lang/String;)Ljava/util/Optional
   </pre>
   We can work around the problem by starting the Glue Job with the additional parameters:
   <pre>
   --extra-jars <i>s3://path/to/aws-sdk-for-java-v2.jar</i>
   --user-jars-first true
   </pre>
   In order to do this, we might need to upload **AWS SDK for Java 2.x** jar file into S3.
4. Create Glue Streaming Job

   * (step 1) Select one of Glue Job Scripts and upload into S3
     <pre>
     (.venv) $ ls src/main/python/
      spark_sql_merge_into_iceberg.py
     (.venv) $ aws s3 mb <i>s3://aws-glue-assets-123456789012-us-east-1</i> --region <i>us-east-1</i>
     (.venv) $ aws s3 cp src/main/python/spark_sql_merge_into_iceberg.py <i>s3://aws-glue-assets-123456789012-us-east-1/scripts/</i>
     </pre>

   * (step 2) Provision the Glue Streaming Job

     <pre>
     (.venv) $ cdk deploy GlueMSKConnection \
                          GlueStreamingMSKtoIcebergJobRole \
                          GlueIcebergDatabase \
                          GrantLFPermissionsOnGlueJobRole \
                          GlueStreamingJobMSKtoIceberg
     </pre>
5. Make sure the glue job to access the Kinesis Data Streams table in the Glue Catalog database, otherwise grant the glue job to permissions

   Wec can get permissions by running the following command:
   <pre>
   (.venv) $ aws lakeformation list-permissions | jq -r '.PrincipalResourcePermissions[] | select(.Principal.DataLakePrincipalIdentifier | endswith(":role/GlueJobRole-MSK2Iceberg"))'
   </pre>
   If not found, we need manually to grant the glue job to required permissions by running the following command:
   <pre>
   (.venv) $ aws lakeformation grant-permissions \
               --principal DataLakePrincipalIdentifier=arn:aws:iam::<i>{account-id}</i>:role/<i>GlueJobRole-MSK2Iceberg</i> \
               --permissions SELECT DESCRIBE ALTER INSERT DELETE \
               --resource '{ "Table": {"DatabaseName": "<i>cdc_iceberg_demo_db</i>", "TableWildcard": {}} }'
   </pre>

#### Create a table with partitioned data in Amazon Athena

Go to [Athena](https://console.aws.amazon.com/athena/home) on the AWS Management console.<br/>
* (step 1) Create a database

   In order to create a new database called `cdc_iceberg_demo_db`, enter the following statement in the Athena query editor and click the **Run** button to execute the query.

   <pre>
   CREATE DATABASE IF NOT EXISTS cdc_iceberg_demo_db;
   </pre>

* (step 2) Create a table

   Copy the following query into the Athena query editor, replace the `xxxxxxx` in the last line under `LOCATION` with the string of your S3 bucket, and execute the query to create a new table.
   <pre>
   CREATE TABLE cdc_iceberg_demo_db.retail_trans_iceberg (
      trans_id bigint,
      customer_id string,
      event string,
      sku string,
      amount bigint,
      device string,
      trans_datetime timestamp
   )
   PARTITIONED BY (`event`)
   LOCATION 's3://glue-iceberg-demo-xxxxxxx/cdc_iceberg_demo_db/retail_trans_iceberg'
   TBLPROPERTIES (
      'table_type'='iceberg'
   );
   </pre>
   If the query is successful, a table named `retail_trans_iceberg` is created and displayed on the left panel under the **Tables** section.

   If you get an error, check if (a) you have updated the `LOCATION` to the correct S3 bucket name, (b) you have mydatabase selected under the Database dropdown, and (c) you have `AwsDataCatalog` selected as the **Data source**.

   :information_source: If you fail to create the table, give Athena users access permissions on `cdc_iceberg_demo_db` through [AWS Lake Formation](https://console.aws.amazon.com/lakeformation/home), or you can grant anyone using Athena to access `cdc_iceberg_demo_db` by running the following command:
   <pre>
   (.venv) $ aws lakeformation grant-permissions \
                 --principal DataLakePrincipalIdentifier=arn:aws:iam::<i>{account-id}</i>:user/<i>example-user-id</i> \
                 --permissions CREATE_TABLE DESCRIBE ALTER DROP \
                 --resource '{ "Database": { "Name": "<i>cdc_iceberg_demo_db</i>" } }'
   (.venv) $ aws lakeformation grant-permissions \
                 --principal DataLakePrincipalIdentifier=arn:aws:iam::<i>{account-id}</i>:user/<i>example-user-id</i> \
                 --permissions SELECT DESCRIBE ALTER INSERT DELETE DROP \
                 --resource '{ "Table": {"DatabaseName": "<i>cdc_iceberg_demo_db</i>", "TableWildcard": {}} }'
   </pre>

## Run MSK Connect

Create and run MSK Connect
   <pre>
   (.venv) $ cdk deploy KafkaConnectorStack
   </pre>


## Run Test

1. Run glue job to load data from Kinesis Data Streams into S3
   <pre>
   (.venv) $ aws glue start-job-run --job-name <i>cdc_based_upsert_to_iceberg_table</i>
   </pre>

2. Generate test data.
   <pre>
    $ export BASTION_HOST_ID=$(aws cloudformation describe-stacks --stack-name <i>AuroraMysqlBastionHost</i> | jq -r '.Stacks[0].Outputs | .[] | select(.OutputKey | endswith("EC2InstanceId")) | .OutputValue')
    $ mssh --region "<i>your-region-name (e.g., us-east-1)</i>" ec2-user@${BASTION_HOST_ID}
    [ec2-user@ip-172-31-7-186 ~]$ pip3 install -r utils/requirements-dev.txt
    [ec2-user@ip-172-31-7-186 ~]$ python3 utils/gen_fake_mysql_data.py \
                                    --database <i>your-database-name</i> \
                                    --table <i>your-table-name</i> \
                                    --user <i>user-name</i> \
                                    --password <i>password</i> \
                                    --host <i>db-cluster-name</i>.cluster-<i>xxxxxxxxxxxx</i>.<i>region-name</i>.rds.amazonaws.com \
                                    --max-count 10
   </pre>

   After filling data into the MySQL table, connect to the Aurora cluster writer node and run some DML(insert, update, delete) queries.

   For example, update some records.
   <pre>
    $ mysql -h<i>db-cluster-name</i>.cluster-<i>xxxxxxxxxxxx</i>.<i>region-name</i>.rds.amazonaws.com -uadmin -p
    Enter password:
    Welcome to the MariaDB monitor.  Commands end with ; or \g.
    Your MySQL connection id is 20
    Server version: 8.0.23 Source distribution

    Copyright (c) 2000, 2018, Oracle, MariaDB Corporation Ab and others.

    Type 'help;' or '\h' for help. Type '\c' to clear the current input statement.

    MySQL [(none)]> USE testdb;
    Database changed

    MySQL [testdb]> SELECT * FROM retail_trans LIMIT 10;
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

    MySQL [testdb]> UPDATE retail_trans SET amount = 3 WHERE trans_id=6;
    Query OK, 1 rows affected (0.00 sec)
    Rows matched: 1  Changed: 1  Warnings: 0

    MySQL [testdb]> UPDATE retail_trans SET amount = 39 WHERE trans_id=19;
    Query OK, 1 rows affected (0.00 sec)
    Rows matched: 1  Changed: 1  Warnings: 0

    MySQL [testdb]> UPDATE retail_trans SET amount = 60 WHERE trans_id=21;
    Query OK, 1 rows affected (0.00 sec)
    Rows matched: 1  Changed: 1  Warnings: 0

    MySQL [testdb]> UPDATE retail_trans SET amount = 4 WHERE trans_id=23;
    Query OK, 1 rows affected (0.00 sec)
    Rows matched: 1  Changed: 1  Warnings: 0

    MySQL [testdb]> UPDATE retail_trans SET amount = 42 WHERE trans_id=24;
    Query OK, 1 rows affected (0.00 sec)
    Rows matched: 1  Changed: 1  Warnings: 0
   </pre>

   Delete some records.
   <pre>
    MySQL [testdb]> DELETE FROM retail_trans WHERE trans_id=6;
    Query OK, 1 rows affected (0.00 sec)

    MySQL [testdb]> DELETE FROM retail_trans WHERE trans_id=33;
    Query OK, 1 rows affected (0.00 sec)

    MySQL [testdb]> DELETE FROM retail_trans WHERE trans_id=23;
    Query OK, 1 rows affected (0.00 sec)
   </pre>

   Insert some new records.
   <pre>
    MySQL [testdb]> INSERT INTO retail_trans (customer_id, event, sku, amount, device) VALUES
    -> ("818177069814", "like", "JS6166YPTE", 1, "mobile"),
    -> ("387378799012", "list", "AI6161BEFX", 1, "pc"),
    -> ("839828949919", "purchase", "AC2306JBRJ", 5, "tablet"),
    -> ("248083404876", "visit", "AS8552DVOO", 1, "pc"),
    -> ("731184658511", "like", "XZ9997LSJN", 1, "tablet");
    Query OK, 5 rows affected (0.00 sec)
    Records: 5  Duplicates: 0  Warnings: 0
   </pre>

3. Check streaming data in S3

   After `5~7` minutes, you can see that the streaming data have been delivered from **MSK** to **S3**.

   ![iceberg-table](./assets/cdc-iceberg-table.png)
   ![iceberg-table](./assets/cdc-iceberg-data-level-01.png)
   ![iceberg-table](./assets/cdc-iceberg-data-level-02.png)
   ![iceberg-table](./assets/cdc-iceberg-data-level-03.png)

4. Run test query using Amazon Athena

   Enter the following SQL statement and execute the query.
   <pre>
   SELECT COUNT(*)
   FROM cdc_iceberg_demo_db.retail_trans_iceberg;
   </pre>


## Clean Up

1. Stop the glue job by replacing the job name in below command.
   <pre>
   (.venv) $ JOB_RUN_IDS=$(aws glue get-job-runs \
               --job-name <i>cdc_based_upsert_to_iceberg_table</i> | jq -r '.JobRuns[] | select(.JobRunState=="RUNNING") | .Id' \
               | xargs)
   (.venv) $ aws glue batch-stop-job-run \
               --job-name <i>cdc_based_upsert_to_iceberg_table</i> \
               --job-run-ids $JOB_RUN_IDS
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

 * (1) [Transactional Data Lake using Apache Iceberg with AWS Glue Streaming and DMS](https://github.com/aws-samples/transactional-datalake-using-apache-iceberg-on-aws-glue)
   ![trsanactional-datalake-with-dms-glue-iceberg](https://raw.githubusercontent.com/aws-samples/transactional-datalake-using-apache-iceberg-on-aws-glue/main/transactional-datalake-arch.svg)
 * (2) [AWS Glue versions](https://docs.aws.amazon.com/glue/latest/dg/release-notes.html): The AWS Glue version determines the versions of Apache Spark and Python that AWS Glue supports.
 * (3) [Use the AWS Glue connector to read and write Apache Iceberg tables with ACID transactions and perform time travel \(2022-06-21\)](https://aws.amazon.com/ko/blogs/big-data/use-the-aws-glue-connector-to-read-and-write-apache-iceberg-tables-with-acid-transactions-and-perform-time-travel/)
 * (4) [AWS Glue Streaming Ingestion from Kafka to Apache Iceberg table in S3](https://github.com/aws-samples/aws-glue-streaming-ingestion-from-kafka-to-apache-iceberg)
 * (5) [Amazon Athena Using Iceberg tables](https://docs.aws.amazon.com/athena/latest/ug/querying-iceberg.html)
 * (6) [Implement a CDC-based UPSERT in a data lake using Apache Iceberg and AWS Glue (2022-06-15)](https://aws.amazon.com/ko/blogs/big-data/implement-a-cdc-based-upsert-in-a-data-lake-using-apache-iceberg-and-aws-glue/)
 * (7) [Apache Iceberg - Spark Writes with SQL (v0.14.0)](https://iceberg.apache.org/docs/0.14.0/spark-writes/)
 * (8) [Crafting serverless streaming ETL jobs with AWS Glue (2020-10-14)](https://aws.amazon.com/ko/blogs/big-data/crafting-serverless-streaming-etl-jobs-with-aws-glue/)
 * (9) [AWS Glue Notebook Samples](https://github.com/aws-samples/aws-glue-samples/tree/master/examples/notebooks) - sample iPython notebook files which show you how to use open data dake formats; Apache Hudi, Delta Lake, and Apache Iceberg on AWS Glue Interactive Sessions and AWS Glue Studio Notebook.
 * (10) [Choosing an open table format for your transactional data lake on AWS (2023-06-09)](https://aws.amazon.com/blogs/big-data/choosing-an-open-table-format-for-your-transactional-data-lake-on-aws/)
 * (11) [Debezium Connectors - MySQL Change event values](https://debezium.io/documentation/reference/stable/connectors/mysql.html#mysql-change-event-values)
 * (12) [Build a transactional data lake using Apache Iceberg, AWS Glue, and cross-account data shares using AWS Lake Formation and Amazon Athena (2023-04-24)](https://aws.amazon.com/blogs/big-data/build-a-transactional-data-lake-using-apache-iceberg-aws-glue-and-cross-account-data-shares-using-aws-lake-formation-and-amazon-athena/)


## Troubleshooting

 * Granting database or table permissions error using AWS CDK
   * Error message:
     <pre>
     AWS::LakeFormation::PrincipalPermissions | CfnPrincipalPermissions Resource handler returned message: "Resource does not exist or requester is not authorized to access requested permissions. (Service: LakeFormation, Status Code: 400, Request ID: f4d5e58b-29b6-4889-9666-7e38420c9035)" (RequestToken: 4a4bb1d6-b051-032f-dd12-5951d7b4d2a9, HandlerErrorCode: AccessDenied)
     </pre>
   * **Solution**:

     The role assumed by cdk is not a data lake administrator. (e.g., `cdk-hnb659fds-deploy-role-12345678912-us-east-1`) <br/>
     So, deploying PrincipalPermissions meets the error such as:

     `Resource does not exist or requester is not authorized to access requested permissions.`

     In order to solve the error, it is necessary to promote the cdk execution role to the data lake administrator.<br/>
     For example, https://github.com/aws-samples/data-lake-as-code/blob/mainline/lib/stacks/datalake-stack.ts#L68

   * Reference:

     [https://github.com/aws-samples/data-lake-as-code](https://github.com/aws-samples/data-lake-as-code) - Data Lake as Code

 * Amazon MSK Serverless does not allow `auto.create.topics.enable` to be set to `true`.

    ```
    $ aws kafka update-cluster-configuration --cluster-arn arn:aws:kafka:us-east-1:123456789012:cluster/msk/39bb8562-e1b9-42a5-ba82-703ac0dee7ea-s1 --configuration-info file://msk-cluster-config.json --current-version K2EUQ1WTGCTBG2

    An error occurred (BadRequestException) when calling the UpdateClusterConfiguration operation: This operation cannot be performed on serverless clusters.
    ```
   * **Solution**: To automatically create Kafka topics, use a Debezium configuration with `topic.creation.enable` set to `true`.

 * Debezium connector failure with the following error message:

    ```
    2023-11-02T06:21:09.000Z [Worker-03ae84b36842a92e0] java.lang.NoClassDefFoundError: com/google/common/base/Strings
    2023-11-02T06:21:09.000Z [Worker-03ae84b36842a92e0] at com.github.jcustenborder.kafka.connect.utils.config.ConfigKeyBuilder.build(ConfigKeyBuilder.java:61)
    2023-11-02T06:21:09.000Z [Worker-03ae84b36842a92e0] at com.github.jcustenborder.kafka.config.aws.SecretsManagerConfigProviderConfig.config(SecretsManagerConfigProviderConfig.java:75)
    2023-11-02T06:21:09.000Z [Worker-03ae84b36842a92e0] at com.github.jcustenborder.kafka.config.aws.SecretsManagerConfigProviderConfig.<init>(SecretsManagerConfigProviderConfig.java:53)
    2023-11-02T06:21:09.000Z [Worker-03ae84b36842a92e0] at com.github.jcustenborder.kafka.config.aws.SecretsManagerConfigProvider.configure(SecretsManagerConfigProvider.java:136)
    2023-11-02T06:21:09.000Z [Worker-03ae84b36842a92e0] at org.apache.kafka.common.config.AbstractConfig.instantiateConfigProviders(AbstractConfig.java:548)
    2023-11-02T06:21:09.000Z [Worker-03ae84b36842a92e0] at org.apache.kafka.common.config.AbstractConfig.resolveConfigVariables(AbstractConfig.java:491)
    2023-11-02T06:21:09.000Z [Worker-03ae84b36842a92e0] at org.apache.kafka.common.config.AbstractConfig.<init>(AbstractConfig.java:107)
    2023-11-02T06:21:09.000Z [Worker-03ae84b36842a92e0] at org.apache.kafka.common.config.AbstractConfig.<init>(AbstractConfig.java:129)
    2023-11-02T06:21:09.000Z [Worker-03ae84b36842a92e0] at org.apache.kafka.connect.runtime.WorkerConfig.<init>(WorkerConfig.java:452)
    2023-11-02T06:21:09.000Z [Worker-03ae84b36842a92e0] at org.apache.kafka.connect.runtime.distributed.DistributedConfig.<init>(DistributedConfig.java:405)
    2023-11-02T06:21:09.000Z [Worker-03ae84b36842a92e0] at org.apache.kafka.connect.cli.ConnectDistributed.startConnect(ConnectDistributed.java:95)
    2023-11-02T06:21:09.000Z [Worker-03ae84b36842a92e0] at org.apache.kafka.connect.cli.ConnectDistributed.main(ConnectDistributed.java:80)
    2023-11-02T06:21:09.000Z [Worker-03ae84b36842a92e0] Caused by: java.lang.ClassNotFoundException: com.google.common.base.Strings
    2023-11-02T06:21:09.000Z [Worker-03ae84b36842a92e0] at java.base/java.net.URLClassLoader.findClass(URLClassLoader.java:476)
    2023-11-02T06:21:09.000Z [Worker-03ae84b36842a92e0] at java.base/java.lang.ClassLoader.loadClass(ClassLoader.java:594)
    2023-11-02T06:21:09.000Z [Worker-03ae84b36842a92e0] at org.apache.kafka.connect.runtime.isolation.PluginClassLoader.loadClass(PluginClassLoader.java:104)
    2023-11-02T06:21:09.000Z [Worker-03ae84b36842a92e0] at java.base/java.lang.ClassLoader.loadClass(ClassLoader.java:527)
    2023-11-02T06:21:09.000Z [Worker-03ae84b36842a92e0] ... 12 more
    2023-11-02T06:21:09.000Z [Worker-03ae84b36842a92e0] MSK Connect encountered errors and failed.
    ```
    * **Solution**: [Confluent hub installation is missing guava #2](https://github.com/jcustenborder/kafka-config-provider-aws/issues/2)

      > To resolve the MSK Connect issue I downloaded the guava jar (guava-31.1-jre.jar) directly from [here](https://repo1.maven.org/maven2/com/google/guava/guava/31.1-jre/)
      >
      > When you create the custom plugin for MSK Connect, after extracting jcusten-border-kafka-config-provider-aws drop the guava jar in the lib folder, before creating the archive that you upload to S3.


## Kafka Commands CheatSheet

 * Set up `client.properties`

   <pre>
   $ cat client.properties
   security.protocol=SASL_SSL
   sasl.mechanism=AWS_MSK_IAM
   sasl.jaas.config=software.amazon.msk.auth.iam.IAMLoginModule required;
   sasl.client.callback.handler.class=software.amazon.msk.auth.iam.IAMClientCallbackHandler
   </pre>

    :information_source: `client.properties` is a property file containing configs to be passed to Admin Client. This is used only with `--bootstrap-server` option for describing and altering broker configs.<br/>
    For more information, see [Getting started using MSK Serverless clusters - Step 3: Create a client machine](https://docs.aws.amazon.com/msk/latest/developerguide/create-serverless-cluster-client.html)

 * Get Bootstrap server information
   <pre>
   $ aws kafka get-bootstrap-brokers --cluster-arn <i>msk_cluster_arn</i>
   $ export BS=<i>{BootstrapBrokerStringSaslIam}</i>
   </pre>

 * List Kafka toipics
   <pre>
   $ kafka-topics.sh --bootstrap-server $BS \
                     --command-config client.properties \
                     --list
   </pre>

 * Create a Kafka toipic
   <pre>
   $ kafka-topics.sh --bootstrap-server $BS \
                     --command-config client.properties \
                     --create \
                     --topic <i>topic_name</i> \
                     --partitions 3 \
                     --replication-factor 2
   </pre>

 * Consume records from a Kafka toipic
   <pre>
   $ kafka-console-consumer.sh --bootstrap-server $BS \
                               --consumer.config client.properties \
                               --topic <i>topic_name</i> \
                               --from-beginning
   </pre>

 * Produce records into a Kafka toipic
   <pre>
   $ kafka-console-producer.sh --bootstrap-server $BS \
                               --producer.config client.properties \
                               --topic <i>topic_name</i>
   </pre>


## Debezium MySQL Change Event Sample Data and Schema

 * Sample Data
   ```
   {
     "before": null,
     "after": {
       "trans_id": 28,
       "customer_id": "818177069814",
       "event": "like",
       "sku": "JS6166YPTE",
       "amount": 1,
       "device": "pc",
       "trans_datetime": 1699441714000
     },
     "source": {
       "version": "2.4.0.Final",
       "connector": "mysql",
       "name": "retail-server",
       "ts_ms": 1699441786000,
       "snapshot": "false",
       "db": "testdb",
       "sequence": null,
       "table": "retail_trans",
       "server_id": 1629810274,
       "gtid": null,
       "file": "mysql-bin-changelog.000003",
       "pos": 10867,
       "row": 0,
       "thread": 8948,
       "query": null
     },
     "op": "c",
     "ts_ms": 1699441786893,
     "transaction": null
   }
   ```

 * Spark DataFrame Schema
   ```
   root
    |-- after: struct (nullable = true)
    |    |-- amount: long (nullable = true)
    |    |-- customer_id: string (nullable = true)
    |    |-- device: string (nullable = true)
    |    |-- event: string (nullable = true)
    |    |-- sku: string (nullable = true)
    |    |-- trans_datetime: long (nullable = true)
    |    |-- trans_id: long (nullable = true)
    |-- before: string (nullable = true)
    |-- op: string (nullable = true)
    |-- source: struct (nullable = true)
    |    |-- connector: string (nullable = true)
    |    |-- db: string (nullable = true)
    |    |-- file: string (nullable = true)
    |    |-- gtid: string (nullable = true)
    |    |-- name: string (nullable = true)
    |    |-- pos: long (nullable = true)
    |    |-- query: string (nullable = true)
    |    |-- row: long (nullable = true)
    |    |-- sequence: string (nullable = true)
    |    |-- server_id: long (nullable = true)
    |    |-- snapshot: string (nullable = true)
    |    |-- table: string (nullable = true)
    |    |-- thread: long (nullable = true)
    |    |-- ts_ms: long (nullable = true)
    |    |-- version: string (nullable = true)
    |-- transaction: string (nullable = true)
    |-- ts_ms: long (nullable = true)
   ```

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.
