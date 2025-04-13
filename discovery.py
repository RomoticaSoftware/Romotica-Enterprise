# Merkezi Sunucu 
import asyncio
import json
from collections import defaultdict

class DiscoveryServer:
    def __init__(self):
        self.sessions = defaultdict(dict)
        
    async def handle_client(self, websocket):
        async for message in websocket:
            data = json.loads(message)
            if data['type'] == 'register':
                self.sessions[data['session_id']] = {
                    'websocket': websocket,
                    'ip': websocket.remote_address[0],
                    'port': data['port'],
                    'password': data['password']
                }
            elif data['type'] == 'connect':
                target = self.sessions.get(data['session_id'])
                if target and target['password'] == data['password']:
                    # İstemciye hedef bilgilerini gönder
                    await websocket.send(json.dumps({
                        'ip': target['ip'],
                        'port': target['port']
                    }))
