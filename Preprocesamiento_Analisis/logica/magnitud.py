#Calcular magnitud

import numpy as np
import pandas as pd

def calcular_magnitud(eje_x, eje_y, eje_z):
    """
    Calcula la magnitud del vector aceleración a partir de los ejes X, Y, Z,
    convirtiéndolos a numéricos para evitar errores de tipo string.
    """
    # Convertir las series/listas a arrays de numpy asegurando tipo numérico float
    x = pd.to_numeric(pd.Series(eje_x).astype(str).str.replace(r'\.(?=.*\.)', '', regex=True), errors='coerce')
    y = pd.to_numeric(pd.Series(eje_y).astype(str).str.replace(r'\.(?=.*\.)', '', regex=True), errors='coerce')
    z = pd.to_numeric(pd.Series(eje_z).astype(str).str.replace(r'\.(?=.*\.)', '', regex=True), errors='coerce')
    
    return np.sqrt(x**2 + y**2 + z**2)