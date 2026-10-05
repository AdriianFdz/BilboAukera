/* Renderiza el mapa de verdad y comprueba la geometría del SVG.
 *
 * El mapa se inserta como nodo hijo, no como innerHTML, así que
 * check_screens.js no lo ve. Aquí se ejecuta map.js contra los datos reales
 * y se verifican los polígonos y las cámaras que produce.
 */
import fs from "node:fs";
import path from "node:path";

const BASE = process.env.BASE || "http://127.0.0.1:8081";
const dir = "app/static";

/* --- DOM mínimo con soporte de SVG --- */
const NS = "http://www.w3.org/2000/svg";
const hojas = [];
function nuevo(t) {
  return {
    tag: t,
    attrs: {},
    children: [],
    texto: "",
    setAttribute(k, v) { this.attrs[k] = v; },
    appendChild(c) { this.children.push(c); return c; },
    addEventListener() {},
    get lastChild() { return this.children[this.children.length - 1]; },
    set textContent(v) { this.texto = v; },
    get textContent() { return this.texto; },
  };
}
globalThis.document = {
  createElement: (t) => nuevo(t),
  createElementNS: (ns, t) => nuevo(t),
  getElementById: () => nuevo("div"),
  querySelector: () => null,
};

const mapSrc = fs
  .readFileSync(path.join(dir, "map.js"), "utf8")
  .replace(/^export /gm, "")
  .replace(/^import .*$/gm, "");

// eslint-disable-next-line no-new-func
new Function(`${mapSrc}\nreturn renderMap;`)();

const city = await (await fetch(BASE + "/city")).json();
const cams = await (await fetch(BASE + "/cameras")).json();
const renderMap = new Function(`${mapSrc}\nreturn renderMap;`)();

const svg = renderMap({
  sections: city.sections,
  cameras: cams.cameras,
  bbox: city.bbox,
  targetId: "328",
  onSelect: () => {},
});

const polys = svg.children.filter((c) => c.tag === "polygon");
const paths = svg.children.filter((c) => c.tag === "g");
const textos = svg.children.filter((c) => c.tag === "text");

const W = 620;
const H = 380;
let fueraDeVista = 0;
for (const p of polys) {
  for (const par of p.attrs.points.split(" ")) {
    const [x, y] = par.split(",").map(Number);
    if (x < 0 || x > W || y < 0 || y > H) fueraDeVista++;
  }
}

console.log(`polígonos de sección: ${polys.length} (esperados ${city.sections.length})`);
console.log(`marcadores de cámara:  ${paths.length} (esperados ${cams.cameras.length})`);
console.log(`etiquetas:             ${textos.length}`);
console.log(`puntos fuera del lienzo: ${fueraDeVista}`);
console.log(`viewBox: ${svg.attrs.viewBox}`);
console.log(`el primero tiene ${polys[0].children.length} <title>`);

const fallos = [];
if (polys.length !== city.sections.length) fallos.push("faltan polígonos");
if (paths.length !== cams.cameras.length) fallos.push("faltan cámaras");
if (fueraDeVista > 0) fallos.push(`${fueraDeVista} puntos fuera del lienzo`);
if (!textos.some((t) => t.texto.includes("Gran"))) fallos.push("falta la etiqueta del objetivo");

console.log(fallos.length ? `\nFALLO: ${fallos.join(", ")}` : "\ngeometría del mapa correcta");
process.exitCode = fallos.length ? 1 : 0;