from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    Image,
)
from reportlab.lib.styles import ParagraphStyle
from datetime import datetime
import os
import html


# ========= Helpers =========

def P(text, bold=False, size=7, align="CENTER", color=colors.black, nowrap=False):
    style = ParagraphStyle(
        name="p",
        fontName="Helvetica-Bold" if bold else "Helvetica",
        fontSize=size,
        textColor=color,
        alignment={"LEFT": 0, "CENTER": 1, "RIGHT": 2}[align],
        leading=size + 1.5,
        wordWrap=None if nowrap else "LTR",
        splitLongWords=False,
    )
    return Paragraph(html.escape(str(text if text is not None else "")), style)


def IMG(path, w, h):
    return Image(path, width=w, height=h) if path and os.path.exists(path) else ""


def vertical_label(text):
    """
    Genera encabezado vertical tipo:
    F
    o
    t
    o
    c
    h
    e
    c
    k
    """
    letters = [c for c in text if c != " "]
    html_text = "<br/>".join(letters)
    style = ParagraphStyle(
        name="v",
        fontName="Helvetica-Bold",
        fontSize=5,
        alignment=1,      # CENTER
        leading=5,
    )
    # NO escapamos porque necesitamos <br/>
    return Paragraph(html_text, style)


# ========= Generar PDF =========

