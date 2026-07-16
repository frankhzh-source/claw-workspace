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

# New field names
FIELD_PLAN = "\u62cd\u6444\u8ba1\u5212_\u586b\u5145"
FIELD_THINK = "\u601d\u8003\u8fc7\u7a0b_\u586b\u5145"
FIELD_OUTPUT = "\u8f93\u51fa\u7ed3\u679c_\u586b\u5145"

def get_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = json.dumps({"app_id": APP_ID, "app_secret": APP_SECRET}).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method='POST')
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode('utf-8'))['tenant_access_token']

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

# Load generated plans
with open(r'C:\Users\jt\WorkBuddy\Claw\generated_plans.json', 'r', encoding='utf-8') as f:
    plans = json.load(f)

print(f"Loaded {len(plans)} records to update")

token = get_token()
success = 0
fail = 0
errors = []

for i, plan in enumerate(plans):
    record_id = plan['record_id']
    fields = {
        FIELD_PLAN: plan['\u62cd\u6444\u8ba1\u5212'],
        FIELD_THINK: plan['\u601d\u8003\u8fc7\u7a0b'],
        FIELD_OUTPUT: plan['\u8f93\u51fa\u7ed3\u679c'],
    }
    
    result = api_put(
        f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/{record_id}",
        token,
        {"fields": fields}
    )
    
    if result.get('code') == 0:
        success += 1
    else:
        fail += 1
        errors.append({"record_id": record_id, "error": result.get('msg', str(result)[:100])})
    
    # Progress every 10 records
    if (i + 1) % 10 == 0:
        print(f"Progress: {i+1}/{len(plans)} (OK:{success} FAIL:{fail})")
    
    # Rate limit: 5 requests per second max
    time.sleep(0.25)

print(f"\n=== Final Result ===")
print(f"Total: {len(plans)}")
print(f"Success: {success}")
print(f"Failed: {fail}")

if errors:
    print(f"\nErrors ({len(errors)}):")
    for e in errors[:5]:
        print(f"  {e['record_id']}: {e['error'][:100]}")

# Save result
result_data = {
    "total": len(plans),
    "success": success,
    "failed": fail,
    "errors": errors,
    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
}
with open(r'C:\Users\jt\WorkBuddy\Claw\batch_update_result.json', 'w', encoding='utf-8') as f:
    json.dump(result_data, f, ensure_ascii=False, indent=2)

# Verify first 3 records
print(f"\n=== Verify first 3 records ===")
def api_get(url, token):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode('utf-8'))

for plan in plans[:3]:
    rec_id = plan['record_id']
    rec = api_get(f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/{rec_id}", token)
    if rec.get('code') == 0:
        fields = rec['data']['record']['fields']
        plan_val = fields.get(FIELD_PLAN, '<empty>')
        think_val = fields.get(FIELD_THINK, '<empty>')
        output_val = fields.get(FIELD_OUTPUT, '<empty>')
        plan_ok = len(str(plan_val)) > 20
        think_ok = len(str(think_val)) > 20
        output_ok = len(str(output_val)) > 20
        name = plan.get('\u4ea7\u54c1\u540d\u79f0', rec_id)[:30]
        print(f"  {name}: plan={plan_ok} think={think_ok} output={output_ok}")
