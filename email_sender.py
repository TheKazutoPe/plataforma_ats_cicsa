import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import os, json
from datetime import datetime

def enviar_correo(pdf_path, supervisor, subject):
    remitente = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASS")
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))

    # Destinatarios principales y copia
    destinatarios = [os.getenv("MAIL_TO_DEFAULT", "a.pradou@ccicsa.com.mx")]
    cc = os.getenv("MAIL_CC", "").split(",") if os.getenv("MAIL_CC") else []

    # Correos de supervisores (desde .env)
    sup_json = os.getenv("SUPERVISOR_EMAILS_JSON", "{}")
    try:
        mapa_supervisores = json.loads(sup_json)
    except Exception:
        mapa_supervisores = {}

    if supervisor in mapa_supervisores:
        destinatarios.append(mapa_supervisores[supervisor])

    # Crear correo
    msg = MIMEMultipart()
    msg["From"] = remitente
    msg["To"] = ", ".join(destinatarios)
    msg["Cc"] = ", ".join(cc)
    msg["Subject"] = subject

    fecha_actual = datetime.now().strftime("%Y-%m-%d")

    body = f"""
    Estimado(a),<br><br>
    Se adjunta el reporte ATS generado.<br><br>
    <b>Supervisor:</b> {supervisor}<br>
    <b>Fecha:</b> {fecha_actual}<br><br>
    Saludos,<br>
    <b>CICSA – Sistema de Reportes ATS</b>
    """
    msg.attach(MIMEText(body, "html"))

    # Adjuntar el PDF
    with open(pdf_path, "rb") as f:
        attach = MIMEApplication(f.read(), _subtype="pdf")
        attach.add_header("Content-Disposition", "attachment", filename=os.path.basename(pdf_path))
        msg.attach(attach)

    # Envío
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(remitente, password)
        server.send_message(msg)

    print(f"✅ Correo enviado a: {destinatarios}  CC: {cc}")
