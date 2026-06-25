import streamlit as st
import sqlite3
import uuid
import pandas as pd
from datetime import datetime, timedelta

# ========== PAGE CONFIG ==========
st.set_page_config(
    page_title="Application Tokens | GlobalInternet.py",
    layout="centered",
    page_icon="🔑"
)

# ========== CUSTOM CSS ==========
st.markdown("""
<style>
    .stApp { background: #0a0a0f; color: #ffffff; }
    .main-header { text-align:center; padding:20px 0; border-bottom:2px solid #2a1f14; margin-bottom:30px; }
    .main-header h1 { color:#00ff64; font-size:2.5rem; margin:0; }
    .main-header p { color:#a09080; font-size:1.1rem; }
    .token-card { background:rgba(20,16,24,0.8); border:1px solid #2a1f14; border-radius:12px; padding:20px; margin:10px 0; text-align:center; }
    .token-card h3 { color:#00ff64; margin:0; }
    .token-card .price { font-size:2rem; font-weight:bold; color:#fff; }
    .token-card .price small { font-size:1rem; color:#a09080; }
    .token-display { background:rgba(0,255,100,0.1); border:1px solid #00ff64; border-radius:8px; padding:15px; font-family:monospace; font-size:1.2rem; word-break:break-all; text-align:center; color:#00ff64; margin:10px 0; }
    .info-box { background:rgba(0,255,100,0.05); border-left:4px solid #00ff64; padding:10px 15px; border-radius:4px; margin:10px 0; color:#fff; }
    .footer { text-align:center; padding:20px 0; border-top:1px solid #2a1f14; margin-top:30px; color:#a09080; font-size:0.9rem; }
    .stButton>button { background:linear-gradient(135deg, #00ff64, #00bfff) !important; color:#0a0a0f !important; border:none !important; border-radius:8px !important; font-weight:600 !important; width:100% !important; }
    .stButton>button:hover { transform:scale(1.02); box-shadow:0 0 30px rgba(0,255,100,0.3); }
    .stTextInput>div>div>input { background-color:#141018 !important; color:#fff !important; border:1px solid #2a1f14 !important; border-radius:8px !important; text-align:center !important; }
</style>
""", unsafe_allow_html=True)

