# 「梵梵店铺0623」AI虚拟模特电商视频 — 制作分镜本

```
PRODUCTION:  落英缤纷·印花睡衣套装
FORMAT:      9:16 Vertical / Douyin Short Video
RUNTIME:     60-70s
DIRECTOR:    海风
AI TOOL:     LibTV / Seedance 2.0 / Kling 3.0
LOG LINE:    AI虚拟模特多场景展示花卉印花睡衣套装，从持衣到穿上到细节特写的全流程展示
TONE:       优雅·舒适·轻奢·居家
```

---

## 一、总览

### 叙事弧线

```
开场(持衣展示) → 穿上(全身正面) → 版型(侧面) → 特写(领口) → 质感(面料) → 定格(展臂结束)
   |-------------------|-------------------|-------------------|-------------------|
   0s                  20s                 40s                 60s
   建立期待             上身效果验证         细节品质锚定         购买冲动收尾
```

### 节奏设计

| 段落 | 节奏 | 镜头数 | 情绪 |
|------|------|--------|------|
| 开场吸引 | 快切入 | 1-2 | 好奇心 |
| 上身展示 | 中等-流畅 | 2-4 | 认同感 |
| 细节质感 | 慢-近距离 | 5-7 | 安全感 |
| 结尾收束 | 拉远+定格 | 8 | 冲动 |

---

## 二、分镜脚本

### SCENE 1 — 开场·持衣展示（0-8s）

| 场号 | 景别 | 运镜 | 画面描述 | 音效 |
|------|------|------|---------|------|
| 1-1 | 中全景 | 固定→缓推 | 店铺/卧室背景，模特右手持衣架挂睡衣套装，左手自然垂放，目光看向镜头微笑 | BGM起 |

**Prompt**:
```
Asian female model, holding floral pajama set on a hanger in right hand,
cozy bedroom background with warm lamplight and soft beige walls,
full body shot, natural smile, elegant standing pose,
professional e-commerce photography, soft volumetric lighting,
16:9 (cropped to 9:16), 8K quality
```

**参数**:
```
model: Seedance 2.0
ratio: 9:16
duration: 3s
motion: slow zoom in (1.0→1.05)
```

---

### SCENE 2 — 全身正面·穿上效果（8-20s）

| 场号 | 景别 | 运镜 | 画面描述 | 音效 |
|------|------|------|---------|------|
| 2-1 | 全身 | 固定 | 纯色米白背景，模特已穿上睡衣，正面站立，展示了上衣+长裤全套效果 | BGM |
| 2-2 | 中全景 | 慢推 | 模特轻微向右转体45°，展示腰部垂坠感和裤型轮廓 | BGM |
| 2-3 | 中景 | 固定 | 模特转回正面，双手自然放在两侧，展示整体版型 | BGM+快门声 |

**Prompts**:
```
[2-1] Asian female model wearing floral pajama set with pink trim collar,
full body front view, standing naturally, cream beige clean background,
soft studio lighting, fabric details visible, elegant posture,
e-commerce product showcase, 8K

[2-2] Same model in floral pajama, three-quarter view, turning slightly to side,
showing waist definition and loose fit pants silhouette,
soft lighting, clean background, professional

[2-3] Same model front view, both hands at sides, showing full outfit drape,
floral print clearly visible, pink trim details, elegant stance,
beige background, lifestyle photography
```

**参数**:
```
model: Seedance 2.0
ratio: 9:16
each duration: 4s
motion: [2-1] static / [2-2] slow dolly in / [2-3] static
```

---

### SCENE 3 — 侧面·版型验证（20-35s）

| 场号 | 景别 | 运镜 | 画面描述 | 音效 |
|------|------|------|---------|------|
| 3-1 | 全身 | 右摇 | 模特右侧面站立，展示背部线条、长裤后身效果和上衣下摆位置 | BGM |
| 3-2 | 中全景 | 固定 | 模特侧身回头看向镜头，展示领口V字设计和后背面料流动 | BGM |
| 3-3 | 中景 | 缓推 | 模特双手插口袋姿态，侧面展示口袋位置和裤型宽松度 | BGM |

