from dotenv import load_dotenv
import os
load_dotenv()

PIPELINE_CONFIG = {
    "name": "oracle_A1",

    "input": {
        "watch_folder": os.getenv("ORACLE_A1_WATCH_FOLDER", r"C:\Users\luisev\OneDrive - OPERADORA DE CINEMAS S.A. DE C.V\Documentos\Raw\A1\AsisTaquillaCompleto"),
        "file_pattern": os.getenv("ORACLE_A1_FILE_PATTERN", ".csv"),
        "encoding": os.getenv("ORACLE_A1_ENCODING", "utf-8")
    },


    "mapping": {
        "columna_pelicula": "Pelicula",
        "homologar_cadena": True
    },


    "apis": {
        "tmdb": {
            "api_key": os.getenv("APIKEYTMDB"),
            "language": "es-MX",
            "timeout": (5, 20)
        }
    },

    "output": {
        "catalogo_peliculas": os.getenv("ORACLE_A1_CATALOGO_PELICULAS", r"C:\Users\luisev\OneDrive - OPERADORA DE CINEMAS S.A. DE C.V\Documentos\Cinemex_IA\Proyecto inicial\data\data 2026-04\Procesada\catalogo_peliculas.xlsx"),
        "processed_log": os.getenv("ORACLE_A1_PROCESSED_LOG", r"C:\Users\luisev\OneDrive - OPERADORA DE CINEMAS S.A. DE C.V\Documentos\Cinemex_IA\Proyecto inicial\data\data 2026-04\Procesada\oracle_A1.txt"),
        "resultado_excel": os.getenv("ORACLE_A1_RESULTADO_EXCEL", r"C:\Users\luisev\OneDrive - OPERADORA DE CINEMAS S.A. DE C.V\Documentos\Cinemex_IA\Proyecto inicial\data\data 2026-04\Procesada\OUT_A1.xlsx"),
    },

"database": {
    "enabled": True,
    "connection_string": (
        f"DRIVER={{{os.getenv('DB_DRIVER', 'ODBC Driver 17 for SQL Server')}}};"
        f"SERVER={os.getenv('DB_SERVER', '10.55.55.134\\SQLDEV')};"
        f"DATABASE={os.getenv('DB_DATABASE', 'Programacion')};"
        f"UID={os.getenv('DB_UID', 'admin_sql')};"
        f"PWD={os.getenv('DB_PWD', 'ProgramacionPoderos0*')};"
        f"TrustServerCertificate={os.getenv('DB_TRUST_SERVER_CERTIFICATE', 'yes')};"
    ),
    "table": "dbo.OracleA1",
},


"catalogos": {
    "formato": r"C:\Users\luisev\OneDrive - OPERADORA DE CINEMAS S.A. DE C.V\Documentos\Cinemex_IA\Proyecto inicial\notebooks\Pipeline\pipelines\Diccionarios\Catalogo_Eventos.xlsx"
},

    "performance": {
        "sleep_watcher": 10,
        "sleep_api": 0.25,
        "similitud_umbral": 0.8
    }
}

