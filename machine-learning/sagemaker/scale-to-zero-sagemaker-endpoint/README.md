
# Reducing Inference Costs on DeepSeek-R1-Distill-Llama-8B with SageMaker Inference's Scale to Zero Capability

This demo notebook demonstrate how you can scale in your SageMaker endpoint to zero instances during idle periods, eliminating the previous requirement of maintaining at least one running instance.

This is a CDK Python project to deploy **DeepSeek-R1-Distill-Llama-8B** a SageMaker real-time endpoint with the scale down to zero feature.

The scale down to zero feature allows you to configure the endpoints so they can scale to zero instances during periods of inactivity, providing an additional tool for resource management.
> :information_source: For more information about the Scale to Zero feature, see this [blog post](https://aws.amazon.com/blogs/machine-learning/unlock-cost-savings-with-the-new-scale-down-to-zero-feature-in-amazon-sagemaker-inference/).


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
$ git sparse-checkout set machine-learning/sagemaker/scale-to-zero-sagemaker-endpoint
$ cd machine-learning/sagemaker/scale-to-zero-sagemaker-endpoint

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

## Set up `cdk.context.json`

Then, you should set approperly the cdk context configuration file, `cdk.context.json`.

For example,
<pre>
{
  "sagemaker_endpoint_name": "deepseek-r1-llama-8b-ep",
  "sagemaker_endpoint_config": {
    "instance_type": "ml.g5.2xlarge",
    "managed_instance_scaling": {
      "min_instance_count": 0,
      "max_instance_count": 2,
      "status": "ENABLED"
    },
    "routing_config": {
      "routing_strategy": "LEAST_OUTSTANDING_REQUESTS"
    }
  },
  "deep_learning_container_image_uri": {
    "repository_name": "djl-inference",
    "tag": "0.31.0-lmi13.0.0-cu124"
  },
  "models": {
    "deepseek-r1-llama-8b": {
      "HF_MODEL_ID": "deepseek-ai/DeepSeek-R1-Distill-Llama-8B",
      "OPTION_MAX_MODEL_LEN": "10000",
      "OPTION_GPU_MEMORY_UTILIZATION": "0.95",
      "OPTION_ENABLE_STREAMING": "false",
      "OPTION_ROLLING_BATCH": "auto",
      "OPTION_MODEL_LOADING_TIMEOUT": "3600",
      "OPTION_PAGED_ATTENTION": "false",
      "OPTION_DTYPE": "fp16"
    }
  },
  "inference_components": {
    "ic-deepseek-r1-llama-8b": {
      "model_name": "deepseek-r1-llama-8b",
      "compute_resource_requirements": {
        "number_of_accelerator_devices_required": 1,
        "number_of_cpu_cores_required": 2,
        "min_memory_required_in_mb": 1024
      },
      "runtime_config": {
        "copy_count": 1
      }
    }
  }
}
</pre>

> :information_source: Swap `HF_MODEL_ID: deepseek-ai/DeepSeek-R1-Distill-Llama-8B` with another [DeepSeek Distilled Variant](https://huggingface.co/deepseek-ai/DeepSeek-R1#deepseek-r1-distill-models) if you prefer to deploy a different dense model. Optionally, you can include `HF_TOKEN: "hf_..."` for gated models.

> :information_source: The avialable Deep Learning Container (DLC) images (`deep_learning_container_image_uri`) can be found in [here](https://github.com/aws/deep-learning-containers/blob/master/available_images.md).

## (Optional) Bootstrap AWS environment for AWS CDK app

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

We can list all the CDK stacks by using the `cdk list` command prior to deployment.

```
(.venv) $ cdk list
```

## Test Run Inference

If you want to run inference, checkout this [example notebook](./src/notebook/DeepSeek-R1-Distill-Llama-8B-scale-to-zero-autoscaling.ipynb).

## Clean Up

Delete the CloudFormation stack by running the below command.

```
(.venv) $ cdk destroy --force --all
```

## (Optional) Deploy the model using SageMaker Python SDK

Following this [example notebook](./src/notebook/deploy-DeepSeek-R1-Distill-Llama-8B-with-scale-to-zero-autoscaling.ipynb) on the SageMaker Studio, we can deploy the model to Amazon SageMaker.

## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

Enjoy!

## References

 * [(AWS Machine Learning Blog) Unlock cost savings with the new scale down to zero feature in SageMaker Inference (2024-12-02)](https://aws.amazon.com/blogs/machine-learning/unlock-cost-savings-with-the-new-scale-down-to-zero-feature-in-amazon-sagemaker-inference/)
   * [💻 scale-to-zero-endpoint/llama3-8b-scale-to-zero-autoscaling.ipynb](https://github.com/aws-samples/sagemaker-genai-hosting-examples/blob/main/scale-to-zero-endpoint/llama3-8b-scale-to-zero-autoscaling.ipynb)
* [💻 (GitHub) sagemaker-genai-hosting-examples](https://github.com/aws-samples/sagemaker-genai-hosting-examples)
* [💻 Deploy DeepSeek R1 Large Language Model from HuggingFace Hub on Amazon SageMaker](https://github.com/aws-samples/sagemaker-genai-hosting-examples/blob/main/Deepseek/DeepSeek-R1-Llama8B-LMI-TGI-Deploy.ipynb)
* [(AWS News Blog) DeepSeek-R1 models now available on AWS (2025-01-30)](https://aws.amazon.com/blogs/aws/deepseek-r1-models-now-available-on-aws/)
* [(AWS re:Post) Get started with DeepSeek R1 on AWS Inferentia and Trainium (2025-01-30)](https://repost.aws/articles/ARDaRTyEVQR9iWfVdek2CQwg/get-started-with-deepseek-r1-on-aws-inferentia-and-trainium)
* [Amazon EC2 Instance types](https://aws.amazon.com/ec2/instance-types/)
