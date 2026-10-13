import os
import sys
import pickle
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.model_selection import StratifiedKFold, cross_val_score, cross_val_predict
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score


def evaluar_5fold_cv(df, feature_cols, target_col='Estado', window_size=10, gamma=0.08, C=10.0, state_names=None):
    """
    Ejecuta la evaluación 5-Fold Cross-Validation sobre la señal real
    y despliega la matriz de confusión y el reporte detallado por clase.
    """
    if state_names is None:
        state_names = {}

    X_raw = df[feature_cols]
    y = df[target_col].astype(int)

    # 1. Contexto temporal (Media Móvil)
    X_smooth = X_raw.rolling(window=window_size, min_periods=1).mean()

    # 2. Estandarización Z-Score
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_smooth)

    # 3. Clasificador RBF-SVM
    svm_model = SVC(kernel='rbf', C=C, gamma=gamma, random_state=42)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    # 4. Cálculo de métricas out-of-fold
    scores = cross_val_score(svm_model, X_scaled, y, cv=cv, scoring='accuracy')
    y_pred = cross_val_predict(svm_model, X_scaled, y, cv=cv)

    # 5. Despliegue formal de resultados
    print("\n" + "=" * 80)
    print(f"EVALUACIÓN 5-FOLD CV EN EL VIAJE REAL (w = {window_size}, RBF-SVM)")
    print("=" * 80)
    print(f"PRECISIÓN MEDIA GLOBAL: {scores.mean() * 100:.2f}% (+/- {scores.std() * 100:.2f}%)")
    folds_str = ", ".join([f"{s * 100:.2f}%" for s in scores])
    print(f"Precisión por Fold:     [{folds_str}]")
    print("-" * 80)

    # Matriz de Confusión
    clases = sorted(np.unique(y))
    nombres_cols = [state_names.get(c, f"Est_{c}") for c in clases]
    cm = confusion_matrix(y, y_pred, labels=clases)

    print("\nMATRIZ DE CONFUSIÓN (Filas: Real, Columnas: Predicho):")
    lbl_header = "Real \\ Pred"
    header = f"{lbl_header:<22}" + "".join([f"{nom:>14}" for nom in nombres_cols]) + f"{'Total':>10}"
    print(header)
    print("-" * len(header))
    for idx, row in enumerate(cm):
        nom_real = state_names.get(clases[idx], f"Est_{clases[idx]}")
        row_str = "".join([f"{val:>14d}" for val in row])
        print(f"{nom_real:<22}{row_str}{np.sum(row):>10d}")

    # Reporte de Métricas por Clase
    print("\nREPORTE DE MÉTRICAS POR CLASE:")
    target_names = [state_names.get(c, f"Estado {c}") for c in clases]
    print(classification_report(y, y_pred, labels=clases, target_names=target_names, digits=4))
    print("=" * 80 + "\n")


def predecir_con_modelo(modelo, df):
    """
    Ejecuta el pipeline de inferencia matricial RBF-SVM usando los pesos del .pkl
    """
    cols_requeridas = modelo['feature_cols']
    cols_faltantes = [c for c in cols_requeridas if c not in df.columns]
    if cols_faltantes:
        raise ValueError(f"El dataset no contiene las columnas requeridas: {cols_faltantes}")

    # Contexto temporal
    window_size = modelo.get('window_size', 10)
    X_smooth = df[cols_requeridas].rolling(window=window_size, min_periods=1).mean().values
    
    # Estandarización
    mean = np.asarray(modelo['mean'])
    std = np.asarray(modelo['std'])
    X_scaled = (X_smooth - mean) / std
    
    # Kernel RBF vectorizado
    X_train = np.asarray(modelo['X_train'])
    gamma = float(modelo.get('gamma', 0.08))
    dists = (
        np.sum(X_scaled**2, axis=1, keepdims=True) 
        + np.sum(X_train**2, axis=1) 
        - 2 * np.dot(X_scaled, X_train.T)
    )
    K_test = np.exp(-gamma * np.maximum(0, dists))
    
    # Scores y clases
    Alpha = np.asarray(modelo['Alpha'])
    scores = np.dot(K_test, Alpha)
    clases = np.asarray(modelo['classes'])
    predicciones = clases[np.argmax(scores, axis=1)]
    
    # Estimación de confianza vía Softmax
    exp_s = np.exp(scores - np.max(scores, axis=1, keepdims=True))
    probabilidades = exp_s / np.sum(exp_s, axis=1, keepdims=True)
    confianza = np.max(probabilidades, axis=1)
    
    return predicciones, confianza


