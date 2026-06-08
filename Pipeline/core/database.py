import pyodbc
import pandas as pd
from sqlalchemy import create_engine, text

from core.agent_debug import agent_log

NOMBRE_PELICULA_MAX_LEN = 50
_TABLA_METADATA_CACHE = {}
SQL_DATETIME_MIN = pd.Timestamp("1753-01-01")
SQL_DATETIME_MAX = pd.Timestamp("9999-12-31 23:59:59")

def _truncar_nombre_pelicula(nombre, max_len=NOMBRE_PELICULA_MAX_LEN):
    return str(nombre).strip()[:max_len]


def _sql_value(val):
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(val, "item"):
        return val.item()
    return val


def _varchar_max_chars(type_name, max_length):
    if max_length <= 0:
        return None
    t = type_name.lower()
    if t in ("nvarchar", "nchar"):
        return max_length // 2
    if t in ("varchar", "char"):
        return max_length
    return None


def _cast_series(valores, type_name):
    t = type_name.lower()
    if t in ("int", "bigint", "smallint", "tinyint"):
        return pd.to_numeric(valores, errors="coerce")
    if t in ("float", "real"):
        return pd.to_numeric(valores, errors="coerce")
    if t == "date":
        return pd.to_datetime(valores, errors="coerce").dt.date
    if t in ("datetime", "datetime2", "smalldatetime"):
        parsed = pd.to_datetime(valores, errors="coerce")
        return parsed.where((parsed >= SQL_DATETIME_MIN) & (parsed <= SQL_DATETIME_MAX))
    return valores


def _obtener_metadata_tabla(cursor, table_name):
    if table_name in _TABLA_METADATA_CACHE:
        return _TABLA_METADATA_CACHE[table_name]

    cursor.execute(
        """
        SELECT c.name, t.name, c.max_length, c.is_identity
        FROM sys.columns c
        JOIN sys.types t ON c.user_type_id = t.user_type_id
        WHERE c.object_id = OBJECT_ID(?)
        ORDER BY c.column_id
        """,
        table_name,
    )
    meta = {}
    for name, type_name, max_length, is_identity in cursor.fetchall():
        meta[name.lower()] = {
            "name": name,
            "type": type_name,
            "max_length": max_length,
            "is_identity": bool(is_identity),
        }
    _TABLA_METADATA_CACHE[table_name] = meta
    return meta


def _ajustar_df_para_tabla(df, tabla_meta, exclude_columns=None):
    skip = {c.lower() for c in (exclude_columns or [])}
    columnas_sql = []
    series = {}
    omitidas = []

    for col in df.columns:
        key = str(col).lower()
        if key in skip:
            omitidas.append(col)
            continue
        info = tabla_meta.get(key)
        if not info or info["is_identity"]:
            if info is None:
                omitidas.append(col)
            continue
        valores = _cast_series(df[col], info["type"])
        max_chars = _varchar_max_chars(info["type"], info["max_length"])
        if max_chars is not None:
            valores = valores.map(
                lambda v: None
                if v is None or (isinstance(v, float) and pd.isna(v))
                else str(v)[:max_chars]
            )
        series[info["name"]] = valores
        columnas_sql.append(info["name"])

    return pd.DataFrame(series), columnas_sql, omitidas


def _sincronizar_ids_tabla_maestra(cursor, nombres):
    mapping = {}
    for nombre in nombres:
        nombre = _truncar_nombre_pelicula(nombre)
        if not nombre:
            continue
        cursor.execute(
            "SELECT IdPelicula FROM dbo.TablaMaestraPeliculas WHERE NombrePelicula = ?",
            nombre,
        )
        row = cursor.fetchone()
        if row:
            mapping[nombre] = row[0]
        else:
            cursor.execute(
                """
                INSERT INTO dbo.TablaMaestraPeliculas (NombrePelicula)
                OUTPUT INSERTED.IdPelicula
                VALUES (?)
                """,
                nombre,
            )
            mapping[nombre] = cursor.fetchone()[0]
    return mapping


