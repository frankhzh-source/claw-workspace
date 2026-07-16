@echo off
REM Elite Memory CLI — 全局快捷入口
REM 放到 PATH 任意目录，即可在任何终端/AI中直接调用 elite

set ELITE_PYTHON=%USERPROFILE%\.workbuddy\binaries\python\envs\default\Scripts\python.exe
set ELITE_SCRIPT=%USERPROFILE%\WorkBuddy\Claw\elite.py

if not exist "%ELITE_PYTHON%" set ELITE_PYTHON=%USERPROFILE%\.workbuddy\binaries\python\versions\3.13.12\python.exe
if not exist "%ELITE_SCRIPT%" set ELITE_SCRIPT=C:\Users\jt\WorkBuddy\Claw\elite.py

if "%~1"=="" (
    "%ELITE_PYTHON%" "%ELITE_SCRIPT%"
) else (
    "%ELITE_PYTHON%" "%ELITE_SCRIPT%" %*
)