def segmentar_viaje(predicciones, window_sec=3.0, state_names=None):
    """
    Agrupa las ventanas temporales continuas en tramos cronológicos de viaje.
    """
    if state_names is None:
        state_names = {}

    if len(predicciones) == 0:
        return []

    tramos = []
    curr_state = predicciones[0]
    start_w = 1

    for i in range(1, len(predicciones)):
        if predicciones[i] != curr_state:
            ventanas = i - start_w + 1
            duracion_sec = ventanas * window_sec
            tramos.append({
                'estado': curr_state,
                'nombre_estado': state_names.get(curr_state, f"Estado {curr_state}"),
                'ventana_inicio': start_w,
                'ventana_fin': i,
                'ventanas': ventanas,
                'duracion_seg': duracion_sec,
                'duracion_min': duracion_sec / 60.0
            })
            curr_state = predicciones[i]
            start_w = i + 1

    ventanas = len(predicciones) - start_w + 1
    duracion_sec = ventanas * window_sec
    tramos.append({
        'estado': curr_state,
        'nombre_estado': state_names.get(curr_state, f"Estado {curr_state}"),
        'ventana_inicio': start_w,
        'ventana_fin': len(predicciones),
        'ventanas': ventanas,
        'duracion_seg': duracion_sec,
        'duracion_min': duracion_sec / 60.0
    })

    return tramos


def main():
    modelo_pkl = "5c_modelo_transporte_rbf_svm.pkl"
    
    if len(sys.argv) > 1:
        archivo_entrada = sys.argv[1]
    else:
        archivo_entrada = "5c_dataset_validacion_4.csv"

    # 1. Cargar el modelo .pkl
    if not os.path.exists(modelo_pkl):
        print(f"Error: No se encontró el archivo de modelo '{modelo_pkl}'.")
        return

    print(f"1. Cargando modelo desde '{modelo_pkl}'...")
    with open(modelo_pkl, 'rb') as f:
        modelo = pickle.load(f)

    state_names = modelo.get('state_names', {})
    feature_cols = modelo.get('feature_cols', [])
    window_size = modelo.get('window_size', 10)
    gamma = modelo.get('gamma', 0.08)
    C = modelo.get('C', 10.0)

    # 2. Cargar datos del viaje
    if not os.path.exists(archivo_entrada):
        print(f"Error: No se encontró el archivo '{archivo_entrada}'.")
        return

    print(f"2. Cargando datos para clasificar: '{archivo_entrada}'...")
    df = pd.read_csv(archivo_entrada)
    print(f"   -> {len(df)} ventanas temporales a evaluar")

    # 3. Realizar predicción
    print("3. Evaluando cadena de viaje...")
    try:
        predicciones, confianza = predecir_con_modelo(modelo, df)
    except Exception as e:
        print(f"Error durante la inferencia: {e}")
        return

    # 4. Guardar archivo con resultados
    df_resultado = df.copy()
    df_resultado['Estado_Predicho'] = predicciones
    df_resultado['Nombre_Estado'] = [state_names.get(p, f"Estado {p}") for p in predicciones]
    df_resultado['Nivel_Confianza'] = np.round(confianza, 4)

    salida_csv = f"{os.path.splitext(archivo_entrada)[0]}_clasificado.csv"
    df_resultado.to_csv(salida_csv, index=False)
    print(f"4. Resultados guardados en: '{salida_csv}'")

    # 5. Resumen de tramos
    print("\n" + "=" * 80)
    print("CADENA DE VIAJE RECONSTRUIDA (TRAMOS DETECTADOS)")
    print("=" * 80)
    tramos = segmentar_viaje(predicciones, window_sec=3.0, state_names=state_names)

    print(f"{'#':<4} {'Estado Detectado':<24} {'Ventanas':<20} {'Duración':<20}")
    print("-" * 80)
    for idx, t in enumerate(tramos, 1):
        print(f"{idx:<4} {t['nombre_estado']:<24} {t['ventana_inicio']:4d} a {t['ventana_fin']:4d} ({t['ventanas']:3d} vent.)   {t['duracion_seg']:5.0f} s ({t['duracion_min']:4.1f} min)")

    # 6. Distribución de tiempo
    print("\n" + "=" * 80)
    print("DISTRIBUCIÓN TOTAL DE TIEMPO POR ESTADO:")
    print("=" * 80)
    resumen = df_resultado['Estado_Predicho'].value_counts().sort_index()
    for est, count in resumen.items():
        nom = state_names.get(est, f"Estado {est}")
        seg = count * 3.0
        pct = (count / len(df_resultado)) * 100
        print(f"• {nom:<24}: {count:4d} ventanas | {seg:6.0f} s ({seg/60:4.1f} min) | {pct:5.1f}% del viaje")
    print("=" * 80)

    # 7. Evaluación de Métricas (si el dataset contiene la columna 'Estado')
    if 'Estado' in df.columns:
        evaluar_5fold_cv(
            df=df,
            feature_cols=feature_cols,
            target_col='Estado',
            window_size=window_size,
            gamma=gamma,
            C=C,
            state_names=state_names
        )


if __name__ == "__main__":
    main()