# -*- coding: utf-8 -*-
"""Pruebas del Lector Modbus con un medidor sintético (sin red ni equipo real).

Los valores son inventados: nunca se usan lecturas del sitio.
"""
import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import lector_modbus as lm  # noqa: E402
from registros_pm556x import REGISTROS  # noqa: E402


def a_registros(valor: float):
    """FLOAT32 big endian (AB CD) -> dos registros de 16 bits."""
    return list(struct.unpack(">HH", struct.pack(">f", valor)))


# --- construir_bloques -------------------------------------------------------

def test_bloques_contiguos_en_uno_solo():
    assert lm.construir_bloques([3000, 3002, 3004]) == [(3000, 6)]


def test_bloques_respetan_el_maximo():
    direcciones = list(range(3000, 3000 + 2 * 100, 2))  # 100 floats = 200 registros
    bloques = lm.construir_bloques(direcciones, max_registros=120)
    assert all(cantidad <= 120 for _, cantidad in bloques)
    # Cada dirección queda cubierta por algún bloque, con sus 2 registros.
    for addr in direcciones:
        assert any(ini <= addr and addr + 1 <= ini + cant - 1 for ini, cant in bloques)


def test_bloques_vacio():
    assert lm.construir_bloques([]) == []


def test_bloques_del_mapa_real_no_exceden_limite_protocolo():
    assert lm.BLOQUES, "el mapa de registros debe generar al menos un bloque"
    assert all(cantidad <= 125 for _, cantidad in lm.BLOQUES)


def test_mapa_sin_direcciones_duplicadas():
    direcciones = [addr for addr, _ in REGISTROS]
    assert len(direcciones) == len(set(direcciones))


# --- decodificar_float -------------------------------------------------------

@pytest.mark.parametrize("valor", [0.0, 1.5, 120.25, -3.75, 59.98])
def test_decodifica_abcd(valor):
    r1, r2 = a_registros(valor)
    abcd, _ = lm.decodificar_float(r1, r2)
    assert abcd == pytest.approx(round(valor, 2))


def test_decodifica_cdab_word_swapped():
    r1, r2 = a_registros(230.4)
    _, cdab = lm.decodificar_float(r2, r1)  # el medidor entrega las palabras invertidas
    assert cdab == pytest.approx(230.4)


def test_registro_fuera_de_rango_no_truena():
    assert lm.decodificar_float(70000, 1) == (0.0, 0.0)


# --- leer_todos_los_bloques con un cliente falso ------------------------------

class Respuesta:
    def __init__(self, registers=None, error=False):
        self.registers = registers or []
        self._error = error

    def isError(self):
        return self._error


class MedidorSintetico:
    """Simula un PM556x: cada dirección de la hoja devuelve addr/10 como float.

    Responde en la dirección física (hoja - 1); los bloques en `bloques_caidos`
    fallan siempre, para probar el aviso de bloques no leídos.
    """

    def __init__(self, bloques_caidos=()):
        self.bloques_caidos = set(bloques_caidos)
        self.peticiones = []

    def read_holding_registers(self, address, count, slave=None):
        self.peticiones.append((address, count))
        inicio_hoja = address + 1
        if inicio_hoja in self.bloques_caidos or address + 1 not in {b[0] for b in lm.BLOQUES}:
            return Respuesta(error=True)
        regs = [0] * count
        for addr, _ in lm.REGISTROS_ORDENADOS:
            off = addr - inicio_hoja
            if 0 <= off <= count - 2:
                regs[off:off + 2] = a_registros(addr / 10)
        return Respuesta(regs)


def test_lee_todas_las_variables():
    valores, fallidos = lm.leer_todos_los_bloques(MedidorSintetico())
    assert fallidos == []
    assert set(valores) == {addr for addr, _ in REGISTROS}
    for addr, (abcd, _cdab) in valores.items():
        assert abcd == pytest.approx(round(addr / 10, 2))


def test_bloque_caido_se_reporta_y_no_detiene_la_lectura():
    primero = lm.BLOQUES[0]
    valores, fallidos = lm.leer_todos_los_bloques(MedidorSintetico(bloques_caidos={primero[0]}))
    assert fallidos == [primero]
    assert valores, "los demás bloques deben seguir leyéndose"
    assert all(not (primero[0] <= a < primero[0] + primero[1]) for a in valores)


# --- construir_reporte -------------------------------------------------------

def test_reporte_incluye_todas_las_variables_y_marca():
    valores, _ = lm.leer_todos_los_bloques(MedidorSintetico())
    texto = lm.construir_reporte("2026-01-01T00:00:00", valores, [])
    for _, nombre in REGISTROS:
        assert nombre in texto
    assert "(sin datos)" not in texto
    assert texto.rstrip().endswith(f"Generado por {lm.MARCA}")


def test_reporte_marca_sin_datos_y_aviso():
    texto = lm.construir_reporte("2026-01-01T00:00:00", {}, [(3000, 6)])
    assert "[AVISO] 1 bloque(s)" in texto
    assert texto.count("(sin datos)") == 2 * len(REGISTROS)
