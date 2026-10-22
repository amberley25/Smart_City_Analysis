export const AXIS = {
  stroke: "var(--border-strong)",
  tick: { fill: "var(--muted)", fontSize: 11 },
  tickLine: false,
};

/** Round an axis maximum up to 1, 2 or 5 times a power of ten so ticks land on tidy values. */
export function niceMax(value) {
  if (!Number.isFinite(value) || value <= 0) return 1;
  const magnitude = 10 ** Math.floor(Math.log10(value));
  const step = [1, 2, 2.5, 5, 10].find((m) => value <= m * magnitude);
  return step * magnitude;
}

export const ZERO_TO_NICE = [0, niceMax];
