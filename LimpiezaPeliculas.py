import re
import pandas as pd
from sqlalchemy import create_engine, text
from rapidfuzz import fuzz, process

# ==========================================
# 1. CONFIGURACIÓN DE CONEXIÓN CON SQLALCHEMY
# ==========================================
# Ajusta estas variables con tus datos de SQL Server
DB_NAME = "Programacion"  # Cambia por el nombre real de tu Base de Datos
SERVER = "10.55.55.134\\SQLDEV" # Tu IP de desarrollo o localhost
USER = "admin_sql"
PASSWORD = "ProgramacionPoderos0*"


# Creamos la URL de conexión de confianza para SQLAlchemy y pyodbc
connection_url = f"mssql+pyodbc://{USER}:{PASSWORD}@{SERVER}/{DB_NAME}?driver=ODBC+Driver+17+for+SQL+Server"
engine = create_engine(connection_url)

# ==========================================
# 2. FUNCIÓN DE LIMPIEZA Y NORMALIZACIÓN
# ==========================================
def normalizar_titulo(titulo):
    if not titulo: 
        return ""
    titulo = str(titulo).upper()
    
    # Remover marcas de reestreno (Ej: RE26, RE 26, REESTRENO)
    titulo = re.sub(r'\bRE\s*\d{2}\b', '', titulo)
    titulo = re.sub(r'\bREESTRENO\b', '', titulo)
    
    # Remover artículos al inicio en español y sufijos/artículos en inglés por si acaso
    titulo = re.sub(r',?\s+\bTHE\b$', '', titulo)
    titulo = re.sub(r'^\bTHE\b\s+|^\bLA\b\s+|^\bEL\b\s+|^\bLOS\b\s+|^\bLAS\b\s+', '', titulo)
    
    # Limpiar palabras ruidosas de formato comunes en cine
    titulo = titulo.replace("LA PELICULA", "").replace("MOVIE", "")
    
    # Homologar números romanos comunes para secuelas (Mortal Kombat II -> Mortal Kombat 2)
    titulo = re.sub(r'\bII\b', '2', titulo)
    titulo = re.sub(r'\bIII\b', '3', titulo)
    
    # Quitar caracteres especiales y estandarizar espacios en blanco
    titulo = re.sub(r'[^\w\s]', '', titulo)
    return " ".join(titulo.split())

