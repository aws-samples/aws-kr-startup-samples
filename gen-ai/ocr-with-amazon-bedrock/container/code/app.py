#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import base64

import streamlit as st
from PIL import Image

import claude3_boto3_ocr as llm_app
# import claude3_langchain_ocr as llm_app


def main():
  chain = llm_app.build_chain()

  st.set_page_config(layout="wide", page_title="Image Understanding")
  st.title("Image Understanding")
  st.write("Upload an image and see any text found in the image!")

  uploaded_file = st.file_uploader("Choose an image", type=["jpg", "jpeg", "png"])

  if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption=f"Uploaded Image: {uploaded_file.name}")

    bytes_data = uploaded_file.getvalue()
    base64_image = base64.b64encode(bytes_data).decode("utf-8")

    st.subheader("Output")
    text = llm_app.run_chain(chain, base64_image)
    st.write(text)


if __name__ == "__main__":
  main()
