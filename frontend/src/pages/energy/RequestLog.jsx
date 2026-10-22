import { api } from "../../api.js";
import { Async, Empty, Panel } from "../../components/ui.jsx";
import { useApi } from "../../hooks/useApi.js";
import { num } from "../../lib/format.js";

function summarise(r) {
  if (r.kind === "forecast") {
    const { forecast_kwh: f, interval: i } = r.response;
    return `${num(f, 1)} kWh (${num(i.lower, 0)}–${num(i.upper, 0)})`;
  }
  return r.response.classification;
}

export default function RequestLog({ refreshKey }) {
  const state = useApi((s) => api.predictions({ limit: 8 }, s), [refreshKey]);
  return (
    <Panel title="Recent requests" subtitle="Forecasts and reading checks stored by the API" flush>
      <Async state={state} height={160}>
        {(d) =>
          d.records.length === 0 ? (
            <Empty>Nothing yet. Run a forecast or check a reading above.</Empty>
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr><th scope="col">#</th><th scope="col">Received</th><th scope="col">Type</th><th scope="col">Zone</th><th scope="col">Target time</th><th scope="col">Result</th></tr>
                </thead>
                <tbody>
                  {d.records.map((r) => (
                    <tr key={r.id}>
                      <td className="muted">{r.id}</td>
                      <td style={{ whiteSpace: "nowrap" }}>{r.created_at.replace("T", " ").replace("Z", " UTC")}</td>
                      <td><span className="badge">{r.kind}</span></td>
                      <td>{r.zone}</td>
                      <td style={{ whiteSpace: "nowrap" }}>{r.target_time?.replace("T", " ").slice(0, 16)}</td>
                      <td>{summarise(r)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        }
      </Async>
    </Panel>
  );
}
