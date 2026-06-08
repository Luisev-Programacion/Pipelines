import pandas as pd

# Rutas con prefijo 'r'
file_path = r'C:\Users\luisev\OneDrive - OPERADORA DE CINEMAS S.A. DE C.V\Documentos\Cinemex_IA\Proyecto inicial\data\data 2026-04\Procesada\CatalogoCinemas.xlsx'
output_path = r'C:\Users\luisev\OneDrive - OPERADORA DE CINEMAS S.A. DE C.V\Documentos\Cinemex_IA\Proyecto inicial\data\data 2026-04\Raw\Catalogo2Result.txt'

# 1. LEER COMO EXCEL (Esto eliminará los caracteres extraños)
try:
    # Usamos read_excel porque el contenido interno es binario
    df = pd.read_excel(file_path, engine='openpyxl')
    print(f"✅ Archivo Excel leído correctamente. Filas detectadas: {len(df)}")
except Exception as e:
    print(f"❌ Error al leer como Excel: {e}")
    exit()

# 2. Generación de Inserts
table_name = 'CatalogoCinemas'

def format_sql_value(val):
    val_str = str(val).strip()
    # Manejar nulos de Excel
    if not val_str or val_str.lower() in ['nan', 'none', 'null']:
        return "NULL"
    # Escapar comillas simples para SQL
    clean_val = val_str.replace("'", "''")
    return f"'{clean_val}'"

with open(output_path, 'w', encoding='utf-8') as f:
    f.write("SET NOCOUNT ON;\nGO\n\n")
    
    for _, row in df.iterrows():
        try:
            # Extraemos las 8 columnas basándonos en tu estructura
            # Asegúrate de que el Excel tenga exactamente ese orden
            values = [format_sql_value(row.iloc[i]) for i in range(8)]
            
            sql = (f"INSERT INTO {table_name} "
                   f"(Semana, Pelicula, IdComscore, Distribuidora, Clasificacion, Formato, Idioma, TipoEstreno) "
                   f"VALUES ({', '.join(values)});\n")
            f.write(sql)
        except Exception:
            continue

print(f"🚀 ¡Ahora sí! Archivo SQL limpio generado en:\n{output_path}")