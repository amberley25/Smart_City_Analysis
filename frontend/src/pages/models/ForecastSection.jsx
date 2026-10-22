import {
  Area, CartesianGrid, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis,
  LineChart,
} from "recharts";
import { Bars, LegendRow, TooltipBox } from "../../components/charts.jsx";
import { Panel, SelectField } from "../../components/ui.jsx";
import { AXIS } from "../../lib/chartTheme.js";
import { fullStamp, hourTick, num } from "../../lib/format.js";
import { ZONES } from "../../lib/measures.js";

const BASELINES = new Set(["Persistence", "Seasonal naive (24h)"]);
const kwh = (v) => `${num(v, 1)} kWh`;
const grid = <CartesianGrid stroke="var(--grid)" vertical={false} />;

export function ModelComparison({ block }) {
  const data = [...block.models].sort((a, b) => a.test_mae - b.test_mae);
  const color = (r) => (BASELINES.has(r.name) ? "var(--faint)" : r.name === block.best_model ? "var(--accent)" : "var(--accent-soft)");
  return (
    <Panel title="Model comparison" subtitle="Mean absolute error on the 28-day holdout, with cross-validated error beside it. Lower is better.">
      <LegendRow items={[
        { label: "Selected model", color: "var(--accent)" },
        { label: "Other candidates", color: "var(--accent-soft)" },
        { label: "Naive baselines", color: "var(--faint)" },
        { label: "5-fold time-series CV", color: "var(--border-strong)" },
      ]} />
      <Bars data={data} layout="vertical" height={270} labelWidth={150} valueFormat={(v) => num(v, 1)} legend={false}
        bars={[
          { key: "test_mae", name: "Holdout MAE (kWh)", color: "var(--accent)", cells: true },
          { key: "cv_mae", name: "Cross-validated MAE (kWh)", color: "var(--border-strong)" },
        ]}
        cellColor={color} />
    </Panel>
  );
}

