#Consigna: Utiilizar filtro.py y com_serie.py para cargar los parámetros del filtro a traves de la com serie y 
# luego plotear con los ejemplos.
import com_serie
from filtro import RaisedCosineFilter
import matplotlib.pyplot as plt
import numpy as np
plt.style.use('dark_background')

filters = []

def analyze_command(data = '') :
    #Creo una función que me permite usar los datos recibidos para crear el filtro
    if data.startswith('generate_filter:') :
        data = data[len('generate_filter:'):]
        parametros = data.split(',')
        if len(parametros) != 4 and ',' in parametros :
            print("Se esperan 4 parámetros separados por comas.")
            return
        alpha = float(parametros[0])
        #Verifico que alpha sea menor que 1 y mayor que 0.
        if alpha < 0 or alpha > 1 :    
            print("El parámetro alpha debe ser un número entre 0 y 1.")
            return
        #Cargo el resto de parámetros a la función del archivo filtro.py
        span = int(parametros[1])
        sps = int(parametros[2])
        if len(parametros) < 4 or parametros[3].lower() == 't' :
            rrc = True
        else:
            rrc = False
        filters.append(RaisedCosineFilter(alpha = alpha, span = span, sps = sps, rrc = rrc))
    elif data.startswith('plot_filter_freq:') :
        data = data[len('plot_filter_freq:'):]
        seleccion = data.split(',')
        filter_n = int(seleccion[0])
        if len(seleccion) < 2 or seleccion[1].lower() == 'c' :
            continuous = True
        else:
            continuous = False
        if filter_n < 0 or filter_n > len(filters) - 1 :
            print("Número de filtro no válido.")
            return
        plt.figure(figsize=(10, 5))
        filters[filter_n].plot(time_domain = False, freq_domain = True, actual = filter_n, continuous = continuous, unique = True)
        show_plots()
    elif data.startswith('plot_filter_time:') :
        data = data[len('plot_filter_time:'):]
        seleccion = data.split(',')
        filter_n = int(seleccion[0])
        if len(seleccion) < 2 or seleccion[1].lower() == 'c' :
            continuous = True
        else :
            continuous = False
        if filter_n < 0 or filter_n > len(filters) - 1 :
            print("Número de filtro no válido.")
            return
        plt.figure(figsize=(10, 5))
        filters[filter_n].plot(time_domain = True, freq_domain = False, actual = filter_n, continuous = continuous, unique = True)
        show_plots()
    elif data.startswith('plot_filter:') :
        data = data[len('plot_filter:'):]
        seleccion = data.split(',')
        filter_n = int(seleccion[0])
        if len(seleccion) < 2 or seleccion[1].lower() == 'c' :
            continuous = True
        else :
            continuous = False
        if filter_n < 0 or filter_n > len(filters) - 1 :
            print("Número de filtro no válido.")
            return
        plt.figure(figsize=(10, 5))
        filters[filter_n].plot(time_domain = True, freq_domain = True, actual = filter_n, continuous = continuous, unique = True)
        show_plots()
    elif data.startswith('plot_all_freq:') :
        plt.figure(figsize=(10, 5*len(filters)))
        data = data[len('plot_all_freq:'):]
        actual = 0
        if data.lower() == 'c' or data == '' :
            continuous = True
        else :
            continuous = False
        for i in range(len(filters)) :
            filters[i].plot(time_domain = False, freq_domain = True, actual = actual, continuous = continuous, unique = False)
            actual = actual+1
        show_plots()
    elif data.startswith('plot_all_time:') :
        plt.figure(figsize=(10, 5*len(filters)))
        data = data[len('plot_all_time:'):]
        actual = 0
        if data.lower() == 'c' or data == '' :
            continuous = True
        else :
            continuous = False
        for i in range(len(filters)) :
            filters[i].plot(time_domain = True, freq_domain = False, actual = actual, continuous = continuous, unique = False)
            actual=actual+1
        show_plots()
    elif data.startswith('plot_simult_time:') :
        plt.figure(figsize=(10, 5))
        data = data[len('plot_simult_time:'):]
        actual = 0
        if data.lower() == 'c' or data == '' :
            continuous = True
        else :
            continuous = False
        for i in range(len(filters)) :
            filters[i].plot(time_domain = True, freq_domain = False, actual = actual, continuous = continuous, unique = True)
            actual = actual+1
        show_plots()
    elif data.startswith('plot_simult_freq:') :
        plt.figure(figsize=(10, 5))
        data = data[len('plot_simult_freq:'):]
        actual = 0
        if data.lower() == 'c' or data == '' :
            continuous = True
        else :
            continuous = False
        for i in range(len(filters)) :
            filters[i].plot(time_domain = False, freq_domain = True, actual = actual, continuous = continuous, unique = True)
            actual = actual+1
        show_plots()
    elif data.startswith('plot_simult_all:') :
        plt.figure(figsize=(10, 5))
        data = data[len('plot_simult_all:'):]
        actual = 0
        if data.lower() == 'c' or data == '' :
            continuous = True
        else :
            continuous = False
        for i in range(len(filters)) :
            filters[i].plot(time_domain = True, freq_domain = True, actual = actual, continuous = continuous, unique = True)
            actual = actual+1
        show_plots()
    else :
        print("Comando desconocido.")

def plot_filter(self, time_domain = True, freq_domain = False, actual = None, continuous = False, unique = False) :
    t = (np.arange(len(self.taps))-len(self.taps)//2)/ self.sps
    
    if time_domain :
        if freq_domain :
            if unique :
                plt.subplot(1, 2, 1)
            else :
                plt.subplot(len(filters), 2, 2*actual + 1)
        else :
            if unique :
                plt.subplot(1, 1, 1)
            else :
                plt.subplot(len(filters), 1, actual+1)
        if continuous :
            plt.plot(t[:len(self.taps)], self.taps, label = f"Impulse Response from filter {actual}")
        else:
            plt.stem(t[:len(self.taps)], self.taps, label = f"Impulse Response from filter {actual}")
        plt.title(f"Raised Cosine Filter {actual} (Time Domain)")
        plt.xlabel("Time [symbol periods]")
        plt.ylabel("Amplitude")
        plt.grid(True)
        plt.legend()

    if freq_domain :
        H = np.fft.fftshift(np.fft.fft(self.taps, 1024))
        f = np.linspace(-0.5, 0.5, len(H), endpoint=False)
        if time_domain :
            if unique :
                plt.subplot(1, 2, 2)
            else :
                plt.subplot(len(filters), 2, 2*actual + 2)
        else :
            if unique :
                plt.subplot(1, 1, 1)
            else :
                plt.subplot(len(filters), 1, actual+1)
        if continuous :
            plt.plot(f, 20 * np.log10(np.abs(H) + 1e-6), label = f"Frequency Response from filter {actual} [dB]")
        else :
            plt.stem(f, 20 * np.log10(np.abs(H) + 1e-6), label = f"Frequency Response from filter {actual} [dB]")
        plt.title(f"Raised Cosine Filter {actual} (Frequency Domain)")
        plt.xlabel("Normalized Frequency [×π rad/sample]")
        plt.ylabel("Magnitude [dB]")
        plt.grid(True)
        plt.legend()

def show_plots() :
    plt.tight_layout()
    plt.show()

RaisedCosineFilter.plot = plot_filter
while True :
    comando = com_serie.pedir_comando()
    if comando != '' :
        analyze_command(comando)