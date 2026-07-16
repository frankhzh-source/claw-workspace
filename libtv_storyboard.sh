#!/bin/bash
# ================================================================
# LibTV 可执行分镜脚本 — 梵梵店铺 0623 复刻
# 商品：落英缤纷·印花睡衣套装
# ================================================================
# 使用方法：
#   1. 先手动登录：libtv login web
#   2. 修改下方案 PRODUCT_IMAGE 路径为你的商品图
#   3. 运行本脚本：bash libtv_storyboard.sh
# ================================================================

set -e

# ==================== 用户需修改 ====================
PRODUCT_IMAGE="C:/Users/jt/Desktop/lib练习素材/CTR潜力爆款/落英缤纷/透明图 (1).png"
WORKSPACE_NAME="落英缤纷-复刻计划"
CANVAS_NAME="梵梵店铺复刻-落英缤纷"
# ====================================================

echo "=== Phase 0: 初始化项目 ==="

# 创建工作区
WORKSPACE_OUTPUT=$(libtv workspace create "$WORKSPACE_NAME" 2>&1)
WORKSPACE_ID=$(echo "$WORKSPACE_OUTPUT" | grep -oP '"id"\s*:\s*"\K[^"]+')
echo "工作区 ID: $WORKSPACE_ID"
libtv workspace use "$WORKSPACE_ID"

# 创建画布
CANVAS_OUTPUT=$(libtv project create "$CANVAS_NAME" 2>&1)
CANVAS_ID=$(echo "$CANVAS_OUTPUT" | grep -oP '"uuid"\s*:\s*"\K[^"]+')
echo "画布 UUID: $CANVAS_ID"
libtv project use "$CANVAS_ID"

echo ""
echo "=== Phase 1: 上传商品素材 ==="

libtv upload "落英缤纷-平铺图" -t image -f "$PRODUCT_IMAGE"

echo ""
echo "=== Phase 2: 搭建6个镜头图片节点 ==="

# 镜1：开场·持衣展示
libtv node create "镜1-开场" -t image \
  --left "落英缤纷-平铺图" \
  -s "model=Seedance 2.0" \
  -s prompt="Asian female model, holding floral pajama set on a hanger in right hand, cozy bedroom background with warm lamplight and soft beige walls, full body shot, natural smile, elegant standing pose, professional e-commerce photography, soft volumetric lighting, 8K quality" \
  -s ratio=9:16 \
  -s count=2

# 镜2-1：全身正面
libtv node create "镜2-全身正面" -t image \
  --left "落英缤纷-平铺图" \
  -s "model=Seedance 2.0" \
  -s prompt="Asian female model wearing floral pajama set with pink trim collar, full body front view, standing naturally, cream beige clean background, soft studio lighting, fabric details visible, elegant posture, e-commerce product showcase, 8K" \
  -s ratio=9:16 \
  -s count=2

# 镜2-2：转体展示
libtv node create "镜2-转体" -t image \
  --left "落英缤纷-平铺图" \
  -s "model=Seedance 2.0" \
  -s prompt="Same model in floral pajama, three-quarter view, turning slightly to side, showing waist definition and loose fit pants silhouette, soft lighting, clean background, professional" \
  -s ratio=9:16

# 镜3-1：侧面版型
libtv node create "镜3-侧面" -t image \
  --left "落英缤纷-平铺图" \
  -s "model=Seedance 2.0" \
  -s prompt="Same model in floral pajama, pure profile view from right side, showing back of robe, hemline of top, and full length of pants, elegant S-curve silhouette, clean beige background, soft light" \
  -s ratio=9:16

# 镜3-2：侧身回眸
libtv node create "镜3-回眸" -t image \
  --left "落英缤纷-平铺图" \
  -s "model=Seedance 2.0" \
  -s prompt="Same model, side profile looking back over shoulder at camera, V-neck collar visible, fabric draping naturally, warm ambient lighting, lifestyle feel" \
  -s ratio=9:16

# 镜4-1：领口特写
libtv node create "镜4-领口特写" -t image \
  --left "落英缤纷-平铺图" \
  -s "model=Kling 3.0" \
  -s prompt="Extreme close-up of pink trim collar edge on floral pajama, female fingers gently touching the collar fabric, soft focus background, showing fabric thickness and stitching details, macro product photography" \
  -s ratio=9:16

# 镜4-2：印花特写
libtv node create "镜4-印花特写" -t image \
  --left "落英缤纷-平铺图" \
  -s "model=Kling 3.0" \
  -s prompt="Macro close-up of floral print pattern on pajama fabric, butterfly bow accent visible, intricate printing details, soft diffused lighting, shallow depth of field, 8K detail" \
  -s ratio=9:16

