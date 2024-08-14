
# RAG Application CDK Python project!

![rag_with_bedrock_docdb_arch](./rag_with_bedrock_docdb_arch.svg)

This is an QA application with LLMs and RAG project for CDK development with Python.

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
$ git sparse-checkout set gen-ai/rag-with-amazon-bedrock-and-documentdb
$ cd gen-ai/rag-with-amazon-bedrock-and-documentdb/cdk_stacks

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

Before synthesizing the CloudFormation, you should set approperly the cdk context configuration file, `cdk.context.json`.

For example:

<pre>
{
  "docdb_cluster_name": "<i>vectordb</i>",
  "sagemaker_studio_domain_name": "<i>llm-app-rag-docdb</i>"
}
</pre>

Now this point you can now synthesize the CloudFormation template for this code.

```
(.venv) $ export CDK_DEFAULT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
(.venv) $ export CDK_DEFAULT_REGION=us-east-1 # your-aws-account-region
(.venv) $ cdk synth --all
```

Now we will be able to deploy all the CDK stacks at once like this:

```
(.venv) $ cdk deploy --require-approval never --all
```

Or, we can provision each CDK stack one at a time like this:

#### Step 1: List all CDK Stacks

```
(.venv) $ cdk list
RAGDocDBVPCStack
RAGDocDBStack
RAGSageMakerStudioInVPCStack
```

#### Step 1: Create Amazon MemoryDB for Vector Search

```
(.venv) $ cdk deploy --require-approval never \
                     RAGDocDBVPCStack \
                     RAGDocDBStack
```

#### Step 2: Create SageMaker Studio

```
(.venv) $ cdk deploy --require-approval never RAGSageMakerStudioInVPCStack
```

**Once all CDK stacks have been successfully created, proceed with the remaining steps of the [overall workflow](../README.md#overall-workflow).**


## Clean Up

Delete the CloudFormation stacks by running the below command.

```
(.venv) $ cdk destroy --force --all
```

## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

Enjoy!

## References

 * [Vector search for Amazon DocumentDB (with MongoDB compatibility)](https://docs.aws.amazon.com/documentdb/latest/developerguide/vector-search.html)
   * [github.com/aws-samples/amazon-documentdb-samples](https://github.com/aws-samples/amazon-documentdb-samples/)
 * [Vector search for Amazon DocumentDB (with MongoDB compatibility) is now generally available (2023-11-29)](https://aws.amazon.com/blogs/aws/vector-search-for-amazon-documentdb-with-mongodb-compatibility-is-now-generally-available/)
