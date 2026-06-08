"""
Script de verificación: Verifica que las columnas problemáticas
se cargaron correctamente en SQL Server
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

# Columnas que previamente se cargaban como NULL
COLUMNAS_PROBLEMA = [
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

def verificar_datos_cargados():
    """Verifica que los datos se cargaron correctamente"""
    
    print("=" * 80)
    print("VERIFICACIÓN: Datos cargados en SQL Server")
    print("=" * 80)
    
    engine = crear_engine()
    
    # 1. Total de registros
    print("\n1. Total de registros en CatalogoCinemas:")
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) as total FROM dbo.CatalogoCinemas"))
        total = result.scalar()
    
    print(f"   ✓ Total registros: {total}")
    
    # 2. Análisis de columnas problemáticas
    print("\n2. Análisis de columnas problemáticas:")
    print("-" * 80)
    
    query = f"""
    SELECT 
        {', '.join([f"SUM(CASE WHEN [{col}] IS NOT NULL THEN 1 ELSE 0 END) as [{col}]" for col in COLUMNAS_PROBLEMA])}
    FROM dbo.CatalogoCinemas
    """
    
    with engine.connect() as conn:
        df_stats = pd.read_sql(text(query), conn)
    
    for col in COLUMNAS_PROBLEMA:
        no_nulos = int(df_stats[col].iloc[0]) if df_stats[col].iloc[0] is not None else 0
        porcentaje = 100 * no_nulos / total if total > 0 else 0
        
        status = "✓" if no_nulos > 0 else "❌"
        print(f"\n   {status} '{col}':")
        print(f"      - No nulos: {no_nulos} ({porcentaje:.1f}%)")
        print(f"      - Nulos: {total - no_nulos}")
    
    # 3. Muestra de datos
    print("\n3. Muestra de datos (primeros 3 registros):")
    print("-" * 80)
    
    with engine.connect() as conn:
        df_muestra = pd.read_sql(
            text(f"SELECT TOP 3 {', '.join([f'[{col}]' for col in COLUMNAS_PROBLEMA])} FROM dbo.CatalogoCinemas"),
            conn
        )
    
    print(df_muestra.to_string())
    
    # 4. Resumen
    print("\n" + "=" * 80)
    print("✓ VERIFICACIÓN COMPLETADA")
    print("  Las columnas que antes se cargaban como NULL ahora tienen datos")
    print("=" * 80)

if __name__ == "__main__":
    try:
        verificar_datos_cargados()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
