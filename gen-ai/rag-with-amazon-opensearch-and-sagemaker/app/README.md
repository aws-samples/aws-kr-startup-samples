## Run the Streamlit application in Studio

Now we’re ready to run the Streamlit web application for our question answering bot.

SageMaker Studio provides a convenient platform to host the Streamlit web application. The following steps describes how to run the Streamlit app on SageMaker Studio. Alternatively, you could also follow the same procedure to run the app on Amazon EC2 instance, Cloud9 in your AWS Account, or deploy as a container service to AWS ECS Fargate.

1. Open Studio and then open a new **System terminal**.
   ![](sagemaker-studio-launcher-screenshot.png)
2. Run the following commands on the terminal to clone the code repository for this post and install the Python packages needed by the application:
   ```
   git clone --depth=1 https://github.com/aws-samples/rag-with-amazon-opensearch-and-sagemaker.git
   cd rag-with-opensearch/app
   python -m venv .env
   source .env/bin/activate
   pip install -r requirements.txt
   ```
3. In the shell, set the following environment variables with the values that are available from the CloudFormation stack output.
   ```
   export AWS_REGION=us-east-1
   export OPENSEARCH_SECRET="your-opensearch-secret"
   export OPENSEARCH_DOMAIN_ENDPOINT="your-opensearch-url"
   export OPENSEARCH_INDEX="llm_rag_embeddings"
   export EMBEDDING_ENDPOINT_NAME="your-sagemakr-endpoint-for-embedding-model"
   export TEXT2TEXT_ENDPOINT_NAME="your-sagemaner-endpoint-for-text-generation-model"
   ```
4. When the application runs successfully, you’ll see an output similar to the following (the IP addresses you will see will be different from the ones shown in this example). Note the port number (typically `8501`) from the output to use as part of the URL for app in the next step.
   ```
   sagemaker-user@studio$ streamlit run app.py

   Collecting usage statistics. To deactivate, set browser.gatherUsageStats to False.

   You can now view your Streamlit app in your browser.

   Network URL: http://169.255.255.2:8501
   External URL: http://52.4.240.77:8501
   ```
5. You can access the app in a new browser tab using a URL that is similar to your Studio domain URL. For example, if your Studio URL is `https://d-randomidentifier.studio.us-east-1.sagemaker.aws/jupyter/default/lab?` then the URL for your Streamlit app will be `https://d-randomidentifier.studio.us-east-1.sagemaker.aws/jupyter/default/proxy/8501/app` (notice that `lab` is replaced with `proxy/8501/app`). If the port number noted in the previous step is different from 8501 then use that instead of 8501 in the URL for the Streamlit app.

   The following screenshot shows the app with a couple of user questions. (e.g., `Whare are the versions of XGBoost supported by Amazon SageMaker?`)

   ![qa-with-llm-and-rag](./qa-with-llm-and-rag.png)


## Deploy Streamlit application on Amazon ECS Fargate with AWS CDK

To deploy the Streamlit application on Amazon ECS Fargate using AWS CDK, follow these steps:

1. Ensure you have the AWS CDK and docker or finch installed and configured.
2. Deploy the ECS stack from `cdk_stacks/` using the command `cdk deploy --require-approval never StreamlitAppStack`.
3. Access the Streamlit application using the public URL provided by the provisioned load balancer.
   1. You can find this value under the export named `{stack-name}-StreamlitEndpoint`
4. Consider adding a security group ingress rule that scopes access to the application from your network by a prefix list or a CIDR block
5. Also consider enabling HTTPS by uploading a ssl certificate from IAM or ACM to the loadbalancer and add a listener on port 443


## References

  * [Build a powerful question answering bot with Amazon SageMaker, Amazon OpenSearch Service, Streamlit, and LangChain (2023-05-25)](https://aws.amazon.com/blogs/machine-learning/build-a-powerful-question-answering-bot-with-amazon-sagemaker-amazon-opensearch-service-streamlit-and-langchain/)
  * [Build Streamlit apps in Amazon SageMaker Studio (2023-04-11)](https://aws.amazon.com/blogs/machine-learning/build-streamlit-apps-in-amazon-sagemaker-studio/)
  * [Quickly build high-accuracy Generative AI applications on enterprise data using Amazon Kendra, LangChain, and large language models (2023-05-03)](https://aws.amazon.com/blogs/machine-learning/quickly-build-high-accuracy-generative-ai-applications-on-enterprise-data-using-amazon-kendra-langchain-and-large-language-models/)
    * [(github) Amazon Kendra Retriver Samples](https://github.com/aws-samples/amazon-kendra-langchain-extensions/tree/main/kendra_retriever_samples)
  * [Use proprietary foundation models from Amazon SageMaker JumpStart in Amazon SageMaker Studio (2023-06-27)](https://aws.amazon.com/blogs/machine-learning/use-proprietary-foundation-models-from-amazon-sagemaker-jumpstart-in-amazon-sagemaker-studio/)
  * [sagemaker-huggingface-inference-toolkit](https://github.com/aws/sagemaker-huggingface-inference-toolkit) - SageMaker Hugging Face Inference Toolkit is an open-source library for serving 🤗 Transformers and Diffusers models on Amazon SageMaker.
  * [LangChain](https://python.langchain.com/docs/get_started/introduction.html) - A framework for developing applications powered by language models.
  * [Streamlit](https://streamlit.io/) - A faster way to build and share data apps
