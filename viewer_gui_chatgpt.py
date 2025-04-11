import sys
import asyncio
import base64
import json
import ssl
import io
import logging
from datetime import datetime
from typing import Optional

from PyQt6 import QtWidgets, QtGui, QtCore
from PyQt6.QtCore import pyqtSignal, QObject, QTimer
import websockets
from PIL import Image, ImageQt

# Log ayarları
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('romotica_client.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('romotica.client')

class QtAsyncioBridge(QObject):
    def __init__(self):
        super().__init__()
        self.loop = asyncio.new_event_loop()
        
    def run_forever(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

class ViewerApp(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.setup_connections()
        
        # Asyncio bridge
        self.bridge = QtAsyncioBridge()
        self.bridge_thread = QtCore.QThread()
        self.bridge.moveToThread(self.bridge_thread)
        self.bridge_thread.started.connect(self.bridge.run_forever)
        self.bridge_thread.start()

    def setup_ui(self):
        self.setWindowTitle("Romotica Client")
        self.setGeometry(100, 100, 800, 600)
        
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QVBoxLayout(central_widget)
        
        # Connection controls
        self.input_url = QtWidgets.QLineEdit("wss://127.0.0.1:8765")
        self.btn_connect = QtWidgets.QPushButton("Connect")
        self.btn_disconnect = QtWidgets.QPushButton("Disconnect", enabled=False)
        
        connection_layout = QtWidgets.QHBoxLayout()
        connection_layout.addWidget(self.input_url)
        connection_layout.addWidget(self.btn_connect)
        connection_layout.addWidget(self.btn_disconnect)
        layout.addLayout(connection_layout)
        
        # Image display
        self.image_label = QtWidgets.QLabel()
        self.image_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background-color: black;")
        layout.addWidget(self.image_label)
        
        # Status bar
        self.status_bar = QtWidgets.QStatusBar()
        self.setStatusBar(self.status_bar)

    def setup_connections(self):
        self.btn_connect.clicked.connect(self.start_connection)
        self.btn_disconnect.clicked.connect(self.stop_connection)
        
    def start_connection(self):
        async def connect():
            try:
                logger.info("Attempting to connect...")
                ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                
                self.websocket = await websockets.connect(
                    self.input_url.text(),
                    ssl=ssl_context,
                    ping_interval=None,
                    max_size=None
                )
                logger.info("Connection established successfully.")
                await self.receive_images()
                
            except Exception as e:
                logger.error(f"Connection error: {str(e)}", exc_info=True)
                # Implement reconnect logic
                await self.reconnect()

        asyncio.run_coroutine_threadsafe(connect(), self.bridge.loop)

    async def reconnect(self):
        """Reattempt the connection with a delay."""
        logger.warning("Attempting to reconnect in 5 seconds...")
        await asyncio.sleep(5)
        await self.start_connection()

    async def receive_images(self):
        try:
            while True:
                data = await self.websocket.recv()
                self.display_image(data)
        except Exception as e:
            logger.error(f"Receive error: {str(e)}", exc_info=True)
            await self.reconnect()

    def display_image(self, data):
        try:
            img_bytes = base64.b64decode(data)
            image = Image.open(io.BytesIO(img_bytes))
            
            qt_img = ImageQt.ImageQt(image)
            pixmap = QtGui.QPixmap.fromImage(qt_img)
            
            self.image_label.setPixmap(pixmap.scaled(
                self.image_label.size(),
                QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                QtCore.Qt.TransformationMode.SmoothTransformation
            ))
            
        except Exception as e:
            logger.error(f"Image display error: {str(e)}", exc_info=True)

    def stop_connection(self):
        async def disconnect():
            await self.websocket.close()
            
        asyncio.run_coroutine_threadsafe(disconnect(), self.bridge.loop)

    def closeEvent(self, event):
        self.stop_connection()
        self.bridge.loop.call_soon_threadsafe(self.bridge.loop.stop)
        self.bridge_thread.quit()
        self.bridge_thread.wait()
        event.accept()

if __name__ == "__main__":
    # MacOS özel ayarı
    if sys.platform == "darwin":
        import ctypes
        libFoundation = ctypes.cdll.LoadLibrary('/System/Library/Frameworks/Foundation.framework/Foundation')
        
    app = QtWidgets.QApplication(sys.argv)
    window = ViewerApp()
    window.show()
    sys.exit(app.exec())
