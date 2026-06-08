"""
Script de depuración para identificar por qué las columnas se cargan como NULL
"""
import pandas as pd
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus


SERVER = r"10.55.55.134\SQLDEV"
DATABASE = "Programacion"
PASSWORD = "ProgramacionPoderos0*"
USERNAME = "admin_sql"
DRIVER = "ODBC Driver 17 for SQL Server"

# ==========================================
# ARCHIVO A DEPURAR
# ==========================================
ARCHIVO_EXCEL = (
    r"C:\Users\luisev\Downloads\ReporteSemanal1.xlsx"
)
TABLA_SQL = "SemanalesShowtime"

# Columnas que se están cargando como NULL
COLUMNAS_PROBLEMATICAS = [
    "Rentrak",
    "RentrakAnterior",
    "NombreMexAtte",
    "NombreRentrak",
    "CdCNMX",
    "EstadoCNMX",
    "EdoIBOE",
    "AperturaFecha",
    "AñoApertura",
    "ZonadeCompetencia",
    "NombreOperaciones",
    "NombreComscore",
    "NombreFilmSession",
    "NombreShowtime",
]

def crear_engine():
    connection_string = (
        f"DRIVER={{{DRIVER}}};SERVER={SERVER};DATABASE={DATABASE};"
        f"UID={USERNAME};PWD={PASSWORD};TrustServerCertificate=yes;"
    )
    return create_engine(f"mssql+pyodbc:///?odbc_connect={quote_plus(connection_string)}")

def debug_excel_sql():
    """Compara Excel vs SQL Server para identificar problemas"""
    
    print("=" * 80)
    print("DEPURACIÓN: ExportXL.py")
    print("=" * 80)
    
    # 1. LEER EXCEL
    print("\n1. LEYENDO EXCEL...")
    print(f"   Archivo: {ARCHIVO_EXCEL}")
    
    df = pd.read_excel(ARCHIVO_EXCEL)
    print(f"   ✓ Filas: {len(df)}, Columnas: {len(df.columns)}")
    
    # Ver nombres de columnas sin procesar
    print("\n2. NOMBRES DE COLUMNAS EN EXCEL (sin procesar):")
    for i, col in enumerate(df.columns):
        print(f"   [{i}] '{col}' (len={len(col)}, tipo={type(col).__name__})")
    
    # Procesar como lo hace ExportXL.py
    df.columns = df.columns.str.strip()
    
    print("\n3. NOMBRES DE COLUMNAS EN EXCEL (DESPUÉS DE .strip()):")
    for i, col in enumerate(df.columns):
        print(f"   [{i}] '{col}' (len={len(col)}, tipo={type(col).__name__})")
    
    # 4. CONECTAR A SQL SERVER Y VER COLUMNAS
    print("\n4. COLUMNAS EN SQL SERVER:")
    engine = crear_engine()
    
    with engine.connect() as conn:
        sql_cols = pd.read_sql(
            text(
                """
                SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = :tabla
                ORDER BY ORDINAL_POSITION
                """
            ),
            conn,
            params={"tabla": TABLA_SQL},
        )
    
    print(f"   Total columnas en SQL: {len(sql_cols)}")
    for idx, row in sql_cols.iterrows():
        print(f"   '{row['COLUMN_NAME']}' | {row['DATA_TYPE']} | IS_NULLABLE={row['IS_NULLABLE']}")
    
    # 5. COMPARAR COLUMNAS PROBLEMÁTICAS
    print("\n5. ANÁLISIS DE COLUMNAS PROBLEMÁTICAS:")
    print("-" * 80)
    
    sql_cols_set = set(sql_cols["COLUMN_NAME"].str.strip())
    excel_cols_set = set(df.columns)
    
    for col_problema in COLUMNAS_PROBLEMATICAS:
        print(f"\n   '{col_problema}':")
        
        # ¿Existe en Excel?
        en_excel = col_problema in excel_cols_set
        print(f"      ¿En Excel? {en_excel}")
        
        # ¿Existe en SQL?
        en_sql = col_problema in sql_cols_set
        print(f"      ¿En SQL? {en_sql}")
        
        if en_excel and en_sql:
            # Analizar los datos
            datos = df[col_problema]
            print(f"      Datos en Excel:")
            print(f"         - Total filas: {len(datos)}")
            print(f"         - No nulos: {datos.notna().sum()}")
            print(f"         - Nulos: {datos.isna().sum()}")
            print(f"         - Tipo de dato: {datos.dtype}")
            print(f"         - Primeros 5 valores: {datos.head().tolist()}")
            print(f"         - Últimos 5 valores: {datos.tail().tolist()}")
            
            # Ver tipos de datos
            print(f"         - Valores únicos: {datos.nunique()}")
            
            # Detectar problemas de formato
            if datos.dtype == 'object':
                print(f"         ⚠️  Columna es tipo 'object' (probablemente strings)")
                # Mostrar ejemplos
                not_null = datos.dropna()
                if len(not_null) > 0:
                    print(f"         Ejemplo de valores no nulos: {not_null.head(3).tolist()}")
        
        elif not en_excel and en_sql:
            print(f"      ❌ PROBLEMA: Columna NO está en Excel pero SÍ en SQL")
        
        elif en_excel and not en_sql:
            print(f"      ❌ PROBLEMA: Columna SÍ está en Excel pero NO en SQL")
        
        else:
            print(f"      ❌ PROBLEMA: Columna no existe en Excel ni en SQL")
    
    # 6. COLUMNAS EN EXCEL QUE NO ESTÁN EN SQL
    print("\n6. COLUMNAS EN EXCEL QUE NO COINCIDEN CON SQL:")
    print("-" * 80)
    excel_no_sql = excel_cols_set - sql_cols_set
    if excel_no_sql:
        for col in sorted(excel_no_sql):
            print(f"   '{col}' <- Se ignorará (no existe en SQL)")
    else:
        print("   ✓ Todas las columnas del Excel existen en SQL")
    
    # 7. VERIFICAR DATOS FILA A FILA
    print("\n7. MUESTRA DE DATOS (primeras 3 filas):")
    print("-" * 80)
    cols_ver = [c for c in COLUMNAS_PROBLEMATICAS if c in df.columns]
    print(df[cols_ver].head(3).to_string())
    
    print("\n" + "=" * 80)
    print("RESUMEN DE DEPURACIÓN COMPLETADO")
    print("=" * 80)

if __name__ == "__main__":
    try:
        debug_excel_sql()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
