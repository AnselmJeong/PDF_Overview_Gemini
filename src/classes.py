from sqlmodel import SQLModel, Field, Column, JSON, Relationship
from pydantic import BaseModel
from pydantic import Field as PField

# SQLModel.__table_args__ = {'extend_existing': True}
# Define your output structure
class Essentials(BaseModel):
    title: str = PField(description="The title of the document", default="")
    authors: list[str] = PField(description="The authors of the document", default=[])
    tldr: str = PField(description="A TLDR summary of the document", default="")
    key_takeaways: list[str] = PField(description="A list of key takeaways from the document", default=[])
    important_point: str = PField(description="An important point from the document", default="")
    toc: str = PField(description="A table of contents of the document", default="")


class SectionSummaries(BaseModel):
    section_summaries: list[str] = PField(description="A list of summaries of the sections in a document", default=[])


# class Summary(BaseModel):
#     pdf_hash: str = PField(description="Hash of the document")
#     file_handle: str | None = PField(description="Google file handle of the uploaded document")
#     title: str = PField(description="The title of the document")
#     authors: list[str] | None = PField(description="The authors of the document")
#     tldr: str | None = PField(description="A TLDR summary of the document")
#     key_takeaways: list[str] | None = PField(description="A list of key takeaways from the document")
#     important_point: str | None = PField(description="A important point from the document")
#     toc: str | None = PField(description="A table of contents of the document")
#     section_summaries: list[str] | None = PField(description="A list of section summaries of the document")


class SummaryDB(SQLModel, table=True):
    pdf_stem: str = Field(primary_key=True)
    md_content: str | None = Field(default=None)
    title: str | None = Field(default=None)
    authors: list[str] | None = Field(default=None, sa_column=Column(JSON))
    tldr: str | None = Field(default=None)
    key_takeaways: list[str] | None = Field(default=None, sa_column=Column(JSON))
    important_point: str | None = Field(default=None)
    toc: str | None = Field(default=None)
    section_summaries: list[str] | None = Field(default=None, sa_column=Column(JSON))
    chat_messages: list["ChatMessageDB"] | None = Relationship(back_populates="summary")
    notes: list["NotesDB"] | None = Relationship(back_populates="summary")
class ChatMessageDB(SQLModel, table=True):
    id: str = Field(primary_key=True)
    role: str
    content: str
    save: bool
    pdf_stem: str | None = Field(default=None, foreign_key="summarydb.pdf_stem")
    summary: SummaryDB | None = Relationship(back_populates="chat_messages")
class NotesDB(SQLModel, table=True):
    id: str = Field(primary_key=True)
    notes: str
    pdf_stem: str | None = Field(default=None, foreign_key="summarydb.pdf_stem")
    summary: SummaryDB | None = Relationship(back_populates="notes")