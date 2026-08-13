import sqlite3
import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Sponsors Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sponsors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        source_channel TEXT NOT NULL UNIQUE,
        affiliate_link TEXT NOT NULL,
        is_active INTEGER DEFAULT 1,
        created_at TEXT NOT NULL,
        post_time TEXT DEFAULT '12:00',
        custom_bonus_text TEXT DEFAULT '',
        custom_banner_url TEXT DEFAULT ''
    )
    """)
    
    # Add columns if upgrading existing table
    try:
        cursor.execute("ALTER TABLE sponsors ADD COLUMN custom_bonus_text TEXT DEFAULT ''")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE sponsors ADD COLUMN custom_banner_url TEXT DEFAULT ''")
    except Exception:
        pass

    # Target Channels Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS target_channels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_id TEXT NOT NULL UNIQUE,
        channel_name TEXT NOT NULL,
        is_active INTEGER DEFAULT 1,
        created_at TEXT NOT NULL
    )
    """)
    
    # System Settings Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """)
    
    # Post History Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS post_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sponsor_id INTEGER,
        sponsor_name TEXT,
        source_channel TEXT,
        original_msg_id TEXT,
        content_preview TEXT,
        affiliate_link_used TEXT,
        target_channel TEXT,
        status TEXT,
        error_msg TEXT,
        sent_at TEXT,
        FOREIGN KEY (sponsor_id) REFERENCES sponsors (id)
    )
    """)
    
    # Insert Default Settings if empty
    default_settings = {
        "bot_token": "8669146607:AAEHgQD8k_jUPRPaS8bGEEx6vYGnG9l2by0",
        "post_hour": "12",
        "post_minute": "00",
        "auto_post_enabled": "true",
        "cta_button_text": "🔥 TIKLA GİR - BONUSUNU AL!",
        "add_cta_button": "true",
        "replace_all_links": "true",
        "only_image_mode": "true",
        "check_interval_hours": "1"
    }
    
    for key, value in default_settings.items():
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value))
        
    # Pre-seed Sponsors with exact user texts and phototourl banner links
    default_sponsors = [
        {
            "name": "casivera",
            "source_channel": "@casivera",
            "affiliate_link": "https://csvera.link/BocekCasino",
            "post_time": "12:00",
            "custom_banner_url": "https://cdn.phototourl.com/member/2026-08-13-94356eb1-3d75-4401-808d-c004775475fc.jpg",
            "custom_bonus_text": "⚔️ 1.000 TL DENEME BONUSU!\n\n⚡ %30 KAYIP BONUSU!\n\n🎰 HERGÜN HEDİYE FREESPİN!\n\n🎉 100 TL HAVALE YATIRIMI!"
        },
        {
            "name": "robinbet",
            "source_channel": "@robinresmi",
            "affiliate_link": "https://robinaa.xyz/pwyxlj",
            "post_time": "13:00",
            "custom_banner_url": "https://cdn.phototourl.com/member/2026-08-13-674f5325-77a0-4983-b00c-85f33e44cca0.png",
            "custom_bonus_text": "⚔️ 500 TL DENEME BONUSU!\n\n🎯 HERGÜN BEDAVA FREESPİN!\n\n⚡ %30 KAYIP BONUSU!\n\n🎉 250 TL HAVALE YATIRIMI!"
        },
        {
            "name": "Natobet",
            "source_channel": "@natobet",
            "affiliate_link": "https://track.natoaff.com/processing/click?btag=27008",
            "post_time": "14:00",
            "custom_banner_url": "https://cdn.phototourl.com/member/2026-08-13-ee64fc40-44d4-4161-86da-4569998ef713.jpg",
            "custom_bonus_text": "⚔️ 250 TL DENEME BONUSU!\n\n🎁 %200 HOŞGELDİN BONUS FIRSATI!\n\n⚡ %20 KAYIP BONUSU!\n\n🎉 250TL HAVALE YATIRIMI!"
        },
        {
            "name": "Beygirbet",
            "source_channel": "@beygirbetresmisosyal",
            "affiliate_link": "https://beygirbetxyls.xyz/cnkn",
            "post_time": "15:00",
            "custom_banner_url": "https://cdn.phototourl.com/member/2026-08-13-6af2a473-2b0b-43a2-918d-413b88e5955b.jpg",
            "custom_bonus_text": "⚔️ 333 FREESPİN  DENEME BONUSU!\n\n⚡ %20 ANLIK +%5 HAFTALIK KAYIP BONUSU!\n\n🎉 250 TL HAVALE YATIRIMI!"
        },
        {
            "name": "Betbey",
            "source_channel": "@bbeysociall",
            "affiliate_link": "https://bbey.live/?btag=269469",
            "post_time": "16:00",
            "custom_banner_url": "https://cdn.phototourl.com/member/2026-08-13-f35be8d4-558b-4587-ab54-e2bca2a1a790.png",
            "custom_bonus_text": "⚔️ 800 TL DENEME BONUSU!\n\n🎁 %100 HOŞGELDİN BONUS FIRSATI!\n\n⚡ %35 KAYIP BONUSU!\n\n🎉 250 TL HAVALE YATIRIMI!"
        },
        {
            "name": "Casinodior",
            "source_channel": "@diorresminew",
            "affiliate_link": "https://www.diorlink.com/links/?btag=2779471",
            "post_time": "17:00",
            "custom_banner_url": "https://cdn.phototourl.com/member/2026-08-13-901c4eb9-92cc-4b35-9ef8-7de0403ef9a1.jpg",
            "custom_bonus_text": "⚔️ 777 FREESPİN DENEME BONUSU!\n\n🎯 HERGÜN BEDAVA FREESPİN!\n\n⚡ %40 KAYIP BONUSU!\n\n🎉 100 TL HAVALE YATIRIMI!"
        },
        {
            "name": "galyabet",
            "source_channel": "@galyabetcom",
            "affiliate_link": "https://t.ly/9jEq_",
            "post_time": "18:00",
            "custom_banner_url": "https://cdn.phototourl.com/member/2026-08-13-2bc9feb7-aa05-459b-ac9e-4461d26a766d.png",
            "custom_bonus_text": "⚔️ 750 TL DENEME BONUSU!\n\n🎁 %100 CASINO & SPOR HOŞGELDİN!\n\n⚡ %30 ANLIK KAYIP BONUSU!\n\n🎰 GÜNLÜK HEDİYE FREESPIN!\n\n🎉 500 TL HAVALE YATIRIMI!"
        },
        {
            "name": "Bankobet",
            "source_channel": "@bankobettg",
            "affiliate_link": "https://bankogirisi.com/jhya1h",
            "post_time": "19:00",
            "custom_banner_url": "https://cdn.phototourl.com/member/2026-08-13-3750c441-f236-48c4-98c1-7c1346ffd5ae.jpg",
            "custom_bonus_text": "⚔️ 1.000 TL DENEME BONUSU!\n\n🎯 DEV MAÇLARA ÖZEL EKSTRA ORAN!\n\n⚡ %25 HAFTALIK KAYIP BONUSU!\n\n🎉 100 TL HAVALE YATIRIMI!"
        }
    ]
    
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for s in default_sponsors:
        cursor.execute("SELECT id FROM sponsors WHERE lower(name) = lower(?)", (s["name"],))
        existing_row = cursor.fetchone()
        if not existing_row:
            cursor.execute(
                "INSERT INTO sponsors (name, source_channel, affiliate_link, is_active, created_at, post_time, custom_bonus_text, custom_banner_url) VALUES (?, ?, ?, 1, ?, ?, ?, ?)",
                (s["name"], s["source_channel"], s["affiliate_link"], now_str, s["post_time"], s["custom_bonus_text"], s["custom_banner_url"])
            )
            
    # Pre-seed Target Channels
    default_targets = [
        ("@bocekbet", "Böcek Bet"),
        ("@bonusveren2027", "Bonus Veren Siteler"),
        ("@bocekbetsohbet", "Böcek Bet Sohbet"),
        ("@denemebonussitesi2027", "Deneme Bonusu Sitesi"),
        ("@denemebonususiteleri2027", "Deneme Bonusu Siteleri"),
        ("@bocekbetozeloran", "Böcek Bet Özel Oran"),
        ("@egebetresmigiris", "Egebet Resmi Giriş"),
        ("@dedebetresmigiris", "Dedebet Resmi Giriş"),
        ("@denemebonusuverensite2027", "Deneme Bonusu Veren Site"),
        ("@betineresmigiris", "Betine Resmi Giriş")
    ]
    for cid, cname in default_targets:
        cursor.execute("INSERT OR IGNORE INTO target_channels (channel_id, channel_name, is_active, created_at) VALUES (?, ?, 1, ?)", (cid, cname, now_str))

    conn.commit()
    conn.close()

def get_default_bonus_text(name: str) -> str:
    s = name.upper()
    return (
        f"🔥 **{s} | ÖZEL DENEME BONUSU & FREESPIN!** 🎁\n\n"
        f"⚡ **Yatırımsız & Çevrimsiz Anında Hesabında!**\n"
        f"🎰 Pragmatic Play & En Çok Kazandıran Slotlar\n"
        f"💎 VIP Oranlar ve 7/24 Limitsiz Çekim Garantisi!\n\n"
        f"👇 *Fırsatı kaçırmamak için aşağıdaki butona tıklayın:*"
    )

# --- SPONSOR OPERATIONS ---
def get_all_sponsors() -> List[Dict[str, Any]]:
    conn = get_db()
    rows = conn.execute("SELECT * FROM sponsors ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_active_sponsors() -> List[Dict[str, Any]]:
    conn = get_db()
    rows = conn.execute("SELECT * FROM sponsors WHERE is_active = 1").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_sponsor(name: str, source_channel: str, affiliate_link: str, post_time: str = "12:00", custom_bonus_text: str = "", custom_banner_url: str = "") -> Dict[str, Any]:
    # Clean channel format
    channel = source_channel.strip()
    if channel.startswith("https://t.me/"):
        channel = "@" + channel.replace("https://t.me/", "").strip("/")
    elif channel.startswith("t.me/"):
        channel = "@" + channel.replace("t.me/", "").strip("/")
    elif not channel.startswith("@"):
        channel = "@" + channel

    if not custom_bonus_text:
        custom_bonus_text = get_default_bonus_text(name)

    conn = get_db()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO sponsors (name, source_channel, affiliate_link, is_active, created_at, post_time, custom_bonus_text, custom_banner_url) VALUES (?, ?, ?, 1, ?, ?, ?, ?)",
        (name, channel, affiliate_link, now, post_time, custom_bonus_text, custom_banner_url)
    )
    conn.commit()
    sponsor_id = cursor.lastrowid
    conn.close()
    return {
        "id": sponsor_id, 
        "name": name, 
        "source_channel": channel, 
        "affiliate_link": affiliate_link, 
        "post_time": post_time,
        "custom_bonus_text": custom_bonus_text,
        "custom_banner_url": custom_banner_url
    }

def update_sponsor(sponsor_id: int, name: str, source_channel: str, affiliate_link: str, is_active: int, post_time: str = "12:00", custom_bonus_text: str = "", custom_banner_url: str = ""):
    channel = source_channel.strip()
    if channel.startswith("https://t.me/"):
        channel = "@" + channel.replace("https://t.me/", "").strip("/")
    elif channel.startswith("t.me/"):
        channel = "@" + channel.replace("t.me/", "").strip("/")
    elif not channel.startswith("@"):
        channel = "@" + channel

    if not custom_bonus_text:
        custom_bonus_text = get_default_bonus_text(name)

    conn = get_db()
    conn.execute(
        "UPDATE sponsors SET name = ?, source_channel = ?, affiliate_link = ?, is_active = ?, post_time = ?, custom_bonus_text = ?, custom_banner_url = ? WHERE id = ?",
        (name, channel, affiliate_link, is_active, post_time, custom_bonus_text, custom_banner_url, sponsor_id)
    )
    conn.commit()
    conn.close()

def delete_sponsor(sponsor_id: int):
    conn = get_db()
    conn.execute("DELETE FROM sponsors WHERE id = ?", (sponsor_id,))
    conn.commit()
    conn.close()

# --- TARGET CHANNELS OPERATIONS ---
def get_all_target_channels() -> List[Dict[str, Any]]:
    conn = get_db()
    rows = conn.execute("SELECT * FROM target_channels ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_active_target_channels() -> List[Dict[str, Any]]:
    conn = get_db()
    rows = conn.execute("SELECT * FROM target_channels WHERE is_active = 1").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_target_channel(channel_id: str, channel_name: str) -> Dict[str, Any]:
    cid = channel_id.strip()
    if cid.startswith("https://t.me/"):
        cid = "@" + cid.replace("https://t.me/", "").strip("/")
    elif cid.startswith("t.me/"):
        cid = "@" + cid.replace("t.me/", "").strip("/")
    elif not cid.startswith("@") and not cid.startswith("-"):
        cid = "@" + cid

    conn = get_db()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO target_channels (channel_id, channel_name, is_active, created_at) VALUES (?, ?, 1, ?)",
        (cid, channel_name, now)
    )
    conn.commit()
    tid = cursor.lastrowid
    conn.close()
    return {"id": tid, "channel_id": cid, "channel_name": channel_name}

def delete_target_channel(target_id: int):
    conn = get_db()
    conn.execute("DELETE FROM target_channels WHERE id = ?", (target_id,))
    conn.commit()
    conn.close()

def toggle_target_channel(target_id: int, is_active: int):
    conn = get_db()
    conn.execute("UPDATE target_channels SET is_active = ? WHERE id = ?", (is_active, target_id))
    conn.commit()
    conn.close()

# --- SETTINGS OPERATIONS ---
def get_settings() -> Dict[str, str]:
    conn = get_db()
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}

def save_settings(settings_dict: Dict[str, str]):
    conn = get_db()
    for key, value in settings_dict.items():
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

# --- POST HISTORY OPERATIONS ---
def is_post_already_sent(sponsor_id: int, original_msg_id: str, target_channel: str) -> bool:
    conn = get_db()
    row = conn.execute(
        "SELECT id FROM post_history WHERE sponsor_id = ? AND original_msg_id = ? AND target_channel = ? AND status = 'SUCCESS'",
        (sponsor_id, str(original_msg_id), str(target_channel))
    ).fetchone()
    conn.close()
    return row is not None

def is_sponsor_posted_today(sponsor_id: int, target_channel: str) -> bool:
    conn = get_db()
    today_str = datetime.now().strftime("%Y-%m-%d")
    row = conn.execute(
        "SELECT id FROM post_history WHERE sponsor_id = ? AND target_channel = ? AND status = 'SUCCESS' AND sent_at LIKE ?",
        (sponsor_id, str(target_channel), f"{today_str}%")
    ).fetchone()
    conn.close()
    return row is not None

def log_post_history(sponsor_id: int, sponsor_name: str, source_channel: str, original_msg_id: str, content_preview: str, affiliate_link_used: str, target_channel: str, status: str, error_msg: str = ""):
    conn = get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        """INSERT INTO post_history 
        (sponsor_id, sponsor_name, source_channel, original_msg_id, content_preview, affiliate_link_used, target_channel, status, error_msg, sent_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (sponsor_id, sponsor_name, source_channel, str(original_msg_id), content_preview[:200], affiliate_link_used, target_channel, status, error_msg, now)
    )
    conn.commit()
    conn.close()

def get_post_history(limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_db()
    rows = conn.execute("SELECT * FROM post_history ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
