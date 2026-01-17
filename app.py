import streamlit as st
import pandas as pd
from datetime import datetime
import uuid

import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Lamajör Jüri Puanlama", page_icon="🎵", layout="wide")

ADMIN_USER = "DEVIL"
ADMIN_DISPLAY = "𓏢 ÐEVłŁ'S✞BE¥"

JUDGE_DISPLAY = {
    "DEVIL": ADMIN_DISPLAY,
    "JURI1": "Jüri 1",
    "JURI2": "Jüri 2",
    "JURI3": "Jüri 3",
    "JURI4": "Jüri 4",
    "JURI5": "Jüri 5",
    "JURI6": "Jüri 6",
}

@st.cache_resource
def gs_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(st.secrets["gcp"], scopes=scopes)
    return gspread.authorize(creds)

def spreadsheet():
    return gs_client().open_by_key(st.secrets["google"]["spreadsheet_id"])

def ensure_tabs():
    sh = spreadsheet()
    titles = [w.title for w in sh.worksheets()]

    if "votes" not in titles:
        ws = sh.add_worksheet("votes", rows=5000, cols=10)
        ws.append_row(["id", "ts", "judge", "contestant", "score"])

    if "contestants" not in titles:
        ws = sh.add_worksheet("contestants", rows=500, cols=5)
        ws.append_row(["name"])
        ws.append_rows([["Yarışmacı 1"], ["Yarışmacı 2"], ["Yarışmacı 3"]])

    if "settings" not in titles:
        ws = sh.add_worksheet("settings", rows=50, cols=5)
        ws.append_row(["key", "value"])
        ws.append_row(["voting_open", "1"])              # 1 açık / 0 kapalı
        ws.append_row(["hide_judges_from_viewers", "1"]) # 1 gizle / 0 göster

def read_settings():
    ws = spreadsheet().worksheet("settings")
    rows = ws.get_all_values()
    d = {}
    for r in rows[1:]:
        if len(r) >= 2:
            d[r[0]] = r[1]
    return d

def set_setting(key: str, value: str):
    ws = spreadsheet().worksheet("settings")
    rows = ws.get_all_values()
    for i, r in enumerate(rows[1:], start=2):
        if r and r[0] == key:
            ws.update(f"B{i}", value)
            return
    ws.append_row([key, value])

def load_contestants():
    ws = spreadsheet().worksheet("contestants")
    rows = ws.get_all_values()
    if len(rows) <= 1:
        return []
    return [r[0].strip() for r in rows[1:] if r and r[0].strip()]

def add_contestant(name: str):
    name = name.strip()
    if not name:
        return
    spreadsheet().worksheet("contestants").append_row([name])

def load_votes_df():
    ws = spreadsheet().worksheet("votes")
    rows = ws.get_all_values()
    if len(rows) <= 1:
        return pd.DataFrame(columns=["id", "ts", "judge", "contestant", "score"])
    df = pd.DataFrame(rows[1:], columns=rows[0])
    df["score"] = pd.to_numeric(df["score"], errors="coerce")
    return df

