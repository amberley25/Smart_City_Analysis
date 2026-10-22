import SeriesExplorer from "../components/SeriesExplorer.jsx";

const AIR = ["pm25_ugm3", "pm10_ugm3", "co2_ppm", "no2_ppb"];
const WEATHER = ["temperature_c", "humidity_pct", "wind_speed_ms", "precipitation_mm"];

// WHO 2021 air quality guideline for PM2.5, 24-hour mean.
const AIR_REFERENCE = { pm25_ugm3: [{ y: 15, label: "WHO 24-h guideline, 15 µg/m³" }] };

export default function Environment() {
  return (
    <>
      <SeriesExplorer slug="air-quality" title="Air quality" measures={AIR} refLines={AIR_REFERENCE} />
      <SeriesExplorer slug="weather" title="Weather" measures={WEATHER} />
    </>
  );
}
