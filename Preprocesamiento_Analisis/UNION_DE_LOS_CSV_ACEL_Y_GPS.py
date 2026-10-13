import numpy as np
import pandas as pd


def procesar_ventanas_alineadas(
    archivo_acel,
    archivo_gps,
    salida_csv=r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\DATASET\SALIDAD_ACEL_GPS_ENERGIA_FFT_VARIANZA\prueba union 50 c - FFT\Dataset_COMBINADO__1.csv",
):
  # 1. Cargar archivos de datos
  df_acel = pd.read_csv(archivo_acel)
  df_gps = pd.read_csv(archivo_gps)

  # 2. Convertir Timestamp a Datetime y ordenar cronológicamente
  df_acel["Timestamp"] = pd.to_datetime(df_acel["Timestamp"])
  df_gps["Timestamp"] = pd.to_datetime(df_gps["Timestamp"])

  df_acel = df_acel.sort_values("Timestamp").reset_index(drop=True)
  df_gps = df_gps.sort_values("Timestamp").reset_index(drop=True)

  # 3. Determinar el tiempo de inicio y fin en el que AMBOS sensores tienen datos (solapamiento)
  t_start = max(df_acel["Timestamp"].min(), df_gps["Timestamp"].min())
  t_end = min(df_acel["Timestamp"].max(), df_gps["Timestamp"].max())

  # 4. Descartar datos previos a t_start y posteriores a t_end
  df_acel = df_acel[
      (df_acel["Timestamp"] >= t_start) & (df_acel["Timestamp"] <= t_end)
  ].reset_index(drop=True)
  df_gps = df_gps[
      (df_gps["Timestamp"] >= t_start) & (df_gps["Timestamp"] <= t_end)
  ].reset_index(drop=True)

  # 5. Seleccionar columnas del GPS (excluyendo 'Estado' para evitar duplicar con el Acelerómetro)
  cols_gps = [c for c in df_gps.columns if c != "Estado"]

  # 6. Sincronización temporal con merge_asof
  df_merged = pd.merge_asof(
      df_acel, df_gps[cols_gps], on="Timestamp", direction="nearest"
  )

  # Rellenar posibles nulos numéricos del GPS
  cols_numericas_gps = [c for c in cols_gps if c != "Timestamp"]
  df_merged[cols_numericas_gps] = df_merged[cols_numericas_gps].fillna(0.0)

  # 7. Segmentación en ventanas de 3 segundos (150 muestras)
  muestras_por_ventana = 150
  ventanas = []
  window_id = 0
  total_filas = len(df_merged)

  for start_idx in range(
      0, total_filas - muestras_por_ventana + 1, muestras_por_ventana
  ):
    window_data = df_merged.iloc[
        start_idx : start_idx + muestras_por_ventana
    ].copy()
    window_data["WindowID"] = window_id

    # Marcar Inicio y Fin de la ventana
    marcas = [""] * muestras_por_ventana
    marcas[0] = "Inicio"
    marcas[-1] = "Fin"
    window_data["Marca_Ventana"] = marcas

    ventanas.append(window_data)
    window_id += 1

  # 8. Concatenar y exportar resultado final
  if ventanas:
    dataset_final = pd.concat(ventanas, ignore_index=True)

    # Orden predefinido de columnas
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
        f"Alineación exitosa. Inicio real en común: {df_merged['Timestamp'].iloc[0]}"
    )
    print(
        f"Total de ventanas generadas: {window_id} | Total de registros:"
        f" {len(dataset_final)}"
    )
    return dataset_final
  else:
    print("Error: Los rangos de tiempo de los archivos no coinciden.")
    return None


if __name__ == "__main__":
  archivo_acel = r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\DATASET\SALIDAD_ACEL_GPS_ENERGIA_FFT_VARIANZA\SALIDAD_2_ACEL_GPS_ENERGIA_FFT_VARIANZA\caracteristicas_completas_TWD + ENERGIA + GPS + FFT_1.csv"
  archivo_gps =  r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\DATASET\SALIDAD_ACEL_GPS_ENERGIA_FFT_VARIANZA\50 carateristicas\metricas_50_xyz_1-selecion.csv"

  df_resultado = procesar_ventanas_alineadas(archivo_acel, archivo_gps)