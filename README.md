Romotica
Romotica, güvenli ve modern bir uzak masaüstü paylaşım uygulamasıdır.
TeamViewer benzeri işlevsellik sunar ve tamamen Python ile geliştirilmiştir.

🚀 Özellikler
🖥 Gerçek zamanlı ekran paylaşımı (Sunucudan istemciye)

🖱 Uzak fare ve klavye kontrolü (İstemciden sunucuya)

📁 Dosya transferi (İstemciden sunucuya)

🔐 SSL/TLS destekli şifreli bağlantı (self-signed sertifika)

🖼 PyQt6 tabanlı modern grafik arayüz (GUI)

🪵 Canlı log görüntüleme ve .log dosyasına otomatik kayıt

🔄 Asenkron yapı sayesinde akıcı deneyim (asyncio)

🧪 Çoklu istemci desteği (ilk test aşamasında)

⚙️ Çözünürlük ve kalite ayarları (HD, Full HD, 2K, 4K)

🔢 FPS takibi ve performans optimizasyonu

📁 Yapı
🖥 server_gui.py
Sunucu tarafı ekran görüntüsü paylaşır

SSL bağlantısı ile istemcileri dinler

Gelen kontrol olaylarını işler (mouse/klavye/dosya)

Otomatik sertifika oluşturur (ilk çalıştırmada)

GUI üzerinden başlatılır, durdurulur, log takip edilir

Oturum ID ve şifre oluşturur

Çözünürlük ve sıkıştırma ayarları sunar

🖥 viewer_gui.py
Sunucuya bağlanarak ekran görüntüsünü canlı alır

Klavye ve fare hareketlerini gönderir

Dosya transferi yapar

GUI üzerinden IP girilir, bağlantı sağlanır, loglar izlenir

FPS takibi yapar

Bağlantı bilgilerini panoya kopyalar

🔧 Gereksinimler
bash
Copy
pip install PyQt6 websockets pynput mss pillow pyautogui requests
Notlar:

pyobjc macOS sistemleri için otomatik yüklenir. Ek izinler gerekebilir.

İlk çalıştırmada SSL sertifikası otomatik oluşturulur.

Windows'ta pyautogui için ek izinler gerekebilir.

🧪 Kullanım
Sunucu Tarafı
python3 server_gui.py komutu ile sunucuyu başlatın

Port ve SSL ayarlarını yapın (varsayılan: 8443 + SSL aktif)

"Sunucuyu Başlat" butonuna basın

Oluşturulan bağlantı bilgilerini (ID, şifre, IP) kopyalayın

İstemci Tarafı
python3 viewer_gui.py komutu ile istemciyi başlatın

Sunucu IP'sini girin (aynı makinede localhost)

Port ve SSL ayarlarını sunucuyla aynı yapın

Sunucudan aldığınız ID ve şifreyi girin

"Bağlan" butonuna basın

Ortak İşlemler
Fare hareketleri ve tıklamaları otomatik aktarılır

Klavye metin kutusuna yazıp Enter'a basarak metin gönderin

"Dosya Gönder" butonu ile dosya transferi yapın

Sunucu tarafında logları takip edin

🛠 Sorun Giderme
Bağlantı Sorunları
"nodename nor servname provided" hatası: IP adresini kontrol edin (localhost veya doğru IP)

SSL sertifika hatası: Sunucu ve istemcide SSL ayarlarını eşleştirin

Port kullanımda hatası: Farklı bir port seçin veya mevcut bağlantıyı kapatın

Performans Sorunları
Çözünürlüğü düşürün (HD -> Full HD gibi)

Sıkıştırma formatını değiştirin (WEBP -> JPEG)

Kalite ayarını düşürün (90 -> 70)

Diğer Sorunlar
Firewall'u kontrol edin (gerekli portları açın)

Python sürümünün 3.7+ olduğundan emin olun

Tüm bağımlılıkların yüklü olduğunu kontrol edin

📦 Planlanan Özellikler
Dosya transferi (v9.0 ile eklendi)

QR kod ile bağlantı paylaşımı

Şifreli oturum / bağlantı kodu

Mobil istemci desteği (Android/iOS)

PyInstaller ile .exe / .app paketleme

Ses aktarımı desteği

Çoklu monitör desteği

Oturum kayıtları (session recording)

📄 Lisans
MIT Lisansı
Geliştirici: [AISOROBOTICS]
Destek ve iletişim: [mail:development@aisorobotics.com/https://www.aisorobotics.com]

✨ Katkıda Bulunma
Hata raporları ve özellik istekleri için iletişim bilgilerini kullanabilirsiniz.

Not: Bu proje Ticari kullanımlar için geliştirilmiştir. Ek güvenlik önlemleri alınacaktır.