import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import confusion_matrix, classification_report

# ==========================================
# 1. CONFIGURACIÓN DE RUTAS DE ENTRADA Y SALIDA
# ==========================================
RUTA_ENTRADA_CSV = r"C:\Users\villa\Desktop\INAOE\fro\datasetBalanceado20000_11.csv"
RUTA_SALIDA_CSV =  r"C:\Users\villa\Desktop\INAOE\fro\INpredicciones_unidades_1.csv"
RUTA_MATRIZ_CONFUSION = r"C:\Users\villa\Desktop\INAOE\fro\INmatriz_confusion_svm.png"

# Configuración de ventana (5 segundos a 100 Hz, sin traslape)
FS_HZ = 100
DURACION_VENTANA_SEG = 5
TAMANO_VENTANA = FS_HZ * DURACION_VENTANA_SEG  # 500 muestras
PASO_VENTANA = TAMANO_VENTANA                  # Sin traslape (paso = 500)

# ==========================================
# 2. CARGA Y EXTRACCIÓN DE CARACTERÍSTICAS (SHAZAM)
# ==========================================
def cargar_y_procesar_datos(ruta_csv, tamaño_ventana=TAMANO_VENTANA, paso=PASO_VENTANA):
    df = pd.read_csv(ruta_csv)
    
    # Magnitud vectorial de la aceleración: sqrt(X^2 + Y^2 + Z^2)
    df['Accel_Mag'] = np.sqrt(df['AccelX']**2 + df['AccelY']**2 + df['AccelZ']**2)
    
    X_caracteristicas = []
    y_etiquetas = []
    
    # Procesar ventanas deslizantes por cada unidad/estado
    for estado, grupo in df.groupby('Estado'):
        gx, gy, gz, gm = grupo['AccelX'].values, grupo['AccelY'].values, grupo['AccelZ'].values, grupo['Accel_Mag'].values
        
        for i in range(0, len(grupo) - tamaño_ventana + 1, paso):
            wx = gx[i : i + tamaño_ventana]
            wy = gy[i : i + tamaño_ventana]
            wz = gz[i : i + tamaño_ventana]
            wm = gm[i : i + tamaño_ventana]
            
            # Extraer huella estadística de la ventana
            feat = [
                np.mean(wx), np.std(wx), np.min(wx), np.max(wx),
                np.mean(wy), np.std(wy), np.min(wy), np.max(wy),
                np.mean(wz), np.std(wz), np.min(wz), np.max(wz),
                np.mean(wm), np.std(wm), np.min(wm), np.max(wm)
            ]
            X_caracteristicas.append(feat)
            y_etiquetas.append(estado)
            
    return np.array(X_caracteristicas), np.array(y_etiquetas)

print(f"Cargando dataset y extrayendo huellas (Ventana: {TAMANO_VENTANA} muestras, sin traslape)...")
X, y = cargar_y_procesar_datos(RUTA_ENTRADA_CSV, tamaño_ventana=TAMANO_VENTANA, paso=PASO_VENTANA)

if len(y) == 0:
    raise ValueError(
        f"No se pudieron generar ventanas. Cada clase necesita al menos {TAMANO_VENTANA} muestras."
    )

conteo_clases = pd.Series(y).value_counts().sort_index()
print(f"\nTotal de ventanas extraídas: {len(y)}")
print("Distribución de ventanas por clase/unidad:")
for cls, cnt in conteo_clases.items():
    print(f"  Unidad/Clase {cls}: {cnt} ventana(s)")

# Filtrar clases con menos de 2 muestras (se requieren al menos 1 para train y 1 para test)
clases_validas = conteo_clases[conteo_clases >= 2].index
if len(clases_validas) < len(conteo_clases):
    descartadas = conteo_clases[conteo_clases < 2]
    print(f"\n⚠️ Advertencia: Se omiten las siguientes clases por tener menos de 2 ventanas: {list(descartadas.index)}")
    mask = np.isin(y, clases_validas)
    X = X[mask]
    y = y[mask]

