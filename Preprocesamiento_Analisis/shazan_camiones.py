
  #  r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\DATASET\DATOS CRUDOS 1\4\acel_20251211_071744_u99_1765459064135.csv_1765463911.csv"

   
 #   r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\DATASET\DATOS CRUDOS 1\4\.csv\salida_acel"


import os
import glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from scipy.fft import rfft, rfftfreq
from scipy.signal import find_peaks, detrend, butter, filtfilt

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report


# ============================================================
# CONFIGURACIÓN
# ============================================================

# Archivo de entrada actual.
# El CSV proporcionado contiene:
# Timestamp, AccelX, AccelY, AccelZ, Estado
RUTA_ENTRADA = (
    r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\datos\100"
    r"acel_20251211_071744_u99_1765459064135.csv"
)

# Para un archivo individual, asigna aquí el ID REAL de la unidad.
# NO uses Estado como identificador de unidad.
UNIDAD_ID_MANUAL = "unidad_01"

# Para procesar una carpeta completa de unidades, cambia a True.
PROCESAR_CARPETA = False

CARPETA_ENTRADA = (
    r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\datos\100\unidades"
)

PATRON_CSV = "*.csv"


# ============================================================
# PARÁMETROS DE SEÑAL
# ============================================================

FS_OBJETIVO = 50

DURACION_VENTANA_SEG = 3

MUESTRAS_POR_VENTANA = (
    FS_OBJETIVO *
    DURACION_VENTANA_SEG
)

TRASLAPE_PCT = 0

# No interpolar sobre huecos muy grandes.
MAX_GAP_INTERPOLACION_SEG = 0.5

# Para evitar que la componente continua/gravedad domine
# el espectro, se elimina la media de cada ventana.
QUITAR_MEDIA_FFT = True

# Filtro pasa-altas opcional para aislar vibración dinámica.
# Se deja desactivado por defecto para no alterar la señal.
USAR_PASA_ALTAS = False
FREC_CORTE_PASA_ALTAS = 0.5


# ============================================================
# SALIDAS
# ============================================================

CARPETA_SALIDA = (
    r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\salida_huella_unidad"
)

ARCHIVO_CARACTERISTICAS = os.path.join(
    CARPETA_SALIDA,
    "caracteristicas_huella_unidad.csv"
)

ARCHIVO_VENTANAS = os.path.join(
    CARPETA_SALIDA,
    "ventanas_3s_50hz.csv"
)


# ============================================================
# LECTURA Y VALIDACIÓN
# ============================================================

def cargar_csv(ruta):
    df = pd.read_csv(ruta)

    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
    )

    requeridas = [
        "Timestamp",
        "AccelX",
        "AccelY",
        "AccelZ"
    ]

    faltantes = [
        c for c in requeridas
        if c not in df.columns
    ]

    if faltantes:
        raise ValueError(
            f"Faltan columnas en {ruta}: {faltantes}\n"
            f"Columnas disponibles: {df.columns.tolist()}"
        )

    if "Estado" not in df.columns:
        df["Estado"] = -1

    df["Timestamp"] = pd.to_datetime(
        df["Timestamp"],
        errors="coerce"
    )

    for c in ["AccelX", "AccelY", "AccelZ", "Estado"]:
        df[c] = pd.to_numeric(
            df[c],
            errors="coerce"
        )

    df = (
        df.dropna(
            subset=[
                "Timestamp",
                "AccelX",
                "AccelY",
                "AccelZ"
            ]
        )
        .sort_values("Timestamp")
        .reset_index(drop=True)
    )

    return df


# ============================================================
# IDENTIFICAR HUECOS TEMPORALES
# ============================================================

def dividir_por_huecos(
    df,
    max_gap_seg=0.5
):
    """
    Divide el registro en segmentos cuando existe un hueco
    demasiado grande. Así evitamos interpolar minutos de datos
    faltantes artificialmente.
    """

    if len(df) < 2:
        return [df.copy()]

    dt = (
        df["Timestamp"]
        .diff()
        .dt.total_seconds()
    )

    cortes = np.where(
        dt.fillna(0).to_numpy()
        > max_gap_seg
    )[0]

    if len(cortes) == 0:
        return [df.copy()]

    segmentos = []

    inicio = 0

    for corte in cortes:
        segmento = df.iloc[
            inicio:corte
        ].copy()

        if not segmento.empty:
            segmentos.append(segmento)

        inicio = corte

    ultimo = df.iloc[
        inicio:
    ].copy()

    if not ultimo.empty:
        segmentos.append(ultimo)

    return segmentos


