# coordenadas_log.py
import re
import json
import time
import logging
import requests
import pandas as pd
from pathlib import Path

# Intentar usar tqdm (barra de progreso); si no está instalado, usar un dummy.
try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable=None, **kwargs):
        return iterable if iterable is not None else []


# ========= CONFIG =========
INPUT_FILE = r"Coordenadas averias- preventivo pext 2025.xlsx"  # ⚠️ Cambia si aplica
SHEET_NAME = "Sheet1"
COL_LAT = "LATITUD"        # ⚠️ Nombre exacto de la columna de latitud
COL_LON = "LONGITUD"       # ⚠️ Nombre exacto de la columna de longitud
OUTPUT_SUFFIX = "_con_distrito"
REQUEST_PAUSE_SEC = 1.2      # respeta Nominatim (>=1s)
TIMEOUT_SEC = 20
USER_AGENT = "geo-distritos-peru/1.0 (contacto: tu_correo@dominio.com)"  # ⚠️ pon tu correo

# Progreso y control
LOG_EVERY_N = 100            # mensaje cada N keys únicas
CHECKPOINT_EVERY_N = 1000
MAX_REQUESTS_PER_RUN = 50000
CACHE_FILE = "cache_osm_reverse.json"


# ========= LOGGING =========
def setup_logger(log_path: Path):
    logger = logging.getLogger("geo_distritos")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    return logger


# ========= HELPERS =========
def clean_coord(value):
    """Limpia coordenadas: admite '°', coma decimal, espacios, etc."""
    if pd.isna(value) or str(value).strip() == "":
        return None
    s = str(value).strip()
    s = s.replace("°", "").replace("º", "").replace(",", ".")
    s = re.sub(r"[^0-9.\-+]", "", s)
    try:
        return float(s)
    except ValueError:
        return None


def reverse_geocode_osm(lat, lon, user_agent=USER_AGENT, timeout=TIMEOUT_SEC, logger=None):
    """Llama a Nominatim y devuelve address + display_name."""
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {"format": "jsonv2", "lat": str(lat), "lon": str(lon), "zoom": "14", "addressdetails": 1}
    headers = {"User-Agent": user_agent}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=timeout)
        if r.status_code == 200:
            data = r.json()
            return {"address": data.get("address", {}), "display_name": data.get("display_name", "")}
        else:
            if logger:
                logger.warning(f"HTTP {r.status_code} en {lat},{lon}")
    except Exception as e:
        if logger:
            logger.error(f"Error de red en {lat},{lon}: {e}")
    return {"address": {}, "display_name": ""}


def first_nonempty(address, keys):
    """Devuelve el primer campo no vacío de 'address' según la lista de claves."""
    for k in keys:
        v = address.get(k)
        if v and str(v).strip():
            return str(v).strip(), k
    return "", ""


def load_cache():
    p = Path(CACHE_FILE)
    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_cache(cache: dict):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)


def is_empty(val):
    """True si es NaN o string vacío/espacios."""
    if val is None:
        return True
    if isinstance(val, str) and val.strip() == "":
        return True
    return pd.isna(val)


