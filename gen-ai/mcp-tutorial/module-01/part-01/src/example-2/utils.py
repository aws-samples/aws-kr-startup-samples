#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import base64
from enum import Enum
import json
import os
import random
from typing import (
  Any,
  Dict,
  List,
  Literal,
  Optional
)
import uuid

from pydantic import (
  BaseModel,
  Field,
  field_validator,
  model_validator
)

from constants import (
  DEFAULT_WIDTH,
  DEFAULT_HEIGHT,
  DEFAULT_QUALITY,
  DEFAULT_CFG_SCALE,
  DEFAULT_NUMBER_OF_IMAGES,
  DEFAULT_OUTPUT_DIR,
)

NOVA_CANVAS_MODEL_ID = os.environ.get('NOVA_CANVAS_MODEL_ID', 'amazon.nova-canvas-v1:0')


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
        if self.imageGenerationConfig else None,
    }


class ImageGenerationResponse(BaseModel):
  """Response from image generation API."""
  status: str
  message: str
  paths: List[str]
  prompt: str
  negative_prompt: Optional[str]=None
  colors: Optional[List[str]]=None

  class Config:
    arbitary_types_allowed=True

  def __getitem__(self, key: str) -> Any:
    if hasattr(self, key):
      return getattr(self, key)
    raise KeyError(f"'{key}' not found")


async def invoke_nova_canvas(
  client,
  request_model_dict: Dict[str, Any]
) -> Dict[str, Any]:
  """Invoke the Nova Canvas API with the given request."""

  request = json.dumps(request_model_dict)

  try:
    response = client.invoke_model(modelId=NOVA_CANVAS_MODEL_ID, body=request)
    result = json.loads(response['body'].read().decode('utf-8'))
    return result
  except Exception as ex:
    import traceback
    traceback.print_exc()
    raise ex


def save_generated_images(
  base64_images: List[str],
  number_of_images: int = DEFAULT_NUMBER_OF_IMAGES,
  filename: Optional[str] = None,
  workspace_dir: Optional[str] = None
) -> Dict[str, List]:

  """Save base64-encoded images to files."""

  output_dir = DEFAULT_OUTPUT_DIR if not workspace_dir else os.path.join(workspace_dir, DEFAULT_OUTPUT_DIR)
  os.makedirs(output_dir, exist_ok=True)

  saved_paths = []
  for i, base64_image_data in enumerate(base64_images):
    suffix = f'_{i+1}' if number_of_images > 1 else ''
    image_filename = (
      f"{filename}{suffix}.png"
      if filename
      else f'{uuid.uuid4()}{suffix}.png'
    )

    image_data = base64.b64decode(base64_image_data)

    image_path = os.path.join(output_dir, image_filename)
    with open(image_path, 'wb') as file:
      file.write(image_data)
    abs_image_path = os.path.abspath(image_path)
    saved_paths.append(abs_image_path)

  return {'paths': saved_paths}


async def generate_image_with_text(
  client,
  prompt: str,
  negative_prompt: Optional[str]=None,
  width: int=DEFAULT_WIDTH,
  height: int=DEFAULT_HEIGHT,
  quality: str=DEFAULT_QUALITY,
  cfg_scale: float=DEFAULT_CFG_SCALE,
  number_of_images: int=DEFAULT_NUMBER_OF_IMAGES,
  filename: Optional[str]=None,
  workspace_dir: Optional[str]=None,
  seed: Optional[int]=None,
) -> ImageGenerationResponse:
  """Generate an image using Amazon Nova Canvas with text prompt."""

  try:
    config = ImageGenerationConfig(
      width=width,
      height=height,
      quality=Quality.STANDARD if quality == DEFAULT_QUALITY else Quality.PREMIUM,
      cfgScale=cfg_scale,
      seed=seed if seed is not None else random.randint(0, 858993459),
      numberOfImages=number_of_images,
    )

    text_params = TextToImageParams(text=prompt, negativeText=negative_prompt)

    request_model = TextImageRequest(
      textToImageParams=text_params,
      imageGenerationConfig=config
    )

    request_model_dict = request_model.to_api_dict()
  except Exception as ex:
    return ImageGenerationResponse(
      status='error',
      message=f'Validation error: {str(ex)}',
      paths=[],
      prompt=prompt,
      negative_prompt=negative_prompt,
    )

  try:
    model_response = await invoke_nova_canvas(client, request_model_dict)
    base64_images = model_response['images']

    result = save_generated_images(
      base64_images,
      number_of_images,
      filename=filename,
      workspace_dir=workspace_dir
    )

    status, message, paths = (
      'success',
      f'Generated {len(result["paths"])} image(s)',
      result['paths']
    )
  except Exception as ex:
    status, message, paths = ('error', f"{ex}", [])

  return ImageGenerationResponse(
    status=status,
    message=message,
    paths=paths,
    prompt=prompt,
    negative_prompt=negative_prompt,
  )
