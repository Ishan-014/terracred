from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile

router = APIRouter(prefix="/api/udyam", tags=["Udyam"])
UPLOAD_DIR = Path("data") / "udyam_uploads"
MAX_BYTES = 10 * 1024 * 1024
ALLOWED_TYPES = {
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": ".jpg",
}


@router.post("/upload")
async def upload_udyam_certificate(file: UploadFile = File(...)):
    """Store a user-provided certificate locally for this prototype.

    This endpoint stores the file but does not OCR or verify certificate contents.
    """
    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Upload a PDF, PNG, or JPG Udyam certificate.",
        )

    content = await file.read(MAX_BYTES + 1)
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(content) > MAX_BYTES:
        raise HTTPException(status_code=413, detail="Maximum certificate size is 10 MB.")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    upload_id = uuid4().hex
    suffix = ALLOWED_TYPES[content_type]
    stored_path = UPLOAD_DIR / f"{upload_id}{suffix}"
    stored_path.write_bytes(content)
    return {
        "upload_id": upload_id,
        "filename": Path(file.filename or f"udyam{suffix}").name,
        "content_type": content_type,
        "size_bytes": len(content),
        "status": "uploaded",
        "extraction_status": "not_performed",
        "message": "Certificate stored locally. Details must be entered manually; the certificate is not OCR-verified.",
    }
