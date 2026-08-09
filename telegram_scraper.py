import httpx
from bs4 import BeautifulSoup
import re
from typing import Dict, Any, Optional, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("telegram_scraper")

def clean_channel_username(channel_input: str) -> str:
    channel = channel_input.strip()
    if channel.startswith("https://t.me/s/"):
        channel = channel.replace("https://t.me/s/", "")
    elif channel.startswith("https://t.me/"):
        channel = channel.replace("https://t.me/", "")
    elif channel.startswith("t.me/s/"):
        channel = channel.replace("t.me/s/", "")
    elif channel.startswith("t.me/"):
        channel = channel.replace("t.me/", "")
    if channel.startswith("@"):
        channel = channel[1:]
    return channel.strip("/")

BONUS_KEYWORDS = [
    'bonus', 'freespin', 'free spin', 'yatırım', 'oran', 'fırsat', 'kayıp', 
    'hoşgeldin', 'etkinlik', 'çekiliş', 'ödül', 'turnuva', 'freebet', 
    'promosyon', 'nakit', 'çevrim', 'çevrimsiz', 'özel oran', 'kazan', 
    'kazanç', 'jackpot', 'pragmatic', 'sweet bonanza', 'gates of olympus'
]

def fetch_latest_channel_post(channel_input: str) -> Optional[Dict[str, Any]]:
    """
    Fetches the best bonus/promotion photo post from a public Telegram channel via t.me/s/{channel_name}.
    Scores posts based on bonus keywords and recency to ensure maximum engagement.
    """
    channel_name = clean_channel_username(channel_input)
    url = f"https://t.me/s/{channel_name}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    
    try:
        with httpx.Client(timeout=15.0, follow_redirects=True, headers=headers) as client:
            response = client.get(url)
            if response.status_code != 200:
                logger.error(f"Failed to fetch channel {channel_name}, HTTP {response.status_code}")
                return None
                
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Find all message widgets with data-post
            messages = soup.find_all("div", attrs={"data-post": True})
            if not messages:
                messages = soup.find_all("div", class_=re.compile(r"tgme_widget_message\b"))
                
            if not messages:
                logger.warning(f"No messages found for channel @{channel_name}")
                return None
                
            candidates = []
            
            # Evaluate all messages from oldest to newest
            for idx, msg in enumerate(messages):
                classes = msg.get("class", [])
                if "service_message" in classes:
                    continue
                    
                text_div = msg.find("div", class_="tgme_widget_message_text")
                raw_text = text_div.get_text(separator="\n", strip=True) if text_div else ""
                lower_text = raw_text.lower()
                
                # Exclude pin / system notifications
                if "pinned a photo" in lower_text or "pinned a message" in lower_text:
                    continue
                    
                # Extract Photo URL
                photo_url = None
                photo_elements = msg.find_all(class_=re.compile(r"tgme_widget_message_photo"))
                for pe in photo_elements:
                    style = pe.get("style", "")
                    bg_match = re.search(r"background-image:\s*url\(['\"]?(https://[^'\"]+)['\"]?\)", style)
                    if bg_match:
                        photo_url = bg_match.group(1)
                        break
                        
                if not photo_url:
                    for tag in msg.find_all(True):
                        style = tag.get("style", "")
                        if "telesco.pe" in style or "cdn" in style:
                            bg_match = re.search(r"background-image:\s*url\(['\"]?(https://[^'\"]+)['\"]?\)", style)
                            if bg_match:
                                photo_url = bg_match.group(1)
                                break
                                
                video_url = None
                video_thumb = msg.find("i", class_=re.compile(r"tgme_widget_message_video_thumb"))
                if video_thumb and not photo_url:
                    style = video_thumb.get("style", "")
                    bg_match = re.search(r"background-image:url\('([^']+)'\)", style)
                    if bg_match:
                        photo_url = bg_match.group(1)
                        
                video_tag = msg.find("video")
                if video_tag and video_tag.get("src"):
                    video_url = video_tag.get("src")
                    
                # We prioritize posts that have a photo
                if not photo_url and not text_div:
                    continue
                    
                # Extract Post ID
                post_data = msg.get("data-post", "")
                msg_id = post_data.split("/")[-1] if "/" in post_data else post_data
                
                # Extract links
                embedded_links = []
                if text_div:
                    for a in text_div.find_all("a"):
                        href = a.get("href", "")
                        link_text = a.get_text(strip=True)
                        if href and not href.startswith("https://t.me/"):
                            embedded_links.append({"text": link_text, "url": href})
                            
                # Extract Timestamp
                time_tag = msg.find("time", class_="time")
                msg_date = time_tag.get("datetime", "") if time_tag else ""
                
                # Calculate bonus score
                kw_matches = [kw for kw in BONUS_KEYWORDS if kw in lower_text]
                # High score if photo + bonus keywords + recency
                score = (100 if photo_url else 10) + (len(kw_matches) * 25) + (idx * 2)
                
                candidates.append({
                    "score": score,
                    "msg_id": msg_id,
                    "text": raw_text,
                    "html_text": str(text_div) if text_div else "",
                    "photo_url": photo_url,
                    "video_url": video_url,
                    "date": msg_date,
                    "channel_username": channel_name,
                    "embedded_links": embedded_links,
                    "keywords": kw_matches
                })
                
            if not candidates:
                logger.warning(f"No valid candidates found for channel @{channel_name}")
                return None
                
            # Filter candidates that have photos if any exist
            photo_candidates = [c for c in candidates if c["photo_url"]]
            pool = photo_candidates if photo_candidates else candidates
            
            # Select the highest-scoring candidate
            best_post = max(pool, key=lambda c: c["score"])
            best_post["post_url"] = f"https://t.me/{channel_name}/{best_post['msg_id']}" if best_post.get("msg_id") else f"https://t.me/s/{channel_name}"
            logger.info(f"Selected best post for @{channel_name}: msg_id={best_post['msg_id']}, score={best_post['score']}, kw={best_post['keywords']}")
            return best_post
            
    except Exception as e:
        logger.error(f"Error scraping @{channel_name}: {e}")
        return None
        logger.error(f"Error scraping channel @{channel_name}: {e}")
        return None
