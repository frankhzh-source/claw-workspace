"""
品类内精选：去模糊 · 去重复 · 去低质
每品类选 50-200 张最佳训练图
"""
import os, sys, time, json, hashlib
from collections import defaultdict
from PIL import Image, ImageFilter
import numpy as np

TRAIN_DIR = r"E:/AI电商工作创建/LORA训练数据集/训练集"
OUTPUT_JSON = r"E:/AI电商工作创建/LORA训练数据集/13_selection_report.json"

TARGET_PER_CATEGORY = 120  # 每品类目标精选数量
MIN_WIDTH = 512
MIN_HEIGHT = 512
BLUR_THRESHOLD = 80      # Laplacian 方差阈值（低于此值视为模糊）
HASH_BITS = 8            # 感知哈希位数

CATEGORIES = ["少女甜系", "纯欲性感", "知性简约", "新中式国风", "老娘客"]

def compute_laplacian_variance(img):
    """计算拉普拉斯方差，衡量图片清晰度"""
    gray = img.convert('L')
    arr = np.array(gray, dtype=np.float32)
    lap = np.array([
        [-1, -1, -1],
        [-1,  8, -1],
        [-1, -1, -1]
    ], dtype=np.float32)
    from scipy.ndimage import convolve
    result = convolve(arr, lap)
    return float(result.var())

def dhash(img, hash_size=8):
    """计算差异感知哈希（dHash）"""
    img = img.convert('L').resize((hash_size + 1, hash_size), Image.LANCZOS)
    pixels = np.array(img, dtype=int)
    diff = pixels[:, 1:] > pixels[:, :-1]
    return hash(diff.tobytes())

def select_category(cat_dir, cat_name, target=TARGET_PER_CATEGORY):
    print(f"\n{'='*40}")
    print(f"品类: {cat_name}")
    print(f"{'='*40}")
    
    files = [f for f in os.listdir(cat_dir) 
             if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
    print(f"  总图数: {len(files)}")
    
    results = []
    hashes = defaultdict(list)
    t0 = time.time()
    
    for i, fname in enumerate(files):
        fpath = os.path.join(cat_dir, fname)
        try:
            img = Image.open(fpath)
            w, h = img.size
            
            # 分辨率过滤
            if w < MIN_WIDTH or h < MIN_HEIGHT:
                continue
            
            # 清晰度检测
            try:
                lap_var = compute_laplacian_variance(img)
            except:
                lap_var = BLUR_THRESHOLD + 1  # 检测失败则保留
            
            if lap_var < BLUR_THRESHOLD:
                continue
            
            # 感知哈希（去重）
            phash = dhash(img)
            
            # 质量评分：清晰度 + 分辨率
            resolution_score = min(w * h / (1024 * 1024), 2.0)  # 1MP+ 满分
            quality_score = lap_var * resolution_score
            
            results.append({
                'file': fname,
                'path': fpath,
                'width': w,
                'height': h,
                'laplacian': round(lap_var, 1),
                'score': round(quality_score, 1),
                'hash': phash,
            })
            hashes[phash].append(fname)
            
        except Exception as e:
            continue
        
        if (i + 1) % 2000 == 0:
            print(f"  扫描中: {i+1}/{len(files)} 张...")
    
    # 按质量评分排序
    results.sort(key=lambda x: -x['score'])
    
    # 去重：同一哈希只保留最佳的一张
    seen_hashes = set()
    deduped = []
    for r in results:
        if r['hash'] not in seen_hashes:
            seen_hashes.add(r['hash'])
            deduped.append(r)
    
    # 取前 target 张
    selected = deduped[:target]
    
    elapsed = time.time() - t0
    print(f"  扫描完成: {elapsed:.0f}s")
    print(f"  合格(>=512px+非模糊): {len(results)} 张")
    print(f"  去重后: {len(deduped)} 张")
    print(f"  精选: {len(selected)} 张")
    
    return selected, files, results, deduped

all_results = {}
summary = {}

print("=" * 50)
print("品类内精选 — 去模糊 · 去重复 · 去低质")
print("=" * 50)

for cat in CATEGORIES:
    cat_dir = os.path.join(TRAIN_DIR, cat)
    if not os.path.exists(cat_dir):
        print(f"\n⚠️ {cat} 目录不存在，跳过")
        continue
    
    selected, total, qualified, deduped = select_category(cat_dir, cat)
    
    # 复制选中图片到精选目录
    sel_dir = os.path.join(cat_dir, "..", f"{cat}_精选")
    os.makedirs(sel_dir, exist_ok=True)
    
    copied = 0
    for r in selected:
        import shutil
        dst = os.path.join(sel_dir, r['file'])
        if not os.path.exists(dst):  # 同名文件不重复复制
            shutil.copy2(r['path'], dst)
            copied += 1
    
    all_results[cat] = {
        'total': len(total),
        'qualified': len(qualified),
        'deduped': len(deduped),
        'selected': len(selected),
        'copied': copied,
        'quality_range': {
            'min_score': min(r['score'] for r in selected) if selected else 0,
            'max_score': max(r['score'] for r in selected) if selected else 0,
            'min_lap': min(r['laplacian'] for r in selected) if selected else 0,
            'max_lap': max(r['laplacian'] for r in selected) if selected else 0,
        }
    }
    
    print(f"  ✅ 复制到 {cat}_精选/: {copied} 张\n")

# 汇总报告
print("=" * 50)
print("精选汇总")
print("=" * 50)
total_selected = 0
for cat in CATEGORIES:
    r = all_results.get(cat, {})
    print(f"{cat:8s}  {r.get('total',0):>6,} → {r.get('selected',0):>3,} 张  (去重{r.get('deduped',0):>5,} → 精选{r.get('copied',0):>3,})")
    total_selected += r.get('selected', 0)
print(f"\n总计精选: {total_selected} 张")

# 保存报告
report = {
    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
    'params': {
        'target_per_category': TARGET_PER_CATEGORY,
        'min_width': MIN_WIDTH,
        'min_height': MIN_HEIGHT,
        'blur_threshold': BLUR_THRESHOLD,
    },
    'categories': all_results,
    'total_selected': total_selected,
}
with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print(f"\n报告已保存: {OUTPUT_JSON}")