# ==========================================
# 3. PROCESO PRINCIPAL (ETL CONSOLIDADO)
# ==========================================
def ejecutar_consolidacion():
    print("🔌 Conectando a SQL Server vía SQLAlchemy...")
    
    try:
        with engine.connect() as conn:
            
            # A. EXTRAER: Leer ambas tablas de la base de datos
            print("📖 Leyendo tablas de la base de datos...")
            
            # 🌟 EXTRAEMOS: id, nombre_pelicula (nombre crudo) y titulo_es (español)
            # REEMPLAZA 'TablaMaestraPeliculas' por el nombre real de tu tabla actual con duplicados
            query_actual = text(f"SELECT IdPelicula AS id, NombrePelicula AS nombre_pelicula, titulo_es FROM {DB_NAME}.dbo.TablaMaestraPeliculas")
            df_actual = pd.read_sql(query_actual, conn)
            
            query_nueva = text(f"SELECT nombre_fuente, id_tmdb_definitivo, nombre_oficial FROM {DB_NAME}.dbo.Dim_Peliculas_Consolidada")
            df_nueva = pd.read_sql(query_nueva, conn)
            
            # B. FILTRAR: Identificar deltas (solo registros de origen que no se hayan mapeado)
            nuevos_registros = df_actual[~df_actual['nombre_pelicula'].isin(df_nueva['nombre_fuente'])].copy()
            
            if nuevos_registros.empty:
                print("✅ Dim_Peliculas_Consolidada ya está al día. No hay registros nuevos que procesar.")
                return
                
            print(f"🧠 Procesando {len(nuevos_registros)} registros nuevos basándose en el campo 'titulo_es'...")
            
            # Crear columna auxiliar en memoria con el texto limpio de los nombres oficiales ya guardados
            df_nueva['nombre_norm'] = df_nueva['nombre_oficial'].apply(normalizar_titulo)
            
            registros_a_cargar = [] # Almacenará diccionarios para la carga masiva

            # C. TRANSFORMAR: Aplicar lógica difusa utilizando el título en español
            for _, fila in nuevos_registros.iterrows():
                nombre_crudo = fila['nombre_pelicula']  # Se conserva intacto para ser la Primary Key de enlace
                id_original = int(fila['id'])
                titulo_espanol = fila['titulo_es']
                
                # Si por algún error de la fuente el campo 'titulo_es' viene vacío, respaldamos con el nombre crudo
                if not titulo_espanol:
                    titulo_espanol = nombre_crudo
                
                # 🌟 NORMALIZAMOS el título en español en lugar del inglés
                nombre_limpio = normalizar_titulo(titulo_espanol) 
                
                # Caso base: Si la tabla nueva está vacía en su primera corrida histórica
                if df_nueva.empty:
                    df_nueva = pd.DataFrame([{
                        'nombre_fuente': nombre_crudo, 
                        'id_tmdb_definitivo': id_original, 
                        'nombre_oficial': titulo_espanol, 
                        'nombre_norm': nombre_limpio
                    }])
                    registros_a_cargar.append({
                        "nombre_fuente": nombre_crudo, 
                        "id_tmdb_definitivo": id_original, 
                        "nombre_oficial": titulo_espanol
                    })
                    continue
                
                # Comparación difusa usando Token Sort Ratio (ignora orden de palabras)
                match = process.extractOne(nombre_limpio, df_nueva['nombre_norm'], scorer=fuzz.token_sort_ratio)
                
                # Si el título en español se parece en un 85% o más a uno existente, se unifican
                if match and match[1] >= 85:
                    idx_match = match[2]
                    id_definitivo = int(df_nueva.iloc[idx_match]['id_tmdb_definitivo'])
                    nombre_oficial = df_nueva.iloc[idx_match]['nombre_oficial']
                    print(f"🔗 Vinculado: '{nombre_crudo}' (ES: {titulo_espanol}) ➔ Mapeado a '{nombre_oficial}' (ID: {id_definitivo})")
                else:
                    # Si no encuentra similitud, es una nueva película maestra
                    id_definitivo = id_original
                    nombre_oficial = titulo_espanol
                    print(f"✨ Nueva película detectada: '{nombre_crudo}' (ES: {nombre_oficial}) (ID: {id_definitivo})")
                    
                    # Actualizar el DataFrame en memoria para que sirva de referencia inmediata en el bucle
                    nueva_fila = pd.DataFrame([{
                        'nombre_fuente': nombre_crudo, 
                        'id_tmdb_definitivo': id_definitivo, 
                        'nombre_oficial': nombre_oficial, 
                        'nombre_norm': nombre_limpio
                    }])
                    df_nueva = pd.concat([df_nueva, nueva_fila], ignore_index=True)
                    
                registros_a_cargar.append({
                    "nombre_fuente": nombre_crudo, 
                    "id_tmdb_definitivo": id_definitivo, 
                    "nombre_oficial": nombre_oficial
                })
            
            # D. CARGAR: Inserción por mapeo masivo eficiente
            if registros_a_cargar:
                print(f"📥 Insertando {len(registros_a_cargar)} registros curados en Dim_Peliculas_Consolidada...")
                
                insert_query = text(f"""
                    INSERT INTO {DB_NAME}.dbo.Dim_Peliculas_Consolidada (nombre_fuente, id_tmdb_definitivo, nombre_oficial)
                    VALUES (:nombre_fuente, :id_tmdb_definitivo, :nombre_oficial)
                """)
                
                conn.execute(insert_query, registros_a_cargar)
                conn.commit()
                print("🚀 ¡Carga e integración masiva completada con éxito!")
                
    except Exception as e:
        print(f"❌ Error durante la ejecución del proceso: {str(e)}")
    finally:
        print("🔌 Conexiones de base de datos cerradas de forma segura.")

if __name__ == "__main__":
    ejecutar_consolidacion()

