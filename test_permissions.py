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
            raw = resp.read().decode('utf-8')
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8')
        return {"code": e.code, "error": err_body}

token = get_token()
TEST_REC = "recTHgeYJP"

# Step 1: Read current values
print("=== Step 1: Current state of test record ===")
rec = api_get(f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/{TEST_REC}", token)
if rec.get('code') == 0:
    fields = rec['data']['record']['fields']
    # Show which fields have data
    for k, v in fields.items():
        if isinstance(v, str) and len(v) > 80:
            v = v[:80] + '...'
        elif isinstance(v, list):
            v = f"[list, {len(v)} items]"
        print(f"  {k}: {v}")

# Step 2: Try updating a field that already has data (product name)
print("\n=== Step 2: Update existing field (product name) ===")
original_name = rec['data']['record']['fields'].get('\u4ea7\u54c1\u540d\u79f0', '')
print(f"  Original: {original_name[:60]}")

test_update = api_put(
    f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/{TEST_REC}",
    token,
    {"fields": {"\u4ea7\u54c1\u540d\u79f0": original_name + " [WRITE_TEST]"}}
)
print(f"  Update code: {test_update.get('code')}, msg: {test_update.get('msg')}")
# Check if update response contains the updated fields
if test_update.get('code') == 0 and test_update.get('data', {}).get('record', {}).get('fields'):
    updated = test_update['data']['record']['fields']
    print(f"  Response fields keys: {list(updated.keys())}")
    print(f"  Response product name: {str(updated.get('\u4ea7\u54c1\u540d\u79f0', ''))[:60]}")

time.sleep(2)

# Verify
rec2 = api_get(f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/{TEST_REC}", token)
if rec2.get('code') == 0:
    name_now = rec2['data']['record']['fields'].get('\u4ea7\u54c1\u540d\u79f0', '')
    has_test = '[WRITE_TEST]' in name_now
    print(f"  After update: {name_now[:60]}")
    print(f"  Write SUCCESS: {has_test}")

    # Restore original name if test succeeded
    if has_test:
        restore = api_put(
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/{TEST_REC}",
            token,
            {"fields": {"\u4ea7\u54c1\u540d\u79f0": original_name}}
        )
        print(f"  Restored: code={restore.get('code')}")

# Step 3: Check app permissions
print("\n=== Step 3: Check app permissions ===")
# Check if the app is a collaborator of the base
perm_resp = api_get(
    f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/members?page_size=20",
    token
)
print(f"  Members API code: {perm_resp.get('code')}")
if perm_resp.get('code') == 0:
    members = perm_resp.get('data', {}).get('items', [])
    for m in members:
        print(f"  member: {m.get('member_id', 'N/A')} type={m.get('member_type', 'N/A')}")

# Step 4: Try with user_access_token instead (use MCP tool)
print("\n=== Step 4: Try batchUpdate with different approach ===")
# Try batch update with a single record
batch_payload = {
    "records": [{
        "record_id": TEST_REC,
        "fields": {
            "\u601d\u8003\u8fc7\u7a0b": "BATCH TEST: thinking process"
        }
    }]
}
batch_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/batch_update"
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
}
data = json.dumps(batch_payload, ensure_ascii=False).encode('utf-8')
req = urllib.request.Request(batch_url, data=data, headers=headers, method='POST')
try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        batch_result = json.loads(resp.read().decode('utf-8'))
    print(f"  batch_update code: {batch_result.get('code')}, msg: {batch_result.get('msg')}")
    if batch_result.get('code') == 0:
        records = batch_result.get('data', {}).get('records', [])
        if records:
            updated_fields = records[0].get('fields', {})
            print(f"  Response fields: {list(updated_fields.keys())[:5]}")
            think_val = updated_fields.get('\u601d\u8003\u8fc7\u7a0b', '<not returned>')
            print(f"  Response think: {str(think_val)[:80]}")
except urllib.error.HTTPError as e:
    print(f"  HTTP {e.code}: {e.read().decode('utf-8')[:300]}")

# Verify batch update
time.sleep(2)
rec3 = api_get(f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/{TEST_REC}", token)
if rec3.get('code') == 0:
    think_val = rec3['data']['record']['fields'].get('\u601d\u8003\u8fc7\u7a0b', '<empty>')
    print(f"  After batch update, think: {str(think_val)[:80]}")
