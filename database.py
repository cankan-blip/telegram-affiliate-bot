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
        post_time TEXT DEFAULT '12:00'
    )
    """)

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
        "bot_token": "",
        "post_hour": "12",
        "post_minute": "00",
        "auto_post_enabled": "true",
        "cta_button_text": "🔥 {SPONSOR} GİRİŞ İÇİN TIKLAYINIZ",
        "add_cta_button": "true",
        "replace_all_links": "true",
        "only_image_mode": "true",
        "check_interval_hours": "1"
    }
    
    for key, value in default_settings.items():
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value))
        
    conn.commit()
    conn.close()

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

def add_sponsor(name: str, source_channel: str, affiliate_link: str, post_time: str = "12:00") -> Dict[str, Any]:
    # Clean channel format
    channel = source_channel.strip()
    if channel.startswith("https://t.me/"):
        channel = "@" + channel.replace("https://t.me/", "").strip("/")
    elif channel.startswith("t.me/"):
        channel = "@" + channel.replace("t.me/", "").strip("/")
    elif not channel.startswith("@"):
        channel = "@" + channel

    conn = get_db()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO sponsors (name, source_channel, affiliate_link, is_active, created_at, post_time) VALUES (?, ?, ?, 1, ?, ?)",
        (name, channel, affiliate_link, now, post_time)
    )
    conn.commit()
    sponsor_id = cursor.lastrowid
    conn.close()
    return {"id": sponsor_id, "name": name, "source_channel": channel, "affiliate_link": affiliate_link, "post_time": post_time}

def update_sponsor(sponsor_id: int, name: str, source_channel: str, affiliate_link: str, is_active: int, post_time: str = "12:00"):
    channel = source_channel.strip()
    if channel.startswith("https://t.me/"):
        channel = "@" + channel.replace("https://t.me/", "").strip("/")
    elif channel.startswith("t.me/"):
        channel = "@" + channel.replace("t.me/", "").strip("/")
    elif not channel.startswith("@"):
        channel = "@" + channel

    conn = get_db()
    conn.execute(
        "UPDATE sponsors SET name = ?, source_channel = ?, affiliate_link = ?, is_active = ?, post_time = ? WHERE id = ?",
        (name, channel, affiliate_link, is_active, post_time, sponsor_id)
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
