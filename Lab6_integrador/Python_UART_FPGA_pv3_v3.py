import sys
import time
import serial

# --- Devices-------------------------------------------------
DEV_READ_SW  = 0x04
DEV_RF_WRITE = 0x10   
DEV_RF_READ  = 0x11   

# --- Comandos --------------------------------------------
CMD_RST     = 0x01
CMD_ENB_TX  = 0x02
CMD_ENB_RX  = 0x03
CMD_PHASE   = 0x04
CMD_RUN_LOG = 0x05
CMD_RD_LOG  = 0x06
CMD_ADDR    = 0x07
CMD_RD_SEL  = 0x08
CMD_BER_RST = 0x09

# --- Codigos ---------------------------------------------------
RD_LOG_DATA   = 0x0
RD_MEM_FULL   = 0x1
RD_SAMP_I_LO  = 0x2
RD_SAMP_I_HI  = 0x3
RD_SAMP_Q_LO  = 0x4
RD_SAMP_Q_HI  = 0x5
RD_ERROR_I_LO = 0x6
RD_ERROR_I_HI = 0x7
RD_ERROR_Q_LO = 0x8
RD_ERROR_Q_HI = 0x9
RD_SWITCHES   = 0xA
RD_STATUS     = 0xB
RD_BUILD_ID   = 0xC

MEM_WORDS = 32768        # BRAM de 32K x 32
WRITE_DELAY = 0.003      # Margen tras cada escritura del GPIO


# ---------------------------------------------------------------------------
# Capa de trama
# ---------------------------------------------------------------------------
def build_frame(device, data=b''):
    size = len(data)
    if size > 15:
        b0, b1, b2 = (0b101 << 5) | (1 << 4), (size >> 8) & 0xFF, size & 0xFF
        trailer = (0b010 << 5) | (1 << 4)
    else:
        b0, b1, b2 = (0b101 << 5) | (size & 0x0F), 0x00, 0x00
        trailer = (0b010 << 5) | (size & 0x0F)
    return bytes([b0, b1, b2, device]) + data + bytes([trailer])


def parse_response(ser, expect_device=None, max_resync=8):
    """Lee una trama, resincronizando si aparece basura antes del header."""
    b0 = None
    for _ in range(max_resync):
        raw = ser.read(1)
        if len(raw) < 1:
            return None, None
        if (raw[0] >> 5) == 0b101:
            b0 = raw[0]
            break
    if b0 is None:
        return None, None

    rest = ser.read(3)
    if len(rest) < 3:
        return None, None

    is_long = (b0 >> 4) & 0x01
    device = rest[2]
    size = ((rest[0] << 8) | rest[1]) if is_long else (b0 & 0x0F)

    data = ser.read(size) if size > 0 else b''
    if len(data) < size:
        return None, None

    trailer = ser.read(1)
    if len(trailer) < 1 or (trailer[0] >> 5) != 0b010:
        return None, None
    if expect_device is not None and device != expect_device:
        return None, None
    return device, data


# ---------------------------------------------------------------------------
# Register File
# ---------------------------------------------------------------------------
def rf_write(ser, command, field23=0):
    payload = bytes([command,
                     (field23 >> 16) & 0x7F,
                     (field23 >> 8) & 0xFF,
                     field23 & 0xFF])
    ser.write(build_frame(DEV_RF_WRITE, payload))
    ser.flush()
    time.sleep(WRITE_DELAY)


def rf_read(ser, rd_sel, retries=3):
    for _ in range(retries):
        ser.reset_input_buffer()
        ser.write(build_frame(DEV_RF_READ, bytes([rd_sel & 0xFF])))
        ser.flush()
        _, data = parse_response(ser, expect_device=DEV_RF_READ)
        if data is not None and len(data) >= 4:
            return (data[0] << 24) | (data[1] << 16) | (data[2] << 8) | data[3]
    return None


def read_switches(ser):
    ser.reset_input_buffer()
    ser.write(build_frame(DEV_READ_SW, b''))
    ser.flush()
    _, data = parse_response(ser, expect_device=DEV_READ_SW)
    return (data[0] & 0x0F) if data else None


