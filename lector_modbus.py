#!/usr/bin/env python3
"""
Lector Modbus TCP - Medidor PowerLogic PM556x (Holding Registers / Función 03)
IP, puerto y esclavo: en config.ini (plantilla: config.ini.example)

Lee todas las variables marcadas con 's' en la hoja "Register List" del
PM556x_PublicModbusRegisterList (ver registros_pm556x.py) y genera un
archivo .txt por cada lectura (cada 3 segundos) en la carpeta 'lecturas',
ubicada junto al ejecutable (funciona igual sin importar desde dónde se
copie o ejecute el programa).

Herramienta de monitoreo -- DevIAlabs
"""

import os
import sys
import time
import struct
import threading
import configparser
from pymodbus.client import ModbusTcpClient

from registros_pm556x import REGISTROS

try:
    import pystray
    from PIL import Image, ImageDraw
    BANDEJA_DISPONIBLE = True
except Exception:
    BANDEJA_DISPONIBLE = False

# En el build "segundo plano" (--windowed) no hay consola: sys.stdout/stderr
# son None. Se redirigen a devnull para que los print() no truenen.
CONSOLA_DISPONIBLE = sys.stdout is not None
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

if sys.platform == "win32" and CONSOLA_DISPONIBLE:
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        ctypes.windll.kernel32.SetConsoleCP(65001)
    except Exception:
        pass
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

CONFIG = {
    "ip": "127.0.0.1",  # la IP real del medidor va en config.ini, nunca en el código
    "puerto": 502,
    "esclavo": 23,
    "intervalo_seg": 3.0,
    "timeout": 3.0
}

MARCA = "DevIAlabs"

# Máximo de registros por lectura Modbus (el límite del protocolo es 125).
MAX_REGISTROS_POR_LECTURA = 120

# direccion_hoja == direccion_logica - 40000 (ej. 3000 == registro lógico 43000).
REGISTROS_ORDENADOS = sorted(REGISTROS, key=lambda item: item[0])


def construir_bloques(direcciones, max_registros=MAX_REGISTROS_POR_LECTURA):
    """Agrupa direcciones (cada una ocupa 2 registros, por ser FLOAT32) en
    bloques de lectura contiguos que no excedan max_registros por petición
    Modbus, para minimizar la cantidad de lecturas por ciclo."""
    bloques = []
    inicio = fin = None
    for addr in direcciones:
        fin_addr = addr + 1
        if inicio is None:
            inicio, fin = addr, fin_addr
            continue
        if fin_addr - inicio + 1 <= max_registros:
            fin = fin_addr
        else:
            bloques.append((inicio, fin - inicio + 1))
            inicio, fin = addr, fin_addr
    if inicio is not None:
        bloques.append((inicio, fin - inicio + 1))
    return bloques


BLOQUES = construir_bloques([addr for addr, _ in REGISTROS_ORDENADOS])


