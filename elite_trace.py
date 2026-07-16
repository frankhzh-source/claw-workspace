#!/usr/bin/env python3
"""
elite_trace.py — Elite 可观测性追踪系统

在生产环境中记录每次 LLM 调用和工具调用的完整链路，
支持追溯、回放、统计和成本分析。

用法:
  python elite_trace.py log <trace_id> --model <model> --prompt <prompt> --response <resp> [--latency <ms>] [--tokens <in,out>] [--status ok|error] [--error <info>] [--cost <$>] [--tool <name> --tool-args <args> --tool-result <result>]
  python elite_trace.py list [--limit 20] [--status ok|error] [--model <model>]
  python elite_trace.py chain <trace_id>
  python elite_trace.py search <keyword>
  python elite_trace.py stats [--model <model>]
  python elite_trace.py replay <trace_id>
  python elite_trace.py status
"""

import argparse
import json
import os
import sqlite3
import sys
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional

TRACE_DIR = os.path.expanduser("~/.openclaw/memory/trace")
DB_PATH = os.path.join(TRACE_DIR, "trace.db")
VERSION = "1.0.0"

MODEL_PRICING = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "claude-3.5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
    "deepseek-v3": {"input": 0.27, "output": 1.10},
    "deepseek-r1": {"input": 0.55, "output": 2.19},
    "ollama/nomic-embed-text": {"input": 0.00, "output": 0.00},
    "ollama/llama3": {"input": 0.00, "output": 0.00},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    "qwen-max": {"input": 0.80, "output": 2.00},
    "unknown": {"input": 1.00, "output": 4.00},
}


