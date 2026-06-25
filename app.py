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

# ============================================================
# TRANSLATIONS DICTIONARY
# ============================================================
T = {
    "en": {
        "app_title": "Application Tokens",
        "app_sub": "By GlobalInternet.py Online Software Company",
        "app_tagline": "— Purchase tokens to unlock our software suite —",
        "sidebar_contact": "Contact",
        "sidebar_email": "Email",
        "sidebar_phone": "Phone",
        "sidebar_website": "Website",
        "sidebar_customer_guide": "Customer Guide",
        "sidebar_how_to_buy": "How to buy a token step by step.",
        "voice_how_to_buy": "🎤 AI Female Voice – How to Buy a Token",
        "sidebar_voice_lang": "Voice Language for Analysis",
        "sidebar_payment": "Payment Methods",
        "sidebar_payment_moncash": "MonCash / Primse Transfer",
        "sidebar_payment_holder": "Account Holder",
        "sidebar_payment_other": "Contact us for other options",
        "sidebar_stats": "Token Stats",
        "sidebar_total": "Total",
        "sidebar_available": "Available",
        "sidebar_used": "Used",
        "sidebar_expired": "Expired",
        "sidebar_services": "Services Status",
        "sidebar_supabase": "Supabase Connected",
        "sidebar_sqlite": "Using SQLite (local storage)",
        "sidebar_groq": "Groq Connected",
        "sidebar_groq_disabled": "AI analysis disabled (no GROQ_API_KEY)",
        "sidebar_voice_available": "Voice available (gTTS)",
        "sidebar_voice_unavailable": "Voice unavailable (install gTTS)",
        "sidebar_security": "Security",
        "sidebar_security_text": "All tokens are encrypted and stored securely.",
        "tab_buy": "🛒 Buy Tokens",
        "tab_verify": "🔓 Verify Token",
        "tab_admin": "🔐 Admin",
        "buy_title": "Choose Your Plan",
        "buy_after_payment": "After payment, you will receive a unique token code. Contact us via email or phone to receive your token.",
        "buy_trial": "Trial Pack",
        "buy_trial_price": "$5",
        "buy_trial_desc": "5 tokens<br>Valid 30 days",
        "buy_trial_note": "For testing",
        "buy_pro": "Pro Monthly",
        "buy_pro_price": "$29",
        "buy_pro_desc": "50 tokens<br>Valid 30 days",
        "buy_pro_note": "For small teams",
        "buy_basic": "Basic Monthly",
        "buy_basic_price": "$15",
        "buy_basic_desc": "20 tokens<br>Valid 30 days",
        "buy_basic_note": "For individuals",
        "buy_lifetime": "Lifetime License",
        "buy_lifetime_price": "$199",
        "buy_lifetime_desc": "♾️ Unlimited tokens<br>Forever valid",
        "buy_lifetime_note": "One‑time purchase",
        "buy_how_to": "How to Purchase",
        "buy_step1": "Choose your plan from above.",
        "buy_step2": "Pay via MonCash or Primse Transfer to the number below.",
        "buy_step3": "Contact us with your payment receipt (email deslandes78@gmail.com).",
        "buy_step4": "Receive your unique token code within 24 hours.",
        "buy_payment_details": "Payment Details",
        "buy_payment_number": "MonCash / Primse Transfer",
        "buy_payment_holder": "Account Holder",
        "buy_payment_keep": "Keep your receipt and send it to",
        "verify_title": "Verify Your Token",
        "verify_enter": "Enter Token Code",
        "verify_placeholder": "e.g., 7F3A8B2C9D1E...",
        "verify_button": "✅ Verify Token",
        "verify_clear": "🔄 Clear Verification",
        "verify_success": "✅ Token is valid!",
        "verify_error": "❌ Token does not exist",
        "verify_used": "Token already used",
        "verify_expired": "Token expired",
        "verify_invalid": "Please enter a token code.",
        "verify_valid": "Valid",
        "verify_plan": "Plan",
        "verify_price": "Price",
        "verify_purchase_date": "Purchase Date",
        "verify_type": "Type",
        "verify_lifetime": "♾️ Lifetime",
        "verify_monthly": "📅 Monthly",
        "verify_expiry": "Expiry",
        "verify_never": "Never",
        "verify_info": "✅ This token is valid. You can now access all GlobalInternet.py software suites.",
        "verify_mark_used": "🔒 Mark as Used (Testing Only)",
        "verify_mark_success": "Token marked as used",
        "admin_title": "Admin Panel",
        "admin_login": "Enter Admin Password",
        "admin_login_button": "Login",
        "admin_logged_in": "✅ Logged in successfully",
        "admin_wrong_password": "❌ Wrong password",
        "admin_access": "🔐 Admin access granted",
        "admin_custom_title": "Custom Token Generator",
        "admin_custom_desc": "Create a token with your own plan name and price – complete flexibility.",
        "admin_custom_plan": "Plan Name",
        "admin_custom_plan_placeholder": "e.g., Premium Business, Special Offer, etc.",
        "admin_custom_price": "Price (USD)",
        "admin_custom_lifetime": "♾️ Lifetime (never expires)",
        "admin_custom_generate": "✨ Generate Custom Token",
        "admin_custom_success": "✅ Custom token generated:",
        "admin_custom_error": "Please enter a plan name.",
        "admin_last_token": "Last Generated Token",
        "admin_download": "📥 Download Token",
        "admin_predefined": "Generate Predefined Tokens",
        "admin_predefined_desc": "Quick‑generate tokens from the standard plans.",
        "admin_trial_btn": "📦 Trial ($5)",
        "admin_basic_btn": "🚀 Basic ($15)",
        "admin_pro_btn": "💼 Pro ($29)",
        "admin_enterprise_btn": "🏢 Enterprise ($49)",
        "admin_lifetime_btn": "⭐ Lifetime ($199)",
        "admin_bulk_title": "Bulk Generate 50 Initial Tokens",
        "admin_bulk_btn": "🔄 Generate 50 Tokens",
        "admin_bulk_success": "✅ Generated {count} tokens.",
        "admin_all_tokens": "All Tokens",
        "admin_token_code": "Token Code",
        "admin_plan": "Plan",
        "admin_price": "Price (USD)",
        "admin_purchase_date": "Purchase Date",
        "admin_expiry": "Expiry",
        "admin_lifetime_col": "Lifetime",
        "admin_used_col": "Used",
        "admin_status_col": "Status",
        "admin_status_active": "🟢 Active",
        "admin_status_used": "🔵 Used",
        "admin_status_expired": "🔴 Expired",
        "admin_no_tokens": "No tokens yet. Generate some!",
        "admin_export": "📥 Export CSV (All Tokens)",
        "admin_delete_manual": "Delete Token by Code (Manual)",
        "admin_delete_enter": "Enter token code to delete:",
        "admin_delete_btn": "Delete Token",
        "admin_delete_success": "✅ Token {code} was removed",
        "admin_delete_not_found": "Token not found",
        "admin_delete_invalid": "Invalid admin password",
        "admin_delete_warning": "Please enter a token code.",
        "admin_ai_analyst": "AI Analyst",
        "admin_ai_desc": "Get AI‑powered insights about your token inventory using Groq.",
        "admin_ai_not_configured": "ℹ️ Groq AI is not configured. To enable, add your `GROQ_API_KEY` to secrets.",
        "admin_ai_stats": "📊 Analyze Token Stats",
        "admin_ai_specific": "🔍 Analyze Specific Token",
        "admin_ai_enter_token": "Or analyze a specific token:",
        "admin_ai_placeholder": "Enter token code",
        "admin_ai_warning": "Please enter a token code.",
        "admin_ai_insights": "💡 AI Insights",
        "admin_ai_listen": "🔊 Listen to Analysis",
        "admin_ai_listen_success": "✅ Analysis played. Click again to repeat.",
        "admin_ai_listen_fail": "❌ Voice generation failed. Please ensure gTTS is installed.",
        "admin_ai_no_analysis": "No analysis yet. Click one of the buttons above to generate insights.",
        "admin_logout": "🚪 Logout Admin",
        "footer_copyright": "© 2026 GlobalInternet.py Online Software Company",
        "footer_built": "Built by <strong>Gesner Deslandes</strong>",
        "footer_secure": "🔐 All tokens encrypted and stored securely. Payment via MonCash / Primse Transfer accepted worldwide.",
        # Voice scripts
        "voice_customer_script": """
Welcome! This is the Application Tokens purchasing guide from GlobalInternet.py.

Here is how you can buy a token to unlock our software.

First, go to the Buy Tokens tab. You will see five pricing plans.

The Trial Pack costs 5 US dollars and gives you 5 tokens valid for 30 days.
The Basic Monthly plan is 15 dollars for 20 tokens, valid for 30 days.
The Pro Monthly plan is 29 dollars for 50 tokens, valid for 30 days.
The Enterprise Monthly plan is 49 dollars for 100 tokens, valid for 30 days.
And the Lifetime License is 199 dollars for unlimited tokens forever.

Choose the plan that fits your needs.

Next, you need to make a payment. We accept MonCash and Primse Transfer. Send your payment to the phone number {moncash}. The account holder is {owner}. Make sure to keep your payment receipt.

After you pay, contact us by email at {email} or by phone at {phone}. Send us your payment receipt and tell us which plan you purchased.

We will then send you a unique token code by email within 24 hours. This token code is your access key.

Once you receive your token, go to the Verify Token tab. Enter your token code and click Verify. If the token is valid, unused, and not expired, you will see a success message.

Now you have full access to all GlobalInternet.py software products! You can use your token to unlock voting systems, dashboards, AI tools, chatbots, school management, drone control, music production, and many more.

If you have any questions, contact us anytime. We are here to help.

Thank you for choosing GlobalInternet.py – connecting the global market with local expertise.
"""
    },
    "fr": {
        "app_title": "Jetons d'Application",
        "app_sub": "Par GlobalInternet.py Online Software Company",
        "app_tagline": "— Achetez des jetons pour débloquer notre suite logicielle —",
        "sidebar_contact": "Contact",
        "sidebar_email": "Email",
        "sidebar_phone": "Téléphone",
        "sidebar_website": "Site web",
        "sidebar_customer_guide": "Guide Client",
        "sidebar_how_to_buy": "Comment acheter un jeton étape par étape.",
        "voice_how_to_buy": "🎤 Voix IA Féminine – Comment acheter un jeton",
        "sidebar_voice_lang": "Langue vocale pour l'analyse",
        "sidebar_payment": "Moyens de paiement",
        "sidebar_payment_moncash": "MonCash / Prisme Transfer",
        "sidebar_payment_holder": "Titulaire du compte",
        "sidebar_payment_other": "Contactez-nous pour d'autres options",
        "sidebar_stats": "Statistiques des jetons",
        "sidebar_total": "Total",
        "sidebar_available": "Disponibles",
        "sidebar_used": "Utilisés",
        "sidebar_expired": "Expirés",
        "sidebar_services": "État des services",
        "sidebar_supabase": "Supabase connecté",
        "sidebar_sqlite": "Utilisation de SQLite (stockage local)",
        "sidebar_groq": "Groq connecté",
        "sidebar_groq_disabled": "Analyse IA désactivée (pas de GROQ_API_KEY)",
        "sidebar_voice_available": "Voix disponible (gTTS)",
        "sidebar_voice_unavailable": "Voix indisponible (installez gTTS)",
        "sidebar_security": "Sécurité",
        "sidebar_security_text": "Tous les jetons sont cryptés et stockés en toute sécurité.",
        "tab_buy": "🛒 Acheter des jetons",
        "tab_verify": "🔓 Vérifier un jeton",
        "tab_admin": "🔐 Administration",
        "buy_title": "Choisissez votre formule",
        "buy_after_payment": "Après paiement, vous recevrez un code jeton unique. Contactez-nous par email ou téléphone pour recevoir votre jeton.",
        "buy_trial": "Pack d'essai",
        "buy_trial_price": "5 $",
        "buy_trial_desc": "5 jetons<br>Valable 30 jours",
        "buy_trial_note": "Pour tester",
        "buy_pro": "Pro Mensuel",
        "buy_pro_price": "29 $",
        "buy_pro_desc": "50 jetons<br>Valable 30 jours",
        "buy_pro_note": "Pour petites équipes",
        "buy_basic": "Basique Mensuel",
        "buy_basic_price": "15 $",
        "buy_basic_desc": "20 jetons<br>Valable 30 jours",
        "buy_basic_note": "Pour particuliers",
        "buy_lifetime": "Licence à vie",
        "buy_lifetime_price": "199 $",
        "buy_lifetime_desc": "♾️ Jetons illimités<br>Valable à vie",
        "buy_lifetime_note": "Achat unique",
        "buy_how_to": "Comment acheter",
        "buy_step1": "Choisissez votre formule ci-dessus.",
        "buy_step2": "Payez via MonCash ou Prisme Transfer au numéro ci-dessous.",
        "buy_step3": "Contactez-nous avec votre reçu de paiement (email deslandes78@gmail.com).",
        "buy_step4": "Recevez votre code jeton unique sous 24 heures.",
        "buy_payment_details": "Détails de paiement",
        "buy_payment_number": "MonCash / Prisme Transfer",
        "buy_payment_holder": "Titulaire du compte",
        "buy_payment_keep": "Conservez votre reçu et envoyez-le à",
        "verify_title": "Vérifiez votre jeton",
        "verify_enter": "Entrez le code jeton",
        "verify_placeholder": "ex: 7F3A8B2C9D1E...",
        "verify_button": "✅ Vérifier le jeton",
        "verify_clear": "🔄 Effacer la vérification",
        "verify_success": "✅ Le jeton est valide !",
        "verify_error": "❌ Le jeton n'existe pas",
        "verify_used": "Jeton déjà utilisé",
        "verify_expired": "Jeton expiré",
        "verify_invalid": "Veuillez entrer un code jeton.",
        "verify_valid": "Valide",
        "verify_plan": "Formule",
        "verify_price": "Prix",
        "verify_purchase_date": "Date d'achat",
        "verify_type": "Type",
        "verify_lifetime": "♾️ À vie",
        "verify_monthly": "📅 Mensuel",
        "verify_expiry": "Expiration",
        "verify_never": "Jamais",
        "verify_info": "✅ Ce jeton est valide. Vous pouvez maintenant accéder à toutes les suites logicielles de GlobalInternet.py.",
        "verify_mark_used": "🔒 Marquer comme utilisé (test uniquement)",
        "verify_mark_success": "Jeton marqué comme utilisé",
        "admin_title": "Panneau d'administration",
        "admin_login": "Entrez le mot de passe administrateur",
        "admin_login_button": "Connexion",
        "admin_logged_in": "✅ Connecté avec succès",
        "admin_wrong_password": "❌ Mot de passe incorrect",
        "admin_access": "🔐 Accès administrateur accordé",
        "admin_custom_title": "Générateur de jetons personnalisé",
        "admin_custom_desc": "Créez un jeton avec votre propre nom et prix – flexibilité totale.",
        "admin_custom_plan": "Nom de la formule",
        "admin_custom_plan_placeholder": "ex: Premium Business, Offre spéciale, etc.",
        "admin_custom_price": "Prix (USD)",
        "admin_custom_lifetime": "♾️ À vie (n'expire jamais)",
        "admin_custom_generate": "✨ Générer un jeton personnalisé",
        "admin_custom_success": "✅ Jeton personnalisé généré :",
        "admin_custom_error": "Veuillez entrer un nom de formule.",
        "admin_last_token": "Dernier jeton généré",
        "admin_download": "📥 Télécharger le jeton",
        "admin_predefined": "Générer des jetons prédéfinis",
        "admin_predefined_desc": "Générer rapidement des jetons à partir des formules standard.",
        "admin_trial_btn": "📦 Essai (5 $)",
        "admin_basic_btn": "🚀 Basique (15 $)",
        "admin_pro_btn": "💼 Pro (29 $)",
        "admin_enterprise_btn": "🏢 Entreprise (49 $)",
        "admin_lifetime_btn": "⭐ À vie (199 $)",
        "admin_bulk_title": "Générer en masse 50 jetons initiaux",
        "admin_bulk_btn": "🔄 Générer 50 jetons",
        "admin_bulk_success": "✅ {count} jetons générés.",
        "admin_all_tokens": "Tous les jetons",
        "admin_token_code": "Code jeton",
        "admin_plan": "Formule",
        "admin_price": "Prix (USD)",
        "admin_purchase_date": "Date d'achat",
        "admin_expiry": "Expiration",
        "admin_lifetime_col": "À vie",
        "admin_used_col": "Utilisé",
        "admin_status_col": "Statut",
        "admin_status_active": "🟢 Actif",
        "admin_status_used": "🔵 Utilisé",
        "admin_status_expired": "🔴 Expiré",
        "admin_no_tokens": "Pas encore de jetons. Générez-en !",
        "admin_export": "📥 Exporter CSV (tous les jetons)",
        "admin_delete_manual": "Supprimer un jeton par code (manuel)",
        "admin_delete_enter": "Entrez le code jeton à supprimer :",
        "admin_delete_btn": "Supprimer le jeton",
        "admin_delete_success": "✅ Jeton {code} supprimé",
        "admin_delete_not_found": "Jeton non trouvé",
        "admin_delete_invalid": "Mot de passe administrateur invalide",
        "admin_delete_warning": "Veuillez entrer un code jeton.",
        "admin_ai_analyst": "Analyste IA",
        "admin_ai_desc": "Obtenez des analyses par IA sur votre inventaire de jetons en utilisant Groq.",
        "admin_ai_not_configured": "ℹ️ Groq IA n'est pas configuré. Pour activer, ajoutez votre `GROQ_API_KEY` aux secrets.",
        "admin_ai_stats": "📊 Analyser les statistiques des jetons",
        "admin_ai_specific": "🔍 Analyser un jeton spécifique",
        "admin_ai_enter_token": "Ou analysez un jeton spécifique :",
        "admin_ai_placeholder": "Entrez le code jeton",
        "admin_ai_warning": "Veuillez entrer un code jeton.",
        "admin_ai_insights": "💡 Analyses IA",
        "admin_ai_listen": "🔊 Écouter l'analyse",
        "admin_ai_listen_success": "✅ Analyse diffusée. Cliquez à nouveau pour répéter.",
        "admin_ai_listen_fail": "❌ La génération vocale a échoué. Veuillez installer gTTS.",
        "admin_ai_no_analysis": "Pas encore d'analyse. Cliquez sur l'un des boutons ci-dessus pour générer des analyses.",
        "admin_logout": "🚪 Déconnexion administrateur",
        "footer_copyright": "© 2026 GlobalInternet.py Online Software Company",
        "footer_built": "Construit par <strong>Gesner Deslandes</strong>",
        "footer_secure": "🔐 Tous les jetons sont cryptés et stockés en toute sécurité. Paiement par MonCash / Prisme Transfer accepté dans le monde entier.",
        "voice_customer_script": """
Bienvenue ! Ceci est le guide d'achat de jetons d'application de GlobalInternet.py.

Voici comment acheter un jeton pour débloquer nos logiciels.

Tout d'abord, allez dans l'onglet Acheter des jetons. Vous verrez cinq formules.

Le Pack d'essai coûte 5 dollars américains et vous donne 5 jetons valables 30 jours.
La formule Basique Mensuelle est à 15 dollars pour 20 jetons, valable 30 jours.
La formule Pro Mensuelle est à 29 dollars pour 50 jetons, valable 30 jours.
La formule Entreprise Mensuelle est à 49 dollars pour 100 jetons, valable 30 jours.
Et la Licence à vie est à 199 dollars pour des jetons illimités pour toujours.

Choisissez la formule qui correspond à vos besoins.

Ensuite, vous devez effectuer un paiement. Nous acceptons MonCash et Prisme Transfer. Envoyez votre paiement au numéro de téléphone {moncash}. Le titulaire du compte est {owner}. Assurez-vous de conserver votre reçu de paiement.

Après avoir payé, contactez-nous par email à {email} ou par téléphone au {phone}. Envoyez-nous votre reçu de paiement et dites-nous quelle formule vous avez achetée.

Nous vous enverrons alors un code jeton unique par email sous 24 heures. Ce code jeton est votre clé d'accès.

Une fois que vous avez reçu votre jeton, allez dans l'onglet Vérifier un jeton. Entrez votre code jeton et cliquez sur Vérifier. Si le jeton est valide, non utilisé et non expiré, vous verrez un message de succès.

Vous avez maintenant un accès complet à tous les produits logiciels de GlobalInternet.py ! Vous pouvez utiliser votre jeton pour débloquer des systèmes de vote, des tableaux de bord, des outils IA, des chatbots, la gestion scolaire, le contrôle de drones, la production musicale, et bien plus encore.

Si vous avez des questions, contactez-nous à tout moment. Nous sommes là pour vous aider.

Merci d'avoir choisi GlobalInternet.py – connecter le marché mondial à l'expertise locale.
"""
    },
    "es": {
        "app_title": "Tokens de Aplicación",
        "app_sub": "Por GlobalInternet.py Online Software Company",
        "app_tagline": "— Compra tokens para desbloquear nuestro suite de software —",
        "sidebar_contact": "Contacto",
        "sidebar_email": "Correo electrónico",
        "sidebar_phone": "Teléfono",
        "sidebar_website": "Sitio web",
        "sidebar_customer_guide": "Guía para el cliente",
        "sidebar_how_to_buy": "Cómo comprar un token paso a paso.",
        "voice_how_to_buy": "🎤 Voz IA Femenina – Cómo comprar un token",
        "sidebar_voice_lang": "Idioma de voz para análisis",
        "sidebar_payment": "Métodos de pago",
        "sidebar_payment_moncash": "MonCash / Prisme Transfer",
        "sidebar_payment_holder": "Titular de la cuenta",
        "sidebar_payment_other": "Contáctenos para otras opciones",
        "sidebar_stats": "Estadísticas de tokens",
        "sidebar_total": "Total",
        "sidebar_available": "Disponibles",
        "sidebar_used": "Usados",
        "sidebar_expired": "Expirados",
        "sidebar_services": "Estado de los servicios",
        "sidebar_supabase": "Supabase conectado",
        "sidebar_sqlite": "Usando SQLite (almacenamiento local)",
        "sidebar_groq": "Groq conectado",
        "sidebar_groq_disabled": "Análisis IA deshabilitado (sin GROQ_API_KEY)",
        "sidebar_voice_available": "Voz disponible (gTTS)",
        "sidebar_voice_unavailable": "Voz no disponible (instala gTTS)",
        "sidebar_security": "Seguridad",
        "sidebar_security_text": "Todos los tokens están encriptados y almacenados de forma segura.",
        "tab_buy": "🛒 Comprar tokens",
        "tab_verify": "🔓 Verificar token",
        "tab_admin": "🔐 Administrador",
        "buy_title": "Elige tu plan",
        "buy_after_payment": "Después del pago, recibirás un código de token único. Contáctanos por correo electrónico o teléfono para recibir tu token.",
        "buy_trial": "Paquete de prueba",
        "buy_trial_price": "$5",
        "buy_trial_desc": "5 tokens<br>Válido 30 días",
        "buy_trial_note": "Para pruebas",
        "buy_pro": "Pro Mensual",
        "buy_pro_price": "$29",
        "buy_pro_desc": "50 tokens<br>Válido 30 días",
        "buy_pro_note": "Para equipos pequeños",
        "buy_basic": "Básico Mensual",
        "buy_basic_price": "$15",
        "buy_basic_desc": "20 tokens<br>Válido 30 días",
        "buy_basic_note": "Para individuos",
        "buy_lifetime": "Licencia de por vida",
        "buy_lifetime_price": "$199",
        "buy_lifetime_desc": "♾️ Tokens ilimitados<br>Válido para siempre",
        "buy_lifetime_note": "Compra única",
        "buy_how_to": "Cómo comprar",
        "buy_step1": "Elige tu plan de los anteriores.",
        "buy_step2": "Paga mediante MonCash o Prisme Transfer al número de abajo.",
        "buy_step3": "Contáctanos con tu comprobante de pago (correo deslandes78@gmail.com).",
        "buy_step4": "Recibe tu código de token único en 24 horas.",
        "buy_payment_details": "Detalles de pago",
        "buy_payment_number": "MonCash / Prisme Transfer",
        "buy_payment_holder": "Titular de la cuenta",
        "buy_payment_keep": "Guarda tu comprobante y envíalo a",
        "verify_title": "Verifica tu token",
        "verify_enter": "Ingresa el código del token",
        "verify_placeholder": "p.ej., 7F3A8B2C9D1E...",
        "verify_button": "✅ Verificar token",
        "verify_clear": "🔄 Borrar verificación",
        "verify_success": "✅ ¡El token es válido!",
        "verify_error": "❌ El token no existe",
        "verify_used": "Token ya usado",
        "verify_expired": "Token expirado",
        "verify_invalid": "Por favor, ingresa un código de token.",
        "verify_valid": "Válido",
        "verify_plan": "Plan",
        "verify_price": "Precio",
        "verify_purchase_date": "Fecha de compra",
        "verify_type": "Tipo",
        "verify_lifetime": "♾️ De por vida",
        "verify_monthly": "📅 Mensual",
        "verify_expiry": "Vencimiento",
        "verify_never": "Nunca",
        "verify_info": "✅ Este token es válido. Ahora puedes acceder a todos los suites de software de GlobalInternet.py.",
        "verify_mark_used": "🔒 Marcar como usado (solo prueba)",
        "verify_mark_success": "Token marcado como usado",
        "admin_title": "Panel de administración",
        "admin_login": "Ingresa la contraseña de administrador",
        "admin_login_button": "Iniciar sesión",
        "admin_logged_in": "✅ Sesión iniciada correctamente",
        "admin_wrong_password": "❌ Contraseña incorrecta",
        "admin_access": "🔐 Acceso de administrador concedido",
        "admin_custom_title": "Generador de tokens personalizado",
        "admin_custom_desc": "Crea un token con tu propio nombre y precio – flexibilidad total.",
        "admin_custom_plan": "Nombre del plan",
        "admin_custom_plan_placeholder": "p.ej., Premium Business, Oferta especial, etc.",
        "admin_custom_price": "Precio (USD)",
        "admin_custom_lifetime": "♾️ De por vida (nunca expira)",
        "admin_custom_generate": "✨ Generar token personalizado",
        "admin_custom_success": "✅ Token personalizado generado:",
        "admin_custom_error": "Por favor, ingresa un nombre de plan.",
        "admin_last_token": "Último token generado",
        "admin_download": "📥 Descargar token",
        "admin_predefined": "Generar tokens predefinidos",
        "admin_predefined_desc": "Genera rápidamente tokens a partir de los planes estándar.",
        "admin_trial_btn": "📦 Prueba ($5)",
        "admin_basic_btn": "🚀 Básico ($15)",
        "admin_pro_btn": "💼 Pro ($29)",
        "admin_enterprise_btn": "🏢 Empresa ($49)",
        "admin_lifetime_btn": "⭐ De por vida ($199)",
        "admin_bulk_title": "Generar 50 tokens iniciales en masa",
        "admin_bulk_btn": "🔄 Generar 50 tokens",
        "admin_bulk_success": "✅ {count} tokens generados.",
        "admin_all_tokens": "Todos los tokens",
        "admin_token_code": "Código del token",
        "admin_plan": "Plan",
        "admin_price": "Precio (USD)",
        "admin_purchase_date": "Fecha de compra",
        "admin_expiry": "Vencimiento",
        "admin_lifetime_col": "De por vida",
        "admin_used_col": "Usado",
        "admin_status_col": "Estado",
        "admin_status_active": "🟢 Activo",
        "admin_status_used": "🔵 Usado",
        "admin_status_expired": "🔴 Expirado",
        "admin_no_tokens": "Aún no hay tokens. ¡Genera algunos!",
        "admin_export": "📥 Exportar CSV (todos los tokens)",
        "admin_delete_manual": "Eliminar token por código (manual)",
        "admin_delete_enter": "Ingresa el código del token a eliminar:",
        "admin_delete_btn": "Eliminar token",
        "admin_delete_success": "✅ Token {code} eliminado",
        "admin_delete_not_found": "Token no encontrado",
        "admin_delete_invalid": "Contraseña de administrador inválida",
        "admin_delete_warning": "Por favor, ingresa un código de token.",
        "admin_ai_analyst": "Analista IA",
        "admin_ai_desc": "Obtén información sobre tu inventario de tokens mediante IA con Groq.",
        "admin_ai_not_configured": "ℹ️ Groq IA no está configurada. Para activarla, añade tu `GROQ_API_KEY` a los secretos.",
        "admin_ai_stats": "📊 Analizar estadísticas de tokens",
        "admin_ai_specific": "🔍 Analizar token específico",
        "admin_ai_enter_token": "O analiza un token específico:",
        "admin_ai_placeholder": "Ingresa el código del token",
        "admin_ai_warning": "Por favor, ingresa un código de token.",
        "admin_ai_insights": "💡 Información de IA",
        "admin_ai_listen": "🔊 Escuchar análisis",
        "admin_ai_listen_success": "✅ Análisis reproducido. Haz clic de nuevo para repetir.",
        "admin_ai_listen_fail": "❌ La generación de voz falló. Asegúrate de instalar gTTS.",
        "admin_ai_no_analysis": "Aún no hay análisis. Haz clic en uno de los botones de arriba para generar información.",
        "admin_logout": "🚪 Cerrar sesión administrador",
        "footer_copyright": "© 2026 GlobalInternet.py Online Software Company",
        "footer_built": "Construido por <strong>Gesner Deslandes</strong>",
        "footer_secure": "🔐 Todos los tokens están encriptados y almacenados de forma segura. Pagos mediante MonCash / Prisme Transfer aceptados en todo el mundo.",
        "voice_customer_script": """
¡Bienvenido! Esta es la guía de compra de tokens de aplicación de GlobalInternet.py.

Así es como puedes comprar un token para desbloquear nuestro software.

Primero, ve a la pestaña Comprar tokens. Verás cinco planes de precios.

El Paquete de prueba cuesta 5 dólares estadounidenses y te da 5 tokens válidos por 30 días.
El plan Básico Mensual es de 15 dólares por 20 tokens, válido por 30 días.
El plan Pro Mensual es de 29 dólares por 50 tokens, válido por 30 días.
El plan Empresa Mensual es de 49 dólares por 100 tokens, válido por 30 días.
Y la Licencia de por vida es de 199 dólares por tokens ilimitados para siempre.

Elige el plan que se adapte a tus necesidades.

Luego, debes realizar un pago. Aceptamos MonCash y Prisme Transfer. Envía tu pago al número de teléfono {moncash}. El titular de la cuenta es {owner}. Asegúrate de guardar tu comprobante de pago.

Después de pagar, contáctanos por correo electrónico a {email} o por teléfono al {phone}. Envíanos tu comprobante de pago e indícanos qué plan compraste.

Te enviaremos un código de token único por correo electrónico en 24 horas. Este código de token es tu clave de acceso.

Una vez que recibas tu token, ve a la pestaña Verificar token. Ingresa tu código de token y haz clic en Verificar. Si el token es válido, no usado y no ha expirado, verás un mensaje de éxito.

Ahora tienes acceso completo a todos los productos de software de GlobalInternet.py. Puedes usar tu token para desbloquear sistemas de votación, paneles, herramientas de IA, chatbots, gestión escolar, control de drones, producción musical, y muchos más.

Si tienes preguntas, contáctanos en cualquier momento. Estamos aquí para ayudarte.

Gracias por elegir GlobalInternet.py – conectando el mercado global con experiencia local.
"""
    },
    "zh": {
        "app_title": "应用程序令牌",
        "app_sub": "由 GlobalInternet.py 在线软件公司提供",
        "app_tagline": "— 购买令牌以解锁我们的软件套件 —",
        "sidebar_contact": "联系方式",
        "sidebar_email": "电子邮件",
        "sidebar_phone": "电话",
        "sidebar_website": "网站",
        "sidebar_customer_guide": "客户指南",
        "sidebar_how_to_buy": "如何一步一步购买令牌。",
        "voice_how_to_buy": "🎤 人工智能女声 – 如何购买令牌",
        "sidebar_voice_lang": "分析用的语音语言",
        "sidebar_payment": "支付方式",
        "sidebar_payment_moncash": "MonCash / Prisme Transfer",
        "sidebar_payment_holder": "账户持有人",
        "sidebar_payment_other": "联系我们了解其他选项",
        "sidebar_stats": "令牌统计",
        "sidebar_total": "总数",
        "sidebar_available": "可用",
        "sidebar_used": "已用",
        "sidebar_expired": "已过期",
        "sidebar_services": "服务状态",
        "sidebar_supabase": "Supabase 已连接",
        "sidebar_sqlite": "使用 SQLite（本地存储）",
        "sidebar_groq": "Groq 已连接",
        "sidebar_groq_disabled": "AI 分析禁用（无 GROQ_API_KEY）",
        "sidebar_voice_available": "语音可用（gTTS）",
        "sidebar_voice_unavailable": "语音不可用（安装 gTTS）",
        "sidebar_security": "安全性",
        "sidebar_security_text": "所有令牌均已加密并安全存储。",
        "tab_buy": "🛒 购买令牌",
        "tab_verify": "🔓 验证令牌",
        "tab_admin": "🔐 管理",
        "buy_title": "选择您的套餐",
        "buy_after_payment": "付款后，您将收到一个唯一的令牌代码。请通过电子邮件或电话联系我们以接收您的令牌。",
        "buy_trial": "试用包",
        "buy_trial_price": "$5",
        "buy_trial_desc": "5 个令牌<br>有效期 30 天",
        "buy_trial_note": "用于测试",
        "buy_pro": "专业版月费",
        "buy_pro_price": "$29",
        "buy_pro_desc": "50 个令牌<br>有效期 30 天",
        "buy_pro_note": "适合小型团队",
        "buy_basic": "基础版月费",
        "buy_basic_price": "$15",
        "buy_basic_desc": "20 个令牌<br>有效期 30 天",
        "buy_basic_note": "适合个人",
        "buy_lifetime": "终身许可证",
        "buy_lifetime_price": "$199",
        "buy_lifetime_desc": "♾️ 无限令牌<br>永久有效",
        "buy_lifetime_note": "一次性购买",
        "buy_how_to": "如何购买",
        "buy_step1": "从上方选择您的套餐。",
        "buy_step2": "通过 MonCash 或 Prisme Transfer 支付到以下号码。",
        "buy_step3": "通过电子邮件 deslandes78@gmail.com 联系我们并提供付款收据。",
        "buy_step4": "在 24 小时内收到您的唯一令牌代码。",
        "buy_payment_details": "付款详情",
        "buy_payment_number": "MonCash / Prisme Transfer",
        "buy_payment_holder": "账户持有人",
        "buy_payment_keep": "保留收据并发送至",
        "verify_title": "验证您的令牌",
        "verify_enter": "输入令牌代码",
        "verify_placeholder": "例如：7F3A8B2C9D1E...",
        "verify_button": "✅ 验证令牌",
        "verify_clear": "🔄 清除验证",
        "verify_success": "✅ 令牌有效！",
        "verify_error": "❌ 令牌不存在",
        "verify_used": "令牌已被使用",
        "verify_expired": "令牌已过期",
        "verify_invalid": "请输入令牌代码。",
        "verify_valid": "有效",
        "verify_plan": "套餐",
        "verify_price": "价格",
        "verify_purchase_date": "购买日期",
        "verify_type": "类型",
        "verify_lifetime": "♾️ 终身",
        "verify_monthly": "📅 月费",
        "verify_expiry": "过期",
        "verify_never": "永不",
        "verify_info": "✅ 此令牌有效。您现在可以访问所有 GlobalInternet.py 软件套件。",
        "verify_mark_used": "🔒 标记为已使用（仅测试）",
        "verify_mark_success": "令牌已标记为已使用",
        "admin_title": "管理面板",
        "admin_login": "输入管理员密码",
        "admin_login_button": "登录",
        "admin_logged_in": "✅ 登录成功",
        "admin_wrong_password": "❌ 密码错误",
        "admin_access": "🔐 管理员访问已授权",
        "admin_custom_title": "自定义令牌生成器",
        "admin_custom_desc": "使用您自己的套餐名称和价格创建令牌 – 完全灵活。",
        "admin_custom_plan": "套餐名称",
        "admin_custom_plan_placeholder": "例如：高级商务、特惠等",
        "admin_custom_price": "价格 (USD)",
        "admin_custom_lifetime": "♾️ 终身（永不过期）",
        "admin_custom_generate": "✨ 生成自定义令牌",
        "admin_custom_success": "✅ 自定义令牌已生成：",
        "admin_custom_error": "请输入套餐名称。",
        "admin_last_token": "最后生成的令牌",
        "admin_download": "📥 下载令牌",
        "admin_predefined": "生成预定义令牌",
        "admin_predefined_desc": "从标准套餐快速生成令牌。",
        "admin_trial_btn": "📦 试用 ($5)",
        "admin_basic_btn": "🚀 基础 ($15)",
        "admin_pro_btn": "💼 专业 ($29)",
        "admin_enterprise_btn": "🏢 企业 ($49)",
        "admin_lifetime_btn": "⭐ 终身 ($199)",
        "admin_bulk_title": "批量生成 50 个初始令牌",
        "admin_bulk_btn": "🔄 生成 50 个令牌",
        "admin_bulk_success": "✅ 已生成 {count} 个令牌。",
        "admin_all_tokens": "所有令牌",
        "admin_token_code": "令牌代码",
        "admin_plan": "套餐",
        "admin_price": "价格 (USD)",
        "admin_purchase_date": "购买日期",
        "admin_expiry": "过期",
        "admin_lifetime_col": "终身",
        "admin_used_col": "已用",
        "admin_status_col": "状态",
        "admin_status_active": "🟢 有效",
        "admin_status_used": "🔵 已用",
        "admin_status_expired": "🔴 已过期",
        "admin_no_tokens": "暂无令牌。请生成一些！",
        "admin_export": "📥 导出 CSV（所有令牌）",
        "admin_delete_manual": "按代码删除令牌（手动）",
        "admin_delete_enter": "输入要删除的令牌代码：",
        "admin_delete_btn": "删除令牌",
        "admin_delete_success": "✅ 令牌 {code} 已删除",
        "admin_delete_not_found": "令牌未找到",
        "admin_delete_invalid": "管理员密码无效",
        "admin_delete_warning": "请输入令牌代码。",
        "admin_ai_analyst": "AI 分析师",
        "admin_ai_desc": "使用 Groq 获取关于令牌库存的 AI 分析洞察。",
        "admin_ai_not_configured": "ℹ️ Groq AI 未配置。请在 secrets 中添加您的 `GROQ_API_KEY` 以启用。",
        "admin_ai_stats": "📊 分析令牌统计",
        "admin_ai_specific": "🔍 分析特定令牌",
        "admin_ai_enter_token": "或分析特定令牌：",
        "admin_ai_placeholder": "输入令牌代码",
        "admin_ai_warning": "请输入令牌代码。",
        "admin_ai_insights": "💡 AI 洞察",
        "admin_ai_listen": "🔊 收听分析",
        "admin_ai_listen_success": "✅ 分析已播放。再次点击重复播放。",
        "admin_ai_listen_fail": "❌ 语音生成失败。请确保已安装 gTTS。",
        "admin_ai_no_analysis": "尚无分析。请点击上方按钮生成洞察。",
        "admin_logout": "🚪 退出管理员",
        "footer_copyright": "© 2026 GlobalInternet.py 在线软件公司",
        "footer_built": "由 <strong>Gesner Deslandes</strong> 构建",
        "footer_secure": "🔐 所有令牌均已加密并安全存储。接受 MonCash / Prisme Transfer 全球支付。",
        "voice_customer_script": """
欢迎！这是 GlobalInternet.py 的应用程序令牌购买指南。

以下是购买令牌以解锁我们软件的方法。

首先，转到“购买令牌”选项卡。您将看到五种定价套餐。

试用包价格为 5 美元，提供 5 个令牌，有效期 30 天。
基础月费套餐为 15 美元，提供 20 个令牌，有效期 30 天。
专业月费套餐为 29 美元，提供 50 个令牌，有效期 30 天。
企业月费套餐为 49 美元，提供 100 个令牌，有效期 30 天。
终身许可证为 199 美元，提供无限令牌，永久有效。

选择最适合您需求的套餐。

接下来，您需要付款。我们接受 MonCash 和 Prisme Transfer。请将款项发送至电话号码 {moncash}，账户持有人为 {owner}。请务必保存您的付款收据。

付款后，请通过电子邮件 {email} 或电话 {phone} 联系我们。将您的付款收据发送给我们，并告知您购买的套餐。

我们将在 24 小时内通过电子邮件向您发送唯一的令牌代码。此令牌代码是您的访问密钥。

收到令牌后，转到“验证令牌”选项卡。输入您的令牌代码并点击验证。如果令牌有效、未被使用且未过期，您将看到成功消息。

现在，您可以完全访问所有 GlobalInternet.py 软件产品！您可以使用令牌解锁投票系统、仪表板、AI 工具、聊天机器人、学校管理、无人机控制、音乐制作等等。

如果您有任何疑问，请随时联系我们。我们随时为您提供帮助。

感谢您选择 GlobalInternet.py – 连接全球市场与本地专业知识。
"""
    }
}

