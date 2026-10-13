import sys
import os
import numpy as np
import pandas as pd
import datetime

from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QFileDialog,
    QVBoxLayout, QFormLayout, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox,
    QTabWidget, QHBoxLayout, QMessageBox
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

    def set_figure(self, fig: go.Figure):

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
            "📊 Análisis TWD - (Transformada Wavelet) PyQt6 + Plotly"
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

        self.ventana_seg.setValue(
            1.0
        )

        self.ventana_seg.setSingleStep(
            0.1
        )

        form.addRow(
            "Tamaño de ventana (s):",
            self.ventana_seg
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
            "Ejecutar análisis"
        )

        self.btn_run.clicked.connect(
            self.ejecutar_analisis
        )

        self.btn_export = QPushButton(
            "Exportar gráficos a HTML"
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
        # TAB COEFICIENTES
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
            "Coeficientes Wavelet (hover)"
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
            # PARÁMETROS
            # -------------------------------------------------

            ventana_seg = float(
                self.ventana_seg.value()
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
            # LEER CSV
            # -------------------------------------------------

            self.append_log(
                "Leyendo CSV de entrada…"
            )

            df = leer_csv(
                ruta
            )
            if "Velocidad" not in df.columns:
                df["Velocidad"] = 0
                self.append_log("Columna 'Velocidad' no encontrada. Se generó con valor 0.")

            # -------------------------------------------------
            # VERIFICAR COLUMNAS
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
            # PREPARAR VELOCIDAD
            # -------------------------------------------------

            self.append_log(
                "🔹 Preparando columna Velocidad…"
            )
            df["Velocidad"] = pd.to_numeric(
                df["Velocidad"],
                errors="coerce"
            ).fillna(0)

            df["Velocidad"] = pd.to_numeric(
                df["Velocidad"],
                errors="coerce"
            )

            # -------------------------------------------------
            # CALCULAR MAGNITUD
            # -------------------------------------------------

            self.append_log(
                "🔹 Calculando magnitud…"
            )

            magnitud = calcular_magnitud(
                df["AccelX"],
                df["AccelY"],
                df["AccelZ"]
            )

            self.df_magnitud = pd.DataFrame(
                {
                    "Timestamp": pd.to_datetime(
                        df["Timestamp"]
                    ),
                    "Magnitud": magnitud,
                    "Velocidad": df["Velocidad"],
                    "Estado": df["Estado"],
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
                f"salida/caracteristicas_wavelet_{sufijo}.csv"
            )

            coef_file = (
                f"salida/coeficientes_wavelet_{sufijo}.csv"
            )

            # -------------------------------------------------
            # GUARDAR MAGNITUD
            # -------------------------------------------------

            guardar_csv(
                self.df_magnitud,
                magnitud_file
            )

            self.append_log(
                f"Magnitud guardada en {magnitud_file}"
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
                "Segmentando señal…"
            )

            self.ventanas_segmentadas = (
                segmentar_traslape_csv(
                    magnitud_file,
                    ventana_seg,
                    traslape_pct,
                    porcentaje_estado
                )
            )

            guardar_csv(
                self.ventanas_segmentadas,
                ventanas_file
            )

            self.append_log(
                "Ventanas segmentadas guardadas en "
                f"{ventanas_file}"
            )

            # -------------------------------------------------
            # VALIDAR VENTANAS
            # -------------------------------------------------

            if self.ventanas_segmentadas.empty:

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

            # -------------------------------------------------
            # EXTRAER CARACTERÍSTICAS
            # -------------------------------------------------

            self.append_log(
                "Extrayendo características, "
                "velocidad y energía…"
            )

            caract_list = []

            self.coef_por_ventana = {}

            for vid, grupo in (
                self.ventanas_segmentadas.groupby(
                    "ID_Ventana"
                )
            ):

                # =============================================
                # SEÑAL DE LA VENTANA
                # =============================================

                ventana_total = (
                    grupo["Magnitud"].values
                )

                # =============================================
                # CARACTERÍSTICAS WAVELET
                # =============================================

                caract, coef_puros = (
                    extraer_caracteristicas_wavelet(
                        ventana_total,
                        tipo_wavelet,
                        niveles
                    )
                )

                if caract is None:
                    continue

                # =============================================
                # ESTADO MAYORITARIO
                # =============================================

                estado_mayoritario = (
                    grupo[
                        "Estado_Ventana"
                    ].iloc[0]
                )

                # =============================================
                # VELOCIDAD DE LA VENTANA
                # =============================================

                velocidad_ventana = pd.to_numeric(
                    grupo["Velocidad"],
                    errors="coerce"
                )

                # Promedio
                velocidad_prom = (
                    velocidad_ventana.mean()
                )

                # Mínima
                velocidad_min = (
                    velocidad_ventana.min()
                )

                # Máxima
                velocidad_max = (
                    velocidad_ventana.max()
                )

                # =============================================
                # ENERGÍA DE LA VENTANA
                # =============================================
                #
                # Energía = suma de los cuadrados de las
                # muestras de la magnitud del acelerómetro.
                #
                # E = Σ x²
                #
                # Se calcula solamente sobre las muestras
                # pertenecientes a esta ventana.
                # =============================================

                energia = np.sum(
                    ventana_total ** 2
                )

                # =============================================
                # CREAR FILA DE CARACTERÍSTICAS
                # =============================================

                caract_row = {
                    "ID_Ventana": vid,

                    "Estado": estado_mayoritario,

                    # -----------------------------
                    # CARACTERÍSTICAS WAVELET
                    # -----------------------------
                    **caract,

                    # -----------------------------
                    # CARACTERÍSTICAS VELOCIDAD
                    # -----------------------------
                    "Velocidad_prom": velocidad_prom,
                    "Velocidad_min": velocidad_min,
                    "Velocidad_max": velocidad_max,

                    # -----------------------------
                    # ENERGÍA
                    # -----------------------------
                    "Energia": energia,
                }

                caract_list.append(
                    caract_row
                )

                self.coef_por_ventana[
                    int(vid)
                ] = coef_puros

            # =================================================
            # CREAR DATAFRAME DE CARACTERÍSTICAS
            # =================================================

            df_caract = pd.DataFrame(
                caract_list
            )

            # =================================================
            # ASEGURAR ORDEN DE COLUMNAS
            # =================================================

            columnas_inicio = [
                "ID_Ventana",
                "Estado"
            ]

            columnas_velocidad = [
                "Velocidad_prom",
                "Velocidad_min",
                "Velocidad_max"
            ]

            columna_energia = [
                "Energia"
            ]

            # Todas las características Wavelet
            columnas_wavelet = [
                columna
                for columna in df_caract.columns
                if columna not in (
                    columnas_inicio
                    + columnas_velocidad
                    + columna_energia
                )
            ]

            # Orden final
            columnas_finales = (
                columnas_inicio
                + columnas_wavelet
                + columnas_velocidad
                + columna_energia
            )

            df_caract = (
                df_caract[
                    columnas_finales
                ]
            )

            # =================================================
            # GUARDAR CARACTERÍSTICAS
            # =================================================

            guardar_csv(
                df_caract,
                caract_file
            )

            self.append_log(
                f"Características guardadas en "
                f"{caract_file}"
            )

            self.append_log(
                "✅ Características agregadas por ventana:"
            )

            self.append_log(
                "   • Velocidad_prom"
            )

            self.append_log(
                "   • Velocidad_min"
            )

            self.append_log(
                "   • Velocidad_max"
            )

            self.append_log(
                "   • Energia"
            )

            # =================================================
            # COEFICIENTES PLANOS
            # =================================================

            coef_flat = []

            for vid, coefs in (
                self.coef_por_ventana.items()
            ):

                row = {
                    "ID_Ventana": vid
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
                f"Coeficientes guardados en "
                f"{coef_file}"
            )

            # =================================================
            # GUARDAR RUTAS
            # =================================================

            self.last_output_paths = {
                "magnitud": magnitud_file,
                "ventanas": ventanas_file,
                "caracteristicas": caract_file,
                "coeficientes": coef_file,
                "sufijo": sufijo,
            }

            # =================================================
            # RENDER PRIMERA VENTANA
            # =================================================

            first = (
                self.ventanas_segmentadas[
                    "ID_Ventana"
                ]
                .unique()[0]
            )

            self.render_coeficientes(
                int(first)
            )

            # =================================================
            # FINAL
            # =================================================

            self.append_log(
                "✅ Análisis completado correctamente."
            )

        except Exception as e:

            self.append_log(
                f"Error: {e}"
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
                    "<br>Mag: %{y:.4f}"
                    "<extra></extra>"
                ),
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
            hovermode="x unified",
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
                    x=grupo.index,
                    y=grupo["Magnitud"],
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
                        "Idx: %{x}"
                        "<br>Mag: %{y:.4f}"
                        "<br>Ventana: "
                        + str(vid)
                        + "<extra></extra>"
                    ),
                )
            )

        fig.update_layout(
            title="Ventanas segmentadas",
            xaxis_title="Índice (muestra)",
            yaxis_title="Magnitud",
            template="plotly_dark",
            margin=dict(
                l=40,
                r=20,
                t=60,
                b=40
            ),
        )

        self.view_vent.set_figure(
            fig
        )

    # =====================================================
    # RENDER COEFICIENTES
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

        niveles = len(coefs) - 1

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
                            "Idx: %{x}"
                            "<br>A: %{y:.4f}"
                            "<extra></extra>"
                        ),
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
                            "Idx: %{x}"
                            "<br>D"
                            + str(i)
                            + ": %{y:.4f}"
                            "<extra></extra>"
                        ),
                    )
                )

        fig.update_layout(
            title=(
                f"Coeficientes Wavelet "
                f"- Ventana {vid}"
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
            ),
        )

        self.view_coef.set_figure(
            fig
        )

    # =====================================================
    # CALLBACKS
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

            # =================================================
            # HTML MAGNITUD
            # =================================================

            df_mag = pd.read_csv(
                ruta_mag
            )

            fig_mag = go.Figure()

            fig_mag.add_trace(
                go.Scatter(
                    x=df_mag["Timestamp"],
                    y=df_mag["Magnitud"],
                    mode="lines",
                    name="Magnitud"
                )
            )

            fig_mag.update_layout(
                title="Magnitud del Acelerómetro",
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
                        x=grupo.index,
                        y=grupo["Magnitud"],
                        mode="lines",
                        name=f"Ventana {vid}"
                    )
                )

            fig_v.update_layout(
                title="Ventanas segmentadas",
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
            # HTML COEFICIENTES
            # =================================================

            df_coef = pd.read_csv(
                ruta_coef
            )

            if not df_coef.empty:

                row = df_coef.iloc[0]

                fig_c = go.Figure()

                for col in df_coef.columns:

                    if col.endswith(
                        "_coefs"
                    ):

                        valores = list(
                            map(
                                float,
                                str(
                                    row[col]
                                ).split(",")
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
                    title="Coeficientes Wavelet",
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
            # MENSAJE FINAL
            # =================================================

            QMessageBox.information(
                self,
                "Exportación lista",
                "Se exportaron los HTML en la carpeta 'salida/'."
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