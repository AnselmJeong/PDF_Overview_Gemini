import streamlit as st
import base64

from pathlib import Path


def view_pdf(pdf_file: Path):
    bytes_data = pdf_file.read_bytes()
    base64_pdf = base64.b64encode(bytes_data).decode("utf-8", "ignore")
    data = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="1000" type="application/pdf">'
    st.markdown(data, unsafe_allow_html=True)


def displayPDF(pdf_file: Path):
    # Read file as bytes:
    markdown_data = f"""
<iframe src="{pdf_file}" width="100%" height="1000">
</iframe>
"""
    st.markdown(markdown_data, unsafe_allow_html=True)
