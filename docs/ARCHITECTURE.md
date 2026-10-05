# Arquitectura MVP — Laboratorio Urbano Digital de Bilbao

## 1. Objetivo

MVP de una aplicación web que permite seleccionar una zona de Bilbao, crear una intervención urbana hipotética y estimar su impacto.

El sistema combina:

- Datos públicos.
- Un modelo simplificado de la ciudad.
- Reglas/simulación sencilla.
- Jev como capa de decisión y clasificación.
- IA generativa opcional para interpretar peticiones y explicar resultados.

El objetivo del MVP no es crear un gemelo digital completo, sino demostrar el flujo:

DATOS → ESCENARIO → SIMULACIÓN → JEV → RESULTADO

## Arquitectura
                 ┌──────────────┐
                 │    USUARIO   │
                 └──────┬───────┘
                        ↓
                 ┌──────────────┐
                 │   FRONTEND   │
                 │  Mapa + UI   │
                 └──────┬───────┘
                        ↓
                 ┌──────────────┐
                 │     API      │
                 └──────┬───────┘
                        ↓
        ┌───────────────┼───────────────┐
        ↓               ↓               ↓
     DATOS          SIMULACIÓN         JEV
     REALES         / REGLAS       DECISIÓN
        │               │               │
        └───────────────┼───────────────┘
                        ↓
                 ┌──────────────┐
                 │   RESULTADO  │
                 │ KPIs + riesgo│
                 └──────┬───────┘
                        ↓
                    USUARIO

## 3.Frontend

Frontend

Aplicación web sencilla.
Tecnologías:

* React / Next.js.
* MapLibre o Leaflet.
* Recharts / Chart.js para gráficos.

Pantallas principales:

1. MAPA
2. CREAR ESCENARIO
3. RESULTADOS
4. COMPARACIÓN

El mapa muestra:

* Calles.
* Tráfico.
* Zonas.
* Intervención seleccionada.
* Impactos del escenario.

## 4. Backend

Tecnología:

```python
Python + FastAPI
```

Responsabilidades:

* Obtener datos.
* Crear escenarios.
* Ejecutar simulaciones.
* Calcular KPIs.
* Enviar resultados a Jev.
* Devolver resultados al frontend.

Endpoints mínimos:
```
GET  /city
GET  /traffic
POST /scenario
POST /simulate
POST /evaluate
```

## 5. Datos

Usar solo los datos necesarios para el MVP:

- tráfico
- velocidad
- geometría de calles
- capacidad
- aparcamiento
- flujo peatonal
- emisiones
- actividad comercial

Fuentes:

- Bilbao Open Data
- Open Data Euskadi
- OpenStreetMap

Para el MVP, si las APIs requieren demasiado tiempo, descargar los datos y trabajar con JSON/CSV locales.

## 6. Modelo urbano

No implementar un gemelo digital completo.

Representar únicamente una zona de Bilbao y sus calles principales.

Cada calle puede tener:

- id
- nombre
- geometría
- tráfico
- capacidad
- velocidad
- emisiones
- flujo peatonal
- actividad comercial

## 7. Escenario

El usuario define una intervención sobre una calle o zona.

Ejemplo de estructura:

- street
- action
- start
- end

Acciones iniciales:

- close
- traffic_restriction
- bike_lane
- remove_parking
- speed_change

Para el MVP implementar solo 1 o 2 acciones.

## 8. Simulación

La simulación será sencilla y basada en reglas.

Ejemplo:

- Si una calle se cierra, su tráfico pasa a 0.
- Parte del tráfico desplazado se reparte entre calles adyacentes.
- Las emisiones se calculan a partir del tráfico y un factor de emisión.
- El flujo peatonal puede aumentar según la intervención.
- La actividad comercial puede variar mediante porcentajes configurados.

Ejemplo de resultado:

- Calle X: tráfico -100%
- Calle A: tráfico +15%
- Calle B: tráfico +10%
- Emisiones: -7%
- Peatones: +25%
- Actividad comercial: +8%

El objetivo es demostrar el funcionamiento del sistema, no conseguir una simulación científica completa.

## 9. KPIs

Calcular únicamente los indicadores necesarios:

- traffic_change
- emissions_change
- travel_time_change
- pedestrian_change
- commercial_activity_change
- accessibility_change

Para el MVP son suficientes 4 o 5 KPIs.

## 10. Jev

Jev será la capa de evaluación y decisión.

Recibirá los resultados estructurados de la simulación.

Ejemplo de entrada:

- traffic_change = +15%
- emissions_change = -7%
- commercial_activity_change = +8%
- accessibility_change = -3%

Jev devolverá una salida estructurada:

- traffic_risk = HIGH
- environmental_impact = POSITIVE
- commercial_impact = POSITIVE
- accessibility_impact = ACCEPTABLE
- overall_status = REVIEW_REQUIRED
- confidence = 0.87

Las reglas pueden ser:

- traffic_change > 15% → HIGH_TRAFFIC_RISK
- emissions_change < -5% → POSITIVE_ENVIRONMENTAL_IMPACT
- commercial_activity_change < -10% → COMMERCIAL_RISK
- accessibility_change < -10% → ACCESSIBILITY_RISK

Jev debe devolver decisiones estructuradas, no texto libre.

## 11. Flujo completo

1. El usuario selecciona una calle.
2. Selecciona una intervención.
3. El frontend envía el escenario a la API.
4. El backend obtiene el estado actual.
5. La simulación aplica las reglas.
6. Se calculan los KPIs.
7. Los KPIs se envían a Jev.
8. Jev clasifica el escenario.
9. El backend devuelve el resultado.
10. El frontend muestra los impactos y riesgos.

## 12. Resultado

La interfaz debe mostrar:

- intervención seleccionada
- cambios en KPIs
- mapa de impacto
- riesgos detectados
- clasificación de Jev
- nivel de confianza

Ejemplo:

ESCENARIO: CERRAR CALLE X

TRÁFICO +15% — RIESGO
EMISIONES -7% — POSITIVO
PEATONES +25% — POSITIVO
COMERCIO +8% — POSITIVO
ACCESIBILIDAD -3% — ACEPTABLE

JEV: REVISIÓN NECESARIA
RIESGO DE TRÁFICO: ALTO
IMPACTO AMBIENTAL: POSITIVO
CONFIANZA: 87%

## Stack MVP

Frontend:

- React o Next.js
- MapLibre o Leaflet

Backend:

- Python
- FastAPI

Datos:

- Bilbao Open Data
- Open Data Euskadi
- OpenStreetMap

Base de datos:

- PostgreSQL + PostGIS
- Para una demo de una hora puede sustituirse por JSON/CSV local.

Simulación:

- Python
- reglas simples

Evaluación:

- Jev

IA generativa:

- opcional

Deploy:

- Vercel para frontend
- Render o Railway para backend

## Arquitectura mínima

DATOS → ESCENARIO → SIMULACIÓN → JEV → RESULTADO

Frontend
↓
API
├── Datos
├── Simulación / reglas
└── Jev
↓
Resultados
↓
Frontend

## Prioridad del MVP

1. Una única zona.
2. Pocos datos.
3. Una intervención principal.
4. Simulación basada en reglas.
5. 4 o 5 KPIs.
6. Evaluación mediante Jev.
7. Mapa de impacto.

## No implementar en el MVP

- gemelo digital completo
- simulación avanzada de tráfico
- modelos complejos de machine learning
- toda la ciudad
- todos los sensores disponibles
- todas las intervenciones urbanas
- sistema autónomo de recomendaciones

## Idea central de la demo

Selecciono una intervención urbana → simulo sus consecuencias → Jev evalúa el escenario → visualizo riesgos y beneficios.
