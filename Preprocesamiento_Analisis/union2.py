import numpy as np
import pandas as pd


def procesar_ventanas_por_tiempo(
    archivo_acel,
    archivo_gps,
    salida_csv=r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\salidad_ACEL_GPS\Dataset_COMBINADO_3s.csv",
):
  # 1. Cargar archivos de datos
  df_acel = pd.read_csv(archivo_acel)
  df_gps = pd.read_csv(archivo_gps)

  # 2. Convertir Timestamp a Datetime y ordenar cronológicamente
  df_acel["Timestamp"] = pd.to_datetime(df_acel["Timestamp"])
  df_gps["Timestamp"] = pd.to_datetime(df_gps["Timestamp"])

  df_acel = df_acel.sort_values("Timestamp").reset_index(drop=True)
  df_gps = df_gps.sort_values("Timestamp").reset_index(drop=True)

  # 3. Determinar el tiempo de solapamiento en el que AMBOS sensores tienen datos
  t_start = max(df_acel["Timestamp"].min(), df_gps["Timestamp"].min())
  t_end = min(df_acel["Timestamp"].max(), df_gps["Timestamp"].max())

  # 4. Filtrar al rango común
  df_acel = df_acel[
      (df_acel["Timestamp"] >= t_start) & (df_acel["Timestamp"] <= t_end)
  ].reset_index(drop=True)
  df_gps = df_gps[
      (df_gps["Timestamp"] >= t_start) & (df_gps["Timestamp"] <= t_end)
  ].reset_index(drop=True)

  # 5. Seleccionar columnas del GPS (excluyendo 'Estado')
  cols_gps = [c for c in df_gps.columns if c != "Estado"]

  # 6. Sincronización temporal con merge_asof
  df_merged = pd.merge_asof(
      df_acel, df_gps[cols_gps], on="Timestamp", direction="nearest"
  )

  # Rellenar nulos numéricos del GPS
  cols_numericas_gps = [c for c in cols_gps if c != "Timestamp"]
  df_merged[cols_numericas_gps] = df_merged[cols_numericas_gps].fillna(0.0)

  # 7. Segmentación basada en ventanas de tiempo real de 3 segundos
  ventanas = []
  window_id = 0

  # Agrupamos por bloques de 3 segundos usando el Timestamp del acelerómetro sincronizado
  for _, group in df_merged.groupby(
      pd.Grouper(key="Timestamp", freq="3s", origin="start")
  ):
    if len(group) == 0:
      continue

    window_data = group.copy()
    window_data["WindowID"] = window_id

    # Marcar Inicio y Fin dentro de este bloque temporal de 3s
    marcas = [""] * len(window_data)
    marcas[0] = "Inicio"
    marcas[-1] = "Fin"
    window_data["Marca_Ventana"] = marcas

    ventanas.append(window_data)
    window_id += 1

  # 8. Concatenar y exportar resultado final
  if ventanas:
    dataset_final = pd.concat(ventanas, ignore_index=True)

    columnas_ordenadas = [
        "Timestamp",
        "AccelX",
        "AccelY",
        "AccelZ",
        "Latitud",
        "Longitud",
        "Altitud",
        "Precision",
        "Velocidad",
        "Estado",
        "WindowID",
        "Marca_Ventana",
    ]
    cols_existentes = [
        c for c in columnas_ordenadas if c in dataset_final.columns
    ]
    dataset_final = dataset_final[cols_existentes]

    dataset_final.to_csv(salida_csv, index=False)
    print(
        f"Alineación temporal exitosa. Inicio real en común: {df_merged['Timestamp'].iloc[0]}"
    )
    print(
        f"Total de ventanas de 3s generadas: {window_id} | Total de registros:"
        f" {len(dataset_final)}"
    )
    return dataset_final
  else:
    print("Error: No se pudieron generar ventanas en el rango de tiempo.")
    return None


if __name__ == "__main__":
  archivo_acel = r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\datos\10\acel_20251211_095629_u99_1765468589296.csv_1765476114.csv"
  archivo_gps = r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\datos\10\gps_20251211_095629_u99_1765468589296.csv_1765476112.csv"

  df_resultado = procesar_ventanas_por_tiempo(archivo_acel, archivo_gps)