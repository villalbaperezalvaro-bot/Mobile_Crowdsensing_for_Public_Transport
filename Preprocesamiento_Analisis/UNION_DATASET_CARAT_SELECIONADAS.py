import pandas as pd

# 1. Definir los nombres de los archivos
archivo_1 = r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\DATASET\SALIDAD_ACEL_GPS_ENERGIA_FFT_VARIANZA\SALIDAD_2_ACEL_GPS_ENERGIA_FFT_VARIANZA\caracteristicas_completas_TWD + ENERGIA + GPS + FFT_2.csv"
archivo_2 = r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\DATASET\SALIDAD_ACEL_GPS_ENERGIA_FFT_VARIANZA\50 carateristicas\metricas_50_xyz_2-selecion.csv"
archivo_salida = r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\DATASET\SALIDAD_ACEL_GPS_ENERGIA_FFT_VARIANZA\prueba union 50 c - FFT\Dataset_COMBINADO__2.csv"

# 2. Cargar los archivos en DataFrames de Pandas
print("Cargando archivos...")
df1 = pd.read_csv(archivo_1)
df2 = pd.read_csv(archivo_2)

print(f"Dimensiones originales - Archivo 1: {df1.shape} | Archivo 2: {df2.shape}")

# 3. Unir los DataFrames (Join por columnas)
# Usamos 'ID_Ventana' y 'Estado' como las llaves para que no se dupliquen.
# 'how="inner"' asegura que solo se unan las filas que coincidan perfectamente en ambos.
df_unido = pd.merge(df1, df2, on=['ID_Ventana', 'Estado'], how='inner')

# 4. Verificar el resultado
print(f"Dimensiones después de unir: {df_unido.shape}")
print("\nColumnas del nuevo archivo:")
for col in df_unido.columns:
    print(f" - {col}")

# 5. Guardar el resultado en un nuevo archivo CSV
df_unido.to_csv(archivo_salida, index=False)
print(f"\n¡Éxito! Archivo guardado como: '{archivo_salida}'")