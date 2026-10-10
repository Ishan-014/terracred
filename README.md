# TerraCred 🌍

### Explainable Climate Risk Intelligence for Micro, Small and Medium Enterprises (MSMEs)

TerraCred is a climate-risk assessment prototype designed to help understand how weather-related disruptions, operational vulnerabilities, and supplier dependencies may affect MSMEs. It combines business information, location-specific weather evidence, and transparent risk indicators to produce an explainable climate-adjusted assessment for further review.

Instead of treating a single score as the whole story, TerraCred presents the underlying evidence, contributing risk dimensions, missing information, and limitations so that users can understand why a business may be exposed to climate-related disruption.

> **Project status:** Experimental prototype for demonstration and research. TerraCred does not produce a validated credit score, predict actual financial losses, or make lending decisions.

---

## 🎯 Problem Statement

MSMEs may be financially vulnerable to extreme weather and disruptions affecting their business premises, raw materials, transport routes, utilities, and suppliers.

Traditional financial assessments may not explicitly capture these climate-related operational dependencies. At the same time, weather information alone cannot establish whether a particular business will suffer damage or financial loss.

TerraCred explores how these different signals can be brought together into a transparent, evidence-based assessment that helps identify potential risks requiring further investigation.

## 💡 Our Solution

TerraCred combines business onboarding, weather evidence, operational context, and supplier information in a single assessment workflow.

### Key Features

- **Udyam certificate onboarding:** Upload a PDF, PNG, or JPG certificate and extract available business information using PDF text extraction or OCR.
- **Business profile management:** Record business activity, location, critical raw materials, operational dependencies, and supporting evidence.
- **Weather intelligence:** Retrieve historical weather observations and forecast data from Open-Meteo for supported locations.
- **Supplier dependency analysis:** Record supplier locations, materials supplied, procurement concentration, criticality, and alternative suppliers.
- **Climate-risk assessment:** Calculate an experimental indicator using available hazard, operational vulnerability, and supplier dependency evidence.
- **Industry and material relevance:** Apply explicit prototype rules to connect weather signals with plausible business disruption pathways.
- **Explainable results:** Display contributing indicators, observed values, evidence sources, missing inputs, and warnings.
- **AI-assisted explanations:** Optionally use an OpenAI model to translate structured evidence into plain language, with a deterministic fallback when AI is unavailable.
- **Assessment report delivery:** Optionally send reports through the configured SendGrid email integration.

## 🔄 How It Works

1. **Upload a business document**  
   Upload a Udyam certificate to prefill business information where fields can be extracted.

2. **Review the information**  
   Correct extracted fields and provide the business location, coordinates, activity, operational dependencies, and relevant materials.

3. **Add supplier information**  
   Record supplier locations, materials supplied, criticality, procurement shares where known, and whether alternatives exist.

4. **Collect weather evidence**  
   Retrieve available historical or forecast weather data for the relevant business and supplier locations.

5. **Validate the inputs**  
   Check coordinates, supported weather measurements, verification status, and missing information. Incomplete evidence is surfaced rather than automatically treated as safe.

6. **Calculate the experimental indicator**  
   Evaluate the available hazard, operational vulnerability, and supplier dependency dimensions using the prototype's rule-based calculations.

7. **Generate an explanation**  
   Present the contributing evidence and limitations. AI-assisted explanations are optional and do not calculate or modify the score.

8. **Review and share the report**  
   Inspect the results and, when configured, deliver the report to the designated reviewer through email.

## 🧮 Risk Assessment Methodology

TerraCred currently uses a transparent, rule-based prototype rather than a trained machine-learning model.

### 1. Hazard indicator

Weather observations may include:

- Maximum daily precipitation
- Maximum daily wind speed
- Percentage of observed days exceeding the configured high-temperature threshold

The prototype uses available weather indicators and basic normalization rules to construct an illustrative hazard dimension.

Business-location and supplier-location evidence are evaluated separately where relevant. Weather observations are connected to business activities and materials using explicit prototype relevance rules.

### 2. Operational vulnerability

Operational vulnerability considers known dependencies such as:

- Critical operations without a fallback
- Critical inputs without a substitute

The prototype averages the available, known vulnerability shares. Missing information is not automatically interpreted as zero risk.

### 3. Supplier dependency

Supplier dependency considers indicators such as:

- Concentration of procurement in the largest supplier
- Share of critical suppliers without an alternative
- Relevant supplier-location weather evidence

Supplier records and dependency summaries are maintained separately from the conventional credit assessment.

### 4. Overall climate-risk indicator

For the core prototype, the overall indicator is the arithmetic mean of the available numeric risk dimensions:

\[
R=\frac{\sum_{i=1}^{n}D_i}{n}
\]

Where:

- \(R\) = experimental climate-risk indicator
- \(D_i\) = an available numeric risk dimension
- \(n\) = number of available numeric dimensions

