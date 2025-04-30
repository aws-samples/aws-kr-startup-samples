# Hybrid MLOps system with self-hosted MLflow integrated with Amazon SageMaker

This repository contains a set of example projects for Hybrid MLOps System with MLflow integrated with Amazon SageMaker.
These projects will be useful when you want to train ML models on-prem GPUs and deploy the trained models to Amazon SageMaker Endpoint.


| Project name | Architecture | Description |
|--------------|--------------|-------------|
| [MLflow on ECS integrated with Amazon SageMaker](./mlflow-ecs-sagemaker) | ![mlflow-ecs-sagemaker-arch](./mlflow-ecs-sagemaker/mlflow-ecs-sagemaker-arch.svg) | MLflow on Amazon ECS Fargate with Amazon SageMaker |
| [MLflow on EC2 integrated with Amazon SageMaker](./mlflow-ec2-sagemaker) | ![mlflow-ec2-sagemaker-arch](./mlflow-ec2-sagemaker/mlflow-sagemaker-arch.svg) | MLflow on Amazon EC2 with Amazon SageMaker |

Enjoy!

## References

 * [(AWS Blog) Announcing the general availability of fully managed MLflow on Amazon SageMaker (2024-06-24)](https://aws.amazon.com/blogs/aws/manage-ml-and-generative-ai-experiments-using-amazon-sagemaker-with-mlflow/)
   * [(AWS Blog) Amazon SageMaker 기반 완전 관리형 MLflow 정식 출시 (2024-06-24)](https://aws.amazon.com/ko/blogs/korea/manage-ml-and-generative-ai-experiments-using-amazon-sagemaker-with-mlflow/)
 * [(AWS Blog) Managing your machine learning lifecycle with MLflow and Amazon SageMaker (2021-01-28)](https://aws.amazon.com/blogs/machine-learning/managing-your-machine-learning-lifecycle-with-mlflow-and-amazon-sagemaker/)
   * [(GitHub Repo) amazon-sagemaker-mlflow-fargate](https://github.com/ksmin23/amazon-sagemaker-mlflow-fargate)
 * [MLflow Documentation](https://mlflow.org/docs/latest/index.html)
