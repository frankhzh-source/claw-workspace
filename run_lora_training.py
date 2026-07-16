#!/usr/bin/env python
"""FLUX.2 Klein 4B LoRA training - optimized for 5090D 24GB"""
import subprocess, sys, os

ENV_PYTHON = r"D:\lora-env-310\Scripts\python.exe"
TRAIN_SCRIPT = r"C:\Users\jt\WorkBuddy\Claw\train_dreambooth_lora_flux2_klein.py"
TRAIN_DIR = r"E:\AI电商工作创建\LORA训练数据集\训练集\知性简约_精选"
OUTPUT_DIR = r"D:\lora-train\output\知性简约"
MODEL_NAME = "black-forest-labs/FLUX.2-klein-base-4B"

os.makedirs(OUTPUT_DIR, exist_ok=True)

cmd = [
    ENV_PYTHON, TRAIN_SCRIPT,
    f"--pretrained_model_name_or_path={MODEL_NAME}",
    f"--instance_data_dir={TRAIN_DIR}",
    f"--output_dir={OUTPUT_DIR}",
    "--instance_prompt=一件简约家居服",
    "--validation_prompt=一件简约纯色家居服, 莫兰迪色系, 宽松舒适, 棉质面料",
    "--resolution=1024",
    "--train_batch_size=2",            # ↑ from 1 → 2
    "--gradient_accumulation_steps=2", # effective batch=4
    "--gradient_checkpointing",        # keep for VRAM safety
    "--learning_rate=1e-4",
    "--lr_scheduler=constant",
    "--lr_warmup_steps=0",
    "--max_train_steps=1000",
    "--checkpointing_steps=100",          # more frequent saves (every 100 steps)
    "--seed=42",
    "--rank=16",
    "--lora_alpha=16",
    "--use_8bit_adam",
    "--guidance_scale=1",
    "--cache_latents",
    "--mixed_precision=bf16",
    "--do_fp8_training",                 # keep but may fallback
    "--validation_epochs=50",            # reduce validation frequency (was 5)
    "--num_validation_images=1",
    "--report_to=tensorboard",
    "--dataloader_num_workers=0",                 # need 0 to avoid pickle error on Windows
    "--resume_from_checkpoint=checkpoint-300",  # resume from latest checkpoint
]

print("=" * 60)
print("FLUX.2 Klein 4B LoRA Training (Optimized for Speed)")
print(f"Model: {MODEL_NAME}")
print(f"Data:  {TRAIN_DIR} (120 images)")
print(f"Steps: 1000 | Batch: 2 (eff:4) | Rank: 16 | LR: 1e-4")
print(f"GPU:   RTX 5090D 24GB | Precision: bf16+FP8")
print("=" * 60)
print()

env = os.environ.copy()
for key in list(env.keys()):
    if len(env[key]) > 30000:
        del env[key]
env["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
env["HF_HOME"] = r"E:\huggingface-cache"
env["OMP_NUM_THREADS"] = "8"
env["TORCH_CUDNN_V8_API_ENABLED"] = "1"

sys.stdout.reconfigure(encoding='utf-8')
result = subprocess.run(cmd, env=env)
sys.exit(result.returncode)
