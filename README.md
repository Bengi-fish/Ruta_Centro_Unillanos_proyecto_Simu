# Ruta de buses Parque - Campus Barcelona (Unillanos)

Simulación de eventos discretos en **AnyLogic** de la ruta institucional de la Universidad de los Llanos entre el Parque de los Estudiantes, en el centro de Villavicencio, y el campus Barcelona, en ambos sentidos.

**Curso:** Simulación Computacional, Ingeniería de Sistemas, Universidad de los Llanos
**Docente:** Angel Alfonso Cruz Roa

| Integrante | Código |
|---|---|
| Johan Sebastián Forero Agudelo | 160005011 |
| Santiago Barrera Meza | 160005004 |
| Juan Diego Vélez González | 160005032 |

## Entregables

| Entregable | Archivo |
|---|---|
| Artículo (LNCS, 8 páginas) | [`articulo/Articulo_Ruta_Unillanos_LNCS.pdf`](articulo/Articulo_Ruta_Unillanos_LNCS.pdf) |
| Presentación (20 diapositivas) | [`presentacion/Presentacion_Ruta_Unillanos.pptx`](presentacion/Presentacion_Ruta_Unillanos.pptx) y su [PDF](presentacion/Presentacion_Ruta_Unillanos.pdf) |
| Modelo en AnyLogic con interfaz Demo | [`modelo_anylogic/RutaUnillanos_mapa.alp`](modelo_anylogic/RutaUnillanos_mapa.alp) |

## Estructura

```
articulo/            Fuente LaTeX (plantilla Springer LNCS), figuras y PDF del artículo
presentacion/        Diapositivas en PPTX y PDF
modelo_anylogic/     Modelo en AnyLogic PLE 8.9.10 y el mapa de fondo de la interfaz
datos/               Datos recolectados, datos derivados y fuentes (ver datos/README.md)
resultados/python/   Réplicas y resumen de los experimentos
simulacion_python/   Segunda implementación del modelo (SimPy) que produce los resultados y las figuras
```

## Modelo

- **Agentes:**
  - **Pasajero:** sigue el flujo Source → Wait → Sink.
  - **Bus:** se controla con un diagrama de estados (Libre, EnParada, EnTramo y Alistando).
  - **Main:** maneja los horarios, la demanda, el despacho y las estadísticas.
- **Operación:**
  - **Horarios:** en ambos sentidos sale un bus cada 20 min, de 5:20 a 22:00 (51 salidas por sentido).
  - **Salidas atrasadas:** si no hay bus libre, la salida sale tarde. No se cancela ni se une a la siguiente.
  - **Flota:** 5 buses de 41 puestos sentados, 51 en total. Al empezar el día la mitad (redondeada hacia arriba) está en el Parque y el resto en Barcelona. Cada bus alterna ida y vuelta, sin viajes vacíos.
- **Tiempos por tramo:** distribución triangular (mínimo, moda, máximo) según la franja horaria, con un factor de 1,1 para el bus. Las franjas son pico de la mañana, valle y pico de la tarde.
- **Demanda:** procesos de Poisson por franja. Es sintética, porque no hubo conteos de pasajeros.
- **Escenarios:**
  - **E1, operación actual:** 5 buses.
  - **E2, inicio de semestre:** 3 buses, 40 % más de demanda y 35 % más de tiempo en la vía al campus.

### Cómo abrir y correr el modelo

1. Abrir `modelo_anylogic/RutaUnillanos_mapa.alp` con AnyLogic PLE 8.9.10 o superior. La imagen `mapa_osm_ruta_unillanos.png` debe quedar en la misma carpeta.
2. Ejecutar el experimento **Actual** o **InicioSemestre**.
   - Para la demostración, usar tiempo real con escala ×60.
   - Para obtener resultados, usar tiempo virtual. La consola escribe una línea `dia;…` por cada día simulado. Cada día ocupa un bloque de 48 h para que terminen los viajes atrasados.

La edición PLE permite crear como máximo 50 000 agentes por corrida. Para tener 30 réplicas por escenario se corren 15 días con la semilla 1 y otros 15 con la semilla 2.

### Implementación en Python

```bash
cd simulacion_python
pip install -r requirements.txt
python modelo.py          # una réplica por escenario
python experimentos.py    # calibración, validación, 30 réplicas por escenario y figuras del artículo
```

`experimentos.py` guarda los resultados en `resultados/python/` y las figuras en `articulo/figuras/`.

## Resultados (media e IC 95 %, 30 réplicas por escenario)

Los resultados salen de la implementación en Python, que sigue las mismas reglas del modelo de AnyLogic.

| Medida | E1 Actual | E2 Inicio de semestre |
|---|---|---|
| Espera en parada (min) | 11,49 ± 0,13 | 58,69 ± 2,08 |
| Tiempo puerta a puerta (min) | 35,84 ± 0,15 | 87,63 ± 2,12 |
| Factor de ocupación medio | 0,325 ± 0,003 | 0,456 ± 0,004 |
| Retraso medio de salida (min) | 0,05 ± 0,01 | 190,4 ± 1,7 |
| Retraso máximo de salida (min) | 2,2 ± 0,3 | 382,3 ± 3,4 |

Con dos buses menos en temporada alta, el ciclo de cada bus supera el intervalo programado. Como ninguna salida se cancela, los retrasos se acumulan durante el día y la última salida parte de madrugada.

## Fuentes de datos

- **Paraderos:** afiche oficial *Rutas Unillanos, ruta Parque* (`datos/fuentes/`).
- **Horario de servicio:** lo precisó el grupo (ambos sentidos, cada 20 min, de 5:20 a 22:00).
- **Tiempos de conducción por tramo:** Google Maps, consultados con hora de salida 5:30, 10:00 y 17:30 en días hábiles.
- **Mapa de la interfaz:** © OpenStreetMap contributors.
