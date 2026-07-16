#!/usr/bin/env python3
"""Generate cover for AI进化论 (deep-thinking AI) articles."""

from PIL import Image, ImageDraw, ImageFont
import os
import sys

W, H = 900, 420


def make_cover(title1, title2, subtitle1, subtitle2, badge, output):
    img = Image.new('RGB', (W, H), '#F8F7F4')
    draw = ImageDraw.Draw(img)

    GREEN = '#1D9E75'
    DARK = '#1A1A1A'
    GRAY = '#5F5E5A'
    LIGHT_GRAY = '#B4B2A9'
    LIGHT_GREEN_BG = '#E1F5EE'
    LINE_COLOR = '#D3D1C7'

    # Left decorative line
    draw.rectangle([40, 60, 42, 360], fill=GREEN)
    draw.ellipse([38, 357, 44, 363], fill=GREEN)

    # Badge (AI策略 / AI进化论 / AI头条)
    bx, by, bw, bh = 68, 60, 90, 26
    draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=13, fill=LIGHT_GREEN_BG)
    try:
        fb = ImageFont.truetype("msyh.ttc", 12)
    except:
        fb = ImageFont.load_default()
    draw.text((bx + bw // 2, by + bh // 2 - 2), badge, fill='#085041', font=fb, anchor='mm')

    # Title
    try:
        ft1 = ImageFont.truetype("msyhbd.ttc", 22)
        ft2 = ImageFont.truetype("msyh.ttc", 16)
        fs = ImageFont.truetype("msyh.ttc", 12)
    except:
        ft1 = ft2 = fs = ImageFont.load_default()

    y = 120
    draw.text((68, y), title1, fill=DARK, font=ft1)
    y += 34
    if title2:
        draw.text((68, y), title2, fill=GREEN, font=ft1)
        y += 34

    # Separator
    draw.line([68, y + 10, 350, y + 10], fill=LINE_COLOR, width=1)
    y += 24

    # Subtitles
    if subtitle1:
        draw.text((68, y), subtitle1, fill=GRAY, font=ft2)
        y += 28
    if subtitle2:
        draw.text((68, y), subtitle2, fill=GRAY, font=ft2)

    # Bottom
    draw.text((68, 405), "海风 · 2026", fill=LIGHT_GRAY, font=fs)
    draw.line([520, 395, 700, 395], fill=LINE_COLOR, width=1)
    draw.text((700, 410), "AI进化论", fill=LIGHT_GRAY, font=fs, anchor='rd')

    img.save(output, 'PNG')
    print(f"Cover saved: {output} ({os.path.getsize(output)} bytes)")
    return output


if __name__ == "__main__":
    title1 = sys.argv[1] if len(sys.argv) > 1 else "被看见的进化史"
    title2 = sys.argv[2] if len(sys.argv) > 2 else "从搜索引擎到AI时代"
    subtitle1 = sys.argv[3] if len(sys.argv) > 3 else "普通人如何抓住GEO窗口"
    subtitle2 = sys.argv[4] if len(sys.argv) > 4 else "搜索引擎 → 算法推荐 → AI问答"
    badge = sys.argv[5] if len(sys.argv) > 5 else "AI进化论"
    output = sys.argv[6] if len(sys.argv) > 6 else r"C:\Users\jt\WorkBuddy\Claw\_cover_aievolution.png"
    make_cover(title1, title2, subtitle1, subtitle2, badge, output)
