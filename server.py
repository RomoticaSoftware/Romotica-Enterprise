# server_gui.py
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
import requests
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, 
                            QTextEdit, QLabel, QLineEdit, QVBoxLayout, 
                            QWidget, QComboBox, QHBoxLayout, QFileDialog,
                            QCheckBox)
from PyQt6.QtCore import QThread, pyqtSignal, QObject
from mss import mss
from PIL import Image
import websockets
import pyautogui

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('server')

class WebSocketServer(QThread):
    log_signal = pyqtSignal(str)
    connection_signal = pyqtSignal(int)
    
    def __init__(self, port, quality, resolution, compression, use_ssl=False):
        super().__init__()
        self.port = port
        self.quality = quality
        self.resolution = resolution
        self.compression = compression
        self.use_ssl = use_ssl
        self.clients = set()
        self.running = False
        self.session_id = f"SRV_{secrets.token_hex(4).upper()}"
        self.session_password = secrets.token_urlsafe(12)
        self.authenticated_clients = set()
        self.discovery_ws = None
        self.resolution_map = {
            "HD (1280x720)": (1280, 720),
            "Full HD (1920x1080)": (1920, 1080),
            "2K (2560x1440)": (2560, 1440),
            "4K (3840x2160)": (3840, 2160),
            "Ekran Çözünürlüğü": None
        }

    async def register_with_discovery(self):
        try:
            self.discovery_ws = await websockets.connect(
                "wss://127.0.0.1:8443",     # "wss://discovery.romotica.com:443", kodun  orjinali  bu olacak siteyi  yapınca
                ssl=True,
                ping_interval=20,
                ping_timeout=40
            )
            await self.discovery_ws.send(json.dumps({
                'type': 'register',
                'server_id': self.session_id,
                'password': self.session_password,
                'public_ip': await self.get_public_ip(),
                'port': self.port,
                'ssl': self.use_ssl
            }))
            response = await self.discovery_ws.recv()
            return json.loads(response).get('status') == 'registered'
        except Exception as e:
            self.log_signal.emit(f"Discovery error: {str(e)}")
            return False

    async def handle_client(self, websocket, path):
        self.clients.add(websocket)
        self.connection_signal.emit(len(self.clients))
        remote_addr = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        logger.info(f"Yeni bağlantı: {remote_addr}")
        self.log_signal.emit(f"Yeni bağlantı: {remote_addr}")
        
        try:
            auth_data = await asyncio.wait_for(websocket.recv(), timeout=30)
            auth_info = json.loads(auth_data)
            
            if (auth_info.get('session_id') == self.session_id and 
                auth_info.get('password') == self.session_password):
                self.authenticated_clients.add(websocket)
                await websocket.send(json.dumps({
                    'status': 'authenticated',
                    'resolution': self.resolution,
                    'fps_limit': 30
                }))
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
                                filepath = os.path.join("received_files", data['name'])
                                os.makedirs("received_files", exist_ok=True)
                                with open(filepath, 'wb') as f:
                                    f.write(file_data)
                                self.log_signal.emit(f"Dosya alındı: {data['name']}")
                        except asyncio.TimeoutError:
                            pass
                        
                        start_time = time.time()
                        screenshot = sct.grab(monitor)
                        img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
                        
                        if target_size:
                            img.thumbnail(target_size, Image.Resampling.LANCZOS)
                        
                        buffer = io.BytesIO()
                        img.save(buffer, format=self.compression, quality=self.quality)
                        encoded = base64.b64encode(buffer.getvalue()).decode('utf-8')
                        
                        await websocket.send(json.dumps({
                            'type': 'screen',
                            'data': encoded,
                            'latency': int((time.time() - start_time)*1000)
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
            self.connection_signal.emit(len(self.clients))
            self.log_signal.emit(f"Bağlantı sonlandı: {remote_addr}")

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
            if not await self.register_with_discovery():
                raise ConnectionError("Discovery sunucusuna bağlanılamadı")
                
            async with websockets.serve(
                self.handle_client,
                "0.0.0.0",
                self.port,
                ssl=ssl_context,
                ping_interval=20,
                ping_timeout=40,
                max_size=100 * 1024 * 1024
            ):
                self.log_signal.emit(
                    f"Sunucu başlatıldı!\n"
                    f"Session ID: {self.session_id}\n"
                    f"Şifre: {self.session_password}\n\n"
                    f"İstemcinin bağlanabilmesi için bu bilgileri paylaşın"
                )
                while self.running:
                    await asyncio.sleep(1)
        except Exception as e:
            self.log_signal.emit(f"Sunucu hatası: {str(e)}")
            logger.error(f"Sunucu hatası: {str(e)}")
        finally:
            if self.discovery_ws:
                await self.discovery_ws.close()

    async def get_public_ip(self):
        try:
            return (await asyncio.to_thread(requests.get, 'https://api.ipify.org')).text
        except:
            return "0.0.0.0"

    def run(self):
        asyncio.run(self.run_server())

class ServerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.server = None
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Romotica Enterprise Sunucu")
        layout = QVBoxLayout()
        
        # Bağlantı Bilgileri
        self.info_label = QLabel("Sunucu başlatıldığında bağlantı bilgileri burada görünecek")
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)
        
        # Bağlantı Sayacı
        self.connection_label = QLabel("Aktif Bağlantı: 0")
        layout.addWidget(self.connection_label)
        
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
        
        # SSL Ayarları
        self.ssl_checkbox = QCheckBox("SSL Kullan (Önerilir)")
        self.ssl_checkbox.setChecked(True)
        layout.addWidget(self.ssl_checkbox)
        
        # Log Alanı
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        layout.addWidget(self.log_area)
        
        # Kontrol Butonları
        button_layout = QHBoxLayout()
        self.start_btn = QPushButton("Sunucuyu Başlat")
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
        resolution = self.resolution_combo.currentText()
        quality = {"Yüksek (90)": 90, "Orta (70)": 70, "Düşük (50)": 50}[self.quality_combo.currentText()]
        compression = self.compression_combo.currentText()
        use_ssl = self.ssl_checkbox.isChecked()
        
        self.server = WebSocketServer(443, quality, resolution, compression, use_ssl)
        self.server.log_signal.connect(self.log_area.append)
        self.server.connection_signal.connect(lambda count: self.connection_label.setText(f"Aktif Bağlantı: {count}"))
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