# ============================================================
# RESAMPLE A 50 Hz
# ============================================================

def normalizar_a_50hz(df):
    """
    Convierte el acelerómetro a una rejilla uniforme de 50 Hz.

    50 Hz => paso temporal de 20 ms.

    Se procesa por segmentos para no interpolar grandes huecos.
    """

    segmentos = dividir_por_huecos(
        df,
        MAX_GAP_INTERPOLACION_SEG
    )

    resultados = []

    for seg in segmentos:

        if len(seg) < 2:
            continue

        seg = seg.copy()

        seg = seg.set_index(
            "Timestamp"
        )

        numericas = [
            "AccelX",
            "AccelY",
            "AccelZ"
        ]

        # ----------------------------------------------------
        # Promediar muestras que caen en el mismo instante
        # de la rejilla temporal.
        # ----------------------------------------------------

        accel = (
            seg[numericas]
            .resample("20ms")
            .mean()
        )

        # ----------------------------------------------------
        # Interpolar pequeños huecos.
        # ----------------------------------------------------

        accel = (
            accel.interpolate(
                method="time",
                limit_direction="both"
            )
        )

        # ----------------------------------------------------
        # Estado:
        # tomar el estado más cercano/último.
        # Estado es solo metadato de actividad humana.
        # NO es la etiqueta de unidad.
        # ----------------------------------------------------

        estado = (
            seg["Estado"]
            .resample("20ms")
            .agg(
                lambda s: (
                    s.mode().iloc[0]
                    if not s.mode().empty
                    else np.nan
                )
            )
        )

        estado = (
            estado.reindex(
                accel.index
            )
            .ffill()
            .bfill()
        )

        out = accel.copy()

        out["Estado"] = estado

        out = (
            out.reset_index()
        )

        resultados.append(
            out
        )

    if not resultados:
        return pd.DataFrame(
            columns=[
                "Timestamp",
                "AccelX",
                "AccelY",
                "AccelZ",
                "Estado"
            ]
        )

    return pd.concat(
        resultados,
        ignore_index=True
    )


# ============================================================
# MAGNITUD
# ============================================================

def calcular_magnitud(
    x,
    y,
    z
):
    return np.sqrt(
        x ** 2 +
        y ** 2 +
        z ** 2
    )


# ============================================================
# FILTRO PASA ALTAS OPCIONAL
# ============================================================

def filtrar_dinamica(
    señal,
    fs,
    frecuencia_corte
):
    """
    Pasa-altas Butterworth para eliminar componentes muy lentas.
    """

    señal = np.asarray(
        señal,
        dtype=float
    )

    if len(señal) < 15:
        return señal.copy()

    wn = frecuencia_corte / (
        fs / 2
    )

    if not 0 < wn < 1:
        return señal.copy()

    b, a = butter(
        3,
        wn,
        btype="highpass"
    )

    return filtfilt(
        b,
        a,
        señal
    )


# ============================================================
# FFT
# ============================================================

def extraer_fft(
    señal,
    fs
):
    """
    Calcula FFT de un solo lado y devuelve:

    frecuencia
    amplitud
    potencia
    """

    señal = np.asarray(
        señal,
        dtype=float
    )

    if QUITAR_MEDIA_FFT:
        señal_fft = detrend(
            señal,
            type="constant"
        )
    else:
        señal_fft = señal.copy()

    if USAR_PASA_ALTAS:
        señal_fft = filtrar_dinamica(
            señal_fft,
            fs,
            FREC_CORTE_PASA_ALTAS
        )

    n = len(
        señal_fft
    )

    fft_complex = rfft(
        señal_fft
    )

    frecuencias = rfftfreq(
        n,
        d=1.0 / fs
    )

    amplitud = (
        np.abs(
            fft_complex
        ) / n
    )

    if n > 1:

        if n % 2 == 0:
            amplitud[1:-1] *= 2
        else:
            amplitud[1:] *= 2

    potencia = (
        amplitud ** 2
    )

    return (
        frecuencias,
        amplitud,
        potencia
    )


# ============================================================
# CARACTERÍSTICAS DE HUella
# ============================================================

