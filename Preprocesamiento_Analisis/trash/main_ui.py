import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QFileDialog, QVBoxLayout, QFormLayout, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox
)


from PyQt6.QtGui import QFont
from datos.acceso_datos import leer_csv, guardar_csv
from logica.procesamiento import extraer_caracteristicas_wavelet
from logica.magnitud import calcular_magnitud
from logica.segmentar_traslape import segmentar_traslape_csv
import pandas as pd

class AnalisisWaveletApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("📊 Análisis TWD - Wavelet")
        self.setGeometry(300, 100, 600, 500)
        self.setStyleSheet("""
            QWidget { background-color: #1e1e2f; color: #ffffff; }
            QLabel { font-size: 14px; }
            QPushButton { background-color: #4caf50; color: white; font-weight: bold; padding: 6px; border-radius: 5px; }
            QPushButton:hover { background-color: #45a049; }
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox { background-color: #2e2e3f; color: #ffffff; padding: 4px; border-radius: 4px; }
            QTextEdit { background-color: #2e2e3f; color: #ffffff; }
        """)

        self.layout = QVBoxLayout()
        self.form_layout = QFormLayout()

        #------------------------- Inputs -------------------------
        self.csv_input = QLineEdit()
        self.btn_browse_csv = QPushButton("Seleccionar CSV")
        self.btn_browse_csv.clicked.connect(self.seleccionar_csv)
        self.form_layout.addRow("Archivo CSV de entrada:", self.csv_input)
        self.form_layout.addRow("", self.btn_browse_csv)

        self.ventana_seg = QDoubleSpinBox()
        self.ventana_seg.setRange(0.1, 10.0)
        self.ventana_seg.setValue(1.0)
        self.ventana_seg.setSingleStep(0.1)
        self.form_layout.addRow("Tamaño de ventana (s):", self.ventana_seg)

        self.porcentaje_estado = QDoubleSpinBox()
        self.porcentaje_estado.setRange(0, 100)
        self.porcentaje_estado.setValue(50)
        self.form_layout.addRow("Porcentaje mínimo estado (%):", self.porcentaje_estado)

        self.traslape_pct = QSpinBox()
        self.traslape_pct.setRange(0, 100)
        self.traslape_pct.setValue(50)
        self.form_layout.addRow("Traslape (%):", self.traslape_pct)

        self.tipo_wavelet = QComboBox()
        self.tipo_wavelet.addItems(['db1','db2','db3','haar'])
        self.form_layout.addRow("Tipo de wavelet:", self.tipo_wavelet)

        self.niveles = QSpinBox()
        self.niveles.setRange(1, 10)
        self.niveles.setValue(3)
        self.form_layout.addRow("Niveles de descomposición:", self.niveles)

        #------------------------- Botón ejecutar -------------------------
        self.btn_ejecutar = QPushButton("✅ Ejecutar Análisis")
        self.btn_ejecutar.clicked.connect(self.ejecutar_analisis)

        #------------------------- Log de progreso -------------------------
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Courier", 10))

        #------------------------- Layout final -------------------------
        self.layout.addLayout(self.form_layout)
        self.layout.addWidget(self.btn_ejecutar)
        self.layout.addWidget(QLabel("Registro de Progreso:"))
        self.layout.addWidget(self.log_text)

        self.setLayout(self.layout)

    #------------------------- Funciones -------------------------
    def seleccionar_csv(self):
        ruta, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo CSV", "", "CSV Files (*.csv)")
        if ruta:
            self.csv_input.setText(ruta)

    def log(self, mensaje):
        self.log_text.append(mensaje)
        QApplication.processEvents()  # Para actualizar la interfaz en tiempo real

    def ejecutar_analisis(self):
        try:
            ruta_entrada = self.csv_input.text()
            if not ruta_entrada:
                self.log("❌ Por favor seleccione un archivo CSV de entrada.")
                return

            ventana_seg = self.ventana_seg.value()
            porcentaje_estado = self.porcentaje_estado.value()
            traslape_pct = self.traslape_pct.value()
            tipo_wavelet = self.tipo_wavelet.currentText()
            niveles = self.niveles.value()

            self.log("📥 Leyendo CSV de entrada...")
            df = leer_csv(ruta_entrada)

            self.log("🔹 Calculando magnitud...")
            magnitud = calcular_magnitud(df["AccelX"], df["AccelY"], df["AccelZ"])
            df_magnitud = pd.DataFrame({
                "Timestamp": df["Timestamp"],
                "Magnitud": magnitud,
                "Estado": df["Estado"]
            })
            ruta_magnitud = "salida/magnitud_acel.csv"
            guardar_csv(df_magnitud, ruta_magnitud)
            self.log(f"✅ Magnitud guardada en {ruta_magnitud}")

            self.log("✂️ Segmentando señal...")
            ventanas_segmentadas = segmentar_traslape_csv(ruta_magnitud, ventana_seg, traslape_pct, porcentaje_estado)
            ruta_segmentadas = "salida/ventanas_segmentadas.csv"
            guardar_csv(ventanas_segmentadas, ruta_segmentadas)
            self.log(f"✅ Ventanas segmentadas guardadas en {ruta_segmentadas}")

            self.log("📊 Extrayendo características Wavelet...")
            caract_list = []
            coef_list = []
            for id_ventana, grupo in ventanas_segmentadas.groupby("ID_Ventana"):
                ventana_total = grupo["Magnitud"].values
                caract, coef_puros = extraer_caracteristicas_wavelet(ventana_total, tipo_wavelet, niveles)
                caract_list.append(caract)
                coef_dict = {"ID_Ventana": id_ventana}
                for i, coef in enumerate(coef_puros):
                    if i == 0:
                        coef_dict[f"A{niveles}_coefs"] = ",".join(map(str, coef))
                    else:
                        coef_dict[f"D{i}_coefs"] = ",".join(map(str, coef))
                coef_list.append(coef_dict)

            ruta_caract = "salida/caracteristicas_wavelet.csv"
            guardar_csv(pd.DataFrame(caract_list), ruta_caract)
            self.log(f"✅ Características guardadas en {ruta_caract}")

            ruta_coef = "salida/coeficientes_wavelet.csv"
            guardar_csv(pd.DataFrame(coef_list), ruta_coef)
            self.log(f"✅ Coeficientes guardados en {ruta_coef}")

            self.log("🎉 Análisis completado exitosamente.")

        except Exception as e:
            self.log(f"❌ Error: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = AnalisisWaveletApp()
    ventana.show()
    sys.exit(app.exec())
