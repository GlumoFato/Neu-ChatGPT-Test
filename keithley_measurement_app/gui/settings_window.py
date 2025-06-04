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
from .measurement_window import MeasurementWindow


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



