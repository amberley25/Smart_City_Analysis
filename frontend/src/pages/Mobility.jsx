import { api } from "../api.js";
import { Bars } from "../components/charts.jsx";
import ProfileChart from "../components/ProfileChart.jsx";
import SeriesExplorer from "../components/SeriesExplorer.jsx";
import { Async, Panel } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";
import { num } from "../lib/format.js";
import { ZONES, ZONE_COLORS } from "../lib/measures.js";

function ZoneComparison() {
  const state = useApi(async (signal) => {
    const results = await Promise.all(ZONES.map((zone) => api.seriesSummary("traffic", { zone }, signal)));
    return ZONES.map((zone, i) => ({
      zone,
      traffic: results[i].measures.traffic_count.mean,
      speed: results[i].measures.avg_speed_kmh.mean,
      missing: results[i].measures.traffic_count.missing_pct,
    }));
  }, []);

  return (
    <Panel title="Zone comparison" subtitle="30-day means. Busier zones run slower.">
      <Async state={state} height={260}>
        {(rows) => (
          <div className="grid cols-2">
            <div>
              <h3 style={{ marginBottom: 6 }}>Vehicles per hour</h3>
              <Bars data={rows} categoryKey="zone" height={230} valueFormat={(v) => num(v, 0)}
                bars={[{ key: "traffic", name: "Vehicles per hour", color: "var(--s1)", cells: true }]} legend={false}
                cellColor={(r) => ZONE_COLORS[r.zone]} />
            </div>
            <div>
              <h3 style={{ marginBottom: 6 }}>Average speed (km/h)</h3>
              <Bars data={rows} categoryKey="zone" height={230} valueFormat={(v) => num(v, 1)}
                bars={[{ key: "speed", name: "Average speed", color: "var(--s1)", cells: true }]} legend={false}
                cellColor={(r) => ZONE_COLORS[r.zone]} />
            </div>
          </div>
        )}
      </Async>
    </Panel>
  );
}

export default function Mobility() {
  return (
    <>
      <div className="grid wide-left">
        <SeriesExplorer slug="traffic" title="Traffic" measures={["traffic_count", "avg_speed_kmh"]} defaultResolution="hourly" />
        <ProfileChart slug="traffic" title="Typical daily profile" unit="veh/h" />
      </div>
      <ZoneComparison />
    </>
  );
}
