import pandas as pd
from sklearn.model_selection import StratifiedKFold, cross_val_score, cross_val_predict
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report
from sklearn.pipeline import Pipeline

# ==========================================
# 1. CARGAR Y LIMPIAR EL DATASET
# ==========================================
print("Cargando dataset...")
df = pd.read_csv(r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\DATASET\SALIDAD_ACEL_GPS_ENERGIA_FFT_VARIANZA\selecion\6c-FFT + VARIANZA + 50CARAT_selecion.csv")
# Limpiar valores nulos (NaN)
df = df.dropna()

# ==========================================
# 2. SEPARAR CARACTERÍSTICAS (X) Y ETIQUETAS (y)
# ==========================================
# Se elimina el ID (no es predictivo) y la variable objetivo para tener las características
X = df.drop(columns=["ID_Ventana", "Estado"])
y = df["Estado"]

# ---> NUEVO: IMPRIMIR ESTADOS Y CANTIDADES <---
print("\n" + "="*40)
print("ESTADOS ENCONTRADOS Y SU CANTIDAD")
print("="*40)
conteo_estados = y.value_counts()
print(conteo_estados)
print(f"\nTotal de estados únicos encontrados: {len(conteo_estados)}")
# ----------------------------------------------

# ==========================================
# 3. DEFINIR EL MODELO Y PREPROCESAMIENTO
# ==========================================
# Usamos un Pipeline. Esto es CRUCIAL en Cross-Validation para que el 
# StandardScaler se ajuste (fit) SOLO con los datos de entrenamiento de cada pliegue 
# y no con todo el dataset, evitando así la fuga de datos (data leakage).
k = 5  # número de vecinos
pipeline = Pipeline([
    ('scaler', StandardScaler()),
    ('knn', KNeighborsClassifier(n_neighbors=k))
])

# ==========================================
# 4. CONFIGURAR LA VALIDACIÓN CRUZADA (3-FCV)
# ==========================================
# StratifiedKFold asegura que cada pliegue mantenga la misma proporción 
# de clases (Estado) que el dataset original.
skf = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)

# ==========================================
# 5. EVALUAR Y OBTENER RESULTADOS
# ==========================================
print("\nRealizando 3-Fold Cross-Validation...")

# cross_val_score entrena y evalúa el pipeline 3 veces y nos devuelve el accuracy de cada vez
scores = cross_val_score(pipeline, X, y, cv=skf, scoring='accuracy')

# cross_val_predict genera las predicciones para cada muestra cuando 
# esta formó parte del conjunto de prueba (out-of-fold), permitiendo armar una matriz global
y_pred_cv = cross_val_predict(pipeline, X, y, cv=skf)

# ==========================================
# 6. MOSTRAR MÉTRICAS
# ==========================================
print("\n" + "="*40)
print("RESULTADOS DEL MODELO KNN CON 3-FCV")
print("="*40)

print(f"\nAccuracy por cada Fold (pliegue): {scores}")
print(f"Accuracy Promedio Global:         {scores.mean():.4f} (+/- {scores.std():.4f})")

print("\nMatriz de Confusión Acumulada:")
print(confusion_matrix(y, y_pred_cv))

print("\nReporte de Clasificación Acumulado:")
print(classification_report(y, y_pred_cv))