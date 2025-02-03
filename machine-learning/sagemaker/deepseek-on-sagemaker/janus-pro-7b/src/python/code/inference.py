#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import base64
from io import BytesIO
import datetime
import json
import os
from typing import List

import numpy as np
import torch
from transformers import (
  AutoConfig,
  AutoModelForCausalLM
)
from janus.models import (
  MultiModalityCausalLM,
  VLChatProcessor
)
from janus.utils.io import load_pil_images
from PIL import Image
from huggingface_hub import snapshot_download

CUDA_DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'


def model_fn(model_dir, context=None):
  if os.environ.get('HF_SNAPSHOT_DOWNLOAD_ENABLED', 'false').lower() == 'true':
      model_id = os.environ['HF_MODEL_ID']
      model_dir = snapshot_download(model_id, force_download=False, max_workers=1)

  try:
    processor = VLChatProcessor.from_pretrained(model_dir)

    config = AutoConfig.from_pretrained(model_dir)
    language_config = config.language_config
    language_config._attn_implementation = 'eager'
    model = AutoModelForCausalLM.from_pretrained(
      model_dir,
      language_config=language_config,
      trust_remote_code=True,
    )

    if torch.cuda.is_available():
      model = model.to(torch.bfloat16).cuda()
    else:
      model = model.to(torch.float16)
  except Exception as ex:
    import traceback
    traceback.print_exc()

  return model, processor


def base64_to_pil_image(base64_string):
  image_bytes = base64.b64decode(base64_string)
  image_buffer = BytesIO(image_bytes)
  pil_image = Image.open(image_buffer).convert('RGB')
  return pil_image


@torch.inference_mode()
# Multimodal Understanding function
def multimodal_understanding(
  vl_gpt: MultiModalityCausalLM,
  vl_chat_processor: VLChatProcessor,
  images: List,
  question: str,
  seed: int = None,
  top_p: float = 0.95,
  temperature: float = 1.0,
  max_new_tokens: int = 512,
  device: str = 'cuda'):

  # Clear CUDA cache before generating
  torch.cuda.empty_cache()

  # Set the seed for reproducible results
  if seed is not None:
    torch.manual_seed(seed)
    np.random.seed(seed)
    torch.cuda.manual_seed(seed)

  conversation = [
    {
      "role": "<|User|>",
      "content": f"<image_placeholder>\n{question}",
      "images": images,
    },
    {"role": "<|Assistant|>", "content": ""},
  ]

  pil_images = [base64_to_pil_image(img) for img in images]
  prepare_inputs = vl_chat_processor(
    conversations=conversation, images=pil_images, force_batchify=True
  ).to(device, dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float16)

  tokenizer = vl_chat_processor.tokenizer

  inputs_embeds = vl_gpt.prepare_inputs_embeds(**prepare_inputs)

  outputs = vl_gpt.language_model.generate(
    inputs_embeds=inputs_embeds,
    attention_mask=prepare_inputs.attention_mask,
    pad_token_id=tokenizer.eos_token_id,
    bos_token_id=tokenizer.bos_token_id,
    eos_token_id=tokenizer.eos_token_id,
    max_new_tokens=max_new_tokens,
    do_sample=False if temperature == 0 else True,
    use_cache=True,
    temperature=temperature,
    top_p=top_p,
  )

  answer = tokenizer.decode(outputs[0].cpu().tolist(), skip_special_tokens=True)
  return answer


