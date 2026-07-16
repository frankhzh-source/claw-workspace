#!/usr/bin/env python3
"""Convert pipeline architecture doc to Feishu XML and append."""

import subprocess

DOC_ID = "L7KFdNez5oMrPJx1VrNcBTC9nsd"

def append_content(xml_content, label=""):
    cmd = [
        "lark-cli", "docs", "+update", "--api-version", "v2",
        "--doc", DOC_ID, "--command", "append", "--content", xml_content
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"FAIL [{label}]: {result.stderr[:200]}")
        return False
    print(f"OK [{label}]: {len(xml_content)} chars")
    return True

# Batch 1: Intro + 方案评审
batch1 = "\n".join([
    '<callout emoji="clapperboard" background-color="light-blue">身份：视频剪辑大师 / AI FDE / AI 架构师 | 对象：海风老师 | 2026-07-06</callout>',
    '<hr/>',
    '<h1>爆款视频复刻管线：架构设计与流程优化</h1>',
    '<h2>一、你的方案评审</h2>',
    '<p>你提的工作流骨架是正确的，但在生产环境中跑会有几个洞。我以三层身份逐层补充。</p>',
    '<h3>你已有的</h3>',
    '<pre lang="text">① 拆解 → ② 关键帧 → ③ 图生图替换 → ④ 音频处理 → ⑤ 合成</pre>',
    '<h3>漏了什么</h3>',
    '<p>三层视角交叉检出的缺失点：</p>',
    '<pre lang="text">视频剪辑大师视角\n  ├─ 缺：剪辑节奏解构（每个镜头的精确时长和切点）\n  ├─ 缺：转场分析（不仅是切点，还有转场类型/时长/缓动曲线）\n  ├─ 缺：运动曲线提取（镜头推拉摇移的缓入缓出参数）\n  ├─ 缺：色彩分级提取（每个场景独立的LUT）\n  └─ 缺：声画同步点（音效与画面的对应关系）\n\nAI FDE 视角\n  ├─ 缺：一致性控制策略（关键帧之间的人物/场景外观如何保证不漂移）\n  ├─ 缺：光流对齐（替换人物后，新人物身上的光照要匹配原场景的光照方向）\n  ├─ 缺：背景补全（抠掉原人物后，背景空洞如何修复）\n  ├─ 缺：分辨率梯队（不同阶段用不同分辨率）\n  └─ 缺：种子锁定策略（每帧用固定seed减少闪烁）\n\nAI 架构师视角\n  ├─ 缺：管线状态机（每步完成后有明确的验收标准才进下一步）\n  ├─ 缺：失败回退机制（某步生成失败了，怎么回退重试而不重跑全量）\n  ├─ 缺：资产树规范（文件结构怎么组织）\n  ├─ 缺：并行化空间（哪些步骤可以并行跑）\n  └─ 缺：增量能力（上次跑过的不重跑，断点续传）</pre>',
])

