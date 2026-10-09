import { useState } from "react";
import { ArrowRight, CheckCircle2, CloudRain, FileUp, Leaf, LoaderCircle, ShieldAlert, UploadCloud } from "lucide-react";
import "./styles.css";

const API = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
const initial = {
  business_name: "", industry: "Manufacturing", place_name: "", latitude: "", longitude: "",
  supplier_name: "", material_supplied: "", procurement_share: "40",
  alternative_supplier_available: false, critical_to_operations: true,
  fallback_available: false, verification_status: "unverified"
};
const bandCopy = {
  Poor: "Higher climate-adjustment impact",
  Fair: "Climate-adjusted score in the fair range",
  Good: "Climate-adjusted score in the good range",
  Excellent: "Climate-adjusted score in the excellent range"
};
function Field({ label, children, hint }) {
  return <label className="simple-field"><span>{label}</span>{children}{hint && <small>{hint}</small>}</label>;
}
export default function App() {
  const [form, setForm] = useState(initial);
  const [file, setFile] = useState(null);
  const [upload, setUpload] = useState(null);
  const [report, setReport] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [step, setStep] = useState(1);
  const change = (key, value) => setForm((old) => ({ ...old, [key]: value }));

  async function call(path, options = {}) {
    const response = await fetch(API + path, options);
    const raw = await response.text();
    let data;
    try { data = raw ? JSON.parse(raw) : {}; } catch { data = { detail: raw }; }
    if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail || data));
    return data;
  }

  async function uploadCertificate() {
    if (!file) { setError("Choose your Udyam certificate first."); return; }
    setBusy(true); setError(""); setMessage("");
    try {
      const body = new FormData();
      body.append("file", file);
      const result = await call("/api/udyam/upload", { method: "POST", body });
      setUpload(result);
      const fields = result.extracted_fields || {};
      setForm((old) => ({
        ...old,
        business_name: fields.business_name || old.business_name,
        industry: fields.industry === "Manufacturing" || fields.industry === "Services"
          ? fields.industry : old.industry,
        place_name: fields.business_address || old.place_name
      }));
      setStep(2);
      setMessage(result.message || "Certificate uploaded. Review the extracted details before continuing.");
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }

  async function generateScore() {
    if (!upload) { setError("Upload the Udyam certificate first."); setStep(1); return; }
    if (!form.business_name.trim() || !form.industry.trim()) { setError("Enter the business name and industry."); return; }
    if (form.latitude === "" || form.longitude === "") { setError("Enter the business latitude and longitude so the backend can retrieve location-based climate evidence."); return; }
    if (!form.supplier_name.trim()) { setError("Enter at least one supplier name."); return; }
    const lat = Number(form.latitude), lon = Number(form.longitude), share = Number(form.procurement_share), base = 750;
    if (!Number.isFinite(lat) || lat < -90 || lat > 90 || !Number.isFinite(lon) || lon < -180 || lon > 180) { setError("Enter valid latitude and longitude values."); return; }
    if (!Number.isFinite(share) || share < 0 || share > 100) { setError("Supplier purchase share must be between 0 and 100%."); return; }

    setBusy(true); setError(""); setMessage(""); setReport(null);
    try {
      const business = await call("/api/businesses", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          business_name: form.business_name.trim(),
          industry: form.industry,
          business_activity: null,
          business_location: {
            latitude: lat, longitude: lon, place_name: form.place_name.trim() || null,
            admin_area: form.place_name.trim() || null, source: "manually entered after certificate upload",
            verification_status: "unverified"
          },
          main_activities: [], critical_raw_materials: [form.material_supplied].filter(Boolean),
          operational_dependencies: [], verification_status: "unverified"
        })
      });
      await call(`/api/businesses/${business.business_id}/suppliers`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          supplier_name: form.supplier_name.trim(),
          material_supplied: form.material_supplied.trim() || null,
          procurement_share: share,
          critical_to_operations: form.critical_to_operations,
          alternative_supplier_available: form.alternative_supplier_available,
          verification_status: "unverified"
        })
      });
      await call(`/api/businesses/${business.business_id}/operational-vulnerability`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          critical_operations: [{ operation_name: "Core business operations", dependency_type: "Business continuity", fallback_available: form.fallback_available, recovery_time_days: null, verification_status: "unverified" }],
          critical_inputs: [{ material_or_service: form.material_supplied.trim() || "Supplier-provided input", critical_to_operations: form.critical_to_operations, inventory_days: null, substitute_available: form.alternative_supplier_available, substitute_time_days: null, verification_status: "unverified" }],
          verification_status: "unverified"
        })
      });
      const result = await call(`/api/businesses/${business.business_id}/climate-risk-assessment`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ years: 5, baseline_credit_score: base, hazard_types: ["precipitation_extremes", "temperature_extremes", "wind_extremes"] })
      });
      setReport(result); setStep(3);
      setMessage("Climate-adjusted score generated by the TerraCred backend.");
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }

  const score = report?.climate_adjusted_credit_score;
  const baseline = report?.baseline_credit_score ?? 750;
  const risk = report?.experimental_climate_risk_indicator;

  return <main className="simple-app">
    <header className="simple-header"><a className="simple-brand"><span><Leaf size={22}/></span>terra<span>cred</span></a><div className="header-note"><span className="live-dot"/> Climate-adjusted MSME scoring</div></header>
    <section className="simple-hero"><div className="simple-kicker"><CloudRain size={15}/> CLIMATE RISK CREDIT ASSESSMENT</div><h1>See how climate risk<br/><em>changes the score.</em></h1><p>Upload an Udyam certificate, add a few supplier details, and generate a climate-adjusted score.</p><div className="simple-steps"><span className={step >= 1 ? "current" : ""}>01 <b>Certificate</b></span><i/><span className={step >= 2 ? "current" : ""}>02 <b>Supplier details</b></span><i/><span className={step >= 3 ? "current" : ""}>03 <b>New score</b></span></div></section>

    {error && <div className="simple-alert error"><ShieldAlert size={17}/><span>{error}</span></div>}
    {message && <div className="simple-alert success"><CheckCircle2 size={17}/><span>{message}</span></div>}

    {step === 1 && <section className="simple-card">
      <div className="simple-card-heading"><div className="card-icon"><FileUp size={20}/></div><div><h2>Upload Udyam certificate</h2><p>Start with the business registration certificate.</p></div></div>
      <label className="upload-zone"><input type="file" accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg" onChange={(e) => { setFile(e.target.files?.[0] || null); setError(""); }}/><span className="upload-icon"><UploadCloud size={24}/></span><strong>{file ? file.name : "Choose certificate to upload"}</strong><small>{file ? `${(file.size / 1024 / 1024).toFixed(2)} MB · Ready to upload` : "PDF, PNG or JPG · Max 10 MB"}</small></label>
      <div className="privacy-note">TerraCred reads text from the PDF or uses OCR for scanned PDFs and images. Extracted fields are suggestions and must be reviewed; the certificate is not officially verified.</div>
      <button className="simple-button" disabled={busy || !file} onClick={uploadCertificate}>{busy ? <><LoaderCircle className="spin" size={17}/> Uploading…</> : <>Upload and continue <ArrowRight size={17}/></>}</button>
    </section>}

    {step === 2 && <section className="simple-card">
      <div className="upload-confirm"><CheckCircle2 size={18}/><span><strong>Certificate uploaded</strong><small>{upload?.filename}</small></span><button className="link-button" onClick={() => { setStep(1); setReport(null); }}>Change</button></div>
      <div className="simple-card-heading"><div className="card-icon"><Leaf size={20}/></div><div><h2>Review business & add supplier</h2><p>Business fields are prefilled from the Udyam certificate when detected.</p></div></div>
      <div className="privacy-note">{upload?.extraction_status === "completed" ? `OCR/text extraction: ${upload.extraction_method || "completed"}. Please correct any mistakes below.` : `Extraction status: ${upload?.extraction_status || "unknown"}. ${upload?.message || "Please enter any missing business details manually."}`}</div>
      <div className="simple-form">
        <Field label="Business name"><input value={form.business_name} onChange={(e) => change("business_name", e.target.value)} placeholder="As shown on Udyam certificate"/></Field>
        <Field label="Industry"><select value={form.industry} onChange={(e) => change("industry", e.target.value)}>{["Manufacturing","Services","Food processing","Agriculture","Retail","Textiles","Logistics","Construction","Hospitality","Other"].map((x) => <option key={x}>{x}</option>)}</select></Field>
        <Field label="Business location" hint="City or district"><input value={form.place_name} onChange={(e) => change("place_name", e.target.value)} placeholder="e.g. Pune, Maharashtra"/></Field>
        <div className="two-fields"><Field label="Latitude"><input type="number" step="any" value={form.latitude} onChange={(e) => change("latitude", e.target.value)} placeholder="18.5204"/></Field><Field label="Longitude"><input type="number" step="any" value={form.longitude} onChange={(e) => change("longitude", e.target.value)} placeholder="73.8567"/></Field></div>
        <div className="form-divider"/>
        <div className="form-subhead">Supplier information</div>
        <Field label="Supplier name"><input value={form.supplier_name} onChange={(e) => change("supplier_name", e.target.value)} placeholder="Main supplier"/></Field>
        <Field label="Material or service supplied"><input value={form.material_supplied} onChange={(e) => change("material_supplied", e.target.value)} placeholder="e.g. raw materials, packaging"/></Field>
        <Field label="Share of purchases from this supplier (%)"><input type="number" min="0" max="100" value={form.procurement_share} onChange={(e) => change("procurement_share", e.target.value)}/></Field>
        <Field label="Is this supplier critical to operations?"><select value={String(form.critical_to_operations)} onChange={(e) => change("critical_to_operations", e.target.value === "true")}><option value="true">Yes</option><option value="false">No</option></select></Field>
        <Field label="Can you switch to an alternative supplier?"><select value={String(form.alternative_supplier_available)} onChange={(e) => change("alternative_supplier_available", e.target.value === "true")}><option value="false">No</option><option value="true">Yes</option></select></Field>
        <Field label="Can core operations continue during a disruption?"><select value={String(form.fallback_available)} onChange={(e) => change("fallback_available", e.target.value === "true")}><option value="false">No</option><option value="true">Yes</option></select></Field>
        <div className="form-divider"/>
      </div>
      <div className="button-row"><button className="simple-button secondary-button" onClick={() => setStep(1)}>Back</button><button className="simple-button" disabled={busy} onClick={generateScore}>{busy ? <><LoaderCircle className="spin" size={17}/> Calculating…</> : <>Generate climate-adjusted score <ArrowRight size={17}/></>}</button></div>
    </section>}

    {report && <section className="simple-card score-report">
      <div className="result-kicker"><CheckCircle2 size={16}/> ASSESSMENT COMPLETE</div><h2>Climate-adjusted credit score</h2><p className="result-intro">{report.business_name || form.business_name} · {report.credit_score_band || "Insufficient evidence"}</p>
      {score == null ? <div className="no-score"><ShieldAlert size={22}/><div><strong>Not enough climate evidence to calculate an adjusted score.</strong><p>The scoring engine did not return a numeric climate-risk indicator. Check the backend warnings below.</p></div></div> : <>
        <div className="score-compare"><div className="score-tile"><small>STARTING SCORE</small><strong>{baseline}</strong><span>Assumed demo baseline</span></div><div className="score-arrow"><ArrowRight size={21}/><small>{(report.climate_adjustment_points ?? 0) > 0 ? `−${report.climate_adjustment_points} pts` : (report.climate_adjustment_points ?? 0) < 0 ? `+${Math.abs(report.climate_adjustment_points)} pts` : "No adjustment"}</small></div><div className="score-tile final-score"><small>CLIMATE-ADJUSTED</small><strong>{score}</strong><span>{report.credit_score_band} range</span></div></div>
        <div className="range-bar"><div className="range-segment poor"/><div className="range-segment fair"/><div className="range-segment good"/><div className="range-segment excellent"/><div className="range-marker" style={{left:`${((score-300)/600)*100}%`}}/></div>
        <div className="range-labels"><span>300 · Poor</span><span>550 · Fair</span><span>650 · Good</span><span>750 · Excellent</span><span>900</span></div>
        <div className="risk-summary"><div><small>CLIMATE RISK INDICATOR</small><strong>{risk ?? "—"}<span>/100</span></strong></div><div><small>CLIMATE ADJUSTMENT</small><strong>{report.climate_adjustment_points > 0 ? `−${report.climate_adjustment_points}` : report.climate_adjustment_points < 0 ? `+${Math.abs(report.climate_adjustment_points)}` : (report.climate_adjustment_points ?? "—")}<span> points</span></strong></div></div>
      </>}
      <div className="result-explanation"><strong>How the score changed</strong><p>{report.credit_score_methodology}</p><p>The climate indicator is returned by the TerraCred backend scoring engine. Higher indicator values produce a larger score reduction in this demo. The starting score is fixed at 750 for demonstration because Udyam does not contain a credit score.</p></div>
      {report.data_quality && <div className="result-explanation data-quality-panel">
        <strong>1. Data quality check · {report.data_quality.status === "passed" ? "Basic checks passed" : "Needs review"}</strong>
        <p>{report.data_quality.summary}</p>
        {(report.data_quality.checks || []).map((item,i)=><div className="quality-check" key={i}>
          <span className={item.status === "passed" ? "quality-dot passed" : "quality-dot issue"} />
          <div><b>{item.check}</b><small>{item.detail}</small></div>
        </div>)}
      </div>}
      {report.evidence_explanation && <div className="result-explanation evidence-explanation">
        <strong>2. What this means for the business {report.evidence_explanation.generated_by === "openai" ? "· OpenAI" : "· Basic explanation"}</strong>
        {report.evidence_explanation.business_problem && <p><b>Possible business problem:</b> {report.evidence_explanation.business_problem}</p>}
        <p>{report.evidence_explanation.summary}</p>
        {(report.evidence_explanation.data_quality_issues || []).length > 0 && <><strong>Data issues to keep in mind</strong><ul>{report.evidence_explanation.data_quality_issues.map((item,i)=><li key={"dq"+i}>{item}</li>)}</ul></>}
        {(report.evidence_explanation.risk_factors || []).length > 0 && <><strong>What could cause disruption</strong><ul>{report.evidence_explanation.risk_factors.map((item,i)=><li key={"risk"+i}>{item}</li>)}</ul></>}
        {(report.evidence_explanation.positive_factors || []).length > 0 && <><strong>Potentially helpful signals</strong><ul>{report.evidence_explanation.positive_factors.map((item,i)=><li key={"positive"+i}>{item}</li>)}</ul></>}
        {(report.evidence_explanation.evidence_limitations || []).length > 0 && <><strong>What we still don't know</strong><ul>{report.evidence_explanation.evidence_limitations.map((item,i)=><li key={"limit"+i}>{item}</li>)}</ul></>}
      </div>}
      {(report.evidence_items || []).length > 0 && <div className="result-explanation">
        <strong>3. Evidence behind the explanation</strong>
        {report.evidence_items.map((item,i)=><div key={i} className="evidence-item">
          <b>{item.label || String(item.hazard_type || "Weather evidence").replaceAll("_"," ")}</b>
          <p>{item.plain_explanation || "A valid observation was not available for this indicator."}</p>
          {item.observed_value != null && <small><b>Observed:</b> {item.observed_value} {item.unit || ""}</small>}
          {item.data_period && <small><b>Period:</b> {item.data_period.start || "unknown"} to {item.data_period.end || "unknown"}</small>}
          {item.source && <small><b>Source:</b> {item.source}</small>}
          {item.source_url && <small><a href={item.source_url} target="_blank" rel="noreferrer">View data source</a></small>}
          <small>Prototype signal: {item.prototype_signal_score}/100. This is a simple proxy, not a damage probability.</small>
        </div>)}
      </div>}
      {(report.warnings || []).length > 0 && <div className="result-warnings"><strong>Data warnings</strong><ul>{report.warnings.map((w,i)=><li key={i}>{w}</li>)}</ul></div>}
      <div className="result-actions"><button className="simple-button secondary-button" onClick={() => { setStep(2); setReport(null); setMessage(""); setError(""); }}>Edit details</button><button className="simple-button" onClick={() => {setStep(1);setFile(null);setUpload(null);setReport(null);setForm(initial);setMessage("");setError("");}}>New assessment</button></div>
      <p className="disclaimer">Hackathon demonstration only. The baseline and score-band mapping are illustrative, not a validated lending score. OCR-extracted details may be inaccurate and are not officially verified. Do not use this output to approve or reject credit.</p>
    </section>}

    <footer className="simple-footer">TerraCred <span>·</span> Explainable climate-risk scoring prototype</footer>
  </main>;
}
