from apscheduler.schedulers.background import BackgroundScheduler
import database as db
import telegram_scraper as scraper
import link_transformer as transformer
import publisher as pub
import logging
from datetime import datetime

logger = logging.getLogger("scheduler")
scheduler = BackgroundScheduler()

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
    
    logger.info(f"Processing scheduled sponsor: {sponsor_name} (@{source_channel}) [OnlyImageMode={only_image}]")
    
    post_data = scraper.fetch_latest_channel_post(source_channel)
    if not post_data:
        logger.warning(f"Could not fetch latest post from @{source_channel}")
        return
        
    original_msg_id = post_data.get("msg_id", "")
    
    transformed_post = transformer.transform_post_content(
        post_data=post_data,
        affiliate_link=affiliate_link,
        sponsor_name=sponsor_name,
        cta_text=cta_text,
        replace_all_links=replace_all,
        add_cta_footer=add_cta,
        only_image_mode=only_image
    )
    
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
    return {"status": "completed", "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

def keep_alive_ping():
    """Heartbeat job running every 10 minutes to prevent free cloud hosts (like Render) from sleeping."""
    logger.info("Keep-alive heartbeat tick: Server active and operational.")

def start_scheduler():
    """Schedules jobs based on settings."""
    if scheduler.running:
        scheduler.remove_all_jobs()
    else:
        scheduler.start()
        
    # 1. 10-minute keep-alive ping to ensure server stays awake 24/7
    scheduler.add_job(keep_alive_ping, "interval", minutes=10, id="keep_alive_job")
    
    settings = db.get_settings()
    if settings.get("auto_post_enabled", "true").lower() == "true":
        # 2. Individual Sponsor Daily Schedules (Staggered times, strictly 1 post per sponsor per day)
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
                id=job_id
            )
            logger.info(f"Scheduled Daily Post for Sponsor '{sponsor['name']}' at {hour:02d}:{minute:02d}")

def reload_scheduler():
    start_scheduler()
