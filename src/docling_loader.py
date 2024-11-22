from pathlib import Path
from typing import Iterator
from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document as LCDocument

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat


pipeline_options = PdfPipelineOptions()
# pipeline_options.do_ocr = False


class DoclingPDFLoader(BaseLoader):
    def __init__(self, file_path: str) -> None:
        if not Path(file_path).exists():
            raise FileNotFoundError(f"File {file_path} does not exist")
        self._file_paths = Path(file_path)
        self._converter = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
        )

    def load(self) -> str:
        dl_doc = self._converter.convert(self._file_paths).document
        text = dl_doc.export_to_markdown()

        index_of_references = text.lower().find("references")
        return text[:index_of_references]
