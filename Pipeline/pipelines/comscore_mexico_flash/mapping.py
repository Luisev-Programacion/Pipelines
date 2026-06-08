import pandas as pd
from core.utils import homologar_cadena


def _parse_date_column(series, column_name=None):
    """
    Parser flexible de fechas con debug. Intenta múltiples formatos y auto-detección.
    """
    raw = series
    
    if pd.api.types.is_datetime64_any_dtype(raw):
        print(f"[DEBUG {column_name}] Ya es datetime64, retornando como está")
        return pd.to_datetime(raw, errors="coerce")

    raw_str = raw.astype(str).str.strip()
    
    # Mostrar primeros valores sin procesar
    print(f"\n[DEBUG {column_name}] Primeros 10 valores sin procesar:")
    for i, v in enumerate(raw_str.head(10)):
        print(f"  [{i}] '{v}'")
    
    # IMPORTANTE: Orden específico - los formatos con timestamp van primero
    formatos = [
        "%Y-%m-%d %H:%M:%S",    # Formato timestamp ISO (2026-03-09 00:00:00)
        "%Y-%m-%d %H:%M:%S.%f", # Con microsegundos
        "%d/%m/%Y",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%m/%d/%Y"
    ]
    mejor = None
    mejor_validos = -1
    mejor_formato = None

    for fmt in formatos:
        try:
            parsed = pd.to_datetime(raw_str, format=fmt, errors="coerce")
            validos = parsed.notna().sum()
            print(f"  Formato '{fmt}': {validos}/{len(parsed)} válidas")
            if validos > mejor_validos:
                mejor_validos = validos
                mejor = parsed
                mejor_formato = fmt
            if len(parsed) > 0 and validos / len(parsed) > 0.9:
                print(f"  ✓ Usando formato '{fmt}'")
                return parsed
        except Exception as e:
            print(f"  Formato '{fmt}': Error ({e})")

    # Auto-detección como último recurso
    autodetect = pd.to_datetime(raw_str, dayfirst=True, errors="coerce")
    autodetect_validos = autodetect.notna().sum()
    print(f"  Auto-detect (dayfirst=True): {autodetect_validos}/{len(autodetect)} válidas")
    
    if autodetect_validos >= mejor_validos:
        print(f"  ✓ Auto-detect fue mejor, usándolo")
        result = autodetect
    else:
        print(f"  ✓ Usando mejor formato: '{mejor_formato}'")
        result = mejor if mejor is not None else pd.to_datetime(raw_str, errors="coerce")
    
    nulos_finales = result.isna().sum()
    print(f"[DEBUG {column_name}] Total NULL: {nulos_finales}/{len(result)}")
    
    # Mostrar qué valores quedaron NULL
    if nulos_finales > 0 and nulos_finales < len(result):
        print(f"[DEBUG {column_name}] Primeros 5 valores que quedaron NULL:")
        null_mask = result.isna()
        for i, original in enumerate(raw_str[null_mask].head(5)):
            print(f"  [{i}] '{original}'")
    
    return result


def transformar(df):

    df_final = pd.DataFrame()

    df_final["IdComscoreFlash"] = df["IBOE Rentrak # by Theatre"].astype(str).str.strip()
    df_final["Pais"] = df["Country"]
    df_final["FechaComscore"] = _parse_date_column(df["Date"], "FechaComscore")
    df_final["Cadena"] = df["Theatre Circuit Name"]
    df_final["CadenaHomologada"] = df["Theatre Circuit Name"].apply(homologar_cadena)
    df_final["IdCircuito"] = df["Screen Circuit ID"]
    df_final["CineComscoreFlash"] = df["Theatre Name"]
    df_final["CiudadComscoreFlash"] = df["City"]
    df_final["NumeroSala"] = pd.to_numeric(df["Screen Number"], errors="coerce")
    df_final["NombrePelicula"] = df["Film Name"]
    df_final["Formato"] = df["Format"]
    df_final["Lenguaje"] = df["Language"]
    df_final["MonedaLocal"] = pd.to_numeric(df["Local Currency"], errors="coerce")
    df_final["Admision"] = pd.to_numeric(df["Adm"], errors="coerce")
    df_final["MonedaUs"] = pd.to_numeric(df["US Dollars"], errors="coerce")
    df_final["Genero"] = df["Film Genre"]
    df_final["FechaLanzamiento"] = _parse_date_column(df["Release Date"], "FechaLanzamiento")
    df_final["Distribuidor"] = df["Distributor"]
    df_final["PaisOrigen"] = df["Country of Origin"]
    df_final["Rating"] = df["Rating"]

    return df_final
   