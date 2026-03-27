from urllib.parse import quote

from fastapi import APIRouter, UploadFile, File
from fastapi.responses import Response

from api.services.upload import read_upload
from api.services.parser import parse_pdf_to_chunks
from api.services.spellcheck import check_all_chunks
from api.services.coherence import check_coherence
from api.services.annotator import locate_errors_in_pdf, annotate_pdf

router = APIRouter()


@router.post("/analyze-pdf")
async def analyze_pdf(file: UploadFile = File(...)):
    pdf_bytes, original_name = await read_upload(file)

    chunks, whitelist = parse_pdf_to_chunks(pdf_bytes)

    results = check_all_chunks(chunks, whitelist)
    located = locate_errors_in_pdf(pdf_bytes, results, chunks)

    findings = check_coherence(chunks)

    annotated_bytes = annotate_pdf(pdf_bytes, located, findings)

    filename = f"{original_name}_annotated.pdf"
    return Response(
        content=annotated_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"
        },
    )
