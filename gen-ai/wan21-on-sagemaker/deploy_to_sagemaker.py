#!/usr/bin/env python3
"""
Deploy Wan2.1 14B model to Amazon SageMaker
"""

import boto3
import json
import time
from datetime import datetime

# Configuration
ALGORITHM_NAME = "wan21-14b-sagemaker-byoc"
MODEL_NAME = f"wan21-14b-model-{int(time.time())}"
ENDPOINT_CONFIG_NAME = f"wan21-14b-config-{int(time.time())}"
ENDPOINT_NAME = f"wan21-14b-endpoint-{int(time.time())}"

# Instance configuration - MUST use g6.2xlarge
INSTANCE_TYPE = "ml.g6.2xlarge"  # Latest GPU instance with L4 GPU, 24GB VRAM
INITIAL_INSTANCE_COUNT = 1

def get_image_uri():
    """Get the ECR image URI"""
    session = boto3.Session()
    account_id = session.client('sts').get_caller_identity()['Account']
    region = session.region_name or 'us-east-1'
    
    image_uri = f"{account_id}.dkr.ecr.{region}.amazonaws.com/{ALGORITHM_NAME}:latest"
    return image_uri

def get_execution_role():
    """Get SageMaker execution role"""
    iam = boto3.client('iam')
    
    # Try to get existing SageMaker execution role
    try:
        role_name = 'SageMakerExecutionRole'
        role = iam.get_role(RoleName=role_name)
        return role['Role']['Arn']
    except:
        # If not found, try common role names
        common_roles = [
            'AmazonSageMaker-ExecutionRole',
            'SageMakerRole',
            'sagemaker-execution-role'
        ]
        
        for role_name in common_roles:
            try:
                role = iam.get_role(RoleName=role_name)
                return role['Role']['Arn']
            except:
                continue
    
    # If no role found, get the first available role with SageMaker permissions
    try:
        roles = iam.list_roles()
        for role in roles['Roles']:
            if 'sagemaker' in role['RoleName'].lower():
                return role['Arn']
    except:
        pass
    
    raise Exception("No suitable SageMaker execution role found. Please create one first.")

def create_model(sagemaker_client, image_uri, role_arn):
    """Create SageMaker model"""
    print(f"🔨 Creating SageMaker model: {MODEL_NAME}")
    
    try:
        response = sagemaker_client.create_model(
            ModelName=MODEL_NAME,
            PrimaryContainer={
                'Image': image_uri,
                'Mode': 'SingleModel'
            },
            ExecutionRoleArn=role_arn
        )
        print(f"✅ Model created: {response['ModelArn']}")
        return response['ModelArn']
    except Exception as e:
        print(f"❌ Failed to create model: {e}")
        raise

def create_endpoint_config(sagemaker_client):
    """Create endpoint configuration"""
    print(f"⚙️  Creating endpoint configuration: {ENDPOINT_CONFIG_NAME}")
    
    try:
        response = sagemaker_client.create_endpoint_config(
            EndpointConfigName=ENDPOINT_CONFIG_NAME,
            ProductionVariants=[
                {
                    'VariantName': 'AllTraffic',
                    'ModelName': MODEL_NAME,
                    'InitialInstanceCount': INITIAL_INSTANCE_COUNT,
                    'InstanceType': INSTANCE_TYPE,
                    'InitialVariantWeight': 1.0
                }
            ]
        )
        print(f"✅ Endpoint configuration created: {response['EndpointConfigArn']}")
        return response['EndpointConfigArn']
    except Exception as e:
        print(f"❌ Failed to create endpoint configuration: {e}")
        raise

def create_endpoint(sagemaker_client):
    """Create and deploy endpoint"""
    print(f"🚀 Creating endpoint: {ENDPOINT_NAME}")
    
    try:
        response = sagemaker_client.create_endpoint(
            EndpointName=ENDPOINT_NAME,
            EndpointConfigName=ENDPOINT_CONFIG_NAME
        )
        print(f"✅ Endpoint creation started: {response['EndpointArn']}")
        return response['EndpointArn']
    except Exception as e:
        print(f"❌ Failed to create endpoint: {e}")
        raise

