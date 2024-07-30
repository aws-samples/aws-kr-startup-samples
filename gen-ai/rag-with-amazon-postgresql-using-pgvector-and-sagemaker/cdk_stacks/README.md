
# RAG Application CDK Python project!

![rag_with_pgvector_arch](./rag_with_pgvector_arch.svg)

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
  "db_cluster_name": "<i>postgresql-cluster-name</i>",
  "jumpstart_model_info": {
    "model_id": "huggingface-text2text-flan-t5-xl",
    "version": "2.1.0"
  },
  "sagemaker_studio_domain_name": "<i>sagmake-studio-domain-name</i>"
}
</pre>

:information_source: The `model_id`, and `version` provided by SageMaker JumpStart can be found in [**SageMaker Built-in Algorithms with pre-trained Model Table**](https://sagemaker.readthedocs.io/en/stable/doc_utils/pretrainedmodels.html).

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
RAGVpcStack
RAGSageMakerStudioStack
RAGPgVectorStack
EmbeddingEndpointStack
LLMEndpointStack
```

#### Step 2: Create Aurora Postgresql cluster

```
(.venv) $ cdk deploy --require-approval never RAGVpcStack RAGPgVectorStack
```

#### Step 3: Create SageMaker Studio

```
(.venv) $ cdk deploy --require-approval never RAGSageMakerStudioStack
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

 * [Leverage pgvector and Amazon Aurora PostgreSQL for Natural Language Processing, Chatbots and Sentiment Analysis (2023-07-13)](https://aws.amazon.com/blogs/database/leverage-pgvector-and-amazon-aurora-postgresql-for-natural-language-processing-chatbots-and-sentiment-analysis/)
 * [Building AI-powered search in PostgreSQL using Amazon SageMaker and pgvector (2023-05-02)](https://aws.amazon.com/blogs/database/building-ai-powered-search-in-postgresql-using-amazon-sagemaker-and-pgvector/)
 * [Use proprietary foundation models from Amazon SageMaker JumpStart in Amazon SageMaker Studio (2023-06-27)](https://aws.amazon.com/blogs/machine-learning/use-proprietary-foundation-models-from-amazon-sagemaker-jumpstart-in-amazon-sagemaker-studio/)
 * [SageMaker Built-in Algorithms with pre-trained Model Table](https://sagemaker.readthedocs.io/en/stable/doc_utils/pretrainedmodels.html)
 * [AWS Deep Learning Containers Images](https://docs.aws.amazon.com/deep-learning-containers/latest/devguide/deep-learning-containers-images.html)
 * [Securing Amazon SageMaker Studio connectivity using a private VPC (2020-10-22)](https://aws.amazon.com/blogs/machine-learning/securing-amazon-sagemaker-studio-connectivity-using-a-private-vpc/)
 * [Connect SageMaker Studio Notebooks in a VPC to External Resources](https://docs.aws.amazon.com/sagemaker/latest/dg/studio-notebooks-and-internet-access.html)
 * [Give SageMaker Processing Jobs Access to Resources in Your Amazon VPC](https://docs.aws.amazon.com/sagemaker/latest/dg/process-vpc.html)
   * **Configure the VPC Security Group**
     * In distributed processing, you must allow communication between the different containers in the same processing job. To do that, configure a rule for your security group that allows inbound connections between members of the same security group.
 * [Using the Amazon SageMaker Studio Image Build CLI to build container images from your Studio notebooks (2020-09-14)](https://aws.amazon.com/blogs/machine-learning/using-the-amazon-sagemaker-studio-image-build-cli-to-build-container-images-from-your-studio-notebooks/)
 * [How can I troubleshoot the InternalServerError response on Amazon SageMaker? - AWS re:Post](https://repost.aws/knowledge-center/sagemaker-http-500-internal-server-error)
