import { createContext, useContext } from "react";

export const ZoneContext = createContext(null);

export function useZone() {
  const ctx = useContext(ZoneContext);
  if (!ctx) throw new Error("useZone must be used inside ZoneProvider");
  return ctx;
}
