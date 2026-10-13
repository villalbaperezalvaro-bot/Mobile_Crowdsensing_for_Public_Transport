import os
import pandas as pd


def calcular_estadisticas_velocidad(
    archivo_entrada,
    archivo_salida=r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\salidad_ESTADISTICAS_VELOCIDAD\Dataset__GPS__10.csv",
):
  """Calcula promedio, mínimo, máximo de velocidad y el estado predominante

  por cada ventana temporal (WindowID).
  """
  print(f"Cargando archivo: {archivo_entrada}...")
  df = pd.read_csv(archivo_entrada)

  # 1. Validar presencia de columnas críticas
  if "WindowID" not in df.columns or "Velocidad" not in df.columns:
    print(
        "Error: El archivo CSV debe contener al menos las columnas 'WindowID' y"
        " 'Velocidad'."
    )
    return None

  # 2. Asegurar que Velocidad sea numérico
  df["Velocidad"] = pd.to_numeric(df["Velocidad"], errors="coerce").fillna(0.0)

  print("Calculando características estadísticas por ventana...")

  # 3. Definir agregaciones estadísticas
  dict_agregaciones = {
      "Velocidad_Promedio": ("Velocidad", "mean"),
      "Velocidad_Minimo": ("Velocidad", "min"),
      "Velocidad_Maximo": ("Velocidad", "max"),
  }

  # Obtener el estado más frecuente (moda) de la ventana si la columna existe
  if "Estado" in df.columns:
    dict_agregaciones["Estado"] = (
        "Estado",
        lambda x: x.mode()[0] if not x.mode().empty else x.iloc[0],
    )

  # 4. Agrupar por WindowID
  df_resumen = df.groupby("WindowID").agg(**dict_agregaciones).reset_index()

  # 5. Redondear resultados numéricos a 4 decimales
  cols_numericas = [
      "Velocidad_Promedio",
      "Velocidad_Minimo",
      "Velocidad_Maximo",
  ]
  df_resumen[cols_numericas] = df_resumen[cols_numericas].round(4)

  # 6. Exportar al archivo CSV final
  df_resumen.to_csv(archivo_salida, index=False)

  print("\n¡Proceso completado con éxito!")
  print(f"Archivo generado en: {os.path.abspath(archivo_salida)}")
  print(f"Total de ventanas procesadas: {len(df_resumen)}")

  return df_resumen


if __name__ == "__main__":
  archivo_csv = r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\salidad_ACEL_GPS\Dataset_COMBINADO__10.csv"
 
  df_resultado = calcular_estadisticas_velocidad(archivo_csv)

  if df_resultado is not None:
    print("\nVista previa de las primeras ventanas procesadas:")
    print(df_resultado.head(10))