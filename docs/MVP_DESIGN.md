# MVP — Laboratorio Urbano Digital de Bilbao

Diseño acotado. Objetivo: demostrar el flujo completo
`DATOS → ESCENARIO → SIMULACIÓN → JEV → RESULTADO` en una sola zona.

---

## 1. Decisiones de alcance (lo que entra y lo que no)

| Entra | No entra |
|---|---|
| Una zona: **Abando / Indautxu** | Toda la ciudad |
| 2 acciones de simulación + 3 trivialmente derivables | 8 tipos de intervención |
| Reglas deterministas | ML, gemelo digital, simulacióncientífica |
| JSON en disco (cache) | PostgreSQL/PostGIS, Alembic |
| Jev = clasificador por reglas | LLM obligatoria |

La base de datos se deja fuera a propósito: `ARCHITECTURE.md` §5 lo autoriza
("puede sustituirse por JSON/CSV local"). Sin DB el MVP arranca en segundos y
todo el esfuerzo va en lo que se demuestra.

## 2. Arquitectura

```
USUARIO → FRONTEND (mapa) → API FastAPI
                              ├─ data.py    : carga + cache + procedencia
                              ├─ engine.py  : simulación por reglas
                              └─ jev.py     : evaluación estructurada
```

El frontend son cinco pantallas HTML en `app/static`, servidas por FastAPI, con
módulos ES nativos y sin paso de compilación. El plano es un SVG dibujado en el
navegador con la geometría real de las secciones (`map.js`), a propósito, para no
depender de un CDN al verlo. El React/MapLibre del documento sigue siendo la
capa siguiente, no un requisito para validar la hipótesis.

## 3. Datos reales y sus trampas

Verificado contra las fuentes el 2026-10-05:

| Fuente | URL | Estado |
|---|---|---|
| Tráfico | `bilbao.eus/aytoonline/srvDatasetTrafico?formato=geojson` | 81 secciones, `CodigoSeccion`/`Ocupacion`/`Intensidad`/`Velocidad`/`FechaHora` |
| Cámaras | `bilbao.eus/aytoonline/srvDatasetCamaras?formato=geojson` | 200 OK, pero el servicio de instantáneas `camarastrafico` devuelve 404 |
| Red viaria | Overpass API (`overpass-api.de/api/interpreter`) | nombres, `lanes`, `oneway`, `maxspeed` |
| Calles | `data/calles.csv` (registro municipal, local) | 923 calles de Bilbao: código, nombre y tipo de vía |

**Trampas que el diseño tiene que absorber:**

1. `srvDatasetTrafico` **no trae nombre de calle**, solo `CodigoSeccion`.
   El nombre se resuelve uniendo por proximidad con OSM.
2. De 81 secciones, **21 no son de hoy**; la más antigua es de 2016.
   Se filtran por antigüedad y se marca la cobertura.
3. `Velocidad` tiene **mediana de 1 km/h**: no es utilizable como tal.
   Se usa como *severidad de congestión* relativa, no como velocidad real.
4. `Ocupacion` va de 0 a 51 sin unidad documentada. Se usa solo como ordinal.
5. El 25 % de las secciones tiene `Intensidad = 0` (sensores apagados).
6. Los nombres de OSM están en **euskera** ("kalea" = calle), y el registro
   municipal los da en castellano y en orden invertido
   (`LOPEZ DE HARO D. DIEGO` frente a `On Diego Lopez Haroko kale nagisia`).
   La unión con el registro municipal es por palabras compartidas, y cada calle
   declara si el enlace es `exact`, `probable` o `none`.
7. El campo `URL` de las cámaras promete instantáneas, pero el servicio
   `camarastrafico` está retirado: 404 para todas las cámaras, para todas las
   variantes de nombre de fichero y para la raíz del directorio. No hay foto que
   enseñar. En su lugar se muestra la lectura medida de la sección que la cámara
   vigila, que sí responde a cómo está la calle ahora mismo.