def generate(
  vl_gpt: MultiModalityCausalLM,
  vl_chat_processor: VLChatProcessor,
  input_ids,
  width,
  height,
  temperature: float = 1.0,
  parallel_size: int = 2,
  cfg_weight: float = 5.0,
  image_token_num_per_image: int = 576,
  patch_size: int = 16,
  device: str = 'cuda'):

  # Clear CUDA cache before generating
  torch.cuda.empty_cache()

  tokens = torch.zeros((parallel_size * 2, len(input_ids)), dtype=torch.int).to(device)
  for i in range(parallel_size * 2):
    tokens[i, :] = input_ids
    if i % 2 != 0:
      tokens[i, 1:-1] = vl_chat_processor.pad_id

  inputs_embeds = vl_gpt.language_model.get_input_embeddings()(tokens)
  generated_tokens = torch.zeros((parallel_size, image_token_num_per_image), dtype=torch.int).to(device)

  pkv = None
  for i in range(image_token_num_per_image):
    with torch.no_grad():
      outputs = vl_gpt.language_model.model(
        inputs_embeds=inputs_embeds,
        use_cache=True,
        past_key_values=pkv)

      pkv = outputs.past_key_values
      hidden_states = outputs.last_hidden_state
      logits = vl_gpt.gen_head(hidden_states[:, -1, :])
      logit_cond = logits[0::2, :]
      logit_uncond = logits[1::2, :]
      logits = logit_uncond + cfg_weight * (logit_cond - logit_uncond)
      probs = torch.softmax(logits / temperature, dim=-1)
      next_token = torch.multinomial(probs, num_samples=1)
      generated_tokens[:, i] = next_token.squeeze(dim=-1)
      next_token = torch.cat([next_token.unsqueeze(dim=1), next_token.unsqueeze(dim=1)], dim=1).view(-1)

      img_embeds = vl_gpt.prepare_gen_img_embeds(next_token)
      inputs_embeds = img_embeds.unsqueeze(dim=1)

  patches = vl_gpt.gen_vision_model.decode_code(
    generated_tokens.to(dtype=torch.int),
    shape=[parallel_size, 8, width // patch_size, height // patch_size])

  return generated_tokens.to(dtype=torch.int), patches


def unpack(dec, width, height, parallel_size=2):
  dec = dec.to(torch.float32).cpu().numpy().transpose(0, 2, 3, 1)
  dec = np.clip((dec + 1) / 2 * 255, 0, 255)

  visual_img = np.zeros((parallel_size, width, height, 3), dtype=np.uint8)
  visual_img[:, :, :] = dec

  return visual_img


@torch.inference_mode()
def generate_image(
  vl_gpt: MultiModalityCausalLM,
  vl_chat_processor: VLChatProcessor,
  prompt: str,
  seed=None,
  guidance=5,
  t2i_temperature=1.0,
  width=384,
  height=384,
  parallel_size=2,
  image_token_num_per_image=576,
  device='cuda'):

  # Clear CUDA cache and avoid tracking gradients
  torch.cuda.empty_cache()

  # Set the seed for reproducible results
  if seed is not None:
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    np.random.seed(seed)

  tokenizer = vl_chat_processor.tokenizer

  with torch.no_grad():
    messages = [{'role': '<|User|>', 'content': prompt},
                {'role': '<|Assistant|>', 'content': ''}]

    text = vl_chat_processor.apply_sft_template_for_multi_turn_prompts(
      conversations=messages,
      sft_format=vl_chat_processor.sft_format,
      system_prompt='')

    text = text + vl_chat_processor.image_start_tag

    input_ids = torch.LongTensor(tokenizer.encode(text))
    _, patches = generate(
      vl_gpt,
      vl_chat_processor,
      input_ids,
      width // 16 * 16,
      height // 16 * 16,
      cfg_weight=guidance,
      parallel_size=parallel_size,
      temperature=t2i_temperature,
      image_token_num_per_image=image_token_num_per_image,
      device=device)

    images = unpack(
      patches,
      width // 16 * 16,
      height // 16 * 16,
      parallel_size=parallel_size)

    return [Image.fromarray(images[i]).resize((768, 768), Image.LANCZOS) for i in range(parallel_size)]


def predict_fn(input_data, model_and_processor, context=None):
  '''
  # visual-question-answering (vqa) task parameter schema
  input_data = {
    "prompt": "text",  # required
    "images": [image], # required

    # the followings are optional
    "task": "visual-question-answering",
    "generate_kwargs": {
      "top_p": 0.95,
      "temperature": 1.0,
      "max_new_tokens": 512
    }
  }

  # text-to-image task parameter schema
  input_data = {
    "prompt": "text",

    # the followings are optional
    "task": "text-to-image",
    "generate_kwargs": {
      "guidance": 5,
      "temperature": 1.0,
      "parallel_size": 2,
      "image_token_num_per_image": 576
    }
  }
  '''

  DEFAULT_SEED = 42

  model, processor = model_and_processor

  if isinstance(input_data, str):
    prediction = generate_image(
      vl_gpt=model,
      vl_chat_processor=processor,
      prompt=input_data,
      seed=DEFAULT_SEED,
      device=CUDA_DEVICE)
  elif isinstance(input_data, dict):
    if input_data.get('task', None) == "visual-question-answering" or input_data.get('images', None):
      images, question = input_data['images'], input_data['prompt']
      generate_kwargs = input_data.get('generate_kwargs', {})

      prediction = multimodal_understanding(
        vl_gpt=model,
        vl_chat_processor=processor,
        images=images,
        question=question,
        seed=generate_kwargs.get('seed', DEFAULT_SEED),
        top_p=generate_kwargs.get('top_p', 0.95),
        temperature=generate_kwargs.get('temperature', 1.0),
        max_new_tokens=generate_kwargs.get('max_new_tokens', 512),
        device=CUDA_DEVICE)
    elif input_data.get('task', "text-to-image") == "text-to-image":
      prompt = input_data['prompt']
      generate_kwargs = input_data.get('generate_kwargs', {})

      prediction = generate_image(
        vl_gpt=model,
        vl_chat_processor=processor,
        prompt=prompt,
        seed=generate_kwargs.get('seed', DEFAULT_SEED),
        guidance=generate_kwargs.get('guidance', 5),
        t2i_temperature=generate_kwargs.get('temperature', 1.0),
        width=generate_kwargs.get('width', 384),
        height=generate_kwargs.get('height', 384),
        parallel_size=generate_kwargs.get('parallel_size', 2),
        image_token_num_per_image=generate_kwargs.get('image_token_num_per_image', 576),
        device=CUDA_DEVICE)
  else:
    raise Exception(f'Requested invalid parameter type: {type(input_data)}')

  return prediction


def decode_json(content):
  return json.loads(content)


def input_fn(input_data, content_type, context=None):
  """
  The input_fn is responsible for deserializing the input data into
  an object for prediction, can handle JSON.
  The input_fn can be overridden for data or feature transformation.

  Args:
    input_data: the request payload serialized in the content_type format.
    content_type: the request content_type.
    context (obj): metadata on the incoming request data (default: None).

  Returns:
    decoded_input_data (dict): deserialized input_data into a Python dictonary.
  """

  if content_type == "application/json":
    decoded_input_data = decode_json(input_data)
  elif content_type == "application/x-text":
    decoded_input_data = input_data.decode('utf-8')
  else:
    raise Exception(f'Requested unsupported ContentType in Accept: {content_type}')
  return decoded_input_data



# https://github.com/automl/SMAC3/issues/453
class _JSONEncoder(json.JSONEncoder):
  """
  custom `JSONEncoder` to make sure float and int64 ar converted
  """

  def default(self, obj):
    if isinstance(obj, np.integer):
      return int(obj)
    elif isinstance(obj, np.floating):
      return float(obj)
    elif hasattr(obj, "tolist"):
      return obj.tolist()
    elif isinstance(obj, datetime.datetime):
      return obj.__str__()
    elif isinstance(obj, Image.Image):
      with BytesIO() as out:
        obj.save(out, format="PNG")
        png_string = out.getvalue()
        return base64.b64encode(png_string).decode("utf-8")
    else:
      return super(_JSONEncoder, self).default(obj)


def encode_json(content, accept_type=None):
  """
  encodes json with custom `JSONEncoder`
  """
  return json.dumps(
    content,
    ensure_ascii=False,
    allow_nan=False,
    indent=None,
    cls=_JSONEncoder,
    separators=(",", ":"),
  )


def output_fn(prediction, accept, context=None):
  """
  The output_fn is responsible for serializing the prediction result to
  the desired accept type, can handle JSON.
  The output_fn can be overridden for inference response transformation.

  Args:
    prediction (dict): a prediction result from predict.
    accept (str): type which the output data needs to be serialized.
    context (obj): metadata on the incoming request data (default: None).
  Returns: output data serialized
  """
  return encode_json(prediction, accept)
