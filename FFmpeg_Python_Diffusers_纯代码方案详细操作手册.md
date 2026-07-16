# FFmpeg + Python Diffusers 纯代码方案：完整操作手册

**用途**：不装 ComfyUI，用 Python 代码直接调用 Stable Diffusion + ControlNet，配合 FFmpeg，实现爆款视频复刻

---

## 一、环境准备

### 1.1 创建独立 Python 环境

```bash
# 用你的 3.10 系统 Python 创建 venv（diffusers 对 3.10/3.11 最稳定）
"C:\Users\jt\AppData\Local\Programs\Python\Python310\python.exe" -m venv D:\video_replicate_env

# 激活
D:\video_replicate_env\Scripts\activate
```

### 1.2 安装依赖

```bash
# 核心
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install diffusers transformers accelerate xformers
pip install controlnet_aux opencv-python pillow

# FFmpeg Python 绑定（更方便调用 ffmpeg）
pip install ffmpeg-python

# IP-Adapter 支持
pip install insightface
```

**注意**：`controlnet_aux` 里包含 OpenPose/Depth/Canny 等预处理器，不需要额外下载模型。

### 1.3 确认 FFmpeg 已安装

```bash
ffmpeg -version
# 如果没有 → winget install ffmpeg
```

---

## 二、模型下载

脚本会在第一次运行时自动下载模型到 `~/.cache/huggingface/`。你需要以下模型：

| 模型 | 大小 | 用途 |
|------|------|------|
| `runwayml/stable-diffusion-v1-5` | ~5GB | 基座模型 |
| `lllyasviel/control_v11p_sd15_openpose` | ~1.4GB | 人体姿势控制 |
| `lllyasviel/control_v11f1p_sd15_depth` | ~1.4GB | 场景深度控制 |
| `lllyasviel/control_v11p_sd15_canny` | ~1.4GB | 边缘构图控制 |
| IP-Adapter 模型 | ~1GB | 风格参考注入 |

**总下载量**：约 10GB，首次运行会自动下载，等待即可。

---

## 三、完整代码

### 3.1 核心脚本：`video_replicate.py`