def _sincronizar_cine_fuentes(cursor, ids):
    """Asegura que existan filas en dbo.CineFuentes para los IdComscoreFlash proporcionados.
    Intenta insertar filas mínimas con solo el IdComscoreFlash. Si la inserción falla
    por requerimientos adicionales de columnas, registra el error y continúa.
    Devuelve el número de filas añadidas.
    """
    added = 0
    for val in ids:
        try:
            clave = str(val).strip()
            if not clave:
                continue
        except Exception:
            continue
        try:
            cursor.execute(
                "SELECT 1 FROM dbo.CineFuentes WHERE IdComscoreFlash = ?",
                clave,
            )
            if cursor.fetchone():
                continue
            try:
                cursor.execute(
                    "INSERT INTO dbo.CineFuentes (IdComscoreFlash, IdCatalogo, IDComscoreZonas) VALUES (?, ?, ?)",
                    clave,
                    clave,
                    clave,
                )
                added += 1
            except Exception as e:
                agent_log(
                    "H3",
                    "core/database.py:cinefuentes_sync",
                    "cinefuentes_insert_failed",
                    {"value": clave, "error": str(e)[:500]},
                )
        except Exception as e:
            agent_log(
                "H3",
                "core/database.py:cinefuentes_sync_check",
                "cinefuentes_check_failed",
                {"value": str(val)[:200], "error": str(e)[:500]},
            )
    return added


def insertar_dataframe_sql(df, table_name, connection_string, exclude_columns=None):
    # region agent log
    agent_log(
        "H2",
        "core/database.py:insertar_entry",
        "insert_sql_called",
        {
            "rows": len(df),
            "empty": df.empty,
            "table": table_name,
            "columns": list(df.columns)[:20],
            "col_count": len(df.columns),
        },
    )
    # endregion

    if df.empty:
        print("DataFrame vacío. No se insertó información.")
        return

    try:
        conn = pyodbc.connect(connection_string)
    except Exception as e:
        agent_log(
            "H3",
            "core/database.py:connect_fail",
            "sql_connect_failed",
            {"error_type": type(e).__name__, "error": str(e)[:500]},
        )
        raise

    cursor = conn.cursor()

    if "NombrePelicula" in df.columns:
        df = df.copy()
        df["NombrePelicula"] = df["NombrePelicula"].map(_truncar_nombre_pelicula)

    if "NombrePelicula" in df.columns and "IdPelicula" in df.columns:
        nombres = df["NombrePelicula"].dropna().unique()
        id_map = _sincronizar_ids_tabla_maestra(cursor, nombres)
        df["IdPelicula"] = df["NombrePelicula"].map(id_map)
        agent_log(
            "H3",
            "core/database.py:maestro_sync",
            "tabla_maestra_ids_resolved",
            {"unique_titles": len(nombres), "mapped": len(id_map)},
        )

    # =============================
    # SINCRONIZAR CINEFUENTES (FK)
    # =============================
    try:
        if table_name and table_name.lower().endswith("comscorempamexico") and "IdComscoreFlash" in df.columns:
            ids = df["IdComscoreFlash"].dropna().unique()
            if len(ids) > 0:
                added = _sincronizar_cine_fuentes(cursor, ids)
                agent_log(
                    "H3",
                    "core/database.py:cinefuentes_sync",
                    "cinefuentes_sync_attempt",
                    {"unique_ids": len(ids), "added": added},
                )
                # comprobar si aún faltan claves; si faltan, excluir la columna para evitar FK failure
                missing = []
                for v in ids:
                    cursor.execute("SELECT 1 FROM dbo.CineFuentes WHERE IdComscoreFlash = ?", v)
                    if not cursor.fetchone():
                        missing.append(v)
                if missing:
                    agent_log(
                        "H3",
                        "core/database.py:cinefuentes_sync",
                        "cinefuentes_missing_after_sync",
                        {"missing_count": len(missing), "missing_ids": missing[:20]},
                    )
                    raise ValueError(
                        f"No existen registros de dbo.CineFuentes para los IdComscoreFlash: {missing[:20]}... "
                        "Debe crear los registros padre en dbo.CineFuentes antes de insertar en dbo.ComscoreMPAMexico."
                    )
    except Exception as e:
        agent_log(
            "H3",
            "core/database.py:cinefuentes_sync",
            "cinefuentes_sync_unexpected",
            {"error": str(e)[:500]},
        )
        raise

    tabla_meta = _obtener_metadata_tabla(cursor, table_name)
    print(f"DEBUG: Columnas en tabla {table_name}: {list(tabla_meta.keys())}")
    print(f"DEBUG: Columnas en DataFrame antes de ajuste: {list(df.columns)}")
    
    df, columnas, omitidas = _ajustar_df_para_tabla(df, tabla_meta, exclude_columns)
    
    print(f"DEBUG: Columnas a insertar ({len(columnas)}): {columnas}")
    print(f"DEBUG: Columnas omitidas: {omitidas}")
    
    agent_log(
        "H4",
        "core/database.py:schema_align",
        "df_aligned_to_table_schema",
        {
            "table": table_name,
            "insert_columns": columnas,
            "omitted_columns": omitidas[:30],
        },
    )

    if not columnas:
        print(f"No hay columnas compatibles con {table_name}.")
        cursor.close()
        conn.close()
        return

    cursor.fast_executemany = True
    conn.timeout = 60
    columnas_sql = ",".join(columnas)
    placeholders = ",".join(["?"] * len(columnas))
    query = f"INSERT INTO {table_name} ({columnas_sql}) VALUES ({placeholders})"
    
    print(f"DEBUG: Query SQL: {query}")
    print(f"DEBUG: Número de parámetros esperados: {len(columnas)}")
    print(f"DEBUG: Número de filas a insertar: {len(df)}")

    data = [
        tuple(_sql_value(x) for x in row)
        for row in df.itertuples(index=False, name=None)
    ]
    
    print(f"DEBUG: Tuplas preparadas, primer elemento tiene {len(data[0]) if data else 0} valores")

    batch_size = 10000
    total_rows = len(data)
    batches = (total_rows + batch_size - 1) // batch_size

    try:
        if total_rows > batch_size:
            for batch_index in range(batches):
                start = batch_index * batch_size
                end = min(start + batch_size, total_rows)
                batch = data[start:end]
                print(f"DEBUG: Insertando batch {batch_index + 1}/{batches} ({len(batch)} filas)")
                try:
                    cursor.executemany(query, batch)
                    conn.commit()
                except Exception as batch_exception:
                    print(f"DEBUG: Error en batch {batch_index + 1}/{batches}: {batch_exception}")
                    agent_log(
                        "H4",
                        "core/database.py:executemany_batch_fail",
                        "sql_executemany_batch_failed",
                        {
                            "batch_index": batch_index + 1,
                            "batch_size": len(batch),
                            "error_type": type(batch_exception).__name__,
                            "error": str(batch_exception)[:1000],
                        },
                    )
                    raise
        else:
            cursor.executemany(query, data)
            conn.commit()
    except Exception as e:
        agent_log(
            "H4",
            "core/database.py:executemany_fail",
            "sql_executemany_failed",
            {"error_type": type(e).__name__, "error": str(e)[:500]},
        )
        cursor.close()
        conn.close()
        raise

    agent_log(
        "H3",
        "core/database.py:after_commit",
        "sql_insert_committed",
        {"rows": len(df), "table": table_name},
    )

    cursor.close()
    conn.close()
    print(f"Insertados {len(df)} registros en {table_name}")

    from sqlalchemy import create_engine, text

