import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report

# 1. Cargar dataset
df = pd.read_csv(r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\salidad_METRICAS_SELECIONADAS\TWD_ENERGIA_GPS_8.csv") # poner el nombre del archivo que desea analisar 
print("Columnas disponibles:", df.columns)



# Limpiar valores nulos (NaN) generados en las estadísticas de velocidad
df = df.dropna() # O puedes usar df = df.fillna(0) si prefieres rellenar con ceros

# 2. Separar características (X) y etiquetas (y)
X = df.drop(columns=["ID_Ventana", "Estado"])  # características
y = df["Estado"]  # etiquetas

# 3. Dividir en entrenamiento y prueba
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y    # porcetanje de prueba y entrenamiento 80 % para entrenamiento y 20 % prueba 
)

# 4. Reconstruir DataFrames con etiquetas
train_df = X_train.copy()
train_df["Estado"] = y_train.values
test_df = X_test.copy()
test_df["Estado"] = y_test.values

# 5. Guardar en CSV
train_df.to_csv("salida/train.csv", index=False)
test_df.to_csv("salida/test.csv", index=False)

print(train_df.info())

# 6. Escalar características (opcional pero recomendado para KNN)
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# 7. Definir y entrenar modelo KNN
k = 5  # número de vecinos
knn = KNeighborsClassifier(n_neighbors=k)
knn.fit(X_train_scaled, y_train)

# 8. Hacer predicciones
y_pred = knn.predict(X_test_scaled)

# 9. Evaluar modelo
print("\nResultados del modelo KNN:")
print("Accuracy:", accuracy_score(y_test, y_pred))
print("\nMatriz de confusión:\n", confusion_matrix(y_test, y_pred))
print("\nReporte de clasificación:\n", classification_report(y_test, y_pred))