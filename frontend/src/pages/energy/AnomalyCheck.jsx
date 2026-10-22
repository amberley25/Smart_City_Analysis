import { useState } from "react";
import { api } from "../../api.js";
import { InputField, Panel, SelectField } from "../../components/ui.jsx";
import { useZone } from "../../hooks/useZone.js";
import { num } from "../../lib/format.js";
import { ZONES } from "../../lib/measures.js";

const EXAMPLES = {
  normal: { label: "Normal reading", zone: "Downtown", timestamp: "2026-04-20T13:00", energy_kwh: "440", voltage_v: "399", current_a: "670", power_factor: "0.95" },
  mismatch: { label: "Meter mismatch", zone: "Downtown", timestamp: "2026-04-20T13:00", energy_kwh: "690", voltage_v: "399", current_a: "670", power_factor: "0.95" },
  sag: { label: "Voltage sag", zone: "Downtown", timestamp: "2026-04-20T13:00", energy_kwh: "440", voltage_v: "335", current_a: "800", power_factor: "0.95" },
};

const FIELDS = [
  { key: "energy_kwh", label: "Energy", hint: "(kWh)", step: "0.1" },
  { key: "voltage_v", label: "Voltage", hint: "(V)", step: "0.1" },
  { key: "current_a", label: "Current", hint: "(A)", step: "0.1" },
  { key: "power_factor", label: "Power factor", hint: "(0–1)", step: "0.001" },
];

const SIGNAL_LABELS = {
  profile_z: "Deviation from profile (z)",
  log_ratio: "Log ratio to typical",
  power_balance: "Meter vs V·I·pf",
  voltage_dev: "Voltage deviation",
  power_factor: "Power factor",
};

function Result({ result }) {
  const scale = Math.max(result.threshold * 1.4, result.score * 1.05);
  return (
    <div className="result" aria-live="polite">
      <div className="result-main">
        <span className={`badge ${result.anomaly ? "bad" : "ok"}`}>{result.classification}</span>
        <span className="muted">score {num(result.score, 3)} against threshold {num(result.threshold, 3)}</span>
      </div>
      <div className="score-track" role="img" aria-label={`Score ${result.score}, threshold ${result.threshold}`}>
        <div className={`score-fill${result.anomaly ? " flagged" : ""}`} style={{ width: `${(result.score / scale) * 100}%` }} />
        <div className="score-mark" style={{ left: `${(result.threshold / scale) * 100}%` }} title="Alert threshold" />
      </div>
      <div className="range-legend"><span>Black mark: alert threshold</span><span>Typical for this hour: {num(result.expected_kwh, 0)} kWh</span></div>
      {result.reasons.length > 0 && <ul>{result.reasons.map((r) => <li key={r}>{r}</li>)}</ul>}
      <div className="signals">
        {Object.entries(result.signals).map(([k, v]) => (
          <div key={k}><span>{SIGNAL_LABELS[k] ?? k}</span>{num(v, 3)}</div>
        ))}
      </div>
    </div>
  );
}

export default function AnomalyCheck({ onSubmitted }) {
  const { zone } = useZone();
  const [form, setForm] = useState({ ...EXAMPLES.normal, zone: zone === "all" ? EXAMPLES.normal.zone : zone });
  const [state, setState] = useState({ busy: false, error: null, result: null });
  const set = (key, value) => setForm((f) => ({ ...f, [key]: value }));

  async function submit(event) {
    event.preventDefault();
    const body = { zone: form.zone, timestamp: form.timestamp || null };
    for (const f of FIELDS) body[f.key] = form[f.key] === "" ? null : Number(form[f.key]);
    setState((s) => ({ ...s, busy: true, error: null }));
    try {
      const result = await api.checkAnomaly(body);
      setState({ busy: false, error: null, result });
      onSubmitted?.();
    } catch (error) {
      setState((s) => ({ ...s, busy: false, error }));
    }
  }

  return (
    <Panel title="Reading check" subtitle="Score a substation reading against the learned profile for its zone and hour"
      actions={Object.entries(EXAMPLES).map(([id, ex]) => (
        <button key={id} type="button" className="btn link" onClick={() => setForm({ ...ex, zone: ex.zone })}>{ex.label}</button>
      ))}>
      <form onSubmit={submit} noValidate>
        <div className="form-grid">
          <SelectField label="Zone" value={form.zone} onChange={(v) => set("zone", v)} options={ZONES.map((z) => ({ value: z, label: z }))} />
          <InputField label="Timestamp" type="datetime-local" value={form.timestamp} onChange={(e) => set("timestamp", e.target.value)} />
          {FIELDS.map((f) => (
            <InputField key={f.key} label={f.label} hint={f.hint} type="number" step={f.step} inputMode="decimal"
              value={form[f.key]} onChange={(e) => set(f.key, e.target.value)} />
          ))}
        </div>
        <div className="form-actions">
          <button type="submit" className="btn primary" disabled={state.busy}>{state.busy ? "Scoring…" : "Check reading"}</button>
        </div>
        {state.error && <div className="notice error" role="alert" style={{ marginTop: 12 }}><div className="grow">{state.error.message}</div></div>}
      </form>
      {state.result && <Result result={state.result} />}
    </Panel>
  );
}
