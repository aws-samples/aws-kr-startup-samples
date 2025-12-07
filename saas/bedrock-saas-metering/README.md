# Bedrock Multi-Tenant SaaS with Token Metering

This project builds a system for metering Amazon Bedrock token usage in a multi-tenant SaaS environment using AWS CDK.

[한국어 문서](README.ko.md) | English

## 🏗️ SaaS Structure Overview

This sample is implemented with a **simple and practical SaaS structure**:

### 📋 Core Concepts
**Fixed Model Usage**
- Uses a fixed model for all requests (in production, it's recommended to provide users with various model selection options)
- Tenants only need to input prompts

**Billing-Focused Design**
- Token usage is collected for SaaS provider billing purposes
- Only response text is provided to tenants
- Usage analysis through CloudWatch Logs and Athena

**Simple API**
```javascript
// Tenant perspective: Simple prompt input
{
  "prompt": "Please explain about AWS."
}

// Response: Text only
{
  "response": "AWS is a cloud computing platform provided by Amazon..."
}
```

## 📁 Project Structure

```
bedrock-saas-metering/
├── bin/
│   └── app.ts                           # CDK app entry point
├── lib/
│   ├── bedrock-metering-stack.ts        # Main API stack (Cognito, API Gateway, Lambda)
│   └── metering-analytics-stack.ts      # Analytics stack (S3, Glue, Athena)

├── package.json                         # Dependencies and scripts
├── cdk.json                            # CDK configuration
├── tsconfig.json                       # TypeScript configuration
├── .gitignore                          # Git ignore file
└── README.md                           # This file
```

## 🏛️ Architecture Overview

### Key Components

1. **Authentication and Authorization**
   - Amazon Cognito User Pool: Tenant-specific user authentication
   - Tenant identification through JWT tokens

2. **API Services**
   - API Gateway: RESTful API endpoints
   - Lambda Function: Bedrock calls and token metering
   - Cognito Authorizer: JWT token-based authentication

3. **AI Services**
   - Amazon Bedrock: Uses Claude 3 Haiku model
   - Token usage tracking (input/output tokens)

4. **Metering and Analytics**
   - CloudWatch Logs: Real-time token usage logging
   - S3: Long-term log data storage
   - AWS Glue: Data catalog and schema management
   - Amazon Athena: SQL-based usage analysis

## 🚀 Deployment Method

### Prerequisites

```bash
# Check Node.js and npm installation
node --version
npm --version

# Configure AWS CLI
aws configure

# Install CDK CLI
npm install -g aws-cdk
```

### Project Setup

```bash
# Install dependencies
npm install

# Compile TypeScript
npm run build

# CDK bootstrap (first time only)
cdk bootstrap
```

### Deployment

```bash
# Deploy all stacks
npm run deploy

# Or deploy individual stacks
cdk deploy BedrockMeteringStack
cdk deploy MeteringAnalyticsStack
```

## 💻 Usage Instructions

**⚠️ Security Precautions**
- **Never hardcode**: Do not directly input actual deployment values (USER_POOL_ID, CLIENT_ID, API_URL, etc.) into code
- **Use environment variables**: For testing, use environment variables or separate configuration files (.env, config.json, etc.)
- **Git security**: Do not commit files containing sensitive information to Git
- **User-defined values**: All `<YOUR_XXX>` values in the examples below are values that users must set themselves

**⚠️ Important: Check configuration values after deployment completion**

When CDK deployment is complete, the following Outputs will be displayed in the terminal:
```
BedrockMeteringStack.UserPoolId = ap-northeast-2_AbCdEfGhI
BedrockMeteringStack.UserPoolClientId = 1a2b3c4d5e6f7g8h9i0j1k2l3m
BedrockMeteringStack.ApiGatewayUrl = https://abc123def4.execute-api.ap-northeast-2.amazonaws.com/prod/
```

In the usage examples below, replace the parts marked with angle brackets like `<USER_POOL_ID>`, `<USER_POOL_CLIENT_ID>`, `<API_GATEWAY_URL>` with the corresponding actual values from the Outputs above.

### 1. API Testing (CLI Commands)

#### Step 1: User Creation and Password Setup

**⚠️ User-configurable values:**
- `<USER_POOL_ID>`: Actual User Pool ID output after CDK deployment
- `<YOUR_USERNAME>`: Desired username (e.g., tenant1-user1, company-admin, etc.)
- `<YOUR_EMAIL>`: Actual email address
- `<YOUR_TENANT_ID>`: Tenant identifier (e.g., tenant-001, company-alpha, etc.)
- `<YOUR_TEMP_PASSWORD>`: Temporary password (8+ characters, uppercase+lowercase+numbers+special characters)
- `<YOUR_PASSWORD>`: Actual password to use (8+ characters, uppercase+lowercase+numbers+special characters)

```bash
# 1. Create user (temporary password)
aws cognito-idp admin-create-user \
  --user-pool-id <USER_POOL_ID> \
  --username <YOUR_USERNAME> \
  --user-attributes Name=email,Value=<YOUR_EMAIL> Name=custom:tenant_id,Value=<YOUR_TENANT_ID> \
  --temporary-password <YOUR_TEMP_PASSWORD> \
  --message-action SUPPRESS

# 2. Set permanent password (change temporary password to actual password)
aws cognito-idp admin-set-user-password \
  --user-pool-id <USER_POOL_ID> \
  --username <YOUR_USERNAME> \
  --password <YOUR_PASSWORD> \
  --permanent
```

#### Step 2: Login to Obtain Token

**⚠️ User-configurable values:**
- `<USER_POOL_CLIENT_ID>`: Actual Client ID output after CDK deployment
- `<YOUR_USERNAME>`: Username created in Step 1
- `<YOUR_PASSWORD>`: Password set in Step 1

```bash
# Cognito login (obtain access token)
aws cognito-idp initiate-auth \
  --client-id <USER_POOL_CLIENT_ID> \
  --auth-flow USER_PASSWORD_AUTH \
  --auth-parameters USERNAME=<YOUR_USERNAME>,PASSWORD=<YOUR_PASSWORD>
```

After executing the above command, copy the `IdToken` value from the response (contains tenant ID information):
```json
{
    "AuthenticationResult": {
        "AccessToken": "abCDefGhIjKlMnOpQrStUvWxYz123456...",
        "IdToken": "xyZ789AbCdEfGhIjKlMnOpQrStUvWx...",  // Copy this value (contains tenant ID)
        "ExpiresIn": 3600,
        "TokenType": "Bearer"
    }
}
```

#### Step 3: API Call Testing

**⚠️ User-configurable values:**
- `<API_GATEWAY_URL>`: Actual API Gateway URL output after CDK deployment
- `<YOUR_ID_TOKEN>`: IdToken value obtained in Step 2 (contains tenant ID)
- `<YOUR_PROMPT>`: Prompt content you want to test

```bash
# Bedrock API call (use the IdToken copied above)
curl -X POST <API_GATEWAY_URL>/bedrock/chat \
  -H "Authorization: Bearer <YOUR_ID_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "<YOUR_PROMPT>"
  }'
```

**💡 Complete example (all placeholders replaced with actual values):**
```bash
# Example: Complete command with all placeholders replaced with actual values
curl -X POST https://abc123def4.execute-api.ap-northeast-2.amazonaws.com/prod/bedrock/chat \
  -H "Authorization: Bearer xyZ789AbCdEfGhIjKlMnOpQrStUvWx..." \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Please explain about AWS Lambda."
  }'
```

**Expected response:**
```json
{
  "response": "AWS Lambda is a serverless computing service that allows you to run code without managing servers..."
}
```

### 2. Usage Analytics Queries

**⚠️ Important: Understanding Data Storage Method**

This system stores CloudWatch Logs data to S3 using **batch processing**:

- **Automatic Schedule**: Exports previous day's data to S3 daily at 1 AM UTC (10 AM KST)
- **Not Real-time Storage**: No data in S3 immediately after API calls
- **Athena Queries**: Requires data to be in S3 for querying

**To test immediately, manually execute data export:**

```bash
# 1. Check Lambda function name (check in AWS console after deployment or use command below)
aws lambda list-functions --query 'Functions[?contains(FunctionName, `LogProcessor`)].FunctionName' --output text

# 2. Manually execute log processing Lambda (exports today's data to S3)
aws lambda invoke \
  --function-name <LogProcessorFunctionName> \
  --payload '{}' \
  response.json

# 3. Check execution results
cat response.json

# 4. Verify data is stored in S3
aws s3 ls s3://<ANALYTICS_BUCKET_NAME>/logs/ --recursive
```

After deployment, you can execute the following queries in Athena.

**⚠️ User-configurable values:**
- `<YEAR>`, `<MONTH>`, `<DAY>`: Actual dates you want to query (e.g., '2025', '12', '07')
- `<YOUR_TENANT_ID>`: Actual tenant ID set in Step 1 (e.g., 'tenant-001', 'company-alpha')

**Query Testing in Athena:**

**🔍 How to Access Athena Console:**
1. Access AWS Athena Console
2. Select **Workgroup**: `bedrock-metering-workgroup`  
3. Select **Database**: `bedrock_metering_db`
4. Copy and execute the queries below

**1. Basic Data Verification:**
```sql
-- Check tenant list 
SELECT DISTINCT tenant_id 
FROM bedrock_metering_db.token_usage_logs 
WHERE year='2025' AND month='12' AND day='07' -- Change to actual date 
LIMIT 10;

-- Check models in use
SELECT DISTINCT model_id 
FROM bedrock_metering_db.token_usage_logs 
WHERE year='2025' AND month='12' AND day='07'-- Change to actual date
; 
```

**2. Main Analytics Queries:**

```sql
-- Daily usage analysis by tenant
SELECT 
    tenant_id,
    DATE(from_iso8601_timestamp(timestamp)) as usage_date,
    SUM(total_tokens) as total_tokens,
    COUNT(*) as request_count,
    AVG(total_tokens) as avg_tokens_per_request
FROM bedrock_metering_db.token_usage_logs
WHERE year = '2025' AND month = '12' AND day = '07'  -- Change to actual date
GROUP BY tenant_id, DATE(from_iso8601_timestamp(timestamp))
ORDER BY usage_date DESC, total_tokens DESC;

-- Hourly usage pattern analysis
SELECT 
    EXTRACT(hour FROM from_iso8601_timestamp(timestamp)) as usage_hour,
    tenant_id,
    COUNT(*) as request_count,
    SUM(total_tokens) as total_tokens,
    AVG(total_tokens) as avg_tokens_per_request
FROM bedrock_metering_db.token_usage_logs
WHERE year = '2025' AND month = '12' AND day = '07'  -- Change to actual date
GROUP BY EXTRACT(hour FROM from_iso8601_timestamp(timestamp)), tenant_id
ORDER BY usage_hour, total_tokens DESC;
```

## ⭐ Key Features

### Token Metering
- Real-time token usage tracking (for SaaS providers)
- Tenant-specific usage separation
- Separate recording of input/output tokens

### Security
- Cognito JWT token-based authentication
- Guaranteed tenant isolation
- API Gateway level access control

### Analytics and Reporting
- Real-time monitoring through CloudWatch Logs
- S3-based data lake
- SQL analysis through Athena
- Efficient queries based on partitioning

## 🧹 Cleanup

```bash
# Delete all resources
npm run destroy
```

## 📋 Notes

- Model access permissions are required in the corresponding region to use Bedrock models
- Consider additional security settings like VPC, WAF for actual production environments
- Monitor Athena query costs when processing large amounts of data
- Recommend setting usage limits and alarms per tenant
