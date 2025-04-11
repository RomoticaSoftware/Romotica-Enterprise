import asyncio
import websockets
import base64
import io
from mss import mss
from PIL import Image
import json

async def share_screen(websocket, path):
    with mss() as sct:
        while True:
            screenshot = sct.grab(sct.monitors[1])
            img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG")
            encoded = base64.b64encode(buffer.getvalue()).decode('utf-8')
            await websocket.send(encoded)
            await asyncio.sleep(0.2)

start_server = websockets.serve(share_screen, "0.0.0.0", 8765)

print("Agent çalışıyor. WebSocket 8765 portunda ekran gönderiyor...")
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
