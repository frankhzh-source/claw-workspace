#!/usr/bin/env python3
"""
「一文三态」自动化流水线 — v1.0

输入: 一篇 Markdown 文章
输出: 三种内容形态
  1. 口播视频脚本 (60-90秒, 用于抖音/视频号)
  2. AI 播客 (TTS 双角色音频, 用于喜马拉雅/小宇宙)
  3. PPT 视频  (PPT 幻灯片 + AI 配音, 用于 B站/视频号)

用法:
  python pipeline_multimodal.py <article.md>                    # 全量生成
  python pipeline_multimodal.py <article.md> --skip-podcast     # 跳过播客
  python pipeline_multimodal.py <article.md> --skip-video       # 跳过视频
  python pipeline_multimodal.py <article.md> --type kiwi        # 强制 KIWI 模式
"""

import os
import sys
import re
import json
import subprocess
import asyncio
import argparse
from pathlib import Path
from datetime import datetime

# ── 工具链检查 ──────────────────────────────────────────────────

def check_dependencies():
    """检查 ffmpeg / edge-tts / PIL 是否可用"""
    deps = {}
    
    # ffmpeg
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        deps["ffmpeg"] = True
    except Exception:
        deps["ffmpeg"] = False
    
    # edge-tts
    try:
        result = subprocess.run(
            [sys.executable, "-c", "import edge_tts; print('ok')"],
            capture_output=True, text=True
        )
        deps["edge_tts"] = result.stdout.strip() == "ok"
    except Exception:
        deps["edge_tts"] = False
    
    # PIL
    try:
        from PIL import Image, ImageDraw, ImageFont
        deps["pil"] = True
    except Exception:
        deps["pil"] = False
    
    return deps


# ── 文章类型检测 ──────────────────────────────────────────────────

def detect_article_type(content: str, filename: str = "") -> str:
    """检测文章属于哪个版块: kiwi / aievolution / geo"""
    fn = filename.lower()
    if "kiwi" in fn or "第" in fn and "章" in fn:
        return "kiwi"
    
    # 检查内容特征
    first_500 = content[:500].lower()
    
    if "kiwi" in first_500 or "来自2031" in first_500:
        return "kiwi"
    
    if "geo" in first_500 or "引力场" in first_500 or "ge" in first_500:
        return "geo"
    
    if "AI进化论" in content[:200] or "进化论" in content[:200]:
        return "aievolution"
    
    # 对话体检测 → kiwi
    dialogue_markers = content.count("海风：") + content.count("Kiwi：")
    total_lines = len(content.split("\n"))
    if dialogue_markers > total_lines * 0.05:
        return "kiwi"
    
    return "geo"


# ── 内容提取 ──────────────────────────────────────────────────────

