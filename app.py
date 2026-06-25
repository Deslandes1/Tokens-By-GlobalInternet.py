import streamlit as st
import sqlite3
import uuid
import pandas as pd
from datetime import datetime, timedelta
import hashlib
import re
import os
import tempfile

# ---------- Optional imports (graceful fallback) ----------
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

# ---------- Voice generation (gTTS) ----------
try:
    from gtts import gTTS
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False

def generate_audio(text, lang_code="en"):
    """Generate audio from text using gTTS"""
    if not VOICE_AVAILABLE or not text.strip():
        return None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            tmp_path = tmp.name
        tts = gTTS(text=text, lang=lang_code, slow=False)
        tts.save(tmp_path)
        with open(tmp_path, "rb") as f:
            audio_bytes = f.read()
        os.unlink(tmp_path)
        return audio_bytes
    except Exception as e:
        return None

# ========== SECRET RETRIEVAL ==========
def get_secret(key_path, default=None):
    keys = key_path.split('.')
    try:
        value = st.secrets
        for k in keys:
            value = value[k]
        return value
    except (KeyError, TypeError):
        flat_key = "_".join(k.upper() for k in keys)
        try:
            return st.secrets[flat_key]
        except KeyError:
            try:
                return st.secrets[flat_key.lower()]
            except KeyError:
                try:
                    return st.secrets[key_path.replace('.', '_')]
                except KeyError:
                    return default

# ========== PAGE CONFIG ==========
st.set_page_config(
    page_title="Application Tokens | GlobalInternet.py",
    layout="centered",
    page_icon="🔑"
)

