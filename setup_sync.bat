@echo off
chcp 65001 >nul
echo ========================================
echo   WorkBuddy 跨电脑同步 - 初始化脚本
echo   适用于新电脑/恢复环境
echo ========================================
echo.

set HOME=%USERPROFILE%
set WB_HOME=%HOME%\.workbuddy
set SYNC_DIR=%HOME%\workbuddy-sync

:: ============================================
:: Step 1: 克隆 workbuddy-sync（用户级记忆）
:: ============================================
echo [1/4] 克隆用户记忆仓库...
if exist "%SYNC_DIR%" (
    echo   已存在，跳过克隆
    cd /d "%SYNC_DIR%"
    git pull
) else (
    git clone https://github.com/frankhzh-source/workbuddy-sync.git "%SYNC_DIR%"
    cd /d "%SYNC_DIR%"
)
if %ERRORLEVEL% NEQ 0 (
    echo   [错误] workbuddy-sync 操作失败
    goto :error
)
echo   [完成]

:: ============================================
:: Step 2: 恢复用户文件到 ~/.workbuddy/
:: ============================================
echo [2/4] 恢复用户记忆到 WorkBuddy...

if not exist "%WB_HOME%" mkdir "%WB_HOME%"

copy /Y "%SYNC_DIR%\MEMORY.md"   "%WB_HOME%\MEMORY.md"   >nul
copy /Y "%SYNC_DIR%\SOUL.md"     "%WB_HOME%\SOUL.md"     >nul
copy /Y "%SYNC_DIR%\IDENTITY.md" "%WB_HOME%\IDENTITY.md" >nul
copy /Y "%SYNC_DIR%\USER.md"     "%WB_HOME%\USER.md"     >nul
copy /Y "%SYNC_DIR%\mcp.json"    "%WB_HOME%\.mcp.json"   >nul

:: 恢复 skills
if exist "%WB_HOME%\skills" rmdir /S /Q "%WB_HOME%\skills"
xcopy /E /I /Q "%SYNC_DIR%\skills" "%WB_HOME%\skills"

echo   [完成]

:: ============================================
:: Step 3: 克隆 claw-workspace（项目文件）
:: ============================================
echo [3/4] 克隆项目工作空间...
set CLAW_DIR=%HOME%\WorkBuddy\Claw
set CLAW_REPO=https://github.com/frankhzh-source/claw-workspace.git

if exist "%CLAW_DIR%\.git" (
    echo   已存在，git pull 更新...
    cd /d "%CLAW_DIR%"
    git pull
) else (
    if not exist "%CLAW_DIR%" mkdir "%CLAW_DIR%"
    git clone "%CLAW_REPO%" "%CLAW_DIR%"
    cd /d "%CLAW_DIR%"
)

if %ERRORLEVEL% NEQ 0 (
    echo   [警告] claw-workspace 操作可能失败，请检查网络
)
echo   [完成]

:: ============================================
:: Step 4: 确认
:: ============================================
echo [4/4] 验证...
echo.
echo   WorkBuddy 用户记忆: %WB_HOME%
echo   项目工作空间:       %CLAW_DIR%
echo   sync_all.py 位置:   %CLAW_DIR%\sync_all.py
echo.
echo ========================================
echo   同步初始化完成！
echo ========================================
echo.
echo 后续日常使用：
echo   - 当前电脑会在自动化中自动 push 变更
echo   - 在对面电脑运行本脚本即可恢复
echo   - 手动同步: cd %CLAW_DIR% ^&^& python sync_all.py push
echo.
pause
goto :end

:error
echo.
echo ========================================
echo   初始化失败，请检查：
echo   1. Git 是否已安装
echo   2. 网络是否能访问 GitHub
echo   3. 账户是否有仓库访问权限
echo ========================================
pause

:end
