#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import av

#XXX: Starting from version 12.2.1, `frame.index` will be deprecated.
# AVDeprecationWarning: Using `frame.index` is deprecated.
# Therefore, it is recommended to stay on version 12.2.0.
assert av.__version__ == '12.2.0'

import base64
import datetime
import json
import numpy as np
import os
import requests
from io import BytesIO
from PIL import Image

import torch
from transformers import (
  BitsAndBytesConfig,
  LlavaNextVideoForConditionalGeneration,
  LlavaNextVideoProcessor
)


def base64_to_pil_image(base64_string):
  image_bytes = base64.b64decode(base64_string)
  image_buffer = BytesIO(image_bytes)
  pil_image = Image.open(image_buffer).convert('RGB')
  return pil_image


def read_video_pyav(container, sampling_rate: int=8):
  total_frames = container.streams.video[0].frames
  # sample uniformly 8 frames from the video (we can sample more for longer videos)
  indices = np.arange(0, total_frames, total_frames / sampling_rate).astype(int)

  frames = []
  start_index = indices[0]
  end_index = indices[-1]
  for frame in container.decode(video=0):
    if frame.index > end_index:
      break
    if frame.index >= start_index and frame.index in indices:
      frames.append(frame.to_ndarray(format="rgb24"))
  return np.array(frames)


def read_video_from_url(url: str, sampling_rate: int=8):
  '''
  Decode the video with PyAV decoder.

  Args:
      url (str): video url.
      sampling_rate (int): sampling rate.

  Returns:
      np.ndarray: np array of decoded frames of shape (num_frames, height, width, 3).
  '''

  with av.open(requests.get(url, stream=True).raw) as container:
    frames_ndarray = read_video_pyav(container, sampling_rate)
  return frames_ndarray


def model_fn(model_dir, context=None):
  model_id = os.environ['HF_MODEL_ID']
  quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16
  )

  processor = LlavaNextVideoProcessor.from_pretrained(model_id)
  model = LlavaNextVideoForConditionalGeneration.from_pretrained(
    model_id,
    quantization_config=quantization_config,
    device_map='auto'
  )

  #XXX: In order to prevent the following warnings:
  # The model weights are not tied. Please use the `tie_weights` method before using the `infer_auto_device` function.
  model.tie_weights()

  return model, processor


def predict_fn(data, model_and_processor, context=None):
  model, processor = model_and_processor

  parameters = data.pop('parameters')

  # The prompt format looks as follows:
  #   USER: <video>\n<prompt> ASSISTANT:
  #   USER: <image>\n<prompt> ASSISTANT:
  input_data_types = []
  prompts = parameters.pop('prompts')
  for each in prompts:
    if each.startswith('USER: <video>'):
      input_data_types.append('video')
    elif each.startswith('USER: <image>'):
      input_data_types.append('image')
    else:
      raise ValueError('Invalid Prompt Format!')

  input_data_list = data.pop("inputs")
  assert len(input_data_types) == len(input_data_list), "Number of prompts does not match the number of inputs"

  image_list, video_list = [], []
  for idx, data_type in enumerate(input_data_types):
    input_data = input_data_list[idx]
    if data_type == 'image':
      if input_data.startswith('http://') or input_data.startswith('https://'):
        image = Image.open(requests.get(input_data, stream=True).raw)
      else:
        image = base64_to_pil_image(input_data)
      image_list.append(image)
    elif data_type == 'video':
      assert input_data.startswith('http://') or input_data.startswith('https://')
      sampling_rate = int(parameters.pop('sampling_rate', 8))
      video_clip = read_video_from_url(input_data, sampling_rate)
      video_list.append(video_clip)
    else:
      raise NotImplementedError()

  params = {
    "padding": True,
    "return_tensors": "pt"
  }

  if image_list:
    params['images'] = image_list
  if video_list:
    params['videos'] = video_list

  inputs = processor(prompts, **params).to(model.device)

  generate_kwargs = parameters.get('generate_kwargs', {})
  output = model.generate(**inputs, **generate_kwargs)
  prediction = processor.batch_decode(output, skip_special_tokens=True)

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
  assert content_type == "application/json"
  decoded_input_data = decode_json(input_data)
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
