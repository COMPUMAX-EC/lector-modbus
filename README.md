# Lector Modbus — DevIAlabs

Lee por Modbus TCP (función 03) el medidor eléctrico **PowerLogic PM556x** y guarda cada lectura (cada 3 s) en archivos `.txt` dentro de `lecturas/`.

- `lector_modbus.py`: programa principal (consola o bandeja del sistema).
- `registros_pm556x.py`: mapa de registros; `generar_registros.py` lo regenera.
- `generar_manual.py`: genera `Manual-LectorModbus-DevIAlabs.pdf`.
- `*.spec`: builds de PyInstaller (consola y segundo plano).

## Configuración

Copie `config.ini.example` como `config.ini` junto al ejecutable y ponga la IP de su medidor. Si no existe, el programa crea uno con `127.0.0.1` (útil con un simulador). La IP real nunca va en el código.

`config.ini`, `lecturas/`, `build/` y `dist/` se quedan en local.

No confundir con el proyecto de vibraciones (`hydro-vibration-analysis`).

## Pruebas

Las pruebas usan un **medidor sintético** (un cliente Modbus falso con valores inventados), así que no necesitan red ni el equipo real:

```bash
pip install -r requirements-dev.txt
python -m pytest -q tests
```

Cubren la agrupación de registros en bloques (límite de 125 del protocolo), la decodificación FLOAT32 en orden ABCD y CDAB, la lectura con un bloque caído y el reporte `.txt`. Corren en cada PR en GitHub Actions.

## Seguridad y licencia

- GitHub Actions revisa todo el historial con **gitleaks** en cada PR y cada lunes, y falla si aparece una IP de red privada en el código.
- Licencia [MIT](LICENSE).

## Simulator test (no plant needed)

`tests/test_simulador.py` starts a real pymodbus TCP server on loopback with a synthetic meter (invented values) and runs the full read cycle against it: block reads, FLOAT32 decoding and the report. Runs in CI; pymodbus is pinned to 3.6–3.8 for the test dependencies.
