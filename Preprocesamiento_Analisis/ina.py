import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.fft import rfft
from scipy.signal import find_peaks
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from matplotlib.widgets import Slider


# ==============================
# MÓDULO 1: Cargar y Normalizar
# ==============================
def modulo_1_simplificar_datos(ruta_csv):
    df = pd.read_csv(ruta_csv)

    print("Columnas detectadas:", df.columns.tolist())

    # Eliminar espacios extra en los nombres de las columnas
    df.columns = df.columns.str.strip()

    # --------------------------
    # Detectar columnas de giroscopio
    # --------------------------
    if all(col in df.columns for col in ['GyroX', 'GyroY', 'GyroZ']):
        df = df.rename(columns={
            'GyroX': 'gyr_x',
            'GyroY': 'gyr_y',
            'GyroZ': 'gyr_z'
        })
    elif all(col in df.columns for col in ['gyr_x', 'gyr_y', 'gyr_z']):
        pass
    else:
        raise ValueError(
            f"No se encontraron columnas de giroscopio válidas.\n"
            f"Columnas disponibles: {df.columns.tolist()}"
        )

    # --------------------------
    # Validar Timestamp y Estado
    # --------------------------
    if 'Timestamp' not in df.columns:
        raise ValueError("Falta la columna Timestamp")

    if 'Estado' not in df.columns:
        raise ValueError("Falta la columna Estado")

    # --------------------------
    # Ordenar y procesar magnitud
    # --------------------------
    df = df.sort_values(by='Timestamp')

    df['vibracion_total'] = np.sqrt(
        df['gyr_x']**2 +
        df['gyr_y']**2 +
        df['gyr_z']**2
    )

    df['timestamp'] = df['Timestamp']
    df['unidad_id'] = df['Estado']

    return df[['timestamp', 'vibracion_total', 'unidad_id']]


# ==============================
# MÓDULO 2: Segmentación por Ventanas
# ==============================
def modulo_2_cortar_ventanas_por_unidad(df, filas_por_ventana=150):
    ventanas = []

    # Agrupar por unidad (Estado)
    grupos = df.groupby('unidad_id')

    for unidad, grupo in grupos:
        grupo = grupo.reset_index(drop=True)
        total = len(grupo)

        # Si el grupo tiene menos datos que la ventana configurada pero no está vacío, tomar todo el grupo
        if 0 < total < filas_por_ventana:
            ventanas.append(grupo)
            continue

        for i in range(0, total, filas_por_ventana):
            segmento = grupo.iloc[i:i+filas_por_ventana]

            if len(segmento) == filas_por_ventana:
                ventanas.append(segmento)

    return ventanas


# ==============================
# VISOR INTERACTIVO
# ==============================
def visor_interactivo(ventanas):
    if not ventanas:
        print("⚠️ No hay ventanas generadas para visualizar.")
        return

    # Crear figura principal
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
    plt.subplots_adjust(bottom=0.25)

    idx = 0
    señal = ventanas[idx]['vibracion_total'].values
    espectro = np.abs(rfft(señal)) / len(señal)

    # ----------------------------
    # GRAFICAR SEÑAL
    # ----------------------------
    linea1, = ax1.plot(señal)
    ax1.set_title("Señal de Vibración")
    ax1.set_xlabel("Muestras")
    ax1.set_ylabel("Amplitud")
    ax1.grid(True)

    # ----------------------------
    # GRAFICAR FFT
    # ----------------------------
    linea2, = ax2.plot(espectro)
    ax2.set_title("FFT - Espectro de Frecuencias")
    ax2.set_xlabel("Frecuencia")
    ax2.set_ylabel("Magnitud")
    ax2.grid(True)

    # ----------------------------
    # SLIDER
    # ----------------------------
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
        señal_act = ventanas[idx_act]['vibracion_total'].values
        espectro_act = np.abs(rfft(señal_act)) / len(señal_act)

        # Actualizar señal
        linea1.set_ydata(señal_act)
        linea1.set_xdata(range(len(señal_act)))
        ax1.relim()
        ax1.autoscale_view()

        # Actualizar FFT
        linea2.set_ydata(espectro_act)
        linea2.set_xdata(range(len(espectro_act)))
        ax2.relim()
        ax2.autoscale_view()

        fig.canvas.draw_idle()

    slider.on_changed(actualizar)

    # Mantener referencia viva del slider para evitar congelamientos en la UI
    fig.slider_ref = slider

    plt.show()


# ==============================
# MÓDULO 3: Extracción de Características
# ==============================
def modulo_3_extraer_adn(ventanas):
    datos = []

    for v in ventanas:
        señal = v['vibracion_total'].values
        unidad = v['unidad_id'].iloc[0]

        espectro = np.abs(rfft(señal)) / len(señal)

        # Umbral dinámico
        threshold = np.mean(espectro) + np.std(espectro)

        picos, _ = find_peaks(espectro, height=threshold)
        picos = sorted(picos, key=lambda x: espectro[x], reverse=True)[:3]

        while len(picos) < 3:
            picos.append(0)

        energia = np.sum(señal**2)
        print(picos)
        datos.append([picos[0], picos[1], picos[2], energia, unidad])

    return pd.DataFrame(datos, columns=[
        'pico_1', 'pico_2', 'pico_3', 'energia', 'unidad_id'
    ])


# ==============================
# MÓDULO 4: Entrenamiento
# ==============================
def entrenar_modelo(df):
    X = df[['pico_1', 'pico_2', 'pico_3', 'energia']]
    y = df['unidad_id']

    # Manejar el split dependiendo de la cantidad total de muestras
    if len(df) < 5:
        print("\n⚠️ Advertencia: Muy pocos datos para un train/test split. Se entrenará con todos los datos.")
        X_train, X_test, y_train, y_test = X, X, y, y
    else:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

    modelo = RandomForestClassifier(
        n_estimators=200,
        class_weight='balanced',
        random_state=42
    )
    modelo.fit(X_train, y_train)

    pred = modelo.predict(X_test)

    print("\nPrecisión:", accuracy_score(y_test, pred) * 100)
    print("\nReporte de clasificación:")
    print(classification_report(y_test, pred, zero_division=0))

    return modelo


# ==============================
# EJECUCIÓN PRINCIPAL
# ==============================
if __name__ == "__main__":

    ruta = r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\datos\100\Dataset_GIRO_ALINEADO.csv"

    print("Procesando archivo...")
    df = modulo_1_simplificar_datos(ruta)

    ventanas = modulo_2_cortar_ventanas_por_unidad(df)

    if len(ventanas) == 0:
        print("❌ ERROR: No se pudieron extraer ventanas del archivo.")
    else:
        print(f" Ventanas generadas correctamente: {len(ventanas)}")
        
        # Muestra el visor interactivo
        visor_interactivo(ventanas)

        # Extrae características y entrena
        adn = modulo_3_extraer_adn(ventanas)

        print("\nDistribución de clases:")
        print(adn['unidad_id'].value_counts())

        modelo = entrenar_modelo(adn)