"""
Script de validación: verifica que el mapeo de columnas funciona correctamente
antes de insertar en SQL Server
"""
import pandas as pd
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

# ==========================================
# CONFIG SQL SERVER
# ==========================================
SERVER = r"10.55.55.134\SQLDEV"
DATABASE = "Programacion"
PASSWORD = "ProgramacionPoderos0*"
USERNAME = "admin_sql"
DRIVER = "ODBC Driver 17 for SQL Server"

# ==========================================
# ARCHIVO Y MAPEO
# ==========================================
ARCHIVO_EXCEL = (
    r"C:\Users\luisev\OneDrive - OPERADORA DE CINEMAS S.A. DE C.V\Documentos\Cinemex_IA\Proyecto inicial\data\data 2026-04\Procesada\CatalogoCinemas.xlsx"
)
TABLA_SQL = "CatalogoCinemas"

MAPEO_COLUMNAS = {
    "Rentrak Anterior": "RentrakAnterior",
    "Nombre MexAtte": "NombreMexAtte",
    "Nombre Rentrak": "NombreRentrak",
    "Cd. CNMX": "CdCNMX",
    "Estado CNMX": "EstadoCNMX",
    "Edo IBOE": "EdoIBOE",
    "Apertura Fecha": "AperturaFecha",
    "Año Apertura": "AñoApertura",
    "Zona de Competencia": "ZonadeCompetencia",
    "Nombre Operaciones": "NombreOperaciones",
    "Nombre Comscore": "NombreComscore",
    "Nombre Film Session": "NombreFilmSession",
    "Nombre Showtime": "NombreShowtime",
}

def crear_engine():
    connection_string = (
        f"DRIVER={{{DRIVER}}};SERVER={SERVER};DATABASE={DATABASE};"
        f"UID={USERNAME};PWD={PASSWORD};TrustServerCertificate=yes;"
    )
    return create_engine(f"mssql+pyodbc:///?odbc_connect={quote_plus(connection_string)}")

def validar_mapeo():
    """Valida que el mapeo de columnas está correcto"""
    
    print("=" * 80)
    print("VALIDACIÓN: Mapeo de columnas")
    print("=" * 80)
    
    # 1. LEER EXCEL
    print("\n1. Leyendo Excel...")
    df = pd.read_excel(ARCHIVO_EXCEL)
    df.columns = df.columns.str.strip()
    
    print(f"   ✓ {len(df)} filas cargadas")
    
    # 2. APLICAR MAPEO
    print("\n2. Aplicando mapeo de columnas...")
    print("   Mapeos a aplicar:")
    for excel_col, sql_col in MAPEO_COLUMNAS.items():
        existe = excel_col in df.columns
        print(f"      '{excel_col}' → '{sql_col}' | {'✓' if existe else '❌'}")
        if not existe:
            print(f"         ⚠️  ADVERTENCIA: Columna no existe en Excel")
    
    df = df.rename(columns=MAPEO_COLUMNAS)
    print(f"   ✓ Mapeo aplicado")
    
    # 3. CONECTAR A SQL Y OBTENER COLUMNAS
    print("\n3. Obteniendo columnas de SQL Server...")
    engine = crear_engine()
    
    with engine.connect() as conn:
        sql_cols = pd.read_sql(
            text(
                """
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = :tabla
                ORDER BY ORDINAL_POSITION
                """
            ),
            conn,
            params={"tabla": TABLA_SQL},
        )
    
    sql_cols_set = set(sql_cols["COLUMN_NAME"].str.strip())
    excel_cols_set = set(df.columns)
    
    print(f"   ✓ Columnas en SQL: {len(sql_cols_set)}")
    
    # 4. VALIDAR COINCIDENCIAS
    print("\n4. Validando coincidencias Excel ↔ SQL...")
    print("-" * 80)
    
    columnas_mapeadas = set(MAPEO_COLUMNAS.values())
    columnas_originales = set(df.columns) - columnas_mapeadas
    
    todas_coinciden = True
    
    print("\n   Columnas mapeadas (con espacios → sin espacios):")
    for col_sql in sorted(columnas_mapeadas):
        en_excel = col_sql in excel_cols_set
        en_sql = col_sql in sql_cols_set
        
        status = "✓ OK" if (en_excel and en_sql) else "❌ ERROR"
        print(f"      {status} '{col_sql}' (Excel: {en_excel}, SQL: {en_sql})")
        
        if not (en_excel and en_sql):
            todas_coinciden = False
    
    print("\n   Columnas sin mapeo (deben coincidir exactamente):")
    for col in sorted(columnas_originales):
        en_sql = col in sql_cols_set
        status = "✓ OK" if en_sql else "❌ ERROR"
        print(f"      {status} '{col}'")
        
        if not en_sql:
            todas_coinciden = False
    
    # 5. ANÁLISIS DE DATOS
    print("\n5. Análisis de datos en columnas mapeadas...")
    print("-" * 80)
    
    for sql_col in sorted(columnas_mapeadas):
        if sql_col in df.columns:
            datos = df[sql_col]
            no_nulos = datos.notna().sum()
            nulos = datos.isna().sum()
            
            print(f"\n   '{sql_col}':")
            print(f"      - Total filas: {len(datos)}")
            print(f"      - No nulos: {no_nulos} ({100*no_nulos/len(datos):.1f}%)")
            print(f"      - Nulos: {nulos} ({100*nulos/len(datos):.1f}%)")
            print(f"      - Tipo: {datos.dtype}")
            
            if no_nulos > 0:
                print(f"      - Ejemplo: {datos.dropna().iloc[0]}")
    
    # 6. RESUMEN
    print("\n" + "=" * 80)
    if todas_coinciden:
        print("✓ VALIDACIÓN OK: Todas las columnas coinciden correctamente")
        print("  Puedes proceder con ExportXL.py")
    else:
        print("❌ VALIDACIÓN FALLÓ: Hay problemas con el mapeo")
        print("  Revisa los errores arriba y ajusta el mapeo")
    
    print("=" * 80)
    
    return todas_coinciden

if __name__ == "__main__":
    try:
        validar_mapeo()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
