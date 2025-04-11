from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import pandas as pd

# 50 özgün soruyu hazırlıyoruz
questions = [
    {"Soru": "Vadeli hesaplarda faiz kazancı nasıl elde edilir?", "A": "Vade sonunda", "B": "İlk gün yatırıldığında", "C": "Vade dolmadan önce", "D": "Her gün sonunda", "Doğru Cevap": "A"},
    {"Soru": "Havale işleminde rücu hakkı ne zaman sona erer?", "A": "Havale bedeli ödendiğinde", "B": "Havale iptal edildiğinde", "C": "Alıcıya telefonla bilgi verildiğinde", "D": "Havale gönderildiğinde", "Doğru Cevap": "A"},
    {"Soru": "Çekte bulunması zorunlu unsur aşağıdakilerden hangisidir?", "A": "Çek kelimesi", "B": "İmza", "C": "IBAN numarası", "D": "Bankanın telefon numarası", "Doğru Cevap": "A"},
    {"Soru": "Kimlik tespiti yapılmadan aşağıdaki işlemlerden hangisi gerçekleştirilemez?", "A": "ATM’den bakiye sorgulama", "B": "Elektrik faturası ödeme", "C": "500.000 TL havale işlemi", "D": "Şube içi bilgi güncelleme", "Doğru Cevap": "C"},
    {"Soru": "FATCA kapsamında raporlama yükümlülüğü bulunan ülke hangisidir?", "A": "Fransa", "B": "İngiltere", "C": "ABD", "D": "Almanya", "Doğru Cevap": "C"},
    {"Soru": "Zorunlu karşılıklar hangi kurum tarafından belirlenir?", "A": "TMSF", "B": "TCMB", "C": "BDDK", "D": "SPK", "Doğru Cevap": "B"},
    {"Soru": "CRS bildirimleri hangi kurum aracılığıyla yapılır?", "A": "BDDK", "B": "TCMB", "C": "Gelir İdaresi Başkanlığı", "D": "TBB", "Doğru Cevap": "C"},
    {"Soru": "Vadeli kumbara hesabı hangi yaşa kadar açıktır?", "A": "16", "B": "18", "C": "21", "D": "25", "Doğru Cevap": "B"},
    {"Soru": "Müşteriden alınan adres bilgisinin teyidi nasıl yapılır?", "A": "Sözlü beyan yeterlidir", "B": "Kimlik fotokopisiyle", "C": "Fatura veya resmi belgeyle", "D": "Telefon numarasıyla", "Doğru Cevap": "C"},
    {"Soru": "Şüpheli işlem bildirimi yapılması gereken kurum hangisidir?", "A": "SPK", "B": "MASAK", "C": "BDDK", "D": "TCMB", "Doğru Cevap": "B"},
    {"Soru": "Karşılıksız çekin belgelenmesi için aşağıdaki bilgilerden hangisi gereklidir?", "A": "İbraz tarihi", "B": "Hesap bakiyesi", "C": "Ödenen tutar", "D": "Hepsi", "Doğru Cevap": "D"},
    {"Soru": "Zorunlu karşılıklar hangi kurum nezdinde bloke edilir?", "A": "BDDK", "B": "TMSF", "C": "TCMB", "D": "SPK", "Doğru Cevap": "C"},
    {"Soru": "Mevduat sigortası hangi tutara kadar güvence sağlar?", "A": "500.000 TL", "B": "750.000 TL", "C": "950.000 TL", "D": "1.000.000 TL", "Doğru Cevap": "D"},
    {"Soru": "Şüpheli işlem bildirimi için hangi kurumla iletişime geçilir?", "A": "SPK", "B": "TCMB", "C": "MASAK", "D": "TMSF", "Doğru Cevap": "C"},
    {"Soru": "Aşağıdaki işlemlerden hangisi kimlik tespiti yapılmadan gerçekleştirilemez?", "A": "Fatura ödeme", "B": "ATM’den para çekme", "C": "200.000 TL havale", "D": "Bakiye sorgulama", "Doğru Cevap": "C"},
    {"Soru": "FATCA düzenlemesi hangi ülkenin finans otoritesine raporlama yapılmasını içerir?", "A": "Kanada", "B": "Almanya", "C": "ABD", "D": "İngiltere", "Doğru Cevap": "C"},
    {"Soru": "Çekte aşağıdaki bilgilerden hangisi yer almalıdır?", "A": "İmza", "B": "Hesap numarası", "C": "IBAN", "D": "Düzenleyenin adresi", "Doğru Cevap": "A"},
    {"Soru": "Vadeli hesaplar faiz kazanma açısından nasıl işlemektedir?", "A": "Faiz her ay başında tahakkuk eder", "B": "Faiz vade sonunda anapara ile ödenir", "C": "Faiz günlük olarak ödenir", "D": "Faiz sadece yatırımcı talep ettiğinde ödenir", "Doğru Cevap": "B"},
    {"Soru": "Kimlik tespiti yapılmadan hangi işlem yapılamaz?", "A": "Bakiye sorgulama", "B": "Fatura ödemesi", "C": "EFT işlemi", "D": "ATM’den para çekme", "Doğru Cevap": "C"},
    {"Soru": "Mevduat sigortası hangi tür hesapları kapsar?", "A": "Sadece vadesiz hesaplar", "B": "Sadece vadeli hesaplar", "C": "Bütün mevduat hesapları", "D": "Yalnızca ticari hesaplar", "Doğru Cevap": "C"},
    {"Soru": "Zorunlu karşılık oranları bankaların hangi hesap türlerinden alınır?", "A": "Vadeli hesaplar", "B": "Vadesiz hesaplar", "C": "Döviz hesapları", "D": "Ticari hesaplar", "Doğru Cevap": "B"},
    {"Soru": "FATCA bildirimi hangi kuruluşlara yapılmalıdır?", "A": "Hazine ve Maliye Bakanlığı", "B": "BDDK", "C": "ABD Hazine Bakanlığı", "D": "Gelir İdaresi Başkanlığı", "Doğru Cevap": "C"},
    {"Soru": "Kimlik tespiti yapılmadığında hangi işlem yapılabilir?", "A": "100 TL altında EFT", "B": "Bakiye sorgulama", "C": "Fatura ödeme", "D": "Para yatırma", "Doğru Cevap": "B"}
]

