from pathlib import Path
# -*- coding: utf-8 -*-
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_CENTER

AZUL = colors.HexColor("#1F3B57")
GRIS = colors.HexColor("#5A6B7A")
GRIS_CLARO = colors.HexColor("#EEF1F4")

styles = getSampleStyleSheet()

titulo = ParagraphStyle(
    "TituloPrincipal", parent=styles["Title"],
    fontName="Helvetica-Bold", fontSize=20, textColor=AZUL, spaceAfter=2,
)
subtitulo = ParagraphStyle(
    "Subtitulo", parent=styles["Normal"],
    fontName="Helvetica", fontSize=10.5, textColor=GRIS, spaceAfter=14,
)
h2 = ParagraphStyle(
    "H2", parent=styles["Heading2"],
    fontName="Helvetica-Bold", fontSize=12.5, textColor=AZUL,
    spaceBefore=14, spaceAfter=6,
)
cuerpo = ParagraphStyle(
    "Cuerpo", parent=styles["Normal"],
    fontName="Helvetica", fontSize=9.7, leading=14, textColor=colors.HexColor("#222222"),
)
bullet = ParagraphStyle(
    "Bullet", parent=cuerpo, leftIndent=14, bulletIndent=2, spaceAfter=3,
)
nota = ParagraphStyle(
    "Nota", parent=cuerpo, fontSize=9, textColor=GRIS, spaceBefore=4,
)
pie = ParagraphStyle(
    "Pie", parent=styles["Normal"], fontName="Helvetica-Oblique",
    fontSize=8.5, textColor=GRIS, alignment=TA_CENTER,
)

story = []

story.append(Paragraph("Lector Modbus TCP", titulo))
story.append(Paragraph("Manual basico de uso &mdash; Desarrollado por DevIAlabs", subtitulo))
story.append(HRFlowable(width="100%", thickness=1, color=GRIS_CLARO, spaceAfter=10))

# 1. Que es
story.append(Paragraph("Que es este programa?", h2))
story.append(Paragraph(
    "Es un programa para Windows que se conecta por <b>Modbus TCP</b> a un medidor electrico "
    "PowerLogic PM556x en la direccion IP indicada en <b>config.ini</b> (por defecto puerto <b>502</b>, esclavo <b>23</b>). "
    "Lee de forma automatica <b>las 945 variables</b> marcadas como necesarias en la lista "
    "oficial de registros del fabricante (corrientes, voltajes, desbalances, armonicos, "
    "factores K, factores de cresta y otras variables de calidad de energia), todas como "
    "numeros decimales (float).",
    cuerpo
))
story.append(Spacer(1, 4))
story.append(Paragraph(
    "Como el protocolo Modbus limita cada lectura a 125 registros, el programa reparte esas "
    "945 variables en <b>20 lecturas por ciclo</b> (bloques), de forma automatica y transparente.",
    nota
))

# 2. Que genera
story.append(Paragraph("Que genera?", h2))
story.append(Paragraph(
    "Cada <b>3 segundos</b> el programa realiza una lectura completa (los 20 bloques) y agrega "
    "el resultado a un archivo <b>.txt</b> dentro de una carpeta llamada <b>lecturas</b>, que se "
    "crea sola junto al ejecutable (sin importar en que carpeta o USB lo coloques). Se genera "
    "<b>un solo archivo por dia</b> (por ejemplo, lecturas_20260828.txt); todas las lecturas de "
    "ese dia se van agregando una tras otra dentro del mismo archivo, y al cambiar la fecha se "
    "empieza un archivo nuevo automaticamente.",
    cuerpo
))
story.append(Paragraph(
    "Cada lectura dentro del archivo incluye las 945 variables con su nombre, su registro "
    "Modbus y su valor (en los dos posibles ordenes de bytes, ABCD y CDAB, por si el equipo usa "
    "uno distinto al esperado). Si alguno de los 20 bloques no se pudo leer en un ciclo, el "
    "archivo lo indica claramente en vez de inventar un valor.",
    cuerpo
))
story.append(Paragraph(
    "Nota de almacenamiento: aunque ahora es un solo archivo por dia, el volumen de datos sigue "
    "siendo el mismo (unas 28,800 lecturas de 945 variables cada una), por lo que ese archivo "
    "diario puede llegar a pesar <b>1 a 1.5 GB</b>. Un archivo tan grande puede abrirse lento en "
    "el Bloc de notas comun; se recomienda usar un editor para archivos grandes (por ejemplo, "
    "Notepad++) y revisar periodicamente la carpeta \"lecturas\" para archivar o borrar los dias "
    "mas antiguos.",
    nota
))

