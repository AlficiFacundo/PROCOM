"""
Resoluciones:
  - Coeficientes del filtro RC y acumulador del sumador: S(9,7)
  - Simbolos (+1/-1): representables exactos en S(9,7), sin cuantizar.

Metodologia de retardos: se mantiene la misma granularidad que el modelo float
(un unico delay_symbols, igual al offset del pico del filtro cuantizado) -> el retardo de cuantizacion
no cambia el retardo de grupo del filtro de forma apreciable.

Redondeo del acumulador: se re-cuantiza a S(9,7) DESPUES DE CADA suma parcial, simulando un
sumador registrado etapa a etapa.
"""
from collections import namedtuple
import numpy as np
from tool._fixedInt import DeFixedInt
import os as os_module

 
F_CLK, OS, ROLLOFF, SPAN = 100e6, 4, 0.5, 6
SEED_I, SEED_Q = 0x1AA, 0x1FE
S_INT, S_FRAC = 9, 7
BER_CNT_WIDTH = 24   
WORD_WIDTH = S_INT  # ancho total S(9,7) = 9 bits
 
CtrlSig = namedtuple("CtrlSig", "reset_all reset_ber enb_tx enb_rx phase")
 
 
def decode_i_sw(i_sw):
    return dict(enb_tx=i_sw & 1, enb_rx=(i_sw >> 1) & 1, phase=(i_sw >> 2) & 0b11)
 
 
def quantize(x):
    """Cuantiza un float a S(9,7) con redondeo y saturacion, devuelve el float resultante."""
    v = DeFixedInt(S_INT, S_FRAC, signedMode='S', roundMode='round', saturateMode='saturate')
    v.value = float(x)
    return v.fValue
 
 
class PRBS9:
    def __init__(self, seed):
        assert seed & 0x1FF, "seed no puede ser 0"
        self._seed = seed & 0x1FF
        self.state = self._seed
 
    def step(self):
        bit = self.state & 1
        fb = bit ^ ((self.state >> 4) & 1)
        self.state = (self.state >> 1) | (fb << 8)
        return bit
 
    def reset(self):
        self.state = self._seed
 
 
def rcosine(beta, Tbaud, os, Nbaud, norm):
    t = np.arange(-0.5 * Nbaud * Tbaud, 0.5 * Nbaud * Tbaud, Tbaud / os)
    with np.errstate(divide="ignore", invalid="ignore"):
        y = np.sinc(t / Tbaud) * np.cos(np.pi * beta * t / Tbaud) / (
            1 - (2 * beta * t / Tbaud) ** 2)
    return (t, y / np.sqrt(np.sum(y ** 2))) if norm else (t, y)
 
 
def rc_coefficients_float(rolloff, span, sps):
    t, h = rcosine(rolloff, 1.0, sps, span, norm=False)
    if rolloff:
        t_sing = 1 / (2 * rolloff)
        h[np.isclose(np.abs(t), t_sing) | ~np.isfinite(h)] = (np.pi / 4) * np.sinc(t_sing)
    N = span * sps
    h = h[:N] if len(h) > N else np.pad(h, (0, N - len(h)))
    bank = h.reshape(span, sps).T
    peak = max(np.sum(np.abs(bank[p])) for p in range(sps))
    return h / peak
 
 
def rc_coefficients_fixed(rolloff, span, sps):
    """Los mismos coeficientes, cuantizados una vez a S(9,7)."""
    h_float = rc_coefficients_float(rolloff, span, sps)
    return np.array([quantize(c) for c in h_float])
 
 
def polyphase_bank(h, span, sps):
    """branches[p][i] = h[p + i*sps]."""
    return h.reshape(span, sps).T.copy()
 
 
class RCBranch:
    """
    PRBS9 + shift register de simbolos + filtro polifasico, en punto fijo.
    El sumador se redondea a S(9,7) despues de cada producto acumulado.
    """
    def __init__(self, seed, bank, span):
        self.prbs, self.bank = PRBS9(seed), bank
        self.shift = np.zeros(span)   # simbolos +-1, exactos, sin cuantizar
 
    def reset(self):
        self.prbs.reset()
        self.shift[:] = 0
 
    def new_symbol(self):
        bit = self.prbs.step()
        self.shift = np.roll(self.shift, 1)
        self.shift[0] = 1.0 if bit == 0 else -1.0
        return bit
 
    def sample(self, phase):
        """Acumulador: suma secuencial de 6 terminos, redondeando a S(9,7) en cada paso."""
        coefs = self.bank[phase]
        acc = 0.0
        for c, s in zip(coefs, self.shift):
            term = c if s > 0 else -c   # negar/no negar (simbolo +-1 exacto)
            acc = quantize(acc + term)  # re-cuantiza DESPUES de cada suma parcial
        return acc
 
 