def obtener_directorio_base() -> str:
    """Carpeta donde vive el ejecutable/script, para que el programa sea portable."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def cargar_configuracion(dir_base: str):
    """Lee config.ini (junto al ejecutable) y sobrescribe CONFIG con sus
    valores. Si el archivo no existe, lo crea con los valores por defecto
    para que quede como plantilla editable."""
    ruta_ini = os.path.join(dir_base, "config.ini")
    parser = configparser.ConfigParser()

    if not os.path.exists(ruta_ini):
        parser["ModbusReader"] = {
            "ip": str(CONFIG["ip"]),
            "puerto": str(CONFIG["puerto"]),
            "esclavo": str(CONFIG["esclavo"]),
            "intervalo_seg": str(CONFIG["intervalo_seg"]),
            "timeout": str(CONFIG["timeout"]),
        }
        try:
            with open(ruta_ini, "w", encoding="utf-8") as f:
                parser.write(f)
            print(f"[INFO] No se encontró config.ini; se creó uno con valores por defecto en: {ruta_ini}")
            print("[INFO] Edite la clave 'ip' con la dirección de su medidor (ver config.ini.example).")
        except OSError as e:
            print(f"[AVISO] No se pudo crear config.ini ({e}); usando valores por defecto.")
        return

    try:
        parser.read(ruta_ini, encoding="utf-8")
        sec = parser["ModbusReader"]
        CONFIG["ip"] = sec.get("ip", CONFIG["ip"])
        CONFIG["puerto"] = sec.getint("puerto", fallback=CONFIG["puerto"])
        CONFIG["esclavo"] = sec.getint("esclavo", fallback=CONFIG["esclavo"])
        CONFIG["intervalo_seg"] = sec.getfloat("intervalo_seg", fallback=CONFIG["intervalo_seg"])
        CONFIG["timeout"] = sec.getfloat("timeout", fallback=CONFIG["timeout"])
        print(f"[INFO] Configuración cargada desde: {ruta_ini}")
    except Exception as e:
        print(f"[AVISO] No se pudo leer config.ini ({e}); usando valores por defecto.")


def ocultar_consola():
    """Oculta la ventana de consola (el proceso sigue corriendo en segundo plano)."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE
    except Exception:
        pass


def crear_imagen_icono():
    """Ícono simple (círculo azul con las iniciales) para la bandeja del sistema."""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((2, 2, 62, 62), fill=(31, 59, 87, 255))
    d.text((14, 20), "DI", fill=(255, 255, 255, 255))
    return img


