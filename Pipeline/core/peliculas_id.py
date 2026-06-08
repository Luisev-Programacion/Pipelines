import requests
import pandas as pd
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
import re
from difflib import SequenceMatcher

# =============================
# CONFIG SESSION
# =============================
def crear_sesion():
    session = requests.Session()
    retry_cfg = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    session.mount("https://", HTTPAdapter(max_retries=retry_cfg))
    return session


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
# TMDB
# =============================
def buscar_pelicula(nombre, api_key, session, idioma="es-MX"):
    url = "https://api.themoviedb.org/3/search/movie"

    params = {
        "api_key": api_key,
        "query": nombre,
        "language": idioma
    }

    try:
        response = session.get(url, params=params, timeout=(5, 20))
        response.raise_for_status()
    except requests.exceptions.RequestException:
        return {"input": nombre, "error": "Error API"}

    data = response.json()

    if data.get("results"):
        peli = data["results"][0]
        return {
            "input": nombre,
            "tmdb_id": peli.get("id"),
            "titulo_es": peli.get("title"),
            "titulo_original": peli.get("original_title"),
            "fecha": peli.get("release_date"),
        }
    else:
        return {"input": nombre, "error": "No encontrado"}


# =============================
# DICCIONARIO
# =============================
def cargar_diccionario(path):
    try:
        df = pd.read_excel(path)
        return dict(zip(df["NombreNormalizado"], df["IdPelicula"]))
    except:
        return {}


def guardar_diccionario(diccionario, path):
    df = pd.DataFrame(
        [(k, v) for k, v in diccionario.items()],
        columns=["NombreNormalizado", "IdPelicula"]
    )
    df.to_excel(path, index=False)


# =============================
# FUNCION PRINCIPAL (LIBRERIA)
# =============================
def asignar_id_pelicula(
    df,
    columna_peliculas,
    api_key,
    dic_no_encontrados=None,
    contador_mv=1,
    umbral_similitud=0.8,
    sleep=0.25
):
    """
    Enriquece un DataFrame agregando la columna IdPelicula

    Params:
    - df: DataFrame de entrada
    - columna_peliculas: nombre de columna con títulos
    - api_key: TMDB API key
    - dic_no_encontrados: diccionario persistente
    - contador_mv: contador para IDs internos
    """

    if columna_peliculas not in df.columns:
        raise ValueError(f"La columna '{columna_peliculas}' no existe")

    if dic_no_encontrados is None:
        dic_no_encontrados = {}

    session = crear_sesion()

    peliculas_unicas = df[columna_peliculas].dropna().astype(str).unique()

    cache = {}
    resultados = []

    for nombre in peliculas_unicas:

        if not nombre.strip():
            continue

        clave = normalizar(nombre)

        if clave in cache:
            resultado = cache[clave]
        else:
            resultado = buscar_pelicula(nombre, api_key, session)
            cache[clave] = resultado
            time.sleep(sleep)

        # =============================
        # LOGICA FINAL
        # =============================
        if "error" in resultado and resultado["error"] == "No encontrado":

            # 1. MATCH EXACTO
            if clave in dic_no_encontrados:
                resultado["IdPelicula"] = dic_no_encontrados[clave]

            else:
                # 2. SIMILITUD
                id_similar, score = buscar_similar_en_diccionario(
                    clave, dic_no_encontrados, umbral_similitud
                )

                if id_similar:
                    resultado["IdPelicula"] = id_similar

                else:
                    # 3. NUEVO ID
                    nuevo_id = f"IdMV{contador_mv}"
                    dic_no_encontrados[clave] = nuevo_id
                    resultado["IdPelicula"] = nuevo_id
                    contador_mv += 1

            resultado["tmdb_id"] = None

        else:
            resultado["IdPelicula"] = resultado.get("tmdb_id")

        resultados.append(resultado)

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
        
    df_final.drop(
        columns=["Encontrado", "score_similitud", "error"],
        inplace=True,
        errors="ignore",
    )

    if "tmdb_id" in df_final.columns:
        df_final["tmdb_id"] = df_final["tmdb_id"].astype("string")

    df_final["FuenteId"] = df_final["IdPelicula"].apply(
        lambda x: "TMDB" if str(x).isdigit() else "INTERNO"
    )

    return df_final, dic_no_encontrados, contador_mv