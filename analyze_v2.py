"""分析 V2 零样本分类结果"""
import numpy as np
from collections import Counter

scores = np.load(r'E:/AI电商工作创建/LORA训练数据集/09_zeroshot_scores_v2.npy')
labels = scores.argmax(axis=1)
max_s = scores.max(axis=1)
cats = ['少女甜系','纯欲性感','知性简约','新中式国风','老娘客']

print(f'V2 结果细分:')
print(f'  平均置信度: {max_s.mean():.4f}\n')

for ci in range(5):
    mask = labels == ci
    cat_scores = max_s[mask]
    high40 = (cat_scores > 0.4).mean() * 100
    print(f'  {cats[ci]:12s}  {mask.sum():>7,d}张  均值:{cat_scores.mean():.4f}  '
          f'中位数:{np.median(cat_scores):.4f}  高置信>0.4:{high40:.0f}%')

print()
print('第二选择分布:')
for ci in range(5):
    mask = labels == ci
    if mask.sum() < 100:
        continue
    sm = scores[mask].copy()
    sm[:, ci] = 0
    second = sm.argmax(axis=1)
    cnt = Counter(second)
    top2 = cnt.most_common(3)
    parts = [f'{cats[s[0]]}({s[1]}张,{s[1]/mask.sum()*100:.0f}%)' for s in top2]
    print(f'  {cats[ci]:12s}: 第二选择 -> {", ".join(parts)}')

# 原始目录 vs CLIP分类的交叉对比
print()
print("原始目录 vs CLIP分类交叉表 (top6目录):")
meta_path = r'E:/AI电商工作创建/LORA训练数据集/07_umap_meta.json'
import json
with open(meta_path, 'r') as f:
    meta = json.load(f)
top_dirs = list(meta['dir_distribution'].keys())[:6]

# 加载路径
paths_path = r'E:/AI电商工作创建/LORA训练数据集/05_clip_paths.txt'
with open(paths_path, 'r', encoding='utf-8') as f:
    paths = [line.strip() for line in f if line.strip()]

root_prefix = r"E:\工作进度\产品图片\原始工作图片库"
for d in top_dirs:
    mask = [p.startswith(f'{root_prefix}\\{d}') for p in paths]
    subset = labels[mask]
    cnt = Counter(subset)
    parts = [f'{cats[int(s[0])]}:{s[1]}' for s in cnt.most_common(5)]
    first = cnt.most_common(1)[0]
    print(f'  {d:16s} ({sum(mask):>6,d}张) → {cats[int(first[0])]}({first[1]}张)  [{", ".join(parts[:3])}]')
