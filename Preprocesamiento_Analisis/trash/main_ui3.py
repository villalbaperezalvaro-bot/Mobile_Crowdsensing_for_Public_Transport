import sys
import pandas as pd


from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QFileDialog,
    QVBoxLayout, QFormLayout, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTabWidget, QHBoxLayout
)
from PyQt6.QtGui import QFont
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from datos.acceso_datos import leer_csv, guardar_csv
from logica.procesamiento import extraer_caracteristicas_wavelet
from logica.magnitud import calcular_magnitud
from logica.segmentar_traslape import segmentar_traslape_csv

class AnalisisWaveletApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("📊 Análisis TWD - Wavelet Interactivo Pro")
        self.setGeometry(100, 50, 1200, 800)
        self.setStyleSheet("""
            QWidget { background-color: #1e1e2f; color: #ffffff; }
            QLabel { font-size: 14px; }
            QPushButton { background-color: #4caf50; color: white; font-weight: bold; padding: 6px; border-radius: 5px; }
            QPushButton:hover { background-color: #45a049; }
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox { background-color: #2e2e3f; color: #ffffff; padding: 4px; border-radius: 4px; }
            QTextEdit { background-color: #2e2e3f; color: #ffffff; }
        """)

        # Layout principal
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

        #------------------------- Tabs para gráficos -------------------------
        self.tabs = QTabWidget()
        # Magnitud
        self.figura_magnitud = Figure(figsize=(5, 4), dpi=100)
        self.canvas_magnitud = FigureCanvas(self.figura_magnitud)
        self.toolbar_magnitud = NavigationToolbar(self.canvas_magnitud, self)
        magnitud_tab = QWidget()
        magnitud_layout = QVBoxLayout()
        magnitud_layout.addWidget(self.toolbar_magnitud)
        magnitud_layout.addWidget(self.canvas_magnitud)
        magnitud_tab.setLayout(magnitud_layout)
        self.tabs.addTab(magnitud_tab, "Magnitud")

        # Ventanas
        self.figura_ventanas = Figure(figsize=(5, 4), dpi=100)
        self.canvas_ventanas = FigureCanvas(self.figura_ventanas)
        self.toolbar_ventanas = NavigationToolbar(self.canvas_ventanas, self)
        ventanas_tab = QWidget()
        ventanas_layout = QVBoxLayout()
        ventanas_layout.addWidget(self.toolbar_ventanas)
        ventanas_layout.addWidget(self.canvas_ventanas)
        ventanas_tab.setLayout(ventanas_layout)
        self.tabs.addTab(ventanas_tab, "Ventanas Segmentadas")

        # Coeficientes
        coef_tab = QWidget()
        coef_layout = QVBoxLayout()
        self.figura_coef = Figure(figsize=(5, 4), dpi=100)
        self.canvas_coef = FigureCanvas(self.figura_coef)
        self.toolbar_coef = NavigationToolbar(self.canvas_coef, self)
        coef_layout.addWidget(self.toolbar_coef)
        coef_layout.addWidget(self.canvas_coef)

        # Selector de ventana
        self.combo_ventana = QComboBox()
        self.combo_ventana.currentIndexChanged.connect(self.actualizar_coef_plot)
        combo_layout = QHBoxLayout()
        combo_layout.addWidget(QLabel("Seleccionar ventana:"))
        combo_layout.addWidget(self.combo_ventana)
        coef_layout.addLayout(combo_layout)

        coef_tab.setLayout(coef_layout)
        self.tabs.addTab(coef_tab, "Coeficientes Wavelet")

        #------------------------- Log de progreso -------------------------
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Courier", 10))

        #------------------------- Layout final -------------------------
        self.layout.addLayout(self.form_layout)
        self.layout.addWidget(self.btn_ejecutar)
        self.layout.addWidget(self.tabs)
        self.layout.addWidget(QLabel("Registro de Progreso:"))
        self.layout.addWidget(self.log_text)

        self.setLayout(self.layout)

        # Datos internos
        self.ventanas_segmentadas = None
        self.coef_list = []

    #------------------------- Funciones -------------------------
    def seleccionar_csv(self):
        ruta, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo CSV", "", "CSV Files (*.csv)")
        if ruta:
            self.csv_input.setText(ruta)

    def log(self, mensaje):
        self.log_text.append(mensaje)
        QApplication.processEvents()

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

            # Leer CSV
            self.log("📥 Leyendo CSV de entrada...")
            df = leer_csv(ruta_entrada)

            # Calcular magnitud
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

            # Plot magnitud
            self.figura_magnitud.clear()
            ax = self.figura_magnitud.add_subplot(111)
            ax.plot(pd.to_datetime(df_magnitud["Timestamp"]), df_magnitud["Magnitud"], color='cyan')
            ax.set_title("Magnitud del Acelerómetro")
            ax.set_xlabel("Timestamp")
            ax.set_ylabel("Magnitud")
            self.canvas_magnitud.draw()

            # Segmentar señal
            self.log("✂️ Segmentando señal...")
            self.ventanas_segmentadas = segmentar_traslape_csv(ruta_magnitud, ventana_seg, traslape_pct, porcentaje_estado)
            ruta_segmentadas = "salida/ventanas_segmentadas.csv"
            guardar_csv(self.ventanas_segmentadas, ruta_segmentadas)
            self.log(f"✅ Ventanas segmentadas guardadas en {ruta_segmentadas}")

            # Plot ventanas
            self.figura_ventanas.clear()
            ax2 = self.figura_ventanas.add_subplot(111)
            for id_ventana, grupo in self.ventanas_segmentadas.groupby("ID_Ventana"):
                ax2.plot(grupo.index, grupo["Magnitud"], label=f'Ventana {id_ventana}')
            ax2.set_title("Ventanas Segmentadas")
            ax2.set_xlabel("Muestras")
            ax2.set_ylabel("Magnitud")
            ax2.legend(fontsize=8)
            self.canvas_ventanas.draw()

            # Extraer características
            self.log("📊 Extrayendo características Wavelet...")
            caract_list = []
            self.coef_list = []
            self.combo_ventana.clear()
            for id_ventana, grupo in self.ventanas_segmentadas.groupby("ID_Ventana"):
                ventana_total = grupo["Magnitud"].values
                caract, coef_puros = extraer_caracteristicas_wavelet(ventana_total, tipo_wavelet, niveles)
                caract_list.append(caract)
                coef_dict = {"ID_Ventana": id_ventana, "coef_puros": coef_puros}
                self.coef_list.append(coef_dict)
                self.combo_ventana.addItem(str(id_ventana))

            # Guardar CSVs
            ruta_caract = "salida/caracteristicas_wavelet.csv"
            guardar_csv(pd.DataFrame(caract_list), ruta_caract)
            self.log(f"✅ Características guardadas en {ruta_caract}")

            ruta_coef = "salida/coeficientes_wavelet.csv"
            # Guardar coeficientes en formato plano
            coef_flat = []
            for c in self.coef_list:
                dic = {"ID_Ventana": c["ID_Ventana"]}
                for i, coef in enumerate(c["coef_puros"]):
                    if i == 0:
                        dic[f"A{niveles}_coefs"] = ",".join(map(str, coef))
                    else:
                        dic[f"D{i}_coefs"] = ",".join(map(str, coef))
                coef_flat.append(dic)
            guardar_csv(pd.DataFrame(coef_flat), ruta_coef)
            self.log(f"✅ Coeficientes guardados en {ruta_coef}")

            # Mostrar primera ventana por defecto
            if self.coef_list:
                self.combo_ventana.setCurrentIndex(0)
                self.actualizar_coef_plot()

            self.log("🎉 Análisis completado exitosamente.")

        except Exception as e:
            self.log(f"❌ Error: {e}")

    def actualizar_coef_plot(self):
        idx = self.combo_ventana.currentIndex()
        if idx < 0 or idx >= len(self.coef_list):
            return
        coef_puros = self.coef_list[idx]["coef_puros"]
        self.figura_coef.clear()
        ax = self.figura_coef.add_subplot(111)
        niveles = len(coef_puros) - 1
        for i, coef in enumerate(coef_puros):
            if i == 0:
                ax.plot(coef, label=f'Aproximación Nivel {niveles}')
            else:
                ax.plot(coef, linestyle='--', alpha=0.7, label=f'Detalle {i}')
        ax.set_title(f"Coeficientes Wavelet - Ventana {self.coef_list[idx]['ID_Ventana']}")
        ax.set_xlabel("Coeficientes")
        ax.set_ylabel("Valor")
        ax.legend(fontsize=8)
        self.canvas_coef.draw()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = AnalisisWaveletApp()
    ventana.show()
    sys.exit(app.exec())
