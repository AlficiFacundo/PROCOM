"""
    PRBS9-> RC Tx -> Salida de muestras
    clock      -> F_CLK = os/T = 100 MHz
    i_rst      -> reset sincrono, limpia PRBS9, shift registers y contador CnT
    i_sw[0]    -> EnbTx 
    i_sw[1]    -> EnbRx 
    i_sw[3:2]  -> Phase 
"""
from collections import namedtuple
import numpy as np
 
F_CLK, OS, ROLLOFF, SPAN = 100e6, 4, 0.5, 6
SEED_I, SEED_Q = 0x1AA, 0x1FE
 
CtrlSig = namedtuple("CtrlSig", "reset_all reset_ber enb_tx enb_rx phase")
 
 
def decode_i_sw(i_sw):
    return dict(enb_tx=i_sw & 1, enb_rx=(i_sw >> 1) & 1, phase=(i_sw >> 2) & 0b11)
 
 
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
 
 
def rc_coefficients(rolloff, span, sps):
    t, h = rcosine(rolloff, 1.0, sps, span, norm=False)
    if rolloff:
        t_sing = 1 / (2 * rolloff)
        h[np.isclose(np.abs(t), t_sing) | ~np.isfinite(h)] = (np.pi / 4) * np.sinc(t_sing)
    N = span * sps
    h = h[:N] if len(h) > N else np.pad(h, (0, N - len(h)))
    return h / np.max(np.abs(h))
 
 
def polyphase_bank(h, span, sps):
    """branches[p][i] = h[p + i*sps]"""
    return h.reshape(span, sps).T.copy()
 
 
class RCBranch:
    """PRBS9 + shift register de simbolos + filtro polifasico, para I o Q."""
    def __init__(self, seed, bank, span):
        self.prbs, self.bank = PRBS9(seed), bank
        self.shift = np.zeros(span)
 
    def reset(self):
        self.prbs.reset()
        self.shift[:] = 0
 
    def new_symbol(self):
        bit = self.prbs.step()
        self.shift = np.roll(self.shift, 1)
        self.shift[0] = 1.0 if bit == 0 else -1.0
        return bit
 
    def sample(self, phase):
        return float(self.bank[phase] @ self.shift)
 
 
class QPSKTxChain:
    def __init__(self, os=OS, rolloff=ROLLOFF, span=SPAN, seed_I=SEED_I, seed_Q=SEED_Q):
        self.os, self.h = os, rc_coefficients(rolloff, span, os)
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
 
    def reset_stats(self):
        self.err = self.tot = 0
 
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
        self.err += rx_bit != self.ref.step()
        self.tot += 1
 
    @property
    def ber(self):
        return None if self.tot == 0 else self.err / self.tot
 
 
class Control:
    """Detecta cambios de fase (i_sw[3:2]) -> dispara reset_stats en el BER."""
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
    """Barre las 'os' fases via i_sw[3:2] y mide el BER resultante en cada una."""
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
    print(f"Coeficientes RC:\n{np.round(sistema.tx.h, 4)}\n")
    print(f"Retardo por fase: {sistema.delay_by_phase}\n")
    for fase, (ber_i, ber_q) in resultados.items():
        print(f"Fase {fase}: BER_I = {ber_i:.5f}   BER_Q = {ber_q:.5f}")
    mejor = min(resultados, key=lambda f: sum(resultados[f]))
    print(f"\nMejor fase: {mejor}")