# AWS WAF v2 Log Analysis with Streamlit and Amazon Bedrock

This project demonstrates how to create a Streamlit application that uses Amazon Bedrock's Claude 3 model to analyze AWS WAF v2 logs. Users can ask questions about their WAF logs in natural language, and the application generates SQL queries to retrieve relevant information from Amazon Athena.

## Architecture

![Architecture](./images/architecture.png)

1. User interacts with the Streamlit web application.
2. The application sends the user's query to Amazon Bedrock's Claude 3 model.
3. Claude 3 generates an SQL query based on the user's question.
4. The generated SQL query is executed on Amazon Athena.
5. Results are returned to the Streamlit application and displayed to the user.

## Prerequisites

Before you begin, ensure you have the following:

- An AWS account with access to Amazon Bedrock and Amazon Athena
- Python 3.7 or later
- AWS CLI configured with appropriate credentials

## Setup

1. Clone this repository:
   ```
   git clone https://github.com/aws-samples/aws-kr-startup-samples.git
   cd aws-kr-startup-samples
   git sparse-checkout init --cone
   git sparse-checkout set gen-ai/bedrock-txt-to-query-for-athena-chatbot
   ```

2. Install the required Python packages:
   ```
   pip install -r requirements.txt
   ```

3. Update the `region_name` in the script if your Bedrock and Athena resources are in a different region.

## Running the Application

To run the Streamlit application, use the following command:

```
streamlit run app.py
```

The application will open in your default web browser. You can then enter questions about your AWS WAF v2 logs, and the application will generate SQL queries and display the results.

## Code Explanation

- The script uses Streamlit to create a web interface for user interaction.
- It initializes a ChatBedrock client to communicate with Amazon Bedrock's Claude 3 model.
- The chat history is maintained using Streamlit's session state.
- When a user enters a question, it's sent to Claude 3 along with the chat history.
- Claude 3 generates a response, which is typically an SQL query or an explanation.
- The response is displayed in the Streamlit interface.

## Customization

- Modify the `prompts.txt` file to adjust the system message for Claude 3.
- Update the `model_kwargs` in the ChatBedrock initialization to change model parameters like temperature or max tokens.
- Extend the script to execute the generated SQL queries on Athena and display the results.

## Security

This application uses AWS credentials to access Bedrock and Athena. Ensure that you're following AWS security best practices, including:

- Using IAM roles with least privilege
- Not hardcoding AWS credentials in the code
- Implementing proper error handling and logging

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Citations
* https://docs.aws.amazon.com/waf/latest/developerguide/logging-fields.html
* https://docs.aws.amazon.com/athena/latest/ug/waf-logs.html
* https://github.com/aws-samples/waf-log-sample-athena-queries
