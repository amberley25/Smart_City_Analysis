import { useMemo } from "react";
import { api } from "../api.js";
import { TimeSeries } from "../components/charts.jsx";
import { Async, Delta, KpiStrip, Panel } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";
import { useZone } from "../hooks/useZone.js";
import { num, percent } from "../lib/format.js";
import { pivotByZone, zonesIn } from "../lib/series.js";

const HEALTH_LABELS = { energy: "Energy", traffic: "Traffic", air_quality: "Air quality", weather: "Weather" };

function kpiItems(d) {
  const k = d.kpis;
  return [
    { label: "Energy, last 24 h", value: num(k.energy_kwh.value, 0), unit: "kWh", note: <Delta pct={k.energy_kwh.change_pct} /> },
    { label: "Traffic, hourly mean", value: num(k.traffic_count.value, 0), unit: "veh/h", note: <Delta pct={k.traffic_count.change_pct} /> },
    { label: "PM2.5, 24 h mean", value: num(k.pm25_ugm3.value, 1), unit: "µg/m³", note: <Delta pct={k.pm25_ugm3.change_pct} tone="down-good" /> },
    { label: "Temperature", value: num(k.temperature_c.value, 1), unit: "°C", note: <Delta pct={k.temperature_c.change_pct} /> },
    { label: "Rainfall, last 24 h", value: num(k.precipitation_mm.value, 1), unit: "mm", note: <span className="kpi-note">{num(k.precipitation_mm.previous, 1)} mm previous 24 h</span> },
    { label: "Flagged anomalies, 7 d", value: num(d.anomalies.last_7d, 0), unit: "readings", note: <span className="kpi-note">{num(d.anomalies.last_24h, 0)} in the last 24 h</span> },
  ];
}

function ZoneTable({ zones, onSelect }) {
  const max = (key) => Math.max(...zones.map((z) => z[key] ?? 0), 1);
  const cols = [
    { key: "energy_kwh", label: "Energy (kWh)", digits: 0 },
    { key: "traffic_count", label: "Traffic (veh/h)", digits: 0 },
    { key: "pm25_ugm3", label: "PM2.5 (µg/m³)", digits: 1 },
    { key: "temperature_c", label: "Temp. (°C)", digits: 1, plain: true },
    { key: "flagged_7d", label: "Flagged, 7 d", digits: 0 },
  ];
  return (
    <div className="table-wrap">
      <table className="table">
        <caption className="sr-only">Zone comparison for the last 24 hours</caption>
        <thead>
          <tr>
            <th scope="col">Zone</th>
            {cols.map((c) => <th key={c.key} scope="col" className="num">{c.label}</th>)}
          </tr>
        </thead>
        <tbody>
          {zones.map((z) => (
            <tr key={z.zone}>
              <th scope="row" style={{ textAlign: "left", fontWeight: 500 }}>
                <button type="button" className="zone-link" onClick={() => onSelect(z.zone)}>{z.zone}</button>
              </th>
              {cols.map((c) => (
                <td key={c.key} className="num">
                  {c.plain ? num(z[c.key], c.digits) : (
                    <div className="cell-bar">
                      <span className="track"><span className="fill" style={{ width: `${((z[c.key] ?? 0) / max(c.key)) * 100}%` }} /></span>
                      <span className="value">{num(z[c.key], c.digits)}</span>
                    </div>
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SensorHealth({ health }) {
  return (
    <div>
      {Object.entries(health).map(([domain, s]) => (
        <div className="health-row" key={domain}>
          <strong style={{ fontWeight: 500 }}>{HEALTH_LABELS[domain]}</strong>
          <div>
            <div className="health-bar" role="img" aria-label={`${HEALTH_LABELS[domain]}: ${s.OK}% OK`}>
              <span className="ok" style={{ width: `${s.OK}%` }} />
              <span className="degraded" style={{ width: `${s.DEGRADED}%` }} />
              <span className="offline" style={{ width: `${s.OFFLINE}%` }} />
            </div>
            <div className="health-text">
              OK {percent(s.OK)} · degraded {percent(s.DEGRADED)} · offline {percent(s.OFFLINE)}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function Accuracy({ a }) {
  if (!a) return <p className="muted">No evaluation report available. Run <code>smartcity train</code>.</p>;
  return (
    <>
      <div className="accuracy">
        <div><div className="label">Holdout MAE</div><div className="value">{num(a.mae, 1)} <small>kWh</small></div></div>
        <div><div className="label">R²</div><div className="value">{num(a.r2, 3)}</div></div>
        <div><div className="label">vs persistence</div><div className="value">{num(a.improvement_pct, 0)}<small>% lower</small></div></div>
      </div>
      <p className="muted" style={{ marginTop: 12 }}>
        {a.model}, 1-hour-ahead, scored on a chronological 28-day holdout. Persistence baseline MAE {num(a.baseline_mae, 1)} kWh.{" "}
        <a href="#/models">View full evaluation</a>
      </p>
    </>
  );
}

export default function Overview() {
  const { zone, setZone } = useZone();
  const overview = useApi((s) => api.overview(zone, s), [zone]);
  const daily = useApi((s) => api.series("energy", { zone, resolution: "daily" }, s), [zone]);

  const chart = useMemo(() => {
    if (!daily.data) return null;
    const rows = pivotByZone(daily.data.records, "energy_kwh").slice(-14);
    return { rows, zones: zonesIn(daily.data.records) };
  }, [daily.data]);

  return (
    <>
      <Async state={overview} height={92}>{(d) => <KpiStrip items={kpiItems(d)} />}</Async>

      <div className="grid wide-left">
        <Panel title="Daily energy demand" subtitle={`${zone === "all" ? "Stacked by zone" : zone} · last 14 days`}>
          <Async state={daily} height={380}>
            {() => <TimeSeries data={chart.rows} series={chart.zones} resolution="daily" unit="kWh/day" digits={0}
              variant={chart.zones.length > 1 ? "stack" : "line"} height={352} />}
          </Async>
        </Panel>
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Panel title="Forecast accuracy">
            <Async state={overview} height={110}>{(d) => <Accuracy a={d.forecast_accuracy} />}</Async>
          </Panel>
          <Panel title="Sensor health" subtitle="Share of readings by status, last 7 days">
            <Async state={overview} height={160}>{(d) => <SensorHealth health={d.sensor_health} />}</Async>
          </Panel>
        </div>
      </div>

      <Panel title="Zone comparison" subtitle="Last 24 hours. Select a zone to filter the whole dashboard." flush>
        <Async state={overview} height={220}>{(d) => <ZoneTable zones={d.zones} onSelect={setZone} />}</Async>
      </Panel>
    </>
  );
}