# Batch 2: 修正后的完整管线 (总图 + Phase 0)
batch2 = "\n".join([
    '<h2>二、修正后的完整管线</h2>',
    '<h3>2.1 总图</h3>',
    '<pre lang="text">┌──────────────────────────────────────────────────────────────────────────┐\n│                        爆款视频复刻全管线                                 │\n│                          （ 五阶段 · 十一步 ）                            │\n└──────────────────────────────────────────────────────────────────────────┘\n\nPhase 0：分析\n  ├─ Step 0.1 节奏分析    → 场景切分 + 每个镜头时长 + 剪辑模式识别\n  ├─ Step 0.2 运动分析    → 每个镜头的 camera motion 曲线 + 主体 motion path\n  ├─ Step 0.3 调色分析    → 每个场景的色板/LUT 提取\n  └─ Step 0.4 音频分析    → BGM 结构 + 人声区间 + 音效时间点 + 声画同步点\n      ↓\nPhase 1：拆解\n  ├─ Step 1.1 画面拆解    → FFmpeg 逐帧 + 按场景分组 + 每场景选关键帧\n  └─ Step 1.2 音频拆解    → 人声轨 / BGM / 音效 分离\n      ↓\nPhase 2：资产准备\n  ├─ Step 2.1 人物替换    → 参考图 → IP-Adapter/InstantID → 每场景多角度生成\n  ├─ Step 2.2 场景替换    → 原场景背景补全 → 新场景生成 → 前后景合成\n  ├─ Step 2.3 光照匹配    → 根据原场景光照方向/强度，校正新元素的 shading\n  └─ Step 2.4 风格统一    → 调色 / 颗粒 / 景深匹配\n      ↓\nPhase 3：音频制作\n  ├─ Step 3.1 人声替换    → 配音 / TTS / 原声保留\n  ├─ Step 3.2 BGM 替换    → 选曲 + 对齐原 BGM 的结构\n  └─ Step 3.3 音效移植    → 原音效时间点不变，替换音色或保留\n      ↓\nPhase 4：合成\n  ├─ Step 4.1 画面合成    → 新画面 + 原结构时间线\n  ├─ Step 4.2 音频混音    → 人声 + BGM + 音效 混音+母带\n  ├─ Step 4.3 定版调色    → 全片统一色板\n  └─ Step 4.4 输出         → 目标平台格式参数</pre>',
    '<hr/>',
    '<h3>2.2 Phase 0：分析（最重要阶段）</h3>',
    '<p>这是方案里缺失最严重的环节。没有 Phase 0，后面的"复刻"只是凭感觉做。</p>',
    '<h3>Step 0.1：节奏分析</h3>',
    '<pre lang="text">原视频\n  │\n  ├─ FFmpeg scene detect → 输出所有切点\n  │   ffmpeg -i source.mp4 -filter:v "select=\'gt(scene,0.3)\',showinfo" -vsync v2 frames/%05d.png\n  │   输出：镜头1 (0-2.3s) | 镜头2 (2.3-5.1s) | 镜头3 (5.1-8.7s) ...\n  │\n  ├─ 多模态 AI 分析每个镜头的类型\n  │   "镜头1：特写-产品展示-固定机位"\n  │   "镜头2：中景-人物说话-缓慢推进"\n  │\n  └─ 输出：剪辑节奏表\n       场景编号 | 起止时间 | 时长 | 景别 | 镜头类型\n       ────────────────────────────────────────────\n       1        | 0-2.3s  | 2.3s | 特写 | 固定\n       2        | 2.3-5.1 | 2.8s | 中景 | 缓慢推</pre>',
    '<h3>Step 0.2：运动分析</h3>',
    '<p>每个镜头的 camera motion 要量化，不能靠感觉：</p>',
    '<pre lang="text">  ├─ 镜头固定 → 参数: is_static=true\n  ├─ 镜头推进 → 参数: zoom_start=1.0, zoom_end=1.3, ease=in_out\n  ├─ 镜头平移 → 参数: pan_start=(x1,y1), pan_end=(x2,y2), ease=linear\n  ├─ 镜头跟拍 → 参数: track_object=true, object_bbox=每帧坐标\n  └─ 手持晃动 → 参数: shake_intensity=0.3, shake_frequency=中\n\n提取方法：用 OpenCV 的光流分析 + 关键点追踪</pre>',
    '<h3>Step 0.3：调色分析</h3>',
    '<p>每个场景提取独立 LUT（Look-Up Table）：</p>',
    '<pre lang="text">  ├─ 主色调 → hex: #2B5EA7\n  ├─ 对比度曲线 → 阴影/中间调/高光的函数曲线\n  ├─ 色温 → 5000K / 7000K / 自定义\n  └─ 颗粒/噪点 → 强度+大小\n\n复刻时：新画面先调色对齐原场景的 LUT</pre>',
])

