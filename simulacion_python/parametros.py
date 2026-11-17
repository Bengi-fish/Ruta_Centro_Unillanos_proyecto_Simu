"""Parámetros de entrada del modelo. Única fuente de verdad: datos/tiempos_tramo.csv
y datos/ruta_centro_paraderos.csv, más las reglas operativas entregadas por el grupo."""
import csv
from pathlib import Path

DATOS = Path(__file__).resolve().parent.parent / "datos" / "originales"

# --- Operación (afiche Rutas Unillanos y respuestas del grupo) -------------------
FLOTA = 5                 # buses asignados a la ruta Parque
CAP_SENTADOS = 41
CAP_TOTAL = 51            # sentados + de pie
FACTOR_BUS = 1.10         # bus vs. automóvil en movimiento (sin contar paradas)
ESPERA_TERMINAL = 5.0     # min de alistamiento en cada extremo
T_FIJO_PARADA = 10 / 60   # min: apertura/cierre de puertas
T_SUBIR = 3 / 60          # min por pasajero que aborda
T_BAJAR = 2 / 60          # min por pasajero que desciende
DELTA_CONSTANTE = 0.5     # ±min cuando el tramo tiene mín = máx

def hm(h, m=0):
    return h * 60 + m      # minutos desde la medianoche

# Ambos sentidos salen cada 20 min de 5:20 a. m. a 10:00 p. m. (51 salidas por sentido).
SALIDAS_IDA = [hm(5, 20) + 20 * k for k in range(51)]      # Parque: 5:20 … 22:00
SALIDAS_VUELTA = [hm(5, 20) + 20 * k for k in range(51)]   # Barcelona: 5:20 … 22:00
# Cada réplica dura 48 h (igual que en AnyLogic): el día de servicio más un margen para que
# los viajes atrasados terminen. Las llegadas de pasajeros solo ocurren el primer día.
FIN_SIM = hm(48)

# --- Franjas horarias (definidas por el grupo) ---------------------------------
def franja(t):
    if hm(5, 30) <= t < hm(7):   return "pico_am"
    if hm(11) <= t < hm(14):     return "pico_md"
    if hm(17, 30) <= t < hm(19): return "pico_pm"
    return "valle"

# Los tiempos medidos cubren pico_am, valle y pico_pm. Para el pico del mediodía
# se usan los tiempos de pico_pm (supuesto conservador: tráfico de hora de almuerzo).
FRANJA_TIEMPO = {"pico_am": "pico_am", "pico_md": "pico_pm", "pico_pm": "pico_pm", "valle": "valle"}

# --- Paraderos ---------------------------------------------------------------
def leer_paraderos():
    ida, vuelta = [], []
    with open(DATOS / "ruta_centro_paraderos.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            (ida if r["sentido"] == "ida" else vuelta).append(r["nombre"])
    return ida, vuelta

PARADAS_IDA, PARADAS_VUELTA = leer_paraderos()

# --- Tiempos de recorrido: triangular por tramo y franja ----------------------
def num(s):
    return float(s.replace(",", "."))

def leer_tramos():
    """{(sentido, tramo, franja): (a, c, b, prom, dist)} con la moda c = 3·prom − a − b."""
    T = {}
    with open(DATOS / "tiempos_tramo.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            a, b, prom = num(r["min_min"]), num(r["Max"]), num(r["min_prom"])
            if a == b:
                a, b = a - DELTA_CONSTANTE, b + DELTA_CONSTANTE
            c = min(max(3 * prom - a - b, a), b)
            T[(r["sentido"], int(r["tramo"]), r["franja"])] = (a, c, b, prom, num(r["distancia_km"]))
    return T

TRAMOS = leer_tramos()
TRAMOS_VIA_CAMPUS = {("ida", 8), ("vuelta", 1)}   # vía Puerto López al campus

# --- Demanda sintética (pasajeros/hora) ----------------------------------------
# No hay conteos de campo; el grupo autorizó generarla aleatoriamente. Se usan
# procesos de Poisson no homogéneos (tasa constante por franja), con semilla fija.
PESO_IDA = {"parque": .30, "unicentro": .15, "tecniguayas": .10, "frente_colegio_industrial": .10,
            "makro": .10, "alborada": .10, "universidad_cooperativa": .10, "eds_primax_ocoa": .05}
TASA_IDA = {"pico_am": 140, "pico_md": 90, "valle": 45, "pico_pm": 30}       # total de la ruta
TASA_VUELTA = {"pico_am": 0, "pico_md": 130, "valle": 45, "pico_pm": 150}    # en Barcelona
TASA_VUELTA_NOCHE = 30                                                       # después de las 19:00
TASA_IDA_NOCHE = 30                                                          # después de las 19:00
VENTANA_IDA = (hm(5), hm(21, 55))        # hasta 5 min antes de la última salida (22:00)
VENTANA_VUELTA = (hm(7, 40), hm(21, 55))
# Destino de quien aborda en Barcelona (solo se baja gente en la vuelta)
PROB_BAJA_VUELTA = {"universidad_cooperativa": .10, "alborada": .10, "makro": .10,
                    "frente_colegio_industrial": .10, "tecniguayas": .10, "unicentro": .15, "parque": .35}

# --- Escenarios ----------------------------------------------------------------
ESCENARIOS = {
    "actual": dict(flota=FLOTA, factor_demanda=1.0, factor_via_campus=1.0),
    # Inicio de semestre: alta demanda, 2 buses en mantenimiento y congestión en la vía al campus
    "inicio_semestre": dict(flota=FLOTA - 2, factor_demanda=1.4, factor_via_campus=1.35),
}
