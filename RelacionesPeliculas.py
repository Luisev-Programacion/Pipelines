import requests
import pandas as pd
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv
import os
import time
import re
from difflib import SequenceMatcher

# =============================
# CONFIG
# =============================
load_dotenv()
API_KEY = os.getenv("APIKEYTMDB")
BASE_URL = "https://api.themoviedb.org/3"

SESSION = requests.Session()
retry_cfg = Retry(
    total=3,
    connect=3,
    read=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"],
)
SESSION.mount("https://", HTTPAdapter(max_retries=retry_cfg))


# =============================
# NORMALIZACION
# =============================
def normalizar(texto):
    texto = str(texto).upper().strip()
    texto = re.sub(r'\b(THE|LA|EL|LOS|LAS|UN|UNA)\b', '', texto)
    texto = re.sub(r'[^\w\s]', '', texto)
    texto = re.sub(r'\s+', ' ', texto)
    return texto.strip()


# =============================
# SIMILITUD
# =============================
def similitud(a, b):
    return SequenceMatcher(None, a, b).ratio()


def buscar_similar_en_diccionario(nombre, diccionario, umbral=0.8):
    mejor_match = None
    mejor_score = 0

    for clave_dic in diccionario.keys():
        score = similitud(nombre, clave_dic)

        if score > mejor_score:
            mejor_score = score
            mejor_match = clave_dic

    if mejor_score >= umbral:
        return diccionario[mejor_match], mejor_score

    return None, mejor_score


# =============================
# DICCIONARIO PERSISTENTE
# =============================
def cargar_diccionario(path):
    if os.path.exists(path):
        df = pd.read_excel(path)
        return dict(zip(df["NombreNormalizado"], df["IdPelicula"]))
    return {}


def guardar_diccionario(diccionario, path):
    df = pd.DataFrame(
        [(k, v) for k, v in diccionario.items()],
        columns=["NombreNormalizado", "IdPelicula"]
    )
    df.to_excel(path, index=False)


# =============================
# LECTURA ARCHIVOS
# =============================
def leer_archivo(path_archivo):
    extension = os.path.splitext(path_archivo)[1].lower()

    if extension == ".csv":
        try:
            return pd.read_csv(path_archivo, encoding="utf-8")
        except:
            return pd.read_csv(path_archivo, encoding="latin1")

    elif extension in [".xlsx", ".xls"]:
        return pd.read_excel(path_archivo)

    else:
        raise ValueError(f"Formato no soportado: {extension}")


# =============================
# TMDB
# =============================
def buscar_pelicula(nombre, idioma="es-MX"):
    url = f"{BASE_URL}/search/movie"

    params = {
        "api_key": API_KEY,
        "query": nombre,
        "language": idioma
    }

    try:
        response = SESSION.get(url, params=params, timeout=(5, 20))
        response.raise_for_status()
    except requests.exceptions.RequestException:
        return {"input": nombre, "error": "Error API"}

    data = response.json()

    if data["results"]:
        peli = data["results"][0]
        return {
            "input": nombre,
            "tmdb_id": peli["id"],
            "titulo_es": peli.get("title"),
            "titulo_original": peli.get("original_title"),
            "fecha": peli.get("release_date"),
        }
    else:
        return {"input": nombre, "error": "No encontrado"}


