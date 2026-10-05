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
    appendChild: () => {},
    dataset: {},
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
globalThis.document = {
  _el: (id) => {
    if (!registry.has(id)) registry.set(id, makeEl(id));
    return registry.get(id);
  },
  getElementById: (id) => globalThis.document._el(id),
  createElement: (t) => makeEl(`<${t}>`),
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

async function runScreen(file, seed) {
  const html = fs.readFileSync(path.join(dir, file), "utf8");
  const own = [...html.matchAll(/<script type="module">([\s\S]*?)<\/script>/g)]
    .map((m) => m[1]).join("\n");
  const js = uiSrc + "\n" + own.replace(/import \{[^}]+\} from "\/static\/ui\.js";?/g, "");

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
    return el && !el.innerHTML.trim() && !el.textContent.trim();
  });
  if (!ok) return;
  if (vacios.length) {
    console.log(`  AVISO ${file}: contenedores vacíos -> ${vacios.join(", ")}`);
  } else {
    console.log(`  OK   ${file}: ${ids.length} contenedores pintados`);
  }
}

const escenario = { street_id: "Gran Vía", action: "close", params: {} };

console.log(`pantallas contra ${BASE}\n`);
let fallos = 0;

for (const [file, ids] of [
  ["datos.html", ["coverage", "rows", "cameras", "provenance", "traps", "rows-note"]],
  ["escenario.html", ["target", "effects", "neighbours", "chips"]],
  ["simulacion.html", ["kpis", "concentration", "impacts", "notes", "demo", "scenario", "kpi-note"]],
  ["jev.html", ["overall", "dimensions", "thresholds", "confidence", "alerts", "why", "scenario"]],
]) {
  const ok = await runScreen(file, file === "simulacion.html" || file === "jev.html" ? escenario : null);
  if (!ok) fallos++;
  report(file, ok, ids);
}

console.log(fallos ? `\n${fallos} pantalla(s) con error` : "\ntodas las pantallas renderizan");
/* Nada de process.exit(): cerrarlo a la fuerza con sockets de undici
 * pendientes hace que libuv aborte con un assertion en Windows. Basta con
 * fijar el código de salida y dejar que el proceso termine solo. */
process.exitCode = fallos ? 1 : 0;