# ========== CUSTOM CSS ==========
st.markdown("""
<style>
    .stApp {
        background: #0a0a0f;
        color: #ffffff;
    }
    .main-header {
        text-align: center;
        padding: 20px 0;
        border-bottom: 2px solid #2a1f14;
        margin-bottom: 30px;
    }
    .main-header h1 {
        color: #00ff64;
        font-size: 2.5rem;
        margin: 0;
    }
    .main-header p {
        color: #a09080;
        font-size: 1.1rem;
    }
    .token-card {
        background: rgba(20, 16, 24, 0.8);
        border: 1px solid #2a1f14;
        border-radius: 12px;
        padding: 20px;
        margin: 10px 0;
        text-align: center;
    }
    .token-card h3 {
        color: #00ff64;
        margin: 0;
    }
    .token-card .price {
        font-size: 2rem;
        font-weight: bold;
        color: #ffffff;
    }
    .token-card .price small {
        font-size: 1rem;
        color: #a09080;
    }
    .token-display {
        background: rgba(0, 255, 100, 0.1);
        border: 1px solid #00ff64;
        border-radius: 8px;
        padding: 15px;
        font-family: monospace;
        font-size: 1.2rem;
        word-break: break-all;
        text-align: center;
        color: #00ff64;
        margin: 10px 0;
    }
    .status-badge {
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: bold;
        display: inline-block;
    }
    .status-active {
        background: #2ecc71;
        color: #0a0a0f;
    }
    .status-expired {
        background: #e74c3c;
        color: #ffffff;
    }
    .status-used {
        background: #f39c12;
        color: #0a0a0f;
    }
    .footer {
        text-align: center;
        padding: 20px 0;
        border-top: 1px solid #2a1f14;
        margin-top: 30px;
        color: #a09080;
        font-size: 0.9rem;
    }
    .stButton>button {
        background: linear-gradient(135deg, #00ff64, #00bfff) !important;
        color: #0a0a0f !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 10px 20px !important;
        width: 100% !important;
    }
    .stButton>button:hover {
        transform: scale(1.02);
        box-shadow: 0 0 30px rgba(0, 255, 100, 0.3);
    }
    .stTextInput>div>div>input {
        background-color: #141018 !important;
        color: #ffffff !important;
        border: 1px solid #2a1f14 !important;
        border-radius: 8px !important;
        text-align: center !important;
        font-size: 1.1rem !important;
    }
    .stExpander {
        border: 1px solid #2a1f14 !important;
        border-radius: 8px !important;
    }
    hr {
        border-color: #2a1f14 !important;
        margin: 20px 0 !important;
    }
    .info-box {
        background: rgba(0, 255, 100, 0.05);
        border-left: 4px solid #00ff64;
        padding: 10px 15px;
        border-radius: 4px;
        margin: 10px 0;
        color: #ffffff;
    }
    .sidebar-contact {
        background: rgba(20,16,24,0.8);
        border: 1px solid #2a1f14;
        border-radius: 8px;
        padding: 12px;
        margin: 10px 0;
        font-size: 0.85rem;
    }
    .sidebar-contact strong {
        color: #00ff64;
    }
    [data-testid="stSidebar"] {
        background-color: #0d0d12 !important;
        border-right: 1px solid #2a1f14 !important;
    }
    [data-testid="stSidebar"] .stMarkdown, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] .stCaption {
        color: #ffffff !important;
    }
    .groq-response {
        background: rgba(0, 255, 100, 0.05);
        border: 1px solid #00ff64;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
        color: #ffffff;
        font-family: 'Courier New', monospace;
        white-space: pre-wrap;
    }
    .sidebar-voice-btn {
        background: linear-gradient(135deg, #ff6b9d, #ff2d55) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 30px !important;
        padding: 10px 20px !important;
        font-weight: 600 !important;
        width: 100% !important;
        cursor: pointer !important;
        transition: all 0.3s ease !important;
    }
    .sidebar-voice-btn:hover {
        transform: scale(1.03);
        box-shadow: 0 0 30px rgba(255, 45, 85, 0.4) !important;
    }
    .token-row {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 8px 0;
        border-bottom: 1px solid #2a1f14;
        flex-wrap: wrap;
    }
    .token-code {
        font-family: monospace;
        background: #141018;
        padding: 4px 8px;
        border-radius: 4px;
        color: #00ff64;
        font-size: 0.9rem;
        flex: 1;
        min-width: 150px;
    }
    .token-info {
        color: #a09080;
        font-size: 0.85rem;
    }
    .action-btn {
        background: transparent;
        border: none;
        cursor: pointer;
        font-size: 1.2rem;
        padding: 0 5px;
        color: #ffffff;
        transition: 0.2s;
    }
    .action-btn:hover {
        color: #00ff64;
        transform: scale(1.1);
    }
</style>
""", unsafe_allow_html=True)

# ========== RETRIEVE SECRETS ==========
ADMIN_PASSWORD = get_secret("ADMIN_PASSWORD", "Nov1979")
CONTACT_EMAIL = get_secret("CONTACT_EMAIL", "deslandes78@gmail.com")
CONTACT_PHONE = get_secret("CONTACT_PHONE", "(509) 4738-5663")
WEBSITE = get_secret("WEBSITE", "https://globalinternetsitepyabh7v6tnmskxxnuplrdcgk.streamlit.app/")
MONCASH_NUMBER = get_secret("MONCASH_NUMBER", "(509) 4738-5663")
MONCASH_OWNER = get_secret("MONCASH_OWNER", "Gesner Deslandes")
MONCASH_API_SECRET = get_secret("MONCASH_API_SECRET", "")

# ========== SUPABASE SETUP (optional) ==========
SUPABASE_URL = get_secret("supabase.url")
SUPABASE_KEY = get_secret("supabase.key")

if SUPABASE_URL and SUPABASE_KEY and SUPABASE_AVAILABLE:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        SUPABASE_CONNECTED = True
    except Exception as e:
        st.error(f"⚠️ Supabase connection error: {e}")
        SUPABASE_CONNECTED = False
        supabase = None
else:
    SUPABASE_CONNECTED = False
    supabase = None

# ========== GROQ SETUP (optional) ==========
GROQ_API_KEY = get_secret("GROQ_API_KEY")

