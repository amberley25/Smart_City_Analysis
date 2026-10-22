import { useEffect, useState } from "react";

export const ROUTES = ["overview", "energy", "environment", "mobility", "models"];

function read() {
  const name = window.location.hash.replace(/^#\/?/, "").split(/[/?]/)[0];
  return ROUTES.includes(name) ? name : "overview";
}

export function useHashRoute() {
  const [route, setRoute] = useState(read);
  useEffect(() => {
    const onChange = () => {
      setRoute(read());
      window.scrollTo({ top: 0 });
    };
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return route;
}