**Prompts**:
```
[3-1] Same model in floral pajama, pure profile view from right side,
showing back of robe, hemline of top, and full length of pants,
elegant S-curve silhouette, clean beige background, soft light

[3-2] Same model, side profile looking back over shoulder at camera,
V-neck collar visible, fabric draping naturally,
warm ambient lighting, lifestyle feel

[3-3] Same model, hands in pockets pose, three-quarter side view,
showing pocket placement and relaxed fit of pants,
casual elegant, soft background
```

**参数**:
```
model: Seedance 2.0
ratio: 9:16
each duration: 4-5s
motion: [3-1] slow pan / [3-2] static / [3-3] slow push
```

---

### SCENE 4 — 领口特写·设计锚点（35-48s）

| 场号 | 景别 | 运镜 | 画面描述 | 音效 |
|------|------|------|---------|------|
| 4-1 | 特写 | 微距推 | 领口粉色滚边+V领设计，手指轻触领口边缘，展示面料厚度 | BGM(弱) |
| 4-2 | 大特写 | 固定 | 蝴蝶结/印花细节，花卉图样清晰可见，展示印染工艺 | BGM(弱) |
| 4-3 | 中近景 | 固定 | 模特轻拉袖口，展示粉色滚边袖口细节和面料弹性 | BGM(弱)+翻折声 |

**Prompts**:
```
[4-1] Extreme close-up of pink trim collar edge on floral pajama,
female fingers gently touching the collar fabric,
soft focus background, showing fabric thickness and stitching details,
macro product photography

[4-2] Macro close-up of floral print pattern on pajama fabric,
butterfly bow accent visible, intricate printing details,
soft diffused lighting, shallow depth of field, 8K detail

[4-3] Medium close-up, model lightly pulling sleeve cuff to show pink trim edge,
fabric stretching slightly, soft skin visible,
texture detail, natural lighting
```

**参数**:
```
model: Kling 3.0
ratio: 9:16
each duration: 4s
motion: [4-1] macro push / [4-2] static / [4-3] static
```

---

### SCENE 5 — 面料质感·信任建立（48-58s）

| 场号 | 景别 | 运镜 | 画面描述 | 音效 |
|------|------|------|---------|------|
| 5-1 | 中近景 | 缓推 | 模特手掌轻抚上衣前襟，感受面料质感的自然动作 | BGM |
| 5-2 | 特写 | 眼动 | 镜头顺着面料垂坠线往下移动，展示整件面料的流畅线条 | BGM+丝绸感音效 |
| 5-3 | 中景 | 固定 | 模特捏起上衣下摆轻轻抖动，展示面料的悬垂感和轻盈度 | BGM |

**Prompts**:
```
[5-1] Medium close-up, model gently stroking front of floral pajama top,
hand moving across fabric, showing smooth texture and comfort,
soft natural expression, warm lighting, lifestyle

[5-2] Camera tracking down along fabric drape line from shoulder to hem,
showing continuous flow of material, floral print cascading,
slow vertical movement, silk-like texture visible

[5-3] Medium shot, model pinching hem of pajama top and gently shaking,
fabric rippling naturally, showing lightweight and flowing quality,
soft motion, elegant gesture
```

**参数**:
```
model: Kling 3.0 (5-1, 5-3) / Seedance 2.0 (5-2)
ratio: 9:16
each duration: 3-4s
motion: [5-1] slow push / [5-2] vertical track / [5-3] static
```

---

### SCENE 6 — 结尾·定格收束（58-70s）

| 场号 | 景别 | 运镜 | 画面描述 | 音效 |
|------|------|------|---------|------|
| 6-1 | 全景 | 缓拉 | 回到卧室场景，模特双臂展开，自信微笑，展示全套效果 | BGM渐强→渐弱 |
| 6-2 | 中全景 | 定格 | 定帧定格画面，叠加产品名"落英缤纷·睡衣套装" | BGM尾音 |

**Prompts**:
```
[6-1] Asian female model in floral pajama set, both arms gently open,
full body shot, confident and warm smile, cozy bedroom background,
evening warm lighting, elegant finale pose, professional photography

[6-2] Same final pose, freeze frame, slightly tighter crop,
picture-perfect product presentation
```