# 镜5-1：面料抚摸
libtv node create "镜5-面料" -t image \
  --left "落英缤纷-平铺图" \
  -s "model=Kling 3.0" \
  -s prompt="Medium close-up, model gently stroking front of floral pajama top, hand moving across fabric, showing smooth texture and comfort, soft natural expression, warm lighting, lifestyle" \
  -s ratio=9:16

# 镜5-3：抖动展示
libtv node create "镜5-抖动" -t image \
  --left "落英缤纷-平铺图" \
  -s "model=Kling 3.0" \
  -s prompt="Medium shot, model pinching hem of pajama top and gently shaking, fabric rippling naturally, showing lightweight and flowing quality, soft motion, elegant gesture" \
  -s ratio=9:16

# 镜6-1：结尾定格
libtv node create "镜6-结尾" -t image \
  --left "落英缤纷-平铺图" \
  -s "model=Seedance 2.0" \
  -s prompt="Asian female model in floral pajama set, both arms gently open, full body shot, confident and warm smile, cozy bedroom background, evening warm lighting, elegant finale pose" \
  -s ratio=9:16

echo ""
echo "=== Phase 3: 图片转视频节点 ==="

# 开场3s → video
libtv node create "vid-开场" -t video \
  --left "镜1-开场" \
  -s "model=Kling 3.0" \
  -s prompt="woman holding pajama, slow zoom in, subtle natural movement" \
  -s ratio=9:16

# 全身正面4s → video
libtv node create "vid-全身正面" -t video \
  --left "镜2-全身正面" \
  -s "model=Seedance 2.0" \
  -s prompt="woman turning slowly, full body showcase, fabric flowing naturally" \
  -s ratio=9:16

# 转体4s → video
libtv node create "vid-转体" -t video \
  --left "镜2-转体" \
  -s "model=Seedance 2.0" \
  -s prompt="woman side turning, slight body rotation, elegant fabric movement" \
  -s ratio=9:16

# 侧面5s → video
libtv node create "vid-侧面" -t video \
  --left "镜3-侧面" \
  -s "model=Seedance 2.0" \
  -s prompt="woman profile, subtle sway, fabric draping naturally" \
  -s ratio=9:16

# 回眸4s → video
libtv node create "vid-回眸" -t video \
  --left "镜3-回眸" \
  -s "model=Seedance 2.0" \
  -s prompt="woman looking back over shoulder, gentle turn, elegant" \
  -s ratio=9:16

# 领口特写4s → video
libtv node create "vid-领口" -t video \
  --left "镜4-领口特写" \
  -s "model=Kling 3.0" \
  -s prompt="slow zoom to collar, hand touching fabric, subtle motion" \
  -s ratio=9:16

# 印花特写4s → video
libtv node create "vid-印花" -t video \
  --left "镜4-印花特写" \
  -s "model=Kling 3.0" \
  -s prompt="macro slow push, fabric print detail, gentle camera movement" \
  -s ratio=9:16

# 面料4s → video
libtv node create "vid-面料" -t video \
  --left "镜5-面料" \
  -s "model=Kling 3.0" \
  -s prompt="hand stroking fabric, soft movement, texture detail visible" \
  -s ratio=9:16

# 抖动3s → video
libtv node create "vid-抖动" -t video \
  --left "镜5-抖动" \
  -s "model=Kling 3.0" \
  -s prompt="fabric shaking gently, rippling effect, lightweight material" \
  -s ratio=9:16

# 结尾4s → video
libtv node create "vid-结尾" -t video \
  --left "镜6-结尾" \
  -s "model=Seedance 2.0" \
  -s prompt="woman arms open, confident smile, slow pull back, finale pose" \
  -s ratio=9:16

echo ""
echo "=== Phase 4: 创建视频合成节点 ==="
echo "⚠️ 请将所有 vid-* 节点手动连线到合成节点，或在LibTV网页端操作"
echo ""
echo "=== 全部搭建完成 ==="
echo "在LibTV网页端打开以下画布："
echo "https://www.liblib.tv/canvas?projectId=$CANVAS_ID"
echo ""
echo "网页端后续步骤："
echo "1. 逐个选中 image 节点 → 点击 Run 生成图片"
echo "2. 图片生成后 → 逐个选中 video 节点 → 点击 Run 生成视频片段"
echo "3. 创建 video-clip 节点 → 将所有 vid-* 节点连入 → 填入时间线 → Run 合成"
