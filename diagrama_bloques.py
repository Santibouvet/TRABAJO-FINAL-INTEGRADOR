"""Diagrama de bloques del sistema de control termico de la sala de servidores."""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle, FancyArrowPatch, Rectangle

TINTA = "#1c1c1a"
GRIS = "#52514e"
BORDE = "#9a9993"
AZUL = "#2a78d6"
NARANJA = "#eb6834"
AGUA = "#1baf7a"
FONDO_CTRL = "#eaf2fc"
FONDO_PROC = "#e9f7f1"
FONDO_MED = "#fdeee7"

fig, ax = plt.subplots(figsize=(13.2, 6.6), dpi=200)
ax.set_xlim(0, 132)
ax.set_ylim(-3, 70)
ax.axis("off")


def bloque(x, y, w, h, texto, sub="", fondo="white", borde=BORDE, fs=8.5):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.2",
                                linewidth=1.3, edgecolor=borde, facecolor=fondo, zorder=3))
    if sub:
        ax.text(x + w / 2, y + h * 0.66, texto, ha="center", va="center",
                fontsize=fs, color=TINTA, zorder=4, weight="bold")
        ax.text(x + w / 2, y + h * 0.30, sub, ha="center", va="center",
                fontsize=fs - 1.4, color=GRIS, zorder=4)
    else:
        ax.text(x + w / 2, y + h / 2, texto, ha="center", va="center",
                fontsize=fs, color=TINTA, zorder=4, weight="bold")
    return (x, y, w, h)


def suma(x, y, signos, r=2.4):
    """signos: lista de (signo, dx, dy) con la posicion relativa de cada signo."""
    ax.add_patch(Circle((x, y), r, linewidth=1.3, edgecolor=TINTA,
                        facecolor="white", zorder=4))
    ax.plot([x - r * 0.62, x + r * 0.62], [y, y], color=TINTA, lw=1.0, zorder=5)
    ax.plot([x, x], [y - r * 0.62, y + r * 0.62], color=TINTA, lw=1.0, zorder=5)
    for signo, dx, dy in signos:
        ax.text(x + dx * r * 1.55, y + dy * r * 1.35, signo, ha="center", va="center",
                fontsize=10, color=TINTA, zorder=5)
    return x, y


def flecha(p0, p1, color=TINTA, etiqueta="", et_dy=1.8, et_dx=0.0, fs=7.6,
           estilo="-|>", et_color=None, ha="center"):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle=estilo, mutation_scale=11,
                                 linewidth=1.25, color=color, zorder=2,
                                 shrinkA=0, shrinkB=0))
    if etiqueta:
        mx, my = (p0[0] + p1[0]) / 2 + et_dx, (p0[1] + p1[1]) / 2 + et_dy
        ax.text(mx, my, etiqueta, ha=ha, va="center", fontsize=fs,
                color=et_color or GRIS, zorder=5)


def linea(p0, p1, color=TINTA):
    ax.plot([p0[0], p1[0]], [p0[1], p1[1]], color=color, lw=1.25, zorder=2)


# ---------------------------------------------------------------- agrupadores
ax.add_patch(Rectangle((8, 30), 50, 24, linewidth=1.1, edgecolor=AZUL,
                       facecolor=FONDO_CTRL, alpha=0.5, zorder=0, ls=(0, (5, 3))))
ax.text(33, 52.3, "CONTROLADOR  (BMS / PLC)  —  dominio digital", ha="center", va="center",
        fontsize=8, color=AZUL, weight="bold", zorder=1)

ax.add_patch(Rectangle((60, 30), 57, 24, linewidth=1.1, edgecolor=AGUA,
                       facecolor=FONDO_PROC, alpha=0.5, zorder=0, ls=(0, (5, 3))))
ax.text(88.5, 52.3, "ACTUADOR  +  PLANTA", ha="center", va="center",
        fontsize=8, color="#12805a", weight="bold", zorder=1)

ax.add_patch(Rectangle((3, 2), 105, 16, linewidth=1.1, edgecolor=NARANJA,
                       facecolor=FONDO_MED, alpha=0.45, zorder=0, ls=(0, (5, 3))))
ax.text(62, 16.3, "RAMA DE REALIMENTACIÓN Y MEDICIÓN   (H total = 133,3 mV/°C)",
        ha="center", va="center", fontsize=8, color="#b4441c", weight="bold", zorder=1)

# ---------------------------------------------------------------- lazo directo
y = 40.0

ax.text(0.5, y - 5.2, "R = 22 °C", ha="left", va="center", fontsize=8.5,
        color=TINTA, weight="bold")
ax.text(0.5, y - 8.8, "consigna\nen el BMS", ha="left", va="center", fontsize=7.2, color=GRIS)
flecha((0.5, y), (10.6, y), etiqueta="θi", et_dy=2.0, et_dx=-1.5)

suma(13.0, y, signos=(("+", -1, 1), ("−", -1, -1)))
ax.text(13.0, y + 5.0, "comparador\ndigital", ha="center", va="center", fontsize=6.8,
        color=GRIS, style="italic")