# ========= MAIN =========
def main():
    input_path = Path(INPUT_FILE)
    output_path = input_path.with_name(input_path.stem + OUTPUT_SUFFIX + input_path.suffix)
    log_path = input_path.with_name(input_path.stem + OUTPUT_SUFFIX + ".log")

    logger = setup_logger(log_path)
    logger.info(f"Iniciando: {INPUT_FILE} -> {output_path.name}")

    df = pd.read_excel(INPUT_FILE, sheet_name=SHEET_NAME)

    # Validar columnas
    for col in [COL_LAT, COL_LON]:
        if col not in df.columns:
            logger.error(f"Falta la columna '{col}' en '{SHEET_NAME}'.")
            raise ValueError(f"Falta la columna '{col}'.")

    total = len(df)
    logger.info(f"Filas totales: {total}")

    # Limpia coordenadas
    df["_lat"] = df[COL_LAT].apply(clean_coord)
    df["_lon"] = df[COL_LON].apply(clean_coord)

    # Genera clave única (lat/lon redondeadas a 5 decimales; descarta inválidas)
    def make_key(t):
        lat, lon = t
        if lat is None or lon is None:
            return None
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return None
        return (round(lat, 5), round(lon, 5))

    df["key"] = list(map(make_key, zip(df["_lat"], df["_lon"])))
    unique_keys = pd.Series(df["key"].unique())
    unique_keys = unique_keys[unique_keys.notna()].tolist()
    logger.info(f"Coordenadas únicas válidas: {len(unique_keys)}")

    # Carga caché persistente
    cache = load_cache()
    logger.info(f"Entradas en caché al inicio: {len(cache)}")

    # Geocodifica SOLO keys nuevas, con barra de progreso
    new_requests = 0
    for i, key in enumerate(tqdm(unique_keys, desc="Geocodificando keys únicas"), start=1):
        skey = str(key)
        if skey not in cache:
            if new_requests >= MAX_REQUESTS_PER_RUN:
                logger.info("Alcanzado MAX_REQUESTS_PER_RUN. Deteniendo esta corrida.")
                break
            lat, lon = key
            time.sleep(REQUEST_PAUSE_SEC)
            cache[skey] = reverse_geocode_osm(lat, lon, logger=logger)
            new_requests += 1

            if i % LOG_EVERY_N == 0:
                logger.info(
                    f"Procesadas {i}/{len(unique_keys)} keys únicas; "
                    f"nuevas requests en esta corrida: {new_requests}"
                )

            if new_requests % 200 == 0:
                save_cache(cache)
                logger.info("Caché guardada (checkpoint).")

    # Guarda caché final
    save_cache(cache)
    logger.info(
        f"Caché persistida. Total entradas: {len(cache)} | "
        f"Nuevas requests en esta corrida: {new_requests}"
    )

    # Construye DF con resultados únicos (solo lo que ya está en cache)
    rows = []
    for key in unique_keys:
        data = cache.get(str(key), {"address": {}, "display_name": ""})
        addr = data.get("address", {})

        # PAÍS
        pais, _ = first_nonempty(addr, ["country"])

        # DEPARTAMENTO (Perú: suele ser 'state')
        departamento, fuente_dep = first_nonempty(
            addr,
            [
                "state",
                "region",
            ],
        )

        # PROVINCIA
        provincia, fuente_prov = first_nonempty(
            addr,
            [
                "county",          # común como provincia
                "state_district",  # a veces provincia
                "province",
                "region",
                "municipality",
            ],
        )

        # DISTRITO: primero estricto, luego fallback
        distrito = ""
        fuente_dist = ""

        # 1) estricto
        distrito, fuente_dist = first_nonempty(
            addr,
            [
                "city_district",
                "district",
            ],
        )

        # 2) fallback si sigue vacío
        if distrito == "":
            distrito, fuente_dist = first_nonempty(
                addr,
                [
                    "city",
                    "town",
                    "village",
                    "municipality",
                    "suburb",
                    "neighbourhood",
                    "borough",
                ],
            )

        rows.append(
            {
                "key": key,
                "DISTRITO": distrito,
                "PROVINCIA": provincia,
                "DEPARTAMENTO": departamento,
                "PAIS": pais,
                "FUENTE_DISTRITO": fuente_dist,
                "FUENTE_PROVINCIA": fuente_prov,
                "FUENTE_DEPARTAMENTO": fuente_dep,
                "DISPLAY_NAME_API": data.get("display_name", ""),
            }
        )

    geo_unique = pd.DataFrame(rows)

    # Une resultados al DataFrame original
    df = df.merge(geo_unique, on="key", how="left")

    # GEO_STATUS por fila: cómo quedó cada registro
    def status_row(row):
        if row["key"] is None:
            if is_empty(row["_lat"]) and is_empty(row["_lon"]):
                return "SIN_COORDENADAS"
            return "COORD_INVALIDA"
        if is_empty(row["DISTRITO"]) and is_empty(row["PROVINCIA"]) and is_empty(row["DEPARTAMENTO"]):
            return "API_SIN_RESULTADOS"
        return "OK"

    df["GEO_STATUS"] = df.apply(status_row, axis=1)

    # Limpia columnas auxiliares
    df.drop(columns=["_lat", "_lon", "key"], inplace=True)

    # Guardar resultado final
    df.to_excel(output_path, sheet_name=SHEET_NAME, index=False)
    logger.info(f"Archivo final: {output_path.resolve()}")
    logger.info("Proceso completado ✅")


if __name__ == "__main__":
    main()
