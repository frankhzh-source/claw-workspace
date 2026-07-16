import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open(r'C:\Users\jt\WorkBuddy\Claw\feishu_records.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

items = data['data']['items']

def has_content(val):
    if val is None:
        return False
    if isinstance(val, list):
        return len(val) > 0
    if isinstance(val, str):
        return len(val.strip()) > 0
    return True

# Categories
categories = {
    'full': [],      # 产品名称 + 商品照片 + 产品详情 + 产品主题画面内容
    'partial': [],   # 仅有商品照片，缺少文字信息
    'no_photo': [],  # 无商品照片
}

empty_three_cols = []  # 拍摄计划/思考过程/输出结果 全空
has_three_cols = []    # 至少有一个有内容

for item in items:
    fields = item['fields']
    record_id = item['record_id']
    
    has_name = has_content(fields.get('产品名称'))
    has_photo = has_content(fields.get('商品照片'))
    has_detail = has_content(fields.get('产品详情'))
    has_theme = has_content(fields.get('产品主题画面内容'))
    
    has_plan = has_content(fields.get('拍摄计划'))
    has_think = has_content(fields.get('思考过程'))
    has_output = has_content(fields.get('输出结果'))
    
    if has_name and has_photo and has_detail and has_theme:
        categories['full'].append(record_id)
    elif has_photo and not (has_name or has_detail or has_theme):
        categories['partial'].append(record_id)
    elif not has_photo:
        categories['no_photo'].append(record_id)
    else:
        # Mixed case - has some text but not all
        categories.setdefault('mixed', []).append(record_id)
    
    if not has_plan and not has_think and not has_output:
        empty_three_cols.append(record_id)
    else:
        has_three_cols.append(record_id)

print(f"总计记录: {len(items)}")
print(f"")
print(f"=== 按数据完整度分类 ===")
print(f"完整记录（名称+照片+详情+主题画面）: {len(categories['full'])}")
print(f"部分记录（仅照片，无文字）: {len(categories.get('partial', []))}")
print(f"无照片记录: {len(categories.get('no_photo', []))}")
print(f"混合记录（有部分文字但不完整）: {len(categories.get('mixed', []))}")
print(f"")
print(f"=== 拍摄计划/思考过程/输出结果 状态 ===")
print(f"三列全空: {len(empty_three_cols)}")
print(f"至少一列有内容: {len(has_three_cols)}")
print(f"")

if len(categories.get('mixed', [])) > 0:
    print(f"混合记录详情（前10条）:")
    for rid in categories['mixed'][:10]:
        for item in items:
            if item['record_id'] == rid:
                f = item['fields']
                print(f"  {rid}: 名称={has_content(f.get('产品名称'))}, 照片={has_content(f.get('商品照片'))}, 详情={has_content(f.get('产品详情'))}, 主题={has_content(f.get('产品主题画面内容'))}")
                break

# Save full records for next step
full_records = []
for item in items:
    if item['record_id'] in categories['full']:
        full_records.append({
            'record_id': item['record_id'],
            '产品名称': item['fields'].get('产品名称', ''),
            '产品详情': item['fields'].get('产品详情', ''),
            '产品主题画面内容': item['fields'].get('产品主题画面内容', ''),
            '产品细节画面': item['fields'].get('产品细节画面', ''),
            '商品名称': item['fields'].get('商品名称', ''),
        })

with open(r'C:\Users\jt\WorkBuddy\Claw\full_records.json', 'w', encoding='utf-8') as f:
    json.dump(full_records, f, ensure_ascii=False, indent=2)

print(f"\n已保存 {len(full_records)} 条完整记录到 full_records.json")
