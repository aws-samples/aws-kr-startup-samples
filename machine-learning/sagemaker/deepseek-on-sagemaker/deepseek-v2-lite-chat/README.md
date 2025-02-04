# Hosting DeepSeek V2 Lite Chat model on Amazon SageMaker Real-time Inference Endpoint using SageMaker DJL Serving DLC

This is a CDK Python project to host the [DeepSeek: A Strong, Economical, and Efficient Mixture-of-Experts Language Model](https://www.deepseek.com/)
on Amazon SageMaker Real-time Inference Endpoint.

[DeepSeek V2 Lite Chat](https://huggingface.co/deepseek-ai/DeepSeek-V2-Lite-Chat) is a strong Mixture-of-Experts (MoE)
language model characterized by economical training and efficient inference.
> Please see [here](#how-to-deploy-deepseek-v3-model-on-sagemaker-endpoint-using-this-cdk-python-project) for information on deploying the [DeepSeek V3](https://huggingface.co/deepseek-ai/DeepSeek-V3) model.

SagemMaker Real-time inference is ideal for inference workloads where you have real-time, interactive, low latency requirements.
You can deploy your model to SageMaker hosting services and get an endpoint that can be used for inference.
These endpoints are fully managed and support autoscaling.

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
$ git sparse-checkout set machine-learning/sagemaker/deepseek-on-sagemaker/deepseek-v2-lite-chat
$ cd machine-learning/sagemaker/deepseek-on-sagemaker/deepseek-v2-lite-chat

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

In order to host the model on Amazon SageMaker, the first step is to save the model artifacts.
These artifacts refer to the essential components of a machine learning model needed for various applications,
including deployment and retraining.
They can include model parameters, configuration files, pre-processing components,
as well as metadata, such as version details, authorship, and any notes related to its performance.

1. Save model artifacts

   The following instructions work well on either `Ubuntu` or `SageMaker Studio`.

   (1) Create a directory for model artifacts.
   ```
   (.venv) mkdir -p model
   ```

   (2) Create `model.tar.gz` with model artifacts including your custom [inference scripts](./src/python/code/).
   ```
   (.venv) cp -rp src/python/code/* model/
   (.venv) tar --exclude=".ipynb_checkpoints" -czf model.tar.gz model/
   (.venv) tar -tvf model.tar.gz
    drwxr-xr-x  0 wheel staff       0 Jan 12 18:29 model/
    -rw-r--r--  0 wheel staff     168 Jan 12 12:02 model/serving.properties
    -rw-r--r--  0 wheel staff    4046 Jan 12 12:01 model/model.py
   ```

   :information_source: For more information about the directory structure of `model.tar.gz`, see [**Model Directory Structure for Deploying Pre-trained PyTorch Models**](https://sagemaker.readthedocs.io/en/stable/frameworks/pytorch/using_pytorch.html#model-directory-structure)

   (3) Upload `model.tar.gz` file into `s3`
   <pre>
   (.venv) export MODEL_URI="s3://{<i>bucket_name</i>}/{<i>key_prefix</i>}/model.tar.gz"
   (.venv) aws s3 cp model.tar.gz ${MODEL_URI}
   </pre>

   :warning: Replace `bucket_name` and `key_prefix` with yours.

   :information_source: This CDK project uses [`cdklabs.generative-ai-cdk-constructs`](https://awslabs.github.io/generative-ai-cdk-constructs/) to deploy SageMaker Endpoints. `cdklabs.generative-ai-cdk-constructs` library assumes the model artifact (`model.tar.gz`) is stored in a bucket on S3 with the word "`sagemaker`" or "`SageMaker`". Therefore, `bucket_name` must include the word "`sagemakr`" or "`SageMaker`". (e.g., `sagemaker-us-east-1-123456789012`, `SageMaker-us-east-1-123456789012`).

2. Set up `cdk.context.json`

   Then, you should set approperly the cdk context configuration file, `cdk.context.json`.

   For example,
   <pre>
   {
     "model_id": "deepseek-ai/DeepSeek-V2-Lite-Chat",
     "model_data_source": {
       "s3_bucket_name": "<i>sagemaker-us-east-1-123456789012</i>",
       "s3_object_key_name": "<i>deepseek-v2-lite-chat/model.tar.gz</i>"
     },
     "sagemaker_endpoint_settings": {
       "min_capacity": 1,
       "max_capacity": 4
     },
     "sagemaker_instance_type": "ml.g5.12xlarge"
   }
   </pre>
   :information_source: This CDK project uses [`cdklabs.generative-ai-cdk-constructs`](https://awslabs.github.io/generative-ai-cdk-constructs/) to deploy SageMaker Endpoints. `cdklabs.generative-ai-cdk-constructs` library assumes the model artifact (`model.tar.gz`) is stored in a bucket on S3 with the word "`sagemaker`" or "`SageMaker`". Therefore, `s3_bucket_name` must include the word "`sagemakr`" or "`SageMaker`". (e.g., `sagemaker-us-east-1-123456789012`, `SageMaker-us-east-1-123456789012`).

3. (Optional) Bootstrap AWS environment for AWS CDK app

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

Following [deploy_deepseek_v2_lite_chat_on_sagemaker_endpoint.ipynb](src/notebook/deploy_deepseek_v2_lite_chat_on_sagemaker_endpoint.ipynb) on the SageMaker Studio, we can deploy the model to Amazon SageMaker.

## Example

Following [deepseek_v2_lite_chat_realtime_endpoint.ipynb](src/notebook/deepseek_v2_lite_chat_realtime_endpoint.ipynb) on the SageMaker Studio, we can invoke the model with sample data.

## How to Deploy DeepSeek V3 Model on SageMaker Endpoint Using This CDK Python Project

To deploy the DeepSeek V3 model using this example, please follow these instructions:

1. When creating **model.tar.gz**, configure the `option.model_id=deepseek-ai/DeepSeek-V3` in the **serving.properties** file as shown below:
    <pre>
    engine=Python
    option.model_id=<i>deepseek-ai/DeepSeek-V3</i>
    option.rolling_batch=vllm
    option.max_model_len=8192
    option.tensor_parallel_size=1
    trust_remote_code=True
    </pre>
2. Configure the DeepSeek V3 settings in **cdk.context.json** by specifying the `model_id` and `sagemaker_instance_type` as follows:
   <pre>
   {
     "model_id": "deepseek-ai/DeepSeek-V3",
     "model_data_source": {
       "s3_bucket_name": "<i>sagemaker-us-east-1-123456789012</i>",
       "s3_object_key_name": "<i>deepseek-v3/model.tar.gz</i>"
     },
     "sagemaker_endpoint_settings": {
       "min_capacity": 1,
       "max_capacity": 4
     },
     "sagemaker_instance_type": "<i>ml.p5e.48xlarge</i>"
   }
   </pre>

Once you've completed these configuration steps, proceed with the deployment process according to the main project instructions.

## References

 * [DeepSeek: A Strong, Economical, and Efficient Mixture-of-Experts Language Model](https://www.deepseek.com/)
   * [DeepSeek in HuggingFace](https://huggingface.co/deepseek-ai)
   * [deepseek-ai/DeepSeek-V2-Lite-Chat](https://huggingface.co/deepseek-ai/DeepSeek-V2-Lite-Chat)
 * [deepseek-ai/deepseek-coder-6.7b-instruct SageMaker LMI deployment guide](https://github.com/aws-samples/llm_deploy_gcr/blob/main/sagemaker/deepseek_coder_6.7_instruct.ipynb)
 * [AWS Generative AI CDK Constructs](https://awslabs.github.io/generative-ai-cdk-constructs/)
 * [(AWS Blog) Announcing Generative AI CDK Constructs (2024-01-31)](https://aws.amazon.com/blogs/devops/announcing-generative-ai-cdk-constructs/)
 * [Available AWS Deep Learning Containers (DLC) images](https://github.com/aws/deep-learning-containers/blob/master/available_images.md)
 * [SageMaker Python SDK - Hugging Face](https://sagemaker.readthedocs.io/en/stable/frameworks/huggingface/index.html)
 * [Docker Registry Paths and Example Code for Pre-built SageMaker Docker images](https://docs.aws.amazon.com/sagemaker/latest/dg-ecr-paths/sagemaker-algo-docker-registry-paths.html)
 * [Model Directory Structure for Deploying Pre-trained PyTorch Models](https://sagemaker.readthedocs.io/en/stable/frameworks/pytorch/using_pytorch.html#model-directory-structure)
 * [Amazon EC2 Instance types](https://aws.amazon.com/ec2/instance-types/)
 * 🛠️ [sagemaker-huggingface-inference-toolkit](https://github.com/aws/sagemaker-huggingface-inference-toolkit) - SageMaker Hugging Face Inference Toolkit is an open-source library for serving 🤗 [Transformers](https://huggingface.co/docs/transformers/index) and [Diffusers](https://huggingface.co/docs/diffusers/index) models on Amazon SageMaker.
 * 🛠️ [sagemaker-inference-toolkit](https://github.com/aws/sagemaker-inference-toolkit) - The SageMaker Inference Toolkit implements a model serving stack and can be easily added to any Docker container, making it [deployable to SageMaker](https://aws.amazon.com/sagemaker/deploy/).
   * [sagemaker-inference-toolkit parameters](https://github.com/aws/sagemaker-inference-toolkit/blob/master/src/sagemaker_inference/parameters.py) - List of environment variables for SageMaker Endpoint
 * 🛠️ [sagemaker-pytorch-inference-toolkit](https://github.com/aws/sagemaker-pytorch-inference-toolkit) - SageMaker PyTorch Inference Toolkit is an open-source library for serving PyTorch models on Amazon SageMaker.
   * [sagemaker-pytorch-inference-toolkit parameters](https://github.com/aws/sagemaker-pytorch-inference-toolkit/blob/master/src/sagemaker_pytorch_serving_container/ts_parameters.py) - List of environment variables for SageMaker Endpoint