# 视频复刻方案执行设计：FFmpeg + LibTV 参考图生成

**2026-07-06 | 目标：爆款视频结构级复刻 | 工具链：FFmpeg + LibTV + Python + LMM**

---

## 一、工具组全景

```
┌─────────────────────────────────────────────────────────────────────┐
│                   工具组 ▸ 各司其职                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  FFmpeg ──── 拆解/合成层                                           │
│    ├─ 场景检测 & 关键帧提取                                          │
│    ├─ 逐帧导出 & 按场景分组                                          │
│    ├─ 音频分离（人声/BGM/音效）                                      │
│    └─ 最终合成（画面+音频+转场+调色）                                 │
│                                                                    │
│  LibTV ──── 参考图生成 & 画布编排层                                  │
│    ├─ image 节点 + 参考图（图生图换人物/场景）                         │
│    ├─ image shortcut（风格迁移/光影校正/九宫格多角度）                  │
│    ├─ video 节点（图生视频/参考视频→视频）                             │
│    ├─ video-clip 节点（时间线合成，精确剪辑拼接）                      │
│    └─ script + storyboard（分镜脚本→分镜图生成）                      │
│                                                                    │
│  Python (可选) ── 精确控制层                                         │
│    ├─ LMM 多模态分析（场景识别/构图提取/运动分析）                      │
│    ├─ OpenCV 光流分析（camera motion 参数提取）                       │
│    ├─ ControlNet 骨架提取（OpenPose/Depth/Canny）                     │
│    └─ Ebsynth 光流传播（质量+效率均衡方案）                            │
│                                                                    │
│  本地存储 ── 资产管理层                                              │
│    └─ 分层文件树（分析/源/场景/音频/合成）                             │
│                                                                    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 二、各工具的选择依据

### 为什么用 FFmpeg + LibTV 而非纯代码方案

| 维度 | FFmpeg + LibTV | 纯 Diffusers 代码 | Ebsynth |
|------|---------------|-------------------|---------|
| **人物/场景替换精确度** | ⭐⭐⭐⭐⭐ 参考图生图 | ⭐⭐⭐⭐⭐ ControlNet | ⭐⭐⭐ 只传播不替换 |
| **操作可视化** | ⭐⭐⭐⭐⭐ 画布可见 | ⭐⭐ 代码不可视 | ⭐⭐⭐ 需额外工具 |
| **批量效率** | ⭐⭐⭐⭐ 半自动 | ⭐⭐⭐⭐⭐ 全自动 | ⭐⭐⭐⭐⭐ 最快 |
| **人物一致性** | ⭐⭐⭐⭐⭐ 参考图绑定 | ⭐⭐⭐⭐⭐ LoRA | ⭐⭐ 依赖初始帧 |
| **可调性** | ⭐⭐⭐⭐⭐ 画布改参数 | ⭐⭐⭐ 改代码 | ⭐⭐ 调参有限 |

**结论：FFmpeg + LibTV 组合在「人物/场景替换」这个核心诉求上，精确度最高、可调性最强。** 如果后续需要大规模批量，再在 Python 层补 ControlNet + Ebsynth 脚本。

---

## 三、完整执行流程

### Phase 0：分析 ▸ 工具：LMM + FFmpeg

```
原视频                       →  分析产物
  │
  ├─ FFmpeg scene detect     →  pacing.json（镜头切分表）
  │   ffmpeg -i src.mp4 -filter:v "select='gt(scene,0.3)',showinfo" -vsync v2 /dev/null
  │
  ├─ LMM（GPT-4o/Claude）    →  composition.json
  │   输入：每个镜头的首帧 + 中间帧 + 末帧
  │   输出：构图类型 / 主体位置 / 色调 / 运镜描述
  │
  └─ FFmpeg 音频提取         →  audio_map.json
      ffmpeg -i src.mp4 -vn -acodec copy audio/audio_full.aac
```

### Phase 1：拆解 ▸ 工具：FFmpeg

```
原视频
  │
  ├─ 逐帧导出
  │   ffmpeg -i src.mp4 -q:v 2 1_source/source_frames/%05d.png
  │
  ├─ 按 Phase 0 的节奏表分场景
  │   scene_001/ → 镜头1所有帧
  │   scene_002/ → 镜头2所有帧
  │
  ├─ 每个场景选关键帧
  │   ├─ keyframe_start.png    → 起始构图
  │   ├─ keyframe_mid.png      → 运动过程中标志性帧
  │   ├─ keyframe_end.png      → 结束构图
  │   └─ ref_person.png        → 人物参考（最清晰正脸/侧脸）
  │
  └─ 音频分离
      demucs --two-stems=vocals src.mp4  →  vocals.wav + no_vocals.wav
