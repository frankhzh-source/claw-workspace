#!/usr/bin/env python3
"""Convert markdown article to WeChat draft and push via API."""

import json
import os
import re
import urllib.request
import urllib.parse
import urllib.error

WECHAT_APPID = os.environ.get("WECHAT_APPID", "wx2003a12d1b3d867f")
WECHAT_SECRET = os.environ.get("WECHAT_SECRET", "32dbd01b12d99e18ed4a997e9145f922")

def get_token():
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={WECHAT_APPID}&secret={WECHAT_SECRET}"
    resp = json.loads(urllib.request.urlopen(url).read())
    if "access_token" in resp:
        print(f"TOKEN_OK: {resp['access_token'][:20]}...")
        return resp["access_token"]
    print(f"TOKEN_ERROR: {resp}")
    return None

def md_to_html(md_text):
    """Convert markdown to HTML with inline styles for WeChat."""
    lines = md_text.split("\n")
    html_parts = ['<section style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; line-height: 1.7; color: #333; padding: 10px 0; font-size: 16px; max-width: 100%;">']

    in_table = False
    in_list = False

    for line in lines:
        stripped = line.strip()

        # Skip separator lines
        if stripped == "---":
            if in_table:
                in_table = False
                html_parts.append("</tbody></table>")
            html_parts.append('<hr style="border: none; border-top: 1px solid #e0e0e0; margin: 25px 0;" />')
            continue

        # Title
        if stripped.startswith("# ") and not stripped.startswith("##"):
            title_text = stripped[2:]
            html_parts.append(f'<h1 style="font-size: 19px; font-weight: 700; margin: 18px 0 10px; letter-spacing: 0.3px; line-height: 1.4;">{escape_html(title_text)}</h1>')
            continue

        # Subtitle
        if stripped.startswith("## "):
            sub_text = stripped[3:]
            html_parts.append(f'<h2 style="font-size: 16px; font-weight: 600; margin: 14px 0 8px; color: #222;">{escape_html(sub_text)}</h2>')
            continue

        # Blockquote (single line)
        if stripped.startswith("> "):
            quote_text = stripped[2:]
            # Handle bold inside blockquote
            quote_text = process_bold(quote_text)
            html_parts.append(f'<blockquote style="background: #f6f8fa; border-left: 4px solid #07c160; padding: 12px 16px; margin: 16px 0; color: #555; font-size: 15px; border-radius: 0 4px 4px 0;">{quote_text}</blockquote>')
            continue

        if stripped.startswith(">"):
            quote_text = stripped[1:]
            quote_text = process_bold(quote_text)
            html_parts.append(f'<blockquote style="background: #f6f8fa; border-left: 4px solid #07c160; padding: 12px 16px; margin: 16px 0; color: #555; font-size: 15px; border-radius: 0 4px 4px 0;">{quote_text}</blockquote>')
            continue

        # Table
        if "|" in stripped and stripped.startswith("|"):
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            if not in_table:
                in_table = True
                html_parts.append('<table style="width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 13px;">')
                # We'll handle header vs body via the row content
            # Check if this is separator row (all ---)
            if re.match(r"^\|[\s\-:]+\|", stripped):
                continue
            # Check if first data row after header (text cells)
            row_type = "td"
            tag = "td"
            html_parts.append(f'<tr style="border-bottom: 1px solid #eee;">')
            for cell in cells:
                cell = process_bold(cell)
                html_parts.append(f'<{tag} style="padding: 8px 10px; border-bottom: 1px solid #eee; vertical-align: top;">{cell}</{tag}>')
            html_parts.append("</tr>")
            continue

        if in_table:
            in_table = False
            html_parts.append("</tbody></table>")

        # List items
        if stripped.startswith("- ") or stripped.startswith("* "):
            item_text = stripped[2:]
            item_text = process_bold(item_text)
            html_parts.append(f'<p style="margin: 4px 0; padding-left: 16px; font-size: 15px;">• {item_text}</p>')
            continue

        if stripped.startswith("**") and "**" in stripped[2:]:
            # Bold line
            bold_text = process_bold(stripped)
            html_parts.append(f'<p style="font-weight: 600; margin: 12px 0; font-size: 16px; color: #222;">{bold_text}</p>')
            continue

        # Empty line
        if not stripped:
            html_parts.append('<p style="margin: 8px 0;">&nbsp;</p>')
            continue

        # Normal paragraph
        para = process_bold(stripped)
        html_parts.append(f'<p style="margin: 8px 0; font-size: 15px; letter-spacing: 0.2px; line-height: 1.7;">{para}</p>')

    html_parts.append("</section>")
    return "\n".join(html_parts)


