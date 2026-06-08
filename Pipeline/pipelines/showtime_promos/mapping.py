import pandas as pd
from core.utils import limpiar_valores_nulos
import pandas as pd

CATEGORIAS_PADRE = [
    "Asistencia Pagada",
    "IE",
    "Promociones Taq",
    "Pases",
    "Prepago"
]


def cargar_mapeo(ruta):
    """
    Carga el catálogo de marcaciones.
    """
    df_map = pd.read_excel(ruta)

    return dict(
        zip(
            df_map["Marcacion"].astype(str).str.strip().str.upper(),
            df_map["Etiqueta"].astype(str).str.strip()
        )
    )


def limpiar_valor(valor):

    s_val = str(valor).strip()

    if s_val in [".", "", "nan"] or pd.isna(valor):
        return 0

    if s_val.endswith("."):
        s_val = s_val[:-1]

    try:
        return float(
            pd.to_numeric(
                s_val.replace(",", ""),
                errors="coerce"
            )
        )
    except Exception:
        return 0


def extraer_datos_hoja(df, diccionario_mapeo, nombre_kpi):

    df = df.rename(
        columns={df.columns[0]: "Marcacion"}
    )

    resultados = []

    tipo_actual = "No Identificado"

    for _, row in df.iterrows():

        marcacion_raw = str(
            row["Marcacion"]
        ).strip()

        if marcacion_raw in CATEGORIAS_PADRE:
            tipo_actual = marcacion_raw
            continue

        if marcacion_raw in ["nan", ""]:
            continue

        for col in df.columns[1:]:

            fecha_dt = pd.to_datetime(
                col,
                errors="coerce"
            )

            if pd.isna(fecha_dt):
                continue

            valor_num = limpiar_valor(
                row[col]
            )

            etiqueta = diccionario_mapeo.get(
                marcacion_raw.upper(),
                "Sin Etiqueta"
            )

            resultados.append({
                "Fecha": fecha_dt.normalize(),
                "Marcacion": marcacion_raw,
                "TipoDinamica": tipo_actual,
                "Etiqueta": etiqueta,
                nombre_kpi: valor_num
            })

    return pd.DataFrame(resultados)


def transformar(path_archivo, config):

    print(f"Leyendo archivo: {path_archivo}")

    ruta_mapeo = config["catalogos"]["mapeo"]

    diccionario_mapeo = cargar_mapeo(
        ruta_mapeo
    )

    xls = pd.ExcelFile(path_archivo)

    # ==========================
    # ASISTENCIA
    # ==========================
    df_asistencia = extraer_datos_hoja(
        pd.read_excel(
            xls,
            sheet_name="Asistencia"
        ),
        diccionario_mapeo,
        "Asistencia"
    )

    # ==========================
    # TAQUILLA
    # ==========================
    df_taquilla = extraer_datos_hoja(
        pd.read_excel(
            xls,
            sheet_name="Ingreso de boletos"
        ),
        diccionario_mapeo,
        "Taquilla"
    )

    # ==========================
    # MERGE
    # ==========================
    df_final = pd.merge(
        df_asistencia,
        df_taquilla,
        on=[
            "Fecha",
            "Marcacion",
            "TipoDinamica",
            "Etiqueta"
        ],
        how="outer"
    )

    df_final.fillna(0, inplace=True)

    print(
        f"Registros transformados: {len(df_final)}"
    )

    return df_final