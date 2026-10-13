import os
import numpy as np
import pandas as pd

from scipy import stats
from scipy.signal import find_peaks


# ============================================================
# CONFIGURACIÓN
# ============================================================

ARCHIVO_ENTRADA = (
   
     r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\DATASET\salidad_ACEL_Y_GPS\Dataset_COMBINADO__10.csv"
   
)

ARCHIVO_SALIDA = (
   
     r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\DATASET\SALIDAD_ACEL_GPS_ENERGIA_FFT_VARIANZA\50 carateristicas\metricas_50_xyz_10.csv"

)


# ============================================================
# PARÁMETROS
# ============================================================

FRECUENCIA_MUESTREO = 50

DURACION_VENTANA_SEG = 3

MUESTRAS_POR_VENTANA = (
    FRECUENCIA_MUESTREO *
    DURACION_VENTANA_SEG
)

# 0 = sin traslape
PORCENTAJE_TRASLAPE = 0

# La ventana debe contener al menos este porcentaje
# del mismo estado para conservarla.
PORCENTAJE_ESTADO = 80


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def convertir_numerico(
    df,
    columnas
):
    """
    Convierte las columnas indicadas a valores numéricos.
    Los valores inválidos se convierten en NaN.
    """

    for columna in columnas:

        df[columna] = pd.to_numeric(
            df[columna],
            errors="coerce"
        )

    return df


# ============================================================
# MAGNITUD VECTORIAL
# ============================================================

def calcular_magnitud(
    x,
    y,
    z
):
    """
    Magnitud del vector de aceleración:

        Magnitud = sqrt(X² + Y² + Z²)
    """

    return np.sqrt(
        x**2 +
        y**2 +
        z**2
    )


# ============================================================
# CREAR VENTANAS DE 3 SEGUNDOS
# ============================================================

def crear_ventanas(
    df,
    muestras_ventana,
    porcentaje_traslape=0,
    porcentaje_estado=80
):
    """
    Genera ventanas consecutivas de:

        3 segundos × 50 Hz = 150 muestras

    Cada ventana conserva:

        AccelX
        AccelY
        AccelZ
        Estado

    """

    paso = int(
        muestras_ventana *
        (
            1 -
            porcentaje_traslape / 100
        )
    )

    if paso <= 0:

        raise ValueError(
            "El traslape genera un paso de ventana <= 0."
        )

    ventanas = []

    id_ventana = 0

    for inicio in range(
        0,
        len(df) - muestras_ventana + 1,
        paso
    ):

        fin = (
            inicio +
            muestras_ventana
        )

        grupo = df.iloc[
            inicio:fin
        ].copy()

        # ----------------------------------------------------
        # VERIFICAR 150 MUESTRAS
        # ----------------------------------------------------

        if len(grupo) != muestras_ventana:

            continue

        # ----------------------------------------------------
        # ESTADO MAYORITARIO
        # ----------------------------------------------------

        conteo = (
            grupo[
                "Estado"
            ]
            .value_counts()
        )

        if conteo.empty:

            continue

        estado_mayoritario = (
            conteo.index[0]
        )

        porcentaje = (
            conteo.iloc[0]
            /
            len(grupo)
            *
            100
        )

        # ----------------------------------------------------
        # VALIDAR PORCENTAJE DE ESTADO
        # ----------------------------------------------------

        if porcentaje < porcentaje_estado:

            continue

        # ----------------------------------------------------
        # ASIGNAR ID
        # ----------------------------------------------------

        grupo[
            "ID_Ventana"
        ] = id_ventana

        ventanas.append(
            grupo
        )

        id_ventana += 1

    # --------------------------------------------------------
    # SIN VENTANAS
    # --------------------------------------------------------

    if not ventanas:

        return pd.DataFrame()

    # --------------------------------------------------------
    # UNIR TODAS
    # --------------------------------------------------------

    return pd.concat(
        ventanas,
        ignore_index=True
    )


# ============================================================
# ESTADÍSTICAS TEMPORALES
# ============================================================

