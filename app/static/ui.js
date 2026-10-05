/* Utilidades compartidas por las pantallas del MVP.
 *
 * El escenario se guarda en localStorage para que se pueda recorrer el flujo
 * completo (datos → escenario → simulación → Jev) sin repetir la petición.
 */

const SCENARIO_KEY = "mvp.scenario";

export const $ = (id) => document.getElementById(id);

export const pct = (v) => (v > 0 ? "+" : "") + Number(v).toFixed(1) + "%";

/* Color según si la variación es buena o mala para esa magnitud. */
export const dirClass = (v, goodUp) =>
  Math.abs(v) < 0.05 ? "zero" : (v > 0) === goodUp ? "pos" : "neg";

/* Los enums se emiten en castellano y algunos llevan espacios y acentos
   ("REQUIERE REVISIÓN"), así que no sirven como clase CSS: se mapea el tono. */
const GOOD = new Set(["BAJO", "POSITIVO", "FAVORABLE"]);
const BAD = new Set(["ALTO", "NEGATIVO", "REQUIERE REVISIÓN"]);

export const tone = (v) => (GOOD.has(v) ? "pos" : BAD.has(v) ? "neg" : "warn");
export const tag = (v) => `<span class="tag ${tone(v)}">${v}</span>`;

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

export const clearScenario = () => localStorage.removeItem(SCENARIO_KEY);

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
  el.innerHTML = `<span class="err">${esc(e.message || e)}</span>`;
}

/** Barra de navegación, con la pantalla actual marcada. */
export function renderNav(active) {
  const screens = [
    ["/", "Datos"],
    ["/escenario", "Escenario"],
    ["/simulacion", "Simulación"],
    ["/jev", "Jev"],
  ];
  const nav = document.createElement("nav");
  nav.className = "screens";
  nav.innerHTML = screens
    .map(([href, label], i) => {
      const cur = href === active ? ' aria-current="page"' : "";
      return `<a href="${href}"${cur}><span class="step">${i + 1}</span>${esc(label)}</a>`;
    })
    .join("");
  document.querySelector("header.top")?.after(nav);
}