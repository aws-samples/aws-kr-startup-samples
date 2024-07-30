
# QA with LLM and RAG (Retrieval Augumented Generation) powered by Amazon Bedrock and Kendra

This project is a Question Answering application with Large Language Models (LLMs) and Amazon Kendra. An application using the RAG(Retrieval Augmented Generation) approach retrieves information most relevant to the user’s request from the enterprise knowledge base or content, bundles it as context along with the user’s request as a prompt, and then sends it to the LLM to get a GenAI response.

LLMs have limitations around the maximum word count for the input prompt, therefore choosing the right passages among thousands or millions of documents in the enterprise, has a direct impact on the LLM’s accuracy.

In this project, Amazon Kendra is used for knowledge base.

The overall architecture is like this:

![rag_with_bedrock_kendra_arch](./cdk_stacks/rag_with_bedrock_kendra_arch.svg)

### Prerequisites

Before using a foundational model in Bedrock your account needs to be granted access first.

Follow the steps here to add models: [Amazon Bedrock - Add model access](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html#add-model-access)

Some models require some additional information and take some time before you are granted access. Once the model shows "Access granted" on the Model Access page, you should be able to call the `invoke_model()` function without the error.

### Overall Workflow

1. Deploy the cdk stacks (For more information, see [here](./cdk_stacks/README.md)).
   - An Amazon Kendra for knowledge base.
2. Open SageMaker Studio and then open a new terminal.
3. Run the following commands on the terminal to clone the code repository for this project:
   ```
   git clone --depth=1 https://github.com/aws-samples/qa-app-with-rag-using-amazon-bedrock-and-kendra.git
   ```
4. Run Streamlit application. (For more information, see [here](./app/README.md))

### References

  * [Amazon Bedrock - Add model access](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html#add-model-access)
  * [Amazon Bedrock Workshop](https://github.com/aws-samples/amazon-bedrock-workshop)
  * [Quickly build high-accuracy Generative AI applications on enterprise data using Amazon Kendra, LangChain, and large language models (2023-05-03)](https://aws.amazon.com/blogs/machine-learning/quickly-build-high-accuracy-generative-ai-applications-on-enterprise-data-using-amazon-kendra-langchain-and-large-language-models/)
    * [(github) Amazon Kendra Retriver Samples](https://github.com/aws-samples/amazon-kendra-langchain-extensions/tree/main/kendra_retriever_samples)
  * [Build a powerful question answering bot with Amazon SageMaker, Amazon OpenSearch Service, Streamlit, and LangChain (2023-05-25)](https://aws.amazon.com/blogs/machine-learning/build-a-powerful-question-answering-bot-with-amazon-sagemaker-amazon-opensearch-service-streamlit-and-langchain/)
  * [Build Streamlit apps in Amazon SageMaker Studio (2023-04-11)](https://aws.amazon.com/blogs/machine-learning/build-streamlit-apps-in-amazon-sagemaker-studio/)
  * [Question answering using Retrieval Augmented Generation with foundation models in Amazon SageMaker JumpStart (2023-05-02)](https://aws.amazon.com/blogs/machine-learning/question-answering-using-retrieval-augmented-generation-with-foundation-models-in-amazon-sagemaker-jumpstart/)
  * [Use proprietary foundation models from Amazon SageMaker JumpStart in Amazon SageMaker Studio (2023-06-27)](https://aws.amazon.com/blogs/machine-learning/use-proprietary-foundation-models-from-amazon-sagemaker-jumpstart-in-amazon-sagemaker-studio/)
  * [LangChain](https://python.langchain.com/docs/get_started/introduction.html) - A framework for developing applications powered by language models.
  * [Streamlit](https://streamlit.io/) - A faster way to build and share data apps
  * [Improve search relevance with ML in Amazon OpenSearch Service Workshop](https://catalog.workshops.aws/semantic-search/en-US) - Module 7. Retrieval Augmented Generation
  * [rag-with-amazon-opensearch-and-sagemaker](https://github.com/aws-samples/rag-with-amazon-opensearch-and-sagemaker) - Question Answering application with Large Language Models (LLMs) and Amazon OpenSearch Service
  * [rag-with-amazon-postgresql-using-pgvector](https://github.com/aws-samples/rag-with-amazon-postgresql-using-pgvector) - Question Answering application with Large Language Models (LLMs) and Amazon Aurora Postgresql

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.
