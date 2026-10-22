import { api } from "../api.js";
import { useApi } from "../hooks/useApi.js";
import { useZone } from "../hooks/useZone.js";
import { dateTime } from "../lib/format.js";
import { ZONES } from "../lib/measures.js";
import { PAGES } from "../lib/pages.js";
import { SelectField } from "./ui.jsx";

function Sidebar({ route }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-inner">
      <div className="brand">
        <svg className="brand-mark" viewBox="0 0 32 32" aria-hidden="true">
          <rect width="32" height="32" rx="6" fill="var(--accent)" />
          <path d="M6 22V13h4v9zm8 0V9h4v13zm8 0v-6h4v6z" fill="#fff" />
        </svg>
        <span>Smart City</span>
      </div>
      <nav className="nav" aria-label="Primary">
        {PAGES.map(({ id, label, icon: Icon }) => (
          <a key={id} href={`#/${id}`} aria-current={route === id ? "page" : undefined}>
            <Icon aria-hidden="true" />
            {label}
          </a>
        ))}
      </nav>
      <div className="sidebar-foot">Simulated sensor network</div>
      </div>
    </aside>
  );
}

function Status({ state }) {
  if (state.error) {
    return (
      <span className="api-status">
        <span className="dot bad" /> API unreachable
      </span>
    );
  }
  if (!state.data) return <span className="api-status">Connecting</span>;
  const { status, data_range: range } = state.data;
  return (
    <span className="api-status">
      <span className={`dot ${status === "ok" ? "ok" : "warn"}`} />
      {range ? `Data through ${dateTime(range.last)}` : "No data loaded"}
    </span>
  );
}

export default function Shell({ route, children }) {
  const { zone, setZone } = useZone();
  const health = useApi((s) => api.health(s), []);
  const page = PAGES.find((p) => p.id === route);
  return (
    <div className="shell">
      <Sidebar route={route} />
      <div className="main">
        <header className="topbar">
          <h1>{page.label}</h1>
          <Status state={health} />
          <SelectField inline label="Zone" value={zone} onChange={setZone}
            options={[{ value: "all", label: "All zones" }, ...ZONES.map((z) => ({ value: z, label: z }))]} />
        </header>
        <main className="content" id="content">
          {children}
        </main>
      </div>
    </div>
  );
}

