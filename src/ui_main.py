import streamlit as st
from streamlit_file_browser import st_file_browser

from streamlit_dimensions import st_dimensions

from pathlib import Path
import re

from db import engine, get_summary, format_summary
from sqlmodel import Session
from streamlit_pdf_viewer import pdf_viewer
from main import main

st.set_page_config(layout="wide")


st.markdown(
    """
<style>

[data-testid="stMarkdown"] h1 {
    font-size:2rem !important;
}
</style>
""",
    unsafe_allow_html=True,
)

root = ""
SCROLL_HEIGHT = 2000
# Create a file browser component in the sidebar
with st.sidebar:
    st.markdown("## File Browser")
    if root := st.text_input("PDF Directory", placeholder="Directory to browse"):
        event = st_file_browser(
            path=root,
            key="file_browser",
            extentions=["pdf"],
            show_choose_file=False,
            show_download_file=False,
            show_preview=False,
            use_cache=False,
        )
    else:
        st.warning("Please enter a directory to browse")
        event = None

pdf_content = None
content = None

info_container = st.container()

# Main content area
with Session(engine) as session:
    if event and event["type"] == "SELECT_FILE":
        pdf_path = Path(root, event["target"]["path"])
        file_name = pdf_path.stem
        # pdf_path = file_path.parent / (file_name.replace('_overview', '') + '.pdf')
        if file_name:
            if raw_summary := get_summary(file_name, engine):
                summary_content = format_summary(raw_summary)

            else:
                info_container.info(f"Summarizing {file_name}")
                summary_content = main(pdf_path, write_md=False)
                summary_content = format_summary(summary_content)

            summary_content = re.sub(r"\*\*(.*?)\*\*", r":orange[\1]", summary_content)

            pdf_content = pdf_path.read_bytes()
        col1, col2 = st.columns([1.5, 1])
        with col1.container(height=SCROLL_HEIGHT):
            if pdf_content:
                pdf_viewer(
                    pdf_content,
                    width=st_dimensions("col1")["width"],
                    height=SCROLL_HEIGHT,
                    render_text=True,
                )

        with col2.container(height=SCROLL_HEIGHT):
            md_container = st.container()
            if summary_content:
                md_container.markdown(summary_content)
            else:
                md_container.markdown("No summary found")
