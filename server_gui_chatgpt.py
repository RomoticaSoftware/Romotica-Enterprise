import sys
import asyncio
import base64
import io
import json
import ssl
import logging
import socket
from datetime import datetime
from typing import Set, Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QTextEdit,
    QLabel, QLineEdit, QVBoxLayout, QWidget, QMessageBox, QFileDialog
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from mss import mss
from PIL import Image
import websockets
import pyautogui

# Debug logging setup
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('romotica_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('websockets.server')
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())

class WebSocketServer(QThread):
    log_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, host: str, port: int, cert_path: str, key_path: str):
        super().__init__()
        self.host = host
        self.port = port
        self.cert_path = cert_path
        self.key_path = key_path
        self.server: Optional[websockets.WebSocketServer] = None
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.running = False
        self.ssl_context: Optional[ssl.SSLContext] = None

    def log(self, message: str):
        """Log mesajını hem GUI'ye hem de console'a yaz"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_message = f"[{timestamp}] {message}"
        self.log_signal.emit(full_message)
        logger.debug(full_message)

    def stop(self):
        """Sunucuyu güvenli şekilde durdur"""
        self.running = False
        if self.server:
            self.server.ws_server.close()
            self.log("Sunucu durduruluyor...")
            self.status_signal.emit("Sunucu durduruluyor")

    def is_port_available(self) -> bool:
        """Portun kullanılabilir olup olmadığını kontrol et"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex((self.host, self.port)) != 0

    async def handle_client(self, websocket: websockets.WebSocketServerProtocol, path: str):
        """Yeni istemci bağlantısını yönet"""
        self.clients.add(websocket)
        client_ip = websocket.remote_address[0]
        self.log(f"Yeni istemci bağlandı: {client_ip}")
        self.status_signal.emit(f"{len(self.clients)} istemci bağlı")
        
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    if data.get("type") == "input":
                        self.handle_input(data)
                    else:
                        self.log(f"Bilinmeyen mesaj türü: {data.get('type')}")
                except json.JSONDecodeError as e:
                    self.log(f"Geçersiz JSON verisi: {message[:50]}... Hata: {str(e)}")
                    
            await self.send_screenshots(websocket)
                
        except websockets.exceptions.ConnectionClosed as e:
            self.log(f"İstemci bağlantısı kesildi: {e.code} - {e.reason}")
        except Exception as e:
            error_msg = f"İstemci hatası: {type(e).__name__} - {str(e)}"
            self.error_signal.emit(error_msg)
            logger.error(error_msg, exc_info=True)
        finally:
            self.clients.discard(websocket)
            remaining = len(self.clients)
            self.status_signal.emit(f"{remaining} istemci bağlı")
            self.log(f"İstemci ayrıldı: {client_ip} (Kalan: {remaining})")

    async def send_screenshots(self, websocket: websockets.WebSocketServerProtocol):
        """Ekran görüntülerini istemciye gönder"""
        with mss() as sct:
            monitor = sct.monitors[1]  # Birincil ekran
            while self.running:
                try:
                    start_time = datetime.now()
                    
                    # Ekran görüntüsü al
                    screenshot = sct.grab(monitor)
                    capture_time = datetime.now() - start_time
                    
                    # Resmi işle
                    img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
                    img.thumbnail((800, 600), Image.Resampling.LANCZOS)
                    
                    # Base64'e kodla
                    buffer = io.BytesIO()
                    img.save(buffer, format="PNG", quality=85)
                    encoded = base64.b64encode(buffer.getvalue()).decode('utf-8')
                    
                    # İstatistikleri logla
                    size_kb = len(encoded) / 1024
                    process_time = datetime.now() - start_time - capture_time
                    
                    logger.debug(
                        f"Görüntü gönderiliyor (Boyut: {size_kb:.1f}KB, "
                        f"Yakalama: {capture_time.total_seconds():.3f}s, "
                        f"İşleme: {process_time.total_seconds():.3f}s)"
                    )
                    
                    await websocket.send(encoded)
                    await asyncio.sleep(0.1)  # FPS kontrolü
                    
                except websockets.exceptions.ConnectionClosed:
                    break
                except Exception as e:
                    error_msg = f"Ekran görüntüsü hatası: {type(e).__name__} - {str(e)}"
                    self.error_signal.emit(error_msg)
                    logger.error(error_msg, exc_info=True)
                    await asyncio.sleep(1)

    def handle_input(self, data: dict):
        """İstemciden gelen giriş olaylarını işle"""
        try:
            event_type = data["event"]
            if event_type == "mouse_move":
                pyautogui.moveTo(data["x"], data["y"])
                logger.debug(f"Fare hareketi: {data['x']}, {data['y']}")
            elif event_type == "mouse_click":
                if data["pressed"]:
                    pyautogui.mouseDown(data["x"], data["y"])
                    logger.debug(f"Fare tıklandı: {data['x']}, {data['y']}")
                else:
                    pyautogui.mouseUp(data["x"], data["y"])
                    logger.debug(f"Fare bırakıldı: {data['x']}, {data['y']}")
            elif event_type == "key_press":
                pyautogui.press(data["key"])
                logger.debug(f"Tuş basıldı: {data['key']}")
        except Exception as e:
            error_msg = f"Giriş işleme hatası: {type(e).__name__} - {str(e)}"
            self.log(error_msg)
            logger.error(error_msg, exc_info=True)

    async def server_task(self):
        """Sunucu görevini çalıştır"""
        self.running = True
        try:
            # Port kontrolü
            if not self.is_port_available():
                raise OSError(f"{self.port} portu zaten kullanımda")

            # SSL bağlamı oluştur
            self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            self.ssl_context.load_cert_chain(
                certfile=self.cert_path,
                keyfile=self.key_path,
                password=None  # Şifresiz sertifika
            )
            
            self.log("SSL sertifikası yüklendi")
            self.status_signal.emit("Sunucu başlatılıyor...")
            
            # Sunucu ayarları
            server_config = {
                "host": self.host,
                "port": self.port,
                "ssl": self.ssl_context,
                "ping_interval": 10,
                "ping_timeout": 30,
                "close_timeout": 5,
                "max_size": 10 * 1024 * 1024,  # 10MB
                "logger": logger,
                "reuse_port": True
            }
            
            self.log(f"Sunucu başlatılıyor: {server_config}")
            
            async with websockets.serve(
                self.handle_client,
                **server_config
            ) as self.server:
                self.log(f"Sunucu başlatıldı: wss://{self.host}:{self.port}")
                self.status_signal.emit(f"Sunucu çalışıyor - {len(self.clients)} istemci")
                
                # Başlatma onayı
                await asyncio.sleep(1)
                self.log("Sunucu başarıyla başlatıldı ve bağlantı bekleniyor...")
                
                # Sonsuz döngü
                while self.running:
                    await asyncio.sleep(1)
                    
        except Exception as e:
            error_msg = f"Sunucu hatası: {type(e).__name__} - {str(e)}"
            self.error_signal.emit(error_msg)
            logger.critical(error_msg, exc_info=True)
        finally:
            self.running = False
            self.log("Sunucu durduruldu")

    def run(self):
        """QThread run metodu"""
        try:
            asyncio.run(self.server_task())
        except Exception as e:
            self.error_signal.emit(f"Sunucu çalıştırılamadı: {str(e)}")
            logger.critical(f"Sunucu çalıştırılamadı: {str(e)}", exc_info=True)