class QPSKTxChain:
    def __init__(self, os=OS, rolloff=ROLLOFF, span=SPAN, seed_I=SEED_I, seed_Q=SEED_Q):
        self.os = os
        self.h = rc_coefficients_fixed(rolloff, span, os)
        bank = polyphase_bank(self.h, span, os)
        self.I, self.Q = RCBranch(seed_I, bank, span), RCBranch(seed_Q, bank, span)
        self.count, self.last_phase = 0, None
        self.tx_bits_I, self.tx_bits_Q = [], []
 
    def reset(self):
        self.I.reset(); self.Q.reset(); self.count = 0
 
    def tick(self, i_rst, i_sw):
        if i_rst:
            self.reset()
            return None, None
        if not (i_sw & 1):
            return None, None
 
        phase, new_symbol = self.count, self.count == 0
        self.count = (self.count + 1) % self.os
        self.last_phase = phase
 
        if new_symbol:
            self.tx_bits_I.append(self.I.new_symbol())
            self.tx_bits_Q.append(self.Q.new_symbol())
 
        return self.I.sample(phase), self.Q.sample(phase)
 
 
class BERCounter:
    def __init__(self, seed):
        self.ref = PRBS9(seed)
        self._last_delay = None
        self.reset_full()
 
    def _new_counter(self):
        return DeFixedInt(BER_CNT_WIDTH, 0, signedMode='U',
                           roundMode='trunc', saturateMode='saturate')
 
    def reset_stats(self):
        self._err = self._new_counter()
        self._tot = self._new_counter()
 
    def reset_full(self):
        self.ref.reset()
        self._last_delay = None
        self.pending = 0
        self.reset_stats()
 
    def set_delay(self, new_delay):
        """Llamar cada ciclo con el delay de la fase actual."""
        if self._last_delay is None:
            self.pending = new_delay              
        elif new_delay != self._last_delay:
            ajuste = new_delay - self._last_delay
            if ajuste > 0:
                self.pending += ajuste             
            else:
                for _ in range(-ajuste):
                    self.ref.step()                
        self._last_delay = new_delay
 
    def process(self, rx_bit):
        if self.pending > 0:
            self.pending -= 1
            return
        if rx_bit != self.ref.step():
            self._err.value = self._err.value + 1   
        self._tot.value = self._tot.value + 1
 
    @property
    def errores(self):
        return self._err.value
 
    @property
    def total(self):
        return self._tot.value
 
    @property
    def ber(self):
        return None if self.total == 0 else self.errores / self.total
 
 
class Control:
    def __init__(self):
        self._last = None
 
    def reset(self):
        self._last = None
 
    def decode(self, i_rst, i_sw):
        sw = decode_i_sw(i_sw)
        reset_ber = not i_rst and self._last is not None and sw["phase"] != self._last
        self._last = None if i_rst else sw["phase"]
        return CtrlSig(bool(i_rst), reset_ber, bool(sw["enb_tx"]), bool(sw["enb_rx"]), sw["phase"])
 
 
class QPSKSystem:
    def __init__(self, os=OS, rolloff=ROLLOFF, span=SPAN, seed_I=SEED_I, seed_Q=SEED_Q):
        self.tx = QPSKTxChain(os, rolloff, span, seed_I, seed_Q)
        self.control, self.os = Control(), os
        bank = self.tx.I.bank
        self.delay_by_phase = [int(np.argmax(np.abs(bank[p]))) for p in range(os)]
 
        self.ber_I, self.ber_Q = BERCounter(seed_I), BERCounter(seed_Q)
        self.rx_bits_I, self.rx_bits_Q = [], []
 
    def reset(self):
        self.tx.reset(); self.ber_I.reset_full(); self.ber_Q.reset_full(); self.control.reset()
 
    def tick(self, i_rst, i_sw):
        ctrl = self.control.decode(i_rst, i_sw)
        if ctrl.reset_all:
            self.reset(); return
        if ctrl.reset_ber:
            self.ber_I.reset_stats(); self.ber_Q.reset_stats()
        if not ctrl.enb_tx:
            return
 
        sI, sQ = self.tx.tick(False, i_sw)
        if not ctrl.enb_rx or self.tx.last_phase != ctrl.phase:
            return
 
        delay = self.delay_by_phase[ctrl.phase]
        self.ber_I.set_delay(delay)
        self.ber_Q.set_delay(delay)
 
        for sample, ber, bits in ((sI, self.ber_I, self.rx_bits_I), (sQ, self.ber_Q, self.rx_bits_Q)):
            bit = 0 if sample >= 0 else 1
            ber.process(bit)
            bits.append(bit)
 
 
