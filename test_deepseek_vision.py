"""检查 DeepSeek 可用模型列表并测试 vision"""
import json, urllib.request, urllib.error, ssl, os

os.environ['HTTPS_PROXY'] = ''
os.environ['HTTP_PROXY'] = ''

# 1. 列出模型
req = urllib.request.Request(
    'https://api.deepseek.com/v1/models',
    headers={'Authorization': 'Bearer sk-c76946e82b1b4a73b4d3796091d3585e'}
)
try:
    resp = urllib.request.urlopen(req, timeout=30, context=ssl.create_default_context())
    data = json.loads(resp.read())
    print('=== 可用模型 ===')
    for m in data.get('data', data)[:10]:
        if isinstance(m, dict):
            print(f"  {m.get('id', m)}")
        else:
            print(f"  {m}")
except Exception as e:
    print(f'模型列表获取失败: {e}')

# 2. 测试 pro 模型是否支持 vision
print('\n=== 测试 deepseek-v4-pro vision ===')
from PIL import Image
import io, base64

img_dir = 'E:/AI电商工作创建/LORA训练数据集/训练集/少女甜系_精选'
img_name = sorted(os.listdir(img_dir))[0]
img_path = os.path.join(img_dir, img_name)

img = Image.open(img_path).convert('RGB')
w, h = img.size
if max(w, h) > 1024:
    scale = 1024 / max(w, h)
    img = img.resize((int(w*scale), int(h*scale)), Image.LANCZOS)
buf = io.BytesIO()
img.save(buf, format='JPEG', quality=85)
b64 = base64.b64encode(buf.getvalue()).decode()

for model in ['deepseek-v4-pro', 'deepseek-chat', 'deepseek-reasoner', 'deepseek-v4-flash']:
    try:
        data = json.dumps({
            'model': model,
            'messages': [{'role': 'user', 'content': [
                {'type': 'text', 'text': '描述这张图。10字。'},
                {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{b64}'}}
            ]}],
            'max_tokens': 50
        }).encode()
        req = urllib.request.Request(
            'https://api.deepseek.com/v1/chat/completions', data,
            headers={'Content-Type': 'application/json',
                     'Authorization': 'Bearer sk-c76946e82b1b4a73b4d3796091d3585e'}
        )
        resp = urllib.request.urlopen(req, timeout=60, context=ssl.create_default_context())
        result = json.loads(resp.read())
        print(f'  {model}: ✅ {result["choices"][0]["message"]["content"][:50]}')
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:100]
        print(f'  {model}: ❌ {e.code} {body}')
    except Exception as e:
        print(f'  {model}: ❌ {str(e)[:60]}')
