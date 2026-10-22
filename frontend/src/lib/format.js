const cache = new Map();

function formatter(digits) {
  if (!cache.has(digits)) {
    cache.set(digits, new Intl.NumberFormat("en-GB", { minimumFractionDigits: digits, maximumFractionDigits: digits }));
  }
  return cache.get(digits);
}

const isMissing = (v) => v == null || Number.isNaN(v);

export const num = (v, digits = 1) => (isMissing(v) ? "—" : formatter(digits).format(v));

export const percent = (v, digits = 1) => (isMissing(v) ? "—" : `${formatter(digits).format(v)}%`);

export function signedPercent(v, digits = 1) {
  if (isMissing(v)) return "—";
  const sign = v > 0 ? "+" : v < 0 ? "−" : "";
  return `${sign}${formatter(digits).format(Math.abs(v))}%`;
}

// The API returns naive ISO timestamps. They are treated as UTC and rendered as UTC so the
// text never depends on the viewer's time zone.
export function parseTime(value) {
  if (value instanceof Date) return value;
  const text = String(value);
  if (text.length <= 10) return new Date(`${text}T00:00:00Z`);
  return new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(text) ? text : `${text}Z`);
}

const fmt = (options) => new Intl.DateTimeFormat("en-GB", { timeZone: "UTC", ...options });
const dayFmt = fmt({ day: "numeric", month: "short" });
const dayYearFmt = fmt({ day: "numeric", month: "short", year: "numeric" });
const timeFmt = fmt({ hour: "2-digit", minute: "2-digit", hour12: false });
const weekdayFmt = fmt({ weekday: "short" });

export const shortDate = (v) => dayFmt.format(parseTime(v));
export const longDate = (v) => dayYearFmt.format(parseTime(v));
export const dateTime = (v) => `${dayYearFmt.format(parseTime(v))}, ${timeFmt.format(parseTime(v))}`;
export const hourTick = (v) => `${dayFmt.format(parseTime(v))} ${timeFmt.format(parseTime(v))}`;
export const fullStamp = (v) => `${weekdayFmt.format(parseTime(v))} ${dateTime(v)}`;

// "YYYY-MM-DDTHH:mm" as expected by <input type="datetime-local">
export const toInputValue = (v) => parseTime(v).toISOString().slice(0, 16);