def extraer_caracteristicas_huella(
    x,
    y,
    z,
    estado,
    unidad_id,
    fs=50
):
    """
    Extrae características para identificar la unidad.

    IMPORTANTE:
    - unidad_id = identidad del autobús/unidad.
    - estado = estado humano 0-7 y solo se conserva como metadato.
    """

    magnitud = calcular_magnitud(
        x,
        y,
        z
    )

    # --------------------------------------------------------
    # FFT
    # --------------------------------------------------------

    (
        frecuencias,
        amplitud,
        potencia
    ) = extraer_fft(
        magnitud,
        fs
    )

    # Ignorar 0 Hz
    if len(amplitud) > 0:
        amplitud[0] = 0
        potencia[0] = 0

    # --------------------------------------------------------
    # Pico principal
    # --------------------------------------------------------

    idx_dom = int(
        np.argmax(
            amplitud
        )
    )

    freq_dominante = float(
        frecuencias[
            idx_dom
        ]
    )

    amp_dominante = float(
        amplitud[
            idx_dom
        ]
    )

    # --------------------------------------------------------
    # Picos espectrales
    # --------------------------------------------------------

    if np.max(amplitud) > 0:

        threshold = (
            np.mean(amplitud) +
            np.std(amplitud)
        )

        peaks, props = find_peaks(
            amplitud,
            height=threshold,
            distance=2
        )

        if len(peaks) > 0:

            orden = np.argsort(
                amplitud[peaks]
            )[::-1]

            peaks = peaks[
                orden
            ][:3]

        else:
            peaks = np.array(
                [],
                dtype=int
            )

    else:

        peaks = np.array(
            [],
            dtype=int
        )

    picos_freq = []

    picos_amp = []

    for p in peaks:

        picos_freq.append(
            float(
                frecuencias[p]
            )
        )

        picos_amp.append(
            float(
                amplitud[p]
            )
        )

    while len(picos_freq) < 3:
        picos_freq.append(0.0)

    while len(picos_amp) < 3:
        picos_amp.append(0.0)

    # --------------------------------------------------------
    # BANDAS DE FRECUENCIA
    # --------------------------------------------------------

    def energia_banda(
        fmin,
        fmax
    ):

        mask = (
            (frecuencias >= fmin)
            &
            (frecuencias < fmax)
        )

        return float(
            np.sum(
                potencia[mask]
            )
        )

    energia_0_3 = energia_banda(
        0,
        3
    )

    energia_3_8 = energia_banda(
        3,
        8
    )

    energia_8_15 = energia_banda(
        8,
        15
    )

    energia_15_25 = energia_banda(
        15,
        25
    )

    energia_total_fft = float(
        np.sum(
            potencia
        )
    )

    # --------------------------------------------------------
    # CENTROIDE ESPECTRAL
    # --------------------------------------------------------

    suma_amp = float(
        np.sum(
            amplitud
        )
    )

    if suma_amp > 0:

        centroide = float(
            np.sum(
                frecuencias *
                amplitud
            ) /
            suma_amp
        )

    else:

        centroide = 0.0

    # --------------------------------------------------------
    # CARACTERÍSTICAS TEMPORALES
    # --------------------------------------------------------

    mag_mean = float(
        np.mean(
            magnitud
        )
    )

    mag_std = float(
        np.std(
            magnitud
        )
    )

    mag_rms = float(
        np.sqrt(
            np.mean(
                magnitud ** 2
            )
        )
    )

    mag_energy = float(
        np.sum(
            magnitud ** 2
        )
    )

    mag_peak = float(
        np.max(
            np.abs(
                magnitud
            )
        )
    )

    mag_ptp = float(
        np.ptp(
            magnitud
        )
    )

    crest = (
        mag_peak / mag_rms
        if mag_rms > 0
        else 0.0
    )

    # --------------------------------------------------------
    # CARACTERÍSTICAS POR EJE
    # --------------------------------------------------------

    x_rms = float(
        np.sqrt(
            np.mean(
                x ** 2
            )
        )
    )

    y_rms = float(
        np.sqrt(
            np.mean(
                y ** 2
            )
        )
    )

    z_rms = float(
        np.sqrt(
            np.mean(
                z ** 2
            )
        )
    )

    # --------------------------------------------------------
    # RETORNO
    # --------------------------------------------------------

    return {

        "unidad_id":
            unidad_id,

        "estado_mayoritario":
            int(estado),

        "freq_dominante":
            freq_dominante,

        "amplitud_dominante":
            amp_dominante,

        "pico_1_freq":
            picos_freq[0],

        "pico_2_freq":
            picos_freq[1],

        "pico_3_freq":
            picos_freq[2],

        "pico_1_amp":
            picos_amp[0],

        "pico_2_amp":
            picos_amp[1],

        "pico_3_amp":
            picos_amp[2],

        "energia_fft":
            energia_total_fft,

        "centroide_frecuencia":
            centroide,

        "energia_0_3hz":
            energia_0_3,

        "energia_3_8hz":
            energia_3_8,

        "energia_8_15hz":
            energia_8_15,

        "energia_15_25hz":
            energia_15_25,

        "mag_mean":
            mag_mean,

        "mag_std":
            mag_std,

        "mag_rms":
            mag_rms,

        "mag_energy":
            mag_energy,

        "mag_peak":
            mag_peak,

        "mag_ptp":
            mag_ptp,

        "crest_factor":
            crest,

        "x_rms":
            x_rms,

        "y_rms":
            y_rms,

        "z_rms":
            z_rms
    }


