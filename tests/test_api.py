import pytest


def get(client, url):
    response = client.get(url)
    return response.status_code, response.get_json()


def test_health_reports_ready(client):
    status, body = get(client, "/api/v1/health")
    assert status == 200 and body["status"] == "ok"
    assert all(body["models"].values())


def test_zones(client):
    _, body = get(client, "/api/v1/zones")
    assert [z["name"] for z in body["zones"]][:2] == ["Downtown", "Industrial"]


def test_overview_structure(client):
    status, body = get(client, "/api/v1/overview")
    assert status == 200
    assert {"energy_kwh", "traffic_count", "pm25_ugm3", "temperature_c", "precipitation_mm"} <= set(body["kpis"])
    assert len(body["zones"]) == 5
    assert body["forecast_accuracy"]["mae"] > 0
    assert get(client, "/api/v1/overview?zone=Harbor")[1]["zone"] == "Harbor"


@pytest.mark.parametrize("slug", ["energy", "traffic", "air-quality", "weather"])
def test_series_for_every_domain(client, slug):
    status, body = get(client, f"/api/v1/series/{slug}?zone=Downtown&limit=24")
    assert status == 200
    assert len(body["records"]) == 24 and body["total"] > 24
    assert all(r["zone"] == "Downtown" for r in body["records"])


def test_daily_series_starts_on_a_whole_day(client):
    _, body = get(client, "/api/v1/series/energy?zone=Residential&resolution=daily")
    first, second = body["records"][0], body["records"][1]
    assert first["energy_kwh"] == pytest.approx(second["energy_kwh"], rel=0.5)
    assert len(first["timestamp"]) == 10


def test_pagination(client):
    _, page1 = get(client, "/api/v1/series/energy?zone=Harbor&limit=10&offset=0")
    _, page2 = get(client, "/api/v1/series/energy?zone=Harbor&limit=10&offset=10")
    assert page1["records"][-1]["timestamp"] < page2["records"][0]["timestamp"]


def test_summary_and_profile(client):
    _, summary = get(client, "/api/v1/series/air-quality/summary?zone=all")
    assert summary["measures"]["pm25_ugm3"]["mean"] > 0
    _, profile = get(client, "/api/v1/series/traffic/profile?zone=Downtown")
    rush = profile["profile"][8]["weekday"]
    night = profile["profile"][3]["weekday"]
    assert rush > 2 * night


@pytest.mark.parametrize(
    "url,code",
    [
        ("/api/v1/series/energy?zone=Mars", "invalid_zone"),
        ("/api/v1/series/energy?resolution=weekly", "invalid_parameter"),
        ("/api/v1/series/energy?limit=0", "invalid_parameter"),
        ("/api/v1/series/energy?start=not-a-date", "invalid_parameter"),
        ("/api/v1/series/energy?start=2026-04-02&end=2026-04-01", "invalid_parameter"),
        ("/api/v1/series/sewage", "unknown_domain"),
        ("/api/v1/predictions?kind=other", "invalid_parameter"),
    ],
)
def test_bad_requests_return_structured_errors(client, url, code):
    status, body = get(client, url)
    assert status in (400, 404)
    assert body["error"]["code"] == code


def test_unknown_route_is_json(client):
    status, body = get(client, "/api/v1/nope")
    assert status == 404 and "error" in body


def test_forecast_returns_interval_and_inputs(client):
    response = client.post("/api/v1/energy/forecast", json={"zone": "Residential", "horizon_hours": 1})
    body = response.get_json()
    assert response.status_code == 200
    assert body["interval"]["lower"] <= body["forecast_kwh"] <= body["interval"]["upper"]
    assert body["inputs"]["latest_observed_kwh"] > 0
    assert body["record_id"] > 0


def test_weather_what_if_reaches_the_model_input(client):
    """The suite trains on 60 days, too little to learn a temperature response, so check the plumbing."""
    r = client.post(
        "/api/v1/energy/forecast",
        json={"zone": "Residential", "horizon_hours": 24, "weather": {"temperature_c": -8, "precipitation_mm": 3}},
    )
    inputs = r.get_json()["inputs"]
    assert inputs["assumed_weather"]["temperature_c"] == -8
    assert inputs["assumed_weather"]["precipitation_mm"] == 3
    assert inputs["weather_overridden"] == ["precipitation_mm", "temperature_c"]


def test_forecast_for_a_historical_origin(client, metrics):
    origin = metrics["dataset"]["holdout_start"][:13].replace(" ", "T") + ":00"
    response = client.post("/api/v1/energy/forecast", json={"zone": "Downtown", "origin": origin})
    assert response.status_code == 200
    assert response.get_json()["origin"].startswith(origin[:13])


@pytest.mark.parametrize(
    "payload,code",
    [
        ({}, "invalid_zone"),
        ({"zone": "Downtown", "horizon_hours": 5}, "invalid_field"),
        ({"zone": "Downtown", "weather": {"temperature_c": 900}}, "invalid_field"),
        ({"zone": "Downtown", "weather": {"humidity_pct": "wet"}}, "invalid_field"),
        ({"zone": "Downtown", "origin": "2020-01-01T00:00"}, "origin_out_of_range"),
        ({"zone": "Downtown", "origin": "yesterday-ish"}, "invalid_parameter"),
    ],
)
def test_forecast_validation(client, payload, code):
    response = client.post("/api/v1/energy/forecast", json=payload)
    assert response.status_code in (400, 422)
    assert response.get_json()["error"]["code"] == code