def iniciar_bandeja(detener_evento: threading.Event):
    """Muestra un ícono "ReadModbus" en la bandeja del sistema. Clic derecho
    sobre el ícono para ver el menú con la opción de detenerlo.

    Corre en un hilo aparte; si pystray/Pillow no están disponibles, no hace
    nada (el programa sigue funcionando, solo sin ícono)."""
    if not BANDEJA_DISPONIBLE:
        print("[AVISO] Ícono de bandeja no disponible; use el Administrador de Tareas para detener.")
        return

    def al_detener(icon, item):
        detener_evento.set()
        icon.stop()

    menu = pystray.Menu(
        pystray.MenuItem(f"ReadModbus ({MARCA}) - en ejecución", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Detener servicio ReadModbus", al_detener),
    )
    icono = pystray.Icon("ReadModbus", crear_imagen_icono(), "ReadModbus", menu)

    def configurar(icon):
        icon.visible = True
        try:
            icon.notify(
                "Clic derecho en este ícono y seleccione "
                "'Detener servicio ReadModbus' para detenerlo.",
                "ReadModbus está corriendo en segundo plano"
            )
        except Exception:
            pass

    hilo = threading.Thread(target=icono.run, kwargs={"setup": configurar}, daemon=True)
    hilo.start()


def preguntar_modo_segundo_plano() -> bool:
    """Decide si el programa debe ocultar su ventana.

    Se puede forzar sin preguntar con los argumentos de línea de comandos
    --segundo-plano / -b (oculto) o --visible / -v (visible) -- útil para
    accesos directos o el Programador de tareas de Windows.
    """
    argv = [a.lower() for a in sys.argv[1:]]
    if any(a in ("--segundo-plano", "--background", "-b") for a in argv):
        return True
    if any(a in ("--visible", "--consola", "-v") for a in argv):
        return False
    if not CONSOLA_DISPONIBLE:
        return False  # ya está oculto (ej. build --windowed)

    print("Seleccione el modo de ejecución:")
    print("  [1] Visible (ventana de consola)  -- por defecto")
    print("  [2] Segundo plano (oculta la ventana)")
    try:
        opcion = input("Opción (1/2) [1]: ").strip()
    except EOFError:
        opcion = ""
    return opcion == "2"


def leer_holding(cliente, direccion: int, cantidad: int, esclavo: int):
    """Lectura compatible para cualquier versión de pymodbus."""
    for kwargs in [{"slave": esclavo}, {"unit": esclavo}, {"device_id": esclavo}, {}]:
        try:
            return cliente.read_holding_registers(address=direccion, count=cantidad, **kwargs)
        except TypeError:
            continue
    return cliente.read_holding_registers(direccion, cantidad)


def decodificar_float(reg1: int, reg2: int):
    """Decodifica números float IEEE-754 en los dos órdenes más comunes."""
    try:
        # Big Endian estándar (AB CD)
        float_abcd = round(struct.unpack(">f", struct.pack(">HH", reg1, reg2))[0], 2)
        # Word Swapped (CD AB)
        float_cdab = round(struct.unpack(">f", struct.pack(">HH", reg2, reg1))[0], 2)
        return float_abcd, float_cdab
    except Exception:
        return 0.0, 0.0


def leer_todos_los_bloques(cliente):
    """Lee todos los BLOQUES necesarios para cubrir REGISTROS.

    Devuelve (valores, bloques_fallidos):
      - valores: dict {direccion_hoja: (float_abcd, float_cdab)} solo para
        las direcciones que se pudieron leer.
      - bloques_fallidos: lista de (inicio_hoja, cantidad) que no se
        pudieron leer en este ciclo (el equipo puede estar ocupado, etc.).

    Puede lanzar una excepción si la conexión TCP se cae (para que el
    llamador dispare la lógica de reconexión).
    """
    valores = {}
    bloques_fallidos = []

    for inicio_hoja, cantidad in BLOQUES:
        direccion_fisica = inicio_hoja - 1
        resp = leer_holding(cliente, direccion_fisica, cantidad, CONFIG["esclavo"])
        if resp is None or resp.isError():
            # Dirección directa (offset alternativo), igual que en el bloque original.
            resp = leer_holding(cliente, inicio_hoja, cantidad, CONFIG["esclavo"])

        if resp is None or resp.isError():
            bloques_fallidos.append((inicio_hoja, cantidad))
            continue

        regs = resp.registers
        for addr, _nombre in REGISTROS_ORDENADOS:
            if inicio_hoja <= addr <= inicio_hoja + cantidad - 2:
                offset = addr - inicio_hoja
                valores[addr] = decodificar_float(regs[offset], regs[offset + 1])

    return valores, bloques_fallidos


def construir_reporte(ahora_iso: str, valores: dict, bloques_fallidos: list) -> str:
    """Arma el contenido del .txt para una lectura completa (todas las
    variables marcadas con 's' en la hoja de registros del PM556x)."""
    lineas = []
    lineas.append("=" * 80)
    lineas.append(f" LECTURA MODBUS TCP | {ahora_iso}")
    lineas.append(f" IP: {CONFIG['ip']}:{CONFIG['puerto']} | Esclavo: {CONFIG['esclavo']}")
    lineas.append(f" Variables: {len(REGISTROS_ORDENADOS)} | Bloques de lectura: {len(BLOQUES)} "
                  f"| Función: 03 (Holding Registers)")
    if bloques_fallidos:
        lineas.append(f" [AVISO] {len(bloques_fallidos)} bloque(s) no se pudieron leer en este ciclo: "
                      f"{bloques_fallidos}")
    lineas.append("=" * 80)

    lineas.append(f"{'Variable':<34} | {'Reg Lógico':<12} | {'Valor (ABCD)':<14} | {'Valor (CDAB)':<14}")
    lineas.append("-" * 80)
    for addr, nombre in REGISTROS_ORDENADOS:
        r_logico = 40000 + addr
        if addr in valores:
            f_abcd, f_cdab = valores[addr]
            lineas.append(f"{nombre:<34} | {r_logico:<12} | {f_abcd:<14} | {f_cdab:<14}")
        else:
            lineas.append(f"{nombre:<34} | {r_logico:<12} | {'(sin datos)':<14} | {'(sin datos)':<14}")

    lineas.append("-" * 80)
    lineas.append(f"Generado por {MARCA}")
    return "\n".join(lineas) + "\n"


def main():
    dir_base = obtener_directorio_base()
    dir_lecturas = os.path.join(dir_base, "lecturas")
    os.makedirs(dir_lecturas, exist_ok=True)

    cargar_configuracion(dir_base)

    segundo_plano = preguntar_modo_segundo_plano()

    print("=" * 80)
    print(f" LECTOR MODBUS TCP | IP: {CONFIG['ip']}:{CONFIG['puerto']} | ESCLAVO: {CONFIG['esclavo']}")
    print(f" Variables a leer: {len(REGISTROS_ORDENADOS)} | Bloques de lectura por ciclo: {len(BLOQUES)}")
    print(f" Guardando lecturas en: {dir_lecturas}")
    print(f" ({MARCA})")
    print("=" * 80)

    detener_evento = threading.Event()

    if segundo_plano:
        print("[INFO] Pasando a segundo plano... la ventana se ocultará en unos instantes.")
        print("[INFO] Para detenerlo, use el ícono en la bandeja del sistema (junto al reloj) -> "
              "clic derecho -> 'Detener servicio ReadModbus'.")
        time.sleep(1.5)
        ocultar_consola()
        iniciar_bandeja(detener_evento)
    else:
        print("[INFO] Para detener el programa, simplemente cierre esta ventana.")

    cliente = ModbusTcpClient(host=CONFIG["ip"], port=CONFIG["puerto"], timeout=CONFIG["timeout"])

    def conectar_hasta_exito() -> bool:
        """True si conectó; False si se pidió terminar antes de lograrlo."""
        intento = 0
        while not cliente.connect():
            if detener_evento.is_set():
                return False
            intento += 1
            print(f"[ERROR] No se pudo conectar a {CONFIG['ip']}:{CONFIG['puerto']} (intento {intento}). "
                  f"Reintentando en {CONFIG['intervalo_seg']}s...")
            if detener_evento.wait(CONFIG["intervalo_seg"]):
                return False
        return True

    if not conectar_hasta_exito():
        print("[INFO] Terminado antes de conectar.")
        cliente.close()
        return
    print(f"[INFO] Conectado a {CONFIG['ip']}:{CONFIG['puerto']}.")

    try:
        while not detener_evento.is_set():
            ahora_dt = time.localtime()
            ahora_iso = time.strftime("%Y-%m-%d %H:%M:%S", ahora_dt)
            fecha_archivo = time.strftime("%Y%m%d", ahora_dt)
            print(f"\n--- [LECTURA {ahora_iso}] ---")

            try:
                valores, bloques_fallidos = leer_todos_los_bloques(cliente)
            except Exception as e:
                print(f"[ERROR] Se perdió la conexión ({e}). Reconectando...")
                cliente.close()
                if not conectar_hasta_exito():
                    break
                print(f"[INFO] Reconectado a {CONFIG['ip']}:{CONFIG['puerto']}.")
                continue

            print(f"[INFO] {len(valores)}/{len(REGISTROS_ORDENADOS)} variables leídas correctamente.")
            if bloques_fallidos:
                print(f"[AVISO] {len(bloques_fallidos)} bloque(s) fallaron en este ciclo: {bloques_fallidos}")

            contenido = construir_reporte(ahora_iso, valores, bloques_fallidos)

            nombre_archivo = os.path.join(dir_lecturas, f"lecturas_{fecha_archivo}.txt")
            try:
                with open(nombre_archivo, "a", encoding="utf-8") as f:
                    f.write(contenido)
            except OSError as e:
                print(f"[ERROR] No se pudo escribir el archivo {nombre_archivo}: {e}")

            detener_evento.wait(CONFIG["intervalo_seg"])

    except KeyboardInterrupt:
        print("\n[INFO] Monitoreo detenido por el usuario.")
    finally:
        detener_evento.set()
        cliente.close()
        print("[INFO] Programa terminado.")


if __name__ == "__main__":
    main()
