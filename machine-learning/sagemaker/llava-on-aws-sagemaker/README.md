# Hosting LLaVA model on Amazon SageMaker Real-time Inference Endpoint using SageMaker HuggingFace DLC

This is a CDK Python project to host the [LLaVA (Large Language and Vision Assistant)](https://llava-vl.github.io/) model
on Amazon SageMaker Real-time Inference Endpoint.

[LLaVA](https://huggingface.co/docs/transformers/model_doc/llava) is is an open-source chatbot trained by fine-tuning LlamA/Vicuna on GPT-generated multimodal instruction-following data.
It is an auto-regressive language model, based on the transformer architecture.
In other words, it is an multi-modal version of LLMs fine-tuned for chat / instructions.

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
$ git sparse-checkout set machine-learning/sagemaker/llava-on-aws-sagemaker
$ cd machine-learning/sagemaker/llava-on-aws-sagemaker

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
   (.venv) cp -rp src/python/code model
   (.venv) tar --exclude=".ipynb_checkpoints" -czf model.tar.gz -C model .
   (.venv) tar -tvf model.tar.gz
    drwxr-xr-x  0 wheel staff       0 Jul 19 13:44 ./
    drwxr-xr-x  0 wheel staff       0 Jul 19 10:33 code/
    -rw-r--r--  0 wheel staff      39 Jul 19 13:30 code/requirements.txt
    -rw-r--r--  0 wheel staff    1249 Jul 19 12:17 code/inference.py
   ```

   :information_source: For more information about the directory structure of `model.tar.gz`, see [**Model Directory Structure for Deploying Pre-trained PyTorch Models**](https://sagemaker.readthedocs.io/en/stable/frameworks/pytorch/using_pytorch.html#model-directory-structure)

   (3) Upload `model.tar.gz` file into `s3`
   <pre>
   (.venv) export MODEL_URI="s3://{<i>bucket_name</i>}/{<i>key_prefix</i>}/model.tar.gz"
   (.venv) aws s3 cp model.tar.gz ${MODEL_URI}
   </pre>

   :warning: Replace `bucket_name` and `key_prefix` with yours.

   :warning: `bucket_name` should start with `sagemaker-` prefix. (e.g., `sagemaker-us-east-1-123456789012`)

2. Set up `cdk.context.json`

   Then, you should set approperly the cdk context configuration file, `cdk.context.json`.

   For example,
   <pre>
   {
     "model_id": "llava-hf/llava-1.5-7b-hf",
     "model_data_source": {
       "s3_bucket_name": "<i>sagemaker-us-east-1-123456789012</i>",
       "s3_object_key_name": "<i>llava-1.5-7b-hf/model.tar.gz</i>"
     }
   }
   </pre>
   :warning: `s3_bucket_name` should start with `sagemaker-` prefix.

## Deploy

At this point you can now synthesize the CloudFormation template for this code.

```
(.venv) $ export CDK_DEFAULT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
(.venv) $ export CDK_DEFAULT_REGION=$(curl -s 169.254.169.254/latest/dynamic/instance-identity/document | jq -r .region)
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

Following [deploy_llava_on_sagemaker_realtime_endpoint.ipynb](src/notebook/deploy_llava_on_sagemaker_realtime_endpoint.ipynb) on the SageMaker Studio, we can deploy the model to Amazon SageMaker.

## Example

Following [llava_realtime_endpoint.ipynb](src/notebook/llava_realtime_endpoint.ipynb) on the SageMaker Studio, we can invoke the model with sample data.

## References

 * [LLaVA: Large Language and Vision Assistant](https://llava-vl.github.io/)
   * [LLaVa in HuggingFace](https://huggingface.co/docs/transformers/model_doc/llava)
   * [llava-hf/llava-1.5-7b-hf](https://huggingface.co/llava-hf/llava-1.5-7b-hf)
   * 🤗 [HuggingFace Transformers Supported models and frameworks](https://huggingface.co/docs/transformers/index#supported-models-and-frameworks)
 * [AWS Generative AI CDK Constructs](https://awslabs.github.io/generative-ai-cdk-constructs/)
 * [(AWS Blog) Announcing Generative AI CDK Constructs (2024-01-31)](https://aws.amazon.com/blogs/devops/announcing-generative-ai-cdk-constructs/)
 * [SageMaker Python SDK - Hugging Face](https://sagemaker.readthedocs.io/en/stable/frameworks/huggingface/index.html)
 * [Docker Registry Paths and Example Code for Pre-built SageMaker Docker images](https://docs.aws.amazon.com/sagemaker/latest/dg-ecr-paths/sagemaker-algo-docker-registry-paths.html)
 * [Model Directory Structure for Deploying Pre-trained PyTorch Models](https://sagemaker.readthedocs.io/en/stable/frameworks/pytorch/using_pytorch.html#model-directory-structure)
 * 🛠️ [sagemaker-huggingface-inference-toolkit](https://github.com/aws/sagemaker-huggingface-inference-toolkit) - SageMaker Hugging Face Inference Toolkit is an open-source library for serving 🤗 [Transformers](https://huggingface.co/docs/transformers/index) and [Diffusers](https://huggingface.co/docs/diffusers/index) models on Amazon SageMaker.
 * 🛠️ [sagemaker-inference-toolkit](https://github.com/aws/sagemaker-inference-toolkit) - The SageMaker Inference Toolkit implements a model serving stack and can be easily added to any Docker container, making it [deployable to SageMaker](https://aws.amazon.com/sagemaker/deploy/).
   * [sagemaker-inference-toolkit parameters](https://github.com/aws/sagemaker-inference-toolkit/blob/master/src/sagemaker_inference/parameters.py) - List of environment variables for SageMaker Endpoint
 * 🛠️ [sagemaker-pytorch-inference-toolkit](https://github.com/aws/sagemaker-pytorch-inference-toolkit) - SageMaker PyTorch Inference Toolkit is an open-source library for serving PyTorch models on Amazon SageMaker.
   * [sagemaker-pytorch-inference-toolkit parameters](https://github.com/aws/sagemaker-pytorch-inference-toolkit/blob/master/src/sagemaker_pytorch_serving_container/ts_parameters.py) - List of environment variables for SageMaker Endpoint