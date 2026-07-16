@echo off
REM Workspace-local lark-cli wrapper (Windows batch)
REM Redirect USERPROFILE to workspace to avoid sandbox triggers
set USERPROFILE=C:\Users\jt\WorkBuddy\Claw
set HOME=C:\Users\jt\WorkBuddy\Claw

"C:\Users\jt\.workbuddy\binaries\node\workspace\node_modules\@larksuite\cli\bin\lark-cli.exe" %*
