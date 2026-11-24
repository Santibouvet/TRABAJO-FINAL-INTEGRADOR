"""
Trabajo Practico Integrador - Teoria de Control (K-4011) - UTN FRBA
Sistema de control de lazo cerrado para la climatizacion de una sala de servidores.

Simula:
  - Planta termica de primer orden (sala + racks + masa termica).
  - Controlador PI digital de accion inversa con anti-windup.
  - Cadena de medicion PT100 + transmisor 4-20 mA + shunt 250 ohm + ADC de 10 bits.
  - Actuador: CRAH con ventiladores EC comandados por senal 0-10 V.
  - Perturbaciones: ola de calor, alta de un rack, apertura de puerta, falla de un CRAH.

Salidas: tablero de control por consola (log) y graficos PNG.

Uso:
  python simulacion_crah.py                      -> ensayo completo, log y graficos PNG
  python simulacion_crah.py --tiempo-real        -> ensayo en tiempo acelerado, con
                                                    graficos que se actualizan en vivo
  python simulacion_crah.py --tiempo-real --velocidad 60
                                                 -> 60 s simulados por cada segundo real
"""

import sys
import argparse
import numpy as np
import matplotlib
if "--tiempo-real" not in sys.argv:
    matplotlib.use("Agg")   # sin ventana: solo se generan archivos PNG
import matplotlib.pyplot as plt

# ----------------------------------------------------------------------------
# 1. PARAMETROS DEL SISTEMA
# ----------------------------------------------------------------------------

# --- Consigna y tiempos ---
R_TEMP = 22.0          # Consigna [C] - centro del rango recomendado ASHRAE (18-27 C)
TS = 30.0              # Tiempo de scan del controlador [s]
T_FINAL = 14400.0      # Duracion de la simulacion [s] (4 h)
DT = 1.0               # Paso de integracion de la planta [s]

# --- Planta termica ---
C_TERM = 2.4e6         # Capacidad termica efectiva de la sala [J/C] (aire + racks + estructura)
UA = 2.0e3             # Conductancia hacia el resto del edificio [W/C]
Q_IT_NOM = 160e3       # Carga termica IT nominal [W] = 20 racks x 8 kW
Q_COOL_MAX = 270e3     # Capacidad frigorifica activa [W] = 3 CRAH x 90 kW (+1 en reserva N+1)
T_AMB_NOM = 25.0       # Temperatura del recinto contiguo / plenum de retorno [C]
T_INICIAL = 26.5       # Temperatura inicial de la sala [C]

# TAU = C/UA = 1200 s ; ganancia estatica respecto de u: K = Q_COOL_MAX/(100*UA)
TAU = C_TERM / UA
K_PLANTA = Q_COOL_MAX / (100.0 * UA)   # [C / %]

# --- Controlador PI (sintonia IMC, lazo cerrado ~5x mas rapido que la planta) ---
TAU_LC = 240.0                          # Constante de tiempo deseada en lazo cerrado [s]
KP = TAU / (K_PLANTA * TAU_LC)          # Ganancia proporcional [% / C]
TI = 500.0                              # Tiempo integral [s]
KI = KP / TI                            # Ganancia integral [% / (C*s)]
U_MIN, U_MAX = 0.0, 100.0               # Saturacion del actuador [%]

# --- Cadena de medicion: PT100 + transmisor 4-20 mA, span 10-40 C, shunt 250 ohm ---
T_SPAN_MIN, T_SPAN_MAX = 10.0, 40.0
V_MIN, V_MAX = 1.0, 5.0                 # 4 mA x 250 ohm = 1 V ; 20 mA x 250 ohm = 5 V
V_REF_ADC = 5.0
BITS_ADC = 10
SIGMA_SENSOR = 0.05                     # Ruido del sensor [C]

# --- Umbrales / zonas de operacion ---
BANDA_NORMAL = 1.0     # +/- 1.0 C  -> 21.0 a 23.0 C
BANDA_ALARMA = 2.5     # +/- 2.5 C  -> 19.5 a 24.5 C
ASHRAE_MIN, ASHRAE_MAX = 18.0, 27.0     # Rango recomendado ASHRAE TC 9.9


