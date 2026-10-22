import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fullStamp, hourTick, num, shortDate } from "../lib/format.js";
import { AXIS, ZERO_TO_NICE } from "../lib/chartTheme.js";
import { ZONE_COLORS } from "../lib/measures.js";


export function TooltipBox({ active, payload, label, labelFormat, valueFormat, hide = [] }) {
  if (!active || !payload?.length) return null;
  const rows = payload.filter((p) => p.value != null && !hide.includes(p.dataKey));
  if (!rows.length) return null;
  return (
    <div className="tooltip">
      <div className="tooltip-title">{labelFormat ? labelFormat(label) : label}</div>
      {rows.map((p) => (
        <div className="tooltip-row" key={`${p.dataKey}-${p.name}`}>
          <span className="swatch" style={{ background: p.color ?? p.stroke ?? p.fill }} />
          <span>{p.name}</span>
          <b>{Array.isArray(p.value) ? p.value.map((v) => valueFormat(v)).join(" – ") : valueFormat(p.value, p)}</b>
        </div>
      ))}
    </div>
  );
}

export function LegendRow({ items }) {
  return (
    <div className="legend">
      {items.map((i) => (
        <span key={i.label}>
          <span className="swatch" style={{ background: i.color }} />
          {i.label}
        </span>
      ))}
    </div>
  );
}

/**
 * Time series with one line per key in `series`. `variant="stack"` draws stacked areas
 * (used for city-wide totals); otherwise plain lines.
 */
export function TimeSeries({ data, series, resolution = "hourly", unit = "", digits = 1, variant = "line", height = 280,
  refLines = [], yDomain }) {
  const tick = resolution === "daily" ? shortDate : hourTick;
  const valueFormat = (v) => `${num(v, digits)}${unit ? ` ${unit}` : ""}`;
  const colorOf = (key) => ZONE_COLORS[key] ?? "var(--s1)";
  const Chart = variant === "stack" ? AreaChart : LineChart;

  return (
    <div className="chart" role="img" aria-label={`Time series chart${unit ? ` in ${unit}` : ""}`}>
      <div className="chart-head">
        {series.length > 1 ? <LegendRow items={series.map((k) => ({ label: k, color: colorOf(k) }))} /> : <span />}
        {unit && <span className="axis-unit">{unit}</span>}
      </div>
      <ResponsiveContainer width="100%" height={height} initialDimension={{ width: 600, height }}>
        <Chart data={data} margin={{ top: 6, right: 12, bottom: 0, left: 0 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="t" {...AXIS} tickFormatter={tick} minTickGap={56} interval="preserveStartEnd" />
          <YAxis {...AXIS} axisLine={false} width={52} domain={yDomain} tickFormatter={(v) => num(v, digits > 1 ? 1 : 0)} />
          <Tooltip content={<TooltipBox labelFormat={fullStamp} valueFormat={valueFormat} />} />
          {refLines.map((r) => (
            <ReferenceLine key={r.label} y={r.y} stroke="var(--danger)" strokeDasharray="4 3"
              label={{ value: r.label, fill: "var(--danger)", fontSize: 11, position: "insideTopLeft", stroke: "var(--surface)", strokeWidth: 4, paintOrder: "stroke" }} />
          ))}
          {series.map((key) =>
            variant === "stack" ? (
              <Area key={key} type="monotone" dataKey={key} name={key} stackId="1" stroke={colorOf(key)}
                fill={colorOf(key)} fillOpacity={0.55} strokeWidth={1} isAnimationActive={false} />
            ) : (
              <Line key={key} type="monotone" dataKey={key} name={key} stroke={colorOf(key)} strokeWidth={1.6}
                dot={false} activeDot={{ r: 3 }} isAnimationActive={false} />
            ),
          )}
        </Chart>
      </ResponsiveContainer>
    </div>
  );
}

/**
 * Categorical bar chart. `layout="vertical"` draws horizontal bars with the category on the
 * y axis, which keeps long labels (model names, feature names) readable.
 */
export function Bars({ data, bars, categoryKey = "name", layout = "horizontal", height = 260, valueFormat, labelWidth = 120,
  cellColor, yLabel, legend = true, sparseTicks = false }) {
  const vertical = layout === "vertical";
  const items = bars.map((b) => ({ label: b.name, color: b.color }));
  return (
    <div className="chart">
      {legend && bars.length > 1 && <LegendRow items={items} />}
      <ResponsiveContainer width="100%" height={height} initialDimension={{ width: 500, height }}>
        <BarChart data={data} layout={layout} margin={{ top: 6, right: 16, bottom: 0, left: 0 }} barCategoryGap="16%">
          <CartesianGrid stroke="var(--grid)" horizontal={!vertical} vertical={vertical} />
          {vertical ? (
            <>
              <XAxis type="number" domain={ZERO_TO_NICE} tickCount={6} {...AXIS} axisLine={false} tickFormatter={valueFormat} />
              <YAxis type="category" dataKey={categoryKey} {...AXIS} width={labelWidth} />
            </>
          ) : (
            <>
              <XAxis dataKey={categoryKey} {...AXIS} interval={sparseTicks ? "preserveStartEnd" : 0} minTickGap={sparseTicks ? 28 : 5} />
              <YAxis {...AXIS} axisLine={false} width={yLabel ? 62 : 44} domain={ZERO_TO_NICE} tickCount={6} tickFormatter={valueFormat}
                label={yLabel ? { value: yLabel, angle: -90, position: "insideLeft", fill: "var(--muted)", fontSize: 11, dx: 0 } : undefined} />
            </>
          )}
          <Tooltip cursor={{ fill: "var(--surface-2)" }} content={<TooltipBox valueFormat={valueFormat ?? ((v) => v)} />} />
          {bars.map((b) => (
            <Bar key={b.key} dataKey={b.key} name={b.name} fill={b.color} radius={[2, 2, 2, 2]} isAnimationActive={false}>
              {cellColor && b.cells && data.map((row) => <Cell key={row[categoryKey]} fill={cellColor(row)} />)}
            </Bar>
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
