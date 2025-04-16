import argparse
import base64
import json
import os
import random
import re
import sys
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
import boto3
from botocore.config import Config
from mcp.server.fastmcp import Context, FastMCP
from loguru import logger
from pydantic import BaseModel, Field, field_validator, model_validator

NOVA_CANVAS_MODEL_ID = 'amazon.nova-canvas-v1:0'
DEFAULT_WIDTH = 1024
DEFAULT_HEIGHT = 1024
DEFAULT_QUALITY = 'standard'
DEFAULT_CFG_SCALE = 6.5
DEFAULT_NUMBER_OF_IMAGES = 1
DEFAULT_OUTPUT_DIR = 'output'

logger.remove()
logger.add(sys.stderr, level=os.getenv('FASTMCP_LOG_LEVEL', 'INFO'))

class Quality(str, Enum):
    """Quality options for image generation."""
    STANDARD = 'standard'
    PREMIUM = 'premium'

class TaskType(str, Enum):
    """Task types for image generation."""
    TEXT_IMAGE = 'TEXT_IMAGE'
    COLOR_GUIDED_GENERATION = 'COLOR_GUIDED_GENERATION'

class ImageGenerationConfig(BaseModel):
    """Configuration for image generation."""
    width: int = Field(default=1024, ge=320, le=4096)
    height: int = Field(default=1024, ge=320, le=4096)
    quality: Quality = Quality.STANDARD
    cfgScale: float = Field(default=6.5, ge=1.1, le=10.0)
    seed: int = Field(default_factory=lambda: random.randint(0, 858993459), ge=0, le=858993459)
    numberOfImages: int = Field(default=1, ge=1, le=5)

    @field_validator('width', 'height')
    @classmethod
    def must_be_divisible_by_16(cls, v: int) -> int:
        if v % 16 != 0:
            raise ValueError('Value must be divisible by 16')
        return v

    @model_validator(mode='after')
    def validate_aspect_ratio_and_total_pixels(self):
        width = self.width
        height = self.height

        # Check aspect ratio between 1:4 and 4:1
        aspect_ratio = width / height
        if aspect_ratio < 0.25 or aspect_ratio > 4.0:
            raise ValueError('Aspect ratio must be between 1:4 and 4:1')

        # Check total pixel count
        total_pixels = width * height
        if total_pixels >= 4194304:
            raise ValueError('Total pixel count must be less than 4,194,304')

        return self

class TextToImageParams(BaseModel):
    """Parameters for text-to-image generation."""
    text: str = Field(..., min_length=1, max_length=1024)
    negativeText: Optional[str] = Field(default=None, min_length=1, max_length=1024)