def read_status(ser):
    val = rf_read(ser, RD_STATUS)
    if val is None:
        return None, None
    return val, {
        'rst':      val & 0x1,
        'enb_tx':   (val >> 1) & 0x1,
        'enb_rx':   (val >> 2) & 0x1,
        'phase':    (val >> 3) & 0x3,
        'run_log':  (val >> 5) & 0x1,
        'read_log': (val >> 6) & 0x1,
        'addr_log': (val >> 7) & 0x7FFF,
    }


def read_ber(ser):
    """Los contadores son de 64 bits, particionados en dos palabras de 32."""
    vals = [rf_read(ser, sel) for sel in
            (RD_SAMP_I_HI, RD_SAMP_I_LO, RD_SAMP_Q_HI, RD_SAMP_Q_LO,
             RD_ERROR_I_HI, RD_ERROR_I_LO, RD_ERROR_Q_HI, RD_ERROR_Q_LO)]
    if None in vals:
        return None
    sIh, sIl, sQh, sQl, eIh, eIl, eQh, eQl = vals
    return ((sIh << 32) | sIl, (sQh << 32) | sQl,
            (eIh << 32) | eIl, (eQh << 32) | eQl)


def read_log_word(ser, addr):
    rf_write(ser, CMD_ADDR, addr & 0x7FFF)
    rf_write(ser, CMD_RD_LOG, 1)
    word = rf_read(ser, RD_LOG_DATA)
    rf_write(ser, CMD_RD_LOG, 0)   # bloquear la lectura fuera del acceso
    return word


def split_iq(word):
    """log_wr_data = {sample_I[31:16], sample_Q[15:0]}, complemento a 2."""
    s_I = (word >> 16) & 0xFFFF
    s_Q = word & 0xFFFF
    return (s_I - 0x10000 if s_I >= 0x8000 else s_I,
            s_Q - 0x10000 if s_Q >= 0x8000 else s_Q)


# ---------------------------------------------------------------------------
# Comandos compuestos
# ---------------------------------------------------------------------------
def cmd_dumplog(ser, n, archivo):
    """Descarga n palabras de la memoria de logueo y las guarda en CSV."""
    rf_write(ser, CMD_RD_LOG, 1)
    filas, perdidas = [], 0
    t0 = time.time()
    for addr in range(n):
        rf_write(ser, CMD_ADDR, addr)
        word = rf_read(ser, RD_LOG_DATA)
        if word is None:
            perdidas += 1
            continue
        s_I, s_Q = split_iq(word)
        filas.append((addr, word, s_I, s_Q))
        if addr and addr % 500 == 0:
            print("   {0}/{1}...".format(addr, n))
    rf_write(ser, CMD_RD_LOG, 0)

    with open(archivo, 'w') as f:
        f.write("addr,word_hex,sample_I,sample_Q\n")
        for addr, word, s_I, s_Q in filas:
            f.write("{0},0x{1:08X},{2},{3}\n".format(addr, word, s_I, s_Q))
    print(">> {0} palabras en {1} ({2:.1f} s{3})".format(
        len(filas), archivo, time.time() - t0,
        ", {0} perdidas".format(perdidas) if perdidas else ""))


def cmd_bersweep(ser, ventana=0.3):
    """
    Mide la BER en las 4 fases de muestreo.
    """
    esperado = {0: 0.0, 1: 0.0, 2: 0.25, 3: 0.0}
    print("fase   samp_I        err_I         BER_I       BER_Q      esperado")
    for ph in (0, 1, 2, 3):
        rf_write(ser, CMD_PHASE, ph)
        rf_write(ser, CMD_ENB_TX, 1)
        rf_write(ser, CMD_ENB_RX, 1)
        rf_write(ser, CMD_RST, 1)
        rf_write(ser, CMD_RST, 0)
        time.sleep(ventana)
        rf_write(ser, CMD_ENB_RX, 0)     # congelar antes de las 8 lecturas
        time.sleep(0.02)

        res = read_ber(ser)
        if res is None:
            print("  {0}    sin respuesta".format(ph))
            continue
        sI, sQ, eI, eQ = res
        bI = (eI / sI) if sI else float('nan')
        bQ = (eQ / sQ) if sQ else float('nan')
        marca = "" if abs(bI - esperado[ph]) < 0.02 else "   <-- NO COINCIDE"
        print("  {0}    {1:<13} {2:<13} {3:<10.4f}  {4:<9.4f}  {5:.2f}{6}".format(
            ph, sI, eI, bI, bQ, esperado[ph], marca))
    rf_write(ser, CMD_ENB_RX, 1)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
