"""
生成 UMAP 聚类可视化仪表盘
产出: 更直观的交互式 HTML，含统计面板 + 可点击图例 + 品类筛选
"""

import numpy as np
import json
import os

DATA_DIR = r"E:/AI电商工作创建/LORA训练数据集"
EMB_2D = os.path.join(DATA_DIR, "07_umap_2d.npy")
PATHS_FILE = os.path.join(DATA_DIR, "05_clip_paths.txt")
META_FILE = os.path.join(DATA_DIR, "07_umap_meta.json")
OUT_HTML = os.path.join(DATA_DIR, "08_cluster_dashboard.html")

# 加载数据
umap_2d = np.load(EMB_2D)
with open(PATHS_FILE, 'r', encoding='utf-8') as f:
    paths = [line.strip() for line in f if line.strip()]
with open(META_FILE, 'r', encoding='utf-8') as f:
    meta = json.load(f)

dir_dist = meta['dir_distribution']
total = meta['total']

# 提取简写目录
root_prefix = r"E:\工作进度\产品图片\原始工作图片库"
short_dirs = []
for p in paths:
    rel = p.replace(root_prefix, "").lstrip("\\")
    parts = rel.split("\\")
    short_dirs.append(parts[0] if len(parts) > 0 else "?")

# 取前12个有效品类（合并小类到"其他"）
from collections import Counter
dir_counts = Counter(short_dirs)
top12 = [d for d, _ in dir_counts.most_common(12)]
dir_to_label = {}
for d in short_dirs:
    dir_to_label[d] = d if d in top12 else "其他"

labels = [dir_to_label[d] for d in short_dirs]
label_counts = Counter(labels)

# 颜色方案（品类专用配色，清晰好区分）
CAT_COLORS = {
    "睡衣-原图": "#4C78A8",
    "原图": "#F58518",
    "摆拍图": "#54A24B",
    "睡衣-成品": "#E45756",
    "睡衣白底图": "#72B7B2",
    "男装-原图": "#B279A2",
    "男装-成品": "#FF9DA6",
    "丝巾AI图": "#9D755D",
    "邓": "#BAB0AC",
    "松": "#9ECAE9",
    "盼": "#D6A5C9",
    "黄圣依睡衣原图02": "#A1C9F4",
    "其他": "#CCCCCC",
}

# 构建 JS 数据
# 按品类分组数据，让图例可切换
traces_data = {}
for i in range(total):
    lbl = labels[i]
    if lbl not in traces_data:
        traces_data[lbl] = {"x": [], "y": [], "paths": [], "fnames": []}
    traces_data[lbl]["x"].append(float(umap_2d[i, 0]))
    traces_data[lbl]["y"].append(float(umap_2d[i, 1]))
    fname = os.path.basename(paths[i])
    traces_data[lbl]["paths"].append(paths[i])
    traces_data[lbl]["fnames"].append(fname)

# 品类排序（按数量降序）
sorted_labels = sorted(traces_data.keys(), key=lambda l: -label_counts[l])

# 构建 JSON 数据（每个品类单独的 trace）
import random
random.seed(42)

json_data = []
for lbl in sorted_labels:
    d = traces_data[lbl]
    # 如果品类太大（>5000点），抽样保留密度
    pts = len(d["x"])
    if pts > 5000:
        idx = sorted(random.sample(range(pts), 5000))
        x_sub = [d["x"][i] for i in idx]
        y_sub = [d["y"][i] for i in idx]
        p_sub = [d["paths"][i] for i in idx]
        f_sub = [d["fnames"][i] for i in idx]
    else:
        x_sub = d["x"]
        y_sub = d["y"]
        p_sub = d["paths"]
        f_sub = d["fnames"]
    
    json_data.append({
        "label": lbl,
        "count": pts,
        "sampled": len(x_sub),
        "x": x_sub,
        "y": y_sub,
        "paths": p_sub,
        "fnames": f_sub,
        "color": CAT_COLORS.get(lbl, "#CCCCCC"),
    })

