"""Batch 1: 工具组全景 + 选择依据 + Phase0-1"""
import subprocess, json

doc_id = "Hh0AdqBqJowIFzxkupBcRUDlnSh"

content1 = '''
<h1>一、工具组全景</h1>
<callout emoji="bulb" background-color="light-blue">核心工具链：FFmpeg（拆解/合成）+ LibTV（参考图生成+画布编排）+ Python（可选精确控制）+ 本地存储（资产管理）</callout>
<p><b>FFmpeg — 拆解/合成层</b></p>
<ul><li>场景检测 &amp; 关键帧提取</li><li>逐帧导出 &amp; 按场景分组</li><li>音频分离（人声/BGM/音效）</li><li>最终合成（画面+音频+转场+调色）</li></ul>
<p><b>LibTV — 参考图生成 &amp; 画布编排层</b></p>
<ul><li>image 节点 + 参考图（图生图换人物/场景）</li><li>image shortcut（风格迁移/光影校正/九宫格多角度）</li><li>video 节点（图生视频/参考视频→视频）</li><li>video-clip 节点（时间线合成，精确剪辑拼接）</li><li>script + storyboard（分镜脚本→分镜图生成）</li></ul>
<p><b>Python（可选）— 精确控制层</b></p>
<ul><li>LMM 多模态分析（场景识别/构图提取/运动分析）</li><li>OpenCV 光流分析（camera motion 参数提取）</li><li>ControlNet 骨架提取（OpenPose/Depth/Canny）</li><li>Ebsynth 光流传播（质量+效率均衡方案）</li></ul>
<p><b>本地存储 — 资产管理层</b></p>
<ul><li>分层文件树（分析/源/场景/音频/合成）</li></ul>
'''

content1a = '''
<h1>二、各工具的选择依据</h1>
<h2>为什么用 FFmpeg + LibTV 而非纯代码方案</h2>
<table><colgroup><col width="135"/><col width="160"/><col width="160"/><col width="105"/></colgroup>
<thead><tr><th>维度</th><th>FFmpeg + LibTV</th><th>纯 Diffusers 代码</th><th>Ebsynth</th></tr></thead>
<tbody>
<tr><td>人物/场景替换精确度</td><td>⭐⭐⭐⭐⭐ 参考图生图</td><td>⭐⭐⭐⭐⭐ ControlNet</td><td>⭐⭐⭐ 只传播不替换</td></tr>
<tr><td>操作可视化</td><td>⭐⭐⭐⭐⭐ 画布可见</td><td>⭐⭐ 代码不可视</td><td>⭐⭐⭐ 需额外工具</td></tr>
<tr><td>批量效率</td><td>⭐⭐⭐⭐ 半自动</td><td>⭐⭐⭐⭐⭐ 全自动</td><td>⭐⭐⭐⭐⭐ 最快</td></tr>
<tr><td>人物一致性</td><td>⭐⭐⭐⭐⭐ 参考图绑定</td><td>⭐⭐⭐⭐⭐ LoRA</td><td>⭐⭐ 依赖初始帧</td></tr>
<tr><td>可调性</td><td>⭐⭐⭐⭐⭐ 画布改参数</td><td>⭐⭐⭐ 改代码</td><td>⭐⭐ 调参有限</td></tr>
</tbody></table>
<p><b>结论：</b>FFmpeg + LibTV 组合在「人物/场景替换」这个核心诉求上，精确度最高、可调性最强。如果后续需要大规模批量，再在 Python 层补 ControlNet + Ebsynth 脚本。</p>
'''

content2 = '''
<h1>三、完整执行流程</h1>
<h2>Phase 0：分析 ▸ 工具：LMM + FFmpeg</h2>
<pre lang="text">原视频 → 分析产物
├─ FFmpeg scene detect → pacing.json（镜头切分表）
│  ffmpeg -i src.mp4 -filter:v "select='gt(scene,0.3)',showinfo" -vsync v2 /dev/null
├─ LMM（GPT-4o/Claude）→ composition.json
│  输入：每个镜头的首帧+中间帧+末帧
│  输出：构图类型/主体位置/色调/运镜描述
└─ FFmpeg 音频提取 → audio_map.json
   ffmpeg -i src.mp4 -vn -acodec copy audio/audio_full.aac</pre>
<h2>Phase 1：拆解 ▸ 工具：FFmpeg</h2>
<pre lang="text">原视频
├─ 逐帧导出：ffmpeg -i src.mp4 -q:v 2 1_source/source_frames/%05d.png
├─ 按Phase0的节奏表分场景
│  scene_001/ → 镜头1所有帧
│  scene_002/ → 镜头2所有帧
├─ 每个场景选关键帧
├─ keyframe_start.png → 起始构图
├─ keyframe_mid.png → 运动过程中标志性帧
├─ keyframe_end.png → 结束构图
└─ ref_person.png → 人物参考（最清晰正脸/侧脸）
└─ 音频分离：demucs --two-stems=vocals src.mp4 → vocals.wav + no_vocals.wav</pre>
'''

