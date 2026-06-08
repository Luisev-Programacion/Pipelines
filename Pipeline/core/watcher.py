import os
import time

from core.agent_debug import agent_log


def run_watcher(
    folder,
    processed_set,
    callback,
    sleep=10,
    log_func=None,
    stop_when_idle=True,
    file_pattern=".csv.gz",
    max_idle_cycles=None,
):

    idle_cycles = 0
    while True:
        processed_in_cycle = 0
        pat = file_pattern.lower()
        archivos = [
            f for f in os.listdir(folder) if f.lower().endswith(pat)
        ]
        # region agent log
        agent_log(
            "H1",
            "core/watcher.py:scan",
            "watcher_scan",
            {
                "folder": folder,
                "file_pattern": file_pattern,
                "matching_files": archivos,
                "processed_count": len(processed_set),
                "already_processed": [a for a in archivos if a in processed_set],
            },
        )
        # endregion

        for archivo in archivos:
            if archivo in processed_set:
                continue

            full_path = os.path.join(folder, archivo)
            # region agent log
            agent_log(
                "H1",
                "core/watcher.py:before_callback",
                "processing_new_file",
                {"file": archivo, "full_path": full_path},
            )
            # endregion

            try:
                callback(full_path)
                processed_set.add(archivo)
                processed_in_cycle += 1
                if log_func:
                    log_func(archivo)
            except Exception as e:
                print(f"Error procesando {archivo}: {e}")
                # region agent log
                agent_log(
                    "H3",
                    "core/watcher.py:callback_error",
                    "callback_exception",
                    {
                        "file": archivo,
                        "error_type": type(e).__name__,
                        "error": str(e)[:500],
                    },
                )
                # endregion

            print("------ DEBUG -   -----")
            print("Archivos en carpeta:", os.listdir(folder))
            print("Procesados:", processed_set)   
            print("Fin del escaneo")

            for archivo in os.listdir(folder):
                print(f"Evaluando: [{archivo}]")

        if processed_in_cycle == 0:
            idle_cycles += 1
        else:
            idle_cycles = 0

        if stop_when_idle and processed_in_cycle == 0:
            print("No hay archivos nuevos. Finalizando watcher.")
            # region agent log
            agent_log(
                "H1",
                "core/watcher.py:idle_exit",
                "watcher_exit_no_new_files",
                {"folder": folder, "matching_files": archivos},
            )
            # endregion
            break

        if max_idle_cycles is not None and idle_cycles >= max_idle_cycles:
            print(f"No hay archivos nuevos tras {idle_cycles} ciclos. Finalizando watcher.")
            # region agent log
            agent_log(
                "H1",
                "core/watcher.py:idle_exit",
                "watcher_exit_max_idle_cycles",
                {
                    "folder": folder,
                    "matching_files": archivos,
                    "idle_cycles": idle_cycles,
                },
            )
            # endregion
            break

        time.sleep(sleep)
        print("Escaneando carpeta...")
        print("Fin del escaneo")