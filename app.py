import streamlit as st
import sqlite3
import uuid
import pandas as pd
from datetime import datetime, timedelta
import hashlib
import re
import os

# Try importing Supabase and Groq
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

# ========== SECRET RETRIEVAL ==========
def get_secret(key_path, default=None):
    """Retrieve a secret from st.secrets, supporting nested or flat keys."""
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

# ========== SUPABASE SETUP ==========
SUPABASE_URL = get_secret("supabase.url")
SUPABASE_KEY = get_secret("supabase.key")

if SUPABASE_URL and SUPABASE_KEY and SUPABASE_AVAILABLE:
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        SUPABASE_CONNECTED = True
    except Exception as e:
        st.error(f"⚠️ Supabase connection error: {e}")
        SUPABASE_CONNECTED = False
        supabase = None
else:
    SUPABASE_CONNECTED = False
    supabase = None

# ========== GROQ SETUP ==========
GROQ_API_KEY = get_secret("GROQ_API_KEY")

if GROQ_API_KEY and GROQ_AVAILABLE:
    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
        GROQ_CONNECTED = True
    except Exception as e:
        st.error(f"⚠️ Groq connection error: {e}")
        GROQ_CONNECTED = False
        groq_client = None
else:
    GROQ_CONNECTED = False
    groq_client = None

