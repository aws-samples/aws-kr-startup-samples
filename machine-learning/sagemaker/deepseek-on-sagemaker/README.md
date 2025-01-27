# Hosting DeepSeek model on Amazon SageMaker

This repository contains a set of example CDK Python projects to host [DeepSeek models](https://huggingface.co/deepseek-ai) on Amazon SageMaker Endpoint.

You can deploy the model to SageMaker hosting services and get an endpoint that can be used for inference. These endpoints are fully managed and support autoscaling.

| CDK Project  | Hugging Face Model Card |
|--------------|-------------------------|
| [deepseek-r1-distill-qwen-14b](./deepseek-r1-distill-qwen-14b/) | [deepseek-ai/DeepSeek-R1-Distill-Qwen-14B](https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-14B) |
| [deepseek-v2-lite-chat](./deepseek-v2-lite-chat/) | [deepseek-ai/DeepSeek-V2-Lite-Chat](https://huggingface.co/deepseek-ai/DeepSeek-V2-Lite-Chat) |

Enjoy!

## References

 * [DeepSeek: A Strong, Economical, and Efficient Mixture-of-Experts Language Model](https://www.deepseek.com/)
   * [DeepSeek in HuggingFace](https://huggingface.co/deepseek-ai)
 * [Available AWS Deep Learning Containers (DLC) images](https://github.com/aws/deep-learning-containers/blob/master/available_images.md)

## Related Works

 * [deepseek-ai/deepseek-coder-6.7b-instruct SageMaker LMI deployment guide](https://github.com/aws-samples/llm_deploy_gcr/blob/main/sagemaker/deepseek_coder_6.7_instruct.ipynb)

