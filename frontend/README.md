# TerraCred frontend

React + Vite interface for the existing TerraCred FastAPI backend.

## Run locally

From the repository root, pull the latest changes and install frontend dependencies:

```powershell
git pull --ff-only origin main
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Open the local Vite URL printed in the terminal (normally `http://localhost:5173`).

In a second terminal, start the backend from the repository root:

```powershell
cd E:\terracred
.\.venv\Scripts\Activate.ps1
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

The frontend uses `VITE_API_BASE_URL` from `.env`, defaulting to `http://127.0.0.1:8000`.

## Assessment workflow

1. Enter a business profile and location coordinates.
2. Add supplier relationships and procurement concentration where known.
3. Record critical operations, fallback capacity, critical inputs, inventory and substitution options.
4. Save the profile or run the assessment.
5. Review the backend-generated indicator, dimension scores, evidence source metadata, missing inputs and warnings.

The frontend does not calculate the climate-risk score. It displays the result returned by the backend scoring engine. The current scoring method is experimental and illustrative, does not estimate a validated probability of loss, and must not be used as a lending decision. Use synthetic data for demonstrations unless you have permission to process real business data.
