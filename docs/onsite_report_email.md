# TerraCred onsite report email

TerraCred can email the generated climate-risk assessment to the person who will visit the business site. Email delivery uses **Twilio SendGrid** (Twilio's email product); a standard Twilio phone/SMS number is not used to send email.

## Configure SendGrid

1. Create or sign in to a Twilio SendGrid account.
2. Verify the sender identity/email address you plan to send from in SendGrid.
3. Create a SendGrid API key with Mail Send permission.
4. In the backend environment file (normally `backend/.env`), set:

```dotenv
SENDGRID_API_KEY=your_sendgrid_api_key
SENDGRID_FROM_EMAIL=verified-sender@example.com
SENDGRID_FROM_NAME=TerraCred Reports
```

Keep the real API key in `.env` only. Do not commit it to GitHub or put it in a `VITE_*` frontend variable. The root `.env.example` lists the required variable names.

## How it works

1. The assessment form asks for the onsite contact's email address.
2. After the backend returns the assessment, the frontend posts the report and recipient to `POST /api/notifications/email-report`.
3. The backend formats an HTML email with the score/band, baseline, score adjustment, explanation, evidence, warnings, and prototype limitations, then sends it through SendGrid.
4. The result screen shows whether delivery succeeded. A delivery/configuration failure does not discard the generated assessment.

## Local setup and test

Install/update backend dependencies in the existing virtual environment (the endpoint uses the already-installed `requests` package):

```powershell
python -m pip install -r backend/requirements.txt
```

Set the three variables in `backend/.env`, then restart the FastAPI backend. Generate an assessment with an onsite contact email. Check the result screen and the recipient inbox/spam folder.

The endpoint returns HTTP 503 when SendGrid is not configured and an error when SendGrid rejects the request. A successful SendGrid API response means accepted for processing, not guaranteed inbox delivery.

## Prototype limitations

- The email is an HTML report in the email body; it is not a PDF attachment.
- Only the configured recipient is sent the report.
- The assessment remains a hackathon prototype. Its score mapping is illustrative and not a validated lending score.
