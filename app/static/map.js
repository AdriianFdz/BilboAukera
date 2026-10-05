/* Mapa de la zona en SVG inline, dibujado con la geometría real de las
 * secciones que devuelve `/city`.
 *
 * Se hace en SVG y no con Leaflet/MapLibre a propósito: no depende de un CDN
 * ni de red en el momento de verlo, y las coordenadas son las de verdad.
 * Lo que no da es fondo de calle ni nombres: es un plano de secciones.
 *
 * El lienzo se calcula sobre la geometría real, no sobre el rectángulo
 * declarado en la configuración: si se usara ese, los vértices de los polígonos
 * que asoman fuera se recortarían sin avisar.
 */

const NS = "http://www.w3.org/2000/svg";

const svgEl = (name, attrs = {}) => {
  const el = document.createElementNS(NS, name);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  return el;
};

/**
 * Extensión real que hay que dibujar: el rectángulo de la zona más todo lo que
 * asome de la geometría y de los marcadores.
 */
function dataExtents(bbox, sections, cameras) {
  let wE = bbox[1], e = bbox[3], s = bbox[0], n = bbox[2];
  const widen = (lon, lat) => {
    wE = Math.min(wE, lon); e = Math.max(e, lon);
    s = Math.min(s, lat); n = Math.max(n, lat);
  };
  for (const sec of sections) {
    for (const [lon, lat] of sec.geometry || []) widen(lon, lat);
    if (sec.centroid) widen(sec.centroid[0], sec.centroid[1]);
  }
  for (const cam of cameras) {
    if (cam.centroid) widen(cam.centroid[0], cam.centroid[1]);
  }
  return [s, wE, n, e];
}

/** Proyecta lon/lat a un rectángulo SVG, corrigiendo la relación de aspecto. */
function makeProjection(bbox, w, h, pad = 16) {
  const [s, wE, n, e] = bbox;
  const midLat = (s + n) / 2;
  // A esta latitud 1° de longitud mide ~cos(lat) veces lo que 1° de latitud.
  const kx = Math.cos((midLat * Math.PI) / 180);
  const wSpan = (e - wE) * kx;
  const hSpan = n - s;
  const scale = Math.min((w - pad * 2) / wSpan, (h - pad * 2) / hSpan);
  const offX = (w - wSpan * scale) / 2;
  const offY = (h - hSpan * scale) / 2;

  return ([lon, lat]) => [
    offX + (lon - wE) * kx * scale,
    // La latitud crece hacia arriba, la pantalla hacia abajo.
    offY + (n - lat) * scale,
  ];
}

/**
 * Dibuja el mapa.
 * @param {object} o
 * @param {Array}  o.sections  secciones con `geometry`, `centroid`, `intensity`
 * @param {Array}  o.cameras    cámaras con `centroid`
 * @param {number[]} o.bbox    [south, west, north, east]
 * @param {string} o.targetId  sección a destacar
 * @param {(s:object)=>void} o.onSelect  callback al pulsar una sección
 */
export function renderMap({ sections, cameras = [], bbox, targetId = null, onSelect }) {
  const W = 620;
  const H = 380;
  const project = makeProjection(dataExtents(bbox, sections, cameras), W, H);

  const svg = svgEl("svg", {
    viewBox: `0 0 ${W} ${H}`,
    width: "100%",
    role: "img",
    "aria-label": `Plano de las ${sections.length} secciones de tráfico de la zona, coloreado por intensidad`,
  });

  const maxInt = Math.max(1, ...sections.map((s) => s.intensity || 0));
  const target = sections.find((s) => s.id === targetId);

  // Polígonos de las secciones, coloreados por intensidad: azul Bilbao poco
  // saturado cuando hay poco tráfico, rojo Bilbao en el extremo alto. La
  // sección objetivo se distingue por el borde, no por el relleno.
  for (const sec of sections) {
    const pts = (sec.geometry || []).map(project);
    if (pts.length < 3) continue;
    const isTarget = sec.id === targetId;
    const t = Math.min(1, (sec.intensity || 0) / maxInt);

    const poly = svgEl("polygon", {
      points: pts.map((p) => p.join(",")).join(" "),
      fill: t > 0.66 ? "var(--rojo)" : t > 0.33 ? "var(--azul)" : "var(--azul-tenue)",
      "fill-opacity": isTarget ? "0.55" : "0.75",
      stroke: isTarget ? "var(--rojo-oscuro)" : "var(--blanco)",
      "stroke-width": isTarget ? 3 : 1,
    });
    const title = svgEl("title");
    title.textContent =
      `${sec.display_name || sec.name || sec.id} · ${Math.round(sec.intensity || 0)} veh/h`;
    poly.appendChild(title);
    if (onSelect) poly.addEventListener("click", () => onSelect(sec));
    svg.appendChild(poly);
  }

  // Cámaras: triángulo apuntando en la dirección de rotación.
  for (const cam of cameras) {
    const [x, y] = project(cam.centroid);
    const g = svgEl("g", { transform: `translate(${x} ${y}) rotate(${cam.rotation_deg ?? 0})` });
    g.appendChild(svgEl("path", {
      d: "M0 -6 L4.5 5 L0 2.5 L-4.5 5 Z",
      fill: "var(--azul-oscuro)",
      stroke: "var(--blanco)",
      "stroke-width": 1.5,
    }));
    const title = svgEl("title");
    title.textContent = `Punto de observación: ${cam.name || cam.id}`;
    g.appendChild(title);
    svg.appendChild(g);
  }

  // Etiqueta de la sección objetivo, con halo para que se lea sobre el color.
  if (target) {
    const [x, y] = project(target.centroid);
    const label = svgEl("text", {
      x, y: y - 12, fill: "var(--tinta)",
      "font-size": 12, "text-anchor": "middle", "font-weight": 600,
      stroke: "var(--blanco)", "stroke-width": 4, "paint-order": "stroke",
    });
    label.textContent = target.display_name || target.name || target.id;
    svg.appendChild(label);
  }

  return svg;
}

/** Leyenda del mapa como lista de texto: el color no puede ser lo único. */
export function mapLegend(sections, cameras) {
  const maxInt = Math.max(1, ...sections.map((s) => s.intensity || 0));
  return `<ul class="leyenda-mapa">
    <li><span class="muestra" style="background:var(--azul-tenue);border-color:var(--linea)"></span>
      Hasta ${Math.round(maxInt / 3)} veh/h</li>
    <li><span class="muestra" style="background:var(--azul);border-color:var(--azul)"></span>
      Entre ${Math.round(maxInt / 3)} y ${Math.round((maxInt * 2) / 3)} veh/h</li>
    <li><span class="muestra" style="background:var(--rojo);border-color:var(--rojo)"></span>
      Más de ${Math.round((maxInt * 2) / 3)} veh/h</li>
    <li><span class="muestra" style="border-radius:50%;background:var(--azul-oscuro)"></span>
      ${cameras.length} puntos de observación, con su dirección de giro</li>
  </ul>`;
}
