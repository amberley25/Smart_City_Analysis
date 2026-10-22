import { AlertCircle, Info } from "lucide-react";
import { useId } from "react";
import { signedPercent } from "../lib/format.js";

export function Panel({ title, subtitle, actions, flush = false, className = "", children }) {
  return (
    <section className={`panel ${className}`}>
      {(title || actions) && (
        <header className="panel-head">
          <div className="titles">
            {title && <h2>{title}</h2>}
            {subtitle && <p className="subtitle">{subtitle}</p>}
          </div>
          {actions && <div className="panel-actions">{actions}</div>}
        </header>
      )}
      <div className={`panel-body${flush ? " flush" : ""}`}>{children}</div>
    </section>
  );
}

export function Segmented({ label, value, onChange, options }) {
  return (
    <div className="segmented" role="group" aria-label={label}>
      {options.map((o) => (
        <button key={o.value} type="button" aria-pressed={value === o.value} onClick={() => onChange(o.value)}>
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function SelectField({ label, value, onChange, options, inline = false, ...rest }) {
  const id = useId();
  const select = (
    <select id={id} className="select" value={value} onChange={(e) => onChange(e.target.value)} {...rest}>
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  );
  return inline ? (
    <label className="inline-field" htmlFor={id}>
      <span>{label}</span>
      {select}
    </label>
  ) : (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      {select}
    </div>
  );
}

export function InputField({ label, hint, className = "", ...rest }) {
  const id = useId();
  return (
    <div className={`field ${className}`}>
      <label htmlFor={id}>
        {label}
        {hint && <span className="muted"> {hint}</span>}
      </label>
      <input id={id} className="input" {...rest} />
    </div>
  );
}

export function Skeleton({ height = 200 }) {
  return <div className="skeleton" style={{ height }} aria-hidden="true" />;
}

export function ErrorBanner({ error, onRetry }) {
  const unreachable = error?.code === "network_error";
  const unavailable = error?.status === 503;
  return (
    <div className="notice error" role="alert">
      <AlertCircle aria-hidden="true" />
      <div className="grow">
        <strong>{unreachable ? "Cannot reach the API" : "Request failed"}</strong>
        <div>
          {error?.message}
          {unreachable && (
            <>
              {" "}
              Start it with <code>smartcity serve</code> (or <code>make serve</code>) and retry.
            </>
          )}
          {unavailable && (
            <>
              {" "}
              Run <code>make setup</code> to generate the dataset and train the models.
            </>
          )}
        </div>
      </div>
      {onRetry && (
        <button type="button" className="btn" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

export function Notice({ children }) {
  return (
    <div className="notice">
      <Info aria-hidden="true" />
      <div className="grow">{children}</div>
    </div>
  );
}

export function Empty({ children }) {
  return <div className="empty">{children}</div>;
}

/** Renders skeleton, error or content from a useApi state. */
export function Async({ state, height = 240, children }) {
  if (state.error) return <ErrorBanner error={state.error} onRetry={state.reload} />;
  if (!state.data) return <Skeleton height={height} />;
  return <div className={state.loading ? "is-refreshing" : undefined}>{children(state.data)}</div>;
}

export function Delta({ pct, tone = "neutral", suffix = "vs previous 24 h" }) {
  if (pct == null) return <span className="kpi-note">No change reference</span>;
  const cls = tone === "down-good" ? (pct <= 0 ? "good" : "bad") : "up";
  return (
    <span className="kpi-note">
      <span className={`delta ${cls}`}>{signedPercent(pct)}</span> {suffix}
    </span>
  );
}

export function KpiStrip({ items }) {
  return (
    <section className="panel kpis" aria-label="Key indicators">
      {items.map((k) => (
        <div className="kpi" key={k.label}>
          <div className="kpi-label">{k.label}</div>
          <div className="kpi-value">
            {k.value}
            {k.unit && <small>{k.unit}</small>}
          </div>
          {k.note}
        </div>
      ))}
    </section>
  );
}
