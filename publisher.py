import httpx
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("publisher")

def send_telegram_post(
    bot_token: str,
    target_channel: str,
    post: Dict[str, Any],
    cta_text: str = "🔥 Sponsor Özel Fırsatına Git",
    add_inline_button: bool = True
) -> Dict[str, Any]:
    """
    Publishes a transformed post to a target Telegram channel/group via Telegram Bot API.
    Supports text, photo, video, and inline CTA buttons.
    """
    if not bot_token:
        return {"success": False, "error": "Bot Token (Bot API Anahtarı) tanımlanmamış."}
        
    api_url = f"https://api.telegram.org/bot{bot_token}"
    
    text = post.get("transformed_text", "")
    photo_url = post.get("photo_url")
    video_url = post.get("video_url")
    affiliate_link = post.get("affiliate_link")
    
    # Inline Keyboard Button with Affiliate Link
    reply_markup = None
    button_text = post.get("cta_text", cta_text)
    if add_inline_button and affiliate_link:
        reply_markup = {
            "inline_keyboard": [
                [
                    {
                        "text": button_text,
                        "url": affiliate_link
                    }
                ]
            ]
        }
        
    headers = {"Content-Type": "application/json"}

    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            # 1. Send Photo if available
            if photo_url:
                try:
                    # Download image bytes locally for 100% reliable upload
                    img_resp = client.get(photo_url)
                    if img_resp.status_code == 200:
                        files = {"photo": ("photo.jpg", img_resp.content, "image/jpeg")}
                        data_payload = {
                            "chat_id": target_channel,
                            "caption": text if text else None,
                            "parse_mode": "Markdown" if text else None,
                            "reply_markup": json.dumps(reply_markup) if reply_markup else None
                        }
                        res = client.post(f"{api_url}/sendPhoto", data=data_payload, files=files)
                        data = res.json()
                        
                        # Fallback to plain text caption if markdown formatting fails
                        if not data.get("ok") and "can't parse entities" in data.get("description", "").lower():
                            data_payload["parse_mode"] = None
                            res = client.post(f"{api_url}/sendPhoto", data=data_payload, files=files)
                            data = res.json()
                            
                        if data.get("ok"):
                            return {"success": True, "message_id": data["result"]["message_id"]}
                except Exception as img_err:
                    logger.warning(f"Failed to download image bytes from {photo_url}: {img_err}")
                    
            # 2. Send Video if available and no photo
            elif video_url:
                payload = {
                    "chat_id": target_channel,
                    "video": video_url,
                    "caption": text,
                    "parse_mode": "Markdown",
                    "reply_markup": reply_markup
                }
                res = client.post(f"{api_url}/sendVideo", json=payload)
                data = res.json()
                if data.get("ok"):
                    return {"success": True, "message_id": data["result"]["message_id"]}

            # 3. Standard Text Message
            payload = {
                "chat_id": target_channel,
                "text": text,
                "parse_mode": "Markdown",
                "disable_web_page_preview": False,
                "reply_markup": reply_markup
            }
            res = client.post(f"{api_url}/sendMessage", json=payload)
            data = res.json()
            
            # Retry without parse_mode if entity markdown error occurs
            if not data.get("ok") and "can't parse entities" in data.get("description", "").lower():
                payload["parse_mode"] = None
                res = client.post(f"{api_url}/sendMessage", json=payload)
                data = res.json()

            if data.get("ok"):
                return {"success": True, "message_id": data["result"]["message_id"]}
            else:
                return {"success": False, "error": data.get("description", "Bilinmeyen API hatası")}

    except Exception as e:
        logger.error(f"Failed to publish to {target_channel}: {e}")
        return {"success": False, "error": str(e)}

def test_bot_connection(bot_token: str) -> Dict[str, Any]:
    """Tests if the provided bot token is valid."""
    if not bot_token:
        return {"success": False, "error": "Bot Token boş olamaz."}
    try:
        with httpx.Client(timeout=10.0) as client:
            res = client.get(f"https://api.telegram.org/bot{bot_token}/getMe")
            data = res.json()
            if data.get("ok"):
                bot_info = data["result"]
                return {
                    "success": True,
                    "bot_name": bot_info.get("first_name"),
                    "username": f"@{bot_info.get('username')}"
                }
            else:
                return {"success": False, "error": data.get("description", "Geçersiz Bot Token")}
    except Exception as e:
        return {"success": False, "error": str(e)}