# 3. Modo visible o segundo plano
story.append(Paragraph("Modo visible o segundo plano", h2))
story.append(Paragraph(
    "Un solo ejecutable, <b>LectorModbus-DevIAlabs.exe</b>, ofrece ambos modos. Al abrirlo, "
    "pregunta en pantalla que modo usar:",
    cuerpo
))
story.append(Paragraph(
    "<b>[1] Visible</b> &mdash; mantiene la ventana de consola abierta. Util para monitoreo "
    "en vivo o pruebas, ya que se ven las lecturas en pantalla en tiempo real. Es la opcion "
    "por defecto (basta con presionar Enter).",
    bullet
))
story.append(Paragraph(
    "<b>[2] Segundo plano</b> &mdash; la ventana se oculta a los pocos segundos y el programa "
    "sigue trabajando de forma invisible. Para detenerlo, aparece un icono en la "
    "<b>bandeja del sistema</b> (junto al reloj, esquina inferior derecha): clic derecho sobre "
    "el icono y seleccionar <b>Terminar</b>.",
    bullet
))
story.append(Paragraph(
    "Si el icono de bandeja no aparece por alguna razon, tambien se puede detener desde el "
    "Administrador de Tareas de Windows (pestana Detalles), buscando el proceso "
    "<i>LectorModbus-DevIAlabs.exe</i> y finalizandolo desde ahi.",
    nota
))
story.append(Paragraph(
    "Para automatizarlo (por ejemplo, con un acceso directo o el Programador de tareas de "
    "Windows) sin que aparezca la pregunta, se puede iniciar directamente en segundo plano "
    "agregando el argumento <b>--segundo-plano</b> al final del acceso directo.",
    nota
))

# 4. Portable
story.append(Paragraph("Portable, sin instalacion", h2))
story.append(Paragraph(
    "El programa es un unico archivo <b>.exe</b> autocontenido: no necesita instalar Python "
    "ni ninguna otra dependencia. Se puede copiar a cualquier carpeta, disco o memoria USB "
    "y funcionara igual, generando su carpeta de lecturas justo al lado de donde se ejecute.",
    cuerpo
))

# 4b. Configuracion externa
story.append(Paragraph("Configuracion (config.ini)", h2))
story.append(Paragraph(
    "La IP, el puerto, el numero de esclavo, el intervalo de lectura y el timeout se pueden "
    "cambiar <b>sin reinstalar ni recompilar el programa</b>. La primera vez que se ejecuta, "
    "crea automaticamente un archivo <b>config.ini</b> junto al .exe con los valores por "
    "defecto:",
    cuerpo
))

ini_ejemplo = (
    "[ModbusReader]\n"
    "ip = 192.0.2.10\n"
    "puerto = 502\n"
    "esclavo = 23\n"
    "intervalo_seg = 3.0\n"
    "timeout = 3.0"
)
codigo = ParagraphStyle(
    "Codigo", parent=styles["Normal"], fontName="Courier", fontSize=9,
    leading=13, textColor=colors.HexColor("#222222"), backColor=GRIS_CLARO,
    borderPadding=8, leftIndent=6,
)
story.append(Spacer(1, 4))
story.append(Paragraph(ini_ejemplo.replace("\n", "<br/>"), codigo))
story.append(Spacer(1, 6))
story.append(Paragraph(
    "Para apuntar el programa a otro equipo, basta con abrir config.ini con el Bloc de notas, "
    "cambiar los valores necesarios, guardar el archivo y volver a ejecutar el .exe. Si el "
    "archivo no existe o tiene un error, el programa usa los valores por defecto y avisa en "
    "pantalla.",
    cuerpo
))

# 5. Reconexion
story.append(Paragraph("Reconexion automatica", h2))
story.append(Paragraph(
    "Si se pierde la conexion de red con el equipo, el programa no se cierra: reintenta "
    "conectarse automaticamente cada 3 segundos hasta recuperar la comunicacion.",
    cuerpo
))

# 6. Como usarlo
story.append(Paragraph("Como usarlo", h2))
for i, item in enumerate([
    "Copia el archivo LectorModbus-DevIAlabs.exe a la carpeta donde quieras que trabaje.",
    "Haz doble clic para ejecutarlo una primera vez; esto crea el archivo config.ini junto "
    "al .exe (si necesitas otra IP, puerto o esclavo, editalo ahora y vuelve a ejecutar).",
    "Elige el modo: presiona Enter (o escribe 1) para modo visible, "
    "o escribe 2 para que pase a segundo plano.",
    "Verifica que se haya creado la carpeta lecturas junto al .exe, con el archivo del dia "
    "(ej. lecturas_20260828.txt) creciendo cada 3 segundos.",
], start=1):
    story.append(Paragraph(f"{i}. {item}", bullet))

# 7. Nota tecnica
story.append(Paragraph("Nota tecnica", h2))
story.append(Paragraph(
    "Los valores numericos de los medidores son numeros de 32 bits (IEEE-754) que ocupan "
    "<b>2 registros Modbus</b> cada uno. Si algun valor se ve incorrecto o fuera de rango, "
    "puede deberse al orden de bytes usado por el equipo; el archivo .txt ya incluye ambas "
    "interpretaciones (ABCD y CDAB) para poder comparar y elegir la correcta.",
    cuerpo
))

story.append(Spacer(1, 22))
story.append(HRFlowable(width="100%", thickness=0.6, color=GRIS_CLARO, spaceAfter=6))
story.append(Paragraph("Herramienta desarrollada por DevIAlabs", pie))

doc = SimpleDocTemplate(
    str(Path(__file__).resolve().parent / "Manual-LectorModbus-DevIAlabs.pdf"),
    pagesize=letter,
    topMargin=1.8 * cm, bottomMargin=1.8 * cm,
    leftMargin=2.0 * cm, rightMargin=2.0 * cm,
    title="Manual Lector Modbus - DevIAlabs",
    author="DevIAlabs",
)
doc.build(story)
print("PDF generado correctamente.")