def ejecutar_sp(connection_string, sp_name):
    """
    Ejecuta una stored procedure en SQL Server.
    
    Args:
        connection_string: Connection string a SQL Server
        sp_name: Nombre de la stored procedure (ej: "SP_CalcularSemanasOracleA1")
    """
    try:
        print(f"\n[DEBUG] Intentando ejecutar SP: {sp_name}")

        # Detectar si se pasó un ODBC style connection string (pyodbc)
        conn_lower = (connection_string or "").lower()
        if "driver=" in conn_lower or "server=" in conn_lower:
            # Convertir a URL para SQLAlchemy usando pyodbc
            from urllib.parse import quote_plus
            odbc_connect = quote_plus(connection_string)
            engine_url = f"mssql+pyodbc:///?odbc_connect={odbc_connect}"
            print(f"[DEBUG] Detectado ODBC connection string, usando URL para SQLAlchemy.")
        else:
            engine_url = connection_string

        print(f"[DEBUG] Engine URL (truncado): {engine_url[-60:]}")

        engine = create_engine(engine_url)

        with engine.begin() as conn:
            print(f"[DEBUG] Conexión establecida, ejecutando: EXEC {sp_name}")
            conn.execute(text(f"EXEC {sp_name}"))

        print(f"✓ SP ejecutado exitosamente: {sp_name}")

    except Exception as e:
        print(f"\n❌ ERROR al ejecutar SP '{sp_name}':")
        print(f"   Tipo de error: {type(e).__name__}")
        print(f"   Mensaje: {str(e)}")
        print(f"   Detalle completo:")
        import traceback
        traceback.print_exc()
        raise
