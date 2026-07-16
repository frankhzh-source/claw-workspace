#!/usr/bin/env python3
"""
Elite Memory MCP Server — 7层记忆系统统一接入层

将 L1-L6 + WAL 全部封装为 MCP 工具，任何支持 MCP 的 AI 客户端一行配置即可接入。

MCP 配置 (mcp.json):
  {
    "mcpServers": {
      "elite-memory": {
        "type": "stdio",
        "command": "C:\\Users\\jt\\.workbuddy\\binaries\\python\\envs\\default\\Scripts\\python.exe",
        "args": ["C:\\Users\\jt\\WorkBuddy\\Claw\\elite_memory_mcp.py"]
      }
    }
  }
"""

import sys
import os
import json
import time
import traceback
from pathlib import Path

# 确保elite模块可导入
PROJECT_DIR = Path(__file__).parent
sys.path.insert(0, str(PROJECT_DIR))

from mcp.server.fastmcp import FastMCP

# ===================== 初始化 MCP Server =====================
mcp = FastMCP("elite-memory")

# ===================== 懒加载精英模块 =====================
_modules = {}

def _get_module(name: str):
    """懒加载elite模块，避免启动时全部import"""
    if name not in _modules:
        if name == "register":
            from elite_register import Register
            _modules[name] = Register()
        elif name == "warmstore":
            from elite_warmstore import WarmStore
            _modules[name] = WarmStore()
        elif name == "coldstore":
            from elite_coldstore import ColdStore
            _modules[name] = ColdStore()
        elif name == "filestore":
            from elite_filestore import FileStore
            _modules[name] = FileStore()
        elif name == "semantic":
            from elite_semantic import SemanticStore
            _modules[name] = SemanticStore()
        elif name == "knowledge":
            from elite_knowledge import KnowledgeGraph
            _modules[name] = KnowledgeGraph()
        elif name == "wal":
            from elite_wal import WALProtocol
            _modules[name] = WALProtocol()
        elif name == "sync":
            from elite_sync import EliteSync
            _modules[name] = EliteSync()
    return _modules[name]


