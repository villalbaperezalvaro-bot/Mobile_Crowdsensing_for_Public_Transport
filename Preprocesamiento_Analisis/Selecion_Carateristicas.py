import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import RFE, SelectKBest, f_classif

# 1. Cargar el dataset completo (100% de características)
archivo_entrada = r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\DATASET\SALIDAD_ACEL_GPS_ENERGIA_FFT_VARIANZA\selecion\6c-FFT.csv"
archivo_salida_reducido = r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\DATASET\SALIDAD_ACEL_GPS_ENERGIA_FFT_VARIANZA\selecion\6c-FFT_selecion.csv"

df = pd.read_csv(archivo_entrada)

# 2. Separar Metadatos, Variables (X) y Etiqueta (y)
metadatos = df[['ID_Ventana', 'Estado']]
X = df.drop(columns=['ID_Ventana', 'Estado'])
y = df['Estado']

print(f"Número total de características iniciales: {X.shape[1]}")

# =========================================================================
# MÉTODO 1: IMPORTANCIA BASADA EN RANDOM FOREST (Embedded Method)
# =========================================================================
modelo_rf = RandomForestClassifier(n_estimators=100, random_state=42)
modelo_rf.fit(X, y)

# Obtener ranking de relevancia
importancias = pd.Series(modelo_rf.feature_importances_, index=X.columns).sort_values(ascending=False)

print("\n--- Ranking de Importancia de Características ---")
for i, (col, imp) in enumerate(importancias.items(), 1):
    print(f"{i:02d}. {col:<15}: {imp:.4f}")

# =========================================================================
# SELECCIÓN DEL SUBCONJUNTO MÁS SIGNIFICATIVO (Ejemplo: Top K características)
# =========================================================================
K_CARACTERISTICAS = 10  # Cambiar al número deseado (ej. 10 de 70)

# Seleccionar los nombres de las K mejores características
top_caracteristicas = importancias.head(K_CARACTERISTICAS).index.tolist()

print(f"\nSubconjunto de las {K_CARACTERISTICAS} mejores características seleccionadas:")
print(top_caracteristicas)

# 3. Construir el nuevo DataFrame reducido
df_reducido = pd.concat([metadatos, X[top_caracteristicas]], axis=1)

# 4. Guardar el nuevo CSV con el subconjunto óptimo
df_reducido.to_csv(archivo_salida_reducido, index=False)
print(f"\nÉxito: Se exportó el archivo reducido con formato {df_reducido.shape} a '{archivo_salida_reducido}'.")