```

### Phase 2：资产准备 ▸ 工具：LibTV（核心）

**这是你设计的核心环节——用 LibTV 的参考图生成功能，替换人物和场景。**

#### 2a：参考图上传

```bash
# 项目绑定
libtv project use <画布UUID>

# 上传原场景关键帧作为参考图资源节点
libtv upload "原场景A_参考图" -t image --resource ./scene_001/ref_person.png

# 上传新人物参考图
libtv upload "新人物_正面" -t image --resource ./new_person_front.png

# 上传新场景参考图
libtv upload "新场景_室内" -t image --resource ./new_scene_interior.png
```

#### 2b：用 LibTV 图生图替换人物

```bash
# 方案一：单节点参考图生图（人物替换）
# 将新人物参考图 + 原场景骨架 → 生成新关键帧
libtv node create "场景A_新人物帧" -t image \
  --prompt "新人物在场景中保持原构图" \
  --set "model=LibNano Pro" \
  --set ratio=16:9 \
  --set quality=2K \
  --left "原场景A_参考图" \
  --left "新人物_正面"

# 方案二：使用 image shortcut 做风格迁移
# 先创建一个 image 节点连参考图
libtv node create "场景A_基础帧" -t image \
  --set ratio=16:9 \
  --set quality=2K \
  --left "原场景A_参考图"
# 然后对已有 image 节点执行 Slash 指令
libtv image shortcut cinematic_lighting_correction -n "场景A_基础帧"
```

#### 2c：多角度参考图生成

```
场景A（正面特写）      →  ref=新人物正面照    → 图生图
场景B（侧面中景）      →  ref=新人物侧面照    → 图生图
场景C（全身远景）      →  ref=新人物全身照    → 图生图

如果只有一张正面照，可以先在 LibTV 里生成多角度版本：
  libtv image shortcut "多机位九宫格" -n "新人物_正面"
  → 自动生成正/侧/背/斜等多个角度
```

#### 2d：场景替换流程

```
L1 — 纯替换背景
  原帧 → 抠出主体 → 用 LibTV 生成新背景 → 合成
  操作：
    libtv node create "新背景" -t image \
      --prompt "现代极简室内，浅色调" \
      --left "原场景_关键帧"

L2 — 保留结构换风格
  原帧 → ControlNet Canny 锁定构图 → 改 prompt 生成
  操作：
    libtv node create "新风格帧" -t image \
      --prompt "赛博朋克风格，霓虹灯" \
      --left "原场景_关键帧"

L3 — 完全替换（人物+场景都换）
  原帧 → 背景补全 → 新人物合成
  分两步：
    libtv node create "新背景_无人物" -t image \
      --prompt "空场景，室内，无人" --left "原场景_关键帧"
    libtv node create "合成帧" -t image \
      --prompt "新人物放在场景中" \
      --left "新背景_无人物" \
      --left "新人物_全身"
```

### Phase 3：音频制作 ▸ 工具：FFmpeg + LibTV

```
原音频分离产物：
  ├─ vocals.wav       → 换人声 → TTS / 真人配音
  ├─ no_vocals.wav    → 新BGM → 对齐原BGM节奏结构
  └─ sfx/              → 音效 → 保留时间点，可选换音色

新音频在 LibTV 上作为 audio 节点上传：
  libtv upload "新配音" -t audio --resource ./3_audio/voiceover_new.mp3
  libtv upload "新BGM" -t audio --resource ./3_audio/bgm_new.mp3
```

### Phase 4：合成 ▸ 工具：LibTV video-clip + FFmpeg

```
第一步：在 LibTV 画布上用 video-clip 节点做时间线编排

video-clip 节点的工作方式：
  ├─ upstream video/audio 节点通过连线（--left）连接到 video-clip
  ├─ clipTimelineData 定义时间线：每个片段在时间轴上的位置和时长
  └─ --run 触发合成

操作过程：
  1. 将每个场景生成的帧序列合成 video 片段
  2. 上传所有 video 片段到 LibTV 画布
  3. 创建 video-clip 节点
  4. 用 --left 将所有 video/audio 节点连到 video-clip
  5. 用 -u clipTimelineData=... 设置精确的时间线
  6. --run 出片

