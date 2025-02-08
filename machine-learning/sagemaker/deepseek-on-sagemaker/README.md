# Hosting DeepSeek model on Amazon SageMaker

This repository contains a set of example CDK Python projects to host [DeepSeek models](https://huggingface.co/deepseek-ai) on Amazon SageMaker Endpoint.

You can deploy the model to SageMaker hosting services and get an endpoint that can be used for inference. These endpoints are fully managed and support autoscaling.

| CDK Project  | Hugging Face Model Card | Description | Deployment |
|--------------|-------------------------|-------------|------------|
| [deepseek-r1-distill-llama-8b](../scale-to-zero-sagemaker-endpoint/) | [deepseek-ai/DeepSeek-R1-Distill-Llama-8B](https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Llama-8B) | Reasoning model | using LMI(Large Model Inference) container, SageMaker Endpoint with Scale-to-Zero capability |
| [deepseek-r1-distill-qwen-14b](./deepseek-r1-distill-qwen-14b/) | [deepseek-ai/DeepSeek-R1-Distill-Qwen-14B](https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-14B) | Reasoning model | using LMI(Large Model Inference) container |
| [deepseek-r1-distill-qwen-32b](./deepseek-r1-distill-qwen-32b/) | [deepseek-ai/DeepSeek-R1-Distill-Qwen-32B](https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-14B) | Reasoning model | using SageMaker JumpStart |
| [deepseek-v2-lite-chat](./deepseek-v2-lite-chat/) | [deepseek-ai/DeepSeek-V2-Lite-Chat](https://huggingface.co/deepseek-ai/DeepSeek-V2-Lite-Chat) | Mixture-of-Experts (MoE) Language model | using LMI(Large Model Inference) container |
| [janus-pro-7b](./janus-pro-7b/) | [deepseek-ai/Janus-Pro-7B](https://huggingface.co/deepseek-ai/Janus-Pro-7B) | Visual Question Answering and Text-to-Image generation | using PyTorch DLC |

Enjoy!

## References

 * [DeepSeek: A Strong, Economical, and Efficient Mixture-of-Experts Language Model](https://www.deepseek.com/)
   * [DeepSeek in HuggingFace](https://huggingface.co/deepseek-ai)
 * [(AWS News Blog) DeepSeek-R1 models now available on AWS (2025-01-30)](https://aws.amazon.com/blogs/aws/deepseek-r1-models-now-available-on-aws/)
 * [Available AWS Deep Learning Containers (DLC) images](https://github.com/aws/deep-learning-containers/blob/master/available_images.md)

## Related Works

 * [deepseek-ai/deepseek-coder-6.7b-instruct SageMaker LMI deployment guide](https://github.com/aws-samples/llm_deploy_gcr/blob/main/sagemaker/deepseek_coder_6.7_instruct.ipynb)

