import sys
import serial

DEV_LED0 = 0x00
DEV_LED1 = 0x01
DEV_LED2 = 0x02
DEV_LED3 = 0x03
DEV_READ_SW = 0x04


def build_frame(device, data=b''):
    size = len(data)
    is_long = size > 15

    if is_long:
        b0 = (0b101 << 5) | (1 << 4)
        b1 = (size >> 8) & 0xFF
        b2 = size & 0xFF
        trailer = (0b010 << 5) | (1 << 4)
    else:
        b0 = (0b101 << 5) | (size & 0x0F)
        b1 = 0x00
        b2 = 0x00
        trailer = (0b010 << 5) | (size & 0x0F)

    b3 = device
    return bytes([b0, b1, b2, b3]) + data + bytes([trailer])


def parse_response(ser):
    header = ser.read(4)
    if len(header) < 4:
        return None, None

    b0 = header[0]
    if (b0 >> 5) != 0b101:
        return None, None

    is_long = (b0 >> 4) & 0x01
    device = header[3]
    size = ((header[1] << 8) | header[2]) if is_long else (b0 & 0x0F)

    data = ser.read(size) if size > 0 else b''
    ser.read(1)  # descarta el byte de fin de trama
    return device, data


def set_led(ser, led, r, g, b):
    color = (r & 1) | ((g & 1) << 1) | ((b & 1) << 2)
    ser.write(build_frame(led, bytes([color])))


def read_switches(ser):
    ser.write(build_frame(DEV_READ_SW, b''))
    device, data = parse_response(ser)
    return data[0] if data else None


def main():
    portUSB = sys.argv[1]

    ser = serial.Serial(
        port='/dev/ttyUSB{}'.format(int(portUSB)),
        baudrate=115200,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=2
    )

    print('Comandos: led <0-3> <r 0/1> <g 0/1> <b 0/1>  |  sw  |  exit')

    while True:
        cmd = input("<< ").strip().split()
        if not cmd:
            continue

        if cmd[0] == 'exit':
            ser.close()
            break

        elif cmd[0] == 'led' and len(cmd) == 5:
            led = int(cmd[1])
            r, g, b = int(cmd[2]), int(cmd[3]), int(cmd[4])
            if 0 <= led <= 3:
                set_led(ser, led, r, g, b)
            else:
                print("LED invalido (0-3)")

        elif cmd[0] == 'sw':
            val = read_switches(ser)
            if val is not None:
                print(">> switches = {0:04b}".format(val))
            else:
                print("Sin respuesta")

        else:
            print("Comando no reconocido")


if __name__ == '__main__':
    main()