# ============================================================
# CREAR VENTANAS
# ============================================================

def crear_ventanas(
    df,
    unidad_id
):
    """
    Crea ventanas estrictas de 150 muestras.

    NO crea ventanas más pequeñas.
    """

    ventanas = []

    paso = int(
        MUESTRAS_POR_VENTANA *
        (
            1 -
            TRASLAPE_PCT / 100
        )
    )

    if paso <= 0:
        raise ValueError(
            "TRASLAPE_PCT produce un paso inválido."
        )

    # --------------------------------------------------------
    # Separar por segmentos de tiempo
    # para no cruzar huecos.
    # --------------------------------------------------------

    segmentos = dividir_por_huecos(
        df,
        MAX_GAP_INTERPOLACION_SEG
    )

    id_local = 0

    for segmento in segmentos:

        segmento = segmento.reset_index(
            drop=True
        )

        total = len(
            segmento
        )

        for inicio in range(
            0,
            total -
            MUESTRAS_POR_VENTANA +
            1,
            paso
        ):

            fin = (
                inicio +
                MUESTRAS_POR_VENTANA
            )

            ventana = (
                segmento.iloc[
                    inicio:fin
                ].copy()
            )

            if len(ventana) != 150:
                continue

            # ------------------------------------------------
            # Estado mayoritario solo como metadata.
            # ------------------------------------------------

            estado = (
                ventana["Estado"]
                .mode()
            )

            if estado.empty:
                estado_mayoritario = -1
            else:
                estado_mayoritario = int(
                    estado.iloc[0]
                )

            ventana["ID_Ventana"] = (
                id_local
            )

            ventana["unidad_id"] = (
                unidad_id
            )

            ventana[
                "Estado_Mayoritario"
            ] = (
                estado_mayoritario
            )

            ventanas.append(
                ventana
            )

            id_local += 1

    return ventanas


# ============================================================
# PROCESAR UNA UNIDAD
# ============================================================

def procesar_unidad(
    ruta_csv,
    unidad_id
):
    print()
    print(
        "=" * 70
    )

    print(
        f"UNIDAD: {unidad_id}"
    )

    print(
        "=" * 70
    )

    print(
        f"Archivo: {ruta_csv}"
    )

    df_original = cargar_csv(
        ruta_csv
    )

    print(
        f"Muestras originales: "
        f"{len(df_original)}"
    )

    print(
        f"Inicio: "
        f"{df_original['Timestamp'].min()}"
    )

    print(
        f"Fin: "
        f"{df_original['Timestamp'].max()}"
    )

    # --------------------------------------------------------
    # NORMALIZAR A 50 Hz
    # --------------------------------------------------------

    print(
        "Normalizando a 50 Hz..."
    )

    df_50hz = normalizar_a_50hz(
        df_original
    )

    print(
        f"Muestras después de normalizar: "
        f"{len(df_50hz)}"
    )

    # --------------------------------------------------------
    # CREAR VENTANAS
    # --------------------------------------------------------

    print(
        "Creando ventanas de 3 segundos..."
    )

    ventanas = crear_ventanas(
        df_50hz,
        unidad_id
    )

    print(
        f"Ventanas válidas: "
        f"{len(ventanas)}"
    )

    # --------------------------------------------------------
    # CARACTERÍSTICAS
    # --------------------------------------------------------

    resultados = []

    for ventana in ventanas:

        x = (
            ventana["AccelX"]
            .to_numpy(
                dtype=float
            )
        )

        y = (
            ventana["AccelY"]
            .to_numpy(
                dtype=float
            )
        )

        z = (
            ventana["AccelZ"]
            .to_numpy(
                dtype=float
            )
        )

        estado = int(
            ventana[
                "Estado_Mayoritario"
            ].iloc[0]
        )

        id_ventana = int(
            ventana[
                "ID_Ventana"
            ].iloc[0]
        )

        features = (
            extraer_caracteristicas_huella(
                x,
                y,
                z,
                estado,
                unidad_id,
                FS_OBJETIVO
            )
        )

        features[
            "ID_Ventana"
        ] = id_ventana

        resultados.append(
            features
        )

    df_features = pd.DataFrame(
        resultados
    )

    return (
        df_50hz,
        ventanas,
        df_features
    )


