"""Jev: capa de evaluación y decisión.

Recibe los KPIs de la simulación y devuelve un veredicto **estructurado**.
No genera texto libre y no inventa resultados: clasifica lo que el motor de
reglas ya ha calculado.

Es determinista a propósito. Los umbrales son configuración, no constantes
mágicas, para que un técnico municipal pueda revisarlos y justificar cada
clasificación.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings
from app.schemas import (
    JevVerdict,
    OverallStatus,
    RiskLevel,
    SimulationResult,
)


@dataclass(frozen=True)
class Thresholds:
    """Umbrales de clasificación. Ajustables por configuración."""

    #: Aumento de tráfico en la zona que dispara riesgo alto.
    traffic_high_pct: float = 15.0
    #: Aumento de tráfico en una sola sección que dispara riesgo alto. El
    #: riesgo de una peatonalización es local: la zona puede no variar.
    section_traffic_high_pct: float = 25.0
    #: Reducción de emisiones que se considera impacto positivo.
    emissions_positive_pct: float = -5.0
    #: Caída de potencial comercial que se considera riesgo.
    commercial_negative_pct: float = -10.0
    #: Caída de accesibilidad que se considera riesgo.
    accessibility_negative_pct: float = -10.0
    #: Aumento de tiempo de desplazamiento que degrada la movilidad.
    travel_time_high_pct: float = 20.0

    @classmethod
    def from_settings(cls, cfg: Settings) -> Thresholds:
        """Construye los umbrales desde la configuración de la aplicación."""
        return cls(**cfg.jev_thresholds)


DEFAULT_THRESHOLDS = Thresholds()


def _confidence(result: SimulationResult, sections_count: int, fresh_ratio: float) -> float:
    """Calcula la confianza del veredicto.

    Baja explícitamente si el tráfico desplazado se sale de la zona, si hay
    pocas secciones o si los datos no son frescos. Un escenario sin soporte
    suficiente no debe presentarse con confianza alta.
    """
    confidence = 0.6

    # El tráfico que sale de la zona queda sin simular: el impacto total es
    # desconocido, así que la confianza no puede ser alta.
    if result.displaced_outside_zone > 0:
        total = result.kpis.baseline.get("zone_vehicles_per_hour", 0.0)
        leaked = min(1.0, result.displaced_outside_zone / total) if total else 1.0
        confidence -= 0.3 * leaked

    if sections_count < 5:
        confidence -= 0.15
    confidence += 0.2 * max(0.0, min(1.0, fresh_ratio))

    return round(max(0.05, min(0.95, confidence)), 2)


def evaluate(
    result: SimulationResult,
    *,
    thresholds: Thresholds = DEFAULT_THRESHOLDS,
    sections_count: int = 0,
    fresh_ratio: float = 1.0,
) -> JevVerdict:
    """Clasifica un escenario simulado y devuelve el veredicto de Jev."""
    k = result.kpis
    alerts: list[str] = []

    # --- Riesgo de tráfico ---
    # Se evalúa el mayor de los dos señales: agregado de zona y sección más
    # afectada. Con capacidad libre en la zona el agregado apenas se mueve,
    # pero una calle vecina puede saturarse.
    traffic_signal = max(k.traffic_change, result.max_section_increase_pct)
    if result.max_section_increase_pct > thresholds.section_traffic_high_pct:
        traffic_risk = RiskLevel.HIGH
        alerts.append(
            f"una sección vecina sube un {result.max_section_increase_pct:.1f}%, "
            f"por encima del umbral de {thresholds.section_traffic_high_pct:.0f}% por sección"
        )
    elif traffic_signal > thresholds.traffic_high_pct:
        traffic_risk = RiskLevel.HIGH
        alerts.append(
            f"el tráfico aumenta un {traffic_signal:.1f}%, "
            f"por encima del umbral de {thresholds.traffic_high_pct:.0f}%"
        )
    elif traffic_signal > 5.0:
        traffic_risk = RiskLevel.ACCEPTABLE
    else:
        traffic_risk = RiskLevel.LOW

    # --- Impacto ambiental ---
    if k.emissions_change < thresholds.emissions_positive_pct:
        environmental = RiskLevel.POSITIVE
    else:
        environmental = RiskLevel.ACCEPTABLE

    # --- Impacto comercial (potencial, no ventas) ---
    if k.commercial_activity_change < thresholds.commercial_negative_pct:
        commercial = RiskLevel.NEGATIVE
        alerts.append("riesgo sobre el potencial de actividad comercial")
    elif k.commercial_activity_change > 2.0:
        commercial = RiskLevel.POSITIVE
    else:
        commercial = RiskLevel.ACCEPTABLE

    # --- Accesibilidad ---
    if k.accessibility_change < thresholds.accessibility_negative_pct:
        accessibility = RiskLevel.NEGATIVE
        alerts.append(
            f"la accesibilidad baja un {abs(k.accessibility_change):.1f}%"
        )
    else:
        accessibility = RiskLevel.ACCEPTABLE

    # --- Degradación de movilidad: el proceso se ralentiza ---
    if k.travel_time_change > thresholds.travel_time_high_pct:
        traffic_risk = RiskLevel.HIGH
        alerts.append(
            f"el tiempo de desplazamiento sube un {k.travel_time_change:.1f}%"
        )

    if result.displaced_outside_zone > 0:
        alerts.append(
            f"{result.displaced_outside_zone:.0f} veh/h desplazados fuera de la zona: "
            "el impacto sobre el resto de la ciudad no está simulado"
        )

    # --- Veredicto global ---
    risky = (RiskLevel.HIGH, RiskLevel.NEGATIVE)
    negatives = sum(
        1 for v in (traffic_risk, commercial, accessibility) if v in risky
    )
    if negatives >= 2 or (negatives == 1 and k.emissions_change > 0):
        overall = OverallStatus.REVIEW_REQUIRED
    elif negatives == 0:
        overall = OverallStatus.FAVORABLE
    else:
        overall = OverallStatus.ACCEPTABLE

    return JevVerdict(
        traffic_risk=traffic_risk,
        environmental_impact=environmental,
        commercial_impact=commercial,
        accessibility_impact=accessibility,
        overall_status=overall,
        confidence=_confidence(result, sections_count, fresh_ratio),
        alerts=alerts,
        thresholds_applied={
            "traffic_high_pct": thresholds.traffic_high_pct,
            "section_traffic_high_pct": thresholds.section_traffic_high_pct,
            "emissions_positive_pct": thresholds.emissions_positive_pct,
            "commercial_negative_pct": thresholds.commercial_negative_pct,
            "accessibility_negative_pct": thresholds.accessibility_negative_pct,
            "travel_time_high_pct": thresholds.travel_time_high_pct,
        },
    )
