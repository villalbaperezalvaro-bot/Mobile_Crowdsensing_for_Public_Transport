import pandas as pd


def segmentar_traslape_csv(ruta_csv, ventana_seg, traslape_pct, porc_estado):
  """Segmenta un archivo CSV en ventanas temporales de tamaño fijo (ej. 3s)

  utilizando una frecuencia de muestreo de 50 Hz, ignorando columnas excedentes.
  """
  df = pd.read_csv(ruta_csv)
  df["Timestamp"] = pd.to_datetime(df["Timestamp"])

  # Ordenar cronológicamente por seguridad
  df = df.sort_values("Timestamp").reset_index(drop=True)

  frecuencia_muestreo = 50  # Frecuencia fija a 50 Hz
  ventana_muestras = int(ventana_seg * frecuencia_muestreo)
  if ventana_muestras < 1:
    ventana_muestras = 1

  traslape_muestras = int(ventana_muestras * traslape_pct / 100)
  paso = max(1, ventana_muestras - traslape_muestras)

  ventanas = []
  ventana_id = 1

  # Bucle por bloques de muestras exactas a 50 Hz
  for inicio in range(0, len(df) - ventana_muestras + 1, paso):
    fin = inicio + ventana_muestras
    ventana_df = df.iloc[inicio:fin].copy()

    conteo_estados = ventana_df["Estado"].value_counts()
    if conteo_estados.empty:
      continue

    estado_mayoritario = conteo_estados.idxmax()
    porcentaje_mayoritario = (conteo_estados.max() / ventana_muestras) * 100

    # Solo agregar la ventana si cumple con el porcentaje del estado mayoritario
    if porcentaje_mayoritario >= porc_estado:
      ventana_df["ID_Ventana"] = ventana_id
      ventana_df["Estado_Ventana"] = estado_mayoritario
      ventanas.append(ventana_df)
      ventana_id += 1

  if ventanas:
    df_segmentado = pd.concat(ventanas, ignore_index=True)
  else:
    df_segmentado = pd.DataFrame(
        columns=df.columns.tolist() + ["ID_Ventana", "Estado_Ventana"]
    )

  return df_segmentado