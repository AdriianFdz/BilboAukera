"""Carga de datos reales: Bilbao Open Data + OpenStreetMap.

Cada fuente se descarga una vez y se cachea en `data/*.json`. Si no hay red,
el MVP sigue funcionando con la última caché válida o, en su defecto, con
datos sintéticos marcados como tales (`provenance: derived`).

Las secciones de tráfico reales **no traen nombre de calle**, así que se
resuelve por proximidad con la red viaria de OSM.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from app.config import Settings, settings
from app.schemas import (
    CityState,
    Provenance,
    Section,
    SectionMetrics,
    haversine_m,
    safe_div,
)

logger = logging.getLogger(__name__)

OVERPASS_QUERY = (
    "[out:json][timeout:60];"
    'way["highway"~"^(trunk|primary|secondary|tertiary|residential|pedestrian|'
    'living_street|unclassified)$"]({bbox});'
    "out geom 400;"
)


def _http_get_json(url: str, *, post: bool = False, payload: str | None = None) -> object:
    """Descarga JSON con urllib y timeout razonable."""
    import urllib.parse
    import urllib.request

    if post:
        # Overpass exige el cuerpo urlencoded: sin esto devuelve 400.
        data = urllib.parse.urlencode({"data": payload or ""}).encode()
        req = urllib.request.Request(url, data=data)
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
    else:
        req = urllib.request.Request(url)

    # Overpass rechaza (406) las peticiones sin User-Agent.
    req.add_header("User-Agent", "mvp-urbano-bilbao/0.1 (reto smart city)")

    with urllib.request.urlopen(req, timeout=90) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw)


def _cached_fetch(name: str, url: str, *, post: bool = False, payload: str | None = None) -> object:
    """Descarga una fuente usando la caché en disco como red de seguridad."""
    path = Path(settings.cache_path(name))
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        try:
            logger.info("Usando caché local: %s", path)
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning("Caché corrupta, se reintenta la descarga: %s", path)

    try:
        logger.info("Descargando %s", url)
        data = _http_get_json(url, post=post, payload=payload)
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return data
    except Exception as exc:
        logger.error("Fallo al descargar %s (%s)", name, exc)
        return None


# --------------------------------------------------------------------------
# Lectura de fuentes
# --------------------------------------------------------------------------


def _outer_ring(geom_type: str, coords: list[Any]) -> list[Any]:
    """Devuelve el anillo exterior de una geometría Polygon o MultiPolygon.

    El feed de Bilbao mezcla ambos tipos, así que hay que desempaquetarlos
    explícitamente: `Polygon` → coords[0], `MultiPolygon` → coords[0][0].
    """
    if not coords:
        return []
    if geom_type == "MultiPolygon":
        polygon = coords[0] if coords else []
        return polygon[0] if polygon else []
    return coords[0]


def _safe_float(value: object) -> float | None:
    """Convierte a float tolerando valores nulos o no numéricos."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _polygon_perimeter_m(geom_type: str, coords: list[Any]) -> float:
    """Perímetro de la geometría en metros (proxy de longitud de tramo)."""
    ring = _outer_ring(geom_type, coords)
    if len(ring) < 2:
        return 0.0
    total = 0.0
    for i in range(len(ring) - 1):
        total += haversine_m(tuple(ring[i]), tuple(ring[i + 1]))
    if ring[0] != ring[-1]:
        total += haversine_m(tuple(ring[-1]), tuple(ring[0]))
    return round(total, 1)


def _polygon_centroid(geom_type: str, coords: list[Any]) -> tuple[float, float]:
    """Centroide del anillo exterior."""
    ring = _outer_ring(geom_type, coords)
    n = len(ring)
    if n == 0:
        return (0.0, 0.0)
    return (
        round(sum(p[0] for p in ring) / n, 6),
        round(sum(p[1] for p in ring) / n, 6),
    )


def _in_bbox(lon: float, lat: float, cfg: Settings) -> bool:
    """Comprueba si un punto cae dentro de la bbox de estudio."""
    return (
        cfg.bbox_west <= lon <= cfg.bbox_east
        and cfg.bbox_south <= lat <= cfg.bbox_north
    )