# Batch 3: Phase 0 continued + Phase 1
batch3 = "\n".join([
    '<h3>Step 0.4：音频分析</h3>',
    '<p>音频是爆款视频的隐藏骨架，往往比画面更重要。</p>',
    '<pre lang="text">  ├─ BGM 结构分析\n  │   前奏(0-3s) → 主歌(3-15s) → 副歌(15-25s) → 结尾(25-30s)\n  │   BPM 检测: 128bpm\n  │   关键节奏点: 每个鼓点的精确时间\n  │\n  ├─ 人声分析\n  │   说话区间: 0:03-0:05, 0:08-0:12 ...\n  │   语速: 4.2 字/秒\n  │   情绪: 鼓励/讲解/惊讶\n  │\n  └─ 音效分析\n      每个音效的时间点 + 类型（转场whoosh/强调ding/情绪音效）\n      这是最容易被忽略但影响最大的细节</pre>',
    '<hr/>',
    '<h3>2.3 Phase 1：拆解（执行细节）</h3>',
    '<h3>Step 1.1：按场景分组的画面拆解</h3>',
    '<pre lang="text">原视频\n    │\n    ├─ FFmpeg 逐帧导出\n    │   ffmpeg -i source.mp4 -q:v 2 source_frames/%05d.png\n    │\n    ├─ 按 Phase 0 的节奏表分场景\n    │   scene_001/ → 镜头1的所有帧（00001-00069.png，共2.3秒）\n    │   scene_002/ → 镜头2的所有帧（00070-00153.png，共2.8秒）\n    │\n    ├─ 每个场景选关键帧（选"特征帧"）\n    │   第1帧（构图启动画面）\n    │   中间帧（运动过程中的标志性姿态）\n    │   最后帧（构图结束画面）\n    │\n    └─ 特写帧（替换用的参考帧）\n        每个场景选1帧最清晰的人物/产品正脸照\n        → 用途：作为图生图的参考图</pre>',
    '<h3>15 秒爆款视频的拆解产物</h3>',
    '<pre lang="text">source_frames/          → 450 帧（30fps）\nscene_001/              → 69帧（2.3s，产品展示特写）\n  ├─ keyframe_001.png   → 起始构图\n  ├─ keyframe_002.png   → 中间角度\n  └─ ref_person.png     → 如果有人物的话\nscene_002/              → 84帧（2.8s，人物说话中景）\n  ├─ keyframe_001.png   → 起始\n  ├─ keyframe_002.png   → 中间\n  ├─ keyframe_003.png   → 结束\n  ├─ ref_person.png     → 人物正脸参考\n  └─ cond_pose.png      → 骨架图</pre>',
    '<h3>文件结构规范（资产树）</h3>',
    '<pre lang="text">project_name/\n├── 0_analysis/\n│   ├── pacing.json        → 节奏分析结果\n│   ├── motion.json        → 运动分析结果\n│   ├── color_palette.json → 调色分析结果\n│   └── audio_map.json     → 音频结构\n├── 1_source/\n│   ├── source.mp4\n│   ├── source_frames/     → 原始帧\n│   └── audio/             → 分离的音频轨\n├── 2_scenes/\n│   ├── scene_001/\n│   │   ├── keyframes/     → 选出的关键帧\n│   │   ├── conditions/    → ControlNet 条件图\n│   │   ├── refs/          → 参考图\n│   │   └── generated/     → 生成的新帧\n│   ├── scene_002/\n│   └── scene_003/\n├── 3_audio/\n│   ├── voiceover_new.mp3\n│   ├── bgm_new.mp3\n│   └── sfx/\n├── 4_composite/\n│   ├── color_graded/\n│   └── final_output.mp4\n└── pipeline_state.json    → 管线状态机（断点续传）</pre>',
])

