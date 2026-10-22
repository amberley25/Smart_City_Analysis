import { useMemo, useState } from "react";
import { api } from "../api.js";
import { useApi } from "../hooks/useApi.js";
import { useZone } from "../hooks/useZone.js";
import { num } from "../lib/format.js";
import { labelOf, unitOf } from "../lib/measures.js";
import { pivotByZone, zonesIn } from "../lib/series.js";
import { TimeSeries } from "./charts.jsx";
import { Async, Empty, Panel, Segmented, SelectField } from "./ui.jsx";

/** Hourly/daily chart for one measure of a sensor network, following the global zone filter. */
export default function SeriesExplorer({ slug, title, measures, refLines = {}, defaultResolution = "daily", showSummary = true }) {
  const { zone } = useZone();
  const [resolution, setResolution] = useState(defaultResolution);
  const [measure, setMeasure] = useState(measures[0]);

  const series = useApi((s) => api.series(slug, { zone, resolution }, s), [slug, zone, resolution]);
  const summary = useApi((s) => api.seriesSummary(slug, { zone }, s), [slug, zone]);

  const prepared = useMemo(() => {
    if (!series.data) return null;
    return { rows: pivotByZone(series.data.records, measure), zones: zonesIn(series.data.records) };
  }, [series.data, measure]);

  const unit = unitOf(measure, resolution);
  const digits = measure === "power_factor" ? 3 : measure === "energy_kwh" || measure === "traffic_count" ? 0 : 1;

  return (
    <Panel
      title={title}
      subtitle={`${zone === "all" ? "All zones" : zone} · ${resolution === "daily" ? "daily, last 60 days" : "hourly, last 7 days"}`}
      actions={
        <>
          {measures.length > 1 && (
            <SelectField inline label="Measure" value={measure} onChange={setMeasure}
              options={measures.map((m) => ({ value: m, label: labelOf(m) }))} />
          )}
          <Segmented label="Resolution" value={resolution} onChange={setResolution}
            options={[{ value: "hourly", label: "Hourly" }, { value: "daily", label: "Daily" }]} />
        </>
      }
      flush={showSummary}
    >
      <div style={showSummary ? { padding: 16 } : undefined}>
        <Async state={series} height={300}>
          {() =>
            prepared.rows.length ? (
              <TimeSeries data={prepared.rows} series={prepared.zones} resolution={resolution} unit={unit}
                digits={digits} refLines={refLines[measure] ?? []} />
            ) : (
              <Empty>No readings in this window.</Empty>
            )
          }
        </Async>
      </div>
      {showSummary && <SummaryStats state={summary} measures={measures.length > 1 ? undefined : measures} />}
    </Panel>
  );
}

export function SummaryStats({ state, measures }) {
  if (state.error || !state.data) return null;
  const keys = measures ?? Object.keys(state.data.measures);
  return (
    <div className="stat-grid" aria-label="30 day summary">
      {keys.map((m) => {
        const s = state.data.measures[m];
        return (
          <div className="stat" key={m}>
            <div className="stat-label">{labelOf(m)}, 30-day mean</div>
            <div className="stat-value">
              {num(s.mean, m === "power_factor" ? 3 : 1)}
              <small>{unitOf(m, "hourly")}</small>
            </div>
            <div className="stat-note">
              range {num(s.min, 1)}–{num(s.max, 1)} · {num(s.missing_pct, 1)}% missing
            </div>
          </div>
        );
      })}
    </div>
  );
}
