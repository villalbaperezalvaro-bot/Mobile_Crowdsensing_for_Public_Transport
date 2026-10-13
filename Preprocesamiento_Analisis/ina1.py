# =========================================================
# IMPORTACIÓN DE LIBRERÍAS
# =========================================================

# Librería para manipulación de datos tipo tablas (DataFrames)
import pandas as pd 

# Librería para operaciones matemáticas y arreglos numéricos
import numpy as np

# Función para calcular la FFT rápida (Transformada de Fourier)
# Se usa para analizar frecuencias de vibración
from scipy.fft import rfft

# Función para detectar picos dentro de una señal
from scipy.signal import find_peaks

# Modelo de Machine Learning tipo Random Forest
from sklearn.ensemble import RandomForestClassifier

# Función para dividir datos en entrenamiento y prueba
from sklearn.model_selection import train_test_split

# Métrica para medir precisión del modelo
from sklearn.metrics import accuracy_score


# =========================================================
# MÓDULO 1
# PREPROCESAMIENTO Y LIMPIEZA DE DATOS
# =========================================================

def modulo_1_simplificar_datos(ruta_csv):

    # Leer archivo CSV y convertirlo en DataFrame
    df = pd.read_csv(ruta_csv)

    # Mostrar nombres de columnas detectadas en el archivo
    print("Columnas detectadas:", df.columns.tolist())

    # -----------------------------------------------------
    # VALIDAR QUE EXISTAN LAS COLUMNAS DEL GIROSCOPIO
    # -----------------------------------------------------

    # Lista de columnas obligatorias
    columnas_giro = ['gyr_x', 'gyr_y', 'gyr_z']

    # Recorrer cada columna requerida
    for col in columnas_giro:

        # Si la columna no existe en el DataFrame
        if col not in df.columns:

            # Lanzar error indicando la columna faltante
            raise ValueError(f"Falta la columna {col}")

    # -----------------------------------------------------
    # ORDENAR DATOS POR TIEMPO
    # -----------------------------------------------------

    # Ordenar filas usando la columna Timestamp
    df = df.sort_values(by='Timestamp')

    # -----------------------------------------------------
    # CREAR MAGNITUD TOTAL DE VIBRACIÓN
    # -----------------------------------------------------

    # Calcular vibración total usando fórmula:
    # sqrt(x² + y² + z²)
    #
    # Esto combina las 3 dimensiones del giroscopio
    # en una sola señal de vibración
    df['vibracion_total'] = np.sqrt(
        df['gyr_x']**2 +
        df['gyr_y']**2 +
        df['gyr_z']**2
    )

    # -----------------------------------------------------
    # CREAR COLUMNAS MÁS SIMPLES
    # -----------------------------------------------------

    # Copiar Timestamp a una columna llamada timestamp
    df['timestamp'] = df['Timestamp']

    # Copiar Estado a unidad_id
    # Esto representa la clase o etiqueta
    df['unidad_id'] = df['Estado']

    # -----------------------------------------------------
    # RETORNAR SOLO COLUMNAS NECESARIAS
    # -----------------------------------------------------

    return df[['timestamp', 'vibracion_total', 'unidad_id']]


# =========================================================
# MÓDULO 2
# DIVISIÓN DE DATOS EN VENTANAS
# =========================================================

def modulo_2_cortar_ventanas_por_unidad(df, filas_por_ventana=500):

    # Lista donde se almacenarán las ventanas
    ventanas = []

    # -----------------------------------------------------
    # AGRUPAR DATOS POR UNIDAD
    # -----------------------------------------------------

    # Agrupa todas las filas según unidad_id
    grupos = df.groupby('unidad_id')

    # Recorrer cada grupo
    for unidad, grupo in grupos:

        # Reiniciar índices del grupo
        grupo = grupo.reset_index(drop=True)

        # Obtener cantidad total de filas
        total = len(grupo)

        # -------------------------------------------------
        # CREAR VENTANAS DE 100 FILAS
        # -------------------------------------------------

        # Recorrer datos en saltos de 100
        for i in range(0, total, filas_por_ventana):

            # Extraer segmento de 100 filas
            segmento = grupo.iloc[i:i+filas_por_ventana]

            # Verificar que sí tenga exactamente 100 filas
            if len(segmento) == filas_por_ventana:

                # Guardar ventana
                ventanas.append(segmento)

    # Retornar lista de ventanas
    return ventanas


# =========================================================
# MÓDULO 3
# EXTRACCIÓN DE CARACTERÍSTICAS (ADN)
# =========================================================

