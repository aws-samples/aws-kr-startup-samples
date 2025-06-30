#!/bin/bash

# S3 bucket name
BUCKET_NAME=$(jq -r '.s3_base_bucket_name' ../style-backend/cdk.context.json)

# User information
USER_ID="test-user"
STYLE="casual"
GENDER="male"

# Test image file name
FILE_NAME="test-1234-4567-casual-male.png"

# S3 prefix
S3_PREFIX="images/generative-stylist/faces"

# Check if file exists
if [ ! -f "$FILE_NAME" ]; then
    echo "Error: File $FILE_NAME does not exist"
    exit 1
fi

# Install required Python packages
echo "Installing required Python packages..."
pip3 install boto3

# Execute Python script
python3 upload_test_images.py \
    --bucket "$BUCKET_NAME" \
    --file-name "$FILE_NAME" \
    --s3-prefix "$S3_PREFIX" \
    --user-id "$USER_ID" \
    --style "$STYLE" \
    --gender "$GENDER" 