import fitz
import pymupdf4llm
from api.services.cleaner import clean_markdown, split_into_chunks, extract_document_terms


def parse_pdf_to_markdown(pdf_bytes: bytes) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    return pymupdf4llm.to_markdown(doc)


def parse_pdf_to_chunks(pdf_bytes: bytes) -> tuple[list[dict], set[str]]:
    raw_markdown = parse_pdf_to_markdown(pdf_bytes)
    whitelist = extract_document_terms(raw_markdown)
    cleaned = clean_markdown(raw_markdown)
    return split_into_chunks(cleaned), whitelist
