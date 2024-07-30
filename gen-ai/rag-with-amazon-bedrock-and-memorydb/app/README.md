## Run the Streamlit application in Studio

Now we’re ready to run the Streamlit web application for our question answering bot.

SageMaker Studio provides a convenient platform to host the Streamlit web application. The following steps describes how to run the Streamlit app on SageMaker Studio. Alternatively, you could also follow the same procedure to run the app on Amazon EC2 instance or Cloud9 in your AWS Account.

1. Open Studio and then open a new **System terminal**.
2. Run the following commands on the terminal to clone the code repository for this post and install the Python packages needed by the application:
   ```
   git clone --depth=1 https://github.com/aws-samples/rag-with-amazon-bedrock-and-memorydb.git
   cd rag-with-amazon-bedrock-and-memorydb/app
   python -m venv .env
   source .env/bin/activate

   # install LangChain MemoryDB package
   git clone --depth=1 https://github.com/aws-samples/amazon-memorydb-for-redis-samples.git
   cd ./amazon-memorydb-for-redis-samples/tutorials/langchain-memorydb
   pip install . # (NOTE: There is a DOT at the end.)
   cd -
   pip install -U -r requirements.txt
   ```
3. In the shell, set the following environment variables with the values that are available from the CloudFormation stack output.
   <pre>
   export AWS_REGION="us-east-1"
   export MEMORYDB_SECRET_NAME="{<i>MemoryDB-Secret-Name</i>}"
   export REDIS_HOST="clustercfg.<i>{memorydb-cluster-name}</i>.memorydb.<i>{region}</i>.amazonaws.com"
   export INDEX_NAME="idx:vss-mm"
   export BEDROCK_MODEL_ID="anthropic.claude-v2:1"
   </pre>
   :information_source: `INDEX_NAME` can be found in [data ingestion to vectordb](../data_ingestion_to_vectordb/data_ingestion_to_memorydb.ipynb) step.
4. When the application runs successfully, you’ll see an output similar to the following (the IP addresses you will see will be different from the ones shown in this example). Note the port number (typically `8501`) from the output to use as part of the URL for app in the next step.
   ```
   sagemaker-user@studio$ streamlit run app.py

   Collecting usage statistics. To deactivate, set browser.gatherUsageStats to False.

   You can now view your Streamlit app in your browser.

   Network URL: http://169.255.255.2:8501
   External URL: http://52.4.240.77:8501
   ```
5. You can access the app in a new browser tab using a URL that is similar to your Studio domain URL. For example, if your Studio URL is `https://d-randomidentifier.studio.us-east-1.sagemaker.aws/jupyter/default/lab?` then the URL for your Streamlit app will be `https://d-randomidentifier.studio.us-east-1.sagemaker.aws/jupyter/default/proxy/8501/app` (notice that `lab` is replaced with `proxy/8501/app`). If the port number noted in the previous step is different from 8501 then use that instead of 8501 in the URL for the Streamlit app.

The following screenshot shows the app with a couple of user questions. (e.g., `What are some reasons a highly regulated industry should pick MemoryDB?`)

![qa-with-llm-and-rag](./qa-with-llm-and-rag.png)

## References

  * [Amazon MemoryDB for Redis Samples](https://github.com/aws-samples/amazon-memorydb-for-redis-samples)
  * [Vector search - Amazon MemoryDB for Redis](https://docs.aws.amazon.com/memorydb/latest/devguide/vector-search.html)
  * [Build Streamlit apps in Amazon SageMaker Studio (2023-04-11)](https://aws.amazon.com/blogs/machine-learning/build-streamlit-apps-in-amazon-sagemaker-studio/)
  * [Use proprietary foundation models from Amazon SageMaker JumpStart in Amazon SageMaker Studio (2023-06-27)](https://aws.amazon.com/blogs/machine-learning/use-proprietary-foundation-models-from-amazon-sagemaker-jumpstart-in-amazon-sagemaker-studio/)
  * [Amazon Bedrock - Inference parameters for foundation models](https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters.html)
  * [LangChain](https://python.langchain.com/docs/get_started/introduction.html) - A framework for developing applications powered by language models.
  * [LangChain Providers - AWS](https://python.langchain.com/docs/integrations/platforms/aws/) - The `LangChain` integrations related to `Amazon AWS` platform.
  * [Streamlit](https://streamlit.io/) - A faster way to build and share data apps
