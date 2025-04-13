import sys
import asyncio
import base64
import io
import logging
import time
import json
import os
import hashlib
import secrets
import ssl
import socket
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, 
                            QTextEdit, QLabel, QLineEdit, QVBoxLayout, 
                            QWidget, QComboBox, QHBoxLayout, QFileDialog,
                            QCheckBox)
from PyQt6.QtCore import QThread, pyqtSignal
from mss import mss
from PIL import Image
import websockets
import pyautogui

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('server')

class WebSocketServer(QThread):
    log_signal = pyqtSignal(str)
    
    def __init__(self, port, quality, resolution, compression, use_ssl=False):
        super().__init__()
        self.port = port
        self.quality = quality
        self.resolution = resolution
        self.compression = compression
        self.use_ssl = use_ssl
        self.clients = set()
        self.running = False
        self.last_image_hash = None
        self.session_id = f"{secrets.randbelow(900000000) + 100000000}"
        self.session_password = secrets.token_urlsafe(8)
        self.authenticated_clients = set()
        self.resolution_map = {
            "HD (1280x720)": (1280, 720),
            "Full HD (1920x1080)": (1920, 1080),
            "2K (2560x1440)": (2560, 1440),
            "4K (3840x2160)": (3840, 2160),
            "Ekran Çözünürlüğü": None
        }

    def is_port_in_use(self, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0

    async def handle_client(self, websocket, path):
        self.clients.add(websocket)
        remote_addr = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        logger.info(f"Yeni bağlantı: {remote_addr}")
        self.log_signal.emit(f"Yeni bağlantı: {remote_addr}")
        
        try:
            auth_data = await asyncio.wait_for(websocket.recv(), timeout=30)
            auth_info = json.loads(auth_data)
            
            if (auth_info.get('session_id') == self.session_id and 
                auth_info.get('password') == self.session_password):
                self.authenticated_clients.add(websocket)
                await websocket.send(json.dumps({'status': 'authenticated'}))
                self.log_signal.emit(f"İstemci doğrulandı: {remote_addr}")
            else:
                await websocket.send(json.dumps({'status': 'authentication_failed'}))
                await websocket.close()
                return

            with mss() as sct:
                monitor = sct.monitors[1]
                target_size = self.resolution_map.get(self.resolution)
                
                while self.running and websocket in self.authenticated_clients:
                    try:
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=0.1)
                            data = json.loads(message)
                            
                            if data.get('type') == 'mouse':
                                x, y = data['x'], data['y']
                                if data.get('click'):
                                    pyautogui.click(x, y)
                                else:
                                    pyautogui.moveTo(x, y)
                            
                            elif data.get('type') == 'keyboard':
                                pyautogui.write(data['text'])
                            
                            elif data.get('type') == 'file':
                                file_data = base64.b64decode(data['content'])
                                with open(data['name'], 'wb') as f:
                                    f.write(file_data)
                                self.log_signal.emit(f"Dosya alındı: {data['name']}")
                        except asyncio.TimeoutError:
                            pass
                        
                        screenshot = sct.grab(monitor)
                        img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
                        
                        if target_size:
                            img.thumbnail(target_size, Image.Resampling.LANCZOS)
                        
                        buffer = io.BytesIO()
                        img.save(buffer, format=self.compression, quality=self.quality)
                        encoded = base64.b64encode(buffer.getvalue()).decode('utf-8')
                        
                        await websocket.send(json.dumps({
                            'type': 'screen',
                            'data': encoded
                        }))
                        
                    except Exception as e:
                        logger.error(f"İşlem hatası: {e}")
                        break
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Bağlantı kapatıldı: {remote_addr}")
        except Exception as e:
            logger.error(f"Hata: {e}")
        finally:
            self.clients.discard(websocket)
            self.authenticated_clients.discard(websocket)

    async def run_server(self):
        self.running = True
        ssl_context = None
        
        if self.use_ssl:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            if not os.path.exists('cert.pem') or not os.path.exists('key.pem'):
                self.log_signal.emit("SSL sertifikası bulunamadı! Yeni oluşturuluyor...")
                os.system('openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes -subj "/CN=localhost"')
            ssl_context.load_cert_chain('cert.pem', 'key.pem')

        try:
            if self.is_port_in_use(self.port):
                raise OSError(f"Port {self.port} zaten kullanımda!")
                
            async with websockets.serve(
                self.handle_client,
                "0.0.0.0",
                self.port,
                ssl=ssl_context,
                ping_interval=20,
                ping_timeout=40,
                max_size=100 * 1024 * 1024
            ):
                public_ip = self.get_public_ip()
                protocol = "wss" if self.use_ssl else "ws"
                self.log_signal.emit(
                    f"Sunucu başlatıldı!\n"
                    f"Bağlantı URL: {protocol}://{public_ip}:{self.port}\n"
                    f"Session ID: {self.session_id}\n"
                    f"Şifre: {self.session_password}\n\n"
                    f"İstemcinin bağlanabilmesi için bu bilgileri paylaşın"
                )
                while self.running:
                    await asyncio.sleep(1)
        except OSError as e:
            self.log_signal.emit(f"HATA: {str(e)}")
            logger.error(f"Sunucu hatası: {str(e)}")
        except Exception as e:
            self.log_signal.emit(f"Kritik HATA: {str(e)}")
            logger.error(f"Kritik hata: {str(e)}")

    def get_public_ip(self):
        try:
            import requests
            return requests.get('https://api.ipify.org').text
        except:
            return "Dinamik IP"

    def run(self):
        asyncio.run(self.run_server())

class ServerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.server = None

    def setup_ui(self):
        self.setWindowTitle("Romotica Sunucu v9.0")
        layout = QVBoxLayout()
        
        # Port Seçimi
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("Port:"))
        self.port_combo = QComboBox()
        self.port_combo.addItems(["8080 (HTTP)", "8443 (HTTPS)", "8888 (Alternatif)"])
        port_layout.addWidget(self.port_combo)
        
        self.ssl_checkbox = QCheckBox("SSL Kullan")
        self.ssl_checkbox.setChecked(True)
        port_layout.addWidget(self.ssl_checkbox)
        layout.addLayout(port_layout)
        
        # Görüntü Ayarları
        settings_layout = QHBoxLayout()
        settings_layout.addWidget(QLabel("Çözünürlük:"))
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems([
            "HD (1280x720)",
            "Full HD (1920x1080)", 
            "2K (2560x1440)",
            "4K (3840x2160)",
            "Ekran Çözünürlüğü"
        ])
        self.resolution_combo.setCurrentIndex(1)
        settings_layout.addWidget(self.resolution_combo)
        
        settings_layout.addWidget(QLabel("Kalite:"))
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Yüksek (90)", "Orta (70)", "Düşük (50)"])
        self.quality_combo.setCurrentIndex(0)
        settings_layout.addWidget(self.quality_combo)
        
        settings_layout.addWidget(QLabel("Sıkıştırma:"))
        self.compression_combo = QComboBox()
        self.compression_combo.addItems(["WEBP", "JPEG", "PNG"])
        self.compression_combo.setCurrentIndex(0)
        settings_layout.addWidget(self.compression_combo)
        layout.addLayout(settings_layout)
        
        # Bağlantı Bilgileri
        self.info_label = QLabel("Sunucu başlatıldığında bağlantı bilgileri burada görünecek")
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)
        
        # Log Alanı
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        layout.addWidget(self.log_area)
        
        # Kontrol Butonları
        button_layout = QHBoxLayout()
        self.start_btn = QPushButton("Başlat")
        self.start_btn.clicked.connect(self.start_server)
        button_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("Durdur")
        self.stop_btn.clicked.connect(self.stop_server)
        self.stop_btn.setEnabled(False)
        button_layout.addWidget(self.stop_btn)
        
        self.copy_btn = QPushButton("Bilgileri Kopyala")
        self.copy_btn.clicked.connect(self.copy_credentials)
        self.copy_btn.setEnabled(False)
        button_layout.addWidget(self.copy_btn)
        layout.addLayout(button_layout)
        
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def start_server(self):
        port_text = self.port_combo.currentText()
        port = int(port_text.split()[0])
        use_ssl = self.ssl_checkbox.isChecked()
        quality_map = {"Yüksek (90)": 90, "Orta (70)": 70, "Düşük (50)": 50}
        quality = quality_map[self.quality_combo.currentText()]
        resolution = self.resolution_combo.currentText()
        compression = self.compression_combo.currentText()
        
        self.server = WebSocketServer(port, quality, resolution, compression, use_ssl)
        self.server.log_signal.connect(self.log_area.append)
        self.server.start()
        
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.copy_btn.setEnabled(True)
        self.log_area.append("Sunucu başlatılıyor...")

    def stop_server(self):
        if self.server:
            self.server.running = False
            self.server.quit()
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.copy_btn.setEnabled(False)
            self.info_label.setText("Sunucu durduruldu")
            self.log_area.append("Sunucu durduruldu")

    def copy_credentials(self):
        if self.server:
            clipboard = QApplication.clipboard()
            credentials = f"ID: {self.server.session_id}\nŞifre: {self.server.session_password}"
            clipboard.setText(credentials)
            self.log_area.append("Bağlantı bilgileri panoya kopyalandı")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ServerGUI()
    window.show()
    sys.exit(app.exec())
