#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

from dotenv import load_dotenv
import os
from typing import Optional

import boto3
from mcp.server.fastmcp import (
  Context,
  FastMCP
)
from pydantic import Field

from constants import (
  DEFAULT_WIDTH,
  DEFAULT_HEIGHT,
  DEFAULT_QUALITY,
  DEFAULT_CFG_SCALE,
  DEFAULT_NUMBER_OF_IMAGES,
  INSTRUCTIONS
)

from utils import (
  generate_image_with_text
)

load_dotenv()


mcp = FastMCP(
  'amazon-nova-canvas-mcp-server',
  instructions=INSTRUCTIONS,
  dependencies=[
    'pydantic',
    'boto3',
  ]
)

aws_region = os.environ.get('AWS_REGION', 'us-east-1')
bedrock_runtime_client = boto3.client('bedrock-runtime', region_name=aws_region)


@mcp.tool(name='generate_image')
async def mcp_generate_image(
    ctx: Context,
    prompt: str=Field(description='Text description for image generation (1-1024 characters)'),
    negative_prompt: Optional[str]=Field(
      default=None,
      description='Description of elements to exclude from the image (1-1024 characters)',
    ),
    filename: Optional[str]=Field(
      default=None,
      description='Filename to save (without extension)',
    ),
    width: int=Field(
      default=DEFAULT_WIDTH,
      description='Width of the generated image (320-4096, must be divisible by 16)',
    ),
    height: int=Field(
      default=DEFAULT_HEIGHT,
      description='Height of the generated image (320-4096, must be divisible by 16)',
    ),
    quality: str=Field(
      default=DEFAULT_QUALITY,
      description='Image quality ("standard" or "premium")',
    ),
    cfg_scale: float=Field(
      default=DEFAULT_CFG_SCALE,
      description='Prompt adherence strength (1.1-10.0)',
    ),
    seed: Optional[int]=Field(
      default=None,
      description='Seed for image generation (0-858,993,459)',
    ),
    number_of_images: int=Field(
      default=DEFAULT_NUMBER_OF_IMAGES,
      description='Number of images to generate (1-5)',
    ),
    workspace_dir: Optional[str]=Field(
      default=None,
      description='Workspace directory to save images',
    )
):
  """Generate images using text prompts and saves them as files.

  Returns:
    Response containing generated image paths and status information
  """

  try:
    response = await generate_image_with_text(
      client=bedrock_runtime_client,
      prompt=prompt,
      negative_prompt=negative_prompt,
      width=width,
      height=height,
      quality=quality,
      cfg_scale=cfg_scale,
      number_of_images=number_of_images,
      filename=filename,
      workspace_dir=workspace_dir,
      seed=seed
    )

    if response.status == 'success':
      status, message, paths = (
        "success",
        response.message,
        response.paths
      )
    else:
      await ctx.error(f'Image generation failed: {response.message}')
      status, message, paths = (
        "error",
        f"Image generation failed: {response.message}",
        []
      )
  except Exception as ex:
    await ctx.error(f'Image generation error: {str(ex)}')
    status, message, paths = (
      "error",
      f"Error occurred: {ex}",
      []
    )

  return {"status": status, "message": message, "paths": paths}


def main():
  mcp.run(transport='stdio')


if __name__ == "__main__":
  main()