def extract_dialogue_pairs(content: str) -> list[dict]:
    """从 KIWI 日记中提取对话对 — 只提取真实角色对话"""
    pairs = []
    lines = content.split("\n")
    
    # ── 格式1: 显式标记 "海风：" / "Kiwi：" ──
    has_explicit = any(
        s.strip().startswith(("海风：", "**海风：**", "Kiwi：", "**Kiwi：**"))
        for s in lines
    )
    
    if has_explicit:
        current = {"speaker": "", "text": []}
        for line in lines:
            s = line.strip()
            if re.match(r"\*\*海风[：:]\*\*\s*", s) or s.startswith("海风："):
                if current["speaker"] and current["text"]:
                    pairs.append(current)
                current = {"speaker": "海风", "text": []}
                current["text"].append(re.sub(r"\*\*海风[：:]\*\*", "", s).strip())
            elif re.match(r"\*\*Kiwi[：:]\*\*\s*", s) or s.startswith("Kiwi："):
                if current["speaker"] and current["text"]:
                    pairs.append(current)
                current = {"speaker": "Kiwi", "text": []}
                current["text"].append(re.sub(r"\*\*Kiwi[：:]\*\*", "", s).strip())
            elif current["speaker"]:
                if s and not s.startswith("#") and not s.startswith("|") and not s.startswith(">"):
                    current["text"].append(s)
        if current["speaker"] and current["text"]:
            pairs.append(current)
        return pairs
    
    # ── 格式2: 中文散文体 — 只提取 "..." 引号内的角色对话 ──
    # 找到对话区域：从第一个 "Kiwi说" 或角色对话开始
    dialogue_section_lines = []
    in_dialogue = False
    for line in lines:
        s = line.strip()
        # 开始条件：遇到纯对话行（以引号开头的角色说话）
        if (s.startswith('"') or s.startswith('\u201c')) and any(
            kw in s for kw in ["Kiwi", "说", "问", "切换", "停顿", "道", "我"]
        ):
            in_dialogue = True
        # 停止条件：遇到分隔线、结尾区块
        if in_dialogue and (s == "---" or s.startswith("**关于") or s.startswith("**作者") or s.startswith("**往期")):
            break
        if in_dialogue:
            dialogue_section_lines.append(line)
    
    if not dialogue_section_lines:
        return pairs
    
    # 提取所有 "..." 中的引语，附带上文 100 字以判断说话人
    dialogue_text = "\n".join(dialogue_section_lines)
    # 匹配中文引号 "..." 
    for m in re.finditer(r'"([^"]{8,300})"', dialogue_text):
        quote = m.group(1)
        # 跳过表格、代码、URL
        if quote.startswith("http") or quote.startswith(":---"):
            continue
        
        # 判断说话人：检查引号前 60 字
        start = max(0, m.start() - 60)
        before = dialogue_text[start:m.start()]
        
        if re.search(r'Kiwi(说|切换|问|道|补充|停顿|瞬间)', before):
            speaker = "Kiwi"
        elif re.search(r'我(说|停|愣|问|靠|拿|关|靠在|回答|心里|想)', before):
            speaker = "海风"
        else:
            # 上下文推断：前一条是谁
            speaker = pairs[-1]["speaker"] if pairs else "Kiwi"
        
        # 去引号内残留格式
        clean = quote.strip().rstrip("。，！？")
        if len(clean) < 10:
            continue
        
        # 合并同一说话人的连续发言
        if pairs and pairs[-1]["speaker"] == speaker:
            pairs[-1]["text"].append(clean)
        else:
            pairs.append({"speaker": speaker, "text": [clean]})
    
    return pairs


def extract_key_points(content: str, article_type: str = "geo") -> list[str]:
    """从文章中提取核心观点（用于口播/PPT）"""
    points = []
    lines = content.split("\n")
    
    # KIWI 日记 → 从对话中提取金句
    if article_type == "kiwi":
        pairs = extract_dialogue_pairs(content)
        for p in pairs:
            if p["speaker"] == "Kiwi":
                for t in p["text"]:
                    # 筛选有哲理/洞察的句子
                    if len(t) > 20 and not t.startswith("http"):
                        points.append(t)
        if points:
            return points[:12]
        
        # 后备：提取所有爆款引号
        all_quotes = re.findall(r'"([^"]{15,150})"', content)
        for q in all_quotes:
            if not q.startswith("http") and not q.startswith("#"):
                points.append(q)
        return points[:12]
    
    # AI进化论/GEO引力场 → 从文章结构中提取
    for line in lines:
        s = line.strip()
        # 抓 H3 标题作为观点（优先于 H2，更有信息量）
        if s.startswith("### "):
            title = re.sub(r"^###\s*", "", s)
            # 去除序号前缀如 "1.1 "、"一、"、"1. "
            title = re.sub(r'^[\d一二三四五六七八九十]+[\.\、\s]+', '', title)
            if not any(skip in title for skip in ["参考", "附录", "排除", "置信度"]):
                points.append(title)
        # 抓 H2 标题
        elif s.startswith("## ") and len(points) < 6:
            title = re.sub(r"^##\s*", "", s)
            title = re.sub(r'^[\d一二三四五六七八九十]+[\.\、\s]+', '', title)
            if not any(skip in title for skip in ["参考", "附录", "排除", "置信度", "目录", "今日AI"]):
                points.append(title)
        # 抓整行加粗的关键句
        elif s.startswith("**") and s.endswith("**") and len(s) > 20:
            points.append(s.strip("*"))
        # 抓内联加粗的关键短语 (如 "**音频对 AI 仍是半不可见格式**")
        elif len(points) < 10:
            bolds = re.findall(r'\*\*([^*]+)\*\*', s)
            for b in bolds:
                if len(b) > 10 and b not in points:
                    points.append(b)
        # 抓冒号后的结论句 (如 "核心结论：音频对 AI 仍是半不可见格式")
        elif "核心结论" in s or "关键判断" in s or "关键发现" in s:
            parts = s.split("：", 1) if "：" in s else s.split(":", 1)
            if len(parts) > 1 and len(parts[1]) > 10:
                points.append(parts[1].strip())
    
    return points[:15]