# ============================================================
# PROCESAR TODAS LAS UNIDADES
# ============================================================

def obtener_archivos():

    if PROCESAR_CARPETA:

        archivos = sorted(
            glob.glob(
                os.path.join(
                    CARPETA_ENTRADA,
                    PATRON_CSV
                )
            )
        )

        if not archivos:
            raise FileNotFoundError(
                f"No hay CSV en {CARPETA_ENTRADA}"
            )

        return [
            (
                ruta,
                os.path.splitext(
                    os.path.basename(
                        ruta
                    )
                )[0]
            )
            for ruta in archivos
        ]

    return [
        (
            RUTA_ENTRADA,
            UNIDAD_ID_MANUAL
        )
    ]


# ============================================================
# ENTRENAMIENTO
# ============================================================

def entrenar_identificador_unidades(
    df_features
):
    """
    Entrena Random Forest para identificar unidad_id.

    Estado NO se utiliza como etiqueta de unidad.
    """

    if df_features.empty:
        print(
            "No hay características para entrenar."
        )
        return None

    if (
        "unidad_id"
        not in df_features.columns
    ):
        raise ValueError(
            "No existe unidad_id."
        )

    etiquetas = (
        df_features[
            "unidad_id"
        ]
        .nunique()
    )

    if etiquetas < 2:

        print()
        print(
            "⚠️ Solo existe una unidad."
        )

        print(
            "No se puede entrenar un clasificador "
            "de identidad de unidad con una sola clase."
        )

        return None

    columnas_no_features = [
        "unidad_id",
        "estado_mayoritario"
    ]

    caracteristicas = [
        c
        for c in df_features.columns
        if c not in columnas_no_features
    ]

    X = df_features[
        caracteristicas
    ].copy()

    y = df_features[
        "unidad_id"
    ]

    # --------------------------------------------------------
    # Evitar columnas no numéricas
    # --------------------------------------------------------

    X = X.apply(
        pd.to_numeric,
        errors="coerce"
    )

    X = (
        X.replace(
            [np.inf, -np.inf],
            np.nan
        )
        .fillna(0)
    )

    # --------------------------------------------------------
    # Modelo
    # --------------------------------------------------------

    modelo = RandomForestClassifier(
        n_estimators=300,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1
    )

    modelo.fit(
        X,
        y
    )

    pred = modelo.predict(
        X
    )

    print()
    print(
        "=" * 70
    )

    print(
        "ENTRENAMIENTO DE HUELLA DIGITAL"
    )

    print(
        "=" * 70
    )

    print(
        f"Unidades: {etiquetas}"
    )

    print(
        f"Ventanas: {len(df_features)}"
    )

    print(
        f"Características: {len(caracteristicas)}"
    )

    print(
        f"Accuracy entrenamiento: "
        f"{accuracy_score(y, pred) * 100:.2f}%"
    )

    print()
    print(
        classification_report(
            y,
            pred,
            zero_division=0
        )
    )

    # --------------------------------------------------------
    # Importancia
    # --------------------------------------------------------

    importancias = (
        pd.Series(
            modelo.feature_importances_,
            index=caracteristicas
        )
        .sort_values(
            ascending=False
        )
    )

    print(
        "Características más importantes:"
    )

    for i, (
        col,
        importancia
    ) in enumerate(
        importancias.items(),
        start=1
    ):

        print(
            f"{i:02d}. "
            f"{col:<28} "
            f"{importancia:.5f}"
        )

        if i >= 10:
            break

    return modelo


# ============================================================
# GRAFICAR UNA VENTANA
# ============================================================

