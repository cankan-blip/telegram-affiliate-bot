import re
from typing import Dict, Any

def transform_post_content(
    post_data: Dict[str, Any],
    affiliate_link: str,
    sponsor_name: str,
    cta_text: str = "🔥 Sponsor Özel Fırsatına Git",
    replace_all_links: bool = True,
    add_cta_footer: bool = True
) -> Dict[str, Any]:
    """
    Transforms sponsor post text by substituting existing URLs with the user's affiliate link
    and adding an explicit CTA footer/link.
    """
    raw_text = post_data.get("text", "")
    
    # 1. URL Replacement in text if configured
    transformed_text = raw_text
    if replace_all_links and raw_text:
        # Regex to find http/https URLs
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        
        # Replace non-Telegram internal links with affiliate link
        def url_replacer(match):
            url = match.group(0)
            if "t.me/" in url or "telegram.org" in url:
                return url # Keep internal telegram links intact or replace as desired
            return affiliate_link

        transformed_text = re.sub(url_pattern, url_replacer, transformed_text)

    # Dynamic CTA text formatting
    if cta_text == "🔥 Sponsor Özel Fırsatına Git" or not cta_text:
        display_cta = f"🔥 {sponsor_name.upper()} GİRİŞ İÇİN TIKLAYINIZ"
    else:
        display_cta = cta_text

    # 2. Append CTA Footer
    if add_cta_footer and affiliate_link:
        footer = f"\n\n👉 [{display_cta}]({affiliate_link})"
        transformed_text = transformed_text + footer

    return {
        "original_text": raw_text,
        "transformed_text": transformed_text,
        "affiliate_link": affiliate_link,
        "sponsor_name": sponsor_name,
        "cta_text": display_cta,
        "photo_url": post_data.get("photo_url"),
        "video_url": post_data.get("video_url"),
        "msg_id": post_data.get("msg_id"),
        "post_url": post_data.get("post_url")
    }
