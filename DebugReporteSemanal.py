"""
Script de depuración para ReporteSemanal1.xlsx
"""
import pandas as pd
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus

SERVER = r"10.55.55.134\SQLDEV"
DATABASE = "Programacion"
PASSWORD = "ProgramacionPoderos0*"
USERNAME = "admin_sql"
DRIVER = "ODBC Driver 17 for SQL Server"

ARCHIVO = r"C:\Users\luisev\Downloads\ReporteSemanal1.xlsx"
TABLA = "SemanalesShowtime"

def crear_engine():
    connection_string = (
        f"DRIVER={{{DRIVER}}};SERVER={SERVER};DATABASE={DATABASE};"
        f"UID={USERNAME};PWD={PASSWORD};TrustServerCertificate=yes;"
    )
    return create_engine(f"mssql+pyodbc:///?odbc_connect={quote_plus(connection_string)}")

print("=" * 80)
print("DEPURACIÓN: ReporteSemanal1.xlsx")
print("=" * 80)

# 1. LEER EXCEL
print("\n1. LEYENDO EXCEL...")
df = pd.read_excel(ARCHIVO)
df.columns = df.columns.str.strip()
print(f"   ✓ Filas: {len(df)}, Columnas: {len(df.columns)}")

print("\n2. COLUMNAS EN EXCEL:")
for i, col in enumerate(df.columns):
    print(f"   [{i}] '{col}'")

# 2. COLUMNAS SQL
print("\n3. COLUMNAS EN SQL SERVER:")
engine = crear_engine()

with engine.connect() as conn:
    sql_cols = pd.read_sql(
        text(
            """
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = :tabla
            ORDER BY ORDINAL_POSITION
            """
        ),
        conn,
        params={"tabla": TABLA},
    )

for idx, row in sql_cols.iterrows():
    print(f"   '{row['COLUMN_NAME']}' | {row['DATA_TYPE']} | nullable={row['IS_NULLABLE']}")

# 3. COMPARACIÓN
print("\n4. ANÁLISIS:")
print("-" * 80)

excel_cols_set = set(df.columns)
sql_cols_set = set(sql_cols["COLUMN_NAME"].str.strip())

coinciden = excel_cols_set & sql_cols_set
en_excel_no_sql = excel_cols_set - sql_cols_set
en_sql_no_excel = sql_cols_set - excel_cols_set

print(f"\n   Coincidencias exactas: {len(coinciden)}")
for col in sorted(coinciden):
    print(f"      ✓ '{col}'")

print(f"\n   EN EXCEL pero NO en SQL ({len(en_excel_no_sql)}):")
for col in sorted(en_excel_no_sql):
    print(f"      ❌ '{col}'")

print(f"\n   EN SQL pero NO en EXCEL ({len(en_sql_no_excel)}):")
for col in sorted(en_sql_no_excel):
    print(f"      ❌ '{col}'")

# 4. SUGERENCIAS DE MAPEO
if en_excel_no_sql:
    print("\n5. MAPEO SUGERIDO:")
    print("-" * 80)
    print("Copia esto en 'mapeo_columnas':")
    print("{")
    for col in sorted(en_excel_no_sql):
        print(f"    '{col}': '???',  # Busca el equivalente en SQL")
    print("}")

print("\n6. MUESTRA DE DATOS (primeras 3 filas):")
print("-" * 80)
print(df.head(3).to_string())

print("\n" + "=" * 80)
