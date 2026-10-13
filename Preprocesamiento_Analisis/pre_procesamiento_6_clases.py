import pandas as pd
from pathlib import Path

base_dir = Path(__file__).resolve().parent
input_file = Path( r'C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\DATASET\SALIDAD_ACEL_GPS_ENERGIA_FFT_VARIANZA\selecion\8c-FFT + VARIANZA + 50CARAT_selecion.csv')
output_file = Path(r'C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\DATASET\SALIDAD_ACEL_GPS_ENERGIA_FFT_VARIANZA\selecion\6c-FFT + VARIANZA + 50CARAT_selecion.csv')

df = pd.read_csv(input_file)

# 1. Mapeo de estados a 6 clases (0 a 5)
mapeo_estados = {
    0: 0,  # Origen / Destino
    7: 0,  # Origen / Destino (combinado con 0)
    1: 1,  # Caminando a la parada
    2: 2,  # Esperando
    3: 3,  # Ascendiendo
    4: 4,  # Viajando parado
    5: 4,  # Viajando sentado (combinado con 4)
    6: 5   # Descendiendo (remapeado a 5)
}

df['Estado'] = df['Estado'].map(mapeo_estados)

# 2. Cálculo de la energía total wavelet (suma de energía promedio de aproximación y detalles: E = prom² + desv²)
#df['energia'] = (
#    (df['A3_prom']**2 + df['A3_desv']**2) +
#    (df['D1_prom']**2 + df['D1_desv']**2) +
#    (df['D2_prom']**2 + df['D2_desv']**2) +
#    (df['D3_prom']**2 + df['D3_desv']**2)
#)

# 3. Exportar archivo resultante
df.to_csv(output_file, index=False)
print(f"Archivo guardado en: {output_file}")