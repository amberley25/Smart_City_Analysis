import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api.js";
import { useApi } from "../hooks/useApi.js";
import { useZone } from "../hooks/useZone.js";
import { num } from "../lib/format.js";
import { AXIS, ZERO_TO_NICE } from "../lib/chartTheme.js";
import { LegendRow, TooltipBox } from "./charts.jsx";
import { Async, Panel } from "./ui.jsx";

const pad = (h) => `${String(h).padStart(2, "0")}:00`;

/** Mean value by hour of day, weekdays against weekends. */
export default function ProfileChart({ slug, title, unit, digits = 0 }) {
  const { zone } = useZone();
  const state = useApi((s) => api.seriesProfile(slug, { zone }, s), [slug, zone]);
  return (
    <Panel title={title} subtitle={`${zone === "all" ? "All zones, mean" : zone} · full dataset`}>
      <Async state={state} height={280}>
        {(d) => (
          <div className="chart" role="img" aria-label={`${title}, weekday and weekend`}>
            <LegendRow items={[{ label: "Weekday", color: "var(--s1)" }, { label: "Weekend", color: "var(--s2)" }]} />
            <ResponsiveContainer width="100%" height={250} initialDimension={{ width: 500, height: 250 }}>
              <LineChart data={d.profile} margin={{ top: 6, right: 12, bottom: 0, left: 0 }}>
                <CartesianGrid stroke="var(--grid)" vertical={false} />
                <XAxis dataKey="hour" {...AXIS} tickFormatter={pad} interval={2} />
                <YAxis {...AXIS} axisLine={false} width={52} domain={ZERO_TO_NICE} tickFormatter={(v) => num(v, 0)} />
                <Tooltip content={<TooltipBox labelFormat={pad} valueFormat={(v) => `${num(v, digits)} ${unit}`} />} />
                <Line type="monotone" dataKey="weekday" name="Weekday" stroke="var(--s1)" strokeWidth={1.8} dot={false} isAnimationActive={false} />
                <Line type="monotone" dataKey="weekend" name="Weekend" stroke="var(--s2)" strokeWidth={1.8} dot={false} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </Async>
    </Panel>
  );
}