def scan_phases(symbols_per_phase=200, os=OS):
    sys_ = QPSKSystem(os=os)
    sys_.tick(i_rst=True, i_sw=0)
    resultados = {}
    for fase in range(os):
        i_sw = (fase << 2) | 0b011
        for _ in range(symbols_per_phase * os):
            sys_.tick(i_rst=False, i_sw=i_sw)
        resultados[fase] = (sys_.ber_I.ber, sys_.ber_Q.ber)
    return sys_, resultados
 
 
if __name__ == "__main__":
    sistema, resultados = scan_phases(symbols_per_phase=200)
    print(f"Coeficientes RC cuantizados S({S_INT},{S_FRAC}):\n{np.round(sistema.tx.h, 5)}\n")
    print(f"Retardo por fase: {sistema.delay_by_phase}\n")
    for fase, (ber_i, ber_q) in resultados.items():
        print(f"Fase {fase}: BER_I = {ber_i:.5f}   BER_Q = {ber_q:.5f}   "
              f"(tot_I={sistema.ber_I.total})")
    mejor = min(resultados, key=lambda f: sum(resultados[f]))
    print(f"\nMejor fase: {mejor}")

# --- Generación de archivo .mem para Vector Matching (VM) ---
def float_to_twos_complement_hex(x, width=WORD_WIDTH, frac=S_FRAC):
    """
    Devuelve el codigo en complemento a 2, como string hex de ancho fijo.
    """
    v = DeFixedInt(width, frac, signedMode='S', roundMode='round', saturateMode='saturate')
    v.value = float(x)
    mask = (1 << width) - 1
    raw = v.value & mask                      # complemento a 2, sin signo
    nibbles = -(-width // 4)                   
    return format(raw, f'0{nibbles}X')
 
 
def generate_vm_files(symbols_per_phase=50, os=OS, out_dir=None):
    if out_dir is None:
        base_dir = os_module.path.dirname(os_module.path.abspath(__file__))
        out_dir = os_module.path.join(base_dir, "VM_mems")
    os_module.makedirs(out_dir, exist_ok=True)
 
    tx = QPSKTxChain(os=os)
 
    lines_i_rst, lines_i_sw = [], []
    lines_sample_I, lines_sample_Q = [], []
 
    def log_cycle(i_rst, i_sw, sample_I, sample_Q):
        lines_i_rst.append(str(int(i_rst)))
        lines_i_sw.append(format(i_sw & 0xF, '04b'))
        # Si Tx esta deshabilitado o en reset, no hay muestra valida:
        # se vuelca 0x000 (DUT y golden deben coincidir en ese estado quieto)
        sI = 0.0 if sample_I is None else sample_I
        sQ = 0.0 if sample_Q is None else sample_Q
        lines_sample_I.append(float_to_twos_complement_hex(sI))
        lines_sample_Q.append(float_to_twos_complement_hex(sQ))
 
    # --- Pulso de reset inicial ---
    sI, sQ = tx.tick(i_rst=True, i_sw=0)
    log_cycle(True, 0, sI, sQ)
 
    # --- Barrido de las 4 fases, EnbTx=1, EnbRx=1 ---
    for fase in range(os):
        i_sw = (fase << 2) | 0b011
        for _ in range(symbols_per_phase * os):
            sI, sQ = tx.tick(i_rst=False, i_sw=i_sw)
            log_cycle(False, i_sw, sI, sQ)
 
    files = {
        "stim_i_rst.mem": lines_i_rst,
        "stim_i_sw.mem": lines_i_sw,
        "expected_sample_I.mem": lines_sample_I,
        "expected_sample_Q.mem": lines_sample_Q,
    }
    for fname, lines in files.items():
        with open(f"{out_dir}/{fname}", "w") as f:
            f.write("\n".join(lines) + "\n")
 
    return tx, files
 
 
if __name__ == "__main__":
    tx, files = generate_vm_files(symbols_per_phase=50)
    for fname, lines in files.items():
        print(f"{fname}: {len(lines)} lineas, primeras 5:")
        print("  " + "\n  ".join(lines[:5]))
        print()