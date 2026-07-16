"""Caption 抽检 —— 每个品类随机抽 5 张，图片+描述对照"""
import json, os, random, base64
from pathlib import Path

CAPTION_FILE = r"E:/AI电商工作创建/LORA训练数据集/14_captions_glm.json"
TRAIN_DIR = r"E:/AI电商工作创建/LORA训练数据集/训练集"
OUTPUT_HTML = r"E:/AI电商工作创建/LORA训练数据集/16_spot_check.html"

with open(CAPTION_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

results = data["results"]
SAMPLE_PER_CAT = 5

html_parts = []
html_parts.append("""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>Caption 抽检报告</title>
<style>
  body { font-family: -apple-system, sans-serif; max-width: 960px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
  h1 { font-size: 22px; color: #1a1a1a; margin-bottom: 8px; }
  .subtitle { color: #666; font-size: 14px; margin-bottom: 24px; }
  .cat-section { background: white; border-radius: 10px; padding: 16px; margin-bottom: 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
  .cat-title { font-size: 18px; font-weight: 600; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 2px solid #eee; }
  .item { display: flex; gap: 16px; padding: 12px 0; border-bottom: 1px solid #f0f0f0; }
  .item:last-child { border-bottom: none; }
  .item img { width: 200px; height: 200px; object-fit: cover; border-radius: 6px; flex-shrink: 0; }
  .caption-area { flex: 1; }
  .caption-label { font-size: 12px; color: #999; margin-bottom: 4px; }
  .caption-text { font-size: 14px; line-height: 1.6; color: #333; background: #f8f8f8; padding: 8px 12px; border-radius: 6px; }
  .status-pass { display: inline-block; background: #e8f5e9; color: #2e7d32; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 500; }
  .status-check { display: inline-block; background: #fff3e0; color: #e65100; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 500; }
</style>
</head>
<body>
<h1>📋 Caption 抽检报告</h1>
<p class="subtitle">每个品类随机抽取 5 张，对照图片内容和描述，判断是否准确</p>
""")

CAT_COLORS = {
    "少女甜系": "#F9A8D4",
    "纯欲性感": "#F472B6",
    "知性简约": "#818CF8",
    "新中式国风": "#F59E0B",
    "老娘客": "#A78BFA",
}

CAT_DIR_MAP = {
    "少女甜系": "少女甜系_精选",
    "纯欲性感": "纯欲性感_精选",
    "知性简约": "知性简约_精选",
    "新中式国风": "新中式国风_精选",
    "老娘客": "老娘客_精选",
}

for cat, caps in results.items():
    items = list(caps.items())
    random.seed(42)
    random.shuffle(items)
    samples = items[:SAMPLE_PER_CAT]
    
    color = CAT_COLORS.get(cat, "#666")
    dir_name = CAT_DIR_MAP.get(cat, cat)
    src_dir = os.path.join(TRAIN_DIR, dir_name)
    
    html_parts.append(f'<div class="cat-section">')
    html_parts.append(f'<div class="cat-title" style="border-bottom-color: {color}; color: {color};">{cat} <span style="font-size:13px;color:#999;font-weight:400;">（共 {len(caps)} 张，抽检 {len(samples)} 张）</span></div>')
    
    for fname, caption in samples:
        img_path = os.path.join(src_dir, fname)
        if os.path.exists(img_path):
            with open(img_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            ext = Path(fname).suffix.lower()
            mime = "image/png" if ext == ".png" else "image/jpeg"
            img_src = f"data:{mime};base64,{b64}"
        else:
            img_src = ""
        
        word_count = len(caption)
        status = '<span class="status-pass">✅ 合格</span>' if word_count > 30 else '<span class="status-check">⚠️ 偏短</span>'
        
        html_parts.append(f'''
    <div class="item">
        <img src="{img_src}" alt="{fname}" onerror="this.alt='图片未找到'">
        <div class="caption-area">
            <div class="caption-label">{fname} · {word_count}字 {status}</div>
            <div class="caption-text">{caption}</div>
        </div>
    </div>''')
    
    html_parts.append('</div>')

# 品类统计
html_parts.append("""
<div class="cat-section" style="background:#f8f9fa;">
  <div class="cat-title" style="border-bottom-color:#888;color:#333;">📊 整体统计</div>
  <table style="width:100%;border-collapse:collapse;font-size:14px;">
    <tr style="border-bottom:1px solid #ddd;">
      <th style="text-align:left;padding:8px;">品类</th>
      <th style="text-align:right;padding:8px;">总数</th>
      <th style="text-align:right;padding:8px;">平均字数</th>
      <th style="text-align:right;padding:8px;">最短</th>
      <th style="text-align:right;padding:8px;">最长</th>
    </tr>""")

for cat, caps in results.items():
    lens = [len(c) for c in caps.values()]
    avg = sum(lens) / len(lens)
    html_parts.append(f"""
    <tr>
      <td style="padding:8px;color:{CAT_COLORS.get(cat,'#333')};font-weight:500;">{cat}</td>
      <td style="text-align:right;padding:8px;">{len(caps)}</td>
      <td style="text-align:right;padding:8px;">{avg:.0f}</td>
      <td style="text-align:right;padding:8px;">{min(lens)}</td>
      <td style="text-align:right;padding:8px;">{max(lens)}</td>
    </tr>""")

all_lens = [len(c) for caps in results.values() for c in caps.values()]
html_parts.append(f"""
    <tr style="border-top:2px solid #333;font-weight:600;">
      <td style="padding:8px;">合计</td>
      <td style="text-align:right;padding:8px;">{len(all_lens)}</td>
      <td style="text-align:right;padding:8px;">{sum(all_lens)/len(all_lens):.0f}</td>
      <td style="text-align:right;padding:8px;">{min(all_lens)}</td>
      <td style="text-align:right;padding:8px;">{max(all_lens)}</td>
    </tr>""")

html_parts.append("</table></div></body></html>")

with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
    f.write("\n".join(html_parts))

print(f"✅ 抽检报告已生成: {OUTPUT_HTML}")
print(f"   页面包含 {sum(len(list(v.items())) for v in results.values())} 张全样 + 每品类抽检 {SAMPLE_PER_CAT} 张对照")
