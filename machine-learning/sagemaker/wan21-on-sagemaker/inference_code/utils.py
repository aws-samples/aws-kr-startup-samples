import os
import torch
import logging
import numpy as np
from typing import List, Dict, Any, Optional

# Wan2.1 module import
import wan
from wan.configs import WAN_CONFIGS, SIZE_CONFIGS

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_model(task: str, ckpt_dir: str, offload_model: bool = False, t5_cpu: bool = False) -> Any:
    """
    Load Wan2.1 model
    
    Args:
        task: Task type (e.g., t2v-14B, t2v-1.3B)
        ckpt_dir: Model checkpoint directory
        offload_model: Whether to offload model if memory is insufficient
        t5_cpu: Whether to run T5 model on CPU
    
    Returns:
        Loaded model
    """
    logger.info(f"Loading Wan2.1 model: {task} from {ckpt_dir}")
    
    try:
        # Load Wan2.1 config
        cfg = WAN_CONFIGS[task]
        
        # Select appropriate model class by task type
        if "t2v" in task or "t2i" in task:
            model = wan.WanT2V(
                config=cfg,
                checkpoint_dir=ckpt_dir,
                device_id=0,
                t5_cpu=t5_cpu,
            )
        elif "i2v" in task:
            model = wan.WanI2V(
                config=cfg,
                checkpoint_dir=ckpt_dir,
                device_id=0,
                t5_cpu=t5_cpu,
            )
        else:
            raise ValueError(f"Unsupported task: {task}")
        
        logger.info(f"Wan2.1 model loaded: {task}")
        return model
        
    except Exception as e:
        logger.error(f"Model load failed: {str(e)}")
        raise

def generate_video(
    model: Any,
    prompt: str,
    size: str,
    sample_steps: int = 50,
    guide_scale: float = 5.0,
    shift: float = 5.0
) -> torch.Tensor:
    """
    Generate video using Wan2.1 model
    
    Args:
        model: Loaded Wan2.1 model
        prompt: Video generation prompt
        size: Video size (e.g., "1280*720")
        sample_steps: Number of sampling steps
        guide_scale: Guide scale
        shift: Sampling shift
    
    Returns:
        Generated video tensor
    """
    logger.info(f"Generating video with Wan2.1: {prompt}, size: {size}")
    
    try:
        # Get size settings from SIZE_CONFIGS
        size_config = SIZE_CONFIGS[size]
        
        # Generate video using Wan2.1 model
        result = model.generate(
            prompt=prompt,
            size=size_config,
            frame_num=81,  # Default frame number
            shift=shift,
            sample_solver='unipc',
            sampling_steps=sample_steps,
            guide_scale=guide_scale,
            seed=-1,  # Random seed
            offload_model=False
        )
        
        logger.info("Wan2.1 video generation complete")
        return result
        
    except Exception as e:
        logger.error(f"Video generation failed: {str(e)}")
        raise

def generate_image(
    model: Any,
    prompt: str,
    size: str,
    sample_steps: int = 50,
    guide_scale: float = 5.0,
    shift: float = 5.0
) -> torch.Tensor:
    """
    Generate image using Wan2.1 model
    
    Args:
        model: Loaded Wan2.1 model
        prompt: Image generation prompt
        size: Image size (e.g., "1280*720")
        sample_steps: Number of sampling steps
        guide_scale: Guide scale
        shift: Sampling shift
    
    Returns:
        Generated image tensor
    """
    logger.info(f"Generating image with Wan2.1: {prompt}, size: {size}")
    
    try:
        # Get size settings from SIZE_CONFIGS
        size_config = SIZE_CONFIGS[size]
        
        # Generate image using Wan2.1 model (T2I)
        result = model.generate(
            prompt=prompt,
            size=size_config,
            frame_num=1,  # Image is 1 frame
            shift=shift,
            sample_solver='unipc',
            sampling_steps=sample_steps,
            guide_scale=guide_scale,
            seed=-1,  # Random seed
            offload_model=False
        )
        
        logger.info("Wan2.1 image generation complete")
        return result
        
    except Exception as e:
        logger.error(f"Image generation failed: {str(e)}")
        raise