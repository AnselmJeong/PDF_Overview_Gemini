import streamlit as st
from streamlit import session_state as sss
from streamlit_file_browser import st_file_browser

from streamlit_dimensions import st_dimensions

from pathlib import Path
import re
from openai import OpenAI

from db import engine, get_summary, format_summary
from sqlmodel import Session
from streamlit_pdf_viewer import pdf_viewer
from main import main
from meta_prompt import generate_prompt

st.set_page_config(layout="wide")
MODEL_NAME = "gpt-4o-mini"
client = OpenAI()


if "messages" not in sss:
    sss.messages = []
if "summary_content" not in sss:
    sss.summary_content = ""
if "md_content" not in sss:
    sss.md_content = ""
if "prompt" not in sss:
    sss.prompt = ""
if "file_name" not in sss:
    sss.file_name = ""


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
        new_file_name = pdf_path.stem
        if new_file_name != sss.file_name:
            sss.messages = []
        sss.file_name = new_file_name
        # pdf_path = file_path.parent / (file_name.replace('_overview', '') + '.pdf')
        if raw_summary := get_summary(sss.file_name, engine):
            sss.summary_content = format_summary(raw_summary)
            sss.md_content = raw_summary.md_content
        else:
            info_container.info(f"Summarizing {sss.file_name}")
            with st.status("Summarizing...") as status:
                sss.summary_content = main(pdf_path, write_md=False)
                sss.md_content = sss.summary_content.md_content
                sss.summary_content = format_summary(sss.summary_content)

        sss.summary_content = re.sub(r"\*\*(.*?)\*\*", r":orange[\1]", sss.summary_content)

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
            with st.expander("Markdown", expanded=True):
                md_container = st.container()
            with st.expander("Chat", expanded=True):
                chat_container = st.container()

            if sss.summary_content:
                md_container.markdown(sss.summary_content)
            else:
                md_container.markdown("No summary found")

            for message in sss.messages:
                with chat_container.chat_message(message["role"]):
                    st.markdown(message["content"])

            sss.prompt = chat_container.chat_input("Ask questions about the document")
            if sss.prompt and sss.md_content != "":
                # Add user message to chat history
                sss.prompt = generate_prompt(sss.prompt)
                
                sss.messages.append({"role": "user", "content": sss.prompt})
                # Display user message in chat message container
                with chat_container.chat_message("user"):
                    st.markdown(sss.prompt)
                with chat_container.chat_message("assistant"):
                    stream = client.chat.completions.create(
                        model=MODEL_NAME,
                        messages=[{"role": m["role"], "content": m["content"]} for m in sss.messages]
                        + [{"role": "user", "content": sss.md_content}],
                        stream=True,
                    )
                    response = st.write_stream(stream)
                    sss.messages.append({"role": "assistant", "content": response})
