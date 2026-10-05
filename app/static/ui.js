/* Utilidades compartidas por las pantallas del MVP.
 *
 * El escenario se guarda en localStorage para que se pueda recorrer el flujo
 * completo (datos → escenario → simulación → Jev) sin repetir la petición.
 */

const SCENARIO_KEY = "mvp.scenario";

export const $ = (id) => document.getElementById(id);

export const pct = (v) => (v > 0 ? "+" : "") + Number(v).toFixed(1) + "%";

/** Clase de color: `baja` cuando mejora la magnitud, `sube` cuando la empeora. */
export const dirClass = (v, goodUp) =>
  Math.abs(v) < 0.05 ? "igual" : (v > 0) === goodUp ? "baja" : "sube";

/* Los enums se emiten en mayúsculas, así que no sirven como clase CSS ni como
   texto de interfaz: se mapea el tono y la presentación (sentence case). */
const TONO = {
  BAJO: "ok", POSITIVO: "ok", FAVORABLE: "ok",
  ALTO: "error", NEGATIVO: "error", "REQUIERE REVISIÓN": "aviso",
  ACEPTABLE: "neutro", SIMULADO: "error", DERIVADO: "neutro", REAL: "ok",
};
const TEXTO = {
  BAJO: "Bajo", ALTO: "Alto", ACEPTABLE: "Aceptable",
  POSITIVO: "Positivo", NEGATIVO: "Negativo", FAVORABLE: "Favorable",
  "REQUIERE REVISIÓN": "Requiere revisión",
  REAL: "Real", DERIVADO: "Derivado", SIMULADO: "Simulado",
};

const tone = (v) => TONO[v] || "neutro";

/** Estado como texto con color. Sin fondo ni píldora: se lee como frase. */
export const tag = (v) =>
  `<span class="estado ${tone(v)}">${esc(TEXTO[v] || v)}</span>`;

/** Procedencia de una magnitud, con el mismo tratamiento que los estados. */
export const provenance = (v) => tag(v);

/** Escapa texto antes de insertarlo con innerHTML. */
export const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c],
  );

/* --- escenario compartido entre pantallas --- */

export const getScenario = () => {
  try {
    return JSON.parse(localStorage.getItem(SCENARIO_KEY));
  } catch {
    return null;
  }
};

export const setScenario = (s) => localStorage.setItem(SCENARIO_KEY, JSON.stringify(s));

/** Cuerpo del POST a /evaluate a partir del formulario de escenario. */
export function scenarioFromForm(streetEl, actionEl, ratioEl) {
  const action = actionEl.value;
  const params = action === "traffic_restriction" ? { allowed_ratio: Number(ratioEl.value) } : {};
  return { street_id: streetEl.value.trim(), action, params };
}

/** Ejecuta /evaluate guardando el escenario para las demás pantallas. */
export async function evaluate(body) {
  setScenario(body);
  const r = await fetch("/evaluate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await r.json();
  if (!r.ok) throw new Error(data.detail || r.statusText);
  return data;
}

/** Si no hay escenario guardado, manda a la pantalla de escenario. */
export function requireScenario() {
  const s = getScenario();
  if (!s) {
    window.location.replace("/escenario?hint=1");
    return null;
  }
  return s;
}

/** Muestra el error de una petición en un contenedor. */
export function showError(el, e) {
  el.innerHTML = `<span class="error-msg">${esc(e.message || e)}</span>`;
}

/* --- chrome institucional -------------------------------------------------
 * Cabecera, barra de navegación y pie se montan por JS para que las cinco
 * pantallas no repitan la misma marca. El escudo es un placeholder declarado:
 * no se puede dibujar el oficial sin su fichero.
 */

const PANTALLAS = [
  ["/", "Inicio"],
  ["/datos", "Datos"],
  ["/escenario", "Escenario"],
  ["/simulacion", "Simulación"],
  ["/jev", "Jev"],
];

export function renderChrome(active, migas = []) {
  const nav = PANTALLAS.map(([href, label]) => {
    const cur = href === active ? ' aria-current="page"' : "";
    return `<a href="${href}"${cur}>${esc(label)}</a>`;
  }).join("");

  document.body.insertAdjacentHTML(
    "afterbegin",
    `<a class="saltar" href="#principal">Saltar al contenido</a>
     <div class="franja"></div>
     <header class="cabecera">
       <div class="contenido">
         <div class="marca">
           <span class="escudo" role="img" aria-label="Escudo de Bilbao, pendiente">EB</span>
           <span>
             <span class="nombre">Bilbao</span><br>
             <span class="servicio">Laboratorio urbano digital</span>
           </span>
         </div>
         <div class="idiomas">
           <span aria-current="true" lang="es">ES</span>
           <span aria-disabled="true" lang="eu"
                 title="La versión en euskera está pendiente">EU</span>
         </div>
       </div>
     </header>
     <div class="barra"><nav aria-label="Pasos del flujo">${nav}</nav></div>`,
  );

  document.body.insertAdjacentHTML(
    "beforeend",
    `<footer class="pie">
       <div class="contenido">
         <div>
           <h3>El caso de uso</h3>
           <p class="legal" style="margin:0;font-size:15px">
             Qué ocurre al pedestrianizar una calle de Bilbao. MVP acotado: una
             acción, una sección de tráfico medida, un veredicto.
           </p>
         </div>
         <div>
           <h3>Pantallas</h3>
           <ul>${PANTALLAS.map(
             ([href, label]) => `<li><a href="${href}">${esc(label)}</a></li>`,
           ).join("")}</ul>
         </div>
         <div>
           <h3>Servicios técnicos</h3>
           <ul>
             <li><a href="/docs">Documentación de la API</a></li>
             <li><a href="/health">Estado de las fuentes</a></li>
             <li><a href="/streets">Calles de Bilbao</a></li>
           </ul>
         </div>
         <p class="legal">
           Estimaciones de un modelo de reglas sobre datos reales parciales.
           No son predicciones ni recomendaciones de política urbana.
           Procedencia de cada magnitud: real, derivado o simulado.
         </p>
       </div>
     </footer>`,
  );

  if (migas.length) {
    const trail = migas
      .map(([href, label]) =>
        href ? `<a href="${href}">${esc(label)}</a>` : `<span>${esc(label)}</span>`,
      )
      .join(" &rsaquo; ");
    document.querySelector("#principal")?.insertAdjacentHTML(
      "afterbegin",
      `<nav class="migas" aria-label="Migas de pan">${trail}</nav>`,
    );
  }
}

