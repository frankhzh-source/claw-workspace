"""Generate training progress dashboard from latest training output"""
import re, os, json, time, subprocess
from pathlib import Path

OUTPUT_DIR = r"E:\AI电商工作创建\LORA训练数据集"
LOG_FILE = r"C:\Users\jt\WorkBuddy\Claw\train_progress.log"
HTML_FILE = os.path.join(OUTPUT_DIR, "17_training_dashboard.html")
DASHBOARD_JSON = os.path.join(OUTPUT_DIR, "17_training_progress.json")

def get_task_output():
    """Try to get training process output via subprocess"""
    # Check if run_lora_training.py is running
    result = subprocess.run(
        ['tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV'],
        capture_output=True, text=True, shell=True
    )
    lines = result.stdout.strip().split('\n')
    processes = [l for l in lines if 'lora' in l.lower() or 'train' in l.lower() or 'python' in l.lower()]
    return len(lines) > 1  # python processes exist

def parse_progress(text):
    """Parse training progress bar output"""
    data = {
        'running': True,
        'current_step': 0,
        'total_steps': 1000,
        'loss_history': [],
        'current_loss': None,
        'lr': 0.0001,
        'speed': 0,
        'eta': '--',
        'elapsed_min': 0,
        'step_durations': [],
        'cache_status': 'completed' if 'Caching latents' not in text or 'Caching latents: 100%' in text else 'in_progress',
    }
    
    # Extract step progress
    step_pattern = re.compile(r'Steps:\s*(\d+)%?\|\w+\s*(\d+)/(\d+)')
    # Try more precise patterns
    step_pattern2 = re.compile(r'Steps:\s+\d+%\|\w+\s+(\d+)/(\d+)')
    
    lines = text.split('\n') if text else []
    
    # Get the last few lines with step info
    step_info_lines = [l for l in lines if 's/it' in l and 'loss=' in l]
    
    if step_info_lines:
        last_line = step_info_lines[-1].strip()
        # Try to parse: "Steps:   2%|▎         | 25/1000 [03:28<2:14:57,  8.30s/it, loss=0.259, lr=0.0001]"
        m = re.search(r'(\d+)/1000.*?(\d+:\d+:\d+)<(\d+:\d+:\d+).*?([\d.]+)s/it.*?loss=([\d.]+)', last_line)
        if m:
            data['current_step'] = int(m.group(1))
            data['elapsed'] = m.group(2)
            data['eta_str'] = m.group(3)
            data['speed'] = float(m.group(4))
            data['current_loss'] = float(m.group(5))
        
        # Parse multiple lines for loss history
        for line in step_info_lines[-50:]:
            m = re.search(r'loss=([\d.]+)', line)
            if m:
                data['loss_history'].append(float(m.group(1)))
    
    # Calculate ETA
    if data['speed'] > 0:
        remaining_steps = data['total_steps'] - data['current_step']
        remaining_sec = remaining_steps * data['speed']
        if remaining_sec < 3600:
            data['eta'] = f"{int(remaining_sec//60)}m {int(remaining_sec%60)}s"
        else:
            data['eta'] = f"{int(remaining_sec//3600)}h {int((remaining_sec%3600)//60)}m"
    
    # Calculate elapsed from first log line
    first_log = [l for l in lines if 'Training' in l or 'loss=' in l]
    if first_log:
        # approximate - the training log started
        pass
    
    # Get current timestamp
    data['timestamp'] = time.strftime('%H:%M:%S')
    
    # Check output directory for saved checkpoints
    output_ckpt_dir = r"D:\lora-train\output\知性简约"
    if os.path.exists(output_ckpt_dir):
        safetensors = [f for f in os.listdir(output_ckpt_dir) if f.endswith('.safetensors')]
        data['checkpoints'] = len(safetensors)
        if safetensors:
            # find latest
            latest = max([os.path.getmtime(os.path.join(output_ckpt_dir, f)) for f in safetensors])
            data['latest_ckpt'] = time.strftime('%H:%M:%S', time.localtime(latest))
    else:
        data['checkpoints'] = 0
        data['latest_ckpt'] = '--'
    
    data['progress_pct'] = round(data['current_step'] / data['total_steps'] * 100, 1)
    
    return data


# Try to get output from the training process
# Since we can't directly read subprocess stdout of a background task,
# let's get the latest output from TaskOutput by checking the log file

