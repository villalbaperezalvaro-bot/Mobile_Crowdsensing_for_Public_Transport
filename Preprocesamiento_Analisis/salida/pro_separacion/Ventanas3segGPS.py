import pandas as pd
from datetime import datetime

def dividir_csv_por_ventanas(ruta_csv, columna_tiempo, segundos_ventana=3):
    """
    Lee un archivo CSV y genera nuevos CSVs divididos en ventanas de tiempo exactas.
    """
    # 1. Cargar el archivo CSV
    df = pd.read_csv(ruta_csv)
    
    # 2. Asegurar que la columna de tiempo esté en formato datetime
    df[columna_tiempo] = pd.to_datetime(df[columna_tiempo])
    
    # 3. Ordenar los datos cronológicamente
    df = df.sort_values(by=columna_tiempo).reset_index(drop=True)
    
    # 4. Obtener el tiempo de inicio y agrupar por bloques de 3 segundos
    inicio_base = df[columna_tiempo].min()
    
    # Creamos una columna auxiliar que calcula la diferencia en segundos desde el inicio,
    # dividida entera entre 3 para obtener el ID de la ventana.
    df['delta_segundos'] = (df[columna_tiempo] - inicio_base).dt.total_seconds()
    df['ventana_id'] = (df['delta_segundos'] // segundos_ventana).astype(int)
    
    # 5. Iterar sobre cada grupo/ventana y exportar a un nuevo CSV
    for ventana_id, grupo in df.groupby('ventana_id'):
        # Limpiar columnas auxiliares antes de guardar
        grupo_limpio = grupo.drop(columns=['delta_segundos', 'ventana_id'])
        
        # Generar un nombre único para el archivo basado en el número de ventana o timestamp
        nombre_archivo = f"ventana_{ventana_id + 1}_de_{segundos}s.csv"
        grupo_limpio.to_csv(nombre_archivo, index=False)
        print(f"Generado: {nombre_archivo} con {len(grupo_limpio)} registros.")

# Ejemplo de uso:
# dividir_csv_por_ventanas('tu_archivo.csv', 'timestamp', segundos_ventana=3)