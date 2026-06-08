from dotenv import load_dotenv
import os
load_dotenv()

PIPELINE_CONFIG = {
    "name": "showtime_mexico_peliculas",

    "input": {
        "watch_folder": os.getenv("SHOWTIME_PELICULAS_WATCH_FOLDER", r"C:\Users\luisev\OneDrive - OPERADORA DE CINEMAS S.A. DE C.V\Documentos\Raw\Showtime\ShowtimePeliculas"),
        "file_pattern": os.getenv("SHOWTIME_PELICULAS_FILE_PATTERN", ".xlsx"),
        "encoding": os.getenv("SHOWTIME_PELICULAS_ENCODING", "utf-8")
    },


    "mapping": {
        # Debe coincidir con una columna del DataFrame después de mapping.transformar()
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
        "catalogo_peliculas": os.getenv("SHOWTIME_PELICULAS_CATALOGO_PELICULAS", r"C:\Users\luisev\OneDrive - OPERADORA DE CINEMAS S.A. DE C.V\Documentos\Cinemex_IA\Proyecto inicial\data\data 2026-04\Procesada\catalogo_peliculas.xlsx"),
        "processed_log": os.getenv("SHOWTIME_PELICULAS_PROCESSED_LOG", r"C:\Users\luisev\OneDrive - OPERADORA DE CINEMAS S.A. DE C.V\Documentos\Cinemex_IA\Proyecto inicial\data\data 2026-04\Procesada\showtime_mexico_peliculas.txt"),
        "resultado_excel": os.getenv("SHOWTIME_PELICULAS_RESULTADO_EXCEL", r"C:\Users\luisev\OneDrive - OPERADORA DE CINEMAS S.A. DE C.V\Documentos\Cinemex_IA\Proyecto inicial\data\data 2026-04\Procesada\OUTsHOW.xlsx"),
        "write_excel": os.getenv("SHOWTIME_PELICULAS_WRITE_EXCEL", "False").lower() == "true",
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
    "table": "dbo.ShowtimePeliculas"
},


    "performance": {
        "sleep_watcher": 10,
        "sleep_api": 0.25,
        "similitud_umbral": 0.8
    }
}