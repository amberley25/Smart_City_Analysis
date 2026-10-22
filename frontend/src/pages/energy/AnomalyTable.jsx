import { useState } from "react";
import { api } from "../../api.js";
import { Async, Empty, Panel } from "../../components/ui.jsx";
import { useApi } from "../../hooks/useApi.js";
import { useZone } from "../../hooks/useZone.js";
import { dateTime, num } from "../../lib/format.js";

const PAGE = 10;

export default function AnomalyTable() {
  const { zone } = useZone();
  const [page, setPage] = useState({ zone, offset: 0 });
  const offset = page.zone === zone ? page.offset : 0;
  const setOffset = (next) => setPage({ zone, offset: next });
  const state = useApi((s) => api.anomalies({ zone, limit: PAGE, offset }, s), [zone, offset]);

  return (
    <Panel title="Flagged readings" subtitle={`${zone === "all" ? "All zones" : zone} · last 30 days · most recent first`} flush>
      <Async state={state} height={320}>
        {(d) =>
          d.records.length === 0 ? (
            <Empty>No readings were flagged in this window.</Empty>
          ) : (
            <>
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th scope="col">Time</th><th scope="col">Zone</th>
                      <th scope="col" className="num">Energy (kWh)</th><th scope="col" className="num">Score</th>
                      <th scope="col">Why it was flagged</th><th scope="col">Ground truth (simulated)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {d.records.map((r) => (
                      <tr key={`${r.zone}-${r.timestamp}`}>
                        <td style={{ whiteSpace: "nowrap" }}>{dateTime(r.timestamp)}</td>
                        <td>{r.zone}</td>
                        <td className="num">{num(r.energy_kwh, 1)}</td>
                        <td className="num">{num(r.score, 3)}</td>
                        <td style={{ minWidth: 260 }}>{r.reasons.join("; ")}</td>
                        <td>{r.true_type ? <span className="badge warn">{r.true_type.replace("_", " ")}</span> : <span className="badge">none injected</span>}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="pager">
                <span>{offset + 1}–{Math.min(offset + PAGE, d.total)} of {d.total}</span>
                <div>
                  <button type="button" className="btn" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))}>Previous</button>
                  <button type="button" className="btn" disabled={offset + PAGE >= d.total} onClick={() => setOffset(offset + PAGE)}>Next</button>
                </div>
              </div>
            </>
          )
        }
      </Async>
    </Panel>
  );
}
