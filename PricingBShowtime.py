import pandas as pd
import os

# --- RUTAS ---
archivo_entrada = r"C:\Users\luisev\Downloads\Tendencia de la Venta de Boletos_2026-06-01T13_48_21.xlsx"
archivo_salida = r"C:\Users\luisev\OneDrive - OPERADORA DE CINEMAS S.A. DE C.V\Documentos\Cinemex_IA\Proyecto inicial\data\data 2026-04\Procesada\ShowtimePromos\Reporte25-mayo31.xlsx"
archivo_mapeo = r"C:\Users\luisev\OneDrive - OPERADORA DE CINEMAS S.A. DE C.V\Documentos\Cinemex_IA\Proyecto inicial\notebooks\Pipeline\pipelines\Diccionarios\Mapeo.xlsx"

CATEGORIAS_PADRE = ["Asistencia Pagada", "IE", "Promociones Taq", "Pases", "Prepago"]
def cargar_mapeo(ruta):
    try:
        df_map = pd.read_excel(ruta)
        return dict(zip(df_map['Marcacion'].astype(str).str.strip().str.upper(), 
                         df_map['Etiqueta'].astype(str).str.strip()))
    except Exception as e:
        print(f"❌ Error cargando mapeo: {e}")
        return {}

def limpiar_valor(valor):
    s_val = str(valor).strip()
    if s_val in [".", "", "nan"] or pd.isna(valor):
        return 0
    if s_val.endswith('.'): s_val = s_val[:-1]
    try:
        return float(pd.to_numeric(s_val.replace(',', ''), errors='coerce'))
    except:
        return 0

def extraer_datos_hoja(df, diccionario_mapeo, nombre_kpi):
    """Transforma la hoja de formato ancho a largo (Unpivot)."""
    df = df.rename(columns={df.columns[0]: "Marcacion"})
    resultados = []
    tipo_actual = "No Identificado"

    for _, row in df.iterrows():
        marcacion_raw = str(row["Marcacion"]).strip()
        if marcacion_raw in CATEGORIAS_PADRE:
            tipo_actual = marcacion_raw
            continue
        if marcacion_raw in ["nan", ""]: continue

        for col in df.columns[1:]:
            fecha_dt = pd.to_datetime(col, errors="coerce")
            if pd.isna(fecha_dt): continue
            
            valor_num = limpiar_valor(row[col])
            etiqueta = diccionario_mapeo.get(marcacion_raw.upper(), "Sin Etiqueta")

            resultados.append({
                "Fecha": fecha_dt.normalize(),
                "Marcacion": marcacion_raw,
                "Tipo Dinamica": tipo_actual,
                "Etiqueta": etiqueta,
                nombre_kpi: valor_num
            })
    return pd.DataFrame(resultados)

# --- PROCESO PRINCIPAL ---
if os.path.exists(archivo_entrada):
    mapeo_dict = cargar_mapeo(archivo_mapeo)
    xls = pd.ExcelFile(archivo_entrada)
    
    # 1. Procesar cada hoja por separado
    df_asistencia = extraer_datos_hoja(pd.read_excel(xls, "Asistencia"), mapeo_dict, "Asistencia")
    df_taquilla = extraer_datos_hoja(pd.read_excel(xls, "Ingreso de boletos"), mapeo_dict, "Taquilla")

    # 2. Unir (Merge) ambos DataFrames por sus dimensiones comunes
    # Usamos 'outer' por si acaso una marcación existe en una hoja pero no en la otra
    df_nuevo = pd.merge(
        df_asistencia, 
        df_taquilla, 
        on=["Fecha", "Marcacion", "Tipo Dinamica", "Etiqueta"], 
        how="outer"
    ).fillna(0) # Si falta un dato en alguna hoja, ponemos 0

    # 3. Manejo de Histórico (UPSERT)
    if os.path.exists(archivo_salida):
        df_hist = pd.read_excel(archivo_salida)
        df_hist["Fecha"] = pd.to_datetime(df_hist["Fecha"]).dt.normalize()
        
        # Combinamos y mantenemos lo más nuevo
        df_final = pd.concat([df_hist, df_nuevo], ignore_index=True)
        df_final = df_final.drop_duplicates(subset=["Fecha", "Marcacion"], keep="last")
        df_final.drop(columns=["Acumulado"], inplace=True, errors="ignore")
    else:
        df_final = df_nuevo

    # 4. Guardar archivo final único (una sola hoja)
    df_final.to_excel(archivo_salida, index=False, sheet_name="Datos_Consolidados")

    print(f"✅ ¡Éxito! Se han cruzado los KPIs. Archivo final: {archivo_salida}")
    print(f"Columnas finales: {df_final.columns.tolist()}")
else:
    print("❌ No se encontró el archivo de entrada.")