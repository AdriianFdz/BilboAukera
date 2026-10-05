"""Pruebas de la clasificación de Jev."""

from __future__ import annotations

from app.jev import Thresholds, evaluate
from app.schemas import Action, KPIs, Scenario, SectionImpact, SimulationResult


def make_result(
    *,
    traffic: float = 0.0,
    emissions: float = -8.0,
    travel: float = 5.0,
    commercial: float = -2.0,
    accessibility: float = -4.0,
    max_section: float = 5.0,
    displaced: float = 0.0,
) -> SimulationResult:
    """Resultado simulado con los KPIs indicados."""
    return SimulationResult(
        scenario=Scenario(street_id="s1", action=Action.CLOSE),
        kpis=KPIs(
            traffic_change=traffic,
            emissions_change=emissions,
            travel_time_change=travel,
            pedestrian_change=25.0,
            commercial_activity_change=commercial,
            accessibility_change=accessibility,
            baseline={"zone_vehicles_per_hour": 10000.0},
            simulated={"zone_vehicles_per_hour": 10000.0},
        ),
        impacts=[
            SectionImpact(
                section_id="s1",
                baseline_vehicles_per_hour=1000.0,
                simulated_vehicles_per_hour=0.0,
                change_pct=-100.0,
            )
        ],
        displaced_outside_zone=displaced,
        max_section_increase_pct=max_section,
    )


def test_clean_scenario_is_favorable() -> None:
    verdict = evaluate(make_result(), sections_count=20, fresh_ratio=1.0)

    assert verdict.overall_status.value == "FAVORABLE"
    assert verdict.environmental_impact.value == "POSITIVO"


def test_section_overload_triggers_high_traffic_risk() -> None:
    verdict = evaluate(make_result(max_section=51.6), sections_count=20, fresh_ratio=1.0)

    assert verdict.traffic_risk.value == "ALTO"
    assert any("secci" in a for a in verdict.alerts)


def test_zone_traffic_increase_triggers_high_risk() -> None:
    verdict = evaluate(make_result(traffic=18.0, max_section=2.0), sections_count=20)

    assert verdict.traffic_risk.value == "ALTO"


def test_slow_travel_time_upgrades_traffic_risk() -> None:
    verdict = evaluate(make_result(travel=35.0, max_section=1.0), sections_count=20)

    assert verdict.traffic_risk.value == "ALTO"
    assert any("desplazamiento" in a for a in verdict.alerts)


def test_commercial_drop_is_flagged() -> None:
    verdict = evaluate(make_result(commercial=-15.0), sections_count=20)

    assert verdict.commercial_impact.value == "NEGATIVO"


def test_accessibility_drop_is_flagged() -> None:
    verdict = evaluate(make_result(accessibility=-12.0), sections_count=20)

    assert verdict.accessibility_impact.value == "NEGATIVO"


def test_two_negatives_require_review() -> None:
    verdict = evaluate(
        make_result(max_section=51.6, accessibility=-15.0), sections_count=20
    )

    assert verdict.overall_status.value == "REQUIERE REVISIÓN"


def test_confidence_drops_when_traffic_leaves_zone() -> None:
    high = evaluate(make_result(), sections_count=20, fresh_ratio=1.0)
    leaked = evaluate(make_result(displaced=6000.0), sections_count=20, fresh_ratio=1.0)

    assert leaked.confidence < high.confidence


def test_confidence_drops_with_few_sections_and_stale_data() -> None:
    strong = evaluate(make_result(), sections_count=30, fresh_ratio=1.0)
    weak = evaluate(make_result(), sections_count=2, fresh_ratio=0.1)

    assert weak.confidence < strong.confidence


def test_thresholds_are_configurable() -> None:
    lenient = Thresholds(traffic_high_pct=80.0, section_traffic_high_pct=90.0)
    strict = evaluate(make_result(traffic=20.0, max_section=5.0), thresholds=lenient)

    assert strict.traffic_risk.value != "ALTO"


def test_verdict_has_no_free_text_field() -> None:
    """Jev devuelve estructura, no texto libre."""
    verdict = evaluate(make_result(displaced=5000.0), sections_count=20)

    assert set(verdict.model_dump()) >= {
        "traffic_risk",
        "environmental_impact",
        "commercial_impact",
        "accessibility_impact",
        "overall_status",
        "confidence",
    }
    assert verdict.disclaimer
