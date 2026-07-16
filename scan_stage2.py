"""
Stage 2: 图片元数据提取 —— 产出含尺寸/色彩/异常的完整清单
========================================================
读取 Stage 1 的 inventory_raw.csv
对每张图片读文件头提取：width, height, color_mode
标记异常：过小图、超大文件、损坏文件、零字节、色彩异常

策略：
- 只读文件头，不解码像素（Pillow 惰性加载）
- 损坏/异常只标记，不删除
- 产出包含 anomaly 标记列的完整 CSV
"""

import os
import csv
import time
from io import UnsupportedOperation
from PIL import Image, UnidentifiedImageError

# ── 配置 ──────────────────────────────────────────
INVENTORY_CSV = r"E:\AI电商工作创建\LORA训练数据集\01_inventory_raw.csv"
OUTPUT_DIR = r"E:\AI电商工作创建\LORA训练数据集"
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "02_metadata_with_anomaly.csv")
ERROR_LOG = os.path.join(OUTPUT_DIR, "02_errors.txt")

# 异常阈值
MIN_WIDTH = 200       # 宽 < 200px → 过小
MIN_HEIGHT = 200      # 高 < 200px → 过小
MAX_FILE_BYTES = 50 * 1024 * 1024  # 50MB 以上 → 超大

# ── 读取逻辑 ──────────────────────────────────────

def read_image_header(filepath):
    """
    用 Pillow 惰性读取图片文件头。
    返回 (width, height, color_mode) 或 (None, None, None) 表示异常。
    """
    try:
        with Image.open(filepath) as img:
            # 不解码像素，只读文件头
            w, h = img.size
            mode = img.mode
            return (w, h, mode)
    except (FileNotFoundError, PermissionError) as e:
        return (None, None, f"IO_ERROR:{e}")
    except (UnidentifiedImageError, UnsupportedOperation, OSError) as e:
        return (None, None, f"FORMAT_ERROR:{e}")
    except Exception as e:
        return (None, None, f"UNKNOWN_ERROR:{e}")


# ── 主流程 ──────────────────────────────────────

