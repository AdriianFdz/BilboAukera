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


def test_every_flow_screen_is_served(client) -> None:
    """Cada etapa del flujo debe devolver su HTML, no un 404."""
    for path, marker in (
        ("/", "Peatonalizar"),
        ("/datos", "Cobertura del feed"),
        ("/escenario", "Definir la intervención"),
        ("/simulacion", "Secciones afectadas"),
        ("/jev", "Veredicto global"),
    ):
        resp = client.get(path)
        assert resp.status_code == 200, path
        assert "text/html" in resp.headers["content-type"], path
        assert marker in resp.text, f"{path} no parece la pantalla correcta"


def test_static_assets_are_served(client) -> None:
    """Los módulos compartidos y el CSS deben servirse sin paso de compilación."""
    for path, fragment in (
        ("/static/base.css", "--rojo"),
        ("/static/ui.js", "renderChrome"),
        ("/static/map.js", "renderMap"),
    ):
        resp = client.get(path)
        assert resp.status_code == 200, path
        assert fragment in resp.text, path


def test_favicon_is_served(client) -> None:
    """El navegador pide favicon en cada carga: no debe devolver 404."""
    for path, media_type in (("/favicon.ico", "image/x-icon"),):
        resp = client.get(path)
        assert resp.status_code == 200, path
        assert media_type in resp.headers["content-type"]


def test_streets_exposes_full_registry_marking_what_is_simulable(client) -> None:
    """El registro trae todas las calles, marcando las que no se pueden simular."""
    body = client.get("/streets?limit=1000").json()

    assert body["total"] > 500, "debería traer el registro completo de Bilbao"
    assert body["with_traffic_data"] < body["total"], "no todas tienen tráfico medido"
    assert any(not s["simulable"] for s in body["streets"])
    assert body["method"], "debe declarar cómo se cruzaron los nombres"


def test_streets_filter_puts_traffic_data_first(client) -> None:
    """Al buscar, lo simulable va primero."""
    body = client.get("/streets?q=heros").json()

    assert body["returned"] >= 1
    assert body["streets"][0]["simulable"] is True


def test_streets_endpoint_is_absent_without_registry(client, synthetic_city, monkeypatch) -> None:
    """Sin el CSV, /streets responde vacío en vez de romperse."""
    monkeypatch.setattr("app.main.load_street_registry", lambda cfg: [])
    monkeypatch.setattr("app.main._street_cache", None)

    body = client.get("/streets").json()

    assert body["total"] == 0
    assert body["streets"] == []


def test_cameras_expose_the_live_reading_of_their_section(
    client, synthetic_city, monkeypatch
) -> None:
    """Sin instantáneas, la cámara se sustituye por la lectura real medida."""
    monkeypatch.setattr(
        "app.main.load_cameras",
        lambda cfg: {
            "source": "x",
            "total_in_city": 119,
            "in_zone": 1,
            "usable_for_simulation": False,
            "limitation": "sin cifras",
            "cameras": [{"id": "1", "name": "Plaza", "centroid": [-2.9400, 43.268]}],
        },
    )

    body = client.get("/cameras").json()

    assert body["snapshots_available"] is False
    assert "404" in body["snapshot_note"]
    live = body["cameras"][0]["live"]
    assert live["vehicles_per_hour"] == 1500.0
    assert live["provenance"] == "REAL"


def test_cameras_are_context_only_and_flag_their_limit(client, synthetic_city, monkeypatch) -> None:
    """Las cámaras no miden tráfico: se expone como capa de contexto.

    Verificado contra el feed real: no trae cifras y sus instantáneas dan 404.
    """
    monkeypatch.setattr(
        "app.main.load_cameras",
        lambda cfg: {
            "source": "bilbao.eus srvDatasetCamaras",
            "total_in_city": 119,
            "in_zone": 1,
            "usable_for_simulation": False,
            "limitation": "El feed no contiene cifras de tráfico",
            "cameras": [
                {
                    "id": "4081",
                    "name": "Plza. Museo",
                    "centroid": [-2.9400, 43.268],
                }
            ],
        },
    )

    body = client.get("/cameras").json()

    assert body["usable_for_simulation"] is False
    assert body["in_zone"] == 1
    # La cámara está sobre el centroide de s1, luego se le asocia.
    assert body["cameras"][0]["nearest_section"] == "calle-s1"
    assert body["sections_observed_count"] >= 1


def test_health_reports_cache(client) -> None:
    body = client.get("/health").json()

    assert body["status"] == "ok"
    assert "trafico" in body["cache"]


def test_city_returns_provenance(client, synthetic_city) -> None:
    body = client.get("/city").json()

    assert len(body["sections"]) == 5
    assert body["sections"][0]["provenance"] == "REAL"
    assert body["metrics"][0]["provenance"] == "DERIVADO"


def test_traffic_marks_freshness(client, synthetic_city) -> None:
    body = client.get("/traffic").json()

    assert body["source"] == "REAL"
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
    assert body["provenance"] == "SIMULADO"


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

    assert verdict["traffic_risk"] in {"BAJO", "ACEPTABLE", "ALTO"}
    assert 0.0 <= verdict["confidence"] <= 1.0


def test_invalid_action_is_rejected(client, synthetic_city) -> None:
    resp = client.post("/simulate", json={"street_id": "s1", "action": "bike_lane"})

    assert resp.status_code == 422


def test_openapi_documents_mvp_routes(client) -> None:
    paths = client.get("/openapi.json").json()["paths"]

    for route in ("/city", "/traffic", "/scenario", "/simulate", "/evaluate"):
        assert route in paths
