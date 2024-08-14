
# RAG Application CDK Python project!

![rag_with_memorydb_and_sagemaker_arch](./rag_with_memorydb_and_sagemaker_arch.svg)

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
$ git sparse-checkout set gen-ai/rag-with-amazon-memorydb-and-sagemaker
$ cd gen-ai/rag-with-amazon-memorydb-and-sagemaker/cdk_stacks

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
  "memorydb_user_name": "<i>memdb-admin</i>",
  "memorydb_cluster_name": "<i>vectordb</i>",
  "sagemaker_studio_domain_name": "<i>llm-app-rag-memorydb</i>",
  "jumpstart_model_info": {
    "model_id": "meta-textgeneration-llama-3-8b-instruct",
    "version": "2.0.2"
  }
}
</pre>

> :information_source: The `model_id`, and `version` provided by SageMaker JumpStart can be found in [**SageMaker Built-in Algorithms with pre-trained Model Table**](https://sagemaker.readthedocs.io/en/stable/doc_utils/pretrainedmodels.html).

> :warning: **Important**: Make sure you need to make sure `docker daemon` is running.<br/>
> Otherwise you will encounter the following errors:

  ```
  ERROR: Cannot connect to the Docker daemon at unix://$HOME/.docker/run/docker.sock. Is the docker daemon running?
  jsii.errors.JavaScriptError:
    Error: docker exited with status 1
  ```

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
RAGMemoryDBVPCStack
RAGMemoryDBAclStack
RAGMemoryDBStack
RAGSageMakerStudioInVPCStack
RAGMemoryDBLLMEndpointStack
```

#### Step 1: Create Amazon MemoryDB for Vector Search

```
(.venv) $ cdk deploy --require-approval never \
                     RAGMemoryDBVPCStack \
                     RAGMemoryDBAclStack \
                     RAGMemoryDBStack
```

#### Step 2: Create SageMaker Studio

```
(.venv) $ cdk deploy --require-approval never RAGSageMakerStudioInVPCStack
```

#### Step 3: Deploy Text Generation LLM Endpoint

```
(.venv) $ cdk deploy --require-approval never RAGMemoryDBLLMEndpointStack
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

 * [Amazon MemoryDB for Redis Samples](https://github.com/aws-samples/amazon-memorydb-for-redis-samples)
 * [Vector search - Amazon MemoryDB for Redis](https://docs.aws.amazon.com/memorydb/latest/devguide/vector-search.html)
 * [Amazon MemoryDB for Redis engine versions](https://docs.aws.amazon.com/memorydb/latest/devguide/engine-versions.html)
 * [Amazon MemoryDB for Redis - Authenticating users with Access Control Lists (ACLs)](https://docs.aws.amazon.com/memorydb/latest/devguide/clusters.acls.html)
 * [Vector search - Amazon MemoryDB for Redis](https://docs.aws.amazon.com/memorydb/latest/devguide/vector-search.html)
 * [AWS Inferentia and AWS Trainium deliver lowest cost to deploy Llama 3 models in Amazon SageMaker JumpStart (2024-05-02)](https://aws.amazon.com/blogs/machine-learning/aws-inferentia-and-aws-trainium-deliver-lowest-cost-to-deploy-llama-3-models-in-amazon-sagemaker-jumpstart/)
