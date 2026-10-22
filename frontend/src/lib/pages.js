import { Gauge, LayoutDashboard, Route, Wind, Zap } from "lucide-react";

export const PAGES = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "energy", label: "Energy", icon: Zap },
  { id: "environment", label: "Environment", icon: Wind },
  { id: "mobility", label: "Mobility", icon: Route },
  { id: "models", label: "Model performance", icon: Gauge },
];
