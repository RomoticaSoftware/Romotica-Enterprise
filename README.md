# Romotica

**Romotica**, güvenli ve modern bir uzak masaüstü paylaşım uygulamasıdır.  
TeamViewer benzeri işlevsellik sunar ve tamamen Python ile geliştirilmiştir.

---

## 🚀 Özellikler

- 🖥 Gerçek zamanlı ekran paylaşımı (Sunucudan istemciye)
- 🖱 Uzak fare ve klavye kontrolü (İstemciden sunucuya)
- 🔐 SSL/TLS destekli şifreli bağlantı (self-signed sertifika)
- 🖼 PyQt6 tabanlı modern grafik arayüz (GUI)
- 🪵 Canlı log görüntüleme ve `.log` dosyasına otomatik kayıt
- 🔄 Asenkron yapı sayesinde akıcı deneyim (asyncio)
- 🧪 Çoklu istemci desteği (ilk test aşamasında)

---

## 📁 Yapı

### 🖥 `server_gui.py`
- Sunucu tarafı ekran görüntüsü paylaşır
- SSL bağlantısı ile istemcileri dinler
- Gelen kontrol olaylarını işler (mouse/klavye)
- GUI üzerinden başlatılır, durdurulur, log takip edilir

### 🖥 `viewer_gui.py`
- Sunucuya bağlanarak ekran görüntüsünü canlı alır
- Klavye ve fare hareketlerini gönderir
- GUI üzerinden IP girilir, bağlantı sağlanır, loglar izlenir

---

## 🔧 Gereksinimler

```bash
pip install PyQt6 websockets pynput mss pillow pyautogui
```

> Not: `pyobjc` macOS sistemleri için otomatik yüklenir. Ek izinler gerekebilir.

---

## 🧪 Kullanım

1. `python3 server_gui.py` → Sertifika gir, “Sunucuyu Başlat”
2. `python3 viewer_gui.py` → IP gir, “Bağlan”
3. Log ekranından bağlantı durumu izlenebilir
4. Gerçek zamanlı ekran görünür, kontrol edilebilir

---

## 📦 Planlanan Özellikler

- [ ] Dosya transferi
- [ ] QR kod ile bağlantı paylaşımı
- [ ] Şifreli oturum / bağlantı kodu
- [ ] Mobil istemci desteği
- [ ] PyInstaller ile `.exe` / `.app` paketleme

---

## 📄 Lisans

MIT Lisansı
