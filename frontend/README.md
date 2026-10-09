# TerraCred frontend

React + Vite interface for the TerraCred FastAPI backend.

## Run locally (Windows PowerShell)

From the repository root:

```powershell
git pull --ff-only origin main
..venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
npm --prefix frontend install
```

### Enable OCR for scanned certificates

TerraCred first extracts embedded text from digital PDFs. For scanned PDFs and JPG/PNG certificates, it uses Tesseract OCR.

1. Install **Tesseract OCR for Windows** using a trusted Windows installer.
2. Ensure the installed `tesseract.exe` directory is on your system `PATH`.
3. Open a new PowerShell terminal and verify it with:

```powershell
tesseract --version
```

If Tesseract is not installed, digital PDFs may still work when they contain selectable text; scanned files will show an OCR setup message.

## Start the backend

From the repository root, in one terminal:

```powershell
..venv\Scripts\Activate.ps1
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

## Start the frontend

In a second terminal:

```powershell
cd frontend
Copy-Item .env.example .env
npm run dev
```

Open the local Vite URL printed in the terminal (normally `http://localhost:5173`). The frontend uses `VITE_API_BASE_URL` from `.env`, defaulting to `http://127.0.0.1:8000`.

## Udyam-to-score workflow

1. Upload a Udyam certificate as PDF, PNG, or JPG.
2. TerraCred extracts embedded PDF text or runs OCR on scanned documents/images.
3. Business name, activity/industry and address are prefilled when detected. Review and correct the fields; OCR output is not officially verified.
4. Enter the business latitude/longitude and the few required supplier/dependency details.
5. Generate the climate-adjusted score from the existing backend assessment engine.

OCR can misread text or miss fields depending on certificate quality and layout. The user must review extracted fields. Udyam certificates do not contain a credit score; the prototype uses its explicitly labelled illustrative baseline and penalty mapping. The output is a hackathon demonstration, not a validated lending score or lending decision. Use synthetic data unless you have permission to process real business documents.
