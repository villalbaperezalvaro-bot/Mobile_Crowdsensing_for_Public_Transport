import numpy as np
import pandas as pd
from scipy import stats

def calcular_50_metricas_tiempo(signal, prefix=''):
    """Calcula 50 métricas estadísticas en el dominio del tiempo para un array 1D."""
    # Convertir la fila a un array numérico, ignorando posibles NaNs
    s = np.asarray(signal, dtype=float)
    s = s[~np.isnan(s)] 
    n = len(s)
    
    if n == 0:
        return {f'{prefix}Media': np.nan} # Retorna vacío si la fila no tiene datos válidos
    
    # 1-7. Estadísticas Descriptivas Básicas
    mean = np.mean(s)
    std = np.std(s, ddof=1) if n > 1 else 0.0
    var = np.var(s, ddof=1) if n > 1 else 0.0
    median = np.median(s)
    minimum = np.min(s)
    maximum = np.max(s)
    p_range = maximum - minimum
    
    # 8-9. Momentos de Forma
    skewness = float(stats.skew(s)) if std > 0 else 0.0
    kurtosis = float(stats.kurtosis(s)) if std > 0 else 0.0
    
    # 10-20. Cuantiles, Percentiles y Rangos
    q01, q05, q10, q25, q75, q90, q95, q99 = np.percentile(s, [1, 5, 10, 25, 75, 90, 95, 99])
    iqr = q75 - q25
    q_range_90_10 = q90 - q10
    q_range_99_01 = q99 - q01
    
    # 21-24. Magnitudes de Amplitud y Normas
    rms = np.sqrt(np.mean(s**2))
    abs_mean = np.mean(np.abs(s))
    sqr_mean_sq = (np.mean(np.sqrt(np.abs(s))))**2
    peak_abs = np.max(np.abs(s))
    
    # 25-28. Factores Adimensionales de Forma y Diagnóstico
    crest_factor = (peak_abs / rms) if rms != 0 else 0.0
    shape_factor = (rms / abs_mean) if abs_mean != 0 else 0.0
    impulse_factor = (peak_abs / abs_mean) if abs_mean != 0 else 0.0
    margin_factor = (peak_abs / sqr_mean_sq) if sqr_mean_sq != 0 else 0.0
    
    # 29-30. Energía y Potencia
    energy = np.sum(s**2)
    power = np.mean(s**2)
    
    # 31-34. Estadísticas de Primera Diferencia (Velocidad Aproximada)
    diff_s = np.diff(s)
    diff_mean = np.mean(diff_s) if len(diff_s) > 0 else 0.0
    diff_std = np.std(diff_s, ddof=1) if len(diff_s) > 1 else 0.0
    diff_rms = np.sqrt(np.mean(diff_s**2)) if len(diff_s) > 0 else 0.0
    diff_max = np.max(np.abs(diff_s)) if len(diff_s) > 0 else 0.0
    
    # 35-37. Estadísticas de Segunda Diferencia (Aceleración Aproximada)
    diff2_s = np.diff(s, n=2)
    diff2_mean = np.mean(diff2_s) if len(diff2_s) > 0 else 0.0
    diff2_std = np.std(diff2_s, ddof=1) if len(diff2_s) > 1 else 0.0
    diff2_rms = np.sqrt(np.mean(diff2_s**2)) if len(diff2_s) > 0 else 0.0
    
    # 38-41. Eventos Temporales y Cruces
    zero_crossings = np.sum(np.diff(np.signbit(s)) != 0)
    mean_crossings = np.sum(np.diff(np.signbit(s - mean)) != 0)
    positive_turns = np.sum((diff_s[:-1] > 0) & (diff_s[1:] < 0)) if len(diff_s) > 1 else 0
    negative_turns = np.sum((diff_s[:-1] < 0) & (diff_s[1:] > 0)) if len(diff_s) > 1 else 0
    
    # 42-43. Longitud de Onda y Variación Absoluta
    mean_abs_diff = np.mean(np.abs(diff_s)) if len(diff_s) > 0 else 0.0
    waveform_length = np.sum(np.abs(diff_s))
    
    # 44-50. Medidas Robustas, Entropía y Métricas compuestas
    mad = np.median(np.abs(s - median))
    cv = (std / mean) if mean != 0 else 0.0
    kurtosis_excess = kurtosis
    entropy = float(stats.entropy(np.histogram(s, bins=10)[0] + 1e-12))
    trimmed_mean_10 = stats.trim_mean(s, 0.1)
    skewness_diff = float(stats.skew(diff_s)) if diff_std > 0 else 0.0
    snr_temporal = (mean**2 / var) if var != 0 else 0.0

    return {
        f'{prefix}Media': mean, f'{prefix}Desviacion_Estandar': std, f'{prefix}Varianza': var,
        f'{prefix}Mediana': median, f'{prefix}Minimo': minimum, f'{prefix}Maximo': maximum,
        f'{prefix}Rango': p_range, f'{prefix}Asimetria': skewness, f'{prefix}Curtosis': kurtosis,
        f'{prefix}Percentil_01': q01, f'{prefix}Percentil_05': q05, f'{prefix}Percentil_10': q10,
        f'{prefix}Percentil_25': q25, f'{prefix}Percentil_75': q75, f'{prefix}Percentil_90': q90,
        f'{prefix}Percentil_95': q95, f'{prefix}Percentil_99': q99, f'{prefix}Rango_Intercuartil': iqr,
        f'{prefix}Rango_90_10': q_range_90_10, f'{prefix}Rango_99_01': q_range_99_01, f'{prefix}RMS': rms,
        f'{prefix}Media_Absoluta': abs_mean, f'{prefix}Media_Raiz_Cuadrada': sqr_mean_sq,
        f'{prefix}Pico_Absoluto': peak_abs, f'{prefix}Factor_Cresta': crest_factor,
        f'{prefix}Factor_Forma': shape_factor, f'{prefix}Factor_Impulso': impulse_factor,
        f'{prefix}Factor_Margen': margin_factor, f'{prefix}Energia': energy, f'{prefix}Potencia': power,
        f'{prefix}Diferencia_Media': diff_mean, f'{prefix}Diferencia_Desv': diff_std,
        f'{prefix}Diferencia_RMS': diff_rms, f'{prefix}Diferencia_Max_Abs': diff_max,
        f'{prefix}Diff2_Media': diff2_mean, f'{prefix}Diff2_Desv': diff2_std, f'{prefix}Diff2_RMS': diff2_rms,
        f'{prefix}Cruces_Por_Cero': zero_crossings, f'{prefix}Cruces_Por_Media': mean_crossings,
        f'{prefix}Picos_Positivos': positive_turns, f'{prefix}Picos_Negativos': negative_turns,
        f'{prefix}Diferencia_Absoluta_Media': mean_abs_diff, f'{prefix}Longitud_Onda': waveform_length,
        f'{prefix}MAD': mad, f'{prefix}Coeficiente_Variacion': cv, f'{prefix}Exceso_Curtosis': kurtosis_excess,
        f'{prefix}Entropia_Histograma': entropy, f'{prefix}Media_Recortada_10': trimmed_mean_10,
        f'{prefix}Diferencia_Asimetria': skewness_diff, f'{prefix}SNR_Temporal': snr_temporal
    }

