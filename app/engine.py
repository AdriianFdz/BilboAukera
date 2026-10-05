"""Simulación por reglas para el caso de uso acotado del MVP.

Caso de uso: **peatonalizar calles** y estimar el efecto sobre la zona.

El motor no está atado a ninguna calle en concreto: aplica el mismo conjunto
de reglas a cualquier sección de la zona. Como ejemplo de demostración se usa
Bilbao, con la Gran Vía de Don Diego López de Haro (Abando) como caso
principal y el Casco Viejo como alternativa.

Cinco reglas, sin machine learning:

1. `close` deja la sección intervenida sin tráfico (peatonalización);
   `traffic_restriction` la reduce según el ratio configurado.
2. El tráfico desplazado se reparte entre las secciones vecinas más próximas
   en proporción a su **capacidad libre**.
3. El tráfico que no cabe en la zona se contabiliza como
   `displaced_outside_zone`: se reporta, nunca se descarta en silencio.
4. Las emisiones derivan del tráfico simulado y la longitud del tramo.
5. Peatones, comercio y accesibilidad se ajustan con porcentajes
   configurables, marcados como potencial y no como mediciones.

Limitación conocida: las secciones se unen por proximidad, no por
conectividad real de cruces. La redistribución aproxima, no asigna viajes.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings
from app.schemas import (
    Action,
    KPIs,
    Scenario,
    Section,
    SectionImpact,
    SectionMetrics,
    SimulationResult,
    pct_change,
)

#: Peso de acceso peatonal frente a acceso en vehículo en el índice de
#: accesibilidad. Se muestra siempre desglosado, nunca como número único.
ACCESSIBILITY_WEIGHTS = {"pedestrian": 0.4, "vehicle": 0.6}

#: Efecto por defecto de cada acción sobre los indicadores no medidos.
#: Los valores reales salen de la configuración; esto solo documenta el
#: comportamiento esperado.
DEFAULT_ACTION_EFFECTS: dict[Action, dict[str, float]] = {
    Action.CLOSE: {
        "pedestrian": 0.25,
        "commercial": -0.05,
        "vehicle_access": -0.35,
        "pedestrian_access": 0.15,
    },
    Action.TRAFFIC_RESTRICTION: {
        "pedestrian": 0.10,
        "commercial": -0.02,
        "vehicle_access": -0.15,
        "pedestrian_access": 0.05,
    },
}


def action_effects(cfg: Settings) -> dict[Action, dict[str, float]]:
    """Efectos por acción tomados de la configuración."""
    return {
        Action.CLOSE: {
            "pedestrian": cfg.pedestrian_gain_close,
            "commercial": cfg.commercial_penalty_close,
            "vehicle_access": cfg.vehicle_access_drop_close,
            "pedestrian_access": cfg.pedestrian_access_gain_close,
        },
        Action.TRAFFIC_RESTRICTION: {
            "pedestrian": cfg.pedestrian_gain_restriction,
            "commercial": cfg.commercial_penalty_restriction,
            "vehicle_access": cfg.vehicle_access_drop_restriction,
            "pedestrian_access": cfg.pedestrian_access_gain_restriction,
        },
    }

#: Proporción de tráfico que retiene una restricción parcial por defecto.
DEFAULT_RESTRICTION_RATIO = 0.6


@dataclass
class _SectionView:
    """Sección con su estado actual y su estado simulado."""

    section: Section
    metrics: SectionMetrics
    baseline_vehicles: float
    simulated_vehicles: float

    @property
    def lanes(self) -> int:
        """Carriles estimados de la sección."""
        return self.section.lanes or 2

    @property
    def capacity(self) -> float:
        """Capacidad horaria estimada."""
        return self.lanes * CAPACITY_PER_LANE


CAPACITY_PER_LANE = 1800.0


def neighbour_ids_of(
    target: Section,
    sections: dict[str, Section],
    order: list[str],
    cfg: Settings,
) -> list[str]:
    """Ids de las secciones vecinas más próximas, por distancia al centroide."""
    from app.schemas import haversine_m

    scored = [
        (haversine_m(target.centroid, sections[sid].centroid), sid)
        for sid in order
        if sid != target.id
    ]
    near = [(d, sid) for d, sid in scored if d <= cfg.neighbour_radius_m]
    near.sort()
    return [sid for _, sid in near[: cfg.neighbour_count]]


def _redistribute(
    displaced: float, views: list[_SectionView]
) -> float:
    """Reparte el tráfico desplazado por capacidad libre y devuelve el sobrante."""
    spare = [max(0.0, v.lanes * CAPACITY_PER_LANE - v.simulated_vehicles) for v in views]
    total_spare = sum(spare)

    if total_spare <= 0 or displaced <= 0:
        return displaced

    for view, room in zip(views, spare, strict=True):
        view.simulated_vehicles += displaced * (room / total_spare)

    overflow = sum(
        max(0.0, v.simulated_vehicles - v.lanes * CAPACITY_PER_LANE) for v in views
    )
    return min(displaced, overflow)


def _emissions(vehicles: float, section: Section, cfg: Settings) -> float:
    """Emisiones de CO2 en gramos por hora para una sección."""
    return vehicles * section.length_m * cfg.emission_factor_co2 / 1000.0


def simulated_zone_emissions(
    views: dict[str, _SectionView],
    baseline: float,
    displaced_outside: float,
    cfg: Settings,
) -> float:
    """Emisiones de la zona tras la intervención, de forma conservadora.

    Regla: **redistribuir tráfico dentro de la zona no ahorra emisiones.**

    Al repartir por capacidad libre, los vehículos aterrizan en calles que
    pueden ser más cortas que la intervenida. Como las emisiones son
    `vehículos x longitud`, eso bajaría el total sin que ningún vehículo
    recorra menos: sería un artefacto del modelo, no un efecto real.

    Así que se parte de las emisiones reales de partida y solo se descuentan
    las del tráfico que **abandona la zona**, medido a la longitud media que
    ya recorría. Si ese tráfico sale hacia otra calle de la ciudad, el ahorro
    es provisional: por eso `displaced_outside` también penaliza la
    confianza del veredicto.
    """
    leaked_length = _mean_length_of_reduced(views)
    avoided = displaced_outside * leaked_length * cfg.emission_factor_co2 / 1000.0
    return max(0.0, baseline - avoided)


def _mean_length_of_reduced(views: dict[str, _SectionView]) -> float:
    """Longitud media de las secciones que han perdido tráfico, ponderada."""
    reduced = [
        v
        for v in views.values()
        if v.baseline_vehicles - v.simulated_vehicles > 1e-9
    ]
    lost_total = sum(v.baseline_vehicles - v.simulated_vehicles for v in reduced)
    if lost_total <= 0:
        return 0.0
    return (
        sum(
            v.section.length_m * (v.baseline_vehicles - v.simulated_vehicles)
            for v in reduced
        )
        / lost_total
    )


def _weighted_travel_time(views: list[_SectionView], cfg: Settings) -> float:
    """Tiempo medio de desplazamiento ponderado por tráfico.

    Es la métrica que refleja el efecto indirecto: las secciones vecinas
    reciben más vehículos yCircular más despacio.
    """
    total_traffic = sum(v.simulated_vehicles for v in views)
    if total_traffic <= 0:
        return 0.0

    weighted = 0.0
    for view in views:
        speed = view.metrics.effective_speed_kmh or cfg.fallback_speed_kmh
        # Más tráfico que capacidad libre implica más congestión.
        free_capacity = max(1.0, view.lanes * CAPACITY_PER_LANE)
        congestion_penalty = 1.0 + max(0.0, view.simulated_vehicles - free_capacity) / free_capacity
        time_s = view.section.length_m / max(1.0, speed * 1000.0 / 3600.0 * congestion_penalty)
        weighted += time_s * view.simulated_vehicles
    return weighted / total_traffic


def simulate(
    scenario: Scenario,
    sections: list[Section],
    metrics_by_id: dict[str, SectionMetrics],
    cfg: Settings,
) -> SimulationResult:
    """Ejecuta el escenario sobre la zona y devuelve los KPIs."""
    by_id = {s.id: s for s in sections}
    if scenario.street_id not in by_id:
        raise KeyError(scenario.street_id)

    notes: list[str] = []
    target_section = by_id[scenario.street_id]

    views = {
        sid: _SectionView(
            section=s,
            metrics=metrics_by_id[sid],
            baseline_vehicles=s.intensity,
            simulated_vehicles=s.intensity,
        )
        for sid, s in by_id.items()
    }
    baseline_zone_traffic = sum(v.baseline_vehicles for v in views.values())
    baseline_emissions = sum(
        _emissions(v.baseline_vehicles, v.section, cfg) for v in views.values()
    )
    baseline_time = _weighted_travel_time(list(views.values()), cfg)

    # --- Regla 1: efecto directo de la intervención ---
    target = views[scenario.street_id]
    if scenario.action is Action.CLOSE:
        target.simulated_vehicles = 0.0
        notes.append("Sección intervenida cerrada al tráfico motorizado.")
    elif scenario.action is Action.TRAFFIC_RESTRICTION:
        ratio = float(scenario.params.get("allowed_ratio", DEFAULT_RESTRICTION_RATIO))
        ratio = max(0.0, min(1.0, ratio))
        target.simulated_vehicles = target.baseline_vehicles * ratio
        notes.append(f"Restricción parcial: se retiene el {ratio:.0%} del tráfico.")

    # --- Reglas 2 y 3: redistribución y tráfico que sale de la zona ---
    displaced = target.baseline_vehicles - target.simulated_vehicles
    neighbour_ids = neighbour_ids_of(target_section, by_id, list(by_id), cfg)
    displaced_outside = _redistribute(displaced, [views[sid] for sid in neighbour_ids])

    if displaced_outside > 0:
        notes.append(
            f"{displaced_outside:.0f} veh/h no caben en la zona: el efecto real "
            "sobre el resto de Bilbao queda fuera del alcance de este MVP."
        )
    if not neighbour_ids:
        notes.append("Sin secciones vecinas dentro del radio: no hay redistribución.")
    if displaced_outside <= 0 and displaced > 0:
        notes.append(
            "Todo el tráfico desplazado cabe dentro de la zona. Las emisiones no "
            "se modelan como ahorro: sin conocer la distancia real de desvío no "
            "se puede afirmar que los vehículos recorran menos, así que el modelo "
            "asume desvío neutro. El beneficio ambiental de una peatonalización "
            "no se puede quantificar con estos datos."
        )

    # --- Regla 4 y KPIs derivados ---
    simulated_zone_traffic = sum(v.simulated_vehicles for v in views.values())
    simulated_emissions = simulated_zone_emissions(
        views, baseline_emissions, displaced_outside, cfg
    )
    simulated_time = _weighted_travel_time(list(views.values()), cfg)

    effects = action_effects(cfg)[scenario.action]
    pedestrian_change = effects["pedestrian"]
    commercial_change = effects["commercial"]

    access_before = 100.0
    access_after = (
        ACCESSIBILITY_WEIGHTS["pedestrian"] * (100.0 * (1 + effects["pedestrian_access"]))
        + ACCESSIBILITY_WEIGHTS["vehicle"] * (100.0 * (1 + effects["vehicle_access"]))
    )
    accessibility_change = pct_change(access_before, access_after)

    kpis = KPIs(
        traffic_change=pct_change(baseline_zone_traffic, simulated_zone_traffic),
        emissions_change=pct_change(baseline_emissions, simulated_emissions),
        travel_time_change=pct_change(baseline_time, simulated_time),
        pedestrian_change=round(pedestrian_change * 100.0, 2),
        commercial_activity_change=round(commercial_change * 100.0, 2),
        accessibility_change=accessibility_change,
        baseline={
            "zone_vehicles_per_hour": round(baseline_zone_traffic, 1),
            "zone_emissions_g_co2_per_hour": round(baseline_emissions, 1),
            "zone_mean_travel_time_s": round(baseline_time, 1),
        },
        simulated={
            "zone_vehicles_per_hour": round(simulated_zone_traffic, 1),
            "zone_emissions_g_co2_per_hour": round(simulated_emissions, 1),
            "zone_mean_travel_time_s": round(simulated_time, 1),
        },
    )

    impacts = [
        SectionImpact(
            section_id=v.section.id,
            name=v.section.name,
            baseline_vehicles_per_hour=round(v.baseline_vehicles, 1),
            simulated_vehicles_per_hour=round(v.simulated_vehicles, 1),
            change_pct=pct_change(v.baseline_vehicles, v.simulated_vehicles),
        )
        for v in sorted(views.values(), key=lambda v: v.section.id)
        if abs(v.simulated_vehicles - v.baseline_vehicles) > 1e-9
    ]

    affected = [
        sid
        for sid in neighbour_ids
        if abs(views[sid].simulated_vehicles - views[sid].baseline_vehicles) > 1e-9
    ]

    # El agregado de zona conserva el tráfico si hay capacidad libre, así que
    # el riesgo de congestión se mide por sección, que es donde se manifiesta.
    max_section_increase_pct = max(
        (
            pct_change(v.baseline_vehicles, v.simulated_vehicles)
            for v in views.values()
            if v.section.id != scenario.street_id
        ),
        default=0.0,
    )
    if max_section_increase_pct > 5.0:
        notes.append(
            f"La sección más afectada sube un {max_section_increase_pct:.1f}%. "
            "El agregado de zona no lo refleja: el problema es local."
        )

    if not target_section.is_fresh:
        notes.append(
            f"La sección intervenida no tiene lectura de hoy "
            f"({target_section.observed_at}): la simulación parte de un dato antiguo."
        )
    notes.append(
        "Comercio y peatones son índices de potencial con porcentajes "
        "configurados; no son mediciones ni previsión de ventas."
    )

    return SimulationResult(
        scenario=scenario,
        kpis=kpis,
        impacts=impacts,
        displaced_outside_zone=round(displaced_outside, 1),
        max_section_increase_pct=max_section_increase_pct,
        affected_sections=affected,
        notes=notes,
    )


def find_section(sections: list[Section], street_id: str) -> Section | None:
    """Localiza una sección por id exacto o, si falla, por nombre.

    Permite escribir `street_id: "Gran Via"` sin conocer el código de sección
    que asigna el feed de Bilbao.
    """
    for s in sections:
        if s.id == street_id:
            return s

    target = street_id.strip().lower()
    # Se busca tanto en el nombre de OSM (euskera) como en el alias en
    # castellano, para que "Gran Vía" encuentre "On Diego Lopez Haroko kale
    # nagusia".
    for candidate in (s.name for s in sections):
        if candidate and target in candidate.lower():
            return next(s for s in sections if s.name == candidate)

    for candidate in (s.display_name for s in sections):
        if candidate and target in candidate.lower():
            return next(s for s in sections if s.display_name == candidate)

    return None
