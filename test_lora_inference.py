#!/usr/bin/env python3
"""Test trained LoRA: load base model + LoRA weights, generate sample images"""
import torch, os, sys
from diffusers import Flux2KleinPipeline

MODEL = "black-forest-labs/FLUX.2-klein-base-4B"
LORA_PATH = r"D:\lora-train\output\知性简约\pytorch_lora_weights.safetensors"
OUTPUT_DIR = r"E:\AI电商工作创建\LORA训练数据集\测试产出"
os.makedirs(OUTPUT_DIR, exist_ok=True)

print("=" * 60)
print("Loading FLUX.2 Klein Base model...")
print(f"Model: {MODEL}")
print(f"LoRA:  {LORA_PATH}")
print(f"GPU:   RTX 5090D 24GB")
print("=" * 60)

# 1. Load base pipeline
pipe = Flux2KleinPipeline.from_pretrained(
    MODEL,
    torch_dtype=torch.bfloat16
).to("cuda")

# 2. Load LoRA weights
print("\nLoading LoRA weights...")
pipe.load_lora_weights(LORA_PATH)
print("LoRA weights loaded successfully!")

# 3. Test prompts - 知性简约 style
test_prompts = [
    "一件简约莫兰迪色宽松家居服, 纯棉面料, 温和灯光, 舒适慵懒氛围",     # base style
    "一件纯色亚麻睡衣套装, 燕麦色, 宽松版型, 文艺随性风格",                # variation 1
    "一件极简风格家居服, 雾霾蓝, 纯棉材质, 干净柔和质感",                    # variation 2
    "一件素色长袖睡衣, 浅灰色, 舒适棉质, 简约休闲, 安静卧室氛围",           # variation 3
]

# Also generate a baseline WITHOUT LoRA for comparison
print("\nGenerating images...\n")

for i, prompt in enumerate(test_prompts):
    print(f"[{i+1}/{len(test_prompts)}] Generating with prompt: {prompt[:40]}...")
    
    with torch.no_grad():
        image = pipe(
            prompt=prompt,
            num_inference_steps=25,
            guidance_scale=4.0,
            generator=torch.Generator("cuda").manual_seed(42 + i),
        ).images[0]
    
    out_path = os.path.join(OUTPUT_DIR, f"知性简约_测试{i+1}.png")
    image.save(out_path)
    print(f"  -> Saved: {out_path}\n")

# Generate one comparison WITHOUT LoRA (baseline)
print("Generating baseline (without LoRA)...")
# Temporarily disable LoRA by unloading
pipe.unload_lora_weights()

with torch.no_grad():
    image_base = pipe(
        prompt=test_prompts[0],
        num_inference_steps=25,
        guidance_scale=4.0,
        generator=torch.Generator("cuda").manual_seed(42),
    ).images[0]

out_base = os.path.join(OUTPUT_DIR, "知性简约_基线对比_无LoRA.png")
image_base.save(out_base)
print(f"  -> Saved: {out_base}\n")

print("=" * 60)
print(f"✅ All test images saved to: {OUTPUT_DIR}")
print("=" * 60)
