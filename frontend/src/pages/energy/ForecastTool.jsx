import { useState } from "react";
import { api } from "../../api.js";
import { InputField, Panel, Segmented, SelectField } from "../../components/ui.jsx";
import { useZone } from "../../hooks/useZone.js";
import { dateTime, num } from "../../lib/format.js";
import { ZONES } from "../../lib/measures.js";

const WEATHER_FIELDS = [
  { key: "temperature_c", label: "Temperature", hint: "°C", step: "0.1" },
  { key: "humidity_pct", label: "Humidity", hint: "%", step: "1" },
  { key: "wind_speed_ms", label: "Wind speed", hint: "m/s", step: "0.1" },
  { key: "precipitation_mm", label: "Precipitation", hint: "mm/h", step: "0.1" },
];

function RangeBar({ result }) {
  const { lower, upper } = result.interval;
  const marks = [
    { key: "forecast", value: result.forecast_kwh, label: "Forecast" },
    { key: "last", value: result.inputs.latest_observed_kwh, label: "Last observed" },
    { key: "week", value: result.inputs.same_hour_last_week_kwh, label: "Same hour last week" },
  ].filter((m) => m.value != null);
  const lo = Math.min(lower, ...marks.map((m) => m.value));
  const hi = Math.max(upper, ...marks.map((m) => m.value));
  const span = (hi - lo) * 1.12 || 1;
  const start = lo - (hi - lo) * 0.06;
  const at = (v) => `${((v - start) / span) * 100}%`;
  return (
    <>
      <div className="range" role="img" aria-label={`Forecast ${num(result.forecast_kwh, 1)} kWh, interval ${num(lower, 1)} to ${num(upper, 1)}`}>
        <div className="rail" />
        <div className="band" style={{ left: at(lower), width: `${((upper - lower) / span) * 100}%` }} />
        {marks.map((m) => <div key={m.key} className={`tick ${m.key}`} style={{ left: at(m.value) }} title={`${m.label}: ${num(m.value, 1)} kWh`} />)}
      </div>
      <div className="range-legend">
        <span>Shaded: {Math.round(result.interval.coverage * 100)}% interval</span>
        <span>Thick mark: forecast</span>
        <span>Thin marks: last observed, same hour last week</span>
      </div>
    </>
  );
}

function Result({ result }) {
  const w = result.inputs.assumed_weather;
  return (
    <div className="result" aria-live="polite">
      <div className="result-main">
        <div className="result-value">{num(result.forecast_kwh, 1)}<small>kWh</small></div>
        <span className="muted">
          {Math.round(result.interval.coverage * 100)}% interval {num(result.interval.lower, 1)} to {num(result.interval.upper, 1)} kWh
        </span>
      </div>
      <RangeBar result={result} />
      <dl>
        <dt>Target hour</dt><dd>{dateTime(result.target_time)}</dd>
        <dt>Forecast origin</dt><dd>{dateTime(result.origin)}</dd>
        <dt>Last observed</dt><dd>{num(result.inputs.latest_observed_kwh, 1)} kWh</dd>
        <dt>Same hour last week</dt><dd>{num(result.inputs.same_hour_last_week_kwh, 1)} kWh</dd>
        <dt>Assumed weather</dt>
        <dd>
          {num(w.temperature_c, 1)} °C, {num(w.humidity_pct, 0)}% RH, {num(w.wind_speed_ms, 1)} m/s, {num(w.precipitation_mm, 1)} mm
          {result.inputs.weather_overridden.length > 0 && " (modified)"}
        </dd>
        <dt>Model</dt><dd>{result.model}</dd>
      </dl>
    </div>
  );
}

export default function ForecastTool({ onSubmitted }) {
  const { zone } = useZone();
  const [form, setForm] = useState({ zone: zone === "all" ? "Residential" : zone, horizon: 1, origin: "", weather: {} });
  const [state, setState] = useState({ busy: false, error: null, result: null });

  const setWeather = (key, value) => setForm((f) => ({ ...f, weather: { ...f.weather, [key]: value } }));

  async function submit(event) {
    event.preventDefault();
    const weather = Object.fromEntries(
      Object.entries(form.weather).filter(([, v]) => v !== "").map(([k, v]) => [k, Number(v)]),
    );
    const body = { zone: form.zone, horizon_hours: form.horizon };
    if (form.origin) body.origin = form.origin;
    if (Object.keys(weather).length) body.weather = weather;
    setState((s) => ({ ...s, busy: true, error: null }));
    try {
      const result = await api.forecast(body);
      setState({ busy: false, error: null, result });
      onSubmitted?.();
    } catch (error) {
      setState((s) => ({ ...s, busy: false, error }));
    }
  }

  return (
    <Panel title="Demand forecast" subtitle="Predict substation energy for the next hour or the same hour tomorrow">
      <form onSubmit={submit} noValidate>
        <div className="form-grid">
          <SelectField label="Zone" value={form.zone} onChange={(zoneValue) => setForm({ ...form, zone: zoneValue })}
            options={ZONES.map((z) => ({ value: z, label: z }))} />
          <div className="field">
            <span id="horizon-label">Horizon</span>
            <Segmented label="Forecast horizon" value={form.horizon} onChange={(h) => setForm({ ...form, horizon: h })}
              options={[{ value: 1, label: "1 hour" }, { value: 24, label: "24 hours" }]} />
          </div>
          <InputField className="full" label="Forecast origin" hint="(optional, defaults to the latest reading)" type="datetime-local"
            value={form.origin} onChange={(e) => setForm({ ...form, origin: e.target.value })} />
        </div>
        <details className="whatif">
          <summary>What-if weather at the target hour</summary>
          <div className="form-grid">
            {WEATHER_FIELDS.map((f) => (
              <InputField key={f.key} label={f.label} hint={`(${f.hint})`} type="number" step={f.step} inputMode="decimal"
                placeholder="as assumed" value={form.weather[f.key] ?? ""} onChange={(e) => setWeather(f.key, e.target.value)} />
            ))}
          </div>
        </details>
        <div className="form-actions">
          <button type="submit" className="btn primary" disabled={state.busy}>{state.busy ? "Forecasting…" : "Run forecast"}</button>
        </div>
        {state.error && <div className="notice error" role="alert" style={{ marginTop: 12 }}><div className="grow">{state.error.message}</div></div>}
      </form>
      {state.result && <Result result={state.result} />}
    </Panel>
  );
}
