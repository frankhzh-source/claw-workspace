#!/usr/bin/env python3
"""
LIBTV 分镜脚本导入工具
用法: python import_script_to_libtv.py
前置条件: 先 libtv login web 登录
"""

import json
import subprocess
import sys
import os

SCRIPT_JSON = r"C:\Users\jt\WorkBuddy\Claw\梵梵店铺_LibTV分镜脚本.json"
PROJECT_NAME = "梵梵店铺-落英缤纷"
SCRIPT_NODE_NAME = "落英缤纷分镜本"

LIBTV = os.path.expanduser(r"~/.libtv/libtv.exe")
# If not found, use PATH
if not os.path.exists(LIBTV):
    LIBTV = "libtv"

def run_libtv(cmd_args, desc=""):
    """Run a libtv command and return output."""
    full_cmd = [LIBTV] + cmd_args
    print(f"\n>>> {desc or ' '.join(cmd_args)}")
    print(f"    Running: {' '.join(full_cmd)}")
    result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        print(f"    ERROR: {result.stderr.strip()[:200]}")
        return None
    out = result.stdout.strip()
    if out:
        print(f"    {out[:300]}")
    return out

def main():
    # Step 0: Check login
    print("=" * 50)
    print(f"LIBTV 导入工具 — {PROJECT_NAME}")
    print("=" * 50)

    info = run_libtv(["account", "info"], "检查登录状态")
    if info is None or "login" in info.lower() or "unauthenticated" in info.lower():
        print("\n⚠️  未登录！请先运行: libtv login web")
        sys.exit(1)
    print("✅ 已登录")

    # Step 1: Create project
    proj_out = run_libtv(
        ["project", "create", PROJECT_NAME],
        f"创建项目「{PROJECT_NAME}」"
    )

    # Step 2: Use the project
    run_libtv(
        ["project", "use", PROJECT_NAME],
        f"绑定项目「{PROJECT_NAME}」"
    )

    # Step 3: Create script node
    node_out = run_libtv(
        ["node", "create", SCRIPT_NODE_NAME, "-t", "script"],
        f"创建脚本节点「{SCRIPT_NODE_NAME}」"
    )
    if node_out is None:
        # Maybe node already exists, try using it directly
        print("    ⚠️  节点可能已存在，尝试直接更新...")

    # Step 4: Read JSON and extract rows
    print(f"\n>>> 读取分镜数据: {SCRIPT_JSON}")
    with open(SCRIPT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    rows = data["rows"]
    print(f"    ✅ 读取到 {len(rows)} 个镜头")

    # Step 5: Update rows on the script node
    # Convert rows to a compact JSON string for the command line
    rows_json = json.dumps(rows, ensure_ascii=False)

    # Use a temp file for the rows data to avoid command line length issues
    temp_rows_file = os.path.join(os.path.dirname(SCRIPT_JSON), "_rows_data.json")
    with open(temp_rows_file, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    print(f"    ✅ 分镜数据已写入临时文件: {temp_rows_file}")

    # Update with -u rows=... using the JSON string
    # For safety, write a small Python script that does the update
    update_py = os.path.join(os.path.dirname(SCRIPT_JSON), "_run_update.py")
    with open(update_py, "w", encoding="utf-8") as f:
        f.write(f'''
import json, subprocess, os

LIBTV = r"{LIBTV}"
rows_file = r"{temp_rows_file}"
node_name = "{SCRIPT_NODE_NAME}"

with open(rows_file, "r", encoding="utf-8") as f:
    rows = json.load(f)

rows_compact = json.dumps(rows, ensure_ascii=False)

# Use -u to update rows
result = subprocess.run(
    [LIBTV, "node", node_name, "-u", f"rows={{rows_compact}}"],
    capture_output=True, text=True, timeout=60
)
if result.returncode == 0:
    print("✅ 分镜数据导入成功!")
    print(result.stdout[:500])
else:
    print(f"❌ 导入失败: {{result.stderr[:500]}}")
    # Try alternative: split into chunks
    print("尝试分段导入...")
''')
    
    run_result = subprocess.run(
        [sys.executable, update_py],
        capture_output=True, text=True, timeout=60
    )
    print(run_result.stdout)
    if run_result.stderr:
        print(f"    STDERR: {run_result.stderr[:300]}")

    # Clean up temp files
    for f in [temp_rows_file, update_py]:
        if os.path.exists(f):
            os.remove(f)

    print("\n" + "=" * 50)
    print("导入流程完成！接下来在 LibTV 网页端：")
    print(f"  1. 打开项目「{PROJECT_NAME}」")
    print(f"  2. 找到脚本节点「{SCRIPT_NODE_NAME}」")
    print("  3. 检查分镜表是否包含15行数据")
    print("  4. 点击「生成分镜」出图")
    print("=" * 50)

if __name__ == "__main__":
    main()
