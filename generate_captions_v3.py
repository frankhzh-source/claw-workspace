"""
AI Caption 生成 v3 — BLIP-2 开放描述版
使用开放式 prompt，让模型描述图片内容而非重复品类引导
"""
import os, sys, time, json, torch
from PIL import Image
from transformers import Blip2Processor, Blip2ForConditionalGeneration
import random

DATA_DIR = r"E:/AI电商工作创建/LORA训练数据集/训练集"
OUTPUT_DIR = r"E:/AI电商工作创建/LORA训练数据集"

CATEGORIES = ["少女甜系", "纯欲性感", "知性简约", "新中式国风", "老娘客"]

# 多样化的通用描述 prompt（随机抽取，避免重复）
DESCRIBE_PROMPTS = [
    "a photo of",
    "describe this image in detail",
    "what is shown in this picture",
    "this image shows",
]

def main():
    print("=" * 50)
    print("AI Caption 生成 v3 — 开放描述版")
    print("=" * 50)
    
    # 检查模型是否已缓存（BLIP-2 已下载）
    print(f"\n加载模型: BLIP-2...")
    t0 = time.time()
    
    processor = Blip2Processor.from_pretrained("Salesforce/blip2-opt-2.7b", local_files_only=True)
    model = Blip2ForConditionalGeneration.from_pretrained(
        "Salesforce/blip2-opt-2.7b",
        torch_dtype=torch.float16,
        local_files_only=True,
    ).cuda().eval()
    
    mem = torch.cuda.memory_allocated() / 1024**3
    print(f"  加载完成: {time.time()-t0:.0f}s | VRAM: {mem:.1f}GB")
    
    all_captions = {}
    
    for cat in CATEGORIES:
        sel_dir = os.path.join(DATA_DIR, f"{cat}_精选")
        if not os.path.exists(sel_dir):
            continue
        
        files = sorted([f for f in os.listdir(sel_dir) 
                        if f.lower().endswith(('.jpg','.jpeg','.png','.webp'))])
        print(f"\n{'-'*40}")
        print(f"{cat} ({len(files)} 张)...")
        
        captions = {}
        t_cat = time.time()
        
        for i, fname in enumerate(files):
            fpath = os.path.join(sel_dir, fname)
            try:
                image = Image.open(fpath).convert('RGB')
                
                # 随机选一个 prompt 增加多样性
                prompt = random.choice(DESCRIBE_PROMPTS)
                
                inputs = processor(
                    images=image,
                    text=prompt,
                    return_tensors="pt"
                ).to('cuda', dtype=torch.float16)
                
                with torch.no_grad():
                    out = model.generate(
                        **inputs,
                        max_new_tokens=120,
                        num_beams=2,  # beam=2 增加多样性
                        do_sample=True,  # 采样增加多样性
                        temperature=0.7,
                        top_p=0.9,
                    )
                
                caption = processor.decode(out[0], skip_special_tokens=True).strip()
                
                # 清理重复词（BLIP-2 有时会重复）
                words = caption.split()
                deduped = []
                for w in words:
                    if len(deduped) < 2 or w != deduped[-1] or w != deduped[-2]:
                        deduped.append(w)
                caption = ' '.join(deduped)
                
                # 限制长度
                if len(caption.split()) > 100:
                    caption = ' '.join(caption.split()[:100])
                
                captions[fname] = caption
                image.close()
                
            except Exception as e:
                captions[fname] = f"[ERROR]"
            
            if (i + 1) % 20 == 0:
                rate = (i + 1) / (time.time() - t_cat)
                eta = (len(files) - i - 1) / rate if rate > 0 else 0
                print(f"  [{i+1}/{len(files)}]  {rate:.1f}张/分  ETA:{eta:.0f}分")
        
        elapsed = time.time() - t_cat
        print(f"  ✅ {cat}: {len(captions)} 张, {elapsed:.0f}s")
        
        all_captions[cat] = captions
    
    # 保存
    out_path = os.path.join(OUTPUT_DIR, "14_captions_all_v3.json")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(all_captions, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 完成: -> {out_path}")
    
    # 样张
    print(f"\n样张:")
    for cat in CATEGORIES:
        caps = all_captions.get(cat, {})
        if caps:
            keys = list(caps.keys())
            for fname in keys[:2]:
                print(f"\n  [{cat}] {fname}")
                print(f"  {caps[fname][:150]}")

if __name__ == '__main__':
    main()
