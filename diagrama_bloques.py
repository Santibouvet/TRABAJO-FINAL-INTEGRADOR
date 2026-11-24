"""Diagrama de bloques del sistema de control termico de la sala de servidores."""

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

fig, ax = plt.subplots(figsize=(13.2, 6.4), dpi=200)
ax.set_xlim(0, 132)
ax.set_ylim(-2, 70)
ax.axis("off")


def bloque(x, y, w, h, texto, sub="", fondo="white", borde=BORDE, fs=8.5):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.2",
                                linewidth=1.3, edgecolor=borde, facecolor=fondo, zorder=3))
    if sub:
        ax.text(x + w / 2, y + h * 0.60, texto, ha="center", va="center",
                fontsize=fs, color=TINTA, zorder=4, weight="bold")
        ax.text(x + w / 2, y + h * 0.26, sub, ha="center", va="center",
                fontsize=fs - 1.4, color=GRIS, zorder=4)
    else:
        ax.text(x + w / 2, y + h / 2, texto, ha="center", va="center",
                fontsize=fs, color=TINTA, zorder=4, weight="bold")
    return (x, y, w, h)


def suma(x, y, r=2.4, signos=(("+", -1, 1), ("-", -1, -1))):
    ax.add_patch(Circle((x, y), r, linewidth=1.3, edgecolor=TINTA,
                        facecolor="white", zorder=4))
    ax.plot([x - r * 0.62, x + r * 0.62], [y, y], color=TINTA, lw=1.0, zorder=5)
    ax.plot([x, x], [y - r * 0.62, y + r * 0.62], color=TINTA, lw=1.0, zorder=5)
    for signo, dx, dy in signos:
        ax.text(x + dx * r * 1.55, y + dy * r * 1.35, signo, ha="center", va="center",
                fontsize=10, color=TINTA, zorder=5)
    return x, y


def flecha(p0, p1, color=TINTA, etiqueta="", et_dy=1.8, et_dx=0.0, fs=7.6,
           estilo="-|>", ls="-", et_color=None):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle=estilo, mutation_scale=11,
                                 linewidth=1.25, color=color, zorder=2,
                                 linestyle=ls, shrinkA=0, shrinkB=0))
    if etiqueta:
        mx, my = (p0[0] + p1[0]) / 2 + et_dx, (p0[1] + p1[1]) / 2 + et_dy
        ax.text(mx, my, etiqueta, ha="center", va="center", fontsize=fs,
                color=et_color or GRIS, zorder=5)


def linea(p0, p1, color=TINTA, ls="-"):
    ax.plot([p0[0], p1[0]], [p0[1], p1[1]], color=color, lw=1.25, zorder=2, ls=ls)


# ---------------------------------------------------------------- agrupadores
ax.add_patch(Rectangle((13, 30), 44, 24, linewidth=1.1, edgecolor=AZUL,
                       facecolor=FONDO_CTRL, alpha=0.5, zorder=0, ls=(0, (5, 3))))
ax.text(35, 52.4, "CONTROLADOR  (BMS / PLC del datacenter)", ha="center", va="center",
        fontsize=8, color=AZUL, weight="bold", zorder=1)

ax.add_patch(Rectangle((60, 30), 55, 24, linewidth=1.1, edgecolor=AGUA,
                       facecolor=FONDO_PROC, alpha=0.5, zorder=0, ls=(0, (5, 3))))
ax.text(87.5, 52.4, "ACTUADOR  +  PLANTA", ha="center", va="center",
        fontsize=8, color="#12805a", weight="bold", zorder=1)

ax.add_patch(Rectangle((22, 4), 86, 15, linewidth=1.1, edgecolor=NARANJA,
                       facecolor=FONDO_MED, alpha=0.45, zorder=0, ls=(0, (5, 3))))
ax.text(65, 17.2, "RAMA DE REALIMENTACIÓN Y MEDICIÓN   (H total)", ha="center", va="center",
        fontsize=8, color="#b4441c", weight="bold", zorder=1)

# ---------------------------------------------------------------- lazo directo
y = 40.0

ax.text(1.5, y + 4.6, "R = 22 °C", ha="left", va="center", fontsize=8.5,
        color=TINTA, weight="bold")
ax.text(1.5, y + 1.9, "(2,600 V)", ha="left", va="center", fontsize=7.6, color=GRIS)
flecha((1.5, y), (10.6, y), etiqueta="θi(t)", et_dy=-2.4)

sx, sy = suma(13.0, y)

