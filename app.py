import streamlit as st
import pandas as pd
from datetime import datetime
import uuid

# Optional Google Sheets
try:
    import gspread
    from google.oauth2.service_account import Credentials
except Exception:
    gspread = None
    Credentials = None

st.set_page_config(page_title="Şarkı Etkinliği Jüri Sistemi", page_icon="🎵", layout="wide")

ADMIN_USER = "DEVIL"
ADMIN_DISPLAY = "𓏢 ÐEVłŁ'S✞BE¥"

JUDGE_USERS = ["DEVIL", "JURI1", "JURI2", "JURI3", "JURI4", "JURI5"]
JUDGE_DISPLAY = {
    "DEVIL": ADMIN_DISPLAY,
    "JURI1": "Jüri 1",
    "JURI2": "Jüri 2",
    "JURI3": "Jüri 3",
    "JURI4": "Jüri 4",
    "JURI5": "Jüri 5",
}

# ----------------------------
# Auth helpers
# ----------------------------

def get_passwords():
    # Secrets varsa oradan al, yoksa demo
    if "judges" in st.secrets:
        return dict(st.secrets["judges"])
    # Demo passwords (kalıcı değil)
    return {
        "DEVIL": "devil",
        "JURI1": "1234",
        "JURI2": "1234",
        "JURI3": "1234",
        "JURI4": "1234",
        "JURI5": "1234",
    }


def check_login(username: str, password: str) -> bool:
    pw = get_passwords()
    return username in pw and str(pw[username]) == str(password)


def is_admin(user: str | None) -> bool:
    return user == ADMIN_USER


# ----------------------------
# Storage layer (Google Sheets preferred)
# ----------------------------

def secrets_ready() -> bool:
    return (
        gspread is not None
        and "SHEET_ID" in st.secrets
        and "service_account" in st.secrets
    )


@st.cache_resource
def get_gs_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds_info = dict(st.secrets["service_account"])
    creds = Credentials.from_service_account_info(creds_info, scopes=scopes)
    return gspread.authorize(creds)


def get_sheet():
    gc = get_gs_client()
    return gc.open_by_key(st.secrets["SHEET_ID"])


def ensure_worksheets():
    sh = get_sheet()
    titles = [ws.title for ws in sh.worksheets()]

    if "votes" not in titles:
        ws = sh.add_worksheet(title="votes", rows=5000, cols=10)
        ws.append_row(["id", "ts", "judge", "contestant", "score"])

    if "contestants" not in titles:
        ws = sh.add_worksheet(title="contestants", rows=500, cols=5)
        ws.append_row(["name"])
        ws.append_rows([["Yarışmacı 1"], ["Yarışmacı 2"], ["Yarışmacı 3"]])

    if "config" not in titles:
        ws = sh.add_worksheet(title="config", rows=50, cols=5)
        ws.append_row(["key", "value"])
        ws.append_row(["voting_open", "1"])  # default open


def now_ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_votes_df():
    if secrets_ready():
        sh = get_sheet()
        ws = sh.worksheet("votes")
        values = ws.get_all_values()
        if len(values) <= 1:
            return pd.DataFrame(columns=["id", "ts", "judge", "contestant", "score"])
        df = pd.DataFrame(values[1:], columns=values[0])
        if not df.empty:
            df["score"] = pd.to_numeric(df["score"], errors="coerce")
        return df

    # Demo storage
    if "votes_demo" not in st.session_state:
        st.session_state["votes_demo"] = []
    df = pd.DataFrame(st.session_state["votes_demo"], columns=["id", "ts", "judge", "contestant", "score"])
    if not df.empty:
        df["score"] = pd.to_numeric(df["score"], errors="coerce")
    return df


def load_contestants():
    if secrets_ready():
        sh = get_sheet()
        ws = sh.worksheet("contestants")
        values = ws.get_all_values()
        if len(values) <= 1:
            return []
        return [r[0].strip() for r in values[1:] if r and r[0].strip()]

    if "contestants_demo" not in st.session_state:
        st.session_state["contestants_demo"] = ["Yarışmacı 1", "Yarışmacı 2", "Yarışmacı 3"]
    return list(st.session_state["contestants_demo"])


def add_contestant(name: str):
    name = name.strip()
    if not name:
        return
    if secrets_ready():
        sh = get_sheet()
        ws = sh.worksheet("contestants")
        ws.append_row([name])
        return
    st.session_state.setdefault("contestants_demo", []).append(name)


