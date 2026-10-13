import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score, cross_val_predict
from sklearn.metrics import confusion_matrix, classification_report

# ==========================================
# 1. CARGAR Y PREPARAR EL DATASET
# ==========================================
print("Cargando dataset...")
# Cambia la ruta según el archivo que desees evaluar (ej. tu dataset reducido con FS o combinado)
ruta_archivo = r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\salidad_union_csv\3c_TWD + ENERGIA + GPS + 50METRICAS.csv"
df = pd.read_csv(ruta_archivo)

# Limpiar posibles valores nulos
df = df.dropna()

# ==========================================
# 2. FILTRAR CLASES MINORITARIAS (Seguridad CV)
# ==========================================
n_splits_cv = 3
conteos = df["Estado"].value_counts()
clases_validas = conteos[conteos >= n_splits_cv].index
df_filtrado = df[df["Estado"].isin(clases_validas)]

muestras_eliminadas = len(df) - len(df_filtrado)
if muestras_eliminadas > 0:
    print(f"Se descartaron {muestras_eliminadas} muestras pertenecientes a clases con menos de {n_splits_cv} elementos.")

# ==========================================
# 3. SEPARAR CARACTERÍSTICAS (X) Y ETIQUETAS (y)
# ==========================================
X = df_filtrado.drop(columns=["ID_Ventana", "Estado"], errors='ignore')
y = df_filtrado["Estado"]

print(f"Dataset listo para entrenamiento: {X.shape[0]} muestras, {X.shape[1]} características.")

# ==========================================
# 4. CONFIGURAR RANDOM FOREST Y 3-FCV
# ==========================================
# class_weight='balanced' compensa automáticamente las clases con pocas muestras
rf_model = RandomForestClassifier(
    n_estimators=100,
    max_depth=None,
    class_weight='balanced',
    random_state=42
)

skf = StratifiedKFold(n_splits=n_splits_cv, shuffle=True, random_state=42)

# ==========================================
# 5. EVALUACIÓN Y PREDICCIONES
# ==========================================
print("\nEjecutando Random Forest con 3-Fold Cross-Validation...")

scores = cross_val_score(rf_model, X, y, cv=skf, scoring='accuracy')
y_pred_cv = cross_val_predict(rf_model, X, y, cv=skf)

# ==========================================
# 6. REPORTAR RESULTADOS
# ==========================================
print("\n" + "="*50)
print("       RESULTADOS DEL MODELO RANDOM FOREST (3-FCV)")
print("="*50)

print(f"\nAccuracy por Pliegue (Fold): {scores}")
print(f"Accuracy Promedio Global:   {scores.mean()*100:.2f}% (+/- {scores.std()*100:.2f}%)")

print("\nMatriz de Confusión Acumulada:")
print(confusion_matrix(y, y_pred_cv))

print("\nReporte de Clasificación Acumulado:")
print(classification_report(y, y_pred_cv))

# ==========================================
# 7. RELEVANCIA REAL DE LAS CARACTERÍSTICAS
# ==========================================
# Entrenamos en la totalidad del subset filtrado para extraer la importancia final
rf_model.fit(X, y)
importancias = pd.Series(rf_model.feature_importances_, index=X.columns).sort_values(ascending=False)

print("\n--- Importancia de las Características en este Modelo ---")
for col, imp in importancias.items():
    print(f"{col:<25}: {imp*100:.2f}%")