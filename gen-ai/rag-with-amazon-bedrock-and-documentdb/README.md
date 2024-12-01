# QA with LLM and RAG (Retrieval Augmented Generation)

This project is a Question Answering application with Large Language Models (LLMs) and Amazon DocumentDB (with MongoDB Compatibility). An application using the RAG(Retrieval Augmented Generation) approach retrieves information most relevant to the user’s request from the enterprise knowledge base or content, bundles it as context along with the user’s request as a prompt, and then sends it to the LLM to get a GenAI response.

LLMs have limitations around the maximum word count for the input prompt, therefore choosing the right passages among thousands or millions of documents in the enterprise, has a direct impact on the LLM’s accuracy.

In this project, Amazon DocumentDB (with MongoDB Compatibility) is used for knowledge base.

The overall architecture is like this:

![rag_with_bedrock_docdb_arch](./cdk_stacks/rag_with_bedrock_docdb_arch.svg)

### Overall Workflow

1. Deploy the cdk stacks (For more information, see [here](./cdk_stacks/README.md)).
   - An Amazon DocumentDB (with MongoDB Compatibility) to store embeddings.
   - An SageMaker Studio for RAG application and data ingestion to the Amazon DocumentDB (with MongoDB Compatibility).
2. Open JupyterLab in SageMaker Studio and then open a new terminal.
3. Run the following commands on the terminal to clone the code repository for this project:
   ```
   git clone --depth=1 https://github.com/aws-samples/aws-kr-startup-samples.git
   cd aws-kr-startup-samples
   git sparse-checkout init --cone
   git sparse-checkout set gen-ai/rag-with-amazon-bedrock-and-documentdb
   ```
4. Open `data_ingestion_to_documentdb.ipynb` notebook and Run it. (For more information, see [here](./data_ingestion_to_vectordb/data_ingestion_to_documentdb.ipynb))
5. Run Streamlit application. (For more information, see [here](./app/README.md))

### References

  * [Vector search for Amazon DocumentDB](https://docs.aws.amazon.com/documentdb/latest/developerguide/vector-search.html)
    * [github.com/aws-samples/amazon-documentdb-samples](https://github.com/aws-samples/amazon-documentdb-samples/)
  * [Vector search for Amazon DocumentDB (with MongoDB compatibility) is now generally available (2023-11-29)](https://aws.amazon.com/blogs/aws/vector-search-for-amazon-documentdb-with-mongodb-compatibility-is-now-generally-available/)
  * [Build a powerful question answering bot with Amazon SageMaker, Amazon OpenSearch Service, Streamlit, and LangChain (2023-05-25)](https://aws.amazon.com/blogs/machine-learning/build-a-powerful-question-answering-bot-with-amazon-sagemaker-amazon-opensearch-service-streamlit-and-langchain/)
  * [Build Streamlit apps in Amazon SageMaker Studio (2023-04-11)](https://aws.amazon.com/blogs/machine-learning/build-streamlit-apps-in-amazon-sagemaker-studio/)
  * [LangChain](https://python.langchain.com/docs/get_started/introduction.html) - A framework for developing applications powered by language models.
  * [Streamlit](https://streamlit.io/) - A faster way to build and share data apps
  * [rag-with-amazon-kendra](https://github.com/ksmin23/rag-with-amazon-kendra) - Question Answering application with Large Language Models (LLMs) and Amazon Kendra
  * [rag-with-amazon-postgresql-using-pgvector](https://github.com/aws-samples/rag-with-amazon-postgresql-using-pgvector) - Question Answering application with Large Language Models (LLMs) and Amazon Aurora Postgresql
  * [rag-with-amazon-opensearch](https://github.com/ksmin23/rag-with-amazon-opensearch) - Question Answering application with Large Language Models (LLMs) and Amazon OpenSearch Service with [LangChain](https://www.langchain.com/)
  * [rag-with-amazon-opensearch-serverless](https://github.com/aws-samples/rag-with-amazon-opensearch-serverless) - Question Answering application with Large Language Models (LLMs) and Amazon OpenSearch Service Serverless with [LangChain](https://www.langchain.com/)
  * [rag-with-haystack-and-amazon-opensearch](https://github.com/ksmin23/rag-with-haystack-and-amazon-opensearch) - Question Answering application with Large Language Models (LLMs) and Amazon OpenSearch Service with [Haystack](https://haystack.deepset.ai/)
  * [rag-with-amazon-documentdb-and-sagemaker](https://github.com/aws-samples/aws-kr-startup-samples/tree/main/gen-ai/rag-with-amazon-documentdb-and-sagemaker) - Question Answering application with Large Language Models (LLMs) and Amazon DocumentDB(with MongoDB Compatibility) with [LangChain](https://www.langchain.com/)

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.
