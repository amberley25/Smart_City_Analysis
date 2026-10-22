export const ZONES = ["Downtown", "Industrial", "Residential", "Harbor", "University"];

export const ZONE_COLORS = {
  Downtown: "var(--s1)",
  Industrial: "var(--s2)",
  Residential: "var(--s3)",
  Harbor: "var(--s4)",
  University: "var(--s5)",
};

// unit may differ by resolution because daily series sum counts and volumes.
export const MEASURES = {
  energy_kwh: { label: "Energy", unit: { hourly: "kWh", daily: "kWh/day" }, digits: 0 },
  voltage_v: { label: "Voltage", unit: "V", digits: 1 },
  current_a: { label: "Current", unit: "A", digits: 0 },
  power_factor: { label: "Power factor", unit: "", digits: 3 },
  traffic_count: { label: "Vehicle count", unit: { hourly: "veh/h", daily: "veh/day" }, digits: 0 },
  avg_speed_kmh: { label: "Average speed", unit: "km/h", digits: 1 },
  pm25_ugm3: { label: "PM2.5", unit: "µg/m³", digits: 1 },
  pm10_ugm3: { label: "PM10", unit: "µg/m³", digits: 1 },
  co2_ppm: { label: "CO₂", unit: "ppm", digits: 0 },
  no2_ppb: { label: "NO₂", unit: "ppb", digits: 1 },
  temperature_c: { label: "Temperature", unit: "°C", digits: 1 },
  humidity_pct: { label: "Humidity", unit: "%", digits: 0 },
  wind_speed_ms: { label: "Wind speed", unit: "m/s", digits: 1 },
  precipitation_mm: { label: "Precipitation", unit: { hourly: "mm/h", daily: "mm/day" }, digits: 1 },
};

export function unitOf(measure, resolution = "hourly") {
  const unit = MEASURES[measure]?.unit ?? "";
  return typeof unit === "string" ? unit : unit[resolution];
}

export const labelOf = (measure) => MEASURES[measure]?.label ?? measure;