def estadisticas_base(
    señal
):
    """
    Calcula estadísticas temporales de una señal.
    """

    señal = np.asarray(
        señal,
        dtype=float
    )

    señal = señal[
        np.isfinite(señal)
    ]

    if len(señal) == 0:

        return {}

    n = len(
        señal
    )

    # --------------------------------------------------------
    # ESTADÍSTICAS BÁSICAS
    # --------------------------------------------------------

    media = float(
        np.mean(
            señal
        )
    )

    std = (
        float(
            np.std(
                señal,
                ddof=1
            )
        )
        if n > 1
        else 0.0
    )

    varianza = (
        float(
            np.var(
                señal,
                ddof=1
            )
        )
        if n > 1
        else 0.0
    )

    mediana = float(
        np.median(
            señal
        )
    )

    minimo = float(
        np.min(
            señal
        )
    )

    maximo = float(
        np.max(
            señal
        )
    )

    rango = (
        maximo -
        minimo
    )

    # --------------------------------------------------------
    # PERCENTILES
    # --------------------------------------------------------

    q10, q25, q75, q90 = (
        np.percentile(
            señal,
            [
                10,
                25,
                75,
                90
            ]
        )
    )

    iqr = (
        q75 -
        q25
    )

    # --------------------------------------------------------
    # RMS
    # --------------------------------------------------------

    rms = float(
        np.sqrt(
            np.mean(
                señal**2
            )
        )
    )

    # --------------------------------------------------------
    # MEDIA ABSOLUTA
    # --------------------------------------------------------

    media_abs = float(
        np.mean(
            np.abs(
                señal
            )
        )
    )

    # --------------------------------------------------------
    # PICO ABSOLUTO
    # --------------------------------------------------------

    pico = float(
        np.max(
            np.abs(
                señal
            )
        )
    )

    # --------------------------------------------------------
    # PICO A PICO
    # --------------------------------------------------------

    pico_pico = float(
        np.ptp(
            señal
        )
    )

    # --------------------------------------------------------
    # ENERGÍA
    # --------------------------------------------------------

    energia = float(
        np.sum(
            señal**2
        )
    )

    # --------------------------------------------------------
    # POTENCIA
    # --------------------------------------------------------

    potencia = float(
        np.mean(
            señal**2
        )
    )

    # --------------------------------------------------------
    # MAD
    # --------------------------------------------------------

    mad = float(
        np.median(
            np.abs(
                señal -
                mediana
            )
        )
    )

    # --------------------------------------------------------
    # ASIMETRÍA
    # --------------------------------------------------------

    if std > 0:

        asimetria = float(
            stats.skew(
                señal
            )
        )

    else:

        asimetria = 0.0

    # --------------------------------------------------------
    # CURTOSIS
    # --------------------------------------------------------

    if std > 0:

        curtosis = float(
            stats.kurtosis(
                señal
            )
        )

    else:

        curtosis = 0.0

    # --------------------------------------------------------
    # FACTOR DE CRESTA
    # --------------------------------------------------------

    crest_factor = (
        pico /
        rms
        if rms != 0
        else 0.0
    )

    # --------------------------------------------------------
    # FACTOR DE FORMA
    # --------------------------------------------------------

    shape_factor = (
        rms /
        media_abs
        if media_abs != 0
        else 0.0
    )

    # --------------------------------------------------------
    # FACTOR DE IMPULSO
    # --------------------------------------------------------

    impulse_factor = (
        pico /
        media_abs
        if media_abs != 0
        else 0.0
    )

    # --------------------------------------------------------
    # PRIMERA DIFERENCIA
    # --------------------------------------------------------

    diff = np.diff(
        señal
    )

    if len(diff) > 0:

        diff_std = (
            float(
                np.std(
                    diff,
                    ddof=1
                )
            )
            if len(diff) > 1
            else 0.0
        )

        diff_rms = float(
            np.sqrt(
                np.mean(
                    diff**2
                )
            )
        )

        diff_max_abs = float(
            np.max(
                np.abs(
                    diff
                )
            )
        )

        waveform_length = float(
            np.sum(
                np.abs(
                    diff
                )
            )
        )

        mean_abs_diff = float(
            np.mean(
                np.abs(
                    diff
                )
            )
        )

    else:

        diff_std = 0.0

        diff_rms = 0.0

        diff_max_abs = 0.0

        waveform_length = 0.0

        mean_abs_diff = 0.0

    # --------------------------------------------------------
    # SEGUNDA DIFERENCIA
    # --------------------------------------------------------

    diff2 = np.diff(
        señal,
        n=2
    )

    if len(diff2) > 0:

        diff2_std = (
            float(
                np.std(
                    diff2,
                    ddof=1
                )
            )
            if len(diff2) > 1
            else 0.0
        )

        diff2_rms = float(
            np.sqrt(
                np.mean(
                    diff2**2
                )
            )
        )

    else:

        diff2_std = 0.0

        diff2_rms = 0.0

    # --------------------------------------------------------
    # CRUCES POR CERO
    # --------------------------------------------------------

    zero_crossings = int(
        np.sum(
            np.diff(
                np.signbit(
                    señal
                )
            ) != 0
        )
    )

    # --------------------------------------------------------
    # CRUCES POR MEDIA
    # --------------------------------------------------------

    mean_crossings = int(
        np.sum(
            np.diff(
                np.signbit(
                    señal -
                    media
                )
            ) != 0
        )
    )

    # --------------------------------------------------------
    # RETORNO
    # --------------------------------------------------------

    return {

        "media":
            media,

        "std":
            std,

        "varianza":
            varianza,

        "mediana":
            mediana,

        "minimo":
            minimo,

        "maximo":
            maximo,

        "rango":
            rango,

        "asimetria":
            asimetria,

        "curtosis":
            curtosis,

        "percentil_10":
            float(q10),

        "percentil_25":
            float(q25),

        "percentil_75":
            float(q75),

        "percentil_90":
            float(q90),

        "iqr":
            float(iqr),

        "rms":
            rms,

        "media_abs":
            media_abs,

        "pico":
            pico,

        "pico_pico":
            pico_pico,

        "energia":
            energia,

        "potencia":
            potencia,

        "mad":
            mad,

        "crest_factor":
            crest_factor,

        "shape_factor":
            shape_factor,

        "impulse_factor":
            impulse_factor,

        "diff_std":
            diff_std,

        "diff_rms":
            diff_rms,

        "diff_max_abs":
            diff_max_abs,

        "diff2_std":
            diff2_std,

        "diff2_rms":
            diff2_rms,

        "zero_crossings":
            zero_crossings,

        "mean_crossings":
            mean_crossings,

        "mean_abs_diff":
            mean_abs_diff,

        "waveform_length":
            waveform_length
    }


