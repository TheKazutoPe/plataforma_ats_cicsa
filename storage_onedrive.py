import os
import requests
from datetime import datetime


def subir_a_onedrive(filepath, supervisor, fecha):
    """
    Sube el archivo generado (PDF) al OneDrive corporativo,
    dentro de la carpeta del supervisor y la fecha del reporte.
    """
    upload_link = os.getenv("ONEDRIVE_UPLOAD_LINK")
    if not upload_link:
        print("⚠️ No se encontró la variable ONEDRIVE_UPLOAD_LINK en el .env")
        return

    # Normalizamos los nombres
    supervisor_folder = supervisor.replace(" ", "_").upper()
    fecha_folder = fecha
    filename = os.path.basename(filepath)

    # Construimos una subcarpeta virtual
    upload_url = f"{upload_link}/{supervisor_folder}/{fecha_folder}/{filename}"

    print(f"📤 Subiendo archivo: {filename} → {supervisor_folder}/{fecha_folder}/")

    try:
        with open(filepath, "rb") as f:
            response = requests.put(upload_url, data=f)

        if response.status_code in [200, 201, 204]:
            print(f"✅ Archivo subido correctamente: {response.status_code}")
        else:
            print(f"❌ Error al subir: {response.status_code} → {response.text}")

    except Exception as e:
        print(f"⚠️ Error al conectar con OneDrive: {e}")
