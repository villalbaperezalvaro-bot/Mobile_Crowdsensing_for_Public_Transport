import sys
import os
import pandas as pd
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QFileDialog, QTextEdit, QSpinBox, QFormLayout)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QTextCursor

# ---------------------------------------------------------
# ESTILO VISUAL (Dark Theme basado en tu imagen)
# ---------------------------------------------------------
ESTILO_OSCURO = """
QMainWindow, QWidget {
    background-color: #1a1a24;
    color: #e0e0e0;
    font-family: 'Segoe UI', Arial, sans-serif;
}
QLabel {
    font-size: 13px;
}
QLineEdit, QSpinBox {
    background-color: #2b2b36;
    border: 1px solid #3f3f5a;
    border-radius: 4px;
    padding: 6px;
    color: #ffffff;
}
QPushButton {
    background-color: #5d5cde;
    color: white;
    border: none;
    border-radius: 5px;
    padding: 8px 15px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #7271f2;
}
QPushButton:disabled {
    background-color: #3f3f5a;
    color: #888888;
}
QTextEdit {
    background-color: #0d0d14;
    border: 1px solid #3f3f5a;
    border-radius: 4px;
    padding: 5px;
    color: #a6e3a1; /* Texto verde estilo terminal */
    font-family: 'Consolas', 'Courier New', monospace;
}
"""

# ---------------------------------------------------------
# REDIRECCIÓN DE CONSOLA A LA INTERFAZ
# ---------------------------------------------------------
class ConsolaEmisor(QObject):
    texto_escrito = pyqtSignal(str)

    def write(self, text):
        self.texto_escrito.emit(str(text))

    def flush(self):
        pass

# ---------------------------------------------------------
# HILO DE TRABAJO (Para no congelar la UI)
# ---------------------------------------------------------
class WorkerProcesamiento(QThread):
    finalizado = pyqtSignal(bool, str)

    def __init__(self, acel, gps, salida, muestras):
        super().__init__()
        self.archivo_acel = acel
        self.archivo_gps = gps
        self.archivo_salida = salida
        self.muestras_por_ventana = muestras

    def run(self):
        try:
            print("--- INICIANDO PROCESAMIENTO ---")
            print(f"Acelerómetro: {self.archivo_acel}")
            print(f"GPS: {self.archivo_gps}")
            
            # Lógica de alineación
            df_acel = pd.read_csv(self.archivo_acel)
            df_gps = pd.read_csv(self.archivo_gps)

            df_acel["Timestamp"] = pd.to_datetime(df_acel["Timestamp"])
            df_gps["Timestamp"] = pd.to_datetime(df_gps["Timestamp"])

            df_acel = df_acel.sort_values("Timestamp").reset_index(drop=True)
            df_gps = df_gps.sort_values("Timestamp").reset_index(drop=True)

            print("Calculando solapamiento temporal...")
            t_start = max(df_acel["Timestamp"].min(), df_gps["Timestamp"].min())
            t_end = min(df_acel["Timestamp"].max(), df_gps["Timestamp"].max())

            df_acel = df_acel[(df_acel["Timestamp"] >= t_start) & (df_acel["Timestamp"] <= t_end)].reset_index(drop=True)
            df_gps = df_gps[(df_gps["Timestamp"] >= t_start) & (df_gps["Timestamp"] <= t_end)].reset_index(drop=True)

            cols_gps = [c for c in df_gps.columns if c != "Estado"]

            print("Alineando sensores (merge_asof)...")
            df_merged = pd.merge_asof(df_acel, df_gps[cols_gps], on="Timestamp", direction="nearest")

            cols_numericas_gps = [c for c in cols_gps if c != "Timestamp"]
            df_merged[cols_numericas_gps] = df_merged[cols_numericas_gps].fillna(0.0)

            print(f"Segmentando en ventanas de {self.muestras_por_ventana} muestras...")
            ventanas = []
            window_id = 0
            total_filas = len(df_merged)

            for start_idx in range(0, total_filas - self.muestras_por_ventana + 1, self.muestras_por_ventana):
                window_data = df_merged.iloc[start_idx : start_idx + self.muestras_por_ventana].copy()
                window_data["WindowID"] = window_id
                
                marcas = [""] * self.muestras_por_ventana
                marcas[0] = "Inicio"
                marcas[-1] = "Fin"
                window_data["Marca_Ventana"] = marcas
                
                ventanas.append(window_data)
                window_id += 1

            if ventanas:
                dataset_final = pd.concat(ventanas, ignore_index=True)
                cols_ordenadas = ["Timestamp", "AccelX", "AccelY", "AccelZ", "Latitud", "Longitud", 
                                  "Altitud", "Precision", "Velocidad", "Estado", "WindowID", "Marca_Ventana"]
                
                dataset_final = dataset_final[[c for c in cols_ordenadas if c in dataset_final.columns]]
                
                dataset_final.to_csv(self.archivo_salida, index=False)
                print(f"\n¡ÉXITO! Archivo guardado en:\n{self.archivo_salida}")
                print(f"Ventanas generadas: {window_id} | Total registros: {len(dataset_final)}")
                self.finalizado.emit(True, "Proceso completado correctamente.")
            else:
                self.finalizado.emit(False, "Error: Los archivos no tienen un rango de tiempo en común.")

        except Exception as e:
            print(f"\nERROR DURANTE LA EJECUCIÓN:\n{str(e)}")
            self.finalizado.emit(False, str(e))