# =============================
# PROCESAMIENTO PRINCIPAL
# =============================
def procesar_archivo(
    path_archivo,
    columna_peliculas,
    output_path,
    dic_no_encontrados,
    contador_mv
):

    df = leer_archivo(path_archivo)

    if columna_peliculas not in df.columns:
        raise ValueError(f"La columna '{columna_peliculas}' no existe")

    peliculas_unicas = df[columna_peliculas].dropna().astype(str).unique()

    print(f"Películas únicas: {len(peliculas_unicas)}")

    cache = {}
    resultados = []
    umbral_similitud = 0.8
    for nombre in peliculas_unicas:

        if not nombre.strip():
            continue

        clave = normalizar(nombre)

        # =============================
        # 1. PRIORIDAD: DICCIONARIO EXACTO
        # =============================
        if clave in dic_no_encontrados:
            resultados.append({
                "input": nombre,
                "IdPelicula": dic_no_encontrados[clave],
                "tmdb_id": None
            })
            continue

        # =============================
        # 2. SIMILITUD EN DICCIONARIO
        # =============================
        id_similar, score = buscar_similar_en_diccionario(
            clave, dic_no_encontrados, umbral_similitud
        )

        if id_similar:
            resultados.append({
                "input": nombre,
                "IdPelicula": id_similar,
                "tmdb_id": None
            })
            continue

        # =============================
        # 3. CACHE (EVITA DUPLICADOS EN MISMO ARCHIVO)
        # =============================
        if clave in cache:
            resultado = cache[clave]
        else:
            resultado = buscar_pelicula(nombre, api_key, session)
            cache[clave] = resultado
            time.sleep(sleep)

        # =============================
        # 4. RESULTADO TMDB O NUEVO ID
        # =============================
        if "error" in resultado and resultado["error"] == "No encontrado":

            nuevo_id = f"IdMV{contador_mv}"
            dic_no_encontrados[clave] = nuevo_id

            resultados.append({
                "input": nombre,
                "IdPelicula": nuevo_id,
                "tmdb_id": None
            })

            contador_mv += 1

        else:
            resultados.append({
                "input": nombre,
                "IdPelicula": resultado.get("tmdb_id"),
                "tmdb_id": resultado.get("tmdb_id")
            })
            
    df_resultados = pd.DataFrame(resultados)

    # =============================
    # MERGE
    # =============================
    df_final = df.merge(
        df_resultados,
        left_on=columna_peliculas,
        right_on="input",
        how="left"
    )

    if "input" in df_final.columns:
        df_final.drop(columns=["input"], inplace=True)

    df_final.drop(columns=["Encontrado", "score_similitud", "error", "tmdb_id"], inplace=True, errors="ignore")

    df_final["FuenteId"] = df_final["IdPelicula"].apply(
        lambda x: "TMDB" if str(x).isdigit() else "INTERNO"
    )

    # =============================
    # EXPORT
    # =============================
    if output_path.endswith(".csv"):
        df_final.to_csv(output_path, index=False)
    else:
        df_final.to_excel(output_path, index=False)

    print(f"Archivo generado: {output_path}")

    return df_final, dic_no_encontrados, contador_mv


# =============================
# EJECUCION MULTI ARCHIVO
# =============================
if __name__ == "__main__":

    archivos = [
         {
            "path": r"C:\Users\luisev\Downloads\20260428_MPA_MexicoFlash.csv\20260428_MPA_MexicoFlash.csv",
            "columna": "Film Name"
        },
        {
            "path": r"C:\Users\luisev\Downloads\20260428_MPA_MexicoFlash.csv\Performance Monitor_2026-04-29T14_29_09.xlsx",
            "columna": "Title Versions"
        }
    ]

    path_diccionario = r"C:\Users\luisev\Downloads\catalogo_no_encontrados.xlsx"

    dic_no_encontrados = cargar_diccionario(path_diccionario)

    contador_mv = (
        max([int(v.replace("IdMV", "")) for v in dic_no_encontrados.values()], default=0) + 1
    )

    for i, archivo in enumerate(archivos, start=1):

        output_path = rf"C:\Users\luisev\Downloads\20260428_MPA_MexicoFlash.csv\output_{i}.xlsx"

        print(f"\nProcesando archivo {i}")

        _, dic_no_encontrados, contador_mv = procesar_archivo(
            path_archivo=archivo["path"],
            columna_peliculas=archivo["columna"],
            output_path=output_path,
            dic_no_encontrados=dic_no_encontrados,
            contador_mv=contador_mv
        )

    # 🔥 GUARDAR DICCIONARIO ACTUALIZADO
    guardar_diccionario(dic_no_encontrados, path_diccionario)

    print("\nDiccionario actualizado correctamente")