import { useState } from "react";
import { api } from "../api.js";
import { Async, Notice, Panel, Segmented } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";
import { useZone } from "../hooks/useZone.js";
import { dateTime, longDate, num, percent } from "../lib/format.js";
import { Confusion, MethodTable, PrPanel, RecallByType, RocPanel } from "./models/AnomalySection.jsx";
import { Backtest, ErrorByHour, ErrorByZone, FeatureImportance, ModelComparison, ResidualPanel, ScatterPanel } from "./models/ForecastSection.jsx";

const FIGURES = [
  ["forecast_model_comparison.png", "Forecast model comparison"],
  ["forecast_backtest.png", "Holdout week, all zones"],
  ["forecast_diagnostics.png", "Forecast diagnostics"],
  ["anomaly_benchmark.png", "Anomaly detector benchmark"],
  ["anomaly_detail.png", "Anomaly confusion and recall"],
  ["anomaly_timeline.png", "Anomaly detections over time"],
  ["eda_daily_profiles.png", "Daily demand profiles"],
  ["eda_relationships.png", "Cross-domain relationships"],
  ["eda_data_quality.png", "Sensor data quality"],
];

function Tiles({ m, horizon }) {
  const block = m.forecast[horizon];
  const best = block.models.find((x) => x.name === block.best_model);
  const primary = m.anomaly.methods[0];
  const tiles = [
    { label: "Selected model", value: block.best_model, note: `${horizon}-hour horizon` },
    { label: "Holdout MAE", value: num(best.test_mae, 1), unit: "kWh", note: `RMSE ${num(best.test_rmse, 1)} kWh` },
    { label: "R²", value: num(best.test_r2, 3), note: `sMAPE ${num(best.test_smape, 1)}%` },
    { label: "Beats naive baseline by", value: num(block.improvement_vs_best_baseline_pct, 1), unit: "%", note: "lower MAE than best baseline" },
    { label: "Interval coverage", value: percent(block.interval.empirical * 100), note: `nominal ${percent(block.interval.nominal * 100, 0)}` },
    { label: "Anomaly precision", value: num(primary.precision, 2), note: `recall ${num(primary.recall, 2)}` },
    { label: "Anomaly ROC AUC", value: num(primary.roc_auc, 3), note: `PR AUC ${num(primary.pr_auc, 3)}` },
  ];
  return (
    <section className="panel tiles" aria-label="Headline metrics">
      {tiles.map((t) => (
        <div className="tile" key={t.label}>
          <div className="tile-label">{t.label}</div>
          <div className="tile-value" style={t.value.length > 12 ? { fontSize: 15, lineHeight: "28px" } : undefined}>
            {t.value}{t.unit && <small>{t.unit}</small>}
          </div>
          <div className="tile-note">{t.note}</div>
        </div>
      ))}
    </section>
  );
}

function Method({ m }) {
  const d = m.dataset;
  return (
    <Panel title="How these numbers were produced">
      <div className="prose">
        <p>
          <strong>Forecasting.</strong> Candidates are compared with 5-fold time-series cross-validation on the training period, then every
          candidate is scored once on a chronological holdout: the final {d.holdout_days} days ({longDate(d.holdout_start)} onward), which no
          model saw during fitting. Two naive baselines (persistence and same hour yesterday) set the bar. The interval is calibrated from
          out-of-fold residuals per zone.
        </p>
        <p>
          <strong>Anomaly detection.</strong> Detectors are unsupervised and never see labels. Each flags the top {percent(m.anomaly.alert_rate * 100)} of
          training scores, so the comparison uses an equal alert budget. Faults are injected by the simulator, which provides ground truth.
        </p>
        <p>
          <strong>Read with care.</strong> The dataset is simulated, so absolute numbers are likely more favourable than a real deployment would
          show. The comparisons between methods are the meaningful part. Weather at the target hour is treated as a known forecast input.
        </p>
      </div>
    </Panel>
  );
}

export default function Models() {
  const { zone } = useZone();
  const state = useApi((s) => api.metrics(s), []);
  const [horizon, setHorizon] = useState("1");
  const [backtestZone, setBacktestZone] = useState(zone === "all" ? "Downtown" : zone);

  return (
    <Async state={state} height={420}>
      {(m) => (
        <>
          <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 12 }}>
            <Segmented label="Forecast horizon" value={horizon} onChange={setHorizon}
              options={[{ value: "1", label: "1 hour ahead" }, { value: "24", label: "24 hours ahead" }]} />
            <span className="muted">Report generated {dateTime(m.generated_at)} UTC · holdout from {longDate(m.dataset.holdout_start)}</span>
          </div>
          <Tiles m={m} horizon={horizon} />

          <h2 style={{ marginTop: 8 }}>Energy forecasting</h2>
          <div className="grid cols-2"><ModelComparison block={m.forecast[horizon]} /><ScatterPanel block={m.forecast[horizon]} /></div>
          <Backtest block={m.forecast[horizon]} zone={backtestZone} onZone={setBacktestZone} />
          <div className="grid cols-3">
            <ResidualPanel block={m.forecast[horizon]} />
            <ErrorByHour forecast={m.forecast} />
            <ErrorByZone forecast={m.forecast} />
          </div>
          <FeatureImportance block={m.forecast[horizon]} />

          <h2 style={{ marginTop: 8 }}>Anomaly detection</h2>
          <MethodTable anomaly={m.anomaly} />
          <div className="grid cols-2"><RocPanel anomaly={m.anomaly} /><PrPanel anomaly={m.anomaly} /></div>
          <div className="grid cols-2 stretch"><Confusion anomaly={m.anomaly} /><RecallByType anomaly={m.anomaly} /></div>

          <Method m={m} />
          <Panel title="Static figures" subtitle="Print-ready versions of the evaluation charts, generated by the training pipeline.">
            <ul className="figures">
              {FIGURES.map(([file, label]) => (
                <li key={file}><a href={api.figureUrl(file)} target="_blank" rel="noreferrer">{label}</a></li>
              ))}
            </ul>
          </Panel>
          <Notice>Figures are served from the API and appear once <code>smartcity train</code> has run.</Notice>
        </>
      )}
    </Async>
  );
}
