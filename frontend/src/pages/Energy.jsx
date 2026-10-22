import { useState } from "react";
import ProfileChart from "../components/ProfileChart.jsx";
import SeriesExplorer from "../components/SeriesExplorer.jsx";
import AnomalyCheck from "./energy/AnomalyCheck.jsx";
import AnomalyTable from "./energy/AnomalyTable.jsx";
import ForecastTool from "./energy/ForecastTool.jsx";
import RequestLog from "./energy/RequestLog.jsx";

export default function Energy() {
  const [logVersion, setLogVersion] = useState(0);
  const bump = () => setLogVersion((n) => n + 1);
  return (
    <>
      <div className="grid wide-left">
        <SeriesExplorer slug="energy" title="Substation telemetry" measures={["energy_kwh", "voltage_v", "current_a", "power_factor"]} defaultResolution="hourly" />
        <ProfileChart slug="energy" title="Typical daily profile" unit="kWh" />
      </div>
      <div className="grid cols-2">
        <ForecastTool onSubmitted={bump} />
        <AnomalyCheck onSubmitted={bump} />
      </div>
      <AnomalyTable />
      <RequestLog refreshKey={logVersion} />
    </>
  );
}
