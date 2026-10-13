import pandas as pd
import matplotlib.pyplot as plt

# 1. Leer archivo CSV
df = pd.read_csv("salida/train_12.csv")

# 2. Revisar las primeras filas para identificar las columnas
print("Columnas disponibles:", df.columns)
print(df.head())

# 3. Seleccionar dos columnas de características para graficar
x_col = "A3_prom"   # <-- cámbialo por otra columna si quieres
y_col = "D1_prom"   # <-- cámbialo también si quieres

# 4. Crear gráfico de dispersión
plt.figure(figsize=(8,6))
for estado in df["Estado"].unique():
    subset = df[df["Estado"] == estado]
    plt.scatter(subset[x_col], subset[y_col], label=f"Clase {estado}", alpha=0.7)

plt.xlabel(x_col)
plt.ylabel(y_col)
plt.title("Gráfico de Dispersión KNN")
plt.legend()
plt.grid(True)
plt.show()
