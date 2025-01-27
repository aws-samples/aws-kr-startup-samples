#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=4 shiftwidth=4 softtabstop=4 expandtab

from djl_python.huggingface import HuggingFaceService
from djl_python.chat_completions.chat_utils import is_chat_completions_request
from djl_python.chat_completions.chat_properties import ChatProperties
from djl_python.inputs import Input
from djl_python.outputs import Output
from djl_python.encode_decode import encode, decode
import logging
import types

_service = HuggingFaceService()


def parse_chat_completions_request(inputs: map, is_rolling_batch: bool,
                                   tokenizer):
    if not hasattr(tokenizer, "apply_chat_template"):
        raise AttributeError(
            f"Cannot provide chat completion for tokenizer: {tokenizer.__class__}, "
            f"please ensure that your tokenizer supports chat templates.")
    chat_params = ChatProperties(**inputs)
    _param = chat_params.model_dump(by_alias=True, exclude_none=True)
    _messages = _param.pop("messages")
    _inputs = tokenizer.apply_chat_template(_messages, tokenize=False, add_generation_prompt=True)

    _param["do_sample"] = chat_params.temperature is not None and chat_params.temperature > 0.0
    _param["details"] = True  # Enable details for chat completions
    _param["output_formatter"] = "jsonlines_chat" if chat_params.stream else "json_chat"

    return _inputs, _param


def parse_inputs_params(input_map, item, input_format_configs):
    if is_chat_completions_request(input_map):
        _inputs, _param = parse_chat_completions_request(
            input_map, input_format_configs.is_rolling_batch,
            input_format_configs.tokenizer)
    else:
        _inputs = input_map.pop("inputs", input_map)
        _param = input_map.pop("parameters", {})

    if input_format_configs.is_rolling_batch:
        _param["stream"] = input_map.pop("stream", False)

    if "cached_prompt" in input_map:
        _param["cached_prompt"] = input_map.pop("cached_prompt")
    if "seed" not in _param:
        # set server provided seed if seed is not part of request
        if item.contains_key("seed"):
            _param["seed"] = item.get_as_string(key="seed")
    if not "output_formatter" in _param:
        _param["output_formatter"] = input_format_configs.output_formatter

    if isinstance(_inputs, list):
        return _inputs, _param, True
    else:
        return [_inputs], _param, False


def custom_input_formatter(self, inputs: Input, tokenizer, output_formatter) -> tuple[list[str], list[int], list[dict], dict, list]:

    input_data = []
    input_size = []
    parameters = []
    adapters = []
    errors = {}
    found_adapters = False
    batch = inputs.get_batches()

    # only for dynamic batch
    is_client_side_batch = [False for _ in range(len(batch))]
    for i, item in enumerate(batch):
        try:
            content_type = item.get_property("Content-Type")
            input_map = decode(item, content_type)
            _inputs, _param, is_client_side_batch[i] = parse_inputs_params(
                input_map, item, self.input_format_configs)

        except Exception as e:  # pylint: disable=broad-except
            logging.warning(f"Parse input failed: {i}")
            input_size.append(0)
            errors[i] = str(e)
            continue

        input_data.extend(_inputs)
        input_size.append(len(_inputs))

        for _ in range(input_size[i]):
            parameters.append(_param)

    return input_data,input_size, parameters, errors, batch


def handle(inputs: Input):
    """
    Default handler function
    """
    if not _service.initialized:
        # stateful model
        props = inputs.get_properties()
        print(f"props: {props}")
        # props['output_formatter'] = custom_output_formatter
        _service.initialize(props)
        _service.parse_input = types.MethodType(custom_input_formatter, _service)

    if inputs.is_empty():
        # initialization request
        return None

    return _service.inference(inputs)