def test_forecast_rejects_non_json(client):
    response = client.post("/api/v1/energy/forecast", data="zone=Downtown", content_type="text/plain")
    assert response.status_code == 400


NORMAL = {
    "zone": "Downtown",
    "timestamp": "2026-04-14T13:00:00",
    "energy_kwh": 440,
    "voltage_v": 400,
    "current_a": 668,
    "power_factor": 0.95,
}


def test_anomaly_accepts_a_typical_reading(client):
    body = client.post("/api/v1/energy/anomaly", json=NORMAL).get_json()
    assert body["anomaly"] is False and body["reasons"] == []


def test_anomaly_flags_an_outage(client):
    payload = {**NORMAL, "energy_kwh": 20, "current_a": 30}
    body = client.post("/api/v1/energy/anomaly", json=payload).get_json()
    assert body["anomaly"] is True
    assert any("below" in r for r in body["reasons"])


def test_anomaly_flags_a_meter_mismatch(client):
    payload = {**NORMAL, "energy_kwh": 700}  # electrical signals still say ~440 kWh
    body = client.post("/api/v1/energy/anomaly", json=payload).get_json()
    assert body["anomaly"] is True
    assert any("meter" in r.lower() for r in body["reasons"])


def test_anomaly_flags_a_deep_voltage_sag(client):
    payload = {**NORMAL, "voltage_v": 330, "current_a": 668 * 400 / 330}
    body = client.post("/api/v1/energy/anomaly", json=payload).get_json()
    assert body["anomaly"] is True
    assert any("Voltage" in r for r in body["reasons"])


@pytest.mark.parametrize(
    "patch,code",
    [
        ({"energy_kwh": None}, "missing_field"),
        ({"energy_kwh": "x"}, "invalid_field"),
        ({"power_factor": 1.7}, "invalid_field"),
        ({"voltage_v": -5}, "invalid_field"),
        ({"zone": "Mars"}, "invalid_zone"),
        ({"timestamp": None}, "missing_field"),
        ({"timestamp": "garbage"}, "invalid_parameter"),
    ],
)
def test_anomaly_validation(client, patch, code):
    response = client.post("/api/v1/energy/anomaly", json={**NORMAL, **patch})
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == code


def test_anomaly_listing_and_history(client):
    _, flagged = get(client, "/api/v1/energy/anomalies?limit=5&start=2026-01-01")
    assert flagged["total"] > 0
    assert all(r["flagged"] for r in flagged["records"])
    _, everything = get(client, "/api/v1/energy/anomalies?flagged=false&limit=5&start=2026-01-01")
    assert everything["total"] > flagged["total"]

    client.post("/api/v1/energy/anomaly", json=NORMAL)
    _, history = get(client, "/api/v1/predictions?kind=anomaly&limit=3")
    assert history["records"][0]["request"]["zone"] == "Downtown"


def test_model_metrics_and_figures(client, settings):
    status, body = get(client, "/api/v1/models/metrics")
    assert status == 200 and {"forecast", "anomaly", "dataset"} <= set(body)
    assert client.get("/api/v1/models/figures/missing.png").status_code == 404
    assert client.get("/api/v1/models/figures/notes.txt").status_code == 404


def test_missing_models_yield_503(tmp_path, settings):
    from dataclasses import replace

    from smartcity.api import create_app

    bare = replace(settings, model_dir=tmp_path)
    response = create_app(bare).test_client().post("/api/v1/energy/forecast", json={"zone": "Downtown"})
    assert response.status_code == 503
    assert response.get_json()["error"]["code"] == "model_unavailable"


def _guarded(settings, **changes):
    from dataclasses import replace

    from smartcity.api import create_app

    return create_app(replace(settings, **changes)).test_client()


def test_api_key_is_enforced_when_configured(settings):
    client = _guarded(settings, api_key="s3cret")
    assert client.get("/api/v1/health").status_code == 200  # health stays open for probes
    denied = client.get("/api/v1/zones")
    assert denied.status_code == 401 and denied.get_json()["error"]["code"] == "unauthorized"
    assert client.get("/api/v1/zones", headers={"X-API-Key": "wrong"}).status_code == 401
    assert client.get("/api/v1/zones", headers={"X-API-Key": "s3cret"}).status_code == 200


def test_api_is_open_without_a_key(client):
    assert client.get("/api/v1/zones").status_code == 200


def test_post_requests_are_rate_limited(settings):
    client = _guarded(settings, rate_limit_per_minute=2)
    body = {"zone": "Harbor"}
    assert client.post("/api/v1/energy/forecast", json=body).status_code == 200
    assert client.post("/api/v1/energy/forecast", json=body).status_code == 200
    limited = client.post("/api/v1/energy/forecast", json=body)
    assert limited.status_code == 429 and limited.get_json()["error"]["code"] == "rate_limited"
    assert client.get("/api/v1/zones").status_code == 200  # reads are not limited


def test_oversized_bodies_are_rejected(client):
    response = client.post("/api/v1/energy/forecast", data="x" * 70_000, content_type="application/json")
    assert response.status_code == 413
    assert "error" in response.get_json()


def test_security_headers_and_cors_default(client):
    response = client.get("/api/v1/zones", headers={"Origin": "http://localhost:5173"})
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:5173"
    other = client.get("/api/v1/zones", headers={"Origin": "http://evil.example"})
    assert "Access-Control-Allow-Origin" not in other.headers
