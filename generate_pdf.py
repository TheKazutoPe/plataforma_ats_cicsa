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
    if not path or not os.path.exists(path):
        return ""
    try:
        return Image(path, width=w, height=h)
    except Exception as e:
        print(f"Error cargando imagen en PDF: {e}")
        return ""


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
    filename = data.get("pdf_filename") or f"ATS_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

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
            0.7 * cm,
            6.0 * cm,
            2.0 * cm,
            2.0 * cm,
            0.7 * cm, 0.7 * cm, 0.7 * cm, 0.7 * cm,
            0.7 * cm, 0.7 * cm, 0.7 * cm, 0.7 * cm,
            0.7 * cm, 0.7 * cm, 0.7 * cm, 0.7 * cm,
            4.3 * cm,
            4.3 * cm,
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
        colWidths=[6.0 * cm, 10.0 * cm, 4.0 * cm, 7.7 * cm],
    )
    charla_tbl.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.6, colors.black),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.black),
                ("BACKGROUND", (0, 0), (-1, -1), GRIS),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
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

    MATRIZ_ATS_PEX = {
        'CONDUCCION DE VEHICULOS MENORES': {
            'peligros': 'Condiciones de vía, fallas mecánicas, clima, imprudencia y distracciones.',
            'riesgos': 'Choques/colisiones, atropellos, caídas, lesiones personales y daños materiales.',
            'controles': 'Checklist preuso, mantenimiento al día, licencia vigente, conducción defensiva, límites de velocidad, cinturón/casco, prohibido celular, plan de ruta y estacionamiento seguro.',
            'nivel': 'M',
        },
        'SEÑALIZACION Y CONTROL DE TRANSITO EN VIA PUBLICA (CONOS / VIGIA / CIERRE PARCIAL)': {
            'peligros': 'Tránsito vehicular, mala visibilidad, conductores distraídos, trabajo en borde de vía.',
            'riesgos': 'Atropello, choque, golpes y lesiones a trabajadores/terceros.',
            'controles': 'Plan de señalización (conos, cinta, paletas), vigía, chaleco reflectivo, iluminación/flashers, ubicar vehículo en protección, permisos y coordinación con tránsito.',
            'nivel': 'M',
        },
        'INSPECCION DE RUTA Y RECONOCIMIENTO DE ZONA DE TRABAJO (WALKDOWN)': {
            'peligros': 'Terreno irregular, pendientes, obstáculos, animales/insectos, tránsito cercano.',
            'riesgos': 'Caídas al mismo nivel, picaduras/mordeduras, golpes, atropello.',
            'controles': 'Inspección previa, ruta segura, calzado antideslizante, repelente, chaleco reflectivo, comunicación y delimitación del área antes de iniciar.',
            'nivel': 'M',
        },
        'APERTURA DE CAMARAS / BUZONES Y MANIPULACION DE DUCTERIA (RIESGO DE ESPACIO CONFINADO)': {
            'peligros': 'Espacio confinado (gases, falta de oxígeno), agua/inundación, caída a distinto nivel, residuos biológicos, herramientas/cortes.',
            'riesgos': 'Asfixia/intoxicación, caídas, infecciones, golpes y cortes.',
            'controles': 'No ingresar sin autorización, medición de gases, ventilación, línea de vida si aplica, barandas/tapa asegurada, guantes, lentes, linterna, orden/limpieza y supervisión.',
            'nivel': 'M',
        },
        'EXCAVACION MANUAL / ZANJADO PARA CANALIZACION O LOCALIZACION DE DUCTOS': {
            'peligros': 'Derrumbe, servicios enterrados (eléctrico/agua/gas), herramientas manuales, proyección de partículas, tránsito.',
            'riesgos': 'Atrapamiento, electrocución/daño a redes, cortes/golpes, lesiones graves.',
            'controles': 'Permiso de excavación, detección de servicios, zanja con talud/entibado según profundidad, señalizar y aislar, EPP completo (casco, guantes, lentes), no excavar con lluvia intensa.',
            'nivel': 'M',
        },
        'TENDIDO / JALADO DE CABLE FO POR DUCTERIA (WINCHE / SOPLADORA / HALADO MANUAL)': {
            'peligros': 'Tensión del cable, atrapamientos en rodillos/winche, retroceso del cable, manipulación de bobinas, tránsito.',
            'riesgos': 'Golpes, atrapamientos, cortes, lesiones musculares, daños al cable.',
            'controles': 'Comunicación entre puntos, área despejada, guantes anticorte, no poner manos en rodillos, usar freno/guía, respetar radios de curvatura, señalizar zona y usar soportes para bobina.',
            'nivel': 'M',
        },
        'TENDIDO AEREO DE CABLE FO EN POSTES (FLEJADO / SUSPENSION / CRUCES)': {
            'peligros': 'Trabajo en altura, cercanía a líneas eléctricas, caída de objetos, viento/clima, tránsito.',
            'riesgos': 'Caídas graves, electrocución, lesiones por objetos caídos, atropello.',
            'controles': 'Distancia segura a redes eléctricas, arnés/línea de vida si aplica, escalera certificada y asegurada, delimitar zona inferior, casco con barboquejo, vigía y suspender por clima adverso.',
            'nivel': 'M',
        },
        'TRABAJOS EN ALTURA CON ESCALERAS TELESCOPICAS PARA SUBIR CABLES DE COMUNICACIÓN CAIDOS AL SUELO': {
            'peligros': 'Caídas de altura, falla de escalera, tránsito vehicular, riesgo eléctrico, caída de herramientas, sobreesfuerzos, clima adverso, atrapamientos.',
            'riesgos': 'Lesiones graves o fatales por caída; electrocución; atropellos; golpes y cortes; caída de objetos; distensiones musculares.',
            'controles': 'Escalera certificada e inspeccionada; señalización de tránsito; distancia segura a cables eléctricos; ayudante para estabilizar; arnés cuando aplique; guantes adecuados; calzado antideslizante; ropa/chaleco reflectivo.',
            'nivel': 'M',
        },
        'TRABAJO EN POSTE CON ARNES Y LINEA DE VIDA (SI APLICA)': {
            'peligros': 'Trabajo en altura en poste, puntos de anclaje inadecuados, fatiga, herramientas, riesgo eléctrico.',
            'riesgos': 'Caídas graves/fatales, golpes/cortes, electrocución.',
            'controles': 'Arnés de cuerpo completo, línea de vida y anclaje certificado, inspección de EPP, técnica de ascenso segura, herramientas con talabarte, mantener distancia a redes energizadas y vigía.',
            'nivel': 'M',
        },
        'MEDICION CON EQUIPO OTDR PARA DETERMINAR LA DISTANCIA APROXIMADA DE ROTURA DE LA FIBRA OPTICA': {
            'peligros': 'Señal láser activa, filamentos cortantes, caídas al mismo nivel, riesgo eléctrico por equipo/cargador, tránsito vehicular, mala postura, iluminación deficiente.',
            'riesgos': 'Daño ocular, cortes, caídas, electrocución leve, fallas de medición o daño del OTDR, lesiones musculares, atropellos.',
            'controles': 'Verificar enlace sin luz activa, organizar cables, señalizar área, usar cargadores certificados, evitar humedad/lluvia, guantes anticorte, calzado seguro y chaleco reflectivo.',
            'nivel': 'M',
        },
        'FUSION DE FIBRA OPTICA EN CASO DE SER  NECESARIO AL NIVEL DEL SUELO O EN ALTURA': {
            'peligros': 'Filamentos cortantes, señal láser, posturas forzadas, caídas al mismo nivel, riesgo eléctrico por equipos, trabajo en altura, falla de escalera, contactos eléctricos, caída de objetos.',
            'riesgos': 'Cortes, daño ocular, lesiones musculares, caídas (mismo nivel o altura), golpes y cortes, impacto a terceros por objetos caídos.',
            'controles': 'Mesa/soporte estable, contenedor para filamentos, señalización, verificar enlace sin luz activa, orden y limpieza, guantes anticorte, gafas, escalera certificada, arnés si aplica, calzado antideslizante y ropa reflectiva.',
            'nivel': 'M',
        },
        'EMPALME / CONECTORIZACION EN NAP / CTO / CAJAS TERMINALES (MANEJO DE FIBRA)': {
            'peligros': 'Filamentos de fibra, señal láser, herramientas punzocortantes, polvo/humedad, posturas forzadas.',
            'riesgos': 'Cortes, daño ocular, irritación, fallas de conectividad, lesiones musculares.',
            'controles': 'Verificar enlace sin luz, limpieza de conectores, guantes anticorte, gafas, contenedor para restos, iluminación adecuada, mesa/soporte estable y orden/limpieza.',
            'nivel': 'M',
        },
        'USO DE HERRAMIENTAS ELECTRICAS PORTATILES (TALADRO / AMOLADORA / SIERRA)': {
            'peligros': 'Partes giratorias, proyección de partículas, cortes, cables eléctricos dañados, ruido.',
            'riesgos': 'Cortes/amputaciones, lesiones oculares, electrocución, quemaduras, hipoacusia.',
            'controles': 'Inspección de herramienta, guardas instaladas, lentes/careta, guantes adecuados, protector auditivo si aplica, RCD/diferencial, cables en buen estado y área despejada.',
            'nivel': 'M',
        },
        'MANIPULACION Y TRANSPORTE DE BOBINAS, ESCALERAS Y HERRAMIENTAS (CARGA / DESCARGA)': {
            'peligros': 'Sobreesfuerzo, golpes por carga, caída de objetos, atrapamientos, mal agarre.',
            'riesgos': 'Lumbalgias, esguinces, contusiones, cortes.',
            'controles': 'Levantamiento seguro, 2 personas para cargas pesadas, carros/diablitos, guantes, calzado de seguridad, asegurar bobinas/escaleras en vehículo y mantener orden.',
            'nivel': 'M',
        },
        'USO DE GENERADOR ELECTRICO / EXTENSIONES EN CAMPO': {
            'peligros': 'Electricidad, combustibles, monóxido/ventilación deficiente, cables expuestos, incendio.',
            'riesgos': 'Electrocución, quemaduras, intoxicación, incendio.',
            'controles': 'Generador en zona ventilada, puesta a tierra, extintor, combustible controlado, cables y conexiones en buen estado, RCD/diferencial, no operar bajo lluvia sin protección y señalizar el área.',
            'nivel': 'M',
        },
        'TRABAJO NOCTURNO O EN BAJA ILUMINACION': {
            'peligros': 'Baja visibilidad, fatiga, tránsito, terreno irregular, seguridad ciudadana.',
            'riesgos': 'Atropello, caídas, golpes, errores operativos.',
            'controles': 'Iluminación portátil, chaleco reflectivo y luces intermitentes, pausas y rotación, vigía, señalizar ampliamente, comunicación y evaluación de seguridad de la zona.',
            'nivel': 'M',
        }
    }


    for i, r in enumerate(riesgos, start=1):
        info = MATRIZ_ATS_PEX.get(r)
        if info:
            pel_txt = info.get("peligros", "")
            rie_txt = info.get("riesgos", "")
            ctrl_txt = info.get("controles", "")
            nivel = (info.get("nivel") or "M").strip().upper()
        else:
            # Fallback (si marcan un riesgo genérico del checklist)
            pel_txt = "Riesgo mecánico / eléctrico / físico"
            rie_txt = "Accidente / lesión / caída"
            ctrl_txt = "Uso de EPP / señalización / orden y limpieza"
            nivel = "M"

        a_mark = "X" if nivel == "A" else ""
        m_mark = "X" if nivel == "M" else ""
        b_mark = "X" if nivel == "B" else ""

        filas_r.append(
            [
                P(i),
                P(r, False, 6.3, "LEFT"),
                P(pel_txt, False, 6.3, "LEFT"),
                P(rie_txt, False, 6.3, "LEFT"),
                P(ctrl_txt, False, 6.3, "LEFT"),
                P(a_mark, True),
                P(m_mark, True),
                P(b_mark, True),
            ]
        )
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
    story.append(Spacer(1, 18))

    # Firma del Encargado: debe ser uno de los técnicos del ATS
    enc_idx = data.get("encargado_idx")
    encargado = None
    if isinstance(enc_idx, int) and tecnicos and 1 <= enc_idx <= len(tecnicos):
        encargado = tecnicos[enc_idx - 1]
    else:
        # fallback: primer técnico con firma
        for tinfo in tecnicos:
            if tinfo.get("firma_path"):
                encargado = tinfo
                break

    enc_sig = P("")
    enc_name = ""
    if encargado:
        enc_name = (encargado.get("nombre") or "").strip()
        fp = encargado.get("firma_path")
        if fp and os.path.exists(fp):
            enc_sig = IMG(fp, 6.4 * cm, 2.0 * cm)

    enc_cell = Table(
        [[enc_sig], [P(enc_name or "", False, 7, "CENTER")]],
        colWidths=[13.85 * cm],
        rowHeights=[2.4 * cm, 0.6 * cm],
    )
    enc_cell.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    firmas = Table(
        [
            [enc_cell, ""],
            [
                P("Encargado de CONTRATA/ CICSA PERU", True, 7, "CENTER", AZUL, True),
                P("Jefe de Obra /Supervisor CONTRATA/ CICSA PERU", True, 7, "CENTER", AZUL, True),
            ],
        ],
        colWidths=[13.85 * cm, 13.85 * cm],
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

    # ========= IMAGEN DEL PERSONAL EN CAMPO CON EPP =========
    fotos_rows = []

    # Fotos individuales por técnico
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

    # Foto general si no hay individuales
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

    # La limpieza de archivos temporales se centraliza ahora en main.py

    return filename
