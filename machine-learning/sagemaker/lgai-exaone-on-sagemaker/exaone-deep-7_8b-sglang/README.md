
# Hosting LG AI EXAONE-Deep models on Amazon SageMaker Real-time Inference Endpoint using SGLang

This is a CDK Python project to host LG AI [EXAONE Deep 7.8B](https://huggingface.co/LGAI-EXAONE/EXAONE-Deep-7.8B) on Amazon SageMaker Real-time Inference Endpoint.

[EXAONE Deep](https://huggingface.co/LGAI-EXAONE), which exhibits superior capabilities in various reasoning tasks including math and coding benchmarks, ranging from 2.4B to 32B parameters developed and released by LG AI Research.

Evaluation results show that 1) [EXAONE Deep 2.4B](https://huggingface.co/LGAI-EXAONE/EXAONE-Deep-2.4B) outperforms other models of comparable size, 2) [EXAONE Deep 7.8B](https://huggingface.co/LGAI-EXAONE/EXAONE-Deep-7.8B) outperforms not only open-weight models of comparable scale but also a proprietary reasoning model OpenAI o1-mini, and 3) [EXAONE Deep 32B](https://huggingface.co/LGAI-EXAONE/EXAONE-Deep-32B) demonstrates competitive performance against leading open-weight models.

> For more details, please refer to the [documentation](https://arxiv.org/abs/2503.12524), [blog](https://www.lgresearch.ai/news/view?seq=543) and [GitHub](https://github.com/LG-AI-EXAONE/EXAONE-Deep).

Note that SageMaker provides [pre-built SageMaker AI Docker images](https://docs.aws.amazon.com/sagemaker/latest/dg/pre-built-containers-frameworks-deep-learning.html) that can help you quickly start with the model inference on SageMaker. It also allows you to [bring your own Docker container](https://docs.aws.amazon.com/sagemaker/latest/dg/adapt-inference-container.html) and use it inside SageMaker AI for training and inference. To be compatible with SageMaker AI, your container must have the following characteristics:

- Your container must have a web server listening on port `8080`.
- Your container must accept POST requests to the `/invocations` and `/ping` real-time endpoints.

In this example, we'll demonstrate how to adapt the [SGLang](https://github.com/sgl-project/sglang) framework to run on SageMaker AI endpoints. SGLang is a serving framework for large language models that provides state-of-the-art performance, including a fast backend runtime for efficient serving with RadixAttention, extensive model support, and an active open-source community. For more information refer to [https://docs.sglang.ai/index.html](https://docs.sglang.ai/index.html) and [https://github.com/sgl-project/sglang](https://github.com/sgl-project/sglang).

By using SGLang and building a custom Docker container, you can run advanced AI models like the [EXAONE Deep 7.8B](https://huggingface.co/LGAI-EXAONE/EXAONE-Deep-7.8B) on a SageMaker AI endpoint.

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
$ git sparse-checkout set machine-learning/sagemaker/lgai-exaone-on-sagemaker/exaone-deep-7_8b-sglang
$ cd machine-learning/sagemaker/lgai-exaone-on-sagemaker/exaone-deep-7_8b-sglang

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

To host the model on Amazon SageMaker with a BYOC(Bring Your Own Container) for SGLang, we need to store the model artifacts in S3 and build the custom container to register the ECR repository.

1. Install required packages
   ```
   (.venv) $ pip install -U huggingface-hub==0.23.5
   ```

2. Save model artifacts

   The following instructions work well on either `Ubuntu` or `SageMaker Studio`.

   (1) Create a directory for model artifacts.
   ```
   (.venv) mkdir -p model
   ```

   (2) Run the following python code to download the model artifacts from Hugging Face model hub.
   ```python
   from huggingface_hub import snapshot_download
   from pathlib import Path

   model_dir = Path('model')
   model_dir.mkdir(exist_ok=True)

   model_id = "LGAI-EXAONE/EXAONE-Deep-7.8B"
   snapshot_download(model_id, local_dir=model_dir)
   ```

   (3) Upload model artifacts into `s3`
   <pre>
   (.venv) export MODEL_URI="s3://{<i>bucket_name</i>}/{<i>key_prefix</i>}/"
   (.venv) aws s3 cp model/ ${MODEL_URI} --recursive
   </pre>

   :warning: Replace `bucket_name` and `key_prefix` with yours.

   :information_source: This CDK project uses [`cdklabs.generative-ai-cdk-constructs`](https://awslabs.github.io/generative-ai-cdk-constructs/) to deploy SageMaker Endpoints. `cdklabs.generative-ai-cdk-constructs` library assumes the model artifact (`model.tar.gz`) is stored in a bucket on S3 with the word "`sagemaker`" or "`SageMaker`". Therefore, `bucket_name` must include the word "`sagemaker`" or "`SageMaker`". (e.g., `sagemaker-us-east-1-123456789012`, `SageMaker-us-east-1-123456789012`).

3. Set up `cdk.context.json`

   Then, we should set approperly the cdk context configuration file, `cdk.context.json`.

   For example,
   <pre>
   {
     "base_docker_image": {
       "name": "lmsysorg/sglang",
       "tag": "v0.4.4.post1-cu125"
     },
     "ecr": {
       "repository_name": "sglang-sagemaker",
       "tag": "latest"
     },
     "model_id": "LGAI-EXAONE/EXAONE-Deep-7.8B",
     "model_data_source": {
       "s3_bucket_name": "<i>{bucket_name}</i>",
       "s3_object_key_name": "<i>{key_prefix}</i>/"
     },
     "sagemaker_endpoint_settings": {
       "environment": {
         "TENSOR_PARALLEL_DEGREE": "1"
       },
       "min_capacity": 1,
       "max_capacity": 2
     },
     "sagemaker_instance_type": "ml.g5.2xlarge"
   }
   </pre>

4. (Optional) Bootstrap AWS environment for AWS CDK app

   Also, before any AWS CDK app can be deployed, you have to bootstrap your AWS environment to create certain AWS resources that the AWS CDK CLI (Command Line Interface) uses to deploy your AWS CDK app.

   Run the cdk bootstrap command to bootstrap the AWS environment.

   ```
   (.venv) $ cdk bootstrap
   ```

## Deploy

At this point you can now synthesize the CloudFormation template for this code.

```
(.venv) $ export CDK_DEFAULT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
(.venv) $ export CDK_DEFAULT_REGION=$(aws configure get region)
(.venv) $ cdk synth --all
```

Use `cdk deploy` command to create the stack shown above.

```
(.venv) $ cdk deploy --require-approval never --all
```
> :warning: **Important**: Make sure you need to make sure `docker daemon` is running.<br/>
> Otherwise you will encounter the following errors:

  ```
  ERROR: Cannot connect to the Docker daemon at unix://$HOME/.docker/run/docker.sock. Is the docker daemon running?
  jsii.errors.JavaScriptError:
    Error: docker exited with status 1
  ```

We can list all the CDK stacks by using the `cdk list` command prior to deployment.

```
(.venv) $ cdk list
```

## Clean Up

Delete the CloudFormation stack by running the below command.

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

## (Optional) Deploy the model using SageMaker Python SDK

Following [deploy_exaone_deep_7_8b_sglang.ipynb](src/notebook/deploy_exaone_deep_7_8b_sglang.ipynb) on the SageMaker Studio, we can deploy the model to Amazon SageMaker.

## Example

Following [exaone_deep_7_8b_sglang_realtime_endpoint.ipynb](src/notebook/exaone_deep_7_8b_sglang_realtime_endpoint.ipynb) on the SageMaker Studio, we can invoke the model with sample data.

## References

 * [LG AI EXAONE](https://huggingface.co/LGAI-EXAONE): The family of Large Language Models (LLMs) and Large Multimodal Models (LMMs) developed by LG AI Research.
   * [LG AI EXAONE Deep 7.8B](https://huggingface.co/LGAI-EXAONE/EXAONE-Deep-7.8B)
   * [(GitHub) LG-AI-EXAONE/EXAONE-Deep](https://github.com/LG-AI-EXAONE/EXAONE-Deep)
 * [AWS Generative AI CDK Constructs](https://awslabs.github.io/generative-ai-cdk-constructs/)
 * [(AWS Blog) Announcing Generative AI CDK Constructs (2024-01-31)](https://aws.amazon.com/blogs/devops/announcing-generative-ai-cdk-constructs/)
 * [Available AWS Deep Learning Containers (DLC) images](https://github.com/aws/deep-learning-containers/blob/master/available_images.md)
 * [SGLang](https://github.com/sgl-project/sglang) - A fast serving framework for large language models and vision language models.
   * [SGLang Backend Tutorial](https://docs.sglang.ai/index.html)
   * [Docker Hub Link for SGLang](https://hub.docker.com/r/lmsysorg/sglang/) - Docker images for https://github.com/sgl-project/sglang
