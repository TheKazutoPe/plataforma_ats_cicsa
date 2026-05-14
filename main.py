from flask import Flask, render_template, request, redirect, session, url_for
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime
import base64
import os
import uuid
import unicodedata

from generate_pdf import generar_pdf

# =========================
# CONFIGURACION BASE
# =========================
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "supersecret")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Falta configurar SUPABASE_URL o SUPABASE_ANON_KEY en el .env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Bucket donde se guardaran los PDFs
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

    # Tecnicos activos
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

    mensaje = None

    if request.method == "POST":
        os.makedirs("temp", exist_ok=True)
        data = {}

        # UUID solo para el nombre base del archivo
        req_uuid = uuid.uuid4().hex[:8]
        pdf_base_name = f"ATS_{req_uuid}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        data["pdf_filename"] = pdf_base_name  # generate_pdf construirá la ruta temp/ internamente

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

        # ===== Tecnicas de control =====
        controles = request.form.getlist("controles[]")
        control_otro = (request.form.get("controles_otro") or "").strip()
        if control_otro:
            controles.append(control_otro)
        data["controles"] = controles

        # ===== Tecnicos / Participantes =====
        tecnicos_post = []
        for i in range(1, 11):
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
                "obs": (request.form.get(f"obs{i}") or "").strip(),
            }

            # Firma desde canvas
            firma_b64 = request.form.get(f"firma{i}")
            fila["firma_path"] = None
            if firma_b64 and "base64" in firma_b64:
                try:
                    raw = firma_b64.split(",")[-1]
                    firma_path = os.path.join(
                        "temp",
                        f"firma_tec{i}_{req_uuid}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                    )
                    with open(firma_path, "wb") as out:
                        out.write(base64.b64decode(raw))
                    fila["firma_path"] = firma_path
                except Exception as e:
                    print(f"Error guardando firma tecnico {i}:", e)

            # Foto individual tecnico
            foto_file = request.files.get(f"foto_tec{i}")
            fila["foto_path"] = None
            if foto_file and foto_file.filename:
                try:
                    foto_path = os.path.join(
                        "temp",
                        f"foto_tec{i}_{req_uuid}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg",
                    )
                    foto_file.save(foto_path)
                    fila["foto_path"] = foto_path
                except Exception as e:
                    print(f"Error guardando foto tecnico {i}:", e)

            tecnicos_post.append(fila)

        data["tecnicos"] = tecnicos_post

        # ===== Encargado (firma en PDF) =====
        # El encargado debe ser uno de los tecnicos del ATS. Por defecto, Tecnico 1.
        enc_sel = request.form.get("encargado_tecnico", "1")
        try:
            enc_idx = int(enc_sel)
        except Exception:
            enc_idx = 1
        if enc_idx < 1:
            enc_idx = 1
        if enc_idx > len(tecnicos_post) and len(tecnicos_post) > 0:
            enc_idx = 1

        data["encargado_idx"] = enc_idx
        if tecnicos_post:
            enc = tecnicos_post[enc_idx - 1]
            data["encargado_nombre"] = enc.get("nombre", "")
            data["encargado_dni"] = enc.get("dni", "")
            data["encargado_cargo"] = enc.get("cargo", "")
            data["encargado_firma_path"] = enc.get("firma_path")
        else:
            data["encargado_nombre"] = ""
            data["encargado_dni"] = ""
            data["encargado_cargo"] = ""
            data["encargado_firma_path"] = None

        # ===== Foto general opcional =====
        foto_general = request.files.get("foto_epp")
        data["foto_path"] = None
        if foto_general and foto_general.filename:
            try:
                foto_path = os.path.join(
                    "temp",
                    f"foto_general_{req_uuid}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg",
                )
                foto_general.save(foto_path)
                data["foto_path"] = foto_path
            except Exception as e:
                print("Error guardando foto general:", e)

        # ===== Generar PDF =====
        pdf_path = generar_pdf(data)
        pdf_name = os.path.basename(pdf_path)  # solo el nombre, sin ruta temp/

        # ===== Subir PDF a Supabase Storage =====
        pdf_storage_path = None
        pdf_public_url = None
        try:
            if os.path.isfile(pdf_path):
                with open(pdf_path, "rb") as f:
                    file_bytes = f.read()

                fecha_reg = data.get("fecha_dia") or datetime.now().strftime("%Y-%m-%d")
                brigada_reg = (data.get("brigada") or "SIN_BRIGADA").replace(" ", "_")

                # Limpiar caracteres especiales (ej: Ñ, tildes) para la ruta de storage
                brigada_safe = unicodedata.normalize('NFKD', brigada_reg).encode('ASCII', 'ignore').decode('utf-8')

                # Ruta dentro del bucket
                pdf_storage_path = f"ats/{fecha_reg}/{brigada_safe}/{pdf_name}"

                # Subir al bucket configurado con content-type correcto
                supabase.storage.from_(PDF_BUCKET).upload(
                    pdf_storage_path,
                    file_bytes,
                    file_options={"content-type": "application/pdf"},
                )

                # Construir URL publica (el bucket debe ser PUBLIC)
                base_url = SUPABASE_URL.rstrip("/")
                pdf_public_url = (
                    f"{base_url}/storage/v1/object/public/{PDF_BUCKET}/{pdf_storage_path}"
                )
        except Exception as e:
            print("Error subiendo PDF a Supabase Storage:", e)

        # ===== Validar subida y registrar en BD =====
        if not pdf_public_url:
            mensaje = "❌ Error al subir el PDF a la nube. Por favor, reintente."
        else:
            try:
                fecha_reg = data.get("fecha_dia") or datetime.now().strftime("%Y-%m-%d")
                brigada_reg = data.get("brigada") or "SIN BRIGADA"
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

                supabase.table("ats_registros_diarios").upsert(
                    registro,
                    on_conflict="fecha,brigada,contrata",
                ).execute()
                mensaje = "✅ Reporte ATS generado y registrado correctamente."
            except Exception as e:
                print("Error registrando ATS diario en Supabase:", e)
                mensaje = "⚠️ El PDF se generó, pero hubo un error al registrar en la base de datos."

        # ===== Limpieza de Archivos =====
        try:
            if data.get("foto_path") and os.path.exists(data.get("foto_path")):
                os.remove(data["foto_path"])
            for t in tecnicos_post:
                f = t.get("firma_path")
                if f and os.path.exists(f):
                    os.remove(f)
                ft = t.get("foto_path")
                if ft and os.path.exists(ft):
                    os.remove(ft)
            # Limpiar la copia temporal de firma del encargado (_enc.png)
            enc_copy = data.get("_enc_sig_copy")
            if enc_copy and os.path.exists(enc_copy):
                os.remove(enc_copy)
            if pdf_path and os.path.exists(pdf_path):
                os.remove(pdf_path)
        except Exception as cleanup_err:
            print("Error en limpieza de archivos:", cleanup_err)

        return render_template(
            "formulario.html",
            datos=user,
            tecnicos=tecnicos,
            charlas=charlas,
            mensaje=mensaje,
            pdf_url=pdf_public_url,
        )

    # GET
    return render_template(
        "formulario.html",
        datos=user,
        tecnicos=tecnicos,
        charlas=charlas,
        mensaje=None,
        pdf_url=None,
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