json_str = json.dumps(json_data, ensure_ascii=False)

# 生成 HTML
html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CLIP 语义空间 UMAP 聚类 — 126K PCS 图片</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #F8F9FA; color: #1A1A2E; }}

.header {{
    background: linear-gradient(135deg, #1A1A2E 0%, #16213E 100%);
    color: white;
    padding: 20px 32px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}}
.header h1 {{ font-size: 20px; font-weight: 600; }}
.header .sub {{ font-size: 13px; opacity: 0.7; margin-top: 4px; }}

.stats-bar {{
    display: flex;
    gap: 16px;
    padding: 16px 32px;
    background: white;
    border-bottom: 1px solid #E5E7EB;
}}
.stat-card {{
    flex: 1;
    background: #F8F9FA;
    border-radius: 10px;
    padding: 14px 18px;
    text-align: center;
}}
.stat-card .num {{ font-size: 28px; font-weight: 700; color: #1A1A2E; }}
.stat-card .label {{ font-size: 12px; color: #6B7280; margin-top: 2px; }}

.main {{ display: flex; height: calc(100vh - 190px); }}

.sidebar {{
    width: 260px;
    min-width: 260px;
    background: white;
    overflow-y: auto;
    border-right: 1px solid #E5E7EB;
    padding: 12px 0;
}}
.sidebar-title {{
    font-size: 13px;
    font-weight: 600;
    color: #6B7280;
    padding: 8px 18px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}
.legend-item {{
    display: flex;
    align-items: center;
    padding: 8px 18px;
    cursor: pointer;
    transition: all 0.15s;
    border-left: 3px solid transparent;
}}
.legend-item:hover {{ background: #F3F4F6; }}
.legend-item.active {{ border-left-color: #1A1A2E; background: #F0F4FF; }}
.legend-item.hidden {{ opacity: 0.35; }}
.legend-dot {{
    width: 12px;
    height: 12px;
    border-radius: 3px;
    margin-right: 10px;
    flex-shrink: 0;
}}
.legend-text {{ flex: 1; font-size: 13px; }}
.legend-count {{ font-size: 12px; color: #9CA3AF; margin-left: 6px; }}

.chart-area {{ flex: 1; position: relative; }}
#plotly-chart {{ width: 100%; height: 100%; }}

.footer {{
    text-align: center;
    padding: 8px;
    font-size: 11px;
    color: #9CA3AF;
    background: white;
    border-top: 1px solid #E5E7EB;
}}
</style>
</head>
<body>

<div class="header">
    <div>
        <h1>📊 126K PCS 图片 — CLIP 语义空间 UMAP 聚类</h1>
        <div class="sub">Chinese-CLIP ViT-H/14 · 1024维 → 2D · n_neighbors=30 · metric=cosine</div>
    </div>
    <div style="font-size:13px; opacity:0.8;">5090D · 本地训练</div>
</div>

<div class="stats-bar" id="stats-bar">
    <div class="stat-card">
        <div class="num">{total:,}</div>
        <div class="label">图片总数</div>
    </div>
    <div class="stat-card">
        <div class="num">{len(sorted_labels)}</div>
        <div class="label">品类分组</div>
    </div>
    <div class="stat-card">
        <div class="num">{len(top12)}+</div>
        <div class="label">来源目录</div>
    </div>
    <div class="stat-card" style="background:#E8F5E9;">
        <div class="num">{dir_dist.get('睡衣-原图', 0):,}</div>
        <div class="label">🏆 最大品类：睡衣-原图</div>
    </div>
</div>

<div class="main">
    <div class="sidebar">
        <div class="sidebar-title">品类图例 · 点击切换</div>
        <div id="legend-container"></div>
    </div>
    <div class="chart-area">
        <div id="plotly-chart"></div>
    </div>
</div>

<div class="footer">💡 悬停查看图片路径 · 点击图例切换品类显示 · 拖拽缩放 · 品类按数量降序排列</div>

<script>
const TRACES = {json_str};

// 构建 Plotly traces
const traces = [];
const legendItems = [];
const state = {{}};

TRACES.forEach((t, i) => {{
    state[i] = true;
    
    const trace = {{
        type: 'scattergl',
        mode: 'markers',
        name: t.label,
        x: t.x,
        y: t.y,
        text: t.paths.map((p, j) => `<b>${{t.label}}</b><br>${{t.fnames[j]}}`),
        hoverinfo: 'text',
        hoverlabel: {{ bgcolor: 'white', font: {{ size: 11, family: 'Arial' }} }},
        marker: {{
            color: t.color,
            size: t.count > 10000 ? 1.8 : (t.count > 1000 ? 2.2 : 3),
            line: {{ width: 0.3, color: 'rgba(0,0,0,0.1)' }},
        }},
        showlegend: false,
    }};
    traces.push(trace);
    
    // 图例项
    const pct = (t.count / {total} * 100).toFixed(1);
    legendItems.push({{
        label: t.label,
        count: t.count,
        pct: pct,
        color: t.color,
        idx: i,
    }});
}});

const layout = {{
    title: '',
    width: null,
    height: null,
    hovermode: 'closest',
    plot_bgcolor: '#F8F9FA',
    paper_bgcolor: '#F8F9FA',
    xaxis: {{ showgrid: true, gridcolor: '#E5E7EB', zeroline: false, title: 'UMAP-1', visible: false }},
    yaxis: {{ showgrid: true, gridcolor: '#E5E7EB', zeroline: false, title: 'UMAP-2', visible: false }},
    margin: {{ l: 10, r: 10, t: 10, b: 10, pad: 0 }},
    dragmode: 'zoom',
    autosize: true,
}};

const config = {{
    responsive: true,
    displayModeBar: true,
    modeBarButtonsToRemove: ['sendDataToCloud', 'lasso2d', 'select2d'],
    displaylogo: false,
    scrollZoom: true,
}};

Plotly.newPlot('plotly-chart', traces, layout, config);

// 渲染图例
function renderLegend() {{
    const container = document.getElementById('legend-container');
    container.innerHTML = '';
    
    legendItems.forEach(item => {{
        const div = document.createElement('div');
        div.className = 'legend-item active';
        div.dataset.idx = item.idx;
        div.innerHTML = `
            <div class="legend-dot" style="background:${{item.color}}"></div>
            <span class="legend-text">${{item.label}}</span>
            <span class="legend-count">${{item.count.toLocaleString()}} (${{item.pct}}%)</span>
        `;
        div.addEventListener('click', () => toggleCategory(item.idx));
        container.appendChild(div);
    }});
}}

function toggleCategory(idx) {{
    state[idx] = !state[idx];
    const visibility = state[idx] ? true : 'legendonly';
    Plotly.restyle('plotly-chart', 'visible', visibility, [idx]);
    
    // 更新图例样式
    const items = document.querySelectorAll('.legend-item');
    items.forEach(el => {{
        const i = parseInt(el.dataset.idx);
        el.classList.toggle('active', state[i]);
        el.classList.toggle('hidden', !state[i]);
    }});
}}

renderLegend();

// 窗口自适应
window.addEventListener('resize', () => {{
    Plotly.Plots.resize(document.getElementById('plotly-chart'));
}});
</script>
</body>
</html>
"""

with open(OUT_HTML, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"✅ 仪表盘已生成: {OUT_HTML}")
print(f"   大小: {os.path.getsize(OUT_HTML)/1024/1024:.1f} MB")

# 写入品类汇总
summary = []
for lbl in sorted_labels:
    d = traces_data[lbl]
    summary.append(f"  {lbl:20s}  {len(d['x']):>7,d}")
print(f"\n品类分布:")
print("\n".join(summary))
