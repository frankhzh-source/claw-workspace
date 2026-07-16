# -*- coding: utf-8 -*-
"""深度扫描指定目录的内容结构"""

import os
from collections import Counter, defaultdict

ROOT = r"E:\工作进度\产品图片\原始工作图片库"
IMG_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.tiff', '.tif', '.avif'}

TARGETS = [
    "松",
    "盼", 
    "邓",
    "睡衣详情",
]

def scan_folder(base_path):
    """扫描单个文件夹的完整结构"""
    if not os.path.exists(base_path):
        return None
    
    total_imgs = 0
    total_dirs = 0
    ext_counter = Counter()
    subfolder_stats = []
    all_img_files = []
    
    for dirpath, dirnames, filenames in os.walk(base_path):
        dirnames[:] = [d for d in dirnames if not d.startswith('.') and not d.startswith('$')]
        total_dirs += 1
        imgs = [f for f in filenames if os.path.splitext(f)[1].lower() in IMG_EXTS]
        total_imgs += len(imgs)
        for f in imgs:
            all_img_files.append(os.path.join(dirpath, f))
            ext = os.path.splitext(f)[1].lower()
            ext_counter[ext] += 1
        
        rel = os.path.relpath(dirpath, base_path)
        if rel == '.':
            rel = '(根)'
        if imgs:
            subfolder_stats.append((rel, len(imgs), len(filenames)))
    
    return {
        'total_imgs': total_imgs,
        'total_dirs': total_dirs,
        'ext_counter': ext_counter,
        'subfolder_stats': sorted(subfolder_stats, key=lambda x: x[1], reverse=True),
        'all_img_files': all_img_files,
    }

def sample_images(img_files, n=5):
    """均匀抽样 n 张图片"""
    if len(img_files) <= n:
        return img_files
    step = len(img_files) // n
    return [img_files[i * step] for i in range(n)]

def print_report(name, data):
    print(f"\n{'=' * 70}")
    print(f"  📁 {name}")
    print(f"{'=' * 70}")
    if data is None:
        print(f"  ❌ 文件夹不存在或无法访问")
        return
    print(f"  总图片数:   {data['total_imgs']:,}")
    print(f"  总文件夹数: {data['total_dirs']:,}")
    print(f"  图片格式:   {dict(data['ext_counter'].most_common())}")
    print()
    
    # Show subfolder structure
    print(f"  【子目录结构 TOP 15】")
    print(f"  {'子目录':<55} {'图片':>8}")
    print(f"  {'-'*55} {'-'*8}")
    for rel, ic, tc in data['subfolder_stats'][:15]:
        label = rel if len(rel) <= 54 else "..." + rel[-51:]
        print(f"  {label:<55} {ic:>8,}")
    
    if len(data['subfolder_stats']) > 15:
        print(f"  ... 还有 {len(data['subfolder_stats'])-15} 个子目录")
    
    # Small folder analysis
    single = sum(1 for _, ic, _ in data['subfolder_stats'] if ic == 1)
    small = sum(1 for _, ic, _ in data['subfolder_stats'] if ic <= 3)
    print(f"\n  ⚠ 仅1张图的子目录: {single}")
    print(f"  ⚠ 仅≤3张图的子目录: {small}")
    
    # Show sampled image paths (for Read tool)
    print(f"\n  【抽样图片路径（供视觉检查）】")
    samples = sample_images(data['all_img_files'], min(5, len(data['all_img_files'])))
    for i, sp in enumerate(samples):
        print(f"  样本 {i+1}: {sp}")
    
    return samples

if __name__ == '__main__':
    all_samples = {}
    
    for name in TARGETS:
        path = os.path.join(ROOT, name)
        data = scan_folder(path)
        samples = print_report(name, data)
        all_samples[name] = {
            'data': data,
            'samples': samples
        }
    
    print(f"\n{'=' * 70}")
    print(f"  扫描完成！共扫描 {len(TARGETS)} 个目标目录")
    print(f"{'=' * 70}")
