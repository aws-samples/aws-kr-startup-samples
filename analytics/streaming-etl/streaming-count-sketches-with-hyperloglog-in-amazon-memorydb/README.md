# Streaming Count Sketches with HyperLogLog in Amazon MemoryDB for Redis

This repository provides you cdk scripts and sample code on how to count unique items (e.g., unique visitors) with hyperloglog in Amazon MemoryDB for Redis.

**HyperLogLog (HLL)** is a probabilistic data structure that estimates the cardinality of a set. As a probabilistic data structure, **HyperLogLog** trades perfect accuracy for efficient space utilization.

Counting unique items usually requires an amount of memory proportional to the number of items you want to count, because you need to remember the elements you have already seen in the past in order to avoid counting them multiple times. However, a set of algorithms exist that trade memory for precision: they return an estimated measure with a standard error, which, in the case of the Redis implementation for HyperLogLog, is less than 1%. The magic of this algorithm is that you no longer need to use an amount of memory proportional to the number of items counted, and instead can use a constant amount of memory.

In this project, we will count unique visitors with HyperLogLog in Amazon MemoryDB for Redis.

Below diagram shows what we are implementing.

![architecture](./streaming-count-sketches-arch.svg)

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

## Prerequisites

**Upload library packages for AWS Lambda Layer to S3**

AWS Lambda function uses `redis-py-cluster` Python package to access Amazon MemoryDB for Redis.<br/>
In this project, we will create AWs Lambda Layer with `redis-py-cluster` Python packages.<br/>
So, we need to upload library packes to S3 for AWS Lambda Layer.

You can create the python package by running the following comands:

<pre>
$ cat <&ltEOF > requirements.txt
> redis-py-cluster==2.1.3
> EOF
$ docker run -v "$PWD":/var/task "public.ecr.aws/sam/build-python3.11" /bin/sh -c "pip install -r requirements.txt -t python/lib/python3.11/site-packages/; exit"
$ zip -r redis-py-cluster-lib.zip python > /dev/null
$ aws s3 mb s3://<i>my-bucket-for-lambda-layer-packages</i>
$ aws s3 cp redis-py-cluster-lib.zip s3://<i>my-bucket-for-lambda-layer-packages</i>/var/
</pre>