第二步：FFmpeg 定版调色 + 目标格式输出
  ffmpeg -i source.mp4 -vf "eq=brightness=0.02:contrast=1.1:saturation=1.1" \
         -c:v libx264 -preset slow -crf 18 \
         -c:a aac -b:a 192k output_final.mp4
```

---

## 四、拆解后的画面和音频放哪里

### 资产树结构

```
<project_name>/
│
├── 0_analysis/                  ← Phase 0 分析产物
│   ├── pacing.json              → 镜头切分表
│   ├── composition.json         → 构图/色调/运镜分析
│   └── audio_map.json           → 音频结构（BGM节拍/人声区间/音效时间点）
│
├── 1_source/                    ← 原视频 + 原始帧
│   ├── source.mp4               → 原视频文件
│   ├── source_frames/           → FFmpeg 导出的所有帧
│   │   ├── 00001.png
│   │   └── 000NN.png
│   └── audio/                   → 分离后的音频文件
│       ├── audio_full.aac       → 原始完整音频
│       ├── vocals.wav           → 人声轨
│       ├── no_vocals.wav        → BGM+音效轨
│       └── sfx_*.wav            → 独立音效文件
│
├── 2_scenes/                    ← 按场景分组的帧 + 关键帧
│   ├── scene_001/               → 场景1（0-2.3秒）
│   │   ├── frames/              → 该场景所有帧（软链或拷贝）
│   │   ├── keyframe_start.png   → 起始关键帧
│   │   ├── keyframe_mid.png     → 中间关键帧
│   │   ├── keyframe_end.png     → 结束关键帧
│   │   ├── ref_person.png       → 人物参考（最清晰）
│   │   ├── ref_scene.png        → 场景参考
│   │   └── cond_pose.png        → 骨架条件图（OpenPose 输出）
│   ├── scene_002/
│   │   └── ...
│   └── scene_003/
│
├── 3_generated/                 ← LibTV / AI 生成的新帧
│   ├── scene_001/               → 场景1 生成的新帧
│   │   ├── new_keyframe_001.png
│   │   ├── new_keyframe_002.png
│   │   └── all_frames/          → Ebsynth 传播后的全帧
│   ├── scene_002/
│   └── scene_003/
│
├── 4_audio_new/                 ← 新音频资产
│   ├── voiceover_new.mp3        → 新配音
│   ├── bgm_new.mp3              → 新BGM
│   └── sfx_new/                 → 新音效（如需替换）
│
├── 5_composite/                 ← 合成 + 最终输出
│   ├── clips/                   → 每场景合成的短片段
│   ├── color_graded/            → 调色后的帧
│   └── final_output.mp4         → 最终成品
│
└── libtv_assets/                ← LibTV 上传的节点缓存（本地映射）
    ├── uploads/                 → 上传到 LibTV 的本地文件副本
    └── generated_downloads/     → 从 LibTV 下载的生成产物
```

> **为什么这样组织？**
> - `0_analysis/` 和 `1_source/` 只读，不改不删（断点可重来）
> - `2_scenes/` 是手工精选的关键帧 + 条件图（人的判断放在这里）
> - `3_generated/` 是 AI 生成结果，可随时清掉重跑
> - `4_audio_new/` 独立于视频资产，可替换版本
> - `5_composite/` 管最终产物，不会污染中间文件

---

## 五、LibTV 参考图生成的具体操作

### 核心命令链

```
# === 前提：登录 + 绑定画布 ===
libtv login web
libtv project use <画布UUID>

# === Step 1：上传参考图 ===
libtv upload "原场景-镜头1" -t image --resource ./scene_001/keyframe_start.png
libtv upload "原场景-人物参考" -t image --resource ./scene_001/ref_person.png
libtv upload "新人物-正面" -t image --resource ./assets/new_person.png

# === Step 2：图生图——换人物 ===
libtv node create "新版本-镜头1" -t image \
  --prompt "新人物穿着日常服装，在原场景中，自然表情，站姿" \
  --set "model=LibNano Pro"  \
  --set ratio=9:16 \
  --set quality=2K \
  --left "原场景-镜头1" \
  --left "新人物-正面"

# === Step 3：下载生成结果 ===
# LibTV 生成完成后，用 libtv node 查看节点数据获取 url
libtv node "新版本-镜头1"
# 从输出中取出 url，下载到本地
curl -o ./3_generated/scene_001/new_keyframe_001.png <url>

