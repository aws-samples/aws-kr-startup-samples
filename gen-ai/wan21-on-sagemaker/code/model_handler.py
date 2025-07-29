"""
Wan2.1 Model Handler for SageMaker Inference - Optimized Version
"""
import os
import sys
import json
import logging
import tempfile
import base64
from PIL import Image
import io
import traceback
import torch
import boto3
from datetime import datetime
import uuid

# Add model directory to Python path
sys.path.insert(0, "/opt/ml/model")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Wan21ModelHandler:
    """
    Wan2.1 Model Handler with in-memory model loading
    """
    
    def __init__(self):
        self.model_dir = "/opt/ml/model"
        self.ckpt_dir = "/opt/ml/model/Wan2.1-T2V-14B"
        self.is_loaded = False
        self.model = None
        self.device = None
        self.s3_client = None
        self.s3_bucket = os.environ.get('S3_BUCKET', None)
        
        # Initialize S3 client if bucket is configured
        if self.s3_bucket:
            try:
                self.s3_client = boto3.client('s3')
                logger.info(f"S3 upload configured for bucket: {self.s3_bucket}")
            except Exception as e:
                logger.warning(f"Failed to initialize S3 client: {e}")
                self.s3_client = None
        
    def load_model(self) -> bool:
        """
        Load model into memory for reuse
        """
        try:
            logger.info("Loading Wan2.1 model into memory...")
            
            # Check if model directory exists
            if not os.path.exists(self.ckpt_dir):
                logger.error(f"Model directory not found: {self.ckpt_dir}")
                return False
            
            # Check key model files
            required_files = [
                "diffusion_pytorch_model.safetensors",
                "models_t5_umt5-xxl-enc-bf16.pth",
                "Wan2.1_VAE.pth"
            ]
            
            for file in required_files:
                file_path = os.path.join(self.ckpt_dir, file)
                if not os.path.exists(file_path):
                    logger.error(f"Required model file not found: {file_path}")
                    return False
                logger.info(f"Found: {file}")
            
            # Set device
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            logger.info(f"Using device: {self.device}")
            
            # Import and initialize model
            try:
                from wan.modules.model import WanModel
                from wan.configs.wan_config import WanConfig
                
                # Load config
                config_path = os.path.join(self.ckpt_dir, "config.json")
                if os.path.exists(config_path):
                    with open(config_path, 'r') as f:
                        config_dict = json.load(f)
                    config = WanConfig(**config_dict)
                else:
                    # Use default config for 14B model
                    config = WanConfig()
                
                # Initialize model
                logger.info("Initializing Wan2.1 model...")
                self.model = WanModel(config)
                
                # Load model weights
                logger.info("Loading model weights...")
                checkpoint_path = os.path.join(self.ckpt_dir, "diffusion_pytorch_model.safetensors")
                
                # Load using safetensors
                from safetensors.torch import load_file
                state_dict = load_file(checkpoint_path)
                self.model.load_state_dict(state_dict, strict=False)
                
                # Move to device
                self.model = self.model.to(self.device)
                self.model.eval()
                
                logger.info("Model loaded successfully into memory")
                
            except ImportError as e:
                logger.warning(f"Could not import Wan model directly: {e}")
                logger.info("Falling back to subprocess method...")
                # Keep the model as None, will use subprocess fallback
                self.model = None
            
            self.is_loaded = True
            logger.info("Wan2.1 model initialization completed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    def predict(self, input_data: dict) -> dict:
        """
        Generate image using Wan2.1 (in-memory model or subprocess fallback)
        """
        if not self.is_loaded:
            raise RuntimeError("Model not loaded")
        
        try:
            # Extract parameters
            prompt = input_data.get("prompt", "")
            if not prompt:
                raise ValueError("Prompt is required")
            
            # Parameters with defaults
            task = input_data.get("task", "t2i-14B")
            size = input_data.get("size", "1280*720")
            num_inference_steps = input_data.get("num_inference_steps", 50)
            guidance_scale = input_data.get("guidance_scale", 5.0)
            seed = input_data.get("seed", None)
            
            logger.info(f"Generating image for prompt: {prompt[:100]}...")
            logger.info(f"Parameters: task={task}, size={size}, steps={num_inference_steps}")
            
            # Try in-memory model first
            if self.model is not None:
                return self._predict_with_model(prompt, task, size, num_inference_steps, guidance_scale, seed)
            else:
                # Fallback to subprocess method
                return self._predict_with_subprocess(prompt, task, size, num_inference_steps, guidance_scale, seed)
                
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return {"status": "error", "error": str(e)}
    
    def _predict_with_model(self, prompt, task, size, num_inference_steps, guidance_scale, seed):
        """
        Generate using in-memory model (faster)
        """
        try:
            logger.info("Using in-memory model for generation...")
            
            # Parse size
            width, height = map(int, size.split('*'))
            
            # Set seed if provided
            if seed is not None:
                torch.manual_seed(seed)
                if torch.cuda.is_available():
                    torch.cuda.manual_seed(seed)
            
            # Generate image using the loaded model
            with torch.no_grad():
                # This is a simplified version - you'll need to implement the actual generation logic
                # based on the Wan2.1 model's interface
                result_image = self.model.generate(
                    prompt=prompt,
                    width=width,
                    height=height,
                    num_inference_steps=num_inference_steps,
                    guidance_scale=guidance_scale
                )
            
            # Convert to PIL Image and encode
            if isinstance(result_image, torch.Tensor):
                # Convert tensor to PIL Image
                result_image = result_image.cpu().numpy()
                result_image = (result_image * 255).astype('uint8')
                result_image = Image.fromarray(result_image)
            
            # Convert to base64
            buffer = io.BytesIO()
            result_image.save(buffer, format='PNG')
            image_data = buffer.getvalue()
            image_b64 = base64.b64encode(image_data).decode('utf-8')
            
            # Prepare metadata
            metadata = {
                "prompt": prompt,
                "task": task,
                "size": size,
                "width": width,
                "height": height,
                "num_inference_steps": num_inference_steps,
                "guidance_scale": guidance_scale,
                "seed": seed,
                "method": "in_memory"
            }
            
            # Upload to S3 if configured
            s3_url = self.upload_to_s3(image_data, prompt, metadata)
            
            result_data = {
                "status": "success",
                "image": image_b64,
                "metadata": metadata
            }
            
            # Add S3 URL if upload was successful
            if s3_url:
                result_data["s3_url"] = s3_url
                result_data["s3_bucket"] = self.s3_bucket
            
            logger.info(f"Image generation completed: {width}x{height} (in-memory)")
            return result_data
            
        except Exception as e:
            logger.warning(f"In-memory generation failed: {e}, falling back to subprocess...")
            return self._predict_with_subprocess(prompt, task, size, num_inference_steps, guidance_scale, seed)
    
    def _predict_with_subprocess(self, prompt, task, size, num_inference_steps, guidance_scale, seed):
        """
        Generate using subprocess (fallback method)
        """
        import subprocess
        
        logger.info("Using subprocess method for generation...")
        
        # Create temporary output file
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            output_path = tmp_file.name
        
        # Build command
        cmd = [
            "python3", 
            os.path.join(self.model_dir, "generate.py"),
            "--task", task,
            "--size", size,
            "--ckpt_dir", self.ckpt_dir,
            "--prompt", prompt,
            "--sample_steps", str(num_inference_steps),
            "--sample_guide_scale", str(guidance_scale),
            "--save_file", output_path
        ]
        
        if seed is not None:
            cmd.extend(["--base_seed", str(seed)])
        
        logger.info(f"Running command: {' '.join(cmd)}")
        
        try:
            # Execute generation
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minutes timeout
                cwd=self.model_dir
            )
            
            if result.returncode != 0:
                logger.error(f"Generation failed with return code {result.returncode}")
                logger.error(f"STDERR: {result.stderr}")
                raise RuntimeError(f"Image generation failed: {result.stderr}")
            
            # Check if output file was created
            if not os.path.exists(output_path):
                raise RuntimeError("Output image file was not created")
            
            # Read and encode image
            with open(output_path, 'rb') as f:
                image_data = f.read()
            
            # Clean up temporary file
            os.unlink(output_path)
            
            # Convert to base64
            image_b64 = base64.b64encode(image_data).decode('utf-8')
            
            # Get image info
            image = Image.open(io.BytesIO(image_data))
            width, height = image.size
            
            # Prepare metadata
            metadata = {
                "prompt": prompt,
                "task": task,
                "size": size,
                "width": width,
                "height": height,
                "num_inference_steps": num_inference_steps,
                "guidance_scale": guidance_scale,
                "seed": seed,
                "method": "subprocess"
            }
            
            # Upload to S3 if configured
            s3_url = self.upload_to_s3(image_data, prompt, metadata)
            
            result_data = {
                "status": "success",
                "image": image_b64,
                "metadata": metadata
            }
            
            # Add S3 URL if upload was successful
            if s3_url:
                result_data["s3_url"] = s3_url
                result_data["s3_bucket"] = self.s3_bucket
            
            logger.info(f"Image generation completed: {width}x{height} (subprocess)")
            return result_data
            
        except subprocess.TimeoutExpired:
            logger.error("Image generation timed out")
            return {"status": "error", "error": "Generation timed out"}
        finally:
            # Clean up temporary file if it exists
            if os.path.exists(output_path):
                os.unlink(output_path)
    
    def upload_to_s3(self, image_data, prompt, metadata):
        """
        Upload image to S3 and return S3 URL
        """
        if not self.s3_client or not self.s3_bucket:
            return None
            
        try:
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            safe_prompt = "".join(c for c in prompt[:30] if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_prompt = safe_prompt.replace(' ', '_')
            
            filename = f"wan21_images/{timestamp}_{unique_id}_{safe_prompt}.png"
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=filename,
                Body=image_data,
                ContentType='image/png',
                Metadata={
                    'prompt': prompt,
                    'task': metadata.get('task', ''),
                    'size': metadata.get('size', ''),
                    'steps': str(metadata.get('num_inference_steps', '')),
                    'guidance_scale': str(metadata.get('guidance_scale', '')),
                    'seed': str(metadata.get('seed', ''))
                }
            )
            
            s3_url = f"s3://{self.s3_bucket}/{filename}"
            logger.info(f"Image uploaded to S3: {s3_url}")
            return s3_url
            
        except Exception as e:
            logger.error(f"Failed to upload to S3: {e}")
            return None
    
    def health_check(self) -> bool:
        """
        Health check for the model
        """
        return self.is_loaded

# Global model handler instance
model_handler = Wan21ModelHandler()
