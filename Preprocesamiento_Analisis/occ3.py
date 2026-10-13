import pandas as pd
import numpy as np
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns

# ==========================================
# 1. CARGA Y PREPARACIÓN DE DATOS
# ==========================================
ruta_archivo = r"C:\Users\villa\Desktop\INAOE\fro\datasetBalanceado20000_11.csv"
df = pd.read_csv(ruta_archivo)

# Asumiendo que tienes una columna 'Estado' o 'Clase' y el resto son características (ej. medias, varianzas, FFT)
columna_etiqueta = 'Estado'
clase_objetivo = 1  # Reemplaza por el ID de la unidad o clase que quieres modelar

# Limpiar valores nulos si existen
df = df.dropna()

# Extraer etiquetas
y = df[columna_etiqueta]

# Extraer SOLO columnas numéricas (excluyendo la etiqueta y columnas de texto como 'Timestamp')
X = df.drop(columns=[columna_etiqueta], errors='ignore')
X = X.select_dtypes(include=[np.number])

print(f"Características numéricas seleccionadas ({X.shape[1]} columnas):")
print(list(X.columns))

# ==========================================
# 2. DIVISIÓN Y FILTRADO (Solo clase objetivo para entrenar)
# ==========================================
X_train_full, X_test, y_train_full, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# El One-Class SVM solo se entrena con la clase que consideramos "normal"
X_train_normal = X_train_full[y_train_full == clase_objetivo]

print(f"\nMuestras totales de entrenamiento clase normal ({clase_objetivo}): {len(X_train_normal)}")
print(f"Muestras totales de prueba: {len(X_test)}")

# ==========================================
# 3. ESCALADO DE DATOS (Crítico para SVM)
# ==========================================
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train_normal)
X_test_scaled = scaler.transform(X_test)

# ==========================================
# 4. CONFIGURACIÓN Y ENTRENAMIENTO DEL MODELO
# ==========================================
# nu: Porcentaje de anomalías esperadas en los datos de entrenamiento (ej. 0.05 = 5%)
# gamma: 'scale' es recomendado para evitar sobreajuste en los límites de decisión
modelo_ocsvm = OneClassSVM(kernel='rbf', gamma='scale', nu=0.05)

print("\nEntrenando One-Class SVM...")
modelo_ocsvm.fit(X_train_scaled)

# ==========================================
# 5. PREDICCIÓN Y EVALUACIÓN
# ==========================================
# predict() devuelve +1 para los inliers (datos normales) y -1 para los outliers (anomalías)
predicciones = modelo_ocsvm.predict(X_test_scaled)

# Convertir las etiquetas de prueba a +1 (clase objetivo) y -1 (anomalías) para evaluar
y_test_binario = np.where(y_test == clase_objetivo, 1, -1)

print("\n--- REPORTE DE EVALUACIÓN ---")
print(classification_report(y_test_binario, predicciones, labels=[-1, 1], target_names=['Anomalía (-1)', 'Normal (+1)'], zero_division=0))

# Matriz de confusión
cm = confusion_matrix(y_test_binario, predicciones, labels=[-1, 1])
print("--- MATRIZ DE CONFUSIÓN ---")
print(cm)