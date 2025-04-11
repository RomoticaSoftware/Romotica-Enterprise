import asyncio
import websockets
import base64
import io
from mss import mss
from PIL import Image

# Çoklu istemci desteği için
connected_clients = set()

async def share_screen(websocket, path):
    connected_clients.add(websocket)
    try:
        with mss() as sct:
            while True:
                screenshot = sct.grab(sct.monitors[1])
                img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG")
                encoded = base64.b64encode(buffer.getvalue()).decode('utf-8')
                # Tüm bağlı istemcilere ekran görüntüsünü gönder
                for client in connected_clients:
                    await client.send(encoded)
                await asyncio.sleep(0.2)
    except websockets.exceptions.ConnectionClosed:
        print("Bağlantı kapandı.")
    finally:
        connected_clients.remove(websocket)

async def handle_clients():
    async with websockets.serve(share_screen, "0.0.0.0", 8765):
        await asyncio.Future()  # Sonsuz bekleme

# Sunucu başlat
asyncio.run(handle_clients())
