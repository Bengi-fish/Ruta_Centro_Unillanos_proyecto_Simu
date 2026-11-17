"""Gemelo en Python (simpy) del modelo de eventos discretos construido en AnyLogic.
Sirve para verificar la lógica y comparar resultados; la lógica es la misma de la guía.
Reglas: ambos sentidos salen cada 20 min de 5:20 a 22:00; una salida sin bus disponible
sale tarde (no se cancela ni se fusiona); cada bus alterna ida y vuelta sin traslados vacíos."""
import numpy as np
import simpy
import parametros as P


class Pasajero:
    __slots__ = ("llega", "origen", "destino", "sube", "baja", "sentido")

    def __init__(self, llega, origen, destino, sentido):
        self.llega, self.origen, self.destino, self.sentido = llega, origen, destino, sentido
        self.sube = self.baja = None


class Ruta:
    def __init__(self, escenario="actual", semilla=1):
        cfg = P.ESCENARIOS[escenario]
        self.flota, self.fd, self.fv = cfg["flota"], cfg["factor_demanda"], cfg["factor_via_campus"]
        # Flujos aleatorios separados (números aleatorios comunes entre escenarios)
        ss = np.random.SeedSequence(semilla).spawn(3)
        self.rng_lleg, self.rng_viaje, self.rng_dest = (np.random.default_rng(s) for s in ss)
        self.env = simpy.Environment(initial_time=P.hm(4, 50))
        self.cola = {p: [] for p in P.PARADAS_IDA}            # ida: paraderos 1..8
        self.cola_campus = []                                   # vuelta: Barcelona
        self.libres = {"parque": simpy.Store(self.env), "barcelona": simpy.Store(self.env)}
        self.pasajeros, self.ocupacion, self.salidas = [], [], []
        self.viajes = []
        # Los buses amanecen repartidos: la mitad (redondeada hacia arriba) en el Parque y el resto en Barcelona.
        for b in range(self.flota):
            self.libres["parque" if b < (self.flota + 1) // 2 else "barcelona"].put(b)
        self._lanzar()

    # ---------------------------------------------------------------- llegadas
    def _tasa(self, t, sentido, parada):
        f = P.franja(t)
        if sentido == "ida":
            base = P.TASA_IDA_NOCHE if t >= P.hm(19) else P.TASA_IDA[f]
            return base * P.PESO_IDA[parada] * self.fd / 60
        base = P.TASA_VUELTA_NOCHE if t >= P.hm(19) else P.TASA_VUELTA[f]
        return base * self.fd / 60

    @staticmethod
    def _proximo_cambio(t):
        cortes = [P.hm(5, 30), P.hm(7), P.hm(11), P.hm(14), P.hm(17, 30), P.hm(19), P.hm(24)]
        return next(c for c in cortes if c > t)

    def llegadas(self, sentido, parada, ventana):
        env = self.env
        yield env.timeout(ventana[0] - env.now)
        while env.now < ventana[1]:
            tasa = self._tasa(env.now, sentido, parada)
            corte = min(self._proximo_cambio(env.now), ventana[1])
            if tasa <= 0:
                yield env.timeout(corte - env.now)
                continue
            dt = self.rng_lleg.exponential(1 / tasa)
            if env.now + dt >= corte:                 # sin memoria: se reinicia en el cambio de franja
                yield env.timeout(corte - env.now)
                continue
            yield env.timeout(dt)
            if sentido == "ida":
                p = Pasajero(env.now, parada, "barcelona", "ida")
                self.cola[parada].append(p)
            else:
                dest = self.rng_dest.choice(list(P.PROB_BAJA_VUELTA), p=list(P.PROB_BAJA_VUELTA.values()))
                p = Pasajero(env.now, "barcelona", dest, "vuelta")
                self.cola_campus.append(p)
            self.pasajeros.append(p)

    # ---------------------------------------------------------------- recorrido
    def t_tramo(self, sentido, tramo, t):
        a, c, b, _, _ = P.TRAMOS[(sentido, tramo, P.FRANJA_TIEMPO[P.franja(t)])]
        x = self.rng_viaje.triangular(a, c, b) * P.FACTOR_BUS
        return x * self.fv if (sentido, tramo) in P.TRAMOS_VIA_CAMPUS else x

    def viaje_ida(self, bus, programada):
        env, abordo = self.env, []
        t0, mov = env.now, 0.0
        self.salidas.append(("ida", programada, env.now - programada, bus))
        for i, parada in enumerate(P.PARADAS_IDA[:-1]):
            cupo = P.CAP_TOTAL - len(abordo)
            suben = self.cola[parada][:cupo]
            del self.cola[parada][:len(suben)]
            if suben:
                yield env.timeout(P.T_FIJO_PARADA + P.T_SUBIR * len(suben))
                for p in suben:
                    p.sube = env.now
                abordo += suben
            self.ocupacion.append(("ida", i + 1, P.franja(env.now), len(abordo)))
            dt = self.t_tramo("ida", i + 1, env.now)
            mov += dt
            yield env.timeout(dt)
        yield env.timeout(P.T_FIJO_PARADA + P.T_BAJAR * len(abordo))
        for p in abordo:
            p.baja = env.now
        self.viajes.append(("ida", P.franja(t0), mov, env.now - t0 - mov, len(abordo)))

    def viaje_vuelta(self, bus, programada):
        env = self.env
        self.salidas.append(("vuelta", programada, env.now - programada, bus))
        t0, mov = env.now, 0.0
        suben = self.cola_campus[:P.CAP_TOTAL]
        del self.cola_campus[:len(suben)]
        abordo = suben
        if suben:
            yield env.timeout(P.T_FIJO_PARADA + P.T_SUBIR * len(suben))
            for p in suben:
                p.sube = env.now
        for i, parada in enumerate(P.PARADAS_VUELTA[1:]):
            self.ocupacion.append(("vuelta", i + 1, P.franja(env.now), len(abordo)))
            dt = self.t_tramo("vuelta", i + 1, env.now)
            mov += dt
            yield env.timeout(dt)
            bajan = [p for p in abordo if p.destino == parada]
            if bajan:
                yield env.timeout(P.T_FIJO_PARADA + P.T_BAJAR * len(bajan))
                for p in bajan:
                    p.baja = env.now
                abordo = [p for p in abordo if p.destino != parada]
        self.viajes.append(("vuelta", P.franja(t0), mov, env.now - t0 - mov, len(suben)))

    # ---------------------------------------------------------------- despacho
    def despachar(self, sentido, programada):
        """Cada salida es independiente: a su hora toma el primer bus libre del extremo.
        Si no hay bus, sale tarde en cuanto llegue uno; nunca se cancela ni se fusiona."""
        env = self.env
        yield env.timeout(programada - env.now)
        bus = yield self.libres["parque" if sentido == "ida" else "barcelona"].get()
        if sentido == "ida":
            yield env.process(self.viaje_ida(bus, programada))
        else:
            yield env.process(self.viaje_vuelta(bus, programada))
        yield env.timeout(P.ESPERA_TERMINAL)
        # El bus queda libre en el extremo al que llegó y sigue con la siguiente salida de ese lado.
        yield self.libres["barcelona" if sentido == "ida" else "parque"].put(bus)

    def _lanzar(self):
        env = self.env
        for p in P.PARADAS_IDA[:-1]:
            env.process(self.llegadas("ida", p, P.VENTANA_IDA))
        env.process(self.llegadas("vuelta", "barcelona", P.VENTANA_VUELTA))
        for s in P.SALIDAS_IDA:
            env.process(self.despachar("ida", s))
        for s in P.SALIDAS_VUELTA:
            env.process(self.despachar("vuelta", s))

    def correr(self):
        self.env.run(until=P.FIN_SIM)
        return self


def resumen(r):
    """Medidas de desempeño de una réplica."""
    serv = [p for p in r.pasajeros if p.baja is not None]
    esp = np.array([p.sube - p.llega for p in serv])
    pap = np.array([p.baja - p.llega for p in serv])
    ocu = np.array([o[3] for o in r.ocupacion]) / P.CAP_SENTADOS
    out = {
        "pasajeros": len(r.pasajeros),
        "atendidos": len(serv),
        "sin_servicio": len(r.pasajeros) - len(serv),
        "espera_prom": esp.mean(),
        "espera_p90": np.percentile(esp, 90),
        "puerta_puerta_prom": pap.mean(),
        "ocupacion_prom": ocu.mean(),
        "tramos_sobre_sentados": (ocu > 1).mean(),
        "retraso_salida_prom": np.mean([s[2] for s in r.salidas]),
        "retraso_salida_max": np.max([s[2] for s in r.salidas]),
        "salidas_realizadas": len(r.salidas),
    }
    for s in ("ida", "vuelta"):
        e = [p.sube - p.llega for p in serv if p.sentido == s]
        d = [p.baja - p.llega for p in serv if p.sentido == s]
        out[f"espera_{s}"] = np.mean(e)
        out[f"puerta_puerta_{s}"] = np.mean(d)
    return out


if __name__ == "__main__":
    for esc in P.ESCENARIOS:
        print(esc, {k: round(v, 2) for k, v in resumen(Ruta(esc, 1).correr()).items()})