export function Backtest({ block, zone, onZone }) {
  const data = block.backtest.filter((r) => r.zone === zone).map((r) => ({
    t: r.timestamp, actual: r.actual, predicted: r.predicted, band: [r.lower, r.upper],
  }));
  return (
    <Panel title="Holdout week, forecast against actual"
      subtitle={`${block.horizon_hours}-hour-ahead forecasts for the final seven days. Shaded band is the ${Math.round(block.interval.nominal * 100)}% interval.`}
      actions={<SelectField inline label="Zone" value={zone} onChange={onZone} options={ZONES.map((z) => ({ value: z, label: z }))} />}>
      <LegendRow items={[
        { label: "Actual", color: "var(--text)" }, { label: "Forecast", color: "var(--accent)" },
        { label: `${Math.round(block.interval.nominal * 100)}% interval`, color: "var(--accent-soft)" },
      ]} />
      <div className="chart" role="img" aria-label={`Forecast against actual energy for ${zone}`}>
        <ResponsiveContainer width="100%" height={280} initialDimension={{ width: 700, height: 280 }}>
          <ComposedChart data={data} margin={{ top: 6, right: 12, bottom: 0, left: 0 }}>
            {grid}
            <XAxis dataKey="t" {...AXIS} tickFormatter={hourTick} minTickGap={64} interval="preserveStartEnd" />
            <YAxis {...AXIS} axisLine={false} width={52} domain={["auto", "auto"]} tickFormatter={(v) => num(v, 0)} />
            <Tooltip content={<TooltipBox labelFormat={fullStamp} valueFormat={kwh} />} />
            <Area dataKey="band" name="Interval" stroke="none" fill="var(--accent-soft)" fillOpacity={0.5} isAnimationActive={false} />
            <Line dataKey="actual" name="Actual" stroke="var(--text)" strokeWidth={1.4} dot={false} isAnimationActive={false} />
            <Line dataKey="predicted" name="Forecast" stroke="var(--accent)" strokeWidth={1.6} strokeDasharray="5 3" dot={false} isAnimationActive={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </Panel>
  );
}

export function ScatterPanel({ block }) {
  const points = block.scatter.map(([x, y]) => ({ x, y }));
  const max = Math.ceil(Math.max(...points.map((p) => Math.max(p.x, p.y))) / 100) * 100;
  return (
    <Panel title="Forecast against actual" subtitle="Each point is one holdout hour. Points on the line are perfect forecasts.">
      <div className="chart" role="img" aria-label="Scatter of forecast against actual energy">
        <ResponsiveContainer width="100%" height={300} initialDimension={{ width: 400, height: 300 }}>
          <ScatterChart margin={{ top: 6, right: 12, bottom: 18, left: 0 }}>
            <CartesianGrid stroke="var(--grid)" />
            <XAxis type="number" dataKey="x" name="Actual" domain={[0, max]} {...AXIS} tickFormatter={(v) => num(v, 0)}
              label={{ value: "Actual (kWh)", position: "insideBottom", offset: -10, fill: "var(--muted)", fontSize: 11 }} />
            <YAxis type="number" dataKey="y" name="Forecast" domain={[0, max]} {...AXIS} axisLine={false} width={64} tickFormatter={(v) => num(v, 0)}
              label={{ value: "Forecast (kWh)", angle: -90, position: "insideLeft", fill: "var(--muted)", fontSize: 11, dx: 0 }} />
            <Tooltip cursor={{ strokeDasharray: "3 3" }} content={<TooltipBox valueFormat={kwh} />} />
            <ReferenceLine segment={[{ x: 0, y: 0 }, { x: max, y: max }]} stroke="var(--s2)" strokeWidth={1.4} />
            <Scatter data={points} fill="var(--accent)" fillOpacity={0.35} isAnimationActive={false} />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </Panel>
  );
}

export function ResidualPanel({ block }) {
  const { counts, edges } = block.residual_histogram;
  const data = counts.map((c, i) => ({ name: Math.round((edges[i] + edges[i + 1]) / 2), count: c }));
  return (
    <Panel title="Error distribution" subtitle="Actual minus forecast. Centred near zero means no systematic bias.">
      <Bars data={data} height={300} valueFormat={(v) => num(v, 0)} legend={false} yLabel="Hours" sparseTicks
        bars={[{ key: "count", name: "Hours", color: "var(--accent)" }]} />
    </Panel>
  );
}

export function ErrorByHour({ forecast }) {
  const data = Array.from({ length: 24 }, (_, h) => ({ hour: h, h1: forecast["1"].mae_by_hour[h], h24: forecast["24"].mae_by_hour[h] }));
  const pad = (h) => `${String(h).padStart(2, "0")}:00`;
  return (
    <Panel title="Error by hour of day" subtitle="Morning ramp-up hours are hardest to predict.">
      <LegendRow items={[{ label: "1 hour ahead", color: "var(--s1)" }, { label: "24 hours ahead", color: "var(--s2)" }]} />
      <div className="chart" role="img" aria-label="Mean absolute error by hour of day">
        <ResponsiveContainer width="100%" height={260} initialDimension={{ width: 400, height: 260 }}>
          <LineChart data={data} margin={{ top: 6, right: 12, bottom: 0, left: 0 }}>
            {grid}
            <XAxis dataKey="hour" {...AXIS} tickFormatter={pad} interval={3} />
            <YAxis {...AXIS} axisLine={false} width={40} tickFormatter={(v) => num(v, 0)} />
            <Tooltip content={<TooltipBox labelFormat={pad} valueFormat={kwh} />} />
            <Line dataKey="h1" name="1 hour ahead" stroke="var(--s1)" strokeWidth={1.8} dot={false} isAnimationActive={false} />
            <Line dataKey="h24" name="24 hours ahead" stroke="var(--s2)" strokeWidth={1.8} dot={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Panel>
  );
}

export function FeatureImportance({ block }) {
  const data = block.feature_importance.map((f) => ({ name: f.feature, value: f.importance }));
  return (
    <Panel title="Feature importance" subtitle="Increase in holdout MAE when a feature is shuffled (permutation importance).">
      <Bars data={data} layout="vertical" height={300} labelWidth={150} valueFormat={(v) => num(v, 1)} legend={false}
        bars={[{ key: "value", name: "MAE increase (kWh)", color: "var(--accent)" }]} />
    </Panel>
  );
}

export function ErrorByZone({ forecast }) {
  const data = ZONES.map((z) => ({ name: z, h1: forecast["1"].mae_by_zone[z], h24: forecast["24"].mae_by_zone[z] }));
  return (
    <Panel title="Error by zone" subtitle="Holdout MAE per zone. Larger zones carry larger absolute errors.">
      <Bars data={data} height={300} valueFormat={(v) => num(v, 1)} yLabel="MAE (kWh)"
        bars={[{ key: "h1", name: "1 hour ahead", color: "var(--s1)" }, { key: "h24", name: "24 hours ahead", color: "var(--s2)" }]} />
    </Panel>
  );
}
