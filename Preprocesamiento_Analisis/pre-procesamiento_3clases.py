import pandas as pd
from pathlib import Path

# __file__ es .../shazam_camiones/src/pre-procesamiento_6clases.py
# .resolve().parent te deja en /src/
# un segundo .parent te sube a la raíz del proyecto (.../shazam_camiones/)
project_root = Path(__file__).resolve().parent.parent

# Rutas relativas a la raíz de tu proyecto
# NOTA: Verifica si las carpetas se llaman "salida_" o "salidad_"
input_file = Path(r'C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\DATASET\SALIDAD_ACEL_GPS_ENERGIA_FFT_VARIANZA\WTD_GPS_ENERGIA_FFT\caracteristicas_completas_TWD + ENERGIA + GPS + FFT_10.csv')
output_file = Path(r'C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\DATASET\SALIDAD_ACEL_GPS_ENERGIA_FFT_VARIANZA\WTD_GPS_ENERGIA_FFT\3c-caracteristicas_completas_TWD + ENERGIA + GPS + FFT_10.csv')

# Asegurarse de que la carpeta de salida exista antes de guardar, para evitar otro error
output_file.parent.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(input_file)

# 1. Mapeo de estados a 6 clases (0 a 5)
mapeo_estados = {
    0: 0,  # Origen / Destino / Caminando a la parada
    7: 0,  # Origen / Destino / Caminando a la parada (combinado con 0)
    1: 0,  # Origen / Destino / Caminando a la parada (combinado con 0)    
    3: 1,  # Ascendiendo          Acendiendo / Desendiendo / Viajando (P/S) (combinado con 1)
    4: 1,  # Viajando parado      Acendiendo / Desendiendo / Viajando (P/S) (combinado con 1)
    5: 1,  # Viajando sentado     Acendiendo / Desendiendo / Viajando (P/S) (combinado con 1)
    6: 1,  # Descendiendo         Acendiendo / Desendiendo / Viajando (P/S) (combinado con 1)
    2: 2   # Esperando           
}

df['Estado'] = df['Estado'].map(mapeo_estados)

# 2. Cálculo de la energía total wavelet 
#df['energia'] = (
  #  (df['A3_prom']**2 + df['A3_desv']**2) +
 #   (df['D1_prom']**2 + df['D1_desv']**2) +
   # (df['D2_prom']**2 + df['D2_desv']**2) +
    #(df['D3_prom']**2 + df['D3_desv']**2)
#)

# 3. Exportar archivo resultante
df.to_csv(output_file, index=False)
print(f"Archivo guardado en: {output_file}")