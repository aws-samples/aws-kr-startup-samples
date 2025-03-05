# Video Maker with Amazon Bedrock(Nova Reel)

## Project Overview
This project is a video creation automation system using Amazon Bedrock(Nova Reel). It is built using AWS CDK for infrastructure and consists of frontend and backend components.

![screenshot1](./docs/images/video-generation-service-1.jpeg)
You can get help from “Generative AI Assist” to get suggested prompts based on best practices from Amazon Nova Reel.
![screenshot1](./docs/images/video-generation-service-2.jpeg)
![screenshot2](./docs/images/video-generation-service-3.jpeg)

## System Architecture
- Frontend: React-based web application
- Backend: Serverless architecture using AWS CDK
  - AWS Lambda
  - Amazon S3
  - Other AWS services

## Installation and Deployment

### Backend Deployment
Follow these steps to deploy the backend:

```bash
# Navigate to backend directory
cd backend

# Install required dependencies
pip install -r requirements.txt

# Deploy using AWS CDK
cdk deploy
```

### Frontend Deployment
Follow these steps to deploy the frontend:

```bash
# Navigate to frontend directory
cd frontend

# change API Gateway Endpoint from CDK Outputs(VideoMakerWithNovaReelStack.VideoMakerWithNovaReelAPIGateway)
vi .env
REACT_APP_API_HOST=https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/prod

# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Deploy to production
npm run deploy

# Start on Localhost
npm start
```

## Prerequisites
- Node.js 16.x or higher
- Python 3.8 or higher
- AWS CLI configured
- AWS CDK CLI installed

## Features
- Automated video creation
- Cloud-based processing
- Scalable architecture
- Easy deployment process

## Configuration
Make sure to set up your AWS credentials and configure the necessary environment variables before deployment.

## Support
For support, please open an issue in the GitHub repository.