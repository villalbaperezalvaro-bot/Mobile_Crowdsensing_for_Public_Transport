import os
import numpy as np
import pandas as pd


def procesar_giroscopio_alineado(
    archivo_acel_referencia,
    archivo_giro,
    salida_csv=r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\salidad_GIROSCOPIO_ALINEADO\Dataset_GIRO_ALINEADO.csv",
):
  """Alinea el archivo del giroscopio tomando como plantilla temporal exacta el

  Dataset Combinado de referencia (Acelerómetro + GPS), heredando el Timestamp,
  WindowID, Marca_Ventana y Estado.
  """
  # 1. Cargar datasets
  print("Leyendo archivos...")
  df_ref = pd.read_csv(archivo_acel_referencia)
  df_giro = pd.read_csv(archivo_giro)

  # 2. Convertir Timestamp a Datetime y ordenar cronológicamente
  df_ref["Timestamp"] = pd.to_datetime(df_ref["Timestamp"])
  df_giro["Timestamp"] = pd.to_datetime(df_giro["Timestamp"])

  df_ref = df_ref.sort_values("Timestamp").reset_index(drop=True)
  df_giro = df_giro.sort_values("Timestamp").reset_index(drop=True)

  # 3. Excluir 'Estado' del giroscopio para evitar duplicidad o sufijos _x/_y (usamos el Estado de referencia)
  cols_giro = [c for c in df_giro.columns if c != "Estado"]

  # 4. Sincronización exacta usando merge_asof (dirección al más cercano)
  print("Sincronizando registros temporales...")
  cols_base_ref = ["Timestamp", "Estado", "WindowID", "Marca_Ventana"]
  cols_existentes_ref = [c for c in cols_base_ref if c in df_ref.columns]

  df_merged = pd.merge_asof(
      df_ref[cols_existentes_ref],
      df_giro[cols_giro],
      on="Timestamp",
      direction="nearest",
  )

  # 5. Detección y normalización dinámica de los ejes del Giroscopio (GyroX/GiroX)
  ejes_giro = []
  for c in df_merged.columns:
    if c.lower() in [
        "gyrox",
        "gyroy",
        "gyroz",
        "girox",
        "giroy",
        "giroz",
        "x",
        "y",
        "z",
    ] and c not in [
        "Timestamp",
        "Estado",
        "WindowID",
        "Marca_Ventana",
    ]:
      ejes_giro.append(c)

  # 6. Rellenar posibles valores nulos en lecturas de giroscopio
  if ejes_giro:
    df_merged[ejes_giro] = df_merged[ejes_giro].fillna(0.0)

  # 7. Definir orden final de columnas
  columnas_ordenadas = [
      "Timestamp",
      "GyroX",
      "GyroY",
      "GyroZ",
      "GiroX",
      "GiroY",
      "GiroZ",
      "Estado",
      "WindowID",
      "Marca_Ventana",
  ]

  cols_finales = [c for c in columnas_ordenadas if c in df_merged.columns]

  # Incluir cualquier columna extra que viniera en el giroscopio original
  for c in df_merged.columns:
    if c not in cols_finales:
      cols_finales.append(c)

  dataset_final = df_merged[cols_finales]

  # 8. Guardar archivo CSV
  os.makedirs(os.path.dirname(salida_csv), exist_ok=True)
  dataset_final.to_csv(salida_csv, index=False)

  print("--------------------------------------------------")
  print("¡Alineación del Giroscopio completada con éxito!")
  print(f"Archivo guardado en: {salida_csv}")
  print(f"Timestamp Inicio real: {dataset_final['Timestamp'].iloc[0]}")
  print(f"Timestamp Fin real:    {dataset_final['Timestamp'].iloc[-1]}")
  print(f"Total de registros:    {len(dataset_final)}")
  print(f"Total de Ventanas:     {dataset_final['WindowID'].nunique()}")
  print("--------------------------------------------------")

  return dataset_final


if __name__ == "__main__":
  # Rutas a tus archivos de prueba
  archivo_acel_referencia = r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\salidad_ACEL_GPS\Dataset_COMBINADO__7.csv"
  archivo_giro = r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\datos\7\giro_20251205_152619__1764969979364.csv_1764973967.csv"

  df_resultado = procesar_giroscopio_alineado(
      archivo_acel_referencia, archivo_giro
  )