flecha((15.4, y), (18.5, y), etiqueta="e(t)", et_dy=2.2)
ax.text(26.0, y + 7.2, "Escala del error:  1 °C  =  133 mV", ha="center",
        va="center", fontsize=7.4, color=GRIS, style="italic")

bloque(18.5, y - 5.0, 15.0, 10.0, "ADC 10 bits", "4,89 mV/LSB\n0,0367 °C/LSB",
       fondo="white", borde=AZUL)
flecha((33.5, y), (38.0, y), etiqueta="e(kT)", et_dy=2.0)

bloque(38.0, y - 5.6, 17.0, 11.2, "Controlador PI", "Kp = 3,70 %/°C\nTi = 500 s\nTs = 30 s",
       fondo="white", borde=AZUL, fs=8.5)
flecha((55.0, y), (61.0, y), etiqueta="u(kT)", et_dy=2.0)

bloque(61.0, y - 5.0, 16.5, 10.0, "Actuador", "PWM → 0-10 V\nVariador · ventilador EC",
       fondo="white", borde=AGUA)
flecha((77.5, y), (83.0, y), etiqueta="0-10 V", et_dy=2.0)

# punto suma de las perturbaciones sobre la planta
px, py = suma(85.4, y, signos=(("+", -1, 1), ("+", 1, 1)))
flecha((85.4, y + 17.0), (85.4, y + 2.6))
bloque(70.0, y + 17.0, 31.0, 8.4, "PERTURBACIONES",
       "Ola de calor · Puerta abierta · Alta de rack · Falla de CRAH",
       fondo="white", borde=NARANJA, fs=8.0)

flecha((87.8, y), (92.5, y))

bloque(92.5, y - 5.6, 22.5, 11.2, "PLANTA — Sala de servidores",
       "C = 2,4 MJ/°C   UA = 2 kW/°C\nτ = 1200 s   K = 1,35 °C/%",
       fondo="white", borde=AGUA, fs=8.5)

# salida
flecha((115.0, y), (125.5, y), etiqueta="θo(t)", et_dy=2.2)
ax.text(126.5, y + 1.4, "Temperatura del", ha="left", va="center", fontsize=7.8, color=GRIS)
ax.text(126.5, y - 1.4, "pasillo frío [°C]", ha="left", va="center", fontsize=7.8, color=GRIS)

# ---------------------------------------------------------------- carga
bloque(92.5, y - 22.0, 22.5, 7.4, "CARGA DEL SISTEMA",
       "Calor disipado por los racks\n20 racks × 8 kW = 160 kW", fondo="white",
       borde=NARANJA, fs=8.0)
# La carga (calor de los racks) ingresa a la planta: la flecha apunta hacia la sala.
flecha((103.75, y - 14.6), (103.75, y - 5.6), estilo="-|>")

# ---------------------------------------------------------------- realimentación
yf = 11.0
linea((122.0, y), (122.0, yf))
ax.add_patch(Circle((122.0, y), 0.75, color=TINTA, zorder=5))
flecha((122.0, yf), (101.5, yf))

bloque(84.0, yf - 4.6, 17.5, 9.2, "Sensor PT100", "Clase A · 1/3 DIN\n±0,15 °C",
       fondo="white", borde=NARANJA)
flecha((84.0, yf), (69.0, yf), etiqueta="Resistencia [Ω]", et_dy=2.0)

bloque(51.0, yf - 4.6, 18.0, 9.2, "Transmisor", "Span 10–40 °C\nSalida 4–20 mA",
       fondo="white", borde=NARANJA)
flecha((51.0, yf), (41.5, yf), etiqueta="4–20 mA", et_dy=2.0)

bloque(24.5, yf - 4.6, 17.0, 9.2, "Shunt 250 Ω", "1 V ↔ 10 °C\n5 V ↔ 40 °C",
       fondo="white", borde=NARANJA)

linea((24.5, yf), (13.0, yf))
flecha((13.0, yf), (13.0, y - 2.4), etiqueta="f(t) = 2,600 V", et_dy=0, et_dx=5.4,
       fs=7.8)

# leyenda de dominios
ax.text(24.5, yf - 7.6, "◄ señales analógicas (tensión / corriente)", ha="left",
        va="center", fontsize=7.6, color=GRIS, style="italic")
ax.text(18.5, 57.6, "◄ señales digitales — registros del BMS ►", ha="left",
        va="center", fontsize=7.6, color=AZUL, style="italic")

fig.tight_layout()
import os
fig.savefig(os.path.join(os.path.dirname(os.path.abspath(__file__)), "g0_diagrama_bloques.png"),
            bbox_inches="tight", facecolor="white")
print("OK")
