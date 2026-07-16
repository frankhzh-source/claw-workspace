"""KIWI日记封面生成器 — 直接输出PNG"""
from PIL import Image, ImageDraw, ImageFont
import os, datetime

FONT_DIR = "C:/Windows/Fonts"

def generate_cover(day, title, subtitle="", output_path=None):
    w, h = 680, 420
    img = Image.new("RGB", (w, h), (248, 247, 244))
    draw = ImageDraw.Draw(img)

    # 字体
    try:
        font_bold = ImageFont.truetype(os.path.join(FONT_DIR, "msyhbd.ttc"), 48)
        font_big = ImageFont.truetype(os.path.join(FONT_DIR, "msyhbd.ttc"), 96)
        font_title = ImageFont.truetype(os.path.join(FONT_DIR, "msyhbd.ttc"), 18)
        font_sub = ImageFont.truetype(os.path.join(FONT_DIR, "msyhl.ttc"), 14)
        font_small = ImageFont.truetype(os.path.join(FONT_DIR, "msyhl.ttc"), 12)
        font_tiny = ImageFont.truetype(os.path.join(FONT_DIR, "msyhl.ttc"), 11)
        font_xs = ImageFont.truetype(os.path.join(FONT_DIR, "msyhl.ttc"), 10)
    except:
        font_bold = font_big = font_title = font_sub = font_small = font_tiny = font_xs = ImageFont.load_default()

    # 左侧装饰线
    for y in range(60, 360):
        draw.rectangle([40, y, 42, y+1], fill=(29, 158, 117))
    draw.ellipse([38, 357, 44, 363], fill=(29, 158, 117, 77))

    # KIWI 徽标
    draw.rounded_rectangle([68, 60, 158, 86], radius=13, fill=(225, 245, 238))
    draw.text((113, 66), "KIWI日记", fill=(8, 80, 65), font=font_small)

    # Day
    draw.text((68, 130), "Day", fill=(26, 26, 26), font=font_bold)
    # Day number
    draw.text((68, 190), str(day), fill=(29, 158, 117), font=font_big)

    # 分隔线
    draw.line([68, 295, 250, 295], fill=(211, 209, 199), width=1)

    # 标题
    y_title = 330
    draw.text((68, y_title - 10), title, fill=(26, 26, 26), font=font_title)
    if subtitle:
        draw.text((68, y_title + 18), subtitle, fill=(95, 94, 90), font=font_sub)

    # 底部
    draw.text((68, 395), f"海风 · {datetime.date.today().year}", fill=(180, 178, 169), font=font_tiny)

    # 右下
    draw.line([520, 395, 640, 395], fill=(211, 209, 199), width=1)
    draw.text((640, 400), "来自2031年的善意", fill=(180, 178, 169), font=font_xs)

    if output_path:
        img.save(output_path, "PNG")
        print(f"Saved: {output_path} ({os.path.getsize(output_path)} bytes)")
    return img

if __name__ == "__main__":
    generate_cover(170, "AI裁掉7.3万人的文章只有0阅读", "我发现了比写作更残酷的事", "C:/Users/jt/AppData/Local/Temp/KIWI_Day170_cover.png")
