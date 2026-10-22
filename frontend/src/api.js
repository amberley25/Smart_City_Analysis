const BASE = `${import.meta.env.VITE_API_BASE ?? ""}/api/v1`;

export class ApiError extends Error {
  constructor(message, { status = 0, code = "network_error" } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

async function request(path, { params, method = "GET", body, signal } = {}) {
  const url = new URL(BASE + path, window.location.origin);
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value !== undefined && value !== null && value !== "") url.searchParams.set(key, value);
  }

  let response;
  try {
    response = await fetch(url, {
      method,
      signal,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new ApiError("The API is not reachable.", { code: "network_error" });
  }

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = payload?.error;
    throw new ApiError(detail?.message ?? `Request failed (${response.status})`, {
      status: response.status,
      code: detail?.code ?? "http_error",
    });
  }
  return payload;
}

export const api = {
  health: (signal) => request("/health", { signal }),
  overview: (zone, signal) => request("/overview", { params: { zone }, signal }),
  series: (slug, params, signal) => request(`/series/${slug}`, { params, signal }),
  seriesSummary: (slug, params, signal) => request(`/series/${slug}/summary`, { params, signal }),
  seriesProfile: (slug, params, signal) => request(`/series/${slug}/profile`, { params, signal }),
  forecast: (body, signal) => request("/energy/forecast", { method: "POST", body, signal }),
  checkAnomaly: (body, signal) => request("/energy/anomaly", { method: "POST", body, signal }),
  anomalies: (params, signal) => request("/energy/anomalies", { params, signal }),
  predictions: (params, signal) => request("/predictions", { params, signal }),
  metrics: (signal) => request("/models/metrics", { signal }),
  figureUrl: (name) => `${BASE}/models/figures/${name}`,
};
