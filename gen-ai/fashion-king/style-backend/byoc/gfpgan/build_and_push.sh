#!/usr/bin/env bash

# Name of algo -> ECR
ecr_repo_name=bedrock-x-gfpgan

#make serve executable
chmod +x src/serve
account=$(aws sts get-caller-identity --query Account --output text)

# Region, defaults to us-west-2
region=$(aws configure get region)

fullname="${account}.dkr.ecr.${region}.amazonaws.com/${ecr_repo_name}:latest"

echo $account
echo $region
echo $fullname

# If the repository doesn't exist in ECR, create it.
aws ecr describe-repositories --repository-names "${ecr_repo_name}" > /dev/null 2>&1
if [ $? -ne 0 ]
then
    aws ecr create-repository --repository-name "${ecr_repo_name}" > /dev/null
fi

# Get the login command from ECR and execute it directly (for AWS ML images)
aws ecr get-login-password --region ${region} | docker login --username AWS --password-stdin 763104351884.dkr.ecr.${region}.amazonaws.com

docker build  -t ${ecr_repo_name} .

# Get the login command from ECR and execute it directly (for Account's images)
aws ecr get-login-password --region ${region} | docker login --username AWS --password-stdin ${fullname}

docker tag ${ecr_repo_name} ${fullname}

docker push ${fullname}
