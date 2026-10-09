from __future__ import annotations

import html
import os

import requests
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

load_dotenv()
router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


class EmailReportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recipient_email: str = Field(min_length=5, max_length=254)
    business_name: str = Field(min_length=1, max_length=200)
    report: dict


def _safe(value) -> str:
    if value is None:
        return "Not available"
    if isinstance(value, (dict, list)):
        value = str(value)
    return html.escape(str(value))


def _report_html(payload: EmailReportRequest) -> str:
    report = payload.report
    score = report.get("climate_adjusted_credit_score")
    baseline = report.get("baseline_credit_score", 750)
    risk = report.get("experimental_climate_risk_indicator")
    band = report.get("credit_score_band", "Insufficient evidence")
    explanation = report.get("evidence_explanation") or {}
    summary = explanation.get("summary") or "No plain-language explanation was returned."
    business_problem = explanation.get("business_problem")
    adjustment = report.get("climate_adjustment_points")
    score_text = _safe(score) if score is not None else "Insufficient evidence"
    evidence_items = report.get("evidence_items") or []
    evidence_html = "".join(
        "<li><b>" + _safe(item.get("label") or item.get("hazard_type")) + "</b>: "
        + _safe(item.get("plain_explanation") or item.get("observed_value"))
        + (" (Observed: " + _safe(item.get("observed_value")) + " " + _safe(item.get("unit", "")) + ")" if item.get("observed_value") is not None else "")
        + "</li>"
        for item in evidence_items[:20]
    ) or "<li>No specific evidence items were returned.</li>"
    warnings = report.get("warnings") or []
    warnings_html = "".join("<li>" + _safe(item) + "</li>" for item in warnings[:20]) or "<li>No backend warnings were returned.</li>"
    limitations = explanation.get("evidence_limitations") or []
    limitations_html = "".join("<li>" + _safe(item) + "</li>" for item in limitations[:20])
    adjustment_text = "Not available" if adjustment is None else f"{int(adjustment):+d} points"
    problem_html = "<p><b>Possible business problem:</b> " + _safe(business_problem) + "</p>" if business_problem else ""
    return f"""<!doctype html><html><body style="font-family:Arial,sans-serif;color:#18342b;line-height:1.55;max-width:760px;margin:auto">
    <div style="background:#eaf6ef;padding:24px;border-radius:12px"><h1 style="margin:0;color:#176b4d">TerraCred</h1><p style="margin-bottom:0">Onsite climate-risk assessment report</p></div>
    <h2>{_safe(payload.business_name)}</h2>
    <p><b>Assessment status:</b> {_safe(band)}</p>
    <table style="border-collapse:collapse;width:100%"><tr><td style="padding:12px;border:1px solid #d5e4dc">Assumed baseline score</td><td style="padding:12px;border:1px solid #d5e4dc"><b>{_safe(baseline)}</b></td></tr>
    <tr><td style="padding:12px;border:1px solid #d5e4dc">Climate-adjusted score</td><td style="padding:12px;border:1px solid #d5e4dc"><b>{score_text}</b> ({_safe(band)})</td></tr>
    <tr><td style="padding:12px;border:1px solid #d5e4dc">Climate risk indicator</td><td style="padding:12px;border:1px solid #d5e4dc">{_safe(risk)} / 100</td></tr>
    <tr><td style="padding:12px;border:1px solid #d5e4dc">Score adjustment</td><td style="padding:12px;border:1px solid #d5e4dc">{_safe(adjustment_text)}</td></tr></table>
    <h3>Summary</h3><p>{_safe(summary)}</p>{problem_html}
    <h3>Evidence and possible impacts</h3><ul>{evidence_html}</ul>
    <h3>Data warnings</h3><ul>{warnings_html}</ul>
    {"<h3>Evidence limitations</h3><ul>" + limitations_html + "</ul>" if limitations_html else ""}
    <hr><p style="font-size:12px;color:#536b61">Hackathon demonstration only. The baseline and score-band mapping are illustrative, not a validated lending score. Weather observations do not prove property damage, flooding, or supplier disruption. Do not use this output by itself to approve or reject credit.</p>
    </body></html>"""


@router.post("/email-report")
def email_report(payload: EmailReportRequest):
    """Email the assessment report through Twilio SendGrid."""
    api_key = os.getenv("SENDGRID_API_KEY", "").strip()
    from_email = os.getenv("SENDGRID_FROM_EMAIL", "").strip()
    from_name = os.getenv("SENDGRID_FROM_NAME", "TerraCred Reports").strip()
    if not api_key or not from_email:
        raise HTTPException(
            status_code=503,
            detail="Email delivery is not configured. Set SENDGRID_API_KEY and SENDGRID_FROM_EMAIL in backend/.env.",
        )
    if "@" not in payload.recipient_email or "." not in payload.recipient_email.rsplit("@", 1)[-1]:
        raise HTTPException(status_code=422, detail="Enter a valid recipient email address.")
    body = {
        "personalizations": [{"to": [{"email": payload.recipient_email.strip()}]}],
        "from": {"email": from_email, "name": from_name},
        "subject": f"TerraCred climate-risk report — {payload.business_name}",
        "content": [{"type": "text/html", "value": _report_html(payload)}],
    }
    try:
        response = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=body,
            timeout=15,
        )
        if response.status_code not in (200, 202):
            detail = f"SendGrid rejected the email (HTTP {response.status_code}). Check the API key and verified sender."
            raise HTTPException(status_code=502, detail=detail)
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Email delivery failed: {type(exc).__name__}.") from exc
    return {"status": "sent", "recipient_email": payload.recipient_email.strip(), "message": f"Report emailed to {payload.recipient_email.strip()}."}