# ==========================================
# DIVISIÓN: 80% ENTRENAMIENTO / 20% PRUEBA
# ==========================================
PORCENTAJE_TEST = 0.20  # 20% para prueba, 80% para entrenamiento

print(f"\nDividiendo datos exactamente en 80% Entrenamiento y 20% Prueba...")

try:
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=PORCENTAJE_TEST, random_state=42, stratify=y
    )
except ValueError:
    # Si el 20% de muestras es menor que la cantidad de clases,
    # se realiza la partición exacta 80% / 20% sin requerir estratificación estricta
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=PORCENTAJE_TEST, random_state=42
    )

print(f"-> Entrenamiento {1-PORCENTAJE_TEST}: {len(y_train)} muestras | Prueba {PORCENTAJE_TEST}: {len(y_test)} muestras")

# Escalamiento de variables
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# ==========================================
# 3. ENTRENAMIENTO ONE-CLASS SVM MULTICLASE
# ==========================================
unidades = np.unique(y_train)
modelos_oc_svm = {}

print("\nEntrenando modelos One-Class SVM por cada unidad...")
for unidad in unidades:
    # Filtra solo los datos pertenecientes a la unidad actual
    X_unidad = X_train_scaled[y_train == unidad]
    
    # Entrena One-Class SVM para esta unidad específica
    oc_svm = OneClassSVM(kernel='rbf', gamma='scale', nu=0.05)
    oc_svm.fit(X_unidad)
    modelos_oc_svm[unidad] = oc_svm

# Evaluar puntuaciones de distancia para cada modelo One-Class SVM
matriz_puntajes = np.column_stack([
    modelos_oc_svm[u].decision_function(X_test_scaled) for u in unidades
])

# Asigna la unidad con la mayor puntuación de coincidencia (Efecto Shazam)
y_predicha = unidades[np.argmax(matriz_puntajes, axis=1)]

# ==========================================
# 4. GENERACIÓN DE ARCHIVOS DE SALIDA
# ==========================================
# Asegurar existencia de las carpetas de salida
os.makedirs(os.path.dirname(os.path.abspath(RUTA_SALIDA_CSV)), exist_ok=True)
os.makedirs(os.path.dirname(os.path.abspath(RUTA_MATRIZ_CONFUSION)), exist_ok=True)

columnas_feat = [
    'X_mean', 'X_std', 'X_min', 'X_max',
    'Y_mean', 'Y_std', 'Y_min', 'Y_max',
    'Z_mean', 'Z_std', 'Z_min', 'Z_max',
    'Mag_mean', 'Mag_std', 'Mag_min', 'Mag_max'
]
df_resultado = pd.DataFrame(X_test, columns=columnas_feat)
df_resultado['Unidad_Real'] = y_test
df_resultado['Unidad_Predicha'] = y_predicha
df_resultado['Acierto'] = df_resultado['Unidad_Real'] == df_resultado['Unidad_Predicha']

df_resultado.to_csv(RUTA_SALIDA_CSV, index=False)
print(f"\n-> Archivo CSV generado con éxito en: {RUTA_SALIDA_CSV}")

# Generar y guardar Matriz de Confusión
cm = confusion_matrix(y_test, y_predicha, labels=unidades)
plt.figure(figsize=(10, 8))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=unidades, yticklabels=unidades)
plt.title("Matriz de Confusión - Shazam de Unidades (One-Class SVM Ensemble)")
plt.xlabel("Unidad / Estado Predicho")
plt.ylabel("Unidad / Estado Real")
plt.tight_layout()
plt.savefig(RUTA_MATRIZ_CONFUSION)
plt.close()
print(f"-> Matriz de confusión guardada como imagen en: {RUTA_MATRIZ_CONFUSION}")

# Reporte final
print("\n--- REPORTE DE CLASIFICACIÓN ---")
print(classification_report(y_test, y_predicha, labels=unidades, zero_division=0))