The indicator is presented on a 0–100 scale when the contributing dimensions support that scale. Missing dimensions are excluded from the arithmetic mean and disclosed through warnings; they are not assumed to be safe.

### 5. Demonstration climate-adjusted score

The current demonstration interface maps the climate-risk indicator to an illustrative baseline score.

\[
A=\operatorname{clamp}(\operatorname{round}(0.5(R-50)),-25,25)
\]

\[
S_{\text{adjusted}}=\operatorname{clamp}(S_{\text{baseline}}-A,300,900)
\]

Where:

- \(R\) = experimental climate-risk indicator
- \(A\) = signed illustrative adjustment
- \(S_{\text{baseline}}\) = assumed baseline score
- \(S_{\text{adjusted}}\) = demonstration score after adjustment

The default demonstration baseline is 750. The displayed bands are Poor (300–549), Fair (550–649), Good (650–749), and Excellent (750–900).

**These formulas and bands are demonstration assumptions, not validated financial-risk or credit-scoring methodologies.** The baseline is not obtained from a Udyam certificate, and the output must not be used to approve or reject real loans.

For the detailed methodology, see [`docs/climate_risk_prototype.md`](docs/climate_risk_prototype.md).

## 🛠️ Technology Stack

| Component | Technology | Purpose |
|---|---|---|
| Frontend | React, TypeScript, Vite | User interface and assessment workflow |
| Backend | Python, FastAPI | API endpoints and application logic |
| Data validation | Pydantic | Structured API inputs and outputs |
| Persistence | SQLite | Local business and supplier records |
| Data processing | NumPy, Pandas | Numerical and tabular processing |
| Weather evidence | Open-Meteo | Historical weather and forecast data |
| Document extraction | PyMuPDF, pytesseract, Pillow | PDF text extraction and image OCR |
| AI explanations | OpenAI API, optional | Plain-language evidence summaries |
| Email delivery | SendGrid, optional | Assessment report delivery |
| Testing | pytest | Backend tests |

## 🏗️ Architecture

```text
                 ┌────────────────────────┐
                 │   React + Vite UI      │
                 │ Business onboarding    │
                 │ Assessment dashboard   │
                 └───────────┬────────────┘
                             │ HTTP / JSON
                 ┌───────────▼────────────┐
                 │     FastAPI Backend    │
                 ├────────────────────────┤
                 │ Business & Suppliers   │
                 │ Udyam Document Upload  │
                 │ Weather Data Services  │
                 │ Hazard Assessment      │
                 │ Climate Risk Engine    │
                 │ Explanation & Reports  │
                 └─────┬─────────┬────────┘
                       │         │
              ┌────────▼───┐ ┌───▼────────────────┐
              │ SQLite DB  │ │ External Services  │
              │ Local Data │ │ Open-Meteo         │
              └────────────┘ │ OpenAI (optional)  │
                             │ SendGrid (optional)│
                             └────────────────────┘
```

The frontend communicates with the backend over HTTP. The backend orchestrates data validation, weather retrieval, business and supplier records, risk calculations, explanations, and optional report delivery.

## 📁 Repository Structure

```text
terracred/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── business.py
│   │   │   ├── climate_risk.py
│   │   │   ├── datasets.py
│   │   │   ├── email_report.py
│   │   │   ├── hazards.py
│   │   │   ├── udyam.py
│   │   │   ├── weather.py
│   │   │   └── weather_features.py
│   │   ├── business/
│   │   ├── data/
│   │   ├── hazards/
│   │   ├── scoring/
│   │   └── main.py
│   ├── tests/
│   └── requirements.txt
├── docs/
│   ├── business_supplier_model.md
│   ├── climate_risk_prototype.md
│   ├── data_sources.md
│   ├── onsite_report_email.md
│   └── operational_vulnerability.md
├── frontend/
│   ├── src/
│   ├── .env.example
│   ├── package.json
│   └── README.md
├── .env.example
└── README.md
```

## 🚀 Getting Started

### Prerequisites

Install the following:

- Python 3.10 or later
- Node.js and npm
- Git
- Tesseract OCR, if scanned-document OCR is required

### 1. Clone the repository

```bash
git clone https://github.com/Ishan-014/terracred.git
cd terracred
```

### 2. Configure the backend

Create a Python virtual environment.

**Windows PowerShell:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
```

**Linux/macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

Create a root environment file by copying the example.

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Linux/macOS:

```bash
cp .env.example .env
```

The application uses SQLite by default. The example configuration sets the database path to `./data/terracred.db`.

Optional environment variables:

```dotenv
TERRACRED_DB_PATH=./data/terracred.db

OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini

SENDGRID_API_KEY=
SENDGRID_FROM_EMAIL=
SENDGRID_FROM_NAME=TerraCred Reports
```

OpenAI is optional for explanations. Configure SendGrid credentials and a verified sender if email delivery is required. Never commit real API keys or secrets.

### 3. Start the backend

From the repository root, with the virtual environment activated:

```bash
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