def extract_abstract(content: str) -> str:
    """提取文章摘要"""
    lines = content.split("\n")
    abstract_lines = []
    started = False
    
    for line in lines:
        s = line.strip()
        if s.startswith("> ") or s.startswith(">"):
            abstract_lines.append(s.lstrip("> "))
            started = True
        elif started and not s:
            break
    
    if not abstract_lines:
        # fallback: 取前 200 个非标题字符
        text = []
        for line in lines:
            s = line.strip()
            if s and not s.startswith("#") and not s.startswith("|") and not s.startswith("-"):
                text.append(s)
            if len(" ".join(text)) > 200:
                break
        return " ".join(text)[:300]
    
    return " ".join(abstract_lines)[:300]


# ── 口播脚本生成 ──────────────────────────────────────────────────

def generate_oral_scripts(content: str, article_type: str) -> list[dict]:
    """生成 60-90 秒口播脚本（3段）"""
    title = extract_title(content)
    points = extract_key_points(content, article_type)
    abstract = extract_abstract(content)
    
    scripts = []
    
    if article_type == "kiwi":
        # KIWI 日记 → 精选 3 段金句对话, 每段 60-90 秒
        pairs = extract_dialogue_pairs(content)
        golden_pairs = []
        for p in pairs:
            text = " ".join(p["text"])
            # 筛选金句（Kiwi 发言、包含哲理的、有一定长度）
            if p["speaker"] == "Kiwi" and len(text) > 15:
                golden_pairs.append(p)
        
        # 如果没有足够的 Kiwi 金句, 提取所有带引号的句子
        if len(golden_pairs) < 2:
            all_quotes = re.findall(r'"([^"]{20,})"', content)
            for q in all_quotes[:3]:
                golden_pairs.append({"speaker": "Kiwi", "text": [q]})
        
        for i, pair in enumerate(golden_pairs[:3]):
            text = " ".join(pair["text"])[:400]
            # 用标题/首段内容做引子
            lines = text.split("。")
            short_text = "。".join(lines[:3]) + "。"
            
            scripts.append({
                "title": f"KIWI日记 | {title[:30] if title else '今日思考'}",
                "index": i + 1,
                "script": (
                    f"📌 KIWI日记今日金句\n\n"
                    f"Kiwi说：\n"
                    f"{short_text}\n\n"
                    f"完整解读见公众号「海风老师」\n"
                    f"#AI思考 #KIWI日记 #来自2031年的善意"
                ),
                "duration_sec": min(max(len(short_text) // 3, 30), 90),  # 语速 3字/秒
                "platform": "抖音/视频号",
                "aspect_ratio": "9:16"
            })
    
    else:
        # AI进化论/GEO引力场 → 3个核心观点
        if not points:
            points = ["AI时代的核心挑战", "如何建立自己的竞争壁垒", "从现在开始行动"]
        
        for i, point in enumerate(points[:3]):
            # 用摘要或下一个观点做正文
            body = abstract[:150] if i == 0 else (points[i+3][:120] if i+3 < len(points) else "")
            
            script_lines = [
                f"📌 {title[:35] if title else '今日观点'}",
                "",
                f"核心观点 #{i+1}：{point[:60]}",
                "",
                body,
                "",
                "🔍 完整分析见公众号「海风老师」",
                f"#{'AI进化论' if article_type == 'aievolution' else 'GEO引力场'} #深度内容"
            ]
            script_text = "\n".join(line for line in script_lines if line.strip() or line == "").strip()
            scripts.append({
                "title": f"{title[:30]} | 观点{i+1}",
                "index": i + 1,
                "script": script_text,
                "duration_sec": 75,
                "platform": "抖音/视频号",
                "aspect_ratio": "9:16"
            })
    
    return scripts


# ── 播客脚本生成 ──────────────────────────────────────────────────

def generate_podcast_script(content: str, article_type: str) -> dict:
    """生成播客脚本（含角色标记和时间标注）"""
    title = extract_title(content)
    abstract = extract_abstract(content)
    points = extract_key_points(content, article_type)
    
    script = {
        "title": title or "未命名",
        "type": article_type,
        "segments": []
    }
    
    if article_type == "kiwi":
        # KIWI 日记 → 双人对话播客
        pairs = extract_dialogue_pairs(content)
        
        # 开场
        script["segments"].append({
            "speaker": "海风",
            "voice": "zh-CN-YunxiNeural",
            "text": f"大家好，欢迎收听 KIWI 观察日记。今天是{datetime.now().strftime('%Y年%m月%d日')}。"
        })
        
        # 提取文章摘要作为背景
        first_para = ""
        for line in content.split("\n"):
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("|") and len(line) > 20:
                first_para = line[:200]
                break
        
        if first_para:
            script["segments"].append({
                "speaker": "海风",
                "voice": "zh-CN-YunxiNeural",
                "text": first_para
            })
        
        used_count = 0
        for i, pair in enumerate(pairs):
            text = " ".join(pair["text"])[:250]
            if len(text) < 8:
                continue
            
            speaker = pair["speaker"]
            voice = "zh-CN-YunxiNeural" if speaker == "海风" else "zh-CN-XiaoxiaoNeural"
            
            script["segments"].append({
                "speaker": speaker,
                "voice": voice,
                "text": text
            })
            used_count += 1
            if used_count >= 16:
                break
        
        # 结尾
        script["segments"].append({
            "speaker": "海风",
            "voice": "zh-CN-YunxiNeural",
            "text": "以上是今天的 KIWI 观察日记。来自 2031 年的善意，我们明天见。关注公众号「海风老师」，获取更多深度内容。"
        })
    
    else:
        # AI进化论/GEO引力场 → 单人深度播客
        script["segments"].append({
            "speaker": "海风",
            "voice": "zh-CN-YunxiNeural",
            "text": f"大家好，我是海风。今天我们来聊一聊：{title}。"
        })
        
        for i, point in enumerate(points[:8]):
            script["segments"].append({
                "speaker": "海风",
                "voice": "zh-CN-YunxiNeural",
                "text": f"第{i+1}点：{point}。关于这一点，我的看法是——"
            })
        
        # 预告下一期
        script["segments"].append({
            "speaker": "海风",
            "voice": "zh-CN-YunxiNeural",
            "text": "感谢收听。下期我们会继续探讨这个话题。关注公众号「海风老师」，获取更多深度内容。"
        })
    
    return script


# ── PPT 幻灯片生成 ──────────────────────────────────────────────

def generate_ppt_slides(content: str, article_type: str, output_dir: Path) -> list[str]:
    """生成 PPT 风格幻灯片图片"""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("[WARN] PIL not available, skipping PPT slide generation")
        return []
    
    os.makedirs(output_dir / "slides", exist_ok=True)
    
    title = extract_title(content)
    points = extract_key_points(content, article_type)
    abstract = extract_abstract(content)
    
    # 颜色方案
    COLORS = {
        "kiwi": {"bg": "#1A1A2E", "accent": "#E94560", "text": "#EAEAEA", "sub": "#AAAAAA"},
        "geo": {"bg": "#0F1923", "accent": "#00D2FF", "text": "#EAEAEA", "sub": "#8899AA"},
        "aievolution": {"bg": "#1B1B2F", "accent": "#6C63FF", "text": "#EAEAEA", "sub": "#AAAAAA"},
    }
    c = COLORS.get(article_type, COLORS["geo"])
    
    W, H = 1920, 1080
    slides = []
    
    # 尝试使用中文字体
    font_paths = [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
    ]
    font_title = None
    font_body = None
    for fp in font_paths:
        if os.path.exists(fp):
            font_title = ImageFont.truetype(fp, 60)
            font_body = ImageFont.truetype(fp, 36)
            font_small = ImageFont.truetype(fp, 28)
            break
    
    if font_body is None:
        font_body = ImageFont.load_default()
        font_title = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    def make_slide(lines: list[tuple[str, str, tuple]], filename: str) -> str:
        """line: (text, type, color)"""
        img = Image.new("RGB", (W, H), c["bg"])
        draw = ImageDraw.Draw(img)
        
        y = 120
        for text, typ, color in lines:
            font = font_title if typ == "title" else (font_small if typ == "small" else font_body)
            
            # 简单的文字换行
            max_chars = 40 if typ == "title" else 55
            wrapped = []
            for paragraph in text.split("\n"):
                current = ""
                for ch in paragraph:
                    if len(current) >= max_chars:
                        wrapped.append(current)
                        current = ch
                    else:
                        current += ch
                if current:
                    wrapped.append(current)
            
            for line_text in wrapped:
                bbox = draw.textbbox((0, 0), line_text, font=font)
                tw = bbox[2] - bbox[0]
                x = (W - tw) // 2
                draw.text((x, y), line_text, fill=color, font=font)
                y += 60 if typ == "title" else 45
            
            y += 20  # 段落间距
        
        # 底部品牌栏
        draw.rectangle([(0, H - 80), (W, H)], fill=c["accent"])
        badge = {"kiwi": "KIWI 观察日记", "geo": "海风 · GEO引力场", "aievolution": "AI进化论"}[article_type]
        draw.text((40, H - 55), f"海风老师 | {badge}", fill="#FFFFFF", font=font_small)
        draw.text((W - 300, H - 55), "frankhzheng", fill="#FFFFFF", font=font_small)
        
        path = str(output_dir / "slides" / filename)
        img.save(path, quality=90)
        return path
    
    # 封面
    slides.append(make_slide([
        (title[:40], "title", c["text"]),
        ("", "body", c["text"]),
        (abstract[:120], "body", c["sub"]),
        ("", "body", c["text"]),
        ({"kiwi": "来自2031年的善意", "geo": "让内容被AI看见", "aievolution": "深度思考 · AI未来"}[article_type], "small", c["accent"]),
    ], "01_cover.png"))
    
    # 内容页（每页 2-3 个观点）
    for i in range(0, min(len(points), 12), 3):
        batch = points[i:i+3]
        lines = []
        for j, p in enumerate(batch):
            lines.append((f"0{i//3+1}. {p[:50]}", "body", c["text"]))
            if j < len(batch) - 1:
                lines.append(("", "body", c["text"]))
        
        slides.append(make_slide(lines, f"0{i//3+2:02d}_content.png"))
    
    # 结尾
    slides.append(make_slide([
        ("感谢阅读", "title", c["text"]),
        ("", "body", c["text"]),
        ("关注公众号「海风老师」", "body", c["text"]),
        ("微信：frankhzheng", "body", c["sub"]),
        ("", "body", c["text"]),
        ("内容资产库：github.com/frankhzh-source/hf-ai-articles", "small", c["accent"]),
    ], "99_end.png"))
    
    return slides


# ── TTS 音频生成 ──────────────────────────────────────────────────

async def generate_podcast_audio(podcast_script: dict, output_dir: Path) -> str:
    """使用 edge-tts 生成播客 MP3"""
    import edge_tts
    
    temp_dir = output_dir / "tts_temp"
    os.makedirs(temp_dir, exist_ok=True)
    audio_files = []
    
    for i, seg in enumerate(podcast_script["segments"]):
        text = seg["text"]
        voice = seg.get("voice", "zh-CN-YunxiNeural")
        
        if len(text) < 5 or len(text) > 500:
            if len(text) > 500:
                print(f"  [SKIP] Segment {i} too long ({len(text)} chars), split manually recommended")
            continue
        
        out_file = temp_dir / f"seg_{i:03d}.mp3"
        
        try:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(str(out_file))
            audio_files.append(str(out_file))
        except Exception as e:
            print(f"  [WARN] TTS segment {i} failed: {str(e)[:80]}")
    
    if not audio_files:
        print("[ERROR] No TTS audio generated")
        return ""
    
    # 合并音频片段
    concat_list = output_dir / "segments.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for af in audio_files:
            f.write(f"file '{af}'\n")
    
    output_mp3 = output_dir / "podcast.mp3"
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_list), "-c", "copy", str(output_mp3)
    ], capture_output=True)
    
    # 清理临时文件
    concat_list.unlink(missing_ok=True)
    for af in audio_files:
        Path(af).unlink(missing_ok=True)
    
    return str(output_mp3)


