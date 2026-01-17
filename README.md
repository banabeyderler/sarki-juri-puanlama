# 🎵 Şarkı Etkinliği – 6 Jüri Girişli Puanlama Sitesi (Streamlit)

Bu proje:
- 6 ayrı jüri girişi (DEVIL + 5 jüri)
- İzleyici modu (giriş yapmadan sadece sonuçları görür)
- Puan 1–10
- Puan girişi sağ tarafta
- **Puan silme / düzenleme sadece admin**: **𓏢 ÐEVłŁ'S✞BE¥**
- Oylama Aç/Kapat (sadece admin)
- Veriler **Google Sheets** üzerinde kalıcı tutulur (güncellemede silinmez)

## 1) GitHub’a yükleme
Repo kök dizininde şu dosyalar olacak:
- `app.py`
- `requirements.txt`
- `README.md`

## 2) Google Sheet hazırlama (kalıcı kayıt)
1. Google Drive → Yeni → Google E-Tablolar oluştur.
2. Sheet adını istediğin gibi koy.
3. Sheet URL’inden **SHEET_ID**’yi al:
   - Örnek URL: `https://docs.google.com/spreadsheets/d/<SHEET_ID>/edit#gid=0`

## 3) Google Service Account (ücretsiz)
1. Google Cloud Console → yeni proje (veya mevcut).
2. **Service Account** oluştur.
3. Bu hesap için **Key (JSON)** indir.
4. Oluşturduğun Google Sheet’i aç → Paylaş → service account email’ini **Editör** olarak ekle.

## 4) Streamlit Secrets ayarı
Streamlit Cloud → App → **Settings → Secrets**
- `secrets_template.toml` içeriğini al
- Değerleri kendi bilgilerinle doldur
- Secrets alanına yapıştır ve kaydet

## 5) Deploy
Streamlit Cloud’da:
- Repo: `banabeyderler/sarki-juri-puanlama`
- Branch: `main`
- Main file: `app.py`

## Kullanım
- Jüri giriş: sidebar’dan kullanıcı seç → şifre yaz → giriş.
- İzleyici: giriş yapmadan sadece sıralama görür.
- Admin (DEVIL / 𓢢 ÐEVłŁ'S✞BE¥):
  - Oylamayı aç/kapat
  - Yarışmacı ekle
  - Puanları düzenle/sil

> Not: Secrets ayarlanmazsa uygulama “Demo Mode” ile açılır (veriler kalıcı olmaz). Kalıcı olması için Google Sheets şart.