# 1. Definir rutas
# Asegúrate de que este archivo contiene los datos de la señal cruda (una columna por cada punto en el tiempo de la ventana)
archivo_entrada = r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\datos\DATASET_8+3+1\caracteristicas_wavelet___7.csv" 
archivo_salida = r"C:\Users\villa\Desktop\INAOE\shazam_camiones\shazam_camiones\50_METRICAS_DOMINIO_TIEMPO\metricas_estadisticas_ventanas7.csv"

# 2. Cargar datos
print("Cargando datos...")
df = pd.read_csv(archivo_entrada)

# 3. Separar metadatos (ID_Ventana, Estado) de los datos numéricos de la señal.
columnas_metadatos = ['ID_Ventana', 'Estado']
# Corrección de la comprensión de listas a sintaxis válida en Python
columnas_senal = [col for col in df.columns if col not in columnas_metadatos]

df_metadatos = df[columnas_metadatos] if set(columnas_metadatos).issubset(df.columns) else pd.DataFrame(index=df.index)
df_senal = df.drop(columns=columnas_metadatos, errors='ignore')

# 4. Calcular métricas FILA POR FILA (Ventana por Ventana)
print(f"Calculando 50 métricas para {len(df_senal)} ventanas...")
lista_metricas = []

for index, row in df_senal.iterrows():
    # Extraemos los valores de la fila actual
    metricas_ventana = calcular_50_metricas_tiempo(row.values)
    lista_metricas.append(metricas_ventana)

# 5. Convertir la lista de diccionarios a DataFrame y unir con los metadatos originales
df_metricas = pd.DataFrame(lista_metricas)
df_resultado = pd.concat([df_metadatos, df_metricas], axis=1)

# 6. Exportar a CSV
df_resultado.to_csv(archivo_salida, index=False)
print(f"Éxito: Se generó '{archivo_salida}' con {len(df_resultado)} filas y {len(df_resultado.columns)} columnas.")