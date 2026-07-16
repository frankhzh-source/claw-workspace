"""
CLIP Batch Embedding Extraction — Chinese-CLIP ViT-H/14
=======================================================
读取 02_metadata_with_anomaly.csv，对所有 is_image=1 的图片
提取 Chinese-CLIP ViT-H/14 的 1024 维语义向量

产出：
  - 05_clip_embeddings.npy      (N, 1024) float32
  - 05_clip_paths.txt           每行一个文件路径（与 npy 顺序一致）
  - 05_clip_status.json         运行元数据

用法：
  D:\lora-env-310\Scripts\python.exe clip_extract.py
  或
  python clip_extract.py  （在装了 torch+transformers 的环境）
"""

import os
import sys
import json
import time
import csv
import numpy as np
from PIL import Image

import torch
from transformers import ChineseCLIPModel, ChineseCLIPProcessor

# ── 配置 ──────────────────────────────────────────
META_CSV = r"E:\AI电商工作创建\LORA训练数据集\02_metadata_with_anomaly.csv"
OUTPUT_DIR = r"E:\AI电商工作创建\LORA训练数据集"
MODEL_NAME = "OFA-Sys/chinese-clip-vit-huge-patch14"

# 批处理参数（5090D 24GB 可开大 batch）
BATCH_SIZE = 128
NUM_WORKERS = 4  # 图片加载线程数

# 输出文件
OUT_EMBED = os.path.join(OUTPUT_DIR, "05_clip_embeddings.npy")
OUT_PATHS = os.path.join(OUTPUT_DIR, "05_clip_paths.txt")
OUT_STATUS = os.path.join(OUTPUT_DIR, "05_clip_status.json")


# ── 主流程 ──────────────────────────────────────

