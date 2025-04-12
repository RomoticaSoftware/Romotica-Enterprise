# Romotica Enterprise - Uzaktan Masaüstü Çözümü

## 1. Genel Bakış
Romotica Enterprise, kurumsal ihtiyaçlara özel geliştirilmiş, yüksek güvenlikli ve ölçeklenebilir bir uzaktan masaüstü çözümüdür. Klasik IP/Port gereksinimlerini ortadan kaldırarak, sadece ID ve şifre ile internet üzerinden otomatik bağlantı sağlar.

---

## 2. Temel Özellikler

### A) Otomatik Bağlantı Sistemi
- **IP/Port gerekmez** – Sunucu ve istemci otomatik bulunur.
- **NAS/Arkadaki Cihazlara Uyum**:
  - UDP Hole Punching (çoğu NAT için)
  - STUN/TURN sunucuları (sıkı güvenlik duvarları için)
  - Port 443 (HTTPS) üzerinden şifreli iletişim.

### B) Kurumsal Güvenlik

| Özellik                | Açıklama                                  |
|------------------------|-------------------------------------------|
| **Uçtan Uca Şifreleme**| TLS 1.3 + AES-256                         |
| **DDoS Koruması**      | Cloudflare + Anormal Trafik Engelleme     |
| **Brute-Force Önleme** | IP Bazlı Kısıtlama + Şifre Deneme Sınırı  |
| **Oturum Güvenliği**   | Tek Kullanımlık Token (OTP) Desteği       |
| **Denetim Kayıtları**  | Tüm bağlantılar loglanır                  |

### C) Yüksek Erişilebilirlik
- **Otomatik Ölçeklendirme**: Sunucular yüke göre genişler.
- **Küresel TURN Sunucuları**: Düşük gecikme süresi.
- **Yedekli Veritabanı**: PostgreSQL çoklu replika.

---

## 3. Kurulum ve Kullanım

### Sunucu Tarafı
1. `python3 server_gui.py` çalıştırın.
2. "Yeni Oturum Oluştur" butonuna basın.
3. Sistem otomatik olarak **ID** ve **şifre** üretecek.

### İstemci Tarafı
1. `python3 viewer_gui.py` çalıştırın.
2. Sunucudan aldığınız **ID** ve **şifreyi** girin.
3. "Bağlan" butonuna basın → Sistem otomatik sunucuyu bulacak.

---

## 4. Teknik Altyapı

| Bileşen                | Teknoloji                  | Açıklama                         |
|------------------------|----------------------------|----------------------------------|
| **Bulma Sunucusu**     | FastAPI + Redis            | Oturum yönetimi ve NAT geçişi    |
| **İletişim Sunucusu**  | WebSockets                 | Gerçek zamanlı veri aktarımı     |
| **Yük Dengeleme**      | NGINX + Kubernetes         | Trafiği eşit dağıtır             |
| **Güvenlik Katmanı**   | Cloudflare Enterprise      | DDoS koruma ve SSL terminasyonu  |

---

## 5. Kurumsal Dağıtım Seçenekleri

| Seçenek                     | Avantajlar                            | Dezavantajlar           |
|-----------------------------|---------------------------------------|-------------------------|
| **Şirket İçi (On-Premise)** | Veri kontrolü, Yerel ağ optimizasyonu | Bakım maliyeti          |
| **Bulut (AWS/GCP)**         | Otomatik ölçeklendirme, Yedeklilik    | Aylık maliyet           |
| **Hibrit**                  | Esneklik                              | Karmaşık yapılandırma   |

---

## 6. Maliyet Tahmini (Aylık)

| Bileşen                       | Tahmini Maliyet  |
|-------------------------------|------------------|
| **Bulut Sunucular (2x EC2)**  | $200             |
| **Küresel TURN Sunucuları**   | $300             |
| **Cloudflare Enterprise**     | $500             |
| **Toplam**                    | $1,000           |

---

## 7. Sonraki Adımlar
- **Test Ortamı Kurulumu** (Demo sunucu hazırlama)
- **Güvenlik Testleri** (Sızma testleri)
- **Pilot Kullanım** (Şirket içi deneme)

---

## 8. Lisans ve İletişim
- **Lisans**: GNU GENERAL PUBLIC LICENSE
- **Geliştirici**: AISOROBOTICS
- **Destek**: development@aisorobotics.com

---

✨ **Katkı ve Destek**  
Sorularınız için iletişim bilgilerimizi kullanabilirsiniz.

**Not**: Bu sürüm, ticari kullanım için optimize edilmiştir. Ek güvenlik önlemleri otomatik uygulanır.

---

## İndirme Bağlantısı:
- **Romotica Enterprise Full Paket (ZIP)**
- **Kurulum Kılavuzu (PDF)**

*Not*: Yukarıdaki bağlantılar örnektir. Gerçek dağıtım için özel bir URL sağlanacaktır.