:information_source: [How to create a Lambda layer using a simulated Lambda environment with Docker](https://aws.amazon.com/premiumsupport/knowledge-center/lambda-layer-simulated-docker/)

**Set up `cdk.context.json`**

Then, before deploying the CloudFormation, you should set approperly the cdk context configuration file, `cdk.context.json`.

For example,
<pre>
{
  "kinesis_stream_name": "<i>demo-kds</i>",
  "s3_bucket_lambda_layer_lib": "<i>lambda-layer-resources</i>",
  "memorydb_cluster_name": "<i>demo-memdb</i>",
}
</pre>

:warning: `s3_bucket_lambda_layer_lib` option should have the s3 bucket name that contains python packages to be registered to AWS Lambda Layer.

**Bootstrap AWS environment for AWS CDK app**

Also, before any AWS CDK app can be deployed, you have to bootstrap your AWS environment to create certain AWS resources that the AWS CDK CLI (Command Line Interface) uses to deploy your AWS CDK app.

Run the `cdk bootstrap` command to bootstrap the AWS environment.

```
(.venv) $ cdk bootstrap
```

## Deployment

At this point you can now synthesize the CloudFormation template for this code.

Let's check all CDK Stacks with `cdk list` command.

<pre>
(.venv) $ export CDK_DEFAULT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
(.venv) $ export CDK_DEFAULT_REGION=$(curl -s 169.254.169.254/latest/dynamic/instance-identity/document | jq -r .region)
(.venv) $ cdk list
MemoryDBVPCStack
MemoryDBAclStack
MemoryDBStack
KinesisDataStreamsStack
LambdaLayersStack
LambdaFunctionStack
BastionHostStack
</pre>

Then, synthesize the CloudFormation template for this code

```
(.venv) $ cdk synth --all
```

To add additional dependencies, for example other CDK libraries, just add
them to your `setup.py` file and rerun the `pip install -r requirements.txt`
command.

You are now ready to run the `cdk deploy` command to build the stack shown above.

```
(.venv) $ cdk deploy --all
```

## Run Test

1. Generate test data.
   <pre>
   $ BASTION_HOST_ID=$(aws cloudformation describe-stacks --stack-name <i>BastionHostStack</i> \
    | jq -r '.Stacks[0].Outputs | .[] | select(.OutputKey | endswith("EC2InstanceId")) |.OutputValue')

    $ aws ec2-instance-connect ssh --instance-id ${BASTION_HOST_ID} --os-user ec2-user

    [ec2-user@ip-172-31-7-186 ~]$ ls -1
    gen_fake_data.py
    redis-6.2.14
    redis-6.2.14.tar.gz

    [ec2-user@ip-172-31-7-186 ~]$ python3 gen_fake_data.py --service-name kinesis --stream-name <i>your-kinesis-data-stream-name</i> --max-count 100
   </pre>

2. Check Amazon MemoryDB for Redis `5~10` minutes later, and you will see data.<br/>
   > :information_source: You can find out Amazon MemoryDB for Redis endpoint by running the following command:
   <pre>
    aws cloudformation describe-stacks --stack-name <i>MemoryDBStack</i> \
    | jq -r '.Stacks[0].Outputs | .[] | select(.OutputKey | endswith("MemoryDBClusterEndpoint")) |.OutputValue'
   </pre>

   Let's check the items in Amazon MemoryDB for Redis.<br/>
   > :information_source: The user and password of Amazon MemoryDB are stored in the [AWS Secrets Manager](https://console.aws.amazon.com/secretsmanager/listsecrets) as a name such as `MemoryDBSecret-xxxxxxxxxxxx`.
   <pre>
    $ BASTION_HOST_ID=$(aws cloudformation describe-stacks --stack-name <i>BastionHostStack</i> \
    | jq -r '.Stacks[0].Outputs | .[] | select(.OutputKey | endswith("EC2InstanceId")) |.OutputValue')

    $ aws ec2-instance-connect ssh --instance-id ${BASTION_HOST_ID} --os-user ec2-user

    [ec2-user@ip-172-31-7-186 ~]$ ls -1
    gen_fake_data.py
    redis-6.2.14
    redis-6.2.14.tar.gz

    [ec2-user@ip-172-31-7-186 ~]$ redis-cli -c --tls -h <i>clustercfg.demo-memdb.81kuqj.memorydb.us-east-1.amazonaws.com</i> -p 6379 --user <i>user-name</i> -a <i>your-password</i>
   </pre>

    Run `pfcount`, `ttl` redis commands to find out unique vistors count.
    For example,
    ```
    Warning: Using a password with '-a' or '-u' option on the command line interface may not be safe.
    demo-memdb-0002-001.demo-memdb.81kuqj.memorydb.us-east-1.amazonaws.com:6379> keys *
     1) "uv:site_id=715:20240309"
     2) "uv:site_id=283:20240309"
    demo-memdb-0002-001.demo-memdb.81kuqj.memorydb.us-east-1.amazonaws.com:6379> pfcount uv:site_id=715:20240309
    (integer) 20
    demo-memdb-0002-001.demo-memdb.81kuqj.memorydb.us-east-1.amazonaws.com:6379> pfcount uv:site_id=283:20240309
    (integer) 23
    demo-memdb-0002-001.demo-memdb.81kuqj.memorydb.us-east-1.amazonaws.com:6379> ttl uv:site_id=283:20240309
    (integer) 82421
    ```

## Clean Up

Delete the CloudFormation stacks by running the below command.

```
(.venv) $ cdk destroy --all
```

## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

Enjoy!

## References

 * [Redis engine versions - Amazon MemoryDB for Redis](https://docs.aws.amazon.com/memorydb/latest/devguide/engine-versions.html)
 * [Connect to a MemoryDB cluster (Linux)](https://docs.aws.amazon.com/memorydb/latest/devguide/getting-startedclusters.connecttonode.html#getting-startedclusters.connecttonode.redis.linux)
   <pre>
   redis-cli -c -h <i>{Primary or Configuration Endpoint}</i> --tls -p 6379 --user <i>{user_name}</i> -a <i>{password}</i>
   </pre>
 * [How to create a Lambda layer using a simulated Lambda environment with Docker](https://aws.amazon.com/premiumsupport/knowledge-center/lambda-layer-simulated-docker/)
 * [Amazon MemoryDB for Redis Immersion Day](https://catalog.us-east-1.prod.workshops.aws/workshops/23394eff-66dd-421a-9513-efe12b9197d0/en-US)
 * [Amazon ElastiCache for Redis Immersion Day](https://catalog.us-east-1.prod.workshops.aws/workshops/17043d97-f284-49db-b2d5-528e80546899/en-US)
 * [Redis Commands](https://redis.io/commands/)
 * [HyperLogLog in Redis](https://redis.io/docs/data-types/probabilistic/hyperloglogs/)
 * [Probabilistic Data Structures in Redis](https://redis.com/blog/streaming-analytics-with-probabilistic-data-structures/)
   * Bloom filters, Cuckoo filters, Count-Min Sketch, Top-K, HyperLogLog
 * [Using HyperLogLog sketches in Amazon Redshift](https://docs.aws.amazon.com/redshift/latest/dg/hyperloglog-overview.html)

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.
