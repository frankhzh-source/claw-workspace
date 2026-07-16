"""
UMAP 聚类降维 + 可视化
输入: 05_clip_embeddings.npy (126,394 × 1024)
输出: 07_umap_cluster.html (交互式散点图)
"""

import numpy as np
import umap
import plotly.graph_objects as go
import os
import json
import time

# ── 路径 ──
DATA_DIR = r"E:/AI电商工作创建/LORA训练数据集"
EMB_FILE = os.path.join(DATA_DIR, "05_clip_embeddings.npy")
PATHS_FILE = os.path.join(DATA_DIR, "05_clip_paths.txt")
STATUS_FILE = os.path.join(DATA_DIR, "05_clip_status.json")
OUT_HTML = os.path.join(DATA_DIR, "07_umap_cluster.html")
OUT_NPY = os.path.join(DATA_DIR, "07_umap_2d.npy")
OUT_JSON = os.path.join(DATA_DIR, "07_umap_meta.json")

print("=" * 55)
print("UMAP 聚类降维 — 126K × 1024 → 2D")
print("=" * 55)

# 1. 加载向量
print("\n[1/4] 加载 CLIP 向量...")
t0 = time.time()
emb = np.load(EMB_FILE, mmap_mode='r')
print(f"  形状: {emb.shape}")
print(f"  类型: {emb.dtype}")
print(f"  耗时: {time.time()-t0:.1f}s")

# 2. 加载路径（用于 hover）
print("\n[2/4] 加载路径映射...")
with open(PATHS_FILE, 'r', encoding='utf-8') as f:
    paths = [line.strip() for line in f if line.strip()]
print(f"  路径数: {len(paths):,}")
assert len(paths) == emb.shape[0], f"路径数({len(paths)}) 与向量数({emb.shape[0]}) 不匹配"

# 3. UMAP 降维
print("\n[3/4] UMAP 降维 (n_neighbors=30, min_dist=0.1)...")
t0 = time.time()

# 加载全量到内存（494MB，可接受）
emb_full = np.array(emb, dtype=np.float32)

reducer = umap.UMAP(
    n_neighbors=30,
    min_dist=0.1,
    n_components=2,
    metric='cosine',
    verbose=True,
    n_jobs=-1,  # 全核并行（不设 random_state 以启用并行）
)

umap_2d = reducer.fit_transform(emb_full)
del emb_full  # 释放内存

print(f"  降维完成: {umap_2d.shape}")
print(f"  耗时: {time.time()-t0:.1f}s")

# 立即保存 2D 坐标，防止后续可视化出错丢失数据
np.save(OUT_NPY, umap_2d)
print(f"  ✅ 2D坐标已保存: {OUT_NPY}")

# 4. 提取源目录简写（用于 hover 和着色）
print("\n[4/4] 生成可视化...")
root_prefix = r"E:\工作进度\产品图片\原始工作图片库"
short_dirs = []
for p in paths:
    rel = p.replace(root_prefix, "").lstrip("\\")
    parts = rel.split("\\")
    short_dirs.append(parts[0] if len(parts) > 0 else "?")

# 统计并分配颜色
from collections import Counter
dir_counts = Counter(short_dirs)
top_dirs = [d for d, _ in dir_counts.most_common(15)]
print(f"  前15个目录: {len(top_dirs)} 类")

# 颜色映射
import plotly.express as px
color_map = {
    top_dirs[i]: px.colors.qualitative.Plotly[i % len(px.colors.qualitative.Plotly)]
    for i in range(len(top_dirs))
}
color_map["其他"] = "#CCCCCC"

colors = []
hover_texts = []
for p, d in zip(paths, short_dirs):
    c = color_map.get(d, color_map["其他"])
    colors.append(c)
    # hover 文本：精简
    fname = os.path.basename(p)
    hover_texts.append(f"<b>{d}</b><br>{fname}<br>{p}")

# 按目录排序（让大簇在底层，小簇在上层可见）
sort_idx = np.argsort([-dir_counts.get(d, 0) for d in short_dirs])
umap_2d_sorted = umap_2d[sort_idx]
colors_sorted = [colors[i] for i in sort_idx]
hover_sorted = [hover_texts[i] for i in sort_idx]

# 图例
legend_traces = []
for d, c in color_map.items():
    cnt = dir_counts.get(d, 0)
    label = f"{d} ({cnt:,}张)" if cnt > 0 else d
    legend_traces.append(go.Scattergl(
        x=[None], y=[None],
        mode='markers',
        marker=dict(size=8, color=c),
        name=label,
        showlegend=True,
    ))

# 主散点图（gl 加速，126K 点流畅）
main_trace = go.Scattergl(
    x=umap_2d_sorted[:, 0],
    y=umap_2d_sorted[:, 1],
    mode='markers',
    marker=dict(
        size=2.5,
        color=colors_sorted,
        line=dict(width=0.2, color='rgba(0,0,0,0.15)'),
    ),
    text=hover_sorted,
    hoverinfo='text',
    hoverlabel=dict(bgcolor='white', font_size=11, font_family='Arial'),
    showlegend=False,
)

fig = go.Figure(
    data=[main_trace] + legend_traces,
    layout=go.Layout(
        title=dict(
            text=f"CLIP 语义空间 UMAP 降维 — 126,394 张 PCS 图片",
            font=dict(size=16),
        ),
        width=1200,
        height=900,
        hovermode='closest',
        plot_bgcolor='#F8F9FA',
        paper_bgcolor='#F8F9FA',
        xaxis=dict(showgrid=True, gridcolor='#E5E7EB', zeroline=False, title='UMAP-1'),
        yaxis=dict(showgrid=True, gridcolor='#E5E7EB', zeroline=False, title='UMAP-2'),
        legend=dict(
            font=dict(size=11),
            itemsizing='constant',
            traceorder='normal',
            x=1.02, y=1,
            xanchor='left',
            yanchor='top',
        ),
        margin=dict(l=60, r=200, t=60, b=60),
    )
)

fig.write_html(OUT_HTML, auto_open=False)
print(f"  HTML 输出: {OUT_HTML}")

# 保存降维坐标
np.save(OUT_NPY, umap_2d)
print(f"  2D坐标输出: {OUT_NPY}")

# 保存关联元数据（路径前1000条足够用于验证）
meta = {
    "total": len(paths),
    "shape_2d": list(umap_2d.shape),
    "dir_distribution": {d: c for d, c in dir_counts.most_common(20)},
    "sample_paths": paths[:10],
    "umap_params": {
        "n_neighbors": 30,
        "min_dist": 0.1,
        "metric": "cosine",
        "random_state": 42,
    },
}
with open(OUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(meta, f, ensure_ascii=False, indent=2)
print(f"  元数据输出: {OUT_JSON}")

print(f"\n{'='*55}")
print(f"✅ UMAP 降维完成！")
print(f"  总耗时: {time.time()-t0:.0f}s")
print(f"  打开 {OUT_HTML} 查看聚类效果")
print(f"{'='*55}")
