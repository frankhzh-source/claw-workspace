"""
簇合并 + 审核界面生成
Step 1: 小簇合并到最近大簇 + 噪声点分配
Step 2: 为每个簇生成缩略图
Step 3: 生成品类审核 HTML 界面
"""

import numpy as np
import os, json, csv, base64, io, time
from collections import Counter
from PIL import Image
from sklearn.neighbors import NearestNeighbors

DATA_DIR = r"E:/AI电商工作创建/LORA训练数据集"
UMAP_2D = os.path.join(DATA_DIR, "07_umap_2d.npy")
PATHS_FILE = os.path.join(DATA_DIR, "05_clip_paths.txt")
HDBSCAN_CSV = os.path.join(DATA_DIR, "10_hdbscan_clusters.csv")
OUT_MERGED_CSV = os.path.join(DATA_DIR, "11_merged_clusters.csv")
OUT_MERGED_JSON = os.path.join(DATA_DIR, "11_merged_summary.json")
OUT_HTML = os.path.join(DATA_DIR, "12_review_interface.html")
THUMB_DIR = os.path.join(DATA_DIR, "_thumbnails")

# ── 参数 ──
LARGE_THRESHOLD = 200      # ≥200 为大簇
SAMPLES_PER_CLUSTER = 9    # 每簇采样 9 张缩略图
THUMB_SIZE = (200, 200)    # 缩略图尺寸（128K→200K，平衡清晰度和性能）

# ── 5 大品类 ──
CATEGORIES = ["少女甜系", "纯欲性感", "知性简约", "新中式国风", "老娘客"]

print("=" * 55)
print("簇合并 + 审核界面生成")
print("=" * 55)

# ── 加载数据 ──
print("\n[1/6] 加载数据...")
t0 = time.time()
umap_2d = np.load(UMAP_2D)
with open(PATHS_FILE, 'r', encoding='utf-8') as f:
    paths = [line.strip() for line in f if line.strip()]