if GROQ_API_KEY and GROQ_AVAILABLE:
    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
        GROQ_CONNECTED = True
    except Exception:
        GROQ_CONNECTED = False
        groq_client = None
else:
    GROQ_CONNECTED = False
    groq_client = None

# ========== DATABASE FUNCTIONS (SQLite fallback always works) ==========
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

    if SUPABASE_CONNECTED and supabase:
        try:
            supabase.table('tokens').insert({
                'id': token_id,
                'token_code': token_code,
                'plan_name': plan_name,
                'price': price,
                'purchase_date': now,
                'expiry_date': expiry_date,
                'is_lifetime': lifetime_flag,
                'is_used': 0,
                'status': 'active'
            }).execute()
            return token_code, token_id
        except Exception:
            pass

    init_db()
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
    if SUPABASE_CONNECTED and supabase:
        try:
            res = supabase.table('tokens').select('*').eq('token_code', token_code).execute()
            if not res.data:
                return None, "Token does not exist"
            data = res.data[0]
            if data['is_used']:
                return None, "Token already used"
            if data['status'] != 'active':
                return None, f"Token status: {data['status']}"
            if data['is_lifetime'] == 0 and data['expiry_date']:
                if datetime.now() > datetime.fromisoformat(data['expiry_date']):
                    supabase.table('tokens').update({'status': 'expired'}).eq('id', data['id']).execute()
                    return None, "Token expired"
            return {
                'id': data['id'],
                'plan_name': data['plan_name'],
                'price': data['price'],
                'purchase_date': data['purchase_date'],
                'expiry_date': data['expiry_date'],
                'is_lifetime': data['is_lifetime']
            }, "Valid"
        except Exception:
            pass

    init_db()
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
    if is_lifetime == 0 and expiry_date:
        if datetime.now() > datetime.fromisoformat(expiry_date):
            conn = sqlite3.connect('tokens.db')
            c = conn.cursor()
            c.execute('UPDATE tokens SET status = ? WHERE id = ?', ('expired', token_id))
            conn.commit()
            conn.close()
            return None, "Token expired"
    return {
        'id': token_id,
        'plan_name': plan_name,
        'price': price,
        'purchase_date': purchase_date,
        'expiry_date': expiry_date,
        'is_lifetime': is_lifetime
    }, "Valid"

def use_token(token_code, user_info=None):
    if SUPABASE_CONNECTED and supabase:
        try:
            supabase.table('tokens').update({
                'is_used': 1,
                'used_at': datetime.now().isoformat(),
                'used_by': user_info or 'anonymous',
                'status': 'used'
            }).eq('token_code', token_code).execute()
            return True
        except Exception:
            pass
    init_db()
    conn = sqlite3.connect('tokens.db')
    c = conn.cursor()
    c.execute('UPDATE tokens SET is_used = 1, used_at = ?, used_by = ?, status = "used" WHERE token_code = ?',
              (datetime.now().isoformat(), user_info or 'anonymous', token_code))
    conn.commit()
    conn.close()
    return True

def get_all_tokens():
    if SUPABASE_CONNECTED and supabase:
        try:
            res = supabase.table('tokens').select('*').order('purchase_date', desc=True).execute()
            if res.data:
                return [(d['token_code'], d['plan_name'], d['price'], d['purchase_date'],
                         d['expiry_date'], d['is_lifetime'], d['is_used'], d['status']) for d in res.data]
        except Exception:
            pass
    init_db()
    conn = sqlite3.connect('tokens.db')
    c = conn.cursor()
    c.execute('SELECT token_code, plan_name, price, purchase_date, expiry_date, is_lifetime, is_used, status FROM tokens ORDER BY purchase_date DESC')
    results = c.fetchall()
    conn.close()
    return results

