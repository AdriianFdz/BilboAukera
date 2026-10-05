"""Configuración del MVP.

Todos los umbrales del modelo viven aquí y son ajustables sin tocar código.
Se leen de variables de entorno con prefijo `MVP_`.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Parámetros de configuración del simulador."""

    model_config = SettingsConfigDict(env_prefix="MVP_", env_file=".env", extra="ignore")

    app_name: str = "MVP Laboratorio Urbano Bilbao"
    version: str = "0.1.0"
    debug: bool = False

    # --- Zona de estudio (Abando / Indautxu) ---
    zone_name: str = "Abando / Indautxu"
    bbox_south: float = 43.2635
    bbox_west: float = -2.9470
    bbox_north: float = 43.2740
    bbox_east: float = -2.9295

    # --- Fuentes de datos ---
    trafico_url: str = "https://www.bilbao.eus/aytoonline/srvDatasetTrafico?formato=geojson"
    camaras_url: str = "https://www.bilbao.eus/aytoonline/srvDatasetCamaras?formato=gml&v=1"
    overpass_url: str = "https://overpass-api.de/api/interpreter"
    cache_dir: str = "data"
    #: Registro oficial de calles de Bilbao (cod_calle, nombre, tipo de vía).
    #: Aportado como fichero local: no se descarga de ninguna API.
    street_registry_path: str = "data/calles.csv"

    # --- Frescura de datos ---
    #: Secciones más antiguas que esto se marcan como no frescas.
    freshness_hours: int = 24
    #: Radio (m) a partir del cual una cámara se considera que observa una
    #: sección. Solo sirve para auditar la procedencia del dato, no para medir.
    camera_audit_radius_m: int = 150
    #: Vecinas consideradas para redistribuir tráfico.
    neighbour_count: int = 4
    #: Radio máximo (m) para considerar que dos secciones son vecinas.
    neighbour_radius_m: int = 350
    #: Fracción del tráfico desplazado que se estima que abandona la zona.
    #: La bbox es una muestra acotada, no una red cerrada de calles.
    displaced_outside_share: float = 0.20

    # --- Parámetros físicos del modelo ---
    #: Capacidad por carril y hora en vía urbana.
    capacity_per_lane_per_hour: float = 1800.0
    #: Factor de emisión g CO2 por vehículo-km en tráfico urbano.
    emission_factor_co2: float = 120.0
    #: Velocidad de referencia cuando la velocidad observada no es utilizable.
    fallback_speed_kmh: float = 30.0

    #: OSM devuelve los nombres en euskera. Estos alias son solo de
    #: presentación: el nombre original de OSM se conserva siempre.
    name_aliases: dict[str, str] = {
        "On Diego Lopez Haroko kale nagusia": "Gran Vía de Don Diego López de Haro",
        "Iparraguirre kalea": "Calle Iparraguirre",
        "General Concha kalea": "Avenida General Concha",
    }

    # --- Ganancias configurables por acción (fracción) ---
    pedestrian_gain_close: float = 0.25
    pedestrian_gain_restriction: float = 0.10
    commercial_penalty_close: float = -0.05
    commercial_penalty_restriction: float = -0.02
    vehicle_access_drop_close: float = -0.35
    vehicle_access_drop_restriction: float = -0.15
    pedestrian_access_gain_close: float = 0.15
    pedestrian_access_gain_restriction: float = 0.05

    # --- Umbrales de clasificación de Jev ---
    #: Aumento de tráfico agregado que dispara riesgo alto.
    traffic_high_pct: float = 15.0
    #: Aumento en una sola sección que dispara riesgo alto. El riesgo de una
    #: peatonalización es local: la zona puede no variar.
    section_traffic_high_pct: float = 25.0
    #: Reducción de emisiones que se considera impacto ambiental positivo.
    emissions_positive_pct: float = -5.0
    #: Caída del potencial comercial que se considera riesgo.
    commercial_negative_pct: float = -10.0
    #: Caída de accesibilidad que se considera riesgo.
    accessibility_negative_pct: float = -10.0
    #: Aumento del tiempo de desplazamiento que degrada la movilidad.
    travel_time_high_pct: float = 20.0

    @property
    def jev_thresholds(self) -> dict[str, float]:
        """Umbrales de Jev en formato plano."""
        return {
            "traffic_high_pct": self.traffic_high_pct,
            "section_traffic_high_pct": self.section_traffic_high_pct,
            "emissions_positive_pct": self.emissions_positive_pct,
            "commercial_negative_pct": self.commercial_negative_pct,
            "accessibility_negative_pct": self.accessibility_negative_pct,
            "travel_time_high_pct": self.travel_time_high_pct,
        }

    @property
    def bbox(self) -> str:
        """Bbox en sintaxis Overpass: south,west,north,east."""
        return f"{self.bbox_south},{self.bbox_west},{self.bbox_north},{self.bbox_east}"

    def cache_path(self, name: str) -> str:
        """Ruta absoluta del fichero de caché de una fuente."""
        return f"{self.cache_dir}/{name}.json"


@lru_cache
def get_settings() -> Settings:
    """Devuelve la configuración cacheada."""
    return Settings()


settings = get_settings()
