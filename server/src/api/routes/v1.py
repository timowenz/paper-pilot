import logging
from urllib.parse import quote

from fastapi import APIRouter, UploadFile, File
from fastapi.responses import Response

from api.services.upload import read_upload
from api.services.parser import parse_pdf_to_chunks
from api.services.spellcheck import check_all_chunks
from api.services.coherence import check_coherence
from api.services.annotator import locate_errors_in_pdf, annotate_pdf

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/analyze-pdf")
async def analyze_pdf(file: UploadFile = File(...)):
    pdf_bytes, original_name = await read_upload(file)

    try:
        logger.info("analyze-pdf: parsing %s (%d bytes)", original_name, len(pdf_bytes))
        chunks, whitelist = parse_pdf_to_chunks(pdf_bytes)

        logger.info("analyze-pdf: spellcheck (%d chunks)", len(chunks))
        results = check_all_chunks(chunks, whitelist)

        logger.info(
            "analyze-pdf: locate in PDF (%d chunk(s) with hits)", len(results)
        )
        located = locate_errors_in_pdf(pdf_bytes, results, chunks)

        logger.info("analyze-pdf: coherence (LLM)")
        findings, evaluation = check_coherence(chunks)

        logger.info("analyze-pdf: annotate PDF")
        annotated_bytes = annotate_pdf(
            pdf_bytes, located, findings, evaluation, chunks
        )
    except Exception:
        logger.exception(
            "analyze-pdf failed for %r (see traceback above for stage)",
            original_name,
        )
        raise

    filename = f"{original_name}_annotated.pdf"
    return Response(
        content=annotated_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"
        },
    )
