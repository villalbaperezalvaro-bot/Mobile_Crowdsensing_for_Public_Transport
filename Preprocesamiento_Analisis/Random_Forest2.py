import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score, cross_val_predict
from sklearn.metrics import confusion_matrix, classification_report

# ==========================================
# 1. CARGAR Y COMBINAR LOS 10 DATASETS
# ==========================================
print("Cargando y combinando datasets...")

# Define el directorio donde están tus archivos
directorio = r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\salidad_union_csv\8c_TWD + ENERGIA + GPS + 50METRICAS.csv"
lista_dfs = []
columnas_base = None

# Iteramos del 1 al 10 para cargar los 10 archivos
for i in range(1, 11):
    nombre_archivo = f"TWD_ENERGIA_GPS_{i}.csv"
    ruta_completa = os.path.join(directorio, nombre_archivo)
    
    try:
        df_temp = pd.read_csv(ruta_completa)
        
        # Validar que todos los archivos tengan las mismas columnas
        if columnas_base is None:
            columnas_base = set(df_temp.columns)
        elif set(df_temp.columns) != columnas_base:
            print(f" -> ADVERTENCIA: {nombre_archivo} tiene columnas diferentes. Revisa los datos.")
            
        lista_dfs.append(df_temp)
        print(f" -> Cargado: {nombre_archivo} con {df_temp.shape[0]} filas.")
    except FileNotFoundError:
        print(f" -> ERROR: No se encontró {nombre_archivo}. Se omitirá.")

if not lista_dfs:
    raise ValueError("No se pudo cargar ningún archivo. Verifica la ruta y los nombres.")

# Concatenar todos los dataframes
df = pd.concat(lista_dfs, ignore_index=True)
print(f"\nDataset combinado inicial: {df.shape[0]} muestras totales.")

# Limpiar valores nulos
df = df.dropna()
print(f"Muestras tras eliminar nulos (NaN): {df.shape[0]}")

# ==========================================
# 2. FILTRAR CLASES MINORITARIAS (Para 3-FCV)
# ==========================================
n_splits_cv = 3
conteos = df["Estado"].value_counts()
clases_validas = conteos[conteos >= n_splits_cv].index
df_filtrado = df[df["Estado"].isin(clases_validas)]

muestras_eliminadas = len(df) - len(df_filtrado)
if muestras_eliminadas > 0:
    print(f"Se descartaron {muestras_eliminadas} muestras de clases minoritarias (<{n_splits_cv} elementos).")

# ==========================================
# 3. SEPARAR CARACTERÍSTICAS (X) Y ETIQUETAS (y)
# ==========================================
X = df_filtrado.drop(columns=["ID_Ventana", "Estado"], errors='ignore')
y = df_filtrado["Estado"]

print(f"\nDataset final para entrenamiento: {X.shape[0]} muestras, {X.shape[1]} características.")

# ==========================================
# 4. CONFIGURAR RANDOM FOREST Y CV
# ==========================================
rf_model = RandomForestClassifier(
    n_estimators=100,
    max_depth=None,
    class_weight='balanced', # Crucial para sets desbalanceados
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
print("\n" + "="*55)
print("       RESULTADOS RANDOM FOREST (10 DATASETS COMBINADOS)")
print("="*55)

print(f"\nAccuracy por Pliegue (Fold): {scores}")
print(f"Accuracy Promedio Global:    {scores.mean()*100:.2f}% (+/- {scores.std()*100:.2f}%)")

print("\nMatriz de Confusión Acumulada:")
print(confusion_matrix(y, y_pred_cv))

print("\nReporte de Clasificación Acumulado:")
print(classification_report(y, y_pred_cv))

# ==========================================
# 7. IMPORTANCIA DE LAS CARACTERÍSTICAS Y GRÁFICA
# ==========================================
# Entrenamos en todo el conjunto para extraer la importancia global
rf_model.fit(X, y)
importancias = pd.Series(rf_model.feature_importances_, index=X.columns).sort_values(ascending=False)

print("\n--- Top 10 Características Más Importantes ---")
print(importancias.head(10).apply(lambda x: f"{x*100:.2f}%"))

# Generar gráfica de las características más importantes
plt.figure(figsize=(10, 6))
importancias.head(10).sort_values().plot(kind='barh', color='teal')
plt.title('Top 10 Características más Importantes (Random Forest)')
plt.xlabel('Importancia Relativa')
plt.ylabel('Características')
plt.grid(axis='x', linestyle='--', alpha=0.7)
plt.tight_layout()
plt.show()