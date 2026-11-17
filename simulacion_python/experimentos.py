"""Diseño experimental: calibración del número de réplicas (entrenamiento), validación
contra los tiempos de Google Maps y corrida final de prueba con semillas independientes."""
import json
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

import parametros as P
from modelo import Ruta, resumen

RAIZ = Path(__file__).resolve().parent.parent
FIG, RES = RAIZ / "articulo" / "figuras", RAIZ / "resultados" / "python"
FIG.mkdir(parents=True, exist_ok=True); RES.mkdir(parents=True, exist_ok=True)
COLOR = {"actual": "#2a78d6", "inicio_semestre": "#eb6834"}
NOMBRE = {"actual": "Operación actual", "inicio_semestre": "Inicio de semestre"}
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8.5, "axes.edgecolor": MUTED,
                     "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                     "grid.color": GRID, "grid.linewidth": .6, "axes.axisbelow": True,
                     "legend.frameon": False, "savefig.dpi": 300, "savefig.bbox": "tight"})


def ic(x, conf=.95):
    x = np.asarray(x, float); n = len(x)
    h = stats.t.ppf((1 + conf) / 2, n - 1) * x.std(ddof=1) / np.sqrt(n)
    return x.mean(), h


# 1) Entrenamiento: réplicas piloto para fijar n (error relativo ≤ 5 % en la espera media)
def replicas_necesarias(n0=10, gamma=.05):
    out = {}
    for esc in P.ESCENARIOS:
        e = [resumen(Ruta(esc, 100 + s).correr())["espera_prom"] for s in range(n0)]
        m, h = ic(e)
        n = int(np.ceil(n0 * (h / (gamma * m)) ** 2))
        out[esc] = dict(n0=n0, media=m, semiancho=h, n_requerido=max(n, n0))
    return out


# 2) Validación: el tiempo en movimiento simulado (÷1,1) debe reproducir los tiempos de
#    Google Maps por franja; el tiempo detenido en paradas se reporta aparte.
def validacion(semillas=range(200, 230)):
    sim = defaultdict(list)
    for s in semillas:
        r = Ruta("actual", s).correr()
        for sentido, f, mov, det, n in r.viajes:
            sim[(sentido, P.FRANJA_TIEMPO[f])].append((mov / P.FACTOR_BUS, det, mov + det))
    filas = []
    for (sentido, f), v in sorted(sim.items()):
        n = 8 if sentido == "ida" else 7
        ref = sum(P.TRAMOS[(sentido, k, f)][3] for k in range(1, n + 1))
        v = np.array(v)
        m, h = ic(v[:, 0])
        filas.append(dict(sentido=sentido, franja=f, google=ref, sim_mov=m, ic=h, n=len(v),
                          diferencia_pct=100 * (m - ref) / ref, detenido=v[:, 1].mean(), total=v[:, 2].mean()))
    return filas


# 3) Prueba: corrida final con números aleatorios comunes
def prueba(n):
    filas, detalle = [], {}
    for esc in P.ESCENARIOS:
        for s in range(1000, 1000 + n):
            r = Ruta(esc, s).correr()
            filas.append(dict(escenario=esc, semilla=s, **resumen(r)))
            if s == 1000:
                detalle[esc] = r
    return filas, detalle


def tabla(filas, n):
    met = ["espera_prom", "espera_ida", "espera_vuelta", "puerta_puerta_prom", "puerta_puerta_ida",
           "puerta_puerta_vuelta", "ocupacion_prom", "tramos_sobre_sentados", "retraso_salida_prom",
           "retraso_salida_max", "sin_servicio", "pasajeros"]
    T = {}
    for m in met:
        a = [f[m] for f in filas if f["escenario"] == "actual"]
        b = [f[m] for f in filas if f["escenario"] == "inicio_semestre"]
        d = np.subtract(b, a)
        t, p = stats.ttest_rel(b, a) if np.std(d) > 0 else (np.nan, np.nan)
        T[m] = dict(actual=ic(a), inicio_semestre=ic(b), dif=ic(d), p=p)
    return T


# ------------------------------------------------------------------ figuras
def fig_entrada():
    """Datos de entrada: triangulares de la vía al campus y tiempo total por franja."""
    fig, axs = plt.subplots(1, 3, figsize=(6.8, 2.3), gridspec_kw=dict(width_ratios=[1, 1, 1.05]))
    tonos = {"pico_am": "#2a78d6", "valle": "#1baf7a", "pico_pm": "#eb6834"}
    nombres = {"pico_am": "Pico 5:30", "valle": "Valle 10:00", "pico_pm": "Pico 17:30"}
    for ax, (sent, tr, tit) in zip(axs[:2], [("ida", 8, "Ida · EDS Ocoa → Barcelona"),
                                             ("vuelta", 1, "Vuelta · Barcelona → U. Coop.")]):
        for f in ("pico_am", "valle", "pico_pm"):
            a, c, b, *_ = P.TRAMOS[(sent, tr, f)]
            x = np.linspace(a - .5, b + .5, 400)
            ax.plot(x, stats.triang.pdf(x, (c - a) / (b - a), loc=a, scale=b - a), lw=2,
                    color=tonos[f], label=nombres[f])
        ax.set_title(tit, fontsize=8.5, loc="left", color=INK)
        ax.set_xlabel("Minutos en automóvil")
    axs[0].set_ylabel("Densidad")
    axs[1].legend(loc="upper right", fontsize=7)
    ax = axs[2]; fr = ["pico_am", "valle", "pico_pm"]; x = np.arange(3); w = .38
    for i, (s, n, col) in enumerate([("ida", 8, "#2a78d6"), ("vuelta", 7, "#eb6834")]):
        v = [sum(P.TRAMOS[(s, k, f)][3] for k in range(1, n + 1)) for f in fr]
        bars = ax.bar(x + (i - .5) * w, v, w * .92, color=col, label=s.capitalize())
        for bx, val in zip(bars, v):
            ax.text(bx.get_x() + bx.get_width() / 2, val + .5, f"{val:.1f}".replace(".", ","),
                    ha="center", fontsize=6.5, color=MUTED)
    ax.set_xticks(x, ["Pico\n5:30", "Valle\n10:00", "Pico\n17:30"]); ax.set_ylim(0, 38)
    ax.set_title("Recorrido completo (min)", fontsize=8.5, loc="left", color=INK)
    ax.legend(loc="upper left", fontsize=7, ncol=2)
    fig.tight_layout(w_pad=1.2)
    fig.savefig(FIG / "entrada.pdf"); plt.close(fig)