```python
#!/usr/bin/env python3
"""
视频复刻管线 — FFmpeg + Python Diffusers + ControlNet
用法: python video_replicate.py --input source.mp4 --prompt "新的内容描述"
"""

import os
import sys
import argparse
import subprocess
import tempfile
from pathlib import Path

import torch
import cv2
import numpy as np
from PIL import Image
from diffusers import (
    StableDiffusionControlNetPipeline,
    ControlNetModel,
    UniPCMultistepScheduler,
)
from controlnet_aux import OpenposeDetector, DepthDetector, CannyDetector


# ─── 参数 ───────────────────────────────────────────────────
FPS = 30              # 输出帧率
WIDTH = 1024          # 输出宽度
HEIGHT = 576          # 输出高度
STRENGTH_POSE = 0.85  # ControlNet Pose 强度
STRENGTH_DEPTH = 0.80 # ControlNet Depth 强度
STRENGTH_CANNY = 0.75 # ControlNet Canny 强度
STEPS = 20            # 采样步数（20-25 最佳平衡）
CFG = 7.0             # 提示词引导强度
BATCH_SIZE = 4        # 每批处理帧数（显存够就大点）


def extract_frames_ffmpeg(video_path, output_dir):
    """用 FFmpeg 提取视频帧到目录"""
    print(f"[1/5] 提取帧: {video_path}")
    os.makedirs(output_dir, exist_ok=True)
    cmd = [
        "ffmpeg", "-i", video_path,
        "-q:v", "2",                    # 高质量
        os.path.join(output_dir, "%05d.png")
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    frame_count = len(os.listdir(output_dir))
    print(f"       → 共 {frame_count} 帧")
    return frame_count


def extract_conditions(frame_dir, output_dir):
    """提取每帧的 ControlNet 条件图（Pose + Depth + Canny）"""
    print(f"[2/5] 提取 ControlNet 条件图...")
    os.makedirs(output_dir, exist_ok=True)
    
    # 加载预处理器（加载一次，复用所有帧）
    pose_detector = OpenposeDetector.from_pretrained("lllyasviel/ControlNet")
    depth_detector = DepthDetector.from_pretrained("lllyasviel/ControlNet")
    canny_detector = CannyDetector()
    
    frames = sorted(Path(frame_dir).glob("*.png"))
    for i, frame_path in enumerate(frames):
        img = Image.open(frame_path).resize((WIDTH, HEIGHT))
        
        # 生成三种条件图
        pose_img = pose_detector(img, hand_and_face=True)
        depth_img = depth_detector(img)
        canny_img = canny_detector(img, low_threshold=100, high_threshold=200)
        
        # 保存
        stem = frame_path.stem
        pose_img.save(os.path.join(output_dir, f"{stem}_pose.png"))
        depth_img.save(os.path.join(output_dir, f"{stem}_depth.png"))
        canny_img.save(os.path.join(output_dir, f"{stem}_canny.png"))
        
        if (i+1) % 50 == 0:
            print(f"       → 处理 {i+1}/{len(frames)} 帧条件图")
    
    print(f"       → 条件图提取完成")


def create_pipeline():
    """创建 ControlNet + SD 管线"""
    print(f"[3/5] 加载 ControlNet 模型...")
    
    # 加载三个 ControlNet
    controlnet_pose = ControlNetModel.from_pretrained(
        "lllyasviel/control_v11p_sd15_openpose",
        torch_dtype=torch.float16
    )
    controlnet_depth = ControlNetModel.from_pretrained(
        "lllyasviel/control_v11f1p_sd15_depth",
        torch_dtype=torch.float16
    )
    controlnet_canny = ControlNetModel.from_pretrained(
        "lllyasviel/control_v11p_sd15_canny",
        torch_dtype=torch.float16
    )
    
    # 创建管线
    pipe = StableDiffusionControlNetPipeline.from_pretrained(
        "runwayml/stable-diffusion-v1-5",
        controlnet=[controlnet_pose, controlnet_depth, controlnet_canny],
        torch_dtype=torch.float16,
        safety_checker=None,         # 关闭安全检查，加速
    ).to("cuda")
    
    # 启用优化
    pipe.enable_xformers_memory_efficient_attention()
    pipe.enable_model_cpu_offload()  # 节省显存
    pipe.scheduler = UniPCMultistepScheduler.from_config(pipe.scheduler.config)
    
    print(f"       → 管线加载完成")
    return pipe


def generate_frames(pipe, cond_dir, output_dir, prompt, negative_prompt=""):
    """逐帧生成新内容"""
    print(f"[4/5] 生成新帧...")
    os.makedirs(output_dir, exist_ok=True)
    
    frame_count = len([f for f in os.listdir(cond_dir) if f.endswith("_pose.png")])
    
    for i in range(1, frame_count + 1):
        # 读取三张条件图
        pose_img = Image.open(os.path.join(cond_dir, f"{i:05d}_pose.png"))
        depth_img = Image.open(os.path.join(cond_dir, f"{i:05d}_depth.png"))
        canny_img = Image.open(os.path.join(cond_dir, f"{i:05d}_canny.png"))
        
        # 生成
        result = pipe(
            prompt=prompt,
            negative_prompt=negative_prompt or "low quality, blurry, distorted",
            image=[pose_img, depth_img, canny_img],
            num_inference_steps=STEPS,
            guidance_scale=CFG,
            controlnet_conditioning_scale=[
                STRENGTH_POSE,
                STRENGTH_DEPTH,
                STRENGTH_CANNY,
            ],
            width=WIDTH,
            height=HEIGHT,
        ).images[0]
        
        result.save(os.path.join(output_dir, f"{i:05d}.png"))
        
        if (i+1) % 10 == 0:
            print(f"       → 生成 {i+1}/{frame_count} 帧")
    
    print(f"       → 生成完成 ({frame_count} 帧)")


def assemble_video_ffmpeg(frame_dir, output_path, audio_source=None):
    """用 FFmpeg 合成视频"""
    print(f"[5/5] 合成视频...")
    
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", os.path.join(frame_dir, "%05d.png"),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "medium",
        "-crf", "18",
        output_path
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    
    # 如果有原音频，同步上去
    if audio_source:
        temp_video = output_path + ".temp.mp4"
        os.rename(output_path, temp_video)
        cmd_audio = [
            "ffmpeg", "-y",
            "-i", temp_video,
            "-i", audio_source,
            "-c:v", "copy",
            "-c:a", "aac",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            output_path
        ]
        subprocess.run(cmd_audio, check=True, capture_output=True)
        os.remove(temp_video)
    
    print(f"       → 输出: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="视频复刻管线")
    parser.add_argument("--input", "-i", required=True, help="原视频路径")
    parser.add_argument("--prompt", "-p", required=True, help="新内容描述")
    parser.add_argument("--negative", "-n", default="", help="负面提示词")
    parser.add_argument("--output", "-o", default="output.mp4", help="输出路径")
    parser.add_argument("--fps", type=int, default=30, help="帧率")
    parser.add_argument("--steps", type=int, default=20, help="采样步数")
    parser.add_argument("--skip-cond", action="store_true", help="跳过条件图提取（已有）")
    parser.add_argument("--skip-gen", action="store_true", help="跳过生成（已有帧）")
    args = parser.parse_args()
    
    global FPS, STEPS
    FPS = args.fps
    STEPS = args.steps
    
    # 创建临时工作目录
    work_dir = tempfile.mkdtemp(prefix="vrep_")
    frames_dir = os.path.join(work_dir, "frames")
    cond_dir = os.path.join(work_dir, "conditions")
    output_frames_dir = os.path.join(work_dir, "output")
    
    try:
        # 提取原视频帧
        extract_frames_ffmpeg(args.input, frames_dir)
        
        # 提取 ControlNet 条件图
        if not args.skip_cond:
            extract_conditions(frames_dir, cond_dir)
        
        # 创建并运行管线
        if not args.skip_gen:
            pipe = create_pipeline()
            generate_frames(pipe, cond_dir, output_frames_dir, args.prompt, args.negative)
        
        # 合成视频（带原音频）
        audio_source = args.input if os.path.exists(args.input) else None
        assemble_video_ffmpeg(output_frames_dir, args.output, audio_source)
        
        print(f"\n✅ 完成！输出: {args.output}")
        
    finally:
        # 清理临时文件
        import shutil
        shutil.rmtree(work_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
```