# ---------------------------------------------------------
# INTERFAZ GRÁFICA PRINCIPAL
# ---------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Análisis de Sensores - Alineación y Segmentación")
        self.resize(850, 650)
        self.setStyleSheet(ESTILO_OSCURO)

        # Widget central
        widget_central = QWidget()
        self.setCentralWidget(widget_central)
        layout_principal = QVBoxLayout(widget_central)
        layout_principal.setSpacing(15)

        # Formulario superior
        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        # 1. Archivo Acelerómetro
        self.input_acel = QLineEdit()
        self.input_acel.setPlaceholderText("Selecciona el CSV de acelerómetro...")
        btn_acel = QPushButton("📁 Seleccionar CSV")
        btn_acel.clicked.connect(self.seleccionar_acel)
        layout_h_acel = QHBoxLayout()
        layout_h_acel.addWidget(self.input_acel)
        layout_h_acel.addWidget(btn_acel)
        form_layout.addRow("Acelerómetro (CSV):", layout_h_acel)

        # 2. Archivo GPS
        self.input_gps = QLineEdit()
        self.input_gps.setPlaceholderText("Selecciona el CSV de GPS...")
        btn_gps = QPushButton("📁 Seleccionar CSV")
        btn_gps.clicked.connect(self.seleccionar_gps)
        layout_h_gps = QHBoxLayout()
        layout_h_gps.addWidget(self.input_gps)
        layout_h_gps.addWidget(btn_gps)
        form_layout.addRow("GPS (CSV):", layout_h_gps)

        # 3. Ruta de salida
        self.input_salida_dir = QLineEdit()
        self.input_salida_dir.setPlaceholderText("Ruta donde se guardará...")
        btn_salida = QPushButton("📁 Carpeta Salida")
        btn_salida.clicked.connect(self.seleccionar_carpeta_salida)
        layout_h_salida = QHBoxLayout()
        layout_h_salida.addWidget(self.input_salida_dir)
        layout_h_salida.addWidget(btn_salida)
        form_layout.addRow("Carpeta de guardado:", layout_h_salida)

        # 4. Nombre de archivo
        self.input_nombre = QLineEdit()
        self.input_nombre.setText("Dataset_COMBINADO_alineado.csv")
        form_layout.addRow("Nombre de archivo:", self.input_nombre)

        # 5. Parámetros
        self.spin_muestras = QSpinBox()
        self.spin_muestras.setRange(10, 5000)
        self.spin_muestras.setValue(150)
        form_layout.addRow("Tamaño de ventana (muestras):", self.spin_muestras)

        layout_principal.addLayout(form_layout)

        # Botón de ejecución (Estilo botón ancho como en la imagen)
        self.btn_ejecutar = QPushButton("Ejecutar análisis")
        self.btn_ejecutar.setFixedHeight(40)
        self.btn_ejecutar.clicked.connect(self.ejecutar_analisis)
        layout_principal.addWidget(self.btn_ejecutar)

        # Consola de registro
        label_consola = QLabel("Registro de progreso:")
        layout_principal.addWidget(label_consola)

        self.consola = QTextEdit()
        self.consola.setReadOnly(True)
        layout_principal.addWidget(self.consola)

        # Redirigir stdout (print) a la consola
        sys.stdout = ConsolaEmisor()
        sys.stdout.texto_escrito.connect(self.actualizar_consola)
        sys.stderr = sys.stdout # Redirigir errores también

    def seleccionar_acel(self):
        ruta, _ = QFileDialog.getOpenFileName(self, "Seleccionar CSV de Acelerómetro", "", "CSV Files (*.csv)")
        if ruta: self.input_acel.setText(ruta)

    def seleccionar_gps(self):
        ruta, _ = QFileDialog.getOpenFileName(self, "Seleccionar CSV de GPS", "", "CSV Files (*.csv)")
        if ruta: self.input_gps.setText(ruta)

    def seleccionar_carpeta_salida(self):
        ruta = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta de Salida")
        if ruta: self.input_salida_dir.setText(ruta)

    def actualizar_consola(self, texto):
        cursor = self.consola.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(texto)
        self.consola.setTextCursor(cursor)
        self.consola.ensureCursorVisible()

    def ejecutar_analisis(self):
        acel = self.input_acel.text().strip()
        gps = self.input_gps.text().strip()
        carpeta = self.input_salida_dir.text().strip()
        nombre = self.input_nombre.text().strip()
        muestras = self.spin_muestras.value()

        if not acel or not gps or not carpeta or not nombre:
            print("\n[!] ADVERTENCIA: Por favor, llena todos los campos de rutas y nombres antes de ejecutar.")
            return

        ruta_final = os.path.join(carpeta, nombre)

        # Bloquear botón para evitar doble ejecución
        self.btn_ejecutar.setEnabled(False)
        self.btn_ejecutar.setText("Procesando... por favor espera")
        self.consola.clear()

        # Iniciar hilo
        self.worker = WorkerProcesamiento(acel, gps, ruta_final, muestras)
        self.worker.finalizado.connect(self.restaurar_ui)
        self.worker.start()

    def restaurar_ui(self, exito, mensaje):
        self.btn_ejecutar.setEnabled(True)
        self.btn_ejecutar.setText("Ejecutar análisis")

# ---------------------------------------------------------
# EJECUCIÓN
# ---------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = MainWindow()
    ventana.show()
    sys.exit(app.exec())