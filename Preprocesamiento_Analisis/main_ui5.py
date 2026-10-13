import sys
import os
import numpy as np
import pandas as pd
import datetime

from scipy.fft import rfft, rfftfreq
from scipy.signal import find_peaks

from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QVBoxLayout,
    QFormLayout,
    QTextEdit,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox,
    QTabWidget,
    QHBoxLayout,
    QMessageBox
)

from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt


# =====================================================
# WebEngine para incrustar Plotly
# =====================================================

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
except Exception as e:
    raise SystemExit(
        "Falta PyQt6-WebEngine. Instala con: "
        "pip install PyQt6-WebEngine\nError: " + str(e)
    )


# =====================================================
# Plotly
# =====================================================

import plotly.graph_objects as go
import plotly.io as pio


# =====================================================
# Módulos propios
# =====================================================

from datos.acceso_datos import leer_csv, guardar_csv
from logica.procesamiento import extraer_caracteristicas_wavelet
from logica.magnitud import calcular_magnitud
from logica.segmentar_traslape import segmentar_traslape_csv


# =====================================================
# VISTA PLOTLY
# =====================================================

class PlotlyView(QWebEngineView):
    """Wrapper para renderizar figuras Plotly en un QWebEngineView."""

    def __init__(self, parent=None):

        super().__init__(parent)

        self.setStyleSheet(
            "background: #1e1e2f;"
        )

    def set_figure(
        self,
        fig: go.Figure
    ):

        html = pio.to_html(
            fig,
            full_html=False,
            include_plotlyjs="cdn",
            config={
                "responsive": True,
                "displaylogo": False,
                "modeBarButtonsToRemove": [
                    "lasso2d",
                    "select2d"
                ],
            },
        )

        self.setHtml(html)


# =====================================================
# APLICACIÓN PRINCIPAL
# =====================================================

