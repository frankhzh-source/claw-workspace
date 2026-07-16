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
    # Try single record update using PUT
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

token = get_token()

# Test 1: Update with field names
print("=== Test 1: 使用字段名 ===")
result1 = update_record(token, "recTHgeYJP", {
    "思考过程": "TEST_思考过程_使用字段名",
    "输出结果": "TEST_输出结果_使用字段名"
})
print(json.dumps(result1, ensure_ascii=False, indent=2))

# Test 2: Update with field IDs
print("\n=== Test 2: 使用字段ID ===")
result2 = update_record(token, "recTHgeYJP", {
    "fld2lbL1xF": "TEST_思考过程_使用字段ID",
    "fldBDRqOU7": "TEST_输出结果_使用字段ID"
})
print(json.dumps(result2, ensure_ascii=False, indent=2))

# Test 3: Rich text field (拍摄计划) with different formats
print("\n=== Test 3: 富文本字段不同格式 ===")
result3 = update_record(token, "recTHgeYJP", {
    "fldh9Tmdbf": {"text": "TEST_拍摄计划_富文本对象格式"}
})
print(json.dumps(result3, ensure_ascii=False, indent=2))
