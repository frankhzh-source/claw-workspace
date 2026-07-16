#!/usr/bin/env python3
"""
GEO品牌可见度自动化测试工具
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
调用主流AI平台API，检测品牌/方法论在AI搜索中的可见度
输出：JSON数据 + Excel报告 + Markdown诊断报告

用法:
  python geo_visibility_test.py --brand "海风老师" --category "电商GEO" --method "三层信源验证法"
  python geo_visibility_test.py --config test_config.json
"""
import json, os, time, sys, argparse
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional
import urllib.request, urllib.error

# ── 配置 ──────────────────────────────────────────────

@dataclass
class TestConfig:
    brand_name: str
    category: str = ""
    methodology: str = ""
    competitors: list = field(default_factory=list)
    scenarios: list = field(default_factory=list)
    # API keys (from env if not set)
    deepseek_key: str = ""
    qwen_key: str = ""
    moonshot_key: str = ""
    doubao_key: str = ""
    hunyuan_key: str = ""

# ── 五平台引擎 ─────────────────────────────────────────

ENGINES = {
    "deepseek": {
        "name": "DeepSeek", "mau": "4.84亿(Web)",
        "url": "https://api.deepseek.com/v1/chat/completions",
        "model": "deepseek-chat",
        "env_key": "DEEPSEEK_API_KEY",
    },
    "qwen": {
        "name": "千问", "mau": "2.51亿",
        "url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "model": "qwen-plus",
        "env_key": "QWEN_API_KEY",
    },
    "kimi": {
        "name": "Kimi", "mau": "2269万",
        "url": "https://api.moonshot.cn/v1/chat/completions",
        "model": "moonshot-v1-8k",
        "env_key": "MOONSHOT_API_KEY",
    },
    "doubao": {
        "name": "豆包", "mau": "3.24亿",
        "url": "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
        "model": "doubao-pro-32k",
        "env_key": "DOUBAO_API_KEY",
    },
    "hunyuan": {
        "name": "元宝(混元)", "mau": "1.04亿",
        "url": "https://api.hunyuan.cloud.tencent.com/v1/chat/completions",
        "model": "hunyuan-lite",
        "env_key": "HUNYUAN_API_KEY",
    },
}

# ── 五维度 × 三轮测试模板 ──────────────────────────────

def build_test_prompts(config: TestConfig):
    """生成5维度×3轮的所有测试prompt"""
    b, c, m = config.brand_name, config.category, config.methodology
    comp = config.competitors[0] if config.competitors else "竞品A"

    prompts = {
        "品牌认知": {
            "R1": f"你知道{b}吗？介绍一下。",
            "R2": f"我在找{b}相关的服务，能帮我介绍一下吗？",
            "R3": f"你刚才的介绍中引用了哪些信息来源？请列举具体网址。",
        },
        "品类提及": {
            "R1": f"推荐一家{c}领域的专业服务商。",
            "R2": f"我想做{c}，杭州有哪些靠谱的服务商或专家推荐？",
            "R3": f"你推荐的这些服务商是基于哪些信息来源？列出具体网址。",
        },
        "方法论识别": {
            "R1": f"什么是{m}？谁提出来的？",
            "R2": f"我在做{c}，有人提到了{m}这个方法，能详细解释一下吗？",
            "R3": f"你解释{m}时引用了哪些来源？列出作者和网址。",
        },
        "竞品对比": {
            "R1": f"{b}和{comp}在{c}方面哪个更好？",
            "R2": f"我在{b}和{comp}之间犹豫，都是做{c}的，有什么建议？",
            "R3": f"你的比较引用了哪些信息来源？列出具体网址。",
        },
        "长尾场景": {
            "R1": f"我是一个电商品牌方，怎么在AI搜索里让客户找到我？",
            "R2": f"我的淘宝/抖音店铺退款率很高，怎么用{c}的方法来分析和优化？",
            "R3": f"你的建议引用了哪些来源？列出具体网址。",
        },
    }
    return prompts


# ── API调用 ────────────────────────────────────────────

