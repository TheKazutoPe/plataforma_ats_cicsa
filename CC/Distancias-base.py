import os
import time
import json
import requests
import pandas as pd
from geopy.geocoders import Nominatim

# ---------- CONFIGURACIÓN ----------
INPUT_FILE = "rutas.xlsx"                 # Archivo de entrada
OUTPUT_FILE = "rutas_con_distancias.xlsx" # Archivo de salida
CACHE_FILE = "cache_geocoding.json"       # Caché persistente en JSON

PAIS_POR_DEFECTO = "Perú"

# Nombres de columnas en tu Excel
COLUMNA_ORIGEN = "origen"
COL_DEST_DEP = "dest_departamento"
COL_DEST_PROV = "dest_provincia"
COL_DEST_DIST = "dest_distrito"

# ORÍGENES QUE SIEMPRE VAN A LIMA
ORIGENES_LIMA = {
    "SAN MIGUEL",
    "LA VICTORIA",
    "INDEPENDENCIA",
    "HUACHIPA",
    "CERCADO DE LIMA"
}

# Geolocalizador
geolocator = Nominatim(user_agent="distancias_excel_app")

# ---------- CARGAR CACHÉ DESDE JSON ----------
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        cache_geocoding = json.load(f)
    print(f"✔ Caché cargado desde {CACHE_FILE} ({len(cache_geocoding)} lugares)")
else:
    cache_geocoding = {}
    print("⚠ No se encontró caché previo. Se iniciará uno nuevo.")


def geocodificar(lugar: str):
    """Devuelve (lat, lon) usando Nominatim + caché JSON."""
    if lugar is None or str(lugar).strip() == "":
        return None, None

    lugar = str(lugar).strip()

    # 1. Revisar caché
    if lugar in cache_geocoding:
        lat, lon = cache_geocoding[lugar]
        return lat, lon

    # 2. Si no está en caché, pedir a Nominatim
    query = lugar  # ya viene armado

    for intento in range(3):
        try:
            time.sleep(1)  # respetar límites Nominatim
            ubicacion = geolocator.geocode(query)
            if ubicacion:
                lat, lon = ubicacion.latitude, ubicacion.longitude
                cache_geocoding[lugar] = (lat, lon)  # guardar en caché
                print(f"  🆕 Geocodificado: {lugar} -> ({lat}, {lon})")
                return lat, lon
        except Exception as e:
            print(f"  Error geocodificando '{lugar}' (intento {intento+1}): {e}")
            time.sleep(2)

    cache_geocoding[lugar] = (None, None)
    return None, None


def calcular_ruta_osrm(lat1, lon1, lat2, lon2):
    """Calcula ruta con OSRM: distancia (km) y duración (min, horas)."""
    url = (
        f"http://router.project-osrm.org/route/v1/driving/"
        f"{lon1},{lat1};{lon2},{lat2}?overview=false"
    )

    resp = requests.get(url)
    data = resp.json()

    if "routes" not in data or not data["routes"]:
        return None, None, None

    distancia_m = data["routes"][0]["distance"]
    duracion_s = data["routes"][0]["duration"]

    distancia_km = round(distancia_m / 1000, 2)
    duracion_min = round(duracion_s / 60, 1)
    duracion_horas = round(duracion_min / 60, 2)

    return distancia_km, duracion_min, duracion_horas


def armar_destino(fila) -> str:
    """Arma el texto de destino usando dep/prov/dist."""
    dep = str(fila[COL_DEST_DEP]).strip() if pd.notna(fila[COL_DEST_DEP]) else ""
    prov = str(fila[COL_DEST_PROV]).strip() if pd.notna(fila[COL_DEST_PROV]) else ""
    dist = str(fila[COL_DEST_DIST]).strip() if pd.notna(fila[COL_DEST_DIST]) else ""

    partes = [dist, prov, dep, PAIS_POR_DEFECTO]
    partes = [p for p in partes if p != ""]
    if not partes:
        return ""
    return ", ".join(partes)


def procesar_excel():
    df = pd.read_excel(INPUT_FILE)
    total_filas = len(df)
    print(f"\nSe encontraron {total_filas} filas para procesar.\n")

    distancias = []
    dur_minutos = []
    dur_horas = []

    for idx, fila in df.iterrows():
        # -------- ORIGEN --------
        origen_crudo = str(fila[COLUMNA_ORIGEN]).strip() if pd.notna(fila[COLUMNA_ORIGEN]) else ""
        origen_upper = origen_crudo.upper()

        if origen_upper in ORIGENES_LIMA:
            # Redirigimos estos casos a Lima Metropolitana
            origen_query = f"{origen_crudo.title()}, Lima Metropolitana, Lima, {PAIS_POR_DEFECTO}"
        else:
            # Caso general: solo añadimos país
            origen_query = f"{origen_crudo}, {PAIS_POR_DEFECTO}" if origen_crudo != "" else ""

        # -------- DESTINO --------
        destino_query = armar_destino(fila)

        # LOG DE PROGRESO
        progreso = ((idx + 1) / total_filas) * 100
        print(f"[{idx + 1}/{total_filas}] {progreso:5.1f}%")
        print(f"   ORIGEN : {origen_query}")
        print(f"   DESTINO: {destino_query}")

        lat1, lon1 = geocodificar(origen_query)
        lat2, lon2 = geocodificar(destino_query)

        if None in (lat1, lon1, lat2, lon2):
            print("  ❌ No se pudieron obtener coordenadas.")
            distancias.append(None)
            dur_minutos.append(None)
            dur_horas.append(None)
            continue

        distancia_km, dur_min, dur_h = calcular_ruta_osrm(lat1, lon1, lat2, lon2)

        if distancia_km is None:
            print("  ❌ No se pudo calcular la ruta.")
            distancias.append(None)
            dur_minutos.append(None)
            dur_horas.append(None)
            continue

        print(f"  ✅ Distancia: {distancia_km} km | Tiempo: {dur_h} h (~{dur_min} min)")

        distancias.append(distancia_km)
        dur_minutos.append(dur_min)
        dur_horas.append(dur_h)

    # Agregar columnas nuevas
    df["distancia_km"] = distancias
    df["duracion_min"] = dur_minutos
    df["duracion_horas"] = dur_horas

    # Guardar resultado Excel
    df.to_excel(OUTPUT_FILE, index=False)
    print(f"\n✔ PROCESO COMPLETADO: {total_filas} filas procesadas.")
    print(f"✔ Archivo guardado como: {OUTPUT_FILE}")

    # Guardar caché en JSON
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache_geocoding, f, ensure_ascii=False, indent=2)
    print(f"✔ Caché actualizado en: {CACHE_FILE} (total {len(cache_geocoding)} lugares)")


if __name__ == "__main__":
    procesar_excel()
