import json
import os
import urllib.request
import urllib.error
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Feishu app credentials (from feishu-bitable-memory skill)
APP_ID = os.environ.get("FEISHU_APP_ID", "cli_aa86b3b3a9389cbd")
APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "")

# Target base
APP_TOKEN = "YjFFbIBEjaFf1Us1jjTcczAfnxf"
TABLE_ID = "tblUPJE583VJqB1b"

def get_tenant_access_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    headers = {"Content-Type": "application/json"}
    data = json.dumps({"app_id": APP_ID, "app_secret": APP_SECRET}).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            if result.get('code') == 0:
                return result['tenant_access_token']
            else:
                print(f"获取token失败: {result}")
                return None
    except Exception as e:
        print(f"请求token异常: {e}")
        return None

def batch_update_records(token, records):
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/batch_update"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    payload = {"records": records}
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8')
        print(f"HTTP错误 {e.code}: {err_body}")
        return {"code": e.code, "error": err_body}
    except Exception as e:
        print(f"请求异常: {e}")
        return {"code": -1, "error": str(e)}

# Load generated plans
with open(r'C:\Users\jt\WorkBuddy\Claw\generated_plans.json', 'r', encoding='utf-8') as f:
    plans = json.load(f)

print(f"准备更新 {len(plans)} 条记录...")

# Get token
token = get_tenant_access_token()
if not token:
    print("无法获取tenant_access_token，终止")
    sys.exit(1)

print(f"获取token成功")

# Prepare records - batch by batch (max 500 per call, we have 57)
records_to_update = []
for p in plans:
    records_to_update.append({
        "record_id": p['record_id'],
        "fields": {
            "拍摄计划": {"text": p['拍摄计划']},
            "思考过程": {"text": p['思考过程']},
            "输出结果": {"text": p['输出结果']}
        }
    })

# Actually for text fields in Feishu, the format might just be a string
# Let me check the correct format. In Feishu Bitable API v1:
# For text fields, the value should be a string directly in the fields object
# But wait, looking at the records we fetched, text fields were just strings in the fields dict

# Let me use string format directly
records_to_update = []
for p in plans:
    records_to_update.append({
        "record_id": p['record_id'],
        "fields": {
            "拍摄计划": p['拍摄计划'],
            "思考过程": p['思考过程'],
            "输出结果": p['输出结果']
        }
    })

print(f"发送更新请求，共 {len(records_to_update)} 条...")
result = batch_update_records(token, records_to_update)
print(f"更新结果: {json.dumps(result, ensure_ascii=False, indent=2)[:2000]}")

# Save result
with open(r'C:\Users\jt\WorkBuddy\Claw\update_result.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print("结果已保存到 update_result.json")
