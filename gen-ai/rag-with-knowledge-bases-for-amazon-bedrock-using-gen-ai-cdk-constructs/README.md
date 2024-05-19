# QA with LLM and RAG (Retrieval Augmented Generation) using Knowledge Bases for Amazon Bedrock

This project is an Question Answering application with Large Language Models (LLMs) and Knowledge Bases for Amazon Bedrock. An application using the RAG(Retrieval Augmented Generation) approach retrieves information most relevant to the user’s request from the enterprise knowledge base or content, bundles it as context along with the user’s request as a prompt, and then sends it to the LLM to get a GenAI response.

LLMs have limitations around the maximum word count for the input prompt, therefore choosing the right passages among thousands or millions of documents in the enterprise, has a direct impact on the LLM’s accuracy.

In this project, Knowledge Bases for Amazon Bedrock is used for knowledge base.

The overall architecture is like this:

![rag_with_knowledge_bases_for_amazon_bedrock_arch](./cdk_stacks/rag_with_knowledge_bases_for_amazon_bedrock_arch.svg)

### Overall Workflow

1. Deploy the cdk stacks (For more information, see [here](./cdk_stacks/README.md)).
   - A Knowledge Base for Amazon Bedrock to store embeddings.
   - A SageMaker Studio for RAG application and data ingestion to Knowledge Base for Amazon Bedrock.
2. Open SageMaker Studio and then open a new terminal.
3. Run the following commands on the terminal to clone the code repository for this project:
   ```
   git clone --depth=1 https://github.com/aws-samples/aws-kr-startup-samples.git
   cd aws-kr-startup-samples/gen-ai/rag-with-knowledge-bases-for-amazon-bedrock-using-gen-ai-cdk-constructs
   ```
4. Open `kb_for_amazon_bedrock.ipynb` notebook and Run it. (For more information, see [here](./data_ingestion_to_vectordb/kb_for_amazon_bedrock.ipynb))
5. Run Streamlit application. (For more information, see [here](./app/README.md))

### References

  * [Amazon Bedrock Workshop](https://catalog.us-east-1.prod.workshops.aws/workshops/a4bdb007-5600-4368-81c5-ff5b4154f518/en-US) - Hands-on labs using Amazon Bedrock APIs, SDKs, and open-source software, such as LangChain and FAISS, to implement the most common Generative AI usage patterns (e.g., summarizing text, answering questions, building chatbots, creating images, and generating code).
  * [Building with Amazon Bedrock and LangChain](https://catalog.workshops.aws/building-with-amazon-bedrock/en-US) - Hands-on labs using [LangChain](https://github.com/langchain-ai/langchain) to build generative AI prototypes with Amazon Bedrock.
  * [Amazon Bedrock Samples](https://github.com/aws-samples/amazon-bedrock-samples) - Pre-built examples to help customers get started with the Amazon Bedrock service.
    * [Deploy e2e RAG solution (using Knowledgebases for Amazon Bedrock) via CloudFormation](https://github.com/aws-samples/amazon-bedrock-samples/tree/main/knowledge-bases/03-infra/e2e-rag-using-bedrock-kb-cfn)
  * [Build a powerful question answering bot with Amazon SageMaker, Amazon OpenSearch Service, Streamlit, and LangChain (2023-05-25)](https://aws.amazon.com/blogs/machine-learning/build-a-powerful-question-answering-bot-with-amazon-sagemaker-amazon-opensearch-service-streamlit-and-langchain/)
  * [Build Streamlit apps in Amazon SageMaker Studio (2023-04-11)](https://aws.amazon.com/blogs/machine-learning/build-streamlit-apps-in-amazon-sagemaker-studio/)
  * [LangChain](https://python.langchain.com/docs/get_started/introduction.html) - A framework for developing applications powered by language models.
  * [Streamlit](https://streamlit.io/) - A faster way to build and share data apps
  * [rag-with-amazon-kendra-and-sagemaker](https://github.com/aws-samples/aws-kr-startup-samples/tree/main/gen-ai/rag-with-amazon-kendra-and-sagemaker) - Question Answering application with Large Language Models (LLMs) and Amazon Kendra
  * [rag-with-amazon-postgresql-using-pgvector](https://github.com/aws-samples/rag-with-amazon-postgresql-using-pgvector) - Question Answering application with Large Language Models (LLMs) and Amazon Aurora Postgresql
  * [rag-with-amazon-opensearch-and-sagemaker](https://github.com/aws-samples/rag-with-amazon-opensearch-and-sagemaker) - Question Answering application with Large Language Models (LLMs) and Amazon OpenSearch Service with [LangChain](https://www.langchain.com/)
  * [rag-with-amazon-opensearch-serverless](https://github.com/aws-samples/rag-with-amazon-opensearch-serverless) - Question Answering application with Large Language Models (LLMs) and Amazon OpenSearch Service Serverless with [LangChain](https://www.langchain.com/)
  * [rag-with-haystack-and-amazon-opensearch](https://github.com/ksmin23/rag-with-haystack-and-amazon-opensearch) - Question Answering application with Large Language Models (LLMs) and Amazon OpenSearch Service with [Haystack](https://haystack.deepset.ai/)