# Batch 4: Phase 2 + Phase 3 + Phase 4
batch4 = "\n".join([
    '<hr/>',
    '<h3>2.4 Phase 2：资产准备（关键帧生成的最佳实践）</h3>',
    '<h3>Step 2.1：人物替换策略</h3>',
    '<p>不是"一张参考图生所有角度"，这是 AI 最容易翻车的地方。</p>',
    '<pre lang="text">正确做法：\n  场景A（正面特写）\n    ref=人物正面照\n    → IP-Adapter FaceID + ControlNet Pose\n    → 生成：保持正面长相 + 对齐原场景的姿势\n\n  场景B（侧面中景）\n    ref=人物侧面照（如果只有正面照 → 先转角度生成）\n    → IP-Adapter + ControlNet Pose\n    → 生成：保持侧脸特征 + 对齐姿势\n\n  场景C（全身远景）\n    ref=人物全身照\n    → LoRA（如果是固定人物，跑一个 LoRA 最稳）\n    → ControlNet Pose + Depth\n\n关键规则：每个场景独立参考，不要试图一张图通吃全片</pre>',
    '<h3>Step 2.2-2.3：场景替换 + 光照匹配</h3>',
    '<p>场景替换有三层，不是直接图生图：</p>',
    '<pre lang="text">  L1 — 纯替换背景（最简单）\n     原图 → 抠出主体 → 生成新背景 → 合成\n     适合：绿幕感/主体清晰的画面\n\n  L2 — 保留原场景结构，换视觉风格\n     原场景 → ControlNet Canny 锁定构图 → 新 prompt 生成\n     适合：换场景风格但保留空间结构\n\n  L3 — 完全替换场景（包括主体）\n     原场景 → 抠掉原人物 → 背景补全（inpaint）\n            → 生成新人物 → 光照匹配\n            → 合成\n     适合：需要彻底换内容\n\n光照匹配是这里最容易被忽略的：\n  原场景阴影方向：左前方 30° 顶光，强度中等\n  新生成人物阴影方向必须对齐\n  不匹配 → 一眼就是P的</pre>',
    '<hr/>',
    '<h3>2.5 Phase 3：音频制作</h3>',
    '<pre lang="text">音轨分离（demucs / vocal remover）：\n  ├─ 人声轨 → 如果换人声 → TTS 生成新台词 / 真人配音\n  │            如果不换人声 → 保留原轨\n  ├─ BGM 轨 → 结构对齐\n  │   原BGM的关键节点：第3秒进鼓、第15秒副歌高潮、第25秒淡出\n  │   新BGM必须在这个时间点上对齐\n  └─ 音效轨 → 保留时间点，可替换音色\n      转场whoosh / 强调音 / 环境音</pre>',
    '<hr/>',
    '<h3>2.6 Phase 4：合成（收尾工程）</h3>',
    '<pre lang="text">合成不是简单的拼起来：\n\n  画面合成\n  ├─ 时间线恢复 → 按 Phase 0 的节奏表，精确到帧对齐\n  ├─ 转场恢复 → 硬切/淡入淡出/滑动 → 参数对齐原视频\n  ├─ 调色→ 每场景用 Phase 0 提取的 LUT 统一调色\n  └─ 画质输出 → 5090D 跑 Topaz 超分到 4K\n\n  音频合成\n  ├─ 人声对齐 → 配音的音量/空间感/混响匹配原场景\n  ├─ BGM 对齐 → 新 BGM 在关键节点与原 BGM 保持一致\n  └─ 音效对齐 → 原有时间点一个不落\n\n  定版\n  ├─ 全片统一检查（色温/音量/字幕/黑场）\n  └─ 目标平台参数输出</pre>',
])

# Batch 5: 差异总结 + 总结 + 作者信息
batch5 = "\n".join([
    '<hr/>',
    '<h2>三、和你的方案的差异总结</h2>',
    '<table><colgroup><col width="140"/><col width="260"/></colgroup><thead><tr><th>你的方案</th><th>我的补充</th></tr></thead><tbody>',
    '<tr><td>拆解画面+音频</td><td>✅ 保留，增加 Phase 0 分析阶段（节奏/运动/调色/音频量化）</td></tr>',
    '<tr><td>分场景提取关键帧</td><td>✅ 保留，增加关键帧用途标注 + 规范的资产树结构</td></tr>',
    '<tr><td>参考图生图替换</td><td>⚠️ 需要分层：每个场景独立参考 + 光照匹配 + 背景补全</td></tr>',
    '<tr><td>音频替换</td><td>⚠️ 不够细：人声/BGM/音效三层分离，BGM需对齐原结构</td></tr>',
    '<tr><td>合成</td><td>✅ 保留，加调色统一 + 质量门禁检查点</td></tr>',
    '</tbody></table>',
    '<hr/>',
    '<h2>四、一句话总结</h2>',
    '<callout emoji="bulb" background-color="light-blue">你的骨架是对的，但缺了 Phase 0（分析量化）和资产树。现在干活像是"看着原视频凭感觉复刻"，加上 Phase 0 之后就变成了"拿着原视频的工程图纸施工"——前者靠运气，后者靠流程。</callout>',
    '<hr/>',
    '<p><b>作者信息</b></p>',
    '<p>海风老师 | AI技术咨询 / LoRA模型训练 / 电商AI落地 / GEO优化</p>',
    '<p>微信：frankhzheng</p>',
    '<p>内容资产库：https://github.com/frankhzh-source/hf-ai-articles</p>',
])

# Execute
batches = [
    (batch1, "Batch 1 - Intro + 方案评审"),
    (batch2, "Batch 2 - 总图 + Phase 0"),
    (batch3, "Batch 3 - Phase 0 cont + Phase 1"),
    (batch4, "Batch 4 - Phase 2+3+4"),
    (batch5, "Batch 5 - 差异总结 + 总结 + 作者"),
]

all_ok = True
for xml, label in batches:
    if not append_content(xml, label):
        all_ok = False
        break

if all_ok:
    print(f"\n=== ALL COMPLETED ===")
    print(f"URL: https://cp8z7brjmy.feishu.cn/docx/L7KFdNez5oMrPJx1VrNcBTC9nsd")
else:
    print("\n=== SOME FAILED ===")
