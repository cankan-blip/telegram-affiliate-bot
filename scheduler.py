from apscheduler.schedulers.background import BackgroundScheduler
import database as db
import telegram_scraper as scraper
import link_transformer as transformer
import publisher as pub
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

logger = logging.getLogger("scheduler")
TZ_TURKEY = ZoneInfo("Europe/Istanbul")
scheduler = BackgroundScheduler(timezone=TZ_TURKEY)

def process_single_sponsor(sponsor_id: int):
    """
    Processes a single sponsor at its scheduled time:
    1. Fetches latest post for the sponsor.
    2. Transforms text with affiliate link and custom CTA.
    3. Publishes to active target channels (deduplicated).
    """
    sponsors = db.get_all_sponsors()
    sponsor = next((s for s in sponsors if s["id"] == sponsor_id), None)
    if not sponsor or not sponsor["is_active"]:
        return
        
    settings = db.get_settings()
    bot_token = settings.get("bot_token", "").strip()
    if not bot_token:
        logger.warning("Job skipped: Bot Token is not configured.")
        return
        
    target_channels = db.get_active_target_channels()
    if not target_channels:
        logger.info("Job skipped: No active target channels found.")
        return
        
    sponsor_name = sponsor["name"]
    source_channel = sponsor["source_channel"]
    affiliate_link = sponsor["affiliate_link"]
    
    cta_text = settings.get("cta_button_text", "🔥 {SPONSOR} GİRİŞ İÇİN TIKLAYINIZ")
    replace_all = settings.get("replace_all_links", "true").lower() == "true"
    add_cta = settings.get("add_cta_button", "true").lower() == "true"
    only_image = settings.get("only_image_mode", "true").lower() == "true"
    
    now_turkey = datetime.now(TZ_TURKEY)
    is_saturday = (now_turkey.weekday() == 5) # 5 = Saturday
    
    transformed_post = None
    original_msg_id = ""
    
    # Mode A: On Saturdays -> Scrape clean image from sponsor's Telegram channel
    if is_saturday:
        logger.info(f"[Saturday Mode] Scraping fresh live banner from @{source_channel} for {sponsor_name}")
        post_data = scraper.fetch_latest_channel_post(source_channel)
        if post_data and post_data.get("photo_url"):
            original_msg_id = post_data.get("msg_id", "")
            transformed_post = transformer.transform_post_content(
                post_data=post_data,
                affiliate_link=affiliate_link,
                sponsor_name=sponsor_name,
                cta_text=cta_text,
                replace_all_links=replace_all,
                add_cta_footer=add_cta,
                only_image_mode=True # Saturday: Only Image + CTA Button
            )
            
    # Mode B: Normal Days (Sunday to Friday) OR Fallback if Saturday scraping has no photo
    if not transformed_post:
        logger.info(f"[Daily Bonus Mode] Building custom bonus & promo post for {sponsor_name}")
        custom_text = sponsor.get("custom_bonus_text")
        if not custom_text:
            custom_text = db.get_default_bonus_text(sponsor_name)
            
        banner_url = sponsor.get("custom_banner_url", "").strip() or None
        
        # If no custom banner URL provided, pull the freshest photo from sponsor channel!
        if not banner_url:
            channel_post = scraper.fetch_latest_channel_post(source_channel)
            if channel_post and channel_post.get("photo_url"):
                banner_url = channel_post.get("photo_url")
                
        original_msg_id = f"bonus_{now_turkey.strftime('%Y%m%d')}_{sponsor_id}"
        
        btn_text = cta_text.replace("{SPONSOR}", sponsor_name.upper()).replace("{sponsor}", sponsor_name)
        if "{SPONSOR}" not in cta_text and "{sponsor}" not in cta_text:
            btn_text = cta_text if cta_text else "🔥 TIKLA GİR - BONUSUNU AL!"
            
        transformed_post = {
            "sponsor_name": sponsor_name,
            "transformed_text": custom_text,
            "photo_url": banner_url,
            "video_url": None,
            "affiliate_link": affiliate_link,
            "cta_text": btn_text,
            "post_mode": "custom_bonus"
        }
        
    for target in target_channels:
        target_id = target["channel_id"]
        target_name = target["channel_name"]
        
        # Enforce 1 post per sponsor per day limit to prevent channel spam
        if db.is_sponsor_posted_today(sponsor_id, target_id):
            logger.info(f"Sponsor '{sponsor_name}' has already published its daily post to {target_name} today. Skipping.")
            continue
            
        if db.is_post_already_sent(sponsor_id, original_msg_id, target_id):
            logger.info(f"Post {original_msg_id} already sent to {target_name}, skipping.")
            continue
            
        res = pub.send_telegram_post(
            bot_token=bot_token,
            target_channel=target_id,
            post=transformed_post,
            cta_text=cta_text,
            add_inline_button=add_cta
        )
        
        status = "SUCCESS" if res.get("success") else "FAILED"
        error_msg = res.get("error", "")
        
        db.log_post_history(
            sponsor_id=sponsor_id,
            sponsor_name=sponsor_name,
            source_channel=source_channel,
            original_msg_id=original_msg_id,
            content_preview=transformed_post["transformed_text"],
            affiliate_link_used=affiliate_link,
            target_channel=f"{target_name} ({target_id})",
            status=status,
            error_msg=error_msg
        )