# First, check if there's a log file from the subprocess
log_text = ""
if os.path.exists(LOG_FILE):
    with open(LOG_FILE, 'r', encoding='utf-8', errors='replace') as f:
        log_text = f.read()[-50000:]  # last 50K chars

# If no log file, try to get from tasklist + the script's stderr redirect  
# The training writes to stdout which may not be captured in a file
# Let's try to find any .out or .log files
for p in [Path(r"C:\Users\jt\WorkBuddy\Claw"), Path(r"D:\lora-train\output")]:
    for logf in p.glob("*.log"):
        if logf.stat().st_size > 0 and logf.name != "train_progress.log":
            with open(logf, 'r', encoding='utf-8', errors='replace') as f:
                log_text += f.read()[-30000:]

if not log_text:
    # Check for nvidia-smi to get GPU usage
    try:
        nv = subprocess.run(['nvidia-smi', '--query-gpu=utilization.gpu,memory.used,memory.total', '--format=csv,noheader,nounits'], 
                          capture_output=True, text=True, timeout=5)
        log_text += f"\nGPU: {nv.stdout.strip()}\n"
    except:
        pass

# Parse progress
data = parse_progress(log_text)

# Save progress data
with open(DASHBOARD_JSON, 'w') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

# Generate HTML
loss_points = data['loss_history']
loss_chart_data = json.dumps([
    {"step": i+1, "loss": v} for i, v in enumerate(loss_points)
])
current_step = data['current_step']
total_steps = data['total_steps']
progress_pct = data['progress_pct']
speed = data['speed']
eta = data['eta']
current_loss = data['current_loss'] if data['current_loss'] else '--'
checkpoints = data['checkpoints']
timestamp = data['timestamp']