def visualizar_ventana(
    ventana,
    fs=50
):
    """
    Visor simple de una ventana de 3 segundos.
    """

    x = ventana[
        "AccelX"
    ].to_numpy()

    y = ventana[
        "AccelY"
    ].to_numpy()

    z = ventana[
        "AccelZ"
    ].to_numpy()

    magnitud = calcular_magnitud(
        x,
        y,
        z
    )

    frecuencias, amplitud, _ = (
        extraer_fft(
            magnitud,
            fs
        )
    )

    fig, (
        ax1,
        ax2
    ) = plt.subplots(
        2,
        1,
        figsize=(12, 8)
    )

    tiempo = (
        np.arange(
            len(magnitud)
        ) /
        fs
    )

    ax1.plot(
        tiempo,
        magnitud,
        label="Magnitud"
    )

    ax1.set_title(
        "Huella temporal - ventana de 3 s"
    )

    ax1.set_xlabel(
        "Tiempo (s)"
    )

    ax1.set_ylabel(
        "Aceleración"
    )

    ax1.grid(
        True
    )

    ax2.plot(
        frecuencias,
        amplitud
    )

    ax2.set_title(
        "Huella espectral - FFT"
    )

    ax2.set_xlabel(
        "Frecuencia (Hz)"
    )

    ax2.set_ylabel(
        "Amplitud"
    )

    ax2.set_xlim(
        0,
        FS_OBJETIVO / 2
    )

    ax2.grid(
        True
    )

    plt.tight_layout()
    plt.show()


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    os.makedirs(
        CARPETA_SALIDA,
        exist_ok=True
    )

    print("=" * 70)
    print(
        "HUELLA DIGITAL DE UNIDADES"
    )
    print("=" * 70)

    print(
        f"Frecuencia objetivo: "
        f"{FS_OBJETIVO} Hz"
    )

    print(
        f"Ventana: "
        f"{DURACION_VENTANA_SEG} s"
    )

    print(
        f"Muestras/ventana: "
        f"{MUESTRAS_POR_VENTANA}"
    )

    print(
        "Nota: Estado 0-7 se conserva como metadata; "
        "no identifica la unidad."
    )

    archivos = obtener_archivos()

    todos_features = []
    todas_ventanas = []
    primer_df_50hz = None
    primera_ventana = None

    for ruta, unidad_id in archivos:

        if not os.path.exists(ruta):

            print(
                f"\n⚠️ No existe: {ruta}"
            )

            continue

        try:

            (
                df_50hz,
                ventanas,
                df_features
            ) = procesar_unidad(
                ruta,
                unidad_id
            )

            if primer_df_50hz is None:
                primer_df_50hz = df_50hz

            if (
                primera_ventana is None
                and
                len(ventanas) > 0
            ):
                primera_ventana = (
                    ventanas[0]
                )

            if len(df_features) > 0:
                todos_features.append(
                    df_features
                )

            for ventana in ventanas:
                todas_ventanas.append(
                    ventana
                )

        except Exception as e:

            print(
                f"\n❌ Error procesando "
                f"{ruta}: {e}"
            )

    # ========================================================
    # GUARDAR CARACTERÍSTICAS
    # ========================================================

    if todos_features:

        df_final_features = pd.concat(
            todos_features,
            ignore_index=True
        )

        df_final_features.to_csv(
            ARCHIVO_CARACTERISTICAS,
            index=False,
            encoding="utf-8-sig"
        )

        print()
        print(
            f"Características guardadas en:\n"
            f"{ARCHIVO_CARACTERISTICAS}"
        )

    else:

        df_final_features = pd.DataFrame()

        print(
            "\n⚠️ No se generaron características."
        )

    # ========================================================
    # GUARDAR VENTANAS
    # ========================================================

    if todas_ventanas:

        df_ventanas = pd.concat(
            todas_ventanas,
            ignore_index=True
        )

        df_ventanas.to_csv(
            ARCHIVO_VENTANAS,
            index=False,
            encoding="utf-8-sig"
        )

        print(
            f"Ventanas 3s/50Hz guardadas en:\n"
            f"{ARCHIVO_VENTANAS}"
        )

    # ========================================================
    # ENTRENAR SI HAY VARIAS UNIDADES
    # ========================================================

    modelo = entrenar_identificador_unidades(
        df_final_features
    )

    # ========================================================
    # VISUALIZAR PRIMERA VENTANA
    # ========================================================

    if primera_ventana is not None:

        visualizar_ventana(
            primera_ventana,
            FS_OBJETIVO
        )
