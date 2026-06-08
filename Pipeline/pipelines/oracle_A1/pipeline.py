from email.mime import text
from core.database import ejecutar_sp
from core.watcher import run_watcher
from core.processor import procesar_archivo
from core.utils import cargar_procesados, guardar_procesado
from core.database import insertar_dataframe_sql
from core.agent_debug import agent_log

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
    # ARCHIVOS PROCESADOS
    # =============================
    procesados = cargar_procesados(processed_log)
    db_cfg = config.get("database", {})
    # region agent log
    agent_log(
        "H2",
        "pipelines/comscore_mexico_flash/pipeline.py:startup",
        "pipeline_startup_db_config",
        {
            "pipeline": config["name"],
            "db_enabled": db_cfg.get("enabled", False),
            "table": db_cfg.get("table"),
            "processed_log_count": len(procesados),
            "watch_folder": watch_folder,
        },
    )
    # endregion

    # =============================
    # CALLBACK
    # =============================
    def callback(path_archivo):

        print(f"\nProcesando archivo: {path_archivo}")

        df = procesar_archivo(
            path_archivo=path_archivo,
            mapping_func=transformar,
            config=config
        )
        # region agent log
        agent_log(
            "H2",
            "pipelines/comscore_mexico_flash/pipeline.py:callback",
            "callback_after_process",
            {"rows": len(df), "cols": len(df.columns)},
        )
        # endregion

        # =============================
        # SQL (CONTROLADO POR CONFIG)
        # =============================
        if config.get("database", {}).get("enabled", False):
            # region agent log
            agent_log(
                "H2",
                "pipelines/comscore_mexico_flash/pipeline.py:sql_branch",
                "sql_insert_branch_entered",
                {"table": config["database"]["table"], "rows": len(df)},
            )
            # endregion
            
            print(f"\n[DEBUG] Verificando FechaOracle antes de insertar:")
            print(f"  - Total registros: {len(df)}")
            print(f"  - Nulos en FechaOracle: {df['FechaOracle'].isna().sum()}")
            print(f"  - Fechas válidas: {(~df['FechaOracle'].isna()).sum()}")
            
            if df['FechaOracle'].isna().sum() == len(df):
                print(f"\n⚠️  ADVERTENCIA: Todos los registros tienen FechaOracle = NULL")
                print(f"   La SP probablemente fallará. Procediendo igual...")
            
            insertar_dataframe_sql(
                df=df,
                table_name=config["database"]["table"],
                connection_string=config["database"]["connection_string"],
                exclude_columns=config["database"].get("exclude_columns"),
            )

            print(f"\n[DEBUG] Inserción completada, procediendo a ejecutar SP...")
            ejecutar_sp(
                config["database"]["connection_string"],
                "SP_CalcularSemanasOracleA1"
            )
        else:
            # region agent log
            agent_log(
                "H2",
                "pipelines/comscore_mexico_flash/pipeline.py:sql_skipped",
                "sql_insert_skipped_disabled",
                {},
            )
            # endregion

    # =============================
    # WATCHER
    # =============================
    print(f"Iniciando pipeline: {config['name']}")
    print(f"Monitoreando carpeta: {watch_folder}")

    run_watcher(
        folder=watch_folder,
        processed_set=procesados,
        callback=callback,
        sleep=sleep_watcher,
        log_func=lambda f: guardar_procesado(processed_log, f),
        file_pattern=config["input"].get("file_pattern", ".csv"),
    )
