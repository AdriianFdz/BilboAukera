"""Pruebas del motor de reglas con datos sintéticos (sin red)."""

from __future__ import annotations

import pytest

from app.config import Settings
from app.data import compute_metrics
from app.engine import find_section, neighbour_ids_of, simulate
from app.schemas import Action, Scenario, Section


@pytest.fixture
def cfg() -> Settings:
    """Configuración de pruebas."""
    return Settings()


def make_section(
    sid: str,
    lon: float,
    intensity: float,
    *,
    lanes: int = 2,
    length_m: float = 400.0,
    name: str | None = None,
) -> Section:
    """Sección sintética mínima."""
    return Section(
        id=sid,
        name=name or f"calle-{sid}",
        display_name=name or f"calle-{sid}",
        intensity=intensity,
        velocity_kmh=25.0,
        lanes=lanes,
        length_m=length_m,
        geometry=[[lon, 43.268], [lon + 0.002, 43.268]],
        centroid=(lon, 43.268),
    )


@pytest.fixture
def city(cfg: Settings) -> list[Section]:
    """Zona con una calle principal y cuatro vecinas."""
    return [
        make_section("target", -2.9400, 1500.0, lanes=4, length_m=900.0, name="Gran Via"),
        make_section("n1", -2.9430, 600.0, lanes=2, length_m=350.0),
        make_section("n2", -2.9370, 400.0, lanes=2, length_m=350.0),
        make_section("n3", -2.9400, 500.0, lanes=2, length_m=350.0),
        make_section("n4", -2.9340, 300.0, lanes=2, length_m=350.0),
    ]


def metrics_for(sections: list[Section], cfg: Settings) -> dict:
    """Métricas derivadas por sección."""
    return {s.id: compute_metrics(s, cfg) for s in sections}


def run(city: list[Section], cfg: Settings, action: Action = Action.CLOSE, **params):
    """Ejecuta la simulación de cierre sobre la calle `target`."""
    metrics = metrics_for(city, cfg)
    scenario = Scenario(street_id="target", action=action, params=params)
    return simulate(scenario, city, metrics, cfg)


def test_close_zeroes_target_traffic(city, cfg) -> None:
    result = run(city, cfg)

    target = next(i for i in result.impacts if i.section_id == "target")
    assert target.simulated_vehicles_per_hour == 0.0
    assert target.change_pct == -100.0


def test_displaced_traffic_lands_in_neighbours(city, cfg) -> None:
    result = run(city, cfg)

    gained = sum(
        i.simulated_vehicles_per_hour - i.baseline_vehicles_per_hour
        for i in result.impacts
        if i.section_id != "target"
    )
    assert gained == pytest.approx(1500.0, rel=1e-6)


def test_unabsorbed_traffic_is_reported_not_discarded(cfg) -> None:
    """Si no hay capacidad libre, la fuga se declara explícitamente."""
    sections = [
        make_section("target", -2.9400, 3000.0),
        make_section("full1", -2.9430, 3600.0, lanes=2),
        make_section("full2", -2.9370, 3600.0, lanes=2),
    ]
    result = run(sections, cfg)

    assert result.displaced_outside_zone > 0
    assert any("fuera del alcance" in n for n in result.notes)


def test_restriction_keeps_configured_share(city, cfg) -> None:
    scenario = Scenario(
        street_id="target",
        action=Action.TRAFFIC_RESTRICTION,
        params={"allowed_ratio": 0.6},
    )
    result = simulate(scenario, city, metrics_for(city, cfg), cfg)

    target = next(i for i in result.impacts if i.section_id == "target")
    assert target.simulated_vehicles_per_hour == pytest.approx(900.0)


def test_max_section_increase_exceeds_zone_change(city, cfg) -> None:
    """El riesgo es local: el agregado de zona no lo refleja."""
    result = run(city, cfg)

    assert result.kpis.traffic_change == pytest.approx(0.0, abs=0.5)
    assert result.max_section_increase_pct > 20.0


def test_redistribution_inside_zone_does_not_cut_emissions(city, cfg) -> None:
    """Repartir tráfico dentro de la zona no puede reducir emisiones.

    El reparto por capacidad libre puede trasladar vehículos a calles más
    cortas, lo que bajaría `vehículos x longitud` sin que nadie recorra
    menos. Ese ahorro es un artefacto, no un efecto real.
    """
    result = run(city, cfg)

    assert result.displaced_outside_zone == 0.0
    assert result.kpis.emissions_change == pytest.approx(0.0, abs=0.01)
    assert any("desvío neutro" in n for n in result.notes)


def test_emissions_only_drop_when_traffic_leaves_zone(cfg) -> None:
    """Si el tráfico sale de la zona, ese tráfico sí deja de emitir."""
    sections = [
        make_section("target", -2.9400, 3000.0),
        make_section("full1", -2.9430, 3600.0, lanes=2),
        make_section("full2", -2.9370, 3600.0, lanes=2),
    ]
    result = run(sections, cfg)

    assert result.displaced_outside_zone > 0
    assert result.kpis.emissions_change < 0.0


def test_pedestrianization_raises_pedestrians(city, cfg) -> None:
    result = run(city, cfg)

    assert result.kpis.pedestrian_change == 25.0


def test_find_section_by_partial_name(city) -> None:
    assert find_section(city, "Gran Via") is not None
    assert find_section(city, "inexistente") is None


def test_find_section_matches_spanish_alias(city) -> None:
    """El alias en castellano debe encontrar la calle aunque OSM la dé en euskera."""
    city[0].display_name = "Gran Vía de Don Diego López de Haro"

    assert find_section(city, "gran vía") is not None
    assert find_section(city, "Diego") is not None


def test_neighbours_respect_radius(city, cfg) -> None:
    by_id = {s.id: s for s in city}
    found = neighbour_ids_of(by_id["target"], by_id, [s.id for s in city], cfg)

    assert "target" not in found
    assert len(found) <= cfg.neighbour_count


def test_scenario_rejects_inverted_time_window() -> None:
    with pytest.raises(ValueError):
        Scenario(street_id="x", action=Action.CLOSE, start="20:00", end="10:00")
