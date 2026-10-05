/* Comprueba que cada $("id") que usa el JS exista en el HTML de su pantalla.
 * Fallo tipográfico en un id = error en runtime, no 500.
 */
const fs = require("fs");
const path = require("path");

const dir = "app/static";
const files = fs.readdirSync(dir).filter((f) => f.endsWith(".html"));
let fallos = 0;

for (const f of files) {
  const html = fs.readFileSync(path.join(dir, f), "utf8");

  const ids = new Set([...html.matchAll(/id="([^"]+)"/g)].map((m) => m[1]));
  const bloques = [...html.matchAll(/<script type="module">([\s\S]*?)<\/script>/g)];
  const js = bloques.map((m) => m[1]).join("\n");

  const usados = new Set([...js.matchAll(/\$\("([^"]+)"\)/g)].map((m) => m[1]));

  /* `#principal` no lo toca el JS de la pantalla: lo busca `renderChrome` en
     ui.js para insertar las migas de pan. */
  if (ids.has("principal")) usados.add("principal");

  const faltan = [...usados].filter((id) => !ids.has(id));
  // Los ids sin usar son solo informativos: pueden estar para el CSS o para
  // una siguiente iteración. Lo que rompe la pantalla es que falte uno.
  const huerfanos = [...ids].filter((id) => !usados.has(id));

  if (faltan.length) {
    console.log(`\nFALLO ${f}: faltan ids en el HTML: ${faltan.join(", ")}`);
    fallos++;
  } else {
    const extra = huerfanos.length ? `  (sin usar: ${huerfanos.join(", ")})` : "";
    console.log(`OK   ${f}  (${ids.size} ids, ${usados.size} usados)${extra}`);
  }
}

/* El JS compartido debe exportar todo lo que las pantallas importan.
 * Ojo: `export const $` empieza por un símbolo, no por \w, y las funciones
 * pueden llevar `async`, así que el patrón tiene que cubrir ambos casos.
 */
const ui = fs.readFileSync(path.join(dir, "ui.js"), "utf8");
const exportados = new Set(
  [...ui.matchAll(/export (?:async )?(?:const|function|let) ([\w$]+)/g)].map((m) => m[1]),
);
console.log("\nexportado por ui.js: " + [...exportados].sort().join(", "));

for (const f of files) {
  const html = fs.readFileSync(path.join(dir, f), "utf8");
  for (const m of html.matchAll(/import \{([^}]+)\} from "\/static\/ui\.js"/g)) {
    for (const nombre of m[1].split(",").map((s) => s.trim()).filter(Boolean)) {
      if (!exportados.has(nombre)) {
        console.log(`  FALLO: ${f} importa '${nombre}', que ui.js no exporta`);
        fallos++;
      }
    }
  }
}

process.exit(fallos ? 1 : 0);