# MVP — Laboratorio Urbano Digital: peatonalizar calles

Caso de uso acotado: **estimar qué pasa al pedestrianizar una calle.**
Ejemplo de demostración: **Bilbao**, Gran Vía de Don Diego López de Haro (Abando).

## Arranque

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\uvicorn app.main:app --reload
```

La primera petición descarga los datos de Bilbao Open Data y OpenStreetMap
(~30 s) y los cachea en `data/`. Las siguientes van a disco.

## Pantallas

Una por etapa del flujo. HTML plano y módulos ES nativos: **sin build, sin bundler**.

| Ruta | Pantalla | Qué muestra |
|---|---|---|
| `/datos` | Datos | Cobertura del feed, tráfico observado sección a sección, procedencia de cada magnitud, cámaras y trampas conocidas de los datos |
| `/escenario` | Escenario | Qué calle se interviene y con qué acción, ficha de la sección, efectos configurados, vecinas candidatas |
| `/simulacion` | Simulación | Los 6 KPIs, concentración del impacto, tabla de secciones afectadas, notas del modelo |
| `/jev` | Jev | Veredicto por dimensión, umbrales aplicados, confianza y alertas |

`/` redirige a `/datos`. El escenario se guarda en `localStorage`, así que se
puede recorrer el flujo entero sin repetir la petición.

- Docs interactivas: http://localhost:8000/docs
- Demo de un clic, dos escenarios ya evaluados: http://localhost:8000/demo

## Endpoints

| Ruta | Para qué |
|---|---|
| `GET /city` | Estado actual de la zona: dato real + magnitudes derivadas |
| `GET /traffic` | Tráfico por sección, con frescura y cobertura |
| `GET /cameras` | Puntos de observación del Ayuntamiento (**contexto, no medición**) |
| `POST /scenario` | Valida el escenario y muestra sus efectos configurados |
| `POST /simulate` | Aplica las reglas y devuelve los 6 KPIs |
| `POST /evaluate` | Pipeline completo: simula y clasifica con Jev |
| `GET /health` | Estado del servicio y de la caché |

```bash
curl -X POST localhost:8000/evaluate \
  -H "Content-Type: application/json" \
  -d '{"street_id":"328","action":"close"}'
```

`street_id` admite el `CodigoSeccion` del feed o parte del nombre
(`"Gran Via"`).

## Qué devuelve

Seis KPIs en porcentaje, con `baseline` y `simulated` para graficar:

| KPI | Origen |
|---|---|
| `traffic_change` | simulado |
| `emissions_change` | simulado |
| `travel_time_change` | simulado |
| `pedestrian_change` | porcentaje configurado |
| `commercial_activity_change` | **potencial**, no ventas |
| `accessibility_change` | índice ponderado por modo |

Y el veredicto de Jev: `traffic_risk`, `environmental_impact`,
`commercial_impact`, `accessibility_impact`, `overall_status`, `confidence`
y las alertas concretas.

## Datos

| Fuente | Uso |
|---|---|
| `bilbao.eus/aytoonline/srvDatasetTrafico` | intensidad, velocidad, ocupación por sección |
| `bilbao.eus/aytoonline/srvDatasetCamaras` | **solo contexto**: dónde se observa la calle |
| Overpass API (OSM) | nombres de calle, carriles, sentidos, límites de velocidad |

Licencia: CC BY 3.0 (Ayuntamiento de Bilbao). OSM: ODbL.

El feed de tráfico **no trae nombre de calle**: se resuelve uniendo por
proximidad con OSM. Se reportan la antigüedad y la cobertura de cada lectura.

### Sobre las cámaras

El feed `srvDatasetCamaras` se verificó en vivo y **no sirve para medir tráfico**:

- 119 cámaras en la ciudad, 12 dentro de la bbox de Abando.
- Sus únicos campos son identificación, nombre, posición y una `URL`. No hay
  intensidad, ni conteo, ni velocidad.
- Las instantáneas que promete el campo `URL` devuelven **404** (comprobado).

Por eso `/cameras` responde con `usable_for_simulation: false` y su
`limitation` explicada: solo sirve para **auditar la procedencia** del dato
(saber qué secciones tienen un punto de observación cercano y por tanto son
contrastables). No entra en ningún cálculo del motor.

## Estructura

```
app/
  main.py     API
  config.py   umbrales y parámetros del modelo (todo configurable)
  data.py     carga, caché, procedencia y unión con OSM
  engine.py   simulación por reglas
  jev.py      clasificación estructurada
  schemas.py  esquemas y contratos
  static/     las 4 pantallas + base.css + ui.js (sin build)
tests/        38 pruebas, sin red
scripts/      comprobaciones de las pantallas (requiere Node)
docs/         arquitectura y definición del reto
```

## Verificación

```bash
.venv\Scripts\python -m pytest -q    # 38 passed
.venv\Scripts\python -m ruff check .
node scripts\check_static.js        # ids e imports de las pantallas
node scripts\check_screens.js       # render real de las 4 pantallas (servidor en marcha)
```

## Límites conocidos

- El tráfico se redistribuye **por proximidad y capacidad**, no por conectividad real de cruces. Es una aproximación, no una asignación de viajes.
- Sin histórico no hay nada que aprender: no hay modelo predictivo, solo reglas.
- El 25 % de las secciones del feed llega con intensidad 0 (sensor apagado) y hay lecturas de hasta 2016.
- `Velocidad` en el feed tiene mediana de 1 km/h: no se usa como velocidad real.
- Comercio y peatones son índices de potencial configurados, no mediciones.
- Las emisiones **solo bajan si el tráfico sale de la zona**. Sin distancia de desvío real, repartir dentro de la zona se asume de recorrido neutro: si no, el reparto a calles más cortas produciría un ahorro ficticio.
- Si el tráfico desplazado no cabe en la zona, se declara como `displaced_outside_zone` y se pierde de vista: el impacto sobre el resto de Bilbao queda fuera del alcance.
- No hay mapa todavía. Las pantallas son tablas y KPIs; el mapa es la siguiente capa.

Nada de esto se presenta como predicción. Cada respuesta lleva `provenance`
(`REAL` / `DERIVADO` / `SIMULADO`) y el veredicto de Jev lleva un descargo.