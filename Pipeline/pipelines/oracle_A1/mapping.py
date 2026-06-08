import pandas as pd
from core.utils import homologar_cadena
from .config import PIPELINE_CONFIG as config

def transformar(df):

    # Debug: mostrar columnas disponibles
    print(f"Columnas en el DataFrame: {list(df.columns)}")
    
    # Validar que existan las columnas necesarias
    columnas_requeridas = ["sitename", "scheduledate", "eventname", "codigo_formato", 
                          "formato", "val", "adm", "centrodecostos", "codigo3letras", 
                          "capacidadsala", "showtime", "numerodesala"]
    faltantes = [col for col in columnas_requeridas if col not in df.columns]
    if faltantes:
        raise ValueError(f"Columnas faltantes: {faltantes}. Disponibles: {list(df.columns)}")

    print(f"DEBUG: Tipo de dato de scheduledate: {df['scheduledate'].dtype}")
    print(f"DEBUG: Valores únicos de scheduledate (sin procesar, primeros 30):")
    for idx, val in enumerate(df["scheduledate"].unique()[:30]):
        print(f"  [{idx}] '{val}' (tipo: {type(val).__name__})")

    df_final = pd.DataFrame()

    df_final["Estado"] = df["sitename"]
    
    # Intentar convertir FechaOracle con múltiples formatos
    fecha_raw = df["scheduledate"].astype(str).str.strip()
    
    print(f"DEBUG: Primeros 5 valores de fecha_raw después de strip:")
    for i, v in enumerate(fecha_raw.head(5)):
        print(f"  [{i}] '{v}'")
    
    # Intentar formatos comunes
    formatos = ["%d/%m/%Y", "%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%m/%d/%Y"]
    fecha_parseada = None
    
    for fmt in formatos:
        try:
            temp = pd.to_datetime(fecha_raw, format=fmt, errors="coerce")
            nulos = temp.isna().sum()
            total = len(temp)
            validos = total - nulos
            print(f"DEBUG: Formato '{fmt}' -> {validos}/{total} fechas válidas ({100*validos/total:.1f}%)")
            
            # Si este formato parsea más del 90% de las fechas, usarlo
            if validos / total > 0.9:
                fecha_parseada = temp
                print(f"DEBUG: ✓ Usando formato '{fmt}'")
                break
        except Exception as e:
            print(f"DEBUG: Formato '{fmt}' -> Error: {e}")
    
    # Si ningún formato funcionó, usar auto-detección
    if fecha_parseada is None:
        print(f"DEBUG: Ningún formato fijo funcionó, usando auto-detección...")
        fecha_parseada = pd.to_datetime(fecha_raw, errors="coerce")
    
    df_final["FechaOracle"] = fecha_parseada
    
    print(f"DEBUG: Muestra de FechaOracle después del parseo (antes del merge):")
    print(df_final[["FechaOracle"]].head(10))
    print(f"DEBUG: Nulos en FechaOracle: {df_final['FechaOracle'].isna().sum()}")
    
    df_final["Pelicula"] = df["eventname"]
    df_final["CodigoFormato"] = df["codigo_formato"]
    df_final["Formato"] = df["formato"]
    df_final["Taquilla"] = pd.to_numeric(df["val"], errors="coerce")
    df_final["Asistencia"] = pd.to_numeric(df["adm"], errors="coerce")
    df_final["CentroCostos"] = df["centrodecostos"]
    df_final["CodigoLetras"] = df["codigo3letras"]
    df_final["Capacidad"] = pd.to_numeric(df["capacidadsala"], errors="coerce")
    df_final["Hora"] = pd.to_datetime(
        df["showtime"].astype(str).str.strip(),
        errors="coerce",
    )
    df_final["Sala"] = df["numerodesala"]

    catalogo = pd.read_excel(
        config["catalogos"]["formato"]
    )
    
    print(f"Columnas del catálogo: {list(catalogo.columns)}")

    df_final = df_final.merge(
        catalogo,
        left_on="CodigoFormato",
        right_on="codigo_formato",
        how="left"
    )

    print(f"DEBUG: Columnas después del merge: {list(df_final.columns)}")
    print(f"DEBUG: Muestra de FechaOracle después del merge:")
    print(df_final[["FechaOracle"]].head(10))
    print(f"DEBUG: Nulos en FechaOracle después del merge: {df_final['FechaOracle'].isna().sum()}")
    print(f"DEBUG: Dtype de FechaOracle: {df_final['FechaOracle'].dtype}")

    # Mantener las columnas que aporta el catálogo
    if "idioma" in df_final.columns:
        df_final = df_final.rename(columns={"idioma": "Idioma"})
    if "tipo_sala" in df_final.columns:
        df_final = df_final.rename(columns={"tipo_sala": "TipoSala"})

    # Eliminar columnas duplicadas o no necesarias del merge del catálogo
    columnas_a_descartar = ["codigo_formato", "formato", "semanacalendario", "runweek"]
    df_final = df_final.drop(
        columns=[col for col in columnas_a_descartar if col in df_final.columns],
        errors="ignore"
    )

    return df_final
   