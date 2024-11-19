# %%
import time
import toml
from pathlib import Path
from instructor.exceptions import InstructorRetryException
# from dotenv import load_dotenv
import instructor
import google.generativeai as genai
from google.ai.generativelanguage_v1beta.types.file import File

from classes import Essentials, SectionSummaries, SummaryDB
from db import engine, save_summary, get_summary, write_summary, initialize_db
from argparse import ArgumentParser
# load_dotenv()

MODEL_NAME = "gemini-1.5-flash"
PROMPTS_PATH = Path("src/prompts.toml")
MAX_RETRIES = 3

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

def upload_pdf(pdf_path: Path) -> File:
    file = genai.upload_file(pdf_path)
    while file.state != File.State.ACTIVE:
        time.sleep(1)
        file = genai.get_file(file.name)
    return file


def summarize(pdf_path: Path) -> SummaryDB:
    
    pdf_stem = pdf_path.stem
    
    if summary_db := get_summary(pdf_stem, engine):
        print("Summary already exists in database")
        return {'summary': summary_db, 'exists': True}
    
    else:
        print("Summary does not exist in database, creating new summary")
        file = upload_pdf(pdf_path)
    
        try:
            essentials = client.chat.completions.create(
                messages=[
                {"role": "user", "content": [ESSENTIALS_PROMPT, file]},
                ],
                response_model=Essentials,
                max_retries=MAX_RETRIES
            )
        except InstructorRetryException as e:
            print(f"Retry Error: {e}\n\n")
            return {'summary': None, 'exists': True}

        section_summaries_prompt = SECTION_SUMMARIES_PROMPT.format(toc=essentials.toc)

        try:
            section_summaries = client.chat.completions.create(
                messages=[
                {"role": "user", "content": [section_summaries_prompt, file]},
            ],
            response_model=SectionSummaries,
                max_retries=MAX_RETRIES
            )
        except InstructorRetryException as e:
            print(f"Retry Error: {e}\n\n")
            return {'summary': None, 'exists': True}
        summary_db = SummaryDB(pdf_stem=pdf_stem,
                            file_handle=file.name, 
                            **essentials.model_dump(), 
                            **section_summaries.model_dump())

        return {'summary': summary_db, 'exists': False}


def directory_summarize(directory: Path):
    for pdf_path in directory.glob("*.pdf"):
        print(f"Summarizing {pdf_path.stem}")
        payload = summarize(Path(pdf_path))
        if not payload['exists']:
            save_summary(payload['summary'], engine)
            write_summary(payload['summary'], pdf_path)


def main(pdf_path: Path | None, directory: Path | None):

    if directory:
        directory_summarize(directory)
    else:
        payload = summarize(pdf_path)
        if not payload['exists']:
            save_summary(payload['summary'], engine)
            write_summary(payload['summary'], pdf_path)

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('pdf_path', nargs='?', type=str)
    parser.add_argument("--directory", "-d", nargs='?', type=str)
    
    args = parser.parse_args()
    
    pdf_path = Path(args.pdf_path) if args.pdf_path else None
    directory = Path(args.directory) if args.directory else None
    initialize_db(engine)
   
    main(pdf_path, directory)