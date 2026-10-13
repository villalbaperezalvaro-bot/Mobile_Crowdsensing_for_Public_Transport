import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score, cross_val_predict
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

# 1. Cargar el dataset
file_path = 'dataset1_shuffled.csv'
df = pd.read_csv(file_path)

# 2. Selección de las 9 características wavelet completas
features = [
    'A3_prom', 'A3_desv', 
    'D1_prom', 'D1_desv', 
    'D2_prom', 'D2_desv', 
    'D3_prom', 'D3_desv', 
    'energia'
]

X = df[features]
y = df['Estado']

# 3. Integración de Contexto Temporal (Media Móvil con w = 10)
X_smooth = X.rolling(window=10, min_periods=1).mean()

# 4. Estandarización Z-Score
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_smooth)

# 5. Configurar el clasificador k-NN ponderado por distancia (k = 3)
knn = KNeighborsClassifier(n_neighbors=3, weights='distance')

# 6. Validación Cruzada Estratificada de 5 Folds
skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

# Obtener exactitud por cada fold
scores = cross_val_score(knn, X_scaled, y, cv=skf, scoring='accuracy')

# Predicciones acumuladas (out-of-fold)
y_pred = cross_val_predict(knn, X_scaled, y, cv=skf)

# 7. Despliegue de Resultados
print("=" * 65)
print(f"EXACTITUD GLOBAL (ACCURACY): {accuracy_score(y, y_pred) * 100:.2f}%")
print(f"Accuracy media por fold: {scores.mean() * 100:.2f}% (+/- {scores.std() * 100:.2f}%)")
print(f"Folds individuales: {[round(s * 100, 2) for s in scores]}")
print("=" * 65)

print("\nMATRIZ DE CONFUSIÓN:")
labels = sorted(y.unique())
header = "Real \\ Pred\t" + "\t".join([f"Pred {c}" for c in labels])
print(header)
print("-" * 65)
cm = confusion_matrix(y, y_pred)
for idx, row in enumerate(cm):
    row_str = "\t".join(str(val) for val in row)
    print(f"Clase {labels[idx]}\t\t{row_str}")

print("\nREPORTE DE CLASIFICACIÓN:")
print(classification_report(y, y_pred, digits=4))