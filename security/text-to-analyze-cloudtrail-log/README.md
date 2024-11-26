# Text Analysis of CloudTrail Logs using Amazon Bedrock

This project demonstrates how to analyze AWS CloudTrail logs using Amazon Bedrock's large language models. It sets up the required AWS infrastructure using AWS CDK and provides a SageMaker notebook for analysis.

![Result Sample 1](/security/text-to-analyze-cloudtrail-log/images/result_sample_1.png)
![Result Sample 2](/security/text-to-analyze-cloudtrail-log/images/result_sample_2.png)
![Result Sample 3](/security/text-to-analyze-cloudtrail-log/images/result_sample_3.png)
## Architecture Overview

![Architecture Diagram](/security/text-to-analyze-cloudtrail-log/images/architect.png)

The project creates the following AWS resources:

- S3 bucket for storing CloudTrail logs with lifecycle management
- CloudTrail trail configured for multi-region logging
- VPC with private subnets for SageMaker notebook instance
- VPC endpoints for secure access to AWS services
- SageMaker notebook instance in the VPC
- Glue database and table for querying CloudTrail logs with Athena
- Required IAM roles and security groups

## Prerequisites

Before getting started, ensure you have:

- AWS CLI installed and configured with appropriate credentials
- AWS CDK CLI installed (npm install -g aws-cdk)
- Python 3.7 or higher installed
- Git installed
- Sufficient AWS permissions to create required resources
- Amazon Bedrock access enabled in your AWS account

## Initial Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/aws-samples/aws-kr-startup-samples.git
   cd aws-kr-startup-samples
   git sparse-checkout init --cone
   git sparse-checkout set security/text-to-analyze-cloudtrail-log
   ```

2. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows, use: .venv\Scripts\activate
   ```

3. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure your AWS CLI profile:
   ```bash
   aws configure
   ```

5. Update the bucket name in `cdk_stacks/text_to_analyze_cloudtrail_log_stack.py`:
   Change the `bucket_name` variable to a globally unique name.

6. Synthesize the CloudFormation template:
   ```bash
   cdk synth --all
   ```

7. Deploy the CDK stack:
   ```bash
   cdk deploy --require-approval never --all
   ```

   Note: The deployment may take 10-15 minutes to complete.

8. After deployment, note the following outputs:
   - CloudTrail Logs S3 Bucket Name
   - SageMaker Notebook Instance Name 
   - Glue Database Name

## Using the SageMaker Notebook

1. Navigate to the SageMaker console in AWS
2. Find the notebook instance named "text-to-analyze-cloudtrail-logs"
3. Click "Open JupyterLab"
4. Create a new notebook using the Python 3 kernel
5. You can now start analyzing CloudTrail logs using:
   - Athena queries through the AWS SDK
   - Amazon Bedrock for text analysis
   - Python data analysis libraries

## Cost Considerations

This solution includes several AWS services that incur costs:

- SageMaker notebook instance (ml.t3.2xlarge)
- VPC NAT Gateway
- S3 storage for CloudTrail logs
- CloudTrail logging
- Athena queries
- Amazon Bedrock API usage

To minimize costs:
- Stop the SageMaker notebook when not in use
- Monitor CloudTrail log storage and clean up old logs
- Use efficient Athena queries
- Be mindful of Bedrock API usage

## Security Considerations

This solution implements several security best practices:

- VPC isolation for SageMaker notebook
- VPC endpoints for secure service access
- No direct internet access from notebook
- S3 bucket encryption and versioning
- CloudTrail multi-region logging
- IAM roles with least privilege
- Security groups with minimal access

## Cleanup

To avoid ongoing charges, delete the resources when no longer needed:

1. Delete the CloudTrail logs from the S3 bucket
2. Run the following command to destroy the stack:
   ```bash
   cdk destroy
   ```

Note: The S3 bucket has a RETAIN removal policy and must be manually deleted after the stack is destroyed.

## Troubleshooting

Common issues and solutions:

1. Notebook fails to start
   - Check VPC endpoints are properly configured
   - Verify security group rules
   - Ensure IAM role has required permissions

2. Cannot access CloudTrail logs
   - Verify S3 bucket permissions
   - Check Glue table configuration
   - Confirm CloudTrail is logging correctly

3. Athena queries fail
   - Validate Glue database and table setup
   - Check query syntax and table schema
   - Ensure proper S3 bucket access

## Extending the Analysis

The provided Jupyter notebook code can be freely modified to perform additional analysis:

1. Custom Analysis Patterns
   - Modify queries to focus on specific AWS services or event types
   - Create visualizations of access patterns and trends
   - Build custom security monitoring dashboards

2. Advanced Analytics
   - Implement anomaly detection using machine learning
   - Analyze user behavior patterns
   - Track resource usage and cost optimization opportunities

3. Integration Options
   - Export analysis results to other monitoring tools
   - Set up automated reporting workflows
   - Create custom alerting based on analysis findings

The flexible architecture allows you to:
- Customize Athena queries for your specific use cases
- Leverage Bedrock's AI capabilities for deeper insights
- Add new analysis notebooks as needed
- Integrate with other AWS services for expanded functionality

Feel free to modify the provided code examples to suit your organization's needs and security requirements.

