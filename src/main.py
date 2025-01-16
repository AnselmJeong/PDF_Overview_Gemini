# %%
import os
import toml
from pathlib import Path
from instructor.exceptions import InstructorRetryException

# from dotenv import load_dotenv
import instructor
from openai import OpenAI

from classes import Essentials, SectionSummaries, SummaryDB
from db import engine, save_summary, get_summary, write_summary, initialize_db
from docling_loader import DoclingPDFLoader

from argparse import ArgumentParser
from dotenv import load_dotenv

load_dotenv()

MODEL_NAME = "deepseek-chat"
PROMPTS_PATH = Path("src/prompts.toml")
MAX_RETRIES = 3

with open(PROMPTS_PATH, "r") as f:
    prompts = toml.load(f)


ESSENTIALS_PROMPT = prompts["essentials"]["prompt"]
SECTION_SUMMARIES_PROMPT = prompts["section_summaries"]["prompt"]


# Initialize the client
client = instructor.from_openai(
    OpenAI(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("DEEPSEEK_BASE_URL"),
    ),
    mode=instructor.Mode.JSON,
)


def upload_pdf(pdf_path: Path) -> str:
    loader = DoclingPDFLoader(pdf_path)
    return loader.load()


def summarize(pdf_path: Path) -> SummaryDB:
    pdf_stem = pdf_path.stem

    if summary_db := get_summary(pdf_stem, engine):
        print("Summary already exists in database")
        return {"summary": summary_db, "exists": True}

    else:
        print("Summary does not exist in database, creating new summary")
        content = upload_pdf(pdf_path)
        print("Converted to markdown")

        try:
            essentials = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "user", "content": [ESSENTIALS_PROMPT, content]},
                ],
                response_model=Essentials,
                max_retries=MAX_RETRIES,
            )
            print("Extracted essentials")
        except InstructorRetryException as e:
            print(f"Retry Error: {e}\n\n")
            return {"summary": None, "exists": True}

        section_summaries_prompt = SECTION_SUMMARIES_PROMPT.format(toc=essentials.toc)

        try:
            section_summaries = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "user", "content": [section_summaries_prompt, content]},
                ],
                response_model=SectionSummaries,
                max_retries=MAX_RETRIES,
            )
            print("Extracted section summaries")
        except InstructorRetryException as e:
            print(f"Retry Error: {e}\n\n")
            return {"summary": None, "exists": True}
        summary_db = SummaryDB(
            pdf_stem=pdf_stem, md_content=content, **essentials.model_dump(), **section_summaries.model_dump()
        )
        print("Created summary db")
        return {"summary": summary_db, "exists": False}


def directory_summarize(directory: Path, write_md: bool = False):
    for pdf_path in directory.glob("*.pdf"):
        print(f"Summarizing {pdf_path.stem}")
        payload = summarize(Path(pdf_path))
        if not payload["exists"]:
            save_summary(payload["summary"], engine)
            if write_md:
                write_summary(payload["summary"], pdf_path)


def main(pdf_path: Path | None = None, directory: Path | None = None, write_md: bool = False):
    if directory:
        directory_summarize(directory, write_md)
    else:
        payload = summarize(pdf_path)
        if not payload["exists"]:
            save_summary(payload["summary"], engine)
            if write_md:
                write_summary(payload["summary"], pdf_path)
        return payload["summary"]


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("pdf_path", nargs="?", type=str)
    parser.add_argument("--directory", "-d", nargs="?", type=str)
    parser.add_argument("--write_md", "-w", action="store_true")

    args = parser.parse_args()

    pdf_path = Path(args.pdf_path) if args.pdf_path else None
    directory = Path(args.directory) if args.directory else None
    initialize_db(engine)

    main(pdf_path, directory, args.write_md)
