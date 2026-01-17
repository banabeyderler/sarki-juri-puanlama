# 🎵 Şarkı Etkinliği — Jüri Puanlama (Streamlit)

Bu repo, **jürilerin puan girip otomatik sıralama** aldığı basit bir web sitesi (Streamlit) içerir.

## Dosyalar
- `app.py` → Uygulamanın kendisi
- `requirements.txt` → Gerekli paketler

## Streamlit Cloud'a Deploy (ücretsiz)
1. Streamlit: `share.streamlit.io` / `streamlit.io/cloud` üzerinden giriş yapın.
2. **Deploy a public app from GitHub** seçin.
3. Alanları şöyle doldurun:
   - **Repo:** `banabeyderler/sarki-juri-puanlama`
   - **Branch (Dal):** `main` (bazı repolarda `master` olabilir)
   - **Main file path:** `app.py`
4. Deploy edin. Çıkan link sizin sitenizdir: `https://....streamlit.app`

## Kullanım
1. **Ayarlar** bölümünden jürileri ve yarışmacıları ekleyin.
2. **Puan Girişi** bölümünden puan verin.
3. **Sıralama** otomatik oluşur. Kazanan en üstte görünür.
4. **Detay** kısmından tüm puanları CSV olarak indirebilirsiniz.

## Not (Veri saklama)
Ücretsiz Streamlit Cloud ortamında kalıcı veri garantisi yoktur. Bu yüzden etkinlik sonunda **CSV indirmeniz** önerilir.