# ============================================================
# AUTOCORRELACIÓN
# ============================================================

def caracteristicas_autocorrelacion(
    señal,
    fs=50
):
    """
    Características de periodicidad.

    Muy útil para actividades periódicas
    como caminar.
    """

    señal = np.asarray(
        señal,
        dtype=float
    )

    if len(señal) < 3:

        return {

            "autocorr_max":
                0.0,

            "autocorr_lag":
                0.0,

            "autocorr_lag_1":
                0.0,

            "autocorr_lag_2":
                0.0,

            "autocorr_lag_3":
                0.0
        }

    # --------------------------------------------------------
    # ELIMINAR MEDIA
    # --------------------------------------------------------

    señal = (
        señal -
        np.mean(
            señal
        )
    )

    # --------------------------------------------------------
    # ENERGÍA
    # --------------------------------------------------------

    denominador = np.sum(
        señal**2
    )

    if denominador == 0:

        return {

            "autocorr_max":
                0.0,

            "autocorr_lag":
                0.0,

            "autocorr_lag_1":
                0.0,

            "autocorr_lag_2":
                0.0,

            "autocorr_lag_3":
                0.0
        }

    # --------------------------------------------------------
    # AUTOCORRELACIÓN
    # --------------------------------------------------------

    autocorr = np.correlate(
        señal,
        señal,
        mode="full"
    )

    autocorr = autocorr[
        len(señal) - 1:
    ]

    autocorr = (
        autocorr /
        autocorr[0]
    )

    # --------------------------------------------------------
    # BUSCAR PERIODICIDAD
    # --------------------------------------------------------

    max_lag_muestras = min(
        len(autocorr) - 1,
        int(
            1.5 *
            fs
        )
    )

    segmento = autocorr[
        1:max_lag_muestras + 1
    ]

    if len(segmento) > 0:

        idx = int(
            np.argmax(
                segmento
            )
        )

        autocorr_max = float(
            segmento[idx]
        )

        autocorr_lag = float(
            idx + 1
        )

    else:

        autocorr_max = 0.0

        autocorr_lag = 0.0

    # --------------------------------------------------------
    # LAGS CORTOS
    # --------------------------------------------------------

    def obtener_lag(
        lag
    ):

        if lag < len(autocorr):

            return float(
                autocorr[
                    lag
                ]
            )

        return 0.0

    # --------------------------------------------------------
    # RETORNO
    # --------------------------------------------------------

    return {

        "autocorr_max":
            autocorr_max,

        "autocorr_lag":
            autocorr_lag,

        "autocorr_lag_1":
            obtener_lag(
                1
            ),

        "autocorr_lag_2":
            obtener_lag(
                2
            ),

        "autocorr_lag_3":
            obtener_lag(
                3
            )
    }


