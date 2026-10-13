import numpy as np
import pywt

def extraer_caracteristicas_wavelet(ventana, wavelet='db1', niveles=3):
    """
    Extrae características de los coeficientes Wavelet validando longitud mínima.
    """
    # 🛡️ Validar que la ventana exista y tenga suficientes muestras para el nivel de descomposición
    if ventana is None or len(ventana) < (2 ** niveles):
        return None, None
        
    try:
        coeficientes = pywt.wavedec(ventana, wavelet, level=niveles)
        
        caracteristicas = {
            f"A{niveles}_prom": np.mean(coeficientes[0]),
            f"A{niveles}_desv": np.std(coeficientes[0])
        }
        for i in range(1, len(coeficientes)):
            caracteristicas[f"D{i}_prom"] = np.mean(coeficientes[i])
            caracteristicas[f"D{i}_desv"] = np.std(coeficientes[i])

        return caracteristicas, coeficientes
    except Exception as e:
        print(f"Error en Wavelet: {e}")
        return None, None