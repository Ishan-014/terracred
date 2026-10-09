from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import fitz
import pytesseract
from fastapi import APIRouter, File, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

router = APIRouter(prefix="/api/udyam", tags=["Udyam"])
UPLOAD_DIR = Path("data") / "udyam_uploads"
MAX_BYTES = 10 * 1024 * 1024
ALLOWED_TYPES = {
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": ".jpg",
}


def _extract_text(content: bytes, content_type: str) -> tuple[str, str]:
    """Extract embedded PDF text first, then use Tesseract OCR as a fallback."""
    if content_type == "application/pdf":
        try:
            with fitz.open(stream=content, filetype="pdf") as document:
                embedded = "\n".join(page.get_text("text") for page in document).strip()
                if len(embedded) >= 40:
                    return embedded, "embedded_text"
                pages = [page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).tobytes("png")
                         for page in list(document)[:4]]
            text = "\n".join(
                pytesseract.image_to_string(Image.open(BytesIO(page)), config="--psm 6")
                for page in pages
            ).strip()
            return text, "ocr" if text else "no_text"
        except pytesseract.TesseractNotFoundError as exc:
            raise RuntimeError("Tesseract OCR is not installed. Install Tesseract OCR and ensure tesseract.exe is on PATH.") from exc
        except Exception as exc:
            if isinstance(exc, RuntimeError):
                raise
            raise RuntimeError(f"Could not read this PDF: {exc}") from exc

    try:
        image = Image.open(BytesIO(content)).convert("RGB")
        text = pytesseract.image_to_string(image, config="--psm 6").strip()
        return text, "ocr" if text else "no_text"
    except pytesseract.TesseractNotFoundError as exc:
        raise RuntimeError("Tesseract OCR is not installed. Install Tesseract OCR and ensure tesseract.exe is on PATH.") from exc
    except (UnidentifiedImageError, OSError) as exc:
        raise RuntimeError("Could not read this image. Try a clearer PNG or JPG.") from exc


def _field(text: str, labels: list[str]) -> str | None:
    """Read common label/value layouts found on Udyam certificates."""
    lines = [re.sub(r"\s+", " ", line).strip(" :\t") for line in text.splitlines()]
    for i, line in enumerate(lines):
        for label in labels:
            match = re.search(rf"(?i)\b{label}\b\s*[:\-]?\s*(.*)$", line)
            if match:
                value = match.group(1).strip(" :-")
                if value and not re.fullmatch(r"(?i)(yes|no|details|particulars)", value):
                    return value[:300]
                for next_line in lines[i + 1:i + 3]:
                    if next_line and not any(re.search(rf"(?i)\b{x}\b", next_line) for x in labels):
                        return next_line[:300]
    return None


def _parse_certificate(text: str) -> dict:
    business_name = _field(text, [
        r"name of enterprise", r"name of the enterprise", r"enterprise name",
        r"name of entrepreneur", r"name of unit"
    ])
    activity = _field(text, [r"major activity", r"main activity", r"activity"])
    address = _field(text, [
        r"official address of enterprise", r"official address", r"address of enterprise",
        r"enterprise address", r"address"
    ])
    udyam_number = _field(text, [
        r"udyam registration number", r"udyam registration no", r"udyam reg(?:istration)? no"
    ])
    organization_type = _field(text, [
        r"type of organisation", r"type of organization", r"organisation type", r"organization type"
    ])
    registration_date = _field(text, [
        r"date of incorporation", r"date of registration", r"registration date"
    ])
    industry = None
    if activity:
        lowered = activity.lower()
        industry = "Manufacturing" if "manufactur" in lowered else (
            "Services" if "service" in lowered else activity
        )
    # If OCR fails to capture an enterprise name, leave it blank for user correction.
    return {
        "business_name": business_name,
        "industry": industry,
        "business_address": address,
        "udyam_registration_number": udyam_number,
        "organization_type": organization_type,
        "major_activity": activity,
        "registration_date": registration_date,
    }


@router.post("/upload")
async def upload_udyam_certificate(file: UploadFile = File(...)):
    """Store a certificate and extract business fields using text extraction/OCR."""
    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="Upload a PDF, PNG, or JPG Udyam certificate.")

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

    try:
        text, extraction_method = _extract_text(content, content_type)
        extracted_fields = _parse_certificate(text)
        extracted_count = sum(bool(value) for value in extracted_fields.values())
        extraction_status = "completed" if extracted_count else "no_fields_found"
        message = (
            f"Extracted {extracted_count} fields. Review them before generating the score."
            if extracted_count else
            "Text was read, but no familiar Udyam fields were detected. Enter the missing details manually."
        )
        return {
            "upload_id": upload_id,
            "filename": Path(file.filename or f"udyam{suffix}").name,
            "content_type": content_type,
            "size_bytes": len(content),
            "status": "uploaded",
            "extraction_status": extraction_status,
            "extraction_method": extraction_method,
            "extracted_fields": extracted_fields,
            "message": message,
            "verification_status": "unverified",
        }
    except RuntimeError as exc:
        return {
            "upload_id": upload_id,
            "filename": Path(file.filename or f"udyam{suffix}").name,
            "content_type": content_type,
            "size_bytes": len(content),
            "status": "uploaded",
            "extraction_status": "failed",
            "extracted_fields": {},
            "message": str(exc),
            "verification_status": "unverified",
        }
