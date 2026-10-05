"""Pruebas de la API con datos sintéticos en memoria (sin red)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.data import compute_metrics
from app.main import app
from app.schemas import CityState, Section


def make_section(sid: str, lon: float, intensity: float, lanes: int = 2) -> Section:
    """Sección sintética."""
    return Section(
        id=sid,
        name=f"calle-{sid}",
        display_name=f"calle-{sid}",
        intensity=intensity,
        velocity_kmh=25.0,
        lanes=lanes,
        length_m=400.0,
        geometry=[[lon, 43.268], [lon + 0.002, 43.268]],
        centroid=(lon, 43.268),
    )


@pytest.fixture
def synthetic_city(monkeypatch) -> CityState:
    """Sustituye el estado real por uno sintético y determinista."""
    cfg = Settings()
    sections = [
        make_section("s1", -2.9400, 1500.0, lanes=4),
        make_section("s2", -2.9430, 600.0),
        make_section("s3", -2.9370, 400.0),
        make_section("s4", -2.9340, 300.0),
        make_section("s5", -2.9310, 250.0),
    ]
    state = CityState(
        zone=cfg.zone_name,
        bbox=[cfg.bbox_south, cfg.bbox_west, cfg.bbox_north, cfg.bbox_east],
        sections=sections,
        metrics=[compute_metrics(s, cfg) for s in sections],
        coverage={"sections_in_zone": 5, "fresh_sections": 5},
    )
    monkeypatch.setattr("app.main.get_city", lambda cfg: state)
    return state


@pytest.fixture
def client() -> TestClient:
    """Cliente HTTP de prueba."""
    with TestClient(app) as c:
        yield c


def test_health_reports_cache(client) -> None:
    body = client.get("/health").json()

    assert body["status"] == "ok"
    assert "trafico" in body["cache"]


def test_city_returns_provenance(client, synthetic_city) -> None:
    body = client.get("/city").json()

    assert len(body["sections"]) == 5
    assert body["sections"][0]["provenance"] == "real"
    assert body["metrics"][0]["provenance"] == "derived"


def test_traffic_marks_freshness(client, synthetic_city) -> None:
    body = client.get("/traffic").json()

    assert body["source"] == "real"
    assert "is_fresh" in body["sections"][0]


def test_scenario_validation_returns_target(client, synthetic_city) -> None:
    resp = client.post("/scenario", json={"street_id": "s1", "action": "close"})

    assert resp.status_code == 200
    assert resp.json()["target"]["vehicles_per_hour"] == 1500.0


def test_scenario_accepts_name_fragment(client, synthetic_city) -> None:
    resp = client.post("/scenario", json={"street_id": "calle-s1", "action": "close"})

    assert resp.status_code == 200
    assert resp.json()["scenario"]["street_id"] == "s1"


def test_unknown_street_returns_404_with_hint(client, synthetic_city) -> None:
    resp = client.post("/scenario", json={"street_id": "no-existe", "action": "close"})

    assert resp.status_code == 404
    assert "Ejemplos" in resp.json()["detail"]


def test_simulate_returns_all_six_kpis(client, synthetic_city) -> None:
    body = client.post(
        "/simulate", json={"street_id": "s1", "action": "close"}
    ).json()

    kpis = body["kpis"]
    for key in (
        "traffic_change",
        "emissions_change",
        "travel_time_change",
        "pedestrian_change",
        "commercial_activity_change",
        "accessibility_change",
    ):
        assert key in kpis
    assert body["provenance"] == "simulated"


def test_evaluate_returns_simulation_and_jev(client, synthetic_city) -> None:
    body = client.post(
        "/evaluate", json={"street_id": "s1", "action": "close"}
    ).json()

    assert body["jev"]["overall_status"]
    assert body["simulation"]["kpis"]["traffic_change"] is not None
    assert body["jev"]["thresholds_applied"]["section_traffic_high_pct"] == 25.0


def test_evaluate_verdict_endpoint(client, synthetic_city) -> None:
    verdict = client.post(
        "/evaluate/verdict", json={"street_id": "s1", "action": "close"}
    ).json()

    assert verdict["traffic_risk"] in {"LOW", "ACCEPTABLE", "HIGH"}
    assert 0.0 <= verdict["confidence"] <= 1.0


def test_invalid_action_is_rejected(client, synthetic_city) -> None:
    resp = client.post("/simulate", json={"street_id": "s1", "action": "bike_lane"})

    assert resp.status_code == 422


def test_openapi_documents_mvp_routes(client) -> None:
    paths = client.get("/openapi.json").json()["paths"]

    for route in ("/city", "/traffic", "/scenario", "/simulate", "/evaluate"):
        assert route in paths
