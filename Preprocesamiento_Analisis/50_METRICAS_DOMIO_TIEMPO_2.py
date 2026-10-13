import numpy as np
import pandas as pd
from scipy import stats

def generar_50_metricas_por_fila(row):
    """
    Toma una fila de características de la ventana y genera un diccionario 
    con 50 métricas estadísticas y de distribución consistentes.
    """
    # Extraemos únicamente los valores numéricos de la señal/características de la ventana
    valores = row.values.astype(float)
    n = len(valores)
    
    # Si hay valores nulos, los filtramos
    valores = valores[~np.isnan(valores)]
    n_val = len(valores)
    
    if n_val == 0:
        return {}

    # 1-7. Estadísticas Descriptivas Básicas
    mean = np.mean(valores)
    std = np.std(valores, ddof=1) if n_val > 1 else 0.0
    var = np.var(valores, ddof=1) if n_val > 1 else 0.0
    median = np.median(valores)
    minimum = np.min(valores)
    maximum = np.max(valores)
    p_range = maximum - minimum

    # 8-9. Momentos Estadísticos de Forma
    skewness = float(stats.skew(valores)) if std > 0 else 0.0
    kurtosis = float(stats.kurtosis(valores)) if std > 0 else 0.0

    # 10-20. Percentiles y Rangos Intercuartílicos
    q01, q05, q10, q25, q75, q90, q95, q99 = np.percentile(valores, [1, 5, 10, 25, 75, 90, 95, 99])
    iqr = q75 - q25
    q_range_90_10 = q90 - q10
    q_range_99_01 = q99 - q01

    # 21-24. Magnitudes de Amplitud y Normas
    rms = np.sqrt(np.mean(valores**2))
    abs_mean = np.mean(np.abs(valores))
    sqr_mean_sq = (np.mean(np.sqrt(np.abs(valores))))**2
    peak_abs = np.max(np.abs(valores))

    # 25-28. Factores Adimensionales
    crest_factor = (peak_abs / rms) if rms != 0 else 0.0
    shape_factor = (rms / abs_mean) if abs_mean != 0 else 0.0
    impulse_factor = (peak_abs / abs_mean) if abs_mean != 0 else 0.0
    margin_factor = (peak_abs / sqr_mean_sq) if sqr_mean_sq != 0 else 0.0

    # 29-30. Energía y Potencia de la Fila
    energy = np.sum(valores**2)
    power = np.mean(valores**2)

    # 31-34. Estadísticas de Primera Diferencia (Cambios entre columnas/variables)
    diff_v = np.diff(valores)
    diff_mean = np.mean(diff_v) if len(diff_v) > 0 else 0.0
    diff_std = np.std(diff_v, ddof=1) if len(diff_v) > 1 else 0.0
    diff_rms = np.sqrt(np.mean(diff_v**2)) if len(diff_v) > 0 else 0.0
    diff_max = np.max(np.abs(diff_v)) if len(diff_v) > 0 else 0.0

    # 35-37. Estadísticas de Segunda Diferencia
    diff2_v = np.diff(valores, n=2)
    diff2_mean = np.mean(diff2_v) if len(diff2_v) > 0 else 0.0
    diff2_std = np.std(diff2_v, ddof=1) if len(diff2_v) > 1 else 0.0
    diff2_rms = np.sqrt(np.mean(diff2_v**2)) if len(diff2_v) > 0 else 0.0

    # 38-41. Cruces y Cambios de Tendencia
    zero_crossings = np.sum(np.diff(np.signbit(valores)) != 0)
    mean_crossings = np.sum(np.diff(np.signbit(valores - mean)) != 0)
    positive_turns = np.sum((diff_v[:-1] > 0) & (diff_v[1:] < 0)) if len(diff_v) > 1 else 0
    negative_turns = np.sum((diff_v[:-1] < 0) & (diff_v[1:] > 0)) if len(diff_v) > 1 else 0

    # 42-43. Variaciones Absolutas y Longitud
    mean_abs_diff = np.mean(np.abs(diff_v)) if len(diff_v) > 0 else 0.0
    waveform_length = np.sum(np.abs(diff_v))

    # 44-50. Medidas Robustas y Avanzadas
    mad = np.median(np.abs(valores - median))
    cv = (std / mean) if mean != 0 else 0.0
    kurtosis_excess = kurtosis
    entropy = float(stats.entropy(np.histogram(valores, bins=min(5, n_val))[0] + 1e-12))
    trimmed_mean_10 = stats.trim_mean(valores, 0.1)
    skewness_diff = float(stats.skew(diff_v)) if diff_std > 0 else 0.0
    snr_temporal = (mean**2 / var) if var != 0 else 0.0

    # Consolidar exactamente las 50 métricas en un diccionario ordenado
    return {
        'Media': mean, 'Desviacion_Estandar': std, 'Varianza': var, 'Mediana': median,
        'Minimo': minimum, 'Maximo': maximum, 'Rango': p_range, 'Asimetria': skewness,
        'Curtosis': kurtosis, 'Percentil_01': q01, 'Percentil_05': q05, 'Percentil_10': q10,
        'Percentil_25': q25, 'Percentil_75': q75, 'Percentil_90': q90, 'Percentil_95': q95,
        'Percentil_99': q99, 'Rango_Intercuartil': iqr, 'Rango_90_10': q_range_90_10,
        'Rango_99_01': q_range_99_01, 'RMS': rms, 'Media_Absoluta': abs_mean,
        'Media_Raiz_Cuadrada': sqr_mean_sq, 'Pico_Absoluto': peak_abs, 'Factor_Cresta': crest_factor,
        'Factor_Forma': shape_factor, 'Factor_Impulso': impulse_factor, 'Factor_Margen': margin_factor,
        'Energia': energy, 'Potencia': power, 'Diferencia_Media': diff_mean,
        'Diferencia_Desv': diff_std, 'Diferencia_RMS': diff_rms, 'Diferencia_Max_Abs': diff_max,
        'Diff2_Media': diff2_mean, 'Diff2_Desv': diff2_std, 'Diff2_RMS': diff2_rms,
        'Cruces_Por_Cero': zero_crossings, 'Cruces_Por_Media': mean_crossings,
        'Picos_Positivos': positive_turns, 'Picos_Negativos': negative_turns,
        'Diferencia_Absoluta_Media': mean_abs_diff, 'Longitud_Onda': waveform_length,
        'MAD': mad, 'Coeficiente_Variacion': cv, 'Exceso_Curtosis': kurtosis_excess,
        'Entropia_Histograma': entropy, 'Media_Recortada_10': trimmed_mean_10,
        'Diferencia_Asimetria': skewness_diff, 'SNR_Temporal': snr_temporal
    }

