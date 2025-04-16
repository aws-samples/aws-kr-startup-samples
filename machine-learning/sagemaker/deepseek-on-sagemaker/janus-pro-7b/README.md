
# Hosting Janus-Pro model on Amazon SageMaker Real-time Inference Endpoint using PyTorch DLC

This is a CDK Python project to host [deepseek-ai/Janus-Pro-7B](https://huggingface.co/deepseek-ai/Janus-Pro-7B) on Amazon SageMaker Real-time Inference Endpoint.

[Janus-Pro-7B](https://huggingface.co/deepseek-ai/Janus-Pro-7B) is a unified understanding and generation MLLM, which decouples visual encoding for multimodal understanding and generation.

SagemMaker Real-time inference is ideal for inference workloads where you have real-time, interactive, low latency requirements.
You can deploy your model to SageMaker hosting services and get an endpoint that can be used for inference.
These endpoints are fully managed and support autoscaling.

The process for deploying Janus-Pro model to Amazon SageMaker Endpoint is illustrated below.

![](./deploy-janus-pro-on-sagemaker-endpoint.svg)

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
$ git sparse-checkout set machine-learning/sagemaker/deepseek-on-sagemaker/janus-pro-7b
$ cd machine-learning/sagemaker/deepseek-on-sagemaker/janus-pro-7b

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
> To add additional dependencies, for example other CDK libraries, just add
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

   (2) Create `model.tar.gz` with model artifacts including your custom [inference scripts](./src/code/).
   ```
   (.venv) $ cp -rp src/python/code model
   (.venv) $ tree model
    model
    └── code
        ├── inference.py
        └── requirements.txt

    2 directories, 2 files
   (.venv) tar --exclude=".cache" --exclude=".ipynb_checkpoints" -cvf model.tar.gz --use-compress-program=pigz -C model/ .
   ```

   :information_source: For more information about the directory structure of `model.tar.gz`, see [**Model Directory Structure for Deploying Pre-trained PyTorch Models**](https://sagemaker.readthedocs.io/en/stable/frameworks/pytorch/using_pytorch.html#model-directory-structure)

   :information_source: `pigz` is used to speed up the `tar` command. More information on how to install `pigz` can be found [here](#pigz-installation-guide).

   (3) Upload `model.tar.gz` file into `s3`
   <pre>
   (.venv) export MODEL_URI="s3://{<i>bucket_name</i>}/{<i>key_prefix</i>}/model.tar.gz"
   (.venv) aws s3 cp model.tar.gz ${MODEL_URI}
   </pre>

   :warning: Replace `bucket_name` and `key_prefix` with yours.

   :information_source: This CDK project uses [`cdklabs.generative-ai-cdk-constructs`](https://awslabs.github.io/generative-ai-cdk-constructs/) to deploy SageMaker Endpoints. `cdklabs.generative-ai-cdk-constructs` library assumes the model artifact (`model.tar.gz`) is stored in a bucket on S3 with the word "`sagemaker`" or "`SageMaker`". Therefore, `bucket_name` must include the word "`sagemaker`" or "`SageMaker`". (e.g., `sagemaker-us-east-1-123456789012`, `SageMaker-us-east-1-123456789012`).

2. Set up `cdk.context.json`

   Then, you should set approperly the cdk context configuration file, `cdk.context.json`.

   For example,
   <pre>
   {
     "model_id": "deepseek-ai/Janus-Pro-7B",
     "model_data_source": {
       "s3_bucket_name": "<i>sagemaker-us-east-1-123456789012</i>",
       "s3_object_key_name": "<i>janus-pro-7b/model.tar.gz</i>"
     },
     "dlc_image_info": {
       "repository_name": "huggingface-pytorch-inference",
       "tag": "2.3.0-transformers4.46.1-gpu-py311-cu121-ubuntu20.04"
     },
     "sagemaker_endpoint_settings": {
       "min_capacity": 1,
       "max_capacity": 4
     }
   }
   </pre>
   :information_source: This CDK project uses [`cdklabs.generative-ai-cdk-constructs`](https://awslabs.github.io/generative-ai-cdk-constructs/) to deploy SageMaker Endpoints. `cdklabs.generative-ai-cdk-constructs` library assumes the model artifact (`model.tar.gz`) is stored in a bucket on S3 with the word "`sagemaker`" or "`SageMaker`". Therefore, `s3_bucket_name` must include the word "`sagemaker`" or "`SageMaker`". (e.g., `sagemaker-us-east-1-123456789012`, `SageMaker-us-east-1-123456789012`).

   :information_source: For more information about `dlc_image_info`, see [**Available AWS Deep Learning Containers (DLC) images**](https://github.com/aws/deep-learning-containers/blob/master/available_images.md)

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

Following [deploy_janus_pro_7b_on_sagemaker_endpoint.ipynb](src/notebook/deploy_janus_pro_7b_on_sagemaker_endpoint.ipynb) on the SageMaker Studio, we can deploy the model to Amazon SageMaker.

## Example

Following [janus_pro_7b_realtime_endpoint.ipynb](src/notebook/janus_pro_7b_realtime_endpoint.ipynb) on the SageMaker Studio, we can invoke the model with sample data.

## References

 * [deepseek-ai/Janus-Pro-1B](https://huggingface.co/deepseek-ai/Janus-Pro-1B)
 * [deepseek-ai/Janus-Pro-7B](https://huggingface.co/deepseek-ai/Janus-Pro-7B)
 * [DeepSeek in HuggingFace](https://huggingface.co/deepseek-ai)
 * [(GitHub) Janus](https://github.com/deepseek-ai/Janus/) - Unified Multimodal Understanding and Generation Models
 * [Available AWS Deep Learning Containers (DLC) images](https://github.com/aws/deep-learning-containers/blob/master/available_images.md)
 * 🛠️ [sagemaker-pytorch-inference-toolkit](https://github.com/aws/sagemaker-pytorch-inference-toolkit) - SageMaker PyTorch Inference Toolkit is an open-source library for serving PyTorch models on Amazon SageMaker.
   * [sagemaker-pytorch-inference-toolkit parameters](https://github.com/aws/sagemaker-pytorch-inference-toolkit/blob/master/src/sagemaker_pytorch_serving_container/ts_parameters.py) - List of environment variables for SageMaker Endpoint
 * 🛠️ [sagemaker-huggingface-inference-toolkit](https://github.com/aws/sagemaker-huggingface-inference-toolkit) - SageMaker Hugging Face Inference Toolkit is an open-source library for serving 🤗 [Transformers](https://huggingface.co/docs/transformers/index) and [Diffusers](https://huggingface.co/docs/diffusers/index) models on Amazon SageMaker.