# === Step 4：批量 ===
# 对每个场景重复 Step 1-3，不同场景用不同的参考图
# 如果需要快速风格化处理，可以加 shortcut
libtv image shortcut "电影级光影校正" -n "新版本-镜头1"
```

### LibTV 能调用的图片生成模型（典型）

通过 `libtv model search --type image` 可以查看所有可用的图片模型。典型模型包括：

- **LibNano Pro** — 高性能图生图，适合人物/场景替换
- **Nebula Ultra** — 高质量视觉生成
- **Seedream 4.0** — 中文场景优化

每个模型的 `modeType` 决定了它支持的参考图模式（文生图 / 图生图 / 多参考图等）。

### 更灵活的方案：LMM + 脚本调度

```
LMM 分析原视频 → 输出每场景的结构化描述 →
  → Python 脚本自动组织 libtv 命令
  → 批量生成所有场景的关键帧
  → 人工审核挑选最好的
  → 进入合成阶段

这样 LMM 负责"看懂"，LibTV 负责"生成"，
你负责"判断"——三层分工，各司其职。
```

---

## 六、总体对比：这条路线 vs 其他方案

| 维度 | FFmpeg + LibTV | 纯 Diffusers 代码 | ComfyUI 逐帧 |
|------|---------------|-------------------|-------------|
| **人物/场景替换** | ✅ 参考图生图，精确可控 | ✅ ControlNet 精确 | ✅ ControlNet 精确 |
| **操作门槛** | 🟡 中等（CLI命令） | 🔴 需写代码 | 🟢 拖节点即可 |
| **可视化反馈** | ✅ 画布可见 | ❌ 不可见 | ✅ GUI可见 |
| **批量处理** | 🟡 半自动 | ✅ 全自动脚本 | 🟡 需插件 |
| **帧间一致性** | 🟡 逐帧差异 | 🟡 逐帧差异 | 🟡 逐帧差异 |
| **本地算力消耗** | 🟢 低（LibTV云端） | 🔴 高（全本地） | 🔴 高（全本地） |
| **合成能力** | ✅ video-clip 精确剪辑 | ❌ 需FFmpeg拼接 | ❌ 需外部工具 |
| **音频处理** | ✅ 画布内音频节点 | ❌ 需外部工具 | ❌ 需外部工具 |

**核心优势总结**：

```
FFmpeg + LibTV = 你告诉 LibTV "参考这张图，生成" 
                + 不用本地 GPU（LibTV 云端算）
                + 画布上能看到所有素材和连接关系
                + video-clip 做时间线剪辑很自然

这个方案特别适合：
  ✅ 你不是大批量量产（每天几条）
  ✅ 对人物/场景替换精度要求高
  ✅ 想要可视化编辑但不想要 ComfyUI
  ✅ 不想绑在本地 GPU 上
```

---

## 七、执行建议

### 一条视频的操作流程（推荐顺序）

```
1️⃣ FFmpeg 场景检测 → 获取镜头切分
   （1分钟）
   
2️⃣ 每个镜头挑关键帧 + 参考图（你判断）
   （5分钟 / 10场景）
   
3️⃣ 在 LibTV 上：上传参考图 → 图生图换人物/场景
   （10-20分钟 / 10场景）
   
4️⃣ 挑选最好的生成结果，下载到本地
   （5分钟）
   
5️⃣ 补中间帧（Ebsynth 传播或逐帧生成）
   （视工具而定）
   
6️⃣ 替换音频（人声/BGM/音效）
   （10分钟）
   
7️⃣ LibTV video-clip 时间线编排 → 合成
   （5分钟）
   
8️⃣ FFmpeg 定版调色输出
   （2分钟）
```

**一条 15-30 秒爆款视频，总耗时约 40-50 分钟**（不含模型生成排队时间）。其中你的**人工判断时间约 10 分钟**，其余是工具执行时间。

### 用 LibTV 做参考图生成的关键要点

1. **每场景独立参考** — 不同场景用不同参考图，不要一张图通吃
2. **同一场景内多角度** — 如果场景有运镜，用 `image shortcut 九宫格` 先生成多角度，再分别对应
3. **人物一致性** — 如果同一人物出现在多个场景，先用 LibTV 的 script 节点写好描述，再 `libtv script storyboard` 生成一致的版本
4. **参考图要清晰** — 原视频关键帧尽量选画面最清晰的帧，模糊帧生成的参考帧效果会差
5. **最终合成用 video-clip** — 比 FFmpeg 手写拼接更精确，支持裁剪/分割/音量调节
