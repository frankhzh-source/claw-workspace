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

token = get_token()

# Update both 产品名称 and 思考过程 in one request
print("=== 同时更新 产品名称 + 思考过程 ===")
result = update_record(token, "recTHgeYJP", {
    "产品名称": "【TEST】同时更新测试",
    "思考过程": "【TEST】思考过程测试内容"
})
print(json.dumps(result, ensure_ascii=False, indent=2))

# Restore 产品名称 only
print("\n=== 只恢复 产品名称 ===")
restore = update_record(token, "recTHgeYJP", {
    "产品名称": "「锦鲤萌宝」国潮盲盒系列——穿越千年的可爱守护灵（限量款收藏级手办）"
})
print(json.dumps(restore, ensure_ascii=False, indent=2))

# Try 输出结果 alone
print("\n=== 单独更新 输出结果 ===")
result2 = update_record(token, "recTHgeYJP", {
    "输出结果": "【TEST】输出结果测试内容"
})
print(json.dumps(result2, ensure_ascii=False, indent=2))

# Try 拍摄计划 (rich text, type 25)
print("\n=== 单独更新 拍摄计划 ===")
result3 = update_record(token, "recTHgeYJP", {
    "拍摄计划": "【TEST】拍摄计划测试内容"
})
print(json.dumps(result3, ensure_ascii=False, indent=2))
