#!/usr/bin/env python3
"""
GEO可见度测试 · 本地API中转服务
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
解决浏览器跨域问题：在本地起一个服务，前端调 /api/ask 让这个服务代为调用5大AI平台
返回AI的原始回答，前端展示给用户；用户决定是否生成报告

用法：
  python geo_api_server.py
  → 浏览器打开 http://localhost:8765/geo_visibility_dashboard.html
"""
import json, os, time, urllib.request, urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

ENGINES = {
    "deepseek": {
        "name": "DeepSeek", "mau": "4.84亿(Web)",
        "url": "https://api.deepseek.com/v1/chat/completions",
        "model": "deepseek-chat",
        "env": "DEEPSEEK_API_KEY",
    },
    "qwen": {
        "name": "千问", "mau": "2.51亿",
        "url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "model": "qwen-plus",
        "env": "QWEN_API_KEY",
    },
    "kimi": {
        "name": "Kimi", "mau": "2269万",
        "url": "https://api.moonshot.cn/v1/chat/completions",
        "model": "moonshot-v1-8k",
        "env": "MOONSHOT_API_KEY",
    },
    "doubao": {
        "name": "豆包", "mau": "3.24亿",
        "url": "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
        "model": "doubao-pro-32k",
        "env": "DOUBAO_API_KEY",
    },
    "hunyuan": {
        "name": "元宝(混元)", "mau": "1.04亿",
        "url": "https://api.hunyuan.cloud.tencent.com/v1/chat/completions",
        "model": "hunyuan-lite",
        "env": "HUNYUAN_API_KEY",
    },
}

def call_ai(engine_id, prompt, timeout=30):
    """调用单个AI平台"""
    engine = ENGINES[engine_id]
    api_key = os.environ.get(engine["env"], "")
    if not api_key:
        return {"status": "no_key", "content": "", "error": f"{engine['env']} 未配置"}

    payload = json.dumps({
        "model": engine["model"],
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 800,
        "temperature": 0.3,
    }).encode("utf-8")

    req = urllib.request.Request(
        engine["url"],
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return {"status": "ok", "content": data["choices"][0]["message"]["content"], "error": ""}
    except urllib.error.HTTPError as e:
        return {"status": "error", "content": "", "error": f"HTTP {e.code}: {e.read().decode('utf-8')[:200]}"}
    except Exception as e:
        return {"status": "error", "content": "", "error": str(e)[:200]}


def build_prompts(brand, category, methodology, competitor):
    """生成5维度×3轮测试prompt"""
    b, c, m, comp = brand, category, methodology, competitor
    return {
        "品牌认知": {
            "R1": f"你知道{b}吗？简单介绍一下。",
            "R2": f"我在找{b}相关的内容/服务，能帮我了解一下吗？",
            "R3": f"你刚才的回答引用了哪些信息来源？请列出具体网址或出处。",
        },
        "品类提及": {
            "R1": f"推荐一家{c}领域的专业服务商。",
            "R2": f"我想做{c}，杭州有哪些靠谱的服务商或专家推荐？",
            "R3": f"你推荐的这些服务商是基于哪些信息？列出具体出处。",
        },
        "方法论识别": {
            "R1": f"什么是{m}？谁提出来的？",
            "R2": f"我在做{c}，有人提到了{m}这个方法，能详细解释一下吗？",
            "R3": f"你解释{m}时引用了哪些来源？列出作者和出处。",
        },
        "竞品对比": {
            "R1": f"{b}和{comp}在{c}方面哪个更好？",
            "R2": f"我在{b}和{comp}之间犹豫，都是做{c}的，有什么建议？",
            "R3": f"你的比较引用了哪些信息来源？列出具体出处。",
        },
        "长尾场景": {
            "R1": f"我是一个电商品牌方，怎么在AI搜索里让客户找到我？",
            "R2": f"我的淘宝/抖音店铺退款率很高，怎么用{c}的方法分析和优化？",
            "R3": f"你的建议引用了哪些来源？列出具体出处。",
        },
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass  # 静音

    def do_GET(self):
        if self.path.startswith("/engines"):
            self._json({"engines": [{"id": k, "name": v["name"], "mau": v["mau"],
                "has_key": bool(os.environ.get(v["env"]))} for k, v in ENGINES.items()]})
        else:
            self.send_error(404)

    def do_POST(self):
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        except:
            return self._json({"error": "invalid json"}, 400)

        if self.path == "/api/ask":
            engine = body.get("engine")
            prompt = body.get("prompt", "")
            if engine not in ENGINES:
                return self._json({"error": "unknown engine"}, 400)
            r = call_ai(engine, prompt)
            return self._json({**r, "engine": engine, "prompt": prompt})

        elif self.path == "/api/prompts":
            prompts = build_prompts(
                body.get("brand", ""),
                body.get("category", ""),
                body.get("methodology", "未指定"),
                body.get("competitor", "无"),
            )
            return self._json({"prompts": prompts})

        elif self.path == "/api/report":
            # 生成HTML报告片段
            results = body.get("results", {})
            config = body.get("config", {})
            html = self._build_report_html(results, config)
            # 写入文件
            try:
                with open("geo_report_latest.html", "w", encoding="utf-8") as f:
                    f.write("<h1>GEO可见度报告</h1>" + html)
                msg = f"✅ 报告已生成: geo_report_latest.html"
            except Exception as e:
                msg = f"⚠️ 报告生成失败: {e}"
            return self._json({"ok": True, "html": html, "message": msg})

        else:
            self.send_error(404)

    def _build_report_html(self, results, config):
        """根据实时回答生成评分报告HTML"""
        brand = config.get("brand", "")
        brand_lower = brand.lower()
        rows = []
        totals = {eid: [0, 0] for eid in results}
        for eid, dims in results.items():
            for dim, rounds in dims.items():
                cells = []
                for rnd in ['R1', 'R2', 'R3']:
                    r = rounds.get(rnd, {})
                    content = r.get('content', '')
                    if r.get('status') == 'ok' and brand_lower and brand_lower in content.lower():
                        score, cls = 2, 'high'
                        totals[eid][0] += 2
                    elif r.get('status') == 'ok':
                        score, cls = 1, 'mid'
                        totals[eid][0] += 1
                    else:
                        score, cls = 0, 'zero'
                    cells.append(f'<td><span class="score-pill {cls}">{score}分</span></td>')
                    totals[eid][1] += 3
                rows.append(f'<tr><td>{ENGINES[eid]["name"]}</td><td>{dim}</td>{"".join(cells)}</tr>')
        table_html = '<table style="width:100%;border-collapse:collapse">'\
            '<thead><tr><th>平台</th><th>维度</th><th>R1</th><th>R2</th><th>R3</th></tr></thead>'\
            f'<tbody>{"".join(rows)}</tbody></table>'
        return table_html

    def _json(self, data, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))


if __name__ == "__main__":
    port = 8765
    print(f"\n🌐 GEO可见度测试服务已启动")
    print(f"   浏览器打开: http://localhost:{port}/geo_visibility_dashboard.html")
    print(f"   API地址:    http://localhost:{port}/api/ask")
    print(f"   按 Ctrl+C 停止\n")
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()