def get_db():
    os.makedirs(TRACE_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    _init_schema(conn)
    return conn


def _init_schema(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS traces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trace_id TEXT NOT NULL,
            sequence INTEGER DEFAULT 0,
            timestamp TEXT NOT NULL,
            model TEXT DEFAULT 'unknown',
            prompt TEXT DEFAULT '',
            response TEXT DEFAULT '',
            latency_ms INTEGER DEFAULT 0,
            tokens_input INTEGER DEFAULT 0,
            tokens_output INTEGER DEFAULT 0,
            cost REAL DEFAULT 0.0,
            status TEXT DEFAULT 'ok',
            error_info TEXT DEFAULT '',
            tool_name TEXT DEFAULT '',
            tool_args TEXT DEFAULT '',
            tool_result TEXT DEFAULT '',
            session_id TEXT DEFAULT '',
            task_type TEXT DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_traces_trace_id ON traces(trace_id);
        CREATE INDEX IF NOT EXISTS idx_traces_timestamp ON traces(timestamp);
        CREATE INDEX IF NOT EXISTS idx_traces_status ON traces(status);
        CREATE INDEX IF NOT EXISTS idx_traces_model ON traces(model);
        CREATE VIRTUAL TABLE IF NOT EXISTS traces_fts USING fts5(
            prompt, response, error_info, tool_args, tool_result,
            content='traces', content_rowid='id'
        );
    """)


def estimate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    pricing = MODEL_PRICING.get(model, MODEL_PRICING["unknown"])
    return (tokens_in / 1000 * pricing["input"] + tokens_out / 1000 * pricing["output"]) / 1000


def cmd_log(args):
    conn = get_db()
    trace_id = args.trace_id or str(uuid.uuid4())[:12]
    
    # Get next sequence number for this trace_id
    cur = conn.execute("SELECT COALESCE(MAX(sequence), -1) + 1 FROM traces WHERE trace_id = ?", (trace_id,))
    seq = cur.fetchone()[0]
    
    ts = args.timestamp or datetime.now().isoformat(timespec="seconds")
    tokens_in = args.tokens[0] if args.tokens else 0
    tokens_out = args.tokens[1] if args.tokens and len(args.tokens) > 1 else 0
    cost = args.cost if args.cost is not None else estimate_cost(args.model, tokens_in, tokens_out)
    
    insert_cur = conn.execute("""
        INSERT INTO traces (trace_id, sequence, timestamp, model, prompt, response,
                            latency_ms, tokens_input, tokens_output, cost, status, error_info,
                            tool_name, tool_args, tool_result, session_id, task_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (trace_id, seq, ts, args.model, args.prompt or "", args.response or "",
          args.latency or 0, tokens_in, tokens_out, cost, args.status or "ok",
          args.error or "", args.tool or "", args.tool_args or "", args.tool_result or "",
          args.session or "", args.task_type or ""))
    
    row_id = insert_cur.lastrowid
    conn.commit()
    
    # Sync FTS
    conn.execute("INSERT INTO traces_fts(rowid, prompt, response, error_info, tool_args, tool_result) VALUES (?, ?, ?, ?, ?, ?)",
                 (row_id, args.prompt or "", args.response or "",
                  args.error or "", args.tool_args or "", args.tool_result or ""))
    conn.commit()
    
    result = {"trace_id": trace_id, "sequence": seq, "status": "logged"}
    print(json.dumps(result, ensure_ascii=False))
    conn.close()


def cmd_list(args):
    conn = get_db()
    query = "SELECT * FROM traces WHERE 1=1"
    params = []
    if args.status:
        query += " AND status = ?"
        params.append(args.status)
    if args.model:
        query += " AND model = ?"
        params.append(args.model)
    if args.trace_id:
        query += " AND trace_id = ?"
        params.append(args.trace_id)
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(args.limit or 20)
    
    rows = conn.execute(query, params).fetchall()
    if args.json:
        output = [dict(r) for r in rows]
        print(json.dumps(output, ensure_ascii=False, default=str))
    else:
        print(f"{'ID':<8} {'时间':<20} {'Trace':<18} {'模型':<22} {'延迟':<7} {'状态':<8} {'摘要'}")
        print("-" * 100)
        for r in rows:
            summary = (r["prompt"] or "")[:40].replace("\n", " ")
            print(f"{r['id']:<8} {r['timestamp'][:19]:<20} {r['trace_id']:<18} {r['model']:<22} {r['latency_ms']:<5}ms {r['status']:<8} {summary}")
    conn.close()


def cmd_chain(args):
    conn = get_db()
    rows = conn.execute("SELECT * FROM traces WHERE trace_id = ? ORDER BY sequence ASC", (args.trace_id,)).fetchall()
    if args.json:
        print(json.dumps([dict(r) for r in rows], ensure_ascii=False, default=str))
    else:
        print(f"Trace Chain: {args.trace_id}")
        print(f"共 {len(rows)} 步")
        print("=" * 80)
        for r in rows:
            print(f"\n[Step {r['sequence']}] {r['timestamp'][:19]} | {r['model']} | {r['latency_ms']}ms | {r['status']}")
            if r['prompt']:
                print(f"  Prompt: {r['prompt'][:100]}")
            if r['response']:
                print(f"  Response: {r['response'][:100]}")
            if r['tool_name']:
                print(f"  Tool: {r['tool_name']}")
                if r['tool_args']:
                    print(f"  Args: {r['tool_args'][:100]}")
                if r['tool_result']:
                    print(f"  Result: {r['tool_result'][:100]}")
            if r['cost']:
                print(f"  Cost: ${r['cost']:.6f}")
            if r['status'] != 'ok':
                print(f"  Error: {r['error_info'][:100]}")
    conn.close()


def cmd_search(args):
    conn = get_db()
    results = conn.execute("""
        SELECT t.* FROM traces t
        JOIN traces_fts fts ON t.id = fts.rowid
        WHERE traces_fts MATCH ?
        ORDER BY rank
        LIMIT 20
    """, (args.keyword,)).fetchall()
    
    if args.json:
        print(json.dumps([dict(r) for r in results], ensure_ascii=False, default=str))
    else:
        print(f"Search: '{args.keyword}' — {len(results)} results")
        print("-" * 80)
        for r in results:
            summary = (r["prompt"] or "")[:50].replace("\n", " ")
            print(f"  [{r['timestamp'][:19]}] {r['trace_id']} | {r['model']} | {summary}")
    conn.close()


def cmd_stats(args):
    conn = get_db()
    where = ""
    params = []
    if args.model:
        where = " WHERE model = ?"
        params.append(args.model)
    
    # Overall stats
    row = conn.execute(f"SELECT COUNT(*) as total, AVG(latency_ms) as avg_lat, "
                       f"SUM(CASE WHEN status='error' THEN 1 ELSE 0 END) as errors, "
                       f"SUM(cost) as total_cost, SUM(tokens_input) as total_tokens_in, "
                       f"SUM(tokens_output) as total_tokens_out FROM traces{where}", params).fetchone()
    
    total = row["total"] or 0
    avg_lat = row["avg_lat"] or 0
    errors = row["errors"] or 0
    total_cost = row["total_cost"] or 0
    total_tokens_in = row["total_tokens_in"] or 0
    total_tokens_out = row["total_tokens_out"] or 0
    error_rate = (errors / total * 100) if total > 0 else 0
    
    # By model
    model_rows = conn.execute(f"""
        SELECT model, COUNT(*) as cnt, AVG(latency_ms) as avg_lat,
               SUM(CASE WHEN status='error' THEN 1 ELSE 0 END) as errs,
               SUM(cost) as cost_sum
        FROM traces{where.replace('model = ?', '1=1') if not args.model else ''}
        GROUP BY model ORDER BY cnt DESC
    """).fetchall() if not args.model else []
    
    if args.json:
        stats = {
            "total": total,
            "avg_latency_ms": round(avg_lat, 1),
            "errors": errors,
            "error_rate_pct": round(error_rate, 2),
            "total_cost": round(total_cost, 4),
            "total_tokens_input": total_tokens_in,
            "total_tokens_output": total_tokens_out,
            "by_model": [dict(m) for m in model_rows] if model_rows else []
        }
        print(json.dumps(stats, ensure_ascii=False, default=str))
    else:
        print(f"Stats{' (model: ' + args.model + ')' if args.model else ''}")
        print("=" * 60)
        print(f"  Total calls:     {total}")
        print(f"  Avg latency:     {avg_lat:.0f}ms")
        print(f"  Errors:          {errors} ({error_rate:.1f}%)")
        print(f"  Total cost:      ${total_cost:.4f}")
        print(f"  Tokens in/out:   {total_tokens_in:,} / {total_tokens_out:,}")
        if model_rows:
            print(f"\n  By model:")
            for m in model_rows:
                err_pct = (m["errs"] / m["cnt"] * 100) if m["cnt"] > 0 else 0
                print(f"    {m['model']:<22} {m['cnt']:>5} calls  {m['avg_lat']:.0f}ms avg  ${m['cost_sum']:.4f}  {err_pct:.0f}% err")
    conn.close()


def cmd_status(args):
    conn = get_db()
    cur = conn.execute("SELECT COUNT(*) FROM traces")
    total = cur.fetchone()[0]
    cur = conn.execute("SELECT COUNT(DISTINCT trace_id) FROM traces")
    chains = cur.fetchone()[0]
    cur = conn.execute("SELECT MIN(timestamp), MAX(timestamp) FROM traces")
    ts_range = cur.fetchone()
    cur = conn.execute("SELECT SUM(cost) FROM traces")
    cost = cur.fetchone()[0] or 0
    
    db_size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0
    
    status = {
        "version": VERSION,
        "db_path": DB_PATH,
        "db_size_bytes": db_size,
        "db_size_kb": round(db_size / 1024, 1),
        "total_records": total,
        "total_chains": chains,
        "time_range": {"from": ts_range[0], "to": ts_range[1]} if ts_range[0] else {},
        "total_cost": round(cost, 4),
    }
    print(json.dumps(status, ensure_ascii=False, default=str))
    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Elite Trace — 可观测性追踪系统")
    sub = parser.add_subparsers(dest="command")
    
    # log
    p_log = sub.add_parser("log", help="记录一次调用")
    p_log.add_argument("trace_id", nargs="?", default="", help="追踪ID（不传自动生成）")
    p_log.add_argument("--model", default="unknown", help="模型名称")
    p_log.add_argument("--prompt", default="", help="输入内容")
    p_log.add_argument("--response", default="", help="输出内容")
    p_log.add_argument("--latency", type=int, default=0, help="延迟（毫秒）")
    p_log.add_argument("--tokens", type=int, nargs=2, default=None, metavar=("IN", "OUT"), help="Token数 输入 输出")
    p_log.add_argument("--cost", type=float, default=None, help="实际成本（美元），不传则根据模型估算")
    p_log.add_argument("--status", default="ok", choices=["ok", "error", "timeout"], help="状态")
    p_log.add_argument("--error", default="", help="错误信息")
    p_log.add_argument("--tool", default="", help="工具名称")
    p_log.add_argument("--tool-args", default="", help="工具参数")
    p_log.add_argument("--tool-result", default="", help="工具返回")
    p_log.add_argument("--session", default="", help="会话ID")
    p_log.add_argument("--task-type", default="", help="任务类型")
    p_log.add_argument("--timestamp", default="", help="时间戳")
    
    # list
    p_list = sub.add_parser("list", help="列出调用记录")
    p_list.add_argument("--limit", type=int, default=20)
    p_list.add_argument("--status", choices=["ok", "error"])
    p_list.add_argument("--model")
    p_list.add_argument("--trace-id")
    p_list.add_argument("--json", action="store_true")
    
    # chain
    p_chain = sub.add_parser("chain", help="查看一条追踪链的全部步骤")
    p_chain.add_argument("trace_id")
    p_chain.add_argument("--json", action="store_true")
    
    # search
    p_search = sub.add_parser("search", help="全文搜索调用记录")
    p_search.add_argument("keyword")
    p_search.add_argument("--json", action="store_true")
    
    # stats
    p_stats = sub.add_parser("stats", help="统计汇总")
    p_stats.add_argument("--model")
    p_stats.add_argument("--json", action="store_true")
    
    # status
    sub.add_parser("status", help="系统状态")
    
    args = parser.parse_args()
    
    commands = {
        "log": cmd_log,
        "list": cmd_list,
        "chain": cmd_chain,
        "search": cmd_search,
        "stats": cmd_stats,
        "status": cmd_status,
    }
    
    if args.command not in commands:
        parser.print_help()
        sys.exit(1)
    
    commands[args.command](args)


if __name__ == "__main__":
    main()