def temp_a_volt(t_c):
    """Relacion de solidaridad temperatura -> voltaje del lazo de medicion."""
    return V_MIN + (t_c - T_SPAN_MIN) * (V_MAX - V_MIN) / (T_SPAN_MAX - T_SPAN_MIN)


def volt_a_temp(v):
    return T_SPAN_MIN + (v - V_MIN) * (T_SPAN_MAX - T_SPAN_MIN) / (V_MAX - V_MIN)


def cuantizar(v):
    """ADC de 10 bits con Vref = 5 V."""
    niveles = 2 ** BITS_ADC - 1
    codigo = int(round(np.clip(v, 0.0, V_REF_ADC) / V_REF_ADC * niveles))
    return codigo, codigo * V_REF_ADC / niveles


def zona(err_abs):
    if err_abs <= BANDA_NORMAL:
        return "NORMALIDAD"
    if err_abs <= BANDA_ALARMA:
        return "ALARMA MENOR"
    return "ALARMA MAYOR"


# ----------------------------------------------------------------------------
# 2. PERTURBACIONES
# ----------------------------------------------------------------------------

T_OLA_CALOR = 2700.0    # 45 min
T_ALTA_RACK = 6000.0    # 100 min
T_PUERTA = 9000.0       # 150 min
T_FALLA_CRAH = 11400.0  # 190 min


def perturbaciones(t):
    """Devuelve (T_amb, Q_extra_IT, Q_cool_max_disponible) para el instante t [s]."""
    t_amb = T_AMB_NOM
    q_extra = 0.0
    factor_capacidad = 1.0
    unidades = 3.0

    # (a) EXTERNA - Ola de calor: la temperatura exterior sube 13 C en rampa de 10 min.
    #     Ademas degrada el intercambio en el condensador: -12 % de capacidad frigorifica.
    if t >= T_OLA_CALOR:
        avance = min(1.0, (t - T_OLA_CALOR) / 600.0)
        t_amb = T_AMB_NOM + 13.0 * avance
        factor_capacidad = 1.0 - 0.12 * avance

    # (b) INTERNA - Alta de un rack nuevo: escalon permanente de +15 kW de carga IT.
    if t >= T_ALTA_RACK:
        q_extra += 15e3

    # (c) EXTERNA - Apertura de la puerta de la sala durante 90 s: infiltracion de +25 kW.
    if T_PUERTA <= t < T_PUERTA + 90.0:
        q_extra += 25e3

    # (d) INTERNA - Falla de 1 de los 3 CRAH durante 300 s, hasta que arranca la
    #     unidad redundante N+1.
    if T_FALLA_CRAH <= t < T_FALLA_CRAH + 300.0:
        unidades = 2.0

    q_max = Q_COOL_MAX * factor_capacidad * (unidades / 3.0)
    return t_amb, q_extra, q_max


# ----------------------------------------------------------------------------
# 3. LAZO DE CONTROL
# ----------------------------------------------------------------------------

