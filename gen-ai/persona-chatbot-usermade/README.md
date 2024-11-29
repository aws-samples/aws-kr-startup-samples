# Persona Chatbot Using Amazon Bedrock (Usermade version)
![Architecture](./images/user-made-1.png)

A Streamlit-based chatbot application that **creates custom persona chatbots** using Amazon Bedrock's Claude 3 model.
![Demo](./images/user-made-2.png)

## Prerequisites
- AWS CDK latest version
- AWS account and credentials
- Amazon Bedrock access (Claude 3 model)
- Docker for container builds

## Setup

1. Clone the repository:
```bash
git clone https://github.com/aws-samples/aws-kr-startup-samples.git
cd aws-kr-startup-samples
git sparse-checkout init --cone
git sparse-checkout set gen-ai/persona-chatbot-usermade
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
persona-chatbot-usermade/
├── app/
│   ├── app.py             # Streamlit application
│   ├── config/            # Character configuration
│   └── templates/         # Prompt templates
├── persona_chatbot_usermade/
│   └── persona_chatbot_usermade_stack.py  # CDK stack
```

## Architecture
- Amazon ECS (Fargate) hosting Streamlit application
- Application Load Balancer for public access
- Amazon Bedrock (Claude 3) for character interactions
- AWS IAM roles for service permissions

## Usage
1. Access application through ALB URL (provided in stack outputs)
2. Create a character:
   - Enter character name
   - Provide character description
   - Set default greeting
   - Add example dialogues
3. Start chatting with created character

## Cleanup
```bash
cdk destroy
```

## License
This project is licensed under the MIT License - see LICENSE file for details.