def run_daily_affiliate_job():
    """Manual or full trigger for all active sponsors."""
    sponsors = db.get_active_sponsors()
    for s in sponsors:
        process_single_sponsor(s["id"])
    return {"status": "completed", "timestamp": datetime.now(TZ_TURKEY).strftime("%Y-%m-%d %H:%M:%S")}

def auto_catchup_daily_posts():
    """
    Periodic catch-up task (runs every 15 minutes).
    ONLY checks if any sponsor's scheduled post hour is EXACTLY in the current hour window,
    preventing all sponsors from firing at once if the server boots up late in the evening.
    """
    settings = db.get_settings()
    if settings.get("auto_post_enabled", "true").lower() != "true":
        return
        
    now_turkey = datetime.now(TZ_TURKEY)
    current_hour = now_turkey.hour
    current_minute = now_turkey.minute
    
    sponsors = db.get_active_sponsors()
    for sponsor in sponsors:
        post_time = sponsor.get("post_time", "12:00")
        try:
            parts = post_time.split(":")
            s_hour = int(parts[0])
            s_minute = int(parts[1]) if len(parts) > 1 else 0
        except Exception:
            s_hour, s_minute = 12, 0
            
        # Strictly catch up ONLY if we are currently in that same hour!
        # Example: At 14:15 catch up Natobet (14:00), but at 21:00 NEVER blast 13:00-19:00 sponsors!
        if current_hour == s_hour and current_minute >= s_minute:
            process_single_sponsor(sponsor["id"])

def keep_alive_ping():
    """Heartbeat job running every 10 minutes to prevent free cloud hosts (like Render) from sleeping."""
    logger.info(f"Keep-alive heartbeat tick [{datetime.now(TZ_TURKEY).strftime('%Y-%m-%d %H:%M:%S')} TRT]: Server active and operational.")

def start_scheduler():
    """Schedules jobs based on settings."""
    if scheduler.running:
        scheduler.remove_all_jobs()
    else:
        scheduler.start()
        
    # 1. 10-minute keep-alive ping
    scheduler.add_job(keep_alive_ping, "interval", minutes=10, id="keep_alive_job")
    
    # 2. 15-minute auto catch-up scanner (ensures zero missed daily posts)
    scheduler.add_job(auto_catchup_daily_posts, "interval", minutes=15, id="auto_catchup_job")
    
    settings = db.get_settings()
    if settings.get("auto_post_enabled", "true").lower() == "true":
        # 3. Individual Sponsor Daily Schedules (Turkey Time UTC+3)
        sponsors = db.get_active_sponsors()
        for sponsor in sponsors:
            post_time = sponsor.get("post_time", "12:00")
            try:
                parts = post_time.split(":")
                hour = int(parts[0])
                minute = int(parts[1]) if len(parts) > 1 else 0
            except Exception:
                hour, minute = 12, 0
                
            job_id = f"sponsor_job_{sponsor['id']}"
            scheduler.add_job(
                process_single_sponsor,
                "cron",
                args=[sponsor["id"]],
                hour=hour,
                minute=minute,
                timezone=TZ_TURKEY,
                misfire_grace_time=3600,
                id=job_id
            )
            logger.info(f"Scheduled Daily Post for Sponsor '{sponsor['name']}' at {hour:02d}:{minute:02d} (Turkey Time)")

def reload_scheduler():
    start_scheduler()
