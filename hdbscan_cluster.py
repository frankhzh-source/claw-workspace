"""
HDBSCAN 密度聚类：对 UMAP 2D 坐标做密度聚类
产出：视觉簇编号 + 簇大小统计 + 审核用汇总表
"""

import numpy as np
import hdbscan
import os
import json
import time
from collections import Counter

DATA_DIR = r"E:/AI电商工作创建/LORA训练数据集"
UMAP_2D = os.path.join(DATA_DIR, "07_umap_2d.npy")
PATHS_FILE = os.path.join(DATA_DIR, "05_clip_paths.txt")
OUT_CSV = os.path.join(DATA_DIR, "10_hdbscan_clusters.csv")
OUT_JSON = os.path.join(DATA_DIR, "10_hdbscan_summary.json")

print("=" * 55)
print("HDBSCAN 密度聚类 — UMAP 2D 坐标 → 视觉簇")
print("=" * 55)

# 1. 加载数据
print("\n[1/4] 加载 UMAP 2D 坐标...")
t0 = time.time()
umap_2d = np.load(UMAP_2D)
print(f"  形状: {umap_2d.shape}")
print(f"  耗时: {time.time()-t0:.1f}s")

with open(PATHS_FILE, 'r', encoding='utf-8') as f:
    paths = [line.strip() for line in f if line.strip()]
print(f"  路径数: {len(paths):,}")

# 2. HDBSCAN 聚类
print("\n[2/4] HDBSCAN 聚类 (min_cluster_size=100, min_samples=5)...")
t0 = time.time()

clusterer = hdbscan.HDBSCAN(
    min_cluster_size=100,
    min_samples=5,
    metric='euclidean',
    cluster_selection_method='eom',
    gen_min_span_tree=True,
    prediction_data=True,
    core_dist_n_jobs=-1,
)

labels = clusterer.fit_predict(umap_2d)
print(f"  聚类完成! 耗时: {time.time()-t0:.1f}s")

n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
noise = (labels == -1).sum()
print(f"  簇数量: {n_clusters}")
print(f"  噪声点（未归簇）: {noise:,} ({noise/len(labels)*100:.1f}%)")
print(f"  已归簇: {len(labels) - noise:,} ({(len(labels)-noise)/len(labels)*100:.1f}%)")

# 3. 统计每个簇
print("\n[3/4] 统计簇分布...")
valid_labels = labels[labels >= 0]
cnt = Counter(valid_labels)

# 按大小降序排列
sorted_clusters = sorted(cnt.items(), key=lambda x: -x[1])

print(f"\n=== 簇大小分布（前 30）===")
total_clustered = sum(c for _, c in sorted_clusters)
for i, (cid, size) in enumerate(sorted_clusters[:30]):
    pct = size / total_clustered * 100
    print(f"  簇#{cid:3d}  {size:>6,d} 张  ({pct:4.1f}%)")

# 簇大小分布统计
sizes = [s for _, s in sorted_clusters]
print(f"\n  簇大小统计:")
print(f"    最小: {min(sizes):,}")
print(f"    最大: {max(sizes):,}")
print(f"    中位数: {np.median(sizes):,.0f}")
print(f"    均值:   {np.mean(sizes):,.0f}")
# 前5大簇合计占比
top5_pct = sum(sorted_clusters[i][1] for i in range(min(5, len(sorted_clusters)))) / total_clustered * 100
print(f"    前5大簇占比: {top5_pct:.1f}%")

# 4. 输出 CSV
print("\n[4/4] 输出结果...")
import csv
with open(OUT_CSV, 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.writer(f)
    writer.writerow(["file_path", "cluster_id", "cluster_size"])
    for i in range(len(paths)):
        cid = labels[i]
        size = cnt.get(cid, 0) if cid >= 0 else 0
        writer.writerow([paths[i], cid, size])
print(f"  CSV: {OUT_CSV}")

# 保存汇总
summary = {
    "total": len(paths),
    "n_clusters": n_clusters,
    "noise_points": int(noise),
    "clustered_points": int(len(labels) - noise),
    "cluster_selection": "eom",
    "min_cluster_size": 100,
    "min_samples": 5,
    "cluster_sizes": {f"cluster_{cid}": int(s) for cid, s in sorted_clusters},
    "distribution": {
        "min_cluster_size": int(min(sizes)),
        "max_cluster_size": int(max(sizes)),
        "median_cluster_size": int(np.median(sizes)),
        "mean_cluster_size": int(np.mean(sizes)),
        "top5_pct": round(top5_pct, 1),
    },
}
with open(OUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)
print(f"  JSON: {OUT_JSON}")

print(f"\n{'='*55}")
print(f"✅ HDBSCAN 聚类完成！")
print(f"  共 {n_clusters} 个簇，{noise:,} 个噪声点")
print(f"  前5大簇占比: {top5_pct:.1f}%")
print(f"{'='*55}")
