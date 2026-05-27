import numpy as np
import matplotlib.pyplot as plt

class RaisedCosineFilter:
    def __init__(self, alpha=0.25, span=6, sps=8, rrc=True):
        """
        Filtro de coseno realzado o raíz de coseno realzado.
        
        Parámetros:
        - alpha: Factor de roll-off (0 <= alpha <= 1)
        - span: Duración total del filtro en símbolos
        - sps: Muestras por símbolo
        - rrc: Si True, genera raíz de coseno realzado; si False, coseno realzado
        """
        self.alpha = alpha
        self.span = span
        self.sps = sps
        self.rrc = rrc
        self.taps = self._generate_filter()

    def _generate_filter(self):

        T = 1  # Duración del símbolo (normalizado)
        N = self.span * self.sps
        t = np.arange(-N//2, N//2 + 1) / self.sps

        if self.rrc:
            # Filtro Root Raised Cosine
            h = np.zeros_like(t)
            for i in range(len(t)):
                ti = t[i]
                if ti == 0.0:
                    h[i] = 1.0 - self.alpha + (4 * self.alpha / np.pi)
                elif abs(ti) == T / (4 * self.alpha):
                    h[i] = (self.alpha / np.sqrt(2)) * (
                        ((1 + 2/np.pi) * (np.sin(np.pi/(4*self.alpha)))) +
                        ((1 - 2/np.pi) * (np.cos(np.pi/(4*self.alpha))))
                    )
                else:
                    h[i] = (np.sin(np.pi * ti * (1 - self.alpha) / T) +
                            4 * self.alpha * ti / T *
                            np.cos(np.pi * ti * (1 + self.alpha) / T)) / \
                           (np.pi * ti * (1 - (4 * self.alpha * ti / T) ** 2))
        else:
            # Filtro Raised Cosine clásico
            h = np.zeros_like(t)
            for i in range(len(t)):
                ti = t[i]
                if ti == 0.0:
                    h[i] = 1.0
                elif abs(ti) == T / (2 * self.alpha):
                    h[i] = (np.pi / 4) * np.sinc(1 / (2 * self.alpha))
                else:
                    h[i] = np.sinc(ti / T) * \
                           np.cos(np.pi * self.alpha * ti / T) / \
                           (1 - (2 * self.alpha * ti / T) ** 2)

        return h

    def plot(self, time_domain=True, freq_domain=False):

        t = np.arange(-len(self.taps)//2, len(self.taps)//2 + 1) / self.sps

        if time_domain:
            plt.figure(figsize=(10, 4))
            plt.plot(t[:len(self.taps)], self.taps, label="Impulse Response")
            plt.title("Raised Cosine Filter (Time Domain)")
            plt.xlabel("Time [symbol periods]")
            plt.ylabel("Amplitude")
            plt.grid(True)
            plt.legend()
            plt.tight_layout()
            plt.show()

        if freq_domain:
            H = np.fft.fftshift(np.fft.fft(self.taps, 1024))
            f = np.linspace(-0.5, 0.5, len(H), endpoint=False)
            plt.figure(figsize=(10, 4))
            plt.plot(f, 20 * np.log10(np.abs(H) + 1e-6), label="Frequency Response [dB]")
            plt.title("Raised Cosine Filter (Frequency Domain)")
            plt.xlabel("Normalized Frequency [×π rad/sample]")
            plt.ylabel("Magnitude [dB]")
            plt.grid(True)
            plt.legend()
            plt.tight_layout()
            plt.show()

    def get_coefficients(self):
        return self.taps
#filtro = RaisedCosineFilter(alpha=1, span=10, sps=10, rrc=True)

#coef = filtro.get_coefficients()
#print(coef)

#filtro.plot(time_domain=True, freq_domain=True)
