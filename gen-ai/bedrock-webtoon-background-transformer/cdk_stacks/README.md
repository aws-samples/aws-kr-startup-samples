This infrastructure stack enables webtoon background transformation using Amazon Bedrock's SDXL model. Starting from existing webtoon backgrounds, it allows artists to generate variations with different atmospheres while preserving the original art style. The stack deploys a secure environment with VPC endpoints and SageMaker notebooks for image-to-image processing through Amazon Bedrock.

Following resources will get created and deployed:
- VPC with 2 Availability Zones and 1 NAT Gateway
- Security Groups for VPC Endpoints and SageMaker
- VPC Endpoints (for Bedrock Runtime, SageMaker API, and SageMaker Runtime)
- AWS IAM role with Bedrock access permissions
- SageMaker Notebook Instance

The cdk.json file tells the CDK Toolkit how to execute your app.

This project is set up like a standard Python project. The initialization process also creates a virtualenv within this project, stored under the .venv directory. To create the virtualenv it assumes that there is a python3 (or python for Windows) executable in your path with access to the venv package. If for any reason the automatic creation of the virtualenv fails, you can create the virtualenv manually.

To manually create a virtualenv on MacOS and Linux:

```
git clone https://github.com/aws-samples/aws-kr-startup-samples.git
cd aws-kr-startup-samples
git sparse-checkout init --cone
git sparse-checkout set genai/bedrock-webtoon-background-transformer

python -m venv .venv
```

After the init process completes and the virtualenv is created, you can use the following step to activate your virtualenv.

```
source .venv/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```
.venv\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```
pip install -r requirements.txt
```

Now this point you can now synthesize the CloudFormation template for this code.

```
export CDK_DEFAULT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
export CDK_DEFAULT_REGION=$(aws configure get region)
cdk synth --all
```

Now you can deploy all the CDK stacks at once like this:

```
cdk deploy --require-approval never --all
```

Note: The deployment may take 10-15 minutes to complete.