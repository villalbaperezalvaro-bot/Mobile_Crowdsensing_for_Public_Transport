import os
import sys
import pickle
import numpy as np
import pandas as pd


def predecir_con_modelo(modelo, df):
    """
    Ejecuta el pipeline de inferencia matricial RBF-SVM usando los pesos del .pkl
    """
    # 1. Validar presencia de características
    cols_requeridas = modelo['feature_cols']
    cols_faltantes = [c for c in cols_requeridas if c not in df.columns]
    if cols_faltantes:
        raise ValueError(f"El dataset no contiene las columnas requeridas: {cols_faltantes}")

    # 2. Contexto temporal (Media Móvil)
    X_smooth = df[cols_requeridas].rolling(
        window=modelo.get('window_size', 10), 
        min_periods=1
    ).mean().values
    
    # 3. Estandarización Z-Score
    X_scaled = (X_smooth - modelo['mean']) / modelo['std']
    
    # 4. Kernel RBF vectorizado de prueba vs entrenamiento: exp(-gamma * ||x - x'||^2)
    dists = (
        np.sum(X_scaled**2, axis=1, keepdims=True) 
        + np.sum(modelo['X_train']**2, axis=1) 
        - 2 * np.dot(X_scaled, modelo['X_train'].T)
    )
    K_test = np.exp(-modelo['gamma'] * np.maximum(0, dists))
    
    # 5. Puntuaciones de decisión y asignación de clase
    scores = np.dot(K_test, modelo['Alpha'])
    clases = np.asarray(modelo['classes'])
    predicciones = clases[np.argmax(scores, axis=1)]
    
    # 6. Estimación de confianza vía Softmax sobre los scores de decisión
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

    # Tramo final
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
    
    # Toma el archivo pasado por parámetro o usa el archivo por defecto
    if len(sys.argv) > 1:
        archivo_entrada = sys.argv[1]  # Corregido: sys.argv[1] en lugar de sys.argv
    else:
        archivo_entrada = "5c_dataset_validacion_1.csv"

    # 1. Cargar el modelo .pkl
    if not os.path.exists(modelo_pkl):
        print(f"Error: No se encontró el archivo de modelo '{modelo_pkl}'.")
        return

    print(f"1. Cargando modelo desde '{modelo_pkl}'...")
    with open(modelo_pkl, 'rb') as f:
        modelo = pickle.load(f)

    state_names = modelo.get('state_names', {})

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
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()