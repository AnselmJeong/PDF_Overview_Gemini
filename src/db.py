from pathlib import Path

from sqlalchemy.engine.base import Engine
from sqlmodel import create_engine, Session, SQLModel, select
from classes import SummaryDB, ChatMessageDB, NotesDB

DB_PATH = Path("db/summaries.db")
engine = create_engine(f"sqlite:///{DB_PATH}")


def initialize_db(engine: Engine):
    SQLModel.metadata.create_all(engine)

def get_notes(pdf_stem: str, engine: Engine) -> list[dict]:
    with Session(engine) as session:
        statement = select(NotesDB).where(NotesDB.pdf_stem == pdf_stem)
        notes = session.exec(statement).all()
        notes_dict = [note.model_dump() for note in notes]
        return notes_dict
    
def save_note(note: dict, engine: Engine) -> None:
    with Session(engine) as session:
        note_db = NotesDB(**note)
        session.add(note_db)
        session.commit()
        session.refresh(note_db)


def get_chat_messages(pdf_stem: str, engine: Engine) -> list[dict]:
    with Session(engine) as session:
        statement = select(ChatMessageDB).where(ChatMessageDB.pdf_stem == pdf_stem)
        chat_messages = session.exec(statement).all()
        chat_messages_dict = [chat_message.model_dump() for chat_message in chat_messages]
        return chat_messages_dict


def save_chat_message(chat_messages: list[dict], pdf_stem: str, engine: Engine) -> None:
    with Session(engine) as session:
        for chat_message in chat_messages:
            chat_message_db = ChatMessageDB(**chat_message, pdf_stem=pdf_stem)
            if chat_message_db.save:
                session.add(chat_message_db)
                session.commit()
                session.refresh(chat_message_db)
                





def get_summary(pdf_name: str, engine: Engine):
    with Session(engine) as session:
        summarydb = session.get(SummaryDB, pdf_name)
        return summarydb
    
def save_summary(summary_db: SummaryDB, engine: Engine):
    with Session(engine) as session:
        session.add(summary_db)
        session.commit()
        session.refresh(summary_db)

    return summary_db

def format_summary(summary: SummaryDB):
    # modified_section_summaries = [ss.replace("\\n", "\n") for ss in summary.section_summaries]

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
### Section Summaries
{"\n\n".join(summary.section_summaries)}
"""


def write_summary(summary: SummaryDB, pdf_path: Path):
    with open(f"{pdf_path.stem}_summary.md", "w") as f:
        f.write(format_summary(summary))
        