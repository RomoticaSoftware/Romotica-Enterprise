import sys
import asyncio
import base64
import io
import logging
import time
import json
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QLabel, QLineEdit, 
                            QPushButton, QVBoxLayout, QWidget, QComboBox,
                            QHBoxLayout, QFileDialog, QMessageBox, QCheckBox)
from PyQt6.QtGui import QPixmap, QImage, QCursor
from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot, Qt
from PIL import Image
import websockets

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('client')

class AsyncClient(QObject):
    image_received = pyqtSignal(bytes)
    status_changed = pyqtSignal(str)
    fps_updated = pyqtSignal(float)
    auth_result = pyqtSignal(bool)
    
    def __init__(self):
        super().__init__()
        self.websocket = None
        self.is_connected = False
        self.is_authenticated = False
        self.loop = asyncio.new_event_loop()
        self.last_frame_time = time.time()
        self.scale_factor_x = 1
        self.scale_factor_y = 1
        self.server_ip = ""
        self.server_port = "443"
        self.use_ssl = True
        self.session_id = ""
        self.password = ""

    def start_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    async def connect(self, server_ip, server_port, use_ssl, session_id, password):
        try:
            self.status_changed.emit("Bağlanıyor...")
            self.server_ip = server_ip
            self.server_port = server_port
            self.use_ssl = use_ssl
            self.session_id = session_id
            self.password = password
            
            protocol = "wss" if self.use_ssl else "ws"
            uri = f"{protocol}://{self.server_ip}:{self.server_port}"
            
            self.websocket = await websockets.connect(
                uri,
                ping_interval=20,
                ping_timeout=40,
                close_timeout=1,
                max_size=100 * 1024 * 1024,
                ssl=None if not self.use_ssl else True
            )
            
            auth_data = {
                'session_id': self.session_id,
                'password': self.password
            }
            await self.websocket.send(json.dumps(auth_data))
            
            response = await asyncio.wait_for(self.websocket.recv(), timeout=10)
            response_data = json.loads(response)
            
            if response_data.get('status') == 'authenticated':
                self.is_connected = True
                self.is_authenticated = True
                self.status_changed.emit("Bağlantı kuruldu - Kimlik doğrulandı")
                self.auth_result.emit(True)
                
                while self.is_connected and self.is_authenticated:
                    try:
                        message = await self.websocket.recv()
                        data = json.loads(message)
                        
                        if data.get('type') == 'screen':
                            current_time = time.time()
                            fps = 1 / (current_time - self.last_frame_time)
                            self.last_frame_time = current_time
                            self.fps_updated.emit(fps)
                            self.image_received.emit(data['data'].encode('utf-8'))
                            
                    except websockets.exceptions.ConnectionClosed as e:
                        logger.error(f"Bağlantı kapatıldı: {e.code} - {e.reason}")
                        break
                    except Exception as e:
                        logger.error(f"Veri alma hatası: {str(e)}")
                        break
            else:
                self.status_changed.emit("Kimlik doğrulama başarısız")
                self.auth_result.emit(False)
                await self.websocket.close()
                
        except asyncio.TimeoutError:
            self.status_changed.emit("Bağlantı zaman aşımına uğradı")
            self.auth_result.emit(False)
        except Exception as e:
            self.status_changed.emit(f"Hata: {str(e)}")
            logger.error(f"Bağlantı hatası: {str(e)}")
            self.auth_result.emit(False)
        finally:
            self.is_connected = False
            self.is_authenticated = False
            if self.websocket:
                await self.websocket.close()
            self.status_changed.emit("Bağlantı kesildi")

    async def send_mouse_event(self, x, y, click=False):
        if self.is_authenticated:
            message = {
                'type': 'mouse',
                'x': int(x),
                'y': int(y),
                'click': click
            }
            await self.websocket.send(json.dumps(message))

    async def send_key_event(self, text):
        if self.is_authenticated:
            message = {
                'type': 'keyboard',
                'text': text
            }
            await self.websocket.send(json.dumps(message))

    async def send_file(self, filepath):
        if self.is_authenticated:
            try:
                with open(filepath, 'rb') as f:
                    content = base64.b64encode(f.read()).decode('utf-8')
                
                message = {
                    'type': 'file',
                    'name': os.path.basename(filepath),
                    'content': content
                }
                await self.websocket.send(json.dumps(message))
                return True
            except Exception as e:
                logger.error(f"Dosya gönderilemedi: {str(e)}")
                return False

    async def disconnect(self):
        if self.websocket:
            await self.websocket.close()
        self.is_connected = False
        self.is_authenticated = False

class ViewerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.client = AsyncClient()
        self.setup_ui()
        self.setup_client()

    def setup_ui(self):
        self.setWindowTitle("Romotica İstemci v8.0 (Port 80/443 Desteği)")
        layout = QVBoxLayout()
        
        # Sunucu Bilgileri
        server_layout = QHBoxLayout()
        server_layout.addWidget(QLabel("Sunucu IP/Domain:"))
        self.server_input = QLineEdit()
        self.server_input.setPlaceholderText("örn: example.com veya 123.123.123.123")
        server_layout.addWidget(self.server_input)
        layout.addLayout(server_layout)
        
        # Port ve SSL Ayarları
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("Port:"))
        self.port_combo = QComboBox()
        self.port_combo.addItems(["443 (HTTPS)", "80 (HTTP)"])
        port_layout.addWidget(self.port_combo)
        
        self.ssl_checkbox = QCheckBox("SSL Kullan")
        self.ssl_checkbox.setChecked(True)
        port_layout.addWidget(self.ssl_checkbox)
        layout.addLayout(port_layout)
        
        # Kimlik Bilgileri
        auth_layout = QHBoxLayout()
        auth_layout.addWidget(QLabel("Session ID:"))
        self.id_input = QLineEdit()
        self.id_input.setPlaceholderText("9 haneli ID")
        auth_layout.addWidget(self.id_input)
        layout.addLayout(auth_layout)
        
        pass_layout = QHBoxLayout()
        pass_layout.addWidget(QLabel("Şifre:"))
        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Sunucu şifresi")
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        pass_layout.addWidget(self.pass_input)
        layout.addLayout(pass_layout)
        
        # Bağlantı Butonu
        self.connect_btn = QPushButton("Bağlan")
        self.connect_btn.clicked.connect(self.toggle_connection)
        layout.addWidget(self.connect_btn)
        
        # Durum Bilgisi
        self.status_label = QLabel("Durum: Bağlantı yok")
        layout.addWidget(self.status_label)
        
        self.fps_label = QLabel("FPS: -")
        layout.addWidget(self.fps_label)
        
        # Görüntü Alanı
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setFixedSize(800, 450)
        self.image_label.setStyleSheet("background-color: black;")
        self.image_label.setMouseTracking(True)
        layout.addWidget(self.image_label)
        
        # Kontroller
        control_layout = QHBoxLayout()
        self.keyboard_input = QLineEdit()
        self.keyboard_input.setPlaceholderText("Metin yazın ve Enter'a basın...")
        self.keyboard_input.returnPressed.connect(self.send_text)
        control_layout.addWidget(self.keyboard_input)
        
        self.file_btn = QPushButton("Dosya Gönder")
        self.file_btn.clicked.connect(self.send_file_dialog)
        self.file_btn.setEnabled(False)
        control_layout.addWidget(self.file_btn)
        
        layout.addLayout(control_layout)
        
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def setup_client(self):
        self.thread = QThread()
        self.client.moveToThread(self.thread)
        
        self.client.image_received.connect(self.update_image)
        self.client.status_changed.connect(self.update_status)
        self.client.fps_updated.connect(self.update_fps)
        self.client.auth_result.connect(self.handle_auth_result)
        self.thread.started.connect(self.client.start_loop)
        self.thread.start()

    @pyqtSlot(bool)
    def handle_auth_result(self, success):
        if success:
            self.file_btn.setEnabled(True)
            self.connect_btn.setText("Bağlantıyı Kes")
        else:
            self.connect_btn.setEnabled(True)
            self.connect_btn.setText("Bağlan")
            QMessageBox.warning(self, "Hata", "Kimlik doğrulama başarısız!")

    def toggle_connection(self):
        self.connect_btn.setEnabled(False)
        
        if self.client.is_connected:
            asyncio.run_coroutine_threadsafe(
                self.client.disconnect(),
                self.client.loop
            )
            self.connect_btn.setText("Bağlan")
            self.file_btn.setEnabled(False)
        else:
            server_ip = self.server_input.text().strip()
            port = "443" if self.port_combo.currentText().startswith("443") else "80"
            use_ssl = self.ssl_checkbox.isChecked()
            session_id = self.id_input.text().strip()
            password = self.pass_input.text().strip()
            
            if not (server_ip and session_id and password):
                QMessageBox.warning(self, "Hata", "Tüm alanları doldurun!")
                self.connect_btn.setEnabled(True)
                return
                
            self.connect_btn.setText("Bağlanıyor...")
            asyncio.run_coroutine_threadsafe(
                self.client.connect(server_ip, port, use_ssl, session_id, password),
                self.client.loop
            )

    def send_text(self):
        text = self.keyboard_input.text()
        if text and self.client.is_authenticated:
            asyncio.run_coroutine_threadsafe(
                self.client.send_key_event(text),
                self.client.loop
            )
            self.keyboard_input.clear()

    def send_file_dialog(self):
        if not self.client.is_authenticated:
            self.status_label.setText("Dosya göndermek için bağlantı gerekli!")
            return
        
        filepath, _ = QFileDialog.getOpenFileName(self, "Dosya Seç")
        if filepath:
            self.status_label.setText(f"Dosya gönderiliyor: {os.path.basename(filepath)}...")
            
            def callback(future):
                if future.result():
                    self.status_label.setText(f"Dosya gönderildi: {os.path.basename(filepath)}")
                else:
                    self.status_label.setText("Dosya gönderilemedi!")
            
            future = asyncio.run_coroutine_threadsafe(
                self.client.send_file(filepath),
                self.client.loop
            )
            future.add_done_callback(callback)

    def mouseMoveEvent(self, event):
        if self.client.is_authenticated and self.image_label.underMouse():
            x = event.position().x() * self.scale_factor_x
            y = event.position().y() * self.scale_factor_y
            asyncio.run_coroutine_threadsafe(
                self.client.send_mouse_event(x, y),
                self.client.loop
            )

    def mousePressEvent(self, event):
        if (event.button() == Qt.MouseButton.LeftButton and 
            self.client.is_authenticated and 
            self.image_label.underMouse()):
            
            x = event.position().x() * self.scale_factor_x
            y = event.position().y() * self.scale_factor_y
            asyncio.run_coroutine_threadsafe(
                self.client.send_mouse_event(x, y, True),
                self.client.loop
            )

    @pyqtSlot(str)
    def update_status(self, status):
        self.status_label.setText(f"Durum: {status}")

    @pyqtSlot(float)
    def update_fps(self, fps):
        self.fps_label.setText(f"FPS: {fps:.1f}")

    @pyqtSlot(bytes)
    def update_image(self, data):
        try:
            img_data = base64.b64decode(data)
            image = Image.open(io.BytesIO(img_data))
            
            self.scale_factor_x = image.width / self.image_label.width()
            self.scale_factor_y = image.height / self.image_label.height()
            
            if image.mode == "RGB":
                qformat = QImage.Format.Format_RGB888
                bytes_per_line = 3 * image.width
            else:
                qformat = QImage.Format.Format_RGBA8888
                bytes_per_line = 4 * image.width
            
            qimage = QImage(image.tobytes(), 
                          image.width, 
                          image.height,
                          bytes_per_line,
                          qformat)
            
            self.image_label.setPixmap(
                QPixmap.fromImage(qimage).scaled(
                    self.image_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            )
        except Exception as e:
            logger.error(f"Görüntü işleme hatası: {str(e)}")

    def closeEvent(self, event):
        if self.client.is_connected:
            asyncio.run_coroutine_threadsafe(
                self.client.disconnect(),
                self.client.loop
            )
        
        if self.client.loop and not self.client.loop.is_closed():
            self.client.loop.call_soon_threadsafe(self.client.loop.stop)
        
        self.thread.quit()
        self.thread.wait()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    if sys.platform == 'darwin':
        try:
            app.setHighDpiScaleFactorRoundingPolicy(
                Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
            )
        except AttributeError:
            pass
    
    window = ViewerApp()
    window.show()
    sys.exit(app.exec())