# 读取 HDBSCAN labels
labels = []
with open(HDBSCAN_CSV, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        labels.append(int(row['cluster_id']))
labels = np.array(labels)
print(f"  UMAP: {umap_2d.shape}, 路径: {len(paths):,}, 簇数: {len(set(labels))}")
print(f"  耗时: {time.time()-t0:.1f}s")

# ── Step 1: 簇合并 ──
print("\n[2/6] 合并小簇 < 200 + 噪声点分配...")
t0 = time.time()

cnt = Counter(l[1] for l in enumerate(labels) if l[1] >= 0)
large_clusters = {cid: size for cid, size in cnt.items() if size >= LARGE_THRESHOLD}
small_clusters = {cid: size for cid, size in cnt.items() if size < LARGE_THRESHOLD}

print(f"  大簇 (≥{LARGE_THRESHOLD}): {len(large_clusters)} 个")
print(f"  小簇 (<{LARGE_THRESHOLD}): {len(small_clusters)} 个")
print(f"  噪声点: {(labels==-1).sum():,}")

# 计算大簇质心
large_centroids = {}
for cid in large_clusters:
    mask = labels == cid
    large_centroids[cid] = umap_2d[mask].mean(axis=0)
large_ids = list(large_centroids.keys())
large_cent_arr = np.array([large_centroids[cid] for cid in large_ids])

# 分配小簇 → 最近大簇
small_to_large = {}
for cid in small_clusters:
    mask = labels == cid
    centroid = umap_2d[mask].mean(axis=0)
    dists = np.linalg.norm(large_cent_arr - centroid, axis=1)
    nearest = large_ids[dists.argmin()]
    small_to_large[cid] = nearest

# 构建新 labels
merged = labels.copy()
for i in range(len(merged)):
    cid = merged[i]
    if cid == -1:
        continue  # 噪声点后面单独处理
    if cid in small_to_large:
        merged[i] = small_to_large[cid]

# 处理噪声点：分配到大簇
noise_mask = labels == -1
noise_coords = umap_2d[noise_mask]
if len(noise_coords) > 0:
    nn = NearestNeighbors(n_neighbors=1, metric='euclidean')
    nn.fit(large_cent_arr)
    _, indices = nn.kneighbors(noise_coords)
    noise_assignments = [large_ids[idx[0]] for idx in indices]
    merged[noise_mask] = noise_assignments

# 新簇统计
merged_cnt = Counter(merged)
n_merged = len(merged_cnt)
print(f"  合并后簇数: {n_merged}")
print(f"  耗时: {time.time()-t0:.1f}s")

# ── Step 2: 输出合并结果 ──
print("\n[3/6] 输出合并结果...")
t0 = time.time()

with open(OUT_MERGED_CSV, 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.writer(f)
    writer.writerow(["file_path", "merged_cluster", "cluster_size"])
    for i in range(len(paths)):
        cid = merged[i]
        writer.writerow([paths[i], cid, merged_cnt[cid]])

print(f"  CSV: {OUT_MERGED_CSV}")

# 汇总 JSON
sorted_clusters = sorted(merged_cnt.items(), key=lambda x: -x[1])
summary = {
    "total": len(paths),
    "n_clusters_before": len(cnt),
    "n_clusters_after": n_merged,
    "noise_assigned": int(noise_mask.sum()),
    "merged_small": len(small_clusters),
    "cluster_sizes": {f"cluster_{cid}": int(s) for cid, s in sorted_clusters},
}
with open(OUT_MERGED_JSON, 'w', encoding='utf-8') as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)
print(f"  JSON: {OUT_MERGED_JSON}")

print(f"\n合并后簇分布（前30）:")
for cid, size in sorted_clusters[:30]:
    print(f"  簇#{cid:3d}  {size:>6,d} 张")

print(f"  耗时: {time.time()-t0:.1f}s")

# ── Step 3: 采样 + 生成缩略图 ──
print(f"\n[4/6] 采样 {SAMPLES_PER_CLUSTER} 张/簇 + 生成缩略图...")
t0 = time.time()

os.makedirs(THUMB_DIR, exist_ok=True)

# 计算每个簇的质心，采样最接近质心的图片
cluster_samples = {}
for cid, size in sorted_clusters:
    mask = merged == cid
    idx = np.where(mask)[0]
    if len(idx) == 0:
        continue
    # 找最接近质心的图片
    centroid = umap_2d[idx].mean(axis=0)
    dists = np.linalg.norm(umap_2d[idx] - centroid, axis=1)
    sample_n = min(SAMPLES_PER_CLUSTER, len(idx))
    sample_idx = idx[dists.argsort()[:sample_n]]
    cluster_samples[cid] = [(int(i), paths[int(i)]) for i in sample_idx]

# 生成缩略图
thumb_data = {}
total_samples = sum(len(v) for v in cluster_samples.values())
processed = 0
for cid, samples in cluster_samples.items():
    for idx, fpath in samples:
        processed += 1
        try:
            img = Image.open(fpath)
            img.thumbnail(THUMB_SIZE, Image.LANCZOS)
            # 转为 RGB（处理 PNG RGBA）
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            # base64 编码
            buf = io.BytesIO()
            img.save(buf, format='JPEG', quality=70)
            b64 = base64.b64encode(buf.getvalue()).decode()
            thumb_data[(cid, idx)] = b64
            img.close()
        except Exception as e:
            thumb_data[(cid, idx)] = None  # 失败标记

        if processed % 200 == 0 or processed == total_samples:
            print(f"  缩略图: {processed}/{total_samples}")

# 簇信息的 JSON 数据（给 HTML 用）
clusters_json = []
for cid, size in sorted_clusters:
    samples = cluster_samples.get(cid, [])
    sample_imgs = []
    for idx, fpath in samples:
        b64 = thumb_data.get((cid, idx))
        fname = os.path.basename(fpath)
        sample_imgs.append({
            "b64": f"data:image/jpeg;base64,{b64}" if b64 else None,
            "fname": fname,
            "path": fpath,
        })
    clusters_json.append({
        "id": int(cid),
        "size": int(size),
        "samples": sample_imgs,
    })

print(f"  缩略图完成! 耗时: {time.time()-t0:.1f}s")
print(f"  总采样: {total_samples} 张")

# ── Step 4: 生成审核 HTML ──
print(f"\n[5/6] 生成审核界面 HTML...")
t0 = time.time()

# 品类颜色标记
CAT_COLORS = {
    "少女甜系": "#E45756",
    "纯欲性感": "#F58518",
    "知性简约": "#54A24B",
    "新中式国风": "#B279A2",
    "老娘客": "#4C78A8",
    "跳过": "#CCCCCC",
}

clusters_json_str = json.dumps(clusters_json, ensure_ascii=False, default=str)

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>品类审核界面 — 126K PCS 家居服</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #F8F9FA; color: #1A1A2E; }}

.header {{
    background: linear-gradient(135deg, #1A1A2E, #16213E);
    color: white; padding: 16px 24px; display: flex; justify-content: space-between; align-items: center;
}}
.header h1 {{ font-size: 18px; }}
.header .stats {{ font-size: 13px; opacity: 0.7; }}

.progress-bar {{
    background: white; padding: 12px 24px; border-bottom: 1px solid #E5E7EB;
    display: flex; align-items: center; gap: 16px;
}}
.progress-fill {{ height: 8px; background: #4C78A8; border-radius: 4px; transition: width 0.3s; }}
.progress-track {{ flex:1; height: 8px; background: #E5E7EB; border-radius: 4px; }}
.progress-text {{ font-size: 13px; color: #6B7280; min-width: 120px; }}

.main {{ max-width: 960px; margin: 0 auto; padding: 20px 16px; }}

.cluster-card {{
    background: white; border-radius: 12px; padding: 20px; margin-bottom: 16px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08); border: 1px solid #E5E7EB;
}}
.cluster-card.done {{ border-left: 4px solid #4C78A8; }}
.cluster-header {{
    display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;
}}
.cluster-id {{ font-size: 15px; font-weight: 600; }}
.cluster-size {{ font-size: 13px; color: #6B7280; }}

.thumb-grid {{
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 14px;
}}
.thumb-grid img {{
    width: 100%; aspect-ratio: 1; object-fit: cover; border-radius: 6px;
    border: 1px solid #E5E7EB; cursor: pointer;
}}
.thumb-grid img:hover {{ border-color: #4C78A8; transform: scale(1.03); transition: all 0.15s; }}

.tag-bar {{
    display: flex; gap: 6px; flex-wrap: wrap; align-items: center;
}}
.tag-btn {{
    padding: 6px 14px; border-radius: 16px; border: 1.5px solid #D1D5DB;
    background: white; cursor: pointer; font-size: 13px; transition: all 0.15s;
}}
.tag-btn:hover {{ border-color: #4C78A8; background: #F0F4FF; }}
.tag-btn.selected {{
    border-width: 2px; color: white; font-weight: 500;
}}
.tag-btn.skip {{ color: #9CA3AF; }}
.tag-btn.skip.selected {{ background: #CCCCCC; border-color: #9CA3AF; color: white; }}

.tag-0.selected {{ background: #E45756; border-color: #E45756; }}
.tag-1.selected {{ background: #F58518; border-color: #F58518; }}
.tag-2.selected {{ background: #54A24B; border-color: #54A24B; }}
.tag-3.selected {{ background: #B279A2; border-color: #B279A2; }}
.tag-4.selected {{ background: #4C78A8; border-color: #4C78A8; }}

.submit-bar {{
    position: sticky; bottom: 0; background: white; border-top: 1px solid #E5E7EB;
    padding: 12px 24px; display: flex; justify-content: space-between; align-items: center;
}}
.submit-btn {{
    padding: 10px 28px; background: #4C78A8; color: white; border: none;
    border-radius: 8px; font-size: 14px; font-weight: 500; cursor: pointer;
}}
.submit-btn:hover {{ background: #185FA5; }}

#toast {{
    position: fixed; top: 20px; left: 50%; transform: translateX(-50%);
    background: #1A1A2E; color: white; padding: 10px 24px; border-radius: 8px;
    font-size: 13px; opacity: 0; transition: opacity 0.3s; z-index: 1000;
}}
#toast.show {{ opacity: 1; }}
</style>
</head>
<body>

<div class="header">
    <div>
        <h1>品类审核 — 126K PCS 家居服</h1>
        <div class="stats" id="stats-line">已审核: 0 / {len(clusters_json)} 簇 · 已标记: 0 张</div>
    </div>
    <div style="font-size:12px;opacity:0.6;">🎀 🌸 🧘 🏮 👑</div>
</div>

<div class="progress-bar">
    <div class="progress-track">
        <div class="progress-fill" id="progress-fill" style="width:0%"></div>
    </div>
    <div class="progress-text" id="progress-text">0 / {len(clusters_json)}</div>
</div>

<div class="main" id="cluster-list"></div>

<div class="submit-bar">
    <span id="submit-status">标签全部选择完毕后可提交</span>
    <button class="submit-btn" id="submit-btn">提交审核结果</button>
</div>

<div id="toast"></div>

<script>
const CLUSTERS = {clusters_json_str};
const CATS = {json.dumps(CATEGORIES, ensure_ascii=False)};
const COLORS = {json.dumps(CAT_COLORS, ensure_ascii=False)};

// 状态: 每个簇的选中标签
const selections = {{}};
CLUSTERS.forEach(c => {{ selections[c.id] = null; }});

// 渲染簇列表
function renderClusters() {{
    const container = document.getElementById('cluster-list');
    container.innerHTML = '';
    
    CLUSTERS.forEach((c, ci) => {{
        const card = document.createElement('div');
        card.className = 'cluster-card';
        card.id = `cluster-${{c.id}}`;
        
        let imgs = '';
        c.samples.forEach(s => {{
            if (s.b64) {{
                imgs += `<img src="${{s.b64}}" title="${{s.fname}}" onclick="window.open('file:///${{s.path}}')">`;
            }}
        }});
        
        let tags = '';
        CATS.forEach((cat, ti) => {{
            tags += `<button class="tag-btn tag-${{ti}}" onclick="select(${{c.id}}, ${{ti}})">${{cat}}</button>`;
        }});
        tags += `<button class="tag-btn skip" onclick="select(${{c.id}}, -1)">跳过</button>`;
        
        card.innerHTML = `
            <div class="cluster-header">
                <span class="cluster-id">簇#观察${{ci+1}} <span class="cluster-size">(${{c.size.toLocaleString()}} 张)</span></span>
            </div>
            <div class="thumb-grid">${{imgs}}</div>
            <div class="tag-bar">${{tags}}</div>
        `;
        container.appendChild(card);
    }});
}}

// 选择标签
function select(cid, ti) {{
    selections[cid] = ti;
    const card = document.getElementById(`cluster-${{cid}}`);
    card.classList.add('done');
    
    // 更新按钮样式
    const btns = card.querySelectorAll('.tag-btn');
    btns.forEach((btn, i) => {{
        btn.classList.toggle('selected', 
            (ti >= 0 && i === ti) || (ti === -1 && i === CATS.length));
    }});
    
    updateProgress();
}}

// 更新进度
function updateProgress() {{
    const done = Object.values(selections).filter(v => v !== null).length;
    const total = CLUSTERS.length;
    const pct = (done / total * 100).toFixed(1);
    
    document.getElementById('progress-fill').style.width = pct + '%';
    document.getElementById('progress-text').textContent = `${{done}} / ${{total}}`;
    
    const totalLabeled = CLUSTERS.reduce((sum, c) => sum + (selections[c.id] !== null ? c.size : 0), 0);
    document.getElementById('stats-line').textContent = 
        `已审核: ${{done}} / ${{total}} 簇 · 已标记: ${{totalLabeled.toLocaleString()}} 张`;
    
    document.getElementById('submit-status').textContent = 
        done < total ? `还剩 ${{total - done}} 簇未审核` : '全部审核完毕，可以提交！';
}}

// 提交
document.getElementById('submit-btn').addEventListener('click', () => {{
    const done = Object.values(selections).filter(v => v !== null).length;
    if (done < CLUSTERS.length) {{
        showToast(`还有 ${{CLUSTERS.length - done}} 簇未审核`);
        return;
    }}
    
    // 生成结果数据
    const result = {{
        timestamp: new Date().toISOString(),
        labels: {{}},
    }};
    CLUSTERS.forEach(c => {{
        const ti = selections[c.id];
        result.labels[c.id] = ti === -1 ? '跳过' : CATS[ti];
    }});
    
    // 下载 JSON
    const blob = new Blob([JSON.stringify(result, null, 2)], {{type: 'application/json'}});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'review_labels.json';
    a.click();
    URL.revokeObjectURL(a.href);
    
    showToast('审核结果已下载！请将 review_labels.json 发给我继续处理');
}});

function showToast(msg) {{
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.className = 'show';
    setTimeout(() => t.className = '', 2500);
}}

// 初始化
renderClusters();
updateProgress();
</script>
</body>
</html>
"""

with open(OUT_HTML, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"  HTML: {OUT_HTML}")
html_size = os.path.getsize(OUT_HTML)
print(f"  大小: {html_size/1024/1024:.1f} MB")
print(f"  耗时: {time.time()-t0:.1f}s")

# 清理临时缩略图
import shutil
if os.path.exists(THUMB_DIR):
    shutil.rmtree(THUMB_DIR)

print(f"\n{'='*55}")
print(f"✅ 全部完成！")
print(f"  合并后簇数: {n_merged}")
print(f"  审核界面: {OUT_HTML}")
print(f"  (打开浏览器审核，完成后下载 review_labels.json 发给我)")
print(f"{'='*55}")