def get_stats():
    if SUPABASE_CONNECTED and supabase:
        try:
            total = len(supabase.table('tokens').select('id').execute().data)
            available = len(supabase.table('tokens').select('id').eq('is_used', 0).eq('status', 'active').execute().data)
            used = len(supabase.table('tokens').select('id').eq('is_used', 1).execute().data)
            expired = len(supabase.table('tokens').select('id').eq('status', 'expired').execute().data)
            return total, available, used, expired
        except Exception:
            pass
    init_db()
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

def delete_token(token_code, admin_password):
    if admin_password != ADMIN_PASSWORD:
        return False, "Invalid admin password"
    if SUPABASE_CONNECTED and supabase:
        try:
            supabase.table('tokens').delete().eq('token_code', token_code).execute()
            return True, f"Token {token_code} deleted from Supabase"
        except Exception:
            pass
    init_db()
    conn = sqlite3.connect('tokens.db')
    c = conn.cursor()
    c.execute('DELETE FROM tokens WHERE token_code = ?', (token_code,))
    deleted = c.rowcount > 0
    conn.commit()
    conn.close()
    return deleted, f"Token {token_code} deleted from SQLite" if deleted else "Token not found"

def get_ai_analysis(token_code=None):
    if not GROQ_CONNECTED or not groq_client:
        return "Groq AI is not available. Please add your GROQ_API_KEY to secrets."
    try:
        token_info = ""
        if token_code:
            data, msg = validate_token(token_code)
            if data:
                token_info = f"Token: {token_code}\nPlan: {data['plan_name']}\nPrice: ${data['price']}\nPurchase: {data['purchase_date']}\nExpiry: {data['expiry_date'] or 'Never (Lifetime)'}\nType: {'Lifetime' if data['is_lifetime'] else 'Monthly'}"
        total, available, used, expired = get_stats()
        stats_info = f"Total: {total}\nAvailable: {available}\nUsed: {used}\nExpired: {expired}"
        prompt = f"You are a business analyst for a software token platform. Analyze:\n\nToken info: {token_info}\nStats: {stats_info}\nProvide concise, actionable insights about inventory, pricing, and marketing."
        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": "You are a business analyst."}, {"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ AI error: {str(e)}"

# ========== VOICE SCRIPT FOR THE OWNER ==========
def get_owner_voice_script():
    return f"""
Welcome, Gesner Deslandes, to your Application Tokens business dashboard.

This is your token sales platform built by GlobalInternet.py.

Here is how this business works.

First, you generate unique token codes using the Admin panel. Each token represents access to your software products. You set the price and the validity period for each token.

Second, you sell these tokens to customers. They pay you via MonCash or Primse Transfer using the phone number {MONCASH_NUMBER}. Once they pay, you manually send them the token code.

Third, customers use the token by entering it in the Verify Token tab. The app checks if the token is valid, unused, and not expired. If everything is correct, the customer gets access to your software.

The token codes are secure, unique, and stored either in your local SQLite database or in Supabase if you have it connected. You can also use the Groq AI to analyze your token sales and get business recommendations.

You have five pricing plans. The Trial Pack at 5 dollars for 5 tokens. Basic Monthly at 15 dollars for 20 tokens. Pro Monthly at 29 dollars for 50 tokens. Enterprise Monthly at 49 dollars for 100 tokens. And Lifetime License at 199 dollars for unlimited tokens forever.

To run this app, you simply deploy it on Streamlit Cloud using the GitHub repository. All your secrets like admin password, contact info, and payment details are stored securely in Streamlit's secrets manager. No sensitive data is exposed in the code.

You, as the owner, have full control. You can generate tokens one by one or in bulk, export the entire token list as a CSV file, delete expired or unused tokens, and monitor your inventory in real time.

The tokens themselves are used by your customers to unlock any software product you offer – voting systems, dashboards, AI tools, chatbots, school management, drone control, music production, and more. Each token gives the customer a license to use that product.

Your revenue comes directly from token sales. No third-party fees, no subscriptions to worry about – just you, your customers, and your software.

Everything is encrypted, secure, and built to scale. As your business grows, you can add more tokens, more plans, and integrate with Supabase for cloud storage.

This is your business, your software, and your future.

Welcome to GlobalInternet.py – connecting the global market with local expertise.

Thank you for choosing GlobalInternet.py. We are the best online software company ever.
"""

