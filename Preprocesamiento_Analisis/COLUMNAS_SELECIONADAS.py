import pandas as pd

# 1. Definir las rutas de los archivos
archivo_entrada = r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\DATASET\SALIDAD_ACEL_GPS_ENERGIA_FFT_VARIANZA\WTD_GPS_ENERGIA_FFT_VARIANZA_50CARATERISTICAS\dataset_unido_10.csv"
archivo_salida =  r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\DATASET\SALIDAD_ACEL_GPS_ENERGIA_FFT_VARIANZA\WTD_GPS_ENERGIA_FFT_VARIANZA_50CARATERISTICAS2\dataset_unido_10.csv"

# 2. Lista exacta de las columnas que deseas conservar
columnas_deseadas = [
    
 'ID_Ventana', 'Estado',
    'Velocidad_prom', 'Velocidad_max', 'Velocidad_min', 'Mag_IQR', 
    'Z_RMS', 'Y_RMS', 'Mag_P75', 'A3_desv', 'Amplitud_FFT_Max', 'Mag_MAD'
    


]
#['A3_desv', 'A3_prom', 'D1_desv', 'D2_desv', 'D3_desv']
# 3. Leer el archivo CSV
print("Cargando archivo CSV...")
df = pd.read_csv(archivo_entrada)

# 4. Verificar que las columnas existan en el archivo para evitar errores
columnas_existentes = [col for col in columnas_deseadas if col in df.columns]

if len(columnas_existentes) < len(columnas_deseadas):
    faltantes = set(columnas_deseadas) - set(columnas_existentes)
    print(f"Advertencia: Las siguientes columnas no se encontraron en el CSV: {faltantes}")

# 5. Filtrar el DataFrame conservando solo las columnas deseadas
df_filtrado = df[columnas_existentes]

# 6. Guardar el nuevo CSV filtrado
df_filtrado.to_csv(archivo_salida, index=False)

print(f"¡Listo! Archivo filtrado con éxito. Se conservaron {df_filtrado.shape[1]} columnas y {df_filtrado.shape[0]} filas.")
print(f"Guardado en: {archivo_salida}")