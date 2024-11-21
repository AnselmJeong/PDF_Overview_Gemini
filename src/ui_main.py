import streamlit as st
from streamlit_file_browser import st_file_browser

# from streamlit_pdf_viewer import pdf_viewer
# from streamlit_pdf_reader import pdf_reader
from streamlit_dimensions import st_dimensions

from pathlib import Path
import re

from db import engine, get_summary, format_summary
from sqlmodel import Session
from streamlit_pdf_viewer import pdf_viewer

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

ROOT = "docs"
SCROLL_HEIGHT = 2000
# Create a file browser component in the sidebar
with st.sidebar:
    st.markdown("## File Browser")
    event = st_file_browser(
        path=ROOT,
        key="file_browser",
        extentions=["pdf"],
        show_choose_file=False,
        show_download_file=False,
        show_preview=False,
        use_cache=False,
    )

pdf_content = None
content = None

# Main content area
with Session(engine) as session:
    if event and event["type"] == "SELECT_FILE":
        pdf_path = Path(ROOT, event["target"]["path"])
        file_name = pdf_path.stem
        # pdf_path = file_path.parent / (file_name.replace('_overview', '') + '.pdf')
        if file_name:
            summary_content = format_summary(get_summary(file_name, engine))
            summary_content = re.sub(r"\*\*(.*?)\*\*", r":orange[\1]", summary_content)

            # with open(pdf_path, "rb") as file:
            #     pdf_content = file.read()
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
            if summary_content:
                st.markdown(summary_content)
            else:
                st.markdown("No summary found")