# ---------- Init DB ----------
init_db()

# ========== SESSION STATE ==========
if 'admin_authenticated' not in st.session_state:
    st.session_state.admin_authenticated = False
if 'token_verified' not in st.session_state:
    st.session_state.token_verified = False
if 'verified_token' not in st.session_state:
    st.session_state.verified_token = None
if 'ai_response' not in st.session_state:
    st.session_state.ai_response = ""
if 'last_generated' not in st.session_state:
    st.session_state.last_generated = None
if 'last_plan' not in st.session_state:
    st.session_state.last_plan = ""
if 'last_price' not in st.session_state:
    st.session_state.last_price = ""
if 'last_expiry' not in st.session_state:
    st.session_state.last_expiry = ""

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
    st.markdown(f"""
    <div class="sidebar-contact">
        <strong>Email:</strong> {CONTACT_EMAIL}<br>
        <strong>Phone:</strong> {CONTACT_PHONE}<br>
        <strong>Website:</strong> <a href="{WEBSITE}" style="color:#00ff64;" target="_blank">globalinternet-py.com</a>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("### 🎤 AI Assistant")
    st.markdown("Get a voice explanation about this token business.")
    
    voice_clicked = st.button("🎤 AI Female Voice – Explain Token Business", use_container_width=True)
    
    if voice_clicked:
        script = get_owner_voice_script()
        with st.spinner("🎤 Generating voice explanation..."):
            audio_bytes = generate_audio(script, "en")
            if audio_bytes:
                st.audio(audio_bytes, format="audio/mp3")
                st.success("✅ Voice explanation played. Click again to repeat.")
            else:
                st.error("❌ Voice generation failed. Please ensure gTTS is installed.")
    
    st.markdown("---")
    
    # Voice language selector for AI analysis reading
    voice_lang = st.selectbox(
        "🎤 Voice Language for Analysis",
        options=["en", "fr", "es", "zh"],
        format_func=lambda x: {"en": "English", "fr": "Français", "es": "Español", "zh": "中文"}.get(x, x),
        key="voice_lang_analysis"
    )
    
    st.markdown("---")
    
    st.markdown("### 💳 Payment Methods")
    st.markdown(f"""
    - **MonCash / Primse Transfer:** {MONCASH_NUMBER}
    - Account Holder: {MONCASH_OWNER}
    - Contact us for other options
    """)
    
    st.markdown("---")
    
    st.markdown("### 📊 Token Stats")
    total, available, used, expired = get_stats()
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Total", total)
        st.metric("Available", available)
    with c2:
        st.metric("Used", used)
        st.metric("Expired", expired)
    
    st.markdown("---")
    
    st.markdown("### 🔌 Services Status")
    if SUPABASE_CONNECTED:
        st.success("✅ Supabase Connected")
    else:
        st.info("ℹ️ Using SQLite (local storage)")
    if GROQ_CONNECTED:
        st.success("✅ Groq Connected")
    else:
        st.info("ℹ️ AI analysis disabled (no GROQ_API_KEY)")
    if VOICE_AVAILABLE:
        st.success("✅ Voice available (gTTS)")
    else:
        st.warning("⚠️ Voice unavailable (install gTTS)")
    
    st.markdown("---")
    st.markdown("### 🔐 Security")
    st.markdown("All tokens are encrypted and stored securely.")

# ========== TABS ==========
tab_buy, tab_verify, tab_ai, tab_admin = st.tabs(["🛒 Buy Tokens", "🔓 Verify Token", "🤖 AI Analysis", "🔐 Admin"])

# ---------- BUY TOKENS ----------
with tab_buy:
    st.markdown("### 🛒 Choose Your Plan")
    st.markdown("After payment, you will receive a unique token code. Contact us via email or phone to receive your token.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="token-card">
            <h3>📦 Trial Pack</h3>
            <div class="price">$5 <small>USD</small></div>
            <p>5 tokens<br>Valid 30 days</p>
            <p style="color:#a09080;font-size:0.8rem;">For testing</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="token-card">
            <h3>💼 Pro Monthly</h3>
            <div class="price">$29 <small>USD</small></div>
            <p>50 tokens<br>Valid 30 days</p>
            <p style="color:#a09080;font-size:0.8rem;">For small teams</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="token-card">
            <h3>🚀 Basic Monthly</h3>
            <div class="price">$15 <small>USD</small></div>
            <p>20 tokens<br>Valid 30 days</p>
            <p style="color:#a09080;font-size:0.8rem;">For individuals</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="token-card">
            <h3>⭐ Lifetime License</h3>
            <div class="price">$199 <small>USD</small></div>
            <p>♾️ Unlimited tokens<br>Forever valid</p>
            <p style="color:#a09080;font-size:0.8rem;">One‑time purchase</p>
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
    
    st.markdown(f"""
    <div class="info-box">
        💡 <strong>Payment Details:</strong><br>
        MonCash / Primse Transfer: {MONCASH_NUMBER}<br>
        Account Holder: {MONCASH_OWNER}<br>
        <span style="color:#a09080;font-size:0.9rem;">Keep your receipt and send it to {CONTACT_EMAIL}</span>
    </div>
    """, unsafe_allow_html=True)

# ---------- VERIFY TOKEN ----------
with tab_verify:
    st.markdown("### 🔓 Verify Your Token")
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
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🔒 Mark as Used (Testing Only)"):
            use_token(token_input, "demo_user")
            st.success("Token marked as used")
            st.rerun()

# ---------- AI ANALYSIS ----------
with tab_ai:
    st.markdown("### 🤖 AI Token Analysis")
    st.markdown("Get AI-powered insights about your token inventory using Groq.")
    
    if not GROQ_CONNECTED:
        st.info("ℹ️ Groq AI is not configured. To enable, add your `GROQ_API_KEY` to secrets. The app will then show AI insights here.")
    else:
        # Buttons for analysis
        col_ai1, col_ai2 = st.columns(2)
        with col_ai1:
            if st.button("📊 Analyze Token Stats", use_container_width=True):
                with st.spinner("🤖 AI is analyzing..."):
                    st.session_state.ai_response = get_ai_analysis()
        with col_ai2:
            token_code_for_ai = st.text_input("Or analyze a specific token:", placeholder="Enter token code", key="ai_token_input")
            if st.button("🔍 Analyze Specific Token", use_container_width=True):
                if token_code_for_ai:
                    with st.spinner("🤖 AI is analyzing token..."):
                        st.session_state.ai_response = get_ai_analysis(token_code_for_ai)
                else:
                    st.warning("Please enter a token code.")
        
        # Display AI response
        if st.session_state.ai_response:
            st.markdown("### 💡 AI Insights")
            st.markdown(f'<div class="groq-response">{st.session_state.ai_response}</div>', unsafe_allow_html=True)
            
            # ----- NEW: Listen to Analysis Button -----
            if st.button("🔊 Listen to Analysis", use_container_width=True):
                with st.spinner("🎤 Generating audio..."):
                    # Get the current voice language from sidebar
                    lang_code = voice_lang if 'voice_lang' in locals() else "en"
                    # Map language codes to gTTS supported codes: 'zh' for Chinese
                    if lang_code == "zh":
                        lang_code = "zh-CN"  # gTTS supports 'zh' as well, but let's keep it
                    audio_bytes = generate_audio(st.session_state.ai_response, lang_code)
                    if audio_bytes:
                        st.audio(audio_bytes, format="audio/mp3")
                        st.success("✅ Analysis played. Click again to repeat.")
                    else:
                        st.error("❌ Voice generation failed. Please ensure gTTS is installed.")
        else:
            st.info("No analysis yet. Click one of the buttons above to generate insights.")

# ---------- ADMIN ----------
with tab_admin:
    st.markdown("### 🔐 Admin Panel")
    st.markdown("Manage tokens – requires admin password.")
    
    if not st.session_state.admin_authenticated:
        admin_pw = st.text_input("Enter Admin Password", type="password", key="admin_pw")
        if st.button("Login", use_container_width=True):
            if admin_pw == ADMIN_PASSWORD:
                st.session_state.admin_authenticated = True
                st.success("✅ Logged in successfully")
                st.rerun()
            else:
                st.error("❌ Wrong password")
    else:
        st.success("🔐 Admin access granted")
        
        # ---------- GENERATE NEW TOKENS (with download) ----------
        st.markdown("### 🆕 Generate New Tokens")
        col_gen1, col_gen2, col_gen3 = st.columns(3)
        with col_gen1:
            if st.button("📦 Trial ($5)", use_container_width=True):
                token, _ = generate_token("Trial Pack", 5.0, False)
                st.session_state.last_generated = token
                st.session_state.last_plan = "Trial Pack"
                st.session_state.last_price = "$5.00"
                st.session_state.last_expiry = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
                st.rerun()
        with col_gen2:
            if st.button("🚀 Basic ($15)", use_container_width=True):
                token, _ = generate_token("Basic Monthly", 15.0, False)
                st.session_state.last_generated = token
                st.session_state.last_plan = "Basic Monthly"
                st.session_state.last_price = "$15.00"
                st.session_state.last_expiry = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
                st.rerun()
        with col_gen3:
            if st.button("💼 Pro ($29)", use_container_width=True):
                token, _ = generate_token("Pro Monthly", 29.0, False)
                st.session_state.last_generated = token
                st.session_state.last_plan = "Pro Monthly"
                st.session_state.last_price = "$29.00"
                st.session_state.last_expiry = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
                st.rerun()
        
        col_gen4, col_gen5 = st.columns(2)
        with col_gen4:
            if st.button("🏢 Enterprise ($49)", use_container_width=True):
                token, _ = generate_token("Enterprise Monthly", 49.0, False)
                st.session_state.last_generated = token
                st.session_state.last_plan = "Enterprise Monthly"
                st.session_state.last_price = "$49.00"
                st.session_state.last_expiry = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
                st.rerun()
        with col_gen5:
            if st.button("⭐ Lifetime ($199)", use_container_width=True):
                token, _ = generate_token("Lifetime License", 199.0, True)
                st.session_state.last_generated = token
                st.session_state.last_plan = "Lifetime License"
                st.session_state.last_price = "$199.00"
                st.session_state.last_expiry = "Never"
                st.rerun()
        
        # Display last generated token with download button
        if st.session_state.last_generated:
            st.markdown("---")
            st.markdown("### 🎯 Last Generated Token")
            col_display, col_download = st.columns([3, 1])
            with col_display:
                st.code(st.session_state.last_generated, language="text")
                st.caption(f"Plan: {st.session_state.last_plan} | Price: {st.session_state.last_price} | Expiry: {st.session_state.last_expiry}")
            with col_download:
                token_content = f"""
Token Code: {st.session_state.last_generated}
Plan: {st.session_state.last_plan}
Price: {st.session_state.last_price}
Expiry: {st.session_state.last_expiry}
Purchase Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}
---
This token grants access to GlobalInternet.py software.
Keep this code secure and share it only with the buyer.
"""
                st.download_button(
                    label="📥 Download Token",
                    data=token_content,
                    file_name=f"token_{st.session_state.last_generated[:8]}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
        
        st.markdown("---")
        
        st.markdown("### 📦 Bulk Generate 50 Initial Tokens")
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
            st.success(f"✅ Generated {len(generated)} tokens.")
        
        st.markdown("---")
        
        # ---------- ALL TOKENS LIST (with copy & delete) ----------
        st.markdown("### 📋 All Tokens")
        tokens = get_all_tokens()
        
        if tokens:
            for idx, token_data in enumerate(tokens):
                token_code, plan, price, purchase_date, expiry, lifetime, used, status = token_data
                
                col_code, col_plan, col_status, col_expiry, col_copy, col_delete = st.columns([2.5, 1.5, 1, 1, 0.6, 0.6])
                
                with col_code:
                    st.code(token_code, language="text")
                
                with col_plan:
                    st.write(f"{plan}")
                    st.caption(f"${price:.2f} USD")
                
                with col_status:
                    status_emoji = {
                        'active': '🟢',
                        'used': '🔵',
                        'expired': '🔴'
                    }.get(status, '⚪')
                    st.write(f"{status_emoji} {status.title()}")
                
                with col_expiry:
                    if expiry:
                        st.write(expiry[:10])
                    else:
                        st.write("Never")
                
                with col_copy:
                    copy_html = f"""
                    <button onclick="navigator.clipboard.writeText('{token_code}').then(() => alert('Token copied to clipboard!'))" style="background:transparent; border:none; cursor:pointer; font-size:1.4rem; color:#00ff64;">📋</button>
                    """
                    st.markdown(copy_html, unsafe_allow_html=True)
                
                with col_delete:
                    if st.button("🗑️", key=f"del_{idx}"):
                        ok, msg = delete_token(token_code, ADMIN_PASSWORD)
                        if ok:
                            st.toast(f"✅ Token {token_code} deleted", icon="🗑️")
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")
                
                st.markdown("---")
        else:
            st.info("No tokens yet. Generate some!")
        
        st.markdown("---")
        
        # ---------- EXPORT CSV ----------
        if tokens:
            df = pd.DataFrame(tokens, columns=['Token Code', 'Plan', 'Price (USD)', 'Purchase Date', 'Expiry', 'Lifetime', 'Used', 'Status'])
            df['Lifetime'] = df['Lifetime'].apply(lambda x: '✅' if x == 1 else '')
            df['Used'] = df['Used'].apply(lambda x: '✅' if x == 1 else '')
            df['Status'] = df['Status'].apply(lambda x: {'active': '🟢 Active', 'used': '🔵 Used', 'expired': '🔴 Expired'}.get(x, x))
            csv = df.to_csv(index=False)
            st.download_button(
                "📥 Export CSV (All Tokens)",
                csv,
                f"tokens_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "text/csv",
                use_container_width=True
            )
            st.markdown("---")
        
        # ---------- DELETE BY MANUAL INPUT ----------
        st.markdown("### 🗑️ Delete Token by Code (Manual)")
        del_code = st.text_input("Enter token code to delete:", key="del_token")
        if st.button("Delete Token", use_container_width=True):
            del_code_clean = del_code.strip() if del_code else ""
            if del_code_clean:
                ok, msg = delete_token(del_code_clean, ADMIN_PASSWORD)
                if ok:
                    st.toast(f"✅ Token {del_code_clean} was removed", icon="🗑️")
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")
            else:
                st.warning("Please enter a token code.")
        
        st.markdown("---")
        
        if st.button("🚪 Logout Admin", use_container_width=True):
            st.session_state.admin_authenticated = False
            st.rerun()

# ========== FOOTER ==========
st.markdown(f"""
<div class="footer">
    <p>© 2026 GlobalInternet.py Online Software Company</p>
    <p>Built by <strong>Gesner Deslandes</strong> | {CONTACT_PHONE} | {CONTACT_EMAIL}</p>
    <p style="font-size:0.8rem; color:#555;">🔐 All tokens encrypted and stored securely. Payment via MonCash / Primse Transfer accepted worldwide.</p>
</div>
""", unsafe_allow_html=True)