def simular(semilla=7, con_integral=True):
    """con_integral=False -> controlador solo Proporcional con bias (para comparar)."""
    rng = np.random.default_rng(semilla)

    n = int(T_FINAL / DT) + 1
    tiempo = np.arange(n) * DT

    temp = np.zeros(n)
    temp_medida = np.zeros(n)
    error = np.zeros(n)
    u = np.zeros(n)
    carga_it = np.zeros(n)
    q_cool = np.zeros(n)
    q_max_hist = np.zeros(n)

    temp[0] = T_INICIAL

    # El integrador arranca precargado en el punto de operacion nominal: los CRAH ya
    # estan en marcha cuando se cierra el lazo, no parten de cero.
    u_nominal = 100.0 * (Q_IT_NOM + UA * (T_AMB_NOM - R_TEMP)) / Q_COOL_MAX
    integral = u_nominal
    u_actual = u_nominal

    log = []

    # Fluctuacion del uso de CPU: ruido coloreado (proceso AR(1) con tiempo de
    # correlacion ~200 s). El uso de CPU de un cluster no cambia al azar cada segundo:
    # sube y baja con la demanda de los usuarios.
    rho = np.exp(-DT / 200.0)
    eta = 0.0

    for k in range(n):
        t = tiempo[k]
        t_amb, q_extra, q_max = perturbaciones(t)

        # Carga IT: nominal + perturbaciones + fluctuacion del uso de CPU (sigma = 2.5 %)
        eta = rho * eta + np.sqrt(1.0 - rho ** 2) * rng.standard_normal()
        q_it = (Q_IT_NOM + q_extra) * (1.0 + 0.025 * eta)
        carga_it[k] = q_it
        q_max_hist[k] = q_max

        # --- Ciclo de scan del controlador (cada TS segundos) ---
        if abs(t % TS) < DT / 2.0:
            # Medicion: sensor -> transmisor -> shunt -> ADC
            t_sensada = temp[k] + SIGMA_SENSOR * rng.standard_normal()
            v_sensada = temp_a_volt(t_sensada)
            _, v_adc = cuantizar(v_sensada)
            t_med = volt_a_temp(v_adc)

            e = R_TEMP - t_med          # Senal de error [C]

            # PI de accion inversa: la planta tiene ganancia negativa respecto de u.
            u_p = -KP * e
            integral_tent = integral + (-KI * e) * TS
            u_tent = u_p + integral_tent

            # Anti-windup por clamping: solo se integra si la salida no satura.
            if con_integral and U_MIN <= u_tent <= U_MAX:
                integral = integral_tent
            u_actual = float(np.clip(u_p + integral, U_MIN, U_MAX))
        else:
            t_med = temp_medida[k - 1] if k > 0 else temp[k]
            e = error[k - 1] if k > 0 else 0.0

        temp_medida[k] = t_med
        error[k] = e
        u[k] = u_actual

        # --- Planta: balance termico de la sala ---
        q_refrig = (u_actual / 100.0) * q_max
        q_cool[k] = q_refrig
        dT = (q_it + UA * (t_amb - temp[k]) - q_refrig) / C_TERM
        if k + 1 < n:
            temp[k + 1] = temp[k] + dT * DT

        # --- Tablero de control (una linea por ciclo de scan) ---
        if abs(t % TS) < DT / 2.0:
            log.append(
                f"t={int(t):5d}s | T={temp[k]:6.2f}C | Vmed={temp_a_volt(t_med):5.3f}V | "
                f"e={e:+6.2f}C ({e * (V_MAX - V_MIN) / (T_SPAN_MAX - T_SPAN_MIN) * 1000:+7.1f} mV) | "
                f"u={u_actual:6.2f}% | Qcool={q_refrig / 1000:6.1f}kW | "
                f"Qit={q_it / 1000:6.1f}kW | {zona(abs(e))}"
            )

    return dict(t=tiempo, temp=temp, temp_med=temp_medida, error=error, u=u,
                q_it=carga_it, q_cool=q_cool, q_max=q_max_hist, log=log)


# ----------------------------------------------------------------------------
# 4. GRAFICOS
# ----------------------------------------------------------------------------

AZUL = "#2a78d6"      # slot 1 - variable controlada
NARANJA = "#eb6834"   # slot 2 - carga termica
AGUA = "#1baf7a"      # slot 3 - senal de control
ROJO = "#e34948"      # estado critico
GRIS = "#52514e"
GRIS_TENUE = "#c9c8c4"

EVENTOS = [
    (T_OLA_CALOR, "Ola de calor"),
    (T_ALTA_RACK, "Alta de rack"),
    (T_PUERTA, "Puerta abierta"),
    (T_FALLA_CRAH, "Falla de CRAH"),
]


def marcar_eventos(ax):
    for t_ev, etiqueta in EVENTOS:
        ax.axvline(t_ev / 60.0, color=GRIS_TENUE, lw=1, ls=":", zorder=0)
        ax.annotate(etiqueta, xy=(t_ev / 60.0, 1.01), xycoords=("data", "axes fraction"),
                    fontsize=7.5, color=GRIS, ha="center", va="bottom")