def modulo_3_extraer_adn(ventanas):

    # Lista donde se almacenarán las características
    datos = []

    # Recorrer cada ventana
    for v in ventanas:

        # -------------------------------------------------
        # OBTENER SEÑAL DE VIBRACIÓN
        # -------------------------------------------------

        # Convertir columna vibracion_total en arreglo numpy
        señal = v['vibracion_total'].values

        # Obtener etiqueta de la unidad
        # iloc[0] toma el primer valor
        unidad = v['unidad_id'].iloc[0]

        # -------------------------------------------------
        # TRANSFORMADA DE FOURIER
        # -------------------------------------------------

        # FFT convierte señal del tiempo → frecuencias
        #
        # np.abs() obtiene magnitud de frecuencias
        # / len(señal) normaliza valores
        espectro = np.abs(rfft(señal)) / len(señal)

        # -------------------------------------------------
        # CALCULAR UMBRAL DINÁMICO
        # -------------------------------------------------

        # Umbral = media + desviación estándar
        #
        # Sirve para detectar picos importantes
        threshold = np.mean(espectro) + np.std(espectro)

        # -------------------------------------------------
        # DETECTAR PICOS
        # -------------------------------------------------

        # Buscar frecuencias con amplitud mayor al umbral
        picos, _ = find_peaks(espectro, height=threshold)

        # -------------------------------------------------
        # ORDENAR PICOS MÁS IMPORTANTES
        # -------------------------------------------------

        # Ordenar picos por amplitud descendente
        #
        # [:3] toma solo los 3 más importantes
        picos = sorted(
            picos,
            key=lambda x: espectro[x],
            reverse=True
        )[:3]

        # -------------------------------------------------
        # ASEGURAR SIEMPRE 3 PICOS
        # -------------------------------------------------

        # Si hay menos de 3 picos
        while len(picos) < 3:

            # Agregar 0 como relleno
            picos.append(0)

        # -------------------------------------------------
        # CALCULAR ENERGÍA TOTAL
        # -------------------------------------------------

        # Energía = suma de señal²
        #
        # Representa intensidad total de vibración
        energia = np.sum(señal**2)

        # -------------------------------------------------
        # GUARDAR CARACTERÍSTICAS
        # -------------------------------------------------

        datos.append([
            picos[0],   # frecuencia principal
            picos[1],   # segunda frecuencia
            picos[2],   # tercera frecuencia
            energia,    # energía total
            unidad      # etiqueta
        ])

    # -----------------------------------------------------
    # CONVERTIR A DATAFRAME
    # -----------------------------------------------------

    return pd.DataFrame(datos, columns=[
        'pico_1',
        'pico_2',
        'pico_3',
        'energia',
        'unidad_id'
    ])


# =========================================================
# MÓDULO 4
# ENTRENAMIENTO DEL MODELO
# =========================================================

def entrenar_modelo(df):

    # -----------------------------------------------------
    # SEPARAR VARIABLES
    # -----------------------------------------------------

    # Variables de entrada (features)
    X = df[['pico_1', 'pico_2', 'pico_3', 'energia']]

    # Variable objetivo (clase)
    y = df['unidad_id']

    # -----------------------------------------------------
    # DIVIDIR DATOS
    # -----------------------------------------------------

    # 80% entrenamiento
    # 20% prueba
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42
    )

    # -----------------------------------------------------
    # CREAR RANDOM FOREST
    # -----------------------------------------------------

    modelo = RandomForestClassifier(

        # Número de árboles
        n_estimators=200,

        # Balancear clases automáticamente
        class_weight='balanced',

        # Semilla aleatoria fija
        random_state=42
    )

    # -----------------------------------------------------
    # ENTRENAR MODELO
    # -----------------------------------------------------

    modelo.fit(X_train, y_train)

    # -----------------------------------------------------
    # HACER PREDICCIONES
    # -----------------------------------------------------

    pred = modelo.predict(X_test)

    # -----------------------------------------------------
    # MOSTRAR PRECISIÓN
    # -----------------------------------------------------

    print("Precisión:", accuracy_score(y_test, pred) * 100)

    # -----------------------------------------------------
    # REPORTE DETALLADO
    # -----------------------------------------------------

    from sklearn.metrics import classification_report

    print("\nReporte de clasificación:")

    print(classification_report(y_test, pred))

    # Retornar modelo entrenado
    return modelo


# =========================================================
# MAIN
# PUNTO DE ENTRADA PRINCIPAL
# =========================================================

if __name__ == "__main__":

    # Ruta del archivo CSV
    ruta = r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\datos\giro_20251118_112033__1763486433675.csv_1763486506.csv"

    # Mensaje inicial
    print("Procesando archivo...")

    # -----------------------------------------------------
    # MÓDULO 1
    # LIMPIEZA Y PREPROCESAMIENTO
    # -----------------------------------------------------

    df = modulo_1_simplificar_datos(ruta)

    # -----------------------------------------------------
    # MÓDULO 2
    # CREACIÓN DE VENTANAS
    # -----------------------------------------------------

    ventanas = modulo_2_cortar_ventanas_por_unidad(df)

    # -----------------------------------------------------
    # VALIDAR QUE EXISTAN VENTANAS
    # -----------------------------------------------------

    if len(ventanas) == 0:

        print("❌ ERROR: No hay suficientes datos")

        # Terminar programa
        exit()

    # -----------------------------------------------------
    # MÓDULO 3
    # EXTRAER ADN DE VIBRACIÓN
    # -----------------------------------------------------

    adn = modulo_3_extraer_adn(ventanas)

    # -----------------------------------------------------
    # MOSTRAR DISTRIBUCIÓN DE CLASES
    # -----------------------------------------------------

    print("\nDistribución de clases:")

    # Contar cuántas muestras hay por clase
    print(adn['unidad_id'].value_counts())

    # -----------------------------------------------------
    # MÓDULO 4
    # ENTRENAR IA
    # -----------------------------------------------------

    modelo = entrenar_modelo(adn)