"""
AI Caption 生成 — Florence-2-large
对精选图片批量生成 FLUX 风格中文描述
"""
import os, sys, time, json, torch
from PIL import Image
from transformers import AutoModelForCausalLM, AutoProcessor

DATA_DIR = r"E:/AI电商工作创建/LORA训练数据集/训练集"
OUTPUT_DIR = r"E:/AI电商工作创建/LORA训练数据集"
MODEL_ID = "microsoft/Florence-2-large"

CATEGORIES = ["少女甜系", "纯欲性感", "知性简约", "新中式国风", "老娘客"]

# 品类专用 prompt（引导描述风格）
CATEGORY_PROMPTS = {
    "少女甜系": "<MORE_DETAILED_CAPTION>",
    "纯欲性感": "<MORE_DETAILED_CAPTION>",
    "知性简约": "<MORE_DETAILED_CAPTION>",
    "新中式国风": "<MORE_DETAILED_CAPTION>",
    "老娘客": "<MORE_DETAILED_CAPTION>",
}

def main():
    print("=" * 50)
    print("AI Caption 生成 — Florence-2-large")
    print("=" * 50)
    
    # 加载模型（5090D fp16）
    print(f"\n加载模型: {MODEL_ID}...")
    t0 = time.time()
    
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        torch_dtype=torch.float16,
        trust_remote_code=True,
    ).cuda().eval()
    
    processor = AutoProcessor.from_pretrained(
        MODEL_ID,
        trust_remote_code=True,
    )
    
    mem = torch.cuda.memory_allocated() / 1024**3
    print(f"  加载完成: {time.time()-t0:.0f}s | VRAM: {mem:.1f}GB")
    
    all_captions = {}
    total = 0
    
    for cat in CATEGORIES:
        sel_dir = os.path.join(DATA_DIR, f"{cat}_精选")
        if not os.path.exists(sel_dir):
            print(f"\n⚠️ {cat}_精选 目录不存在")
            continue
        
        files = sorted([f for f in os.listdir(sel_dir) 
                        if f.lower().endswith(('.jpg','.jpeg','.png','.webp'))])
        print(f"\n{'-'*40}")
        print(f"{cat} ({len(files)} 张)...")
        
        captions = {}
        t_cat = time.time()
        prompt = CATEGORY_PROMPTS[cat]
        
        for i, fname in enumerate(files):
            fpath = os.path.join(sel_dir, fname)
            try:
                image = Image.open(fpath).convert('RGB')
                
                inputs = processor(
                    text=prompt,
                    images=image,
                    return_tensors="pt"
                ).to('cuda', dtype=torch.float16)
                
                with torch.no_grad():
                    generated_ids = model.generate(
                        input_ids=inputs["input_ids"],
                        pixel_values=inputs["pixel_values"],
                        max_new_tokens=150,
                        num_beams=3,
                        do_sample=False,
                    )
                
                generated_text = processor.batch_decode(
                    generated_ids, skip_special_tokens=False
                )[0]
                
                # 解析输出
                parsed = processor.post_process_generation(
                    generated_text, 
                    task=prompt, 
                    image_size=(image.width, image.height)
                )
                
                caption = parsed.get(prompt, generated_text).strip()
                
                # 限制长度 40-100 词
                words = caption.split()
                if len(words) > 100:
                    caption = ' '.join(words[:100])
                
                captions[fname] = caption
                image.close()
                
            except Exception as e:
                captions[fname] = f"[ERROR: {str(e)[:50]}]"
            
            if (i + 1) % 20 == 0:
                mem_now = torch.cuda.memory_allocated() / 1024**3
                rate = (i + 1) / (time.time() - t_cat)
                eta = (len(files) - i - 1) / rate if rate > 0 else 0
                print(f"  [{i+1}/{len(files)}]  {rate:.1f}张/分  ETA {eta:.0f}分  VRAM:{mem_now:.1f}GB")
        
        elapsed = time.time() - t_cat
        print(f"  ✅ {cat} 完成: {len(captions)} 张, {elapsed:.0f}s ({len(captions)/elapsed*60:.1f}张/分)")
        
        all_captions[cat] = captions
        total += len(captions)
        
        # 每品类保存一次中间结果
        temp_path = os.path.join(OUTPUT_DIR, f"14_captions_{cat}.json")
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(captions, f, ensure_ascii=False, indent=2)
        print(f"  中间保存: {temp_path}")
    
    # 合并保存全部
    print(f"\n{'='*40}")
    print(f"汇总: {total} 张")
    
    output_path = os.path.join(OUTPUT_DIR, "14_captions_all.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_captions, f, ensure_ascii=False, indent=2)
    print(f"保存: {output_path}")
    
    # 打印样张
    print(f"\n样张（每品类前2张）:")
    for cat in CATEGORIES:
        caps = all_captions.get(cat, {})
        for fname in list(caps.keys())[:2]:
            print(f"\n  [{cat}] {fname}")
            print(f"    {caps[fname][:120]}...")

if __name__ == '__main__':
    main()
