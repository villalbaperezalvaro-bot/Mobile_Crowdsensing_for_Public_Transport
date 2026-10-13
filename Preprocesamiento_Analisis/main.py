
from datos.acceso_datos import leer_csv, guardar_csv
from logica.procesamiento import extraer_caracteristicas_wavelet
from logica.magnitud import calcular_magnitud
from logica.segmentar_traslape import segmentar_traslape_csv
import pandas as pd

#--------------------------------------------------------------

# Ruta del CSV
ruta_entrada = r"datos\acel_20250826_113055_1_1756229455807.csv"

# Leer datos
df = leer_csv(ruta_entrada)

# Calcular magnitud
magnitud = calcular_magnitud(df["AccelX"], df["AccelY"], df["AccelZ"])

df_magnitud = pd.DataFrame({
    "Timestamp": df["Timestamp"],
    "Magnitud": magnitud,
    "Estado": df["Estado"]
})
guardar_csv(df_magnitud, "salida/magnitud_acel.csv")
#---------------------------------------------------------------
ruta_csv_magnitud = "salida/magnitud_acel.csv"
ventana_seg = 1.0  # Tamaño de ventana en segundos
porcentaje_estado = 50.0  # Porcentaje mínimo de muestras del estado mayoritario
traslape_pct = 50  # Porcentaje de traslape

# Segmentar señal
ventanas_segmentadas = segmentar_traslape_csv(ruta_csv_magnitud,ventana_seg,traslape_pct,porcentaje_estado)
guardar_csv(ventanas_segmentadas, "salida/ventanas_segmentadas.csv")
#---------------------------------------------------------------

ruta_csv_ventanas = "salida/ventanas_segmentadas.csv"
ventanas_segmentadas = leer_csv(ruta_csv_ventanas)

tipo_wavelet = 'db1'
niveles = 3

caract_list = []
coef_list = []

for id_ventana, grupo in ventanas_segmentadas.groupby("ID_Ventana"):
    ventana_total = grupo["Magnitud"].values
    
    # Extraer características y coeficientes puros
    caract, coef_puros = extraer_caracteristicas_wavelet(ventana_total, tipo_wavelet, niveles)
    
    # Agregar ID de la ventana a las características
    caract_list.append(caract)
    
    # Guardar coeficientes puros en un diccionario y agregar ID de la ventana
    coef_dict = {"ID_Ventana": id_ventana}
    for i, coef in enumerate(coef_puros):
        if i == 0:
            coef_dict[f"A3_coefs"] = ",".join(map(str, coef))  # Aproximación último nivel
        else:
            coef_dict[f"D{i}_coefs"] = ",".join(map(str, coef))  # Detalles
    coef_list.append(coef_dict)

# Guardar CSV de características resumidas
df_caract = pd.DataFrame(caract_list)
guardar_csv(df_caract, "salida/caracteristicas_wavelet.csv")

# Guardar CSV de coeficientes puros
df_coef = pd.DataFrame(coef_list)
guardar_csv(df_coef, "salida/coeficientes_wavelet.csv")
#---------------------------------------------------------------     