def get_voting_open() -> bool:
    if secrets_ready():
        sh = get_sheet()
        ws = sh.worksheet("config")
        values = ws.get_all_values()
        # key/value rows
        for r in values[1:]:
            if len(r) >= 2 and r[0] == "voting_open":
                return str(r[1]).strip() == "1"
        # fallback
        ws.append_row(["voting_open", "1"])
        return True

    return st.session_state.get("voting_open_demo", True)


def set_voting_open(open_: bool):
    if secrets_ready():
        sh = get_sheet()
        ws = sh.worksheet("config")
        values = ws.get_all_values()
        # find row
        for idx, r in enumerate(values[1:], start=2):
            if len(r) >= 2 and r[0] == "voting_open":
                ws.update_cell(idx, 2, "1" if open_ else "0")
                return
        ws.append_row(["voting_open", "1" if open_ else "0"])
        return

    st.session_state["voting_open_demo"] = open_


def upsert_vote(judge: str, contestant: str, score: int):
    """One vote per judge per contestant. Updates if exists."""
    contestant = contestant.strip()
    if secrets_ready():
        sh = get_sheet()
        ws = sh.worksheet("votes")
        values = ws.get_all_values()
        if len(values) <= 1:
            # header only
            row_id = str(uuid.uuid4())
            ws.append_row([row_id, now_ts(), judge, contestant, int(score)])
            return "insert"

        header = values[0]
        rows = values[1:]
        j_col = header.index("judge")
        c_col = header.index("contestant")
        s_col = header.index("score")
        t_col = header.index("ts")

        # search for existing (first match)
        for i, r in enumerate(rows, start=2):
            if len(r) > max(j_col, c_col) and r[j_col] == judge and r[c_col] == contestant:
                # update score + ts
                ws.update_cell(i, s_col + 1, str(int(score)))
                ws.update_cell(i, t_col + 1, now_ts())
                return "update"

        row_id = str(uuid.uuid4())
        ws.append_row([row_id, now_ts(), judge, contestant, int(score)])
        return "insert"

    # Demo
    st.session_state.setdefault("votes_demo", [])
    # find
    for rec in st.session_state["votes_demo"]:
        if rec["judge"] == judge and rec["contestant"] == contestant:
            rec["score"] = int(score)
            rec["ts"] = now_ts()
            return "update"
    st.session_state["votes_demo"].append({
        "id": str(uuid.uuid4()),
        "ts": now_ts(),
        "judge": judge,
        "contestant": contestant,
        "score": int(score),
    })
    return "insert"


def admin_delete_votes(ids_to_delete: set[str]) -> int:
    if not ids_to_delete:
        return 0

    if secrets_ready():
        sh = get_sheet()
        ws = sh.worksheet("votes")
        values = ws.get_all_values()
        if len(values) <= 1:
            return 0
        header = values[0]
        rows = values[1:]
        id_col = header.index("id")
        delete_row_numbers = []
        for i, r in enumerate(rows, start=2):
            if len(r) > id_col and r[id_col] in ids_to_delete:
                delete_row_numbers.append(i)
        for rn in sorted(delete_row_numbers, reverse=True):
            ws.delete_rows(rn)
        return len(delete_row_numbers)

    # Demo
    before = len(st.session_state.get("votes_demo", []))
    st.session_state["votes_demo"] = [r for r in st.session_state.get("votes_demo", []) if r.get("id") not in ids_to_delete]
    return before - len(st.session_state["votes_demo"])


def admin_edit_vote(vote_id: str, new_score: int) -> bool:
    """Admin can edit any vote score."""
    if secrets_ready():
        sh = get_sheet()
        ws = sh.worksheet("votes")
        values = ws.get_all_values()
        if len(values) <= 1:
            return False
        header = values[0]
        rows = values[1:]
        id_col = header.index("id")
        s_col = header.index("score")
        t_col = header.index("ts")
        for i, r in enumerate(rows, start=2):
            if len(r) > id_col and r[id_col] == vote_id:
                ws.update_cell(i, s_col + 1, str(int(new_score)))
                ws.update_cell(i, t_col + 1, now_ts())
                return True
        return False

    for rec in st.session_state.get("votes_demo", []):
        if rec.get("id") == vote_id:
            rec["score"] = int(new_score)
            rec["ts"] = now_ts()
            return True
    return False


