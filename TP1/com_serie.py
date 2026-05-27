import time
import serial

#############################################
# Nota:
# Comentar esta linea si se utiliza el puerto serie
# con la FPGA
ser = serial.serial_for_url('loop://', timeout=1)

#############################################
# Nota:
# Descomentar esta linea si se utiliza el puerto serie
# con la FPGA
#############################################
# ser = serial.Serial(
#     port     = '/dev/ttyUSB1', #COM3
#     baudrate = 9600,
#     parity   = serial.PARITY_NONE,
#     stopbits = serial.STOPBITS_ONE,
#     bytesize = serial.EIGHTBITS
# )

ser.isOpen()
ser.timeout=None
ser.flushInput()
ser.flushOutput()

print('Ingrese un comando:\n')
def pedir_comando() :
    char_v = []
    data = input("ToSent: ")
    if data == 'exit':
        if ser.isOpen():
            ser.close()
        exit(0)
    else:
        # Arma el vector a transmitir
        for ptr in range(len(data)):
            char_v.append(data[ptr])
        #print(char_v)
        
        for ptr in range(len(char_v)):
            ser.write(char_v[ptr].encode())
            time.sleep(0.01)

        out = ''
        while ser.inWaiting() > 0:
            out += ser.read(1).decode()

        if out != '':
            print(">> " + out)
    return out
        