import asyncio
import base64
from PIL import Image, ImageTk
import io
import tkinter as tk
import websockets

class ScreenViewer:
    def __init__(self, root):
        self.root = root
        self.label = tk.Label(root)
        self.label.pack()

    async def update_screen(self):
        uri = "ws://<AGENT_IP>:8765"
        async with websockets.connect(uri) as websocket:
            while True:
                data = await websocket.recv()
                image_data = base64.b64decode(data)
                image = Image.open(io.BytesIO(image_data))
                photo = ImageTk.PhotoImage(image)
                self.label.config(image=photo)
                self.label.image = photo

def start_client():
    root = tk.Tk()
    root.title("Remote Screen Viewer")
    viewer = ScreenViewer(root)
    asyncio.get_event_loop().run_until_complete(viewer.update_screen())
    root.mainloop()

start_client()
