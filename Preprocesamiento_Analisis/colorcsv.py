import os
import pandas as pd

# Opción 1: Si el CSV está dentro de una carpeta 'datos' en tu directorio actual
file_path = "datos/acel_20251205_142624__1764966384456.csv_1764973941.csv"

# Opción 2: Si el CSV está en la misma carpeta que 'colorcsv.py'
# file_path = "acel_20251205_142624__1764966384456.csv_1764973941.csv"

# Verificar existencia antes de leer para evitar que truene el script
if not os.path.exists(file_path):
    raise FileNotFoundError(
        f"No se encontró el archivo en: {os.path.abspath(file_path)}"
    )

df = pd.read_csv(file_path)

# Mapeo de colores y nombres
color_map_hex = {
    0: "#1F77B4",
    1: "#FF7F0E",
    2: "#2CA02C",
    3: "#D62728",
    4: "#9467BD",
    5: "#8C564B",
    6: "#E377C2",
    7: "#7F7F7F",
}

state_names = {
    0: "Origen",
    1: "Caminando a la parada / Destino",
    2: "Esperando",
    3: "Ascendiendo",
    4: "De pie",
    5: "Sentado",
    6: "Descendiendo",
    7: "Destino",
}

df["Color_HEX"] = df["Estado"].map(color_map_hex)
df["Nombre_Estado"] = df["Estado"].map(state_names)

# Guardar resultado
output_path = "acelerometria_con_colores.csv"
df.to_csv(output_path, index=False)
print(f"Archivo guardado correctamente en: {output_path}")