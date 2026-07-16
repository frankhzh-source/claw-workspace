@echo off
chcp 65001 >nul
echo =============================================
echo   LIBTV 分镜脚本一键导入
echo   梵梵店铺 — 落英缤纷·印花睡衣套装
echo =============================================
echo.
echo 步骤 1/4: 检查登录状态...
libtv account info >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  未登录！正在打开登录链接...
    start https://www.liblib.tv/zh/login
    echo 请扫码登录后，按任意键继续...
    pause >nul
)
echo ✅ 已登录
echo.
echo 步骤 2/4: 创建项目「梵梵店铺-落英缤纷」...
libtv project create "梵梵店铺-落英缤纷" >nul 2>&1
if %errorlevel% equ 0 ( echo ✅ 项目创建成功 ) else ( echo ⚠️  项目可能已存在，继续... )
libtv project use "梵梵店铺-落英缤纷"
echo.
echo 步骤 3/4: 创建脚本节点并导入分镜数据...
python "%~dp0import_script_to_libtv.py"
echo.
echo 步骤 4/4: 完成！
echo.
echo 接下来在 LibTV 网页端：
echo   1. 打开项目「梵梵店铺-落英缤纷」
echo   2. 找到脚本节点「落英缤纷分镜本」
echo   3. 检查分镜表是否包含全部15个镜头
echo   4. 点击「生成分镜」出图
echo.
pause