HELP = """Comandos:
  rst <0/1>                reset del DSP
  entx <0/1> | enrx <0/1>  habilitacion de Tx y Rx
  phase <0-3>              fase de muestreo del decimador
  sw                       lectura de las llaves
  status                   readback de los registros del RF
  ber                      contadores de muestras y errores (64 bits)
  berrst                   reset de los contadores
  bersweep                 BER en las 4 fases
  runlog                   dispara el logueo de la memoria
  memfull                  1 cuando la memoria termino de escribirse
  addr <n>                 fija la direccion de lectura
  readword <n>             lee una palabra del log
  dumplog <n> [archivo]    descarga n palabras a CSV
  buildid                  firma del bitstream cargado
  help | exit"""


def main():
    if len(sys.argv) < 2:
        print('Uso: python3 {0} <n>   (usa /dev/ttyUSB<n>)'.format(sys.argv[0]))
        sys.exit(1)

    ser = serial.Serial(
        port='/dev/ttyUSB{}'.format(int(sys.argv[1])),
        baudrate=115200,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=2)

    print(HELP)

    while True:
        try:
            cmd = input("<< ").strip().split()
        except (EOFError, KeyboardInterrupt):
            print()
            ser.close()
            break
        if not cmd:
            continue

        c = cmd[0]

        if c == 'exit':
            ser.close()
            break

        elif c == 'help':
            print(HELP)

        elif c == 'rst' and len(cmd) == 2:
            rf_write(ser, CMD_RST, int(cmd[1]))

        elif c == 'entx' and len(cmd) == 2:
            rf_write(ser, CMD_ENB_TX, int(cmd[1]))

        elif c == 'enrx' and len(cmd) == 2:
            rf_write(ser, CMD_ENB_RX, int(cmd[1]))

        elif c == 'phase' and len(cmd) == 2:
            rf_write(ser, CMD_PHASE, int(cmd[1]) & 0x3)

        elif c == 'sw':
            val = read_switches(ser)
            print(">> switches = {0:04b}".format(val) if val is not None
                  else "Sin respuesta")

        elif c == 'status':
            raw, st = read_status(ser)
            print(">> 0x{0:08X}  {1}".format(raw, st) if raw is not None
                  else "Sin respuesta")

        elif c == 'ber':
            res = read_ber(ser)
            if res is None:
                print("Sin respuesta")
            else:
                sI, sQ, eI, eQ = res
                print(">> I: samp={0} err={1} BER={2:.3e}".format(
                    sI, eI, (eI / sI) if sI else 0.0))
                print(">> Q: samp={0} err={1} BER={2:.3e}".format(
                    sQ, eQ, (eQ / sQ) if sQ else 0.0))

        elif c == 'berrst':
            rf_write(ser, CMD_BER_RST, 0)

        elif c == 'bersweep':
            cmd_bersweep(ser)

        elif c == 'runlog':
            rf_write(ser, CMD_RD_LOG, 0)    # bloquear lectura mientras escribe
            rf_write(ser, CMD_RUN_LOG, 1)
            rf_write(ser, CMD_RUN_LOG, 0)

        elif c == 'memfull':
            val = rf_read(ser, RD_MEM_FULL)
            print(">> mem_full = {0}".format(val) if val is not None
                  else "Sin respuesta")

        elif c == 'addr' and len(cmd) == 2:
            rf_write(ser, CMD_ADDR, int(cmd[1]) & 0x7FFF)

        elif c == 'readword' and len(cmd) == 2:
            word = read_log_word(ser, int(cmd[1]))
            if word is None:
                print("Sin respuesta")
            else:
                s_I, s_Q = split_iq(word)
                print(">> word=0x{0:08X}  sample_I={1}  sample_Q={2}".format(
                    word, s_I, s_Q))

        elif c == 'dumplog' and len(cmd) >= 2:
            n = min(int(cmd[1]), MEM_WORDS)
            cmd_dumplog(ser, n, cmd[2] if len(cmd) > 2 else 'log.csv')

        elif c == 'buildid':
            val = rf_read(ser, RD_BUILD_ID)
            print(">> build id = 0x{0:08X}".format(val) if val is not None
                  else "Sin respuesta")

        else:
            print("Comando desconocido")


if __name__ == '__main__':
    main()