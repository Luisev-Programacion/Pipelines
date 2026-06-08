from dotenv import load_dotenv
import os
load_dotenv()

PIPELINE_CONFIG = {
    "name": "comscore_mexico_flash",

    "input": {
        "watch_folder": os.getenv("COMSCORE_WATCH_FOLDER", r"C:\Users\luisev\OneDrive - OPERADORA DE CINEMAS S.A. DE C.V\Documentos\Raw\Comscore\ComscoreFlash"),
        "file_pattern": os.getenv("COMSCORE_FILE_PATTERN", ".xlsx"),
        "encoding": os.getenv("COMSCORE_ENCODING", "utf-8")
    },


    "mapping": {
        "columna_pelicula": "NombrePelicula",
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
        "catalogo_peliculas": os.getenv("COMSCORE_CATALOGO_PELICULAS", r"C:\Users\luisev\OneDrive - OPERADORA DE CINEMAS S.A. DE C.V\Documentos\Cinemex_IA\Proyecto inicial\data\data 2026-04\Procesada\catalogo_peliculas.xlsx"),
        "processed_log": os.getenv("COMSCORE_PROCESSED_LOG", r"C:\Users\luisev\OneDrive - OPERADORA DE CINEMAS S.A. DE C.V\Documentos\Cinemex_IA\Proyecto inicial\data\data 2026-04\Procesada\comscore_mexico_flash.txt"),
        "resultado_excel": os.getenv("COMSCORE_RESULTADO_EXCEL", r"C:\Users\luisev\OneDrive - OPERADORA DE CINEMAS S.A. DE C.V\Documentos\Cinemex_IA\Proyecto inicial\data\data 2026-04\Procesada\OUT.xlsx"),
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
    "table": "dbo.ComscoreMPAMexico",
},


    "performance": {
        "sleep_watcher": 10,
        "sleep_api": 0.25,
        "similitud_umbral": 0.8
    }
}