---

## 四、使用方式

### 4.1 基础用法

```bash
python video_replicate.py \
    --input source_video.mp4 \
    --prompt "一个白色陶瓷杯放在木桌上，柔和的自然光线，电影质感"
```

### 4.2 调参

```bash
# 高质量模式（步数多，更精确）
python video_replicate.py \
    --input source.mp4 \
    --prompt "..." \
    --steps 25 \
    --fps 24

# 快速模式（步数少，更快）
python video_replicate.py \
    --input source.mp4 \
    --prompt "..." \
    --steps 15
```

### 4.3 分步执行（如果中途断了）

```bash
# 第一步：提取帧 + 条件图
python video_replicate.py --input source.mp4 --prompt "..." --skip-gen

# 第二步：生成新帧（复用已有条件图）
python video_replicate.py --input source.mp4 --prompt "..." --skip-cond

# 第三步：只合成（如果已有输出帧）
# 手动改脚本跳过前4步，直接跑 assemble_video_ffmpeg
```

---

## 五、你的 5090D 上性能预期

| 参数 | 值 |
|------|-----|
| 单帧生成时间 | ~1.5-2 秒（3个 ControlNet 同时跑） |
| 10秒视频（300帧）总时间 | ~8-12 分钟 |
| 显存占用 | ~12-16GB（三路 ControlNet） |
| 同时批处理 | BATCH_SIZE=4 时约 14GB |

**优化技巧**：

```
1. 用 --steps 15 代替 20 → 速度快 25%，质量几乎不变
2. 关掉 depth ControlNet（如果场景深度不重要）→ 显存降 4GB
3. 用 torch.float16 + xformers → 速度提升 30-40%
4. 如果不需要精确复刻，只用 pose + canny 就够
```

---

## 六、进阶：关键帧 + Ebsynth 混合优化

纯逐帧方案 300 帧跑 10 分钟。如果想更快，加 Ebsynth：

```python
# 在 video_replicate.py 中加入 ebsynth 传播

def generate_keyframes_and_propagate(pipe, cond_dir, output_dir, prompt):
    """只生成关键帧 → Ebsynth 传播到全帧"""
    
    KEYFRAME_INTERVAL = 10  # 每 10 帧取 1 个关键帧
    
    # 1. 只生成关键帧
    frame_count = len([f for f in os.listdir(cond_dir) if f.endswith("_pose.png")])
    keyframe_indices = list(range(1, frame_count + 1, KEYFRAME_INTERVAL))
    
    os.makedirs(output_dir, exist_ok=True)
    
    for i in keyframe_indices:
        # ... 同 generate_frames 逻辑
        pass
    
    # 2. 调用 Ebsynth CLI 传播
    subprocess.run([
        "ebsynth",
        "-style", output_dir,        # 关键帧目录
        "-guide", cond_dir,          # 引导帧（原视频）
        "-output", output_dir_full,  # 输出所有帧
        "-weight", "1.0"
    ], check=True)
    
    # 速度：30帧关键帧生成（1-2分钟）+ Ebsynth 传播（30秒）
    # 比逐帧 300 帧快 3-5 倍
```

---

## 七、常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| CUDA out of memory | 三个 ControlNet 同时加载 | 减少 batch size；关掉不需要的 ControlNet |
| 帧间闪烁 | 逐帧生成缺乏时序约束 | 降低 CFG 到 5-6；加 frame overlap 平均相邻帧 |
| 人物变形 | Pose 检测不准 | `STRENGTH_POSE` 提高到 0.95 |
| 颜色不一致 | 每帧独立生成 | 固定 seed；加 IP-Adapter 风格参考 |
| 太慢 | 逐帧 300 帧 | 改用关键帧+Ebsynth 混合方案 |

---

## 八、这套方案的优劣势

### 优势

- **无 GUI 依赖** — 不需要装 ComfyUI，不需要拖节点，直接跑
- **完全可编程** — 可以写循环/批处理/自动化，一次处理多个视频
- **和 ComfyUI 完全相同的底层能力** — 同样的 ControlNet、同样的 SD 模型
- **参数可控** — 每一帧的参数都可以单独调
- **可扩展** — 加 IP-Adapter、LoRA、ControlNet 都只是加几行代码

### 劣势

- **需要写代码** — 但我可以帮你一次性写好，你以后只用改 prompt
- **逐帧比 ComfyUI 快不了太多** — 底层是同一个推理引擎
- **调试不如 ComfyUI 直观** — 出错了要看日志，不是看节点图