flecha((15.4, y), (21.0, y), etiqueta="e(kT)", et_dy=2.0)

bloque(21.0, y - 5.6, 16.5, 11.2, "Controlador PI",
       "Amplifica el error: Kp\nKp = 3,70 %/°C · Ti = 500 s\nTs = 30 s · anti-windup",
       fondo="white", borde=AZUL, fs=8.3)
ax.text(29.25, y + 8.6, "1 °C = 133 mV = 27,3 cuentas", ha="center", va="center",
        fontsize=6.8, color=GRIS, style="italic")

flecha((37.5, y), (41.5, y), etiqueta="u(kT)", et_dy=2.0, fs=7.2)

bloque(41.5, y - 5.0, 14.5, 10.0, "Salida analógica", "PWM + filtro\nu → 0-10 V",
       fondo="white", borde=AZUL, fs=8.0)

flecha((56.0, y), (62.0, y), etiqueta="0-10 V", et_dy=2.0)

bloque(62.0, y - 5.6, 15.5, 11.2, "Actuador",
       "Ventiladores EC\n+ válvula de 3 vías\n(agua helada)", fondo="white", borde=AGUA)

flecha((77.5, y), (83.0, y), etiqueta="Qcool", et_dy=2.2)
ax.text(80.25, y - 2.4, "[kW]", ha="center", va="center", fontsize=6.8, color=GRIS)

# punto suma del balance termico (en kW)
suma(85.4, y, signos=(("−", -1, 1), ("+", 1, 1), ("+", 1, -1)))

bloque(71.0, y + 17.0, 30.0, 8.4, "PERTURBACIONES  Qd",
       "Ola de calor · Puerta abierta · Alta de rack · Falla de CRAH",
       fondo="white", borde=NARANJA, fs=8.0)
flecha((85.4, y + 17.0), (85.4, y + 2.4), etiqueta="[kW]", et_dx=1.2, et_dy=-1.5,
       fs=6.8, ha="left")

bloque(74.4, y - 19.6, 22.0, 7.2, "CARGA DEL SISTEMA  Q_IT",
       "20 racks × 8 kW = 160 kW", fondo="white", borde=NARANJA, fs=7.8)
flecha((85.4, y - 12.4), (85.4, y - 2.4))

flecha((87.8, y), (93.0, y))

bloque(93.0, y - 6.0, 22.5, 12.0, "PLANTA — Sala",
       "θo = (Q_IT + Qd − Qcool) / (C·s + UA)\nC = 2,4 MJ/°C · UA = 2 kW/°C\nτ = 1200 s",
       fondo="white", borde=AGUA, fs=8.4)

# salida
flecha((115.5, y), (125.5, y), etiqueta="θo(t)", et_dy=2.2)
ax.text(126.3, y + 1.4, "Temperatura del", ha="left", va="center", fontsize=7.8, color=GRIS)
ax.text(126.3, y - 1.4, "pasillo frío [°C]", ha="left", va="center", fontsize=7.8, color=GRIS)

# ---------------------------------------------------------------- realimentación
yf = 9.0
linea((122.0, y), (122.0, yf))
ax.add_patch(Circle((122.0, y), 0.75, color=TINTA, zorder=5))
flecha((122.0, yf), (101.5, yf))

bloque(84.0, yf - 4.6, 17.5, 9.2, "Sensor PT100", "Clase A · 3/4 hilos\n0,385 Ω/°C",
       fondo="white", borde=NARANJA)
flecha((84.0, yf), (70.0, yf), etiqueta="R [Ω]", et_dy=2.0)

bloque(52.0, yf - 4.6, 18.0, 9.2, "Transmisor", "Span 10–40 °C\n4–20 mA",
       fondo="white", borde=NARANJA)
flecha((52.0, yf), (42.0, yf), etiqueta="4–20 mA", et_dy=2.0)

bloque(25.0, yf - 4.6, 17.0, 9.2, "Shunt 250 Ω", "1 V ↔ 10 °C\n5 V ↔ 40 °C",
       fondo="white", borde=NARANJA)
flecha((25.0, yf), (20.5, yf), etiqueta="1–5 V", et_dy=2.0, fs=7.0)

bloque(5.5, yf - 4.6, 15.0, 9.2, "ADC 10 bits", "4,89 mV/LSB\n0,0367 °C/LSB",
       fondo="white", borde=AZUL)
flecha((13.0, yf + 4.6), (13.0, y - 2.4), etiqueta="f(kT)", et_dx=1.2, et_dy=-2.5,
       fs=7.6, ha="left")

# leyenda de dominios
ax.text(3.5, -1.2, "◄ señales analógicas: resistencia, corriente y tensión en la rama de "
        "medición; 0-10 V hacia el actuador.   Señales digitales: dentro del controlador "
        "(muestreo cada 30 s).", ha="left", va="center", fontsize=7.2, color=GRIS,
        style="italic")

fig.tight_layout()
fig.savefig(os.path.join(os.path.dirname(os.path.abspath(__file__)), "g0_diagrama_bloques.png"),
            bbox_inches="tight", facecolor="white")
print("OK")