# ----------------------------
# UI
# ----------------------------

st.title("🎵 Şarkı Etkinliği – Jüri Puanlama")

if not secrets_ready():
    st.warning(
        "Şu an **Demo Mode** aktif: Google Sheets Secrets ayarlı değil. "
        "Bu modda veriler kalıcı değildir (deploy/restart olunca silinebilir).\n\n"
        "Kalıcı kayıt için `secrets_template.toml` dosyasındaki adımları uygulayıp Streamlit Secrets’i doldur."
    )
else:
    try:
        ensure_worksheets()
    except Exception as e:
        st.error("Google Sheets bağlantısında sorun var. Secrets/izinleri kontrol et.")
        st.exception(e)

# Session login
if "user" not in st.session_state:
    st.session_state["user"] = None

# Sidebar Login
with st.sidebar:
    st.header("🔐 Jüri Girişi")

    if st.session_state["user"] is None:
        u = st.selectbox("Kullanıcı", JUDGE_USERS)
        p = st.text_input("Şifre", type="password")
        if st.button("Giriş Yap"):
            if check_login(u, p):
                st.session_state["user"] = u
                st.success(f"Giriş başarılı: {JUDGE_DISPLAY.get(u,u)}")
                st.rerun()
            else:
                st.error("Kullanıcı/şifre hatalı")
        st.caption("Giriş yapmazsan izleyici olarak sadece sonuçları görürsün.")
    else:
        st.success(f"Aktif: {JUDGE_DISPLAY.get(st.session_state['user'], st.session_state['user'])}")
        if st.button("Çıkış"):
            st.session_state["user"] = None
            st.rerun()

    st.divider()
    st.subheader("Durum")
    open_ = get_voting_open()
    st.write("🟢 Oylama Açık" if open_ else "🔴 Oylama Kapalı")

    if is_admin(st.session_state["user"]):
        toggle = st.toggle("Oylamayı Aç/Kapat", value=open_)
        if toggle != open_:
            set_voting_open(toggle)
            st.rerun()

# Load data
contestants = load_contestants()
votes_df = load_votes_df()

# Layout: left results, right voting
left, right = st.columns([2, 1], gap="large")

# ----------------------------
# LEFT: Leaderboard + viewer
# ----------------------------
with left:
    st.subheader("🏆 Sıralama")

    if votes_df.empty:
        st.info("Henüz oy girilmedi.")
    else:
        # Tie-break: total desc, avg desc, count of 10s desc, name asc
        v = votes_df.dropna(subset=["score"]).copy()
        v["score"] = pd.to_numeric(v["score"], errors="coerce")

        total = v.groupby("contestant", as_index=False)["score"].sum().rename(columns={"score": "toplam"})
        avg = v.groupby("contestant", as_index=False)["score"].mean().rename(columns={"score": "ortalama"})
        tens = v.assign(is10=(v["score"] == 10)).groupby("contestant", as_index=False)["is10"].sum().rename(columns={"is10": "on_sayisi"})

        board = total.merge(avg, on="contestant", how="outer").merge(tens, on="contestant", how="outer")
        board["ortalama"] = board["ortalama"].round(2)
        board["on_sayisi"] = board["on_sayisi"].fillna(0).astype(int)

        board = board.sort_values(by=["toplam", "ortalama", "on_sayisi", "contestant"], ascending=[False, False, False, True]).reset_index(drop=True)
        board.insert(0, "Sıra", board.index + 1)

        st.dataframe(board, use_container_width=True, hide_index=True)

        winner = board.iloc[0]["contestant"]
        st.success(f"🏆 Şu an 1. sırada: **{winner}**")

    st.divider()

    # Admin-only insights
    if is_admin(st.session_state["user"]):
        st.subheader("📊 Jüri İlerlemesi (Admin)")
        total_cont = max(len(contestants), 1)
        if contestants and not votes_df.empty:
            prog_rows = []
            for u in JUDGE_USERS:
                jname = JUDGE_DISPLAY.get(u, u)
                count = int((votes_df["judge"] == u).sum())
                prog_rows.append({"Jüri": jname, "Verilen Oy": count, "Toplam Yarışmacı": total_cont})
            prog = pd.DataFrame(prog_rows)
            st.dataframe(prog, use_container_width=True, hide_index=True)
        else:
            st.info("İlerleme için yarışmacı ve en az 1 oy olmalı.")

        st.subheader("👥 Yarışmacı Ekle (Admin)")
        new_name = st.text_input("Yeni yarışmacı adı", placeholder="Örn: Abdullah")
        if st.button("➕ Ekle"):
            if new_name.strip():
                add_contestant(new_name.strip())
                st.success("Yarışmacı eklendi")
                st.rerun()
            else:
                st.warning("İsim boş olamaz")

    st.divider()

    st.subheader("👀 İzleyici Bilgisi")
    st.caption("Giriş yapmayanlar sadece sıralamayı görür. Jüri isimleri izleyicide gösterilmez.")

