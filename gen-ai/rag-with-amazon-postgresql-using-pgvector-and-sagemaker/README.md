# QA with LLM and RAG (Retrieval Augmented Generation)

This project is a Question Answering application with Large Language Models (LLMs) and Amazon Aurora Postgresql using [pgvector](https://github.com/pgvector/pgvector). An application using the RAG(Retrieval Augmented Generation) approach retrieves information most relevant to the user’s request from the enterprise knowledge base or content, bundles it as context along with the user’s request as a prompt, and then sends it to the LLM to get a GenAI response.

LLMs have limitations around the maximum word count for the input prompt, therefore choosing the right passages among thousands or millions of documents in the enterprise, has a direct impact on the LLM’s accuracy.

In this project, Amazon Aurora Postgresql with pgvector is used for knowledge base.

The overall architecture is like this:

![rag_with_pgvector_arch](./cdk_stacks/rag_with_pgvector_arch.svg)

### Overall Workflow

1. Deploy the cdk stacks (For more information, see [here](./cdk_stacks/README.md)).
   - A SageMaker Studio in a private VPC.
   - A SageMaker Endpoint for text generation.
   - A SageMaker Endpoint for generating embeddings.
   - An Amazon Aurora Postgresql cluster for storing embeddings.
   - Aurora Postgresql cluster's access credentials (username and password) stored in AWS Secrets Mananger as a name such as `RAGPgVectorStackAuroraPostg-xxxxxxxxxxxx`.
2. Open SageMaker Studio and then open a new **System terminal**.
3. Run the following commands on the terminal to clone the code repository for this project:
   ```
   git clone --depth=1 https://github.com/aws-samples/rag-with-amazon-postgresql-using-pgvector.git
   ```
4. Open `data_ingestion_to_pgvector.ipynb` notebook and Run it. (For more information, see [here](./data_ingestion_to_vectordb/data_ingestion_to_pgvector.ipynb))
5. Run Streamlit application. (For more information, see [here](./app/README.md))

### References

  * [Leverage pgvector and Amazon Aurora PostgreSQL for Natural Language Processing, Chatbots and Sentiment Analysis (2023-07-13)](https://aws.amazon.com/blogs/database/leverage-pgvector-and-amazon-aurora-postgresql-for-natural-language-processing-chatbots-and-sentiment-analysis/)
  * [Accelerate HNSW indexing and searching with pgvector on Amazon Aurora PostgreSQL-compatible edition and Amazon RDS for PostgreSQL (2023-11-06)](https://aws.amazon.com/blogs/database/accelerate-hnsw-indexing-and-searching-with-pgvector-on-amazon-aurora-postgresql-compatible-edition-and-amazon-rds-for-postgresql/)
  * [Optimize generative AI applications with pgvector indexing: A deep dive into IVFFlat and HNSW techniques (2024-03-15)](https://aws.amazon.com/blogs/database/optimize-generative-ai-applications-with-pgvector-indexing-a-deep-dive-into-ivfflat-and-hnsw-techniques/)
  * [Improve the performance of generative AI workloads on Amazon Aurora with Optimized Reads and pgvector (2024-02-09)](https://aws.amazon.com/blogs/database/accelerate-generative-ai-workloads-on-amazon-aurora-with-optimized-reads-and-pgvector/)
  * [Building AI-powered search in PostgreSQL using Amazon SageMaker and pgvector (2023-05-03)](https://aws.amazon.com/blogs/database/building-ai-powered-search-in-postgresql-using-amazon-sagemaker-and-pgvector/)
  * [Build Streamlit apps in Amazon SageMaker Studio (2023-04-11)](https://aws.amazon.com/blogs/machine-learning/build-streamlit-apps-in-amazon-sagemaker-studio/)
  * [Quickly build high-accuracy Generative AI applications on enterprise data using Amazon Kendra, LangChain, and large language models (2023-05-03)](https://aws.amazon.com/blogs/machine-learning/quickly-build-high-accuracy-generative-ai-applications-on-enterprise-data-using-amazon-kendra-langchain-and-large-language-models/)
    * [(github) Amazon Kendra Retriver Samples](https://github.com/aws-samples/amazon-kendra-langchain-extensions/tree/main/kendra_retriever_samples)
  * [Question answering using Retrieval Augmented Generation with foundation models in Amazon SageMaker JumpStart (2023-05-02)](https://aws.amazon.com/blogs/machine-learning/question-answering-using-retrieval-augmented-generation-with-foundation-models-in-amazon-sagemaker-jumpstart/)
  * [Use proprietary foundation models from Amazon SageMaker JumpStart in Amazon SageMaker Studio (2023-06-27)](https://aws.amazon.com/blogs/machine-learning/use-proprietary-foundation-models-from-amazon-sagemaker-jumpstart-in-amazon-sagemaker-studio/)
  * [LangChain](https://python.langchain.com/docs/get_started/introduction.html) - A framework for developing applications powered by language models.
  * [Streamlit](https://streamlit.io/) - A faster way to build and share data apps
  * [rag-with-amazon-kendra-and-sagemaker](https://github.com/aws-samples/aws-kr-startup-samples/tree/main/gen-ai/rag-with-amazon-kendra-and-sagemaker) - Question Answering application with Large Language Models (LLMs) and Amazon Kendra
  * [rag-with-amazon-opensearch-and-sagemaker](https://github.com/aws-samples/rag-with-amazon-opensearch-and-sagemaker) - Question Answering application with Large Language Models (LLMs) and Amazon OpenSearch Service
  * [rag-with-amazon-opensearch-serverless](https://github.com/aws-samples/rag-with-amazon-opensearch-serverless) - Question Answering application with Large Language Models (LLMs) and Amazon OpenSearch Serverless Service
  * [Pgvector changelog](https://github.com/pgvector/pgvector/blob/master/CHANGELOG.md#040-2023-01-11)
    > Increased max dimensions for vector from 1024 to 16000<br/>
    > Increased max dimensions for index from 1024 to 2000

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.