def wait_for_endpoint(sagemaker_client):
    """Wait for endpoint to be in service"""
    print(f"⏳ Waiting for endpoint to be in service...")
    
    start_time = time.time()
    while True:
        try:
            response = sagemaker_client.describe_endpoint(EndpointName=ENDPOINT_NAME)
            status = response['EndpointStatus']
            
            elapsed = int(time.time() - start_time)
            print(f"   Status: {status} (elapsed: {elapsed}s)")
            
            if status == 'InService':
                print(f"✅ Endpoint is now in service!")
                return True
            elif status == 'Failed':
                failure_reason = response.get('FailureReason', 'Unknown error')
                print(f"❌ Endpoint deployment failed: {failure_reason}")
                return False
            
            time.sleep(30)  # Wait 30 seconds before checking again
            
        except Exception as e:
            print(f"❌ Error checking endpoint status: {e}")
            return False

def test_endpoint():
    """Test the deployed endpoint"""
    print(f"🧪 Testing endpoint: {ENDPOINT_NAME}")
    
    runtime = boto3.client('sagemaker-runtime')
    
    # Test payload
    payload = {
        "prompt": "A beautiful landscape with mountains and a lake",
        "num_inference_steps": 20,
        "guidance_scale": 5.0,
        "seed": 42
    }
    
    try:
        print("   Sending test request...")
        response = runtime.invoke_endpoint(
            EndpointName=ENDPOINT_NAME,
            ContentType='application/json',
            Body=json.dumps(payload)
        )
        
        result = json.loads(response['Body'].read().decode())
        print(f"✅ Test successful! Generated image with {len(result.get('frames', []))} frames")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def main():
    """Main deployment function"""
    print("🚀 Starting Wan2.1 14B SageMaker Deployment")
    print("=" * 50)
    
    try:
        # Initialize clients
        sagemaker_client = boto3.client('sagemaker')
        
        # Get configuration
        image_uri = get_image_uri()
        role_arn = get_execution_role()
        
        print(f"📋 Configuration:")
        print(f"   Image URI: {image_uri}")
        print(f"   Execution Role: {role_arn}")
        print(f"   Instance Type: {INSTANCE_TYPE}")
        print(f"   Model Name: {MODEL_NAME}")
        print(f"   Endpoint Name: {ENDPOINT_NAME}")
        print()
        
        # Step 1: Create model
        model_arn = create_model(sagemaker_client, image_uri, role_arn)
        
        # Step 2: Create endpoint configuration
        config_arn = create_endpoint_config(sagemaker_client)
        
        # Step 3: Create endpoint
        endpoint_arn = create_endpoint(sagemaker_client)
        
        # Step 4: Wait for deployment
        if wait_for_endpoint(sagemaker_client):
            # Step 5: Test endpoint
            test_endpoint()
            
            print("\n🎉 Deployment completed successfully!")
            print(f"📍 Endpoint Name: {ENDPOINT_NAME}")
            print(f"🔗 Endpoint ARN: {endpoint_arn}")
            
            # Save endpoint info
            endpoint_info = {
                "endpoint_name": ENDPOINT_NAME,
                "endpoint_arn": endpoint_arn,
                "model_name": MODEL_NAME,
                "created_at": datetime.now().isoformat(),
                "instance_type": INSTANCE_TYPE
            }
            
            with open('endpoint_info.json', 'w') as f:
                json.dump(endpoint_info, f, indent=2)
            
            print(f"💾 Endpoint info saved to endpoint_info.json")
            
        else:
            print("❌ Deployment failed!")
            return 1
            
    except Exception as e:
        print(f"❌ Deployment error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
