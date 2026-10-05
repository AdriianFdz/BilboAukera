# Reto tecnológico: Simulación del impacto de decisiones urbanas en Bilbao

## 1. Problema

Las decisiones de planificación urbana pueden generar efectos interdependientes sobre la movilidad, la actividad económica y la sostenibilidad ambiental.

Una intervención sobre una calle o una zona de la ciudad puede modificar los flujos de tráfico, afectar a las rutas de transporte, cambiar la accesibilidad a los comercios y producir variaciones en las emisiones. Además, los efectos de una decisión pueden extenderse más allá del espacio directamente intervenido.

Por ejemplo, una decisión que reduzca el tráfico en una calle puede provocar que parte de los vehículos se desplacen hacia calles cercanas. Del mismo modo, una modificación del espacio destinado a vehículos puede afectar al flujo de peatones, a la accesibilidad de los comercios o al transporte público.

El problema es que resulta difícil anticipar estos efectos antes de implementar físicamente una intervención.

El reto consiste en diseñar una aplicación que permita utilizar datos reales de Bilbao y otras fuentes públicas para crear escenarios urbanos hipotéticos y simular cómo podrían cambiar diferentes indicadores de la ciudad.

La aplicación no pretende determinar automáticamente qué decisión debe tomar el Ayuntamiento, sino proporcionar una herramienta de apoyo a la decisión que permita comparar alternativas y comprender sus posibles consecuencias.

## 2. Objetivo del reto

Desarrollar un simulador urbano que permita responder a la pregunta:

"¿Qué pasaría si modificamos algún elemento del sistema urbano de Bilbao?"

El usuario podrá seleccionar una zona, modificar determinadas condiciones y comparar el escenario resultante con la situación actual.

La aplicación deberá permitir analizar, como mínimo, tres dimensiones:

- Movilidad.
- Actividad comercial.
- Impacto ambiental.

El objetivo no es construir una réplica exacta de la ciudad, sino desarrollar un modelo suficientemente realista que permita explorar diferentes escenarios y visualizar sus posibles efectos.

## 3. Usuario objetivo

### Usuario principal

Técnicos y responsables del Ayuntamiento de Bilbao relacionados con:

- Movilidad.
- Urbanismo.
- Medio ambiente.
- Sostenibilidad.
- Comercio.
- Planificación urbana.

### Necesidad del usuario

Estos usuarios necesitan evaluar las posibles consecuencias de diferentes decisiones urbanas antes de implementarlas.

La herramienta les permitiría plantear preguntas como:

- ¿Qué ocurre con el tráfico si modificamos la circulación de una zona?
- ¿Cómo se redistribuyen los vehículos si restringimos el acceso a una calle?
- ¿Cómo pueden cambiar las emisiones?
- ¿Qué zonas pueden experimentar un aumento o disminución del tráfico?
- ¿Cómo puede verse afectada la actividad comercial?
- ¿Qué diferencias existen entre varias alternativas posibles?
- ¿Qué efectos secundarios puede generar una intervención?

La necesidad principal es disponer de una herramienta que permita pasar de analizar una intervención de forma aislada a comprender sus posibles efectos sobre el sistema urbano.

## 4. Casos de uso

### Caso de uso 1: Peatonalización de una calle

El Ayuntamiento estudia peatonalizar una calle determinada.

El usuario introduce la intervención en la aplicación y compara la situación actual con el escenario propuesto.

La aplicación estima:

- Cambio en el tráfico de la calle.
- Redistribución del tráfico hacia calles cercanas.
- Variación estimada de emisiones.
- Cambio en los flujos peatonales.
- Posible impacto sobre la actividad comercial.

Este caso sirve como ejemplo de cómo una decisión localizada puede producir efectos en diferentes variables y zonas.

### Caso de uso 2: Creación de un carril bici

El Ayuntamiento quiere transformar parte del espacio destinado actualmente a vehículos para crear un carril bici.

El usuario introduce la modificación y analiza:

- Cambios en el flujo de vehículos.
- Posible redistribución del tráfico.
- Cambios en los desplazamientos en bicicleta.
- Impacto estimado sobre las emisiones.
- Efectos sobre la accesibilidad de la zona.

