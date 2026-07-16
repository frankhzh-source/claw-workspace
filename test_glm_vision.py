"""GLM-5V-Turbo 图片理解 - 加大 token 限制"""
import json, urllib.request, ssl, os, io, base64
from PIL import Image

os.environ['HTTPS_PROXY'] = ''
os.environ['HTTP_PROXY'] = ''
API_KEY = "8bf88563b0564a66a31a52d5f2abdcb9.u5se8L5itocnmNP5"

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

data = {
    'model': 'glm-5v-turbo',
    'messages': [{'role': 'user', 'content': [
        {'type': 'text', 'text': '用中文描述这件家居服：风格、颜色、材质、设计细节。30-50字。不要思考过程，直接输出描述。'},
        {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{b64}'}}
    ]}],
    'max_tokens': 2000
}
req = urllib.request.Request(
    'https://open.bigmodel.cn/api/paas/v4/chat/completions',
    data=json.dumps(data).encode(),
    headers={'Content-Type': 'application/json',
             'Authorization': f'Bearer {API_KEY}'}
)
resp = urllib.request.urlopen(req, timeout=60, context=ssl.create_default_context())
result = json.loads(resp.read())

msg = result['choices'][0]['message']
print(f'finish_reason: {result["choices"][0]["finish_reason"]}')
print(f'content: [{msg.get("content","")}]')
rc = msg.get('reasoning_content','')
if rc:
    print(f'reasoning: {rc[:100]}...')
print(f'tokens: {result.get("usage",{})}')