**Unidad de simulación = la sección de tráfico**, no la calle. Es la única que
tiene dato real medido, y sin dato real no hay con qué simular. Por eso el
selector ofrece las 923 calles del registro pero solo marca como simulables las
15 que enlazan con una sección medida.

Toda respuesta lleva `provenance`: `REAL` | `DERIVADO` | `SIMULADO`.
Ningún valor estimado se etiqueta como medición.

## 4. Endpoints

```
GET  /city              estado actual de la zona (real + derivado), con geometría
GET  /traffic           tráfico por sección, con frescura y cobertura
GET  /streets           923 calles de Bilbao, marcando las simulables
GET  /cameras           puntos de observación y lectura real de su sección
POST /scenario          valida y normaliza un escenario
POST /simulate          ejecuta reglas → KPIs
POST /evaluate          KPIs → veredicto estructurado de Jev
GET  /health            estado del servicio y de la cache
```

## 5. Modelo urbano

```python
Section   id, name, geom, centroid, intensity, velocity, occupancy,
          observed_at, is_fresh, name_source
Street    ← nombre resolvido por proximidad OSM
```

Derivados por sección: `capacity` (carriles × 1800 veh/h), `length_m`
(perímetro), `emissions_g`, `travel_time_s`.

## 6. Escenario

```python
Scenario(street_id, action, start, end, params)
action ∈ {close, traffic_restriction, bike_lane, remove_parking, speed_change}
```

## 7. Simulación (reglas, sin ML)

1. `close` → tráfico de la sección a 0.
2. Redistribución: el tráfico desplazado se reparte entre las secciones
   vecinas más próximas, proporcionalmente a su **capacidad libre**. Lo que
   no cabe se contabiliza como `displaced_outside_zone` y **se reporta**, no
   se descarta.
3. Emisiones = `veh/h × length_m × factor(velocidad)`. Menos tráfico, menos
   emisiones; pero solo si el tráfico no se desplaza dentro de la zona.
4. Velocidad → tiempo de desplazamiento (`length / velocidad_efectiva`).
5. Peatones: `base × (1 + pedestrian_gain)` si la acción es peatonal/bici.
6. Comercially: índice de **potencial** con porcentajes configurables.

## 8. KPIs (6)

`traffic_change`, `emissions_change`, `travel_time_change`,
`pedestrian_change`, `commercial_activity_change`, `accessibility_change`.

Todos en **%** respecto al estado actual. Se incluye `baseline` y `simulated`
para que el frontend pueda graficar sin recalcular.

## 9. Jev (capa de decisión)

Clasificador determinista. **Devuelve estructura, nunca texto libre.**

```python
JevVerdict(
  traffic_risk, environmental_impact, commercial_impact,
  accessibility_impact, overall_status, confidence, alerts
)
```

Reglas (umbrales en configuración, no hardcodeados):

| Condición | Salida |
|---|---|
| `traffic_change > +15%` | `traffic_risk = HIGH` |
| `emissions_change < -5%` | `environmental_impact = POSITIVE` |
| `commercial_activity_change < -10%` | `commercial_impact = NEGATIVE` |
| `accessibility_change < -10%` | `accessibility_impact = NEGATIVE` |
| ≥2维度 negativas | `overall_status = REVIEW_REQUIRED` |

`confidence` **baja** explícitamente si los datos son parciales, antiguos o
escasos. Un escenario sin datos no debe salir con confianza alta.

## 10. Qué hay que ver en la demo

Un caso: **cerrar al tráfico la Gran Vía de Don Diego López de Haro** y ver
cómo el tráfico se reparte, las emisiones bajan, la accesibilidad de coche
cae y Jev pide revisión.

---

## 11. Deuda consciente del MVP

- Sin base de datos: no hay histórico, así que no hay nada que aprender (§22 del doc largo queda fuera).
- Sin grafo de red: las secciones se spatially unen por proximidad, no por conectividad real de cruces. La redistribución es una aproximación por capacidad, no un asignación de viaje.
- Sin Perú: la capa OSM completa (Overpass) tarda; se cachea y se limita a la bbox.
- La velocidad real no existe en los datos; el modelo usa velocidad efectiva derivada.