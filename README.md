# KAMUI v3.0 Wothenza — 7/24 Ücretsiz & Kapanmayan Lisans Sunucusu

Bu klasör, lisans sistemini 7/24 online ve kesintisiz çalıştırmak için hazırlanmış 2 farklı ücretsiz seçenek sunar.

---

## ⚡ SEÇENEK 1: Cloudflare Workers (EN ÇOK ÖNERİLEN — 0 Uyku, 0 Gecikme)

Cloudflare Workers asla uykuya dalmaz (cold start 0 ms), dünya çapında 300+ veri merkezinde çalışır ve günde 100.000 isteğe kadar **tamamen ücretsizdir**.

### 1 Dakikalık Kurulum:
1. [dash.cloudflare.com](https://dash.cloudflare.com) adresine gidin (ücretsiz hesap açın).
2. Sol menüden **Workers & Pages** -> **Create application** -> **Create Worker** butonuna tıklayın.
3. İsim olarak `kamui-license` yazın ve **Deploy**'a basın.
4. Açılan sayfada **Quick Edit** butonuna tıklayın.
5. Soldaki editörün içindekileri silin ve `server/worker.js` dosyasının içeriğini **olduğu gibi yapıştırın**.
6. Sağ üstten **Save and Deploy** butonuna basın.

🎉 **Sunucunuz anında yayında!** Size verdiği link örneği:
`https://kamui-license.kullaniciadi.workers.dev`

### Web Admin Paneli:
`https://kamui-license.kullaniciadi.workers.dev/admin?pass=wothenza_admin_2026` adresine giderek:
- Tek tıkla yeni anahtarlar üretebilirsiniz.
- Müşterilerin HWID'lerini görebilir ve tek tıkla sıfırlayabilirsiniz.
- İstediğiniz anahtarı anında bloklayabilirsiniz.

---

## 🚀 SEÇENEK 2: Render.com (Flask + SQLite + Otomatik Anti-Sleep)

Render üzerinde çalıştırmak isterseniz:
1. Kodları GitHub deponuza yükleyin.
2. [render.com](https://render.com) -> **New Web Service** seçin.
3. Reponuzu bağlayın.
4. Ayarlar:
   - **Environment**: Python 3
   - **Build Command**: `pip install -r server/requirements.txt`
   - **Start Command**: `gunicorn server.app:app`
5. **Anti-Sleep Motoru**: `app.py` içinde dahili bir self-ping thread'i bulunur. Her 10 dakikada bir kendini pingleyerek Render'ın uykuya geçmesini (idle spin-down) engeller ve 7/24 aktif tutar.

---

## 📱 iOS Uygulamasına Bağlama

Sunucunuzu kurduktan sonra `src/WZSupabaseConfig.h` dosyasını açın:
```objc
#define kWZSupabaseURL @"https://kamui-license.kullaniciadi.workers.dev"
```
yazıp `python build_win.py` çalıştırın. Yeni derlenen IPA doğrudan canlı sunucunuza bağlanacaktır!

