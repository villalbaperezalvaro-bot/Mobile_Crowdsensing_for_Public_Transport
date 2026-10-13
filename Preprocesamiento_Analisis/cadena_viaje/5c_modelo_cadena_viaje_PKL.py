import pandas as pd
import numpy as np
import pickle
import os

def entrenar_y_guardar():
    # 1. Configuración de archivos
    archivo_csv = "5c_dataset_validacion_1.csv"
    archivo_modelo_pkl = "5c_modelo_transporte_rbf_svm.pkl"

    if not os.path.exists(archivo_csv):
        print(f"Error: no se encontró '{archivo_csv}'")
        return

    print(f"1. Cargando datos de entrenamiento: '{archivo_csv}'...")
    df = pd.read_csv(archivo_csv)
    print(f"   -> {len(df)} ventanas cargadas (~{len(df)*3/60:.1f} min)")

    # 2. Selección de características y etiqueta
    feature_cols = [
        'A3_prom', 'A3_desv', 'D1_prom', 'D1_desv', 
        'D2_prom', 'D2_desv', 'D3_prom', 'D3_desv', 'energia'
    ]
    y = df['Estado'].values.astype(int)
    classes = np.unique(y)
    w_size = 10
    gamma = 0.08
    C = 20.0

    print("2. Aplicando contexto temporal y estandarización...")
    # Contexto temporal causal (media móvil de 10 ventanas = ~30s)
    X_smoothed = df[feature_cols].rolling(window=w_size, min_periods=1).mean().values

    # Escalador Z-Score
    mean = np.mean(X_smoothed, axis=0)
    std = np.std(X_smoothed, axis=0)
    std[std == 0] = 1.0
    X_scaled = (X_smoothed - mean) / std

    print("3. Entrenando clasificador RBF-SVM...")
    n = len(X_scaled)
    # Matriz Kernel RBF
    dists = np.sum(X_scaled**2, axis=1, keepdims=True) + np.sum(X_scaled**2, axis=1) - 2 * np.dot(X_scaled, X_scaled.T)
    K = np.exp(-gamma * np.maximum(0, dists))
    
    # Matriz One-vs-All
    Y = np.full((n, len(classes)), -1.0)
    for i, c in enumerate(classes):
        Y[y == c, i] = 1.0
        
    # Pesos del modelo SVM
    Alpha = np.linalg.solve(K + (1.0 / C) * np.eye(n), Y)

    # 4. Estructura del modelo serializable (puro NumPy/dict)
    modelo_dict = {
        'mean': mean,
        'std': std,
        'X_train': X_scaled,
        'Alpha': Alpha,
        'gamma': gamma,
        'classes': classes,
        'feature_cols': feature_cols,
        'window_size': w_size,
        'state_names': {
            0: "0 (Origen/Destino)",
            1: "1 (Caminata)",
            2: "2 (Espera en parada)",
            3: "3 (Abordar)",
            4: "4 (A bordo)",
            5: "5 (Descender)"
        }
    }

    print(f"4. Guardando modelo en '{archivo_modelo_pkl}'...")
    with open(archivo_modelo_pkl, 'wb') as f:
        pickle.dump(modelo_dict, f)

    tamanio_kb = os.path.getsize(archivo_modelo_pkl) / 1024
    print(f"✓ Modelo guardado exitosamente ({tamanio_kb:.2f} KB).\n")

if __name__ == "__main__":
    entrenar_y_guardar()