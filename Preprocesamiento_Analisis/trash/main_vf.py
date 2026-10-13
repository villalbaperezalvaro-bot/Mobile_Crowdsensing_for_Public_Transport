import sys
import os
BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)
sys.path.insert(0, BASE_DIR)
import pandas as pd
import datetime
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QFileDialog,
    QVBoxLayout, QFormLayout, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox,
    QTabWidget, QHBoxLayout, QMessageBox
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt


# WebEngine para incrustar Plotly
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
except Exception as e:  # Mensaje claro si falta el módulo
    raise SystemExit("Falta PyQt6-WebEngine. Instala con: pip install PyQt6-WebEngine\nError: " + str(e))

# Plotly
import plotly.graph_objects as go
import plotly.io as pio

from datos.acceso_datos import leer_csv, guardar_csv
from logica.procesamiento import extraer_caracteristicas_wavelet
from logica.magnitud import calcular_magnitud
from logica.segmentar_traslape import segmentar_traslape_csv


class PlotlyView(QWebEngineView):
    """Wrapper para renderizar figuras Plotly en un QWebEngineView."""
    def __init__(self, parent=None):
        super().__init__(parent)
        # Fondo oscuro coherente
        self.setStyleSheet("background: #1e1e2f;")

    def set_figure(self, fig: go.Figure):
        html = pio.to_html(fig, full_html=False, include_plotlyjs='cdn', config={
            'responsive': True,
            'displaylogo': False,
            'modeBarButtonsToRemove': ['lasso2d', 'select2d']
        })
        self.setHtml(html)

class AnalisisWaveletApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("📊 Análisis TWD - Deluxe (PyQt6 + Plotly)")
        self.setGeometry(60, 30, 1360, 860)
        self.setStyleSheet(
            """
            QWidget { background-color: #0f1220; color: #e6e6e9; }
            QLabel { font-size: 14px; }
            QPushButton { background-color: #4f46e5; color: white; font-weight: 600; padding: 10px 14px; border-radius: 10px; }
            QPushButton:hover { background-color: #181283; }
            
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
                background-color: #191c2b; color: #e6e6e9; padding: 8px; border-radius: 8px; border: 1px solid #2a2f45;
            }
            QTextEdit { background-color: #0f1428; color: #cbd5e1; border: 1px solid #243047; border-radius: 12px; }
            
            QTabWidget::pane { border: 1px solid #243047; border-radius: 12px; }
            QTabBar::tab { background: #191c2b; color: #e6e6e9; padding: 8px 16px; border-top-left-radius: 10px; border-top-right-radius: 10px; }
            QTabBar::tab:selected { background: #0f1428; }
            """
        )
        # Estado interno
        self.df_magnitud = None
        self.ventanas_segmentadas = None
        self.coef_por_ventana = {}  # id -> list[np.ndarray]

        # ---- Layouts ----
        root = QVBoxLayout(self)
        form = QFormLayout()

        # --- Controles de archivo y parámetros ---
        self.csv_input = QLineEdit()
        self.csv_input.setPlaceholderText("Selecciona un CSV de entrada…")
        btn_browse = QPushButton("📂 Seleccionar CSV")
        btn_browse.clicked.connect(self.seleccionar_csv)
        file_row = QHBoxLayout()
        file_row.addWidget(self.csv_input, stretch=1)
        file_row.addWidget(btn_browse)
        file_row_w = QWidget(); file_row_w.setLayout(file_row)
        form.addRow("Archivo CSV de entrada:", file_row_w)

        self.ventana_seg = QDoubleSpinBox(); self.ventana_seg.setRange(0.1, 60.0); self.ventana_seg.setValue(1.0); self.ventana_seg.setSingleStep(0.1)
        form.addRow("Tamaño de ventana (s):", self.ventana_seg)

        self.porcentaje_estado = QDoubleSpinBox(); self.porcentaje_estado.setRange(0, 100); self.porcentaje_estado.setValue(80)
        form.addRow("Porcentaje mínimo estado (%):", self.porcentaje_estado)

        self.traslape_pct = QSpinBox(); self.traslape_pct.setRange(0, 100); self.traslape_pct.setValue(0)
        form.addRow("Traslape (%):", self.traslape_pct)

        self.tipo_wavelet = QComboBox(); self.tipo_wavelet.addItems(['db1','db2','db3','db4','haar'])
        form.addRow("Tipo de wavelet:", self.tipo_wavelet)

        self.niveles = QSpinBox(); self.niveles.setRange(1, 10); self.niveles.setValue(3)
        form.addRow("Niveles de descomposición:", self.niveles)

        # Botones de acción
        actions = QHBoxLayout()
        self.btn_run = QPushButton("Ejecutar análisis")
        self.btn_run.clicked.connect(self.ejecutar_analisis)
        self.btn_export = QPushButton("Exportar gráficos a HTML")
        self.btn_export.clicked.connect(self.exportar_html)
        actions.addWidget(self.btn_run)
        actions.addWidget(self.btn_export)

        # Tabs con Plotly
        self.tabs = QTabWidget()

        # Tab Magnitud
        self.view_mag = PlotlyView()
        tab_mag = QWidget(); lay_mag = QVBoxLayout(tab_mag);
        lay_mag.addWidget(self.view_mag)
        self.tabs.addTab(tab_mag, "Magnitud")

        # Tab Ventanas
        self.view_vent = PlotlyView()
        tab_vent = QWidget(); lay_vent = QVBoxLayout(tab_vent)
        # Selector de ventana para resaltar/filtrar
        sel_row = QHBoxLayout()
        self.combo_ventana = QComboBox(); self.combo_ventana.currentIndexChanged.connect(self.actualizar_plots_por_ventana)
        self.combo_ventana.addItem("Todas")
        sel_row.addWidget(QLabel("Mostrar ventana:"))
        sel_row.addWidget(self.combo_ventana)
        sel_row_w = QWidget(); sel_row_w.setLayout(sel_row)
        lay_vent.addWidget(sel_row_w)
        lay_vent.addWidget(self.view_vent)
        self.tabs.addTab(tab_vent, "Ventanas segmentadas")

        # Tab Coeficientes
        self.view_coef = PlotlyView()
        tab_coef = QWidget(); lay_coef = QVBoxLayout(tab_coef)
        lay_coef.addWidget(self.view_coef)
        self.tabs.addTab(tab_coef, "Coeficientes Wavelet (hover)")

        # Log
        self.log = QTextEdit(); self.log.setReadOnly(True); self.log.setFont(QFont("JetBrains Mono", 10))

        # Ensamble
        root.addLayout(form)
        root.addLayout(actions)
        root.addWidget(self.tabs, stretch=1)
        root.addWidget(QLabel("Registro de progreso:"))
        root.addWidget(self.log, stretch=1)

    # ---------- Utilidades UI ----------
    def append_log(self, msg: str):
        self.log.append(msg)
        QApplication.processEvents()

    def seleccionar_csv(self):
        ruta, _ = QFileDialog.getOpenFileName(self, "Seleccionar CSV", "", "CSV (*.csv)")
        if ruta:
            self.csv_input.setText(ruta)

    # ---------- Pipeline principal ----------
    def ejecutar_analisis(self):
        try:
            ruta = self.csv_input.text().strip()
            if not ruta:
                QMessageBox.warning(self, "CSV requerido", "Selecciona un archivo CSV de entrada.")
                return

            ventana_seg = float(self.ventana_seg.value())
            porcentaje_estado = float(self.porcentaje_estado.value())
            traslape_pct = int(self.traslape_pct.value())
            tipo_wavelet = self.tipo_wavelet.currentText()
            niveles = int(self.niveles.value())
            
            # Generar sufijo único
            sufijo = datetime.datetime.now().strftime("%Y%m%d_%H%M")

            self.append_log("Leyendo CSV de entrada…")
            df = leer_csv(ruta)

            # Magnitud
            self.append_log("🔹 Calculando magnitud…")
            magnitud = calcular_magnitud(df["AccelX"], df["AccelY"], df["AccelZ"])
            self.df_magnitud = pd.DataFrame({
                "Timestamp": pd.to_datetime(df["Timestamp"]),
                "Magnitud": magnitud,
                "Estado": df["Estado"],
            })
            os.makedirs("salida", exist_ok=True)
            
            """ magnitud_file = f"salida/magnitud_acel_{sufijo}.csv"
            guardar_csv(self.df_magnitud, magnitud_file)
            self.append_log(f"Magnitud guardada en {magnitud_file}") """
            
            guardar_csv(self.df_magnitud, "salida/magnitud_acel.csv")
            self.append_log("Magnitud guardada en salida/magnitud_acel.csv")

            # Plot magnitud
            self.render_magnitud(self.df_magnitud)

            # Segmentar
            self.append_log("Segmentando señal…")
            self.ventanas_segmentadas = segmentar_traslape_csv(
                "salida/magnitud_acel.csv", ventana_seg, traslape_pct, porcentaje_estado
            )
            guardar_csv(self.ventanas_segmentadas, "salida/ventanas_segmentadas.csv")
            self.append_log("Ventanas segmentadas guardadas en salida/ventanas_segmentadas.csv")

            # Plot ventanas + combo
            self.combo_ventana.blockSignals(True)
            self.combo_ventana.clear(); self.combo_ventana.addItem("Todas")
            for vid in self.ventanas_segmentadas["ID_Ventana"].unique().tolist():
                self.combo_ventana.addItem(str(vid))
            self.combo_ventana.blockSignals(False)
            self.render_ventanas(self.ventanas_segmentadas, selected=None)

            # Extraer características y coeficientes
            self.append_log("Extrayendo características y coeficientes Wavelet…")
            caract_list = []
            self.coef_por_ventana = {}
            for vid, grupo in self.ventanas_segmentadas.groupby("ID_Ventana"):
                ventana_total = grupo["Magnitud"].values
                caract, coef_puros = extraer_caracteristicas_wavelet(ventana_total, tipo_wavelet, niveles)
                estado_mayoritario = grupo["Estado_Ventana"].iloc[0] 
                caract_row = {"ID_Ventana": vid,"Estado":estado_mayoritario, **caract}
                caract_list.append(caract_row)
                self.coef_por_ventana[int(vid)] = coef_puros

            # Guardar CSVs
            df_caract = pd.DataFrame(caract_list)
            guardar_csv(df_caract, "salida/caracteristicas_wavelet.csv")
            self.append_log("Características guardadas en salida/caracteristicas_wavelet.csv")

            # Coefs planos
            coef_flat = []
            for vid, coefs in self.coef_por_ventana.items():
                row = {"ID_Ventana": vid}
                for i, c in enumerate(coefs):
                    if i == 0:
                        row[f"A{niveles}_coefs"] = ",".join(map(str, c))
                    else:
                        row[f"D{i}_coefs"] = ",".join(map(str, c))
                coef_flat.append(row)
            guardar_csv(pd.DataFrame(coef_flat), "salida/coeficientes_wavelet.csv")
            self.append_log("Coeficientes guardados en salida/coeficientes_wavelet.csv")

            # Render coeficientes de la primera ventana o la seleccionada
            first = self.ventanas_segmentadas["ID_Ventana"].unique()[0]
            self.render_coeficientes(int(first))

            self.append_log("Análisis completado.")
        except Exception as e:
            self.append_log(f"Error: {e}")

    # ---------- Render Plotly ----------
    def render_magnitud(self, df_mag: pd.DataFrame):
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_mag["Timestamp"], y=df_mag["Magnitud"], mode='lines', name='Magnitud',
            hovertemplate='Tiempo: %{x}<br>Mag: %{y:.4f}<extra></extra>'
        ))
        fig.update_layout(
            title='Magnitud del Acelerómetro',
            xaxis_title='Tiempo', yaxis_title='Magnitud',
            template='plotly_dark', margin=dict(l=40, r=20, t=60, b=40),
            hovermode='x unified'
        )
        self.view_mag.set_figure(fig)

    def render_ventanas(self, df_seg: pd.DataFrame, selected: int | None):
        fig = go.Figure()
        # Si el CSV de segmentación mantiene índice original, usamos un eje X continuo
        x = list(range(len(df_seg)))
        # Trazas por ventana
        for vid, grupo in df_seg.groupby("ID_Ventana"):
            # Usamos las posiciones reales del grupo para que se vea la separación
            fig.add_trace(go.Scatter(
                x=grupo.index, y=grupo["Magnitud"], mode='lines', name=f'Ventana {vid}',
                line=dict(width=2 if (selected is not None and int(vid)==selected) else 1),
                opacity=1.0 if (selected is None or int(vid)==selected) else 0.25,
                hovertemplate='Idx: %{x}<br>Mag: %{y:.4f}<br>Ventana: '+str(vid)+'<extra></extra>'
            ))
        fig.update_layout(
            title='Ventanas segmentadas', xaxis_title='Índice (muestra)', yaxis_title='Magnitud',
            template='plotly_dark', margin=dict(l=40, r=20, t=60, b=40)
        )
        self.view_vent.set_figure(fig)

    def render_coeficientes(self, vid: int):
        coefs = self.coef_por_ventana.get(int(vid))
        if coefs is None:
            # limpiar
            self.view_coef.set_figure(go.Figure())
            return
        niveles = len(coefs) - 1
        fig = go.Figure()
        for i, c in enumerate(coefs):
            if i == 0:
                fig.add_trace(go.Scatter(y=c, mode='lines', name=f'Aproximación A{niveles}',
                                         hovertemplate='Idx: %{x}<br>A: %{y:.4f}<extra></extra>'))
            else:
                fig.add_trace(go.Scatter(y=c, mode='lines', name=f'Detalle D{i}',
                                         line=dict(dash='dash'),
                                         hovertemplate='Idx: %{x}<br>D'+str(i)+': %{y:.4f}<extra></extra>'))
        fig.update_layout(
            title=f'Coeficientes Wavelet - Ventana {vid}',
            xaxis_title='Índice del coeficiente', yaxis_title='Valor',
            template='plotly_dark', margin=dict(l=40, r=20, t=60, b=40)
        )
        self.view_coef.set_figure(fig)

    # ---------- Callbacks ----------
    def actualizar_plots_por_ventana(self):
        if self.ventanas_segmentadas is None:
            return
        texto = self.combo_ventana.currentText()
        selected = None if (texto == "Todas" or texto == "") else int(texto)
        # Actualiza ventana resaltada en el tab de Ventanas
        self.render_ventanas(self.ventanas_segmentadas, selected)
        # Si hay id, también refresca coeficientes
        if selected is not None:
            self.render_coeficientes(selected)

    # ---------- Exportar ----------
    def exportar_html(self):
        # Exporta los 3 tabs a archivos HTML independientes dentro de /salida
        try:
            if self.df_magnitud is None:
                QMessageBox.information(self, "Nada que exportar", "Primero ejecuta el análisis.")
                return
            os.makedirs("salida", exist_ok=True)
            # Reconstruir las figuras actuales y guardarlas
            # Magnitud
            fig_mag = go.Figure()
            fig_mag.add_trace(go.Scatter(x=self.df_magnitud["Timestamp"], y=self.df_magnitud["Magnitud"], mode='lines', name='Magnitud'))
            fig_mag.update_layout(title='Magnitud del Acelerómetro', template='plotly_dark')
            with open("salida/magnitud.html", "w", encoding="utf-8") as f:
                f.write(pio.to_html(fig_mag, full_html=True, include_plotlyjs='cdn'))
            # Ventanas (todas)
            fig_v = go.Figure()
            for vid, grupo in self.ventanas_segmentadas.groupby("ID_Ventana"):
                fig_v.add_trace(go.Scatter(x=grupo.index, y=grupo["Magnitud"], mode='lines', name=f'Ventana {vid}'))
            fig_v.update_layout(title='Ventanas segmentadas', template='plotly_dark')
            with open("salida/ventanas_segmentadas.html", "w", encoding="utf-8") as f:
                f.write(pio.to_html(fig_v, full_html=True, include_plotlyjs='cdn'))
            # Coeficientes (si hay selección, usa esa; si no, la primera)
            vid = None
            texto = self.combo_ventana.currentText()
            if texto and texto != "Todas":
                vid = int(texto)
            else:
                vid = list(self.coef_por_ventana.keys())[0] if self.coef_por_ventana else None
            if vid is not None:
                coefs = self.coef_por_ventana[vid]
                fig_c = go.Figure()
                for i, c in enumerate(coefs):
                    if i == 0:
                        fig_c.add_trace(go.Scatter(y=c, mode='lines', name=f'Aproximación A{len(coefs)-1}'))
                    else:
                        fig_c.add_trace(go.Scatter(y=c, mode='lines', name=f'Detalle D{i}', line=dict(dash='dash')))
                fig_c.update_layout(title=f'Coeficientes Wavelet - Ventana {vid}', template='plotly_dark')
                with open("salida/coeficientes_wavelet.html", "w", encoding="utf-8") as f:
                    f.write(pio.to_html(fig_c, full_html=True, include_plotlyjs='cdn'))

            QMessageBox.information(self, "Exportación lista",
                                    "Se exportaron los HTML en la carpeta 'salida/'.")
        except Exception as e:
            QMessageBox.critical(self, "Error al exportar", str(e))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = AnalisisWaveletApp()
    w.show()
    sys.exit(app.exec())
