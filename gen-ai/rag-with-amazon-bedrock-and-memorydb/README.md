# QA with LLM and RAG (Retrieval Augmented Generation)

This project is a Question Answering application with Large Language Models (LLMs) and Amazon MemoryDB for Redis. An application using the RAG(Retrieval Augmented Generation) approach retrieves information most relevant to the user’s request from the enterprise knowledge base or content, bundles it as context along with the user’s request as a prompt, and then sends it to the LLM to get a GenAI response.

LLMs have limitations around the maximum word count for the input prompt, therefore choosing the right passages among thousands or millions of documents in the enterprise, has a direct impact on the LLM’s accuracy.

In this project, Amazon MemoryDB for Redis is used for knowledge base.

The overall architecture is like this:

![rag_with_bedrock_memorydb_arch](./cdk_stacks/rag_with_bedrock_memorydb_arch.svg)

### Overall Workflow

1. Deploy the cdk stacks (For more information, see [here](./cdk_stacks/README.md)).
   - An Amazon MemoryDB for Redis to store embeddings.
   - An SageMaker Studio for RAG application and data ingestion to Amazon MemoryDB for Redis.
2. Open SageMaker Studio and then open a new terminal.
3. Run the following commands on the terminal to clone the code repository for this project:
   ```
   git clone --depth=1 https://github.com/aws-samples/rag-with-amazon-bedrock-and-memorydb.git
   ```
4. Open `data_ingestion_to_memorydb.ipynb` notebook and Run it. (For more information, see [here](./data_ingestion_to_vectordb/data_ingestion_to_memorydb.ipynb))
5. Run Streamlit application. (For more information, see [here](./app/README.md))

### References

  * [Vector search - Amazon MemoryDB for Redis](https://docs.aws.amazon.com/memorydb/latest/devguide/vector-search.html)
  * [Amazon MemoryDB for Redis engine versions](https://docs.aws.amazon.com/memorydb/latest/devguide/engine-versions.html)
  * [Build a powerful question answering bot with Amazon SageMaker, Amazon OpenSearch Service, Streamlit, and LangChain (2023-05-25)](https://aws.amazon.com/blogs/machine-learning/build-a-powerful-question-answering-bot-with-amazon-sagemaker-amazon-opensearch-service-streamlit-and-langchain/)
  * [Build Streamlit apps in Amazon SageMaker Studio (2023-04-11)](https://aws.amazon.com/blogs/machine-learning/build-streamlit-apps-in-amazon-sagemaker-studio/)
  * [LangChain](https://python.langchain.com/docs/get_started/introduction.html) - A framework for developing applications powered by language models.
  * [Streamlit](https://streamlit.io/) - A faster way to build and share data apps
  * [rag-with-amazon-kendra](https://github.com/ksmin23/rag-with-amazon-kendra) - Question Answering application with Large Language Models (LLMs) and Amazon Kendra
  * [rag-with-amazon-postgresql-using-pgvector](https://github.com/aws-samples/rag-with-amazon-postgresql-using-pgvector) - Question Answering application with Large Language Models (LLMs) and Amazon Aurora Postgresql
  * [rag-with-amazon-opensearch](https://github.com/ksmin23/rag-with-amazon-opensearch) - Question Answering application with Large Language Models (LLMs) and Amazon OpenSearch Service with [LangChain](https://www.langchain.com/)
  * [rag-with-amazon-opensearch-serverless](https://github.com/aws-samples/rag-with-amazon-opensearch-serverless) - Question Answering application with Large Language Models (LLMs) and Amazon OpenSearch Service Serverless with [LangChain](https://www.langchain.com/)
  * [rag-with-haystack-and-amazon-opensearch](https://github.com/ksmin23/rag-with-haystack-and-amazon-opensearch) - Question Answering application with Large Language Models (LLMs) and Amazon OpenSearch Service with [Haystack](https://haystack.deepset.ai/)
  * [rag-with-amazon-memorydb-and-sagemaker](https://github.com/aws-samples/aws-kr-startup-samples/tree/main/gen-ai/rag-with-amazon-memorydb-and-sagemaker) - Question Answering application with Large Language Models (LLMs) and Amazon MemoryDB for Redis with [LangChain](https://www.langchain.com/)

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.