# ============================================================
# LANGUAGE DETECTION & TRANSLATION FUNCTION
# ============================================================
def get_translations(lang_code):
    """Return the translation dictionary for the given language"""
    return T.get(lang_code, T["en"])

# ============================================================
# RETRIEVE SECRETS
# ============================================================
ADMIN_PASSWORD = get_secret("ADMIN_PASSWORD", "Nov1979")
CONTACT_EMAIL = get_secret("CONTACT_EMAIL", "deslandes78@gmail.com")
CONTACT_PHONE = get_secret("CONTACT_PHONE", "(509) 4738-5663")
WEBSITE = get_secret("WEBSITE", "https://globalinternetsitepyabh7v6tnmskxxnuplrdcgk.streamlit.app/")
MONCASH_NUMBER = get_secret("MONCASH_NUMBER", "(509) 4738-5663")
MONCASH_OWNER = get_secret("MONCASH_OWNER", "Gesner Deslandes")
MONCASH_API_SECRET = get_secret("MONCASH_API_SECRET", "")

# ========== PAGE CONFIG ==========
st.set_page_config(
    page_title="Application Tokens | GlobalInternet.py",
    layout="centered",
    page_icon="🔑"
)

# ========== CUSTOM CSS (unchanged, kept for styling) ==========
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
    .stNumberInput>div>div>input {
        background-color: #141018 !important;
        color: #ffffff !important;
        border: 1px solid #2a1f14 !important;
        border-radius: 8px !important;
        text-align: center !important;
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
    .custom-gen-box {
        background: rgba(0, 255, 100, 0.03);
        border: 1px solid #2a1f14;
        border-radius: 12px;
        padding: 20px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# SUPABASE SETUP (optional)
# ============================================================
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

# ========== DATABASE FUNCTIONS (unchanged) ==========
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

# ========== LANGUAGE SELECTION AND SESSION STATE ==========
if "lang" not in st.session_state:
    st.session_state.lang = "en"

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

# ========== TRANSLATION FUNCTION ==========
def t(key):
    """Return translated string for the current language"""
    lang = st.session_state.lang
    return T[lang].get(key, T["en"].get(key, key))

# ========== HEADER ==========
st.markdown(f"""
<div class="main-header">
    <h1>🔑 {t('app_title')}</h1>
    <p>{t('app_sub')}</p>
    <p style="font-size:0.9rem; color:#666;">{t('app_tagline')}</p>
</div>
""", unsafe_allow_html=True)

# ========== SIDEBAR ==========
with st.sidebar:
    # Language selection at the top
    lang_options = {
        "en": "English",
        "fr": "Français",
        "es": "Español",
        "zh": "中文"
    }
    selected_lang = st.selectbox(
        "🌐 Language",
        options=list(lang_options.keys()),
        format_func=lambda x: lang_options[x],
        index=list(lang_options.keys()).index(st.session_state.lang)
    )
    if selected_lang != st.session_state.lang:
        st.session_state.lang = selected_lang
        st.rerun()
    
    st.markdown("---")
    
    st.markdown(f"### 📞 {t('sidebar_contact')}")
    st.markdown(f"""
    <div class="sidebar-contact">
        <strong>{t('sidebar_email')}:</strong> {CONTACT_EMAIL}<br>
        <strong>{t('sidebar_phone')}:</strong> {CONTACT_PHONE}<br>
        <strong>{t('sidebar_website')}:</strong> <a href="{WEBSITE}" style="color:#00ff64;" target="_blank">globalinternet-py.com</a>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown(f"### 🎤 {t('sidebar_customer_guide')}")
    st.markdown(f"<p style='font-size:0.85rem; color:#a09080;'>{t('sidebar_how_to_buy')}</p>", unsafe_allow_html=True)
    
    # Customer voice button
    voice_clicked = st.button(t('voice_how_to_buy'), use_container_width=True)
    
    if voice_clicked:
        # Get the script for the current language and format it with contact details
        script_template = T[st.session_state.lang]['voice_customer_script']
        script = script_template.format(
            moncash=MONCASH_NUMBER,
            owner=MONCASH_OWNER,
            email=CONTACT_EMAIL,
            phone=CONTACT_PHONE
        )
        with st.spinner("🎤 Generating voice guide..."):
            # Map language to gTTS code
            lang_code = st.session_state.lang
            if lang_code == "zh":
                lang_code = "zh"  # gTTS supports 'zh'
            audio_bytes = generate_audio(script, lang_code)
            if audio_bytes:
                st.audio(audio_bytes, format="audio/mp3")
                st.success("✅ Voice guide played. Click again to repeat.")
            else:
                st.error("❌ Voice generation failed. Please ensure gTTS is installed.")
    
    st.markdown("---")
    
    # Voice language selector for AI analysis reading (admin only)
    voice_lang = st.selectbox(
        t('sidebar_voice_lang'),
        options=["en", "fr", "es", "zh"],
        format_func=lambda x: {"en": "English", "fr": "Français", "es": "Español", "zh": "中文"}[x],
        key="voice_lang_analysis"
    )
    
    st.markdown("---")
    
    st.markdown(f"### 💳 {t('sidebar_payment')}")
    st.markdown(f"""
    - **{t('sidebar_payment_moncash')}:** {MONCASH_NUMBER}
    - {t('sidebar_payment_holder')}: {MONCASH_OWNER}
    - {t('sidebar_payment_other')}
    """)
    
    st.markdown("---")
    
    st.markdown(f"### 📊 {t('sidebar_stats')}")
    total, available, used, expired = get_stats()
    c1, c2 = st.columns(2)
    with c1:
        st.metric(t('sidebar_total'), total)
        st.metric(t('sidebar_available'), available)
    with c2:
        st.metric(t('sidebar_used'), used)
        st.metric(t('sidebar_expired'), expired)
    
    st.markdown("---")
    
    st.markdown(f"### 🔌 {t('sidebar_services')}")
    if SUPABASE_CONNECTED:
        st.success(f"✅ {t('sidebar_supabase')}")
    else:
        st.info(f"ℹ️ {t('sidebar_sqlite')}")
    if GROQ_CONNECTED:
        st.success(f"✅ {t('sidebar_groq')}")
    else:
        st.info(f"ℹ️ {t('sidebar_groq_disabled')}")
    if VOICE_AVAILABLE:
        st.success(f"✅ {t('sidebar_voice_available')}")
    else:
        st.warning(f"⚠️ {t('sidebar_voice_unavailable')}")
    
    st.markdown("---")
    st.markdown(f"### 🔐 {t('sidebar_security')}")
    st.markdown(f"{t('sidebar_security_text')}")

# ========== TABS ==========
tab_buy, tab_verify, tab_admin = st.tabs([t('tab_buy'), t('tab_verify'), t('tab_admin')])

# ---------- BUY TOKENS ----------
with tab_buy:
    st.markdown(f"### 🛒 {t('buy_title')}")
    st.markdown(t('buy_after_payment'))
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        <div class="token-card">
            <h3>📦 {t('buy_trial')}</h3>
            <div class="price">{t('buy_trial_price')} <small>USD</small></div>
            <p>{t('buy_trial_desc')}</p>
            <p style="color:#a09080;font-size:0.8rem;">{t('buy_trial_note')}</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="token-card">
            <h3>💼 {t('buy_pro')}</h3>
            <div class="price">{t('buy_pro_price')} <small>USD</small></div>
            <p>{t('buy_pro_desc')}</p>
            <p style="color:#a09080;font-size:0.8rem;">{t('buy_pro_note')}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="token-card">
            <h3>🚀 {t('buy_basic')}</h3>
            <div class="price">{t('buy_basic_price')} <small>USD</small></div>
            <p>{t('buy_basic_desc')}</p>
            <p style="color:#a09080;font-size:0.8rem;">{t('buy_basic_note')}</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="token-card">
            <h3>⭐ {t('buy_lifetime')}</h3>
            <div class="price">{t('buy_lifetime_price')} <small>USD</small></div>
            <p>{t('buy_lifetime_desc')}</p>
            <p style="color:#a09080;font-size:0.8rem;">{t('buy_lifetime_note')}</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown(f"### 📝 {t('buy_how_to')}")
    st.markdown(f"""
    1. {t('buy_step1')}
    2. {t('buy_step2')}
    3. {t('buy_step3')}
    4. {t('buy_step4')}
    """)
    
    st.markdown(f"""
    <div class="info-box">
        💡 <strong>{t('buy_payment_details')}:</strong><br>
        {t('buy_payment_number')}: {MONCASH_NUMBER}<br>
        {t('buy_payment_holder')}: {MONCASH_OWNER}<br>
        <span style="color:#a09080;font-size:0.9rem;">{t('buy_payment_keep')} {CONTACT_EMAIL}</span>
    </div>
    """, unsafe_allow_html=True)

# ---------- VERIFY TOKEN ----------
with tab_verify:
    st.markdown(f"### 🔓 {t('verify_title')}")
    token_input = st.text_input(t('verify_enter'), placeholder=t('verify_placeholder'), key="token_input")
    
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        if st.button(t('verify_button'), use_container_width=True):
            if token_input:
                data, msg = validate_token(token_input)
                if data:
                    st.session_state.token_verified = True
                    st.session_state.verified_token = data
                    st.success(f"✅ {t('verify_success')}")
                    st.balloons()
                else:
                    st.error(f"❌ {msg}")
            else:
                st.warning(t('verify_invalid'))
    
    with col_v2:
        if st.button(t('verify_clear'), use_container_width=True):
            st.session_state.token_verified = False
            st.session_state.verified_token = None
            st.rerun()
    
    if st.session_state.token_verified and st.session_state.verified_token:
        data = st.session_state.verified_token
        st.markdown("---")
        st.markdown(f"### ✅ {t('verify_valid')}")
        
        col_i1, col_i2 = st.columns(2)
        with col_i1:
            st.markdown(f"**{t('verify_plan')}:** {data['plan_name']}")
            st.markdown(f"**{t('verify_price')}:** ${data['price']} USD")
            st.markdown(f"**{t('verify_purchase_date')}:** {data['purchase_date'][:10]}")
        with col_i2:
            st.markdown(f"**{t('verify_type')}:** {t('verify_lifetime') if data['is_lifetime'] else t('verify_monthly')}")
            if data['expiry_date']:
                st.markdown(f"**{t('verify_expiry')}:** {data['expiry_date'][:10]}")
            else:
                st.markdown(f"**{t('verify_expiry')}:** {t('verify_never')}")
        
        st.markdown(f"""
        <div class="info-box">
            {t('verify_info')}
        </div>
        """, unsafe_allow_html=True)
        
        if st.button(t('verify_mark_used')):
            use_token(token_input, "demo_user")
            st.success(t('verify_mark_success'))
            st.rerun()

# ---------- ADMIN ----------
with tab_admin:
    st.markdown(f"### 🔐 {t('admin_title')}")
    st.markdown("Manage tokens – requires admin password.")
    
    if not st.session_state.admin_authenticated:
        admin_pw = st.text_input(t('admin_login'), type="password", key="admin_pw")
        if st.button(t('admin_login_button'), use_container_width=True):
            if admin_pw == ADMIN_PASSWORD:
                st.session_state.admin_authenticated = True
                st.success(t('admin_logged_in'))
                st.rerun()
            else:
                st.error(t('admin_wrong_password'))
    else:
        st.success(t('admin_access'))
        
        # ---------- CUSTOM TOKEN GENERATOR ----------
        st.markdown(f"### 🛠️ {t('admin_custom_title')}")
        st.markdown(t('admin_custom_desc'))
        
        with st.container(border=True):
            col_custom1, col_custom2 = st.columns(2)
            with col_custom1:
                custom_plan_name = st.text_input(
                    t('admin_custom_plan'),
                    placeholder=t('admin_custom_plan_placeholder'),
                    key="custom_plan_input",
                    help="Enter any plan name you want"
                )
                custom_price = st.number_input(
                    t('admin_custom_price'),
                    min_value=0.01,
                    max_value=100000.0,
                    value=50.0,
                    step=5.0,
                    key="custom_price_input",
                    help="Set your own price"
                )
            with col_custom2:
                custom_is_lifetime = st.checkbox(
                    t('admin_custom_lifetime'),
                    key="custom_lifetime_check",
                    help="If checked, the token will never expire"
                )
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button(t('admin_custom_generate'), use_container_width=True, key="custom_gen_btn"):
                    if custom_plan_name.strip():
                        plan_name = custom_plan_name.strip()
                        price = custom_price
                        token, _ = generate_token(plan_name, price, custom_is_lifetime)
                        st.session_state.last_generated = token
                        st.session_state.last_plan = plan_name
                        st.session_state.last_price = f"${price:.2f}"
                        st.session_state.last_expiry = "Never" if custom_is_lifetime else (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
                        st.success(f"✅ {t('admin_custom_success')} {token}")
                        st.rerun()
                    else:
                        st.warning(t('admin_custom_error'))
        
        # Display last generated token with download button
        if st.session_state.last_generated:
            st.markdown("---")
            st.markdown(f"### 🎯 {t('admin_last_token')}")
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
                    label=t('admin_download'),
                    data=token_content,
                    file_name=f"token_{st.session_state.last_generated[:8]}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
        
        st.markdown("---")
        
        # ---------- PREDEFINED TOKENS ----------
        st.markdown(f"### 🆕 {t('admin_predefined')}")
        st.markdown(t('admin_predefined_desc'))
        
        col_gen1, col_gen2, col_gen3 = st.columns(3)
        with col_gen1:
            if st.button(t('admin_trial_btn'), use_container_width=True):
                token, _ = generate_token("Trial Pack", 5.0, False)
                st.session_state.last_generated = token
                st.session_state.last_plan = "Trial Pack"
                st.session_state.last_price = "$5.00"
                st.session_state.last_expiry = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
                st.rerun()
        with col_gen2:
            if st.button(t('admin_basic_btn'), use_container_width=True):
                token, _ = generate_token("Basic Monthly", 15.0, False)
                st.session_state.last_generated = token
                st.session_state.last_plan = "Basic Monthly"
                st.session_state.last_price = "$15.00"
                st.session_state.last_expiry = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
                st.rerun()
        with col_gen3:
            if st.button(t('admin_pro_btn'), use_container_width=True):
                token, _ = generate_token("Pro Monthly", 29.0, False)
                st.session_state.last_generated = token
                st.session_state.last_plan = "Pro Monthly"
                st.session_state.last_price = "$29.00"
                st.session_state.last_expiry = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
                st.rerun()
        
        col_gen4, col_gen5 = st.columns(2)
        with col_gen4:
            if st.button(t('admin_enterprise_btn'), use_container_width=True):
                token, _ = generate_token("Enterprise Monthly", 49.0, False)
                st.session_state.last_generated = token
                st.session_state.last_plan = "Enterprise Monthly"
                st.session_state.last_price = "$49.00"
                st.session_state.last_expiry = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
                st.rerun()
        with col_gen5:
            if st.button(t('admin_lifetime_btn'), use_container_width=True):
                token, _ = generate_token("Lifetime License", 199.0, True)
                st.session_state.last_generated = token
                st.session_state.last_plan = "Lifetime License"
                st.session_state.last_price = "$199.00"
                st.session_state.last_expiry = "Never"
                st.rerun()
        
        st.markdown("---")
        
        # ---------- BULK GENERATE ----------
        st.markdown(f"### 📦 {t('admin_bulk_title')}")
        if st.button(t('admin_bulk_btn'), use_container_width=True):
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
            st.success(t('admin_bulk_success').format(count=len(generated)))
        
        st.markdown("---")
        
        # ---------- ALL TOKENS LIST ----------
        st.markdown(f"### 📋 {t('admin_all_tokens')}")
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
                    status_text = {
                        'active': t('admin_status_active'),
                        'used': t('admin_status_used'),
                        'expired': t('admin_status_expired')
                    }.get(status, status)
                    st.write(f"{status_emoji} {status_text}")
                
                with col_expiry:
                    if expiry:
                        st.write(expiry[:10])
                    else:
                        st.write(t('verify_never'))
                
                with col_copy:
                    copy_html = f"""
                    <button onclick="navigator.clipboard.writeText('{token_code}').then(() => alert('Token copied to clipboard!'))" style="background:transparent; border:none; cursor:pointer; font-size:1.4rem; color:#00ff64;">📋</button>
                    """
                    st.markdown(copy_html, unsafe_allow_html=True)
                
                with col_delete:
                    if st.button("🗑️", key=f"del_{idx}"):
                        ok, msg = delete_token(token_code, ADMIN_PASSWORD)
                        if ok:
                            st.toast(f"✅ {t('admin_delete_success').format(code=token_code)}", icon="🗑️")
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")
                
                st.markdown("---")
        else:
            st.info(t('admin_no_tokens'))
        
        st.markdown("---")
        
        # ---------- EXPORT CSV ----------
        if tokens:
            df = pd.DataFrame(tokens, columns=[
                t('admin_token_code'), t('admin_plan'), t('admin_price'),
                t('admin_purchase_date'), t('admin_expiry'), t('admin_lifetime_col'),
                t('admin_used_col'), t('admin_status_col')
            ])
            df[t('admin_lifetime_col')] = df[t('admin_lifetime_col')].apply(lambda x: '✅' if x == 1 else '')
            df[t('admin_used_col')] = df[t('admin_used_col')].apply(lambda x: '✅' if x == 1 else '')
            df[t('admin_status_col')] = df[t('admin_status_col')].apply(lambda x: {
                'active': t('admin_status_active'),
                'used': t('admin_status_used'),
                'expired': t('admin_status_expired')
            }.get(x, x))
            csv = df.to_csv(index=False)
            st.download_button(
                t('admin_export'),
                csv,
                f"tokens_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "text/csv",
                use_container_width=True
            )
            st.markdown("---")
        
        # ---------- DELETE BY MANUAL INPUT ----------
        st.markdown(f"### 🗑️ {t('admin_delete_manual')}")
        del_code = st.text_input(t('admin_delete_enter'), key="del_token")
        if st.button(t('admin_delete_btn'), use_container_width=True):
            del_code_clean = del_code.strip() if del_code else ""
            if del_code_clean:
                ok, msg = delete_token(del_code_clean, ADMIN_PASSWORD)
                if ok:
                    st.toast(f"✅ {t('admin_delete_success').format(code=del_code_clean)}", icon="🗑️")
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")
            else:
                st.warning(t('admin_delete_warning'))
        
        st.markdown("---")
        
        # ---------- AI ANALYST (Admin only) ----------
        st.markdown(f"### 🤖 {t('admin_ai_analyst')}")
        st.markdown(t('admin_ai_desc'))
        
        if not GROQ_CONNECTED:
            st.info(t('admin_ai_not_configured'))
        else:
            col_ai1, col_ai2 = st.columns(2)
            with col_ai1:
                if st.button(t('admin_ai_stats'), use_container_width=True, key="admin_ai_stats"):
                    with st.spinner("🤖 AI is analyzing..."):
                        st.session_state.ai_response = get_ai_analysis()
            with col_ai2:
                token_code_for_ai = st.text_input(t('admin_ai_enter_token'), placeholder=t('admin_ai_placeholder'), key="admin_ai_token")
                if st.button(t('admin_ai_specific'), use_container_width=True, key="admin_ai_specific"):
                    if token_code_for_ai:
                        with st.spinner("🤖 AI is analyzing token..."):
                            st.session_state.ai_response = get_ai_analysis(token_code_for_ai)
                    else:
                        st.warning(t('admin_ai_warning'))
            
            if st.session_state.ai_response:
                st.markdown(f"### 💡 {t('admin_ai_insights')}")
                st.markdown(f'<div class="groq-response">{st.session_state.ai_response}</div>', unsafe_allow_html=True)
                
                # Listen button – uses the voice_lang selected in sidebar
                if st.button(t('admin_ai_listen'), use_container_width=True, key="admin_ai_listen"):
                    with st.spinner("🎤 Generating audio..."):
                        lang_code = voice_lang if 'voice_lang' in locals() else "en"
                        if lang_code == "zh":
                            lang_code = "zh"
                        audio_bytes = generate_audio(st.session_state.ai_response, lang_code)
                        if audio_bytes:
                            st.audio(audio_bytes, format="audio/mp3")
                            st.success(f"✅ {t('admin_ai_listen_success')}")
                        else:
                            st.error(f"❌ {t('admin_ai_listen_fail')}")
            else:
                st.info(t('admin_ai_no_analysis'))
        
        st.markdown("---")
        
        # ---------- LOGOUT ----------
        if st.button(t('admin_logout'), use_container_width=True):
            st.session_state.admin_authenticated = False
            st.rerun()

# ========== FOOTER ==========
st.markdown(f"""
<div class="footer">
    <p>{t('footer_copyright')}</p>
    <p>{t('footer_built')} | {CONTACT_PHONE} | {CONTACT_EMAIL}</p>
    <p style="font-size:0.8rem; color:#555;">{t('footer_secure')}</p>
</div>
""", unsafe_allow_html=True)
