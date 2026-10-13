import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.fft import rfft
from scipy.signal import find_peaks
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from matplotlib.widgets import Slider

# ==============================
# MÓDULO 1 (CORREGIDO PARA EVITAR ERROR DE TEXTO)
# ==============================
def modulo_1_simplificar_datos(ruta_csv):
    df = pd.read_csv(ruta_csv)

    print("Columnas detectadas:", df.columns.tolist())

    # Validar columnas del acelerómetro y estado
    columnas_giro = ['AccelX', 'AccelY', 'AccelZ']
    for col in columnas_giro:
        if col not in df.columns:
            raise ValueError(f"Falta la columna {col}")

    # Convertir explícitamente las columnas a numéricas (por si se leyeron como texto)
    for col in columnas_giro:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Opcional: limpiar filas que tengan NaNs resultantes de la conversión
    df = df.dropna(subset=columnas_giro).reset_index(drop=True)

    # Ordenar por tiempo
    df = df.sort_values(by='Timestamp')

    # Crear vibración total usando la magnitud de la aceleración
    df['vibracion_total'] = np.sqrt(
        df['AccelX']**2 +
        df['AccelY']**2 +
        df['AccelZ']**2
    )

    df['timestamp'] = df['Timestamp']
    df['unidad_id'] = df['Estado']
   # df['velocidad'] = df['Velocidad'] if 'Velocidad' in df.columns else 0

    return df[['timestamp', 'vibracion_total', 'unidad_id']]