html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="refresh" content="15">
<title>LoRA 训练进度 — 知性简约</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ background: #0F172A; color: #E2E8F0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 20px; }}
.container {{ max-width: 900px; margin: 0 auto; }}
.header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }}
.header h1 {{ font-size: 20px; font-weight: 600; color: #F1F5F9; }}
.header .status {{ padding: 4px 12px; border-radius: 20px; font-size: 13px; font-weight: 500; }}
.status.running {{ background: #1E3A5F; color: #60A5FA; }}
.status.complete {{ background: #14532D; color: #4ADE80; }}

.cards {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px; }}
.card {{ background: #1E293B; border-radius: 12px; padding: 16px; border: 1px solid #334155; }}
.card .label {{ font-size: 11px; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }}
.card .value {{ font-size: 24px; font-weight: 700; color: #F1F5F9; }}
.card .sub {{ font-size: 12px; color: #64748B; margin-top: 4px; }}

.progress-container {{ background: #1E293B; border-radius: 12px; padding: 20px; margin-bottom: 20px; border: 1px solid #334155; }}
.progress-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }}
.progress-header .title {{ font-size: 14px; font-weight: 500; }}
.progress-header .pct {{ font-size: 28px; font-weight: 700; color: #60A5FA; }}
.progress-bar {{ height: 10px; background: #334155; border-radius: 5px; overflow: hidden; }}
.progress-bar .fill {{ height: 100%; border-radius: 5px; background: linear-gradient(90deg, #3B82F6, #8B5CF6); transition: width 1s; width: {progress_pct}%; }}
.progress-info {{ display: flex; justify-content: space-between; margin-top: 8px; font-size: 12px; color: #64748B; }}

.chart-container {{ background: #1E293B; border-radius: 12px; padding: 20px; margin-bottom: 20px; border: 1px solid #334155; }}
.chart-container h2 {{ font-size: 14px; font-weight: 500; margin-bottom: 16px; }}

.info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
.info-card {{ background: #1E293B; border-radius: 12px; padding: 16px; border: 1px solid #334155; }}
.info-card h3 {{ font-size: 12px; color: #94A3B8; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px; }}
.info-card .row {{ display: flex; justify-content: space-between; padding: 6px 0; font-size: 13px; border-bottom: 1px solid #1E293B; }}
.info-card .row:last-child {{ border: none; }}
.info-card .key {{ color: #94A3B8; }}
.info-card .val {{ color: #E2E8F0; font-weight: 500; }}
.footer {{ text-align: center; font-size: 11px; color: #475569; margin-top: 20px; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>🧶 知性简约 · FLUX.2 Klein 4B LoRA</h1>
    <span class="status running">● 运行中</span>
  </div>

  <div class="cards">
    <div class="card">
      <div class="label">当前步数</div>
      <div class="value">{current_step}</div>
      <div class="sub">/ {total_steps}</div>
    </div>
    <div class="card">
      <div class="label">当前 Loss</div>
      <div class="value">{current_loss}</div>
      <div class="sub">初始 ~0.3-0.6</div>
    </div>
    <div class="card">
      <div class="label">速度</div>
      <div class="value">{speed:.1f}s</div>
      <div class="sub">每步</div>
    </div>
    <div class="card">
      <div class="label">预估剩余</div>
      <div class="value">{eta}</div>
      <div class="sub">Checkpoint: {checkpoints}</div>
    </div>
  </div>

  <div class="progress-container">
    <div class="progress-header">
      <span class="title">训练进度</span>
      <span class="pct">{progress_pct}%</span>
    </div>
    <div class="progress-bar">
      <div class="fill" style="width:{progress_pct}%"></div>
    </div>
    <div class="progress-info">
      <span>步 {current_step}/{total_steps}</span>
      <span>预计完成: {eta}</span>
    </div>
  </div>

  <div class="chart-container">
    <h2>📉 Loss 曲线</h2>
    <canvas id="lossChart" height="200"></canvas>
  </div>

  <div class="info-grid">
    <div class="info-card">
      <h3>📋 训练参数</h3>
      <div class="row"><span class="key">模型</span><span class="val">FLUX.2-klein-base-4B</span></div>
      <div class="row"><span class="key">LoRA Rank</span><span class="val">16</span></div>
      <div class="row"><span class="key">学习率</span><span class="val">1e-4 (constant)</span></div>
      <div class="row"><span class="key">训练精度</span><span class="val">bf16 + FP8</span></div>
      <div class="row"><span class="key">Batch Size</span><span class="val">1 (Grad Accum 4)</span></div>
      <div class="row"><span class="key">训练图数</span><span class="val">120 张</span></div>
    </div>
    <div class="info-card">
      <h3>🎯 品类目标</h3>
      <div class="row"><span class="key">知性简约</span><span class="val" style="color:#4ADE80">● 首轮训练中</span></div>
      <div class="row"><span class="key">少女甜系</span><span class="val" style="color:#64748B">○ 待训练</span></div>
      <div class="row"><span class="key">纯欲性感</span><span class="val" style="color:#64748B">○ 待训练</span></div>
      <div class="row"><span class="key">新中式国风</span><span class="val" style="color:#64748B">○ 待训练</span></div>
      <div class="row"><span class="key">老娘客</span><span class="val" style="color:#64748B">○ 待训练</span></div>
    </div>
  </div>

  <div class="footer">
    数据更新: {timestamp} · 页面每 15 秒自动刷新
  </div>
</div>

<script>
const ctx = document.getElementById('lossChart').getContext('2d');
const data = {loss_chart_data};
const labels = data.map(d => d.step);
const values = data.map(d => d.loss);

new Chart(ctx, {{
  type: 'scatter',
  data: {{
    datasets: [{{
      label: 'Loss',
      data: data.map(d => ({{x: d.step, y: d.loss}})),
      backgroundColor: '#60A5FA',
      borderColor: '#3B82F6',
      pointRadius: 2,
      pointHoverRadius: 5,
      showLine: true,
      tension: 0.3,
      borderWidth: 1.5,
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      x: {{ title: {{ display: true, text: '步数', color: '#94A3B8' }},
             grid: {{ color: '#1E293B' }},
             ticks: {{ color: '#64748B' }} }},
      y: {{ title: {{ display: true, text: 'Loss', color: '#94A3B8' }},
             grid: {{ color: '#1E293B' }},
             ticks: {{ color: '#64748B' }},
             reverse: false }}
    }},
    interaction: {{ mode: 'nearest', axis: 'x' }}
  }}
}});
</script>
</body>
</html>'''

with open(HTML_FILE, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"✅ 训练仪表盘已生成: {HTML_FILE}")
print(f"   当前进度: {progress_pct}% ({current_step}/{total_steps})")
print(f"   当前 Loss: {current_loss}")
print(f"   预估剩余: {eta}")
