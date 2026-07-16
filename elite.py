#!/usr/bin/env python3
"""
Elite 统一 CLI — 7层记忆系统零配置接入

任何AI客户端只需一行命令即可读写全部记忆：
  elite remember "内容"          # 一键记忆（自动路由）
  elite remember "内容" -c        # 标记为关键记忆
  elite search "关键词"           # 跨层搜索
  elite status                   # 全系统状态
  elite recall "关键词"           # 深度回溯
  elite forget <wal_id>          # 标记过期

设计原则：零配置、自然语言命令、JSON输出
"""

import sys
import os
import json
import time
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
sys.path.insert(0, str(PROJECT_DIR))

def _vprint(msg, **kwargs):
    """只在非JSON模式下打印"""
    if not _JSON_MODE:
        print(msg, **kwargs)

_JSON_MODE = "--json" in sys.argv

# 检测Python路径
def _find_python():
    """找到可用的Python"""
    candidates = [
        Path.home() / ".workbuddy/binaries/python/envs/default/Scripts/python.exe",
        Path.home() / ".workbuddy/binaries/python/versions/3.13.12/python.exe",
        Path.home() / "AppData/Local/Programs/Python/Python312/python.exe",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return sys.executable


# ===================== 统一入口 =====================

def cmd_remember(args):
    """elite remember "content" [--critical|--high|--low]"""
    importance = "normal"
    clean_args = []
    for a in args:
        if a == "--json":
            continue
        if a == "-c" or a == "--critical":
            importance = "critical"
        elif a == "-h" or a == "--high":
            importance = "high"
        elif a == "-l" or a == "--low":
            importance = "low"
        else:
            clean_args.append(a)
    content = " ".join(clean_args) if clean_args else ""

    results = []
    wal_id = ""

    # WAL 写入
    try:
        from elite_wal import WALProtocol
        wal = WALProtocol()
        r = wal.write_through(content, source="cli")
        wal_id = r.get("wal_id", "")
        wal.close()
        results.append({"layer": "WAL", "status": "ok", "id": wal_id})
    except Exception as e:
        results.append({"layer": "WAL", "status": "error", "error": str(e)})

    if importance in ("critical", "high"):
        # L1 + L2
        try:
            from elite_register import Register
            reg = Register()
            key = f"cli_{int(time.time())}"
            reg.set("RECENT", key, content, wal_enabled=False)
            results.append({"layer": "L1", "status": "ok"})
        except Exception as e:
            results.append({"layer": "L1", "status": "error", "error": str(e)})

        try:
            from elite_warmstore import WarmStore
            ws = WarmStore()
            ws.add(content, source="cli")
            results.append({"layer": "L2", "status": "ok"})
        except Exception as e:
            results.append({"layer": "L2", "status": "error", "error": str(e)})

    elif importance == "normal":
        try:
            from elite_warmstore import WarmStore
            ws = WarmStore()
            ws.add(content, source="cli")
            results.append({"layer": "L2", "status": "ok"})
        except Exception:
            # L2不可用时降级到L3
            try:
                from elite_coldstore import ColdStore
                cs = ColdStore()
                cs.archive(content, source="cli")
                results.append({"layer": "L3", "status": "ok"})
            except Exception as e2:
                results.append({"layer": "L2/L3", "status": "error", "error": str(e2)})

    elif importance == "low":
        try:
            from elite_coldstore import ColdStore
            cs = ColdStore()
            cs.archive(content, source="cli")
            results.append({"layer": "L3", "status": "ok"})
        except Exception as e:
            results.append({"layer": "L3", "status": "error", "error": str(e)})

    return {
        "action": "remember",
        "importance": importance,
        "content": content[:100],
        "wal_id": wal_id,
        "results": results,
    }


def cmd_search(args):
    """elite search "query" [--limit N]"""
    limit = 5
    query_parts = []
    skip_next = False
    for a in args:
        if a == "--json":
            continue
        if a == "--limit" or a == "-n":
            skip_next = True
            continue
        if skip_next:
            try:
                limit = int(a)
            except ValueError:
                pass
            skip_next = False
            continue
        if a.startswith("--limit="):
            limit = int(a.split("=")[1])
        elif a.startswith("-n="):
            limit = int(a.split("=")[1])
        else:
            query_parts.append(a)
    query = " ".join(query_parts) if query_parts else ""

    if not query:
        return {"error": "用法: elite search \"搜索关键词\""}

    all_results = []

    # L2 语义搜索
    try:
        from elite_warmstore import WarmStore
        ws = WarmStore()
        for r in ws.search(query, limit=limit):
            rd = dict(r) if hasattr(r, 'keys') else r
            all_results.append({
                "layer": "L2", "score": round(rd.get("score", 0), 4),
                "text": str(rd.get("text", ""))[:200],
            })
    except Exception:
        pass

    # L3 全文搜索
    try:
        from elite_coldstore import ColdStore
        cs = ColdStore()
        for r in cs.search(query, limit=limit):
            rd = dict(r) if hasattr(r, 'keys') else r
            all_results.append({
                "layer": "L3",
                "text": str(rd.get("content", ""))[:200],
            })
    except Exception:
        pass

    # L4 文件搜索
    try:
        from elite_filestore import FileStore
        fs = FileStore()
        for r in fs.search(query, limit=limit):
            rd = dict(r) if hasattr(r, 'keys') else r
            all_results.append({
                "layer": "L4",
                "text": str(rd.get("content", ""))[:200],
                "file": rd.get("file_name", ""),
            })
    except Exception:
        pass

    # L5 压缩搜索
    try:
        from elite_semantic import SemanticStore
        ss = SemanticStore()
        for r in ss.search(query, limit=limit):
            rd = dict(r) if hasattr(r, 'keys') else r
            all_results.append({
                "layer": "L5",
                "text": str(rd.get("summary", rd.get("content", "")))[:200],
            })
    except Exception:
        pass

    # L6 图谱搜索
    try:
        from elite_knowledge import KnowledgeGraph
        kg = KnowledgeGraph()
        for r in kg.search(query, limit=limit):
            rd = dict(r) if hasattr(r, 'keys') else r
            all_results.append({
                "layer": "L6",
                "text": f"{rd.get('name', '')}({rd.get('type', '')}): {str(rd.get('content', ''))[:100]}",
            })
    except Exception:
        pass

    return {
        "action": "search",
        "query": query,
        "total": len(all_results),
        "results": all_results,
    }


def cmd_status(_args=None):
    """elite status"""
    results = {}

    # L1
    try:
        from elite_register import Register
        reg = Register()
        snap = reg.snapshot()
        count = 0
        if isinstance(snap, dict):
            for v in snap.values():
                if isinstance(v, dict):
                    count += len(v)
        results["L1"] = {"type": "寄存器", "count": count, "status": "active"}
    except Exception as e:
        results["L1"] = {"type": "寄存器", "error": str(e)}

    # L2
    try:
        from elite_warmstore import WarmStore
        ws = WarmStore()
        s = ws.stats()
        results["L2"] = {"type": "向量库", "count": s.get("total_records", 0), "status": "active"}
    except Exception as e:
        results["L2"] = {"type": "向量库", "error": str(e)}

    # L3
    try:
        from elite_coldstore import ColdStore
        cs = ColdStore()
        s = cs.status()
        results["L3"] = {"type": "冷存储", "count": s.get("total_records", 0) if isinstance(s, dict) else 0, "status": "active"}
    except Exception as e:
        results["L3"] = {"type": "冷存储", "error": str(e)}

    # L4
    try:
        from elite_filestore import FileStore
        fs = FileStore()
        s = fs.status()
        results["L4"] = {"type": "文件记忆", "count": s.get("total_records", 0) if isinstance(s, dict) else 0, "status": "active"}
    except Exception as e:
        results["L4"] = {"type": "文件记忆", "error": str(e)}

    # L5
    try:
        from elite_semantic import SemanticStore
        ss = SemanticStore()
        s = ss.status()
        results["L5"] = {"type": "语义压缩", "count": s.get("total_records", 0) if isinstance(s, dict) else 0, "status": "active"}
    except Exception as e:
        results["L5"] = {"type": "语义压缩", "error": str(e)}

    # L6
    try:
        from elite_knowledge import KnowledgeGraph
        kg = KnowledgeGraph()
        s = kg.status()
        results["L6"] = {"type": "知识图谱", "entities": s.get("total_entities", 0) if isinstance(s, dict) else 0,
                         "relations": s.get("total_relations", 0) if isinstance(s, dict) else 0, "status": "active"}
    except Exception as e:
        results["L6"] = {"type": "知识图谱", "error": str(e)}

    # WAL
    try:
        from elite_wal import WALProtocol
        wal = WALProtocol()
        s = wal.stats()
        results["WAL"] = {"type": "防丢日志", "count": s.get("total_records", 0),
                         "distribution": s.get("status_distribution", {}), "status": "active"}
        wal.close()
    except Exception as e:
        results["WAL"] = {"type": "防丢日志", "error": str(e)}

    return {"action": "status", "layers": results}


def cmd_recall(args):
    """elite recall "query" — 深度回溯，搜得更深"""
    query = " ".join([a for a in args if a != "--json"]) if args else ""
    if not query:
        return {"error": "用法: elite recall \"回溯内容\""}

    results = cmd_search([query, "--limit=10"])
    results["action"] = "recall"

    # 额外搜索WAL日志
    try:
        from elite_wal import WALProtocol
        wal = WALProtocol()
        wal_records = wal.conn.execute(
            "SELECT id, status, message FROM wal_records ORDER BY created_at DESC LIMIT 20"
        ).fetchall()
        query_lower = query.lower()
        for r in wal_records:
            if query_lower in str(r[2]).lower():
                results["results"].append({
                    "layer": "WAL",
                    "text": str(r[2])[:200],
                    "status": r[1],
                })
        wal.close()
    except Exception:
        pass

    return results


def cmd_forget(args):
    """elite forget <wal_id> — 标记WAL记录为过期"""
    wal_id = args[0] if args else ""
    if not wal_id:
        return {"error": "用法: elite forget <wal_id>"}

    try:
        from elite_wal import WALProtocol
        wal = WALProtocol()
        wal.conn.execute(
            "UPDATE wal_records SET status = 'EXPIRED' WHERE id = ?",
            (wal_id,)
        )
        wal.conn.commit()
        wal._log(wal_id, "cli_forget", "marked expired")
        wal.close()
        return {"action": "forget", "wal_id": wal_id, "status": "ok"}
    except Exception as e:
        return {"action": "forget", "wal_id": wal_id, "error": str(e)}


# ===================== 分发 =====================

COMMANDS = {
    "remember": cmd_remember,
    "r": cmd_remember,
    "search": cmd_search,
    "s": cmd_search,
    "status": cmd_status,
    "st": cmd_status,
    "recall": cmd_recall,
    "rc": cmd_recall,
    "forget": cmd_forget,
    "f": cmd_forget,
}


def main():
    global _JSON_MODE
    _JSON_MODE = "--json" in sys.argv

    if len(sys.argv) < 2:
        print("Elite 7层记忆系统 CLI")
        print()
        print("用法:")
        print("  elite remember \"内容\"         一键记忆")
        print("  elite remember \"内容\" -c      关键记忆 (L1+L2+WAL)")
        print("  elite search \"关键词\"         搜索")
        print("  elite recall \"关键词\"         深度回溯")
        print("  elite status                  系统状态")
        print("  elite forget <id>             标记过期")
        print()
        print("选项:")
        print("  -c, --critical   关键记忆")
        print("  -h, --high       高重要度")
        print("  -l, --low        低重要度")
        print("  --json           JSON输出")
        print("  --limit=N        限制搜索结果")
        return

    cmd = sys.argv[1].lower()
    func = COMMANDS.get(cmd)

    if not func:
        print(f"未知命令: {cmd}")
        print(f"可用: {', '.join(COMMANDS.keys())}")
        return

    result = func(sys.argv[2:])

    if _JSON_MODE:
        print(json.dumps(result, ensure_ascii=False, default=str))
    else:
        # 人类可读输出
        action = result.get("action", "")
        if action in ("remember",):
            imp = result.get("importance", "normal")
            print(f"[remember] importance={imp}")
            for r in result.get("results", []):
                status = r.get("status", "?")
                layer = r.get("layer", "?")
                err = r.get("error", "")
                if err:
                    print(f"  {layer}: FAILED ({err})")
                else:
                    print(f"  {layer}: {status}")
            if result.get("wal_id"):
                print(f"  wal_id: {result['wal_id']}")

        elif action in ("search", "recall"):
            print(f"[{action}] \"{result.get('query', '')}\" → {result.get('total', 0)}条结果")
            for r in result.get("results", []):
                layer = r.get("layer", "?")
                text = r.get("text", "")[:100]
                score = r.get("score", "")
                score_str = f" (score={score})" if score else ""
                file = r.get("file", "")
                file_str = f" [{file}]" if file else ""
                print(f"  [{layer}]{score_str}{file_str} {text}")

        elif action == "status":
            print("=== Elite 7层记忆系统 ===")
            for layer, info in sorted(result.get("layers", {}).items()):
                if "error" in info:
                    print(f"  {layer} {info['type']}: {info['error']}")
                elif layer == "WAL":
                    dist = info.get("distribution", {})
                    print(f"  {layer} {info['type']}: {info['count']}条 {dist}")
                elif layer == "L6":
                    print(f"  {layer} {info['type']}: {info.get('entities',0)}实体+{info.get('relations',0)}关系")
                else:
                    print(f"  {layer} {info['type']}: {info.get('count',0)}条")

        elif action == "forget":
            print(f"[forget] {result.get('wal_id', '')}: {result.get('status', '')}")

        else:
            print(json.dumps(result, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
