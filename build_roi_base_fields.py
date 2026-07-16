#!/usr/bin/env python
"""向飞书多维表格批量添加字段和数据"""
import subprocess, json, time

BASE="CX8hb3C0WaYhUasvN1GcxNosn0c"
AS="--as user"

def cmd(args):
    r = subprocess.run(["cd","/c/Users/jt","&&","lark-cli","base"] + args, capture_output=True, text=True, shell=True)
    time.sleep(0.8)
    return r.stdout

# === 1. 收益侧分类 (tblQ3dxBCj3NQf4L) ===
t = "tblQ3dxBCj3NQf4L"
fields = [
    {"name":"度量指标","type":"text"},
    {"name":"计算公式","type":"text"},
    {"name":"案例","type":"text"},
    {"name":"可信度","type":"select","multiple":False,
     "options":[{"name":"⭐⭐⭐⭐⭐","hue":"Green","lightness":"Light"},
                {"name":"⭐⭐⭐⭐","hue":"Blue","lightness":"Light"},
                {"name":"⭐⭐⭐","hue":"Orange","lightness":"Light"}]}
]
for f in fields:
    j = json.dumps(f, ensure_ascii=False)
    out = cmd(["+field-create",f"--base-token={BASE}",AS,f"--table-id={t}",f'--json={j}'])
    print(f"收益表字段 {f['name']}: {'OK' if 'created' in out else 'FAIL'}")

# === 2. 四阶段ROI模型 (tblfZeM11uVgPyP5) ===
t = "tblfZeM11uVgPyP5"
fields = [
    {"name":"时间窗口","type":"text"},
    {"name":"核心问题","type":"text"},
    {"name":"度量方法","type":"text"},
    {"name":"关键指标","type":"text"},
    {"name":"通过标准","type":"text"}
]
for f in fields:
    j = json.dumps(f, ensure_ascii=False)
    out = cmd(["+field-create",f"--base-token={BASE}",AS,f"--table-id={t}",f'--json={j}'])
    print(f"四阶段表字段 {f['name']}: {'OK' if 'created' in out else 'FAIL'}")

# === 3. 行业对标基准 (tbloxiVML1Bl0Qsm) ===
t = "tbloxiVML1Bl0Qsm"
fields = [
    {"name":"典型Agent场景","type":"text"},
    {"name":"规模化期ROI参考","type":"text"},
    {"name":"关键决定因素","type":"text"},
    {"name":"标杆案例","type":"text"}
]
for f in fields:
    j = json.dumps(f, ensure_ascii=False)
    out = cmd(["+field-create",f"--base-token={BASE}",AS,f"--table-id={t}",f'--json={j}'])
    print(f"行业表字段 {f['name']}: {'OK' if 'created' in out else 'FAIL'}")

# === 4. 电商场景ROI精算 (tbldnnb5lfrD9Mhl) ===
t = "tbldnnb5lfrD9Mhl"
fields = [
    {"name":"优先级","type":"select","multiple":False,
     "options":[{"name":"P0","hue":"Red","lightness":"Light"},
                {"name":"P1","hue":"Orange","lightness":"Light"},
                {"name":"P2","hue":"Blue","lightness":"Light"}]},
    {"name":"月投入（元）","type":"number","style":{"type":"currency","precision":0,"currency_code":"CNY"}},
    {"name":"月收益（元）","type":"number","style":{"type":"currency","precision":0,"currency_code":"CNY"}},
    {"name":"月ROI","type":"text"},
    {"name":"案例参考","type":"text"},
    {"name":"说明","type":"text"}
]
for f in fields:
    j = json.dumps(f, ensure_ascii=False)
    out = cmd(["+field-create",f"--base-token={BASE}",AS,f"--table-id={t}",f'--json={j}'])
    print(f"电商表字段 {f['name']}: {'OK' if 'created' in out else 'FAIL'}")

print("\n所有字段创建完毕")
