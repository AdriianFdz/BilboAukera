"""Esquemas Pydantic de la API del MVP."""

from __future__ import annotations

import math
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class Provenance(StrEnum):
    """Origen del dato, para no presentar estimaciones como mediciones."""

    REAL = "REAL"
    DERIVED = "DERIVADO"
    SIMULATED = "SIMULADO"


class Action(StrEnum):
    """Intervenciones soportadas por el MVP.

    Solo dos, a propósito: el caso de uso acotado es la peatonalización de
    la Gran Vía, y una restricción parcial de tráfico pesado como contraste.
    """

    CLOSE = "close"
    TRAFFIC_RESTRICTION = "traffic_restriction"


class RiskLevel(StrEnum):
    """Niveles de riesgo/impacto emitidos por Jev."""

    LOW = "BAJO"
    ACCEPTABLE = "ACEPTABLE"
    HIGH = "ALTO"
    POSITIVE = "POSITIVO"
    NEGATIVE = "NEGATIVO"


class OverallStatus(StrEnum):
    """Veredicto global de Jev."""

    FAVORABLE = "FAVORABLE"
    ACCEPTABLE = "ACEPTABLE"
    REVIEW_REQUIRED = "REQUIERE REVISIÓN"


class Section(BaseModel):
    """Sección de tráfico: la unidad real de simulación."""

    id: str
    name: str | None = Field(
        default=None, description="Nombre resuelto desde OSM por proximidad (en euskera)."
    )
    display_name: str | None = Field(
        default=None, description="Alias en castellano para presentación. Cosmético."
    )
    name_source: str | None = None
    intensity: float = Field(description="vehículos/hora (dato real observado).")
    velocity_kmh: float | None = None
    occupancy: float | None = None
    observed_at: str | None = None
    is_fresh: bool = True
    lanes: int | None = None
    speed_limit_kmh: float | None = None
    is_oneway: bool | None = None
    length_m: float = 0.0
    geometry: list[list[float]] = Field(default_factory=list)
    centroid: tuple[float, float] = (0.0, 0.0)
    provenance: Provenance = Provenance.REAL


class SectionMetrics(BaseModel):
    """Métricas derivadas de una sección, con su procedencia."""

    section_id: str
    vehicles_per_hour: float
    capacity_per_hour: float
    saturation: float
    length_m: float
    effective_speed_kmh: float
    travel_time_s: float
    emissions_g_co2_per_hour: float
    provenance: Provenance = Provenance.DERIVED


class CityState(BaseModel):
    """Estado actual de la zona de estudio."""

    zone: str
    bbox: list[float]
    sections: list[Section]
    metrics: list[SectionMetrics]
    coverage: dict[str, Any]
    provenance: Provenance = Provenance.REAL


class StreetRecord(BaseModel):
    """Calle del registro administrativo de Bilbao.

    Son las 923 calles de la ciudad, no solo las de la zona de estudio. Casi
    todas **no tienen tráfico medido**: `section_id` queda a `None` y no son
    simulables. El campo `match` dice con qué fuerza se cruzó con una sección
    de tráfico, porque la unión es por palabras y no es exacta.
    """

    code: str
    name: str
    street_type: str | None = None
    type_code: str | None = None
    section_id: str | None = None
    match: str = "none"
    match_score: int = 0


class Scenario(BaseModel):
    """Intervención define por el usuario."""

    street_id: str = Field(description="id de la sección intervenida.")
    action: Action
    start: str | None = Field(default=None, description="Hora inicio HH:MM.")
    end: str | None = Field(default=None, description="Hora fin HH:MM.")
    params: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_window(self) -> Scenario:
        """Comprueba que la ventana horaria sea coherente."""
        if self.start and self.end and self.start >= self.end:
            raise ValueError("`start` debe ser anterior a `end`")
        return self


class SectionImpact(BaseModel):
    """Impacto sobre una sección concreta."""

    section_id: str
    name: str | None = None
    baseline_vehicles_per_hour: float
    simulated_vehicles_per_hour: float
    change_pct: float
    provenance: Provenance = Provenance.SIMULATED


class KPIs(BaseModel):
    """Los seis indicadores del MVP, en porcentaje de variación."""

    traffic_change: float
    emissions_change: float
    travel_time_change: float
    pedestrian_change: float
    commercial_activity_change: float
    accessibility_change: float

    baseline: dict[str, float] = Field(default_factory=dict)
    simulated: dict[str, float] = Field(default_factory=dict)


class SimulationResult(BaseModel):
    """Salida de POST /simulate."""

    scenario: Scenario
    kpis: KPIs
    impacts: list[SectionImpact]
    displaced_outside_zone: float = Field(
        default=0.0, description="Vehículos/hora que no caben en la zona."
    )
    max_section_increase_pct: float = Field(
        default=0.0,
        description=(
            "Mayor aumento porcentual en una sección vecina. El tráfico se "
            "redistribuye dentro de la zona, así que el agregado de zona puede "
            "quedar igual: el riesgo real aparece por sección."
        ),
    )
    affected_sections: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    provenance: Provenance = Provenance.SIMULATED


class JevVerdict(BaseModel):
    """Evaluación estructurada de Jev. Sin texto libre."""

    traffic_risk: RiskLevel
    environmental_impact: RiskLevel
    commercial_impact: RiskLevel
    accessibility_impact: RiskLevel
    overall_status: OverallStatus
    confidence: float = Field(ge=0.0, le=1.0)
    alerts: list[str] = Field(default_factory=list)
    thresholds_applied: dict[str, Any] = Field(default_factory=dict)
    disclaimer: str = (
        "Clasificación por reglas sobre datos reales parciales. "
        "No es una predicción ni una recomendación de política urbana."
    )


class HealthResponse(BaseModel):
    """Estado del servicio."""

    status: str
    app: str
    version: str
    cache: dict[str, Any] = Field(default_factory=dict)


def safe_div(numerator: float, denominator: float) -> float:
    """División que devuelve 0 en lugar de fallar con denominador nulo."""
    return numerator / denominator if denominator else 0.0


def pct_change(baseline: float, simulated: float) -> float:
    """Variación porcentual, protegida ante baseline cero."""
    if not baseline:
        return 0.0
    return round((simulated - baseline) / baseline * 100.0, 2)


def haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Distancia en metros entre dos puntos (lon, lat)."""
    r = 6371000.0
    lon1, lat1 = map(math.radians, a)
    lon2, lat2 = map(math.radians, b)
    dlon, dlat = lon2 - lon1, lat2 - lat1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))
