# MVP — Laboratorio Urbano Digital: peatonalizar calles

Caso de uso acotado: **estimar qué pasa al pedestrianizar una calle.**
Ejemplo de demostración: **Bilbao**, Gran Vía de Don Diego López de Haro (Abando).

## Arranque

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\uvicorn app.main:app --reload
```

- Docs interactivas: http://localhost:8000/docs
- Demo de un clic, dos escenarios ya evaluados: http://localhost:8000/demo

La primera petición descarga los datos de Bilbao Open Data y OpenStreetMap
(~30 s) y los cachea en `data/`. Las siguientes van a disco.

## Endpoints

| Ruta | Para qué |
|---|---|
| `GET /city` | Estado actual de la zona: dato real + magnitudes derivadas |
| `GET /traffic` | Tráfico por sección, con frescura y cobertura |
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
| `bilbao.eus/aytoonline/srvDatasetCamaras` | cámaras de tráfico |
| Overpass API (OSM) | nombres de calle, carriles, sentidos, límites de velocidad |

Licencia: CC BY 3.0 (Ayuntamiento de Bilbao). OSM: ODbL.

El feed de tráfico **no trae nombre de calle**: se resuelve uniendo por
proximidad con OSM. Se reportan la antigüedad y la cobertura de cada lectura.

## Estructura

```
app/
  main.py     API
  config.py   umbrales y parámetros del modelo (todo configurable)
  data.py     carga, caché, procedencia y unión con OSM
  engine.py   simulación por reglas
  jev.py      clasificación estructurada
  schemas.py  esquemas y contratos
tests/        31 pruebas, sin red
docs/         arquitectura y definición del reto
```

## Verificación

```bash
.venv\Scripts\python -m pytest -q    # 31 passed
.venv\Scripts\python -m ruff check .
```

## Límites conocidos

- El tráfico se redistribuye **por proximidad y capacidad**, no por conectividad real de cruces. Es una aproximación, no una asignación de viajes.
- Sin histórico no hay nada que aprender: no hay modelo predictivo, solo reglas.
- El 25 % de las secciones del feed llega con intensidad 0 (sensor apagado) y hay lecturas de hasta 2016.
- `Velocidad` en el feed tiene mediana de 1 km/h: no se usa como velocidad real.
- Comercio y peatones son índices de potencial configurados, no mediciones.
- Si el tráfico desplazado no cabe en la zona, se declara como `displaced_outside_zone` y se pierde de vista: el impacto sobre el resto de Bilbao queda fuera del alcance.

Nada de esto se presenta como predicción. Cada respuesta lleva `provenance`
(`real` / `derived` / `simulated`) y el veredicto de Jev lleva un descargo.