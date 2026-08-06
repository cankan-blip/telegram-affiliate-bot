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

def fetch_latest_channel_post(channel_input: str) -> Optional[Dict[str, Any]]:
    """
    Fetches the latest post from a public Telegram channel via t.me/s/{channel_name}.
    Returns a dictionary containing:
    - msg_id: str
    - text: str (raw text)
    - html_text: str (with original links preserved)
    - photo_url: Optional[str]
    - video_url: Optional[str]
    - date: str
    - channel_username: str
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
            
            # Find all message widgets
            messages = soup.find_all("div", class_=re.compile(r"tgme_widget_message\b"))
            if not messages:
                logger.warning(f"No messages found for channel @{channel_name}")
                return None
                
            # Take the last message (latest)
            latest_msg = None
            for msg in reversed(messages):
                # Ensure it has text or media content
                text_div = msg.find("div", class_="tgme_widget_message_text")
                photo_div = msg.find("a", class_=re.compile(r"tgme_widget_message_photo_default"))
                video_div = msg.find("a", class_=re.compile(r"tgme_widget_message_video_player"))
                
                if text_div or photo_div or video_div:
                    latest_msg = msg
                    break
                    
            if not latest_msg:
                return None
                
            # Extract Post ID
            post_data = latest_msg.get("data-post", "")
            msg_id = post_data.split("/")[-1] if "/" in post_data else post_data
            
            # Extract Text & HTML
            text_div = latest_msg.find("div", class_="tgme_widget_message_text")
            raw_text = text_div.get_text(separator="\n", strip=True) if text_div else ""
            
            # Extract links in the post
            embedded_links = []
            if text_div:
                for a in text_div.find_all("a"):
                    href = a.get("href", "")
                    link_text = a.get_text(strip=True)
                    if href and not href.startswith("https://t.me/"): # Exclude telegram hashtag/mention links if needed
                        embedded_links.append({"text": link_text, "url": href})

            # Extract Photo URL
            photo_url = None
            # Search for photo_wrap or photo elements
            photo_elements = latest_msg.find_all(class_=re.compile(r"tgme_widget_message_photo"))
            for pe in photo_elements:
                style = pe.get("style", "")
                bg_match = re.search(r"background-image:\s*url\(['\"]?(https://[^'\"]+)['\"]?\)", style)
                if bg_match:
                    photo_url = bg_match.group(1)
                    break
                    
            if not photo_url:
                # Fallback: search any element with telescop.pe / cdn image in style
                for tag in latest_msg.find_all(True):
                    style = tag.get("style", "")
                    if "telesco.pe" in style or "cdn" in style:
                        bg_match = re.search(r"background-image:\s*url\(['\"]?(https://[^'\"]+)['\"]?\)", style)
                        if bg_match:
                            photo_url = bg_match.group(1)
                            break
                    
            # Extract Video URL
            video_url = None
            video_thumb = latest_msg.find("i", class_=re.compile(r"tgme_widget_message_video_thumb"))
            if video_thumb:
                style = video_thumb.get("style", "")
                bg_match = re.search(r"background-image:url\('([^']+)'\)", style)
                if bg_match:
                    photo_url = bg_match.group(1) # Send thumbnail photo if video video file link not direct
                    
            video_tag = latest_msg.find("video")
            if video_tag and video_tag.get("src"):
                video_url = video_tag.get("src")
                
            # Extract Timestamp
            time_tag = latest_msg.find("time", class_="time")
            msg_date = time_tag.get("datetime", "") if time_tag else ""
            
            return {
                "msg_id": msg_id,
                "text": raw_text,
                "photo_url": photo_url,
                "video_url": video_url,
                "date": msg_date,
                "channel_username": channel_name,
                "embedded_links": embedded_links,
                "post_url": f"https://t.me/{channel_name}/{msg_id}" if msg_id else f"https://t.me/s/{channel_name}"
            }
            
    except Exception as e:
        logger.error(f"Error scraping channel @{channel_name}: {e}")
        return None
