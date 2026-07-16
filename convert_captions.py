#!/usr/bin/env python
"""Convert GLM Caption JSON to per-image .txt files for FLUX.2 Klein training."""
import json, os

CAPTION_FILE = r"E:\AI电商工作创建\LORA训练数据集\14_captions_glm.json"
TRAIN_DIR    = r"E:\AI电商工作创建\LORA训练数据集\训练集"

with open(CAPTION_FILE, "r", encoding="utf-8") as f:
    raw = json.load(f)

# JSON has nested structure: { "results": { "少女甜系": {...}, ... }, "model": ..., "progress": ... }
results = raw.get("results", raw)
# If results itself contains sub-keys that aren't categories, skip them
skip_keys = {"model", "prompt", "total", "done", "errors", "elapsed_min", "results", "progress"}

total = 0
for cat_name, caps in results.items():
    if cat_name in skip_keys:
        continue
    # map category names to directory names
    dir_map = {
        "知性简约": "知性简约_精选",
        "少女甜系": "少女甜系_精选",
        "纯欲性感": "纯欲性感_精选",
        "新中式国风": "新中式国风_精选",
        "老娘客": "老娘客_精选",
    }
    matched_dir = None
    for key, dirname in dir_map.items():
        if key in cat_name:
            matched_dir = dirname
            break
    if not matched_dir:
        print(f"  SKIP: unknown category '{cat_name}'")
        continue

    cat_dir = os.path.join(TRAIN_DIR, matched_dir)
    if not os.path.exists(cat_dir):
        print(f"  SKIP: dir not found '{cat_dir}'")
        continue

    count = 0
    for fname, caption in caps.items():
        name_no_ext = os.path.splitext(fname)[0]
        txt_path = os.path.join(cat_dir, name_no_ext + ".txt")
        with open(txt_path, "w", encoding="utf-8") as out:
            out.write(caption.strip())
        count += 1

    print(f"  {matched_dir}: {count} .txt files written")
    total += count

print(f"\nDone: {total} total caption files written.")
