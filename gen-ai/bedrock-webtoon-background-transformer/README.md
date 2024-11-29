# Transforming Webtoon Background Atmosphere Using Amazon Bedrock

This project provides sample code that uses Stable Diffusion XL (SDXL) model on Amazon Bedrock to transform the atmosphere of webtoon background image. It can be used to modify weather conditions or time of day for the original webtoon image.

## Features

- Transform the atmosphere of existing webtoon background images:
    - Generate various weather conditions (rain, snow, fog, sunshine)
    - Create different time-of-day variations (day, night)
    - Produce seasonal variations (spring, summer, autumn, winter)

- Maintain authentic webtoon art style:
    - Preserve original background art style
    - Generate high-quality output suitable for production use

## Architecture
- **Amazon Bedrock**: Provides access to SDXL image-to-image capability to generate webtoon backgrounds with different atmospheric conditions
- **VPC Endpoints**: Enable secure communication between Amazon Bedrock and SageMaker Studio within VPC without internet access
- **Amazon SageMaker Studio**: Provides development environment for running Jupyter notebooks to transform webtoon backgrounds and visualize results


## Setup Instructions

### Prerequisites
- AWS CLI installed and configured with appropriate credentials
- AWS CDK CLI installed (npm install -g aws-cdk)
- Python 3.7+
- Git
- Sufficient AWS permissions to create required resources
- Access enabled for Amazon Bedrock SDXL model ([Enable Model Access Guide](https://docs.aws.amazon.com/ko_kr/bedrock/latest/userguide/model-access-modify.html))

### Setup Steps
1. Deploy the cdk stacks (For detailed deployment instructions, refer to [here](cdk_stacks/README.md))
2. Open SageMaker Notebook and then open a new terminal
3. Clone the project repository:
    ```
    git clone --depth=1 https://github.com/aws-samples/aws-kr-startup-samples.git
    cd aws-kr-startup-samples
    git sparse-checkout init --cone
    git sparse-checkout set gen-ai/bedrock-webtoon-background-transformer
    ```
4. Open and run the `bedrock-webtoon-background-transformer.ipynb` notebook.