### Caso de uso 3: Eliminación de plazas de aparcamiento

El Ayuntamiento plantea eliminar parte de las plazas de aparcamiento de una zona para recuperar espacio público.

La aplicación permite analizar:

- Posible aumento de vehículos buscando aparcamiento.
- Cambios en el tráfico.
- Variación de los tiempos de desplazamiento.
- Impacto sobre las emisiones.
- Cambios en la accesibilidad de comercios y servicios.

### Caso de uso 4: Modificación del transporte público

Se plantea modificar el recorrido o las frecuencias de una línea de transporte público.

La aplicación permite comparar:

- Accesibilidad antes y después.
- Cambios en los desplazamientos.
- Posible transferencia de viajes entre transporte público y vehículo privado.
- Impacto estimado sobre tráfico y emisiones.
- Zonas que pueden quedar mejor o peor conectadas.

### Caso de uso 5: Restricción de acceso a una zona

El Ayuntamiento plantea restringir el acceso de determinados vehículos a una zona urbana.

La aplicación permite estudiar:

- Reducción del tráfico dentro de la zona.
- Redistribución de vehículos en las calles colindantes.
- Cambios en las emisiones.
- Accesibilidad de residentes y comerciantes.
- Posibles efectos sobre la actividad económica.

## 5. Contexto urbano

### Ciudad

Bilbao, Bizkaia.

Bilbao constituye un entorno adecuado para este reto porque combina una elevada densidad urbana con diferentes formas de movilidad, transporte público, actividad comercial, turismo y diferentes niveles de tráfico y accesibilidad.

El proyecto utilizará Bilbao como entorno de referencia y podrá seleccionar posteriormente una zona concreta para desarrollar y validar el prototipo.

### Posibles zonas de estudio

Algunas zonas que podrían utilizarse como escenario de prueba son:

- Casco Viejo.
- Abando.
- Indautxu.
- Bilbao La Vieja.
- Arenal.
- Entorno de la Gran Vía.

La selección definitiva dependerá de la disponibilidad y calidad de los datos necesarios para la simulación.

## 6. Actores implicados

### Ayuntamiento de Bilbao

Es el usuario principal de la herramienta y el responsable de planificar y evaluar diferentes intervenciones urbanas.

### Residentes

Pueden verse afectados por cambios en:

- Accesibilidad.
- Tráfico.
- Ruido.
- Calidad ambiental.
- Espacio público.

### Comerciantes

Pueden verse afectados por cambios en:

- Flujo de peatones.
- Accesibilidad.
- Tráfico.
- Carga y descarga.
- Visibilidad y accesibilidad de los establecimientos.

### Peatones

Pueden experimentar cambios en:

- Seguridad.
- Accesibilidad.
- Calidad del espacio público.
- Conectividad entre zonas.

### Conductores

Pueden verse afectados por:

- Cambios en las rutas.
- Tiempos de desplazamiento.
- Restricciones de acceso.
- Disponibilidad de aparcamiento.

### Usuarios del transporte público

Pueden verse afectados por modificaciones en:

- Recorridos.
- Frecuencias.
- Tiempos de viaje.
- Accesibilidad.

### Servicios de logística y reparto

Necesitan mantener el acceso a las zonas comerciales y residenciales para realizar operaciones de carga y descarga.

### Servicios de emergencia

Las intervenciones urbanas deben garantizar que ambulancias, bomberos y otros servicios puedan acceder a las zonas afectadas.

## 7. Fuentes de datos

Una parte fundamental del proyecto será utilizar datos reales para construir el estado inicial de la ciudad.

Se podrán utilizar APIs y datasets públicos, dando prioridad a las fuentes oficiales de Bilbao y Euskadi.

### Bilbao Open Data

Bilbao dispone de un portal de datos abiertos con diferentes conjuntos de datos relacionados con la ciudad.

Entre las fuentes de interés para el proyecto se encuentran datos relacionados con:

- Tráfico.
- Cámaras de tráfico.
- Aparcamientos.
- Transporte.
- Obras.
- Urbanismo.
- Medio ambiente.
- Información geográfica.
- Actividad económica.

Bilbao también dispone de GeoBilbao, un geoportal que integra diferentes capas urbanas, entre ellas información sobre ocupación de aparcamientos, cámaras de tráfico, obras, medios de transporte y estado del tráfico.

Estas fuentes pueden utilizarse para construir una representación del estado actual de la ciudad.

### Open Data Euskadi

Open Data Euskadi proporciona APIs y datasets que pueden complementar la información de Bilbao.

Especialmente relevante es la API de tráfico, que proporciona información sobre:

- Cámaras de tráfico.
- Incidencias.
- Densidad de tráfico.

La API integra información procedente del Gobierno Vasco, Diputaciones Forales y los ayuntamientos de las tres capitales vascas.

También existen datos de aforos y densidad de tráfico que pueden utilizarse para caracterizar los flujos de vehículos.

### Otras fuentes públicas

El proyecto podrá utilizar otras APIs o fuentes públicas cuando sean necesarias.

Algunas posibilidades son:

- OpenStreetMap para la red viaria y características de las calles.
- Eustat para datos estadísticos y demográficos.
- Datos meteorológicos de Euskalmet.
- Datos públicos de transporte.
- Datos públicos de calidad ambiental.
- Otras fuentes abiertas relacionadas con comercio, movilidad o actividad urbana.

La selección definitiva de fuentes dependerá de las variables necesarias para construir el modelo de simulación.

## 8. Datos reales frente a datos simulados

El proyecto diferenciará entre:

### Datos reales

Datos obtenidos de APIs y fuentes públicas que representan el estado actual o histórico de Bilbao.

Ejemplos:

- Tráfico observado.
- Localización de calles.
- Aparcamientos.
- Transporte público.
- Incidencias.
- Localización de comercios.
- Datos demográficos.

### Datos derivados

Información calculada a partir de los datos reales.

Ejemplos:

- Intensidad de tráfico por zona.
- Nivel de accesibilidad.
- Densidad comercial.
- Emisiones estimadas a partir del tráfico.
- Flujo potencial de usuarios.

### Datos simulados

Resultados generados por el modelo al modificar las condiciones actuales.

Ejemplos:

- Tráfico después de cerrar una calle.
- Redistribución de vehículos.
- Variación de emisiones.
- Cambio estimado del flujo peatonal.
- Variación potencial de accesibilidad comercial.

Esta diferenciación permitirá mostrar claramente qué información procede de datos reales y qué información corresponde a una simulación.

## 9. Variables principales de la simulación

La aplicación debería centrarse inicialmente en tres grandes dimensiones.

### Movilidad

- Volumen de tráfico.
- Distribución del tráfico.
- Velocidad media.
- Tiempo de desplazamiento.
- Flujos peatonales.
- Uso de bicicleta.
- Transporte público.
- Accesibilidad.
- Ocupación de aparcamientos.

### Actividad comercial

- Número y distribución de comercios.
- Densidad comercial.
- Flujo peatonal.
- Accesibilidad a los comercios.
- Acceso de vehículos de reparto.
- Actividad comercial estimada.

La actividad comercial deberá tratarse como una estimación o indicador indirecto cuando no existan datos económicos suficientemente detallados.

### Medio ambiente

- Emisiones estimadas de CO2.
- Emisiones estimadas de NOx.
- Partículas contaminantes, cuando existan datos suficientes.
- Ruido, si existen datos disponibles para la zona.
- Calidad ambiental.

## 10. Funcionamiento de la aplicación

La aplicación funcionará como un laboratorio urbano.

### Paso 1: Seleccionar zona

El usuario selecciona una zona, calle o conjunto de calles de Bilbao.

### Paso 2: Consultar situación actual

La aplicación muestra los datos disponibles sobre la situación actual:

- Tráfico.
- Transporte.
- Aparcamiento.
- Comercio.
- Medio ambiente.
- Características urbanas.

### Paso 3: Definir una intervención

El usuario modifica virtualmente alguna característica del entorno.