# ==========================================
# EJECUCIÓN PRINCIPAL
# ==========================================
archivo_entrada = r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\datos\DATASET_8+3+1\caracteristicas_wavelet___10.csv"
archivo_salida = r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\50_METRICAS_DOMINIO_TIEMPO\metricas_estadisticas_ventanas__10.csv"

print("Cargando el documento...")
df = pd.read_csv(archivo_entrada)

# Separar identificadores o metadatos si existen para conservarlos intactos en la salida
metadatos = df[['ID_Ventana', 'Estado']].copy() if {'ID_Ventana', 'Estado'}.issubset(df.columns) else pd.DataFrame(index=df.index)

# Seleccionar solo las columnas numéricas de características para calcular las 50 métricas por fila
cols_numericas = df.drop(columns=['ID_Ventana', 'Estado'], errors='ignore')

print(f"Procesando {len(df)} ventanas (filas)...")
lista_resultados = []

for idx, row in cols_numericas.iterrows():
    metricas = generar_50_metricas_por_fila(row)
    lista_resultados.append(metricas)

# Crear DataFrame con las 50 métricas calculadas
df_metricas = pd.DataFrame(lista_resultados)

# Unir con los metadatos originales (ID_Ventana y Estado)
df_final = pd.concat([metadatos, df_metricas], axis=1)

# Guardar el resultado en formato CSV
df_final.to_csv(archivo_salida, index=False)
print(f"¡Proceso exitoso! Archivo guardado en: {archivo_salida}")
print(f"Dimensiones finales: {df_final.shape[0]} filas, {df_final.shape[1]} columnas.")