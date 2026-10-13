import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from pathlib import Path

# 1. Cargar datos
# Definimos la ruta absoluta al archivo CSV usando un raw string (r"")
filepath = r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\DATASET\SALIDAD_ACEL_GPS_ENERGIA_FFT_VARIANZA\50 carateristicas\metricas_50_xyz_10-selecion.csv"

df = pd.read_csv(filepath)

# 2. Definición de todas las 10 características (ajustado según tu lista) y la variable objetivo
feature_cols = [
    'Z_RMS', 'Mag_IQR', 'Mag_P90', 'Y_RMS', 'Mag_Cruces_Media', 
    'Mag_MAD', 'Mag_P75', 'Mag_P25', 'Autocorr_Lag3', 'X_STD'
]
y = df['Estado'].values.astype(int)

# 3. Aplicar ventana temporal móvil (w = 10) sobre todas las características
w_size = 10
X_smoothed = df[feature_cols].rolling(window=w_size, min_periods=1).mean().values

# 4. Estandarización Z-Score
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_smoothed)

# 5. Configuración del clasificador RBF-SVM y Validación Cruzada
clf = SVC(kernel='rbf', C=20.0, gamma=0.08, decision_function_shape='ovr', random_state=42)
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

# 6. Evaluación Fold por Fold
print("=" * 70)
print(f"EVALUACIÓN 5-FOLD CV (w = {w_size}, TODAS LAS CARACTERÍSTICAS)")
print("=" * 70)

fold_accs = []
for fold, (train_idx, test_idx) in enumerate(cv.split(X_scaled, y), 1):
    X_tr, y_tr = X_scaled[train_idx], y[train_idx]
    X_te, y_te = X_scaled[test_idx], y[test_idx]
    
    clf.fit(X_tr, y_tr)
    preds = clf.predict(X_te)
    acc = accuracy_score(y_te, preds)
    fold_accs.append(acc)
    print(f"Fold {fold}: Precisión = {acc * 100:6.2f}%")

print("-" * 70)
print(f"PRECISIÓN MEDIA GLOBAL: {np.mean(fold_accs) * 100:.2f}% (+/- {np.std(fold_accs) * 100:.2f}%)")
print("-" * 70)

# 7. Matriz de Confusión y Reporte por Clase
y_pred_total = cross_val_predict(clf, X_scaled, y, cv=cv)

# Detectar cuántas clases hay dinámicamente
clases_unicas = np.unique(y)
num_clases = len(clases_unicas)

print("\nMATRIZ DE CONFUSIÓN (Filas: Real, Columnas: Predicho):")
cm = confusion_matrix(y, y_pred_total)

# Encabezados dinámicos
headers = "    ".join([f"E{c}" for c in clases_unicas])
print(f"          {headers}")
for i, row in zip(clases_unicas, cm):
    print(f"E{i}: [ " + "  ".join([f"{val:4d}" for val in row]) + " ]")

print("\nREPORTE DE CLASIFICACIÓN:")
nombres_clases = [f"Estado {c}" for c in clases_unicas]
print(classification_report(y, y_pred_total, target_names=nombres_clases, digits=4))