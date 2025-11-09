import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import os
import json
from datetime import datetime


def enviar_correo(pdf_path: str, supervisor: str, subject: str) -> bool:
    """
    Envía el PDF por correo usando la config del .env.
    Retorna:
      - True si el correo se envió correctamente.
      - False si hubo cualquier problema (SIN romper la app).
    """

    # === Configuración básica SMTP ===
    remitente = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASS")
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    from_header = os.getenv("MAIL_FROM", remitente or "")
    timeout = int(os.getenv("SMTP_TIMEOUT", "8"))

    if not remitente or not password:
        print("⚠️ SMTP_USER / SMTP_PASS no configurado. No se envía correo.")
        return False

    # === Destinatarios ===
    destinatarios = []

    # Destinatario por defecto
    default_to = os.getenv("MAIL_TO_DEFAULT")
    if default_to:
        destinatarios.append(default_to)

    # CC (opcional)
    cc_raw = os.getenv("MAIL_CC", "")
    cc = [c.strip() for c in cc_raw.split(",") if c.strip()] if cc_raw else []

    # Correos de supervisores desde JSON
    sup_json = os.getenv("SUPERVISOR_EMAILS_JSON", "{}")
    try:
        mapa_supervisores = json.loads(sup_json)
    except Exception as e:
        print(f"⚠️ Error parseando SUPERVISOR_EMAILS_JSON: {e}")
        mapa_supervisores = {}

    correo_sup = None
    if supervisor:
        # Normalizamos claves para evitar fallos por mayúsculas
        sup_norm = supervisor.strip()
        sup_norm_upper = sup_norm.upper()

        # Buscar directo
        if sup_norm in mapa_supervisores:
            correo_sup = mapa_supervisores[sup_norm]
        elif sup_norm_upper in mapa_supervisores:
            correo_sup = mapa_supervisores[sup_norm_upper]
        else:
            # Intento flexible
            for k, v in mapa_supervisores.items():
                if k.strip().upper() == sup_norm_upper:
                    correo_sup = v
                    break

    if correo_sup:
        destinatarios.append(correo_sup)
    else:
        print(f"ℹ️ No se encontró correo específico para el supervisor '{supervisor}'. Se usa solo MAIL_TO_DEFAULT/CC.")

    # Validar que haya al menos un destinatario
    if not destinatarios and not cc:
        print("⚠️ No hay destinatarios configurados. No se envía correo.")
        return False

    # Validar PDF
    if not pdf_path or not os.path.isfile(pdf_path):
        print(f"⚠️ No se encontró el archivo PDF para adjuntar: {pdf_path}")
        return False

    # === Construcción del mensaje ===
    msg = MIMEMultipart()
    msg["From"] = from_header or remitente
    msg["To"] = ", ".join(destinatarios)
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg["Subject"] = subject

    fecha_actual = datetime.now().strftime("%Y-%m-%d")

    body = f"""
    Estimado(a),<br><br>
    Se adjunta el reporte ATS generado desde la plataforma.<br><br>
    <b>Supervisor:</b> {supervisor or '-'}<br>
    <b>Fecha:</b> {fecha_actual}<br><br>
    Saludos cordiales,<br>
    <b>CICSA – Sistema de Reportes ATS</b>
    """
    msg.attach(MIMEText(body, "html"))

    # Adjuntar PDF
    try:
        with open(pdf_path, "rb") as f:
            attach = MIMEApplication(f.read(), _subtype="pdf")
        attach.add_header(
            "Content-Disposition",
            "attachment",
            filename=os.path.basename(pdf_path),
        )
        msg.attach(attach)
    except Exception as e:
        print(f"⚠️ Error leyendo el PDF para adjuntar: {e}")
        return False

    # === Envío (con timeout y manejo de errores) ===
    try:
        with smtplib.SMTP(smtp_server, smtp_port, timeout=timeout) as server:
            server.starttls()
            server.login(remitente, password)
            server.send_message(msg)

        print(f"✅ Correo enviado a: {destinatarios}  CC: {cc}")
        return True

    except Exception as e:
        # Importante: NO reventar la app, solo loguear
        print(f"⚠️ Error enviando correo (manejado, no se cae la app): {e}")
        return False
