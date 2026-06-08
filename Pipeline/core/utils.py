import pandas as pd
import os

def leer_csv_gz(path):
    return pd.read_csv(
        path,
        compression="gzip",
        dtype=str,
        encoding="latin1",
        low_memory=False
    )

def cargar_procesados(path):
    if not os.path.exists(path):
        return set()
    with open(path, "r") as f:
        return set(line.strip() for line in f)

def guardar_procesado(path, archivo):
    with open(path, "a") as f:
        f.write(archivo + "\n")


def es_valor_nulo(cadena):
    if cadena is None:
        return True
    valor = str(cadena).strip()
    if valor == "":
        return True
    return valor.lower() in {
        "nan",
        "na",
        "<na>",
        "null",
        "none",
        "n/a",
        "sin datos",
    }


def limpiar_valores_nulos(df):
    df = df.copy()
    for col in df.columns:
        if df[col].dtype == object or pd.api.types.is_string_dtype(df[col]):
            df[col] = df[col].apply(
                lambda x: pd.NA if es_valor_nulo(x) else x
            )
    return df


def homologar_cadena(cadena):
    if not cadena:
        return "INDEPENDIENTES"

    c = str(cadena).upper()

    if "CINEPOLIS" in c:
        return "CINEPOLIS"
    elif "CINEMEX" in c:
        return "CINEMEX"
    else:
        return "INDEPENDIENTES"