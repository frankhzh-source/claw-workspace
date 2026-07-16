#!/usr/bin/env python
"""测试lark-cli调用"""
import subprocess, sys

LARK_BAT = r"C:\Users\jt\.workbuddy\binaries\lark-cli.bat"

# 先测试lark-cli是否可用
args = [LARK_BAT, "base", "+field-create",
        "--base-token=CX8hb3C0WaYhUasvN1GcxNosn0c",
        "--as", "user",
        "--table-id=tblQ3dxBCj3NQf4L",
        '--json={"name":"测试字段","type":"text"}']

r = subprocess.run(args, capture_output=True, text=True, cwd=r"C:\Users\jt")
print("STDOUT:", r.stdout[:500])
print("STDERR:", r.stderr[:500])
print("RC:", r.returncode)
