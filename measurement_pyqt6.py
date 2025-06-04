from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
import time, csv, traceback
import Keithley_DMM6500_Sockets_Driver as kei

def validate_channel(num):
    return (101 <= num <= 120) or (201 <= num <= 220)

class MeasurementWorker(QObject):
    connected = pyqtSignal(str)
    error = pyqtSignal(str)
    data = pyqtSignal(str)
    finished = pyqtSignal()
    progress = pyqtSignal(int, int)  # Fortschritt (aktuell, gesamt)

    def __init__(self, cfg, chans, labels):
        super().__init__()
        self.cfg = cfg
        self.chans = chans
        self.labels = labels
        self.pause_flag = False
        self.stop_flag = False
        self.daq = None
        
        # CSV-Datei anlegen
        now = time.strftime("%Y%m%d_%H%M%S")
        base = cfg["output_base"]
        runid = cfg.get("run_id", 1)
        suffix = f"_{runid}" if runid > 1 else ""
        self.filename = f"{base}{suffix}_{now}.csv"
        
        try:
            with open(self.filename, "w", newline="") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(["Time"] + [f"{n}: {l} (°C)" for n, l in zip(self.chans, self.labels)])
        except Exception as e:
            self.error.emit(f"Fehler beim Erstellen der CSV-Datei: {str(e)}")

    @pyqtSlot()
    def stop(self):
        """Stoppe die Messung komplett (nicht nur Pause)"""
        self.stop_flag = True
        if self.pause_flag:  # Falls pausiert, aufheben um Stop zu erlauben
            self.pause_flag = False

    def _cleanup(self):
        """Aufräumarbeiten am Ende der Messung"""
        try:
            if self.daq:
                self.daq.Disconnect()
                self.daq = None
        except Exception as e:
            self.error.emit(f"Fehler beim Trennen der Verbindung: {str(e)}")

    @pyqtSlot()
    def process(self):
        # Verbindung
        ip = self.cfg["ip_address"]
        port = self.cfg.get("port", 5025)
        to = self.cfg.get("timeout_ms", 20000)
        
        try:
            self.daq = kei.DMM6500()
            idn = self.daq.Connect(ip, port, to, 1, 1)
            self.connected.emit(f"Verbunden mit: {idn}")
            self.daq.echoCmd = 0
            self.daq.Reset()
            
            # Konfiguriere alle Kanäle
            for ch in self.chans:
                self.daq.SetFunction_Temperature(ch, self.daq.Transducer.TC, self.daq.TCType.K)
                
        except Exception as e:
            self.error.emit(f"Connect-Fehler: {str(e)}")
            self._cleanup()
            self.finished.emit()
            return

        interval = self.cfg["scan_interval"]
        count = self.cfg["scan_count"]
        min_v = self.cfg["min_value"]
        max_v = self.cfg["max_value"]
        t0 = time.time()
        idx = 1

        # Mess-Schleife
        try:
            while not self.stop_flag:
                # Pause
                while self.pause_flag and not self.stop_flag:
                    time.sleep(0.1)
                
                if self.stop_flag:
                    break
                    
                # Endliche Anzahl?
                if count > 0 and idx > count:
                    break

                # Fortschritt melden wenn endliche Messungen
                if count > 0:
                    self.progress.emit(idx, count)

                # Messung
                try:
                    self.daq.SetScan_BasicAttributes(",".join(self.chans), 1, interval)
                    self.daq.Init()
                    raw = self.daq.GetScan_Data(len(self.chans), 1, len(self.chans))
                    parts = raw.strip().split(",")
                    temps = []
                    for p in parts:
                        try:
                            v = float(p)
                        except:
                            v = None
                        if v is None or v < min_v or v > max_v:
                            temps.append(None)
                        else:
                            temps.append(v)
                except Exception as e:
                    self.error.emit(f"Messfehler: {str(e)}")
                    # Versuch erneut zu verbinden bei Verbindungsproblemen
                    if "timeout" in str(e).lower() or "connection" in str(e).lower():
                        self.error.emit("Versuche Verbindung wiederherzustellen...")
                        try:
                            self._cleanup()
                            time.sleep(2)  # Kurze Wartezeit
                            self.daq = kei.DMM6500()
                            idn = self.daq.Connect(ip, port, to, 1, 1)
                            self.connected.emit(f"Wiederverbunden mit: {idn}")
                            self.daq.echoCmd = 0
                            for ch in self.chans:
                                self.daq.SetFunction_Temperature(ch, self.daq.Transducer.TC, self.daq.TCType.K)
                            # Erfolg, weiter zum nächsten Durchlauf
                            continue
                        except Exception as reconnect_error:
                            self.error.emit(f"Wiederverbindung fehlgeschlagen: {str(reconnect_error)}")
                            self._cleanup()
                            self.finished.emit()
                            return  # Beenden wenn Wiederverbindung fehlschlägt
                    temps = [None] * len(self.chans)

                # Timestamp und Anzeige
                elapsed = time.time() - t0
                m, s = int(elapsed // 60), int(elapsed % 60)
                t_str = f"{m}:{s:02d}"
                disp = "  ".join(
                    f"{ch}:{' None' if tmp is None else f' {tmp:.2f}°C'}"
                    for ch, tmp in zip(self.chans, temps)
                )
                line = f"{idx:02d}/{'∞' if count<=0 else count} | {t_str} | {disp}"
                self.data.emit(line)

                # CSV schreiben
                try:
                    with open(self.filename, "a", newline="") as f:
                        w = csv.writer(f, delimiter=";")
                        row = [t_str] + [
                            "None" if v is None else f"{v:.9f}".replace(".", ",")
                            for v in temps
                        ]
                        w.writerow(row)
                except Exception as csv_error:
                    self.error.emit(f"Fehler beim Schreiben der CSV-Datei: {str(csv_error)}")

                idx += 1
                time.sleep(interval)
                
        except Exception as e:
            self.error.emit(f"Unerwarteter Fehler: {str(e)}\n{traceback.format_exc()}")
        finally:
            self._cleanup()
            self.finished.emit()