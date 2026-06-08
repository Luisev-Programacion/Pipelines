from core.watcher import run_watcher
from core.utils import cargar_procesados, guardar_procesado
from core.database import insertar_dataframe_sql

from .config import PIPELINE_CONFIG
from .mapping import transformar


def run_pipeline():

    config = PIPELINE_CONFIG

    # =============================
    # CONFIG
    # =============================
    watch_folder = config["input"]["watch_folder"]
    processed_log = config["output"]["processed_log"]
    sleep_watcher = config["performance"]["sleep_watcher"]

    # =============================
    # ARCHIVOS YA PROCESADOS
    # =============================
    procesados = cargar_procesados(processed_log)

    # =============================
    # CALLBACK
    # =============================
    def callback(path_archivo):

        print(f"\nProcesando archivo: {path_archivo}")

        try:

            # =============================
            # TRANSFORMACIÓN
            # =============================
            df = transformar(
                path_archivo=path_archivo,
                config=config
            )

            print(
                f"Registros transformados: {len(df)}"
            )

            # =============================
            # SQL SERVER
            # =============================
            if config["database"]["enabled"]:

                insertar_dataframe_sql(
                    df=df,
                    table_name=config["database"]["table"],
                    connection_string=config["database"]["connection_string"]
                )

                print(
                    f"Datos cargados en {config['database']['table']}"
                )

            print("Proceso finalizado OK")

        except Exception as e:

            print(
                f"Error procesando archivo: {e}"
            )

            raise

    # =============================
    # WATCHER
    # =============================
    print(
        f"Iniciando pipeline: {config['name']}"
    )

    print(
        f"Monitoreando carpeta: {watch_folder}"
    )

    run_watcher(
        folder=watch_folder,
        processed_set=procesados,
        callback=callback,
        sleep=sleep_watcher,
        log_func=lambda f: guardar_procesado(
            processed_log,
            f
        ),
        file_pattern=config["input"].get("file_pattern", ".xlsx"),
    )