def _parse_observed_at(value: str | None) -> datetime | None:
    """Interpreta el timestamp `YYYY-MM-DD HH:MM:SS.0` del feed de Bilbao."""
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def load_osm_streets(cfg: Settings) -> list[dict[str, Any]]:
    """Red viaria de OSM dentro de la bbox, con nombres, carriles y sentidos."""
    query = OVERPASS_QUERY.replace("{bbox}", cfg.bbox)
    raw = _cached_fetch("osm_streets", cfg.overpass_url, post=True, payload=query)
    if not raw:
        return []

    streets: list[dict[str, Any]] = []
    for way in raw.get("elements", []):
        tags = way.get("tags") or {}
        geom = way.get("geometry") or []
        if not tags.get("name") or len(geom) < 2:
            continue

        lanes = None
        if tags.get("lanes"):
            try:
                lanes = int(float(tags["lanes"]))
            except ValueError:
                lanes = None

        speed = None
        if tags.get("maxspeed"):
            try:
                speed = float(str(tags["maxspeed"]).replace("km/h", "").strip())
            except ValueError:
                speed = None

        points = [[round(p["lon"], 6), round(p["lat"], 6)] for p in geom]
        length_m = round(
            sum(
                haversine_m(tuple(points[i]), tuple(points[i + 1]))
                for i in range(len(points) - 1)
            ),
            1,
        )

        streets.append(
            {
                "osm_id": f"way/{way['id']}",
                "name": tags["name"],
                "highway": tags.get("highway"),
                "lanes": lanes or (1 if tags.get("oneway") == "yes" else 2),
                "oneway": tags.get("oneway") == "yes",
                "speed_limit_kmh": speed or (30.0 if tags["highway"] != "trunk" else 50.0),
                "length_m": length_m,
                "centroid": _line_centroid(points),
                "points": points,
            }
        )
    logger.info("OSM: %d calles con nombre en la bbox", len(streets))
    return streets


