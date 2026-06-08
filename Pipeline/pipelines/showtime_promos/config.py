from dotenv import load_dotenv
import os

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

# Variables de entorno con fallback seguro para no romper el pipeline si aún no están seteadas.
SERVER = os.getenv('DB_SERVER', '10.55.55.134\\SQLDEV')
DATABASE = os.getenv('DB_DATABASE', 'Programacion')
UID = os.getenv('DB_UID', 'admin_sql')
PWD = os.getenv('DB_PWD', 'ProgramacionPoderos0*')
watch_folder_PROMOS = os.getenv('SHOWTIME_PROMOS_WATCH_FOLDER') or r'C:\Users\luisev\OneDrive - OPERADORA DE CINEMAS S.A. DE C.V\Documentos\Raw\ShowtimePromos\Promos1'
file_pattern_PROMOS = os.getenv('SHOWTIME_PROMOS_FILE_PATTERN', '.xlsx')
processed_log_PROMOS = os.getenv('SHOWTIME_PROMOS_PROCESSED_LOG') or r'C:\Users\luisev\OneDrive - OPERADORA DE CINEMAS S.A. DE C.V\Documentos\Cinemex_IA\Proyecto inicial\data\data 2026-04\Procesada\showtime_promos.txt'
mapeo_PROMOS = os.getenv('SHOWTIME_PROMOS_MAPEO') or r'C:\Users\luisev\OneDrive - OPERADORA DE CINEMAS S.A. DE C.V\Documentos\Cinemex_IA\Proyecto inicial\notebooks\Pipeline\pipelines\Diccionarios\Mapeo.xlsx'

PIPELINE_CONFIG = {

    "name": "showtime_promos",

    "input": {
        "watch_folder": watch_folder_PROMOS,
        "file_pattern": file_pattern_PROMOS
    },
    "output": {
        "processed_log": processed_log_PROMOS,
    },
    "catalogos": {
              "mapeo": mapeo_PROMOS
    },

    "database": {
        "enabled": True,

        "connection_string": (
            f"DRIVER={{{os.getenv('DB_DRIVER', 'ODBC Driver 17 for SQL Server')}}};"
            f"SERVER={SERVER};"
            f"DATABASE={DATABASE};"
            f"UID={UID};"
            f"PWD={PWD};"
            f"TrustServerCertificate={os.getenv('DB_TRUST_SERVER_CERTIFICATE', 'yes')};"
        ),

        "table": "dbo.SemanalesShowtime",
    },
    "performance": {
    "sleep_watcher": 10
}
}