# Keithley Measurement App

This repository contains a PyQt6 based GUI for temperature measurements with a Keithley DMM6500 device. The code is organized as a package with the following structure:

```
keithley_measurement_app/
├── main.py                  # Entry point for the GUI application
├── gui/
│   ├── settings_window.py   # Configuration window
│   ├── measurement_window.py# Window displaying measurements
│   └── __init__.py
├── measurement/
│   ├── worker.py            # Background measurement worker
│   ├── keithley_adapter.py  # Device specific commands
│   ├── data_handler.py      # Helpers for storing data
│   └── __init__.py
├── config/
│   ├── manager.py           # Load/save configuration files
│   ├── validator.py         # Simple input validators
│   └── __init__.py
└── utils/
    ├── helpers.py           # Miscellaneous helper functions
    └── __init__.py
```

Run the application via:

```bash
python -m keithley_measurement_app.main
```
