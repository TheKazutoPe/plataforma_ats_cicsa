from flask import Flask, render_template, request, redirect, session, url_for
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime
import base64
import os

from generate_pdf import generar_pdf
from email_sender import enviar_correo

# =========================
# CONFIGURACIÓN BASE
# =========================
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "supersecret")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Falta configurar SUPABASE_URL o SUPABASE_ANON_KEY en el .env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Bucket donde se guardarán los PDFs (crearlo en Supabase)
PDF_BUCKET = os.getenv("SUPABASE_PDF_BUCKET", "ats_pdfs")

os.makedirs("temp", exist_ok=True)


def get_user():
    return session.get("usuario")


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
            error = "Ingrese usuario y clave."
            return render_template("login.html", error=error)

        try:
            resp = (
                supabase.table("usuarios_brigadas")
                .select("id,usuario,nombre,cargo,brigada,zona,contrata,dni,clave,activo")
                .eq("usuario", usuario)
                .eq("clave", clave)
                .eq("activo", True)
                .single()
                .execute()
            )
            data = resp.data
        except Exception:
            data = None

        if not data:
            error = "Usuario o clave incorrectos."
        else:
            session["usuario"] = {
                "id": data.get("id"),
                "usuario": data.get("usuario"),
                "nombre": data.get("nombre"),
                "cargo": data.get("cargo"),
                "brigada": data.get("brigada"),
                "zona": data.get("zona"),
                "contrata": data.get("contrata"),
                "dni": data.get("dni"),
            }
            return redirect(url_for("formulario"))

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

    # Charlas programadas
    try:
        charlas = (
            supabase.table("charlas_programadas")
            .select("item,tema,expositor")
            .order("item")
            .execute()
        ).data or []
    except Exception:
        charlas = []

    if request.method == "POST":
        os.makedirs("temp", exist_ok=True)
        data = {}

        # ===== Datos generales =====
        data["fecha_dia"] = request.form.get("fecha_dia") or datetime.now().strftime(
            "%Y-%m-%d"
        )
        data["hora_inicio"] = request.form.get("hora_inicio", "")
        data["hora_fin"] = request.form.get("hora_fin", "")

        trabajo = request.form.get("trabajo") or ""
        trabajo_otro = request.form.get("trabajo_otro") or ""
        if trabajo == "OTRO" and trabajo_otro.strip():
            data["actividad"] = trabajo_otro.strip()
        else:
            data["actividad"] = trabajo

        data["lugar_trabajo"] = request.form.get("lugar_trabajo", "")
        data["recomendaciones"] = request.form.get("recomendaciones", "")
        data["supervisor"] = request.form.get("supervisor", "SIN SUPERVISOR")

        # Usuario que registra
        data["usuario_registro"] = user.get("usuario")
        data["brigada_usuario"] = user.get("brigada")
        data["zona_usuario"] = user.get("zona")
        data["contrata"] = user.get("contrata", "")
        data["area"] = "MRD F.O. LIMA METROP."
        data["brigada"] = user.get("brigada", "SIN BRIGADA")

        # ===== Charla programada =====
        charla_item = request.form.get("charla")
        expositor_manual = request.form.get("expositor_charla", "")
        charla_sel = next(
            (c for c in charlas if str(c.get("item")) == str(charla_item)),
            None,
        )
        if charla_sel:
            data["tema_charla"] = charla_sel.get("tema", "")
            data["expositor_charla"] = (
                charla_sel.get("expositor", "") or expositor_manual
            )
        else:
            data["tema_charla"] = charla_item or ""
            data["expositor_charla"] = expositor_manual

        # ===== Riesgos =====
        riesgos = request.form.getlist("riesgos[]")
        riesgo_otro = (request.form.get("riesgos_otro") or "").strip()
        if riesgo_otro:
            riesgos.append(riesgo_otro)
        data["riesgos"] = riesgos

        # ===== Técnicos (1..3) con firma y foto individual =====
        tecnicos_post = []

        for i in (1, 2, 3):
            key = request.form.get(f"tec{i}")
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
                    with open(firma_path, "wb") as out:
                        out.write(base64.b64decode(raw))
                    fila["firma_path"] = firma_path
                except Exception as e:
                    print(f"Error guardando firma técnico {i}:", e)

            # Foto individual técnico
            foto_file = request.files.get(f"foto_tec{i}")
            fila["foto_path"] = None
            if foto_file and foto_file.filename:
                try:
                    foto_path = os.path.join(
                        "temp",
                        f"foto_tec{i}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg",
                    )
                    foto_file.save(foto_path)
                    fila["foto_path"] = foto_path
                except Exception as e:
                    print(f"Error guardando foto técnico {i}:", e)

            tecnicos_post.append(fila)

        data["tecnicos"] = tecnicos_post

        # ===== Foto general opcional =====
        foto_general = request.files.get("foto_epp")
        data["foto_path"] = None
        if foto_general and foto_general.filename:
            try:
                foto_path = os.path.join(
                    "temp",
                    f"foto_general_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg",
                )
                foto_general.save(foto_path)
                data["foto_path"] = foto_path
            except Exception as e:
                print("Error guardando foto general:", e)

        # ===== Generar PDF =====
        pdf_path = generar_pdf(data)
        pdf_name = os.path.basename(pdf_path)

        # ===== Enviar correo con PDF =====
        try:
            supervisor = data.get("supervisor", "SIN SUPERVISOR")
            fecha_actual = datetime.now().strftime("%Y-%m-%d")
            brigada_usuario = (user.get("brigada") or "SIN BRIGADA").upper()
            subject = f"Reporte ATS – {supervisor} – {brigada_usuario} – {fecha_actual}"
            enviar_correo(pdf_path, supervisor, subject)
        except Exception as e:
            print("⚠️ Error al enviar correo:", e)

        # ===== Subir PDF a Supabase Storage =====
        pdf_storage_path = None
        pdf_public_url = None
        try:
            if os.path.isfile(pdf_path):
                with open(pdf_path, "rb") as f:
                    file_bytes = f.read()

                # Ruta organizada por fecha y brigada
                fecha_reg = data.get("fecha_dia") or datetime.now().strftime("%Y-%m-%d")
                brigada_reg = (data.get("brigada") or "SIN_BRIGADA").replace(" ", "_")
                pdf_storage_path = f"ats/{fecha_reg}/{brigada_reg}/{pdf_name}"

                # upload (si existe el archivo con el mismo nombre, se recomienda configurar upsert en el bucket)
                supabase.storage.from_(PDF_BUCKET).upload(pdf_storage_path, file_bytes)

                try:
                    pdf_public_url = supabase.storage.from_(PDF_BUCKET).get_public_url(
                        pdf_storage_path
                    )
                except Exception:
                    pdf_public_url = None
            else:
                print("⚠️ PDF no encontrado para subir a Supabase Storage:", pdf_path)
        except Exception as e:
            print("⚠️ Error al subir PDF a Supabase Storage:", e)

        # ===== Registrar cumplimiento diario en ats_registros_diarios =====
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
                # Si luego agregas columnas para el PDF, aquí las envías:
                # "pdf_path": pdf_storage_path,
                # "pdf_url": pdf_public_url,
            }

            supabase.table("ats_registros_diarios").upsert(
                registro,
                on_conflict="fecha,brigada,contrata",
            ).execute()
        except Exception as e:
            print("⚠️ Error registrando ATS diario en Supabase:", e)

        # ===== Responder al usuario en la plataforma =====
        mensaje = "✅ Reporte ATS generado, enviado por correo y registrado correctamente."
        return render_template(
            "formulario.html",
            datos=user,
            tecnicos=tecnicos,
            charlas=charlas,
            mensaje=mensaje,
        )

    # GET
    return render_template("formulario.html", datos=user, tecnicos=tecnicos, charlas=charlas)


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
