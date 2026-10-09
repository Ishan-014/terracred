import { useEffect, useMemo, useState } from "react";
import { Activity, ArrowRight, Building2, CheckCircle2, ChevronRight, CloudRain, Database, FileCheck2, Gauge, Leaf, LoaderCircle, MapPin, Plus, RefreshCw, ShieldAlert, Trash2, Waves, Wind } from "lucide-react";

const API = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
const splitList = (value) => value.split(",").map((item) => item.trim()).filter(Boolean);
const emptySupplier = () => ({ supplier_name: "", material_supplied: "", procurement_share: "", critical_to_operations: true, alternative_supplier_available: false, verification_status: "unknown" });
const initialForm = {
  business_name: "Synthetic Pune Foods MSME",
  industry: "Food processing",
  business_activity: "Small food processing and packaging unit",
  place_name: "Pune, Maharashtra",
  latitude: "18.5204",
  longitude: "73.8567",
  verification_status: "unverified",
  main_activities: "Processing, packaging, dispatch",
  critical_raw_materials: "Grains, packaging material",
  operational_dependencies: "Electricity, road transport, water",
  years: "5"
};

function Field({ label, hint, children }) {
  return <label className="field"><span>{label}</span>{children}{hint && <small>{hint}</small>}</label>;
}
function SectionTitle({ number, title, subtitle }) {
  return <div className="section-title"><span className="step-number">{number}</span><div><h3>{title}</h3><p>{subtitle}</p></div></div>;
}
function scoreLabel(score) {
  if (score == null) return "Insufficient evidence";
  if (score < 34) return "Lower prototype signal";
  if (score < 67) return "Moderate prototype signal";
  return "Higher prototype signal";
}
function prettyKey(key) {
  return key.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function App() {
  const [form, setForm] = useState(initialForm);
  const [suppliers, setSuppliers] = useState([emptySupplier()]);
  const [operations, setOperations] = useState([{ operation_name: "Core production", dependency_type: "Electricity", fallback_available: false, recovery_time_days: 3, continuity_measure: "" }]);
  const [inputs, setInputs] = useState([{ material_or_service: "Grains", critical_to_operations: true, inventory_days: 5, substitute_available: false, substitute_time_days: 7 }]);
  const [apiState, setApiState] = useState("checking");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [business, setBusiness] = useState(null);
  const [report, setReport] = useState(null);
  const [notice, setNotice] = useState("");

  const request = async (path, options = {}) => {
    const response = await fetch(API + path, { ...options, headers: { "Content-Type": "application/json", ...(options.headers || {}) } });
    const raw = await response.text();
    let data;
    try { data = raw ? JSON.parse(raw) : {}; } catch { data = { detail: raw }; }
    if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail || data));
    return data;
  };

  useEffect(() => {
    request("/health").then(() => setApiState("online")).catch(() => setApiState("offline"));
  }, []);

  const dimensions = report?.dimensions ? Object.entries(report.dimensions) : [];
  const availableDimensions = useMemo(() => dimensions.filter(([, item]) => item.score != null).length, [report]);

  const updateSupplier = (index, key, value) => setSuppliers((all) => all.map((item, i) => i === index ? { ...item, [key]: value } : item));
  const updateOperation = (index, key, value) => setOperations((all) => all.map((item, i) => i === index ? { ...item, [key]: value } : item));
  const updateInput = (index, key, value) => setInputs((all) => all.map((item, i) => i === index ? { ...item, [key]: value } : item));

  async function createBusiness() {
    setBusy(true); setError(""); setNotice(""); setReport(null);
    try {
      const payload = {
        business_name: form.business_name.trim(),
        industry: form.industry.trim(),
        business_activity: form.business_activity.trim() || null,
        business_location: {
          place_name: form.place_name.trim() || null,
          admin_area: form.place_name.trim() || null,
          latitude: form.latitude === "" ? null : Number(form.latitude),
          longitude: form.longitude === "" ? null : Number(form.longitude),
          source: "user-entered demo profile",
          verification_status: form.verification_status
        },
        main_activities: splitList(form.main_activities),
        critical_raw_materials: splitList(form.critical_raw_materials),
        operational_dependencies: splitList(form.operational_dependencies),
        verification_status: form.verification_status
      };
      const created = await request("/api/businesses", { method: "POST", body: JSON.stringify(payload) });
      setBusiness(created);
      for (const supplier of suppliers) {
        if (!supplier.supplier_name.trim()) continue;
        await request(`/api/businesses/${created.business_id}/suppliers`, { method: "POST", body: JSON.stringify({
          ...supplier,
          procurement_share: supplier.procurement_share === "" ? null : Number(supplier.procurement_share),
          supplier_location: null,
          material_supplied: supplier.material_supplied || null
        }) });
      }
      await request(`/api/businesses/${created.business_id}/operational-vulnerability`, { method: "POST", body: JSON.stringify({
        critical_operations: operations.filter((x) => x.operation_name.trim()).map((x) => ({ ...x, recovery_time_days: Number(x.recovery_time_days) || 0, continuity_measure: x.continuity_measure || null })),
        critical_inputs: inputs.filter((x) => x.material_or_service.trim()).map((x) => ({ ...x, inventory_days: Number(x.inventory_days) || 0, substitute_time_days: Number(x.substitute_time_days) || 0 })),
        verification_status: form.verification_status
      }) });
      setNotice("Business profile, supplier details and operational vulnerability saved. Ready to assess.");
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }

  async function runAssessment() {
    setBusy(true); setError(""); setNotice("");
    try {
      let activeBusiness = business;
      if (!activeBusiness) {
        await createBusiness();
        // createBusiness manages its own state and errors; use the persisted record below.
        const list = await request("/api/businesses");
        const matches = (list.businesses || []).filter((x) => x.business_name === form.business_name.trim());
        activeBusiness = matches[matches.length - 1];
      }
      if (!activeBusiness?.business_id) throw new Error("Could not find the saved business profile. Save the profile, then assess again.");
      const result = await request(`/api/businesses/${activeBusiness.business_id}/climate-risk-assessment`, {
        method: "POST", body: JSON.stringify({ years: Number(form.years), hazard_types: ["precipitation_extremes", "temperature_extremes", "wind_extremes"] })
      });
      setBusiness(activeBusiness); setReport(result);
      setNotice("Assessment returned by the TerraCred backend scoring engine.");
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }

  async function saveProfile() {
    await createBusiness();
  }

  function resetAssessment() { setReport(null); setError(""); setNotice(""); setBusiness(null); }

  return <div className="app-shell">
    <aside className="sidebar">
      <a className="brand" href="#"><span className="brand-mark"><Leaf size={21} /></span><span>terra<span>cred</span><small>CLIMATE RISK INTELLIGENCE</small></span></a>
      <div className="workspace-label">WORKSPACE</div>
      <div className="nav-item active"><Gauge size={18} /> Risk assessment</div>
      <div className="nav-item"><Building2 size={18} /> MSME profiles <span className="soon">LIVE</span></div>
      <div className="nav-item"><Database size={18} /> Evidence sources</div>
      <div className="sidebar-bottom"><div className="status-dot" /><div><strong>Prototype environment</strong><small>Rule-based · Explainable</small></div></div>
    </aside>

    <main className="main">
      <header className="topbar"><div className="breadcrumb">TerraCred <ChevronRight size={14} /> Climate intelligence</div><div className={`api-status ${apiState}`}><span /> API {apiState === "online" ? "connected" : apiState === "checking" ? "checking…" : "offline"}</div></header>
      <div className="content">
        <section className="hero">
          <div><div className="eyebrow"><span className="eyebrow-line" /> MSME CLIMATE RESILIENCE</div><h1>Understand risk.<br /><em>Build resilience.</em></h1><p>Turn climate evidence, operational dependencies and supplier concentration into an explainable assessment for small businesses.</p><div className="hero-tags"><span><CloudRain size={14} /> Climate hazards</span><span><Activity size={14} /> Operations</span><span><Building2 size={14} /> Supply chain</span></div></div>
          <div className="hero-graphic"><div className="orbit orbit-one" /><div className="orbit orbit-two" /><div className="globe"><Leaf size={43} strokeWidth={1.2} /></div><span className="graphic-label label-top">CLIMATE SIGNALS</span><span className="graphic-label label-bottom">MSME RESILIENCE</span><span className="graphic-dot dot-one" /><span className="graphic-dot dot-two" /></div>
        </section>

        <div className="section-heading"><div><span className="eyebrow">ASSESSMENT WORKFLOW</span><h2>Build a business assessment</h2><p>Complete the profile in sequence. The backend computes the indicator.</p></div><button className="button ghost" onClick={resetAssessment}><RefreshCw size={15} /> New assessment</button></div>

        {error && <div className="alert error"><ShieldAlert size={18} /><div><strong>Could not complete request</strong><p>{error}</p><small>Confirm the backend is running and the API URL is correct.</small></div></div>}
        {notice && <div className="alert success"><CheckCircle2 size={18} /><p>{notice}</p></div>}

        <div className="workflow">
          <section className="panel">
            <SectionTitle number="01" title="Business profile" subtitle="Identify the business and its operating location." />
            <div className="form-grid">
              <Field label="Business name"><input value={form.business_name} onChange={(e) => setForm({ ...form, business_name: e.target.value })} placeholder="e.g. Pune Foods Pvt Ltd" /></Field>
              <Field label="Industry"><select value={form.industry} onChange={(e) => setForm({ ...form, industry: e.target.value })}>{["Food processing","Manufacturing","Retail","Agriculture","Textiles","Logistics","Construction","Hospitality","Other"].map((x) => <option key={x}>{x}</option>)}</select></Field>
              <Field label="Business activity" ><input value={form.business_activity} onChange={(e) => setForm({ ...form, business_activity: e.target.value })} /></Field>
              <Field label="Location / district"><input value={form.place_name} onChange={(e) => setForm({ ...form, place_name: e.target.value })} placeholder="City, state" /></Field>
              <Field label="Latitude" hint="Required for live location-based weather assessment"><input type="number" step="any" value={form.latitude} onChange={(e) => setForm({ ...form, latitude: e.target.value })} /></Field>
              <Field label="Longitude"><input type="number" step="any" value={form.longitude} onChange={(e) => setForm({ ...form, longitude: e.target.value })} /></Field>
              <Field label="Evidence verification"><select value={form.verification_status} onChange={(e) => setForm({ ...form, verification_status: e.target.value })}><option value="unknown">Unknown</option><option value="unverified">Unverified</option><option value="verified">Verified</option></select></Field>
              <Field label="Historical period"><select value={form.years} onChange={(e) => setForm({ ...form, years: e.target.value })}>{[1,3,5,10,15,20,30].map((x) => <option value={x} key={x}>{x} years</option>)}</select></Field>
              <Field label="Main activities" hint="Separate items with commas"><input value={form.main_activities} onChange={(e) => setForm({ ...form, main_activities: e.target.value })} /></Field>
              <Field label="Critical raw materials" hint="Separate items with commas"><input value={form.critical_raw_materials} onChange={(e) => setForm({ ...form, critical_raw_materials: e.target.value })} /></Field>
              <Field label="Operational dependencies" hint="Separate items with commas"><input value={form.operational_dependencies} onChange={(e) => setForm({ ...form, operational_dependencies: e.target.value })} /></Field>
            </div>
          </section>

          <section className="panel">
            <SectionTitle number="02" title="Supplier dependencies" subtitle="Capture concentration and alternatives. Unknown is not the same as safe." />
            {suppliers.map((supplier, i) => <div className="repeat-card" key={i}><div className="repeat-heading"><strong>Supplier {i + 1}</strong>{suppliers.length > 1 && <button className="icon-button" onClick={() => setSuppliers(suppliers.filter((_, j) => i !== j))} aria-label="Remove supplier"><Trash2 size={15} /></button>}</div><div className="form-grid compact">
              <Field label="Supplier name"><input value={supplier.supplier_name} onChange={(e) => updateSupplier(i, "supplier_name", e.target.value)} placeholder="Supplier or source" /></Field>
              <Field label="Material supplied"><input value={supplier.material_supplied} onChange={(e) => updateSupplier(i, "material_supplied", e.target.value)} placeholder="e.g. grain" /></Field>
              <Field label="Procurement share (%)"><input type="number" min="0" max="100" value={supplier.procurement_share} onChange={(e) => updateSupplier(i, "procurement_share", e.target.value)} placeholder="Unknown" /></Field>
              <Field label="Verification"><select value={supplier.verification_status} onChange={(e) => updateSupplier(i, "verification_status", e.target.value)}><option value="unknown">Unknown</option><option value="unverified">Unverified</option><option value="verified">Verified</option></select></Field>
              <Field label="Critical to operations"><select value={String(supplier.critical_to_operations)} onChange={(e) => updateSupplier(i, "critical_to_operations", e.target.value === "true")}><option value="true">Yes</option><option value="false">No</option></select></Field>
              <Field label="Alternative supplier"><select value={String(supplier.alternative_supplier_available)} onChange={(e) => updateSupplier(i, "alternative_supplier_available", e.target.value === "true")}><option value="false">No / not documented</option><option value="true">Yes</option></select></Field>
            </div></div>)}
            <button className="button secondary" onClick={() => setSuppliers([...suppliers, emptySupplier()])}><Plus size={15} /> Add supplier</button>
          </section>

          <section className="panel">
            <SectionTitle number="03" title="Operational vulnerability" subtitle="Record fallback capacity and substitution options." />
            <div className="subsection-label">CRITICAL OPERATIONS</div>
            {operations.map((item, i) => <div className="repeat-card" key={i}><div className="form-grid compact">
              <Field label="Operation"><input value={item.operation_name} onChange={(e) => updateOperation(i, "operation_name", e.target.value)} placeholder="Production line" /></Field>
              <Field label="Dependency type"><input value={item.dependency_type} onChange={(e) => updateOperation(i, "dependency_type", e.target.value)} placeholder="Electricity, water…" /></Field>
              <Field label="Fallback available"><select value={String(item.fallback_available)} onChange={(e) => updateOperation(i, "fallback_available", e.target.value === "true")}><option value="false">No</option><option value="true">Yes</option></select></Field>
              <Field label="Recovery time (days)"><input type="number" min="0" value={item.recovery_time_days} onChange={(e) => updateOperation(i, "recovery_time_days", e.target.value)} /></Field>
            </div></div>)}
            <button className="button text-button" onClick={() => setOperations([...operations, { operation_name: "", dependency_type: "", fallback_available: false, recovery_time_days: 0, continuity_measure: "" }])}><Plus size={14} /> Add operation</button>
            <div className="subsection-label input-label">CRITICAL INPUTS</div>
            {inputs.map((item, i) => <div className="repeat-card" key={i}><div className="form-grid compact">
              <Field label="Input or service"><input value={item.material_or_service} onChange={(e) => updateInput(i, "material_or_service", e.target.value)} placeholder="Raw material, water…" /></Field>
              <Field label="Inventory coverage (days)"><input type="number" min="0" value={item.inventory_days} onChange={(e) => updateInput(i, "inventory_days", e.target.value)} /></Field>
              <Field label="Substitute available"><select value={String(item.substitute_available)} onChange={(e) => updateInput(i, "substitute_available", e.target.value === "true")}><option value="false">No</option><option value="true">Yes</option></select></Field>
              <Field label="Substitution time (days)"><input type="number" min="0" value={item.substitute_time_days} onChange={(e) => updateInput(i, "substitute_time_days", e.target.value)} /></Field>
            </div></div>)}
            <button className="button text-button" onClick={() => setInputs([...inputs, { material_or_service: "", critical_to_operations: true, inventory_days: 0, substitute_available: false, substitute_time_days: 0 }])}><Plus size={14} /> Add critical input</button>
          </section>

          <section className="submit-panel"><div><div className="submit-icon"><FileCheck2 size={22} /></div><h3>Ready to assess?</h3><p>Save the profile, retrieve available climate evidence, and run the backend scoring engine.</p><small>Assessment period: {form.years} years · 3 requested weather hazard categories</small></div><div className="submit-actions"><button className="button secondary" disabled={busy} onClick={saveProfile}>{busy ? <LoaderCircle className="spin" size={16} /> : <Database size={16} />} Save profile</button><button className="button primary" disabled={busy || apiState !== "online"} onClick={runAssessment}>{busy ? <LoaderCircle className="spin" size={16} /> : <>Run assessment <ArrowRight size={16} /></>}</button></div></section>
        </div>

        {report && <section className="report" id="report">
          <div className="report-header"><div><div className="eyebrow"><span className="eyebrow-line" /> ASSESSMENT OUTPUT</div><h2>Climate risk evidence report</h2><p>{report.business_name || "Business"} · Model {report.model_version}</p></div><span className={`status-pill ${report.status === "experimental_indicator" ? "caution" : "muted"}`}>{prettyKey(report.status || "unknown")}</span></div>
          <div className="score-layout"><div className="score-card"><span className="score-label">EXPERIMENTAL INDICATOR</span><div className="score-number">{report.experimental_climate_risk_indicator == null ? "—" : report.experimental_climate_risk_indicator}<small>{report.experimental_climate_risk_indicator == null ? "" : "/100"}</small></div><span className="score-caption">{report.experimental_climate_risk_indicator == null ? "Insufficient evidence to calculate" : scoreLabel(report.experimental_climate_risk_indicator)}</span><div className="score-track"><span style={{ width: `${report.experimental_climate_risk_indicator ?? 0}%` }} /></div><p>Prototype signal only; not a probability of loss or a credit score.</p></div><div className="dimension-grid">{dimensions.map(([key, item]) => <div className="dimension-card" key={key}><div className="dimension-top"><span>{key === "hazard_evidence" ? <CloudRain size={17} /> : key === "operational_vulnerability" ? <Activity size={17} /> : key === "supplier_dependency" ? <Building2 size={17} /> : <Database size={17} />}</span><span className={`mini-status ${item.score == null && key !== "evidence_quality" ? "missing" : ""}`}>{item.score == null ? "N/A" : "Available"}</span></div><h4>{prettyKey(key)}</h4><div className="dimension-score">{item.score == null ? (item.verification_coverage_pct == null ? "—" : `${item.verification_coverage_pct}%`) : item.score}<small>{item.score == null && item.verification_coverage_pct != null ? " verified" : item.score == null ? "" : " / 100"}</small></div><p>{item.explanation}</p>{item.signals_used != null && <small>{item.signals_used} scored signal(s)</small>}</div>)}</div></div>
          <div className="report-columns"><div className="report-box"><h3><Database size={17} /> Evidence & provenance</h3>{dimensions.filter(([,d]) => d.sources?.length).map(([key,d]) => <div className="source-group" key={key}><strong>{prettyKey(key)}</strong>{d.sources.map((s,i) => <div className="source-row" key={i}><span>{prettyKey(s.hazard_type || "Climate evidence")}</span><span>{s.source || "Source not specified"}</span>{s.source_url && <a href={s.source_url} target="_blank" rel="noreferrer">View source ↗</a>}{s.data_period && <small>{JSON.stringify(s.data_period)}</small>}</div>)}</div>)}{!dimensions.some(([,d]) => d.sources?.length) && <p className="muted-text">No scored hazard source metadata was returned. Check the warnings below.</p>}</div><div className="report-box"><h3><ShieldAlert size={17} /> Missing inputs</h3>{(report.missing_inputs || []).length ? <ul className="warning-list">{report.missing_inputs.map((w,i) => <li key={i}>{w}</li>)}</ul> : <p>No missing inputs were reported by the scoring engine.</p>}<h3 className="warning-heading"><Waves size={17} /> Warnings & limitations</h3><ul className="warning-list">{(report.warnings || []).map((w,i) => <li key={i}>{w}</li>)}</ul></div></div>
          <div className="methodology"><div><strong>Methodology</strong><p>{report.methodology}</p></div><div className="decision-note"><ShieldAlert size={18} /><span><strong>No lending decision is generated</strong><small>Conventional credit assessment remains separate.</small></span></div></div>
        </section>}
        <footer><span>TerraCred · Prototype for explainable climate-risk evidence</span><span><MapPin size={13} /> Location data is user-entered</span></footer>
      </div>
    </main>
  </div>;
}