# ============================================================
# PICOS TEMPORALES
# ============================================================

def caracteristicas_picos(
    señal
):
    """
    Detecta picos temporales
    de la magnitud.
    """

    señal = np.asarray(
        señal,
        dtype=float
    )

    if len(señal) < 5:

        return {

            "numero_picos":
                0,

            "distancia_picos_media":
                0.0,

            "distancia_picos_std":
                0.0
        }

    std = float(
        np.std(
            señal
        )
    )

    if std == 0:

        return {

            "numero_picos":
                0,

            "distancia_picos_media":
                0.0,

            "distancia_picos_std":
                0.0
        }

    # --------------------------------------------------------
    # UMBRAL DINÁMICO
    # --------------------------------------------------------

    altura = (
        np.mean(
            señal
        )
        +
        0.5 *
        std
    )

    # --------------------------------------------------------
    # DETECTAR PICOS
    # --------------------------------------------------------

    peaks, _ = find_peaks(
        señal,
        height=altura,
        distance=3
    )

    numero_picos = int(
        len(peaks)
    )

    # --------------------------------------------------------
    # DISTANCIA ENTRE PICOS
    # --------------------------------------------------------

    if len(peaks) >= 2:

        distancias = np.diff(
            peaks
        )

        distancia_media = float(
            np.mean(
                distancias
            )
        )

        distancia_std = float(
            np.std(
                distancias
            )
        )

    else:

        distancia_media = 0.0

        distancia_std = 0.0

    return {

        "numero_picos":
            numero_picos,

        "distancia_picos_media":
            distancia_media,

        "distancia_picos_std":
            distancia_std
    }


# ============================================================
# CORRELACIÓN ENTRE X Y Z
# ============================================================

def correlaciones_xyz(
    x,
    y,
    z
):
    """
    Correlación entre los tres ejes.
    """

    def corr(
        a,
        b
    ):

        if (
            np.std(a) == 0
            or
            np.std(b) == 0
        ):

            return 0.0

        valor = np.corrcoef(
            a,
            b
        )[0, 1]

        if np.isnan(
            valor
        ):

            return 0.0

        return float(
            valor
        )

    return {

        "corr_xy":
            corr(
                x,
                y
            ),

        "corr_xz":
            corr(
                x,
                z
            ),

        "corr_yz":
            corr(
                y,
                z
            )
    }


# ============================================================
# ENTROPÍA
# ============================================================

def entropia_histograma(
    señal,
    bins=10
):
    """
    Entropía de la distribución
    de la magnitud.
    """

    señal = np.asarray(
        señal,
        dtype=float
    )

    if len(señal) == 0:

        return 0.0

    hist, _ = np.histogram(
        señal,
        bins=bins,
        density=False
    )

    hist = hist.astype(
        float
    )

    suma = np.sum(
        hist
    )

    if suma == 0:

        return 0.0

    probabilidades = (
        hist /
        suma
    )

    probabilidades = (
        probabilidades[
            probabilidades > 0
        ]
    )

    return float(
        -np.sum(
            probabilidades *
            np.log2(
                probabilidades
            )
        )
    )


# ============================================================
# 50 CARACTERÍSTICAS
# ============================================================