def call_ai(engine_id: str, prompt: str, api_key: str, timeout: int = 30) -> dict:
    """调用单个AI平台，返回{status, content, error}"""
    engine = ENGINES[engine_id]
    if not api_key:
        return {"status": "skipped", "content": "", "error": f"{engine['name']}: API key未配置"}

    payload = json.dumps({
        "model": engine["model"],
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 800,
        "temperature": 0.3,
    }).encode("utf-8")

    req = urllib.request.Request(
        engine["url"],
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            return {"status": "ok", "content": content, "error": ""}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")[:300]
        return {"status": "error", "content": "", "error": f"HTTP {e.code}: {body}"}
    except Exception as e:
        return {"status": "error", "content": "", "error": str(e)[:200]}


# ── 评分引擎 ────────────────────────────────────────────

def score_mention(answer: str, brand: str, methodology: str = "") -> dict:
    """
    对AI回答打分: 3=精确提及且有署名, 2=正确提及无署名, 1=描述有误, 0=未提及
    返回 {score, level, evidence}
    """
    b_lower = brand.lower()
    a_lower = answer.lower()

    # 精确提及
    if b_lower in a_lower:
        # 检查是否有署名锚点（方法论/来源说明）
        has_source = any(kw in a_lower for kw in ["www.", "http", "来源", "引用", "官网"])
        has_method = (methodology and methodology in answer)
        if has_source or has_method:
            return {"score": 3, "level": "L1-署名", "evidence": f"品牌名'{brand}'直接出现，且有来源/方法论署名"}
        return {"score": 2, "level": "L1-提及", "evidence": f"品牌名'{brand}'直接出现，但无署名锚点"}

    # 语义关联（描述接近但没点名）
    # 简单语义检查：品类/方法论关键词是否出现
    semantic_hints = 0
    for kw in ["电商", "geo", "生成式引擎", "ai搜索", "三层信源", "可见度"]:
        if kw in a_lower:
            semantic_hints += 1
    if semantic_hints >= 2:
        return {"score": 1, "level": "L2-语义", "evidence": f"未直接提及品牌，但语义相关(hints={semantic_hints})"}

    return {"score": 0, "level": "L3-未提及", "evidence": "内容与品牌无关"}


# ── 报告生成 ────────────────────────────────────────────

def generate_report(results: dict, config: TestConfig) -> dict:
    """聚合所有测试结果为标准化报告"""
    now = datetime.now().isoformat()
    report = {
        "meta": {
            "generated_at": now,
            "brand": config.brand_name,
            "category": config.category,
            "methodology": config.methodology,
            "competitors": config.competitors,
        },
        "engine_scores": {},
        "dimension_scores": {},
        "total_score": 0,
        "max_score": 0,
        "anomalies": [],
    }

    dim_total = {}
    max_per_engine = 5 * 3 * 3  # 5维度 × 3轮 × 最高分3
    max_total = len(ENGINES) * max_per_engine

    for eng_id, eng_data in results.items():
        eng_score = 0
        eng_count = 0
        for dim, rounds in eng_data.items():
            if dim not in dim_total:
                dim_total[dim] = 0
            for rnd, r in rounds.items():
                s = r.get("score", 0)
                eng_score += s
                dim_total[dim] += s
                if s < 2:
                    report["anomalies"].append({
                        "engine": eng_id,
                        "dimension": dim,
                        "round": rnd,
                        "score": s,
                        "evidence": r.get("evidence", ""),
                        "error": r.get("error", ""),
                    })
        report["engine_scores"][eng_id] = {"total": eng_score, "max": max_per_engine}
        report["total_score"] += eng_score

    report["max_score"] = max_total
    report["dimension_scores"] = {d: {"total": s, "max": len(ENGINES) * 3 * 3} for d, s in dim_total.items()}

    # 计算加权分 (R2 × 40%)
    # 简化为总分的百分比
    report["visibility_rate"] = round(report["total_score"] / report["max_score"] * 100, 1)

    return report


def report_to_markdown(report: dict, config: TestConfig) -> str:
    """生成Markdown诊断报告"""
    lines = []
    lines.append(f"# GEO品牌可见度测试报告")
    lines.append(f"**品牌:** {config.brand_name} | **品类:** {config.category} | **日期:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    lines.append(f"## 总体得分: {report['visibility_rate']}%")
    lines.append("")

    # 各平台得分
    lines.append("## 平台得分")
    lines.append("| 平台 | MAU | 得分 | 满分 | 占比 |")
    lines.append("|:---|---:|---:|---:|---:|")
    for eng_id, s in report["engine_scores"].items():
        eng = ENGINES[eng_id]
        pct = round(s["total"] / s["max"] * 100, 1) if s["max"] > 0 else 0
        lines.append(f"| {eng['name']} | {eng['mau']} | {s['total']} | {s['max']} | {pct}% |")
    lines.append("")

    # 各维度得分
    lines.append("## 维度得分")
    lines.append("| 维度 | 得分 | 满分 | 占比 |")
    lines.append("|:---|---:|---:|---:|")
    for dim, s in report["dimension_scores"].items():
        pct = round(s["total"] / s["max"] * 100, 1) if s["max"] > 0 else 0
        lines.append(f"| {dim} | {s['total']} | {s['max']} | {pct}% |")
    lines.append("")

    # 异常诊断
    if report["anomalies"]:
        lines.append("## 异常信号诊断")
        lines.append("| 平台 | 维度 | 轮次 | 得分 | 证据 |")
        lines.append("|:---|:---|:---:|:---:|:---|")
        for a in report["anomalies"][:20]:
            eng_name = ENGINES.get(a["engine"], {}).get("name", a["engine"])
            lines.append(f"| {eng_name} | {a['dimension']} | {a['round']} | {a['score']} | {a.get('evidence','')[:60]} |")
        lines.append("")

    # 建议
    lines.append("## 修复建议")
    if report["visibility_rate"] < 30:
        lines.append("- **P0 建基础信源**: 百度百科/官网/公众号/知乎专栏 — 品牌无AI索引根目录")
    if report["dimension_scores"].get("方法论识别", {}).get("total", 0) < 5:
        lines.append("- **方法论署名锚点**: 在所有内容平台统一加盖「方法论名称+提出者」署名")
    if report["dimension_scores"].get("竞品对比", {}).get("total", 0) < 3:
        lines.append("- **第三方对比文章**: 在知乎/CSDN发布独立对比文章，提供多源信源")

    return "\n".join(lines)


# ── 主流程 ───────────────────────────────────────────────

def run_tests(config: TestConfig, engines: list = None) -> tuple:
    """执行全量测试，返回(results, report)"""
    if engines is None:
        engines = list(ENGINES.keys())

    prompts = build_test_prompts(config)
    results = {}

    for eng_id in engines:
        eng = ENGINES[eng_id]
        api_key = os.environ.get(eng["env_key"], "")
        if config.deepseek_key and eng_id == "deepseek":
            api_key = config.deepseek_key
        if config.qwen_key and eng_id == "qwen":
            api_key = config.qwen_key
        if config.moonshot_key and eng_id == "kimi":
            api_key = config.moonshot_key
        if config.doubao_key and eng_id == "doubao":
            api_key = config.doubao_key
        if config.hunyuan_key and eng_id == "hunyuan":
            api_key = config.hunyuan_key

        if not api_key:
            print(f"[{eng['name']}] 跳过: API key未配置 (设置环境变量 {eng['env_key']})")
            # 生成空结果
            results[eng_id] = {}
            for dim in prompts:
                results[eng_id][dim] = {}
                for rnd, _ in prompts[dim].items():
                    results[eng_id][dim][rnd] = {"score": 0, "level": "N/A", "evidence": "", "error": "API key未配置"}
            continue

        results[eng_id] = {}
        print(f"[{eng['name']}] 开始测试...")

        for dim, rounds in prompts.items():
            results[eng_id][dim] = {}
            for rnd, prompt in rounds.items():
                resp = call_ai(eng_id, prompt, api_key)
                if resp["status"] == "ok":
                    s = score_mention(resp["content"], config.brand_name, config.methodology)
                    results[eng_id][dim][rnd] = {**s, "answer_snippet": resp["content"][:200]}
                else:
                    results[eng_id][dim][rnd] = {"score": 0, "level": "ERROR", "evidence": "", "error": resp["error"]}
                time.sleep(0.5)  # rate limit

        print(f"[{eng['name']}] 完成")

    report = generate_report(results, config)
    return results, report


# ── CLI ─────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="GEO品牌可见度自动化测试工具")
    parser.add_argument("--brand", required=True, help="品牌/人物名称")
    parser.add_argument("--category", default="", help="品类/领域")
    parser.add_argument("--method", default="", help="方法论名称")
    parser.add_argument("--competitors", nargs="*", default=[], help="竞品名称（可多个）")
    parser.add_argument("--engines", default="deepseek,qwen", help="测试平台(逗号分隔): deepseek,qwen,kimi,doubao,hunyuan")
    parser.add_argument("--output", default="geo_report", help="输出文件前缀")
    parser.add_argument("--format", default="all", choices=["json","md","excel","all"], help="输出格式")

    args = parser.parse_args()
    engine_list = [e.strip() for e in args.engines.split(",") if e.strip() in ENGINES]

    config = TestConfig(
        brand_name=args.brand,
        category=args.category,
        methodology=args.method,
        competitors=args.competitors,
    )

    print(f"\n{'='*60}")
    print(f"  GEO品牌可见度测试")
    print(f"  品牌: {config.brand_name}  |  品类: {config.category or '未指定'}")
    print(f"  方法论: {config.methodology or '未指定'}  |  平台: {len(engine_list)}个")
    print(f"{'='*60}\n")

    results, report = run_tests(config, engine_list)

    # 输出
    if args.format in ("json", "all"):
        with open(f"{args.output}.json", "w", encoding="utf-8") as f:
            json.dump({"results": results, "report": report}, f, ensure_ascii=False, indent=2)
        print(f"\n✅ JSON报告: {args.output}.json")

    if args.format in ("md", "all"):
        md = report_to_markdown(report, config)
        with open(f"{args.output}.md", "w", encoding="utf-8") as f:
            f.write(md)
        print(f"✅ Markdown报告: {args.output}.md")

        # 输出摘要
        print(f"\n{'─'*40}")
        print(f"  可见度总得分: {report['visibility_rate']}%")
        for eng_id, s in report["engine_scores"].items():
            pct = round(s["total"] / s["max"] * 100, 1) if s["max"] > 0 else 0
            print(f"  {ENGINES[eng_id]['name']:12s}: {pct}%")
        print(f"{'─'*40}")

if __name__ == "__main__":
    main()
