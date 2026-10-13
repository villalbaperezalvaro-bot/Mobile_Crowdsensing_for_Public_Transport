import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.fft import rfft, rfftfreq
from scipy.signal import find_peaks
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.metrics import accuracy_score, classification_report
from matplotlib.widgets import Slider


# ==============================
# MÓDULO 1: Cargar y Normalizar Acelerómetro
# ==============================
def modulo_1_simplificar_datos(ruta_csv):
    df = pd.read_csv(ruta_csv)
    df.columns = df.columns.str.strip()

    # Mapeo flexible de nombres para Acelerómetro
    col_map = {}
    for col in df.columns:
        c_low = col.lower().replace("_", "")
        if c_low in ['accelx', 'accx', 'acelx']:
            col_map[col] = 'acc_x'
        elif c_low in ['accely', 'accy', 'acely']:
            col_map[col] = 'acc_y'
        elif c_low in ['accelz', 'accz', 'acelz']:
            col_map[col] = 'acc_z'
        elif c_low in ['timestamp', 'time', 'tiempo']:
            col_map[col] = 'timestamp'
        elif c_low in ['estado', 'unidad_id', 'unidad', 'label']:
            col_map[col] = 'unidad_id'

    df = df.rename(columns=col_map)

    # Validación de columnas requeridas
    columnas_req = ['acc_x', 'acc_y', 'acc_z', 'timestamp', 'unidad_id']
    faltantes = [c for c in columnas_req if c not in df.columns]
    if faltantes:
        raise ValueError(
            f"Faltan columnas requeridas: {faltantes}\n"
            f"Columnas detectadas en el CSV: {list(df.columns)}"
        )

    # Ordenar por timestamp
    df = df.sort_values(by='timestamp')

    # Magnitud de aceleración total (vibración bruta)
    df['vibracion_total'] = np.sqrt(
        df['acc_x']**2 +
        df['acc_y']**2 +
        df['acc_z']**2
    )

    return df[['timestamp', 'vibracion_total', 'unidad_id']]


# ==============================
# MÓDULO 2: Segmentación (3s @ 50 Hz = 150 Muestras)
# ==============================
def modulo_2_cortar_ventanas_por_unidad(df, filas_por_ventana=150):
    ventanas = []
    grupos = df.groupby('unidad_id')

    for unidad, grupo in grupos:
        grupo = grupo.reset_index(drop=True)
        total = len(grupo)

        # Extraer segmentos exactos de 150 muestras
        for i in range(0, total - filas_por_ventana + 1, filas_por_ventana):
            segmento = grupo.iloc[i:i + filas_por_ventana]
            ventanas.append(segmento)

    return ventanas


# ==============================
# VISOR INTERACTIVO
# ==============================
def visor_interactivo(ventanas, fs=50):
    if not ventanas:
        print("⚠️ No hay ventanas generadas para visualizar.")
        return

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 6))
    plt.subplots_adjust(bottom=0.25)

    idx = 0
    señal_raw = ventanas[idx]['vibracion_total'].values

    # PASO 1: Restar gravedad (componente DC)
    señal_ac = señal_raw - np.mean(señal_raw)

    # PASO 2: FFT y Espectro de Potencia
    n = len(señal_ac)
    freqs = rfftfreq(n, d=1.0/fs)
    potencia = (np.abs(rfft(señal_ac)) ** 2) / n

    # Graficar Señal Dinámica (AC)
    linea1, = ax1.plot(señal_ac, color='tab:blue')
    ax1.set_title("Señal Dinámica AC (Gravedad Restada)")
    ax1.set_xlabel("Muestras (3s @ 50Hz = 150 pts)")
    ax1.set_ylabel("Aceleración Residual (m/s²)")
    ax1.grid(True)

    # Graficar Espectro de Potencia
    linea2, = ax2.plot(freqs, potencia, color='tab:red')
    ax2.set_title("Espectro de Potencia (|FFT|² / N)")
    ax2.set_xlabel("Frecuencia (Hz)")
    ax2.set_ylabel("Potencia / Energía")
    ax2.grid(True)

    # Slider
    ax_slider = plt.axes([0.2, 0.1, 0.6, 0.03])
    max_val = max(0, len(ventanas) - 1)

    slider = Slider(
        ax_slider,
        'Ventana',
        0,
        max_val,
        valinit=0,
        valstep=1 if max_val > 0 else 0
    )

    def actualizar(val):
        idx_act = int(slider.val)
        s_raw = ventanas[idx_act]['vibracion_total'].values
        s_ac_act = s_raw - np.mean(s_raw)
        n_act = len(s_ac_act)
        freqs_act = rfftfreq(n_act, d=1.0/fs)
        pot_act = (np.abs(rfft(s_ac_act)) ** 2) / n_act

        linea1.set_ydata(s_ac_act)
        linea1.set_xdata(range(n_act))
        ax1.relim()
        ax1.autoscale_view()

        linea2.set_ydata(pot_act)
        linea2.set_xdata(freqs_act)
        ax2.relim()
        ax2.autoscale_view()

        fig.canvas.draw_idle()

    slider.on_changed(actualizar)
    fig.slider_ref = slider
    plt.show()


