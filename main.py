from flask import Flask, render_template, request, redirect, session, url_for
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime
from threading import Thread
import base64
import os

from generate_pdf import generar_pdf
from email_sender import enviar_correo

# =========================
# CONFIGURACIÓN BASE
# =========================
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("❌ SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY no configurados en el entorno.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "cicsa-secret-key")

PDF_BUCKET = os.getenv("PDF_BUCKET", "ats-pdfs")


# =========================
# HELPERS DE SESIÓN
# =========================
def is_logged_in():
    return "user" in session


def get_user():
    return session.get("user")


# =========================
# RUTA PRINCIPAL
# =========================
@app.route("/")
def index():
    return redirect(url_for("login"))


# =========================
# LOGIN
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        usuario = (request.form.get("usuario") or "").strip()
        clave = (request.form.get("clave") or "").strip()

        if not usuario or not clave:
            error = "Usuario y clave son requeridos."
        else:
            try:
                resp = (
                    supabase.table("usuarios_brigadas")
                    .select(
                        "usuario,nombre,cargo,brigada,zona,contrata,activo,dni"
                    )
                    .eq("usuario", usuario)
                    .eq("clave", clave)
                    .eq("activo", True)
                    .limit(1)
                    .execute()
                )
                data = resp.data or []
                if not data:
                    error = "Usuario o clave incorrectos, o usuario inactivo."
                else:
                    user = data[0]
                    session["user"] = {
                        "usuario": user.get("usuario"),
                        "nombre": user.get("nombre"),
                        "cargo": user.get("cargo"),
                        "brigada": user.get("brigada"),
                        "zona": user.get("zona"),
                        "contrata": user.get("contrata"),
                        "dni": user.get("dni"),
                    }
                    return redirect(url_for("formulario"))
            except Exception as e:
                print("❌ Error consultando usuarios_brigadas:", e)
                error = "Error interno al validar usuario."

    return render_template("login.html", error=error)


# =========================
# FORMULARIO ATS
# =========================
@app.route("/formulario", methods=["GET", "POST"])
def formulario():
    user = get_user()
    if not user:
        return redirect(url_for("login"))

    # Técnicos activos
    try:
        tecnicos = (
            supabase.table("usuarios_brigadas")
            .select("usuario,nombre,cargo,brigada,zona,contrata,dni,activo")
            .eq("activo", True)
            .order("nombre")
            .execute()
        ).data or []
    except Exception:
        tecnicos = []

    mensaje = None
    error = None

    if request.method == "POST":
        try:
            data = {}

            # =========================
            # DATOS GENERALES
            # =========================
            data["usuario_registro"] = user.get("usuario")
            data["nombre_registro"] = user.get("nombre")
            data["brigada_usuario"] = user.get("brigada")
            data["zona_usuario"] = user.get("zona")
            data["contrata"] = user.get("contrata")

            data["empresa"] = request.form.get("empresa", "CICSA PERU S.A.C.")
            data["contrata"] = (
                request.form.get("contrata") or user.get("contrata") or "CICSA PERU S.A.C."
            )
            data["actividad"] = request.form.get("actividad", "")
            data["fecha_dia"] = request.form.get("fecha_dia", "")
            data["hora_inicio"] = request.form.get("hora_inicio", "")
            data["hora_fin"] = request.form.get("hora_fin", "")
            data["area"] = request.form.get("area", "MRD F.O.")

            data["supervisor"] = request.form.get("supervisor", "").strip()
            data["lugar_trabajo"] = request.form.get("lugar_trabajo", "").strip()
            data["coordenadas"] = request.form.get("coordenadas", "").strip()
            data["riesgos_adicionales"] = request.form.get("riesgos_adicionales", "").strip()

            # =========================
            # TAREAS / ACTIVIDADES
            # =========================
            actividades = []
            for i in range(1, 11):
                tarea = request.form.get(f"tarea{i}", "").strip()
                riesgo = request.form.get(f"riesgo{i}", "").strip()
                medida = request.form.get(f"medida{i}", "").strip()
                responsable = request.form.get(f"responsable{i}", "").strip()

                if not (tarea or riesgo or medida or responsable):
                    continue

                actividades.append(
                    {
                        "item": i,
                        "tarea": tarea,
                        "riesgo": riesgo,
                        "medida": medida,
                        "responsable": responsable,
                    }
                )
            data["actividades"] = actividades

            # =========================
            # TÉCNICOS / PARTICIPANTES
            # =========================
            tecnicos_post = []
            for i in range(1, 11):
                key = (request.form.get(f"tec{i}") or "").strip()
                if not key:
                    continue

                tec = next((t for t in tecnicos if t.get("usuario") == key), None)
                if not tec:
                    continue

                fila = {
                    "item": i,
                    "usuario": tec.get("usuario", ""),
                    "nombre": tec.get("nombre", ""),
                    "cargo": tec.get("cargo", ""),
                    "dni": tec.get("dni", ""),
                    "brigada": tec.get("brigada", ""),
                    "zona": tec.get("zona", ""),
                    "contrata": tec.get("contrata", ""),
                    "epp": request.form.getlist(f"epp{i}[]"),
                    "obs": (request.form.get(f"obs{i}", "") or "").strip(),
                }

                # Firma desde canvas
                firma_b64 = request.form.get(f"firma{i}")
                fila["firma_path"] = None
                if firma_b64 and "base64" in firma_b64:
                    try:
                        raw = firma_b64.split(",")[-1]
                        firma_path = os.path.join(
                            "temp",
                            f"firma_tec{i}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                        )
                        os.makedirs("temp", exist_ok=True)
                        with open(firma_path, "wb") as img_f:
                            img_f.write(base64.b64decode(raw))
                        fila["firma_path"] = firma_path
                    except Exception as e:
                        print(f"⚠️ Error guardando firma del técnico {i}: {e}")

                tecnicos_post.append(fila)

            data["tecnicos"] = tecnicos_post

            # Firma del supervisor
            firma_sup_b64 = request.form.get("firma_supervisor")
            data["firma_supervisor_path"] = None
            if firma_sup_b64 and "base64" in firma_sup_b64:
                try:
                    raw = firma_sup_b64.split(",")[-1]
                    firma_sup_path = os.path.join(
                        "temp",
                        f"firma_sup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                    )
                    os.makedirs("temp", exist_ok=True)
                    with open(firma_sup_path, "wb") as img_f:
                        img_f.write(base64.b64decode(raw))
                    data["firma_supervisor_path"] = firma_sup_path
                except Exception as e:
                    print("⚠️ Error guardando firma del supervisor:", e)

            # =========================
            # GENERAR PDF
            # =========================
            pdf_path = generar_pdf(data)
            if not pdf_path or not os.path.isfile(pdf_path):
                raise RuntimeError("No se pudo generar el PDF.")

            # =========================
            # ENVIAR CORREO (ASÍNCRONO)
            # =========================
            # ===== Enviar correo con PDF (ASÍNCRONO: no bloquea el formulario) =====
            supervisor = data.get("supervisor", "SIN SUPERVISOR")
            fecha_actual = datetime.now().strftime("%Y-%m-%d")
            brigada_usuario = (user.get("brigada") or "SIN BRIGADA").upper()
            subject = f"Reporte ATS – {supervisor} – {brigada_usuario} – {fecha_actual}"

            def _enviar_correo_async(pdf_path_local, supervisor_local, subject_local):
                try:
                    enviar_correo(pdf_path_local, supervisor_local, subject_local)
                except Exception as e:
                    print("⚠️ Error al enviar correo (hilo en segundo plano):", e)

            try:
                Thread(
                    target=_enviar_correo_async,
                    args=(pdf_path, supervisor, subject),
                    daemon=True,
                ).start()
                email_ok = True  # asumimos OK de cara al usuario; el hilo reporta errores en logs
            except Exception as e:
                print("⚠️ No se pudo lanzar el hilo de envío de correo:", e)
                email_ok = False

            # =========================
            # SUBIR PDF A SUPABASE STORAGE
            # =========================
            pdf_storage_path = None
            pdf_public_url = None
            try:
                if os.path.isfile(pdf_path):
                    pdf_filename = os.path.basename(pdf_path)
                    pdf_storage_path = f"ats/{datetime.now().strftime('%Y/%m/%d')}/{pdf_filename}"

                    with open(pdf_path, "rb") as f:
                        file_data = f.read()

                    supabase.storage.from_(PDF_BUCKET).upload(
                        pdf_storage_path,
                        file_data,
                        {"content-type": "application/pdf"},
                    )

                    base_url = SUPABASE_URL.rstrip("/")
                    pdf_public_url = (
                        f"{base_url}/storage/v1/object/public/{PDF_BUCKET}/{pdf_storage_path}"
                    )
                else:
                    print("⚠️ PDF no encontrado para subir a Supabase Storage:", pdf_path)
            except Exception as e:
                print("⚠️ Error al subir PDF a Supabase Storage:", e)
                pdf_storage_path = None
                pdf_public_url = None

            # =========================
            # REGISTRO DIARIO EN SUPABASE
            # =========================
            try:
                fecha_reg = data["fecha_dia"]
                brigada_reg = data.get("brigada_usuario")
                zona_reg = data.get("zona_usuario")
                contrata_reg = data.get("contrata")
                usuario_reg = data.get("usuario_registro")
                supervisor_reg = data.get("supervisor")
                tecnicos_count = len(tecnicos_post)

                registro = {
                    "fecha": fecha_reg,
                    "brigada": brigada_reg,
                    "zona": zona_reg,
                    "contrata": contrata_reg,
                    "usuario_registro": usuario_reg,
                    "supervisor": supervisor_reg,
                    "tecnicos_count": tecnicos_count,
                    "completado": True,
                    "pdf_path": pdf_storage_path,
                    "pdf_url": pdf_public_url,
                }

                supabase.table("ats_registros_diarios").insert(registro).execute()
            except Exception as e:
                print("⚠️ Error registrando ats_registros_diarios:", e)

            # =========================
            # MENSAJE FINAL AL USUARIO
            # =========================
            if email_ok:
                mensaje = "✅ Reporte ATS generado, registrado y envío de correo en proceso."
            else:
                mensaje = (
                    "⚠️ Reporte ATS generado y registrado en la plataforma. "
                    "No se pudo lanzar correctamente el envío automático de correo."
                )

        except Exception as e:
            print("❌ Error general en POST /formulario:", e)
            error = "Ocurrió un error al procesar el formulario. Intente nuevamente."

    return render_template(
        "formulario.html",
        user=user,
        tecnicos=tecnicos,
        mensaje=mensaje,
        error=error,
    )


# =========================
# LOGOUT
# =========================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# =========================
# MAIN LOCAL
# =========================
if __name__ == "__main__":
    app.run(debug=True, port=5000)
