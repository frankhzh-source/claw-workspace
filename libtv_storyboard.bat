@echo off
chcp 65001 >nul
REM ================================================================
REM LibTV 可执行分镜脚本 — 梵梵店铺 0623 复刻（Windows版）
REM 商品：落英缤纷·印花睡衣套装
REM ================================================================
REM 使用方法：
REM   1. 先手动登录：libtv login web
REM   2. 修改下方 PRODUCT_IMAGE 路径
REM   3. 双击运行本脚本
REM ================================================================

set PATH=%USERPROFILE%\.libtv;%PATH%

set PRODUCT_IMAGE=C:\Users\jt\Desktop\lib练习素材\CTR潜力爆款\落英缤纷\透明图 (1).png
set CANVAS_NAME=梵梵店铺复刻-落英缤纷

echo === Phase 0: 初始化项目 ===

libtv workspace create "落英缤纷-复刻计划" >nul
for /f "tokens=2 delims=:," %%a in ('libtv workspace list --json ^| findstr "id"') do (
  set WS_ID=%%a
  goto :ws_done
)
:ws_done
set WS_ID=%WS_ID:"=%
set WS_ID=%WS_ID: =%
libtv workspace use %WS_ID%

libtv project create "%CANVAS_NAME%" >nul
for /f "tokens=2 delims=:," %%a in ('libtv project list --json ^| findstr "uuid"') do (
  set PR_ID=%%a
  goto :pr_done
)
:pr_done
set PR_ID=%PR_ID:"=%
set PR_ID=%PR_ID: =%
libtv project use %PR_ID%

echo 画布已创建，UUID: %PR_ID%

echo.
echo === Phase 1: 上传商品素材 ===

libtv upload "落英缤纷-平铺图" -t image -f "%PRODUCT_IMAGE%"

echo.
echo === Phase 2: 搭建6个镜头图片节点 ===

libtv node create "镜1-开场" -t image --left "落英缤纷-平铺图" -s "model=Seedance 2.0" -s prompt="Asian female model, holding floral pajama set on a hanger in right hand, cozy bedroom background, warm lamplight, full body, elegant, 8K" -s ratio=9:16 -s count=2

libtv node create "镜2-全身正面" -t image --left "落英缤纷-平铺图" -s "model=Seedance 2.0" -s prompt="Asian female model wearing floral pajama set with pink trim, full body front view, cream beige background, soft studio lighting, elegant posture, 8K" -s ratio=9:16 -s count=2

libtv node create "镜2-转体" -t image --left "落英缤纷-平铺图" -s "model=Seedance 2.0" -s prompt="Same model three-quarter view, turning slightly, showing waist and pants silhouette, beige background" -s ratio=9:16

libtv node create "镜3-侧面" -t image --left "落英缤纷-平铺图" -s "model=Seedance 2.0" -s prompt="Same model pure profile view, showing back of robe and pants, S-curve silhouette, beige background, soft light" -s ratio=9:16

libtv node create "镜3-回眸" -t image --left "落英缤纷-平铺图" -s "model=Seedance 2.0" -s prompt="Same model looking back over shoulder, V-neck visible, fabric draping naturally, warm lighting, lifestyle" -s ratio=9:16

libtv node create "镜4-领口特写" -t image --left "落英缤纷-平铺图" -s "model=Kling 3.0" -s prompt="Extreme close-up pink trim collar, fingers touching, soft focus bg, fabric stitching detail, macro" -s ratio=9:16

libtv node create "镜4-印花特写" -t image --left "落英缤纷-平铺图" -s "model=Kling 3.0" -s prompt="Macro close-up floral print pattern, butterfly bow accent, intricate details, shallow depth of field, 8K" -s ratio=9:16

libtv node create "镜5-面料" -t image --left "落英缤纷-平铺图" -s "model=Kling 3.0" -s prompt="Medium close-up model stroking front of pajama top, hand moving across fabric, smooth texture, natural expression" -s ratio=9:16

libtv node create "镜5-抖动" -t image --left "落英缤纷-平铺图" -s "model=Kling 3.0" -s prompt="Model pinching hem and shaking gently, fabric rippling, lightweight quality, elegant gesture" -s ratio=9:16

libtv node create "镜6-结尾" -t image --left "落英缤纷-平铺图" -s "model=Seedance 2.0" -s prompt="Asian female model both arms gently open, full body, confident smile, cozy bedroom background, warm lighting, finale" -s ratio=9:16

echo.
echo === Phase 3: 图片转视频节点 ===

libtv node create "vid-开场" -t video --left "镜1-开场" -s "model=Kling 3.0" -s prompt="woman holding pajama, slow zoom in, subtle movement" -s ratio=9:16
libtv node create "vid-全身正面" -t video --left "镜2-全身正面" -s "model=Seedance 2.0" -s prompt="woman turning slowly, full body showcase" -s ratio=9:16
libtv node create "vid-转体" -t video --left "镜2-转体" -s "model=Seedance 2.0" -s prompt="woman side turning, elegant fabric movement" -s ratio=9:16
libtv node create "vid-侧面" -t video --left "镜3-侧面" -s "model=Seedance 2.0" -s prompt="woman profile, subtle sway, natural" -s ratio=9:16
libtv node create "vid-回眸" -t video --left "镜3-回眸" -s "model=Seedance 2.0" -s prompt="woman looking back, gentle turn" -s ratio=9:16
libtv node create "vid-领口" -t video --left "镜4-领口特写" -s "model=Kling 3.0" -s prompt="slow zoom collar, hand touching, subtle" -s ratio=9:16
libtv node create "vid-印花" -t video --left "镜4-印花特写" -s "model=Kling 3.0" -s prompt="macro slow push, detail movement" -s ratio=9:16
libtv node create "vid-面料" -t video --left "镜5-面料" -s "model=Kling 3.0" -s prompt="hand stroking fabric, soft texture" -s ratio=9:16
libtv node create "vid-抖动" -t video --left "镜5-抖动" -s "model=Kling 3.0" -s prompt="fabric shaking gently, rippling" -s ratio=9:16
libtv node create "vid-结尾" -t video --left "镜6-结尾" -s "model=Seedance 2.0" -s prompt="woman arms open, slow pull back" -s ratio=9:16

echo.
echo ====================================
echo  全部搭建完成！
echo ====================================
echo.
echo 在LibTV网页端打开画布操作：
echo https://www.liblib.tv/canvas?projectId=%PR_ID%
echo.
echo 后续步骤（手动）：
echo 1. 依次选中 image 节点 → 点 Run 生成图片
echo 2. 图片就绪后 → 选中 video 节点 → 点 Run 生成视频
echo 3. 创建 video-clip 节点 → 连入所有 vid-* → 填时间线合成
echo.
pause
