from scipy.io import loadmat

archivo = loadmat(r"C:\Users\villa\Downloads\Nueva carpeta\SHLDataset_preview_v1\User1\270617\data.mat")

print(archivo.keys())  # Ver variables dentro del .mat