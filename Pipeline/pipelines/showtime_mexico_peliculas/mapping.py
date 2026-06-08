import pandas as pd
from core.utils import limpiar_valores_nulos


def _col(df, name):
    if name in df.columns:
        return df[name]
    return pd.Series([pd.NA] * len(df), index=df.index)


def transformar(df):

    df_final = pd.DataFrame()

    df_final["Estatus"] = _col(df, "Estatus")
    df_final["FechaShowtime"] = pd.to_datetime(_col(df, "Date"), errors="coerce").dt.date
    df_final["Hora"] = _col(df, "Time").astype(str).str.strip()
    df_final["Cinema"] = _col(df, "Cine")
    df_final["Sala"] = _col(df, "Pantallas")
    df_final["NombrePelicula"] = _col(df, "Title Versions")
    df_final["Asistencia"] = pd.to_numeric(_col(df, "Asistencia"), errors="coerce")
    df_final["Capacidad"] = pd.to_numeric(_col(df, "Capacidad"), errors="coerce")
    df_final["IngresoDeBoletos"] = pd.to_numeric(_col(df, "Ingreso de boletos"), errors="coerce")

    df_final = limpiar_valores_nulos(df_final)

    return df_final
