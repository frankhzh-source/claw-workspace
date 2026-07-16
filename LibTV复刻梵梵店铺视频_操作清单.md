# LibTV 复刻梵梵店铺视频 — 操作清单

**目标**：用 LibTV 复刻"梵梵店铺0623.mp4"的 AI 虚拟模特带货视频
**商品**：落英缤纷印花睡衣套装（开衫+长裤，花卉印花+粉色滚边）
**参考文件**：`C:\Users\jt\Desktop\lib练习素材\CTR潜力爆款\落英缤纷\透明图 (1).png`

---

## Phase 0：前置准备（已完成）

- [x] LibTV CLI v1.1.1 已安装（`libtv --help` 确认）
- [x] 已登录（`libtv login web` → 扫码）
- [ ] 创建项目工作区
- [ ] 创建画布
- [ ] 绑定画布到当前目录

```bash
# 1. 创建工作区
libtv workspace create "落英缤纷-复刻计划"

# 2. 创建工作区后拿到 workspaceId，绑定到目录
libtv workspace use <workspaceId>

# 3. 在项目下创建画布
libtv project create "梵梵店铺复刻-落英缤纷"

# 4. 拿到画布 UUID，绑定到目录
libtv project use <画布UUID>

# 5. 创建分组管理每个镜头
libtv group create "开场镜头"
libtv group create "全身展示"
libtv group create "侧面版型"
libtv group create "领口特写"
libtv group create "面料展示"
libtv group create "结尾定版"
```

---

## Phase 1：上传商品素材

```bash
# 上传商品透明底图（核心参考素材）
libtv upload "落英缤纷-平铺图" -t image -f "C:\Users\jt\Desktop\lib练习素材\CTR潜力爆款\落英缤纷\透明图 (1).png"

# 上传店铺背景参考图（可先用梵梵原视频的关键帧做背景参考）
libtv upload "商品上身参考" -t image -f "<上身图路径>"

# 确认素材已上传
libtv node "落英缤纷-平铺图"
```

---

## Phase 2：搭建分镜工作流（6镜头）

### 2.1 创建剧本节点

```bash
libtv node create "落英缤纷-剧本" -t script \
  --name "落英缤纷-剧本" \
  -u rows='[
    {"shot":"开场","description":"店铺背景，模特手持衣架展示睡衣，自然微笑"},
    {"shot":"全身正面","description":"纯色背景，模特全身正面站立，轻微转体展示版型"},
    {"shot":"侧面版型","description":"模特侧身45°，展示腰线、裤型、垂坠感"},
    {"shot":"领口特写","description":"近景推近，粉色滚边领口+V领设计，手部轻触"},
    {"shot":"面料展示","description":"中景，手部抚摸面料，展示面料质感和垂感"},
    {"shot":"结尾定格","description":"回到店铺背景，双臂展开，微笑定格"}
  ]'
```

### 2.2 从剧本生成 storyboard（一键分镜）

```bash
libtv node "落英缤纷-剧本" --left "落英缤纷-平铺图"
libtv node create "落英缤纷-分镜" -t storyboard --left "落英缤纷-剧本" --run
```

### 2.3 逐个镜头生成图片

**镜头1：开场店铺场景 — AI模特持衣展示**

```bash
libtv node create "镜1-开场" -t image \
  --left "落英缤纷-平铺图" \
  -s "model=Seedance 2.0" \
  -s prompt="Asian female model holding floral pajama set on hanger, cozy bedroom background, warm lighting, full body, elegant pose, professional product photography, 8k quality" \
  -s ratio=9:16 \
  --run
```

**镜头2：全身正面展示 — 纯色背景**

```bash
libtv node create "镜2-全身正面" -t image \
  --left "落英缤纷-平铺图" \
  -s "model=Seedance 2.0" \
  -s prompt="Asian female model wearing floral pajama set with pink trim, full body front view, standing pose, beige clean background, soft studio lighting, 8k quality" \
  -s ratio=9:16 \
  --run
```

**镜头3：侧面版型展示**

```bash
libtv node create "镜3-侧面版型" -t image \
  --left "落英缤纷-平铺图" \
  -s "model=Seedance 2.0" \
  -s prompt="Asian female model wearing floral pajama, side view 45 degree, showing waist line and loose fit pants, elegant silhouette, beige background, soft lighting" \
  -s ratio=9:16 \
  --run
```

**镜头4：领口特写**

```bash
libtv node create "镜4-领口特写" -t image \
  --left "落英缤纷-平铺图" \
  -s "model=Kling 3.0" \
  -s prompt="Close up of pink trim collar and V-neck design on floral pajama, hand gently touching collar, soft focus background, fabric texture visible" \
  -s ratio=9:16 \
  --run
```

**镜头5：面料细节展示**

```bash
libtv node create "镜5-面料展示" -t image \
  --left "落英缤纷-平铺图" \
  -s "model=Kling 3.0" \
  -s prompt="Hand touching smooth fabric of floral pajama, medium shot, showing fabric texture and drape, soft natural lighting, luxury loungewear feel" \
  -s ratio=9:16 \
  --run
```

**镜头6：结尾定格**

