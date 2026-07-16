"""
AI Caption 生成 v2 — BLIP-2
对精选图片批量生成 FLUX 风格中文描述
"""
import os, sys, time, json, torch
from PIL import Image
from transformers import Blip2Processor, Blip2ForConditionalGeneration

DATA_DIR = r"E:/AI电商工作创建/LORA训练数据集/训练集"
OUTPUT_DIR = r"E:/AI电商工作创建/LORA训练数据集"

CATEGORIES = ["少女甜系", "纯欲性感", "知性简约", "新中式国风", "老娘客"]

def main():
    print("=" * 50)
    print("AI Caption 生成 v2 — BLIP-2")
    print("=" * 50)
    
    print(f"\n加载模型: BLIP-2 (opt-2.7b)...")
    t0 = time.time()
    
    processor = Blip2Processor.from_pretrained("Salesforce/blip2-opt-2.7b")
    model = Blip2ForConditionalGeneration.from_pretrained(
        "Salesforce/blip2-opt-2.7b",
        torch_dtype=torch.float16,
    ).cuda().eval()
    
    mem = torch.cuda.memory_allocated() / 1024**3
    print(f"  加载完成: {time.time()-t0:.0f}s | VRAM: {mem:.1f}GB")
    
    all_captions = {}
    total = 0
    
    for cat in CATEGORIES:
        sel_dir = os.path.join(DATA_DIR, f"{cat}_精选")
        if not os.path.exists(sel_dir):
            print(f"\n⚠️ {cat}_精选 不存在")
            continue
        
        files = sorted([f for f in os.listdir(sel_dir) 
                        if f.lower().endswith(('.jpg','.jpeg','.png','.webp'))])
        print(f"\n{'-'*40}")
        print(f"{cat} ({len(files)} 张)...")
        
        captions = {}
        t_cat = time.time()
        
        # 品类引导 prompt
        cat_prompts = {
            "少女甜系": "a cute sweet girl's pajama set in pink with bows and lace, detailed product photo",
            "纯欲性感": "a sexy sheer lace silk camisole pajama set, elegant bedroom photography",
            "知性简约": "a simple solid color comfortable loungewear set, relaxed home wear",
            "新中式国风": "a traditional Chinese style pajama with embroidery and Mandarin collar",
            "老娘客": "a luxurious silk robe, elegant high-end loungewear, premium quality",
        }
        prompt = cat_prompts.get(cat, "a detailed product photo of sleepwear")
        
        for i, fname in enumerate(files):
            fpath = os.path.join(sel_dir, fname)
            try:
                image = Image.open(fpath).convert('RGB')
                
                inputs = processor(
                    images=image,
                    text=prompt,
                    return_tensors="pt"
                ).to('cuda', dtype=torch.float16)
                
                with torch.no_grad():
                    out = model.generate(
                        **inputs,
                        max_new_tokens=100,
                        num_beams=3,
                        do_sample=False,
                    )
                
                caption = processor.decode(out[0], skip_special_tokens=True).strip()
                
                # 限制长度
                words = caption.split()
                if len(words) > 100:
                    caption = ' '.join(words[:100])
                if len(words) < 10:
                    caption = caption + " Detailed view of sleepwear garment."
                
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
        total += len(captions)
        
        # 中间保存
        with open(os.path.join(OUTPUT_DIR, f"14_captions_{cat}.json"), 'w', encoding='utf-8') as f:
            json.dump(captions, f, ensure_ascii=False, indent=2)
    
    # 全部保存
    out_path = os.path.join(OUTPUT_DIR, "14_captions_all.json")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(all_captions, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 全部完成: {total} 张 -> {out_path}")
    
    # 样张
    print(f"\n样张（每品类第1张）:")
    for cat in CATEGORIES:
        caps = all_captions.get(cat, {})
        if caps:
            fname = list(caps.keys())[0]
            print(f"\n  [{cat}] {fname}")
            print(f"  {caps[fname][:150]}")

if __name__ == '__main__':
    main()
