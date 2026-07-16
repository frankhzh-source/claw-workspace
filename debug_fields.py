import json
import os
import urllib.request
import sys

sys.stdout.reconfigure(encoding='utf-8')

APP_ID = os.environ.get("FEISHU_APP_ID", "cli_aa86b3b3a9389cbd")
APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")
APP_TOKEN = os.environ.get("FEISHU_APP_TOKEN", "YjFFbIBEjaFf1Us1jjTcczAfnxf")
TABLE_ID = os.environ.get("FEISHU_TABLE_ID", "tblUPJE583VJqB1b")

def get_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = json.dumps({"app_id": APP_ID, "app_secret": APP_SECRET}).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method='POST')
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode('utf-8'))['tenant_access_token']

def api_get(url, token):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode('utf-8'))

def api_put(url, token, payload):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method='PUT')
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8')
        return {"code": e.code, "error": err_body}

token = get_token()

# 1. Get field definitions
print("=== 字段定义 ===")
fields_resp = api_get(
    f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/fields",
    token
)

target_fields = ['拍摄计划', '思考过程', '输出结果', '产品名称', '产品详情']
if fields_resp.get('code') == 0:
    for f in fields_resp['data']['items']:
        if f['field_name'] in target_fields:
            print(f"字段: {f['field_name']}")
            print(f"  type: {f['type']}")
            print(f"  ui_type: {f.get('ui_type', 'N/A')}")
            print(f"  property: {json.dumps(f.get('property', {}), ensure_ascii=False)[:200]}")
            print()
else:
    print("获取字段失败:", json.dumps(fields_resp, ensure_ascii=False, indent=2)[:500])

# 2. Get first record to see current field values
print("\n=== 首条记录（recTHgeYJP）当前值 ===")
rec_resp = api_get(
    f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/recTHgeYJP",
    token
)
if rec_resp.get('code') == 0:
    fields = rec_resp['data']['record']['fields']
    for key in target_fields:
        val = fields.get(key, '<不存在>')
        if isinstance(val, str) and len(val) > 100:
            val = val[:100] + '...'
        elif isinstance(val, list):
            val = f"[list, len={len(val)}]"
        print(f"  {key}: {val}")

# 3. Test update: write plain text to 拍摄计划
print("\n=== 测试写入 拍摄计划（纯文本）===")
test_result = api_put(
    f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/recTHgeYJP",
    token,
    {"fields": {"拍摄计划": "【测试】拍摄计划写入测试 - 可以删除"}}
)
print(f"  code: {test_result.get('code')}")
print(f"  msg: {test_result.get('msg')}")
if test_result.get('code') == 0:
    updated_fields = test_result.get('data', {}).get('record', {}).get('fields', {})
    val = updated_fields.get('拍摄计划', '<未返回>')
    print(f"  返回的拍摄计划值: {str(val)[:100]}")

# 4. Verify by reading back
print("\n=== 读回验证 ===")
verify_resp = api_get(
    f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/recTHgeYJP",
    token
)
if verify_resp.get('code') == 0:
    fields = verify_resp['data']['record']['fields']
    val = fields.get('拍摄计划', '<空>')
    if isinstance(val, str) and len(val) > 100:
        val = val[:100] + '...'
    elif isinstance(val, list):
        val = f"[list, len={len(val)}]"
    print(f"  拍摄计划: {val}")
    print(f"  产品名称: {str(fields.get('产品名称', '<空>'))[:80]}")
