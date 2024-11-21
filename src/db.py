from pathlib import Path

from sqlalchemy.engine.base import Engine
from sqlmodel import create_engine, Session, SQLModel
from classes import SummaryDB

DB_PATH = Path("db/summaries.db")
engine = create_engine(f"sqlite:///{DB_PATH}")


def initialize_db(engine: Engine):
    SQLModel.metadata.create_all(engine)


def save_summary(summary_db: SummaryDB, engine: Engine):
    with Session(engine) as session:
        session.add(summary_db)
        session.commit()
        session.refresh(summary_db)

    return summary_db


def format_summary(summary: SummaryDB):
    modified_section_summaries = [ss.replace("\\n", "\n") for ss in summary.section_summaries]

    return f"""
# {summary.title}\n\n
#### {", ".join(summary.authors)}\n\n
### TL;DR\n
{summary.tldr}\n\n
### Key Takeaways\n
{"\n".join([f"- {kta}" for kta in summary.key_takeaways])}\n\n
### Important Point\n
{summary.important_point}\n\n
- - -
{"\n\n".join(modified_section_summaries)}
"""


def write_summary(summary: SummaryDB, pdf_path: Path):
    with open(f"{pdf_path.stem}_summary.md", "w") as f:
        f.write(format_summary(summary))


def get_summary(pdf_name: str, engine: Engine):
    with Session(engine) as session:
        summarydb = session.get(SummaryDB, pdf_name)
        return summarydb
