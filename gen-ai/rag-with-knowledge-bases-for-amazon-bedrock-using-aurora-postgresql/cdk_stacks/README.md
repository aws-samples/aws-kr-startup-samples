# QnA with RAG using Knowledge Bases for Amazon Bedrock CDK Python project!

![rag_with_kb_for_amazon_bedrock_using_aurora_postgresql_arch](./rag_with_kb_for_amazon_bedrock_using_aurora_postgresql_arch.svg)

This is a complete setup for automatic deployment of Knowledge Bases for Amazon Bedrock using Amazon Aurora Postgresql as a vector store.

Following resources will get created and deployed:

- AWS IAM role
- Amazon Aurora Postgresql
- Set up Data Source and Knowledge Base for Amazon Bedrock

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
$ git sparse-checkout set gen-ai/rag-with-knowledge-bases-for-amazon-bedrock-using-aurora-postgresql
$ cd gen-ai/rag-with-knowledge-bases-for-amazon-bedrock-using-aurora-postgresql/cdk_stacks

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

Before deployment, you need to make sure `docker daemon` is running.
Otherwise you will encounter the following errors:

```
ERROR: Cannot connect to the Docker daemon at unix://$HOME/.docker/run/docker.sock. Is the docker daemon running?
jsii.errors.JavaScriptError:
  Error: docker exited with status 1
```

### Set up `cdk.context.json`

Then, you should set approperly the cdk context configuration file, `cdk.context.json`.

For example,

<pre>
{
  "db_cluster_name": "rag-pgvector-demo",
  "aurora_vectorstore_database_name": "bedrock_vector_db",
  "knowledge_base_data_source_name": "kb-data-source",
  "sagemaker_studio_domain_name": "qa-with-rag-using-kb-aurora-pgvector"
}
</pre>

:information_source: `aurora_vectorstore_database_name` will be used in [**Step 4: Prepare Aurora PostgreSQL to be used as a Knowledge Base for Amazon Bedrock**](../data_ingestion_to_vectordb/setup_aurora_postgresql.ipynb).

## Deploy

At this point you can now synthesize the CloudFormation template for this code.

<pre>
(.venv) $ export CDK_DEFAULT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
(.venv) $ export CDK_DEFAULT_REGION=$(curl -s 169.254.169.254/latest/dynamic/instance-identity/document | jq -r .region)
(.venv) $ cdk synth --all
</pre>

Using `cdk deploy` command, we can provision each CDK stack one at a time like this:

#### Step 1: List all CDK Stacks

```
(.venv) $ cdk list
BedrockKBVpcStack
BedrockKBAuroraPgVectorStack
BedrockKBSageMakerStudioStack
BedrockKnowledgeBaseStack
```

#### Step 2: Create Amazon Aurora PostgreSQL cluster

```
(.venv) $ cdk deploy --require-approval never BedrockKBVpcStack BedrockKBAuroraPgVectorStack
```

> :information_source: Launching the Amazon Aurora PostgreSQL cluster stacks (i.e., **Step 2**) requires about `20~30` minutes.

#### Step 3: Create SageMaker Studio

```
(.venv) $ cdk deploy --require-approval never BedrockKBSageMakerStudioStack
```

#### Step 4: Prepare Aurora PostgreSQL to be used as a Knowledge Base for Amazon Bedrock

1. Open SageMaker Studio and then open a new terminal.
2. Run the following commands on the terminal to clone the code repository for this project:
   ```
   git clone --depth=1 https://github.com/aws-samples/aws-kr-startup-samples.git
   cd aws-kr-startup-samples/gen-ai/rag-with-knowledge-bases-for-amazon-bedrock-using-aurora-postgresql/data_ingestion_to_vectordb
   ```
3. Open `setup_aurora_postgresql.ipynb` notebook and Run it. (For more information, see [here](../data_ingestion_to_vectordb/setup_aurora_postgresql.ipynb))
4. Return to the terminal and deploy the remaining stacks.

#### Step 5: Create Knowledge Bases for Amazon Bedrock

```
(.venv) $ cdk deploy --require-approval never BedrockKnowledgeBaseStack
```

## Clean Up

Delete the CloudFormation stack by running the below command.

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

 * [AWS Generative AI CDK Constructs](https://awslabs.github.io/generative-ai-cdk-constructs/)
 * [Announcing Generative AI CDK Constructs (2024-01-31)](https://aws.amazon.com/blogs/devops/announcing-generative-ai-cdk-constructs/)
 * [(Video) AWS re:Invent 2023 - Use RAG to improve responses in generative AI applications (AIM336)](https://youtu.be/N0tlOXZwrSs?t=1659)
 * [Knowledge Bases now delivers fully managed RAG experience in Amazon Bedrock (2023-11-28)](https://aws.amazon.com/blogs/aws/knowledge-bases-now-delivers-fully-managed-rag-experience-in-amazon-bedrock/)
 * [Knowledge base for Amazon Bedrock Developer Guide](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base.html)
   * [Using Aurora PostgreSQL as a Knowledge Base for Amazon Bedrock](https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/AuroraPostgreSQL.VectorDB.html)
 * [LangChain - AmazonKnowledgeBasesRetriever](https://python.langchain.com/docs/integrations/retrievers/bedrock)
 * [Building with Amazon Bedrock and LangChain](https://catalog.workshops.aws/building-with-amazon-bedrock/en-US) - Hands-on labs using [LangChain](https://github.com/langchain-ai/langchain) to build generative AI prototypes with Amazon Bedrock.
 * [Amazon Bedrock Workshop](https://catalog.us-east-1.prod.workshops.aws/workshops/a4bdb007-5600-4368-81c5-ff5b4154f518/en-US) - Hands-on labs using Amazon Bedrock APIs, SDKs, and open-source software, such as LangChain and FAISS, to implement the most common Generative AI usage patterns (e.g., summarizing text, answering questions, building chatbots, creating images, and generating code).

