import { describe, expect, it, vi } from "vitest";
import { api, ApiError } from "./api.js";

const respond = (payload, status = 200) => ({ ok: status < 400, status, json: async () => payload });

describe("api client", () => {
  it("builds query strings and drops empty parameters", async () => {
    const fetch = vi.fn().mockResolvedValue(respond({ records: [] }));
    vi.stubGlobal("fetch", fetch);

    await api.series("energy", { zone: "Harbor", resolution: "daily", start: "", end: undefined, limit: 0 });

    const url = fetch.mock.calls[0][0];
    expect(url.pathname).toBe("/api/v1/series/energy");
    expect(url.searchParams.get("zone")).toBe("Harbor");
    expect(url.searchParams.get("limit")).toBe("0");
    expect(url.searchParams.has("start")).toBe(false);
    expect(url.searchParams.has("end")).toBe(false);
  });

  it("sends JSON bodies with a content type on POST", async () => {
    const fetch = vi.fn().mockResolvedValue(respond({ forecast_kwh: 1 }));
    vi.stubGlobal("fetch", fetch);

    await api.forecast({ zone: "Harbor", horizon_hours: 24 });

    const [, init] = fetch.mock.calls[0];
    expect(init.method).toBe("POST");
    expect(init.headers).toEqual({ "Content-Type": "application/json" });
    expect(JSON.parse(init.body)).toEqual({ zone: "Harbor", horizon_hours: 24 });
  });

  it("turns a structured API error into an ApiError with its code", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(respond({ error: { code: "invalid_zone", message: "zone must be one of" } }, 400)),
    );

    const failure = await api.forecast({}).catch((error) => error);

    expect(failure).toBeInstanceOf(ApiError);
    expect(failure).toMatchObject({ status: 400, code: "invalid_zone", message: "zone must be one of" });
  });

  it("copes with an error response that is not JSON", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 502, json: async () => Promise.reject(new Error("x")) }));

    const failure = await api.health().catch((error) => error);

    expect(failure).toMatchObject({ status: 502, code: "http_error", message: "Request failed (502)" });
  });

  it("reports an unreachable API as a network error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    const failure = await api.health().catch((error) => error);

    expect(failure).toMatchObject({ code: "network_error", status: 0 });
  });

  it("lets aborts through untouched so callers can ignore them", async () => {
    const abort = Object.assign(new Error("aborted"), { name: "AbortError" });
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(abort));

    await expect(api.health()).rejects.toBe(abort);
  });

  it("points figure links at the API", () => {
    expect(api.figureUrl("forecast_backtest.png")).toBe("/api/v1/models/figures/forecast_backtest.png");
  });
});
