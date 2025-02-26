
# Backend forVideo Maker with Amazon Bedrock(Nova Reel)

## Prerequisites
- AWS CDK latest version
- AWS account and credentials

## Setup

1. Clone the repository:
```bash
git clone https://github.com/aws-samples/aws-kr-startup-samples.git
cd aws-kr-startup-samples
git sparse-checkout init --cone
git sparse-checkout set gen-ai/video-maker-with-nova-reel
```

2. Create virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: `.venv\Scripts\activate`
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure AWS credentials:
```bash
aws configure
```

## Deployment

1. Synthesize CloudFormation template:
```bash
cdk synth
```

2. Deploy stack:
```bash
cdk deploy
```

## Project Structure
```
backend
├── README.md
├── app.py
├── cdk.context.json
├── cdk.json
├── lambda
│   └── api
│       ├── delete-video
│       │   └── index.py
│       ├── generate-video
│       │   ├── index.py
│       │   └── requirements.txt
│       ├── get-video
│       │   └── index.py
│       ├── list-video
│       │   └── index.py
│       ├── prompt-assist
│       └── status-video
│           └── index.py
├── requirements.txt
└── stacks
    └── video_maker_with_nova_reel_stack.py
```

## Architecture
- Amazon API Gateway for API management
- AWS Lambda for serverless execution
- Amazon S3 for media storage
- Amazon Bedrock (Nova Reel) for video generation
- AWS IAM roles for service permissions

## Cleanup
```bash
cdk destroy
```
