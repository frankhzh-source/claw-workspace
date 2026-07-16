#!/usr/bin/env python3
"""Push the ROI article to WeChat draft."""

import json
import os
import re
import urllib.request

WECHAT_APPID = "wx2003a12d1b3d867f"
WECHAT_SECRET = "32dbd01b12d99e18ed4a997e9145f922"
MD_PATH = r"C:\Users\jt\WorkBuddy\Claw\公众号_AI的ROI算法是错的.md"
COVER_PATH = r"C:\Users\jt\WorkBuddy\Claw\_cover_roi_article.png"

def get_token():
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={WECHAT_APPID}&secret={WECHAT_SECRET}"
    resp = json.loads(urllib.request.urlopen(url).read())
    return resp.get("access_token")

def upload_cover(token, path):
    boundary = '----Boundary'
    with open(path, 'rb') as f:
        data = f.read()
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="media"; filename="cover.png"\r\nContent-Type: image/png\r\n\r\n').encode() + data + f'\r\n--{boundary}--\r\n'.encode()
    url = f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={token}&type=image"
    req = urllib.request.Request(url, data=body)
    req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
    resp = json.loads(urllib.request.urlopen(req).read())
    return resp.get("media_id")

def md_to_html(md):
    lines = md.split("\n")
    html = ['<section style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; line-height: 1.8; color: #333; padding: 10px 0;">']
    for line in lines:
        s = line.strip()
        if not s:
            html.append('<p style="margin: 8px 0;">&nbsp;</p>')
            continue
        if s == "---":
            html.append('<hr style="border: none; border-top: 1px solid #e0e0e0; margin: 25px 0;" />')
            continue
        if s.startswith("# ") and not s.startswith("## "):
            html.append(f'<h1 style="font-size: 22px; font-weight: 700; margin: 20px 0 12px; line-height: 1.4;">{esc(s[2:])}</h1>')
            continue
        if s.startswith("> "):
            t = esc(s[2:])
            t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
            html.append(f'<blockquote style="background: #f6f8fa; border-left: 4px solid #07c160; padding: 12px 16px; margin: 16px 0; color: #555; font-size: 14px; border-radius: 0 4px 4px 0;">{t}</blockquote>')
            continue
        if s.startswith("**") and s.endswith("**"):
            t = esc(s[2:-2])
            html.append(f'<p style="font-weight: 600; margin: 14px 0; font-size: 16px; color: #222;">{t}</p>')
            continue
        t = esc(s)
        t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
        html.append(f'<p style="margin: 10px 0; font-size: 15px; letter-spacing: 0.3px;">{t}</p>')
    html.append("</section>")
    return "\n".join(html)

def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def create_draft(token, title, digest, content, thumb_id):
    url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}"
    payload = json.dumps({
        "articles": [{
            "title": title, "author": "海风老师",
            "digest": digest, "content": content,
            "thumb_media_id": thumb_id,
            "need_open_comment": 1, "only_fans_can_comment": 0
        }]
    }, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    resp = json.loads(urllib.request.urlopen(req).read())
    return resp

# Read article
with open(MD_PATH, "r", encoding="utf-8") as f:
    md = f.read()

title = "你的AI ROI算法是错的——7层成本和4个阶段的真相"
digest = "大多数企业算AI成本只看Token调用费，但这只占了15-25%。隐藏在冰山下的另外5层，才是决定真实ROI的关键。"

# Get token
token = get_token()
print(f"Token: {'OK' if token else 'FAIL'}")
if not token:
    exit(1)

# Upload cover
thumb_id = upload_cover(token, COVER_PATH)
print(f"Cover media_id: {thumb_id}")

# Create draft
html_content = md_to_html(md)
resp = create_draft(token, title, digest, html_content, thumb_id)
print(f"Draft response: {resp}")
