"""
Grafica el volcado de la memoria de logueo del DSP.
Terminal:  python3 graph.py log_fase0.csv [n_muestras]
"""

import sys
import csv
import matplotlib.pyplot as plt

N_PHASES = 4
OFFSET = 0          


def leer_csv(ruta):
    addr, s_I, s_Q = [], [], []
    with open(ruta, newline='') as f:
        for fila in csv.DictReader(f):
            addr.append(int(fila['addr']))
            s_I.append(int(fila['sample_I']))
            s_Q.append(int(fila['sample_Q']))
    return addr, s_I, s_Q


def figura_fases(addr, s_I, s_Q, ruta):
    """Una fase por panel: la senal completa de fondo y encima las muestras
    que le tocarian al decimador con esa fase seleccionada."""
    fig, axes = plt.subplots(2, 2, figsize=(12, 7), sharex=True, sharey=True)
    y = max(max(map(abs, s_I)), max(map(abs, s_Q))) * 1.15

    for fase in range(N_PHASES):
        ax = axes[fase // 2][fase % 2]
        ax.plot(addr, s_I, color='0.75', linewidth=0.8, zorder=1)
        ax.axhline(0, color='0.5', linewidth=0.8, zorder=1)

        sel = [i for i in range(len(addr))
               if (addr[i] + OFFSET) % N_PHASES == fase]
        ax.plot([addr[i] for i in sel], [s_I[i] for i in sel],
                'o', markersize=5, color='tab:red', zorder=3)
        ax.vlines([addr[i] for i in sel], 0, [s_I[i] for i in sel],
                  color='tab:red', alpha=0.35, linewidth=1.0, zorder=2)

        ax.set_ylim(-y, y)
        ax.set_title('Fase {0}'.format(fase))
        ax.grid(alpha=0.3)
        if fase >= 2:
            ax.set_xlabel('Direccion de memoria')
        if fase % 2 == 0:
            ax.set_ylabel('Amplitud (canal I)')

    fig.suptitle('Instantes de muestreo del decimador sobre la salida del filtro Tx')
    plt.tight_layout()
    salida = ruta.rsplit('.', 1)[0] + '_fases.png'
    plt.savefig(salida, dpi=150)
    print("  {0}".format(salida))


def figura_ojos(s_I, s_Q, ruta):
    """Ojos de I y de Q, cada uno en su propio eje."""
    span = 2 * N_PHASES + 1          
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

    for ax, datos, nombre, color in ((axes[0], s_I, 'I', 'tab:blue'),
                                     (axes[1], s_Q, 'Q', 'tab:green')):
        n = 0
        for ini in range(0, len(datos) - span, N_PHASES):
            ax.plot(range(-N_PHASES, N_PHASES + 1), datos[ini:ini + span],
                    color=color, alpha=0.18, linewidth=0.9)
            n += 1
        ax.axvline(0, color='0.4', linestyle='--', linewidth=1.0)
        ax.set_xlim(-N_PHASES, N_PHASES)
        ax.set_xticks(range(-N_PHASES, N_PHASES + 1))
        ax.set_xlabel('Muestras respecto del centro del simbolo')
        ax.set_ylabel('Amplitud')
        ax.set_title('Diagrama de ojo - Canal {0} ({1} Trazas)'.format(nombre, n))
        ax.grid(alpha=0.3)

    plt.tight_layout()
    salida = ruta.rsplit('.', 1)[0] + '_ojos.png'
    plt.savefig(salida, dpi=150)
    print("  {0}".format(salida))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    ruta = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 200

    addr, s_I, s_Q = leer_csv(ruta)
    addr, s_I, s_Q = addr[:n], s_I[:n], s_Q[:n]
    print("{0} muestras, I en [{1}, {2}], Q en [{3}, {4}]".format(
        len(s_I), min(s_I), max(s_I), min(s_Q), max(s_Q)))

    print("Figuras guardadas:")
    figura_fases(addr, s_I, s_Q, ruta)
    figura_ojos(s_I, s_Q, ruta)
    plt.show()


if __name__ == '__main__':
    main()