```bash
libtv node create "镜6-结尾定格" -t image \
  --left "落英缤纷-平铺图" \
  -s "model=Seedance 2.0" \
  -s prompt="Asian female model in floral pajama set, both arms slightly open, full body, confident smile, cozy bedroom background, warm evening light" \
  -s ratio=9:16 \
  --run
```

---

## Phase 3：图片转视频片段（关键步骤）

每个镜头的静态图生成后，转为2-3秒短视频：

```bash
# 镜1：开场3秒
libtv node create "vid-开场" -t video \
  --left "镜1-开场" \
  -s "model=Kling 3.0" \
  -s prompt="woman holding pajama, slow zoom in, subtle movement, natural" \
  -s ratio=9:16 \
  --run

# 镜2：全身展示4秒（轻微转体）
libtv node create "vid-全身" -t video \
  --left "镜2-全身正面" \
  -s "model=Seedance 2.0" \
  -s prompt="woman turning slowly, full body showcase, fabric flowing naturally" \
  -s ratio=9:16 \
  --run

# 镜3：侧面展示4秒
libtv node create "vid-侧面" -t video \
  --left "镜3-侧面版型" \
  -s "model=Seedance 2.0" \
  -s prompt="woman side view, slight body turn, elegant" \
  -s ratio=9:16 \
  --run

# 镜4：特写3秒
libtv node create "vid-领口" -t video \
  --left "镜4-领口特写" \
  -s "model=Kling 3.0" \
  -s prompt="slow zoom to collar, hand touching fabric, subtle motion" \
  -s ratio=9:16 \
  --run

# 镜5：面料展示3秒
libtv node create "vid-面料" -t video \
  --left "镜5-面料展示" \
  -s "model=Kling 3.0" \
  -s prompt="hand stroking fabric, soft movement, texture detail" \
  -s ratio=9:16 \
  --run

# 镜6：结尾定版2秒
libtv node create "vid-结尾" -t video \
  --left "镜6-结尾定格" \
  -s "model=Seedance 2.0" \
  -s prompt="woman smiling, both arms open, final pose, gentle" \
  -s ratio=9:16 \
  --run
```

---

## Phase 4：音频节点（BGM+配音）

```bash
# 上传或选择BGM
libtv upload "BGM-轻快电商" -t audio -f "<BGM文件路径>"

# 可选：配音文本节点
libtv node create "配音文案" -t text \
  -s "model=GVLM 3.1" \
  -s prompt='写一段15秒商品配音文案：落英缤纷睡衣套装，花卉印花，粉色滚边，柔软亲肤，居家必备。语气温柔有亲和力。' \
  --run
```

---

## Phase 5：视频合成（最关键一步）

按时间线拼接所有视频片段 + 加BGM：

```bash
# 建视频合成节点
libtv node create "最终合成" -t video-clip \
  --name "落英缤纷-成片" \
  --left "vid-开场" --left "vid-全身" --left "vid-侧面" \
  --left "vid-领口" --left "vid-面料" --left "vid-结尾" \
  --left "BGM-轻快电商" \
  -u 'clipTimelineData={
    "clips":[
      {"sourceNodeId":"vid-开场","startTime":0,"duration":3,"sourceOffset":0,"sourceDuration":3},
      {"sourceNodeId":"vid-全身","startTime":3,"duration":4,"sourceOffset":0,"sourceDuration":4},
      {"sourceNodeId":"vid-侧面","startTime":7,"duration":4,"sourceOffset":0,"sourceDuration":4},
      {"sourceNodeId":"vid-领口","startTime":11,"duration":3,"sourceOffset":0,"sourceDuration":3},
      {"sourceNodeId":"vid-面料","startTime":14,"duration":3,"sourceOffset":0,"sourceDuration":3},
      {"sourceNodeId":"vid-结尾","startTime":17,"duration":2,"sourceOffset":0,"sourceDuration":2}
    ]
  }' \
  --run
```

---

## Phase 6：导出与发布

```bash
# 等待合成完成后，查看画布详情获取输出
libtv project <画布UUID>

# 下载成片（从网页端导出更方便）
# 打开链接查看画布：https://www.liblib.tv/canvas?projectId=<画布UUID>
```

---

## 检查清单（全部打勾后发布）

- [ ] 商品透明图上传成功
- [ ] 6个分镜头图片均已生成
- [ ] 6段视频片段均已生成
- [ ] BGM已上传并连接
- [ ] 时间线拼接正确（时长19s左右）
- [ ] 预览检查无抖帧/跳帧
- [ ] 导出成片
- [ ] 成片时长对标梵梵原视频（60-70s，可以多轮循环）

---

## > 关键参数备忘

| 场景 | 推荐模型 | 运镜 | 时长 |
|------|---------|------|------|
| 开场/结尾 | Seedance 2.0 | 缓推 | 3s |
| 全身展示 | Seedance 2.0 | 慢转 | 4s |
| 侧面/摆姿 | Seedance 2.0 | 轻微晃动 | 4s |
| 特写/细节 | Kling 3.0 | 推近 | 3s |
| 面料/触感 | Kling 3.0 | 微距 | 3s |
