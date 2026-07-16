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

token = get_token()

# Get ALL field definitions - full output
print("=== ALL field definitions ===")
fields_resp = api_get(
    f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/fields",
    token
)
if fields_resp.get('code') == 0:
    for f in fields_resp['data']['items']:
        name = f['field_name']
        ftype = f['type']
        ui = f.get('ui_type', 'N/A')
        # Mark AI/computed fields
        extra = ""
        if ftype == 25:
            extra = " <-- TYPE 25 (Object/AI)"
        elif name in ['\u62cd\u6444\u8ba1\u5212', '\u601d\u8003\u8fc7\u7a0b', '\u8f93\u51fa\u7ed3\u679c']:
            extra = " <-- TARGET FIELD"
        print(f"  [{ftype}/{ui}] {name}{extra}")

# Check specific fields that might be "AI shortcut" output fields
print("\n=== Detailed info for AI-related fields ===")
if fields_resp.get('code') == 0:
    for f in fields_resp['data']['items']:
        name = f['field_name']
        if any(kw in name for kw in ['\u62cd\u6444', '\u601d\u8003', '\u8f93\u51fa', '\u63d0\u793a\u8bcd', 'AI', 'ai', '\u6307\u4ee4', '\u9009\u62e9']):
            # Print full field definition
            print(f"\n--- {name} ---")
            print(json.dumps(f, ensure_ascii=False, indent=2))
