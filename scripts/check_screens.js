import fs from "node:fs";
import path from "node:path";

/* Ejecuta la lógica de cada pantalla contra el servidor real, con un DOM mínimo.
 *
 * `node --check` solo valida sintaxis: no detecta un campo renombrado en la
 * respuesta de la API ni un `undefined` al pintar. Aquí sí se ejecuta el
 * render de verdad y se falla si algo lanza.
 */
const BASE = process.env.BASE || "http://127.0.0.1:8079";
const dir = "app/static";

/* --- DOM mínimo --- */
const registry = new Map();
function makeEl(id) {
  const el = {
    id,
    innerHTML: "",
    textContent: "",
    value: "",
    hidden: false,
    disabled: false,
    style: {},
    className: "",
    // `closest` debe devolver un elemento: las pantallas lo usan para tocar el
    // estilo de la etiqueta que envuelve a un input.
    closest: () => makeEl(`${id}:closest`),
    addEventListener: () => {},
    querySelector: () => null,
    after: () => {},
    /* El plano se pinta como nodo hijo, no como innerHTML: se anotan los hijos
     * para que `report` lo cuente como contenedor pintado. */
    appendChild: (c) => { el.children.push(c); return c; },
    children: [],
    dataset: {},
    /* `renderChrome` inserta cabecera y pie en el body, y las migas en el
       contenedor principal. Que no sea un throw es lo que importa aquí. */
    insertAdjacentHTML: (pos, html) => {
      el[`html_${pos}`] = html;
    },
  };
  return el;
}

globalThis.localStorage = {
  _d: {},
  getItem(k) { return this._d[k] ?? null; },
  setItem(k, v) { this._d[k] = String(v); },
  removeItem(k) { delete this._d[k]; },
};
globalThis.location = { href: "", search: "", replace: () => {} };

/* createElementNS + appendChild hacen falta para el SVG del mapa. */
const NS = "http://www.w3.org/2000/svg";
function appendTo(parent, child) {
  (parent.children || (parent.children = [])).push(child);
  return child;
}
globalThis.document = {
  body: makeEl("body"),
  _el: (id) => {
    if (!registry.has(id)) registry.set(id, makeEl(id));
    return registry.get(id);
  },
  getElementById: (id) => globalThis.document._el(id),
  createElement: (t) => makeEl(`<${t}>`),
  createElementNS: (ns, t) => {
    const el = makeEl(`<${t}>`);
    el.ns = ns;
    el.setAttribute = (k, v) => { el.attrs = { ...(el.attrs || {}), [k]: v }; };
    el.appendChild = (c) => appendTo(el, c);
    el.lastChild = null;
    return el;
  },
  querySelector: () => null,
};
/* `Connection: close` evita que el pool keep-alive de undici deje sockets a
 * medio cerrar: al salir del proceso, libuv aborta con un assertion en Windows. */
const nativeFetch = globalThis.fetch;
globalThis.fetch = (u, o = {}) =>
  nativeFetch(u.startsWith("http") ? u : BASE + u, {
    ...o,
    headers: { ...(o.headers || {}), Connection: "close" },
  });

/* `ui.js` es un módulo ES; aquí se inyecta su código en el temporal quitando
 * las palabras `export`/`import`, para que los helpers queden en el ámbito. */
const uiSrc = fs
  .readFileSync(path.join(dir, "ui.js"), "utf8")
  .replace(/^export /gm, "")
  .replace(/^import .*$/gm, "");
const mapSrc = fs
  .readFileSync(path.join(dir, "map.js"), "utf8")
  .replace(/^export /gm, "")
  .replace(/^import .*$/gm, "");

async function runScreen(file, seed) {
  const html = fs.readFileSync(path.join(dir, file), "utf8");
  const own = [...html.matchAll(/<script type="module">([\s\S]*?)<\/script>/g)]
    .map((m) => m[1]).join("\n");
  const js = uiSrc + "\n" + mapSrc + "\n" +
    own.replace(/import \{[^}]+\} from "\/static\/ui\.js";?/g, "")
       .replace(/import \{[^}]+\} from "\/static\/map\.js";?/g, "");

  if (seed) localStorage.setItem("mvp.scenario", JSON.stringify(seed));

  /* Se evalúa con `new Function` en vez de con `import()` de un temporal: cargar
     módulos dinámicos deja handles de libuv a medio cerrar y Node aborta con un
     assertion en Windows al salir del proceso. */
  try {
    const fn = new Function(`return (async () => {\n${js}\n})();`);
    await fn();
    return true;
  } catch (e) {
    console.log(`  ERROR en ${file}: ${e.message}`);
    return false;
  }
}

function report(file, ok, ids) {
  const vacios = ids.filter((id) => {
    const el = registry.get(id);
    if (!el) return true;
    // `textContent` puede haber recibido un número, no una cadena.
    return !String(el.innerHTML || "").trim() && !String(el.textContent || "").trim()
      && !el.children.length;
  });
  if (!ok) return;
  if (vacios.length) {
    console.log(`  AVISO ${file}: contenedores vacíos -> ${vacios.join(", ")}`);
  } else {
    console.log(`  OK   ${file}: ${ids.length} contenedores pintados`);
  }
}

const escenario = { street_id: "Gran Vía", action: "close", params: {} };
/* Se pasa escenario a las pantallas que arrancan desde uno guardado:
   escenario (para consultar la ficha) y las dos de resultado. */
const CON_ESCENARIO = new Set(["escenario.html", "simulacion.html", "jev.html"]);

console.log(`pantallas contra ${BASE}\n`);
let fallos = 0;

for (const [file, ids] of [
  ["index.html", ["flow", "quick"]],
  ["datos.html", ["mapa", "leyenda", "coverage", "rows", "cameras", "provenance", "traps", "rows-note"]],
  ["escenario.html", ["target", "effects", "neighbours", "resultados", "buscar-info", "total-calles", "con-datos"]],
  ["simulacion.html", ["kpis", "concentration", "impacts", "notes", "demo", "scenario", "kpi-note"]],
  ["jev.html", ["overall", "dimensions", "thresholds", "confidence", "alerts", "why", "scenario"]],
]) {
  const ok = await runScreen(file, CON_ESCENARIO.has(file) ? escenario : null);
  if (!ok) fallos++;
  report(file, ok, ids);
}

console.log(fallos ? `\n${fallos} pantalla(s) con error` : "\ntodas las pantallas renderizan");
/* Nada de process.exit(): cerrarlo a la fuerza con sockets de undici
 * pendientes hace que libuv aborte con un assertion en Windows. Basta con
 * fijar el código de salida y dejar que el proceso termine solo. */
process.exitCode = fallos ? 1 : 0;