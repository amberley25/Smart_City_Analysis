import { lazy, Suspense } from "react";
import Shell from "./components/Shell.jsx";
import { Skeleton } from "./components/ui.jsx";
import ZoneProvider from "./components/ZoneProvider.jsx";
import { useHashRoute } from "./hooks/useHashRoute.js";

const PAGE_COMPONENTS = {
  overview: lazy(() => import("./pages/Overview.jsx")),
  energy: lazy(() => import("./pages/Energy.jsx")),
  environment: lazy(() => import("./pages/Environment.jsx")),
  mobility: lazy(() => import("./pages/Mobility.jsx")),
  models: lazy(() => import("./pages/Models.jsx")),
};

export default function App() {
  const route = useHashRoute();
  const Page = PAGE_COMPONENTS[route];
  return (
    <ZoneProvider>
      <Shell route={route}>
        <Suspense fallback={<Skeleton height={320} />}>
          <Page />
        </Suspense>
      </Shell>
    </ZoneProvider>
  );
}
