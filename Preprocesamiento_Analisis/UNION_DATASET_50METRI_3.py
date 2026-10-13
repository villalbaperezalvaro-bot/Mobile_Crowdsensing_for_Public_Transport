import pandas as pd

# 1. Definir los nombres de los archivos
archivo_1 = r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\DATASET\SALIDAD_ACEL_GPS_ENERGIA_FFT_VARIANZA\WTD_GPS_ENERGIA_FFT_VARIANZA\caracteristicas_completas_TWD + ENERGIA + GPS + FFT_10.csv"
archivo_2 = r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\DATASET\SALIDAD_ACEL_GPS_ENERGIA_FFT_VARIANZA\50 carateristicas\metricas_50_xyz_10.csv"
archivo_salida = r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\DATASET\SALIDAD_ACEL_GPS_ENERGIA_FFT_VARIANZA\WTD_GPS_ENERGIA_FFT_VARIANZA_50CARATERISTICAS\dataset_unido_10.csv"

# 2. Cargar los archivos
print("Cargando archivos...")
df1 = pd.read_csv(archivo_1)
df2 = pd.read_csv(archivo_2)

# 3. Corregir el desfase del ID_Ventana
# Como df2 empieza en 0 y df1 empieza en 1, le sumamos 1 a todo df2
print("Alineando ID_Ventana (sumando 1 al segundo archivo)...")
df2['ID_Ventana'] = df2['ID_Ventana'] + 1

# 4. Unir los DataFrames
# Ahora que los IDs coinciden (ambos empiezan en 1), los unimos sin duplicar 'Estado' ni 'ID_Ventana'
df_unido = pd.merge(df1, df2, on=['ID_Ventana', 'Estado'], how='inner')

# 5. Guardar y verificar
print(f"Dimensiones después de unir: {df_unido.shape}")
df_unido.to_csv(archivo_salida, index=False)
print(f"¡Éxito! Archivo guardado como: '{archivo_salida}'")