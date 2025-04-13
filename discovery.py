# discovery_server.py
import asyncio
import json
import logging
import ssl
import os
import subprocess
import socket
from collections import defaultdict
import websockets
import hashlib
from datetime import datetime, timedelta

# Loglama ayarları
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discovery')

class DiscoveryServer:
    def __init__(self, port=8443):
        self.sessions = defaultdict(dict)
        self.connection_stats = {
            'total_connections': 0,
            'active_connections': 0
        }
        self.port = port
        self.ssl_context = self._create_ssl_context()
        self.session_timeout = timedelta(minutes=30)

    def _is_port_available(self, port):
        """Portun kullanılabilir olup olmadığını kontrol eder"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) != 0

    def _find_available_port(self, start_port):
        """Kullanılabilir bir port bulur"""
        port = start_port
        while port < 65535:
            if self._is_port_available(port):
                return port
            port += 1
        raise RuntimeError("Kullanılabilir port bulunamadı")

    def _create_ssl_context(self):
        """SSL bağlamı oluşturur"""
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        cert_file = 'discovery_cert.pem'
        key_file = 'discovery_key.pem'
        
        if not os.path.exists(cert_file) or not os.path.exists(key_file):
            logger.info("SSL sertifikaları oluşturuluyor...")
            self._generate_self_signed_cert(cert_file, key_file)
        
        try:
            context.load_cert_chain(cert_file, key_file)
            return context
        except Exception as e:
            logger.error(f"SSL bağlamı oluşturulamadı: {str(e)}")
            return None

    def _generate_self_signed_cert(self, cert_file, key_file):
        """Daha geçerli sertifika oluşturma"""
        try:
            subprocess.run([
                'openssl', 'req', '-x509', '-newkey', 'rsa:4096',
                '-keyout', key_file, '-out', cert_file,
                '-days', '3650',  # 10 yıl geçerlilik
                '-nodes', '-subj', '/CN=romotica.local',
                '-addext', 'subjectAltName=DNS:localhost,DNS:romotica.local,IP:127.0.0.1'
            ], check=True)
            
            logger.info("Gelişmiş SSL sertifikaları oluşturuldu")
        except subprocess.CalledProcessError as e:
            logger.error(f"Sertifika oluşturma hatası: {str(e)}")

    async def handle_client(self, websocket, path):
        client_ip = websocket.remote_address[0]
        logger.info(f"Yeni bağlantı: {client_ip}")
        self.connection_stats['total_connections'] += 1
        self.connection_stats['active_connections'] += 1

        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    logger.debug(f"Alınan mesaj: {data}")

                    if data['type'] == 'register':
                        await self._handle_register(websocket, data, client_ip)
                    elif data['type'] == 'connect':
                        await self._handle_connect(websocket, data)
                    elif data['type'] == 'heartbeat':
                        await self._handle_heartbeat(data['session_id'])
                    elif data['type'] == 'stats':
                        await self._send_stats(websocket)
                    else:
                        await websocket.send(json.dumps({
                            'error': 'invalid_message_type',
                            'message': 'Geçersiz mesaj türü'
                        }))

                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        'error': 'invalid_json',
                        'message': 'Geçersiz JSON formatı'
                    }))
                except KeyError as e:
                    await websocket.send(json.dumps({
                        'error': 'missing_field',
                        'message': f'Eksik alan: {str(e)}'
                    }))

        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Bağlantı kapatıldı: {client_ip}")
        finally:
            self.connection_stats['active_connections'] -= 1

    async def _handle_register(self, websocket, data, client_ip):
        """Sunucu kayıt işlemini yönetir"""
        session_id = data['session_id']
        
        # Şifreyi hash'le
        password_hash = hashlib.sha256(data['password'].encode()).hexdigest()
        
        self.sessions[session_id] = {
            'websocket': websocket,
            'ip': client_ip,
            'public_ip': data.get('public_ip', client_ip),
            'port': data['port'],
            'password_hash': password_hash,
            'ssl': data.get('ssl', True),
            'last_seen': datetime.now(),
            'nat_type': data.get('nat_type', 'unknown')
        }
        
        await websocket.send(json.dumps({
            'status': 'registered',
            'session_id': session_id,
            'timestamp': datetime.now().isoformat()
        }))
        logger.info(f"Sunucu kaydedildi: {session_id}")

    async def _handle_connect(self, websocket, data):
        """İstemci bağlantı isteğini yönetir"""
        session_id = data['session_id']
        target = self.sessions.get(session_id)
        
        if not target:
            await websocket.send(json.dumps({
                'error': 'server_not_found',
                'message': 'Sunucu bulunamadı'
            }))
            return
            
        # Şifre kontrolü
        provided_hash = hashlib.sha256(data['password'].encode()).hexdigest()
        if provided_hash != target['password_hash']:
            await websocket.send(json.dumps({
                'error': 'authentication_failed',
                'message': 'Kimlik doğrulama başarısız'
            }))
            return
            
        # Zaman aşımı kontrolü
        if datetime.now() - target['last_seen'] > self.session_timeout:
            del self.sessions[session_id]
            await websocket.send(json.dumps({
                'error': 'server_timeout',
                'message': 'Sunucu zaman aşımına uğradı'
            }))
            return
            
        # Bağlantı bilgilerini gönder
        await websocket.send(json.dumps({
            'type': 'connection_info',
            'ip': target['public_ip'],
            'port': target['port'],
            'ssl': target['ssl'],
            'nat_type': target['nat_type'],
            'timestamp': datetime.now().isoformat()
        }))
        logger.info(f"Bağlantı bilgisi gönderildi: {session_id}")

    async def _handle_heartbeat(self, session_id):
        """Sunucu canlılık sinyalini işler"""
        if session_id in self.sessions:
            self.sessions[session_id]['last_seen'] = datetime.now()
            logger.debug(f"Heartbeat alındı: {session_id}")

    async def _send_stats(self, websocket):
        """İstatistikleri gönderir"""
        await websocket.send(json.dumps({
            'type': 'stats',
            'total_servers': len(self.sessions),
            'total_connections': self.connection_stats['total_connections'],
            'active_connections': self.connection_stats['active_connections'],
            'timestamp': datetime.now().isoformat()
        }))

    async def cleanup_sessions(self):
        """Zaman aşımına uğramış oturumları temizler"""
        while True:
            await asyncio.sleep(60)  # Her dakika kontrol et
            now = datetime.now()
            expired = [sid for sid, session in self.sessions.items() 
                      if now - session['last_seen'] > self.session_timeout]
            
            for sid in expired:
                del self.sessions[sid]
                logger.info(f"Oturum zaman aşımı: {sid}")

async def start_server():
    # Kullanılabilir bir port bul
    try:
        port = 8443  # Varsayılan port
        server = DiscoveryServer(port)
        
        if not server._is_port_available(port):
            port = server._find_available_port(port)
            server = DiscoveryServer(port)
            logger.info(f"{port} portu kullanılıyor")
        
        if server.ssl_context is None:
            logger.error("SSL bağlamı oluşturulamadı. Sunucu başlatılamıyor.")
            return

        asyncio.create_task(server.cleanup_sessions())
        
        async with websockets.serve(
            server.handle_client,
            "0.0.0.0",
            port,
            ssl=server.ssl_context,
            ping_interval=30,
            ping_timeout=60,
            max_size=10 * 1024 * 1024
        ):
            logger.info(f"Discovery Server başlatıldı (wss://127.0.0.1:{port})")
            logger.info(f"Bağlantı için port: {port}")
            await asyncio.Future()
            
    except Exception as e:
        logger.error(f"Sunucu başlatılamadı: {str(e)}")

if __name__ == "__main__":
    # OpenSSL kontrolü
    try:
        subprocess.run(['openssl', 'version'], check=True, capture_output=True)
        asyncio.run(start_server())
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("HATA: OpenSSL kurulu değil. Lütfen önce OpenSSL'i yükleyin.")
        print("macOS/Linux için: 'openssl' paketini yükleyin")
        print("Windows için: https://slproweb.com/products/Win32OpenSSL.html")
        exit(1)
    except RuntimeError as e:
        print(f"HATA: {str(e)}")
        exit(1)