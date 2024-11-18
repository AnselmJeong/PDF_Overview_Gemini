# %%
import time
import toml
import sqlite3
from pathlib import Path
from dotenv import load_dotenv
import instructor
import google.generativeai as genai
from google.ai.generativelanguage_v1beta.types.file import File
from pydantic import BaseModel, Field


load_dotenv()

MODEL_NAME = "gemini-exp-1114"
PDF_PATH = Path("../docs/Fugure of ChatGPT.pdf")
PROMPTS_PATH = Path("./prompts.toml")
GENAI_HANDLES_PATH = Path("./genai_handles.toml")
DB_PATH = Path("./summaries.db")
with open(PROMPTS_PATH, "r") as f:
    prompts = toml.load(f)


ESSENTIALS_PROMPT = prompts["essentials"]["prompt"]
SECTION_SUMMARIES_PROMPT = prompts["section_summaries"]["prompt"]


# Initialize the client
client = instructor.from_gemini(
    client=genai.GenerativeModel(
        model_name=MODEL_NAME,
    )
)
# %%


# Define your output structure
class Essentials(BaseModel):
    title: str = Field(description="The title of the document")
    authors: list[str] = Field(description="The authors of the document")
    tldr: str = Field(description="A TLDR summary of the document")
    key_takeaways: list[str] = Field(description="A list of key takeaways from the document")
    important_point: str = Field(description="A important point from the document")
    toc: str = Field(description="A table of contents of the document")


class SectionSummaries(BaseModel):
    summaries: list[str] = Field(description="A list of summaries of the sections in a document")


def log_uploaded_file(pdf_path: Path, file: File, genai_handles_path: Path):
    with open(genai_handles_path, "w") as f:
        toml.dump({pdf_path.name: {"genai_handle": file.name}}, f)


def check_genai_handle(pdf_path: Path, toml_path: Path):
    with open(toml_path, "r") as f:
        genai_handles = toml.load(f)

    section = genai_handles.get(pdf_path.name, None)
    file_handle = section["genai_handle"] if section else None

    return file_handle


def upload_pdf(pdf_path: Path, genai_handles_path: Path):
    def _upload(pdf_path: Path):
        file = genai.upload_file(pdf_path)
        while file.state != File.State.ACTIVE:
            time.sleep(1)
            file = genai.get_file(file.name)

        print("File is now ready\n")
        log_uploaded_file(pdf_path, file, genai_handles_path)
        return file

    file_handle = check_genai_handle(pdf_path, genai_handles_path)

    if file_handle:
        print("File has been previously uploaded, trying to fetch\n")
        try:
            file = genai.get_file(file_handle)
        except Exception as e:
            print(f"Failed to fetch file: {e}\n")
            file = _upload(pdf_path)
    else:
        file = _upload(pdf_path)

    return file


def summarize(file: File):
    essentials = client.chat.completions.create(
        messages=[
            {"role": "user", "content": [ESSENTIALS_PROMPT, file]},
        ],
        response_model=Essentials,
    )

    section_summaries_prompt = SECTION_SUMMARIES_PROMPT.format(toc=essentials.toc)

    section_summaries = client.chat.completions.create(
        messages=[
            {"role": "user", "content": [section_summaries_prompt, file]},
        ],
        response_model=SectionSummaries,
    )

    return {"essentials": essentials, "section_summaries": section_summaries}


def format_summary(summary: dict):
    modified_summaries = [summary.replace("\\n", "\n") for summary in summary["section_summaries"].summaries]

    return f"""
    # {summary["essentials"].title}\n\n
    #### {", ".join(summary["essentials"].authors)}\n\n
    ### TL;DR\n
    {summary["essentials"].tldr}\n\n
    ### Key Takeaways\n
    {summary["key_takeaways"]}\n\n
    ### Important Point\n
    {summary["important_point"]}\n\n
    - - -
    {"\n\n".join(modified_summaries)}
    """


def write_summaries(summary: dict, pdf_path: Path):
    with open(pdf_path.stem.with_suffix("_summary.md"), "w") as f:
        f.write(format_summary(summary))


def save_sqlite(pdf_path: Path, summary: dict, db_path: Path = DB_PATH):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    pdf_hash = hash(pdf_path.stem)

    # Create table if it doesn't exist
    c.execute("""CREATE TABLE IF NOT EXISTS summaries
                     (pdf_hash TEXT PRIMARY KEY, summary TEXT)""")

    # Insert or replace the summary data
    c.execute(
        """INSERT OR REPLACE INTO summaries (pdf_hash, summary) VALUES (?, ?)""",
        (pdf_hash, format_summary(summary)),
    )

    # Commit the transaction and close the connection
    conn.commit()
    conn.close()


def main():
    file = upload_pdf(PDF_PATH, GENAI_HANDLES_PATH)

    summaries = summarize(file)

    write_summaries(summaries, PDF_PATH)
