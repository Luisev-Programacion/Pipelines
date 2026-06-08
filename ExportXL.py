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

SQL_SERVER_MAX_PARAMS = 2100


# ==========================================
# CARGAS: Excel -> tabla SQL
# ==========================================

CARGAS = [
    {
        "archivo_excel": r"C:\Users\luisev\OneDrive - OPERADORA DE CINEMAS S.A. DE C.V\Documentos\Cinemex_IA\Proyecto inicial\data\data 2026-04\Procesada\ShowtimePromos\Reporte25-mayo31.xlsx",
        "tabla_destino": "SemanalesShowtime",
        "if_exists": "append",
        "mapeo_columnas": {
            "Tipo Dinamica": "TipoDinamica",
        },
        "foreign_keys": [
            {
                "columna": "Fecha",
                "tabla_referencia": "Fecha",
                "columna_referencia": "Fecha",
            }
        ],
    },
]


def crear_engine():
    """Crea conexión a SQL Server"""
    connection_string = (
        f"DRIVER={{{DRIVER}}};SERVER={SERVER};DATABASE={DATABASE};"
        f"UID={USERNAME};PWD={PASSWORD};TrustServerCertificate=yes;"
    )
    return create_engine(f"mssql+pyodbc:///?odbc_connect={quote_plus(connection_string)}")


def alinear_columnas_sql(df, engine, tabla_destino, mapeo_columnas=None):
    """Alinea columnas del Excel con las de SQL Server (aplica mapeo si existe)"""
    if mapeo_columnas:
        df = df.rename(columns=mapeo_columnas)
    
    with engine.connect() as conn:
        sql_cols = pd.read_sql(
            text(
                "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = :tabla "
                "ORDER BY ORDINAL_POSITION"
            ),
            conn,
            params={"tabla": tabla_destino},
        )
    
    validas = set(sql_cols["COLUMN_NAME"].str.strip())
    excel_cols = list(df.columns)
    usar = [c for c in excel_cols if c in validas]
    omitidas = [c for c in excel_cols if c not in validas]
    
    if omitidas:
        print(f"  Columnas omitidas: {omitidas}")
    
    if not usar:
        raise ValueError(
            f"No hay coincidencias de columnas. Excel: {excel_cols} | SQL: {sorted(validas)}"
        )
    
    return df[usar]





def filtrar_foreign_keys(df, engine, foreign_keys):
    """Filtra filas que no tienen relaciones FK válidas (case-insensitive)"""
    df_out = df.copy()
    
    for fk in foreign_keys:
        col = fk["columna"]
        ref_table = fk["tabla_referencia"]
        ref_col = fk["columna_referencia"]
        
        with engine.connect() as conn:
            ref_ids = pd.read_sql(
                text(f"SELECT DISTINCT UPPER([{ref_col}]) AS id FROM dbo.[{ref_table}]"),
                conn,
            )
        
        ref_set = set(ref_ids["id"].dropna().str.upper())
        valores = df_out[col].astype(str).str.upper()
        mask = valores.isin(ref_set)
        rechazadas = (~mask).sum()
        
        if rechazadas:
            invalidos = valores[~mask].dropna().unique().tolist()
            print(f"  FK {col} -> {ref_table}.{ref_col}: {rechazadas} fila(s) rechazadas")
        
        df_out = df_out.loc[mask].copy()
    
    return df_out





def cargar_excel_a_sql(engine, carga):
    """Carga un archivo Excel a SQL Server"""
    archivo = carga["archivo_excel"]
    tabla = carga["tabla_destino"]
    if_exists = carga.get("if_exists", "append")
    mapeo_columnas = carga.get("mapeo_columnas")
    
    print(f"\n--- {archivo} -> dbo.{tabla} ---")
    print("Leyendo Excel...")
    
    df = pd.read_excel(archivo)
    df.columns = df.columns.str.strip()
    df = df.where(pd.notnull(df), None)
    
    df = alinear_columnas_sql(df, engine, tabla, mapeo_columnas=mapeo_columnas)
    
    if carga.get("foreign_keys"):
        antes = len(df)
        df = filtrar_foreign_keys(df, engine, carga["foreign_keys"])
        print(f"  Filas tras validar FK: {len(df)} (de {antes})")
    
    if df.empty:
        print("  Sin filas para insertar")
        return
    
    chunksize = max(1, SQL_SERVER_MAX_PARAMS // len(df.columns))
    
    print(f"Insertando {len(df)} filas...")
    df.to_sql(
        name=tabla,
        con=engine,
        schema="dbo",
        if_exists=if_exists,
        index=False,
        chunksize=chunksize,
    )
    print(f"✓ Carga OK: {len(df)} filas")





def main():
    if not CARGAS:
        raise ValueError("Defina al menos una carga en CARGAS")
    
    engine = crear_engine()
    
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    
    print(f"Conectado a {SERVER} / {DATABASE}")
    
    for carga in CARGAS:
        cargar_excel_a_sql(engine, carga)
    
    print("\n✓ Todas las cargas finalizaron")





if __name__ == "__main__":

    main()


