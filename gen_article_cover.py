#!/usr/bin/env python3
"""Generate a clean cover for the ROI article."""

from PIL import Image, ImageDraw, ImageFont
import os

W = 900
H = 420

img = Image.new('RGB', (W, H), '#F8F7F4')
draw = ImageDraw.Draw(img)

GREEN = '#1D9E75'
DARK = '#1A1A1A'
GRAY = '#5F5E5A'
LIGHT_GRAY = '#B4B2A9'

# Left decorative line
draw.rectangle([40, 60, 42, 360], fill=GREEN)
draw.ellipse([38, 357, 44, 363], fill=GREEN)

try:
    font_title = ImageFont.truetype("msyhbd.ttc", 22)
    font_sub = ImageFont.truetype("msyh.ttc", 15)
    font_small = ImageFont.truetype("msyh.ttc", 12)
except:
    font_title = ImageFont.load_default()
    font_sub = ImageFont.load_default()
    font_small = ImageFont.load_default()

draw.text((68, 130), "你的AI ROI算法", fill=DARK, font=font_title)
draw.text((68, 162), "是错的", fill=GREEN, font=font_title)
draw.text((68, 200), "7层成本和4个阶段的真相", fill=GRAY, font=font_sub)
draw.text((68, 228), "算清AI投入产出，从这一篇开始", fill=GRAY, font=font_sub)

# Bottom
draw.text((68, 405), "海风 · 2026", fill=LIGHT_GRAY, font=font_small)

output_path = r"C:\Users\jt\WorkBuddy\Claw\_cover_roi_article.png"
img.save(output_path, 'PNG')
print(f"Cover saved: {output_path} ({os.path.getsize(output_path)} bytes)")
