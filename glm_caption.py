"""GLM-5V-Turbo Caption 生成 - 600张家居服图片"""
import json, os, io, base64, time, concurrent.futures, urllib.request, ssl
from PIL import Image
from collections import defaultdict

os.environ['HTTPS_PROXY'] = ''
os.environ['HTTP_PROXY'] = ''

API_KEY = "8bf88563b0564a66a31a52d5f2abdcb9.u5se8L5itocnmNP5"
MODEL = "glm-5v-turbo"
URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
OUTPUT = "E:/AI电商工作创建/LORA训练数据集/14_captions_glm.json"
MAX_WORKERS = 3  # 并发数
MAX_TOKENS = 2000

CATEGORIES = ['少女甜系', '纯欲性感', '知性简约', '新中式国风', '老娘客']
TRAIN_DIR = 'E:/AI电商工作创建/LORA训练数据集/训练集'
PROMPT = '用中文描述这件家居服：风格、颜色、材质、设计细节。20-50字。不要思考过程直接输出。'

def encode_image(img_path):
    """压缩并 base64 编码图片"""
    img = Image.open(img_path).convert('RGB')
    w, h = img.size
    if max(w, h) > 768:
        scale = 768 / max(w, h)
        img = img.resize((int(w*scale), int(h*scale)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=80)
    return base64.b64encode(buf.getvalue()).decode()

def generate_caption(img_path):
    """调用 GLM-5V-Turbo 生成单张图片描述"""
    b64 = encode_image(img_path)
    data = {
        'model': MODEL,
        'messages': [{'role': 'user', 'content': [
            {'type': 'text', 'text': PROMPT},
            {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{b64}'}}
        ]}],
        'max_tokens': MAX_TOKENS
    }
    req = urllib.request.Request(
        URL, json.dumps(data).encode(),
        headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {API_KEY}'}
    )
    resp = urllib.request.urlopen(req, timeout=120, context=ssl.create_default_context())
    result = json.loads(resp.read())
    content = result['choices'][0]['message'].get('content', '').strip()
    return content if content else '(空描述)'

def main():
    # 收集所有图片路径
    all_images = []
    for cat in CATEGORIES:
        cat_dir = os.path.join(TRAIN_DIR, f'{cat}_精选')
        if not os.path.exists(cat_dir):
            print(f'⚠️ 目录不存在: {cat_dir}')
            continue
        for fname in sorted(os.listdir(cat_dir)):
            all_images.append((cat, os.path.join(cat_dir, fname)))
    
    total = len(all_images)
    print(f'总图片数: {total}')
    
    # 分批处理
    results = {cat: {} for cat in CATEGORIES}
    done = 0
    errors = []
    t0 = time.time()
    
    # 单线程处理（避免并发造成 API 限流不稳定）
    for cat, fpath in all_images:
        fname = os.path.basename(fpath)
        try:
            caption = generate_caption(fpath)
            results[cat][fname] = caption
            done += 1
            elapsed = time.time() - t0
            rate = done / elapsed * 3600 if elapsed > 0 else 0
            eta = (total - done) / (done / elapsed) if done > 0 else 0
            print(f'  [{done}/{total}] {cat}/{fname[:30]:30s} → {caption[:50]}... ({rate:.0f}张/时, ETA {eta/60:.0f}分)')
        except Exception as e:
            errors.append((fpath, str(e)[:80]))
            print(f'  ❌ [{done}/{total}] {cat}/{fname} 失败: {str(e)[:60]}')
            results[cat][fname] = f'[ERROR] {str(e)[:60]}'
        
        # 每 20 张存一次中间结果
        if done % 20 == 0:
            with open(OUTPUT, 'w', encoding='utf-8') as f:
                json.dump({'results': results, 'errors': errors, 'progress': f'{done}/{total}'}, f, ensure_ascii=False, indent=2)
            print(f'  💾 已保存中间结果 ({done}/{total})')
    
    # 最终保存
    final = {
        'model': MODEL,
        'prompt': PROMPT,
        'total': total,
        'done': done,
        'errors': errors,
        'elapsed_min': (time.time() - t0) / 60,
        'results': results
    }
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(final, f, ensure_ascii=False, indent=2)
    
    print(f'\n✅ 完成! {done}/{total}, 错误 {len(errors)}, 耗时 {(time.time()-t0)/60:.0f}分钟')
    print(f'   保存: {OUTPUT}')

if __name__ == '__main__':
    main()
