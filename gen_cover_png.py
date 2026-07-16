#!/usr/bin/env python3
"""Generate KIWI diary cover PNG — parameterized: chapter, title lines, subtitle."""
# Usage: python gen_cover_png.py --chapter 173 --title1 "城市选择这道题" --title2 "AI时代的答案变了" --sub "FDE的正确定义不是Full-stack，是Forward Deployed Engineer"
# NOTE: chapter parameter should be the NUMBER ONLY (e.g. "177"). The script auto-wraps with "第" and "章".
# Output: C:\Users\jt\WorkBuddy\Claw\_cover_latest.png

from PIL import Image, ImageDraw, ImageFont
import os, sys, argparse

W, H = 900, 420

def make_cover(chapter, title1, title2="", subtitle="", output=None):
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

    # KIWI badge
    bx, by, bw, bh = 68, 60, 90, 26
    draw.rounded_rectangle([bx, by, bx+bw, by+bh], radius=13, fill=LIGHT_GREEN_BG)
    try:
        fb = ImageFont.truetype("msyh.ttc", 12)
    except:
        fb = ImageFont.load_default()
    draw.text((bx + bw//2, by + bh//2 - 2), "KIWI日记", fill='#085041', font=fb, anchor='mm')

    # Chapter number
    try:
        fc = ImageFont.truetype("msyhbd.ttc", 72)
    except:
        fc = ImageFont.load_default()
    draw.text((68, 100), f"第 {chapter} 章", fill=GREEN, font=fc)

    # Separator
    draw.line([68, 190, 350, 190], fill=LINE_COLOR, width=1)

    # Title lines
    try:
        ft1 = ImageFont.truetype("msyhbd.ttc", 22)
        ft2 = ImageFont.truetype("msyh.ttc", 16)
        fs = ImageFont.truetype("msyh.ttc", 12)
    except:
        ft1 = ft2 = fs = ImageFont.load_default()

    y = 210
    draw.text((68, y), title1, fill=DARK, font=ft1)
    y += 30
    if title2:
        draw.text((68, y), title2, fill=DARK, font=ft1)
        y += 30
    if subtitle:
        draw.text((68, y), subtitle, fill=GRAY, font=ft2)

    # Bottom
    draw.text((68, 405), "海风 · 2026", fill=LIGHT_GRAY, font=fs)
    draw.line([520, 395, 640, 395], fill=LINE_COLOR, width=1)
    draw.text((640, 410), "来自2031年的善意", fill=LIGHT_GRAY, font=fs, anchor='rd')

    out_path = output or r"C:\Users\jt\WorkBuddy\Claw\_cover_latest.png"
    img.save(out_path, 'PNG')
    print(f"Cover saved: {out_path} ({os.path.getsize(out_path)} bytes)")
    return out_path

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument('--chapter', default="173")
    p.add_argument('--title1', default="城市选择这道题")
    p.add_argument('--title2', default="AI时代的答案变了")
    p.add_argument('--sub', default="FDE的正确定义不是Full-stack，是Forward Deployed Engineer")
    p.add_argument('--output', default=None)
    args = p.parse_args()
    make_cover(args.chapter, args.title1, args.title2, args.sub, args.output)
