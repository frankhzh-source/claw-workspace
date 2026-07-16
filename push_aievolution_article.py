#!/usr/bin/env python3
"""Push AI进化论 article to WeChat draft with correct author and cover."""

import json
import os
import re
import urllib.request
import sys

WECHAT_APPID = "wx2003a12d1b3d867f"
WECHAT_SECRET = "32dbd01b12d99e18ed4a997e9145f922"


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
    in_table = False

    for line in lines:
        s = line.strip()
        if not s:
            html.append('<p style="margin: 8px 0;">&nbsp;</p>')
            continue
        if s == "---":
            if in_table:
                in_table = False
                html.append("</tbody></table>")
            html.append('<hr style="border: none; border-top: 1px solid #e0e0e0; margin: 25px 0;" />')
            continue
        if s.startswith("# ") and not s.startswith("## "):
            html.append(f'<h1 style="font-size: 22px; font-weight: 700; margin: 20px 0 12px; line-height: 1.4;">{esc(s[2:])}</h1>')
            continue
        if s.startswith("## "):
            html.append(f'<h2 style="font-size: 18px; font-weight: 600; margin: 18px 0 10px; color: #222;">{esc(s[3:])}</h2>')
            continue
        if s.startswith("> "):
            t = esc(s[2:])
            t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', t)
            html.append(f'<blockquote style="background: #f6f8fa; border-left: 4px solid #07c160; padding: 12px 16px; margin: 16px 0; color: #555; font-size: 15px; border-radius: 0 4px 4px 0;">{t}</blockquote>')
            continue
        if s.startswith("|") and "|" in s:
            cells = [c.strip() for c in s.split("|")[1:-1]]
            if not in_table:
                in_table = True
                html.append('<table style="width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 13px;">')
            if re.match(r"^\|[\s\-:]+\|", s):
                continue
            html.append('<tr style="border-bottom: 1px solid #eee;">')
            for cell in cells:
                cell = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', esc(cell))
                html.append(f'<td style="padding: 8px 10px; border-bottom: 1px solid #eee; vertical-align: top;">{cell}</td>')
            html.append("</tr>")
            continue
        if in_table:
            in_table = False
            html.append("</tbody></table>")
        if s.startswith("- ") or s.startswith("* "):
            t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', esc(s[2:]))
            html.append(f'<p style="margin: 4px 0; padding-left: 16px; font-size: 15px;">• {t}</p>')
            continue
        if s.startswith("**") and "**" in s[2:]:
            t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', esc(s))
            html.append(f'<p style="font-weight: 600; margin: 12px 0; font-size: 16px; color: #222;">{t}</p>')
            continue
        t = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', esc(s))
        html.append(f'<p style="margin: 10px 0; font-size: 15px; letter-spacing: 0.3px;">{t}</p>')

    if in_table:
        html.append("</tbody></table>")
    html.append("</section>")
    return "\n".join(html)


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def create_draft(token, title, digest, content, thumb_id):
    url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}"
    title_bytes = title.encode('utf-8')
    if len(title_bytes) > 64:
        title = title[:20] + "…"
    payload = json.dumps({
        "articles": [{
            "title": title,
            "author": "海风老师",
            "digest": digest,
            "content": content,
            "thumb_media_id": thumb_id,
            "need_open_comment": 1,
            "only_fans_can_comment": 0
        }]
    }, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    resp = json.loads(urllib.request.urlopen(req).read())
    return resp


if __name__ == "__main__":
    md_path = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\jt\WorkBuddy\Claw\公众号_被看见的进化史.md"
    cover_path = sys.argv[2] if len(sys.argv) > 2 else r"C:\Users\jt\WorkBuddy\Claw\_cover_aievolution.png"
    title = sys.argv[3] if len(sys.argv) > 3 else "被看见的进化史：从搜索引擎到AI时代，普通人如何抓住GEO窗口"
    digest = sys.argv[4] if len(sys.argv) > 4 else "2026年的被看见已经变成两件事：你要被人类信任，还要被AI引用。三个时代的规则变化，以及普通人可以立刻执行的五个方向。"

    with open(md_path, "r", encoding="utf-8") as f:
        md = f.read()

    token = get_token()
    print(f"Token: {'OK' if token else 'FAIL'}")
    if not token:
        exit(1)

    thumb_id = upload_cover(token, cover_path)
    print(f"Cover media_id: {thumb_id}")
    if not thumb_id:
        exit(1)

    html_content = md_to_html(md)
    resp = create_draft(token, title, digest, html_content, thumb_id)
    print(f"Draft response: {resp}")
