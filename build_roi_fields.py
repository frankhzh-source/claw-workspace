#!/usr/bin/env python
"""批量添加字段到飞书多维表格ROI Base"""
import subprocess, json, time, sys

BASE="CX8hb3C0WaYhUasvN1GcxNosn0c"
LARK = r"C:\Users\jt\.workbuddy\binaries\lark-cli.bat"

def add_field(table_id, field_def):
    args = [LARK, "base", "+field-create",
            f"--base-token={BASE}",
            "--as", "user",
            f"--table-id={table_id}",
            f"--json={json.dumps(field_def, ensure_ascii=False)}"]
    r = subprocess.run(args, capture_output=True, text=True, cwd=r"C:\Users\jt")
    ok = '"ok": true' in r.stdout or '"created": true' in r.stdout
    print(f"  {field_def['name']}: {'OK' if ok else 'FAIL'}", flush=True)
    time.sleep(0.5)
    return ok

def add_fields(table_id, name, fields):
    print(f"\n=== {name} ===")
    for f in fields:
        add_field(table_id, f)

# === 收益侧分类 (tblQ3dxBCj3NQf4L) ===
add_fields("tblQ3dxBCj3NQf4L", "收益侧分类", [
    {"name":"计算公式","type":"text"},
    {"name":"案例","type":"text"},
    {"name":"可信度","type":"select","multiple":False,
     "options":[{"name":"⭐⭐⭐⭐⭐","hue":"Green","lightness":"Light"},
                {"name":"⭐⭐⭐⭐","hue":"Blue","lightness":"Light"},
                {"name":"⭐⭐⭐","hue":"Orange","lightness":"Light"}]}
])

# === 四阶段ROI模型 (tblfZeM11uVgPyP5) ===
add_fields("tblfZeM11uVgPyP5", "四阶段ROI模型", [
    {"name":"时间窗口","type":"text"},
    {"name":"核心问题","type":"text"},
    {"name":"度量方法","type":"text"},
    {"name":"关键指标","type":"text"},
    {"name":"通过标准","type":"text"}
])

# === 行业对标基准 (tbloxiVML1Bl0Qsm) ===
add_fields("tbloxiVML1Bl0Qsm", "行业对标基准", [
    {"name":"典型Agent场景","type":"text"},
    {"name":"规模化期ROI参考","type":"text"},
    {"name":"关键决定因素","type":"text"},
    {"name":"标杆案例","type":"text"}
])

# === 电商场景ROI精算 (tbldnnb5lfrD9Mhl) ===
add_fields("tbldnnb5lfrD9Mhl", "电商场景ROI精算", [
    {"name":"优先级","type":"select","multiple":False,
     "options":[{"name":"P0","hue":"Red","lightness":"Light"},
                {"name":"P1","hue":"Orange","lightness":"Light"},
                {"name":"P2","hue":"Blue","lightness":"Light"}]},
    {"name":"月投入（元）","type":"number","style":{"type":"currency","precision":0,"currency_code":"CNY"}},
    {"name":"月收益（元）","type":"number","style":{"type":"currency","precision":0,"currency_code":"CNY"}},
    {"name":"月ROI","type":"text"},
    {"name":"案例参考","type":"text"},
    {"name":"说明","type":"text"}
])

print("\n✅ 所有字段创建完毕")