def generar_pdf(data: dict) -> str:
    filename = f"ATS_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    AZUL = colors.HexColor("#002b5c")
    GRIS = colors.HexColor("#f2f3f5")

    # A4 horizontal. Ancho útil = 29.7 - 2 cm = 27.7 cm
    doc = SimpleDocTemplate(
        filename,
        pagesize=landscape(A4),
        leftMargin=1.0 * cm,
        rightMargin=1.0 * cm,
        topMargin=0.8 * cm,
        bottomMargin=0.8 * cm,
    )

    story = []

    # ========= ENCABEZADO =========
    logo_path = "static/logo_cicsa.png"
    logo = IMG(logo_path, 4.5 * cm, 1.5 * cm)

    titulo = P(
        "CHARLA DE 5 MIN / ANALISIS DE TRABAJO SEGURO (ATS)",
        bold=True,
        size=10,
        align="CENTER",
        color=colors.white,
        nowrap=True,
    )

    cod_info = Table(
        [
            [P("Código:", True, 7, "LEFT", colors.white, True),
             P("PE-FR-SG-31", False, 7, "LEFT", colors.white, True)],
            [P("Versión:", True, 7, "LEFT", colors.white, True),
             P("08", False, 7, "LEFT", colors.white, True)],
            [P("Fecha:", True, 7, "LEFT", colors.white, True),
             P("09/03/2020", False, 7, "LEFT", colors.white, True)],
            [P("Página:", True, 7, "LEFT", colors.white, True),
             P("1 de 1", False, 7, "LEFT", colors.white, True)],
        ],
        colWidths=[2.6 * cm, 3.1 * cm],
    )

    encabezado = Table(
        [[logo, titulo, cod_info]],
        # 5.0 + 17.0 + 5.7 = 27.7
        colWidths=[5.0 * cm, 17.0 * cm, 5.7 * cm],
    )
    encabezado.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), AZUL),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (1, 0), (1, 0), "CENTER"),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.7, colors.black),
            ]
        )
    )
    story.append(encabezado)
    story.append(Spacer(1, 3))

    # ========= DATOS GENERALES =========
    empresa = "CICSA PERU S.A.C."
    contrata = (data.get("contrata") or "").strip() or "CICSA PERU S.A.C."
    actividad = data.get("actividad", "")
    fecha_dia = data.get("fecha_dia", "")
    hora_ini = data.get("hora_inicio", "")
    hora_fin = data.get("hora_fin", "")
    area = data.get("area", "MRD F.O.")

    generales = [
        [
            P("EMPRESA", True, nowrap=True),
            P(empresa, False, 7, "LEFT"),
            P("CONTRATISTA", True, nowrap=True),
            P(contrata, False, 7, "LEFT"),
        ],
        [
            P("PROYECTO DE TRABAJO/N°PLANO", True, nowrap=True),
            P(actividad, False, 7, "LEFT"),
            "", "",
        ],
        [
            P("FECHA", True, nowrap=True),
            P(fecha_dia, False, 7, "LEFT"),
            P("AREA", True, nowrap=True),
            P(area, False, 7, "LEFT"),
        ],
        [
            P("HORA INICIO", True, nowrap=True),
            P(hora_ini, False, 7, "LEFT"),
            P("HORA FINAL", True, nowrap=True),
            P(hora_fin, False, 7, "LEFT"),
        ],
    ]

    # 6.0 + 9.0 + 4.0 + 8.7 = 27.7
    tabla_generales = Table(
        generales,
        colWidths=[6.0 * cm, 9.0 * cm, 4.0 * cm, 8.7 * cm],
    )
    tabla_generales.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.6, colors.black),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.black),
                ("BACKGROUND", (0, 0), (-1, -1), GRIS),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(tabla_generales)
    story.append(Spacer(1, 3))

    # ========= PERSONAL PARTICIPANTE / EPP =========
    story.append(P("PERSONAL PARTICIPANTE / VERIFICACIÓN DE EPP", True, 8, "LEFT", AZUL, True))

    tecnicos = data.get("tecnicos", []) or []

    # Encabezados EPP en vertical
    epp_headers = [
        vertical_label("Fotocheck"),
        vertical_label("Uniforme"),
        vertical_label("Casco"),
        vertical_label("Barbiquejo"),
        vertical_label("Lentes"),
        vertical_label("UV"),
        vertical_label("Guantes Dielectricos"),
        vertical_label("Guantes Anticorte"),
        vertical_label("Chaleco"),
        vertical_label("Arnes"),
        vertical_label("Botas"),
        vertical_label("SCTR"),
    ]

    header = [
        P("Item", True, nowrap=True),
        P("Nombre y Apellidos de los involucrados", True, nowrap=True),
        P("Cargo", True, nowrap=True),
        P("DNI", True, nowrap=True),
    ] + epp_headers + [
        P("Observaciones", True, nowrap=True),
        P("Firma", True, nowrap=True),
    ]

    filas = [header]

    def marcado(keys, epps):
        for kw in keys:
            for e in epps:
                if kw.lower() in e.lower():
                    return "✔"
        return ""

    checks_map = [
        ["fotocheck", "foto"],
        ["uniforme"],
        ["casco"],
        ["barbuquejo", "barb"],
        ["lentes"],
        ["uv", "ultravioleta"],
        ["diel"],
        ["anticorte"],
        ["chaleco"],
        ["arnes", "arnés", "cinturon", "cinturón"],
        ["bota"],
        ["sctr"],
    ]

    for i, t in enumerate(tecnicos, start=1):
        nombre = t.get("nombre", "")
        cargo = t.get("cargo", "")
        dni = t.get("dni", "")
        obs = t.get("obs", "")
        epps = [str(x) for x in (t.get("epp") or [])]

        fila = [
            P(i),
            P(nombre, False, 6.2, "LEFT"),
            P(cargo, False, 6.2, "LEFT"),
            P(dni, False, 6.2, "LEFT"),
        ]
        for ks in checks_map:
            fila.append(P(marcado(ks, epps), False, 6))

        fila.append(P(obs, False, 6.2, "LEFT"))

        firma_path = t.get("firma_path")
        if firma_path and os.path.exists(firma_path):
            firma_cell = IMG(firma_path, 2.6 * cm, 1.2 * cm)
        else:
            firma_cell = P("_________________", False, 6)
        fila.append(firma_cell)

        filas.append(fila)

    # 0.7 + 6.0 + 2.0 + 2.0 + 12*0.7 + 4.3 + 4.3 = 27.7
    tabla_part = Table(
        filas,
        colWidths=[
            0.7 * cm,      # Item
            6.0 * cm,      # Nombre
            2.0 * cm,      # Cargo
            2.0 * cm,      # DNI
            # 12 EPP verticales
            0.7 * cm, 0.7 * cm, 0.7 * cm, 0.7 * cm,
            0.7 * cm, 0.7 * cm, 0.7 * cm, 0.7 * cm,
            0.7 * cm, 0.7 * cm, 0.7 * cm, 0.7 * cm,
            4.3 * cm,      # Observaciones
            4.3 * cm,      # Firma
        ],
        repeatRows=1,
    )
    tabla_part.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.6, colors.black),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.black),
                ("BACKGROUND", (0, 0), (-1, 0), GRIS),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(tabla_part)
    story.append(Spacer(1, 3))

    # ========= CHARLA DE 5 MINUTOS =========
    story.append(P("CHARLA DE 5 MINUTOS", True, 8, "LEFT", AZUL, True))

    tema_charla = data.get("tema_charla", "")
    expositor_charla = data.get("expositor_charla", "")
    lugar_trabajo = data.get("lugar_trabajo", "")

    charla_data = [
        [
            P("TEMA", True, nowrap=True),
            P(tema_charla, False, 7, "LEFT"),
            P("EXPOSITOR", True, nowrap=True),
            P(expositor_charla, False, 7, "LEFT"),
        ],
        # Fila ATS combinada
        [
            P("ANALISIS DE TRABAJO SEGURO (ATS)", True, 7, "CENTER"),
            "", "", "",
        ],
        [
            P("TRABAJO A REALIZAR", True, nowrap=True),
            P(actividad, False, 7, "LEFT"),
            P("LUGAR DE TRABAJO", True, nowrap=True),
            P(lugar_trabajo, False, 7, "LEFT"),
        ],
    ]

    charla_tbl = Table(
        charla_data,
        colWidths=[6.0 * cm, 10.0 * cm, 4.0 * cm, 7.7 * cm],  # total 27.7
    )
    charla_tbl.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.6, colors.black),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.black),
                ("BACKGROUND", (0, 0), (-1, -1), GRIS),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                # Combinar celda ATS en fila 1 (segunda fila)
                ("SPAN", (0, 1), (-1, 1)),
                ("ALIGN", (0, 1), (-1, 1), "CENTER"),
            ]
        )
    )
    story.append(charla_tbl)
    story.append(Spacer(1, 3))

    # ========= MATRIZ DE RIESGOS =========
    story.append(
        P(
            "IDENTIFICACION DE PELIGROS, EVALUACION DE RIESGOS Y DETERMINACION DE CONTROLES",
            True,
            7,
            "LEFT",
            AZUL,
            True,
        )
    )

    riesgos = data.get("riesgos", []) or ["Sin riesgos registrados"]

    header_r = [
        P("ITEM", True, nowrap=True),
        P("ACTIVIDAD DEL TRABAJO A REALIZAR", True, nowrap=True),
        P("PELIGROS", True, nowrap=True),
        P("RIESGOS", True, nowrap=True),
        P("MEDIDAS DE CONTROL", True, nowrap=True),
        P("A", True, nowrap=True),
        P("M", True, nowrap=True),
        P("B", True, nowrap=True),
    ]
    filas_r = [header_r]

    for i, r in enumerate(riesgos, start=1):
        filas_r.append(
            [
                P(i),
                P(r, False, 6.3, "LEFT"),
                P("Riesgo mecánico / eléctrico / físico", False, 6.3, "LEFT"),
                P("Accidente / lesión / caída", False, 6.3, "LEFT"),
                P("Uso de EPP / señalización / orden y limpieza", False, 6.3, "LEFT"),
                P(""),
                P("X", True),
                P(""),
            ]
        )

    # 1.0 + 8.5 + 4.0 + 4.0 + 8.4 + 0.6 + 0.6 + 0.6 = 27.7
    matriz = Table(
        filas_r,
        colWidths=[
            1.0 * cm,
            8.5 * cm,
            4.0 * cm,
            4.0 * cm,
            8.4 * cm,
            0.6 * cm,
            0.6 * cm,
            0.6 * cm,
        ],
        repeatRows=1,
    )
    matriz.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.6, colors.black),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.black),
                ("BACKGROUND", (0, 0), (-1, 0), GRIS),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(matriz)
    story.append(Spacer(1, 2))

    story.append(P(
        "A: ALTO RIESGO INTOLERABLE REQUIERE DE CONTROL INMEDIATO. DE NO CONTROLARSE EL PELIGRO SE PARALIZA LA OBRA.",
        False, 6, "LEFT"))
    story.append(P(
        "M: INICIAR MEDIDAS PARA CONTROLAR/MINIMIZAR EL RIESGO. EVALUAR SI LA ACCION SE PUEDE EJECUTAR DE MANERA INMEDIATA",
        False, 6, "LEFT"))
    story.append(P("B: RIESGO TOLERABLE", False, 6, "LEFT"))
    story.append(Spacer(1, 3))

    # ========= RECOMENDACIONES =========
    story.append(P("RECOMENDACIONES", True, 7, "LEFT", AZUL, True))
    rec_text = data.get("recomendaciones", "")
    rec_tabla = Table(
        [[P(rec_text, False, 6.5, "LEFT")]],
        colWidths=[27.7 * cm],
    )
    rec_tabla.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.6, colors.black),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(rec_tabla)

    # ========= ESPACIO PARA FIRMAS =========
    story.append(Spacer(1, 18))  # espacio para firmas manuscritas

    firmas = Table(
        [
            ["", ""],
            [
                P("Encargado de CONTRATA/ CICSA PERU", True, 7, "CENTER", AZUL, True),
                P("Jefe de Obra /Supervisor CONTRATA/ CICSA PERU", True, 7, "CENTER", AZUL, True),
            ],
        ],
        colWidths=[13.85 * cm, 13.85 * cm],  # 27.7
    )
    firmas.setStyle(
        TableStyle(
            [
                ("LINEABOVE", (0, 1), (0, 1), 0.8, colors.black),
                ("LINEABOVE", (1, 1), (1, 1), 0.8, colors.black),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(firmas)
    story.append(Spacer(1, 3))

    # ========= IMAGEN DEL PERSONAL EN CAMPO CON EPP (1 POR TÉCNICO) =========
    fotos_rows = []

    # Fotos individuales por técnico (si existen)
    for t in tecnicos:
        nombre = t.get("nombre", "")
        fpath = t.get("foto_path")
        if fpath and os.path.exists(fpath):
            fotos_rows.append(
                [
                    P(nombre, False, 6.5, "LEFT"),
                    IMG(fpath, 4.5 * cm, 3.5 * cm),
                ]
            )

    # Foto general (compatibilidad) si no hay fotos individuales
    foto_general = data.get("foto_path")
    if not fotos_rows and foto_general and os.path.exists(foto_general):
        for t in tecnicos:
            fotos_rows.append(
                [
                    P(t.get("nombre", ""), False, 6.5, "LEFT"),
                    IMG(foto_general, 4.5 * cm, 3.5 * cm),
                ]
            )

    if fotos_rows:
        story.append(P("IMAGEN DEL PERSONAL EN CAMPO CON EPP", True, 7, "LEFT", AZUL, True))

        filas_foto = [
            [P("Nombre y Apellidos", True, 6.5, "CENTER"),
             P("Foto", True, 6.5, "CENTER")]
        ] + fotos_rows

        tabla_foto = Table(
            filas_foto,
            colWidths=[13.85 * cm, 13.85 * cm],
        )
        tabla_foto.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.6, colors.black),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.black),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        story.append(tabla_foto)
        story.append(Spacer(1, 2))

    # ========= PIE =========
    story.append(
        P(
            "Área de Seguridad y Salud en el Trabajo — CICSA PERÚ S.A.C.",
            True,
            7,
            "CENTER",
            AZUL,
            True,
        )
    )

    # Construir PDF
    doc.build(story)

    # Limpieza temporales (firmas + fotos)
    try:
        # Foto general
        if foto_general and os.path.exists(foto_general):
            os.remove(foto_general)
        # Firmas y fotos por técnico
        for t in tecnicos:
            f = t.get("firma_path")
            if f and os.path.exists(f):
                os.remove(f)
            ft = t.get("foto_path")
            if ft and os.path.exists(ft):
                os.remove(ft)
    except Exception:
        pass

    return filename
