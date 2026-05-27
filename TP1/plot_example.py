import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import numpy as np
# plt.style.use('ggplot')  # otros: 'seaborn', 'classic', 'bmh', 'dark_background'
# plt.style.use('dark_background')  # otros: 'seaborn', 'classic', 'bmh', 'dark_background'
plt.style.use('bmh')  # otros: 'seaborn', 'classic', 'bmh', 'dark_background'
# plt.style.use('classic')  # otros: 'seaborn', 'classic', 'bmh', 'dark_background'


t = np.linspace(0,2*np.pi,1000)
data = 2*np.sin(t)

plt.figure(figsize=(8, 6), dpi=100)
plt.subplot(3,2,1)
plt.plot(t,data)
plt.title('plt.plot() - Sinusoide', fontsize=16, color='navy')
plt.xlabel('Tiempo [s]', fontsize=12)
plt.ylabel('Amplitud [V]', fontsize=12)
plt.subplot(3,2,2)
# Datos
tipos_fibra = ['Monomodo', 'Multimodo OM1', 'Multimodo OM2', 'Multimodo OM3']
atenuaciones = [0.20, 3.50, 2.50, 2.00]

# Gráfico de barras
plt.bar(tipos_fibra, atenuaciones, color='navy')

# Títulos y etiquetas
plt.title('plt.bar() - Atenuación en diferentes tipos de fibra óptica (1550 nm)')
plt.xlabel('Tipo de Fibra')
plt.ylabel('Atenuación (dB/km)')
plt.subplot(3,2,3)
total = 23
messi = 8
cr7 = 5
resto = total-messi-cr7
por = np.array([messi, cr7, resto])
plt.pie(por/total)
plt.legend(["Messi","CR7","Resto"])
plt.title('plt.pie() - Balones de Oro S. XXI', fontsize=16, color='navy')
plt.subplot(3,2,4)
size_ = 10000
caras = np.array([1,2,3,4,5,6])
print(caras)
cara = np.random.randint(1,7,int(size_))
freq = np.zeros(6)
for ii,c in enumerate(caras):
    aux = np.zeros(int(size_))
    aux[cara == c] = 1
    freq[ii] = np.sum(aux)
print(freq)
print(cara)
# plt.hist(cara,bins = caras,width=0.3)
data = np.random.randn(1000)  # normal distribution centered around 0
# Define bins centered on zero, for example from -5 to 5 with step 1
bins = np.arange(1, 7, 1)  # bins from -5 to 5 inclusive
plt.hist(cara, [ii for ii in range(1,8)], edgecolor='black',width=0.3,align="mid",density=False)
# plt.title('Histogram Centered Around Zero')
plt.title('plt.bar() - Frecuencia cara de un dado', fontsize=16, color='navy')
plt.xlabel('Cara Dado', fontsize=12)
plt.xlim(1,6.5)
plt.ylabel('Freq. de Aparición', fontsize=12)
ax = plt.subplot2grid((3, 2), (2, 0), colspan=2)
# Datos
distancia = [1, 2, 3, 4, 5]
potencia = [-2.1, -3.5, -5.9, -7.8, -9.7]

# Gráfico de dispersión
plt.scatter(distancia, potencia, color='red', marker='o')

# Títulos y etiquetas
plt.title('Dispersión de Potencia Óptica vs Distancia')
plt.xlabel('Distancia (km)')
plt.ylabel('Potencia (dBm)')

# Mostrar cuadrícula
plt.grid(True)
#plt.savefig("/home/Santi/Celero/Fundación/Procom/Procom/cursoProcom/parte01_python/doc/figures/example_plt.jpg")
plt.show()