def escape_html(text):
    """Escape HTML special chars."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

def process_bold(text):
    """Convert **bold** to <strong>."""
    # First escape HTML, then apply bold
    text = escape_html(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    return text

def create_draft(token, title, digest, content_html, cover_id=None):
    """Create a WeChat draft."""
    url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}"

    # Handle title byte limit - max 64 bytes
    title_bytes = title.encode('utf-8')
    if len(title_bytes) > 64:
        # Truncate safely at byte boundary
        truncated = title_bytes[:61]
        # Find last valid UTF-8 character boundary
        decoded = truncated.decode('utf-8', errors='ignore')
        title = decoded + "…"
        print(f"Title truncated to: {title}")

    # Default cover: KIWI diary 173章
    default_cover = "CPphwVaTdyJY6D79IuCazV2yEaAsj9XTpU5XFb1CnSU4jzkUbLm3hv3GDXoMxEQ-"
    payload = {
        "articles": [{
            "title": title,
            "author": "Kiwi",
            "digest": digest,
            "content": content_html,
            "thumb_media_id": cover_id or default_cover,
            "need_open_comment": 1,
            "only_fans_can_comment": 0
        }]
    }

    data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    resp = json.loads(urllib.request.urlopen(req).read())

    if "media_id" in resp:
        print(f"✅ 草稿创建成功！media_id: {resp['media_id']}")
        return resp["media_id"]
    else:
        print(f"❌ 创建失败: {resp}")
        return None


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python push_wechat_draft.py <md_path> [cover_path]")
        sys.exit(1)

    md_path = sys.argv[1]
    cover_path = sys.argv[2] if len(sys.argv) > 2 else r"C:\Users\jt\WorkBuddy\Claw\_cover_latest.png"

    with open(md_path, "r", encoding="utf-8") as f:
        md_content = f.read()

    # Parse title from first # heading line
    title = ""
    digest = ""
    body_start = 0
    for i, line in enumerate(md_content.split("\n")):
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.startswith("## "):
            title = stripped[2:]
            body_start = i + 1
            continue
        # Try to use second paragraph as digest (skip empty lines after title)
        if title and not digest and stripped and not stripped.startswith("#"):
            digest = stripped[:120]
            if len(digest) == 120:
                digest += "…"
            break

    if not title:
        print("❌ Could not find title (# heading) in markdown file")
        sys.exit(1)

    print(f"Title: {title}")
    print(f"Digest: {digest[:60]}...")

    # Convert to HTML
    html_content = md_to_html(md_content)

    # Get token
    token = get_token()
    if not token:
        sys.exit(1)

    # Upload cover image to get media_id
    cover_id = None
    try:
        boundary = '----Boundary7MA4YW'
        with open(cover_path, 'rb') as f:
            img_data = f.read()
        body_bytes = (
            f'--{boundary}\r\nContent-Disposition: form-data; name="media"; filename="cover.png"\r\nContent-Type: image/png\r\n\r\n'
        ).encode() + img_data + f'\r\n--{boundary}--\r\n'.encode()
        upload_url = f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={token}&type=image"
        req = urllib.request.Request(upload_url, data=body_bytes)
        req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
        upload_resp = json.loads(urllib.request.urlopen(req).read())
        if "media_id" in upload_resp:
            cover_id = upload_resp["media_id"]
            print(f"Cover uploaded: {cover_id}")
        else:
            print(f"Cover upload failed: {upload_resp}, using default")
    except Exception as e:
        print(f"Cover upload error: {e}, using default")

    # Create draft with parsed title + uploaded cover
    create_draft(token, title, digest, html_content, cover_id)