def _safe_call(func, *args, **kwargs):
    """安全调用，捕获异常返回错误信息"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        return {"error": str(e), "traceback": traceback.format_exc()}


# ===================== 系统级工具 =====================

@mcp.tool()
def elite_status() -> str:
    """查看Elite记忆系统全貌：各层数量、WAL状态、飞书同步情况"""
    results = []
    results.append("=== Elite 7\u5c42\u8bb0\u5fc6\u7cfb\u7edf\u72b6\u6001 ===\n")

    # L1
    try:
        reg = _get_module("register")
        snap = reg.snapshot()
        if isinstance(snap, dict):
            l1_count = 0
            for k, v in snap.items():
                if isinstance(v, dict):
                    l1_count += len(v)
            results.append(f"L1 \u5bc4\u5b58\u5668: {l1_count} \u6761\u6d3b\u8dc3")
            for slot, items in snap.items():
                if isinstance(items, dict) and items:
                    results.append(f"  {slot}: {len(items)} \u6761")
        else:
            results.append(f"L1 \u5bc4\u5b58\u5668: {snap}")
    except Exception as e:
        results.append(f"L1 \u5bc4\u5b58\u5668: \u8bfb\u53d6\u5931\u8d25 ({e})")

    # L2
    try:
        ws = _get_module("warmstore")
        l2_stats = ws.stats()
        results.append(f"L2 \u5411\u91cf\u5e93: {l2_stats.get('total_records', 0)} \u6761")
    except Exception as e:
        results.append(f"L2 \u5411\u91cf\u5e93: \u4e0d\u53ef\u7528 ({type(e).__name__})")

    # L3
    try:
        cs = _get_module("coldstore")
        l3_status = cs.status()
        l3_count = l3_status.get("total_records", 0) if isinstance(l3_status, dict) else 0
        results.append(f"L3 \u51b7\u5b58\u50a8: {l3_count} \u6761")
    except Exception as e:
        results.append(f"L3 \u51b7\u5b58\u50a8: \u8bfb\u53d6\u5931\u8d25 ({type(e).__name__})")

    # L4
    try:
        fs = _get_module("filestore")
        l4_status = fs.status()
        l4_count = l4_status.get("total_records", 0) if isinstance(l4_status, dict) else 0
        results.append(f"L4 \u6587\u4ef6\u8bb0\u5fc6: {l4_count} \u6761")
    except Exception as e:
        results.append(f"L4 \u6587\u4ef6\u8bb0\u5fc6: \u8bfb\u53d6\u5931\u8d25 ({type(e).__name__})")

    # L5
    try:
        sc = _get_module("semantic")
        l5_status = sc.status()
        l5_count = l5_status.get("total_records", 0) if isinstance(l5_status, dict) else 0
        results.append(f"L5 \u8bed\u4e49\u538b\u7f29: {l5_count} \u6761")
    except Exception as e:
        results.append(f"L5 \u8bed\u4e49\u538b\u7f29: \u8bfb\u53d6\u5931\u8d25 ({type(e).__name__})")

    # L6
    try:
        kg = _get_module("knowledge")
        l6_status = kg.status()
        entities = l6_status.get("total_entities", 0) if isinstance(l6_status, dict) else 0
        relations = l6_status.get("total_relations", 0) if isinstance(l6_status, dict) else 0
        results.append(f"L6 \u77e5\u8bc6\u56fe\u8c31: {entities} \u5b9e\u4f53 + {relations} \u5173\u7cfb")
    except Exception as e:
        results.append(f"L6 \u77e5\u8bc6\u56fe\u8c31: \u8bfb\u53d6\u5931\u8d25 ({type(e).__name__})")

    # WAL
    try:
        wal = _get_module("wal")
        wal_stats = wal.stats()
        results.append(f"WAL \u9632\u4e22\u65e5\u5fd7: {wal_stats.get('total_records', 0)} \u6761")
        dist = wal_stats.get("status_distribution", {})
        results.append(f"  \u72b6\u6001\u5206\u5e03: {json.dumps(dist, ensure_ascii=False)}")
    except Exception as e:
        results.append(f"WAL \u9632\u4e22\u65e5\u5fd7: \u8bfb\u53d6\u5931\u8d25 ({type(e).__name__})")

    return "\n".join(results)


# ===================== L1 寄存器工具 =====================

@mcp.tool()
def l1_set(slot: str, key: str, value: str, ttl: int = None) -> str:
    """写入L1寄存器（短期工作记忆）

    Args:
        slot: 槽位名 (RECENT/TASK/CONTEXT/TEMP/GOAL/EMO)
        key: 键名
        value: 值内容
        ttl: 可选TTL（秒），不传则使用默认
    """
    reg = _get_module("register")
    entry = reg.set(slot, key, value, ttl=ttl, wal_enabled=True)
    return json.dumps({
        "status": "ok",
        "slot": slot,
        "key": key,
        "content_hash": entry.get("content_hash", ""),
        "wal_logged": True,
    }, ensure_ascii=False)


@mcp.tool()
def l1_get(slot: str, key: str) -> str:
    """读取L1寄存器中的值"""
    reg = _get_module("register")
    value = reg.get(slot, key)
    if value is None:
        return json.dumps({"status": "not_found", "slot": slot, "key": key})
    return json.dumps({"status": "ok", "slot": slot, "key": key, "value": value}, ensure_ascii=False)


@mcp.tool()
def l1_list(slot: str = None) -> str:
    """列出L1寄存器内容

    Args:
        slot: 可选槽位名，不传则列出全部
    """
    reg = _get_module("register")
    if slot:
        slot = slot.upper()
        items = reg.list_slot(slot)
        return json.dumps({"slot": slot, "count": len(items) if items else 0, "items": items},
                         ensure_ascii=False, default=str)
    snap = reg.snapshot()
    total = sum(len(v) for v in snap.values()) if isinstance(snap, dict) else 0
    summary = {k: len(v) for k, v in snap.items() if v and isinstance(v, dict)} if isinstance(snap, dict) else {}
    return json.dumps({"total": total, "slots": summary}, ensure_ascii=False)


@mcp.tool()
def l1_delete(slot: str, key: str) -> str:
    """删除L1寄存器中的条目"""
    reg = _get_module("register")
    ok = reg.delete(slot, key)
    return json.dumps({"status": "ok" if ok else "not_found", "slot": slot, "key": key})


# ===================== L2 向量库工具 =====================

@mcp.tool()
def l2_search(query: str, limit: int = 5) -> str:
    """在L2向量库中语义搜索

    Args:
        query: 搜索查询文本
        limit: 返回结果数量
    """
    try:
        ws = _get_module("warmstore")
        results = ws.search(query, limit=limit)
        items = []
        for r in results:
            rd = dict(r) if hasattr(r, 'keys') else r
            items.append({
                "text": str(rd.get("text", ""))[:200],
                "score": round(rd.get("score", 0), 4) if isinstance(rd.get("score"), (int, float)) else 0,
                "source": rd.get("source", ""),
            })
        return json.dumps({"query": query, "count": len(items), "results": items}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"query": query, "error": str(e), "results": []}, ensure_ascii=False)


@mcp.tool()
def l2_add(text: str, source: str = "mcp") -> str:
    """向L2向量库添加记忆

    Args:
        text: 记忆文本内容
        source: 来源标识
    """
    try:
        ws = _get_module("warmstore")
        record_id = ws.add(text, source=source)
        return json.dumps({"status": "ok", "record_id": str(record_id)}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False)


# ===================== L3 冷存储工具 =====================

@mcp.tool()
def l3_search(query: str, limit: int = 10) -> str:
    """在L3冷存储中全文搜索

    Args:
        query: 搜索关键词
        limit: 返回结果数量
    """
    cs = _get_module("coldstore")
    results = cs.search(query, limit=limit)
    items = []
    for r in results:
        rd = dict(r) if hasattr(r, 'keys') else r
        items.append({
            "content": str(rd.get("content", ""))[:200],
            "source": rd.get("source", ""),
            "layer": rd.get("layer", "L3"),
        })
    return json.dumps({"query": query, "count": len(items), "results": items}, ensure_ascii=False)


@mcp.tool()
def l3_add(content: str, source: str = "mcp", layer: str = "L3") -> str:
    """向L3冷存储添加记录"""
    cs = _get_module("coldstore")
    record_id = cs.archive(content, source=source)
    return json.dumps({"status": "ok", "record_id": str(record_id)}, ensure_ascii=False)


# ===================== L4 文件记忆工具 =====================

@mcp.tool()
def l4_search(query: str, limit: int = 10) -> str:
    """在L4文件记忆中搜索

    Args:
        query: 搜索关键词
        limit: 返回结果数量
    """
    fs = _get_module("filestore")
    results = fs.search(query, limit=limit)
    items = []
    for r in results:
        rd = dict(r) if hasattr(r, 'keys') else r
        items.append({
            "content": str(rd.get("content", ""))[:200],
            "file_name": rd.get("file_name", ""),
            "source": rd.get("source", ""),
        })
    return json.dumps({"query": query, "count": len(items), "results": items}, ensure_ascii=False)


@mcp.tool()
def l4_add(content: str, file_name: str = "", source: str = "mcp") -> str:
    """向L4文件记忆添加记录"""
    fs = _get_module("filestore")
    record_id = fs.add(content, file_name=file_name, source=source)
    return json.dumps({"status": "ok", "record_id": str(record_id)}, ensure_ascii=False)


# ===================== L5 语义压缩工具 =====================

@mcp.tool()
def l5_search(query: str, limit: int = 10) -> str:
    """在L5语义压缩存储中搜索"""
    sc = _get_module("semantic")
    results = sc.search(query, limit=limit)
    items = []
    for r in results:
        rd = dict(r) if hasattr(r, 'keys') else r
        items.append({
            "summary": str(rd.get("summary", rd.get("content", "")))[:200],
            "source_topics": rd.get("source_topics", ""),
        })
    return json.dumps({"query": query, "count": len(items), "results": items}, ensure_ascii=False)


@mcp.tool()
def l5_stats() -> str:
    """查看L5语义压缩统计"""
    sc = _get_module("semantic")
    stats = sc.status()
    return json.dumps(stats, ensure_ascii=False, default=str)


# ===================== L6 知识图谱工具 =====================

@mcp.tool()
def l6_search(query: str, limit: int = 10) -> str:
    """在L6知识图谱中搜索实体和关系"""
    kg = _get_module("knowledge")
    results = kg.search(query, limit=limit)
    items = []
    for r in results:
        rd = dict(r) if hasattr(r, 'keys') else r
        items.append({
            "name": rd.get("name", ""),
            "type": rd.get("type", ""),
            "content": str(rd.get("content", ""))[:200],
        })
    return json.dumps({"query": query, "count": len(items), "results": items}, ensure_ascii=False)


@mcp.tool()
def l6_add_entity(name: str, entity_type: str, content: str, tags: list = None) -> str:
    """向L6知识图谱添加实体

    Args:
        name: 实体名称
        entity_type: 实体类型 (person/concept/project/tool/event/skill)
        content: 实体描述
        tags: 可选标签列表
    """
    kg = _get_module("knowledge")
    entity_id = kg.add_entity(name, entity_type, content, tags=tags or [])
    return json.dumps({"status": "ok", "entity_id": str(entity_id)}, ensure_ascii=False)


@mcp.tool()
def l6_add_relation(source: str, relation: str, target: str) -> str:
    """向L6知识图谱添加关系

    Args:
        source: 源实体名称
        relation: 关系类型
        target: 目标实体名称
    """
    kg = _get_module("knowledge")
    rel_id = kg.add_relation(source, relation, target)
    return json.dumps({"status": "ok", "relation_id": str(rel_id)}, ensure_ascii=False)


@mcp.tool()
def l6_stats() -> str:
    """查看L6知识图谱统计"""
    kg = _get_module("knowledge")
    stats = kg.status()
    return json.dumps(stats, ensure_ascii=False, default=str)


# ===================== WAL 防丢日志工具 =====================

@mcp.tool()
def wal_begin(message: str, source: str = "user", session_id: str = "") -> str:
    """开始WAL日志记录（收到消息时调用）

    Args:
        message: 收到的消息内容
        source: 来源 (user/system/agent)
        session_id: 可选会话ID
    """
    wal = _get_module("wal")
    result = wal.begin(message, source=source, session_id=session_id)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def wal_confirm(wal_id: str, l1_slot: str = "", l1_key: str = "") -> str:
    """确认WAL记录（L1已持久化后调用，confirm-before-reply）

    Args:
        wal_id: WAL记录ID
        l1_slot: L1槽位名
        l1_key: L1键名
    """
    wal = _get_module("wal")
    result = wal.confirm(wal_id, l1_slot=l1_slot, l1_key=l1_key)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def wal_sync(wal_id: str, l2_hash: str = "") -> str:
    """标记WAL记录已同步到L2/L4

    Args:
        wal_id: WAL记录ID
        l2_hash: L2同步后的内容hash
    """
    wal = _get_module("wal")
    result = wal.sync(wal_id, l2_hash=l2_hash)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def wal_write_through(message: str, source: str = "user",
                      l1_slot: str = "RECENT", l1_key: str = "") -> str:
    """WAL快捷写入：begin -> processing -> confirm 一条龙

    适用于简单消息的快速日志记录，无需分步操作。

    Args:
        message: 消息内容
        source: 来源
        l1_slot: L1槽位
        l1_key: L1键名
    """
    wal = _get_module("wal")
    result = wal.write_through(message, source=source, l1_slot=l1_slot, l1_key=l1_key)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def wal_recover(dry_run: bool = True) -> str:
    """恢复崩溃后未确认的WAL记录

    Args:
        dry_run: True=仅预览不执行，False=执行恢复
    """
    wal = _get_module("wal")
    result = wal.recover(dry_run=dry_run)
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool()
def wal_stats() -> str:
    """查看WAL统计信息"""
    wal = _get_module("wal")
    stats = wal.stats()
    return json.dumps(stats, ensure_ascii=False)


# ===================== 跨层搜索 =====================

@mcp.tool()
def memory_search(query: str, limit: int = 5) -> str:
    """跨层统一搜索：同时搜索L2向量库、L3冷存储、L4文件记忆、L5压缩、L6图谱

    Args:
        query: 搜索查询
        limit: 每层返回结果数量
    """
    all_results = []

    # L2 语义搜索
    try:
        ws = _get_module("warmstore")
        l2_results = ws.search(query, limit=limit)
        for r in l2_results:
            rd = dict(r) if hasattr(r, 'keys') else r
            all_results.append({
                "layer": "L2",
                "text": str(rd.get("text", ""))[:200],
                "score": round(rd.get("score", 0), 4) if isinstance(rd.get("score"), (int, float)) else 0,
                "source": rd.get("source", ""),
            })
    except Exception:
        pass

    # L3 全文搜索
    try:
        cs = _get_module("coldstore")
        l3_results = cs.search(query, limit=limit)
        for r in l3_results:
            rd = dict(r) if hasattr(r, 'keys') else r
            all_results.append({
                "layer": "L3",
                "text": str(rd.get("content", ""))[:200],
                "source": rd.get("source", ""),
            })
    except Exception:
        pass

    # L4 文件搜索
    try:
        fs = _get_module("filestore")
        l4_results = fs.search(query, limit=limit)
        for r in l4_results:
            rd = dict(r) if hasattr(r, 'keys') else r
            all_results.append({
                "layer": "L4",
                "text": str(rd.get("content", ""))[:200],
                "file_name": rd.get("file_name", ""),
            })
    except Exception:
        pass

    # L5 压缩搜索
    try:
        sc = _get_module("semantic")
        l5_results = sc.search(query, limit=limit)
        for r in l5_results:
            rd = dict(r) if hasattr(r, 'keys') else r
            all_results.append({
                "layer": "L5",
                "text": str(rd.get("summary", rd.get("content", "")))[:200],
                "source_topics": rd.get("source_topics", ""),
            })
    except Exception:
        pass

    # L6 图谱搜索
    try:
        kg = _get_module("knowledge")
        l6_results = kg.search(query, limit=limit)
        for r in l6_results:
            rd = dict(r) if hasattr(r, 'keys') else r
            all_results.append({
                "layer": "L6",
                "text": f"{rd.get('name', '')} ({rd.get('type', '')}): {str(rd.get('content', ''))[:100]}",
            })
    except Exception:
        pass

    return json.dumps({
        "query": query,
        "total": len(all_results),
        "results": all_results,
    }, ensure_ascii=False)


# ===================== 快速记忆写入（最常用） =====================

@mcp.tool()
def memory_remember(content: str, source: str = "user", importance: str = "normal") -> str:
    """一键记忆写入：自动路由到合适层级

    根据 importance 自动选择层级：
    - critical: L1 + L2 + WAL
    - high: L1 + L2 + WAL
    - normal: L2 + WAL
    - low: L3

    Args:
        content: 要记忆的内容
        source: 来源标识
        importance: 重要程度 (critical/high/normal/low)
    """
    results = []
    wal_id = ""

    # WAL 记录（总是执行）
    try:
        wal = _get_module("wal")
        wt_result = wal.write_through(content, source=source)
        wal_id = wt_result.get("wal_id", "")
        results.append(f"WAL: ok ({wal_id})")
    except Exception as e:
        results.append(f"WAL: failed ({type(e).__name__})")

    # 根据重要程度路由
    if importance in ("critical", "high"):
        # L1 寄存器
        try:
            reg = _get_module("register")
            key = f"auto_{int(time.time())}"
            reg.set("RECENT", key, content, wal_enabled=False)  # WAL已记录
            results.append("L1: ok")
        except Exception as e:
            results.append(f"L1: failed ({type(e).__name__})")

        # L2 向量库
        try:
            ws = _get_module("warmstore")
            ws.add(content, source=source)
            results.append("L2: ok")
        except Exception as e:
            results.append(f"L2: failed ({type(e).__name__})")

    elif importance == "normal":
        # L2 向量库
        try:
            ws = _get_module("warmstore")
            ws.add(content, source=source)
            results.append("L2: ok")
        except Exception as e:
            results.append(f"L2: failed ({type(e).__name__})")

    elif importance == "low":
        # L3 冷存储
        try:
            cs = _get_module("coldstore")
            cs.archive(content, source=source)
            results.append("L3: ok")
        except Exception as e:
            results.append(f"L3: failed ({type(e).__name__})")

    return json.dumps({
        "status": "ok",
        "importance": importance,
        "wal_id": wal_id,
        "routing": results,
    }, ensure_ascii=False)


# ===================== 飞书同步工具 =====================

@mcp.tool()
def feishu_sync_status() -> str:
    """查看飞书多维表同步状态"""
    results = []

    # L6 同步状态
    try:
        kg = _get_module("knowledge")
        sync_status = kg.get_sync_status()
        results.append(f"L6: {sync_status}")
    except Exception as e:
        results.append(f"L6: {type(e).__name__}")

    # WAL 同步状态
    try:
        wal = _get_module("wal")
        unsynced = wal.get_unsynced_records()
        wal_total = wal.stats().get("total_records", 0)
        synced_count = wal_total - len(unsynced)
        results.append(f"WAL: {synced_count}/{wal_total} \u5df2\u540c\u6b65\u98de\u4e66")
    except Exception as e:
        results.append(f"WAL: {type(e).__name__}")

    return json.dumps({"status": "ok", "details": results}, ensure_ascii=False)


@mcp.tool()
def wal_get_unsynced() -> str:
    """获取WAL中未同步到飞书的记录（供外部MCP调用推送）"""
    wal = _get_module("wal")
    unsynced = wal.get_unsynced_records()
    if not unsynced:
        return json.dumps({"status": "ok", "count": 0, "message": "\u6240\u6709WAL\u8bb0\u5f55\u5df2\u540c\u6b65\u98de\u4e66"})
    feishu_data = wal.get_feishu_batch_data(unsynced)
    return json.dumps({
        "status": "ok",
        "count": len(unsynced),
        "wal_ids": [r["id"] for r in unsynced],
        "feishu_records": feishu_data,
    }, ensure_ascii=False)


@mcp.tool()
def wal_set_feishu_id(wal_id: str, feishu_id: str) -> str:
    """回写飞书记录ID到本地WAL（推送飞书后调用）"""
    wal = _get_module("wal")
    wal.update_feishu_id(wal_id, feishu_id)
    return json.dumps({"status": "ok", "wal_id": wal_id, "feishu_id": feishu_id})


# ===================== 启动 =====================

if __name__ == "__main__":
    mcp.run(transport="stdio")
