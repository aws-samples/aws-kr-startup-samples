#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os
import torch
from transformers import BitsAndBytesConfig
from transformers import pipeline


def model_fn(model_dir, context=None):
  task = os.environ.get('HF_TASK', 'image-to-text')

  quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.float16
  )

  hf_pipeline = pipeline(
    task=task,
    model=model_dir,
    model_kwargs={
      "quantization_config": quantization_config,
      "device_map": "auto",
      "torch_dtype": "auto"
    },
    tokenizer=model_dir
  )
  return hf_pipeline


def predict_fn(data, model, context=None):
  # pop inputs for pipeline
  # The pipeline handles three types of images:
  # - A string containing a HTTP(s) link pointing to an image
  # - A string containing a local path to an image
  # - An image loaded in PIL directly
  # The pipeline accepts either a single image or a batch of images.
  inputs = data.pop("inputs", data)
  parameters = data.pop("parameters", None)

  # pass inputs with all kwargs in data
  if parameters is not None:
    prediction = model(inputs, **parameters)
  else:
    prediction = model(inputs)
  return prediction