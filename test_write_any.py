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

def update_record(token, record_id, fields):
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/{record_id}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    payload = {"fields": fields}
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method='PUT')
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8')
        print(f"HTTP {e.code}: {err_body}")
        return {"code": e.code, "error": err_body}

def get_record(token, record_id):
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/{record_id}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode('utf-8'))

token = get_token()

# Try updating a field that currently has content: 产品名称
print("=== 更新 产品名称 ===")
result = update_record(token, "recTHgeYJP", {"产品名称": "【TEST】锦鲤萌宝"})
print(json.dumps(result, ensure_ascii=False, indent=2))

# Verify
print("\n=== 验证 ===")
verify = get_record(token, "recTHgeYJP")
print(f"产品名称当前值: {verify['data']['record']['fields'].get('产品名称', 'N/A')}")

# Restore original value
print("\n=== 恢复原值 ===")
restore = update_record(token, "recTHgeYJP", {"产品名称": "「锦鲤萌宝」国潮盲盒系列——穿越千年的可爱守护灵（限量款收藏级手办）"})
print(json.dumps(restore, ensure_ascii=False, indent=2))
