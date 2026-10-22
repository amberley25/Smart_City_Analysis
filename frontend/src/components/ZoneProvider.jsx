import { useMemo, useState } from "react";
import { ZoneContext } from "../hooks/useZone.js";
import { ZONES } from "../lib/measures.js";

const STORAGE_KEY = "smartcity.zone";

function initial() {
  try {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    return saved === "all" || ZONES.includes(saved) ? saved : "all";
  } catch {
    return "all";
  }
}

export default function ZoneProvider({ children }) {
  const [zone, setZoneState] = useState(initial);
  const value = useMemo(
    () => ({
      zone,
      setZone: (next) => {
        setZoneState(next);
        try {
          window.localStorage.setItem(STORAGE_KEY, next);
        } catch {
          /* storage unavailable: the selection is simply not remembered */
        }
      },
    }),
    [zone],
  );
  return <ZoneContext.Provider value={value}>{children}</ZoneContext.Provider>;
}
