# Style Backend

This project uses AWS CDK to construct the style backend infrastructure for a fashion styling application.

## Prerequisites

- Install and configure AWS CLI
- Install Node.js and npm
- Install Python 3.8 or higher
- Install AWS CDK (`npm install -g aws-cdk`)

## Initial Setup

```bash
# Run CDK bootstrap (if using AWS account for the first time)
cdk bootstrap

# Create and activate Python virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

## Project Structure

```
.
├── app.py                  # Main CDK application entry point
├── byoc                    # Bring Your Own Container resources
│   └── facechain           # FaceChain model container resources
├── lambda                  # Lambda function source code
│   ├── apis                # API handler functions
│   ├── facechain_codebuild # FaceChain build functions
│   └── image-processing    # Image processing functions
└── stacks                  # CDK stack definitions
    ├── apigateway          # API Gateway stack
    ├── byoc                # BYOC stack
    ├── cognito             # Cognito user authentication stack
    ├── ddb                 # DynamoDB tables stack
    ├── facechain           # FaceChain model stack
    ├── lambdas             # Lambda functions stack
    └── s3                  # S3 bucket stack
```

## Stacks

The project consists of the following stacks:

### 1. BYOC (Bring Your Own Container) Stacks
- Infrastructure for container management and deployment
- Key components:
  - FaceChain ECR Stack: Container registry for FaceChain model
  - FaceChain CodeBuild Stack: Build pipeline for FaceChain container

### 2. FaceChain Stacks
- Infrastructure for FaceChain model deployment and management
- Key components:
  - SageMaker Endpoint Stack: Model deployment endpoint
  - CodeBuild Trigger Stack: Automated build triggers
  - CodeBuild Status Checker Stack: Build status monitoring

### 3. API Gateway Stacks
- REST API endpoint management and configuration
- Key components:
  - Image Upload API (/apis/images/upload)
  - Image Retrieval API (/apis/images/{userId})
  - User Agreement API (/agree)
  - CORS configuration and permission management
  - Lambda integration

### 4. Cognito Stacks
- User authentication and authorization management
- Key components:
  - User Pool configuration
  - Client application settings
  - Domain configuration

### 5. DynamoDB Stacks
- Data storage management
- Key tables:
  - Process Table: Image processing status management
  - Display Table: Image display information management
  - Display History Table: Image display history tracking
  - Base Resource Table: Base resource information storage
  - User Agreement Table: User consent information management

### 6. Lambda Stacks
- Serverless function management
- Key functions:
  - Image Processing Lambdas:
    - Face Crop Lambda: Face image cropping processing
    - Face Swap Lambda: Face swapping processing
    - Face Swap Completion Lambda: Face swap completion handling
  - S3 event-based automated processing configuration

### 7. S3 Stacks
- Object storage management
- Key features:
  - Image storage configuration
  - CORS settings
  - Bucket policy management
  - Event notification setup

## Deployment Prerequisites

Before deploying this application:

1. Configure the `s3_base_bucket_name` in your `cdk.context.json` file:
   ```json
   {
     "s3_base_bucket_name": "your-unique-bucket-name"
   }
   ```

2. It is recommended to deploy this application in the **us-west-2** region for optimal performance and compatibility.

## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

## How to deploy

This project is set up like a standard Python project. The initialization
process also creates a virtualenv within this project, stored under the `.venv`
directory.  To create the virtualenv it assumes that there is a `python3`
(or `python` for Windows) executable in your path with access to the `venv`
package. If for any reason the automatic creation of the virtualenv fails,
you can create the virtualenv manually.

To manually create a virtualenv on MacOS and Linux:

```
$ python3 -m venv .venv
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .venv/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```
% .venv\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```
$ pip install -r requirements.txt
```

At this point you can now synthesize the CloudFormation template for this code.

```
$ cdk synth
```

To add additional dependencies, for example other CDK libraries, just add
them to your `setup.py` file and rerun the `pip install -r requirements.txt`
command.