# ==============================
# MÓDULO 2: CORTAR VENTANAS DINÁMICO (ADAPTABLE A CUALQUIER META Y ESTADOS)
# ==============================
def modulo_2_cortar_ventanas_por_unidad(df, filas_por_ventana=150, ventanas_por_clase=300):
    ventanas = []
    
    # Detecta automáticamente todos los estados que existan en el archivo (sea 0, 1, 2 o de 0 a 8)
    estados_unicos = sorted(df['unidad_id'].unique())
    print(f"Estados detectados en el dataset: {estados_unicos}")

    for estado in estados_unicos:
        # Aislar todas las filas de este estado de forma independiente
        grupo_estado = df[df['unidad_id'] == estado].reset_index(drop=True)
        total_muestras = len(grupo_estado)
        
        print(f"\nProcesando Estado {estado} | Muestras disponibles: {total_muestras}")
        
        if total_muestras < filas_por_ventana:
            print(f" ❌ Advertencia: El estado {estado} tiene muy pocas muestras ({total_muestras}) para una ventana de {filas_por_ventana}.")
            continue

        # Opcional: Si quieres usar traslape automático cuando falten muestras para llegar a tu meta (ej. 300)
        espacio_disponible = total_muestras - filas_por_ventana
        if espacio_disponible <= 0:
            paso = 1
        else:
            # Si hay suficientes muestras, avanza sin traslape (paso = 150). 
            # Si faltan, calcula un paso menor para alcanzar las ventanas deseadas.
            paso = min(filas_por_ventana, max(1, espacio_disponible // (ventanas_por_clase - 1)))

        ventanas_creadas = 0
        inicio = 0
        
        while ventanas_creadas < ventanas_por_clase and (inicio + filas_por_ventana) <= total_muestras:
            segmento = grupo_estado.iloc[inicio:inicio + filas_por_ventana].copy()
            ventanas.append(segmento)
            ventanas_creadas += 1
            inicio += paso  

        print(f" -> Ventanas logradas para el estado {estado}: {ventanas_creadas} / {ventanas_por_clase}")

    print(f"\n¡Proceso completado! Total general de ventanas recolectadas: {len(ventanas)}")
    return ventanas



# ==============================
# VISOR INTERACTIVO
# ==============================
def visor_interactivo(ventanas):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
    plt.subplots_adjust(bottom=0.25)

    idx = 0
    señal = ventanas[idx]['vibracion_total'].values
    espectro = np.abs(rfft(señal)) / len(señal)

    linea1, = ax1.plot(señal)
    ax1.set_title("Señal de Vibración (Acelerómetro)")
    ax1.set_xlabel("Muestras")
    ax1.set_ylabel("Amplitud")
    ax1.grid(True)

    linea2, = ax2.plot(espectro)
    ax2.set_title("FFT - Espectro")
    ax2.set_xlabel("Frecuencia")
    ax2.set_ylabel("Magnitud")
    ax2.grid(True)

    ax_slider = plt.axes([0.2, 0.1, 0.6, 0.03])
    slider = Slider(ax_slider, 'Ventana', 0, len(ventanas)-1, valinit=0, valstep=1)

    def actualizar(val):
        idx = int(slider.val)
        señal = ventanas[idx]['vibracion_total'].values
        espectro = np.abs(rfft(señal)) / len(señal)

        linea1.set_ydata(señal)
        linea1.set_xdata(range(len(señal)))
        ax1.relim()
        ax1.autoscale_view()

        linea2.set_ydata(espectro)
        linea2.set_xdata(range(len(espectro)))
        ax2.relim()
        ax2.autoscale_view()

        fig.canvas.draw_idle()

    slider.on_changed(actualizar)
    plt.show()


# ==============================
# MÓDULO 3: EXTRAER ADN Y GUARDAR CSV
# ==============================
def modulo_3_extraer_adn(ventanas):
    datos = []

    for v in ventanas:
        señal = v['vibracion_total'].values
        unidad = v['unidad_id'].iloc[0]  # Estado

        espectro = np.abs(rfft(señal)) / len(señal)

        threshold = np.mean(espectro) + np.std(espectro)
        picos, _ = find_peaks(espectro, height=threshold)

        picos = sorted(picos, key=lambda x: espectro[x], reverse=True)[:3]

        while len(picos) < 3:
            picos.append(0)

        energia = np.sum(señal**2)
      #  print(energia)
        
        # Características solicitadas: [picos[0], picos[1], picos[2], energia, estado]
        datos.append([picos[0], picos[1], picos[2], energia, unidad])

    df_adn = pd.DataFrame(datos, columns=[
        'pico_1', 'pico_2', 'pico_3', 'energia', 'estado'
    ])

    # Guardar en la ruta especificada
    directorio_salida = r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\salidad_FFT"
    os.makedirs(directorio_salida, exist_ok=True)
    
    ruta_salida = os.path.join(directorio_salida, "PRUEBA.csv")
    df_adn.to_csv(ruta_salida, index=False)
    print(f"\nArchivo CSV de características guardado exitosamente en:\n{ruta_salida}")

    return df_adn


# ==============================
# MÓDULO 4: ENTRENAR MODELO
# ==============================
def entrenar_modelo(df):
    X = df[['pico_1', 'pico_2', 'pico_3', 'energia']]
    y = df['estado']

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

    print("Precisión:", accuracy_score(y_test, pred) * 100)
    
    from sklearn.metrics import classification_report
    print("\nReporte de clasificación:")
    print(classification_report(y_test, pred))

    return modelo
#C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\datos\Dataset_6.csv

# ==============================
# MAIN
# ==============================
if __name__ == "__main__":
    # Ajusta esta ruta al archivo CSV limpio combinado que vayas a procesar
    ruta = r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\datos\Dataset_6.csv"

    print("Procesando archivo...")

    try:
        df = modulo_1_simplificar_datos(ruta)
    except FileNotFoundError:
        print(f"❌ ERROR: No se encontró el archivo en la ruta: {ruta}")
        exit()

    ventanas = modulo_2_cortar_ventanas_por_unidad(df)

    if len(ventanas) == 0:
        print("❌ ERROR: No hay suficientes datos para armar ventanas de 150 filas.")
        exit()

    visor_interactivo(ventanas)

    adn = modulo_3_extraer_adn(ventanas)

    print("\nDistribución de clases:")
    print(adn['estado'].value_counts())

    modelo = entrenar_modelo(adn)