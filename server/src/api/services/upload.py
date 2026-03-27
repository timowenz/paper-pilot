import os

from fastapi import UploadFile, HTTPException


async def read_upload(file: UploadFile) -> tuple[bytes, str]:
    """Read the uploaded PDF into memory and return (pdf_bytes, original_name).

    Nothing is written to disk.
    """
    file_extension = os.path.splitext(file.filename or "")[1].lower()
    if file_extension != ".pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
    original_name = os.path.splitext(file.filename or "upload")[0]
    pdf_bytes = await file.read()
    return pdf_bytes, original_name