def append_or_update_vote(judge: str, contestant: str, score: int):
    ws = spreadsheet().worksheet("votes")
    rows = ws.get_all_values()
    if len(rows) <= 1:
        ws.append_row(["id", "ts", "judge", "contestant", "score"])
        rows = ws.get_all_values()

    header = rows[0]
    data = rows[1:]

    # sütunlar
    id_i = header.index("id")
    ts_i = header.index("ts")
    judge_i = header.index("judge")
    cont_i = header.index("contestant")
    score_i = header.index("score")

    # update varsa güncelle
    for row_idx, r in enumerate(data, start=2):
        if len(r) > max(judge_i, cont_i) and r[judge_i] == judge and r[cont_i] == contestant:
            def col(n): return chr(ord("A") + n)
            ws.update(f"{col(score_i)}{row_idx}", str(int(score)))
            ws.update(f"{col(ts_i)}{row_idx}", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            return "update"

    # yoksa ekle
    ws.append_row([
        str(uuid.uuid4()),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        judge,
        contestant,
        int(score)
    ])
    return "insert"

def admin_delete_votes_for_contestant(contestant: str) -> int:
    ws = spreadsheet().worksheet("votes")
    rows = ws.get_all_values()
    if len(rows) <= 1:
        return 0
    header = rows[0]
    cont_i = header.index("contestant")

    delete_rows = []
    for idx, r in enumerate(rows[1:], start=2):
        if len(r) > cont_i and r[cont_i] == contestant:
            delete_rows.append(idx)

    for rn in sorted(delete_rows, reverse=True):
        ws.delete_rows(rn)
    return len(delete_rows)

def admin_reset_all_votes():
    ws = spreadsheet().worksheet("votes")
    ws.clear()
    ws.append_row(["id", "ts", "judge", "contestant", "score"])

# --- start ---
ensure_tabs()
settings = read_settings()
voting_open = settings.get("voting_open", "1") == "1"
hide_judges = settings.get("hide_judges_from_viewers", "1") == "1"

# session
if "user" not in st.session_state:
    st.session_state.user = None
if "display_name" not in st.session_state:
    st.session_state.display_name = "İzleyici"

def is_admin(u): return u == ADMIN_USER

# Sidebar login
with st.sidebar:
    st.header("🔐 Giriş")
    if st.session_state.user is None:
        u = st.selectbox("Kullanıcı", list(st.secrets["judges"].keys()))
        p = st.text_input("Şifre", type="password")
        if st.button("Giriş Yap"):
            if str(st.secrets["judges"][u]) == str(p):
                st.session_state.user = u
                st.session_state.display_name = JUDGE_DISPLAY.get(u, u)
                st.success(f"Giriş: {st.session_state.display_name}")
                st.rerun()
            else:
                st.error("Şifre yanlış")
        st.caption("Giriş yapmazsan izleyici olarak sonuçları görürsün.")
    else:
        st.success(f"Giriş: {st.session_state.display_name}")
        if st.button("Çıkış Yap"):
            st.session_state.user = None
            st.session_state.display_name = "İzleyici"
            st.rerun()

st.title("🎵 Lamajör Jüri Puanlama Sistemi")

user = st.session_state.user

left, right = st.columns([2, 1], gap="large")

# LEFT: results
with left:
    st.subheader("📊 Canlı Sıralama")
    votes_df = load_votes_df()

    if votes_df.empty:
        st.info("Henüz oy yok.")
    else:
        show_df = votes_df.copy()
        if user is None and hide_judges:
            show_df["judge"] = "Jüri"

        agg = votes_df.groupby("contestant", as_index=False).agg(
            total_score=("score", "sum"),
            avg_score=("score", "mean"),
            vote_count=("score", "count")
        )
        agg = agg.sort_values(["total_score", "avg_score", "vote_count"], ascending=[False, False, False]).reset_index(drop=True)
        agg.insert(0, "rank", range(1, len(agg) + 1))
        st.dataframe(agg, use_container_width=True)

        with st.expander("🧾 Tüm Oylar (detay)"):
            st.dataframe(show_df.sort_values("ts", ascending=False), use_container_width=True)

# RIGHT: scoring panel
with right:
    st.subheader("🎤 Puan Paneli")
    contestants = load_contestants()

    if user is None:
        st.info("İzleyicisin. Puan vermek için giriş yap.")
    else:
        if (not voting_open) and (not is_admin(user)):
            st.warning("Oylama şu an kapalı. Admin açınca puan verebilirsin.")
        else:
            if not contestants:
                st.warning("Yarışmacı yok. Admin ekleyebilir.")
            else:
                c = st.selectbox("Yarışmacı", contestants)
                s = st.radio("Puan", list(range(1, 11)), horizontal=True)
                if st.button("✅ Puanı Kaydet / Güncelle"):
                    action = append_or_update_vote(user, c, int(s))
                    st.success("Puan kaydedildi ✅" if action == "insert" else "Puan güncellendi ✅")
                    st.rerun()

# Admin panel
if is_admin(user):
    st.divider()
    st.subheader("👑 Admin Paneli")

    a1, a2, a3 = st.columns(3)

    with a1:
        st.write("**Oylama Durumu**")
        open_val = st.toggle("Oylama Açık", value=voting_open)
        if st.button("Kaydet (Oylama)"):
            set_setting("voting_open", "1" if open_val else "0")
            st.success("Kaydedildi.")
            st.rerun()

    with a2:
        st.write("**İzleyicide jüri isimleri**")
        hide_val = st.toggle("İzleyicide gizle", value=hide_judges)
        if st.button("Kaydet (Gizlilik)"):
            set_setting("hide_judges_from_viewers", "1" if hide_val else "0")
            st.success("Kaydedildi.")
            st.rerun()

    with a3:
        st.write("**Yarışmacı Ekle**")
        new_name = st.text_input("Yeni yarışmacı adı")
        if st.button("➕ Ekle"):
            add_contestant(new_name)
            st.success("Yarışmacı eklendi.")
            st.rerun()

    st.markdown("### 🗑️ Puan Silme (Sadece Admin)")
    contestants = load_contestants()
    if contestants:
        del_c = st.selectbox("Puanları silinecek yarışmacı", contestants)
        if st.button("Bu yarışmacının TÜM puanlarını sil"):
            n = admin_delete_votes_for_contestant(del_c)
            st.success(f"{n} oy satırı silindi.")
            st.rerun()

    st.markdown("### ⚠️ Tüm oyları sıfırla")
    if st.button("TÜM OYLARI SIFIRLA (geri dönüş yok)"):
        admin_reset_all_votes()
        st.success("Tüm oylar sıfırlandı.")
        st.rerun()
