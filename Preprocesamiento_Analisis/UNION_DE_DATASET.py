import pandas as pd

# 1. Definir la lista de archivos a unir
# Puedes agregar todos los archivos que necesites separados por comas
archivos = [
    r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\DATASET\SALIDAD_ACEL_GPS_ENERGIA_FFT_VARIANZA\WTD_GPS_ENERGIA_FFT_VARIANZA_50CARATERISTICAS\dataset_unido_1.csv",
    r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\DATASET\SALIDAD_ACEL_GPS_ENERGIA_FFT_VARIANZA\WTD_GPS_ENERGIA_FFT_VARIANZA_50CARATERISTICAS\dataset_unido_2.csv",
    r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\DATASET\SALIDAD_ACEL_GPS_ENERGIA_FFT_VARIANZA\WTD_GPS_ENERGIA_FFT_VARIANZA_50CARATERISTICAS\dataset_unido_3.csv",
    r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\DATASET\SALIDAD_ACEL_GPS_ENERGIA_FFT_VARIANZA\WTD_GPS_ENERGIA_FFT_VARIANZA_50CARATERISTICAS\dataset_unido_4.csv",
    r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\DATASET\SALIDAD_ACEL_GPS_ENERGIA_FFT_VARIANZA\WTD_GPS_ENERGIA_FFT_VARIANZA_50CARATERISTICAS\dataset_unido_5.csv",
    r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\DATASET\SALIDAD_ACEL_GPS_ENERGIA_FFT_VARIANZA\WTD_GPS_ENERGIA_FFT_VARIANZA_50CARATERISTICAS\dataset_unido_6.csv",
    r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\DATASET\SALIDAD_ACEL_GPS_ENERGIA_FFT_VARIANZA\WTD_GPS_ENERGIA_FFT_VARIANZA_50CARATERISTICAS\dataset_unido_7.csv",
    r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\DATASET\SALIDAD_ACEL_GPS_ENERGIA_FFT_VARIANZA\WTD_GPS_ENERGIA_FFT_VARIANZA_50CARATERISTICAS\dataset_unido_8.csv",
    r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\DATASET\SALIDAD_ACEL_GPS_ENERGIA_FFT_VARIANZA\WTD_GPS_ENERGIA_FFT_VARIANZA_50CARATERISTICAS\dataset_unido_9.csv",
    r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\DATASET\SALIDAD_ACEL_GPS_ENERGIA_FFT_VARIANZA\WTD_GPS_ENERGIA_FFT_VARIANZA_50CARATERISTICAS\dataset_unido_10.csv"

]

archivo_salida = r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\DATASET\SALIDAD_ACEL_GPS_ENERGIA_FFT_VARIANZA\selecion\8c-FFT + VARIANZA + 50CARAT.csv"

# 2. Leer y almacenar todos los DataFrames en una lista
print("Leyendo los archivos...")
lista_dfs = []

for archivo in archivos:
    print(f"Cargando: {archivo}")
    df = pd.read_csv(archivo)
    lista_dfs.append(df)

# 3. Unir (concatenar) todos los DataFrames de la lista
# Se unirán exactamente en el orden en que los pusiste en la lista de arriba
print("Uniendo los datos...")
df_unido = pd.concat(lista_dfs, ignore_index=True)

# 4. Guardar el resultado en un nuevo archivo CSV
df_unido.to_csv(archivo_salida, index=False)

print(f"¡Listo! {len(archivos)} archivos unidos con éxito. El resultado se guardó en:\n{archivo_salida}")