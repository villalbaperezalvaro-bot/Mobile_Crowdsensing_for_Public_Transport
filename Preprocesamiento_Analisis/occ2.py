import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from sklearn.svm import OneClassSVM
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import confusion_matrix, classification_report, ConfusionMatrixDisplay

# ==========================================
# 1. CONFIGURACIÓN DE RUTAS Y PARÁMETROS
# ==========================================
RUTA_ENTRADA = r"C:\Users\villa\Desktop\INAOE\fro\datasetBalanceado20000_11.csv"
RUTA_SALIDA = r"C:\Users\villa\Desktop\INAOE\fro\predicciones_one_class_svm_1.csv"

# Definición de columnas y clase de entrenamiento (Normal)
COLUMNAS_FEATURES = ['AccelX', 'AccelY', 'AccelZ']
COLUMNA_ETIQUETA = 'Estado'
CLASE_NORMAL = 1  # La clase seleccionada como comportamiento normal (inlier)

# ==========================================
# 2. CARGA Y PREPARACIÓN DE DATOS
# ==========================================
df = pd.read_csv(RUTA_ENTRADA)

X = df[COLUMNAS_FEATURES]
y_real = df[COLUMNA_ETIQUETA]

# Mapeo binario para evaluación ground truth:
#  1 -> Normal (Inlier)
# -1 -> Anomalía (Outlier / Cualquier otra clase)
y_binary = np.where(y_real == CLASE_NORMAL, 1, -1)

# Entrenamiento usando únicamente instancias de la clase normal
X_train = X[y_real == CLASE_NORMAL]

# Escalado de variables (esencial para la métrica de distancia de SVM)
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_scaled = scaler.transform(X)

# ==========================================
# 3. ENTRENAMIENTO DEL MODELO ONE-CLASS SVM
# ==========================================
# kernel: 'rbf' para fronteras no lineales
# nu: Proporción estimada de atípicos/falsos positivos en el entrenamiento (ej. 5%)
model = OneClassSVM(kernel='rbf', gamma='scale', nu=0.05)
model.fit(X_train_scaled)

# ==========================================
# 4. GENERACIÓN DE PREDICCIONES Y SALIDA CSV
# ==========================================
# scikit-learn OneClassSVM retorna 1 (Inlier/Normal) y -1 (Outlier/Anomalía)
df['Prediccion_SVM'] = model.predict(X_scaled)
df['Es_Anomalia'] = np.where(df['Prediccion_SVM'] == -1, 1, 0)
df['Etiqueta_Predicha'] = np.where(df['Prediccion_SVM'] == 1, 'Normal', 'Anomalía')

# Exportar dataset enriquecido
df.to_csv(RUTA_SALIDA, index=False)
print(f"Resultados exportados correctamente a: {RUTA_SALIDA}")

# ==========================================
# 5. MATRIZ DE CONFUSIÓN Y MÉTRICAS
# ==========================================
cm = confusion_matrix(y_binary, df['Prediccion_SVM'], labels=[1, -1])

print("\n--- MATRIZ DE CONFUSIÓN ---")
print(cm)

print("\n--- REPORTE DE CLASIFICACIÓN ---")
print(classification_report(y_binary, df['Prediccion_SVM'], target_names=['Normal (1)', 'Anomalía (-1)'], labels=[1, -1]))

# Visualización gráfica de la Matriz de Confusión
fig, ax = plt.subplots(figsize=(6, 5))
disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=['Normal (1)', 'Anomalía (-1)'])
disp.plot(cmap=plt.cm.Blues, ax=ax)
plt.title("Matriz de Confusión - One-Class SVM")
plt.tight_layout()
plt.show()