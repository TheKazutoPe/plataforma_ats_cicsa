import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import os
import json
from datetime import datetime
import time
import re
def _extract_email(addr: str) -> str:
    """Normaliza un email para comparación (soporta 'Nombre <email@dominio>')."""
    if not addr:
        return ""
    addr = str(addr).strip()
    m = re.search(r"<\s*([^>\s]+)\s*>", addr)
    if m:
        addr = m.group(1)
    return addr.strip().lower()


def _dedupe_emails(seq):
    """Quita duplicados preservando orden, usando email normalizado como clave."""
    seen = set()
    out = []
    for a in seq:
        key = _extract_email(a)
        if not key:
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append(a.strip())
    return out


def enviar_correo(pdf_path: str, supervisor: str, subject: str) -> bool:
    """
    Envía el PDF por correo usando la config del .env.
    Destinatarios:
      - Si el supervisor existe en SUPERVISOR_EMAILS_JSON:
            TO = correo del supervisor
      - Si NO existe:
            TO = MAIL_TO_DEFAULT (si está configurado)
      - CC = MAIL_CC (si está configurado)

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

    # Timeout corto para no colgar el request
    timeout = int(os.getenv("SMTP_TIMEOUT", "5"))

    # Reintentos
    max_retries = int(os.getenv("SMTP_MAX_RETRIES", "2"))

    if not remitente or not password:
        print("⚠️ SMTP_USER / SMTP_PASS no configurado. No se envía correo.")
        return False

    # ===============================
    # RESOLVER DESTINATARIOS
    # ===============================
    destinatarios = []

    # CC (copias fijas)
    cc_raw = os.getenv("MAIL_CC", "")
    if cc_raw:
        cc = [c.strip() for c in cc_raw.split(",") if c.strip()]
    else:
        cc = []

    # Destinatario por defecto (para cuando no haya supervisor con correo)
    default_to = os.getenv("MAIL_TO_DEFAULT")

    # Correos de supervisores desde JSON (SUPERVISOR_EMAILS_JSON)
    sup_json = os.getenv("SUPERVISOR_EMAILS_JSON", "{}")
    try:
        mapa_supervisores = json.loads(sup_json)
    except Exception as e:
        print(f"⚠️ Error parseando SUPERVISOR_EMAILS_JSON: {e}")
        mapa_supervisores = {}

    correo_sup = None
    if supervisor:
        sup_norm = supervisor.strip()
        sup_norm_upper = sup_norm.upper()

        # Búsqueda directa por clave exacta
        if sup_norm in mapa_supervisores:
            correo_sup = mapa_supervisores[sup_norm]
        elif sup_norm_upper in mapa_supervisores:
            correo_sup = mapa_supervisores[sup_norm_upper]
        else:
            # Búsqueda normalizada (por si hay espacios, mayúsculas, etc.)
            for k, v in mapa_supervisores.items():
                if k.strip().upper() == sup_norm_upper:
                    correo_sup = v
                    break

    # Regla principal de destinatarios:
    # 1) Si el supervisor tiene correo → enviar SOLO a él en TO.
    # 2) Si no tiene → enviar al MAIL_TO_DEFAULT (si existe).
    if correo_sup:
        destinatarios.append(correo_sup)
        print(f"ℹ️ Supervisor '{supervisor}' reconocido. Enviando a su correo: {correo_sup}")
    else:
        if default_to:
            destinatarios.append(default_to)
            print(
                f"ℹ️ Supervisor '{supervisor}' sin correo configurado. "
                f"Se usa MAIL_TO_DEFAULT: {default_to}"
            )
        else:
            print(
                f"⚠️ Supervisor '{supervisor}' sin correo y MAIL_TO_DEFAULT no configurado. "
                f"No hay destinatarios en TO."
            )


    # ===============================
    # EVITAR AUTOENVÍO (NO enviarse a sí mismo)
    # ===============================
    sender_email = _extract_email(remitente)

    # Quitar remitente de TO/CC si aparece por error en el mapa, default o CC.
    destinatarios = [d for d in destinatarios if _extract_email(d) != sender_email]
    cc = [c for c in cc if _extract_email(c) != sender_email]

    # Quitar duplicados y vacíos
    destinatarios = _dedupe_emails(destinatarios)
    cc = _dedupe_emails(cc)

    # Si el único destino era el remitente, no enviamos (para evitar spam / bloqueos)
    if not destinatarios and not cc:
        print(
            "⚠️ Destinatarios vacíos luego de filtrar autoenvío. "
            "Revisa SUPERVISOR_EMAILS_JSON / MAIL_TO_DEFAULT / MAIL_CC."
        )
        return False


    # Validar que haya al menos un destinatario en TO o CC
    if not destinatarios and not cc:
        print("⚠️ No hay destinatarios configurados (ni TO ni CC). No se envía correo.")
        return False

    # ===============================
    # VALIDAR PDF
    # ===============================
    if not pdf_path or not os.path.isfile(pdf_path):
        print(f"⚠️ No se encontró el archivo PDF para adjuntar: {pdf_path}")
        return False

    # ===============================
    # CONSTRUIR MENSAJE
    # ===============================
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

    # ===============================
    # ENVÍO CON TIMEOUT + REINTENTOS
    # ===============================
    for intento in range(1, max_retries + 1):
        try:
            with smtplib.SMTP(smtp_server, smtp_port, timeout=timeout) as server:
                server.starttls()
                server.login(remitente, password)

                # TO reales = destinatarios + CC (porque send_message no reenvía a "Cc" automáticamente)
                all_recipients = destinatarios + cc
                server.send_message(msg, to_addrs=all_recipients)

            print(
                f"✅ Correo enviado. TO: {destinatarios}  CC: {cc} "
                f"(intento {intento}/{max_retries})"
            )
            return True

        except Exception as e:
            print(
                f"⚠️ Error enviando correo (intento {intento}/{max_retries}, "
                f"manejado, no se cae la app): {e}"
            )
            if intento < max_retries:
                time.sleep(2)

    # Si llegó aquí, todos los intentos fallaron
    return False