# ----------------------------
# RIGHT: Voting panel (on the right)
# ----------------------------
with right:
    st.subheader("🗳️ Puan Girişi")

    user = st.session_state["user"]
    open_ = get_voting_open()

    if user is None:
        st.info("Puan vermek için jüri girişi yapmalısın.")
    elif not open_:
        st.warning("Oylama şu an kapalı. Admin açınca puan girebilirsin.")
    else:
        if not contestants:
            st.warning("Yarışmacı listesi boş. Admin yarışmacı eklemeli.")
        else:
            st.write(f"Aktif Jüri: **{JUDGE_DISPLAY.get(user, user)}**")

            contestant = st.selectbox("Yarışmacı", contestants)

            # Current vote for this pair
            existing = None
            if not votes_df.empty:
                m = (votes_df["judge"] == user) & (votes_df["contestant"] == contestant)
                if m.any():
                    existing = votes_df[m].iloc[0]

            # 1-10 as buttons
            st.caption("Puanı seç (1–10)")
            btn_cols = st.columns(5)
            selected = st.session_state.get("selected_score", 8)

            for i, score in enumerate(range(1, 11)):
                with btn_cols[i % 5]:
                    if st.button(str(score), use_container_width=True, key=f"scorebtn_{score}"):
                        selected = score
                        st.session_state["selected_score"] = score

            st.write(f"Seçilen Puan: **{selected}**")

            if existing is not None:
                st.info(f"Bu yarışmacıya daha önce oy verdin: **{int(existing['score'])}**. Kaydet ile güncellenir.")

            if st.button("✅ Kaydet / Güncelle", use_container_width=True):
                action = upsert_vote(user, contestant, int(selected))
                st.success("Oy kaydedildi." if action == "insert" else "Oy güncellendi.")
                st.rerun()

    st.divider()

    # Admin tools: delete / edit
    if is_admin(user):
        st.subheader("🛠️ Admin: Puan Sil / Düzenle")
        if votes_df.empty:
            st.info("Silinecek/düzenlenecek oy yok.")
        else:
            # Show editor with delete checkbox
            show = votes_df.copy()
            # hide judges from viewer normally, but admin sees
            show["judge_name"] = show["judge"].map(lambda x: JUDGE_DISPLAY.get(x, x))
            show = show[["id", "ts", "judge_name", "contestant", "score"]].rename(columns={"judge_name": "jüri"})
            show.insert(0, "Sil", False)

            edited = st.data_editor(show, use_container_width=True, hide_index=True)

            c1, c2 = st.columns([1, 1])
            with c1:
                if st.button("🗑️ Seçilenleri Sil", use_container_width=True):
                    ids = set(edited.loc[edited["Sil"] == True, "id"].astype(str).tolist())
                    n = admin_delete_votes(ids)
                    st.success(f"Silindi: {n}")
                    st.rerun()

            with c2:
                st.caption("Düzenleme: aşağıdan bir kaydı seç")

            # Simple edit by id
            vote_ids = edited["id"].astype(str).tolist()
            pick = st.selectbox("Düzenlenecek oy (id)", vote_ids)
            new_score = st.slider("Yeni puan", 1, 10, 8)
            if st.button("✏️ Puanı Güncelle", use_container_width=True):
                ok = admin_edit_vote(pick, int(new_score))
                st.success("Güncellendi" if ok else "Bulunamadı")
                st.rerun()

# Footer
st.caption("Made for Lamajör etkinlikleri • İzleyici: sonuçları görür • Jüri: oy verir • Admin: yönetir")
