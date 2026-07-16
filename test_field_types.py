import json
import os
import urllib.request
import sys
import time

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
TEST_REC = "recTHgeYJP"

# Test 1: Write to 思考过程 (type 1 Text)
print("=== Test 1: Write to Text field ===")
r1 = api_put(
    f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/{TEST_REC}",
    token,
    {"fields": {"\u601d\u8003\u8fc7\u7a0b": "TEST: think process content"}}
)
print(f"  code: {r1.get('code')}, msg: {r1.get('msg')}")

time.sleep(1)
v1 = api_get(f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/{TEST_REC}", token)
if v1.get('code') == 0:
    val = v1['data']['record']['fields'].get('\u601d\u8003\u8fc7\u7a0b', '<empty>')
    print(f"  Read back: {str(val)[:80]}")

# Test 2: Write to 输出结果 (type 1 Text)
print("\n=== Test 2: Write to Text field 2 ===")
r2 = api_put(
    f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/{TEST_REC}",
    token,
    {"fields": {"\u8f93\u51fa\u7ed3\u679c": "TEST: output result content"}}
)
print(f"  code: {r2.get('code')}, msg: {r2.get('msg')}")

time.sleep(1)
v2 = api_get(f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/{TEST_REC}", token)
if v2.get('code') == 0:
    val = v2['data']['record']['fields'].get('\u8f93\u51fa\u7ed3\u679c', '<empty>')
    print(f"  Read back: {str(val)[:80]}")

# Test 3: Get full field definition for type 25 Object
print("\n=== Test 3: Full field definition for Object field ===")
fields_resp = api_get(
    f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/fields",
    token
)
if fields_resp.get('code') == 0:
    for f in fields_resp['data']['items']:
        if f['field_name'] == '\u62cd\u6444\u8ba1\u5212':
            print(json.dumps(f, ensure_ascii=False, indent=2))

# Test 4: Try different formats for type 25 Object field
print("\n=== Test 4: Try different formats for Object field ===")

formats = [
    ("plain text", "TEST plain text"),
    ("array of text runs", [[{"type": "text", "text": "TEST rich text"}]]),
    ("content block object", {"text": "TEST content block"}),
    ("link+text object", {"link": "https://example.com", "text": "TEST link text"}),
    ("nested array", [{"type": "paragraph", "children": [{"type": "text", "text": "TEST nested"}]}]),
]

for name, value in formats:
    print(f"\n--- Format: {name} ---")
    payload = {"fields": {"\u62cd\u6444\u8ba1\u5212": value}}
    r = api_put(
        f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/{TEST_REC}",
        token,
        payload
    )
    print(f"  code: {r.get('code')}, msg: {r.get('msg')}")
    if r.get('code') != 0:
        print(f"  error: {str(r.get('error', r.get('msg', '')))[:200]}")

# Final verify
time.sleep(1)
vf = api_get(f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/{TEST_REC}", token)
if vf.get('code') == 0:
    plan_val = vf['data']['record']['fields'].get('\u62cd\u6444\u8ba1\u5212', '<empty>')
    think_val = vf['data']['record']['fields'].get('\u601d\u8003\u8fc7\u7a0b', '<empty>')
    output_val = vf['data']['record']['fields'].get('\u8f93\u51fa\u7ed3\u679c', '<empty>')
    print(f"\n=== Final state ===")
    print(f"  plan: {json.dumps(plan_val, ensure_ascii=False)[:150]}")
    print(f"  think: {str(think_val)[:150]}")
    print(f"  output: {str(output_val)[:150]}")

# Clean up test data
print("\n=== Cleanup: clear test values ===")
cleanup = api_put(
    f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/{TEST_REC}",
    token,
    {"fields": {"\u601d\u8003\u8fc7\u7a0b": "", "\u8f93\u51fa\u7ed3\u679c": ""}}
)
print(f"  code: {cleanup.get('code')}")
