# Control de lazo cerrado para la climatización de una sala de servidores

Trabajo Final Integrador de **Teoría de Control**, UTN FRBA, comisión **K4572**, 2do cuatrimestre 2026.
Autor: **Santino Bouvet**. Profesor: Omar Oscar Civale.

Este repositorio contiene el programa que simula y verifica el sistema de control descripto en la memoria técnica. El sistema regula la temperatura del pasillo frío de una sala de 20 racks (160 kW), refrigerada por unidades CRAH de agua helada (3 × 90 kW + 1 en reserva N+1). Lo hace mediante un controlador PI digital de acción inversa con anti-windup.

## Recursos necesarios

| Recurso | Detalle |
|---|---|
| Sistema operativo | Windows, Linux o macOS |
| Python | 3.9 o superior ([python.org/downloads](https://www.python.org/downloads/)) |
| Bibliotecas | NumPy y Matplotlib (ver `requirements.txt`) |
| Hardware | Cualquier PC actual. El ensayo completo tarda unos segundos. |
| Modo tiempo real | Requiere entorno gráfico (Tkinter, incluido en el instalador oficial de Python) |

## Acceso e instalación

1. Descargar el repositorio. Hay dos formas:
   - Desde la web: botón verde **Code → Download ZIP**, y descomprimir.
   - Con Git: `git clone <URL de este repositorio>`
2. Abrir una terminal en la carpeta del repositorio e instalar las dependencias:

   ```
   python -m pip install -r requirements.txt
   ```

## Ejecución

| Comando | Qué hace |
|---|---|
| `python simulacion_crah.py` | Ejecuta el ensayo completo de 4 horas. Imprime los parámetros del lazo, extractos del tablero de control y las métricas de desempeño. Genera `tablero_control.log` y los gráficos `g1` a `g5`. |
| `python simulacion_crah.py --tiempo-real` | Reproduce el ensayo en tiempo acelerado. Los gráficos de temperatura, señal de control y balance térmico se actualizan en vivo, y el tablero se imprime en la consola en cada ciclo de scan (cada 30 s simulados). |
| `python simulacion_crah.py --tiempo-real --velocidad 60` | Igual que el anterior, pero con 60 s simulados por cada segundo real. Por defecto son 120, de modo que el ensayo dura 2 minutos. |
| `python diagrama_bloques.py` | Regenera el diagrama de bloques `g0_diagrama_bloques.png`. |

En Linux y macOS puede ser necesario usar `python3` en lugar de `python`.

## Contenido

| Archivo | Descripción |
|---|---|
| `simulacion_crah.py` | Simulación del lazo completo: planta térmica, cadena de medición (PT100, transmisor 4-20 mA, shunt de 250 Ω y conversor A/D de 10 bits), controlador PI con anti-windup, actuador y perturbaciones. |
| `diagrama_bloques.py` | Genera el diagrama de bloques del sistema. |
| `tablero_control.log` | Tablero de control completo: una línea por ciclo de scan con temperatura, tensión medida, error, señal de control, potencias y zona de operación. |
| `g0_diagrama_bloques.png` | Diagrama de bloques del lazo. |
| `g1_temperatura.png` | Variable controlada: temperatura del pasillo frío. |
| `g2_senal_control.png` | Variable manipulada: señal de control u(t). |
| `g3_carga.png` | Carga térmica, potencia frigorífica entregada y capacidad disponible. |
| `g4_error.png` | Señal de error e(t). |
| `g5_comparacion_p_pi.png` | Comparación entre control proporcional puro y proporcional-integral. |

## Escenario simulado

La sala arranca a 26,5 °C con consigna de 22 °C. Durante el ensayo se introducen cuatro perturbaciones:

| Minuto | Perturbación | Tipo |
|---|---|---|
| 45 | Ola de calor: +13 °C exterior y −12 % de capacidad frigorífica | Externa, rampa |
| 100 | Alta de un rack nuevo: +15 kW | Interna, escalón permanente |
| 150 | Apertura de puerta: +25 kW durante 90 s | Externa, impulso |
| 190 | Falla de una unidad CRAH durante 5 min, hasta que arranca la de reserva | Interna, escalón temporal |

Resultados principales:

| Indicador | Control PI | Control P |
|---|---|---|
| Error medio en régimen permanente (min 133-148) | +0,02 °C | −5,66 °C |
| Tiempo fuera del rango ASHRAE (18-27 °C) | 0,2 % | 55 % |
| Temperatura máxima | 27,3 °C | 32,6 °C |

## Modificar el ensayo

Todos los parámetros están declarados como constantes al comienzo de `simulacion_crah.py`: consigna, capacidad instalada, sintonía del controlador (`TAU_LC`, `TI`, `TS`), cadena de medición y umbrales. Los instantes de las perturbaciones están en la sección 2 del archivo. La función `simular(con_integral=False)` reproduce el ensayo con control proporcional puro.
