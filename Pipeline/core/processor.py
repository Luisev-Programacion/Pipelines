import os
import json
import time
import tempfile
import uuid

import pandas as pd

from core.utils import leer_csv_gz
from core.peliculas_id import (
    asignar_id_pelicula,
    cargar_diccionario,
    guardar_diccionario
)


DEBUG_LOG_PATH = r"C:\Users\luisev\.cursor\projects\1777911243382\debug-656760.log"


def _debug_log(hypothesis_id, location, message, data):
    payload = {
        "sessionId": "656760",
        "runId": "excel-debug",
        "hypothesisId": hypothesis_id,
        "id": f"log_{uuid.uuid4().hex}",
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=True) + "\n")

def procesar_archivo(
    path_archivo,
    mapping_func,
    config
):
    """
    Procesa un archivo completo:
    1. Lectura
    2. Transformación (mapping específico del pipeline)
    3. Enriquecimiento (IdPelicula)
    4. Persistencia de diccionario

    Params:
    - path_archivo: ruta del archivo
    - mapping_func: función de transformación del pipeline
    - config: diccionario de configuración del pipeline
    """

    # =============================
    # CONFIG
    # =============================
    input_config = config["input"]
    mapping_config = config["mapping"]
    api_config = config["apis"]["tmdb"]
    output_config = config["output"]
    perf_config = config["performance"]

    columna_pelicula = mapping_config["columna_pelicula"]
    api_key = api_config["api_key"]
    catalogo_path = output_config["catalogo_peliculas"]
    out_xlsx_path = output_config["resultado_excel"]

    sleep_api = perf_config.get("sleep_api", 0.25)
    umbral_similitud = perf_config.get("similitud_umbral", 0.8)

    print(f"Leyendo archivo: {path_archivo}")

    # =============================
    # 1. LECTURA
    # =============================
    encoding = input_config.get("encoding", "utf-8")
    fallback_encoding = input_config.get("fallback_encoding", "latin1")
    path_l = path_archivo.lower()
    if path_l.endswith(".csv.gz"):
        df_raw = leer_csv_gz(path_archivo)
    elif path_l.endswith(".csv"):
        try:
            df_raw = pd.read_csv(path_archivo, dtype=str, encoding=encoding)
        except UnicodeDecodeError:
            print(
                f"Advertencia: no se pudo decodificar {path_archivo} con {encoding}. "
                f"Reintentando con {fallback_encoding}."
            )
            df_raw = pd.read_csv(path_archivo, dtype=str, encoding=fallback_encoding)
    elif path_l.endswith(".xlsx") or path_l.endswith(".xls"):
        df_raw = pd.read_excel(path_archivo, dtype=str)
    else:
        raise ValueError(
            f"Extensión no soportada: {path_archivo!r} "
            f"(configure input.file_pattern o use .csv.gz / .csv / .xlsx)"
        )

    if df_raw.empty:
        raise ValueError("El archivo está vacío")

    print(f"Registros leídos: {len(df_raw)}")
    print(f"Columnas detectadas: {list(df_raw.columns)}")

    # =============================
    # 2. TRANSFORMACIÓN
    # =============================
    df = mapping_func(df_raw)

    if df.empty:
        raise ValueError("El DataFrame transformado está vacío")

    print(f"Registros transformados: {len(df)}")

    # =============================
    # 3. DICCIONARIO
    # =============================
    dic = cargar_diccionario(catalogo_path)

    contador = max(
        [
            int(v.replace("IdMV", ""))
            for v in dic.values()
            if str(v).startswith("IdMV")
        ],
        default=0
    ) + 1

    print(f"Diccionario cargado: {len(dic)} elementos")
    print(f"Contador inicial: {contador}")

    # =============================
    # 4. ENRIQUECIMIENTO (IdPelicula)
    # =============================
    df, dic, contador = asignar_id_pelicula(
        df=df,
        columna_peliculas=columna_pelicula,
        api_key=api_key,
        dic_no_encontrados=dic,
        contador_mv=contador,
        umbral_similitud=umbral_similitud,
        sleep=sleep_api
    )

    print("Enriquecimiento completado (IdPelicula)")

    # =============================
    # 5. GUARDAR DICCIONARIO
    # =============================
    guardar_diccionario(dic, catalogo_path)

    print("Diccionario actualizado")

    # =============================
    # 6. VALIDACIONES BÁSICAS
    # =============================
    if "IdPelicula" not in df.columns:
        raise ValueError("No se generó la columna IdPelicula")

    nulos = df["IdPelicula"].isna().sum()

    if nulos > 0:
        print(f"⚠️ Advertencia: {nulos} registros sin IdPelicula")

    # =============================
    # 7. (OPCIONAL) SQL
    # =============================

    # =============================
    # FIN
    # =============================
    print(f"Archivo procesado OK: {path_archivo}")

    write_excel = output_config.get("write_excel", True)
    if not write_excel:
        print("Omitiendo exportación a Excel por configuración.")
        return df

    os.makedirs(os.path.dirname(out_xlsx_path), exist_ok=True)

    temp_dir = tempfile.gettempdir()
    temp_xlsx_path = os.path.join(
        temp_dir,
        f"tmp_{uuid.uuid4().hex}_{os.path.basename(out_xlsx_path)}",
    )

    # region agent log
    _debug_log(
        "P5",
        "core/processor.py:161",
        "before_to_excel",
        {
            "rows": len(df),
            "out_xlsx_path": out_xlsx_path,
            "temp_xlsx_path": temp_xlsx_path,
        },
    )
    # endregion

    try:
        print(f"Guardando Excel temporal en: {temp_xlsx_path}")
        df.to_excel(temp_xlsx_path, index=False)
        os.replace(temp_xlsx_path, out_xlsx_path)
        output_written = out_xlsx_path
    except PermissionError:
        alternate_name = f"{os.path.splitext(out_xlsx_path)[0]}_{os.path.basename(path_archivo)}.xlsx"
        alternate_path = os.path.join(os.path.dirname(out_xlsx_path), alternate_name)
        df.to_excel(alternate_path, index=False)
        output_written = alternate_path
        print(f"Advertencia: no se pudo escribir en {out_xlsx_path}. Guardado en {alternate_path}")
    finally:
        if os.path.exists(temp_xlsx_path):
            try:
                os.remove(temp_xlsx_path)
            except OSError:
                pass

    print(f"Salida Excel: {output_written}")
    # region agent log
    _debug_log(
        "P6",
        "core/processor.py:172",
        "after_to_excel",
        {"out_xlsx_path": output_written},
    )
    # endregion
    return df