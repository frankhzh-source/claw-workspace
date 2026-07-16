"""
Stage 1: 全量文件遍历 —— 产出原始清单
=====================================
遍历 E:\工作进度\产品图片\原始工作图片库 的全部文件
产出: inventory_raw.csv（含 is_image 标记）

策略：
- 用 os.scandir 手写递归（最快遍历方式）
- 只读文件系统级元数据（大小/时间/类型）
- 不读图片内容、不解码、不破坏原文件
- 非图片文件标记 is_image=False 但不删除
"""

import os
import csv
import time
from pathlib import Path

# ── 配置 ──────────────────────────────────────────
SRC_ROOT = r"E:\工作进度\产品图片\原始工作图片库"
OUTPUT_DIR = r"E:\AI电商工作创建\LORA训练数据集"
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "01_inventory_raw.csv")

# 图片格式白名单（统一小写判断）
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tiff", ".tif", ".avif", ".heic", ".heif"}

# ── 扫描逻辑 ──────────────────────────────────────

def scandir_recursive(root_dir):
    """
    用 os.scandir 递归遍历目录，返回所有文件的生成器。
    每个元素：(file_path, file_name, ext, size_bytes, modified_at, is_image)
    """
    total = 0
    try:
        with os.scandir(root_dir) as entries:
            for entry in entries:
                if entry.is_file(follow_symlinks=False):
                    total += 1
                    fpath = entry.path
                    fname = entry.name
                    ext = os.path.splitext(fname)[1].lower()
                    is_img = ext in IMAGE_EXTS
                    try:
                        mtime = os.path.getmtime(fpath)
                    except OSError:
                        mtime = 0.0
                    yield (fpath, fname, ext, entry.stat().st_size, mtime, is_img)
                elif entry.is_dir(follow_symlinks=False):
                    yield from scandir_recursive(entry.path)
    except PermissionError as e:
        print(f"  ⚠️ 权限跳过: {e}")
    except OSError as e:
        print(f"  ⚠️ 目录跳过: {e}")


def format_mtime(ts):
    """时间戳 → ISO 8601 字符串"""
    if ts <= 0:
        return ""
    try:
        return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(ts))
    except (ValueError, OSError):
        return ""


# ── 主流程 ──────────────────────────────────────

def main():
    print("=" * 60)
    print("Stage 1: 全量文件遍历")
    print(f"源目录:  {SRC_ROOT}")
    print(f"输出:    {OUTPUT_CSV}")
    print("=" * 60)

    if not os.path.isdir(SRC_ROOT):
        print(f"❌ 源目录不存在: {SRC_ROOT}")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    t0 = time.time()

    # 写 CSV
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "file_path", "file_name", "ext", "size_bytes",
            "modified_at", "is_image"
        ])

        count_total = 0
        count_image = 0
        count_non_image = 0

        for row in scandir_recursive(SRC_ROOT):
            fpath, fname, ext, size, mtime, is_img = row
            mtime_str = format_mtime(mtime)
            writer.writerow([fpath, fname, ext, size, mtime_str, 1 if is_img else 0])

            count_total += 1
            if is_img:
                count_image += 1
            else:
                count_non_image += 1

            # 每 5000 行打一次进度
            if count_total % 5000 == 0:
                elapsed = time.time() - t0
                print(f"  📄 已扫描 {count_total:,} 个文件 ({elapsed:.0f}s) ... 图片 {count_image:,} / 非图片 {count_non_image:,}")

    elapsed = time.time() - t0
    print()
    print("=" * 60)
    print(f"✅ 扫描完成！耗时 {elapsed:.0f} 秒")
    print(f"   总文件:   {count_total:,}")
    print(f"   图片:     {count_image:,}")
    print(f"   非图片:   {count_non_image:,}")
    print(f"   输出:     {OUTPUT_CSV}")
    print("=" * 60)


if __name__ == "__main__":
    main()
