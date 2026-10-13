import pandas as pd
import numpy as np
import pickle
from pathlib import Path

base_dir = Path(__file__).resolve().parent
filename = base_dir / 'TWD + ENERGIA + GPS + 50METRICAS_1.csv'


df_train = pd.read_csv(filename)


feature_cols = [
    'Velocidad_max', 'A3_desv', 'Velocidad_prom', 'Velocidad_min', 
    'Factor_Forma', 'Diferencia_Asimetria', 'D3_desv', 
    'Coeficiente_Variacion', 'SNR_Temporal', 'Factor_Impulso'
]
y_train = df_train['Estado'].values.astype(int)

# 2. Suavizado temporal w = 10
w_size = 10
X_train_smoothed = df_train[feature_cols].rolling(window=w_size, min_periods=1).mean().values

# 3. Escalador Z-Score
class StandaloneScaler:
    def __init__(self):
        self.mean_ = None
        self.scale_ = None
        
    def fit(self, X):
        self.mean_ = np.mean(X, axis=0)
        self.scale_ = np.std(X, axis=0)
        self.scale_[self.scale_ == 0] = 1.0
        return self
        
    def transform(self, X):
        return (X - self.mean_) / self.scale_
        
    def fit_transform(self, X):
        return self.fit(X).transform(X)

scaler = StandaloneScaler()
X_train_scaled = scaler.fit_transform(X_train_smoothed)

# 4. Clasificador RBF-SVM
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
        
    def fit(self, X, y):
        self.classes_ = np.unique(y)
        self.X_train_ = X
        n = len(X)
        K = self._rbf_kernel(X, X)
        Y = np.full((n, len(self.classes_)), -1.0)
        for i, c in enumerate(self.classes_):
            Y[y == c, i] = 1.0
        self.Alpha_ = np.linalg.solve(K + (1.0 / self.C) * np.eye(n), Y)
        return self
        
    def predict(self, X_test):
        K_test = self._rbf_kernel(X_test, self.X_train_)
        scores = np.dot(K_test, self.Alpha_)
        return self.classes_[np.argmax(scores, axis=1)]
        
    def predict_proba(self, X_test):
        K_test = self._rbf_kernel(X_test, self.X_train_)
        scores = np.dot(K_test, self.Alpha_)
        exp_s = np.exp(scores - np.max(scores, axis=1, keepdims=True))
        return exp_s / np.sum(exp_s, axis=1, keepdims=True)

model = StandaloneRBFSVM(gamma=0.08, C=20.0)
model.fit(X_train_scaled, y_train)

# 5. Guardar el paquete completo del modelo
model_payload = {
    'scaler': scaler,
    'model': model,
    'feature_cols': feature_cols,
    'classes': model.classes_,
    'w_size': w_size
}

output_model_file = r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\DATASET\8c_PKL\modelo_cadena_viaje.pkl"
with open(output_model_file, 'wb') as f:
    pickle.dump(model_payload, f)

print(f"Modelo entrenado y exportado exitosamente en: '{output_model_file}'")