def _line_centroid(points: list[list[float]]) -> tuple[float, float]:
    """Centroide del punto medio de una polilínea."""
    mid = points[len(points) // 2]
    return (mid[0], mid[1])


def _nearest_street(
    point: tuple[float, float], streets: list[dict[str, Any]], max_m: float = 250.0
) -> dict[str, Any] | None:
    """Calle OSM más próxima a un punto, dentro de un radio máximo."""
    best: tuple[float, dict[str, Any]] | None = None
    for st in streets:
        d = haversine_m(point, st["centroid"])
        if d <= max_m and (best is None or d < best[0]):
            best = (d, st)
    return best[1] if best else None


def load_sections(cfg: Settings) -> tuple[list[Section], dict[str, Any]]:
    """Secciones de tráfico de Bilbao, unidas por nombre con OSM."""
    raw = _cached_fetch("trafico", cfg.trafico_url)
    streets = load_osm_streets(cfg)

    if not raw or "features" not in raw:
        logger.warning("Sin feed de tráfico: se usan datos sintéticos de demostración.")
        return _synthetic_sections(cfg), _synthetic_coverage(cfg)

    now = datetime.now()
    sections: list[Section] = []
    stale = 0
    off_zone = 0

    for feat in raw["features"]:
        props = feat.get("properties") or {}
        geom = feat.get("geometry") or {}
        geom_type = geom.get("type", "Polygon")
        coords = geom.get("coordinates") or []
        if not coords:
            continue

        centroid = _polygon_centroid(geom_type, coords)
        if not _in_bbox(centroid[0], centroid[1], cfg):
            off_zone += 1
            continue

        try:
            intensity = float(props.get("Intensidad"))
            velocity = float(props.get("Velocidad"))
            occupancy = float(props.get("Ocupacion"))
        except (TypeError, ValueError):
            continue

        observed = _parse_observed_at(props.get("FechaHora"))
        is_fresh = bool(observed and now - observed <= timedelta(hours=cfg.freshness_hours))

        match = _nearest_street(centroid, streets)
        osm_name = match["name"] if match else None
        section = Section(
            id=str(props.get("CodigoSeccion")),
            name=osm_name,
            display_name=cfg.name_aliases.get(osm_name, osm_name),
            name_source=f"osm:{match['osm_id']}" if match else None,
            intensity=intensity,
            velocity_kmh=velocity,
            occupancy=occupancy,
            observed_at=props.get("FechaHora"),
            is_fresh=is_fresh,
            lanes=match["lanes"] if match else None,
            speed_limit_kmh=match["speed_limit_kmh"] if match else None,
            is_oneway=match["oneway"] if match else None,
            length_m=_polygon_perimeter_m(geom_type, coords),
            geometry=[[float(p[0]), float(p[1])] for p in _outer_ring(geom_type, coords)],
            centroid=centroid,
        )
        sections.append(section)
        if not is_fresh:
            stale += 1

    coverage = {
        "sections_in_zone": len(sections),
        "sections_off_zone_skipped": off_zone,
        "stale_sections": stale,
        "fresh_sections": len(sections) - stale,
        "freshness_pct": round(safe_div(len(sections) - stale, len(sections)) * 100, 1),
        "zero_intensity_sections": sum(1 for s in sections if s.intensity == 0),
        "named_sections": sum(1 for s in sections if s.name),
        "source": "bilbao.eus srvDatasetTrafico + OSM",
    }
    logger.info(
        "Tráfico: %d secciones en zona, %d con nombre OSM",
        len(sections),
        coverage["named_sections"],
    )
    return sections, coverage


def _synthetic_sections(cfg: Settings) -> list[Section]:
    """Datos sintéticos de respaldo, explícitamente marcados como derivados."""
    names = ["Gran Via Don Diego Lopez de Haro", "Euskalduna", "General Concha", "Autonomía"]
    sections = []
    for i, name in enumerate(names):
        lon = cfg.bbox_west + 0.002 * i
        lat = cfg.bbox_south + 0.001 * i
        sections.append(
            Section(
                id=f"synthetic-{i}",
                name=name,
                display_name=name,
                name_source="synthetic",
                intensity=float(400 + 250 * i),
                velocity_kmh=22.0,
                occupancy=3.0,
                observed_at=datetime.now().isoformat(timespec="seconds"),
                is_fresh=True,
                lanes=2,
                speed_limit_kmh=50.0,
                length_m=220.0 + 40 * i,
                geometry=[[lon, lat], [lon + 0.001, lat + 0.0004]],
                centroid=(lon, lat),
                provenance=Provenance.DERIVED,
            )
        )
    return sections


def _synthetic_coverage(cfg: Settings) -> dict[str, Any]:
    """Cobertura declarada como sintética, para no ocultarlo."""
    return {
        "sections_in_zone": 0,
        "synthetic": True,
        "source": "fallback sintetico (sin acceso al feed de Bilbao)",
        "freshness_pct": 0.0,
    }


def compute_metrics(section: Section, cfg: Settings) -> SectionMetrics:
    """Deriva capacidad, saturación, tiempo y emisiones de una sección."""
    lanes = section.lanes or 2
    capacity = lanes * cfg.capacity_per_lane_per_hour

    # `Velocidad` del feed tiene mediana de 1 km/h: no es utilizable como
    # velocidad real, así que se interpreta solo como severidad relativa.
    observed = section.velocity_kmh or 0.0
    effective = observed if observed >= 10.0 else cfg.fallback_speed_kmh

    travel_time = safe_div(section.length_m * 1000.0, effective * 1000.0 / 3600.0)
    emissions = section.intensity * section.length_m * cfg.emission_factor_co2 / 1000.0

    return SectionMetrics(
        section_id=section.id,
        vehicles_per_hour=section.intensity,
        capacity_per_hour=capacity,
        saturation=round(safe_div(section.intensity, capacity), 3),
        length_m=section.length_m,
        effective_speed_kmh=effective,
        travel_time_s=round(travel_time, 1),
        emissions_g_co2_per_hour=round(emissions, 1),
    )


def load_cameras(cfg: Settings) -> dict[str, Any]:
    """Puntos de observación del Ayuntamiento dentro de la zona.

    **No alimenta la simulación.** El feed no trae ninguna cifra de tráfico
    (ni intensidad, ni conteo, ni velocidad) y las instantáneas que promete
    el campo `URL` devuelven 404, así que no hay nada medible que extraer.

    Lo único real que aporta es *dónde* se observa la calle, que sirve para
    auditar la procedencia: qué secciones tienen un punto de verificación
    cercano y quién puede contrastar la medición. Por eso `usable` es False
    y no se usa en ningún cálculo del motor.

    Se expone como `/cameras` para que la pantalla de datos muestre la capa
    de contexto con su limitación explícita, en vez de omitirla en silencio.
    """
    raw = _cached_fetch("camaras", cfg.camaras_url)
    empty = {
        "source": "bilbao.eus srvDatasetCamaras",
        "total_in_city": 0,
        "in_zone": 0,
        "usable_for_simulation": False,
        "limitation": (
            "El feed no contiene cifras de tráfico y las instantáneas del campo "
            "URL devuelven 404 (verificado). Solo se usa como capa de contexto."
        ),
        "cameras": [],
    }
    if not raw or "features" not in raw:
        return empty

    cameras: list[dict[str, Any]] = []
    total = 0
    for feat in raw["features"]:
        geom = feat.get("geometry") or {}
        if geom.get("type") != "Point":
            continue
        coords = geom.get("coordinates") or []
        if len(coords) < 2:
            continue
        total += 1
        lon, lat = float(coords[0]), float(coords[1])
        if not _in_bbox(lon, lat, cfg):
            continue
        props = feat.get("properties") or {}
        cameras.append(
            {
                "id": str(props.get("ID") or ""),
                "name": props.get("Nombre") or props.get("Texto_SPA"),
                "type": props.get("Tipo"),
                "rotation_deg": _safe_float(props.get("Rotacion_SPA")),
                "centroid": [lon, lat],
                "provenance": Provenance.REAL.value,
            }
        )

    logger.info("Cámaras: %d en la ciudad, %d dentro de la zona", total, len(cameras))
    return {
        "source": "bilbao.eus srvDatasetCamaras",
        "total_in_city": total,
        "in_zone": len(cameras),
        "usable_for_simulation": False,
        "limitation": empty["limitation"],
        "cameras": cameras,
    }


def nearest_camera_m(camera: dict[str, Any], section: Section) -> float:
    """Distancia en metros entre una cámara y el centroide de una sección."""
    return haversine_m(tuple(camera["centroid"]), section.centroid)


def load_city_state(cfg: Settings) -> CityState:
    """Estado actual completo de la zona de estudio."""
    sections, coverage = load_sections(cfg)
    metrics = [compute_metrics(s, cfg) for s in sections]
    return CityState(
        zone=cfg.zone_name,
        bbox=[cfg.bbox_south, cfg.bbox_west, cfg.bbox_north, cfg.bbox_east],
        sections=sections,
        metrics=metrics,
        coverage=coverage,
    )


def neighbour_ids(section: Section, sections: list[Section], cfg: Settings) -> list[str]:
    """Secciones vecinas más próximas dentro del radio configurado."""
    scored = [
        (haversine_m(section.centroid, other.centroid), other.id)
        for other in sections
        if other.id != section.id
    ]
    close = [(d, sid) for d, sid in scored if d <= cfg.neighbour_radius_m]
    close.sort()
    return [sid for _, sid in close[: cfg.neighbour_count]]


def cache_status(cfg: Settings) -> dict[str, Any]:
    """Estado de los ficheros de caché, para /health."""
    status: dict[str, Any] = {}
    for name in ("trafico", "osm_streets", "camaras"):
        path = Path(cfg.cache_path(name))
        if path.exists():
            age_h = (datetime.now().timestamp() - path.stat().st_mtime) / 3600.0
            status[name] = {
                "cached": True,
                "size_kb": round(path.stat().st_size / 1024, 1),
                "age_hours": round(age_h, 1),
            }
        else:
            status[name] = {"cached": False}
    return status


os.makedirs(settings.cache_dir, exist_ok=True)
