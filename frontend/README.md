# Smart City dashboard

React 19 + Vite single-page app for the Smart City Analytics API. Charts use Recharts, icons come from lucide-react, and
there is no other runtime dependency. Light and dark themes follow the operating system setting.

## Development

```bash
npm install
npm run dev        # http://localhost:5173, proxies /api to http://127.0.0.1:5000
npm run lint
npm test           # vitest: formatting, API client, data hook, form flow
npm run build      # production bundle in dist/
npm run preview    # serve the bundle, same /api proxy
```

Start the API first (`make serve` or `smartcity serve` from the repository root). If the API is down the dashboard shows
an error banner with the command to run.

## Configuration

| Variable | Purpose | Default |
| --- | --- | --- |
| `VITE_API_BASE` | Absolute API origin baked in at build time, for deployments where the API is on another host | empty (same origin, `/api/v1`) |
| `VITE_PROXY_TARGET` | Target of the dev/preview `/api` proxy | `http://127.0.0.1:5000` |

## Structure

```
src/
  api.js            fetch client, ApiError, one function per endpoint
  hooks/            useApi (abort + loading/error), useHashRoute, useZone
  lib/              formatting, measure metadata, series helpers, chart theme
  components/       Shell, UI primitives, chart wrappers, SeriesExplorer
  pages/            Overview, Energy, Environment, Mobility, Models
    energy/         forecast tool, reading check, anomaly table, request log
    models/         forecast and anomaly evaluation panels
  styles/           layout, component and page CSS (tokens live in index.css)
```

Routes are hash based (`#/overview`, `#/energy`, `#/environment`, `#/mobility`, `#/models`), so the built app can be
served from any static host. The zone selector in the top bar is shared by every page.
