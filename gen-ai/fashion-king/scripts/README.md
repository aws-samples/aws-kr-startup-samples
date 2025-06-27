# Test Image Upload Scripts

This directory contains scripts for uploading test images to S3.

## Script Descriptions

### upload_test_images.py
- Base upload script written in Python
- Uploads all image files from a directory to S3
- Usage:
  ```bash
  python3 upload_test_images.py --bucket <bucket-name> --local-path <local-path> --s3-prefix <s3-prefix>
  ```

### upload_test_person.sh
- Shell script for uploading test-person-image.png
- Usage:
  ```bash
  ./upload_test_person.sh
  ```

## Prerequisites

1. AWS CLI must be installed
2. AWS credentials must be configured
3. test-person-image.png file must be in the same directory as the script

## Usage Example

```bash
# Upload test-person-image.png
cd scripts
./upload_test_person.sh
```

## Notes

- S3 bucket name is taken from s3_base_bucket_name in cdk.context.json
- Default S3 prefix is 'images/generative-stylist/faces'
- Upon successful upload, the S3 path for each file will be displayed 