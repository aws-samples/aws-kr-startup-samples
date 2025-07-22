#!/usr/bin/env python3
"""
Test script for Wan2.1 SageMaker endpoint
"""
import boto3
import json
import time
import base64

def test_endpoint():
    # Load endpoint info
    with open('endpoint_info.json', 'r') as f:
        endpoint_info = json.load(f)
    
    endpoint_name = endpoint_info['endpoint_name']
    print(f"🧪 Testing endpoint: {endpoint_name}")
    
    # Create SageMaker runtime client with longer timeout
    runtime = boto3.client('sagemaker-runtime', region_name='us-east-1')
    runtime._client_config.read_timeout = 300  # 5 minutes
    
    # Test payload
    payload = {
        "prompt": "A beautiful sunset over the ocean with gentle waves",
        "task": "t2i-14B",
        "size": "1280*720",
        "num_inference_steps": 15,  # Reduced for faster testing
        "guidance_scale": 5.0,
        "seed": 42
    }
    
    print(f"📝 Request payload:")
    print(json.dumps(payload, indent=2))
    print()
    
    try:
        print("⏳ Sending inference request...")
        start_time = time.time()
        
        response = runtime.invoke_endpoint(
            EndpointName=endpoint_name,
            ContentType='application/json',
            Body=json.dumps(payload)
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"✅ Request completed in {duration:.1f} seconds")
        
        # Parse response
        result = json.loads(response['Body'].read().decode())
        
        if result.get('status') == 'success':
            print("🎉 Image generation successful!")
            print(f"📊 Generated image: {result.get('width', 'N/A')}x{result.get('height', 'N/A')}")
            
            # Save image if base64 data is provided
            if 'image_base64' in result:
                try:
                    image_data = base64.b64decode(result['image_base64'])
                    with open('generated_image.png', 'wb') as f:
                        f.write(image_data)
                    print("💾 Image saved as 'generated_image.png'")
                except Exception as e:
                    print(f"⚠️  Could not save image: {e}")
            
            print(f"🎯 Metadata: {result.get('metadata', {})}")
            
        else:
            print(f"❌ Generation failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
        if 'ModelError' in str(e) and 'timed out' in str(e):
            print("💡 This is normal for the first request - the model needs time to load")
            print("💡 Try running the test again in a few minutes")

if __name__ == "__main__":
    test_endpoint()