def main():
    print("=" * 60)
    print("Chinese-CLIP ViT-H/14 批量向量提取")
    print(f"模型:        {MODEL_NAME}")
    print(f"输入 CSV:    {META_CSV}")
    print(f"输出目录:    {OUTPUT_DIR}")
    print(f"Batch size:  {BATCH_SIZE}")
    print(f"设备:        CUDA" if torch.cuda.is_available() else "设备:        CPU")
    print("=" * 60)

    # 1. 读取图片路径
    print("\n[1/5] 读取图片路径...")
    image_paths = []
    with open(META_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            if row["is_image"] == "1":
                image_paths.append(row["file_path"])

    total = len(image_paths)
    print(f"  → 共 {total:,} 张图片需要提取向量")

    # 2. 加载模型
    print("\n[2/5] 加载模型...")
    t0 = time.time()
    device = "cuda" if torch.cuda.is_available() else "cpu"

    model = ChineseCLIPModel.from_pretrained(MODEL_NAME)
    processor = ChineseCLIPProcessor.from_pretrained(MODEL_NAME)
    model = model.to(device)
    model.eval()

    # warmup (1 pass)
    dummy = Image.new("RGB", (224, 224), color="white")
    dummy_inputs = processor(images=dummy, return_tensors="pt").to(device)
    with torch.no_grad():
        _ = model.get_image_features(**dummy_inputs)
    print(f"  → 模型加载完成 ({time.time()-t0:.0f}s), 设备: {device}")
    if device == "cuda":
        print(f"  → 显存占用: {torch.cuda.memory_allocated()/1024**3:.2f} GB")

    # 3. 批处理提取
    print(f"\n[3/5] 批处理提取向量 (batch={BATCH_SIZE})...")
    all_embeddings = []
    batch_images = []
    batch_indices = []
    failed_paths = []

    t_start = time.time()
    last_log = time.time()

    for idx, path in enumerate(image_paths):
        try:
            img = Image.open(path).convert("RGB")
            batch_images.append(img)
            batch_indices.append(idx)
        except Exception as e:
            failed_paths.append((path, str(e)))
            continue

        # Log progress every 1000 images

        # 批次满 or 最后一批
        if len(batch_images) >= BATCH_SIZE or idx == total - 1:
            if batch_images:
                try:
                    inputs = processor(
                        images=batch_images,
                        return_tensors="pt",
                        padding=True,
                    ).to(device)

                    with torch.no_grad():
                        output = model.get_image_features(**inputs)
                        emb = output.pooler_output
                        # L2 归一化
                        emb = emb / emb.norm(p=2, dim=-1, keepdim=True)

                    all_embeddings.append(emb.cpu().numpy())
                except Exception as e:
                    # 批处理失败，降级为逐张处理
                    print(f"\n  ⚠️ 批处理失败 (size={len(batch_images)}), 降级为逐张处理: {e}")
                    for single_img in batch_images:
                        try:
                            inputs = processor(
                                images=single_img,
                                return_tensors="pt",
                            ).to(device)
                            with torch.no_grad():
                                s_out = model.get_image_features(**inputs)
                                s_emb = s_out.pooler_output
                                s_emb = s_emb / s_emb.norm(p=2, dim=-1, keepdim=True)
                            all_embeddings.append(s_emb.cpu().numpy())
                        except Exception as e2:
                            # 跳过这张
                            dummy_emb = np.zeros((1, model.config.projection_dim), dtype=np.float32)
                            all_embeddings.append(dummy_emb)
                            failed_paths.append((image_paths[batch_indices[len(all_embeddings)-1]], str(e2)))

                batch_images = []
                batch_indices = []

            # 每 10K 张保存一次中间结果防止丢失
            cumulative = sum(arr.shape[0] for arr in all_embeddings)
            if cumulative > 0 and cumulative % 10000 < BATCH_SIZE:
                temp_emb = np.concatenate(all_embeddings, axis=0)
                np.save(os.path.join(OUTPUT_DIR, "05_clip_checkpoint.npy"), temp_emb)
                print(f"\n  💾 Checkpoint saved: {temp_emb.shape[0]:,} vectors")

        # 进度日志：每 1000 张打印一次
        if (idx + 1) % 1000 == 0 or idx == total - 1:
            elapsed_now = time.time() - t_start
            rate = (idx + 1) / elapsed_now
            eta = (total - idx - 1) / rate if rate > 0 else 0
            print(f"  📷 [{idx+1:>7,}/{total:,}] {rate:.0f}张/秒  ETA {eta/60:.0f}分  "
                  f"失败{len(failed_paths)}")

    # 4. 合并结果
    print(f"\n[4/5] 合并结果...")
    if all_embeddings:
        embeddings = np.concatenate(all_embeddings, axis=0)
    else:
        embeddings = np.zeros((0, 1024), dtype=np.float32)

    # 对于失败的图片，补零向量
    if len(failed_paths) > 0:
        print(f"  ⚠️ {len(failed_paths)} 张图片提取失败，补零向量")
        # 注意：这里需要确保顺序一致
        full_embeddings = np.zeros((total, model.config.projection_dim), dtype=np.float32)
        full_embeddings[:embeddings.shape[0]] = embeddings
        embeddings = full_embeddings

    elapsed = time.time() - t_start
    print(f"  → 耗时: {elapsed:.0f}秒 ({elapsed/60:.1f}分钟)")
    print(f"  → 嵌入向量形状: {embeddings.shape}")

    # 5. 保存
    print(f"\n[5/5] 保存到 {OUTPUT_DIR}...")

    # 5a. 保存向量
    np.save(OUT_EMBED, embeddings)

    # 5b. 保存路径
    with open(OUT_PATHS, "w", encoding="utf-8") as f:
        for p in image_paths:
            f.write(p + "\n")

    # 5c. 保存状态
    status = {
        "model": MODEL_NAME,
        "embedding_dim": model.config.projection_dim,
        "total_images": total,
        "success": total - len(failed_paths),
        "failed": len(failed_paths),
        "failed_details": failed_paths[:20],  # 最多记录前20条
        "elapsed_seconds": elapsed,
        "batch_size": BATCH_SIZE,
        "device": device,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(OUT_STATUS, "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)

    # 清理 checkpoint
    cp = os.path.join(OUTPUT_DIR, "05_clip_checkpoint.npy")
    if os.path.exists(cp):
        os.remove(cp)

    print(f"\n✅ 全部完成！")
    print(f"   向量文件:   {OUT_EMBED} ({embeddings.nbytes/1024**2:.0f} MB)")
    print(f"   路径文件:   {OUT_PATHS} ({total:,} 行)")
    print(f"   状态文件:   {OUT_STATUS}")
    print(f"   耗时:       {elapsed:.0f}秒 ({elapsed/60:.1f}分钟)")
    if failed_paths:
        print(f"   失败:       {len(failed_paths)} 张（已补零向量）")


if __name__ == "__main__":
    main()