def main():
    print("=" * 60)
    print("Stage 2: 图片元数据提取")
    print(f"输入:    {INVENTORY_CSV}")
    print(f"输出:    {OUTPUT_CSV}")
    print(f"异常日志: {ERROR_LOG}")
    print("=" * 60)

    if not os.path.isfile(INVENTORY_CSV):
        print(f"❌ 输入文件不存在: {INVENTORY_CSV}")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    t0 = time.time()
    errors = []

    with (open(INVENTORY_CSV, "r", encoding="utf-8-sig") as fin,
          open(OUTPUT_CSV, "w", newline="", encoding="utf-8-sig") as fout,
          open(ERROR_LOG, "w", encoding="utf-8-sig") as ferr):

        reader = csv.DictReader(fin)
        # 输出 CSV 增加 width, height, color_mode, anomaly 四列
        fieldnames = reader.fieldnames + ["width", "height", "color_mode", "anomaly"]
        writer = csv.DictWriter(fout, fieldnames=fieldnames)
        writer.writeheader()

        total = 0
        img_total = 0
        img_ok = 0
        img_anomaly = 0
        count_anomaly_small = 0
        count_anomaly_large = 0
        count_anomaly_huge_file = 0
        count_anomaly_zero = 0
        count_anomaly_corrupt = 0
        count_anomaly_cmyk = 0

        for row in reader:
            total += 1
            is_image = row["is_image"] == "1"
            size_bytes = int(row["size_bytes"])
            filepath = row["file_path"]

            result_row = dict(row)
            result_row["width"] = ""
            result_row["height"] = ""
            result_row["color_mode"] = ""
            result_row["anomaly"] = ""

            if not is_image:
                # 非图片文件：直接写入，留空图片字段
                writer.writerow(result_row)
                continue

            img_total += 1
            anomalies = []

            # 1) 零字节检查
            if size_bytes == 0:
                anomalies.append("ZERO_BYTES")

            # 2) 超大文件检查
            if size_bytes > MAX_FILE_BYTES:
                anomalies.append("HUGE_FILE")

            # 3) 读文件头
            w, h, mode = read_image_header(filepath)

            if w is None:
                # 读取失败 → 损坏
                anomalies.append("CORRUPT")
                result_row["color_mode"] = mode if mode else "READ_FAILED"
                count_anomaly_corrupt += 1
            else:
                result_row["width"] = str(w)
                result_row["height"] = str(h)
                result_row["color_mode"] = mode

                # 4) 过小检查
                if w < MIN_WIDTH or h < MIN_HEIGHT:
                    anomalies.append(f"TOO_SMALL({w}x{h})")

                # 5) 非 RGB 色彩模式检查
                if mode not in ("RGB", "RGBA"):
                    anomalies.append(f"NON_RGB({mode})")
                    if mode == "CMYK":
                        count_anomaly_cmyk += 1

            # 汇总 anomaly 标记
            if anomalies:
                result_row["anomaly"] = ";".join(anomalies)
                img_anomaly += 1
                # 记录错误到日志
                err_path = filepath[:80] + "..." if len(filepath) > 80 else filepath
                ferr.write(f"[{';'.join(anomalies)}] {err_path}\n")

                # 计数
                for a in anomalies:
                    if a.startswith("TOO_SMALL"):
                        count_anomaly_small += 1
                    elif a == "HUGE_FILE":
                        count_anomaly_huge_file += 1
                    elif a == "ZERO_BYTES":
                        count_anomaly_zero += 1
                    elif a == "CORRUPT":
                        count_anomaly_corrupt += 1
                    elif a.startswith("NON_RGB"):
                        count_anomaly_cmyk += 1
                # 避免一个图多个异常导致重复计数，修正：
                # 这些计数已经每个异常都加了，但其实一个图可能有多个标记
                # 我们重新按类别计数
            else:
                img_ok += 1

            writer.writerow(result_row)

            if img_total % 5000 == 0:
                elapsed = time.time() - t0
                print(f"  📷 已处理 {img_total:,}/{126394:,} 张图片 ({elapsed:.0f}s) ... "
                      f"正常 {img_ok:,} / 异常 {img_anomaly:,}")

    # 修正计数：重新从 CSV 做精确统计
    # 但先打当前记录
    print()
    print("  ⏳ 正在统计最终异常明细...")

    # 重新扫描 CSV 做精确统计
    with open(OUTPUT_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        final_total = 0
        final_anomaly = 0
        anomaly_detail = {
            "TOO_SMALL": 0,
            "ZERO_BYTES": 0,
            "HUGE_FILE": 0,
            "CORRUPT": 0,
            "NON_RGB": 0,
            "CMYK": 0,
        }
        for row in reader:
            final_total += 1
            a = row.get("anomaly", "").strip()
            if a:
                final_anomaly += 1
                for tag in a.split(";"):
                    if tag.startswith("TOO_SMALL"):
                        anomaly_detail["TOO_SMALL"] += 1
                    elif tag == "ZERO_BYTES":
                        anomaly_detail["ZERO_BYTES"] += 1
                    elif tag == "HUGE_FILE":
                        anomaly_detail["HUGE_FILE"] += 1
                    elif tag == "CORRUPT":
                        anomaly_detail["CORRUPT"] += 1
                    elif tag.startswith("NON_RGB"):
                        anomaly_detail["NON_RGB"] += 1
                        if "CMYK" in tag:
                            anomaly_detail["CMYK"] += 1

    elapsed = time.time() - t0

    print()
    print("=" * 60)
    print(f"✅ 元数据提取完成！耗时 {elapsed:.0f} 秒")
    print(f"   总图片:        {img_total:,}")
    print(f"   正常:          {final_total - final_anomaly:,}")
    print(f"   异常标记:      {final_anomaly:,}")
    print(f"     ├─ 过小图:   {anomaly_detail['TOO_SMALL']:,}")
    print(f"     ├─ 零字节:   {anomaly_detail['ZERO_BYTES']:,}")
    print(f"     ├─ 超大文件: {anomaly_detail['HUGE_FILE']:,}")
    print(f"     ├─ 损坏:     {anomaly_detail['CORRUPT']:,}")
    print(f"     ├─ 非RGB:    {anomaly_detail['NON_RGB']:,}")
    print(f"     └─ 含 CMYK: {anomaly_detail['CMYK']:,}")
    print(f"   输出:          {OUTPUT_CSV}")
    print(f"   错误日志:      {ERROR_LOG}")
    print("=" * 60)


if __name__ == "__main__":
    main()
