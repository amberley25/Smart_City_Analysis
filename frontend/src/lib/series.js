/** Long-form API records -> one row per timestamp with a column per zone. */
export function pivotByZone(records, measure) {
  const rows = new Map();
  for (const r of records) {
    if (!rows.has(r.timestamp)) rows.set(r.timestamp, { t: r.timestamp });
    rows.get(r.timestamp)[r.zone] = r[measure];
  }
  return [...rows.values()];
}

export const zonesIn = (records) => [...new Set(records.map((r) => r.zone))];

export const mean = (values) => {
  const v = values.filter((x) => x != null);
  return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null;
};