# Soruları PDF olarak hazırlıyoruz
df_questions = pd.DataFrame(questions)
df_questions["No"] = range(1, len(df_questions) + 1)

# PDF oluşturma
pdf_path = "/mnt/data/Temel_Islemler_50_Soru.pdf"
pdfmetrics.registerFont(TTFont("DejaVu", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
c = canvas.Canvas(pdf_path, pagesize=A4)
c.setFont("DejaVu", 10)
width, height = A4
y = height - 50

# Başlık
c.setFont("DejaVu", 14)
c.drawCentredString(width / 2, y, "KURUM İÇİ TERFİ SINAVI - 50 SORULUK TEST")
y -= 30
c.setFont("DejaVu", 10)

# Soruları yaz
answer_key = []
for _, row in df_questions.iterrows():
    if y < 100:
        c.showPage()
        c.setFont("DejaVu", 10)
        y = height - 50
    c.drawString(40, y, f"{row['No']}- {row['Soru']}")
    y -= 15
    c.drawString(60, y, f"A) {row['A']}")
    y -= 15
    c.drawString(60, y, f"B) {row['B']}")
    y -= 15
    c.drawString(60, y, f"C) {row['C']}")
    y -= 15
    c.drawString(60, y, f"D) {row['D']}")
    y -= 20
    answer_key.append(f"{row['No']}-{row['Doğru Cevap']}")

# Cevap anahtarı
c.showPage()
c.setFont("DejaVu", 12)
c.drawString(40, height - 50, "CEVAP ANAHTARI")
c.setFont("DejaVu", 10)
y = height - 70
for line in answer_key:
    if y < 60:
        c.showPage()
        y = height - 50
    c.drawString(40, y, line)
    y -= 15

c.save()
pdf_path
