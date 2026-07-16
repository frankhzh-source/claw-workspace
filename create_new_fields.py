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

def api_post(url, token, payload):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8')
        return {"code": e.code, "error": err_body}

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

# Step 1: Create 3 new regular text columns
new_fields = [
    {"field_name": "\u62cd\u6444\u8ba1\u5212_\u586b\u5145", "type": 1},  # Text
    {"field_name": "\u601d\u8003\u8fc7\u7a0b_\u586b\u5145", "type": 1},  # Text
    {"field_name": "\u8f93\u51fa\u7ed3\u679c_\u586b\u5145", "type": 1},  # Text
]

field_ids = {}
for nf in new_fields:
    print(f"Creating field: {nf['field_name']}...")
    result = api_post(
        f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/fields",
        token,
        nf
    )
    if result.get('code') == 0:
        fid = result['data']['field']['field_id']
        field_ids[nf['field_name']] = fid
        print(f"  OK: field_id={fid}")
    else:
        print(f"  FAILED: {json.dumps(result, ensure_ascii=False)[:300]}")

print(f"\nCreated {len(field_ids)} fields: {list(field_ids.keys())}")

# Step 2: Test writing to the new field on one record
TEST_REC = "recTHgeYJP"
print(f"\n=== Test write to new field on {TEST_REC} ===")

# Read the record first to verify it exists
rec = api_get(f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/{TEST_REC}", token)
print(f"Record exists: {rec.get('code') == 0}")

# Write test content to new field
test_write = api_put(
    f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/{TEST_REC}",
    token,
    {"fields": {"\u62cd\u6444\u8ba1\u5212_\u586b\u5145": "TEST: writing to new regular text field"}}
)
print(f"Write code: {test_write.get('code')}, msg: {test_write.get('msg')}")

time.sleep(2)

# Verify write
verify = api_get(f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/{TEST_REC}", token)
if verify.get('code') == 0:
    val = verify['data']['record']['fields'].get('\u62cd\u6444\u8ba1\u5212_\u586b\u5145', '<empty>')
    has_data = val != '<empty>' and len(str(val)) > 0
    print(f"Read back: {str(val)[:100]}")
    print(f"Write verified: {has_data}")

    # Clean up test value
    if has_data:
        api_put(
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/{TEST_REC}",
            token,
            {"fields": {"\u62cd\u6444\u8ba1\u5212_\u586b\u5145": ""}}
        )
        print("Test value cleaned up")

print(f"\nField IDs for batch write: {json.dumps(field_ids, ensure_ascii=False)}")
