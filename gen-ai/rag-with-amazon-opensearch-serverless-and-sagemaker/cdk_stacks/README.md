
# RAG Application CDK Python project!

![rag_with_opensearch_serverless_arch](./rag_with_opensearch_serverless_arch.svg)

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
$ git sparse-checkout set gen-ai/rag-with-amazon-opensearch-serverless-and-sagemaker
$ cd gen-ai/rag-with-amazon-opensearch-serverless-and-sagemaker/cdk_stacks

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
  "user_name": "<i>AWS_IAM_User_Name</i>",
  "collection_name": "<i>llm-rag-vectordb</i>",
  "jumpstart_model_info": {
    "model_id": "meta-textgeneration-llama-2-7b-f",
    "version": "2.0.1"
  }
}
</pre>

> :information_source: `AWS_IAM_User_Name` should have privileges to sign in and have permissions to to use Amazon OpenSearch Serverless resources.

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
(.venv) $ export CDK_DEFAULT_REGION=$(aws configure get region)
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
RAGVpcStack
RAGSageMakerStudioStack
RAGOpenSearchServerlessStack
EmbeddingEndpointStack
LLMEndpointStack
```

#### Step 2: Create SageMaker Studio

```
(.venv) $ cdk deploy --require-approval never RAGVpcStack RAGSageMakerStudioStack
```

#### Step 3: Create OpenSearch Serverless collection

```
(.venv) $ cdk deploy --require-approval never RAGOpenSearchServerlessStack
```

#### Step 4: Deploy LLM Embedding Endpoint

```
(.venv) $ cdk deploy --require-approval never EmbeddingEndpointStack
```

#### Step 5: Deploy Text Generation LLM Endpoint

```
(.venv) $ cdk deploy --require-approval never LLMEndpointStack
```

**Once all CDK stacks have been successfully created, proceed with the remaining steps of the [overall workflow](../README.md#overall-workflow).**


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

 * [Data access control for Amazon OpenSearch Serverless](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/serverless-data-access.html)
 * [Identity and Access Management for Amazon OpenSearch Serverless](https://docs.aws.amazon.com/opensearch-service/latest/developerguide/security-iam-serverless.html)
 * [Build a powerful question answering bot with Amazon SageMaker, Amazon OpenSearch Service, Streamlit, and LangChain (2023-05-25)](https://aws.amazon.com/blogs/machine-learning/build-a-powerful-question-answering-bot-with-amazon-sagemaker-amazon-opensearch-service-streamlit-and-langchain/)
 * [Use proprietary foundation models from Amazon SageMaker JumpStart in Amazon SageMaker Studio (2023-06-27)](https://aws.amazon.com/blogs/machine-learning/use-proprietary-foundation-models-from-amazon-sagemaker-jumpstart-in-amazon-sagemaker-studio/)
 * [SageMaker Built-in Algorithms with pre-trained Model Table](https://sagemaker.readthedocs.io/en/stable/doc_utils/pretrainedmodels.html)
 * [AWS Deep Learning Containers Images](https://docs.aws.amazon.com/deep-learning-containers/latest/devguide/deep-learning-containers-images.html)
 * [OpenSearch Popular APIs](https://opensearch.org/docs/latest/opensearch/popular-api/)
 * [Using the Amazon SageMaker Studio Image Build CLI to build container images from your Studio notebooks (2020-09-14)](https://aws.amazon.com/blogs/machine-learning/using-the-amazon-sagemaker-studio-image-build-cli-to-build-container-images-from-your-studio-notebooks/)
