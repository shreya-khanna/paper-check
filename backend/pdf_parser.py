"""
Step 1: Parse a paper PDF with Docling.

Input:  path to a PDF file
Output: dict with:
  - "markdown": full structured markdown (headings preserved) -> fed to the LLM
  - "text": plain text fallback
  - "num_pages": int
  - "tables": list of table markdown strings
"""

from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend

# Initialize converter using PyPdfium backend for maximum stability on Windows / Python 3.13
_converter = DocumentConverter(
    allowed_formats=[InputFormat.PDF],
    format_options={
        InputFormat.PDF: PdfFormatOption(backend=PyPdfiumDocumentBackend)
    }
)

def parse_paper(pdf_path: str) -> dict:
    result = _converter.convert(pdf_path)
    doc = result.document

    markdown = doc.export_to_markdown()

    tables = []
    for table in getattr(doc, "tables", []):
        try:
            tables.append(table.export_to_markdown(doc=doc))
        except Exception:
            pass  # skip a table if it fails to export

    return {
        "markdown": markdown,
        "text": markdown,
        "num_pages": len(doc.pages) if hasattr(doc, "pages") else None,
        "tables": tables,
        "source_path": pdf_path,
    }