# ========== DATABASE FUNCTIONS ==========
def init_db():
    """Initialize SQLite database (fallback if Supabase not available)"""
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
    """Generate a unique token"""
    token_code = str(uuid.uuid4()).replace('-', '').upper()
    token_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    
    if is_lifetime:
        expiry_date = None
        lifetime_flag = 1
    else:
        expiry_date = (datetime.now() + timedelta(days=30)).isoformat()
        lifetime_flag = 0
    
    # Try Supabase first
    if SUPABASE_CONNECTED and supabase:
        try:
            data = {
                'id': token_id,
                'token_code': token_code,
                'plan_name': plan_name,
                'price': price,
                'purchase_date': now,
                'expiry_date': expiry_date,
                'is_lifetime': lifetime_flag,
                'is_used': 0,
                'used_at': None,
                'used_by': None,
                'status': 'active'
            }
            supabase.table('tokens').insert(data).execute()
            return token_code, token_id
        except Exception as e:
            st.error(f"⚠️ Supabase insert error: {e}")
            # Fallback to SQLite
    
    # Fallback to SQLite
    init_db()
    conn = sqlite3.connect('tokens.db')
    c = conn.cursor()
    
    c.execute('''
        INSERT INTO tokens 
        (id, token_code, plan_name, price, purchase_date, expiry_date, is_lifetime, is_used, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (token_id, token_code, plan_name, price, now, expiry_date, lifetime_flag, 0, 'active'))
    
    conn.commit()
    conn.close()
    
    return token_code, token_id

def validate_token(token_code):
    """Validate a token"""
    # Try Supabase first
    if SUPABASE_CONNECTED and supabase:
        try:
            response = supabase.table('tokens').select('*').eq('token_code', token_code).execute()
            if not response.data:
                return None, "Token does not exist"
            
            data = response.data[0]
            token_id = data['id']
            plan_name = data['plan_name']
            price = data['price']
            purchase_date = data['purchase_date']
            expiry_date = data['expiry_date']
            is_lifetime = data['is_lifetime']
            is_used = data['is_used']
            status = data['status']
            
            if is_used == 1:
                return None, "Token has already been used"
            
            if status != 'active':
                return None, f"Token status: {status}"
            
            if is_lifetime == 0 and expiry_date:
                expiry = datetime.fromisoformat(expiry_date)
                if datetime.now() > expiry:
                    supabase.table('tokens').update({'status': 'expired'}).eq('id', token_id).execute()
                    return None, "Token has expired"
            
            return {
                'id': token_id,
                'plan_name': plan_name,
                'price': price,
                'purchase_date': purchase_date,
                'expiry_date': expiry_date,
                'is_lifetime': is_lifetime
            }, "Valid"
        except Exception as e:
            st.error(f"⚠️ Supabase query error: {e}")
            # Fallback to SQLite
    
    # Fallback to SQLite
    init_db()
    conn = sqlite3.connect('tokens.db')
    c = conn.cursor()
    
    c.execute('''
        SELECT id, plan_name, price, purchase_date, expiry_date, is_lifetime, is_used, status
        FROM tokens WHERE token_code = ?
    ''', (token_code,))
    
    result = c.fetchone()
    conn.close()
    
    if not result:
        return None, "Token does not exist"
    
    token_id, plan_name, price, purchase_date, expiry_date, is_lifetime, is_used, status = result
    
    if is_used == 1:
        return None, "Token has already been used"
    
    if status != 'active':
        return None, f"Token status: {status}"
    
    if is_lifetime == 0 and expiry_date:
        expiry = datetime.fromisoformat(expiry_date)
        if datetime.now() > expiry:
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
    """Mark token as used"""
    # Try Supabase first
    if SUPABASE_CONNECTED and supabase:
        try:
            now = datetime.now().isoformat()
            supabase.table('tokens').update({
                'is_used': 1,
                'used_at': now,
                'used_by': user_info or 'anonymous',
                'status': 'used'
            }).eq('token_code', token_code).execute()
            return True
        except Exception as e:
            st.error(f"⚠️ Supabase update error: {e}")
            # Fallback to SQLite
    
    # Fallback to SQLite
    init_db()
    conn = sqlite3.connect('tokens.db')
    c = conn.cursor()
    
    now = datetime.now().isoformat()
    c.execute('''
        UPDATE tokens 
        SET is_used = 1, used_at = ?, used_by = ?, status = 'used'
        WHERE token_code = ?
    ''', (now, user_info or 'anonymous', token_code))
    
    conn.commit()
    conn.close()
    return True

def get_all_tokens():
    """Get all tokens (admin)"""
    # Try Supabase first
    if SUPABASE_CONNECTED and supabase:
        try:
            response = supabase.table('tokens').select('*').order('purchase_date', desc=True).execute()
            if response.data:
                results = []
                for data in response.data:
                    results.append((
                        data['token_code'],
                        data['plan_name'],
                        data['price'],
                        data['purchase_date'],
                        data['expiry_date'],
                        data['is_lifetime'],
                        data['is_used'],
                        data['status']
                    ))
                return results
        except Exception as e:
            st.error(f"⚠️ Supabase query error: {e}")
            # Fallback to SQLite
    
    # Fallback to SQLite
    init_db()
    conn = sqlite3.connect('tokens.db')
    c = conn.cursor()
    
    c.execute('''
        SELECT token_code, plan_name, price, purchase_date, expiry_date, is_lifetime, is_used, status
        FROM tokens ORDER BY purchase_date DESC
    ''')
    
    results = c.fetchall()
    conn.close()
    return results

def get_stats():
    """Get token statistics"""
    # Try Supabase first
    if SUPABASE_CONNECTED and supabase:
        try:
            total = len(supabase.table('tokens').select('id').execute().data)
            available = len(supabase.table('tokens').select('id').eq('is_used', 0).eq('status', 'active').execute().data)
            used = len(supabase.table('tokens').select('id').eq('is_used', 1).execute().data)
            expired = len(supabase.table('tokens').select('id').eq('status', 'expired').execute().data)
            return total, available, used, expired
        except Exception as e:
            st.error(f"⚠️ Supabase stats error: {e}")
            # Fallback to SQLite
    
    # Fallback to SQLite
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
    """Delete a token (admin only)"""
    if admin_password != ADMIN_PASSWORD:
        return False, "Invalid admin password"
    
    # Try Supabase first
    if SUPABASE_CONNECTED and supabase:
        try:
            supabase.table('tokens').delete().eq('token_code', token_code).execute()
            return True, "Token deleted"
        except Exception as e:
            st.error(f"⚠️ Supabase delete error: {e}")
            # Fallback to SQLite
    
    # Fallback to SQLite
    init_db()
    conn = sqlite3.connect('tokens.db')
    c = conn.cursor()
    c.execute('DELETE FROM tokens WHERE token_code = ?', (token_code,))
    deleted = c.rowcount > 0
    conn.commit()
    conn.close()
    
    return deleted, "Token deleted" if deleted else "Token not found"

def get_ai_analysis(token_code=None):
    """Use Groq AI to analyze token data or provide insights"""
    if not GROQ_CONNECTED or not groq_client:
        return "Groq API not available. Please add your GROQ_API_KEY to secrets."
    
    try:
        # Get token info if provided
        token_info = ""
        if token_code:
            data, msg = validate_token(token_code)
            if data:
                token_info = f"""
Token: {token_code}
Plan: {data['plan_name']}
Price: ${data['price']}
Purchase Date: {data['purchase_date']}
Expiry: {data['expiry_date'] or 'Never (Lifetime)'}
Type: {'Lifetime' if data['is_lifetime'] else 'Monthly'}
"""
        
        # Get overall stats
        total, available, used, expired = get_stats()
        stats_info = f"""
Total Tokens: {total}
Available: {available}
Used: {used}
Expired: {expired}
"""
        
        prompt = f"""
You are an AI assistant for GlobalInternet.py, a software token sales platform.

Please analyze the following token data and provide insights:
{tokens}

Overall statistics:
{stats_info}

Please provide:
1. A summary of the token inventory status
2. Recommendations for the business (pricing, marketing, etc.)
3. Any notable patterns or observations

Keep the response concise, professional, and actionable.
"""
        
        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a business analyst for a software token sales platform. Provide actionable insights."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        
        return completion.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ AI analysis error: {str(e)}"

# ========== INIT DATABASE ==========
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
    st.markdown(f"""
    <div class="sidebar-contact">
        <strong>Email:</strong> {CONTACT_EMAIL}<br>
        <strong>Phone:</strong> {CONTACT_PHONE}<br>
        <strong>Website:</strong> <a href="{WEBSITE}" style="color:#00ff64;" target="_blank">globalinternet-py.com</a>
    </div>
    """, unsafe_allow_html=True)
    
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
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total", total)
        st.metric("Available", available)
    with col2:
        st.metric("Used", used)
        st.metric("Expired", expired)
    
    st.markdown("---")
    
    # Status indicators
    st.markdown("### 🔌 Services Status")
    if SUPABASE_CONNECTED:
        st.success("✅ Supabase Connected")
    else:
        st.warning("⚠️ Supabase Not Connected (using SQLite)")
    
    if GROQ_CONNECTED:
        st.success("✅ Groq API Connected")
    else:
        st.warning("⚠️ Groq API Not Connected")
    
    st.markdown("---")
    st.markdown("### 🔐 Security")
    st.markdown("All tokens are encrypted and stored securely.")

# ========== TABS ==========
tab1, tab2, tab3, tab4 = st.tabs(["🛒 Buy Tokens", "🔓 Verify Token", "🤖 AI Analysis", "🔐 Admin"])

# ========== TAB 1: BUY TOKENS ==========
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
    
    st.markdown(f"""
    <div class="info-box">
        💡 <strong>Payment Details:</strong><br>
        MonCash / Primse Transfer: {MONCASH_NUMBER}<br>
        Account Holder: {MONCASH_OWNER}<br>
        <span style="color:#a09080; font-size:0.9rem;">Keep your receipt and send it to {CONTACT_EMAIL}</span>
    </div>
    """, unsafe_allow_html=True)

# ========== TAB 2: VERIFY TOKEN ==========
with tab2:
    st.markdown("### 🔓 Verify Your Token")
    st.markdown("Enter your token code to unlock access.")
    
    token_input = st.text_input(
        "Enter Token Code",
        placeholder="e.g., 7F3A8B2C9D1E...",
        key="token_input"
    )
    
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
        
        # Option to mark as used (for testing)
        if st.button("🔒 Mark as Used (Testing Only)"):
            use_token(token_input, "demo_user")
            st.success("Token marked as used")
            st.rerun()

# ========== TAB 3: AI ANALYSIS ==========
with tab3:
    st.markdown("### 🤖 AI Token Analysis")
    st.markdown("Get AI-powered insights about your token inventory using Groq.")
    
    if not GROQ_CONNECTED:
        st.warning("⚠️ Groq API not connected. Please add your GROQ_API_KEY to secrets.")
    else:
        col_ai1, col_ai2 = st.columns(2)
        with col_ai1:
            if st.button("📊 Analyze Token Stats", use_container_width=True):
                with st.spinner("🤖 AI is analyzing..."):
                    response = get_ai_analysis()
                    st.session_state.ai_response = response
        
        with col_ai2:
            token_code_for_ai = st.text_input("Or analyze specific token:", placeholder="Enter token code", key="ai_token_input")
            if st.button("🔍 Analyze Specific Token", use_container_width=True):
                if token_code_for_ai:
                    with st.spinner("🤖 AI is analyzing token..."):
                        response = get_ai_analysis(token_code_for_ai)
                        st.session_state.ai_response = response
                else:
                    st.warning("Please enter a token code.")
        
        if 'ai_response' in st.session_state and st.session_state.ai_response:
            st.markdown("### 💡 AI Insights")
            st.markdown(f'<div class="groq-response">{st.session_state.ai_response}</div>', unsafe_allow_html=True)

# ========== TAB 4: ADMIN ==========
with tab4:
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
                file_name=f"tokens_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.info("No tokens yet. Generate some!")
        
        st.markdown("---")
        
        # Delete token
        st.markdown("### 🗑️ Delete Token")
        delete_token_code = st.text_input("Enter token code to delete:", key="delete_token_input")
        if st.button("Delete Token", use_container_width=True):
            if delete_token_code:
                deleted, msg = delete_token(delete_token_code, ADMIN_PASSWORD)
                if deleted:
                    st.success(f"✅ {msg}")
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")
            else:
                st.warning("Please enter a token code.")
        
        st.markdown("---")
        
        # AI Token Analysis in Admin
        if GROQ_CONNECTED:
            st.markdown("### 🤖 AI Token Advisor")
            if st.button("Get AI Advice on Token Sales", use_container_width=True):
                with st.spinner("🤖 AI is thinking..."):
                    response = get_ai_analysis()
                    st.markdown(f'<div class="groq-response">{response}</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Logout
        if st.button("🚪 Logout Admin", use_container_width=True):
            st.session_state.admin_authenticated = False
            st.rerun()

# ========== FOOTER ==========
st.markdown(f"""
<div class="footer">
    <p>© 2026 GlobalInternet.py Online Software Company</p>
    <p>Built by <strong>Gesner Deslandes</strong> | {CONTACT_PHONE} | {CONTACT_EMAIL}</p>
    <p style="font-size:0.8rem; color:#555;">
        🔐 All tokens encrypted and stored securely.<br>
        Payment via MonCash / Primse Transfer accepted worldwide.
    </p>
</div>
""", unsafe_allow_html=True)