class TextImageRequest(BaseModel):
    """Request model for text-to-image generation."""
    taskType: Literal[TaskType.TEXT_IMAGE] = TaskType.TEXT_IMAGE
    textToImageParams: TextToImageParams
    imageGenerationConfig: Optional[ImageGenerationConfig] = Field(
        default_factory=ImageGenerationConfig
    )

    def to_api_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary suitable for API requests."""
        text_to_image_params = self.textToImageParams.model_dump()
        # Remove negativeText if it's None
        if text_to_image_params.get('negativeText') is None:
            text_to_image_params.pop('negativeText', None)

        return {
            'taskType': self.taskType,
            'textToImageParams': text_to_image_params,
            'imageGenerationConfig': self.imageGenerationConfig.model_dump()
            if self.imageGenerationConfig
            else None,
        }

class ImageGenerationResponse(BaseModel):
    """Response from image generation API."""
    status: str
    message: str
    paths: List[str]
    prompt: str
    negative_prompt: Optional[str] = None
    colors: Optional[List[str]] = None

    class Config:
        arbitrary_types_allowed = True

    def __getitem__(self, key: str) -> Any:
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(f"'{key}' not found in ImageGenerationResponse")

def save_generated_images(
    base64_images: List[str],
    filename: Optional[str] = None,
    number_of_images: int = DEFAULT_NUMBER_OF_IMAGES,
    prefix: str = 'nova_canvas',
    workspace_dir: Optional[str] = None,
) -> Dict[str, List]:
    """Save base64-encoded images to files."""
    logger.debug(f'Saving {len(base64_images)} images')

    if workspace_dir:
        output_dir = os.path.join(workspace_dir, DEFAULT_OUTPUT_DIR)
    else:
        output_dir = DEFAULT_OUTPUT_DIR

    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Save the generated images
    saved_paths: List[str] = []
    for i, base64_image_data in enumerate(base64_images):
        # Generate filename if not provided
        if filename:
            image_filename = (
                f'{filename}_{i + 1}.png' if number_of_images > 1 else f'{filename}.png'
            )
        else:
            # Generate a random filename
            random_id = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
            image_filename = f'{prefix}_{random_id}_{i + 1}.png'

        # Decode the base64 image data
        image_data = base64.b64decode(base64_image_data)

        # Save the image
        image_path = os.path.join(output_dir, image_filename)
        with open(image_path, 'wb') as file:
            file.write(image_data)
        # Convert to absolute path
        abs_image_path = os.path.abspath(image_path)
        saved_paths.append(abs_image_path)

    return {'paths': saved_paths}

async def invoke_nova_canvas(
    request_model_dict: Dict[str, Any],
    bedrock_runtime_client,
) -> Dict[str, Any]:
    """Invoke the Nova Canvas API with the given request."""
    logger.debug('Invoking Nova Canvas API')

    # Convert the request payload to JSON
    request = json.dumps(request_model_dict)

    try:
        # Invoke the model
        logger.info(f'Sending request to Nova Canvas model: {NOVA_CANVAS_MODEL_ID}')
        response = bedrock_runtime_client.invoke_model(modelId=NOVA_CANVAS_MODEL_ID, body=request)

        # Decode the response body
        result = json.loads(response['body'].read().decode('utf-8'))
        logger.info('Nova Canvas API call successful')
        return result
    except Exception as e:
        logger.error(f'Nova Canvas API call failed: {str(e)}')
        raise

async def generate_image_with_text(
    prompt: str,
    bedrock_runtime_client,
    negative_prompt: Optional[str] = None,
    filename: Optional[str] = None,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    quality: str = DEFAULT_QUALITY,
    cfg_scale: float = DEFAULT_CFG_SCALE,
    seed: Optional[int] = None,
    number_of_images: int = DEFAULT_NUMBER_OF_IMAGES,
    workspace_dir: Optional[str] = None,
) -> ImageGenerationResponse:
    """Generate an image using Amazon Nova Canvas with text prompt."""
    logger.debug(f"Generating text-to-image with prompt: '{prompt[:30]}...' ({width}x{height})")

    try:
        # Validate input parameters using Pydantic
        try:
            logger.debug('Validating parameters and creating request model')

            # Create image generation config
            config = ImageGenerationConfig(
                width=width,
                height=height,
                quality=Quality.STANDARD if quality == DEFAULT_QUALITY else Quality.PREMIUM,
                cfgScale=cfg_scale,
                seed=seed if seed is not None else random.randint(0, 858993459),
                numberOfImages=number_of_images,
            )

            # Create text-to-image params
            # The Nova Canvas API doesn't accept null for negativeText
            if negative_prompt is not None:
                text_params = TextToImageParams(text=prompt, negativeText=negative_prompt)
            else:
                text_params = TextToImageParams(text=prompt)

            # Create the full request
            request_model = TextImageRequest(
                textToImageParams=text_params, imageGenerationConfig=config
            )

            # Convert model to dictionary
            request_model_dict = request_model.to_api_dict()
            logger.info('Request validation successful')

        except Exception as e:
            logger.error(f'Parameter validation failed: {str(e)}')
            return ImageGenerationResponse(
                status='error',
                message=f'Validation error: {str(e)}',
                paths=[],
                prompt=prompt,
                negative_prompt=negative_prompt,
            )

        try:
            # Invoke the Nova Canvas API
            logger.debug('Sending request to Nova Canvas API')
            model_response = await invoke_nova_canvas(request_model_dict, bedrock_runtime_client)

            # Extract the image data
            base64_images = model_response['images']
            logger.info(f'Received {len(base64_images)} images from Nova Canvas API')

            # Save the generated images
            result = save_generated_images(
                base64_images,
                filename,
                number_of_images,
                prefix='nova_canvas',
                workspace_dir=workspace_dir,
            )

            logger.info(f'Successfully generated {len(result["paths"])} image(s)')
            return ImageGenerationResponse(
                status='success',
                message=f'Generated {len(result["paths"])} image(s)',
                paths=result['paths'],
                prompt=prompt,
                negative_prompt=negative_prompt,
            )
        except Exception as e:
            logger.error(f'Image generation failed: {str(e)}')
            return ImageGenerationResponse(
                status='error',
                message=str(e),
                paths=[],
                prompt=prompt,
                negative_prompt=negative_prompt,
            )

    except Exception as e:
        logger.error(f'Unexpected error in generate_image_with_text: {str(e)}')
        return ImageGenerationResponse(
            status='error',
            message=str(e),
            paths=[],
            prompt=prompt,
            negative_prompt=negative_prompt,
        )

# Create simple documentation
INSTRUCTIONS = """
# Amazon Nova Canvas Image Generation

