import json

with open("registros_extraidos.json", encoding="utf-8") as f:
    filas = json.load(f)

lineas = []
lineas.append("# -*- coding: utf-8 -*-")
lineas.append('"""Lista de registros Modbus del medidor PowerLogic PM556x marcados con')
lineas.append("'s' en PM556x_PublicModbusRegisterList (hoja Register List). Cada entrada")
lineas.append("es (direccion_hoja, nombre); direccion_hoja equivale a direccion_logica -")
lineas.append('40000. Todos son FLOAT32 de solo lectura (2 registros cada uno)."""')
lineas.append("")
lineas.append("REGISTROS = [")
for addr, nombre in filas:
    nombre_escapado = nombre.replace("\\", "\\\\").replace('"', '\\"')
    lineas.append(f'    ({addr}, "{nombre_escapado}"),')
lineas.append("]")
lineas.append("")

contenido = "\n".join(lineas) + "\n"
with open("registros_pm556x.py", "w", encoding="utf-8") as f:
    f.write(contenido)
print("escrito registros_pm556x.py,", len(filas), "entradas")