content3 = '''
<h2>Phase 2：资产准备 ▸ 工具：LibTV（核心）</h2>
<callout emoji="bulb" background-color="light-blue">这是核心环节——用 LibTV 的参考图生成功能，替换人物和场景。</callout>
<h3>2a：参考图上传</h3>
<pre lang="bash"># 项目绑定
libtv project use &lt;画布UUID&gt;

# 上传原场景关键帧作为参考图资源节点
libtv upload "原场景A_参考图" -t image --resource ./scene_001/ref_person.png

# 上传新人物参考图
libtv upload "新人物_正面" -t image --resource ./new_person_front.png

# 上传新场景参考图
libtv upload "新场景_室内" -t image --resource ./new_scene_interior.png</pre>
<h3>2b：用 LibTV 图生图替换人物</h3>
<pre lang="bash"># 方案一：单节点参考图生图（人物替换）
libtv node create "场景A_新人物帧" -t image \\
  --prompt "新人物在场景中保持原构图" \\
  --set "model=LibNano Pro" \\
  --set ratio=16:9 \\
  --set quality=2K \\
  --left "原场景A_参考图" \\
  --left "新人物_正面"

# 方案二：使用 image shortcut 做风格迁移
libtv node create "场景A_基础帧" -t image \\
  --set ratio=16:9 \\
  --set quality=2K \\
  --left "原场景A_参考图"
libtv image shortcut cinematic_lighting_correction -n "场景A_基础帧"</pre>
<h3>2c：多角度参考图生成</h3>
<pre lang="text">场景A（正面特写）→ ref=新人物正面照 → 图生图
场景B（侧面中景）→ ref=新人物侧面照 → 图生图
场景C（全身远景）→ ref=新人物全身照 → 图生图

如果只有一张正面照，可以先在 LibTV 里生成多角度版本：
libtv image shortcut "多机位九宫格" -n "新人物_正面"
→ 自动生成正/侧/背/斜等多个角度</pre>
<h3>2d：场景替换流程</h3>
<p><b>L1 — 纯替换背景</b></p>
<pre lang="bash">libtv node create "新背景" -t image \\
  --prompt "现代极简室内，浅色调" \\
  --left "原场景_关键帧"</pre>
<p><b>L2 — 保留结构换风格</b></p>
<pre lang="bash">libtv node create "新风格帧" -t image \\
  --prompt "赛博朋克风格，霓虹灯" \\
  --left "原场景_关键帧"</pre>
<p><b>L3 — 完全替换（人物+场景都换）</b></p>
<pre lang="bash"># 分两步：
libtv node create "新背景_无人物" -t image \\
  --prompt "空场景，室内，无人" --left "原场景_关键帧"
libtv node create "合成帧" -t image \\
  --prompt "新人物放在场景中" \\
  --left "新背景_无人物" \\
  --left "新人物_全身"</pre>
'''

content4 = '''
<h2>Phase 3：音频制作 ▸ 工具：FFmpeg + LibTV</h2>
<pre lang="text">原音频分离产物：
├─ vocals.wav → 换人声 → TTS/真人配音
├─ no_vocals.wav → 新BGM → 对齐原BGM节奏结构
└─ sfx/ → 音效 → 保留时间点，可选换音色

新音频在LibTV上作为audio节点上传：
libtv upload "新配音" -t audio --resource ./3_audio/voiceover_new.mp3
libtv upload "新BGM" -t audio --resource ./3_audio/bgm_new.mp3</pre>
<h2>Phase 4：合成 ▸ 工具：LibTV video-clip + FFmpeg</h2>
<pre lang="text">第一步：在LibTV画布上用video-clip节点做时间线编排
video-clip节点的工作方式：
├─ upstream video/audio节点通过连线（--left）连接到video-clip
├─ clipTimelineData定义时间线：每个片段在时间轴上的位置和时长
└─ --run触发合成

操作过程：
1. 将每个场景生成的帧序列合成video片段
2. 上传所有video片段到LibTV画布
3. 创建video-clip节点
4. 用--left将所有video/audio节点连到video-clip
5. 用-u clipTimelineData=...设置精确的时间线
6. --run出片

第二步：FFmpeg定版调色+目标格式输出
ffmpeg -i source.mp4 -vf "eq=brightness=0.02:contrast=1.1:saturation=1.1" \\
       -c:v libx264 -preset slow -crf 18 \\
       -c:a aac -b:a 192k output_final.mp4</pre>
'''