This MCP server uses Amazon Bedrock's Nova Canvas model to generate images from text prompts.

## Available Tools

### generate_image
Generate images using text prompts.

## Prompt Writing Tips

1. Prompts should not exceed 1024 characters.
2. Avoid negative expressions like "without", "no", "lacking". Use negative_prompt parameter instead.
3. Effective prompt structure:
   - Subject/object
   - Environment/background
   - (Optional) Position or pose of the subject
   - (Optional) Lighting description
   - (Optional) Camera position/framing
   - (Optional) Visual style or medium ("photo", "illustration", "painting", etc.)
"""

mcp = FastMCP(
    'amazon-nova-canvas-mcp-server',
    instructions=INSTRUCTIONS,
    dependencies=[
        'pydantic',
        'boto3'
    ],
)

# Initialize Bedrock Runtime Client
aws_region: str = os.environ.get('AWS_REGION', 'us-east-1')
bedrock_runtime_client = None

try:
    if aws_profile := os.environ.get('AWS_PROFILE'):
        bedrock_runtime_client = boto3.Session(
            profile_name=aws_profile, region_name=aws_region
        ).client('bedrock-runtime')
    else:
        aws_access_key_id = os.environ.get('AWS_ACCESS_KEY_ID')
        aws_secret_access_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
        
        if aws_access_key_id and aws_secret_access_key:
            bedrock_config = Config(read_timeout=300)
            bedrock_runtime_client = boto3.client(
                'bedrock-runtime',
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=aws_region,
                config=bedrock_config
            )
        else:
            bedrock_runtime_client = boto3.Session(region_name=aws_region).client('bedrock-runtime')
except Exception as e:
    logger.error(f'Error creating bedrock runtime client: {str(e)}')

@mcp.tool(name='generate_image')
async def mcp_generate_image(
    ctx: Context,
    prompt: str = Field(
        description='Text description for image generation (1-1024 characters)'
    ),
    negative_prompt: Optional[str] = Field(
        default=None,
        description='Description of elements to exclude from the image (1-1024 characters)',
    ),
    filename: Optional[str] = Field(
        default=None,
        description='Filename to save (without extension)',
    ),
    width: int = Field(
        default=DEFAULT_WIDTH,
        description='Width of the generated image (320-4096, must be divisible by 16)',
    ),
    height: int = Field(
        default=DEFAULT_HEIGHT,
        description='Height of the generated image (320-4096, must be divisible by 16)',
    ),
    quality: str = Field(
        default=DEFAULT_QUALITY,
        description='Image quality ("standard" or "premium")',
    ),
    cfg_scale: float = Field(
        default=DEFAULT_CFG_SCALE,
        description='Prompt adherence strength (1.1-10.0)',
    ),
    seed: Optional[int] = Field(
        default=None, 
        description='Seed for image generation (0-858,993,459)',
    ),
    number_of_images: int = Field(
        default=DEFAULT_NUMBER_OF_IMAGES,
        description='Number of images to generate (1-5)',
    ),
    workspace_dir: Optional[str] = Field(
        default=None,
        description='Workspace directory to save images',
    ),
):
    """Generate images using text prompts with Amazon Nova Canvas.

    This tool generates images based on text prompts and saves them as files.
    Returns the paths to the generated images.

    ## Prompt Writing Tips

    Effective prompts include short descriptions of:
    1. Subject/object
    2. Environment/background
    3. (Optional) Position or pose of the subject
    4. (Optional) Lighting description
    5. (Optional) Camera position/framing
    6. (Optional) Visual style or medium ("photo", "illustration", "painting", etc.)

    Avoid negative expressions in your prompt like "without", "no", or "lacking".
    Instead, use the negative_prompt parameter to specify unwanted elements.

    Consider including "people, anatomy, hands, low quality, low resolution, low detail" 
    in negative_prompt for better results.

    ## Example Prompts

    - "Realistic photo of a female teacher standing in front of a classroom blackboard, warm smile"
    - "Fantastic and mystical story illustration with soft colors: woman with a big hat looking at the sea"
    - "Drone view of a dark river cutting through Icelandic landscape, cinematic quality"

    Returns:
        Response containing generated image paths and status information
    """
    logger.debug(
        f"MCP tool generate_image called with prompt: '{prompt[:30]}...', dims: {width}x{height}"
    )

    try:
        if bedrock_runtime_client is None:
            error_msg = "AWS Bedrock client was not initialized."
            logger.error(error_msg)
            await ctx.error(error_msg)
            return {"status": "error", "message": error_msg, "paths": []}
            
        logger.info(
            f'Generating image with text prompt, quality: {quality}, cfg_scale: {cfg_scale}'
        )
        response = await generate_image_with_text(
            prompt=prompt,
            bedrock_runtime_client=bedrock_runtime_client,
            negative_prompt=negative_prompt,
            filename=filename,
            width=width,
            height=height,
            quality=quality,
            cfg_scale=cfg_scale,
            seed=seed,
            number_of_images=number_of_images,
            workspace_dir=workspace_dir,
        )

        if response.status == 'success':
            return {
                "status": "success",
                "message": response.message,
                "paths": response.paths,
            }
        else:
            logger.error(f'Image generation error occurred: {response.message}')
            await ctx.error(f'Image generation failed: {response.message}')
            return {
                "status": "error", 
                "message": f"Image generation failed: {response.message}",
                "paths": []
            }
    except Exception as e:
        logger.error(f'mcp_generate_image error: {str(e)}')
        await ctx.error(f'Image generation error: {str(e)}')
        return {
            "status": "error", 
            "message": f"Error occurred: {str(e)}",
            "paths": []
        }

def main():
    """Run the MCP server with CLI argument support."""
    logger.info('Starting Nova Canvas MCP server')

    parser = argparse.ArgumentParser(
        description='Amazon Nova Canvas Image Generation MCP Server'
    )
    parser.add_argument('--stdio', action='store_true', help='Use STDIO transport mode (default: HTTP)')
    parser.add_argument('--port', type=int, default=8888, help='Server port to run on')
    parser.add_argument('--host', type=str, default='127.0.0.1', help='Server binding localhost')

    args = parser.parse_args()
    logger.debug(f'Parsed arguments: stdio={args.stdio}, port={args.port}, host={args.host}')
      
    mcp.run(transport='stdio')


if __name__ == '__main__':
    main()
