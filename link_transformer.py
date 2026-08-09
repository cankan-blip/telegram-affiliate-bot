import re
from typing import Dict, Any

def transform_post_content(
    post_data: Dict[str, Any],
    affiliate_link: str,
    sponsor_name: str,
    cta_text: str = "🔥 {SPONSOR} GİRİŞ İÇİN TIKLAYINIZ",
    replace_all_links: bool = True,
    add_cta_footer: bool = True,
    only_image_mode: bool = True
) -> Dict[str, Any]:
    """
    Transforms sponsor post content:
    - If only_image_mode is True, strips original text caption, sending only photo + inline CTA button.
    - Replaces links with affiliate link and formats dynamic sponsor CTA button text.
    """
    raw_text = post_data.get("text", "")
    has_photo = bool(post_data.get("photo_url"))
    
    # Format CTA text
    if "{SPONSOR}" in cta_text:
        display_cta = cta_text.replace("{SPONSOR}", sponsor_name.upper())
    elif cta_text == "🔥 Sponsor Özel Fırsatına Git" or not cta_text:
        display_cta = f"🔥 {sponsor_name.upper()} GİRİŞ İÇİN TIKLAYINIZ"
    else:
        display_cta = cta_text

    # Check if only image mode is active
    if only_image_mode and has_photo:
        transformed_text = ""
    else:
        transformed_text = raw_text
        if replace_all_links and raw_text:
            url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
            def url_replacer(match):
                url = match.group(0)
                if "t.me/" in url or "telegram.org" in url:
                    return url
                return affiliate_link
            transformed_text = re.sub(url_pattern, url_replacer, transformed_text)

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
        "post_url": post_data.get("post_url"),
        "only_image_mode": only_image_mode
    }
