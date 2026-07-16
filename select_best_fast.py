"""
品类内精选：快速版 — 去模糊 · 去重复 · 去低质
每品类选 120 张最佳训练图
使用文件大小 + 分辨率 + 快速清晰度作为质量指标
"""
import os, sys, time, json, hashlib
from collections import defaultdict
from PIL import Image
import numpy as np

TRAIN_DIR = r"E:/AI电商工作创建/LORA训练数据集/训练集"
OUTPUT_JSON = r"E:/AI电商工作创建/LORA训练数据集/13_selection_report.json"

TARGET_PER_CATEGORY = 120
MIN_WIDTH = 400
MIN_HEIGHT = 400

CATEGORIES = ["少女甜系", "纯欲性感", "知性简约", "新中式国风", "老娘客"]

def fast_sharpness(img):
    """快速边缘检测 — 用 Sobel 近似替代 Laplacian"""
    gray = np.array(img.convert('L'), dtype=np.float32)
    if gray.size == 0:
        return 0
    h, w = gray.shape
    # 用水平/垂直差分近似（比完整卷积快 10 倍）
    dx = np.diff(gray, axis=1)
    dy = np.diff(gray, axis=0)
    return float(((dx**2).mean() + (dy**2).mean()) / 2)

def dhash_bytes(img, hash_size=8):
    """dHash 返回 bytes 用于去重"""
    img = img.convert('L').resize((hash_size + 1, hash_size), Image.LANCZOS)
    pixels = np.array(img, dtype=int)
    diff = pixels[:, 1:] > pixels[:, :-1]
    return diff.tobytes()

def select_category(cat_dir, cat_name, target=TARGET_PER_CATEGORY):
    print(f"\n{'='*40}")
    print(f"品类: {cat_name}")
    print(f"{'='*40}")
    
    files = [f for f in os.listdir(cat_dir) 
             if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
    print(f"  总图数: {len(files)}")
    
    candidates = []
    hashes = set()
    dup_count = 0
    small_count = 0
    t0 = time.time()
    
    for i, fname in enumerate(files):
        fpath = os.path.join(cat_dir, fname)
        try:
            # 先看文件大小（快速过滤）
            fsize = os.path.getsize(fpath)
            if fsize < 10240:  # < 10KB 极低质量
                continue
            
            img = Image.open(fpath)
            w, h = img.size
            
            # 分辨率过滤
            if w < MIN_WIDTH or h < MIN_HEIGHT:
                small_count += 1
                continue
            
            # 快速清晰度（差分近似）
            sharpness = fast_sharpness(img)
            
            # 感知哈希去重
            ph = dhash_bytes(img)
            if ph in hashes:
                dup_count += 1
                continue
            hashes.add(ph)
            
            # 质量评分：清晰度 + 分辨率 + 文件大小（综合）
            mp = w * h / (1024 * 1024)
            score = sharpness * min(mp, 2.0) * min(fsize / 50000, 2.0)
            
            candidates.append({
                'file': fname,
                'path': fpath,
                'width': w,
                'height': h,
                'sharpness': round(sharpness, 1),
                'size_kb': round(fsize / 1024, 1),
                'score': round(score, 1),
            })
            
        except Exception as e:
            continue
        
        if (i + 1) % 5000 == 0:
            print(f"  扫描中: {i+1}/{len(files)} 张... (已去重{dup_count} 已过滤小图{small_count})")
    
    # 按质量评分排序，取前 target
    candidates.sort(key=lambda x: -x['score'])
    selected = candidates[:target]
    
    elapsed = time.time() - t0
    print(f"  耗时: {elapsed:.0f}s")
    print(f"  合格: {len(candidates)} 张 | 去重: {dup_count} 张 | 小图: {small_count} 张")
    print(f"  精选: {len(selected)} 张")
    
    return selected

all_results = {}

print("=" * 50)
print("品类内精选 — 快速版")
print("=" * 50)

for cat in CATEGORIES:
    cat_dir = os.path.join(TRAIN_DIR, cat)
    if not os.path.exists(cat_dir):
        print(f"\n⚠️ {cat} 目录不存在")
        continue
    
    selected = select_category(cat_dir, cat)
    
    # 复制到精选目录
    sel_dir = os.path.join(TRAIN_DIR, f"{cat}_精选")
    os.makedirs(sel_dir, exist_ok=True)
    
    import shutil
    copied = 0
    for r in selected:
        dst = os.path.join(sel_dir, r['file'])
        if not os.path.exists(dst):
            try:
                shutil.copy2(r['path'], dst)
                copied += 1
            except:
                pass
    
    all_results[cat] = {
        'total': len([f for f in os.listdir(cat_dir) if f.lower().endswith(('.jpg','.jpeg','.png','.webp'))]),
        'selected': len(selected),
        'copied': copied,
        'quality_range': {
            'min_score': min(r['score'] for r in selected) if selected else 0,
            'max_score': max(r['score'] for r in selected) if selected else 0,
        }
    }
    
    print(f"  ✅ 已复制: {copied} 张 -> {cat}_精选/\n")

# 汇总
print("=" * 50)
print("精选汇总")
print("=" * 50)
total_selected = 0
for cat in CATEGORIES:
    r = all_results.get(cat, {})
    print(f"{cat:8s} {r.get('total',0):>6,} → {r.get('selected',0):>3,} 张精选 (复制{r.get('copied',0):>3,})")
    total_selected += r.get('selected', 0)
print(f"\n总计精选: {total_selected} 张")

report = {
    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
    'params': {'target_per_category': TARGET_PER_CATEGORY, 'min_width': MIN_WIDTH, 'min_height': MIN_HEIGHT},
    'categories': all_results,
    'total_selected': total_selected,
}
with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print(f"\n报告: {OUTPUT_JSON}")