def estilo(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(GRIS_TENUE)
    ax.spines["bottom"].set_color(GRIS_TENUE)
    ax.tick_params(colors=GRIS, labelsize=8.5, length=3)
    ax.grid(axis="y", color=GRIS_TENUE, lw=0.6, alpha=0.55)
    ax.set_axisbelow(True)
    ax.set_xlim(0, T_FINAL / 60.0)


def graficar(r, ruta_base):
    tmin = r["t"] / 60.0

    # ---- Figura 1: variable controlada con bandas de operacion ----
    fig, ax = plt.subplots(figsize=(9.2, 3.6), dpi=200)
    ax.axhspan(ASHRAE_MIN, ASHRAE_MAX, color=AGUA, alpha=0.07, lw=0)
    ax.axhspan(R_TEMP - BANDA_NORMAL, R_TEMP + BANDA_NORMAL, color=AZUL, alpha=0.10, lw=0)
    ax.axhline(R_TEMP, color=GRIS, lw=1.2, ls="--")
    ax.axhline(ASHRAE_MAX, color=ROJO, lw=1.0, ls="-.")
    ax.plot(tmin, r["temp"], color=AZUL, lw=2.0, solid_capstyle="round")
    marcar_eventos(ax)
    ax.annotate("Consigna R = 22 °C", xy=(T_FINAL / 60.0 - 2, R_TEMP), fontsize=8, color=GRIS,
                ha="right", va="bottom")
    ax.annotate("Límite recomendado ASHRAE = 27 °C", xy=(2, ASHRAE_MAX), fontsize=8,
                color=ROJO, ha="left", va="bottom")
    ax.annotate("Banda de normalidad ±1 °C", xy=(58, R_TEMP - BANDA_NORMAL), fontsize=8,
                color=AZUL, ha="left", va="top")
    ax.set_ylabel("Temperatura del pasillo frío  [°C]", fontsize=9, color=GRIS)
    ax.set_xlabel("Tiempo  [min]", fontsize=9, color=GRIS)
    ax.set_ylim(17.5, 28.5)
    estilo(ax)
    fig.tight_layout()
    fig.savefig(f"{ruta_base}/g1_temperatura.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)

    # ---- Figura 2: senal de control ----
    fig, ax = plt.subplots(figsize=(9.2, 2.9), dpi=200)
    ax.fill_between(tmin, 0, r["u"], color=AGUA, alpha=0.13, lw=0)
    ax.plot(tmin, r["u"], color=AGUA, lw=2.0, solid_capstyle="round")
    ax.axhline(100, color=ROJO, lw=1.0, ls="-.")
    ax.annotate("Saturación del actuador (100 %)", xy=(T_FINAL / 60.0 - 2, 100), fontsize=8,
                color=ROJO, ha="right", va="bottom")
    marcar_eventos(ax)
    ax.set_ylabel("Señal de control u  [% de capacidad]", fontsize=9, color=GRIS)
    ax.set_xlabel("Tiempo  [min]", fontsize=9, color=GRIS)
    ax.set_ylim(0, 118)
    estilo(ax)
    fig.tight_layout()
    fig.savefig(f"{ruta_base}/g2_senal_control.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)

    # ---- Figura 3: carga termica vs capacidad entregada ----
    fig, ax = plt.subplots(figsize=(9.2, 3.3), dpi=200)
    ax.plot(tmin, r["q_max"] / 1000.0, color=GRIS_TENUE, lw=1.4, ls="--",
            label="Capacidad instalada disponible")
    ax.plot(tmin, r["q_it"] / 1000.0, color=NARANJA, lw=1.6,
            label="Carga térmica IT (carga del sistema)")
    ax.plot(tmin, r["q_cool"] / 1000.0, color=AGUA, lw=2.0,
            label="Potencia frigorífica entregada")
    marcar_eventos(ax)
    ax.set_ylabel("Potencia térmica  [kW]", fontsize=9, color=GRIS)
    ax.set_xlabel("Tiempo  [min]", fontsize=9, color=GRIS)
    ax.legend(fontsize=8, frameon=False, loc="upper center",
              bbox_to_anchor=(0.5, -0.26), ncol=3, labelcolor=GRIS)
    estilo(ax)
    fig.tight_layout()
    fig.savefig(f"{ruta_base}/g3_carga.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)

    # ---- Figura 4: senal de error ----
    fig, ax = plt.subplots(figsize=(9.2, 2.9), dpi=200)
    ax.axhspan(-BANDA_NORMAL, BANDA_NORMAL, color=AZUL, alpha=0.10, lw=0)
    ax.axhline(0, color=GRIS, lw=1.0, ls="--")
    ax.plot(tmin, r["error"], color=AZUL, lw=1.8, solid_capstyle="round")
    marcar_eventos(ax)
    ax.annotate("Zona de normalidad  e(t) = ±1 °C  (±133 mV)", xy=(58, BANDA_NORMAL),
                fontsize=8, color=AZUL, ha="left", va="bottom")
    ax.set_ylabel("Señal de error  e(t)  [°C]", fontsize=9, color=GRIS)
    ax.set_xlabel("Tiempo  [min]", fontsize=9, color=GRIS)
    ax.set_ylim(-6.2, 3.2)
    estilo(ax)
    fig.tight_layout()
    fig.savefig(f"{ruta_base}/g4_error.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def graficar_comparacion(r_pi, r_p, ruta_base):
    """Justificacion de la ley de control: P deja error en estado estable, PI no."""
    tmin = r_pi["t"] / 60.0
    fig, ax = plt.subplots(figsize=(9.2, 3.4), dpi=200)
    ax.axhspan(R_TEMP - BANDA_NORMAL, R_TEMP + BANDA_NORMAL, color=AZUL, alpha=0.10, lw=0)
    ax.axhline(R_TEMP, color=GRIS, lw=1.2, ls="--")
    ax.plot(tmin, r_p["temp"], color=NARANJA, lw=1.8,
            label="Solo Proporcional (P)")
    ax.plot(tmin, r_pi["temp"], color=AZUL, lw=2.0,
            label="Proporcional + Integral (PI)")
    marcar_eventos(ax)
    ax.annotate("Consigna R = 22 °C", xy=(T_FINAL / 60.0 - 2, R_TEMP), fontsize=8,
                color=GRIS, ha="right", va="bottom")
    ax.set_ylabel("Temperatura del pasillo frío  [°C]", fontsize=9, color=GRIS)
    ax.set_xlabel("Tiempo  [min]", fontsize=9, color=GRIS)
    # El limite superior se ajusta al pico del control P para no recortarlo.
    ax.set_ylim(19.5, max(31.5, float(np.max(r_p["temp"])) + 0.8))
    ax.legend(fontsize=8, frameon=False, loc="upper center",
              bbox_to_anchor=(0.5, -0.24), ncol=2, labelcolor=GRIS)
    estilo(ax)
    fig.tight_layout()
    fig.savefig(f"{ruta_base}/g5_comparacion_p_pi.png", bbox_inches="tight",
                facecolor="white")
    plt.close(fig)


# ----------------------------------------------------------------------------
# 5. MODO TIEMPO REAL
# ----------------------------------------------------------------------------

def tiempo_real(r, velocidad=120.0):
    """Reproduce el ensayo en tiempo acelerado: los graficos de temperatura, senal de
    control y balance termico se dibujan a medida que avanza el tiempo simulado, y el
    tablero de control se imprime en la consola en cada ciclo de scan.

    velocidad: segundos simulados por cada segundo real (120 -> 4 h en 2 min).
    """
    import time
    from matplotlib.animation import FuncAnimation

    tmin = r["t"] / 60.0
    fig, (ax_t, ax_u, ax_q) = plt.subplots(3, 1, figsize=(10, 8.2), sharex=True)
    try:
        fig.canvas.manager.set_window_title("Sala de servidores - lazo de control en tiempo real")
    except AttributeError:
        pass

    # Fondo fijo: bandas, consigna, limites y eventos
    ax_t.axhspan(ASHRAE_MIN, ASHRAE_MAX, color=AGUA, alpha=0.07, lw=0)
    ax_t.axhspan(R_TEMP - BANDA_NORMAL, R_TEMP + BANDA_NORMAL, color=AZUL, alpha=0.10, lw=0)
    ax_t.axhline(R_TEMP, color=GRIS, lw=1.2, ls="--")
    ax_t.axhline(ASHRAE_MAX, color=ROJO, lw=1.0, ls="-.")
    ax_t.set_ylim(17.5, 28.5)
    ax_t.set_ylabel("Temperatura [°C]", fontsize=9, color=GRIS)

    ax_u.axhline(100, color=ROJO, lw=1.0, ls="-.")
    ax_u.set_ylim(0, 118)
    ax_u.set_ylabel("u [% capacidad]", fontsize=9, color=GRIS)

    ax_q.set_ylim(0.9 * min(np.min(r["q_it"]), np.min(r["q_cool"])) / 1000.0,
                  1.05 * np.max(r["q_max"]) / 1000.0)
    ax_q.set_ylabel("Potencia [kW]", fontsize=9, color=GRIS)
    ax_q.set_xlabel("Tiempo [min]", fontsize=9, color=GRIS)

    for ax in (ax_t, ax_u, ax_q):
        estilo(ax)
        marcar_eventos(ax)

    l_t, = ax_t.plot([], [], color=AZUL, lw=2.0)
    l_u, = ax_u.plot([], [], color=AGUA, lw=2.0)
    l_qmax, = ax_q.plot([], [], color=GRIS_TENUE, lw=1.4, ls="--", label="Capacidad disponible")
    l_qit, = ax_q.plot([], [], color=NARANJA, lw=1.4, label="Carga térmica IT")
    l_qc, = ax_q.plot([], [], color=AGUA, lw=2.0, label="Potencia frigorífica")
    ax_q.legend(fontsize=8, frameon=False, loc="lower left", ncol=3, labelcolor=GRIS)
    panel = ax_t.text(0.01, 0.04, "", transform=ax_t.transAxes, fontsize=8.5,
                      family="monospace", color=GRIS, va="bottom",
                      bbox=dict(facecolor="white", edgecolor=GRIS_TENUE, alpha=0.9))
    fig.tight_layout()

    pasos_por_scan = int(round(TS / DT))
    n = len(r["t"])
    estado = {"t0": None, "log": -1}

    def actualizar(_):
        if estado["t0"] is None:
            estado["t0"] = time.perf_counter()
        t_sim = min((time.perf_counter() - estado["t0"]) * velocidad, T_FINAL)
        k = min(int(t_sim / DT), n - 1)

        l_t.set_data(tmin[:k + 1], r["temp"][:k + 1])
        l_u.set_data(tmin[:k + 1], r["u"][:k + 1])
        l_qmax.set_data(tmin[:k + 1], r["q_max"][:k + 1] / 1000.0)
        l_qit.set_data(tmin[:k + 1], r["q_it"][:k + 1] / 1000.0)
        l_qc.set_data(tmin[:k + 1], r["q_cool"][:k + 1] / 1000.0)

        # Tablero por consola: una linea por cada ciclo de scan alcanzado
        while estado["log"] < min(k // pasos_por_scan, len(r["log"]) - 1):
            estado["log"] += 1
            print(r["log"][estado["log"]])

        e = r["error"][k]
        panel.set_text(f"t = {r['t'][k] / 60.0:6.1f} min   T = {r['temp'][k]:5.2f} °C   "
                       f"e = {e:+5.2f} °C   u = {r['u'][k]:5.1f} %   {zona(abs(e))}")

        if t_sim >= T_FINAL:
            anim.event_source.stop()
        return l_t, l_u, l_qmax, l_qit, l_qc, panel

    anim = FuncAnimation(fig, actualizar, interval=100, blit=False, cache_frame_data=False)
    plt.show()
    return anim


# ----------------------------------------------------------------------------
# 6. MAIN
# ----------------------------------------------------------------------------

if __name__ == "__main__":
    import os
    base = os.path.dirname(os.path.abspath(__file__))

    parser = argparse.ArgumentParser(
        description="Simulacion del lazo de control termico de una sala de servidores.")
    parser.add_argument("--tiempo-real", action="store_true",
                        help="muestra el ensayo en tiempo acelerado con graficos en vivo")
    parser.add_argument("--velocidad", type=float, default=120.0,
                        help="segundos simulados por segundo real en modo tiempo real "
                             "(por defecto 120: las 4 h del ensayo en 2 min)")
    args = parser.parse_args()

    if args.tiempo_real:
        print(f"Modo tiempo real: {args.velocidad:.0f} s simulados por segundo real. "
              f"Cerrar la ventana para terminar.\n")
        tiempo_real(simular(), args.velocidad)
        sys.exit(0)

    print("=" * 96)
    print("PARAMETROS DEL LAZO")
    print("=" * 96)
    print(f"Consigna R                : {R_TEMP:.1f} C  ->  {temp_a_volt(R_TEMP):.3f} V")
    print(f"Constante de tiempo TAU   : {TAU:.0f} s ({TAU/60:.1f} min)")
    print(f"Ganancia de planta K      : {K_PLANTA:.3f} C/%")
    print(f"Kp                        : {KP:.3f} %/C")
    print(f"Ti                        : {TI:.0f} s   ->  Ki = {KI:.5f} %/(C*s)")
    print(f"Tiempo de scan Ts         : {TS:.0f} s")
    print(f"Resolucion del ADC        : {V_REF_ADC/(2**BITS_ADC-1)*1000:.2f} mV/LSB "
          f"= {V_REF_ADC/(2**BITS_ADC-1)/((V_MAX-V_MIN)/(T_SPAN_MAX-T_SPAN_MIN)):.4f} C/LSB")
    print()

    r = simular()

    print("=" * 96)
    print("TABLERO DE CONTROL (extractos)")
    print("=" * 96)
    tramos = [("Puesta en marcha", 0), ("Regimen permanente", int(2100 / TS)),
              ("Ola de calor", int(T_OLA_CALOR / TS)), ("Alta de rack", int(T_ALTA_RACK / TS)),
              ("Puerta abierta", int(T_PUERTA / TS)), ("Falla de CRAH", int(T_FALLA_CRAH / TS))]
    for titulo, i0 in tramos:
        print(f"\n--- {titulo} ---")
        for linea in r["log"][i0:i0 + 8]:
            print(linea)

    with open(os.path.join(base, "tablero_control.log"), "w", encoding="utf-8") as f:
        f.write("\n".join(r["log"]))

    graficar(r, base)

    # Contraste con un controlador solo Proporcional (misma Kp, mismo escenario)
    r_p = simular(con_integral=False)
    graficar_comparacion(r, r_p, base)
    idx_p = (r["t"] > 8000) & (r["t"] < 8900)
    print()
    print(f"[Contraste P vs PI]  Error medio con solo P (133-148 min): "
          f"{np.mean(r_p['error'][idx_p]):+.3f} C")
    print(f"[Contraste P vs PI]  Error medio con PI     (133-148 min): "
          f"{np.mean(r['error'][idx_p]):+.3f} C")

    # --- Metricas de desempeno ---
    idx_estable = (r["t"] > 1800) & (r["t"] < T_OLA_CALOR)
    idx_final = r["t"] > 13800
    print()
    print("=" * 96)
    print("METRICAS")
    print("=" * 96)
    print(f"Error medio en regimen permanente (30-45 min): {np.mean(r['error'][idx_estable]):+.4f} C")
    print(f"Error medio al final (230-240 min)           : {np.mean(r['error'][idx_final]):+.4f} C")
    print(f"Desvio estandar del error en 30-45 min       : {np.std(r['error'][idx_estable]):.4f} C")
    print(f"Temperatura maxima alcanzada                 : {np.max(r['temp']):.2f} C")
    print(f"Temperatura minima alcanzada                 : {np.min(r['temp']):.2f} C")
    print(f"Tiempo fuera de la banda de normalidad       : "
          f"{100*np.mean(np.abs(r['error'])>BANDA_NORMAL):.1f} % del ensayo")
    print(f"Tiempo fuera del rango recomendado ASHRAE    : "
          f"{100*np.mean((r['temp']>ASHRAE_MAX)|(r['temp']<ASHRAE_MIN)):.1f} % del ensayo")
    print(f"u maxima                                     : {np.max(r['u']):.1f} %")
