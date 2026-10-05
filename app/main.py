"""API del MVP: datos → escenario → simulación → Jev → resultado.

Ocho rutas, sin base de datos, sin estado. Los datos se cachean en disco.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException

from app import engine
from app.config import Settings, settings
from app.data import cache_status, load_city_state
from app.jev import Thresholds, evaluate
from app.schemas import (
    CityState,
    HealthResponse,
    JevVerdict,
    Scenario,
    Section,
    SimulationResult,
)

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description=(
        "MVP del laboratorio urbano digital. Caso de uso: **peatonalizar calles**.\n\n"
        "Ejemplo de demostración: Gran Vía de Don Diego López de Haro (Abando, "
        "Bilbao).\n\n"
        "Los resultados son estimaciones de un modelo de reglas sobre datos "
        "reales parciales. No son predicciones exactas ni recomendaciones de "
        "política urbana."
    ),
)


_city_cache: CityState | None = None


def get_city(cfg: Settings) -> CityState:
    """Estado actual de la zona, cacheado en memoria por proceso.

    No se usa `lru_cache` porque `Settings` de pydantic no es hashable.
    """
    global _city_cache
    if _city_cache is None:
        _city_cache = load_city_state(cfg)
    return _city_cache


def _metrics_by_id(state: CityState, cfg: Settings) -> dict[str, Any]:
    """Indexa las métricas por id de sección."""
    return {m.section_id: m for m in state.metrics}


def _resolve(state: CityState, street_id: str) -> Section:
    """Resuelve la sección por id o por nombre, con error claro."""
    found = engine.find_section(state.sections, street_id)
    if found is None:
        available = [s.name for s in state.sections if s.name][:5]
        raise HTTPException(
            status_code=404,
            detail=(
                f"No se encontró la sección '{street_id}'. "
                f"Usa un CodigoSeccion del feed de Bilbao o parte del nombre. "
                f"Ejemplos disponibles: {available}"
            ),
        )
    return found


def _run(scenario: Scenario, cfg: Settings) -> tuple[CityState, SimulationResult]:
    """Ejecuta el escenario sobre el estado actual."""
    state = get_city(cfg)
    section = _resolve(state, scenario.street_id)
    if section.id != scenario.street_id:
        scenario = scenario.model_copy(update={"street_id": section.id})

    metrics = _metrics_by_id(state, cfg)
    if not metrics:
        raise HTTPException(status_code=503, detail="Sin métricas de tráfico disponibles.")

    try:
        result = engine.simulate(scenario, state.sections, metrics, cfg)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Sección no encontrada: {exc}") from exc
    return state, result


@app.get("/health", response_model=HealthResponse, tags=["sistema"])
def health() -> HealthResponse:
    """Estado del servicio y de la caché de datos."""
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=settings.version,
        cache=cache_status(settings),
    )


@app.get("/city", response_model=CityState, tags=["datos"])
def city() -> CityState:
    """Estado actual de la zona de estudio.

    Mezcla dato real observado (`sections`) y magnitudes derivadas
    (`metrics`). Cada campo lleva su `provenance`.
    """
    return get_city(settings)


@app.get("/traffic", tags=["datos"])
def traffic() -> dict[str, Any]:
    """Tráfico por sección con frescura y cobertura del dato.

    Incluye solo lo observado, sin estimaciones.
    """
    state = get_city(settings)
    return {
        "zone": state.zone,
        "source": state.provenance.value,
        "coverage": state.coverage,
        "sections": [
            {
                "id": s.id,
                "name": s.name,
                "name_source": s.name_source,
                "vehicles_per_hour": s.intensity,
                "velocity_kmh": s.velocity_kmh,
                "occupancy": s.occupancy,
                "observed_at": s.observed_at,
                "is_fresh": s.is_fresh,
                "centroid": list(s.centroid),
                "geometry": s.geometry,
                "provenance": s.provenance.value,
            }
            for s in state.sections
        ],
    }


@app.post("/scenario", tags=["escenario"])
def validate_scenario(scenario: Scenario) -> dict[str, Any]:
    """Valida y normaliza un escenario sin ejecutarlo.

    Devuelve la acción resuelta, sus efectos configurados y la sección
    objetivo, para que el frontend muestre el escenario antes de simular.
    """
    state = get_city(settings)
    section = _resolve(state, scenario.street_id)
    effects = engine.action_effects(settings)[scenario.action]

    return {
        "scenario": scenario.model_copy(update={"street_id": section.id}),
        "target": {
            "id": section.id,
            "name": section.name,
            "display_name": section.display_name,
            "vehicles_per_hour": section.intensity,
            "lanes": section.lanes,
            "length_m": section.length_m,
            "observed_at": section.observed_at,
            "is_fresh": section.is_fresh,
        },
        "configured_effects": effects,
        "neighbours": engine.neighbour_ids_of(
            section, {s.id: s for s in state.sections}, [s.id for s in state.sections], settings
        ),
    }


@app.post("/simulate", response_model=SimulationResult, tags=["simulación"])
def simulate(scenario: Scenario) -> SimulationResult:
    """Aplica las reglas de simulación y devuelve los KPIs."""
    _, result = _run(scenario, settings)
    logger.info(
        "Escenario %s sobre %s → tráfico %+.1f%%, emisiones %+.1f%%",
        scenario.action,
        scenario.street_id,
        result.kpis.traffic_change,
        result.kpis.emissions_change,
    )
    return result


@app.post("/evaluate", tags=["jev"])
def evaluate_scenario(scenario: Scenario) -> dict[str, Any]:
    """Pipeline completo: simula y clasifica con Jev.

    Atajo para el frontend: no necesita dos llamadas ni estado en servidor.
    """
    state, result = _run(scenario, settings)
    coverage = state.coverage or {}
    total = max(1, coverage.get("sections_in_zone", 1))
    fresh_ratio = coverage.get("fresh_sections", total) / total

    verdict = evaluate(
        result,
        thresholds=Thresholds.from_settings(settings),
        sections_count=len(state.sections),
        fresh_ratio=fresh_ratio,
    )
    return {
        "scenario": result.scenario,
        "simulation": result,
        "jev": verdict.model_dump(),
    }


@app.post("/evaluate/verdict", response_model=JevVerdict, tags=["jev"])
def verdict_only(scenario: Scenario) -> JevVerdict:
    """Solo el veredicto de Jev, sin repetir la simulación en el frontend."""
    state, result = _run(scenario, settings)
    coverage = state.coverage or {}
    total = max(1, coverage.get("sections_in_zone", 1))
    return evaluate(
        result,
        thresholds=Thresholds.from_settings(settings),
        sections_count=len(state.sections),
        fresh_ratio=coverage.get("fresh_sections", total) / total,
    )


@app.get("/demo", tags=["sistema"])
def demo() -> dict[str, Any]:
    """Ejecuta los dos escenarios de demostración sobre Bilbao."""
    state = get_city(settings)
    gran_via = next(
        (s for s in state.sections if s.name and "Diego" in s.name),
        next((s for s in state.sections if s.name), None),
    )
    if gran_via is None:
        raise HTTPException(status_code=503, detail="Sin secciones con nombre OSM en la zona.")

    scenarios = [
        Scenario(street_id=gran_via.id, action="close"),
        Scenario(
            street_id=gran_via.id,
            action="traffic_restriction",
            params={"allowed_ratio": 0.6},
        ),
    ]
    coverage = state.coverage or {}
    total = max(1, coverage.get("sections_in_zone", 1))
    fresh_ratio = coverage.get("fresh_sections", total) / total
    metrics = _metrics_by_id(state, settings)

    results = []
    for sc in scenarios:
        sim = engine.simulate(sc, state.sections, metrics, settings)
        results.append(
            {
                "scenario": sc.model_dump(mode="json"),
                "kpis": sim.kpis.model_dump(),
                "jev": evaluate(
                    sim,
                    thresholds=Thresholds.from_settings(settings),
                    sections_count=len(state.sections),
                    fresh_ratio=fresh_ratio,
                ).model_dump(),
            }
        )

    return {
        "city": "Bilbao",
        "zone": state.zone,
        "street": {
            "id": gran_via.id,
            "name": gran_via.name,
            "display_name": gran_via.display_name,
        },
        "coverage": coverage,
        "scenarios": results,
    }
