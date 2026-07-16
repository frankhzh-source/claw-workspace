# LibTV 复刻抖音爆款视频 · 完整方法论

**作者**：海风老师 — 电商 AIGC 落地咨询
**工具链**：LibTV（CLI + Canvas）| Seedance 2.0/2.5 | Kling 3.0 | Seedream 4.5/4.6
**适用场景**：家居服/服装电商 AI 模特展示视频复刻

---

## 核心理念

**复刻不是复制。** 复刻抖音爆款视频的本质是：

1. 拆出原视频的**结构范式**（分镜节奏 + 运镜模式 + 信息流）
2. 用 AI 工具**替换人物、服装、场景**三个可变要素
3. 保留其**被市场验证过的流量结构**

> 复刻的是「为什么火」——不是「他穿了什么」。

---

# 方法论框架（6阶段）

---

## 阶段一：拆解分析 — 把原视频变成可复现的数据

### 1.1 逐帧拆解表

拿到爆款视频后，逐帧记录以下 8 个维度：

| 维度 | 记录内容 | 示例 |
|------|---------|------|
| 镜号 | 1A, 1B, 2A... | 1A |
| 时间轴 | 镜头起始→结束秒数 | 0:00-0:03 |
| 景别 | 远景/全景/中景/近景/特写 | 中全景 |
| 运镜 | 固定/缓推/缓拉/摇移/跟随 | 固定→缓推 |
| 人物状态 | 做什么/什么表情/看哪里 | 右手持衣架，微笑看向镜头 |
| 服装呈现 | 展示哪个部位/什么动作 | 正面全身展示印花 |
| 灯光氛围 | 主光方向/色温/氛围 | 左前45°暖光，居家氛围 |
| 参考帧 | 该镜头关键帧截图 | frame_001.png |

> **工具建议**：用剪映/Premiere 逐帧截图，按镜号命名 frame_001~030.jpg

### 1.2 节奏模板提取

从拆解表中提炼出**不依赖具体内容**的节奏模板：

```
[开场 3s] 手持展示 → [产品展示 15s] 正面/侧面/背面三角度
→ [细节特写 12s] 领口/印花/面料 → [上身效果 10s] 模特穿着的动态
→ [结尾 5s] 品牌/产品定帧
```

> **注意**：节奏模板才是复刻的核心资产。它可被反复应用于不同服装/人物/场景。

### 1.3 要素替换清单

| 原视频要素 | 替换为 | 准备方式 |
|-----------|--------|---------|
| 人物 | 新模特 | 十维框架生成主视觉+三视图+表情 |
| 服装 | 新服装 | 白底图+平铺图+细节图作为参考 |
| 场景 | 新场景（或保留） | 用prompt描述或上传参考图 |
| 灯光 | 统一光方案 | 从十维框架固定照明参数 |
| BGM | 新BGM | 找风格相似的版权音乐 |

---

## 阶段二：角色资产准备 — 十维一致性框架落地

### 2.1 10维参考图资产

| # | 维度 | 生成方式 | LibTV用法 |
|---|------|---------|----------|
| 1 | 主视觉肖像 | Seedream → image node，正面半身 | 后续所有节点的参考图 |
| 2 | 三视图 | 3个独立image node（正面/侧面/背面） | 同服装/同光源分图生成 |
| 3 | 表情设定 | 4组（喜/静/忧/疑） | 按场景选不同表情Prompt |
| 4 | 面部细节 | 六要素固定块（眉眼口鼻唇肤） | 每镜Prompt前缀固定块 |
| 5 | 服饰材质 | 白底图+平铺图作参考 | 上传至image node，weight 0.8 |
| 6 | 手部与姿态 | 参考帧+Prompt描述 | 避免手指粘连/姿势变形 |
| 7 | 道具特写 | 衣架/配件等参考图 | 按需生成对应节点 |
| 8 | 色彩参考 | 主色#F5F0EB/辅色#4A4A4A | 写入Prompt描述或上传色卡 |
| 9 | 剪影比例 | 全身剪影统一 | 每镜保持宽高比例一致 |
| 10 | 角色信息 | 年龄/气质/妆造固定描述块 | 每个Prompt前缀统一 |

### 2.2 人物固定块写作规范

每次写 Prompt 时，在最前面粘贴以下固定块：