# ==============================
# MÓDULO 3: Extracción de Huella Digital (ADN)
# ==============================
def modulo_3_extraer_adn(ventanas, fs=50):
    datos = []

    for v in ventanas:
        señal_raw = v['vibracion_total'].values
        unidad = v['unidad_id'].iloc[0]

        # PASO 1: Restar la gravedad (Remover componente DC / 0 Hz)
        señal_ac = señal_raw - np.mean(señal_raw)

        # PASO 2: FFT y Espectro de Potencia
        n = len(señal_ac)
        freqs = rfftfreq(n, d=1.0/fs)
        fft_vals = rfft(señal_ac)
        espectro_potencia = (np.abs(fft_vals) ** 2) / n

        # PASO 3: Umbral dinámico y detección de picos dominantes
        threshold = np.mean(espectro_potencia) + np.std(espectro_potencia)
        picos_idx, _ = find_peaks(espectro_potencia, height=threshold)

        # Ordenar picos por potencia descendente
        picos_idx_ordenados = sorted(picos_idx, key=lambda x: espectro_potencia[x], reverse=True)[:3]

        picos_freq = [freqs[i] for i in picos_idx_ordenados]
        picos_power = [espectro_potencia[i] for i in picos_idx_ordenados]

        # Rellenar con 0.0 si hay menos de 3 picos detectados
        while len(picos_freq) < 3:
            picos_freq.append(0.0)
            picos_power.append(0.0)

        # Energía espectral total de la ventana
        energia_total = np.sum(espectro_potencia)

        datos.append([
            picos_freq[0], picos_power[0],
            picos_freq[1], picos_power[1],
            picos_freq[2], picos_power[2],
            energia_total,
            unidad
        ])

    columnas = [
        'freq_pico_1', 'power_pico_1',
        'freq_pico_2', 'power_pico_2',
        'freq_pico_3', 'power_pico_3',
        'energia_total', 'unidad_id'
    ]
    return pd.DataFrame(datos, columns=columnas)


# ==============================
# MÓDULO 4: Clasificador Shazam (3-FCV) y Exportación CSV
# ==============================
def entrenar_y_evaluar_modelo(df_adn, ruta_salida_csv=None, n_splits=3):
    # Identificar y filtrar clases con menos muestras que el número de folds (3)
    conteo_clases = df_adn['unidad_id'].value_counts()
    clases_validas = conteo_clases[conteo_clases >= n_splits].index

    clases_ignoradas = conteo_clases[conteo_clases < n_splits]
    if not clases_ignoradas.empty:
        print(f"\n⚠️ Clases omitidas por tener menos de {n_splits} muestras para 3-FCV:")
        for cls, cnt in clases_ignoradas.items():
            print(f"   - Unidad {cls}: {cnt} muestra(s)")

    # Filtrar el DataFrame para la validación cruzada
    df_filtrado = df_adn[df_adn['unidad_id'].isin(clases_validas)].copy()

    if df_filtrado.empty:
        print("❌ ERROR: No hay clases con suficientes muestras para entrenar.")
        return None

    X = df_filtrado.drop(columns=['unidad_id'])
    y = df_filtrado['unidad_id']

    # Configuración de 3-Fold Stratified Cross-Validation
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    modelo = RandomForestClassifier(
        n_estimators=200, class_weight='balanced', random_state=42
    )

    # Evaluación cruzada
    y_pred = cross_val_predict(modelo, X, y, cv=skf)

    # Agregar predicciones al DataFrame filtrado
    df_filtrado['unidad_predicha'] = y_pred

    print(f"\n=== Resultados 3-Fold Cross-Validation (3-FCV) ===")
    print("Precisión global (Accuracy):", round(accuracy_score(y, y_pred) * 100, 2), "%")
    print("\nReporte de Clasificación:")
    print(classification_report(y, y_pred, zero_division=0))

    # Guardar archivo CSV con características y resultados
    if ruta_salida_csv:
        df_filtrado.to_csv(ruta_salida_csv, index=False)
        print(f"💾 Archivo CSV con características y predicciones guardado en:\n   -> {ruta_salida_csv}")

    # Entrenar el modelo final con todas las clases válidas
    modelo.fit(X, y)
    return modelo


# ==============================
# EJECUCIÓN
# ==============================
if __name__ == "__main__":
    ruta_entrada = r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\DATASET\DATOS CRUDOS 1\10\acel_20251211_095629_u99_1765468589296.csv_1765476114.csv"
    ruta_salida_csv = r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\DATASET\DATOS CRUDOS 1\10\caracteristicas_adn.csv"

    print("Procesando archivo CSV de acelerómetro...")
    df = modulo_1_simplificar_datos(ruta_entrada)

    ventanas = modulo_2_cortar_ventanas_por_unidad(df, filas_por_ventana=150)

    if not ventanas:
        print("❌ ERROR: No se generaron ventanas de 150 muestras.")
    else:
        print(f" Ventanas de 3s (150 muestras) generadas: {len(ventanas)}")

        # Extracción de ADN
        adn = modulo_3_extraer_adn(ventanas, fs=50)

        print("\nDistribución de muestras por unidad:")
        print(adn['unidad_id'].value_counts())

        # Entrenamiento y guardado de resultados a CSV
        modelo = entrenar_y_evaluar_modelo(adn, ruta_salida_csv=ruta_salida_csv)

        # Visualización interactiva
        visor_interactivo(ventanas, fs=50)