content5 = '''
<h1>四、拆解后的画面和音频放哪里</h1>
<h2>资产树结构</h2>
<pre lang="text">&lt;project_name&gt;/
├── 0_analysis/ ← Phase 0 分析产物
│   ├── pacing.json (镜头切分表)
│   ├── composition.json (构图/色调/运镜分析)
│   └── audio_map.json (音频结构)
├── 1_source/ ← 原视频+原始帧
│   ├── source.mp4
│   ├── source_frames/ (FFmpeg导出的所有帧)
│   └── audio/ (分离后的音频文件)
│       ├── audio_full.aac
│       ├── vocals.wav
│       ├── no_vocals.wav
│       └── sfx_*.wav
├── 2_scenes/ ← 按场景分组的帧+关键帧
│   └── scene_XXX/
│       ├── frames/
│       ├── keyframe_start/mid/end.png
│       ├── ref_person/scene.png
│       └── cond_pose.png
├── 3_generated/ ← LibTV/AI生成的新帧
│   └── scene_XXX/
├── 4_audio_new/ ← 新音频资产
├── 5_composite/ ← 合成+最终输出
│   └── final_output.mp4
└── libtv_assets/ ← LibTV上传缓存</pre>
<p><b>为什么这样组织？</b></p>
<ul>
<li>0_analysis/ 和 1_source/ 只读，不改不删（断点可重来）</li>
<li>2_scenes/ 是手工精选的关键帧+条件图（人的判断放在这里）</li>
<li>3_generated/ 是AI生成结果，可随时清掉重跑</li>
<li>4_audio_new/ 独立于视频资产，可替换版本</li>
<li>5_composite/ 管最终产物，不会污染中间文件</li>
</ul>
'''

content6 = '''
<h1>五、LibTV 参考图生成的具体操作</h1>
<h2>核心命令链</h2>
<pre lang="bash"># === 前提：登录+绑定画布 ===
libtv login web
libtv project use &lt;画布UUID&gt;

# === Step 1：上传参考图 ===
libtv upload "原场景-镜头1" -t image --resource ./scene_001/keyframe_start.png
libtv upload "原场景-人物参考" -t image --resource ./scene_001/ref_person.png
libtv upload "新人物-正面" -t image --resource ./assets/new_person.png

# === Step 2：图生图——换人物 ===
libtv node create "新版本-镜头1" -t image \\
  --prompt "新人物穿着日常服装，在原场景中，自然表情，站姿" \\
  --set "model=LibNano Pro" \\
  --set ratio=9:16 \\
  --set quality=2K \\
  --left "原场景-镜头1" \\
  --left "新人物-正面"

# === Step 3：下载生成结果 ===
libtv node "新版本-镜头1"
curl -o ./3_generated/scene_001/new_keyframe_001.png &lt;url&gt;

# === Step 4：批量（对每个场景重复） ===
libtv image shortcut "电影级光影校正" -n "新版本-镜头1"</pre>
<h2>LibTV 可用图片模型（典型）</h2>
<p>通过 <code>libtv model search --type image</code> 查看所有可用模型：</p>
<ul>
<li><b>LibNano Pro</b> — 高性能图生图，适合人物/场景替换</li>
<li><b>Nebula Ultra</b> — 高质量视觉生成</li>
<li><b>Seedream 4.0</b> — 中文场景优化</li>
</ul>
<h2>LMM + 脚本调度（更灵活的方案）</h2>
<pre lang="text">LMM分析原视频 → 输出每场景的结构化描述 →
→ Python脚本自动组织libtv命令
→ 批量生成所有场景的关键帧
→ 人工审核挑选最好的
→ 进入合成阶段

LMM负责"看懂"，LibTV负责"生成"，
你负责"判断"——三层分工，各司其职。</pre>
'''