```
[人物固定块]
亚洲女性，28岁，电商家居服模特
鹅蛋脸，自然弯眉深棕色，杏眼内眼角略尖睫毛微翘，直鼻梁鼻翼窄，上唇薄下唇厚豆沙色哑光
暖白偏黄哑光肌保留纹理不磨皮
黑色长发披肩，中分，发尾微卷

[服装固定块 - 示例：达芬奇密码洛神玫瑰]
米白色缎面底，大花型洛神玫瑰印花，青果领交叉翻领
长袖长裤套装，95%聚酯纤维+5%氨纶，微弹垂坠，丝滑哑光质感
粉色滚边装饰领口与袖口

[光照固定块]
暖光3000K，45度右侧柔光，阴影柔和
背景暖白简约卧室/纯色米白背景
```

### 2.3 固定块粘贴原则（铁律）

- **同一视频内，固定块不允许修改**——哪怕只是换一个词
- 人物/服装/光照三块固定后，每镜只修改：**景别 + 运镜 + 动作 + 表情**
- 如果换服装（下一个商品），重新生成固定块

---

## 阶段三：分镜脚本编写 — LibTV Script Node

### 3.1 分镜行数据结构

每个镜头 = JSON 数组中的一行：

```json
{
  "shotNumber": 1,
  "durationSeconds": 3.0,
  "shotSize": "中全景",
  "plotDescription": "场景+人物+动作+表情的文字描述",
  "characters": [
    {
      "characterName": "AI模特",
      "characterDescription": "完整的固定块描述",
      "characterImageUrl": "主视觉肖像图URL（上传至LibTV后的地址）"
    }
  ],
  "characterAction": "动作描述",
  "emotion": "情绪关键词",
  "sceneTags": "场景标签",
  "lightingAndAtmosphere": "灯光氛围描述",
  "audioEffects": "音效/BGM说明",
  "dialogue": "台词（可空）",
  "imageGenerationPrompt": "分镜图生成提示词（英文，含固定块）",
  "videoMotionPrompt": "视频运镜提示词（英文）"
}
```

### 3.2 提示词工程 — 英文 Prompt 写作规则

LibTV 的 imageGenerationPrompt 和 videoMotionPrompt 默认用英文效果最好：

**imageGenerationPrompt 公式：**
```
[人物固定块] + [服装固定块] + [景别] + [动作] + [表情] + [构图] + [光照] + [质量后缀]
```

**videoMotionPrompt 公式：**
```
[camera motion] + [人物运动] + [速度] + [帧率]
```

**质量后缀统一表：**

| 用途 | 后缀 |
|------|------|
| 主视觉/肖像 | `8K, highly detailed, soft natural lighting` |
| 服装展示 | `sharp fabric texture, clear print detail, 8K` |
| 特写 | `macro shot, extreme detail, sharp focus, 8K` |
| 全身 | `full body, clean background, soft studio lighting, 8K` |

### 3.3 运镜 Prompt 标准词库

| 中文描述 | 英文写法 |
|---------|---------|
| 固定机位 | `fixed camera` |
| 缓慢推近 | `slow zoom in 1.0→1.05` |
| 缓慢拉远 | `slow zoom out` |
| 从左向右摇 | `pan right` |
| 从右向左摇 | `pan left` |
| 上下摇 | `tilt up/down` |
| 环绕 | `orbit around subject` |
| 跟随人物 | `tracking shot following subject` |
| 微呼吸感 | `subtle breathing movement` |
| 定帧 | `static frame, no camera motion` |

### 3.4 标准景别描述

| 景别 | 英文 | 画面范围 |
|------|------|---------|
| 远景 | `wide shot / establishing shot` | 人物占画面1/3以下 |
| 全景 | `full body shot` | 从头到脚 |
| 中全景 | `medium full shot` | 膝盖以上 |
| 中景 | `medium shot` | 腰部以上 |
| 中近景 | `medium close-up` | 胸部以上 |
| 近景 | `close-up` | 肩部以上 |
| 特写 | `extreme close-up` | 局部（领口/面料/印花） |

---

## 阶段四：图像节点生成 — 关键帧创建

### 4.1 模型选择策略

| 画面类型 | 推荐模型 | 原因 |
|---------|---------|------|
| 主视觉肖像 | Seedream 4.5 | 角色一致性最强 |
| 高质感服装图 | Seedream 4.6 或 悠船 V8.1 | 材质细节更真实 |
| 场景氛围图 | Seedream 4.0 | 场景理解好 |
| 服装材质特写 | Seedream 4.6 | 印花/面料还原度高 |
| 快速试稿 | Seedream 5.0 Lite | 速度快 |

### 4.2 关键帧生成流程

