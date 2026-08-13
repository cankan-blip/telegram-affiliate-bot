from fastapi import FastAPI, Request, Response, HTTPException, Body
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import os
from typing import Optional, List, Dict, Any

import database as db
import telegram_scraper as scraper
import link_transformer as transformer
import publisher as pub
import scheduler as sched

try:
    import frontend_bundle
except ImportError:
    frontend_bundle = None

app = FastAPI(title="Telegram Sponsor & Affiliate Otomasyonu", version="1.0.0")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

# Initialize Database & Scheduler on startup
@app.on_event("startup")
def startup_event():
    db.init_db()
    sched.start_scheduler()

# --- WEB DASHBOARD ROUTE ---
@app.get("/", response_class=HTMLResponse)
def read_dashboard(request: Request):
    index_file = os.path.join(TEMPLATES_DIR, "index.html")
    if os.path.exists(index_file):
        try:
            with open(index_file, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
        except Exception:
            pass
    if frontend_bundle and hasattr(frontend_bundle, "INDEX_HTML"):
        return HTMLResponse(content=frontend_bundle.INDEX_HTML)
    return HTMLResponse(content="<h1>Telegram Affiliate Dashboard</h1><p>Panel yukleniyor...</p>")

@app.get("/static/style.css")
def get_style_css():
    css_file = os.path.join(STATIC_DIR, "style.css")
    if os.path.exists(css_file):
        try:
            with open(css_file, "r", encoding="utf-8") as f:
                return Response(content=f.read(), media_type="text/css")
        except Exception:
            pass
    if frontend_bundle and hasattr(frontend_bundle, "STYLE_CSS"):
        return Response(content=frontend_bundle.STYLE_CSS, media_type="text/css")
    return Response(content="", media_type="text/css")

@app.get("/static/app.js")
def get_app_js():
    js_file = os.path.join(STATIC_DIR, "app.js")
    if os.path.exists(js_file):
        try:
            with open(js_file, "r", encoding="utf-8") as f:
                return Response(content=f.read(), media_type="application/javascript")
        except Exception:
            pass
    if frontend_bundle and hasattr(frontend_bundle, "APP_JS"):
        return Response(content=frontend_bundle.APP_JS, media_type="application/javascript")
    return Response(content="", media_type="application/javascript")

# --- STATS API ---
@app.get("/api/stats")
def get_stats():
    sponsors = db.get_all_sponsors()
    targets = db.get_all_target_channels()
    history = db.get_post_history(100)
    settings = db.get_settings()
    
    total_sent = sum(1 for h in history if h["status"] == "SUCCESS")
    total_failed = sum(1 for h in history if h["status"] == "FAILED")
    
    return {
        "total_sponsors": len(sponsors),
        "active_sponsors": sum(1 for s in sponsors if s["is_active"] == 1),
        "total_targets": len(targets),
        "active_targets": sum(1 for t in targets if t["is_active"] == 1),
        "total_sent": total_sent,
        "total_failed": total_failed,
        "auto_post_enabled": settings.get("auto_post_enabled", "true").lower() == "true",
        "post_schedule": f"{int(settings.get('post_hour', 12)):02d}:{int(settings.get('post_minute', 0)):02d}"
    }

# --- SPONSORS API ---
# --- SPONSORS API ---
class SponsorCreate(BaseModel):
    name: str
    source_channel: str
    affiliate_link: str
    post_time: Optional[str] = "12:00"
    custom_bonus_text: Optional[str] = ""
    custom_banner_url: Optional[str] = ""

class SponsorUpdate(BaseModel):
    name: str
    source_channel: str
    affiliate_link: str
    is_active: int
    post_time: Optional[str] = "12:00"
    custom_bonus_text: Optional[str] = ""
    custom_banner_url: Optional[str] = ""

@app.get("/api/sponsors")
def list_sponsors():
    return db.get_all_sponsors()

@app.post("/api/sponsors")
def create_sponsor(sponsor: SponsorCreate):
    if not sponsor.name or not sponsor.source_channel or not sponsor.affiliate_link:
        raise HTTPException(status_code=400, detail="Lütfen tüm zorunlu alanları doldurun.")
    new_sponsor = db.add_sponsor(
        name=sponsor.name,
        source_channel=sponsor.source_channel,
        affiliate_link=sponsor.affiliate_link,
        post_time=sponsor.post_time or "12:00",
        custom_bonus_text=sponsor.custom_bonus_text or "",
        custom_banner_url=sponsor.custom_banner_url or ""
    )
    sched.reload_scheduler()
    return {"success": True, "sponsor": new_sponsor}

@app.put("/api/sponsors/{sponsor_id}")
def edit_sponsor(sponsor_id: int, sponsor: SponsorUpdate):
    db.update_sponsor(
        sponsor_id=sponsor_id,
        name=sponsor.name,
        source_channel=sponsor.source_channel,
        affiliate_link=sponsor.affiliate_link,
        is_active=sponsor.is_active,
        post_time=sponsor.post_time or "12:00",
        custom_bonus_text=sponsor.custom_bonus_text or "",
        custom_banner_url=sponsor.custom_banner_url or ""
    )
    sched.reload_scheduler()
    return {"success": True}

@app.delete("/api/sponsors/{sponsor_id}")
def remove_sponsor(sponsor_id: int):
    db.delete_sponsor(sponsor_id)
    sched.reload_scheduler()
    return {"success": True}

# --- TARGET CHANNELS API ---
class TargetChannelCreate(BaseModel):
    channel_id: str
    channel_name: str

@app.get("/api/target-channels")
def list_target_channels():
    return db.get_all_target_channels()

@app.post("/api/target-channels")
def create_target_channel(target: TargetChannelCreate):
    if not target.channel_id or not target.channel_name:
        raise HTTPException(status_code=400, detail="Kanal ID ve Adı zorunludur.")
    new_target = db.add_target_channel(target.channel_id, target.channel_name)
    return {"success": True, "target": new_target}

@app.delete("/api/target-channels/{target_id}")
def remove_target_channel(target_id: int):
    db.delete_target_channel(target_id)
    return {"success": True}

@app.put("/api/target-channels/{target_id}/toggle")
def toggle_target(target_id: int, is_active: int = Body(..., embed=True)):
    db.toggle_target_channel(target_id, is_active)
    return {"success": True}

# --- SETTINGS API ---
@app.get("/api/settings")
def get_settings():
    return db.get_settings()

@app.post("/api/settings")
def update_settings(settings: Dict[str, str]):
    db.save_settings(settings)
    sched.reload_scheduler()
    return {"success": True, "message": "Ayarlar kaydedildi ve zamanlayıcı güncellendi."}

# --- BOT TEST & MANUAL TRIGGER API ---
@app.post("/api/test-bot")
def test_bot(bot_token: str = Body(..., embed=True)):
    return pub.test_bot_connection(bot_token)

@app.get("/api/preview-sponsor-post/{sponsor_id}")
def preview_sponsor_post(sponsor_id: int):
    sponsors = db.get_all_sponsors()
    sponsor = next((s for s in sponsors if s["id"] == sponsor_id), None)
    if not sponsor:
        raise HTTPException(status_code=404, detail="Sponsor bulunamadı")
        
    settings = db.get_settings()
    cta_text = settings.get("cta_button_text", "🔥 TIKLA GİR - BONUSUNU AL!")
    
    # Check custom bonus post
    custom_text = sponsor.get("custom_bonus_text") or db.get_default_bonus_text(sponsor["name"])
    banner_url = sponsor.get("custom_banner_url", "").strip() or None
    
    # Check Saturday live channel scrape
    live_post = scraper.fetch_latest_channel_post(sponsor["source_channel"])
    
    btn_text = cta_text.replace("{SPONSOR}", sponsor["name"].upper()).replace("{sponsor}", sponsor["name"])
    if "{SPONSOR}" not in cta_text and "{sponsor}" not in cta_text:
        btn_text = cta_text if cta_text else "🔥 TIKLA GİR - BONUSUNU AL!"
    
    preview_data = {
        "sponsor_name": sponsor["name"],
        "source_channel": sponsor["source_channel"],
        "affiliate_link": sponsor["affiliate_link"],
        "cta_text": btn_text,
        # Normal Day post preview
        "daily_bonus_text": custom_text,
        "daily_banner_url": banner_url,
        "transformed_text": custom_text,
        "photo_url": banner_url or (live_post.get("photo_url") if live_post else None),
        # Saturday live channel post preview
        "saturday_photo_url": live_post.get("photo_url") if live_post else None,
        "has_live_channel": live_post is not None
    }
    
    return {"success": True, "preview": preview_data}

@app.post("/api/trigger-job-now")
def trigger_job_now():
    result = sched.run_daily_affiliate_job()
    return result

class SingleTestPost(BaseModel):
    sponsor_id: int
    target_channel_id: str

@app.post("/api/send-single-test-post")
def send_single_test_post(req: SingleTestPost):
    sponsors = db.get_all_sponsors()
    sponsor = next((s for s in sponsors if s["id"] == req.sponsor_id), None)
    if not sponsor:
        raise HTTPException(status_code=404, detail="Sponsor bulunamadı")
        
    settings = db.get_settings()
    bot_token = settings.get("bot_token", "").strip()
    if not bot_token:
        raise HTTPException(status_code=400, detail="Telegram Bot Token ayarlar kısmında tanımlanmamış.")
        
    cta_text = settings.get("cta_button_text", "🔥 TIKLA GİR - BONUSUNU AL!")
    btn_text = cta_text.replace("{SPONSOR}", sponsor["name"].upper()).replace("{sponsor}", sponsor["name"])
    if "{SPONSOR}" not in cta_text and "{sponsor}" not in cta_text:
        btn_text = cta_text if cta_text else "🔥 TIKLA GİR - BONUSUNU AL!"
    
    custom_text = sponsor.get("custom_bonus_text") or db.get_default_bonus_text(sponsor["name"])
    banner_url = sponsor.get("custom_banner_url", "").strip() or None
    
    # Try channel photo if banner_url is empty
    if not banner_url:
        live_post = scraper.fetch_latest_channel_post(sponsor["source_channel"])
        if live_post and live_post.get("photo_url"):
            banner_url = live_post.get("photo_url")
            
    transformed = {
        "sponsor_name": sponsor["name"],
        "transformed_text": custom_text,
        "photo_url": banner_url,
        "video_url": None,
        "affiliate_link": sponsor["affiliate_link"],
        "cta_text": btn_text
    }
    
    res = pub.send_telegram_post(
        bot_token=bot_token,
        target_channel=req.target_channel_id,
        post=transformed,
        cta_text=btn_text,
        add_inline_button=True
    )
    
    status = "SUCCESS" if res.get("success") else "FAILED"
    db.log_post_history(
        sponsor_id=sponsor["id"],
        sponsor_name=sponsor["name"],
        source_channel=sponsor["source_channel"],
        original_msg_id=post_data.get("msg_id", ""),
        content_preview=transformed["transformed_text"],
        affiliate_link_used=sponsor["affiliate_link"],
        target_channel=req.target_channel_id,
        status=status,
        error_msg=res.get("error", "")
    )
    
    return res

# --- HISTORY API ---
@app.get("/api/history")
def get_history(limit: int = 50):
    return db.get_post_history(limit)
