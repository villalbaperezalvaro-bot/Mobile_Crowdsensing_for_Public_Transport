def normalizar_minmax(df):
    df_normalizado = df.copy()
    for columna in df.columns:
        min_val = df[columna].min()
        max_val = df[columna].max()
        df_normalizado[columna] = (
            (df[columna] - min_val) / (max_val - min_val)
            if max_val - min_val != 0 else 0
        )
    return df_normalizado
