# -*- coding: utf-8 -*-
"""La IP del medidor vive en config.ini, no en el código."""
import configparser
import ipaddress
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import lector_modbus as lm  # noqa: E402


def test_ip_por_defecto_no_es_de_una_red_real():
    ip = ipaddress.ip_address(lm.CONFIG["ip"])
    assert ip.is_loopback


def test_plantilla_tiene_todas_las_claves():
    parser = configparser.ConfigParser()
    parser.read(RAIZ / "config.ini.example", encoding="utf-8")
    sec = parser["ModbusReader"]
    assert set(sec) == {"ip", "puerto", "esclavo", "intervalo_seg", "timeout"}
    # 192.0.2.0/24 es el rango de documentación (RFC 5737)
    assert ipaddress.ip_address(sec["ip"]) in ipaddress.ip_network("192.0.2.0/24")


def test_config_ini_sobrescribe_valores(tmp_path, monkeypatch):
    monkeypatch.setattr(lm, "CONFIG", dict(lm.CONFIG))
    (tmp_path / "config.ini").write_text(
        "[ModbusReader]\nip = 192.0.2.55\npuerto = 1502\n", encoding="utf-8")
    lm.cargar_configuracion(str(tmp_path))
    assert lm.CONFIG["ip"] == "192.0.2.55"
    assert lm.CONFIG["puerto"] == 1502
    assert lm.CONFIG["esclavo"] == 23
