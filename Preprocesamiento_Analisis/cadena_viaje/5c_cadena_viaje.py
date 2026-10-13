import pandas as pd
import numpy as np
import os

# ==============================================================================
# 1. CONFIGURACIÓN DEL ARCHIVO
# ==============================================================================
dataset = r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\DATASET\SALIDAD_ACEL_GPS_ENERGIA_FFT_VARIANZA\selecion\6c-FFT + VARIANZA + 50CARAT_selecion.csv"  # <-- Nombre de tu archivo

if not os.path.exists(dataset):
    print(f"Error: No se encontró el archivo '{dataset}'.")
    exit(1)

df = pd.read_csv(dataset)
print(f"Archivo cargado: '{dataset}' ({len(df)} ventanas temporales / ~{len(df) * 3 / 60:.1f} minutos)")

# ==============================================================================
# 2. SELECCIÓN DE CARACTERÍSTICAS Y ETIQUETA
# ==============================================================================
# Se seleccionan las 9 características basadas en la descomposición Wavelet
feature_cols = ['Velocidad_prom', 'Velocidad_max', 'Velocidad_min', 'Mag_IQR', 'Z_RMS', 'Y_RMS', 'Mag_P75', 'A3_desv', 'Amplitud_FFT_Max', 'Mag_MAD']


y = df['Estado'].values.astype(int)
classes = np.unique(y)

# ==============================================================================
# 3. CONTEXTO TEMPORAL CAUSAL (w = 10 ventanas = ~30 segundos de memoria)
# ==============================================================================
w_size = 10
X_smoothed = df[feature_cols].rolling(window=w_size, min_periods=1).mean().values

# ==============================================================================
# 4. ESCALADOR Z-SCORE
# ==============================================================================
class StandardScaler:
    def fit_transform(self, X):
        self.mean = np.mean(X, axis=0)
        self.std = np.std(X, axis=0)
        self.std[self.std == 0] = 1.0
        return (X - self.mean) / self.std

    def transform(self, X):
        return (X - self.mean) / self.std

# ==============================================================================
# 5. CLASIFICADOR RBF-SVM (Support Vector Machine con Kernel Gaussiano)
# ==============================================================================
class RBFSVMClassifier:
    def __init__(self, gamma=0.08, C=20.0):
        self.gamma = gamma
        self.C = C

    def _rbf_kernel(self, X1, X2):
        dists = np.sum(X1**2, axis=1, keepdims=True) + np.sum(X2**2, axis=1) - 2 * np.dot(X1, X2.T)
        return np.exp(-self.gamma * np.maximum(0, dists))

    def fit(self, X, y):
        self.classes = np.unique(y)
        self.X_train = X
        n = len(X)
        K = self._rbf_kernel(X, X)
        Y = np.full((n, len(self.classes)), -1.0)
        for i, c in enumerate(self.classes):
            Y[y == c, i] = 1.0
        self.Alpha = np.linalg.solve(K + (1.0 / self.C) * np.eye(n), Y)
        return self

    def predict(self, X_test):
        K_test = self._rbf_kernel(X_test, self.X_train)
        scores = np.dot(K_test, self.Alpha)
        return self.classes[np.argmax(scores, axis=1)]

# ==============================================================================
# 6. VALIDACIÓN CRUZADA ESTRATIFICADA 5-FOLD
# ==============================================================================
def stratified_kfold(y, n_splits=3, random_state=42):
    np.random.seed(random_state)
    folds = [[] for _ in range(n_splits)]
    for c in np.unique(y):
        idx = np.where(y == c)[0]
        np.random.shuffle(idx)
        split_idx = np.array_split(idx, n_splits)
        for fold_i, s in enumerate(split_idx):
            folds[fold_i].extend(s)
            
    for i in range(n_splits):
        test_idx = np.array(folds[i])
        train_idx = np.setdiff1d(np.arange(len(y)), test_idx)
        yield train_idx, test_idx

print("\n" + "=" * 75)
print(f"EVALUACIÓN 5-FOLD CV EN EL VIAJE REAL (w = {w_size}, RBF-SVM)")
print("=" * 75)

all_preds = np.zeros(len(y), dtype=int)
fold_accs = []

