# Datos del proyecto

Esta carpeta reúne los datos que recolectamos y los que derivamos para alimentar el modelo.

## `originales/`: datos recolectados por el grupo

Son la única fuente de verdad del modelo. No se editan.

| Archivo | Contenido | Cómo se obtuvo |
|---|---|---|
| `ruta_centro_paraderos.csv` | Paraderos de ida (9) y de vuelta (8) en orden, con latitud y longitud en grados, minutos y segundos | Ubicamos en el mapa cada paradero del afiche oficial |
| `tiempos_tramo.csv` | Para cada tramo (8 de ida y 7 de vuelta) y cada franja: distancia, tiempo promedio, mínimo y máximo, en minutos | Google Maps, ruta en carro con «Salir a las» 5:30, 10:00 y 17:30 en días hábiles de una semana |

## `procesados/`: datos derivados que usa el modelo

Se generan a partir de los originales y de las reglas de operación. El código está en `simulacion_python/parametros.py`.

| Archivo | Contenido |
|---|---|
| `paraderos_decimal.csv` | Coordenadas de los paraderos en grados decimales. Se usaron para ubicarlos sobre el mapa de la demostración |
| `tramos_triangular.csv` | Parámetros de la distribución triangular por tramo y franja (mínimo, moda, máximo), en carro y con el factor de 1,1 del bus. Moda = 3·promedio − mínimo − máximo. Cuando mínimo = máximo, se abre ±0,5 min |
| `horarios_salidas.csv` | Las 102 salidas programadas por día: 51 de ida y 51 de vuelta, cada 20 min de 5:20 a 22:00 |
| `parametros_operacion.csv` | Flota, capacidades, tiempos de detención, alistamiento y factores de los escenarios, cada uno con su fuente |
| `demanda_tasas.csv` | Tasas de llegada de pasajeros por sentido y franja (pasajeros por hora) |
| `demanda_reparto.csv` | Probabilidad de origen por paradero en la ida y de destino en la vuelta |

**Sobre la demanda:** no hicimos conteos de pasajeros. Las tasas y repartos son **sintéticos**: supuestos plausibles que generan las llegadas mediante procesos de Poisson.

## `fuentes/`

- `afiche_rutas_unillanos.png`: afiche oficial de la ruta Parque. Es la fuente de la lista de paraderos. El horario de servicio (5:20 a 22:00 en ambos sentidos) lo precisó el grupo.

## Franjas horarias

| Franja | Horario | Tiempo de recorrido usado |
|---|---|---|
| Pico mañana | 5:30 a 7:00 | Consulta de las 5:30 |
| Pico mediodía | 11:00 a 14:00 | Consulta de las 17:30 (no se midió el mediodía, así que se usa el tráfico más alto medido) |
| Pico tarde | 17:30 a 19:00 | Consulta de las 17:30 |
| Valle | Resto del día | Consulta de las 10:00 |