Por ejemplo:

- Peatonalizar una calle.
- Cambiar el sentido de circulación.
- Crear un carril bici.
- Eliminar plazas de aparcamiento.
- Modificar una línea de transporte público.
- Restringir el acceso a determinados vehículos.
- Cambiar los horarios de carga y descarga.

### Paso 4: Ejecutar simulación

El sistema utiliza los datos actuales y un modelo de simulación para estimar cómo podría cambiar el comportamiento del sistema urbano.

### Paso 5: Comparar escenarios

La aplicación compara:

- Situación actual.
- Escenario simulado.
- Diferencia entre ambos.

### Paso 6: Visualizar resultados

Los resultados pueden mostrarse mediante:

- Mapa interactivo.
- Indicadores.
- Gráficos.
- Flujos de tráfico.
- Zonas afectadas.
- Cambios en emisiones.
- Cambios en accesibilidad.
- Indicadores relacionados con la actividad comercial.

## 11. Arquitectura conceptual

El funcionamiento general de la solución puede representarse como:

DATOS REALES DE BILBAO
        ↓
CAPA DE DATOS
        ↓
REPRESENTACIÓN DEL ESTADO ACTUAL
        ↓
USUARIO DEFINE UNA INTERVENCIÓN
        ↓
MODELO DE SIMULACIÓN
        ↓
ESCENARIO URBANO ALTERNATIVO
        ↓
COMPARACIÓN
        ↓
┌─────────────────┬─────────────────┬─────────────────┐
│     MOVILIDAD   │    COMERCIO     │   MEDIO AMBIENTE│
└─────────────────┴─────────────────┴─────────────────┘
        ↓
VISUALIZACIÓN DE RESULTADOS

## 12. Diferenciación respecto a las herramientas existentes

Bilbao ya dispone de herramientas como GeoBilbao que permiten visualizar diferentes capas de información urbana, incluyendo tráfico, aparcamientos, cámaras, obras y transporte.

Por tanto, el valor diferencial del proyecto no debe consistir simplemente en mostrar datos urbanos en un mapa.

La principal diferencia será pasar de una herramienta descriptiva a una herramienta de exploración de escenarios.

### Herramienta descriptiva

"¿Qué está pasando actualmente en Bilbao?"

### Herramienta propuesta

"¿Qué podría pasar si modificamos algo?"

La aplicación utilizará los datos actuales como punto de partida y permitirá experimentar virtualmente con diferentes decisiones urbanas.

## 13. Reto tecnológico

Diseñar y desarrollar un simulador urbano basado en datos reales que permita a los responsables municipales de Bilbao experimentar virtualmente con diferentes decisiones de planificación y visualizar sus posibles efectos sobre la movilidad, la actividad comercial y el medio ambiente.

El sistema deberá combinar:

- APIs públicas.
- Open Data de Bilbao.
- Open Data Euskadi.
- Datos geográficos.
- Datos de movilidad.
- Datos ambientales.
- Datos relacionados con la actividad urbana.
- Modelos de simulación.
- Visualización geoespacial.

## 14. Pregunta central del reto

¿Cómo podemos ayudar al Ayuntamiento de Bilbao a anticipar y comprender las consecuencias de diferentes decisiones urbanas antes de implementarlas?

## 15. Definición resumida

Las ciudades generan grandes cantidades de datos sobre movilidad, medio ambiente, transporte y actividad urbana. Sin embargo, disponer de estos datos no permite por sí solo conocer qué ocurrirá cuando se modifica algún elemento de la ciudad.

El reto consiste en transformar datos reales de Bilbao en una herramienta que permita experimentar con escenarios hipotéticos y estimar sus consecuencias.

La aplicación será un "laboratorio urbano digital" en el que el usuario pueda modificar virtualmente diferentes elementos de la ciudad y comparar el resultado con la situación actual.

La peatonalización de una calle será uno de los posibles casos de uso, pero no constituye el límite del problema.

El objetivo final es permitir explorar diferentes decisiones urbanas y comprender sus posibles efectos sobre el tráfico, la actividad comercial y las emisiones.