def generar_50_caracteristicas(
    x,
    y,
    z,
    fs=50
):
    """
    Genera exactamente 50 características
    a partir de 150 muestras de X, Y y Z.

    3 segundos × 50 Hz = 150 muestras.
    """

    # ========================================================
    # VALIDAR TAMAÑO
    # ========================================================

    if (
        len(x) != 150
        or
        len(y) != 150
        or
        len(z) != 150
    ):

        raise ValueError(
            "Cada ventana debe tener exactamente "
            "150 muestras."
        )

    # ========================================================
    # MAGNITUD
    # ========================================================

    magnitud = calcular_magnitud(
        x,
        y,
        z
    )

    # ========================================================
    # ESTADÍSTICAS
    # ========================================================

    mag = estadisticas_base(
        magnitud
    )

    sx = estadisticas_base(
        x
    )

    sy = estadisticas_base(
        y
    )

    sz = estadisticas_base(
        z
    )

    # ========================================================
    # AUTOCORRELACIÓN
    # ========================================================

    auto = caracteristicas_autocorrelacion(
        magnitud,
        fs
    )

    # ========================================================
    # PICOS
    # ========================================================

    picos = caracteristicas_picos(
        magnitud
    )

    # ========================================================
    # CORRELACIÓN XYZ
    # ========================================================

    corr = correlaciones_xyz(
        x,
        y,
        z
    )

    # ========================================================
    # ENTROPÍA
    # ========================================================

    entropia = entropia_histograma(
        magnitud,
        bins=10
    )

    # ========================================================
    # RMS AC
    # ========================================================

    magnitud_centrado = (
        magnitud -
        np.mean(
            magnitud
        )
    )

    rms_ac = float(
        np.sqrt(
            np.mean(
                magnitud_centrado**2
            )
        )
    )

    # ========================================================
    # PORCENTAJE DE ALTA AMPLITUD
    # ========================================================

    media_mag = float(
        np.mean(
            magnitud
        )
    )

    std_mag = float(
        np.std(
            magnitud
        )
    )

    umbral_alta = (
        media_mag +
        2 *
        std_mag
    )

    porcentaje_alta_amplitud = float(
        np.mean(
            magnitud >
            umbral_alta
        )
        *
        100
    )

    # ========================================================
    # CONSTRUIR EXACTAMENTE 50
    # ========================================================

    caracteristicas = {

        # ====================================================
        # 1-10
        # ESTADÍSTICA GENERAL DE MAGNITUD
        # ====================================================

        "Mag_Media":
            mag["media"],

        "Mag_STD":
            mag["std"],

        "Mag_Varianza":
            mag["varianza"],

        "Mag_Mediana":
            mag["mediana"],

        "Mag_Minimo":
            mag["minimo"],

        "Mag_Maximo":
            mag["maximo"],

        "Mag_Rango":
            mag["rango"],

        "Mag_Asimetria":
            mag["asimetria"],

        "Mag_Curtosis":
            mag["curtosis"],

        "Mag_RMS":
            mag["rms"],


        # ====================================================
        # 11-16
        # AMPLITUD Y ENERGÍA
        # ====================================================

        "Mag_Pico":
            mag["pico"],

        "Mag_Pico_Pico":
            mag["pico_pico"],

        "Mag_Energia":
            mag["energia"],

        "Mag_Potencia":
            mag["potencia"],

        "Mag_MAD":
            mag["mad"],

        "Mag_Crest_Factor":
            mag["crest_factor"],


        # ====================================================
        # 17-25
        # CAMBIOS TEMPORALES
        # ====================================================

        "Mag_Diff_STD":
            mag["diff_std"],

        "Mag_Diff_RMS":
            mag["diff_rms"],

        "Mag_Diff_Max":
            mag["diff_max_abs"],

        "Mag_Diff2_STD":
            mag["diff2_std"],

        "Mag_Diff2_RMS":
            mag["diff2_rms"],

        "Mag_Longitud_Onda":
            mag["waveform_length"],

        "Mag_Cruces_Cero":
            mag["zero_crossings"],

        "Mag_Cruces_Media":
            mag["mean_crossings"],

        "Mag_Media_Diff_Abs":
            mag["mean_abs_diff"],


        # ====================================================
        # 26-30
        # DISTRIBUCIÓN
        # ====================================================

        "Mag_P10":
            mag["percentil_10"],

        "Mag_P25":
            mag["percentil_25"],

        "Mag_P75":
            mag["percentil_75"],

        "Mag_P90":
            mag["percentil_90"],

        "Mag_IQR":
            mag["iqr"],


        # ====================================================
        # 31-35
        # PERIODICIDAD
        # ====================================================

        "Autocorr_Max":
            auto["autocorr_max"],

        "Autocorr_Lag":
            auto["autocorr_lag"],

        "Autocorr_Lag1":
            auto["autocorr_lag_1"],

        "Autocorr_Lag2":
            auto["autocorr_lag_2"],

        "Autocorr_Lag3":
            auto["autocorr_lag_3"],


        # ====================================================
        # 36-38
        # PICOS
        # ====================================================

        "Numero_Picos":
            picos["numero_picos"],

        "Distancia_Picos_Media":
            picos["distancia_picos_media"],

        "Distancia_Picos_STD":
            picos["distancia_picos_std"],


        # ====================================================
        # 39-41
        # RELACIONES ENTRE EJES
        # ====================================================

        "Corr_XY":
            corr["corr_xy"],

        "Corr_XZ":
            corr["corr_xz"],

        "Corr_YZ":
            corr["corr_yz"],


        # ====================================================
        # 42-47
        # INFORMACIÓN INDIVIDUAL DE X, Y, Z
        # ====================================================

        "X_RMS":
            sx["rms"],

        "Y_RMS":
            sy["rms"],

        "Z_RMS":
            sz["rms"],

        "X_STD":
            sx["std"],

        "Y_STD":
            sy["std"],

        "Z_STD":
            sz["std"],


        # ====================================================
        # 48
        # ENTROPÍA
        # ====================================================

        "Mag_Entropia":
            entropia,


        # ====================================================
        # 49
        # RMS AC
        # ====================================================

        "Mag_RMS_AC":
            rms_ac,


        # ====================================================
        # 50
        # PORCENTAJE ALTA AMPLITUD
        # ====================================================

        "Mag_Alta_Amplitud_Pct":
            porcentaje_alta_amplitud
    }

    # ========================================================
    # VALIDACIÓN
    # ========================================================

    if len(
        caracteristicas
    ) != 50:

        raise RuntimeError(
            "ERROR: Se generaron "
            f"{len(caracteristicas)} "
            "características en lugar de 50."
        )

    return caracteristicas


