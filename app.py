"""Ledger - personal expense tracker (Streamlit + SQLite)."""
import re, sqlite3, os
from datetime import date, timedelta
import bcrypt, pandas as pd, plotly.express as px, streamlit as st

st.set_page_config(page_title="Ledger", page_icon="💰", layout="wide")
INCOME = ["Salary", "Freelancing", "Business", "Investments", "Interest", "Gift", "Other"]
EXPENSE = ["Food", "Transportation", "Shopping", "Housing and Rent", "Bills and Utilities", "Education",
           "Healthcare", "Entertainment", "Travel", "Personal Care", "Subscriptions", "Other"]
DB_PATH = os.environ.get("LEDGER_DB", "ledger.db")   # point to a persistent path/volume when deploying

# ---------------- look & feel ----------------
ICONS = {  # Lucide-style paths
 "wallet": '<path d="M20 12V8H6a2 2 0 0 1-2-2c0-1.1.9-2 2-2h12v4"/><path d="M4 6v12c0 1.1.9 2 2 2h14v-4"/><path d="M18 12a2 2 0 0 0 0 4h4v-4Z"/>',
 "up": '<path d="M22 7 13.5 15.5 8.5 10.5 2 17"/><path d="M16 7h6v6"/>',
 "down": '<path d="M22 17 13.5 8.5 8.5 13.5 2 7"/><path d="M16 17h6v-6"/>',
 "pct": '<path d="M19 5 5 19"/><circle cx="6.5" cy="6.5" r="2.5"/><circle cx="17.5" cy="17.5" r="2.5"/>',
 "target": '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
 "tag": '<path d="M12 2H2v10l9.3 9.3a1 1 0 0 0 1.4 0l8.6-8.6a1 1 0 0 0 0-1.4Z"/><circle cx="7" cy="7" r="1.5"/>',
 "cal": '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
 "list": '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
 "chart": '<path d="M3 3v18h18"/><path d="M18 17V9M13 17V5M8 17v-3"/>',
 "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
 "alert": '<path d="m21.7 18-8-14a2 2 0 0 0-3.4 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.7-3Z"/><path d="M12 9v4M12 17h.01"/>',
}
def svg(name, size=22):
    return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</svg>'

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
html,body,[class*=css],.stApp{font-family:'Plus Jakarta Sans',system-ui,sans-serif}
.stApp{background:radial-gradient(1200px 500px at 90% -10%,#10b98122,transparent),radial-gradient(900px 500px at -10% 0,#6d5bd01f,transparent),#f4f7fb}
#MainMenu,footer{visibility:hidden}.block-container{padding-top:2rem;max-width:1200px}
section[data-testid=stSidebar]{background:linear-gradient(180deg,#0b1533,#0f2a4a 60%,#0f4c4a)}
section[data-testid=stSidebar] *{color:#dbe6ff!important}
section[data-testid=stSidebar] a[data-testid=stSidebarNavLink][aria-current=page]{background:#ffffff22;border-radius:12px}
section[data-testid=stSidebar] button{background:#ffffff14;border:1px solid #ffffff2e;border-radius:12px}
.brand{display:flex;align-items:center;gap:10px;font-weight:800;font-size:22px;padding:6px 4px 14px}
.brand i{width:38px;height:38px;border-radius:12px;display:grid;place-items:center;background:linear-gradient(135deg,#10b981,#0f766e);box-shadow:0 6px 14px #10b98155,inset 0 1px 0 #fff6}
.chip{display:flex;gap:10px;align-items:center;background:#ffffff14;border-radius:14px;padding:10px;margin-bottom:10px}
.chip b{display:block}.chip small{opacity:.7}
.ph{display:flex;align-items:center;gap:14px;margin-bottom:18px}.ph h1{margin:0;font-size:28px;font-weight:800;color:#0f1b3d}
.ph p{margin:0;color:#5b6785}
.tile{width:46px;height:46px;border-radius:14px;display:grid;place-items:center;color:#fff;flex:none;
 box-shadow:0 10px 18px -6px var(--c),inset 0 2px 0 #ffffff55,inset 0 -3px 0 #00000022}
.kpi{background:#fff;border:1px solid #e6ebf3;border-radius:20px;padding:18px;display:flex;gap:14px;align-items:center;
 box-shadow:0 1px 0 #fff inset,0 14px 30px -18px #0f1b3d66;transition:transform .2s,box-shadow .2s}
.kpi:hover{transform:translateY(-3px);box-shadow:0 22px 34px -18px #0f1b3d77}
.kpi span{color:#5b6785;font-size:13px;font-weight:600}.kpi b{display:block;font-size:24px;color:#0f1b3d;font-weight:800;line-height:1.25}
.kpi small{color:#8792ab}.kpi.neg{border-color:#f9736255;background:linear-gradient(#fff,#fff5f3)}.kpi.neg b{color:#e5533f}
.tx{display:flex;align-items:center;gap:14px;background:#fff;border:1px solid #e6ebf3;border-radius:16px;padding:10px 14px;margin-bottom:8px}
.tx .tile{width:40px;height:40px;border-radius:12px}.tx .mid{flex:1;min-width:0}.tx .mid b{display:block;color:#0f1b3d}
.tx .mid span{color:#7a859e;font-size:13px}.tx .amt{font-weight:800}.tx.income .amt{color:#059669}.tx.expense .amt{color:#e5533f}
.pill{font-size:11px;font-weight:700;padding:2px 8px;border-radius:99px;margin-left:8px}
.income .pill{background:#d1fae5;color:#047857}.expense .pill{background:#ffe4df;color:#c2410c}
.bar{height:12px;background:#e6ebf3;border-radius:99px;overflow:hidden}.bar i{display:block;height:100%;border-radius:99px;background:linear-gradient(90deg,#0f766e,#10b981)}
.bar i.warn{background:linear-gradient(90deg,#f59e0b,#fbbf24)}.bar i.over{background:linear-gradient(90deg,#e5533f,#f97362)}
.bud{background:#fff;border:1px solid #e6ebf3;border-radius:16px;padding:14px 16px;margin-bottom:10px}
.bud div.h{display:flex;justify-content:space-between;margin-bottom:8px;color:#0f1b3d;flex-wrap:wrap}
.empty{text-align:center;padding:36px;border:2px dashed #d3dbe8;border-radius:20px;color:#5b6785;background:#ffffffaa}
.empty .tile{margin:0 auto 10px}
.hero{background:linear-gradient(135deg,#0b1533,#0f4c4a);color:#fff;padding:40px;border-radius:28px;position:relative;overflow:hidden;
 box-shadow:0 30px 60px -30px #0b1533}
.hero:after{content:"";position:absolute;right:-80px;top:-80px;width:280px;height:280px;border-radius:50%;background:radial-gradient(#6d5bd0aa,transparent 70%)}
.hero h1{color:#fff;font-size:42px;line-height:1.1;font-weight:800;margin:0 0 12px}.hero p{color:#c3d2f3;max-width:46ch}
.prev{margin-top:22px;background:#ffffff18;backdrop-filter:blur(10px);border:1px solid #ffffff30;border-radius:18px;padding:14px;display:flex;gap:10px}
.prev div{flex:1;background:#ffffff14;border-radius:12px;padding:10px;font-size:12px;color:#c3d2f3}.prev b{display:block;color:#fff;font-size:17px}
.stButton>button,.stDownloadButton>button,[data-testid=stFormSubmitButton]>button{border-radius:12px;font-weight:600;transition:transform .1s}
.stButton>button:active,[data-testid=stFormSubmitButton]>button:active{transform:scale(.97)}
[data-testid=stFormSubmitButton]>button[kind=primary],.stButton>button[kind=primary]{background:linear-gradient(135deg,#0f766e,#10b981);border:0;color:#fff;box-shadow:0 8px 16px -8px #0f766e}
[data-testid=stVerticalBlockBorderWrapper]{border-radius:20px;background:#ffffffd9}
@media(prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
</style>""", unsafe_allow_html=True)

def tile(name, c1, c2, size=22):
    return f'<div class="tile" style="--c:{c1}aa;background:linear-gradient(135deg,{c1},{c2})">{svg(name, size)}</div>'
def kpi(icon, label, value, note="", c=("#10b981", "#0f766e"), neg=False):
    st.markdown(f'<div class="kpi {"neg" if neg else ""}">{tile(icon, *c)}<div><span>{label}</span><b>{value}</b><small>{note}</small></div></div>', unsafe_allow_html=True)
def header(icon, title, sub, c=("#0f766e", "#10b981")):
    st.markdown(f'<div class="ph">{tile(icon, *c)}<div><h1>{title}</h1><p>{sub}</p></div></div>', unsafe_allow_html=True)
def empty(icon, title, sub):
    st.markdown(f'<div class="empty">{tile(icon, "#6d5bd0", "#8b5cf6")}<b>{title}</b><br>{sub}</div>', unsafe_allow_html=True)
def tx_html(r):
    inc = r["type"] == "income"; c = ("#10b981", "#0f766e") if inc else ("#f97362", "#e5533f")
    return (f'<div class="tx {r["type"]}">{tile("up" if inc else "down", *c, size=18)}<div class="mid"><b>{r["category"]}'
            f'<span class="pill">{"Income" if inc else "Expense"}</span></b><span>{r["description"] or "No description"} · {r["day"]}</span></div>'
            f'<div class="amt">{"+" if inc else "−"}{inr(r["paise"])}</div></div>')
def style_fig(fig):
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_family="Plus Jakarta Sans", margin=dict(t=50, b=10, l=10, r=10),
                      colorway=["#0f766e", "#10b981", "#6d5bd0", "#f97362", "#1e3a8a", "#f59e0b", "#14b8a6", "#8b5cf6"])
    return fig

# ---------------- database ----------------
@st.cache_resource
def db():
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, pw BLOB NOT NULL);
    CREATE TABLE IF NOT EXISTS tx(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, type TEXT NOT NULL CHECK(type IN('income','expense')),
      paise INTEGER NOT NULL CHECK(paise>0), category TEXT NOT NULL, description TEXT DEFAULT '', day TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS ix_tx ON tx(user_id, day);
    CREATE TABLE IF NOT EXISTS budgets(user_id INTEGER, category TEXT, paise INTEGER NOT NULL, PRIMARY KEY(user_id, category));""")
    return c

def q(sql, args=(), one=False, commit=False):
    cur = db().execute(sql, args)
    if commit: db().commit()
    return cur.fetchone() if one else cur.fetchall()

def inr(p):
    """Paise -> Indian-formatted rupees, e.g. -1234567 -> -₹12,345.67"""
    s = f"{abs(p) / 100:.2f}"; i, d = s.split(".")
    if len(i) > 3: i = re.sub(r"(\d)(?=(\d\d)+$)", r"\1,", i[:-3]) + "," + i[-3:]
    return f"{'-' if p < 0 else ''}₹{i}.{d}"

# ---------------- data helpers (every query filtered by user_id) ----------------
def totals(uid, start=None, end=None):
    sql, a = "SELECT type, COALESCE(SUM(paise),0) s FROM tx WHERE user_id=?", [uid]
    if start: sql += " AND day>=?"; a.append(start.isoformat())
    if end: sql += " AND day<=?"; a.append(end.isoformat())
    d = {r["type"]: r["s"] for r in q(sql + " GROUP BY type", a)}
    inc, exp = d.get("income", 0), d.get("expense", 0)
    return inc, exp, inc - exp, ((inc - exp) / inc * 100 if inc > 0 else None)   # None avoids divide-by-zero

def frame(uid, start=None, end=None):
    sql, a = "SELECT * FROM tx WHERE user_id=?", [uid]
    if start: sql += " AND day>=?"; a.append(start.isoformat())
    if end: sql += " AND day<=?"; a.append(end.isoformat())
    df = pd.DataFrame([dict(r) for r in q(sql, a)], columns=["id","user_id","type","paise","category","description","day"])
    df["amount"] = df["paise"] / 100; df["day"] = pd.to_datetime(df["day"]); return df

def tx_form(uid, kind, key, row=None):
    """Shared add/edit form. Returns True when saved."""
    cats = INCOME if kind == "income" else EXPENSE
    with st.form(key, clear_on_submit=row is None):
        amt = st.number_input("Amount (₹)", min_value=0.0, step=100.0, format="%.2f", value=row["paise"] / 100 if row else 0.0)
        cat = st.selectbox("Category", cats, index=cats.index(row["category"]) if row and row["category"] in cats else 0)
        desc = st.text_input("Description", max_chars=140, value=row["description"] if row else "")
        day = st.date_input("Date", value=date.fromisoformat(row["day"]) if row else date.today())
        if st.form_submit_button("Save changes" if row else f"Add {kind}", type="primary", use_container_width=True, icon=":material/check_circle:"):
            paise = round(amt * 100)
            if paise <= 0: st.error("Amount must be greater than zero."); return False
            with st.spinner("Saving transaction…"):
                if row: q("UPDATE tx SET paise=?,category=?,description=?,day=? WHERE id=? AND user_id=?", (paise, cat, desc.strip(), day.isoformat(), row["id"], uid), commit=True)
                else: q("INSERT INTO tx(user_id,type,paise,category,description,day) VALUES(?,?,?,?,?,?)", (uid, kind, paise, cat, desc.strip(), day.isoformat()), commit=True)
            st.toast(f"{kind.title()} {'updated' if row else 'added'}", icon="✅")
            if not row and kind == "expense" and totals(uid)[2] < 0: st.toast("Your expenses have exceeded your income.", icon="⚠️")
            return True
    return False

@st.dialog("Edit transaction")
def edit_dialog(uid, row):
    if tx_form(uid, row["type"], "edit", row): st.rerun()

@st.dialog("Delete transaction?")
def delete_dialog(uid, row):
    st.write(f"{row['type'].title()} of **{inr(row['paise'])}** ({row['category']}) will be removed permanently.")
    a, b = st.columns(2)
    if a.button("Delete", type="primary", use_container_width=True, icon=":material/delete:"):
        q("DELETE FROM tx WHERE id=? AND user_id=?", (row["id"], uid), commit=True); st.toast("Transaction deleted", icon="🗑️"); st.rerun()
    if b.button("Cancel", use_container_width=True): st.rerun()

# ---------------- auth ----------------
def auth_page():
    l, r = st.columns([1.25, 1], gap="large")
    with l:
        st.markdown(f'''<div class="hero"><h1>Know where every rupee went.</h1><p>Track income and spending, set monthly budgets, and watch your savings rate update the moment you add a transaction.</p>
        <div class="prev"><div>{svg("up",16)}<br>Income<b>₹85,000</b></div><div>{svg("down",16)}<br>Expenses<b>₹52,400</b></div><div>{svg("pct",16)}<br>Savings<b>38%</b></div></div>
        <small style="opacity:.6">Sample preview — your own numbers appear after you sign up.</small></div>''', unsafe_allow_html=True)
    with r:
        with st.container(border=True):
            tab_in, tab_up = st.tabs([":material/login: Log in", ":material/person_add: Sign up"])
            with tab_in, st.form("login", border=False):
                email = st.text_input("Email", icon=":material/mail:"); pw = st.text_input("Password", type="password", icon=":material/lock:")
                if st.form_submit_button("Log in", type="primary", use_container_width=True, icon=":material/login:"):
                    u = q("SELECT * FROM users WHERE email=?", (email.strip().lower(),), one=True)
                    if u and bcrypt.checkpw(pw.encode(), u["pw"]): st.session_state.uid = u["id"]; st.rerun()
                    else: st.error("Incorrect email or password.", icon=":material/error:")
            with tab_up, st.form("signup", border=False):
                name = st.text_input("Full name", icon=":material/person:"); email = st.text_input("Email address", icon=":material/mail:")
                pw = st.text_input("Password", type="password", icon=":material/lock:", help="8+ characters with letters and numbers")
                pw2 = st.text_input("Confirm password", type="password", icon=":material/lock_reset:")
                if st.form_submit_button("Create account", type="primary", use_container_width=True, icon=":material/rocket_launch:"):
                    email = email.strip().lower()
                    if not name.strip() or not re.fullmatch(r"\S+@\S+\.\S+", email): st.error("Enter your name and a valid email.")
                    elif not re.fullmatch(r"(?=.*[A-Za-z])(?=.*\d).{8,}", pw): st.error("Password needs 8+ characters with letters and numbers.")
                    elif pw != pw2: st.error("Passwords do not match.")
                    elif q("SELECT 1 FROM users WHERE email=?", (email,), one=True): st.error("An account with this email already exists.")
                    else:
                        cur = db().execute("INSERT INTO users(name,email,pw) VALUES(?,?,?)", (name.strip(), email, bcrypt.hashpw(pw.encode(), bcrypt.gensalt())))
                        db().commit(); st.session_state.uid = cur.lastrowid; st.rerun()

# ---------------- pages ----------------
def dashboard():
    header("wallet", f"Welcome back, {user['name']}!", f"Your financial overview · {date.today():%B %Y}")
    inc, exp, bal, rate = totals(uid)
    c = st.columns(4)
    with c[0]: kpi("up", "Total income", inr(inc), "All recorded income")
    with c[1]: kpi("down", "Total expenses", inr(exp), "All recorded spending", ("#f97362", "#e5533f"))
    with c[2]: kpi("wallet", "Current balance", inr(bal), "Overspent" if bal < 0 else "Income − expenses", ("#1e3a8a", "#0f766e") if bal >= 0 else ("#f97362", "#e5533f"), bal < 0)
    with c[3]: kpi("pct", "Savings rate", "—" if rate is None else f"{rate:.1f}%", "Share of income kept", ("#6d5bd0", "#8b5cf6"))
    st.write("")
    if bal < 0: st.warning("Your expenses have exceeded your income.", icon=":material/warning:")
    elif inc > 0: st.success(f"You've spent {exp / inc * 100:.0f}% of your income — {100 - exp / inc * 100:.0f}% is saved.", icon=":material/savings:")
    a, b = st.columns(2); saved = False
    with a, st.container(border=True): st.subheader(":material/add_circle: Add income"); saved |= tx_form(uid, "income", "add_inc")
    with b, st.container(border=True): st.subheader(":material/remove_circle: Add expense"); saved |= tx_form(uid, "expense", "add_exp")
    if saved: st.rerun()
    st.subheader(":material/history: Recent transactions")
    rows = q("SELECT * FROM tx WHERE user_id=? ORDER BY day DESC, id DESC LIMIT 5", (uid,))
    if rows: st.markdown("".join(tx_html(r) for r in rows), unsafe_allow_html=True)
    else: empty("list", "No transactions yet", "Add your first income or expense above to get started.")

def history():
    header("list", "Transactions", "Search, filter, edit and export your history")
    with st.container(border=True):
        f = st.columns([2, 1, 1.4, 1.2, 1.2, 1])
        search = f[0].text_input("Search", icon=":material/search:", placeholder="Description or category")
        typ = f[1].selectbox("Type", ["All", "income", "expense"]); cat = f[2].selectbox("Category", ["All"] + sorted(set(INCOME + EXPENSE)))
        d1 = f[3].date_input("From", value=None); d2 = f[4].date_input("To", value=None)
        sort = f[5].selectbox("Sort", ["Newest", "Oldest", "Highest", "Lowest"])
    sql, a = " FROM tx WHERE user_id=?", [uid]
    if typ != "All": sql += " AND type=?"; a.append(typ)
    if cat != "All": sql += " AND category=?"; a.append(cat)
    if search: sql += " AND (description LIKE ? OR category LIKE ?)"; a += [f"%{search}%"] * 2
    if d1: sql += " AND day>=?"; a.append(d1.isoformat())
    if d2: sql += " AND day<=?"; a.append(d2.isoformat())
    total = q("SELECT COUNT(*) n" + sql, a, one=True)["n"]
    order = {"Newest": "day DESC,id DESC", "Oldest": "day ASC,id ASC", "Highest": "paise DESC", "Lowest": "paise ASC"}[sort]
    per = 10; pages = max(1, -(-total // per))
    page = st.number_input("Page", 1, pages, 1) if pages > 1 else 1
    rows = q(f"SELECT *{sql} ORDER BY {order} LIMIT ? OFFSET ?", a + [per, (page - 1) * per])
    if not rows: empty("tag", "No transactions found", "Add one from the dashboard or clear your filters."); return
    st.caption(f"{total} transactions · page {page} of {pages}")
    for r in rows:
        c = st.columns([12, 1, 1], vertical_alignment="center")
        c[0].markdown(tx_html(r), unsafe_allow_html=True)
        if c[1].button("", key=f"e{r['id']}", icon=":material/edit:", help="Edit"): edit_dialog(uid, dict(r))
        if c[2].button("", key=f"d{r['id']}", icon=":material/delete:", help="Delete"): delete_dialog(uid, dict(r))
    out = pd.DataFrame([dict(r) for r in q(f"SELECT day,type,category,description,paise/100.0 AS amount{sql} ORDER BY {order}", a)])
    st.download_button("Export CSV", out.to_csv(index=False), "transactions.csv", "text/csv", icon=":material/download:")

def ranges():
    t = date.today(); first = t.replace(day=1); last_end = first - timedelta(days=1)
    return {"This month": (first, t), "Last month": (last_end.replace(day=1), last_end),
            "Last 3 months": ((first - timedelta(days=62)).replace(day=1), t), "This year": (date(t.year, 1, 1), t), "All time": (None, None)}

def analytics():
    header("chart", "Analytics", "Charts built from your real transactions", ("#6d5bd0", "#8b5cf6"))
    choice = st.segmented_control("Date range", list(ranges()), default="All time"); choice = choice or "All time"
    s, e = ranges()[choice]; df = frame(uid, s, e)
    if df.empty: empty("chart", "Not enough data yet", "Add transactions in this range to see charts."); return
    inc, exp, bal, rate = totals(uid, s, e); exps = df[df.type == "expense"]; df["month"] = df["day"].dt.strftime("%Y-%m")
    c = st.columns(4)
    with c[0]: kpi("tag", "Top spending", exps.groupby("category").amount.sum().idxmax() if not exps.empty else "—", "Highest category", ("#f59e0b", "#f97362"))
    with c[1]: kpi("cal", "Avg monthly spend", inr(round(exp / max(df.month.nunique(), 1))), choice, ("#1e3a8a", "#0f766e"))
    with c[2]: kpi("wallet", "Balance", inr(bal), "", ("#10b981", "#0f766e") if bal >= 0 else ("#f97362", "#e5533f"), bal < 0)
    with c[3]: kpi("pct", "Savings rate", "—" if rate is None else f"{rate:.1f}%", "", ("#6d5bd0", "#8b5cf6"))
    st.write(""); a, b = st.columns(2)
    with a, st.container(border=True):
        st.plotly_chart(style_fig(px.bar(pd.DataFrame({"Type": ["Income", "Expenses"], "₹": [inc / 100, exp / 100]}), x="Type", y="₹", color="Type",
                        color_discrete_map={"Income": "#10b981", "Expenses": "#f97362"}, title="Income vs expenses")), use_container_width=True)
    with b, st.container(border=True):
        if exps.empty: st.info("No expenses in this range.")
        else: st.plotly_chart(style_fig(px.pie(exps, names="category", values="amount", hole=.55, title="Expense breakdown")), use_container_width=True)
    mon = df.pivot_table(index="month", columns="type", values="amount", aggfunc="sum", fill_value=0).reset_index()
    with st.container(border=True):
        st.plotly_chart(style_fig(px.line(mon, x="month", y=[x for x in ("income", "expense") if x in mon], markers=True, title="Monthly trend",
                        color_discrete_map={"income": "#10b981", "expense": "#f97362"})), use_container_width=True)

def budgets():
    header("target", "Budgets", "Monthly limits that reset each month — history is never deleted", ("#f59e0b", "#f97362"))
    months = [(date.today().replace(day=1) - timedelta(days=31 * i)).strftime("%Y-%m") for i in range(12)]
    m = st.selectbox("Month", months); start = date.fromisoformat(m + "-01"); end = (start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    lim = {r["category"]: r["paise"] for r in q("SELECT category,paise FROM budgets WHERE user_id=?", (uid,))}
    spent = {r["category"]: r["s"] for r in q("SELECT category, SUM(paise) s FROM tx WHERE user_id=? AND type='expense' AND day BETWEEN ? AND ? GROUP BY category", (uid, start.isoformat(), end.isoformat()))}
    for cat, limit in lim.items():
        used = sum(spent.values()) if cat == "__overall__" else spent.get(cat, 0); pct = used / limit * 100 if limit > 0 else 0
        cls = "over" if pct >= 100 else "warn" if pct >= 80 else ""
        note = "⚠ Budget reached or exceeded" if pct >= 100 else "You've used 80% of this budget" if pct >= 80 else ""
        st.markdown(f'<div class="bud"><div class="h"><b>{"Overall budget" if cat == "__overall__" else cat}</b><span>{pct:.0f}% used</span></div>'
                    f'<div class="bar"><i class="{cls}" style="width:{min(pct, 100)}%"></i></div>'
                    f'<small>{inr(used)} of {inr(limit)} · {inr(limit - used)} left &nbsp; <b>{note}</b></small></div>', unsafe_allow_html=True)
    if not lim: empty("target", "No budgets yet", "Set an overall or category budget below.")
    with st.container(border=True):
        st.subheader(":material/tune: Set a budget")
        with st.form("budget", border=False):
            cat = st.selectbox("Budget for", ["Overall"] + EXPENSE); amt = st.number_input("Monthly limit (₹) — 0 removes it", min_value=0.0, step=500.0)
            if st.form_submit_button("Save budget", type="primary", icon=":material/save:"):
                key = "__overall__" if cat == "Overall" else cat
                if amt > 0: q("INSERT OR REPLACE INTO budgets VALUES(?,?,?)", (uid, key, round(amt * 100)), commit=True)
                else: q("DELETE FROM budgets WHERE user_id=? AND category=?", (uid, key), commit=True)
                st.rerun()

def profile():
    header("user", "Profile", "Update how your name appears", ("#1e3a8a", "#6d5bd0"))
    with st.container(border=True), st.form("profile", border=False):
        name = st.text_input("Full name", user["name"], icon=":material/person:"); st.text_input("Email", user["email"], disabled=True, icon=":material/mail:")
        if st.form_submit_button("Save profile", type="primary", icon=":material/save:"):
            if name.strip(): q("UPDATE users SET name=? WHERE id=?", (name.strip(), uid), commit=True); st.toast("Profile updated", icon="✅"); st.rerun()
            else: st.error("Name cannot be empty.")

@st.dialog("Log out?")
def logout_dialog():
    a, b = st.columns(2)
    if a.button("Log out", type="primary", use_container_width=True, icon=":material/logout:"): st.session_state.clear(); st.rerun()
    if b.button("Stay", use_container_width=True): st.rerun()

# ---------------- router ----------------
uid = st.session_state.get("uid")
user = q("SELECT * FROM users WHERE id=?", (uid,), one=True) if uid else None
if not user: auth_page(); st.stop()
pg = st.navigation([st.Page(dashboard, title="Dashboard", icon=":material/dashboard:", url_path="dashboard", default=True),
                    st.Page(history, title="Transactions", icon=":material/receipt_long:", url_path="transactions"),
                    st.Page(analytics, title="Analytics", icon=":material/insights:", url_path="analytics"),
                    st.Page(budgets, title="Budgets", icon=":material/target:", url_path="budgets"),
                    st.Page(profile, title="Profile", icon=":material/person:", url_path="profile")])
with st.sidebar:
    st.markdown(f'<div class="brand"><i>{svg("wallet", 20)}</i>Ledger</div>'
                f'<div class="chip">{svg("user", 20)}<div><b>{user["name"]}</b><small>{user["email"]}</small></div></div>', unsafe_allow_html=True)
    if st.button("Log out", use_container_width=True, icon=":material/logout:"): logout_dialog()
pg.run()