**参数**:
```
model: Seedance 2.0
ratio: 9:16
duration: 3s + 2s freeze
motion: slow pull back → freeze
```

---

## 三、重点技术参数

### 视觉参数

| 参数 | 设置 |
|------|------|
| 主色调 | 米白(背景) + 粉色滚边(锚点) + 多花色(主体) |
| 灯光 | 柔光箱×2(左右45°) + 暖色背光(营造居家氛围) |
| 景深 | Scene 1-bg实 / Scene 2-3 背景虚 / Scene 4-5 浅景深 |
| 色温 | 4500K-5000K 暖白（不偏黄不偏蓝）|
| 模特定位 | 25-35岁亚洲女性，温婉气质，长发自然 |


### AI生成参数（关键）

```json
{
  "negative_prompt": "deformed, bad anatomy, disfigured, poorly drawn face,
  mutation, extra limbs, ugly, blurry, low quality, bad proportions,
  cloned face, watermark, text label",
  "cfg_scale": 7.0,
  "steps": 30,
  "sampler": "DPM++ 2M Karras"
}
```


## 四、成片时间线

```
00:00 ─ ─ ─ ─ 片头/广告标识 "广告" + "AI生成以实物为准" 字样
         ─ ─ 镜1-1 (持衣展示) 3s
00:03 ─ ─ ─ ─ 镜2-1 (正面全身) 4s
00:07 ─ ─ ─ ─ 镜2-2 (转体展示) 4s
00:11 ─ ─ ─ ─ 镜2-3 (正面定姿) 4s
00:15 ─ ─ ─ ─ 镜3-1 (侧面版型) 5s
00:20 ─ ─ ─ ─ 镜3-2 (侧身回眸) 4s
00:24 ─ ─ ─ ─ 镜3-3 (插袋展示) 5s
00:29 ─ ─ ─ ─ 镜4-1 (领口特写) 4s
00:33 ─ ─ ─ ─ 镜4-2 (印花特写) 4s
00:37 ─ ─ ─ ─ 镜4-3 (袖口翻折) 4s
00:41 ─ ─ ─ ─ 镜5-1 (面料抚摸) 4s
00:45 ─ ─ ─ ─ 镜5-2 (垂坠线) 4s
00:49 ─ ─ ─ ─ 镜5-3 (抖动展示) 3s
00:52 ─ ─ ─ ─ 镜6-1 (展臂收束) 4s
00:56 ─ ─ ─ ─ 镜6-2 (定帧+字幕) 14s
01:10 ─ ─ ─ ─ END
```


## 五、字幕与视觉辅助

### 屏幕文字（Overlay）

| 时间 | 位置 | 内容 | 样式 |
|------|------|------|------|
| 0-70s | 左上 | 广告 | 灰底白字，半透明，10px |
| 0-70s | 左下 | AI生成以实物为准 | 灰底白字，半透明，8px |
| 3-6s | 右上 | ✨ 强烈推荐 ✨ | 金色闪烁，旋转出现 |
| 8-11s | 右下 | 哇哦 太好看了吧 | 粉色手写体，弹跳出现 |
| 30-33s | 中下 | 粉色滚边 V领设计 | 白字黑边，从左滑入 |
| 45-48s | 中下 | 柔软亲肤 垂感十足 | 白字黑边，从右滑入 |
| 56-60s | 中 | 落英缤纷·印花睡衣套装 | 大字标题，居中 |
| 60-70s | 中下 | 点击下方购物车 立即购买 | 白字黑边，呼吸闪烁 |

---

## 六、BGM参考

| 段 | BGM风格 | 曲风参考 |
|----|---------|---------|
| 总体 | 轻电商·优雅钢琴+轻弦乐 | Lofi beats / 轻钢琴曲 |
| 开场 | 弱起，缓慢加速 | 钢琴单音起步 |
| 展示段 | 稳定节奏，轻快 | 吉他+轻鼓点 |
| 特写段 | 减弱，聚焦 | 单弦乐/pad音色 |
| 结尾 | 渐强→渐弱收尾 | 完整旋律收回 |
