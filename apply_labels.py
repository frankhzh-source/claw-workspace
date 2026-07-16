"""
应用审核标签 → 填充 5 大品类训练集目录
读取 review_labels.json + merged_clusters.csv
按品类复制图片到 训练集/{品类}/
"""
import json, csv, os, shutil, time
from collections import Counter

DATA_DIR = r"E:/AI电商工作创建/LORA训练数据集"
LABELS_FILE = r"E:/AI电商工作创建/LORA打标/review_labels.json"
MERGED_CSV = os.path.join(DATA_DIR, "11_merged_clusters.csv")
TRAIN_DIR = os.path.join(DATA_DIR, "训练集")

CATEGORIES = ["少女甜系", "纯欲性感", "知性简约", "新中式国风", "老娘客"]

t0 = time.time()
print("=" * 50)
print("品类标签应用 — 复制图片到训练集目录")
print("=" * 50)

# 1. 读取标签
with open(LABELS_FILE, 'r', encoding='utf-8') as f:
    labels_data = json.load(f)
cluster_labels = labels_data['labels']  # {cluster_id: label}

# 标准化键为 int
cluster_labels = {int(k): v for k, v in cluster_labels.items()}

# 统计品类-簇映射
cat_clusters = Counter()
for cid, label in cluster_labels.items():
    if label != '跳过':
        cat_clusters[label] += 1

print(f"\n标签映射: {len(cluster_labels)} 簇")
for cat, cnt in sorted(cat_clusters.items(), key=lambda x: -x[1]):
    print(f"  {cat}: {cnt} 簇")

# 2. 遍历 CSV，按品类复制
total = 0
copied = Counter()
skipped_count = 0
errors = []

with open(MERGED_CSV, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for idx, row in enumerate(reader):
        fp = row['file_path']
        cid = int(row['merged_cluster'])
        
        # 检查这个簇有没有标签
        label = cluster_labels.get(cid)
        if label is None or label == '跳过':
            skipped_count += 1
            continue
        
        # 只复制已归类的品类
        if label in CATEGORIES:
            dest_dir = os.path.join(TRAIN_DIR, label)
            os.makedirs(dest_dir, exist_ok=True)
            
            fname = os.path.basename(fp)
            dest_path = os.path.join(dest_dir, fname)
            
            # 处理重名（加编号）
            if os.path.exists(dest_path):
                base, ext = os.path.splitext(fname)
                dest_path = os.path.join(dest_dir, f"{base}_{cid}_{idx}{ext}")
            
            try:
                shutil.copy2(fp, dest_path)
                copied[label] += 1
            except Exception as e:
                errors.append((fp, str(e)))
        
        total += 1
        if total % 20000 == 0:
            print(f"  处理中: {total:,} 张...")

elapsed = time.time() - t0
print(f"\n{'='*40}")
print(f"✅ 完成! 耗时: {elapsed:.0f}s")
print(f"\n处理总行: {total:,} 张")
print(f"已跳过: {skipped_count:,} 张")
print(f"已复制: {sum(copied.values()):,} 张")
print(f"\n品类分布:")
for cat, cnt in sorted(copied.items(), key=lambda x: -x[1]):
    print(f"  {cat}: {cnt:,} 张")
print(f"\n错误: {len(errors)} 条")
for fp, err in errors[:5]:
    print(f"  ❌ {fp}: {err}")

# 最终统计
print(f"\n{'='*40}")
print("最终训练集目录:")
for cat in CATEGORIES:
    d = os.path.join(TRAIN_DIR, cat)
    if os.path.exists(d):
        n = len(os.listdir(d))
        print(f"  {cat}: {n:,} 张")
    else:
        print(f"  {cat}: 0 张")