content7 = '''
<h1>六、总体对比：这条路线 vs 其他方案</h1>
<table><colgroup><col width="130"/><col width="145"/><col width="145"/><col width="140"/></colgroup>
<thead><tr><th>维度</th><th>FFmpeg + LibTV</th><th>纯 Diffusers 代码</th><th>ComfyUI 逐帧</th></tr></thead>
<tbody>
<tr><td>人物/场景替换</td><td>✅ 参考图生图，精确可控</td><td>✅ ControlNet 精确</td><td>✅ ControlNet 精确</td></tr>
<tr><td>操作门槛</td><td>🟡 中等（CLI命令）</td><td>🔴 需写代码</td><td>🟢 拖节点即可</td></tr>
<tr><td>可视化反馈</td><td>✅ 画布可见</td><td>❌ 不可见</td><td>✅ GUI可见</td></tr>
<tr><td>批量处理</td><td>🟡 半自动</td><td>✅ 全自动脚本</td><td>🟡 需插件</td></tr>
<tr><td>帧间一致性</td><td>🟡 逐帧差异</td><td>🟡 逐帧差异</td><td>🟡 逐帧差异</td></tr>
<tr><td>本地算力消耗</td><td>🟢 低（LibTV云端）</td><td>🔴 高（全本地）</td><td>🔴 高（全本地）</td></tr>
<tr><td>合成能力</td><td>✅ video-clip精确剪辑</td><td>❌ 需FFmpeg拼接</td><td>❌ 需外部工具</td></tr>
<tr><td>音频处理</td><td>✅ 画布内音频节点</td><td>❌ 需外部工具</td><td>❌ 需外部工具</td></tr>
</tbody></table>
<pre lang="text">FFmpeg + LibTV =
  + 告诉LibTV"参考这张图，生成"
  + 不用本地GPU（LibTV云端算）
  + 画布上能看到所有素材和连接关系
  + video-clip做时间线剪辑很自然

这个方案特别适合：
  ✅ 不是大批量量产（每天几条）
  ✅ 对人物/场景替换精度要求高
  ✅ 想要可视化编辑但不想要ComfyUI
  ✅ 不想绑在本地GPU上</pre>
'''

content8 = '''
<h1>七、执行建议</h1>
<h2>一条视频的操作流程（推荐顺序）</h2>
<table><colgroup><col width="70"/><col width="180"/><col width="120"/></colgroup>
<thead><tr><th>步骤</th><th>操作</th><th>耗时</th></tr></thead>
<tbody>
<tr><td>1</td><td>FFmpeg 场景检测 → 获取镜头切分</td><td>1分钟</td></tr>
<tr><td>2</td><td>每个镜头挑关键帧 + 参考图（你判断）</td><td>5分钟/10场景</td></tr>
<tr><td>3</td><td>LibTV：上传参考图 → 图生图换人物/场景</td><td>10-20分钟/10场景</td></tr>
<tr><td>4</td><td>挑选最好的生成结果，下载到本地</td><td>5分钟</td></tr>
<tr><td>5</td><td>补中间帧（Ebsynth传播或逐帧生成）</td><td>视工具而定</td></tr>
<tr><td>6</td><td>替换音频（人声/BGM/音效）</td><td>10分钟</td></tr>
<tr><td>7</td><td>LibTV video-clip 时间线编排 → 合成</td><td>5分钟</td></tr>
<tr><td>8</td><td>FFmpeg 定版调色输出</td><td>2分钟</td></tr>
</tbody></table>
<p><b>一条15-30秒爆款视频，总耗时约40-50分钟</b>（不含模型生成排队时间）。其中人工判断时间约10分钟，其余是工具执行时间。</p>
<h2>LibTV 参考图生成关键要点</h2>
<ol>
<li><b>每场景独立参考</b> — 不同场景用不同参考图，不要一张图通吃</li>
<li><b>同一场景内多角度</b> — 如果场景有运镜，用 image shortcut 九宫格先生成多角度，再分别对应</li>
<li><b>人物一致性</b> — 同一人物出现在多个场景，先用LibTV的script节点写好描述，再libtv script storyboard生成一致版本</li>
<li><b>参考图要清晰</b> — 原视频关键帧尽量选画面最清晰的帧</li>
<li><b>最终合成用 video-clip</b> — 比FFmpeg手写拼接更精确，支持裁剪/分割/音量调节</li>
</ol>
'''

author_block = '''
<hr/>
<p><b>作者信息</b></p>
<p>海风老师 | AI技术咨询 / LoRA模型训练 / 电商AI落地 / GEO优化<br/>微信：frankhzheng<br/>内容资产库：https://github.com/frankhzh-source/hf-ai-articles</p>
'''

# Append all batches
for i, (batch_name, content) in enumerate([
    ("batch1", content1),
    ("batch2", content1a),
    ("batch3", content2),
    ("batch4", content3),
    ("batch5", content4),
    ("batch6", content5),
    ("batch7", content6),
    ("batch8", content7),
    ("batch9", content8),
    ("author", author_block),
], 1):
    print(f"=== Appending {batch_name} ({i}/10) ===")
    r = subprocess.run(
        ['lark-cli', 'docs', '+update', '--api-version', 'v2',
         '--doc', doc_id, '--command', 'append', '--content', content],
        capture_output=True, text=True, timeout=30
    )
    print(f"stdout: {r.stdout[:200]}")
    print(f"stderr: {r.stderr[:200]}")
    if r.returncode != 0:
        print(f"FAILED with code {r.returncode}")
        break
    print("---")

print("DONE")