def fig_espera_hora(detalles_por_esc):
    fig, ax = plt.subplots(figsize=(6.6, 2.4))
    horas = np.arange(5, 22)
    for esc, reps in detalles_por_esc.items():
        prom = []
        for h in horas:
            v = [p.sube - p.llega for r in reps for p in r.pasajeros
                 if p.sube is not None and h * 60 <= p.llega < (h + 1) * 60]
            prom.append(np.mean(v) if v else np.nan)
        ax.plot(horas + .5, prom, lw=2, marker="o", ms=4, color=COLOR[esc], label=NOMBRE[esc])
    for a, b in [(5.5, 7), (11, 14), (17.5, 19)]:
        ax.axvspan(a, b, color="#f2f1ed", zorder=0)
    ax.set_xticks(horas, [f"{h}" for h in horas]); ax.set_xlim(5, 22)
    ax.set_xlabel("Hora de llegada del pasajero a la parada (sombreado: horas pico)")
    ax.set_ylabel("Espera media (min)")
    ax.legend(loc="upper left", fontsize=7.5)
    fig.savefig(FIG / "espera_por_hora.pdf"); plt.close(fig)


def fig_ocupacion(detalles_por_esc):
    fig, axs = plt.subplots(1, 2, figsize=(6.6, 2.4), sharey=True)
    for ax, s in zip(axs, ("ida", "vuelta")):
        n = 8 if s == "ida" else 7
        etiquetas = P.PARADAS_IDA if s == "ida" else P.PARADAS_VUELTA
        for esc, reps in detalles_por_esc.items():
            v = [np.mean([o[3] for r in reps for o in r.ocupacion if o[0] == s and o[1] == k
                          and o[2] != "valle"]) / P.CAP_SENTADOS for k in range(1, n + 1)]
            ax.plot(range(1, n + 1), v, lw=2, marker="o", ms=4, color=COLOR[esc], label=NOMBRE[esc])
        ax.axhline(1, color=MUTED, lw=1, ls="--")
        ax.text(n + .1, 1.02, "41 sentados", fontsize=7, color=MUTED, ha="right", va="bottom")
        abre = {"parque": "Parque", "unicentro": "Unic.", "tecniguayas": "Tecnig.", "frente_colegio_industrial": "C. Ind.",
                "makro": "Makro", "alborada": "Albor.", "universidad_cooperativa": "U. Coop.",
                "eds_primax_ocoa": "EDS", "barcelona": "Barc."}
        ax.set_xticks(range(1, n + 1), [abre[etiquetas[k - 1]] for k in range(1, n + 1)], rotation=40, fontsize=7)
        ax.set_title("Ida (sale de cada parada)" if s == "ida" else "Vuelta (sale de cada parada)",
                     fontsize=8.5, loc="left", color=INK)
    axs[0].set_ylabel("Factor de ocupación\n(horas pico)")
    axs[1].legend(loc="lower left", fontsize=7.5)
    fig.savefig(FIG / "ocupacion_tramo.pdf"); plt.close(fig)


if __name__ == "__main__":
    cal = replicas_necesarias()
    n = max(30, max(c["n_requerido"] for c in cal.values()))
    val = validacion()
    filas, _ = prueba(n)
    T = tabla(filas, n)
    det = {esc: [Ruta(esc, 1000 + s).correr() for s in range(10)] for esc in P.ESCENARIOS}
    fig_entrada(); fig_espera_hora(det); fig_ocupacion(det)
    import csv
    with open(RES / "replicas.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0])); w.writeheader(); w.writerows(filas)
    json.dump(dict(calibracion=cal, n=n, validacion=val,
                   tabla={k: {kk: (list(map(float, vv)) if isinstance(vv, tuple) else float(vv))
                              for kk, vv in v.items()} for k, v in T.items()}),
              open(RES / "resumen.json", "w"), indent=1, ensure_ascii=False)
    print(json.dumps(cal, indent=1)); print("n =", n)
    for v in val: print(v)
    for k, v in T.items():
        print(f"{k:24s} act {v['actual'][0]:8.2f}±{v['actual'][1]:.2f}  ini {v['inicio_semestre'][0]:8.2f}±{v['inicio_semestre'][1]:.2f}  p={v['p']:.2g}")
