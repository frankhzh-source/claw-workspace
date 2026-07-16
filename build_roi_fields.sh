#!/usr/bin/env bash
# 批量添加字段到ROI多维表格
BASE="CX8hb3C0WaYhUasvN1GcxNosn0c"

add_field() {
  local table=$1
  local json=$2
  cd /c/Users/jt && lark-cli base +field-create --base-token "$BASE" --as user --table-id "$table" --json "$json" 2>&1 | grep -q '"ok": true' && echo "  OK" || echo "  FAIL"
  sleep 0.5
}

echo "=== 收益侧分类 ==="
T="tblQ3dxBCj3NQf4L"
add_field "$T" '{"name":"度量指标","type":"text"}'
add_field "$T" '{"name":"计算公式","type":"text"}'
add_field "$T" '{"name":"案例","type":"text"}'
add_field "$T" '{"name":"可信度","type":"select","multiple":false,"options":[{"name":"⭐⭐⭐⭐⭐","hue":"Green","lightness":"Light"},{"name":"⭐⭐⭐⭐","hue":"Blue","lightness":"Light"},{"name":"⭐⭐⭐","hue":"Orange","lightness":"Light"}]}'

echo "=== 四阶段ROI模型 ==="
T="tblfZeM11uVgPyP5"
add_field "$T" '{"name":"时间窗口","type":"text"}'
add_field "$T" '{"name":"核心问题","type":"text"}'
add_field "$T" '{"name":"度量方法","type":"text"}'
add_field "$T" '{"name":"关键指标","type":"text"}'
add_field "$T" '{"name":"通过标准","type":"text"}'

echo "=== 行业对标基准 ==="
T="tbloxiVML1Bl0Qsm"
add_field "$T" '{"name":"典型Agent场景","type":"text"}'
add_field "$T" '{"name":"规模化期ROI参考","type":"text"}'
add_field "$T" '{"name":"关键决定因素","type":"text"}'
add_field "$T" '{"name":"标杆案例","type":"text"}'

echo "=== 电商场景ROI精算 ==="
T="tbldnnb5lfrD9Mhl"
add_field "$T" '{"name":"优先级","type":"select","multiple":false,"options":[{"name":"P0","hue":"Red","lightness":"Light"},{"name":"P1","hue":"Orange","lightness":"Light"},{"name":"P2","hue":"Blue","lightness":"Light"}]}'
add_field "$T" '{"name":"月投入（元）","type":"number","style":{"type":"currency","precision":0,"currency_code":"CNY"}}'
add_field "$T" '{"name":"月收益（元）","type":"number","style":{"type":"currency","precision":0,"currency_code":"CNY"}}'
add_field "$T" '{"name":"月ROI","type":"text"}'
add_field "$T" '{"name":"案例参考","type":"text"}'
add_field "$T" '{"name":"说明","type":"text"}'

echo ""
echo "✅ 所有字段创建完毕"