# ============================================================
# PROCESAMIENTO DEL DATASET
# ============================================================

def procesar_dataset():

    print("=" * 70)

    print(
        "EXTRACCIÓN DE 50 CARACTERÍSTICAS "
        "TEMPORALES XYZ"
    )

    print("=" * 70)

    print(
        f"Frecuencia: "
        f"{FRECUENCIA_MUESTREO} Hz"
    )

    print(
        f"Ventana: "
        f"{DURACION_VENTANA_SEG} segundos"
    )

    print(
        f"Muestras por ventana: "
        f"{MUESTRAS_POR_VENTANA}"
    )

    print(
        f"Porcentaje mínimo de estado: "
        f"{PORCENTAJE_ESTADO}%"
    )

    print()

    # ========================================================
    # EXISTENCIA DEL ARCHIVO
    # ========================================================

    if not os.path.exists(
        ARCHIVO_ENTRADA
    ):

        raise FileNotFoundError(
            "No existe el archivo:\n"
            +
            ARCHIVO_ENTRADA
        )

    # ========================================================
    # CARGAR DATASET
    # ========================================================

    print(
        "Cargando dataset..."
    )

    df = pd.read_csv(
        ARCHIVO_ENTRADA
    )

    print(
        f"Filas originales: "
        f"{len(df)}"
    )

    print(
        "Columnas detectadas:"
    )

    print(
        df.columns.tolist()
    )

    print()

    # ========================================================
    # COLUMNAS NECESARIAS
    # ========================================================

    requeridas = [
        "AccelX",
        "AccelY",
        "AccelZ",
        "Estado"
    ]

    faltantes = [
        columna
        for columna in requeridas
        if columna not in df.columns
    ]

    if faltantes:

        raise ValueError(
            "Faltan columnas necesarias:\n"
            +
            "\n".join(
                faltantes
            )
        )

    # ========================================================
    # CONVERTIR COLUMNAS
    # ========================================================

    df = convertir_numerico(
        df,
        [
            "AccelX",
            "AccelY",
            "AccelZ",
            "Estado"
        ]
    )

    # ========================================================
    # ELIMINAR FILAS INVALIDAS
    # ========================================================

    filas_antes = len(
        df
    )

    df = df.dropna(
        subset=[
            "AccelX",
            "AccelY",
            "AccelZ",
            "Estado"
        ]
    ).copy()

    filas_despues = len(
        df
    )

    print(
        "Filas eliminadas por NaN: "
        f"{filas_antes - filas_despues}"
    )

    # ========================================================
    # ORDEN TEMPORAL
    # ========================================================

    if "Timestamp" in df.columns:

        df["Timestamp"] = pd.to_datetime(
            df["Timestamp"],
            errors="coerce"
        )

        # IMPORTANTE:
        # solo ordenar si Timestamp realmente tiene
        # valores válidos.

        if df["Timestamp"].notna().any():

            df = (
                df.sort_values(
                    "Timestamp"
                )
                .reset_index(
                    drop=True
                )
            )

            print(
                "Dataset ordenado temporalmente."
            )

    # ========================================================
    # MOSTRAR DISTRIBUCIÓN ORIGINAL
    # ========================================================

    print()

    print(
        "Distribución original de estados:"
    )

    print(
        df[
            "Estado"
        ]
        .value_counts()
        .sort_index()
    )

    # ========================================================
    # CREAR VENTANAS
    # ========================================================

    print()

    print(
        "Generando ventanas de "
        f"{MUESTRAS_POR_VENTANA} muestras..."
    )

    df_ventanas = crear_ventanas(
        df,
        MUESTRAS_POR_VENTANA,
        PORCENTAJE_TRASLAPE,
        PORCENTAJE_ESTADO
    )

    # ========================================================
    # VALIDAR
    # ========================================================

    if df_ventanas.empty:

        raise ValueError(
            "No se generaron ventanas válidas."
        )

    numero_ventanas = (
        df_ventanas[
            "ID_Ventana"
        ]
        .nunique()
    )

    print(
        f"Ventanas generadas: "
        f"{numero_ventanas}"
    )

    # ========================================================
    # PROCESAR VENTANA
    # ========================================================

    resultados = []

    print()

    print(
        "Extrayendo 50 características..."
    )

    for id_ventana, grupo in (
        df_ventanas.groupby(
            "ID_Ventana"
        )
    ):

        # ----------------------------------------------------
        # VERIFICAR 150 MUESTRAS
        # ----------------------------------------------------

        if len(grupo) != 150:

            print(
                f"Ventana {id_ventana} ignorada: "
                f"{len(grupo)} muestras."
            )

            continue

        # ----------------------------------------------------
        # EXTRAER X
        # ----------------------------------------------------

        x = (
            grupo[
                "AccelX"
            ]
            .to_numpy(
                dtype=float
            )
        )

        # ----------------------------------------------------
        # EXTRAER Y
        # ----------------------------------------------------

        y = (
            grupo[
                "AccelY"
            ]
            .to_numpy(
                dtype=float
            )
        )

        # ----------------------------------------------------
        # EXTRAER Z
        # ----------------------------------------------------

        z = (
            grupo[
                "AccelZ"
            ]
            .to_numpy(
                dtype=float
            )
        )

        # ----------------------------------------------------
        # VALIDAR TAMAÑOS
        # ----------------------------------------------------

        if (
            len(x) != 150
            or
            len(y) != 150
            or
            len(z) != 150
        ):

            print(
                f"Ventana {id_ventana} "
                "ignorada por tamaño incorrecto."
            )

            continue

        # ----------------------------------------------------
        # ESTADO MAYORITARIO
        # ----------------------------------------------------

        estado = int(
            grupo[
                "Estado"
            ]
            .mode()
            .iloc[0]
        )

        # ----------------------------------------------------
        # EXTRAER CARACTERÍSTICAS
        # ----------------------------------------------------

        caracteristicas = (
            generar_50_caracteristicas(
                x,
                y,
                z,
                FRECUENCIA_MUESTREO
            )
        )

        # ----------------------------------------------------
        # CREAR FILA
        # ----------------------------------------------------

        fila = {

            "ID_Ventana":
                int(
                    id_ventana
                ),

            "Estado":
                estado
        }

        fila.update(
            caracteristicas
        )

        resultados.append(
            fila
        )

    # ========================================================
    # DATAFRAME FINAL
    # ========================================================

    df_final = pd.DataFrame(
        resultados
    )

    if df_final.empty:

        raise ValueError(
            "No se pudieron generar "
            "características."
        )

    # ========================================================
    # OBTENER COLUMNAS DE CARACTERÍSTICAS
    # ========================================================

    columnas_caracteristicas = [
        columna
        for columna in df_final.columns
        if columna not in [
            "ID_Ventana",
            "Estado"
        ]
    ]

    # ========================================================
    # VALIDAR EXACTAMENTE 50
    # ========================================================

    cantidad = len(
        columnas_caracteristicas
    )

    if cantidad != 50:

        raise RuntimeError(
            "ERROR FINAL:\n"
            f"Se generaron {cantidad} "
            "características en lugar de 50."
        )

    # ========================================================
    # VERIFICAR ESTADOS 0-7
    # ========================================================

    estados = sorted(
        df_final[
            "Estado"
        ].unique()
    )

    print()

    print(
        "Estados encontrados:"
    )

    print(
        estados
    )

    # ========================================================
    # VALIDACIÓN ESTADOS FUERA DE 0-7
    # ========================================================

    estados_validos = set(
        range(8)
    )

    estados_detectados = set(
        estados
    )

    fuera_rango = (
        estados_detectados -
        estados_validos
    )

    if fuera_rango:

        print()

        print(
            "⚠ ADVERTENCIA:"
        )

        print(
            "Se detectaron estados "
            "fuera del rango 0-7:"
        )

        print(
            sorted(
                fuera_rango
            )
        )

    # ========================================================
    # CREAR CARPETA DE SALIDA
    # ========================================================

    carpeta_salida = os.path.dirname(
        ARCHIVO_SALIDA
    )

    os.makedirs(
        carpeta_salida,
        exist_ok=True
    )

    # ========================================================
    # GUARDAR CSV
    # ========================================================

    df_final.to_csv(
        ARCHIVO_SALIDA,
        index=False,
        encoding="utf-8-sig"
    )

    # ========================================================
    # RESUMEN FINAL
    # ========================================================

    print()

    print(
        "=" * 70
    )

    print(
        "PROCESAMIENTO TERMINADO"
    )

    print(
        "=" * 70
    )

    print(
        f"Ventanas válidas: "
        f"{len(df_final)}"
    )

    print(
        f"Características: "
        f"{cantidad}"
    )

    print(
        f"Columnas totales: "
        f"{len(df_final.columns)}"
    )

    print()

    print(
        "Distribución final de estados:"
    )

    print(
        df_final[
            "Estado"
        ]
        .value_counts()
        .sort_index()
    )

    print()

    print(
        "LISTA DE LAS 50 CARACTERÍSTICAS:"
    )

    print(
        "-" * 70
    )

    for numero, columna in enumerate(
        columnas_caracteristicas,
        start=1
    ):

        print(
            f"{numero:02d}. {columna}"
        )

    print()

    print(
        "Archivo generado:"
    )

    print(
        ARCHIVO_SALIDA
    )

    print()

    print(
        "=" * 70
    )


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":

    try:

        procesar_dataset()

    except Exception as e:

        print()

        print(
            "=" * 70
        )

        print(
            "ERROR"
        )

        print(
            "=" * 70
        )

        print(
            str(e)
        )

        print()

        print(
            "Verifica:"
        )

        print(
            "1. La ruta del CSV."
        )

        print(
            "2. AccelX, AccelY, AccelZ y Estado."
        )

        print(
            "3. Que cada ventana tenga 150 muestras."
        )

        print(
            "4. Que scipy esté instalado."
        )