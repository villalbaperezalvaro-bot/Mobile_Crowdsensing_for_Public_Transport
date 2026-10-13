import pandas as pd
from pathlib import Path

# 1. Definir rutas relativas al script
base_dir = Path(__file__).resolve().parent
input_file = base_dir / 'dataset1.csv'
output_file = base_dir / 'dataset1_shuffled.csv'

# 2. Cargar el dataset
df = pd.read_csv(input_file)

# 3. Mezclar/randomizar todas las filas (frac=1 toma el 100% de los datos)
#    - random_state es opcional: pon un entero si quieres reproducibilidad o quítalo si quieres aleatoriedad pura
df_shuffled = df.sample(frac=1, random_state=42).reset_index(drop=True)

# 4. Guardar el nuevo CSV
df_shuffled.to_csv(output_file, index=False)

print(f"Dataset desordenado guardado en: {output_file}")