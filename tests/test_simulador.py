# -*- coding: utf-8 -*-
"""End-to-end client test against a real pymodbus TCP server (synthetic meter).

All values are invented; no plant data and no real IP (loopback only).
"""
import asyncio
import socket
import struct
import sys
import threading
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import lector_modbus as lm  # noqa: E402
from pymodbus.client import ModbusTcpClient  # noqa: E402
from pymodbus.datastore import (  # noqa: E402
    ModbusSlaveContext, ModbusServerContext, ModbusSequentialDataBlock)
from pymodbus.server import ModbusTcpServer  # noqa: E402

VALOR = 230.5  # synthetic volts


def _puerto_libre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def simulador():
    """Start a Modbus TCP server in a thread; every float register pair = VALOR."""
    hi, lo = struct.unpack(">HH", struct.pack(">f", VALOR))
    maxaddr = max(a for a, _ in lm.REGISTROS) + 4
    valores = [hi if i % 2 == 0 else lo for i in range(maxaddr + 2)]
    bloque = ModbusSequentialDataBlock(0, valores)
    dev = ModbusSlaveContext(hr=bloque)
    contexto = ModbusServerContext(slaves={lm.CONFIG["esclavo"]: dev}, single=False)
    puerto = _puerto_libre()
    estado = {}

    def correr():
        loop = asyncio.new_event_loop()
        estado["loop"] = loop
        asyncio.set_event_loop(loop)

        async def servir():
            srv = ModbusTcpServer(contexto, address=("127.0.0.1", puerto))
            estado["srv"] = srv
            await srv.serve_forever()

        try:
            loop.run_until_complete(servir())
        except Exception:
            pass

    hilo = threading.Thread(target=correr, daemon=True)
    hilo.start()
    for _ in range(50):
        try:
            socket.create_connection(("127.0.0.1", puerto), timeout=0.2).close()
            break
        except OSError:
            time.sleep(0.1)
    yield puerto
    try:
        asyncio.run_coroutine_threadsafe(estado["srv"].shutdown(), estado["loop"]).result(5)
    except Exception:
        pass


def test_lectura_completa_contra_simulador(simulador):
    cliente = ModbusTcpClient("127.0.0.1", port=simulador, timeout=2)
    assert cliente.connect()
    try:
        valores, fallidos = lm.leer_todos_los_bloques(cliente)
    finally:
        cliente.close()
    assert fallidos == []
    assert len(valores) > 0
    leidos = [abc for abc, _ in valores.values()]
    assert VALOR in leidos
    reporte = lm.construir_reporte("2026-01-01T00:00:00", valores, fallidos)
    assert "LECTURA MODBUS TCP" in reporte
