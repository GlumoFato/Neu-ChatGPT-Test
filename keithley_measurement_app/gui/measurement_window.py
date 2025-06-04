import sys
import os
import re
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                            QGridLayout, QWidget, QLabel, QLineEdit, QPushButton,
                            QTableWidget, QTableWidgetItem, QMessageBox, QSpinBox,
                            QMenuBar, QTabWidget, QTextEdit, QFrame, QSizePolicy,
                            QProgressBar)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QFont, QAction
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from ..measurement.worker import MeasurementWorker
from .settings_window import SettingsWindow

class MeasurementWindow(QMainWindow):
    def __init__(self, config, channels, labels):
        super().__init__()
        self.config = config
        self.channels = channels
        self.labels = labels
        self.measurement_data = {ch: [] for ch in channels}
        self.time_data = []
        self.measurement_running = False
        
        # Worker thread setup
        self.worker_thread = QThread()
        self.worker = MeasurementWorker(config, channels, labels)
        self.worker.moveToThread(self.worker_thread)
        
        # Connect signals
        self.worker.connected.connect(self.on_connected)
        self.worker.error.connect(self.on_error)
        self.worker.data.connect(self.on_data_received)
        self.worker.finished.connect(self.on_measurement_finished)
        self.worker.progress.connect(self.on_progress)
        
        self.worker_thread.started.connect(self.worker.process)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        
        self.setWindowTitle("Keithley Messung - Laufende Messung")
        self.setGeometry(150, 150, 1200, 800)
        
        self.init_ui()
        
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        
        # Status and progress
        status_layout = QHBoxLayout()
        self.status_label = QLabel("Verbinde...")
        self.status_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        status_layout.addWidget(self.status_label)
        
        # Progress bar (only shown for finite measurements)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        status_layout.addWidget(self.progress_bar)
        layout.addLayout(status_layout)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        
        # Data tab
        self.data_tab = QWidget()
        self.init_data_tab()
        self.tab_widget.addTab(self.data_tab, "Daten")
        
        # Graph tab
        self.graph_tab = QWidget()
        self.init_graph_tab()
        self.tab_widget.addTab(self.graph_tab, "Graphen")
        
        layout.addWidget(self.tab_widget)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.pause_btn = QPushButton("Pause")
        self.pause_btn.clicked.connect(self.pause_measurement)
        self.pause_btn.setEnabled(False)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_measurement)
        
        self.back_btn = QPushButton("Zurück zu Einstellungen")
        self.back_btn.clicked.connect(self.back_to_settings)
        self.back_btn.setEnabled(False)
        
        self.exit_btn = QPushButton("Programm beenden")
        self.exit_btn.clicked.connect(self.close_application)
        
        button_layout.addWidget(self.pause_btn)
        button_layout.addWidget(self.stop_btn)
        button_layout.addWidget(self.back_btn)
        button_layout.addWidget(self.exit_btn)
        
        layout.addLayout(button_layout)
        central_widget.setLayout(layout)
        
        # Start measurement worker
        self.start_measurement()
        
    def init_data_tab(self):
        layout = QVBoxLayout()
        
        # Connection info
        self.connection_label = QLabel("Nicht verbunden")
        layout.addWidget(self.connection_label)
        
        # Data display
        self.data_text = QTextEdit()
        self.data_text.setReadOnly(True)
        self.data_text.setFont(QFont("Courier", 10))
        layout.addWidget(self.data_text)
        
        self.data_tab.setLayout(layout)
        
    def init_graph_tab(self):
        layout = QVBoxLayout()
        
        # Create matplotlib figure
        self.figure = Figure(figsize=(12, 8))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        
        self.graph_tab.setLayout(layout)
        
    def start_measurement(self):
        self.measurement_running = True
        self.worker_thread.start()
        
        # Show progress bar for finite measurements
        if self.config["scan_count"] > 0:
            self.progress_bar.setMaximum(self.config["scan_count"])
            self.progress_bar.setVisible(True)
        
    @pyqtSlot(str)
    def on_connected(self, connection_info):
        self.connection_label.setText(connection_info)
        self.status_label.setText("Messung läuft...")
        self.pause_btn.setEnabled(True)
        
    @pyqtSlot(str)
    def on_error(self, error_message):
        # Append error to data display
        current_text = self.data_text.toPlainText()
        if current_text:
            current_text += "\n"
        self.data_text.setPlainText(current_text + f"FEHLER: {error_message}")
        
        # Scroll to bottom
        cursor = self.data_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.data_text.setTextCursor(cursor)
        
    @pyqtSlot(str)
    def on_data_received(self, data_line):
        # Parse the data line to extract values for plotting
        try:
            # Format: "01/∞ | 0:05 | 101: 25.00°C  102: 26.00°C"
            parts = data_line.split(" | ")
            if len(parts) >= 3:
                # Extract measurement index and time
                idx_part = parts[0].split("/")[0]
                measurement_idx = int(idx_part) - 1
                
                time_part = parts[1]
                minutes, seconds = map(int, time_part.split(":"))
                time_in_seconds = minutes * 60 + seconds
                
                # Ensure we have enough time data points
                while len(self.time_data) <= measurement_idx:
                    if len(self.time_data) == 0:
                        self.time_data.append(0)
                    else:
                        # Estimate time based on interval
                        self.time_data.append(len(self.time_data) * self.config["scan_interval"])
                
                # Update the actual time
                if measurement_idx < len(self.time_data):
                    self.time_data[measurement_idx] = time_in_seconds
                
                # Extract temperature values
                temp_data = parts[2] if len(parts) > 2 else ""
                for i, channel in enumerate(self.channels):
                    # Ensure measurement_data has enough entries
                    while len(self.measurement_data[channel]) <= measurement_idx:
                        self.measurement_data[channel].append(None)
                    
                    # Try to extract temperature for this channel
                    pattern = rf"{channel}:\s*([0-9.-]+)°C"
                    match = re.search(pattern, temp_data)
                    if match:
                        temp_value = float(match.group(1))
                        self.measurement_data[channel][measurement_idx] = temp_value
                    else:
                        # Check for "None" values
                        none_pattern = rf"{channel}:\s*None"
                        if re.search(none_pattern, temp_data):
                            self.measurement_data[channel][measurement_idx] = None
                
                # Update graph
                self.update_graph()
                
        except Exception as e:
            # If parsing fails, just display the raw data
            pass
        
        # Display the data line
        current_text = self.data_text.toPlainText()
        if current_text:
            current_text += "\n"
        self.data_text.setPlainText(current_text + data_line)
        
        # Scroll to bottom
        cursor = self.data_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.data_text.setTextCursor(cursor)
        
    @pyqtSlot(int, int)
    def on_progress(self, current, total):
        self.progress_bar.setValue(current)
        self.status_label.setText(f"Messung läuft... ({current}/{total})")
        
    @pyqtSlot()
    def on_measurement_finished(self):
        self.measurement_running = False
        self.status_label.setText("Messung beendet.")
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.back_btn.setEnabled(True)
        self.worker_thread.quit()
        self.worker_thread.wait()
        
    def pause_measurement(self):
        if hasattr(self.worker, 'pause_flag'):
            if self.worker.pause_flag:
                self.worker.pause_flag = False
                self.pause_btn.setText("Pause")
                self.status_label.setText("Messung läuft...")
            else:
                self.worker.pause_flag = True
                self.pause_btn.setText("Fortsetzen")
                self.status_label.setText("Messung pausiert...")
                
    def stop_measurement(self):
        if self.worker:
            self.worker.stop()
        self.status_label.setText("Messung wird gestoppt...")
        self.stop_btn.setEnabled(False)
        
    def back_to_settings(self):
        # Create new settings window
        self.settings_window = SettingsWindow()
        self.settings_window.show()
        self.close()
        
    def close_application(self):
        if self.measurement_running and self.worker:
            self.worker.stop()
        if self.worker_thread.isRunning():
            self.worker_thread.quit()
            self.worker_thread.wait()
        QApplication.quit()
        
    def closeEvent(self, event):
        # Handle window close event
        if self.measurement_running and self.worker:
            reply = QMessageBox.question(self, 'Messung läuft', 
                                       'Messung läuft noch. Wirklich beenden?',
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                       QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.worker.stop()
                if self.worker_thread.isRunning():
                    self.worker_thread.quit()
                    self.worker_thread.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
        
    def update_graph(self):
        self.figure.clear()
        
        if not self.time_data or not any(self.measurement_data.values()):
            return
            
        ax = self.figure.add_subplot(111)
        
        # Plot temperature data for each channel
        for i, (channel, label) in enumerate(zip(self.channels, self.labels)):
            if channel in self.measurement_data:
                data = self.measurement_data[channel]
                # Filter out None values for plotting
                valid_times = []
                valid_temps = []
                for j, temp in enumerate(data):
                    if temp is not None and j < len(self.time_data):
                        valid_times.append(self.time_data[j])
                        valid_temps.append(temp)
                
                if valid_times and valid_temps:
                    ax.plot(valid_times, valid_temps, label=f"{label} (Ch {channel})", 
                           marker='o', markersize=3, linewidth=1.5)
                
        ax.set_xlabel('Zeit (s)')
        ax.set_ylabel('Temperatur (°C)')
        ax.set_title('Temperaturverlauf')
        ax.grid(True, alpha=0.3)
        
        # Add legend if there are plots
        if ax.get_lines():
            ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        
