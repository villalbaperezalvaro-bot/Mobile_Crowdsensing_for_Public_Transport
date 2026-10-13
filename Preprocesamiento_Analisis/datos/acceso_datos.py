import pandas as pd

def leer_csv(ruta):
    """Lee un archivo CSV y retorna un DataFrame."""
    return pd.read_csv(ruta)

def guardar_csv(df, ruta):
    """Guarda un DataFrame en CSV."""
    df.to_csv(ruta, index=False)