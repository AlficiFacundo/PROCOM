"""
Gráficos del filtro Tx del sistema QPSK, usando import de float_qpskchain.py o fp_qpskchain

-Bits transmitidos (PRBS9, ramas I y Q)
-Rta al impulso y en frecuencia del filtro Tx
-Salida (oversampleada) y diagrama de ojo del filtro Tx
-Constelación a la salida del filtro Tx, para cada una de las fases
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os

from fp_qpskchain import QPSKTxChain, F_CLK, OS, ROLLOFF, SPAN

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE_DIR, "Informe_lab4", "imagenes") + os.sep
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------------
# generar datos
# ---------------------------------------------------------------------
N_SYMBOLS = 300
tx = QPSKTxChain()
i_sw = 0b0001  # EnbTx=1

samples_I, samples_Q = [], []
for _ in range(N_SYMBOLS * OS):
    sI, sQ = tx.tick(False, i_sw)
    samples_I.append(sI)
    samples_Q.append(sQ)

samples_I = np.array(samples_I)
samples_Q = np.array(samples_Q)
h = tx.h
delay_symbols = int(np.argmax(np.abs(h)) // OS)

print(f"Simbolos simulados: {N_SYMBOLS} | Muestras generadas: {len(samples_I)}")
print(f"Retardo de grupo del filtro: {delay_symbols} simbolos")

# ---------------------------------------------------------------------
# func rta en freq y diagrama de ojo
# ---------------------------------------------------------------------
def resp_freq(filt, Ts, Nfreqs):
    H = []
    A = []
    filt_len = len(filt)
 
    freqs = np.matrix(np.linspace(0, 1.0 / (2.0 * Ts), Nfreqs))
    Lseq = 20.0 / (freqs[0, 1] * Ts)
    t = np.matrix(np.arange(0, Lseq)) * Ts
    Omega = 2.0j * np.pi * (t.transpose() * freqs)
    fin = np.exp(Omega)
 
    for i in range(0, np.size(fin, 1)):
        fout = np.convolve(np.squeeze(np.array(fin[:, i].transpose())), filt)
        mfout = abs(fout[filt_len:len(fout) - filt_len])
        afout = np.angle(fout[filt_len:len(fout) - filt_len])
        H.append(mfout.sum() / len(mfout))
        A.append(afout.sum() / len(afout))
 
    return [H, A, list(np.squeeze(np.array(freqs)))]
 
 
def eyediagram(data, n, offset, period):
    span = 2 * n
    segments = int(len(data) / span)
    xmax = (n - 1) * period
    xmin = -(n - 1) * period
    x = list(np.arange(-n, n) * period)
    xoff = offset
 
    plt.figure()
    for i in range(0, segments - 1):
        plt.plot(x, data[(i * span + xoff):((i + 1) * span + xoff)], 'b')
    plt.grid(True)
    plt.xlim(xmin, xmax)
    
# ---------------------------------------------------------------------
# 1) Bits transmitidos
# ---------------------------------------------------------------------
N_BITS_PLOT = 40
fig, axs = plt.subplots(2, 1, figsize=[12, 5], sharex=True)
axs[0].stem(tx.tx_bits_I[:N_BITS_PLOT])
axs[0].set_ylabel("Bit I")
axs[0].grid(True)
axs[1].stem(tx.tx_bits_Q[:N_BITS_PLOT])
axs[1].set_ylabel("Bit Q")
axs[1].set_xlabel("Indice de simbolo")
axs[1].grid(True)
fig.suptitle("Bits transmitidos (PRBS9)")
fig.savefig(OUT + "01_bits_transmitidos_fp.png", dpi=110, bbox_inches="tight")
plt.close(fig)

# ---------------------------------------------------------------------
# 2) Rta al impulso y en frecuencia del filtro Tx
# ---------------------------------------------------------------------
t = (np.arange(len(h)) - len(h) / 2) / OS 

fig = plt.figure(figsize=[14, 5])
plt.plot(t, h, "o-", linewidth=2.0, color="tab:blue",
         label=fr"$\beta={ROLLOFF}$, span={SPAN} baudios, os={OS}")
plt.legend()
plt.grid(True)
plt.xlabel("Tiempo [simbolos]")
plt.ylabel("Magnitud")
plt.title("Respuesta al impulso - Filtro Raised Cosine Tx")
fig.savefig(OUT + "02_respuesta_impulso_fp.png", dpi=110, bbox_inches="tight")
plt.close(fig)

Ts = 1.0 / F_CLK
H, A, F = resp_freq(h, Ts, Nfreqs=256)

fig = plt.figure(figsize=[14, 6])
plt.semilogx(F, 20 * np.log10(H), "b", linewidth=2.0,
             label=fr"$\beta={ROLLOFF}$")
plt.axvline(x=(1.0 / Ts) / 2.0, color="k", linewidth=1.5, linestyle="--",
            label="Nyquist (F_CLK/2)")
plt.axhline(y=20 * np.log10(0.5), color="gray", linewidth=1.0, linestyle=":")
plt.legend(loc=3)
plt.grid(True)
plt.xlim(F[1], F[-1])
plt.xlabel("Frecuencia [Hz]")
plt.ylabel("Magnitud [dB]")
plt.title("Respuesta en frecuencia - Filtro Raised Cosine Tx")
fig.savefig(OUT + "03_respuesta_frecuencia_fp.png", dpi=110, bbox_inches="tight")
plt.close(fig)

# ---------------------------------------------------------------------
# 3) Salida del filtro Tx y diagrama de ojo
# ---------------------------------------------------------------------
N_MUESTRAS_PLOT = 200
inicio = delay_symbols * OS

fig, axs = plt.subplots(2, 1, figsize=[14, 6], sharex=True)
axs[0].plot(samples_I[inicio:inicio + N_MUESTRAS_PLOT], "r-", linewidth=1.5)
axs[0].set_ylabel("Amplitud I")
axs[0].grid(True)
axs[1].plot(samples_Q[inicio:inicio + N_MUESTRAS_PLOT], "g-", linewidth=1.5)
axs[1].set_ylabel("Amplitud Q")
axs[1].set_xlabel("Muestras")
axs[1].grid(True)
fig.suptitle("Salida del filtro Tx (oversampleada, os=%d)" % OS)
fig.savefig(OUT + "04_salida_filtro_tx_fp.png", dpi=110, bbox_inches="tight")
plt.close(fig)

eyediagram(samples_I[inicio:], OS, 0, SPAN)
plt.title("Diagrama de ojo - Rama I")
plt.xlabel("Muestras")
plt.ylabel("Amplitud")
plt.gcf().savefig(OUT + "05_ojo_I_fp.png", dpi=110, bbox_inches="tight")
plt.close()

eyediagram(samples_Q[inicio:], OS, 0, SPAN)
plt.title("Diagrama de ojo - Rama Q")
plt.xlabel("Muestras")
plt.ylabel("Amplitud")
plt.gcf().savefig(OUT + "06_ojo_Q_fp.png", dpi=110, bbox_inches="tight")
plt.close()

# ---------------------------------------------------------------------
# 4) Constelacion a la salida del filtro Tx, para cada fase
# ---------------------------------------------------------------------
fig, axs = plt.subplots(1, OS, figsize=[4 * OS, 4])
descarte_simbolos = delay_symbols + 2  

for fase in range(OS):
    dec_I = samples_I[fase::OS][descarte_simbolos:]
    dec_Q = samples_Q[fase::OS][descarte_simbolos:]

    axs[fase].plot(dec_I, dec_Q, ".", markersize=4)
    axs[fase].set_xlim(-2, 2)
    axs[fase].set_ylim(-2, 2)
    axs[fase].grid(True)
    axs[fase].set_title(f"Fase {fase}")
    axs[fase].set_xlabel("Real (I)")
    if fase == 0:
        axs[fase].set_ylabel("Imag (Q)")

fig.suptitle("Constelacion a la salida del filtro Tx, por fase")
fig.tight_layout()
fig.savefig(OUT + "07_constelacion_por_fase_fp.png", dpi=110, bbox_inches="tight")
plt.close(fig)