The backend should be available at:

- API root: `http://127.0.0.1:8000/`
- Health check: `http://127.0.0.1:8000/health`
- Interactive API documentation: `http://127.0.0.1:8000/docs`

### 4. Configure and start the frontend

Open a second terminal:

```bash
cd frontend
npm install
```

Create the frontend environment file.

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Linux/macOS:

```bash
cp .env.example .env
```

The frontend API configuration is:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Start the development server:

```bash
npm run dev
```

Open the URL printed by Vite, normally `http://localhost:5173`.

### 5. Enable OCR for scanned documents

TerraCred first attempts to extract embedded text from digital PDFs. Scanned PDFs and image uploads require OCR.

Install Tesseract OCR using a trusted installer, ensure its executable is on your system `PATH`, and verify the installation:

```bash
tesseract --version
```

OCR may misread or omit fields. Always review extracted business information before continuing.

### 6. Run backend tests

From the repository root, with the virtual environment activated:

```bash
python -m pytest backend/tests
```

## 🔌 API Overview

The FastAPI application registers routes for the following capabilities:

| Capability | Purpose |
|---|---|
| Business profiles | Create, retrieve, update, and validate business information |
| Supplier management | Record supplier relationships and dependency information |
| Weather | Retrieve weather evidence for supported locations |
| Weather features | Generate weather-derived indicators |
| Hazard assessment | Evaluate available hazard evidence |
| Climate-risk assessment | Calculate the experimental risk indicator and explanation |
| Udyam upload | Extract available business fields from uploaded certificates |
| Email reports | Support configured assessment report delivery |
| Datasets | Expose dataset-related functionality |

Interactive API documentation at `/docs` is the recommended reference for request schemas, exact route paths, parameters, and responses.

## 🌦️ Data Sources

### Open-Meteo

Used by the backend for weather evidence, including historical archive and forecast requests where available.

Variables include maximum and minimum daily temperature, daily precipitation, and maximum daily wind speed.

Source: https://open-meteo.com/

### World Bank Climate Change Knowledge Portal

Documented as a research source for long-term climate baselines and projections. It is not currently wired into the backend API.

Source: https://climateknowledgeportal.worldbank.org/

### Flood hazard datasets

Official and research datasets are documented as potential future inputs. A dependable, automated property-level flood-data integration is not currently part of the prototype.

See [`docs/data_sources.md`](docs/data_sources.md) for access status, intended use, and limitations.

## ⚠️ Limitations and Responsible Use

TerraCred is an experimental prototype and has important limitations:

- The risk indicator is rule-based and has not been scientifically calibrated or independently validated.
- Weather observations at coordinates do not establish property-level flood probability, actual damage, or financial loss.
- A high daily rainfall value does not by itself prove that a location is flood-prone.
- OCR extracts document text; it does not authenticate a Udyam certificate or verify business identity with an authoritative government service.
- Supplier relationships and procurement shares must be supplied and supported by evidence; they must not be invented.
- Missing or unverified inputs reduce confidence in the assessment and should be surfaced explicitly.
- The illustrative climate-adjusted score is not a conventional credit score or a validated prediction of default.
- AI-generated explanations may be imperfect. They are intended to summarize supplied evidence, not replace the deterministic scoring engine.
- Production deployment would require security controls, privacy safeguards, access management, monitoring, calibrated models, and independent validation.

**Do not use TerraCred's current prototype score to make real lending, credit approval, or rejection decisions.**

Use synthetic data for demonstrations unless you have appropriate authorization to process real business documents.

## 🗺️ Roadmap

Potential future improvements include:

- Integration of authoritative flood-hazard and regional climate datasets.
- Better geospatial exposure analysis for business and supplier locations.
- More robust data provenance, verification, and completeness reporting.
- Validated climate-disruption and financial-impact models.
- Improved assessment history, monitoring, and change detection.
- Stronger security, multi-user support, and production deployment.
- Independent calibration and evaluation before any financial decision-support use.

These are proposed directions, not claims about existing functionality.

## 📚 Documentation

- [Climate-risk prototype and scoring methodology](docs/climate_risk_prototype.md)
- [Business and supplier data model](docs/business_supplier_model.md)
- [Data sources and evidence status](docs/data_sources.md)
- [Operational vulnerability model](docs/operational_vulnerability.md)
- [On-site report email workflow](docs/onsite_report_email.md)

## 🤝 Contributing

Contributions, issue reports, and suggestions are welcome.

1. Fork the repository.
2. Create a feature branch.
3. Make focused changes and add appropriate tests.
4. Run the available backend tests and frontend build.
5. Open a pull request describing the change and any assumptions.

## 📄 License

No license is specified here. Add a `LICENSE` file before describing the repository as open-source or granting reuse permissions.

---

**TerraCred — Making climate-related MSME risk more transparent, explainable, and evidence-driven.**
