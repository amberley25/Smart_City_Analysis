import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { LegendRow, TooltipBox } from "../../components/charts.jsx";
import { Panel } from "../../components/ui.jsx";
import { AXIS } from "../../lib/chartTheme.js";
import { num, percent } from "../../lib/format.js";

const COLORS = ["var(--s1)", "var(--s2)", "var(--s4)", "var(--s3)"];
const SHORT = {
  "Isolation forest (engineered features)": "Isolation forest, engineered features",
  "Isolation forest (raw readings)": "Isolation forest, raw readings",
  "Robust z-score (energy only)": "Robust z-score, energy only",
  "Isolation forest (no voltage rule)": "Isolation forest, no voltage rule (ablation)",
};

export function MethodTable({ anomaly }) {
  const cols = [
    { key: "precision", label: "Precision" }, { key: "recall", label: "Recall" }, { key: "f1", label: "F1" },
    { key: "roc_auc", label: "ROC AUC" }, { key: "pr_auc", label: "PR AUC" },
  ];
  return (
    <Panel title="Detector comparison"
      subtitle={`Scored on ${num(anomaly.holdout_rows, 0)} holdout readings containing ${anomaly.holdout_anomalies} injected faults. Precision, recall and F1 use a ${percent(anomaly.alert_rate * 100)} alert budget.`}
      flush>
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr><th scope="col">Method</th>{cols.map((c) => <th key={c.key} scope="col" className="num">{c.label}</th>)}</tr>
          </thead>
          <tbody>
            {anomaly.methods.map((m, i) => (
              <tr key={m.name}>
                <th scope="row" style={{ textAlign: "left", fontWeight: i === 0 ? 600 : 400 }}>
                  <span className="swatch" style={{ background: COLORS[i], display: "inline-block", marginRight: 8 }} />
                  {SHORT[m.name]}
                </th>
                {cols.map((c) => (
                  <td key={c.key} className="num">
                    <div className="cell-bar">
                      <span className="track"><span className="fill" style={{ width: `${m[c.key] * 100}%`, background: COLORS[i] }} /></span>
                      <span className="value">{num(m[c.key], 3)}</span>
                    </div>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}

function CurvePanel({ title, subtitle, anomaly, curve, xLabel, yLabel, diagonal }) {
  return (
    <Panel title={title} subtitle={subtitle}>
      <LegendRow items={anomaly.methods.map((m, i) => ({ label: SHORT[m.name], color: COLORS[i] }))} />
      <div className="chart" role="img" aria-label={title}>
        <ResponsiveContainer width="100%" height={300} initialDimension={{ width: 400, height: 300 }}>
          <LineChart margin={{ top: 6, right: 12, bottom: 18, left: 0 }}>
            <CartesianGrid stroke="var(--grid)" />
            <XAxis type="number" dataKey="x" domain={[0, 1]} ticks={[0, 0.25, 0.5, 0.75, 1]} {...AXIS} tickFormatter={(v) => num(v, 2)}
              label={{ value: xLabel, position: "insideBottom", offset: -10, fill: "var(--muted)", fontSize: 11 }} />
            <YAxis type="number" domain={[0, 1.02]} ticks={[0, 0.25, 0.5, 0.75, 1]} {...AXIS} axisLine={false} width={64} tickFormatter={(v) => num(v, 2)}
              label={{ value: yLabel, angle: -90, position: "insideLeft", fill: "var(--muted)", fontSize: 11, dx: 0 }} />
            <Tooltip content={<TooltipBox labelFormat={(v) => `${xLabel} ${num(v, 3)}`} valueFormat={(v) => num(v, 3)} />} />
            {diagonal && <ReferenceLine segment={[{ x: 0, y: 0 }, { x: 1, y: 1 }]} stroke="var(--border-strong)" strokeDasharray="4 3" />}
            {anomaly.methods.map((m, i) => (
              <Line key={m.name} data={anomaly.curves[m.name][curve].map(([x, y]) => ({ x, y }))} dataKey="y" name={SHORT[m.name]}
                stroke={COLORS[i]} strokeWidth={1.8} dot={false} isAnimationActive={false} type="linear" />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Panel>
  );
}

export const RocPanel = ({ anomaly }) => (
  <CurvePanel title="ROC curve" subtitle="Detection rate against false alarm rate across all thresholds." anomaly={anomaly}
    curve="roc" xLabel="False positive rate" yLabel="True positive rate" diagonal />
);

export const PrPanel = ({ anomaly }) => (
  <CurvePanel title="Precision-recall curve" subtitle="More informative than ROC when faults are rare (under 3% of readings)." anomaly={anomaly}
    curve="pr" xLabel="Recall" yLabel="Precision" />
);

export function Confusion({ anomaly }) {
  const c = anomaly.methods[0].confusion;
  const neg = c.tn + c.fp;
  const pos = c.tp + c.fn;
  const cell = (value, share, extra) => (
    <div className={`cell ${extra}`}><b>{num(value, 0)}</b><span>{percent(share * 100)}</span></div>
  );
  return (
    <Panel title="Confusion matrix" subtitle="Engineered-feature isolation forest on the holdout.">
      <div className="confusion" role="table" aria-label="Confusion matrix">
        <div />
        <div className="axis">Predicted normal</div>
        <div className="axis">Predicted anomaly</div>
        <div className="axis">Actually normal</div>
        {cell(c.tn, c.tn / neg, "")}
        {cell(c.fp, c.fp / neg, "")}
        <div className="axis">Actually anomalous</div>
        {cell(c.fn, c.fn / pos, "miss")}
        {cell(c.tp, c.tp / pos, "strong")}
      </div>
      <p className="muted" style={{ marginTop: 10, fontSize: 12 }}>Percentages are shares of each true class.</p>
    </Panel>
  );
}

export function RecallByType({ anomaly }) {
  const label = (t) => t.replace("_", " ");
  const sag = anomaly.per_type.find((t) => t.type === "voltage_sag");
  const ruleGain = sag && sag.recall_without_rule != null && sag.recall > sag.recall_without_rule
    ? { alone: sag.recall_without_rule, full: sag.recall }
    : null;
  return (
    <Panel title="Detection rate by fault type" subtitle="Share of injected fault hours that were flagged.">
      <div className="bars">
        {anomaly.per_type.map((t) => (
          <div className="bar-row" key={t.type}>
            <span style={{ textTransform: "capitalize" }}>{label(t.type)}</span>
            <span className="track"><span className="fill" style={{ width: `${(t.recall ?? 0) * 100}%` }} /></span>
            <span className="meta"><strong style={{ color: "var(--text)", fontWeight: 600 }}>{percent((t.recall ?? 0) * 100, 0)}</strong> n={t.count}</span>
          </div>
        ))}
      </div>
      <p className="muted" style={{ marginTop: 14, fontSize: 12 }}>
        Mild demand spikes close to normal variation are the hardest to separate; outages and metering faults are the easiest.
        {ruleGain && ` A fixed grid-limit voltage rule lifts voltage-sag recall from ${percent(ruleGain.alone * 100, 0)} (learned detector alone) to ${percent(ruleGain.full * 100, 0)}.`}
      </p>
    </Panel>
  );
}