class AnalisisWaveletApp(QWidget):

    def __init__(self):

        super().__init__()

        self.setWindowTitle(
            "📊 Análisis Acelerómetro - Wavelet + FFT + Varianza"
        )

        self.setGeometry(
            60,
            30,
            1360,
            860
        )

        self.setStyleSheet(
            """
            QWidget {
                background-color: #0f1220;
                color: #e6e6e9;
            }

            QLabel {
                font-size: 14px;
            }

            QPushButton {
                background-color: #4f46e5;
                color: white;
                font-weight: 600;
                padding: 10px 14px;
                border-radius: 10px;
            }

            QPushButton:hover {
                background-color: #181283;
            }

            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
                background-color: #191c2b;
                color: #e6e6e9;
                padding: 8px;
                border-radius: 8px;
                border: 1px solid #2a2f45;
            }

            QTextEdit {
                background-color: #0f1428;
                color: #cbd5e1;
                border: 1px solid #243047;
                border-radius: 12px;
            }

            QTabWidget::pane {
                border: 1px solid #243047;
                border-radius: 12px;
            }

            QTabBar::tab {
                background: #191c2b;
                color: #e6e6e9;
                padding: 8px 16px;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }

            QTabBar::tab:selected {
                background: #0f1428;
            }
            """
        )

        # =================================================
        # ESTADO INTERNO
        # =================================================

        self.df_magnitud = None
        self.ventanas_segmentadas = None
        self.coef_por_ventana = {}
        self.fft_por_ventana = {}
        self.varianza_por_ventana = {}
        self.last_output_paths = {}

        # =================================================
        # LAYOUTS
        # =================================================

        root = QVBoxLayout(self)
        form = QFormLayout()

        # =================================================
        # ARCHIVO CSV
        # =================================================

        self.csv_input = QLineEdit()

        self.csv_input.setPlaceholderText(
            "Selecciona un CSV de entrada…"
        )

        btn_browse = QPushButton(
            "📂 Seleccionar CSV"
        )

        btn_browse.clicked.connect(
            self.seleccionar_csv
        )

        file_row = QHBoxLayout()

        file_row.addWidget(
            self.csv_input,
            stretch=1
        )

        file_row.addWidget(
            btn_browse
        )

        file_row_w = QWidget()

        file_row_w.setLayout(
            file_row
        )

        form.addRow(
            "Archivo CSV de entrada:",
            file_row_w
        )

        # =================================================
        # TAMAÑO DE VENTANA
        # =================================================

        self.ventana_seg = QDoubleSpinBox()

        self.ventana_seg.setRange(
            0.1,
            60.0
        )

        # Dataset trabajado: 3 segundos = 150 muestras
        self.ventana_seg.setValue(
            3.0
        )

        self.ventana_seg.setSingleStep(
            0.1
        )

        form.addRow(
            "Tamaño de ventana (s):",
            self.ventana_seg
        )

        # =================================================
        # FRECUENCIA DE MUESTREO
        # =================================================

        self.frecuencia_muestreo = QSpinBox()

        self.frecuencia_muestreo.setRange(
            1,
            1000
        )

        self.frecuencia_muestreo.setValue(
            50
        )

        form.addRow(
            "Frecuencia de muestreo FFT (Hz):",
            self.frecuencia_muestreo
        )

        # =================================================
        # VENTANA VARIANZA MOVIL
        # =================================================

        self.ventana_varianza = QDoubleSpinBox()

        self.ventana_varianza.setRange(
            0.02,
            2.0
        )

        # 0.2 segundos = 10 muestras a 50 Hz
        self.ventana_varianza.setValue(
            0.2
        )

        self.ventana_varianza.setSingleStep(
            0.05
        )

        form.addRow(
            "Ventana varianza móvil (s):",
            self.ventana_varianza
        )

        # =================================================
        # UMBRAL DE PICOS FFT
        # =================================================

        self.umbral_picos_fft = QDoubleSpinBox()

        self.umbral_picos_fft.setRange(
            0.01,
            1.0
        )

        self.umbral_picos_fft.setValue(
            0.30
        )

        self.umbral_picos_fft.setSingleStep(
            0.05
        )

        form.addRow(
            "Umbral picos FFT (% máximo):",
            self.umbral_picos_fft
        )

        # =================================================
        # PORCENTAJE DE ESTADO
        # =================================================

        self.porcentaje_estado = QDoubleSpinBox()

        self.porcentaje_estado.setRange(
            0,
            100
        )

        self.porcentaje_estado.setValue(
            80
        )

        form.addRow(
            "Porcentaje mínimo estado (%):",
            self.porcentaje_estado
        )

        # =================================================
        # TRASLAPE
        # =================================================

        self.traslape_pct = QSpinBox()

        self.traslape_pct.setRange(
            0,
            100
        )

        self.traslape_pct.setValue(
            0
        )

        form.addRow(
            "Traslape (%):",
            self.traslape_pct
        )

        # =================================================
        # TIPO DE WAVELET
        # =================================================

        self.tipo_wavelet = QComboBox()

        self.tipo_wavelet.addItems(
            [
                "db1",
                "db2",
                "db3",
                "db4",
                "haar"
            ]
        )

        form.addRow(
            "Tipo de wavelet:",
            self.tipo_wavelet
        )

        # =================================================
        # NIVELES DE DESCOMPOSICIÓN
        # =================================================

        self.niveles = QSpinBox()

        self.niveles.setRange(
            1,
            10
        )

        self.niveles.setValue(
            3
        )

        form.addRow(
            "Niveles de descomposición:",
            self.niveles
        )

        # =================================================
        # SUFIJO
        # =================================================

        self.sufijo_input = QLineEdit()

        self.sufijo_input.setPlaceholderText(
            "Opcional: escribe un sufijo para los archivos de salida..."
        )

        form.addRow(
            "Sufijo de guardado:",
            self.sufijo_input
        )

        # =================================================
        # BOTONES
        # =================================================

        actions = QHBoxLayout()

        self.btn_run = QPushButton(
            "▶ Ejecutar análisis"
        )

        self.btn_run.clicked.connect(
            self.ejecutar_analisis
        )

        self.btn_export = QPushButton(
            "📊 Exportar gráficos a HTML"
        )

        self.btn_export.clicked.connect(
            self.exportar_html
        )

        actions.addWidget(
            self.btn_run
        )

        actions.addWidget(
            self.btn_export
        )

        # =================================================
        # TABS
        # =================================================

        self.tabs = QTabWidget()

        # =================================================
        # TAB MAGNITUD
        # =================================================

        self.view_mag = PlotlyView()

        tab_mag = QWidget()

        lay_mag = QVBoxLayout(
            tab_mag
        )

        lay_mag.addWidget(
            self.view_mag
        )

        self.tabs.addTab(
            tab_mag,
            "Magnitud"
        )

        # =================================================
        # TAB VENTANAS
        # =================================================

        self.view_vent = PlotlyView()

        tab_vent = QWidget()

        lay_vent = QVBoxLayout(
            tab_vent
        )

        sel_row = QHBoxLayout()

        self.combo_ventana = QComboBox()

        self.combo_ventana.currentIndexChanged.connect(
            self.actualizar_plots_por_ventana
        )

        self.combo_ventana.addItem(
            "Todas"
        )

        sel_row.addWidget(
            QLabel("Mostrar ventana:")
        )

        sel_row.addWidget(
            self.combo_ventana
        )

        sel_row_w = QWidget()

        sel_row_w.setLayout(
            sel_row
        )

        lay_vent.addWidget(
            sel_row_w
        )

        lay_vent.addWidget(
            self.view_vent
        )

        self.tabs.addTab(
            tab_vent,
            "Ventanas segmentadas"
        )

        # =================================================
        # TAB COEFICIENTES WAVELET
        # =================================================

        self.view_coef = PlotlyView()

        tab_coef = QWidget()

        lay_coef = QVBoxLayout(
            tab_coef
        )

        lay_coef.addWidget(
            self.view_coef
        )

        self.tabs.addTab(
            tab_coef,
            "Coeficientes Wavelet"
        )

        # =================================================
        # TAB FFT
        # =================================================

        self.view_fft = PlotlyView()

        tab_fft = QWidget()

        lay_fft = QVBoxLayout(
            tab_fft
        )

        lay_fft.addWidget(
            self.view_fft
        )

        self.tabs.addTab(
            tab_fft,
            "FFT"
        )

        # =================================================
        # TAB VARIANZA
        # =================================================

        self.view_varianza = PlotlyView()

        tab_varianza = QWidget()

        lay_varianza = QVBoxLayout(
            tab_varianza
        )

        lay_varianza.addWidget(
            self.view_varianza
        )

        self.tabs.addTab(
            tab_varianza,
            "Varianza móvil"
        )

        # =================================================
        # LOG
        # =================================================

        self.log = QTextEdit()

        self.log.setReadOnly(
            True
        )

        self.log.setFont(
            QFont(
                "JetBrains Mono",
                10
            )
        )

        # =================================================
        # ENSAMBLE
        # =================================================

        root.addLayout(
            form
        )

        root.addLayout(
            actions
        )

        root.addWidget(
            self.tabs,
            stretch=1
        )

        root.addWidget(
            QLabel(
                "Registro de progreso:"
            )
        )

        root.addWidget(
            self.log,
            stretch=1
        )

    # =====================================================
    # UTILIDADES UI
    # =====================================================

    def append_log(
        self,
        msg: str
    ):

        self.log.append(
            msg
        )

        QApplication.processEvents()

    # =====================================================
    # SELECCIONAR CSV
    # =====================================================

    def seleccionar_csv(self):

        ruta, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar CSV",
            "",
            "CSV (*.csv)"
        )

        if ruta:

            self.csv_input.setText(
                ruta
            )

    # =====================================================
    # FFT
    # =====================================================

    def extraer_caracteristicas_fft(
        self,
        señal,
        fs,
        umbral_picos
    ):

        señal = np.asarray(
            señal,
            dtype=float
        )

        señal = señal[
            np.isfinite(señal)
        ]

        if len(señal) < 4:

            return {
                "Freq_Dominante": 0.0,
                "Amplitud_FFT_Max": 0.0,
                "Energia_FFT": 0.0,
                "Centroide_Frecuencia": 0.0,
                "Num_Picos_FFT": 0
            }, np.array([]), np.array([])

        # -------------------------------------------------
        # ELIMINAR COMPONENTE DC / MEDIA
        # -------------------------------------------------

        señal_detrend = (
            señal - np.mean(señal)
        )

        n = len(
            señal_detrend
        )

        # -------------------------------------------------
        # FFT REAL
        # -------------------------------------------------

        fft_compleja = rfft(
            señal_detrend
        )

        frecuencias = rfftfreq(
            n,
            d=1.0 / fs
        )

        # -------------------------------------------------
        # AMPLITUD NORMALIZADA
        # -------------------------------------------------

        amplitud = (
            np.abs(
                fft_compleja
            ) / n
        )

        # Convertir a espectro de un solo lado
        if n > 1:

            if n % 2 == 0:

                amplitud[1:-1] *= 2

            else:

                amplitud[1:] *= 2

        # -------------------------------------------------
        # IGNORAR 0 Hz
        # -------------------------------------------------

        amplitud_sin_dc = amplitud.copy()

        if len(amplitud_sin_dc) > 0:

            amplitud_sin_dc[0] = 0

        # -------------------------------------------------
        # FRECUENCIA DOMINANTE
        # -------------------------------------------------

        indice_dominante = int(
            np.argmax(
                amplitud_sin_dc
            )
        )

        freq_dominante = float(
            frecuencias[
                indice_dominante
            ]
        )

        # -------------------------------------------------
        # AMPLITUD MAXIMA FFT
        # -------------------------------------------------

        amplitud_fft_max = float(
            amplitud_sin_dc[
                indice_dominante
            ]
        )

        # -------------------------------------------------
        # ENERGIA ESPECTRAL FFT
        # -------------------------------------------------

        energia_fft = float(
            np.sum(
                amplitud_sin_dc ** 2
            )
        )

        # -------------------------------------------------
        # CENTROIDE DE FRECUENCIA
        # -------------------------------------------------

        suma_amplitudes = float(
            np.sum(
                amplitud_sin_dc
            )
        )

        if suma_amplitudes > 0:

            centroide_frecuencia = float(
                np.sum(
                    frecuencias *
                    amplitud_sin_dc
                )
                / suma_amplitudes
            )

        else:

            centroide_frecuencia = 0.0

        # -------------------------------------------------
        # NUMERO DE PICOS
        # -------------------------------------------------

        max_fft = float(
            np.max(
                amplitud_sin_dc
            )
        )

        if max_fft > 0:

            altura_minima = (
                max_fft *
                umbral_picos
            )

            # Separación mínima aproximada
            # para evitar contar el mismo pico repetido
            distancia_minima = max(
                1,
                int(
                    fs / 20
                )
            )

            peaks, _ = find_peaks(
                amplitud_sin_dc,
                height=altura_minima,
                distance=distancia_minima
            )

            num_picos_fft = int(
                len(peaks)
            )

        else:

            peaks = np.array(
                [],
                dtype=int
            )

            num_picos_fft = 0

        # -------------------------------------------------
        # DICCIONARIO DE CARACTERÍSTICAS
        # -------------------------------------------------

        caract_fft = {

            "Freq_Dominante":
                freq_dominante,

            "Amplitud_FFT_Max":
                amplitud_fft_max,

            "Energia_FFT":
                energia_fft,

            "Centroide_Frecuencia":
                centroide_frecuencia,

            "Num_Picos_FFT":
                num_picos_fft
        }

        return (
            caract_fft,
            frecuencias,
            amplitud
        )

    # =====================================================
    # VARIANZA MOVIL
    # =====================================================

    def extraer_caracteristicas_varianza(
        self,
        señal,
        fs,
        ventana_seg
    ):

        señal = np.asarray(
            señal,
            dtype=float
        )

        señal = señal[
            np.isfinite(señal)
        ]

        if len(señal) < 2:

            return {
                "Varianza_Media": 0.0,
                "Varianza_Max": 0.0,
                "Varianza_STD": 0.0
            }, np.zeros(
                len(señal)
            )

        # -------------------------------------------------
        # CONVERTIR SEGUNDOS A MUESTRAS
        # -------------------------------------------------

        ventana_muestras = max(
            2,
            int(
                round(
                    ventana_seg * fs
                )
            )
        )

        # No permitir ventana mayor que la señal
        ventana_muestras = min(
            ventana_muestras,
            len(señal)
        )

        serie = pd.Series(
            señal
        )

        varianza_movil = serie.rolling(
            window=ventana_muestras,
            center=True,
            min_periods=2
        ).var()

        # Rellenar valores extremos
        varianza_movil = (
            varianza_movil
            .bfill()
            .ffill()
            .fillna(0)
        )

        valores_varianza = (
            varianza_movil
            .to_numpy(
                dtype=float
            )
        )

        # -------------------------------------------------
        # CARACTERISTICAS
        # -------------------------------------------------

        varianza_media = float(
            np.mean(
                valores_varianza
            )
        )

        varianza_max = float(
            np.max(
                valores_varianza
            )
        )

        varianza_std = float(
            np.std(
                valores_varianza
            )
        )

        caract_varianza = {

            "Varianza_Media":
                varianza_media,

            "Varianza_Max":
                varianza_max,

            "Varianza_STD":
                varianza_std
        }

        return (
            caract_varianza,
            valores_varianza
        )

    # =====================================================
    # PIPELINE PRINCIPAL
    # =====================================================

    def ejecutar_analisis(self):

        try:

            # -------------------------------------------------
            # RUTA
            # -------------------------------------------------

            ruta = (
                self.csv_input.text().strip()
            )

            if not ruta:

                QMessageBox.warning(
                    self,
                    "CSV requerido",
                    "Selecciona un archivo CSV de entrada."
                )

                return

            # -------------------------------------------------
            # SUFIJO
            # -------------------------------------------------

            sufijo_manual = (
                self.sufijo_input.text().strip()
            )

            if sufijo_manual:

                sufijo = sufijo_manual

            else:

                sufijo = (
                    datetime.datetime.now().strftime(
                        "%Y%m%d_%H%M%S"
                    )
                )

            # -------------------------------------------------
            # PARAMETROS
            # -------------------------------------------------

            ventana_seg = float(
                self.ventana_seg.value()
            )

            fs = int(
                self.frecuencia_muestreo.value()
            )

            ventana_varianza_seg = float(
                self.ventana_varianza.value()
            )

            umbral_picos = float(
                self.umbral_picos_fft.value()
            )

            porcentaje_estado = float(
                self.porcentaje_estado.value()
            )

            traslape_pct = int(
                self.traslape_pct.value()
            )

            tipo_wavelet = (
                self.tipo_wavelet.currentText()
            )

            niveles = int(
                self.niveles.value()
            )

            # -------------------------------------------------
            # INFORMACION
            # -------------------------------------------------

            muestras_ventana = int(
                round(
                    ventana_seg * fs
                )
            )

            muestras_varianza = int(
                round(
                    ventana_varianza_seg * fs
                )
            )

            self.append_log(
                "=============================================="
            )

            self.append_log(
                "INICIO DEL ANALISIS"
            )

            self.append_log(
                "=============================================="
            )

            self.append_log(
                f"Frecuencia de muestreo: {fs} Hz"
            )

            self.append_log(
                f"Ventana: {ventana_seg:.2f} s "
                f"({muestras_ventana} muestras)"
            )

            self.append_log(
                f"Ventana varianza móvil: "
                f"{ventana_varianza_seg:.2f} s "
                f"({muestras_varianza} muestras)"
            )

            self.append_log(
                f"Umbral picos FFT: "
                f"{umbral_picos * 100:.1f}%"
            )

            # -------------------------------------------------
            # LEER CSV
            # -------------------------------------------------

            self.append_log(
                "Leyendo CSV de entrada..."
            )

            df = leer_csv(
                ruta
            )

            # -------------------------------------------------
            # VELOCIDAD
            # -------------------------------------------------

            if "Velocidad" not in df.columns:

                df["Velocidad"] = 0

                self.append_log(
                    "Columna 'Velocidad' no encontrada. "
                    "Se generó con valor 0."
                )

            # -------------------------------------------------
            # COLUMNAS REQUERIDAS
            # -------------------------------------------------

            columnas_requeridas = [
                "Timestamp",
                "AccelX",
                "AccelY",
                "AccelZ",
                "Estado",
                "Velocidad"
            ]

            columnas_faltantes = [
                columna
                for columna in columnas_requeridas
                if columna not in df.columns
            ]

            if columnas_faltantes:

                raise ValueError(
                    "Faltan las siguientes columnas en el CSV: "
                    + ", ".join(
                        columnas_faltantes
                    )
                )

            # -------------------------------------------------
            # CONVERTIR ACELEROMETRO A NUMERICO
            # -------------------------------------------------

            self.append_log(
                "🔹 Preparando acelerómetro..."
            )

            for columna in [
                "AccelX",
                "AccelY",
                "AccelZ"
            ]:

                df[columna] = pd.to_numeric(
                    df[columna],
                    errors="coerce"
                )

            # -------------------------------------------------
            # ELIMINAR FILAS INVALIDAS
            # -------------------------------------------------

            filas_antes = len(
                df
            )

            df = df.dropna(
                subset=[
                    "AccelX",
                    "AccelY",
                    "AccelZ"
                ]
            ).copy()

            filas_despues = len(
                df
            )

            if filas_antes != filas_despues:

                self.append_log(
                    f"Se eliminaron "
                    f"{filas_antes - filas_despues} "
                    f"filas con acelerómetro inválido."
                )

            # -------------------------------------------------
            # PREPARAR VELOCIDAD
            # -------------------------------------------------

            self.append_log(
                "🔹 Preparando columna Velocidad..."
            )

            df["Velocidad"] = pd.to_numeric(
                df["Velocidad"],
                errors="coerce"
            ).fillna(0)

            # -------------------------------------------------
            # CALCULAR MAGNITUD
            # -------------------------------------------------

            self.append_log(
                "🔹 Calculando magnitud..."
            )

            magnitud = calcular_magnitud(
                df["AccelX"],
                df["AccelY"],
                df["AccelZ"]
            )

            self.df_magnitud = pd.DataFrame(
                {
                    "Timestamp": pd.to_datetime(
                        df["Timestamp"],
                        errors="coerce"
                    ),

                    "AccelX": df["AccelX"].to_numpy(),

                    "AccelY": df["AccelY"].to_numpy(),

                    "AccelZ": df["AccelZ"].to_numpy(),

                    "Magnitud": magnitud,

                    "Velocidad": df["Velocidad"].to_numpy(),

                    "Estado": df["Estado"].to_numpy()
                }
            )

            # -------------------------------------------------
            # CREAR CARPETA SALIDA
            # -------------------------------------------------

            os.makedirs(
                "salida",
                exist_ok=True
            )

            # -------------------------------------------------
            # RUTAS DE SALIDA
            # -------------------------------------------------

            magnitud_file = (
                f"salida/magnitud_acel_{sufijo}.csv"
            )

            ventanas_file = (
                f"salida/ventanas_segmentadas_{sufijo}.csv"
            )

            caract_file = (
                f"salida/caracteristicas_completas_{sufijo}.csv"
            )

            coef_file = (
                f"salida/coeficientes_wavelet_{sufijo}.csv"
            )

            fft_file = (
                f"salida/fft_por_ventana_{sufijo}.csv"
            )

            varianza_file = (
                f"salida/varianza_movil_{sufijo}.csv"
            )

            # -------------------------------------------------
            # GUARDAR MAGNITUD
            # -------------------------------------------------

            guardar_csv(
                self.df_magnitud,
                magnitud_file
            )

            self.append_log(
                f"Magnitud guardada en: "
                f"{magnitud_file}"
            )

            # -------------------------------------------------
            # GRAFICAR MAGNITUD
            # -------------------------------------------------

            self.render_magnitud(
                self.df_magnitud
            )

            # -------------------------------------------------
            # SEGMENTAR
            # -------------------------------------------------

            self.append_log(
                "🔹 Segmentando señal..."
            )

            self.ventanas_segmentadas = (
                segmentar_traslape_csv(
                    magnitud_file,
                    ventana_seg,
                    traslape_pct,
                    porcentaje_estado
                )
            )

            if self.ventanas_segmentadas.empty:

                guardar_csv(
                    self.ventanas_segmentadas,
                    ventanas_file
                )

                QMessageBox.warning(
                    self,
                    "Sin ventanas",
                    "No se generaron ventanas que cumplan "
                    "el porcentaje mínimo del estado."
                )

                self.append_log(
                    "No se generaron ventanas válidas."
                )

                return

            guardar_csv(
                self.ventanas_segmentadas,
                ventanas_file
            )

            self.append_log(
                "Ventanas segmentadas guardadas en: "
                f"{ventanas_file}"
            )

            # -------------------------------------------------
            # COMBO DE VENTANAS
            # -------------------------------------------------

            self.combo_ventana.blockSignals(
                True
            )

            self.combo_ventana.clear()

            self.combo_ventana.addItem(
                "Todas"
            )

            for vid in (
                self.ventanas_segmentadas[
                    "ID_Ventana"
                ]
                .unique()
                .tolist()
            ):

                self.combo_ventana.addItem(
                    str(vid)
                )

            self.combo_ventana.blockSignals(
                False
            )

            self.render_ventanas(
                self.ventanas_segmentadas,
                selected=None
            )

            # =================================================
            # EXTRAER CARACTERISTICAS
            # =================================================

            self.append_log(
                "🔹 Extrayendo Wavelet + FFT + Varianza..."
            )

            caract_list = []

            coef_flat = []

            fft_rows = []

            varianza_rows = []

            self.coef_por_ventana = {}

            self.fft_por_ventana = {}

            self.varianza_por_ventana = {}

            # -------------------------------------------------
            # RECORRER VENTANAS
            # -------------------------------------------------

            for vid, grupo in (
                self.ventanas_segmentadas.groupby(
                    "ID_Ventana"
                )
            ):

                # =============================================
                # SEÑAL MAGNITUD
                # =============================================

                ventana_total = (
                    pd.to_numeric(
                        grupo["Magnitud"],
                        errors="coerce"
                    )
                    .dropna()
                    .to_numpy(
                        dtype=float
                    )
                )

                if len(
                    ventana_total
                ) < 4:

                    self.append_log(
                        f"Ventana {vid} ignorada: "
                        f"muy pocas muestras."
                    )

                    continue

                # =============================================
                # WAVELET
                # =============================================

                caract, coef_puros = (
                    extraer_caracteristicas_wavelet(
                        ventana_total,
                        tipo_wavelet,
                        niveles
                    )
                )

                if caract is None:

                    self.append_log(
                        f"Ventana {vid} ignorada "
                        f"por Wavelet."
                    )

                    continue

                # =============================================
                # ESTADO MAYORITARIO
                # =============================================

                estado_mayoritario = (
                    grupo[
                        "Estado_Ventana"
                    ]
                    .iloc[0]
                )

                # =============================================
                # VELOCIDAD
                # =============================================

                velocidad_ventana = pd.to_numeric(
                    grupo["Velocidad"],
                    errors="coerce"
                )

                velocidad_prom = float(
                    velocidad_ventana.mean()
                )

                velocidad_min = float(
                    velocidad_ventana.min()
                )

                velocidad_max = float(
                    velocidad_ventana.max()
                )

                # =============================================
                # ENERGIA TEMPORAL
                # =============================================
                #
                # E = SUMA(Magnitud^2)
                #
                # Se conserva tu característica actual.
                # =============================================

                energia = float(
                    np.sum(
                        ventana_total ** 2
                    )
                )

                # =============================================
                # FFT
                # =============================================

                (
                    caract_fft,
                    frecuencias,
                    amplitud_fft
                ) = self.extraer_caracteristicas_fft(
                    ventana_total,
                    fs,
                    umbral_picos
                )

                # =============================================
                # VARIANZA MOVIL
                # =============================================

                (
                    caract_varianza,
                    varianza_movil
                ) = self.extraer_caracteristicas_varianza(
                    ventana_total,
                    fs,
                    ventana_varianza_seg
                )

                # =============================================
                # FILA COMPLETA
                # =============================================

                caract_row = {

                    "ID_Ventana":
                        vid,

                    "Estado":
                        estado_mayoritario,

                    # -----------------------------
                    # WAVELET
                    # -----------------------------

                    **caract,

                    # -----------------------------
                    # VELOCIDAD
                    # -----------------------------

                    "Velocidad_prom":
                        velocidad_prom,

                    "Velocidad_min":
                        velocidad_min,

                    "Velocidad_max":
                        velocidad_max,

                    # -----------------------------
                    # ENERGIA TEMPORAL
                    # -----------------------------

                    "Energia":
                        energia,

                    # -----------------------------
                    # FFT
                    # -----------------------------

                    **caract_fft,

                    # -----------------------------
                    # VARIANZA
                    # -----------------------------

                    **caract_varianza
                }

                caract_list.append(
                    caract_row
                )

                # =============================================
                # GUARDAR COEFICIENTES WAVELET
                # =============================================

                self.coef_por_ventana[
                    int(vid)
                ] = coef_puros

                # =============================================
                # GUARDAR FFT PARA GRAFICA
                # =============================================

                self.fft_por_ventana[
                    int(vid)
                ] = (
                    frecuencias,
                    amplitud_fft
                )

                # =============================================
                # GUARDAR VARIANZA PARA GRAFICA
                # =============================================

                self.varianza_por_ventana[
                    int(vid)
                ] = (
                    varianza_movil
                )

                # =============================================
                # FILA FFT
                # =============================================

                fft_rows.append(
                    {
                        "ID_Ventana":
                            vid,

                        "Estado":
                            estado_mayoritario,

                        **caract_fft
                    }
                )

                # =============================================
                # FILA VARIANZA
                # =============================================

                varianza_rows.append(
                    {
                        "ID_Ventana":
                            vid,

                        "Estado":
                            estado_mayoritario,

                        **caract_varianza
                    }
                )

            # =================================================
            # DATAFRAME FINAL
            # =================================================

            df_caract = pd.DataFrame(
                caract_list
            )

            if df_caract.empty:

                raise ValueError(
                    "No fue posible extraer "
                    "características de ninguna ventana."
                )

            # =================================================
            # ORDENAR COLUMNAS
            # =================================================

            columnas_inicio = [
                "ID_Ventana",
                "Estado"
            ]

            columnas_wavelet = [
                columna
                for columna in [
                    "A3_prom",
                    "A3_desv",
                    "D1_prom",
                    "D1_desv",
                    "D2_prom",
                    "D2_desv",
                    "D3_prom",
                    "D3_desv"
                ]
                if columna in df_caract.columns
            ]

            columnas_velocidad = [
                "Velocidad_prom",
                "Velocidad_min",
                "Velocidad_max"
            ]

            columnas_energia = [
                "Energia"
            ]

            columnas_fft = [
                "Freq_Dominante",
                "Amplitud_FFT_Max",
                "Energia_FFT",
                "Centroide_Frecuencia",
                "Num_Picos_FFT"
            ]

            columnas_varianza = [
                "Varianza_Media",
                "Varianza_Max",
                "Varianza_STD"
            ]

            columnas_finales = (
                columnas_inicio
                + columnas_wavelet
                + columnas_velocidad
                + columnas_energia
                + columnas_fft
                + columnas_varianza
            )

            # Agregar cualquier característica Wavelet
            # que pudiera variar por cantidad de niveles.
            columnas_restantes = [
                c
                for c in df_caract.columns
                if c not in columnas_finales
            ]

            columnas_finales += (
                columnas_restantes
            )

            df_caract = df_caract[
                columnas_finales
            ]

            # =================================================
            # GUARDAR CSV COMPLETO
            # =================================================

            guardar_csv(
                df_caract,
                caract_file
            )

            self.append_log(
                f"✅ CSV completo guardado en: "
                f"{caract_file}"
            )

            # =================================================
            # GUARDAR FFT
            # =================================================

            df_fft = pd.DataFrame(
                fft_rows
            )

            guardar_csv(
                df_fft,
                fft_file
            )

            self.append_log(
                f"✅ Características FFT guardadas en: "
                f"{fft_file}"
            )

            # =================================================
            # GUARDAR VARIANZA
            # =================================================

            df_varianza = pd.DataFrame(
                varianza_rows
            )

            guardar_csv(
                df_varianza,
                varianza_file
            )

            self.append_log(
                f"✅ Características de varianza guardadas en: "
                f"{varianza_file}"
            )

            # =================================================
            # MOSTRAR LOG DE CARACTERISTICAS
            # =================================================

            self.append_log(
                "=============================================="
            )

            self.append_log(
                "CARACTERISTICAS GENERADAS"
            )

            self.append_log(
                "=============================================="
            )

            for columna in columnas_wavelet:

                self.append_log(
                    f"• {columna}"
                )

            for columna in columnas_velocidad:

                self.append_log(
                    f"• {columna}"
                )

            self.append_log(
                "• Energia"
            )

            self.append_log(
                "• Freq_Dominante"
            )

            self.append_log(
                "• Amplitud_FFT_Max"
            )

            self.append_log(
                "• Energia_FFT"
            )

            self.append_log(
                "• Centroide_Frecuencia"
            )

            self.append_log(
                "• Num_Picos_FFT"
            )

            self.append_log(
                "• Varianza_Media"
            )

            self.append_log(
                "• Varianza_Max"
            )

            self.append_log(
                "• Varianza_STD"
            )

            self.append_log(
                f"Total de características: "
                f"{len(columnas_finales) - 2}"
            )

            # =================================================
            # COEFICIENTES WAVELET PLANOS
            # =================================================

            for vid, coefs in (
                self.coef_por_ventana.items()
            ):

                row = {
                    "ID_Ventana":
                        vid
                }

                for i, c in enumerate(
                    coefs
                ):

                    if i == 0:

                        row[
                            f"A{niveles}_coefs"
                        ] = ",".join(
                            map(
                                str,
                                c
                            )
                        )

                    else:

                        row[
                            f"D{i}_coefs"
                        ] = ",".join(
                            map(
                                str,
                                c
                            )
                        )

                coef_flat.append(
                    row
                )

            guardar_csv(
                pd.DataFrame(
                    coef_flat
                ),
                coef_file
            )

            self.append_log(
                f"✅ Coeficientes Wavelet guardados en: "
                f"{coef_file}"
            )

            # =================================================
            # GUARDAR RUTAS
            # =================================================

            self.last_output_paths = {

                "magnitud":
                    magnitud_file,

                "ventanas":
                    ventanas_file,

                "caracteristicas":
                    caract_file,

                "coeficientes":
                    coef_file,

                "fft":
                    fft_file,

                "varianza":
                    varianza_file,

                "sufijo":
                    sufijo
            }

            # =================================================
            # GRAFICOS
            # =================================================

            primera_ventana = (
                list(
                    self.coef_por_ventana.keys()
                )[0]
            )

            self.render_coeficientes(
                int(
                    primera_ventana
                )
            )

            self.render_fft(
                int(
                    primera_ventana
                )
            )

            self.render_varianza(
                int(
                    primera_ventana
                )
            )

            # =================================================
            # RESUMEN
            # =================================================

            self.append_log(
                "=============================================="
            )

            self.append_log(
                "✅ ANALISIS COMPLETADO"
            )

            self.append_log(
                "=============================================="
            )

            self.append_log(
                f"Ventanas analizadas: "
                f"{len(df_caract)}"
            )

            self.append_log(
                f"Caracteristicas por ventana: "
                f"{len(columnas_finales) - 2}"
            )

            self.append_log(
                f"Frecuencia FFT: {fs} Hz"
            )

            self.append_log(
                f"Ventana FFT: {ventana_seg:.2f} s"
            )

            self.append_log(
                f"Muestras por ventana esperadas: "
                f"{muestras_ventana}"
            )

            self.append_log(
                "=============================================="
            )

        except Exception as e:

            self.append_log(
                f"❌ Error: {e}"
            )

            QMessageBox.critical(
                self,
                "Error",
                str(e)
            )

    # =====================================================
    # RENDER MAGNITUD
    # =====================================================

    def render_magnitud(
        self,
        df_mag: pd.DataFrame
    ):

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=df_mag["Timestamp"],
                y=df_mag["Magnitud"],
                mode="lines",
                name="Magnitud",
                hovertemplate=(
                    "Tiempo: %{x}"
                    "<br>Magnitud: %{y:.4f}"
                    "<extra></extra>"
                )
            )
        )

        fig.update_layout(
            title="Magnitud del Acelerómetro",
            xaxis_title="Tiempo",
            yaxis_title="Magnitud",
            template="plotly_dark",
            margin=dict(
                l=40,
                r=20,
                t=60,
                b=40
            ),
            hovermode="x unified"
        )

        self.view_mag.set_figure(
            fig
        )

    # =====================================================
    # RENDER VENTANAS
    # =====================================================

    def render_ventanas(
        self,
        df_seg: pd.DataFrame,
        selected: int | None
    ):

        fig = go.Figure()

        for vid, grupo in (
            df_seg.groupby(
                "ID_Ventana"
            )
        ):

            fig.add_trace(
                go.Scatter(
                    x=np.arange(
                        len(grupo)
                    ),

                    y=grupo[
                        "Magnitud"
                    ],

                    mode="lines",

                    name=f"Ventana {vid}",

                    line=dict(
                        width=(
                            2
                            if (
                                selected is not None
                                and int(vid) == selected
                            )
                            else 1
                        )
                    ),

                    opacity=(
                        1.0
                        if (
                            selected is None
                            or int(vid) == selected
                        )
                        else 0.25
                    ),

                    hovertemplate=(
                        "Muestra: %{x}"
                        "<br>Magnitud: %{y:.4f}"
                        "<br>Ventana: "
                        + str(vid)
                        + "<extra></extra>"
                    )
                )
            )

        fig.update_layout(
            title="Ventanas segmentadas",
            xaxis_title="Índice de muestra",
            yaxis_title="Magnitud",
            template="plotly_dark",
            margin=dict(
                l=40,
                r=20,
                t=60,
                b=40
            )
        )

        self.view_vent.set_figure(
            fig
        )

    # =====================================================
    # RENDER WAVELET
    # =====================================================

    def render_coeficientes(
        self,
        vid: int
    ):

        coefs = self.coef_por_ventana.get(
            int(vid)
        )

        if coefs is None:

            self.view_coef.set_figure(
                go.Figure()
            )

            return

        niveles = len(
            coefs
        ) - 1

        fig = go.Figure()

        for i, c in enumerate(
            coefs
        ):

            if i == 0:

                fig.add_trace(
                    go.Scatter(
                        y=c,
                        mode="lines",
                        name=(
                            f"Aproximación "
                            f"A{niveles}"
                        ),

                        hovertemplate=(
                            "Índice: %{x}"
                            "<br>A: %{y:.4f}"
                            "<extra></extra>"
                        )
                    )
                )

            else:

                fig.add_trace(
                    go.Scatter(
                        y=c,
                        mode="lines",
                        name=f"Detalle D{i}",

                        line=dict(
                            dash="dash"
                        ),

                        hovertemplate=(
                            "Índice: %{x}"
                            "<br>D"
                            + str(i)
                            + ": %{y:.4f}"
                            "<extra></extra>"
                        )
                    )
                )

        fig.update_layout(
            title=(
                f"Coeficientes Wavelet - "
                f"Ventana {vid}"
            ),

            xaxis_title=(
                "Índice del coeficiente"
            ),

            yaxis_title="Valor",

            template="plotly_dark",

            margin=dict(
                l=40,
                r=20,
                t=60,
                b=40
            )
        )

        self.view_coef.set_figure(
            fig
        )

    # =====================================================
    # RENDER FFT
    # =====================================================

    def render_fft(
        self,
        vid: int
    ):

        datos = (
            self.fft_por_ventana.get(
                int(vid)
            )
        )

        if datos is None:

            self.view_fft.set_figure(
                go.Figure()
            )

            return

        frecuencias, amplitud = datos

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=frecuencias,
                y=amplitud,
                mode="lines",

                name="Espectro FFT",

                hovertemplate=(
                    "Frecuencia: %{x:.3f} Hz"
                    "<br>Amplitud: %{y:.6f}"
                    "<extra></extra>"
                )
            )
        )

        fig.update_layout(
            title=(
                f"FFT - Ventana {vid}"
            ),

            xaxis_title=(
                "Frecuencia (Hz)"
            ),

            yaxis_title=(
                "Amplitud"
            ),

            template="plotly_dark",

            margin=dict(
                l=40,
                r=20,
                t=60,
                b=40
            )
        )

        self.view_fft.set_figure(
            fig
        )

    # =====================================================
    # RENDER VARIANZA
    # =====================================================

    def render_varianza(
        self,
        vid: int
    ):

        varianza = (
            self.varianza_por_ventana.get(
                int(vid)
            )
        )

        if varianza is None:

            self.view_varianza.set_figure(
                go.Figure()
            )

            return

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=np.arange(
                    len(varianza)
                ),

                y=varianza,

                mode="lines",

                name="Varianza móvil",

                hovertemplate=(
                    "Muestra: %{x}"
                    "<br>Varianza: %{y:.6f}"
                    "<extra></extra>"
                )
            )
        )

        fig.update_layout(
            title=(
                f"Varianza móvil - "
                f"Ventana {vid}"
            ),

            xaxis_title=(
                "Índice de muestra"
            ),

            yaxis_title=(
                "Varianza"
            ),

            template="plotly_dark",

            margin=dict(
                l=40,
                r=20,
                t=60,
                b=40
            )
        )

        self.view_varianza.set_figure(
            fig
        )

    # =====================================================
    # CALLBACK DE VENTANA
    # =====================================================

    def actualizar_plots_por_ventana(
        self
    ):

        if self.ventanas_segmentadas is None:

            return

        texto = (
            self.combo_ventana.currentText()
        )

        selected = (
            None
            if (
                texto == "Todas"
                or texto == ""
            )
            else int(texto)
        )

        self.render_ventanas(
            self.ventanas_segmentadas,
            selected
        )

        if selected is not None:

            self.render_coeficientes(
                selected
            )

            self.render_fft(
                selected
            )

            self.render_varianza(
                selected
            )

    # =====================================================
    # EXPORTAR HTML
    # =====================================================

    def exportar_html(
        self
    ):

        try:

            if not self.last_output_paths:

                QMessageBox.information(
                    self,
                    "Nada que exportar",
                    "Primero ejecuta el análisis."
                )

                return

            os.makedirs(
                "salida",
                exist_ok=True
            )

            ruta_mag = (
                self.last_output_paths.get(
                    "magnitud"
                )
            )

            ruta_vent = (
                self.last_output_paths.get(
                    "ventanas"
                )
            )

            ruta_coef = (
                self.last_output_paths.get(
                    "coeficientes"
                )
            )

            ruta_fft = (
                self.last_output_paths.get(
                    "fft"
                )
            )

            ruta_varianza = (
                self.last_output_paths.get(
                    "varianza"
                )
            )

            # =================================================
            # HTML MAGNITUD
            # =================================================

            df_mag = pd.read_csv(
                ruta_mag
            )

            fig_mag = go.Figure()

            fig_mag.add_trace(
                go.Scatter(
                    x=df_mag[
                        "Timestamp"
                    ],

                    y=df_mag[
                        "Magnitud"
                    ],

                    mode="lines",

                    name="Magnitud"
                )
            )

            fig_mag.update_layout(
                title=(
                    "Magnitud del Acelerómetro"
                ),

                template="plotly_dark"
            )

            with open(
                ruta_mag.replace(
                    ".csv",
                    ".html"
                ),

                "w",

                encoding="utf-8"
            ) as f:

                f.write(
                    pio.to_html(
                        fig_mag,
                        full_html=True,
                        include_plotlyjs="cdn"
                    )
                )

            # =================================================
            # HTML VENTANAS
            # =================================================

            df_vent = pd.read_csv(
                ruta_vent
            )

            fig_v = go.Figure()

            for vid, grupo in (
                df_vent.groupby(
                    "ID_Ventana"
                )
            ):

                fig_v.add_trace(
                    go.Scatter(
                        x=np.arange(
                            len(grupo)
                        ),

                        y=grupo[
                            "Magnitud"
                        ],

                        mode="lines",

                        name=f"Ventana {vid}"
                    )
                )

            fig_v.update_layout(
                title=(
                    "Ventanas segmentadas"
                ),

                template="plotly_dark"
            )

            with open(
                ruta_vent.replace(
                    ".csv",
                    ".html"
                ),

                "w",

                encoding="utf-8"
            ) as f:

                f.write(
                    pio.to_html(
                        fig_v,
                        full_html=True,
                        include_plotlyjs="cdn"
                    )
                )

            # =================================================
            # HTML WAVELET
            # =================================================

            df_coef = pd.read_csv(
                ruta_coef
            )

            if not df_coef.empty:

                row = (
                    df_coef.iloc[0]
                )

                fig_c = go.Figure()

                for col in df_coef.columns:

                    if col.endswith(
                        "_coefs"
                    ):

                        texto = str(
                            row[col]
                        )

                        valores = list(
                            map(
                                float,
                                texto.split(",")
                            )
                        )

                        fig_c.add_trace(
                            go.Scatter(
                                y=valores,

                                mode="lines",

                                name=col
                            )
                        )

                fig_c.update_layout(
                    title=(
                        "Coeficientes Wavelet"
                    ),

                    template="plotly_dark"
                )

                with open(
                    ruta_coef.replace(
                        ".csv",
                        ".html"
                    ),

                    "w",

                    encoding="utf-8"
                ) as f:

                    f.write(
                        pio.to_html(
                            fig_c,
                            full_html=True,
                            include_plotlyjs="cdn"
                        )
                    )

            # =================================================
            # HTML FFT
            # =================================================

            if (
                ruta_fft
                and os.path.exists(
                    ruta_fft
                )
            ):

                df_fft = pd.read_csv(
                    ruta_fft
                )

                fig_fft = go.Figure()

                # Como el CSV contiene características,
                # se genera un gráfico resumen por ventana.
                fig_fft.add_trace(
                    go.Scatter(
                        x=df_fft[
                            "ID_Ventana"
                        ],

                        y=df_fft[
                            "Freq_Dominante"
                        ],

                        mode="lines+markers",

                        name="Frecuencia dominante",

                        hovertemplate=(
                            "Ventana: %{x}"
                            "<br>Freq dominante: %{y:.3f} Hz"
                            "<extra></extra>"
                        )
                    )
                )

                fig_fft.update_layout(
                    title=(
                        "Frecuencia dominante por ventana"
                    ),

                    xaxis_title=(
                        "Ventana"
                    ),

                    yaxis_title=(
                        "Frecuencia dominante (Hz)"
                    ),

                    template="plotly_dark"
                )

                with open(
                    ruta_fft.replace(
                        ".csv",
                        ".html"
                    ),

                    "w",

                    encoding="utf-8"
                ) as f:

                    f.write(
                        pio.to_html(
                            fig_fft,
                            full_html=True,
                            include_plotlyjs="cdn"
                        )
                    )

            # =================================================
            # HTML VARIANZA
            # =================================================

            if (
                ruta_varianza
                and os.path.exists(
                    ruta_varianza
                )
            ):

                df_var = pd.read_csv(
                    ruta_varianza
                )

                fig_var = go.Figure()

                fig_var.add_trace(
                    go.Scatter(
                        x=df_var[
                            "ID_Ventana"
                        ],

                        y=df_var[
                            "Varianza_Max"
                        ],

                        mode="lines+markers",

                        name="Varianza máxima",

                        hovertemplate=(
                            "Ventana: %{x}"
                            "<br>Varianza máxima: %{y:.6f}"
                            "<extra></extra>"
                        )
                    )
                )

                fig_var.update_layout(
                    title=(
                        "Varianza máxima por ventana"
                    ),

                    xaxis_title=(
                        "Ventana"
                    ),

                    yaxis_title=(
                        "Varianza máxima"
                    ),

                    template="plotly_dark"
                )

                with open(
                    ruta_varianza.replace(
                        ".csv",
                        ".html"
                    ),

                    "w",

                    encoding="utf-8"
                ) as f:

                    f.write(
                        pio.to_html(
                            fig_var,
                            full_html=True,
                            include_plotlyjs="cdn"
                        )
                    )

            # =================================================
            # MENSAJE FINAL
            # =================================================

            QMessageBox.information(
                self,

                "Exportación lista",

                "Se exportaron los HTML "
                "en la carpeta 'salida/'."
            )

        except Exception as e:

            QMessageBox.critical(
                self,

                "Error al exportar",

                str(e)
            )


# =====================================================
# EJECUCIÓN
# =====================================================

if __name__ == "__main__":

    app = QApplication(
        sys.argv
    )

    w = AnalisisWaveletApp()

    w.show()

    sys.exit(
        app.exec()
    )