# ── PPT 视频合成 ──────────────────────────────────────────────────

def combine_slides_to_video(slides: list[str], audio_path: str, output_dir: Path) -> str:
    """将 PPT 幻灯片 + 音频合成为视频"""
    if not slides:
        return ""
    
    # 计算每张幻灯片的时长
    import subprocess
    
    # 获取音频总时长
    result = subprocess.run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", audio_path
    ], capture_output=True, text=True)
    
    try:
        total_duration = float(result.stdout.strip())
    except Exception:
        total_duration = 60
    
    n_slides = len(slides)
    duration_per_slide = max(total_duration / n_slides, 3)  # 最少 3 秒
    
    # 为每张幻灯片生成视频片段
    temp_dir = output_dir / "video_temp"
    os.makedirs(temp_dir, exist_ok=True)
    clip_files = []
    
    for i, slide in enumerate(slides):
        clip_file = temp_dir / f"clip_{i:03d}.mp4"
        subprocess.run([
            "ffmpeg", "-y",
            "-loop", "1", "-i", slide,
            "-t", str(duration_per_slide),
            "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-pix_fmt", "yuv420p",
            str(clip_file)
        ], capture_output=True)
        clip_files.append(str(clip_file))
    
    # 合并视频片段
    concat_list = temp_dir / "concat.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for cf in clip_files:
            f.write(f"file '{cf}'\n")
    
    video_silent = temp_dir / "video_silent.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_list), "-c", "copy", str(video_silent)
    ], capture_output=True)
    
    # 合成音频
    output_video = output_dir / "ppt_video.mp4"
    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(video_silent),
        "-i", audio_path,
        "-c:v", "copy", "-c:a", "aac", "-shortest",
        str(output_video)
    ], capture_output=True)
    
    # 清理
    concat_list.unlink(missing_ok=True)
    
    return str(output_video)


