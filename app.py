import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Şarkı Jüri Puanlama", page_icon="🎵", layout="centered")

DATA_FILE = Path("data.json")


def _default_state():
    return {
        "contestants": [],
        "judges": [],
        "scores": [],  # list of dicts: {contestant, judge, score, note, ts}
    }


def load_data():
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except Exception:
            return _default_state()
    return _default_state()


def save_data(data: dict):
    # Streamlit Cloud'da bu dosya geçici olabilir ama aynı oturum içinde işe yarar.
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def ensure_state():
    if "data" not in st.session_state:
        st.session_state.data = load_data()


def normalize_name(s: str) -> str:
    return " ".join(s.strip().split())


def add_unique(lst, item):
    item = normalize_name(item)
    if not item:
        return False
    if item not in lst:
        lst.append(item)
        return True
    return False


def compute_table(data: dict):
    if not data["scores"]:
        return pd.DataFrame(columns=["Sıra", "Yarışmacı", "Toplam", "Ortalama", "Puan Sayısı"])

    df = pd.DataFrame(data["scores"])
    df["score"] = pd.to_numeric(df["score"], errors="coerce")
    df = df.dropna(subset=["score"])

    agg = (
        df.groupby("contestant")["score"]
        .agg([("Toplam", "sum"), ("Ortalama", "mean"), ("Puan Sayısı", "count")])
        .reset_index()
        .rename(columns={"contestant": "Yarışmacı"})
    )

    # Sıralama: Toplam azalan, eşitse Ortalama azalan, eşitse alfabetik
    agg = agg.sort_values(by=["Toplam", "Ortalama", "Yarışmacı"], ascending=[False, False, True]).reset_index(drop=True)
    agg.insert(0, "Sıra", range(1, len(agg) + 1))

    # Yuvarla
    agg["Ortalama"] = agg["Ortalama"].round(2)
    agg["Toplam"] = agg["Toplam"].astype(float).round(2)
    return agg


def scores_detail_df(data: dict):
    if not data["scores"]:
        return pd.DataFrame(columns=["Zaman", "Jüri", "Yarışmacı", "Puan", "Not"])
    df = pd.DataFrame(data["scores"]).copy()
    df = df.rename(columns={
        "ts": "Zaman",
        "judge": "Jüri",
        "contestant": "Yarışmacı",
        "score": "Puan",
        "note": "Not",
    })
    # Zamanı okunur yap
    try:
        df["Zaman"] = pd.to_datetime(df["Zaman"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass
    return df[["Zaman", "Jüri", "Yarışmacı", "Puan", "Not"]]


ensure_state()
data = st.session_state.data

st.title("🎵 Şarkı Etkinliği — Jüri Puanlama")
st.caption("Basit, hızlı, ücretsiz. Jüriler puan girer, sistem otomatik sıralar.")

with st.expander("⚙️ Ayarlar (Jüri & Yarışmacı listesi)", expanded=True):
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("👥 Jüriler")
        new_judge = st.text_input("Jüri adı ekle", placeholder="Örn: Jüri-1 / Azra / Safi", key="new_judge")
        if st.button("Jüri Ekle", use_container_width=True):
            if add_unique(data["judges"], new_judge):
                save_data(data)
                st.success("Jüri eklendi.")
            else:
                st.warning("Jüri adı boş ya da zaten var.")
        if data["judges"]:
            st.write("Mevcut jüriler:")
            st.write(" • " + "\n • ".join(data["judges"]))

    with col2:
        st.subheader("🎤 Yarışmacılar")
        new_cont = st.text_input("Yarışmacı adı ekle", placeholder="Örn: Ali / Ayşe", key="new_cont")
        if st.button("Yarışmacı Ekle", use_container_width=True):
            if add_unique(data["contestants"], new_cont):
                save_data(data)
                st.success("Yarışmacı eklendi.")
            else:
                st.warning("Yarışmacı adı boş ya da zaten var.")
        if data["contestants"]:
            st.write("Mevcut yarışmacılar:")
            st.write(" • " + "\n • ".join(data["contestants"]))

st.divider()

st.subheader("📝 Puan Girişi")

if not data["judges"] or not data["contestants"]:
    st.info("Önce **Ayarlar** kısmından en az 1 jüri ve 1 yarışmacı ekleyin.")
else:
    colA, colB = st.columns(2)
    with colA:
        judge = st.selectbox("Jüri", data["judges"], key="sel_judge")
    with colB:
        contestant = st.selectbox("Yarışmacı", data["contestants"], key="sel_cont")

    score = st.slider("Puan", min_value=1, max_value=10, value=8, step=1)
    note = st.text_input("Not (opsiyonel)", placeholder="Örn: Ses temiz, sahne iyi", key="note")

    colS1, colS2 = st.columns(2)
    with colS1:
        if st.button("✅ Puanı Kaydet", type="primary", use_container_width=True):
            data["scores"].append(
                {
                    "contestant": contestant,
                    "judge": judge,
                    "score": int(score),
                    "note": normalize_name(note),
                    "ts": datetime.now().isoformat(timespec="seconds"),
                }
            )
            save_data(data)
            st.success("Puan kaydedildi.")

    with colS2:
        if st.button("↩️ Son Puanı Geri Al", use_container_width=True):
            if data["scores"]:
                data["scores"].pop()
                save_data(data)
                st.warning("Son puan silindi.")
            else:
                st.info("Silinecek puan yok.")

st.divider()

st.subheader("🏆 Sıralama")
leaderboard = compute_table(data)

if leaderboard.empty:
    st.info("Henüz puan girilmedi.")
else:
    st.dataframe(leaderboard, use_container_width=True, hide_index=True)
    winner = leaderboard.iloc[0]
    st.success(f"🏆 **Kazanan:** {winner['Yarışmacı']} — Toplam: {winner['Toplam']} | Ortalama: {winner['Ortalama']}")

st.divider()

with st.expander("📋 Detay (kim kime kaç verdi)"):
    detail = scores_detail_df(data)
    st.dataframe(detail, use_container_width=True, hide_index=True)

    # CSV indir
    if not detail.empty:
        csv = detail.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Detayı CSV indir", data=csv, file_name="puanlar_detay.csv", mime="text/csv")

with st.expander("🧹 Temizlik / Sıfırlama"):
    st.caption("Dikkat: Bu işlem puanları siler.")
    colR1, colR2 = st.columns(2)
    with colR1:
        if st.button("Puanları Sıfırla", use_container_width=True):
            data["scores"] = []
            save_data(data)
            st.warning("Puanlar sıfırlandı.")
    with colR2:
        if st.button("Her Şeyi Sıfırla", use_container_width=True):
            st.session_state.data = _default_state()
            save_data(st.session_state.data)
            st.error("Jüri + yarışmacı + puanlar sıfırlandı.")

st.caption("Not: Streamlit Cloud ücretsiz planda veriler çoğu zaman oturum/instance bazlı tutulur. Resmî kayıt için CSV indirip saklayın.")