```
上传参考图（白底图+平铺图+模特图）
  → 设置参考图权重 0.8-0.9
  → 输入imageGenerationPrompt（含固定块）
  → 选择模型 Seedream 4.5/4.6
  → 生成 → 质检 → 不合格则调整Prompt重跑
```

### 4.3 批量生成策略

- 同一服装/场景下：一次生成所有关键帧（15-20张）
- 批量模式下：**固定Prompt模板只替换景别+动作两个变量**
- 避免：每张图从头写Prompt（会导致风格不一致）

---

## 阶段五：视频节点生成 — AI 视频生成

### 5.1 模型选择

| 场景 | 模型 | 参数 |
|------|------|------|
| 全身/半身展示 | Seedance 2.0/2.5 | duration 4-5s, 720p |
| 面料质感动态 | Kling 3.0 | duration 3-4s, 720p |
| 大特写微动 | Kling 3.0 | duration 3-4s, 最强材质表现 |
| 人物转体/动作 | Seedance 2.0 | duration 4-5s |
| 30秒长镜头 | Seedance 2.5 | 原生30s, 4K |

### 5.2 视频节点配置

```bash
# 图生视频 — 标准配置
libtv node create "镜1A_手持展示" -t video \
  --prompt "[videoMotionPrompt]" \
  -s "model=Seedance 2.0" \
  -s ratio=9:16 \
  -s duration=5 \
  -s enableSound=on \
  -s resolution=720p \
  --left "关键帧_1A"

# 特写微动 — Kling 3.0
libtv node create "镜4A_领口特写" -t video \
  --prompt "slow zoom in on collar, fabric texture subtle movement, silk loungewear, 24fps" \
  -s "model=Kling 3.0" \
  -s ratio=9:16 \
  -s duration=4 \
  --left "关键帧_4A"
```

### 5.3 人物一致性控制 × 视频生成

视频节点的人物一致性比图像节点更难控制。核心策略：

1. **关键帧先确保一致**：视频生成的上游参考图（关键帧）必须是同一套人物/服装
2. **每帧用同一张主视觉参考图**：视频生成的参考图不是关键帧，而是「主视觉肖像」
3. **固定的面部细节Prompt**：在videoMotionPrompt中混入「same face, same model identity」
4. **Seedance 表演强度控制**：0.3-0.5（电商用，不要开高）

### 5.4 常见视频翻车 & 修法

| 翻车现象 | 根因 | 修法 |
|---------|------|------|
| 人物脸变 | 参考图不一致 | 所有视频节点用同一张参考图 |
| 服装印花漂移 | 参考图权重太低 | 参考图权重提到0.85-0.9 |
| 面部扭曲 | 动作幅度太大 | 降低表演强度到0.3，缩短duration |
| 镜头突然跳变 | 运镜描述冲突 | 只写一种运镜，不写多种叠加 |
| 背景闪烁 | 参考图背景太复杂 | 用纯色背景+后期抠图 |

---

## 阶段六：视频合成 — LibTV Video-Clip Node

### 6.1 简单拼接（不需clipTimelineData）

```bash
libtv node create "最终合成" -t video-clip \
  --left "镜1A_手持展示" \
  --left-add "镜2A_正面展示" \
  --left-add "镜2B_转体展示" \
  --left-add "镜2C_正面定姿" \
  --left-add "镜3A_侧面版型" \
  --left-add "镜3B_侧面回眸" \
  --left-add "镜3C_侧面插袋" \
  --left-add "镜4A_领口特写" \
  --left-add "镜4B_印花特写" \
  --left-add "镜4C_袖口近景" \
  --left-add "镜5A_抚摸面料" \
  --left-add "镜5B_垂坠线" \
  --left-add "镜5C_抖动面料" \
  --left-add "镜6A_结尾展臂" \
  --left-add "镜6B_定帧标题"

libtv node "最终合成" --run
```

**视频-clip的优缺点**：
- ✅ 最简单，1条命令完成
- ✅ 适合首尾相接的展示类视频
- ❌ 不能裁剪单个镜头时长
- ❌ 不能调音量

### 6.2 精细剪辑（带clipTimelineData）

当需要裁剪/分割/调音量时，写时间线数据：

```json
{
  "clips": [
    {
      "id": "clip_1",
      "sourceNodeId": "镜1A_手持展示",
      "type": "video",
      "startTime": 0.0,
      "duration": 3.0,
      "sourceOffset": 0.0,
      "sourceDuration": 3.0
    },
    {
      "id": "clip_2",
      "sourceNodeId": "镜2A_正面展示",
      "type": "video",
      "startTime": 3.0,
      "duration": 3.5,
      "sourceOffset": 0.0,
      "sourceDuration": 3.5
    }
  ],
  "videoAudioVolume": 0.3,
  "audioTrackMuted": false
}
```

