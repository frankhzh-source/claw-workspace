"""轻量级进度监控服务器 - 实时读取 GLM Caption 进度"""
import json, os, time, http.server, threading, socket

CHECKPOINT = 'E:/AI电商工作创建/LORA训练数据集/14_captions_glm.json'
PROGRESS = 'E:/AI电商工作创建/LORA训练数据集/14_progress.json'
TOTAL = 600
CATEGORIES = ['少女甜系', '纯欲性感', '知性简约', '新中式国风', '老娘客']
TRAIN_DIR = 'E:/AI电商工作创建/LORA训练数据集/训练集'

def update_progress():
    """持续更新进度文件（每2秒）"""
    while True:
        if os.path.exists(CHECKPOINT):
            try:
                with open(CHECKPOINT, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                results = data.get('results', {})
                errors = data.get('errors', [])
                
                done = sum(len(v) for v in results.values())
                cat_progress = {}
                for cat in CATEGORIES:
                    cat_done = len(results.get(cat, {}))
                    cat_dir = os.path.join(TRAIN_DIR, f'{cat}_精选')
                    cat_total = len(os.listdir(cat_dir)) if os.path.exists(cat_dir) else 0
                    cat_progress[cat] = {'done': cat_done, 'total': cat_total}
                
                elapsed = time.time() - data.get('_start_time', time.time())
                rate = done / elapsed if elapsed > 0 else 0
                eta = (TOTAL - done) / rate if rate > 0 else 0
                
                # 最近10条Caption
                recent = []
                for cat in CATEGORIES:
                    for fname, cap in list(results.get(cat, {}).items())[-5:]:
                        recent.append({'cat': cat, 'file': fname, 'caption': cap[:80]})
                recent = recent[-10:]
                
                # 样张（每个品类最新1条）
                samples = {}
                for cat in CATEGORIES:
                    items = list(results.get(cat, {}).items())
                    if items:
                        samples[cat] = items[-1][1][:100]
                
                progress = {
                    'done': done, 'total': TOTAL, 'pct': round(done/TOTAL*100, 1),
                    'elapsed_min': round(elapsed/60, 1),
                    'eta_min': round(eta/60, 1),
                    'cat_progress': cat_progress,
                    'errors': len(errors),
                    'recent': recent[-6:],
                    'samples': samples,
                    'timestamp': time.strftime('%H:%M:%S')
                }
                with open(PROGRESS, 'w', encoding='utf-8') as f:
                    json.dump(progress, f, ensure_ascii=False)
            except:
                pass
        time.sleep(2)

# 启动进度更新线程
t = threading.Thread(target=update_progress, daemon=True)
t.start()

# 写入脚本启动时间戳到 checkpoint（如果存在）
if os.path.exists(CHECKPOINT):
    try:
        with open(CHECKPOOINT, 'r+', encoding='utf-8') as f:
            data = json.load(f)
            data['_start_time'] = time.time()
            f.seek(0)
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        pass

PORT = 8765
HTML_PATH = os.path.join(os.path.dirname(PROGRESS), '15_caption_dashboard.html')

# 生成 HTML 仪表盘
HTML = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GLM Caption 进度仪表盘</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
body{background:#f5f5f5;padding:24px;color:#333}
.header{display:flex;justify-content:space-between;align-items:center;margin-bottom:24px}
.header h1{font-size:24px;font-weight:600}
.header .status{font-size:14px;color:#666}
.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:24px}
.card{background:white;border-radius:12px;padding:20px;box-shadow:0 1px 3px rgba(0,0,0,.08)}
.card .label{font-size:13px;color:#888;margin-bottom:4px}
.card .value{font-size:32px;font-weight:700;color:#222}
.card .sub{font-size:13px;color:#999;margin-top:4px}
.card.accent{background:#4361ee;color:white}
.card.accent .value{color:white}
.card.accent .label{color:rgba(255,255,255,.7)}
.card.accent .sub{color:rgba(255,255,255,.6)}
.progress-bar{height:8px;background:#e8e8e8;border-radius:4px;margin-top:12px;overflow:hidden}
.progress-bar .fill{height:100%;background:#4361ee;border-radius:4px;transition:width 1s ease}
.card.accent .progress-bar{background:rgba(255,255,255,.2)}
.card.accent .progress-bar .fill{background:rgba(255,255,255,.9)}
.category-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-bottom:24px}
.cat-card{background:white;border-radius:10px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,.08)}
.cat-card .cat-name{font-size:14px;font-weight:600;margin-bottom:8px}
.cat-card .cat-count{font-size:22px;font-weight:700;color:#4361ee}
.cat-card .cat-total{font-size:13px;color:#999}
.cat-card .mini-bar{height:4px;background:#e8e8e8;border-radius:2px;margin-top:10px;overflow:hidden}
.cat-card .mini-bar .fill{height:100%;background:#4361ee;border-radius:2px;transition:width 1s ease}
.section{margin-bottom:24px}
.section h2{font-size:16px;font-weight:600;margin-bottom:12px;color:#555}
.recent-table{width:100%;background:white;border-radius:10px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.08)}
.recent-table th{background:#f8f9fa;padding:10px 14px;font-size:13px;font-weight:600;color:#666;text-align:left}
.recent-table td{padding:10px 14px;font-size:13px;border-top:1px solid #f0f0f0}
.recent-table .cat-tag{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:500}
.samples-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:12px}
.sample-card{background:white;border-radius:10px;padding:14px;box-shadow:0 1px 3px rgba(0,0,0,.08)}
.sample-card .s-cat{font-size:12px;font-weight:600;color:#4361ee;margin-bottom:6px}
.sample-card .s-text{font-size:13px;color:#555;line-height:1.5}
.error-badge{display:inline-block;padding:2px 10px;border-radius:10px;font-size:12px;font-weight:600}
.error-badge.ok{background:#e8f5e9;color:#2e7d32}
.error-badge.err{background:#fce4ec;color:#c62828}
.footer{text-align:center;font-size:12px;color:#bbb;padding:20px}
</style>
</head>
<body>
<div class="header">
  <h1>🖼️ GLM Caption 生成进度</h1>
  <div class="status">上次更新: <span id="timestamp">--</span> <span class="error-badge ok" id="errorBadge">0 错误</span></div>
</div>

<div class="cards" id="summaryCards">
  <div class="card accent">
    <div class="label">总进度</div>
    <div class="value" id="totalDone">0</div>
    <div class="sub">/ 600 张</div>
    <div class="progress-bar"><div class="fill" id="totalBar" style="width:0%"></div></div>
  </div>
  <div class="card">
    <div class="label">已耗时</div>
    <div class="value" id="elapsed">0</div>
    <div class="sub">分钟</div>
  </div>
  <div class="card">
    <div class="label">预估剩余</div>
    <div class="value" id="eta">--</div>
    <div class="sub">分钟</div>
  </div>
  <div class="card">
    <div class="label">处理速度</div>
    <div class="value" id="rate">--</div>
    <div class="sub">张/分钟</div>
  </div>
</div>

<div class="section">
  <h2>📊 品类进度</h2>
  <div class="category-grid" id="catGrid"></div>
</div>

<div class="section">
  <h2>📝 最新描述</h2>
  <table class="recent-table">
    <thead><tr><th>品类</th><th>文件名</th><th>Caption</th></tr></thead>
    <tbody id="recentBody"></tbody>
  </table>
</div>

<div class="section">
  <h2>🎯 品类样张（最新一条）</h2>
  <div class="samples-grid" id="samplesGrid"></div>
</div>

<div class="footer">自动刷新中 · 每 3 秒更新</div>

<script>
const CAT_COLORS = {
  '少女甜系': '#e91e63', '纯欲性感': '#ff6f91',
  '知性简约': '#4a90d9', '新中式国风': '#e8a838', '老娘客': '#9c27b0'
};

async function fetchProgress() {
  try {
    const r = await fetch('/progress.json?'+Date.now());
    const d = await r.json();
    render(d);
  } catch(e) {
    document.getElementById('totalDone').textContent = '⏳';
  }
}

function render(d) {
  document.getElementById('timestamp').textContent = d.timestamp || '--';
  document.getElementById('totalDone').textContent = d.done || 0;
  document.getElementById('totalBar').style.width = (d.pct||0) + '%';
  document.getElementById('elapsed').textContent = d.elapsed_min || 0;
  document.getElementById('eta').textContent = d.eta_min ? Math.round(d.eta_min) : '--';
  document.getElementById('rate').textContent = d.elapsed_min > 0 ? Math.round(d.done/d.elapsed_min) : '--';

  const errBadge = document.getElementById('errorBadge');
  if (d.errors > 0) {
    errBadge.textContent = d.errors + ' 错误';
    errBadge.className = 'error-badge err';
  } else {
    errBadge.textContent = '0 错误';
    errBadge.className = 'error-badge ok';
  }

  // 品类进度
  const catGrid = document.getElementById('catGrid');
  if (d.cat_progress) {
    catGrid.innerHTML = '';
    for (const [cat, p] of Object.entries(d.cat_progress)) {
      const pct = p.total > 0 ? (p.done/p.total*100) : 0;
      const color = CAT_COLORS[cat] || '#4361ee';
      catGrid.innerHTML += `
        <div class="cat-card">
          <div class="cat-name" style="color:${color}">${cat}</div>
          <div><span class="cat-count">${p.done}</span><span class="cat-total"> / ${p.total}</span></div>
          <div class="mini-bar"><div class="fill" style="width:${pct}%;background:${color}"></div></div>
        </div>`;
    }
  }

  // 最近描述
  const recentBody = document.getElementById('recentBody');
  if (d.recent && d.recent.length > 0) {
    recentBody.innerHTML = d.recent.map(r => {
      const color = CAT_COLORS[r.cat] || '#4361ee';
      return `<tr>
        <td><span class="cat-tag" style="background:${color}20;color:${color}">${r.cat}</span></td>
        <td style="font-size:12px;color:#999;max-width:150px;overflow:hidden;text-overflow:ellipsis">${r.file}</td>
        <td>${r.caption}</td>
      </tr>`;
    }).join('');
  } else {
    recentBody.innerHTML = '<tr><td colspan="3" style="text-align:center;color:#ccc;padding:20px">暂无数据</td></tr>';
  }

  // 样张
  const samplesGrid = document.getElementById('samplesGrid');
  if (d.samples && Object.keys(d.samples).length > 0) {
    samplesGrid.innerHTML = '';
    for (const [cat, cap] of Object.entries(d.samples)) {
      const color = CAT_COLORS[cat] || '#4361ee';
      samplesGrid.innerHTML += `
        <div class="sample-card">
          <div class="s-cat" style="color:${color}">${cat}</div>
          <div class="s-text">${cap}</div>
        </div>`;
    }
  }
}

fetchProgress();
setInterval(fetchProgress, 3000);
</script>
</body>
</html>'''

with open(HTML_PATH, 'w', encoding='utf-8') as f:
    f.write(HTML)
print(f'HTML 仪表盘已生成: {HTML_PATH}')

# 启动 HTTP 服务器
os.chdir(os.path.dirname(PROGRESS))
handler = http.server.SimpleHTTPRequestHandler
httpd = http.server.HTTPServer(('127.0.0.1', PORT), handler)
print(f'HTTP 服务器已启动: http://127.0.0.1:{PORT}/15_caption_dashboard.html')
httpd.serve_forever()