for fold, (train_idx, test_idx) in enumerate(stratified_kfold(y, n_splits=3, random_state=42), 1):
    X_train, y_train = X_smoothed[train_idx], y[train_idx]
    X_test, y_test = X_smoothed[test_idx], y[test_idx]

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    clf = RBFSVMClassifier(gamma=0.08, C=20.0)
    clf.fit(X_train_scaled, y_train)
    preds = clf.predict(X_test_scaled)
    
    acc = np.mean(preds == y_test)
    fold_accs.append(acc)
    all_preds[test_idx] = preds
    aciertos = np.sum(preds == y_test)
    print(f"Fold {fold}: Precisión = {acc * 100:6.2f}% ({aciertos}/{len(y_test)} aciertos)")

mean_acc = np.mean(fold_accs)
std_acc = np.std(fold_accs)
print("-" * 75)
print(f"PRECISIÓN MEDIA GLOBAL: {mean_acc * 100:.2f}% (+/- {std_acc * 100:.2f}%)")
print("-" * 75)

# ==============================================================================
# 7. MATRIZ DE CONFUSIÓN
# ==============================================================================
cm = np.zeros((len(classes), len(classes)), dtype=int)
for true_lbl, pred_lbl in zip(y, all_preds):
    cm[true_lbl, pred_lbl] += 1

print("\nMATRIZ DE CONFUSIÓN (Filas: Real, Columnas: Predicho):")
print("          E0    E1    E2    E3    E4    E5    Total Real")
for i in range(len(classes)):
    row_str = "  ".join([f"{cm[i, j]:4d}" for j in range(len(classes))])
    print(f"Estado {i}: [ {row_str} ]   {np.sum(cm[i, :]):5d}")

# ==============================================================================
# 8. REPORTE DE MÉTRICAS POR CLASE
# ==============================================================================
print("\nREPORTE DE MÉTRICAS POR CLASE:")
print(f"{'Estado':<10} {'Precision':<12} {'Recall':<12} {'F1-Score':<12} {'Soporte':<10}")
for i in range(len(classes)):
    tp = cm[i, i]
    fp = np.sum(cm[:, i]) - tp
    fn = np.sum(cm[i, :]) - tp
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    support = np.sum(cm[i, :])
    print(f"Estado {i:<3} {precision * 100:>8.2f}%    {recall * 100:>8.2f}%    {f1 * 100:>8.2f}%    {support:>7d}")

# ==============================================================================
# 9. RECONSTRUCCIÓN DE LA CADENA DE VIAJE DETECTADA
# ==============================================================================
print("\n" + "=" * 75)
print("SECUENCIA CRONOLÓGICA DETECTADA EN EL VIAJE:")
print("=" * 75)
tramos = []
curr_state = all_preds[0]
start_idx = 1
for i in range(1, len(all_preds)):
    if all_preds[i] != curr_state:
        dur = (i - start_idx + 1) * 3
        tramos.append((curr_state, start_idx, i, dur))
        curr_state = all_preds[i]
        start_idx = i + 1
dur_final = (len(all_preds) - start_idx + 1) * 3
tramos.append((curr_state, start_idx, len(all_preds), dur_final))

nombres_estados = {
    0: "0 (Origen/Destino)",
    1: "1 (Caminata)",
    2: "2 (Espera parada)",
    3: "3 (Abordar)",
    4: "4 (A bordo)",
    5: "5 (Descender)"
}

print(f"{'Tramo':<8} {'Estado Detectado':<22} {'Ventanas':<20} {'Duración Estimada':<20}")
for idx, (st, s_w, e_w, dur) in enumerate(tramos[:15], 1):  # Muestra los primeros 15 tramos
    est_name = nombres_estados.get(st, f"Estado {st}")
    print(f"{idx:<8} {est_name:<22} Ventanas {s_w:4d} a {e_w:4d}      ~{dur:4d} s ({dur/60:.1f} min)")

if len(tramos) > 15:
    print(f"... [{len(tramos) - 15} tramos adicionales en el archivo exportado]")

# ==============================================================================
# 10. EXPORTAR CSV CON PREDICCIONES
# ==============================================================================
salida_csv = f"{os.path.splitext(dataset)[0]}_predicho_6c.csv"
df_res = df.copy()
df_res['Estado_Predicho'] = all_preds
df_res.to_csv(salida_csv, index=False)
print("-" * 75)
print(f"Predicciones exportadas a: '{salida_csv}'\n")