# ── 辅助 ──────────────────────────────────────────────────────────

def extract_title(content: str) -> str:
    """提取文章主标题"""
    for line in content.split("\n"):
        s = line.strip()
        if s.startswith("# ") and not s.startswith("## "):
            return s[2:].strip()
        if s.startswith("## "):
            return s[3:].strip()
    return ""


def slugify(text: str) -> str:
    """生成文件名安全的标识"""
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s]+', '_', text)
    return text[:40]


# ── 主流水线 ──────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(description="一文三态自动化流水线")
    parser.add_argument("article", help="Markdown 文章路径")
    parser.add_argument("--type", choices=["kiwi", "geo", "aievolution"], help="文章类型")
    parser.add_argument("--skip-podcast", action="store_true", help="跳过播客生成")
    parser.add_argument("--skip-video", action="store_true", help="跳过 PPT 视频生成")
    parser.add_argument("--output", "-o", default="./output_multimodal", help="输出目录")
    args = parser.parse_args()
    
    article_path = Path(args.article)
    if not article_path.exists():
        print(f"[ERROR] 文件不存在: {article_path}")
        sys.exit(1)
    
    # 检查依赖
    deps = check_dependencies()
    if not deps["ffmpeg"]:
        print("[ERROR] ffmpeg 未安装")
        sys.exit(1)
    if not deps["edge_tts"] and not args.skip_podcast:
        print("[WARN] edge-tts 未安装, 将跳过播客音频生成")
    if not deps["pil"]:
        print("[WARN] PIL 未安装, 将跳过 PPT 幻灯片生成")
    
    # 读取文章
    content = article_path.read_text(encoding="utf-8")
    article_type = args.type or detect_article_type(content, article_path.name)
    title = extract_title(content)
    slug = slugify(title) or f"article_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print(f"\n{'='*60}")
    print(f"  一文三态流水线 v1.0")
    print(f"  文章: {title[:50]}")
    print(f"  类型: {article_type}")
    print(f"{'='*60}\n")
    
    # 输出目录
    output_dir = Path(args.output) / slug
    os.makedirs(output_dir, exist_ok=True)
    
    # ── 态 1: 口播视频脚本 ──
    print("[1/3] 生成口播视频脚本...")
    oral_scripts = generate_oral_scripts(content, article_type)
    oral_dir = output_dir / "oral_scripts"
    os.makedirs(oral_dir, exist_ok=True)
    
    for s in oral_scripts:
        script_file = oral_dir / f"oral_{s['index']:02d}.txt"
        script_file.write_text(s["script"], encoding="utf-8")
    
    oral_index = oral_dir / "README.md"
    index_lines = []
    for i, s in enumerate(oral_scripts):
        index_lines += [
            f"## 口播脚本 {i+1}",
            f"- 时长: {s['duration_sec']}秒",
            f"- 平台: {s['platform']}",
            f"- 比例: {s['aspect_ratio']}",
            f"- 文件: oral_{i+1:02d}.txt",
            ""
        ]
    oral_index.write_text("\n".join(index_lines), encoding="utf-8")
    
    print(f"  ✅ 生成 {len(oral_scripts)} 段口播脚本 → {oral_dir}")
    
    # ── 态 2: AI 播客 ──
    if not args.skip_podcast:
        print("[2/3] 生成播客脚本 + 音频...")
        podcast_script = generate_podcast_script(content, article_type)
        
        # 保存播客脚本
        podcast_dir = output_dir / "podcast"
        os.makedirs(podcast_dir, exist_ok=True)
        
        script_text = []
        for seg in podcast_script["segments"]:
            speaker = seg["speaker"]
            text = seg["text"]
            script_text.append(f"【{speaker}】{text}")
        
        (podcast_dir / "script.txt").write_text(
            "\n\n".join(script_text), encoding="utf-8"
        )
        
        # 生成音频
        if deps["edge_tts"]:
            try:
                audio_path = await generate_podcast_audio(podcast_script, podcast_dir)
                if audio_path:
                    print(f"  ✅ 播客音频 → {audio_path}")
                else:
                    print(f"  ⚠️ 音频生成失败, 脚本已保存")
            except Exception as e:
                print(f"  ⚠️ TTS 异常: {e}, 脚本已保存")
        else:
            print(f"  ⚠️ edge-tts 不可用, 仅保存脚本")
    else:
        print("[2/3] 跳过播客生成")
        podcast_script = None
    
    # ── 态 3: PPT 视频 ──
    if not args.skip_video and deps["pil"]:
        print("[3/3] 生成 PPT 幻灯片 + 视频...")
        ppt_dir = output_dir / "ppt_video"
        os.makedirs(ppt_dir, exist_ok=True)
        
        slides = generate_ppt_slides(content, article_type, ppt_dir)
        print(f"  ✅ 生成 {len(slides)} 张幻灯片")
        
        # 如果有播客音频, 合成视频
        podcast_audio = output_dir / "podcast" / "podcast.mp3"
        if podcast_audio.exists():
            video_path = combine_slides_to_video(slides, str(podcast_audio), ppt_dir)
            if video_path:
                print(f"  ✅ PPT 视频 → {video_path}")
    elif args.skip_video:
        print("[3/3] 跳过 PPT 视频")
    else:
        print("[3/3] PIL 不可用, 跳过 PPT 视频")
    
    # ── 输出汇总 ──
    print(f"\n{'='*60}")
    print(f"  输出目录: {output_dir}")
    print(f"  文件清单:")
    
    all_files = list(output_dir.rglob("*"))
    for f in sorted(all_files):
        if f.is_file() and f.suffix in [".txt", ".mp3", ".mp4", ".png"]:
            size = f.stat().st_size
            size_str = f"{size/1024:.1f}KB" if size < 1024*1024 else f"{size/1024/1024:.1f}MB"
            print(f"    {f.relative_to(output_dir)} ({size_str})")
    
    print(f"{'='*60}\n")
    
    # 保存配置摘要
    summary = {
        "title": title,
        "type": article_type,
        "generated_at": datetime.now().isoformat(),
        "output_dir": str(output_dir),
        "oral_scripts": len(oral_scripts),
        "podcast_generated": podcast_script is not None,
        "ppt_slides": len(slides) if "slides" in dir() else 0,
    }
    (output_dir / "_pipeline_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    asyncio.run(main())
