DEFAULT_OUTPUT_DIR = 'output'
DEFAULT_WIDTH, DEFAULT_HEIGHT = (1024, 1024)
DEFAULT_QUALITY = 'standard'
DEFAULT_CFG_SCALE = 6.5
DEFAULT_NUMBER_OF_IMAGES = 1

INSTRUCTIONS = """# Amazon Nova Canvas Image Generation

This MCP server uses Amazon Bedrock's Nova Canvas model to generate images from text prompts.

## Available Tools

### generate_image
Generate images using text prompts and saves them as files.
Returns the paths to the generated images.

## Prompt Writing Tips

1. Prompts should not exceed 1024 characters.
2. Avoid negative expressions like "without", "no", "lacking". Use negative_prompt parameter instead.
3. Consider including "people, anatomy, hands, low quality, low resolution, low detail" in negative_prompt for better results.
4. Effective prompt structure:
   - Subject/object
   - Environment/background
   - (Optional) Position or pose of the subject
   - (Optional) Lighting description
   - (Optional) Camera position/framing
   - (Optional) Visual style or medium ("photo", "illustration", "painting", etc.)

## Example Prompts

- "Realistic photo of a female teacher standing in front of a classroom blackboard, warm smile"
- "Fantastic and mystical story illustration with soft colors: woman with a big hat looking at the sea"
- "Drone view of a dark river cutting through Icelandic landscape, cinematic quality"
"""
