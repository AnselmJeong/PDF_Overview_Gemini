import streamlit as st
from streamlit import session_state as sss

from streamlit_file_browser import st_file_browser

from streamlit_dimensions import st_dimensions
from streamlit_extras.row import row

from pathlib import Path
import re
import uuid
from openai import OpenAI

from db import engine, get_summary, format_summary, save_chat_message, get_chat_messages, get_notes, save_note
# from db import initialize_db
# initialize_db(engine)

from sqlmodel import Session
from streamlit_pdf_viewer import pdf_viewer
from main import main
from meta_prompt import generate_prompt

st.set_page_config(layout="wide", page_title="PDF Overviewer", initial_sidebar_state="expanded")
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
if "pdf_stem" not in sss:
    sss.pdf_stem = ""
if "prev_chat_messages" not in sss:
    sss.prev_chat_messages = []
if "notes" not in sss:
    sss.notes = []
if "pdf_content" not in sss:
    sss.pdf_content = None

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

def checkbox_callback(message_id: str):
    for message in sss.messages:
        if message["id"] == message_id:
            message["save"] = not message["save"]

def display_message(message: dict):
    row1 = row([6,1], vertical_align="top")
    row1.markdown(message["content"])
    row1.checkbox("Save", value=message["save"], key=f"save_{message['id']}", on_change=checkbox_callback, args=[message["id"]])
    
def on_note_change():
    if note := sss['new_note']:
        new_note = {"id": str(uuid.uuid4()), "notes": note, "pdf_stem": sss.pdf_stem}
        save_note(new_note, engine)
        sss.notes.append({"id": str(uuid.uuid4()), "notes": note, "pdf_stem": sss.pdf_stem})
        sss['new_note'] = ""

root = ""
SCROLL_HEIGHT = 2000
# Create a file browser component in the sidebar
with st.sidebar:
    st.title(":red[PDF Overviewer] :sunglasses:")
    if root := st.text_input("Directory", placeholder="Directory to browse", label_visibility="collapsed"):
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
        new_pdf_stem = pdf_path.stem
        
        if new_pdf_stem != sss.pdf_stem:
            if sss.messages:
                save_chat_message(sss.messages, sss.pdf_stem, engine)
                sss.messages = []
            
            sss.pdf_stem = new_pdf_stem
        
            if raw_summary := get_summary(sss.pdf_stem, engine):
                sss.summary_content = format_summary(raw_summary)
                sss.md_content = raw_summary.md_content
            else:
                info_container.info(f"Summarizing {sss.pdf_stem}")
                with st.status("Summarizing...") as status:
                    sss.summary_content = main(pdf_path, write_md=False)
                    sss.md_content = sss.summary_content.md_content
                    sss.summary_content = format_summary(sss.summary_content)

            sss.notes = get_notes(sss.pdf_stem, engine)
            sss.summary_content = re.sub(r"\*\*(.*?)\*\*", r":orange[\1]", sss.summary_content)
            sss.prev_chat_messages = get_chat_messages(sss.pdf_stem, engine)
            sss.pdf_content = pdf_path.read_bytes()

        col1, col2 = st.columns([1.5, 1])
        
        with col1.container(height=SCROLL_HEIGHT):
            try:
                col_width = st_dimensions("col1")["width"]
            except Exception:
                col_width = 1000
            
            if sss.pdf_content:
                pdf_viewer(
                    sss.pdf_content,
                    width=col_width,
                    height=SCROLL_HEIGHT,
                    render_text=True,
                )

        with col2.container(height=SCROLL_HEIGHT):
            with st.expander("Notes", expanded=True):
                notes_container = st.container()
            with st.expander("Overview", expanded=True):
                md_container = st.container()
            with st.expander("Previous Chat", expanded=False):
                prev_chat_container = st.container()
            with st.expander("Current Chat", expanded=True):
                curr_chat_container = st.container()

            notes_container.text_area("Add Note", key="new_note", on_change=on_note_change)
            
            if sss.notes:
                for note in sss.notes:
                    notes_container.markdown(f'- {note["notes"]}')
                
            # Display markdown summary
            if sss.summary_content:
                md_container.markdown(sss.summary_content)
            else:
                md_container.markdown("No summary found")
                
            if sss.prev_chat_messages:
                for message in sss.prev_chat_messages:
                    with prev_chat_container.chat_message(message["role"]):
                        display_message(message)
            
            # Display chat history
            for message in sss.messages:
                with curr_chat_container.chat_message(message["role"]):
                    display_message(message)
                    
                    # st.checkbox("Save", key=f"message_save")

            # Add user message to chat history
            sss.prompt = curr_chat_container.chat_input("Ask questions about the document")
            if sss.prompt and sss.md_content != "":
                # Generate prompt for LLM
                with st.status("Generating prompt...") as status:
                    updated_prompt = generate_prompt(sss.prompt)
                
                # Add user message to chat history
                sss.messages.append({"id": str(uuid.uuid4()), "role": "user", "content": sss.prompt, "save": False})
                # Display user message in chat message container
                with curr_chat_container.chat_message("user"):
                    display_message(sss.messages[-1])
                with curr_chat_container.chat_message("assistant"):
                    stream = client.chat.completions.create(
                        model=MODEL_NAME,
                        messages=[{"role": m["role"], "content": m["content"]} for m in sss.messages[:-1]]
                        + [{"role": "user", "content": f"{updated_prompt}\n\nCONTEXT:\n{sss.md_content}"}],
                        stream=True,
                    )
                    temp_id = str(uuid.uuid4())
                    temp_row = row([6,1], vertical_align="top")
                    response = temp_row.write_stream(stream)
                    temp_row.checkbox("Save", key=f"save_{temp_id}")
                    
                    sss.messages.append({"id": temp_id, "role": "assistant", "content": response, "save": False})
