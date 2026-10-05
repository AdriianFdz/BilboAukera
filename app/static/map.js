/* Mapa Leaflet con cartografía OSM y las secciones de tráfico superpuestas. */

const OSM_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
const SATELLITE_URL =
  "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";

function trafficColor(value, max) {
  const ratio = Math.min(1, Math.max(0, (value || 0) / max));
  const hue = 120 - ratio * 120;
  return `hsl(${hue} 78% 42%)`;
}

function boundsFromSections(sections, cameras, bbox) {
  const points = [];
  for (const sec of sections) {
    for (const [lon, lat] of sec.geometry || []) points.push([lat, lon]);
    if (sec.centroid) points.push([sec.centroid[1], sec.centroid[0]]);
  }
  for (const cam of cameras) {
    if (cam.centroid) points.push([cam.centroid[1], cam.centroid[0]]);
  }
  if (!points.length) return [[bbox[0], bbox[1]], [bbox[2], bbox[3]]];
  return points;
}

export function renderMap({ sections, cameras = [], bbox, targetId = null, onSelect }) {
  if (!globalThis.L) {
    throw new Error("No se pudo cargar Leaflet para mostrar el mapa.");
  }

  const container = document.createElement("div");
  container.className = "mapa-leaflet";
  container.setAttribute("role", "img");
  container.setAttribute(
    "aria-label",
    `Mapa OSM de las ${sections.length} secciones de tráfico de Bilbao`,
  );

  const map = L.map(container, { scrollWheelZoom: false, preferCanvas: true });
  const osm = L.tileLayer(OSM_URL, {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  });
  const satellite = L.tileLayer(SATELLITE_URL, {
    maxZoom: 19,
    attribution: "Tiles &copy; Esri",
  });
  satellite.addTo(map);

  const max = Math.max(1, ...sections.map((s) => s.intensity || 0));
  for (const sec of sections) {
    const latLngs = (sec.geometry || []).map(([lon, lat]) => [lat, lon]);
    if (latLngs.length < 2) continue;
    const selected = sec.id === targetId;
    const line = L.polyline(latLngs, {
      color: trafficColor(sec.intensity, max),
      weight: selected ? 8 : 4 + Math.round(4 * (sec.intensity || 0) / max),
      opacity: 0.95,
      lineCap: "round",
      lineJoin: "round",
    });
    const intensity = Math.round(sec.intensity || 0);
    const reading = intensity === 0
      ? "<br><small>Lectura a cero; puede ser sensor sin dato</small>"
      : "";
    line.bindTooltip(
      `${sec.display_name || sec.name || sec.id}<br><strong>${intensity} veh/h</strong>${reading}`,
    );
    if (onSelect) line.on("click", () => onSelect(sec));
    line.addTo(map);
  }

  for (const cam of cameras) {
    if (!cam.centroid) continue;
    L.circleMarker([cam.centroid[1], cam.centroid[0]], {
      radius: 5,
      color: "#ffffff",
      weight: 2,
      fillColor: "#22262B",
      fillOpacity: 1,
    }).bindTooltip(`Punto de observación: ${cam.name || cam.id}`).addTo(map);
  }

  const points = boundsFromSections(sections, cameras, bbox);
  map.fitBounds(points, { padding: [20, 20] });
  container._leafletMap = map;
  container._layers = { osm, satellite };
  setTimeout(() => map.invalidateSize(), 0);
  return container;
}

export function mapLegend(sections, cameras) {
  const max = Math.max(1, ...sections.map((s) => s.intensity || 0));
  return `<ul class="leyenda-mapa">
    <li><span class="muestra trafico-bajo"></span> 0–${Math.round(max / 3)} veh/h</li>
    <li><span class="muestra trafico-medio"></span> ${Math.round(max / 3)}–${Math.round((max * 2) / 3)} veh/h</li>
    <li><span class="muestra trafico-alto"></span> Más de ${Math.round((max * 2) / 3)} veh/h</li>
    <li><span class="muestra muestra-camara"></span> ${cameras.length} puntos de observación</li>
  </ul>`;
}

export function setMapLayer(container, layer) {
  const map = container?._leafletMap;
  const layers = container?._layers;
  if (!map || !layers) return;
  const chosen = layer === "satellite" ? layers.satellite : layers.osm;
  const other = layer === "satellite" ? layers.osm : layers.satellite;
  if (map.hasLayer(other)) map.removeLayer(other);
  if (!map.hasLayer(chosen)) map.addLayer(chosen);
}
