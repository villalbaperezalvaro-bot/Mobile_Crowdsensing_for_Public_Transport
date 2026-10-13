import pandas as pd
import numpy as np
import pickle
import os

# ==============================================================================
# CONFIGURACIÓN: INDICA AQUÍ EL ARCHIVO QUE DESEAS EVALUAR Y SU MODELO
# ==============================================================================
dataset = r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\DATASET\salidad_pre_procesamiento_8clases\TWD + ENERGIA + GPS + 50METRICAS_2.csv"
archivo_modelo = r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\DATASET\8c_PKL\modelo_cadena_viaje.pkl"


# ==============================================================================
# DEFINICIÓN DE CLASES DEL MODELO (Necesarias para cargar el .pkl)
# ==============================================================================
class StandaloneScaler:
    def __init__(self):
        self.mean_ = None
        self.scale_ = None
        
    def transform(self, X):
        return (X - self.mean_) / self.scale_


class StandaloneRBFSVM:
    def __init__(self, gamma=0.08, C=20.0):
        self.gamma = gamma
        self.C = C
        self.classes_ = None
        self.X_train_ = None
        self.Alpha_ = None
        
    def _rbf_kernel(self, X1, X2):
        dists = np.sum(X1**2, axis=1, keepdims=True) + np.sum(X2**2, axis=1) - 2 * np.dot(X1, X2.T)
        return np.exp(-self.gamma * np.maximum(0, dists))
        
    def predict(self, X_test):
        K_test = self._rbf_kernel(X_test, self.X_train_)
        scores = np.dot(K_test, self.Alpha_)
        return self.classes_[np.argmax(scores, axis=1)]
        
    def predict_proba(self, X_test):
        K_test = self._rbf_kernel(X_test, self.X_train_)
        scores = np.dot(K_test, self.Alpha_)
        exp_s = np.exp(scores - np.max(scores, axis=1, keepdims=True))
        return exp_s / np.sum(exp_s, axis=1, keepdims=True)


# ==============================================================================
# PROCESAMIENTO Y EVALUACIÓN DEL VIAJE
# ==============================================================================
def evaluar_viaje(archivo_viaje, modelo_path):
    if not os.path.exists(modelo_path):
        print(f"Error: No se encontró el modelo '{modelo_path}'.")
        print("Asegúrate de haber ejecutado previamente el script de entrenamiento.")
        return

    if not os.path.exists(archivo_viaje):
        print(f"Error: No se encontró el archivo de datos '{archivo_viaje}'.")
        print("Verifica que la ruta y el nombre estén bien escritos.")
        return

    # 1. Cargar modelo pre-entrenado
    with open(modelo_path, 'rb') as f:
        pkg = pickle.load(f)

    saved_scaler = pkg['scaler']
    saved_model = pkg['model']
    feat_cols = pkg['feature_cols']
    w = pkg['w_size']
    classes = pkg['classes']

    # 2. Cargar archivo del nuevo viaje
    df_viaje = pd.read_csv(archivo_viaje)
    n_ventanas = len(df_viaje)
    
    print("\n" + "=" * 75)
    print(f"EVALUANDO VIAJE: '{archivo_viaje}'")
    print(f"Total de ventanas: {n_ventanas} (~{n_ventanas * 3} s / {n_ventanas * 3 / 60:.1f} min)")
    print("=" * 75)

    # 3. Aplicar ventana deslizante causal w = 10 sobre las características
    X_raw = df_viaje[feat_cols].rolling(window=w, min_periods=1).mean().values

    # 4. Estandarizar usando los parámetros del modelo original
    X_scaled = saved_scaler.transform(X_raw)

    # 5. Generar predicciones y nivel de confianza
    predicciones = saved_model.predict(X_scaled)
    probabilidades = saved_model.predict_proba(X_scaled)
    confianza = np.max(probabilidades, axis=1) * 100

    df_resultado = df_viaje.copy()
    df_resultado['Estado_Predicho'] = predicciones
    df_resultado['Confianza_%'] = np.round(confianza, 2)

    # 6. MÉTRICAS Y MATRIZ DE CONFUSIÓN DINÁMICA
    if 'Estado' in df_viaje.columns:
        y_real = df_viaje['Estado'].values.astype(int)
        acc = np.mean(predicciones == y_real) * 100
        print(f"\n-> PRECISIÓN GLOBAL EN ESTE VIAJE: {acc:.2f}%\n")
        
        # Ajustar dinámicamente la dimensión de la matriz según las clases presentes
        max_label = max(y_real.max(), predicciones.max())
        n_classes_eval = max(len(classes), max_label + 1)
        
        cm = np.zeros((n_classes_eval, n_classes_eval), dtype=int)
        for t, p in zip(y_real, predicciones):
            cm[t, p] += 1
            
        print("Matriz de Confusión:")
        headers = "    ".join([f"E{i}" for i in range(n_classes_eval)])
        print(f"          {headers}")
        for i, row in enumerate(cm):
            print(f"Estado {i}: [ " + "  ".join([f"{val:4d}" for val in row]) + " ]")

    # 7. Resumen de la Cadena de Viaje Detectada (Segmentos continuos)
    print("\n" + "-" * 75)
    print("SECUENCIA CRONOLÓGICA DE LA CADENA DE VIAJE DETECTADA:")
    print("-" * 75)
    tramos = []
    curr_state = predicciones[0]
    start_idx = 1
    for i in range(1, len(predicciones)):
        if predicciones[i] != curr_state:
            dur = (i - start_idx + 1) * 3
            tramos.append((curr_state, start_idx, i, dur))
            curr_state = predicciones[i]
            start_idx = i + 1
    dur_final = (len(predicciones) - start_idx + 1) * 3
    tramos.append((curr_state, start_idx, len(predicciones), dur_final))

    print(f"{'Tramo':<8} {'Estado':<16} {'Ventanas':<20} {'Duración Estimada':<20}")
    for idx, (st, s_w, e_w, dur) in enumerate(tramos, 1):
        print(f"{idx:<8} Estado {st:<9} Ventanas {s_w:4d} a {e_w:4d}      ~{dur:4d} s ({dur/60:.1f} min)")

    # 8. Exportar CSV con resultados (nombre_archivo_predicho.csv)
    nombre_base = os.path.splitext(archivo_viaje)[0]
    salida_csv = f"{nombre_base}_predicho.csv"
    df_resultado.to_csv(salida_csv, index=False)
    print("-" * 75)
    print(f"Archivo exportado con predicciones en: '{salida_csv}'\n")


# Ejecución automática
if __name__ == '__main__':
    evaluar_viaje(dataset, archivo_modelo)