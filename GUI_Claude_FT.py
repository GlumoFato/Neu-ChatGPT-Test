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
from measurement_pyqt6 import MeasurementWorker


class SettingsWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Keithley Messung - Einstellungen")
        self.setGeometry(100, 100, 800, 600)
        
        # Initialize channels data
        self.channels = {}
        self.used_channels = set()
        
        self.init_menu()
        self.init_ui()
        
    def init_menu(self):
        menubar = self.menuBar()
        
        # Datei Menu
        file_menu = menubar.addMenu('Datei')
        
        load_action = QAction('Konfiguration laden', self)
        load_action.triggered.connect(self.load_config)
        file_menu.addAction(load_action)
        
        save_action = QAction('Konfiguration speichern', self)
        save_action.triggered.connect(self.save_config)
        file_menu.addAction(save_action)
        
        # Hilfe Menu
        help_menu = menubar.addMenu('Hilfe')
        
        about_action = QAction('Über', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        
        # IP Address
        ip_layout = QHBoxLayout()
        ip_layout.addWidget(QLabel("IP-Adresse:"))
        self.ip_edit = QLineEdit("10.222.19.121")
        self.ip_edit.textChanged.connect(self.validate_ip)
        ip_layout.addWidget(self.ip_edit)
        layout.addLayout(ip_layout)
        
        # Anzahl Messungen
        count_layout = QHBoxLayout()
        count_layout.addWidget(QLabel("Anzahl Messungen (0=∞):"))
        self.count_spin = QSpinBox()
        self.count_spin.setRange(0, 99999)
        self.count_spin.setValue(0)
        count_layout.addWidget(self.count_spin)
        layout.addLayout(count_layout)
        
        # Intervall
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("Intervall (1s - 600s):"))
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 600)
        self.interval_spin.setValue(5)
        self.interval_spin.setSuffix(" s")
        interval_layout.addWidget(self.interval_spin)
        layout.addLayout(interval_layout)
        
        # Output filename
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Ausgabedateiname:"))
        self.output_edit = QLineEdit("DonnerstagTestTest")
        self.output_edit.textChanged.connect(self.validate_filename)
        output_layout.addWidget(self.output_edit)
        layout.addLayout(output_layout)
        
        # Min/Max values
        minmax_layout = QHBoxLayout()
        minmax_layout.addWidget(QLabel("Min-Wert:"))
        self.min_spin = QSpinBox()
        self.min_spin.setRange(-150, 999)
        self.min_spin.setValue(0)
        self.min_spin.setSuffix(" °C")
        minmax_layout.addWidget(self.min_spin)
        
        minmax_layout.addWidget(QLabel("Max-Wert:"))
        self.max_spin = QSpinBox()
        self.max_spin.setRange(-150, 999)
        self.max_spin.setValue(300)
        self.max_spin.setSuffix(" °C")
        minmax_layout.addWidget(self.max_spin)
        layout.addLayout(minmax_layout)
        
        # Min/Max validation
        self.min_spin.valueChanged.connect(self.validate_min_max)
        self.max_spin.valueChanged.connect(self.validate_min_max)
        
        # Channels section
        channels_label = QLabel("Kanäle & Label:")
        channels_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(channels_label)
        
        # Channel table
        self.channel_table = QTableWidget()
        self.channel_table.setColumnCount(2)
        self.channel_table.setHorizontalHeaderLabels(["Kanal", "Beschriftung"])
        self.channel_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.channel_table)
        
        # Channel buttons
        channel_btn_layout = QHBoxLayout()
        self.add_channel_btn = QPushButton("+ Kanal")
        self.add_channel_btn.clicked.connect(self.add_channel)
        self.remove_channel_btn = QPushButton("- Kanal")
        self.remove_channel_btn.clicked.connect(self.remove_channel)
        
        channel_btn_layout.addWidget(self.add_channel_btn)
        channel_btn_layout.addWidget(self.remove_channel_btn)
        channel_btn_layout.addStretch()
        layout.addLayout(channel_btn_layout)
        
        # Control buttons
        button_layout = QHBoxLayout()
        self.start_btn = QPushButton("Messung starten")
        self.start_btn.clicked.connect(self.start_measurement)
        self.exit_btn = QPushButton("Programm beenden")
        self.exit_btn.clicked.connect(self.close)
        
        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.exit_btn)
        layout.addLayout(button_layout)
        
        central_widget.setLayout(layout)
        
    def validate_ip(self):
        ip = self.ip_edit.text()
        # Simple IP validation regex
        ip_pattern = r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$'
        match = re.match(ip_pattern, ip)
        
        if match:
            parts = [int(part) for part in match.groups()]
            if all(0 <= part <= 255 for part in parts):
                self.ip_edit.setStyleSheet("")
                return True
        
        if ip:  # Only show error if field is not empty
            self.ip_edit.setStyleSheet("border: 2px solid red;")
        return False
        
    def validate_filename(self):
        filename = self.output_edit.text()
        # Allow German letters, numbers, hyphen, underscore
        valid_pattern = r'^[a-zA-ZäöüÄÖÜß0-9_-]*$'
        
        if re.match(valid_pattern, filename):
            self.output_edit.setStyleSheet("")
            return True
        else:
            self.output_edit.setStyleSheet("border: 2px solid red;")
            return False
            
    def validate_min_max(self):
        if self.min_spin.value() >= self.max_spin.value():
            self.min_spin.setStyleSheet("border: 2px solid red;")
            self.max_spin.setStyleSheet("border: 2px solid red;")
            return False
        else:
            self.min_spin.setStyleSheet("")
            self.max_spin.setStyleSheet("")
            return True
            
    def get_next_available_channel(self):
        # Check 101-120 range
        for i in range(101, 121):
            if i not in self.used_channels:
                return i
        # Check 201-220 range
        for i in range(201, 221):
            if i not in self.used_channels:
                return i
        return None
        
    def add_channel(self):
        if len(self.channels) >= 40:
            QMessageBox.warning(self, "Fehler", "Maximal 40 Kanäle erlaubt!")
            return
            
        channel_num = self.get_next_available_channel()
        if channel_num is None:
            QMessageBox.warning(self, "Fehler", "Keine freien Kanäle verfügbar!")
            return
            
        sensor_num = len(self.channels) + 1
        description = f"Sensor {sensor_num}"
        
        self.channels[channel_num] = description
        self.used_channels.add(channel_num)
        self.refresh_channel_table()
        
    def remove_channel(self):
        current_row = self.channel_table.currentRow()
        if current_row >= 0:
            channel_nums = list(self.channels.keys())
            if current_row < len(channel_nums):
                channel_to_remove = channel_nums[current_row]
                del self.channels[channel_to_remove]
                self.used_channels.remove(channel_to_remove)
                self.refresh_channel_table()
                
    def refresh_channel_table(self):
        self.channel_table.setRowCount(len(self.channels))
        
        for row, (channel, description) in enumerate(self.channels.items()):
            # Channel number (read-only)
            channel_item = QTableWidgetItem(str(channel))
            channel_item.setFlags(channel_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.channel_table.setItem(row, 0, channel_item)
            
            # Description (editable)
            desc_item = QTableWidgetItem(description)
            self.channel_table.setItem(row, 1, desc_item)
            
        # Connect item changed signal
        self.channel_table.itemChanged.connect(self.update_channel_description)
        
    def update_channel_description(self, item):
        if item.column() == 1:  # Description column
            row = item.row()
            channel_nums = list(self.channels.keys())
            if row < len(channel_nums):
                channel_num = channel_nums[row]
                self.channels[channel_num] = item.text()
                
    def check_descriptions_changed(self):
        """Check if any descriptions still have default 'Sensor X' format"""
        for channel, description in self.channels.items():
            if re.match(r'^Sensor \d+$', description):
                return False
        return True
        
    def start_measurement(self):
        # Validate all inputs
        if not self.validate_ip():
            QMessageBox.warning(self, "Fehler", "Falsche IP-Adresse!")
            return
            
        if not self.validate_filename():
            QMessageBox.warning(self, "Fehler", "Ungültiger Dateiname! Nur Buchstaben, Zahlen, '-' und '_' erlaubt.")
            return
            
        if not self.validate_min_max():
            QMessageBox.warning(self, "Fehler", "Min-Wert muss kleiner als Max-Wert sein!")
            return
            
        if not self.channels:
            QMessageBox.warning(self, "Fehler", "Mindestens ein Kanal muss hinzugefügt werden!")
            return
            
        if not self.check_descriptions_changed():
            QMessageBox.warning(self, "Fehler", "Bitte ändern Sie die Beschriftungen der Kanäle!")
            return
            
        # Prepare configuration for measurement worker
        config = {
            "ip_address": self.ip_edit.text(),
            "port": 5025,  # Standard Keithley port
            "timeout_ms": 20000,
            "scan_interval": self.interval_spin.value(),
            "scan_count": self.count_spin.value(),
            "min_value": self.min_spin.value(),
            "max_value": self.max_spin.value(),
            "output_base": self.output_edit.text(),
            "run_id": 1
        }
        
        # Prepare channels and labels
        channels = [str(ch) for ch in sorted(self.channels.keys())]
        labels = [self.channels[int(ch)] for ch in channels]
        
        # Start measurement window
        self.measurement_window = MeasurementWindow(config, channels, labels)
        self.measurement_window.show()
        self.hide()
        
    def load_config(self):
        QMessageBox.information(self, "Info", "Konfiguration laden - Funktion noch nicht implementiert")
        
    def save_config(self):
        QMessageBox.information(self, "Info", "Konfiguration speichern - Funktion noch nicht implementiert")
        
    def show_about(self):
        QMessageBox.about(self, "Über", 
                         "Keithley Messung GUI\n\n"
                         "Version 1.0\n"
                         "Entwickelt für Temperaturmessungen\n\n"
                         "© 2025 Ihr Unternehmen")


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
        
        # Adjust layout to prevent legend cutoff
        self.figure.tight_layout()
        self.canvas.draw()


def main():
    app = QApplication(sys.argv)
    window = SettingsWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()