```bash
# 写入时间线数据
libtv node "最终合成" \
  -u clipTimelineData='{
    "clips": [{"id":"c1","type":"video","startTime":0.0,"duration":3.0,"sourceOffset":0.0,"sourceDuration":3.0}],
    "videoAudioVolume": 0.3
  }'

# 触发合成
libtv node "最终合成" --run
```

### 6.3 合成参数建议

| 参数 | 建议值 | 说明 |
|------|-------|------|
| 视频轨音量 | 0.3-0.5 | 原视频声音压低，给BGM空间 |
| 音频轨曲目 | 上传BGM作为audio节点后接入 | 抖音风轻快BGM |
| 总时长 | 60-90秒 | 抖音推荐区间 |
| 音频轨音量 | 0.7-0.8 | BGM音量高于视频原声 |
| 结尾定帧 | 8-15秒 | 产品信息停留 |

---

# 附录

## 附录A：LibTV 标准工作流命令速查

```bash
# ===== 1. 项目初始化 =====
libtv project create --name "达芬奇密码_0623"
libtv project use <UUID>

# ===== 2. 上传参考图 =====
libtv upload "C:/assets/白底图.jpg" --name "白底图_reference"
libtv upload "C:/assets/平铺图.jpg" --name "平铺图_reference"
libtv upload "C:/assets/主视觉肖像.png" --name "主视觉肖像"

# ===== 3. 建脚本节点并写入分镜 =====
libtv node create "分镜脚本" -t script -s "model=GVLM 3.1" --prompt "家居服展示视频"
libtv node "分镜脚本" -u rows='[{...分镜行JSON...}]'
libtv node "分镜脚本" --run

# ===== 4. 生成分镜图组 =====
libtv script storyboard "分镜脚本" -s "model=Seedream 4.0" -s ratio=9:16

# ===== 5. 建视频节点并生成 =====
libtv node create "镜1_手持展示" -t video -s "model=Seedance 2.0" \
  -s ratio=9:16 -s duration=5 --prompt "prompt..." \
  --left "关键帧_1A"

# ===== 6. 合成 =====
libtv node create "最终合成" -t video-clip \
  --left "镜1_手持展示" --left-add "镜2_正面展示"

libtv node "最终合成" --run
```

## 附录B：爆款视频复刻检查清单

### 拆解阶段
- [ ] 逐帧记录8个维度（镜号/时间/景别/运镜/人物/服装/灯光/参考帧）
- [ ] 提取节奏模板（不依赖内容的结构范式）
- [ ] 提取要素替换清单（哪些要替换/哪些保留）

### 资产准备阶段
- [ ] 生成10维参考图资产
- [ ] 写好人物/服装/光照三个固定块
- [ ] 固定块写入后不再修改

### 生成阶段
- [ ] 所有视频节点用同一张参考图
- [ ] 每镜Prompt前缀固定块一致
- [ ] 只改景别+运镜+动作三个变量
- [ ] 表演强度 0.3-0.5

### 合成阶段
- [ ] 镜头首尾拼接无黑帧
- [ ] BGM 音量 ≥ 原视频音量
- [ ] 总时长 60-90秒
- [ ] 结尾定帧 8-15秒

### 交付前检查
- [ ] 人物从头到尾一致（脸不变）
- [ ] 服装印花/版型一致（不走样）
- [ ] 表情自然不过度
- [ ] 运镜不突兀
- [ ] 素材没露AI拼接痕迹

## 附录C：常见复刻失败模式

| 失败模式 | 原因 | 预防 |
|---------|------|------|
| 人物漂移 | 不同镜用了不同参考图 | 全程一张主视觉肖像 |
| 服装走样 | 不同镜的服装描述不一致 | 服装固定块锁死不修改 |
| 节奏不对 | 没拆时间轴，凭感觉复用 | 严格按拆解表计时 |
| 光不统一 | 每镜写不同光参数 | 光照固定块统一 |
| 表情僵硬 | 没给原因只给了关键词 | 用表情公式拆解 |
| 运镜跳脱 | 用太多不同运镜 | 每镜只写1种运镜 |
| 印花扭曲 | 参考图权重太低 | 提到0.85-0.9 |
| 成品像PPT | 没做动态关键帧 | 每镜至少有微小的呼吸动作 |
