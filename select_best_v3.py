"""
品类内精选 v3 — 多进程加速版
使用 multiprocessing Pool 并行处理图片去重+质量评分
"""
import os, sys, time, json, hashlib
from collections import defaultdict
from PIL import Image
import numpy as np
from multiprocessing import Pool, cpu_count
import shutil

TRAIN_DIR = r"E:/AI电商工作创建/LORA训练数据集/训练集"
OUTPUT_JSON = r"E:/AI电商工作创建/LORA训练数据集/13_selection_report.json"
TARGET = 120
MIN_SIZE = 400

CATEGORIES = ["少女甜系", "纯欲性感", "知性简约", "新中式国风", "老娘客"]

def process_image(args):
    """处理单张图片：质量评分 + dhash"""
    fname, fpath = args
    try:
        fsize = os.path.getsize(fpath)
        if fsize < 10240:
            return None
        
        img = Image.open(fpath)
        w, h = img.size
        if w < MIN_SIZE or h < MIN_SIZE:
            img.close()
            return None
        
        # dhash
        gray = img.convert('L').resize((9, 8), Image.LANCZOS)
        pixels = np.array(gray, dtype=int)
        diff = pixels[:, 1:] > pixels[:, :-1]
        phash = diff.tobytes()
        img.close()
        
        # 质量评分
        mp = w * h / (1024 * 1024)
        score = min(mp, 2.0) * min(fsize / 50000, 2.0)
        
        return {
            'file': fname,
            'path': fpath,
            'w': w, 'h': h,
            'size_kb': round(fsize / 1024, 1),
            'score': round(score, 1),
            'hash': phash,
        }
    except:
        return None

def process_category(cat):
    cat_dir = os.path.join(TRAIN_DIR, cat)
    if not os.path.exists(cat_dir):
        return cat, None
    
    files = [f for f in os.listdir(cat_dir) 
             if f.lower().endswith(('.jpg','.jpeg','.png','.webp'))]
    total = len(files)
    print(f"[{cat}] {total} 张...", end=' ', flush=True)
    t0 = time.time()
    
    # 多进程处理
    n_workers = min(cpu_count(), 8)
    with Pool(n_workers) as pool:
        results = pool.map(process_image, [(f, os.path.join(cat_dir, f)) for f in files])
    
    # 去空 + 去重
    valid = [r for r in results if r is not None]
    seen = set()
    deduped = []
    for r in sorted(valid, key=lambda x: -x['score']):
        if r['hash'] not in seen:
            seen.add(r['hash'])
            deduped.append(r)
    
    selected = deduped[:TARGET]
    
    # 复制
    sel_dir = os.path.join(TRAIN_DIR, f"{cat}_精选")
    os.makedirs(sel_dir, exist_ok=True)
    copied = 0
    for r in selected:
        dst = os.path.join(sel_dir, r['file'])
        if not os.path.exists(dst):
            try:
                shutil.copy2(r['path'], dst)
                copied += 1
            except:
                pass
    
    elapsed = time.time() - t0
    print(f"{elapsed:.0f}s → {len(selected)}张  (去重:{total-len(deduped)} 复制:{copied})")
    
    report = {
        'total': total,
        'valid': len(valid),
        'deduped': len(deduped),
        'selected': len(selected),
        'copied': copied,
        'elapsed_s': round(elapsed),
    }
    return cat, report

if __name__ == '__main__':
    print("=" * 50)
    print("品类内精选 v3 — 多进程版")
    print("=" * 50 + "\n")

    all_results = {}
    for cat in CATEGORIES:
        cat, report = process_category(cat)
        all_results[cat] = report
    
    print("\n" + "=" * 50)
    print("精选汇总")
    print("=" * 50)
    total_sel = 0
    for cat in CATEGORIES:
        r = all_results[cat]
        print(f"{cat:8s} {r['total']:>6,} → {r['selected']:>3,}张  (去重{r['valid']-r['deduped']:>4,} 复制{r['copied']:>3,})")
        total_sel += r['selected']
    print(f"\n总计精选: {total_sel} 张")

    report = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'params': {'target_per_category': TARGET, 'min_size': MIN_SIZE},
        'categories': all_results,
        'total_selected': total_sel,
    }
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"报告: {OUTPUT_JSON}")
