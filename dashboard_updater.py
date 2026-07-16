import sys, os, re, subprocess, time, json

OUTPUT_DIR = r"E:\AI电商工作创建\LORA训练数据集"
HTML_FILE = os.path.join(OUTPUT_DIR, "17_training_dashboard.html")
CKPT_DIR = r"D:\lora-train\output\知性简约"

def get_gpu():
    try:
        nv = subprocess.run(['nvidia-smi', '--query-gpu=utilization.gpu,power.draw,temperature.gpu,memory.used,memory.total', '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=5, shell=True)
        parts = [p.strip() for p in nv.stdout.strip().split(', ')]
        return {"util": parts[0], "power": parts[1], "temp": parts[2], "vram": f"{parts[3]}/{parts[4]} MB"}
    except: return {"util":"?","power":"?","temp":"?","vram":"?"}

def get_ckpts():
    if os.path.exists(CKPT_DIR):
        return len([f for f in os.listdir(CKPT_DIR) if f.endswith('.safetensors')])
    return 0

# Loss data reference (will append latest)
loss_data = [0.585,0.178,0.308,0.296,0.385,0.326,0.115,0.624,0.298,0.313,
0.298,0.315,0.251,0.413,0.196,0.137,0.771,0.159,0.396,0.347,
0.467,0.411,0.393,0.640,0.137,0.392,0.329,0.224,0.290,0.215,
0.408,0.216,0.234,0.221,0.247,0.200,0.461,0.390,0.717,0.448,
0.263,0.199,0.884,0.409,0.299,0.577,0.469,0.321,0.535,0.138,
0.208,0.773,0.094,0.520,0.285,0.320,0.112,0.300,0.284,0.980,
0.219,0.220,0.305,0.863,0.084,0.264,0.357,0.403,0.365,0.167,
1.060,0.097,0.427,0.455,1.000,0.288,0.317,0.368,0.231,0.387,
0.363,0.595,0.155,0.326,0.506,0.277,0.440,0.367,0.488,0.387,
0.430,0.428,0.327,1.040,0.359,0.519,0.275,0.437,0.259,0.537,
0.252,0.651,0.141,0.311,0.211,0.395,0.203,0.483,0.421,0.369,
0.634,0.346,0.390,0.194,0.552,0.651,0.427,0.264,0.241,0.191,
0.318,0.413,0.706,0.258,0.413,0.395,0.350,0.209,0.268,0.400,
0.346,0.245,0.510,0.322,0.421,0.464,0.346,0.183,0.305,0.298,
0.283,0.332,0.297,0.321,0.240,0.698,0.477,0.355,0.561,0.217,
0.267,0.256,0.320,0.251,0.400,0.232,0.335,0.486,0.323,0.343,
0.346,0.541,0.284,0.499,0.410,0.639,0.410,0.304,0.288,0.248,
0.419,0.382,0.546,0.347,0.364,0.605,0.497,0.589,0.303,0.296,
0.252,0.462,0.427,0.295,0.260,0.275,0.188,0.451,0.556,0.230,
0.624,0.361,0.491,0.288,0.292,0.479,0.250,0.362,0.585,0.530,
0.309,0.257,0.358,0.366,0.402,0.282,0.478,0.393,0.444,0.210,
0.374,0.290,0.221,0.522,0.415,0.577,0.623,0.501,0.224,0.473,
0.257,0.525,0.376,0.222,0.471,0.332,0.307,0.310,0.214,0.325,
0.555,0.569,0.170,0.357,0.608,0.472,0.429,0.491,0.218,0.331,
0.365,0.490,0.355,0.626,0.403,0.212,0.829,0.412,0.410,0.384,
0.324,0.463,0.328,0.264,0.406,0.197,0.490,0.324,0.518,0.303,
0.390,0.215,0.226,0.296,0.124,0.178,0.194,0.585,0.328,0.449,
0.282,0.367,0.508,0.191,0.418,0.460,0.380,0.219,0.441,0.302,
0.428,0.312,0.718,0.245,0.520,0.176,0.368,0.488,0.489,0.572,
0.328,0.217,0.496,0.490,0.243,0.435,0.225,0.421,0.570,0.266,
0.498,0.293,0.158,0.614,0.291,0.620,0.290,0.308,0.371,0.295,
0.311,0.645,0.217,0.366,0.200,0.288,0.272,0.301,0.175,0.348,
0.358,0.838,0.217,0.301,0.429,0.384,0.298,0.418,0.244,0.510,
0.461,0.432,0.215,0.330,0.437,0.440,0.339,0.464,0.357,0.310,
0.525,0.550,0.373,0.262,0.544,0.364,0.168]
CIRCUMFERENCE = 270

def generate_html(step, total, speed, loss, gpu, ckpts, loss_data):
    pct = step / total * 100
    elapsed_min = (step * speed) / 60 if step > 0 else 0
    eta_min = ((total - step) * speed) / 60 if step > 0 else 0
    offset = CIRCUMFERENCE * (1 - pct / 100)
    ld = loss_data[-step:] if step <= len(loss_data) else loss_data
    loss_json = json.dumps([{"x": i+1, "y": v} for i, v in enumerate(ld)])

    return f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta http-equiv="refresh" content="10"><title>LoRA 训练 — 知性简约</title><script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script><style>
*{{margin:0;padding:0;box-sizing:border-box}}body{{background:#0B1120;color:#E2E8F0;font:-apple-system,'Segoe UI',sans-serif;padding:10px;height:100vh;overflow-y:auto}}
.container{{max-width:920px;margin:0 auto}}
.topbar{{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}}
.topbar h1{{font-size:14px;font-weight:600;color:#F1F5F9}}
.topbar .badge{{padding:3px 10px;border-radius:20px;font-size:11px;background:#1E3A5F;color:#60A5FA;border:1px solid #2D5A8F}}
.badge .dot{{display:inline-block;width:7px;height:7px;border-radius:50%;background:#60A5FA;margin-right:5px;animation:pulse 1.5s infinite}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:0.3}}}}
.main-row{{display:flex;gap:8px;margin-bottom:8px}}
.ring-card{{flex:0 0 110px;background:#1E293B;border:1px solid #334155;border-radius:8px;padding:8px;text-align:center}}
.ring-card svg{{width:90px;height:90px;transform:rotate(-90deg)}}
.ring-bg{{fill:none;stroke:#1E293B;stroke-width:6}}
.ring-fg{{fill:none;stroke:url(#grad);stroke-width:6;stroke-linecap:round;transition:stroke-dashoffset 0.8s}}
.ring-center{{position:absolute;top:calc(50% + 1px);left:50%;transform:translate(-50%,-50%);text-align:center}}
.ring-center .pct{{font-size:20px;font-weight:700;color:#60A5FA}}
.ring-center .label{{font-size:8px;color:#64748B}}
.rlabel{{font-size:10px;color:#94A3B8;margin-top:2px}}
.ring-wrap{{position:relative;width:90px;height:90px;margin:0 auto}}
.stats-grid{{flex:1;display:grid;grid-template-columns:repeat(3,1fr);gap:5px}}
.scard{{background:#1E293B;border:1px solid #334155;border-radius:6px;padding:6px 8px}}
.scard .sl{{font-size:9px;color:#64748B}}
.scard .sv{{font-size:16px;font-weight:700;margin-top:1px}}
.scard .ss{{font-size:9px;color:#475569}}
.cl{{color:#FBBF24}}.cs{{color:#60A5FA}}.ct{{color:#4ADE80}}.ce{{color:#F87171}}
.progress-card{{background:#1E293B;border:1px solid #334155;border-radius:6px;padding:6px 10px;margin-bottom:6px}}
.pbar{{height:8px;background:#0F172A;border-radius:4px;overflow:hidden;margin:3px 0}}
.pbar .fill{{height:100%;border-radius:4px;background:linear-gradient(90deg,#3B82F6,#8B5CF6,#EC4899);transition:width 0.8s;width:{pct:.1f}%}}
.prow{{display:flex;justify-content:space-between;font-size:10px}}
.prow .pi{{color:#64748B}}.prow .pv{{color:#94A3B8}}
.bottom-row{{display:grid;grid-template-columns:7fr 5fr;gap:6px;margin-bottom:4px}}
.chart-card{{background:#1E293B;border:1px solid #334155;border-radius:6px;padding:6px 8px}}
.chart-card h3{{font-size:10px;color:#64748B;margin-bottom:2px}}
.info-card{{background:#1E293B;border:1px solid #334155;border-radius:6px;padding:6px 8px}}
.info-card h3{{font-size:9px;color:#64748B;margin-bottom:3px;border-bottom:1px solid #0F172A;padding-bottom:3px}}
.info-card .row{{display:flex;justify-content:space-between;padding:1px 0;font-size:10px;border-bottom:1px solid #0F172A}}
.info-card .row:last-child{{border:none}}
.info-card .k{{color:#64748B}}
.pitem{{display:flex;align-items:center;gap:4px;font-size:9px}}
.pitem .dot{{width:6px;height:6px;border-radius:50%;flex-shrink:0}}
.dot.done{{background:#4ADE80}}.dot.active{{background:#60A5FA;animation:pulse 1.5s infinite}}.dot.wait{{background:#334155}}
.ft{{text-align:center;font-size:9px;color:#334155;padding:2px 0}}
</style></head><body>
<svg width="0" height="0"><defs><linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="0%"><stop offset="0%" stop-color="#3B82F6"/><stop offset="50%" stop-color="#8B5CF6"/><stop offset="100%" stop-color="#EC4899"/></linearGradient></defs></svg>
<div class="container">
<div class="topbar"><h1>🧶 知性简约 · FLUX.2 Klein 4B</h1><span class="badge"><span class="dot"></span>Step {step}/{total} · {pct:.0f}%</span></div>
<div class="main-row">
<div class="ring-card"><div class="ring-wrap"><svg width="90" height="90" viewBox="0 0 90 90"><circle class="ring-bg" cx="45" cy="45" r="38.5"/><circle class="ring-fg" cx="45" cy="45" r="38.5" stroke-dasharray="270" stroke-dashoffset="{270*(1-pct/100):.1f}"/></svg><div class="ring-center"><div class="pct">{pct:.0f}%</div><div class="label">完成</div></div></div><div class="rlabel">{step}/{total} 步</div></div>
<div class="stats-grid">
<div class="scard"><div class="sl">Loss</div><div class="sv cl">{loss:.3f}</div><div class="ss">逐步收敛中</div></div>
<div class="scard"><div class="sl">速度</div><div class="sv cs">{speed:.1f}s</div><div class="ss">每步</div></div>
<div class="scard"><div class="sl">已运行</div><div class="sv ct">{elapsed_min:.0f}分</div><div class="ss">{time.strftime("%H:%M")} 更新</div></div>
<div class="scard"><div class="sl">Checkpoint</div><div class="sv cs">{ckpts}</div><div class="ss">下一个在200步</div></div>
<div class="scard"><div class="sl">预估剩余</div><div class="sv ce">{eta_min:.0f}分</div><div class="ss">~{time.strftime("%H:%M", time.localtime(time.time()+eta_min*60))}</div></div>
<div class="scard"><div class="sl">GPU</div><div class="sv cs">{gpu["util"]}%</div><div class="ss">{gpu["temp"]}°C · {gpu["vram"]}</div></div>
</div></div>
<div class="progress-card"><div class="prow"><span class="pi">训练进度</span><span class="pv">Step {step}/{total} · ETA {eta_min:.0f}分</span></div><div class="pbar"><div class="fill"></div></div></div>
<div class="bottom-row">
<div class="chart-card"><h3>📐 Loss 曲线</h3><canvas id="lc" height="90"></canvas></div>
<div class="info-card"><h3>⚙ 参数</h3>
<div class="row"><span class="k">模型</span><span>FLUX.2-klein-base-4B</span></div>
<div class="row"><span class="k">Rank</span><span>16</span></div>
<div class="row"><span class="k">LR</span><span>1e-4 constant</span></div>
<div class="row"><span class="k">Batch/Grad</span><span>2 / 2</span></div>
<div class="row"><span class="k">精度</span><span>bf16+FP8</span></div>
<div class="row"><span class="k">WD</span><span>0.05 · GS=1.0</span></div>
<div class="row"><span class="k">图数</span><span>120张 · 精选</span></div></div></div>
<div class="progress-card" style="margin-bottom:2px"><div class="prow"><span class="pi">🗺 整体进展</span></div>
<div style="display:grid;grid-template-columns:repeat(7,1fr);gap:2px;margin-top:3px;text-align:center">
<div><div class="pitem"><span class="dot done"></span>采集</div></div>
<div><div class="pitem"><span class="dot done"></span>审核</div></div>
<div><div class="pitem"><span class="dot done"></span>精选</div></div>
<div><div class="pitem"><span class="dot active"></span><strong>训练</strong></div></div>
<div><div class="pitem"><span class="dot wait"></span>测试</div></div>
<div><div class="pitem"><span class="dot wait"></span>扩品</div></div>
<div><div class="pitem"><span class="dot wait"></span>交付</div></div></div></div>
<div class="ft">每 10 秒自动刷新 · Step {step}/{total} · {time.strftime("%H:%M:%S")}</div>
</div>
<script>
const ld = {loss_json};
new Chart(document.getElementById("lc"),{{type:"line",data:{{datasets:[{{label:"Loss",data:ld,borderColor:"#60A5FA",backgroundColor:"rgba(96,165,250,0.15)",fill:true,tension:0.4,pointRadius:0,borderWidth:1.3}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},scales:{{x:{{grid:{{color:"rgba(51,65,85,0.3)"}},ticks:{{color:"#475569",maxTicksLimit:4,font:{{size:8}}}}}},y:{{grid:{{color:"rgba(51,65,85,0.3)"}},ticks:{{color:"#475569",font:{{size:8}}}},min:0}}}}}}});
</script></body></html>'''

import subprocess as sp
while True:
    try:
        task = sp.run(['D:/lora-env-310/Scripts/python.exe', 'C:/Users/jt/WorkBuddy/Claw/gen_dashboard_v3.py'], capture_output=True, text=True, timeout=30)
        out = task.stdout.strip()
        if out: print(out)
    except: pass
    time.sleep(10)