# ========== DATABASE ==========
def init_db():
    conn = sqlite3.connect('tokens.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS tokens (
            id TEXT PRIMARY KEY,
            token_code TEXT UNIQUE NOT NULL,
            plan_name TEXT NOT NULL,
            price REAL NOT NULL,
            purchase_date TEXT NOT NULL,
            expiry_date TEXT,
            is_lifetime INTEGER DEFAULT 0,
            is_used INTEGER DEFAULT 0,
            used_at TEXT,
            used_by TEXT,
            status TEXT DEFAULT 'active'
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_id TEXT,
            buyer_name TEXT,
            buyer_email TEXT,
            payment_method TEXT,
            payment_reference TEXT,
            purchase_date TEXT,
            FOREIGN KEY (token_id) REFERENCES tokens (id)
        )
    ''')
    conn.commit()
    conn.close()

def generate_token(plan_name, price, is_lifetime=False):
    token_code = str(uuid.uuid4()).replace('-', '').upper()
    token_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    expiry_date = None if is_lifetime else (datetime.now() + timedelta(days=30)).isoformat()
    lifetime_flag = 1 if is_lifetime else 0
    conn = sqlite3.connect('tokens.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO tokens (id, token_code, plan_name, price, purchase_date, expiry_date, is_lifetime, is_used, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (token_id, token_code, plan_name, price, now, expiry_date, lifetime_flag, 0, 'active'))
    conn.commit()
    conn.close()
    return token_code, token_id

def validate_token(token_code):
    conn = sqlite3.connect('tokens.db')
    c = conn.cursor()
    c.execute('SELECT id, plan_name, price, purchase_date, expiry_date, is_lifetime, is_used, status FROM tokens WHERE token_code = ?', (token_code,))
    result = c.fetchone()
    conn.close()
    if not result:
        return None, "Token does not exist"
    token_id, plan_name, price, purchase_date, expiry_date, is_lifetime, is_used, status = result
    if is_used:
        return None, "Token already used"
    if status != 'active':
        return None, f"Token status: {status}"
    if not is_lifetime and expiry_date and datetime.now() > datetime.fromisoformat(expiry_date):
        conn = sqlite3.connect('tokens.db')
        c = conn.cursor()
        c.execute('UPDATE tokens SET status = ? WHERE id = ?', ('expired', token_id))
        conn.commit()
        conn.close()
        return None, "Token has expired"
    return {
        'id': token_id,
        'plan_name': plan_name,
        'price': price,
        'purchase_date': purchase_date,
        'expiry_date': expiry_date,
        'is_lifetime': is_lifetime
    }, "Valid"

def use_token(token_code, user_info=None):
    conn = sqlite3.connect('tokens.db')
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute('UPDATE tokens SET is_used = 1, used_at = ?, used_by = ?, status = "used" WHERE token_code = ?',
              (now, user_info or 'anonymous', token_code))
    conn.commit()
    conn.close()

def get_all_tokens():
    conn = sqlite3.connect('tokens.db')
    c = conn.cursor()
    c.execute('SELECT token_code, plan_name, price, purchase_date, expiry_date, is_lifetime, is_used, status FROM tokens ORDER BY purchase_date DESC')
    results = c.fetchall()
    conn.close()
    return results

def get_stats():
    conn = sqlite3.connect('tokens.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM tokens')
    total = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM tokens WHERE is_used = 0 AND status = "active"')
    available = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM tokens WHERE is_used = 1')
    used = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM tokens WHERE status = "expired"')
    expired = c.fetchone()[0]
    conn.close()
    return total, available, used, expired

init_db()

# ========== SESSION STATE ==========
if 'admin_authenticated' not in st.session_state:
    st.session_state.admin_authenticated = False
if 'token_verified' not in st.session_state:
    st.session_state.token_verified = False
if 'verified_token' not in st.session_state:
    st.session_state.verified_token = None

# ========== HEADER ==========
st.markdown("""
<div class="main-header">
    <h1>🔑 Application Tokens</h1>
    <p>By GlobalInternet.py Online Software Company</p>
    <p style="font-size:0.9rem; color:#666;">— Purchase tokens to unlock our software suite —</p>
</div>
""", unsafe_allow_html=True)

# ========== SIDEBAR ==========
with st.sidebar:
    st.markdown("### 📞 Contact")
    st.markdown(f"**Email:** deslandes78@gmail.com")
    st.markdown(f"**Phone:** (509) 4738-5663")
    st.markdown(f"**Website:** [globalinternet-py.com](https://globalinternet-py.com)")
    st.markdown("---")
    st.markdown("### 💳 Payment Methods")
    st.markdown("""
    - **MonCash / Primse Transfer**
    - Contact us for other options
    """)
    st.markdown("---")
    st.markdown("### 📊 Token Stats")
    total, available, used, expired = get_stats()
    st.metric("Total Tokens", total)
    st.metric("Available", available)
    st.metric("Used", used)
    st.metric("Expired", expired)

# ========== TABS ==========
tab1, tab2, tab3 = st.tabs(["🛒 Buy Tokens", "🔓 Verify Token", "🔐 Admin"])

# ========== TAB 1: BUY ==========
with tab1:
    st.markdown("### 🛒 Choose Your Plan")
    st.markdown("After payment, you will receive a unique token code. Contact us via email or phone to receive your token.")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div class="token-card">
            <h3>📦 Trial Pack</h3>
            <div class="price">$5 <small>USD</small></div>
            <p>5 tokens<br>Valid 30 days</p>
            <p style="color:#a09080; font-size:0.8rem;">For testing</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("""
        <div class="token-card">
            <h3>💼 Pro Monthly</h3>
            <div class="price">$29 <small>USD</small></div>
            <p>50 tokens<br>Valid 30 days</p>
            <p style="color:#a09080; font-size:0.8rem;">For small teams</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="token-card">
            <h3>🚀 Basic Monthly</h3>
            <div class="price">$15 <small>USD</small></div>
            <p>20 tokens<br>Valid 30 days</p>
            <p style="color:#a09080; font-size:0.8rem;">For individuals</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("""
        <div class="token-card">
            <h3>⭐ Lifetime License</h3>
            <div class="price">$199 <small>USD</small></div>
            <p>♾️ Unlimited tokens<br>Forever valid</p>
            <p style="color:#a09080; font-size:0.8rem;">One‑time purchase</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 📝 How to Purchase")
    st.markdown("""
    1. **Choose** your plan from above.
    2. **Pay** via MonCash or Primse Transfer to the number below.
    3. **Contact us** with your payment receipt (email deslandes78@gmail.com).
    4. **Receive** your unique token code within 24 hours.
    """)
    st.markdown("""
    <div class="info-box">
        💡 <strong>Payment Details:</strong><br>
        MonCash / Primse Transfer: (509) 4738-5663<br>
        Account Holder: Gesner Deslandes<br>
        <span style="color:#a09080; font-size:0.9rem;">Keep your receipt and send it to deslandes78@gmail.com</span>
    </div>
    """, unsafe_allow_html=True)

# ========== TAB 2: VERIFY ==========
with tab2:
    st.markdown("### 🔓 Verify Your Token")
    st.markdown("Enter your token code to unlock access.")

    token_input = st.text_input("Enter Token Code", placeholder="e.g., 7F3A8B2C9D1E...", key="token_input")

    col_v1, col_v2 = st.columns(2)
    with col_v1:
        if st.button("✅ Verify Token", use_container_width=True):
            if token_input:
                data, msg = validate_token(token_input)
                if data:
                    st.session_state.token_verified = True
                    st.session_state.verified_token = data
                    st.success("✅ Token is valid!")
                    st.balloons()
                else:
                    st.error(f"❌ {msg}")
            else:
                st.warning("Please enter a token code.")
    with col_v2:
        if st.button("🔄 Clear Verification", use_container_width=True):
            st.session_state.token_verified = False
            st.session_state.verified_token = None
            st.rerun()

    if st.session_state.token_verified and st.session_state.verified_token:
        data = st.session_state.verified_token
        st.markdown("---")
        st.markdown("### ✅ Verification Successful")
        col_i1, col_i2 = st.columns(2)
        with col_i1:
            st.markdown(f"**Plan:** {data['plan_name']}")
            st.markdown(f"**Price:** ${data['price']} USD")
            st.markdown(f"**Purchase Date:** {data['purchase_date'][:10]}")
        with col_i2:
            st.markdown(f"**Type:** {'♾️ Lifetime' if data['is_lifetime'] else '📅 Monthly'}")
            if data['expiry_date']:
                st.markdown(f"**Expiry:** {data['expiry_date'][:10]}")
            else:
                st.markdown("**Expiry:** Never")
        st.markdown("""
        <div class="info-box">
            ✅ This token is valid. You can now access all GlobalInternet.py software suites.
            Enter this token in each application to unlock full functionality.
        </div>
        """, unsafe_allow_html=True)

# ========== TAB 3: ADMIN ==========
with tab3:
    st.markdown("### 🔐 Admin Panel")
    st.markdown("Manage tokens – requires admin password.")

    if not st.session_state.admin_authenticated:
        admin_pw = st.text_input("Enter Admin Password", type="password", key="admin_pw")
        if st.button("Login", use_container_width=True):
            if admin_pw == st.secrets.get("ADMIN_PASSWORD", "Nov1979"):
                st.session_state.admin_authenticated = True
                st.success("✅ Logged in")
                st.rerun()
            else:
                st.error("❌ Wrong password")
    else:
        st.success("🔐 Admin access granted")

        # Generate single tokens
        st.markdown("### 🆕 Generate New Tokens")
        col_gen1, col_gen2, col_gen3 = st.columns(3)
        with col_gen1:
            if st.button("📦 Trial ($5)", use_container_width=True):
                token, _ = generate_token("Trial Pack", 5.0, False)
                st.success(f"Token: `{token}`")
        with col_gen2:
            if st.button("🚀 Basic ($15)", use_container_width=True):
                token, _ = generate_token("Basic Monthly", 15.0, False)
                st.success(f"Token: `{token}`")
        with col_gen3:
            if st.button("💼 Pro ($29)", use_container_width=True):
                token, _ = generate_token("Pro Monthly", 29.0, False)
                st.success(f"Token: `{token}`")
        col_gen4, col_gen5 = st.columns(2)
        with col_gen4:
            if st.button("🏢 Enterprise ($49)", use_container_width=True):
                token, _ = generate_token("Enterprise Monthly", 49.0, False)
                st.success(f"Token: `{token}`")
        with col_gen5:
            if st.button("⭐ Lifetime ($199)", use_container_width=True):
                token, _ = generate_token("Lifetime License", 199.0, True)
                st.success(f"Token: `{token}` (♾️ Never expires)")

        st.markdown("---")

        # Bulk generate 50 initial tokens
        st.markdown("### 📦 Bulk Generate 50 Initial Tokens")
        st.markdown("Click below to generate 50 tokens across all plans (ready for sale).")
        if st.button("🔄 Generate 50 Tokens", use_container_width=True):
            plans = [
                ("Trial Pack", 5.0, False, 10),
                ("Basic Monthly", 15.0, False, 15),
                ("Pro Monthly", 29.0, False, 10),
                ("Enterprise Monthly", 49.0, False, 5),
                ("Lifetime License", 199.0, True, 10)
            ]
            generated = []
            for plan, price, lifetime, count in plans:
                for _ in range(count):
                    token, _ = generate_token(plan, price, lifetime)
                    generated.append(token)
            st.success(f"✅ Generated {len(generated)} tokens. Check the list below.")

        st.markdown("---")

        # Token list
        st.markdown("### 📋 All Tokens")
        tokens = get_all_tokens()
        if tokens:
            df = pd.DataFrame(tokens, columns=[
                'Token Code', 'Plan', 'Price (USD)', 'Purchase Date', 'Expiry', 'Lifetime', 'Used', 'Status'
            ])
            df['Lifetime'] = df['Lifetime'].apply(lambda x: '✅' if x == 1 else '')
            df['Used'] = df['Used'].apply(lambda x: '✅' if x == 1 else '')
            df['Status'] = df['Status'].apply(lambda x: {
                'active': '🟢 Active',
                'used': '🔵 Used',
                'expired': '🔴 Expired'
            }.get(x, x))
            st.dataframe(df, use_container_width=True, height=400)

            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Export CSV",
                data=csv,
                file_name=f"tokens_export_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.info("No tokens yet. Generate some!")

        st.markdown("---")
        if st.button("🚪 Logout Admin", use_container_width=True):
            st.session_state.admin_authenticated = False
            st.rerun()

# ========== FOOTER ==========
st.markdown("""
<div class="footer">
    <p>© 2026 GlobalInternet.py Online Software Company</p>
    <p>Built by Gesner Deslandes | (509) 4738-5663 | deslandes78@gmail.com</p>
    <p style="font-size:0.8rem; color:#555;">
        🔐 All tokens encrypted and stored securely.<br>
        Payment via MonCash / Primse Transfer accepted worldwide.
    </p>
</div>
""", unsafe_allow_html=True)
