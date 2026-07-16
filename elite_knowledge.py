"""
Elite L6 Knowledge Graph - 知识图谱记忆层
实体-关系三元组，跨层语义关联，图遍历与路径查询。

架构：
  SQLite + FTS5 知识图谱
  ├── knowledge.db       -- 实体表 + 关系表 + FTS索引
  ├── knowledge.json     -- 元信息（飞书同步状态、统计）
  └── snapshots/         -- 时间快照目录

与 Elite 架构的关系：
  L1(寄存器) -> L2(向量库) -> L3(冷存储) -> L4(文件记忆) -> L5(语义压缩) -> L6(知识图谱)
                                                                          |
                                                              实体提取 -> 实体节点
                                                              关系发现 -> 三元组 (s-p-o)
                                                              跨层关联 -> 语义图谱
                                                              L6 <-> 飞书: 图谱记录双向映射（L6-图谱）
                                                              L5 关键词/实体 -> L6 节点种子

知识图谱模型：
  实体(Entity): id, name, type, layer_source, source_id, description, attributes
  关系(Relation): id, subject_id, predicate, object_id, confidence, evidence, layer_source

核心能力：
  add-entity:      添加实体节点
  add-relation:    添加关系三元组
  auto-extract:    从 L2-L5 自动提取实体和关系
  search:         全文搜索（FTS5+LIKE 双通道，中文友好）
  traverse:       从实体出发遍历关系
  path:           两实体间路径查找（BFS）
  neighbors:      实体的邻居节点
  list:           列出实体/关系
  info:           查看实体/关系详情
  merge:          合并重复实体
  push:           L6 -> 飞书多维表格（图谱记录映射）
  pull:           飞书多维表格 -> L6（逆向恢复）
  sync-status:    飞书同步状态
  snapshot:       时间快照
  status:         统计概览
  log:            操作日志

CLI:
  python elite_knowledge.py add-entity <name> [--type TYPE] [--desc DESC] [--layer L2] [--source-id ID]
  python elite_knowledge.py add-relation <subject_id> <predicate> <object_id> [--confidence 0.8] [--evidence TEXT]
  python elite_knowledge.py auto-extract [--min-length 50]
  python elite_knowledge.py search <query> [--limit 10]
  python elite_knowledge.py traverse <entity_id> [--depth 2] [--direction both]
  python elite_knowledge.py path <entity_id_1> <entity_id_2> [--max-depth 4]
  python elite_knowledge.py neighbors <entity_id>
  python elite_knowledge.py list-entities [--type TYPE] [--layer L2] [--limit 20]
  python elite_knowledge.py list-relations [--predicate PRED] [--limit 20]
  python elite_knowledge.py info <entity_or_relation_id>
  python elite_knowledge.py merge <entity_id_1> <entity_id_2>
  python elite_knowledge.py push [--all]
  python elite_knowledge.py pull
  python elite_knowledge.py sync-status
  python elite_knowledge.py snapshot
  python elite_knowledge.py status
  python elite_knowledge.py log [--limit 20]
"""

import json
import time
import hashlib
import sqlite3
import sys
import os
import re
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict, deque

# ===================== 配置 =====================
KG_DIR = str(Path.home() / ".openclaw" / "memory" / "knowledge")
KG_DB = str(Path(KG_DIR) / "knowledge.db")
KG_META = str(Path(KG_DIR) / "knowledge.json")
SNAPSHOT_DIR = str(Path(KG_DIR) / "snapshots")

# 飞书多维表格配置（与其他层共用同一张表，通过 记忆层级=L6-图谱 区分）
FEISHU_APP_TOKEN = "G56JbFHC0abrj2sdgIwcE9Cenn2"
FEISHU_TABLE_ID = "tblZxOCAmGAk84cJ"
FEISHU_FOLDER_ID = "ERi3fwcAql5qKhdNpKacpyhXnih"

# 实体类型
ENTITY_TYPES = [
    "concept", "person", "org", "tool", "file", "layer",
    "project", "event", "technology", "location", "other"
]

# 关系谓词预设
PREDICATES = [
    "属于", "包含", "依赖", "关联", "使用", "实现", "替代",
    "同步", "映射", "压缩", "归档", "恢复", "晋升",
    "part_of", "has_part", "depends_on", "uses", "implements",
    "syncs_with", "maps_to", "compresses", "archives", "restores"
]

# 中文停用词
STOP_WORDS = set(
    "的 了 是 在 我 有 和 就 不 人 都 一 一个 上 也 很 到 说 要 去 你 会 着 没有 看 好 "
    "自己 这 他 她 它 们 那 些 什么 怎么 这个 那个 还 就是 可以 没 能 被 从 把 而 与 "
    "但 如 因为 所以 如果 那么 虽然 可是 或者 而且 其中 通过 进行 可以 已经 之后 "
    "对于 关于 由于 以及 包括 同时 另外 此外 不仅 还是 只是 然而 可是 不是 而是 "
    "之 其 此 该 本 各 某 每 另 非 未 将 于 及 等 以 为 则 且 若 因 故 遂 乃 亦".split()
)


# ===================== KnowledgeGraph 类 =====================
class KnowledgeGraph:
    def __init__(self):
        os.makedirs(KG_DIR, exist_ok=True)
        os.makedirs(SNAPSHOT_DIR, exist_ok=True)
        self._init_db()
        self._meta = self._load_meta()
        self._log("init", "", "L6 Knowledge Graph initialized")

    def _init_db(self):
        self.conn = sqlite3.connect(KG_DB)
        self.conn.row_factory = sqlite3.Row
        c = self.conn.cursor()

        # 实体表
        c.execute("""CREATE TABLE IF NOT EXISTS entities (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT DEFAULT 'concept',
            layer_source TEXT DEFAULT '',
            source_id TEXT DEFAULT '',
            description TEXT DEFAULT '',
            attributes TEXT DEFAULT '{}',
            content_hash TEXT DEFAULT '',
            feishu_id TEXT DEFAULT '',
            created_at REAL,
            updated_at REAL,
            last_accessed REAL,
            status TEXT DEFAULT 'active',
            source TEXT DEFAULT 'manual'
        )""")

        # 关系表
        c.execute("""CREATE TABLE IF NOT EXISTS relations (
            id TEXT PRIMARY KEY,
            subject_id TEXT NOT NULL,
            predicate TEXT NOT NULL,
            object_id TEXT NOT NULL,
            confidence REAL DEFAULT 1.0,
            evidence TEXT DEFAULT '',
            layer_source TEXT DEFAULT '',
            content_hash TEXT DEFAULT '',
            feishu_id TEXT DEFAULT '',
            created_at REAL,
            updated_at REAL,
            status TEXT DEFAULT 'active',
            source TEXT DEFAULT 'manual',
            FOREIGN KEY (subject_id) REFERENCES entities(id),
            FOREIGN KEY (object_id) REFERENCES entities(id)
        )""")

        # FTS5 实体索引
        c.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS fts_entities
            USING fts5(name, type, description, attributes, content=entities, content_rowid=rowid)""")

        # FTS5 关系索引
        c.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS fts_relations
            USING fts5(predicate, evidence, layer_source, content=relations, content_rowid=rowid)""")

        # FTS 同步触发器
        c.execute("""CREATE TRIGGER IF NOT EXISTS entities_ai AFTER INSERT ON entities BEGIN
            INSERT INTO fts_entities(rowid, name, type, description, attributes)
            VALUES (new.rowid, new.name, new.type, new.description, new.attributes);
        END""")
        c.execute("""CREATE TRIGGER IF NOT EXISTS entities_ad AFTER DELETE ON entities BEGIN
            INSERT INTO fts_entities(fts_entities, rowid, name, type, description, attributes)
            VALUES ('delete', old.rowid, old.name, old.type, old.description, old.attributes);
        END""")
        c.execute("""CREATE TRIGGER IF NOT EXISTS entities_au AFTER UPDATE ON entities BEGIN
            INSERT INTO fts_entities(fts_entities, rowid, name, type, description, attributes)
            VALUES ('delete', old.rowid, old.name, old.type, old.description, old.attributes);
            INSERT INTO fts_entities(rowid, name, type, description, attributes)
            VALUES (new.rowid, new.name, new.type, new.description, new.attributes);
        END""")

        c.execute("""CREATE TRIGGER IF NOT EXISTS relations_ai AFTER INSERT ON relations BEGIN
            INSERT INTO fts_relations(rowid, predicate, evidence, layer_source)
            VALUES (new.rowid, new.predicate, new.evidence, new.layer_source);
        END""")
        c.execute("""CREATE TRIGGER IF NOT EXISTS relations_ad AFTER DELETE ON relations BEGIN
            INSERT INTO fts_relations(fts_relations, rowid, predicate, evidence, layer_source)
            VALUES ('delete', old.rowid, old.predicate, old.evidence, old.layer_source);
        END""")
        c.execute("""CREATE TRIGGER IF NOT EXISTS relations_au AFTER UPDATE ON relations BEGIN
            INSERT INTO fts_relations(fts_relations, rowid, predicate, evidence, layer_source)
            VALUES ('delete', old.rowid, old.predicate, old.evidence, old.layer_source);
            INSERT INTO fts_relations(rowid, predicate, evidence, layer_source)
            VALUES (new.rowid, new.predicate, new.evidence, new.layer_source);
        END""")

        # 操作日志表
        c.execute("""CREATE TABLE IF NOT EXISTS kg_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT,
            target TEXT,
            detail TEXT,
            timestamp REAL
        )""")

        self.conn.commit()

    # ---------- 元信息 ----------
    def _load_meta(self) -> dict:
        if os.path.exists(KG_META):
            try:
                with open(KG_META, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "created_at": time.time(),
            "version": "1.0",
            "feishu_sync": {"synced_entity_hashes": [], "synced_relation_hashes": [],
                            "synced_feishu_ids": [], "last_push_ts": 0, "last_pull_ts": 0},
        }

    def _save_meta(self):
        with open(KG_META, "w", encoding="utf-8") as f:
            json.dump(self._meta, f, ensure_ascii=False, indent=2)

    # ---------- 日志 ----------
    def _log(self, action: str, target: str, detail: str):
        self.conn.execute(
            "INSERT INTO kg_log (action, target, detail, timestamp) VALUES (?,?,?,?)",
            (action, target, detail, time.time()),
        )
        self.conn.commit()

    # ---------- 哈希 ----------
    @staticmethod
    def _content_hash(text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()[:12]

    @staticmethod
    def _relation_hash(subject_id: str, predicate: str, object_id: str) -> str:
        return hashlib.md5(f"{subject_id}|{predicate}|{object_id}".encode("utf-8")).hexdigest()[:12]

    # ---------- FTS5 查询构建 ----------
    @staticmethod
    def _make_fts_query(query: str) -> str:
        """中文友好 FTS5 查询：单字 OR + 后缀匹配"""
        tokens = []
        for ch in query:
            if ch.strip() and ch not in STOP_WORDS:
                tokens.append(f'"{ch}"')
        if not tokens:
            return f'"{query}"'
        return " OR ".join(tokens[:20])

    # ===================== 实体操作 =====================

    def add_entity(self, name: str, etype: str = "concept",
                   layer_source: str = "", source_id: str = "",
                   description: str = "", attributes: dict = None,
                   source: str = "manual") -> dict:
        """添加实体节点"""
        content_hash = self._content_hash(f"{name}:{etype}:{layer_source}")

        # 去重：同名+同类型+同来源视为重复
        existing = self.conn.execute(
            "SELECT id FROM entities WHERE content_hash = ? AND status = 'active'",
            (content_hash,),
        ).fetchone()
        if existing:
            return {"status": "dup", "id": existing["id"], "message": "Entity already exists"}

        entity_id = f"E6-{int(time.time())}-{content_hash}"
        now = time.time()
        attrs = json.dumps(attributes or {}, ensure_ascii=False)

        self.conn.execute(
            """INSERT INTO entities
            (id, name, type, layer_source, source_id, description, attributes,
             content_hash, created_at, updated_at, last_accessed, status, source)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (entity_id, name, etype, layer_source, source_id, description, attrs,
             content_hash, now, now, now, "active", source),
        )
        self.conn.commit()
        self._log("add_entity", entity_id, f"{name} ({etype})")
        return {"status": "ok", "id": entity_id, "name": name, "type": etype}

    def add_relation(self, subject_id: str, predicate: str, object_id: str,
                     confidence: float = 1.0, evidence: str = "",
                     layer_source: str = "", source: str = "manual") -> dict:
        """添加关系三元组"""
        # 验证实体存在
        sub = self.conn.execute("SELECT id, name FROM entities WHERE id = ?", (subject_id,)).fetchone()
        obj = self.conn.execute("SELECT id, name FROM entities WHERE id = ?", (object_id,)).fetchone()
        if not sub:
            return {"status": "error", "message": f"Subject entity not found: {subject_id}"}
        if not obj:
            return {"status": "error", "message": f"Object entity not found: {object_id}"}

        rel_hash = self._relation_hash(subject_id, predicate, object_id)

        # 去重
        existing = self.conn.execute(
            "SELECT id FROM relations WHERE content_hash = ? AND status = 'active'",
            (rel_hash,),
        ).fetchone()
        if existing:
            return {"status": "dup", "id": existing["id"], "message": "Relation already exists"}

        rel_id = f"R6-{int(time.time())}-{rel_hash}"
        now = time.time()

        self.conn.execute(
            """INSERT INTO relations
            (id, subject_id, predicate, object_id, confidence, evidence,
             layer_source, content_hash, created_at, updated_at, status, source)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (rel_id, subject_id, predicate, object_id, confidence, evidence,
             layer_source, rel_hash, now, now, "active", source),
        )
        self.conn.commit()
        self._log("add_relation", rel_id, f"{sub['name']} -{predicate}-> {obj['name']}")
        return {"status": "ok", "id": rel_id, "subject": sub["name"],
                "predicate": predicate, "object": obj["name"]}

    # ===================== 搜索 =====================

    def search(self, query: str, limit: int = 10) -> list:
        """搜索实体和关系（FTS5+LIKE 双通道）"""
        results = []
        seen = set()

        # FTS5 实体搜索
        fts_q = self._make_fts_query(query)
        try:
            rows = self.conn.execute(
                f"""SELECT e.* FROM entities e
                JOIN fts_entities f ON e.rowid = f.rowid
                WHERE fts_entities MATCH ? AND e.status = 'active'
                ORDER BY e.last_accessed DESC LIMIT ?""",
                (fts_q, limit),
            ).fetchall()
            for r in rows:
                rd = dict(r)
                if rd["id"] not in seen:
                    seen.add(rd["id"])
                    rd["match_type"] = "entity"
                    results.append(rd)
        except sqlite3.OperationalError:
            pass

        # LIKE 实体兜底
        try:
            rows = self.conn.execute(
                """SELECT * FROM entities
                WHERE (name LIKE ? OR description LIKE ? OR type LIKE ?)
                AND status = 'active' ORDER BY last_accessed DESC LIMIT ?""",
                (f"%{query}%", f"%{query}%", f"%{query}%", limit),
            ).fetchall()
            for r in rows:
                rd = dict(r)
                if rd["id"] not in seen:
                    seen.add(rd["id"])
                    rd["match_type"] = "entity"
                    results.append(rd)
        except sqlite3.OperationalError:
            pass

        # FTS5 关系搜索
        try:
            rows = self.conn.execute(
                f"""SELECT r.* FROM relations r
                JOIN fts_relations f ON r.rowid = f.rowid
                WHERE fts_relations MATCH ? AND r.status = 'active'
                ORDER BY r.last_accessed DESC LIMIT ?""",
                (fts_q, limit),
            ).fetchall()
            for r in rows:
                rd = dict(r)
                if rd["id"] not in seen:
                    seen.add(rd["id"])
                    rd["match_type"] = "relation"
                    results.append(rd)
        except sqlite3.OperationalError:
            pass

        # LIKE 关系兜底
        try:
            rows = self.conn.execute(
                """SELECT * FROM relations
                WHERE (predicate LIKE ? OR evidence LIKE ?)
                AND status = 'active' ORDER BY last_accessed DESC LIMIT ?""",
                (f"%{query}%", f"%{query}%", limit),
            ).fetchall()
            for r in rows:
                rd = dict(r)
                if rd["id"] not in seen:
                    seen.add(rd["id"])
                    rd["match_type"] = "relation"
                    results.append(rd)
        except sqlite3.OperationalError:
            pass

        return results[:limit]

    # ===================== 图遍历 =====================

    def traverse(self, entity_id: str, depth: int = 2, direction: str = "both") -> dict:
        """从实体出发遍历关系图"""
        entity = self.conn.execute(
            "SELECT * FROM entities WHERE id = ? AND status = 'active'", (entity_id,)
        ).fetchone()
        if not entity:
            return {"status": "error", "message": f"Entity not found: {entity_id}"}

        visited_nodes = {entity_id: dict(entity)}
        visited_edges = []
        queue = deque([(entity_id, 0)])

        while queue:
            current_id, current_depth = queue.popleft()
            if current_depth >= depth:
                continue

            # 出边
            if direction in ("both", "out"):
                rows = self.conn.execute(
                    """SELECT r.*, e.name as object_name FROM relations r
                    JOIN entities e ON r.object_id = e.id
                    WHERE r.subject_id = ? AND r.status = 'active'""",
                    (current_id,),
                ).fetchall()
                for r in rows:
                    rd = dict(r)
                    edge_key = (rd["subject_id"], rd["predicate"], rd["object_id"])
                    if edge_key not in [(e[0], e[1], e[2]) for e in visited_edges]:
                        visited_edges.append(edge_key)
                    if rd["object_id"] not in visited_nodes:
                        obj = self.conn.execute(
                            "SELECT * FROM entities WHERE id = ?", (rd["object_id"],)
                        ).fetchone()
                        if obj:
                            visited_nodes[rd["object_id"]] = dict(obj)
                            queue.append((rd["object_id"], current_depth + 1))

            # 入边
            if direction in ("both", "in"):
                rows = self.conn.execute(
                    """SELECT r.*, e.name as subject_name FROM relations r
                    JOIN entities e ON r.subject_id = e.id
                    WHERE r.object_id = ? AND r.status = 'active'""",
                    (current_id,),
                ).fetchall()
                for r in rows:
                    rd = dict(r)
                    edge_key = (rd["subject_id"], rd["predicate"], rd["object_id"])
                    if edge_key not in [(e[0], e[1], e[2]) for e in visited_edges]:
                        visited_edges.append(edge_key)
                    if rd["subject_id"] not in visited_nodes:
                        sub = self.conn.execute(
                            "SELECT * FROM entities WHERE id = ?", (rd["subject_id"],)
                        ).fetchone()
                        if sub:
                            visited_nodes[rd["subject_id"]] = dict(sub)
                            queue.append((rd["subject_id"], current_depth + 1))

        return {
            "status": "ok",
            "root": entity_id,
            "depth": depth,
            "nodes": len(visited_nodes),
            "edges": len(visited_edges),
            "node_details": {k: {"name": v["name"], "type": v["type"]}
                             for k, v in visited_nodes.items()},
            "edge_details": [{"subject": s, "predicate": p, "object": o}
                             for s, p, o in visited_edges],
        }

    def path(self, from_id: str, to_id: str, max_depth: int = 4) -> dict:
        """两实体间最短路径（BFS）"""
        if from_id == to_id:
            from_ent = self.conn.execute(
                "SELECT name FROM entities WHERE id = ?", (from_id,)
            ).fetchone()
            return {"status": "ok", "path": [from_id], "names": [from_ent["name"] if from_ent else from_id], "length": 0}

        visited = {from_id: None}  # id -> (parent_id, predicate, direction)
        queue = deque([(from_id, 0)])

        while queue:
            current_id, current_depth = queue.popleft()
            if current_depth >= max_depth:
                continue

            # 出边
            rows = self.conn.execute(
                """SELECT object_id, predicate FROM relations
                WHERE subject_id = ? AND status = 'active'""",
                (current_id,),
            ).fetchall()
            for r in rows:
                next_id = r["object_id"]
                if next_id not in visited:
                    visited[next_id] = (current_id, r["predicate"], "out")
                    if next_id == to_id:
                        # 回溯路径
                        return self._build_path(visited, from_id, to_id)
                    queue.append((next_id, current_depth + 1))

            # 入边
            rows = self.conn.execute(
                """SELECT subject_id, predicate FROM relations
                WHERE object_id = ? AND status = 'active'""",
                (current_id,),
            ).fetchall()
            for r in rows:
                next_id = r["subject_id"]
                if next_id not in visited:
                    visited[next_id] = (current_id, r["predicate"], "in")
                    if next_id == to_id:
                        return self._build_path(visited, from_id, to_id)
                    queue.append((next_id, current_depth + 1))

        return {"status": "no_path", "message": f"No path found within depth {max_depth}"}

    def _build_path(self, visited: dict, from_id: str, to_id: str) -> dict:
        """从 BFS 回溯结果构建路径"""
        path_ids = []
        path_edges = []
        current = to_id
        while current != from_id:
            path_ids.append(current)
            parent, predicate, direction = visited[current]
            path_edges.append((parent, predicate, current, direction))
            current = parent
        path_ids.append(from_id)
        path_ids.reverse()
        path_edges.reverse()

        # 获取名称
        names = {}
        for eid in path_ids:
            ent = self.conn.execute("SELECT name FROM entities WHERE id = ?", (eid,)).fetchone()
            names[eid] = ent["name"] if ent else eid

        return {
            "status": "ok",
            "path": path_ids,
            "names": [names[eid] for eid in path_ids],
            "edges": [{"from": s, "predicate": p, "to": o, "direction": d,
                       "from_name": names[s], "to_name": names[o]}
                      for s, p, o, d in path_edges],
            "length": len(path_edges),
        }

    def neighbors(self, entity_id: str) -> dict:
        """获取实体的直接邻居"""
        entity = self.conn.execute(
            "SELECT * FROM entities WHERE id = ? AND status = 'active'", (entity_id,)
        ).fetchone()
        if not entity:
            return {"status": "error", "message": f"Entity not found: {entity_id}"}

        outgoing = []
        for r in self.conn.execute(
            """SELECT r.id, r.predicate, r.object_id, e.name as object_name, e.type as object_type
            FROM relations r JOIN entities e ON r.object_id = e.id
            WHERE r.subject_id = ? AND r.status = 'active'""",
            (entity_id,),
        ).fetchall():
            rd = dict(r)
            outgoing.append(rd)

        incoming = []
        for r in self.conn.execute(
            """SELECT r.id, r.predicate, r.subject_id, e.name as subject_name, e.type as subject_type
            FROM relations r JOIN entities e ON r.subject_id = e.id
            WHERE r.object_id = ? AND r.status = 'active'""",
            (entity_id,),
        ).fetchall():
            rd = dict(r)
            incoming.append(rd)

        return {
            "status": "ok",
            "entity": {"id": entity_id, "name": entity["name"], "type": entity["type"]},
            "outgoing": outgoing,
            "incoming": incoming,
            "total_connections": len(outgoing) + len(incoming),
        }

    # ===================== 列表 / 详情 =====================

    def list_entities(self, etype: str = "", layer: str = "", limit: int = 20) -> list:
        sql = "SELECT * FROM entities WHERE status = 'active'"
        params = []
        if etype:
            sql += " AND type = ?"
            params.append(etype)
        if layer:
            sql += " AND layer_source = ?"
            params.append(layer)
        sql += " ORDER BY last_accessed DESC LIMIT ?"
        params.append(limit)
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def list_relations(self, predicate: str = "", limit: int = 20) -> list:
        sql = "SELECT * FROM relations WHERE status = 'active'"
        params = []
        if predicate:
            sql += " AND predicate = ?"
            params.append(predicate)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def info(self, item_id: str) -> dict:
        """查看实体或关系详情"""
        # 先查实体
        row = self.conn.execute("SELECT * FROM entities WHERE id = ?", (item_id,)).fetchone()
        if row:
            rd = dict(row)
            # 获取邻居数
            out_cnt = self.conn.execute(
                "SELECT COUNT(*) FROM relations WHERE subject_id = ? AND status = 'active'",
                (item_id,),
            ).fetchone()[0]
            in_cnt = self.conn.execute(
                "SELECT COUNT(*) FROM relations WHERE object_id = ? AND status = 'active'",
                (item_id,),
            ).fetchone()[0]
            rd["outgoing_relations"] = out_cnt
            rd["incoming_relations"] = in_cnt
            rd["total_degree"] = out_cnt + in_cnt
            # 更新访问时间
            self.conn.execute(
                "UPDATE entities SET last_accessed = ? WHERE id = ?",
                (time.time(), item_id),
            )
            self.conn.commit()
            return {"status": "ok", "type": "entity", "data": rd}

        # 再查关系
        row = self.conn.execute("SELECT * FROM relations WHERE id = ?", (item_id,)).fetchone()
        if row:
            rd = dict(row)
            sub = self.conn.execute("SELECT name FROM entities WHERE id = ?", (rd["subject_id"],)).fetchone()
            obj = self.conn.execute("SELECT name FROM entities WHERE id = ?", (rd["object_id"],)).fetchone()
            rd["subject_name"] = sub["name"] if sub else rd["subject_id"]
            rd["object_name"] = obj["name"] if obj else rd["object_id"]
            return {"status": "ok", "type": "relation", "data": rd}

        return {"status": "error", "message": f"Not found: {item_id}"}

    # ===================== 合并实体 =====================

    def merge(self, primary_id: str, secondary_id: str) -> dict:
        """合并两个实体（secondary 并入 primary）"""
        primary = self.conn.execute("SELECT * FROM entities WHERE id = ?", (primary_id,)).fetchone()
        secondary = self.conn.execute("SELECT * FROM entities WHERE id = ?", (secondary_id,)).fetchone()
        if not primary or not secondary:
            return {"status": "error", "message": "One or both entities not found"}

        # 把 secondary 的所有关系转给 primary
        self.conn.execute(
            "UPDATE relations SET subject_id = ? WHERE subject_id = ?",
            (primary_id, secondary_id),
        )
        self.conn.execute(
            "UPDATE relations SET object_id = ? WHERE object_id = ?",
            (primary_id, secondary_id),
        )
        # 标记 secondary 为 merged
        self.conn.execute(
            "UPDATE entities SET status = 'merged', updated_at = ? WHERE id = ?",
            (time.time(), secondary_id),
        )
        # 合并描述
        new_desc = primary["description"]
        if secondary["description"] and secondary["description"] not in new_desc:
            new_desc = f"{new_desc}; {secondary["description"]}" if new_desc else secondary["description"]
        self.conn.execute(
            "UPDATE entities SET description = ?, updated_at = ? WHERE id = ?",
            (new_desc, time.time(), primary_id),
        )
        self.conn.commit()
        self._log("merge", primary_id, f"Merged {secondary_id} into {primary_id}")
        return {"status": "ok", "primary": primary_id, "merged": secondary_id}

    # ===================== 自动提取 =====================

    def auto_extract(self, min_length: int = 50) -> dict:
        """从 L2-L5 自动提取实体和关系"""
        entities_added = 0
        entities_dup = 0
        relations_added = 0
        relations_dup = 0
        errors = []

        # ---- L2 向量库 ----
        try:
            import lancedb
            db = lancedb.connect(str(Path.home() / ".openclaw" / "memory" / "lancedb"))
            tbl = db.open_table("elite_memory")
            data = tbl.head(200).to_pydict()
            for i in range(len(data.get("text", []))):
                text_val = data["text"][i]
                layer_val = data.get("layer", [""])[i]
                id_val = data.get("id", [""])[i]
                if len(text_val) >= min_length:
                    ext = self._extract_from_text(text_val, layer_val, id_val)
                    entities_added += ext["entities_added"]
                    entities_dup += ext["entities_dup"]
                    relations_added += ext["relations_added"]
                    relations_dup += ext["relations_dup"]
        except Exception as e:
            errors.append(f"L2: {e}")

        # ---- L3 冷存储 ----
        cs_path = str(Path.home() / ".openclaw" / "memory" / "coldstore" / "coldstore.db")
        if os.path.exists(cs_path):
            try:
                conn2 = sqlite3.connect(cs_path)
                conn2.row_factory = sqlite3.Row
                rows = conn2.execute(
                    f"SELECT id, text, layer FROM archive WHERE length(text) > ?",
                    (min_length,),
                ).fetchall()
                for r in rows:
                    ext = self._extract_from_text(r["text"], r["layer"] or "L3", r["id"])
                    entities_added += ext["entities_added"]
                    entities_dup += ext["entities_dup"]
                    relations_added += ext["relations_added"]
                    relations_dup += ext["relations_dup"]
                conn2.close()
            except Exception as e:
                errors.append(f"L3: {e}")

        # ---- L4 文件记忆 ----
        fs_path = str(Path.home() / ".openclaw" / "memory" / "filestore" / "filestore.db")
        if os.path.exists(fs_path):
            try:
                conn2 = sqlite3.connect(fs_path)
                conn2.row_factory = sqlite3.Row
                rows = conn2.execute(
                    "SELECT id, description, category FROM files WHERE length(description) > ? AND description != ''",
                    (min_length,),
                ).fetchall()
                for r in rows:
                    ext = self._extract_from_text(r["description"], "L4", r["id"])
                    entities_added += ext["entities_added"]
                    entities_dup += ext["entities_dup"]
                    relations_added += ext["relations_added"]
                    relations_dup += ext["relations_dup"]
                conn2.close()
            except Exception as e:
                errors.append(f"L4: {e}")

        # ---- L5 语义压缩 ----
        sem_path = str(Path.home() / ".openclaw" / "memory" / "semantic" / "semantic.db")
        if os.path.exists(sem_path):
            try:
                conn2 = sqlite3.connect(sem_path)
                conn2.row_factory = sqlite3.Row
                rows = conn2.execute(
                    "SELECT id, compressed_text, keywords, entities, original_layer FROM compressed WHERE status = 'active'",
                ).fetchall()
                for r in rows:
                    # L5 已有提取的关键词和实体，直接用
                    kw_list = json.loads(r["keywords"]) if r["keywords"] else []
                    ent_list = json.loads(r["entities"]) if r["entities"] else []
                    layer_val = r["original_layer"] or "L5"

                    # 从 L5 关键词创建实体
                    for kw in kw_list[:5]:
                        res = self.add_entity(kw, "concept", layer_val, r["id"],
                                              source="auto:L5")
                        if res["status"] == "ok":
                            entities_added += 1
                        else:
                            entities_dup += 1

                    # 从 L5 实体创建实体
                    for ent in ent_list[:5]:
                        res = self.add_entity(ent, self._guess_entity_type(ent), layer_val, r["id"],
                                              source="auto:L5")
                        if res["status"] == "ok":
                            entities_added += 1
                        else:
                            entities_dup += 1

                conn2.close()
            except Exception as e:
                errors.append(f"L5: {e}")

        # ---- 层间关系自动构建 ----
        layer_relations = self._build_layer_relations()
        relations_added += layer_relations["added"]
        relations_dup += layer_relations["dup"]

        self._log("auto_extract", "",
                  f"entities_added={entities_added} entities_dup={entities_dup} "
                  f"relations_added={relations_added} relations_dup={relations_dup} "
                  f"errors={len(errors)}")
        return {
            "status": "ok",
            "entities_added": entities_added,
            "entities_dup": entities_dup,
            "relations_added": relations_added,
            "relations_dup": relations_dup,
            "errors": errors,
        }

    def _extract_from_text(self, text: str, layer: str, source_id: str) -> dict:
        """从文本提取实体（简单规则）"""
        entities_added = 0
        entities_dup = 0
        relations_added = 0
        relations_dup = 0

        # 1. 提取层名实体（L1-L6）
        layer_pattern = re.compile(r'L([1-6])')
        for m in layer_pattern.finditer(text):
            layer_name = f"L{m.group(1)}"
            res = self.add_entity(layer_name, "layer", layer, source_id,
                                  description=f"Elite记忆架构第{m.group(1)}层",
                                  source=f"auto:{layer}")
            if res["status"] == "ok":
                entities_added += 1
            else:
                entities_dup += 1

        # 2. 提取路径实体
        path_pattern = re.compile(r'[A-Z]:[/\\][\w./\\-]+|~?/[\w./\\-]+')
        for m in path_pattern.finditer(text):
            path_val = m.group()
            if len(path_val) > 5:
                res = self.add_entity(path_val, "file", layer, source_id,
                                      source=f"auto:{layer}")
                if res["status"] == "ok":
                    entities_added += 1
                else:
                    entities_dup += 1

        # 3. 提取技术名词（驼峰/连字符组合）
        tech_pattern = re.compile(r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b|\b[a-z]+(?:-[a-z]+)+\b')
        for m in tech_pattern.finditer(text):
            term = m.group()
            if len(term) > 3 and term.lower() not in STOP_WORDS:
                res = self.add_entity(term, "technology", layer, source_id,
                                      source=f"auto:{layer}")
                if res["status"] == "ok":
                    entities_added += 1
                else:
                    entities_dup += 1

        # 4. 提取中文概念（2-6字，含特定关键词）
        concept_keywords = ["架构", "记忆", "存储", "压缩", "向量", "同步", "映射",
                           "归档", "恢复", "晋升", "实体", "关系", "图谱", "索引",
                           "飞书", "搜索", "文件", "配置", "注册", "冷存", "热存"]
        for kw in concept_keywords:
            if kw in text:
                res = self.add_entity(kw, "concept", layer, source_id,
                                      source=f"auto:{layer}")
                if res["status"] == "ok":
                    entities_added += 1
                else:
                    entities_dup += 1

        return {
            "entities_added": entities_added,
            "entities_dup": entities_dup,
            "relations_added": relations_added,
            "relations_dup": relations_dup,
        }

    @staticmethod
    def _guess_entity_type(name: str) -> str:
        """根据实体名猜测类型"""
        if re.match(r'^L[1-6]$', name):
            return "layer"
        if re.match(r'^[A-Z]:[/\\]', name) or name.startswith('/'):
            return "file"
        if re.match(r'^[A-Z][a-z]+[A-Z]', name):
            return "technology"
        if name.endswith('.py') or name.endswith('.json') or name.endswith('.db'):
            return "file"
        return "concept"

    def _build_layer_relations(self) -> dict:
        """自动构建层间关系"""
        added = 0
        dup = 0

        # 层间晋升/老化/恢复关系
        layer_connections = [
            ("L1", "晋升", "L2"),
            ("L2", "归档", "L3"),
            ("L3", "恢复", "L2"),
            ("L4", "晋升", "L2"),
            ("L4", "归档", "L3"),
            ("L5", "映射", "L2"),
            ("L6", "关联", "L5"),
            ("L2", "同步", "飞书"),
            ("L4", "同步", "飞书"),
            ("L5", "同步", "飞书"),
            ("L6", "同步", "飞书"),
        ]

        # 确保层实体存在
        for layer_name in ["L1", "L2", "L3", "L4", "L5", "L6", "飞书"]:
            existing = self.conn.execute(
                "SELECT id FROM entities WHERE name = ? AND status = 'active'",
                (layer_name,),
            ).fetchone()
            if not existing:
                etype = "layer" if layer_name.startswith("L") else "tool"
                self.add_entity(layer_name, etype, source="auto:system")

        # 获取所有层实体 ID
        layer_ids = {}
        for r in self.conn.execute(
            "SELECT id, name FROM entities WHERE name IN ('L1','L2','L3','L4','L5','L6','飞书') AND status = 'active'"
        ).fetchall():
            layer_ids[r["name"]] = r["id"]

        for sub_name, pred, obj_name in layer_connections:
            sub_id = layer_ids.get(sub_name)
            obj_id = layer_ids.get(obj_name)
            if sub_id and obj_id:
                res = self.add_relation(sub_id, pred, obj_id,
                                       confidence=0.9, layer_source="system",
                                       source="auto:system")
                if res["status"] == "ok":
                    added += 1
                else:
                    dup += 1

        return {"added": added, "dup": dup}

    # ===================== L6 <-> 飞书映射 =====================

    def _make_entity_feishu_text(self, row: dict) -> str:
        """实体 -> 飞书记忆文本"""
        attrs = json.loads(row.get("attributes", "{}"))
        parts = [
            f"[实体] {row['name']}",
            f"[L6-图谱]",
            f"类型: {row['type']}",
            f"来源层: {row['layer_source']}",
            f"来源ID: {row['source_id']}",
            f"描述: {row['description']}",
        ]
        if attrs:
            parts.append(f"属性: {json.dumps(attrs, ensure_ascii=False)}")
        if row.get("feishu_id"):
            parts.append(f"飞书ID: {row['feishu_id']}")
        return "\n".join(parts)

    def _make_relation_feishu_text(self, row: dict) -> str:
        """关系 -> 飞书记忆文本"""
        sub = self.conn.execute("SELECT name FROM entities WHERE id = ?", (row["subject_id"],)).fetchone()
        obj = self.conn.execute("SELECT name FROM entities WHERE id = ?", (row["object_id"],)).fetchone()
        sub_name = sub["name"] if sub else row["subject_id"]
        obj_name = obj["name"] if obj else row["object_id"]

        parts = [
            f"[关系] {sub_name} --{row['predicate']}--> {obj_name}",
            f"[L6-图谱]",
            f"主语: {sub_name} ({row['subject_id']})",
            f"谓词: {row['predicate']}",
            f"宾语: {obj_name} ({row['object_id']})",
            f"置信度: {row['confidence']:.1%}",
            f"证据: {row['evidence']}",
            f"来源层: {row['layer_source']}",
        ]
        return "\n".join(parts)

    @staticmethod
    def _parse_entity_feishu_text(text: str) -> dict:
        """飞书文本 -> 实体字段"""
        lines = text.strip().split("\n")
        result = {
            "name": "", "type": "concept", "layer_source": "",
            "source_id": "", "description": "", "attributes": {},
        }

        # 第一行提取实体名
        if lines and lines[0].startswith("[实体]"):
            result["name"] = lines[0].replace("[实体]", "").strip()

        for line in lines:
            if line.startswith("类型:"):
                result["type"] = line.split(":", 1)[1].strip()
            elif line.startswith("来源层:"):
                result["layer_source"] = line.split(":", 1)[1].strip()
            elif line.startswith("来源ID:"):
                result["source_id"] = line.split(":", 1)[1].strip()
            elif line.startswith("描述:"):
                result["description"] = line.split(":", 1)[1].strip()
            elif line.startswith("属性:"):
                try:
                    result["attributes"] = json.loads(line.split(":", 1)[1].strip())
                except (json.JSONDecodeError, ValueError):
                    pass
        return result

    @staticmethod
    def _parse_relation_feishu_text(text: str) -> dict:
        """飞书文本 -> 关系字段"""
        lines = text.strip().split("\n")
        result = {
            "subject_id": "", "predicate": "", "object_id": "",
            "confidence": 1.0, "evidence": "", "layer_source": "",
        }

        for line in lines:
            if line.startswith("主语:"):
                val = line.split(":", 1)[1].strip()
                # 提取 ID（括号内）
                m = re.search(r'\(([^)]+)\)', val)
                if m:
                    result["subject_id"] = m.group(1)
            elif line.startswith("谓词:"):
                result["predicate"] = line.split(":", 1)[1].strip()
            elif line.startswith("宾语:"):
                val = line.split(":", 1)[1].strip()
                m = re.search(r'\(([^)]+)\)', val)
                if m:
                    result["object_id"] = m.group(1)
            elif line.startswith("置信度:"):
                try:
                    val = line.split(":", 1)[1].strip().rstrip("%")
                    result["confidence"] = float(val) / 100
                except ValueError:
                    pass
            elif line.startswith("证据:"):
                result["evidence"] = line.split(":", 1)[1].strip()
            elif line.startswith("来源层:"):
                result["layer_source"] = line.split(":", 1)[1].strip()
        return result

    def push_to_feishu(self, push_all: bool = False) -> dict:
        """L6 -> 飞书：准备推送数据（由 AI agent 调用 MCP 工具实际写入）

        返回:
          entities: 待推送实体列表
          relations: 待推送关系列表
        """
        synced_e_hashes = set(
            self._meta.get("feishu_sync", {}).get("synced_entity_hashes", [])
        )
        synced_r_hashes = set(
            self._meta.get("feishu_sync", {}).get("synced_relation_hashes", [])
        )

        # 实体
        if push_all:
            e_rows = self.conn.execute(
                "SELECT * FROM entities WHERE status = 'active'"
            ).fetchall()
        else:
            e_rows = self.conn.execute(
                "SELECT * FROM entities WHERE status = 'active' AND feishu_id = ''"
            ).fetchall()

        entity_results = []
        for row in e_rows:
            rd = dict(row)
            ch = rd["content_hash"]
            if not push_all and ch in synced_e_hashes:
                continue
            text = self._make_entity_feishu_text(rd)
            entity_results.append({
                "text": text,
                "layer": "L6-图谱",
                "source": rd.get("source", "manual"),
                "timestamp": rd.get("created_at", time.time()),
                "lancedb_id": rd["id"],
                "sync_status": "已同步",
                "content_hash": ch,
                "record_id": rd["id"],
                "item_type": "entity",
            })

        # 关系
        if push_all:
            r_rows = self.conn.execute(
                "SELECT * FROM relations WHERE status = 'active'"
            ).fetchall()
        else:
            r_rows = self.conn.execute(
                "SELECT * FROM relations WHERE status = 'active' AND feishu_id = ''"
            ).fetchall()

        relation_results = []
        for row in r_rows:
            rd = dict(row)
            ch = rd["content_hash"]
            if not push_all and ch in synced_r_hashes:
                continue
            text = self._make_relation_feishu_text(rd)
            relation_results.append({
                "text": text,
                "layer": "L6-图谱",
                "source": rd.get("source", "manual"),
                "timestamp": rd.get("created_at", time.time()),
                "lancedb_id": rd["id"],
                "sync_status": "已同步",
                "content_hash": ch,
                "record_id": rd["id"],
                "item_type": "relation",
            })

        # 更新同步元信息
        all_e_hashes = list(synced_e_hashes | {r["content_hash"] for r in entity_results})
        all_r_hashes = list(synced_r_hashes | {r["content_hash"] for r in relation_results})
        if "feishu_sync" not in self._meta:
            self._meta["feishu_sync"] = {}
        self._meta["feishu_sync"]["synced_entity_hashes"] = all_e_hashes
        self._meta["feishu_sync"]["synced_relation_hashes"] = all_r_hashes
        self._meta["feishu_sync"]["last_push_ts"] = time.time()
        self._save_meta()

        return {"entities": entity_results, "relations": relation_results}

    def pull_from_feishu(self, feishu_records: list) -> dict:
        """飞书 -> L6：从飞书拉取 L6-图谱 记录"""
        results = {"entities": [], "relations": []}
        synced_ids = set(
            self._meta.get("feishu_sync", {}).get("synced_feishu_ids", [])
        )

        for rec in feishu_records:
            layer = rec.get("layer", "")
            if layer not in ("L6-图谱", "L6"):
                continue

            feishu_id = rec.get("feishu_id", "")
            if feishu_id and feishu_id in synced_ids:
                continue

            text = rec.get("text", "")
            if not text:
                continue

            # 判断是实体还是关系
            if text.startswith("[实体]"):
                parsed = self._parse_entity_feishu_text(text)
                content_hash = self._content_hash(f"{parsed['name']}:{parsed['type']}:{parsed['layer_source']}")

                existing = self.conn.execute(
                    "SELECT id FROM entities WHERE content_hash = ?", (content_hash,)
                ).fetchone()
                if existing:
                    self.conn.execute(
                        "UPDATE entities SET feishu_id = ? WHERE id = ?",
                        (feishu_id, existing["id"]),
                    )
                    results["entities"].append({"status": "exists", "id": existing["id"], "feishu_id": feishu_id})
                else:
                    entity_id = f"E6-{int(time.time())}-{content_hash}"
                    now = time.time()
                    self.conn.execute(
                        """INSERT INTO entities
                        (id, name, type, layer_source, source_id, description, attributes,
                         content_hash, feishu_id, created_at, updated_at, last_accessed, status, source)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (entity_id, parsed["name"], parsed["type"], parsed["layer_source"],
                         parsed["source_id"], parsed["description"],
                         json.dumps(parsed["attributes"], ensure_ascii=False),
                         content_hash, feishu_id, now, now, now, "active", "feishu_pull"),
                    )
                    results["entities"].append({"status": "pulled", "id": entity_id, "feishu_id": feishu_id})

            elif text.startswith("[关系]"):
                parsed = self._parse_relation_feishu_text(text)
                if not parsed["subject_id"] or not parsed["object_id"]:
                    continue
                rel_hash = self._relation_hash(parsed["subject_id"], parsed["predicate"], parsed["object_id"])

                existing = self.conn.execute(
                    "SELECT id FROM relations WHERE content_hash = ?", (rel_hash,)
                ).fetchone()
                if existing:
                    self.conn.execute(
                        "UPDATE relations SET feishu_id = ? WHERE id = ?",
                        (feishu_id, existing["id"]),
                    )
                    results["relations"].append({"status": "exists", "id": existing["id"], "feishu_id": feishu_id})
                else:
                    rel_id = f"R6-{int(time.time())}-{rel_hash}"
                    now = time.time()
                    self.conn.execute(
                        """INSERT INTO relations
                        (id, subject_id, predicate, object_id, confidence, evidence,
                         layer_source, content_hash, feishu_id, created_at, updated_at, status, source)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (rel_id, parsed["subject_id"], parsed["predicate"], parsed["object_id"],
                         parsed["confidence"], parsed["evidence"], parsed["layer_source"],
                         rel_hash, feishu_id, now, now, "active", "feishu_pull"),
                    )
                    results["relations"].append({"status": "pulled", "id": rel_id, "feishu_id": feishu_id})

        self.conn.commit()

        # 更新同步元信息
        new_synced = list(synced_ids | {r.get("feishu_id", "") for r in results["entities"] + results["relations"]})
        self._meta["feishu_sync"]["synced_feishu_ids"] = new_synced
        self._meta["feishu_sync"]["last_pull_ts"] = time.time()
        self._save_meta()

        return results

    def update_feishu_id(self, record_id: str, feishu_id: str):
        """回写飞书 ID 到本地记录"""
        # 先查实体
        existing = self.conn.execute("SELECT id FROM entities WHERE id = ?", (record_id,)).fetchone()
        if existing:
            self.conn.execute("UPDATE entities SET feishu_id = ? WHERE id = ?", (feishu_id, record_id))
            self.conn.commit()
            return
        # 再查关系
        existing = self.conn.execute("SELECT id FROM relations WHERE id = ?", (record_id,)).fetchone()
        if existing:
            self.conn.execute("UPDATE relations SET feishu_id = ? WHERE id = ?", (feishu_id, record_id))
            self.conn.commit()
            return

    def get_sync_status(self) -> dict:
        """飞书同步状态"""
        total_entities = self.conn.execute("SELECT COUNT(*) FROM entities WHERE status = 'active'").fetchone()[0]
        total_relations = self.conn.execute("SELECT COUNT(*) FROM relations WHERE status = 'active'").fetchone()[0]
        synced_e = self.conn.execute("SELECT COUNT(*) FROM entities WHERE feishu_id != '' AND status = 'active'").fetchone()[0]
        synced_r = self.conn.execute("SELECT COUNT(*) FROM relations WHERE feishu_id != '' AND status = 'active'").fetchone()[0]

        return {
            "total_entities": total_entities,
            "total_relations": total_relations,
            "synced_entities": synced_e,
            "synced_relations": synced_r,
            "unsynced_entities": total_entities - synced_e,
            "unsynced_relations": total_relations - synced_r,
            "last_push": self._meta.get("feishu_sync", {}).get("last_push_ts", 0),
            "last_pull": self._meta.get("feishu_sync", {}).get("last_pull_ts", 0),
        }

    # ===================== 快照 =====================

    def snapshot(self) -> dict:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        sp = os.path.join(SNAPSHOT_DIR, f"kg_{ts}.db")
        self.conn.commit()
        import shutil
        shutil.copy2(KG_DB, sp)
        self._log("snapshot", sp, "Knowledge graph snapshot created")
        return {"status": "ok", "path": sp}

    # ===================== 状态 =====================

    def status(self) -> dict:
        total_e = self.conn.execute("SELECT COUNT(*) FROM entities WHERE status = 'active'").fetchone()[0]
        total_r = self.conn.execute("SELECT COUNT(*) FROM relations WHERE status = 'active'").fetchone()[0]
        merged_e = self.conn.execute("SELECT COUNT(*) FROM entities WHERE status = 'merged'").fetchone()[0]

        # 类型分布
        type_dist = {}
        for r in self.conn.execute("SELECT type, COUNT(*) as cnt FROM entities WHERE status = 'active' GROUP BY type").fetchall():
            type_dist[r["type"]] = r["cnt"]

        # 谓词分布
        pred_dist = {}
        for r in self.conn.execute("SELECT predicate, COUNT(*) as cnt FROM relations WHERE status = 'active' GROUP BY predicate").fetchall():
            pred_dist[r["predicate"]] = r["cnt"]

        # 来源层分布
        layer_dist = {}
        for r in self.conn.execute("SELECT layer_source, COUNT(*) as cnt FROM entities WHERE status = 'active' GROUP BY layer_source").fetchall():
            layer_dist[r["layer_source"] or "none"] = r["cnt"]

        # 度分布（连接数）
        avg_degree = 0
        if total_e > 0:
            total_degree = self.conn.execute(
                """SELECT COUNT(*) FROM (
                    SELECT subject_id as eid FROM relations WHERE status = 'active'
                    UNION ALL
                    SELECT object_id as eid FROM relations WHERE status = 'active'
                )"""
            ).fetchone()[0]
            avg_degree = total_degree / total_e

        db_size = os.path.getsize(KG_DB) / 1024 if os.path.exists(KG_DB) else 0

        return {
            "total_entities": total_e,
            "total_relations": total_r,
            "merged_entities": merged_e,
            "type_distribution": type_dist,
            "predicate_distribution": pred_dist,
            "layer_distribution": layer_dist,
            "avg_degree": round(avg_degree, 2),
            "db_size_kb": round(db_size, 1),
        }

    # ===================== 日志 =====================

    def get_log(self, limit: int = 20) -> list:
        rows = self.conn.execute(
            "SELECT * FROM kg_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self):
        self.conn.close()


# ===================== CLI =====================

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]
    kg = KnowledgeGraph()

    try:
        if cmd == "add-entity":
            name = sys.argv[2]
            etype = "concept"
            layer = ""
            source_id = ""
            desc = ""
            i = 3
            while i < len(sys.argv):
                if sys.argv[i] == "--type" and i + 1 < len(sys.argv):
                    etype = sys.argv[i + 1]; i += 2
                elif sys.argv[i] == "--layer" and i + 1 < len(sys.argv):
                    layer = sys.argv[i + 1]; i += 2
                elif sys.argv[i] == "--source-id" and i + 1 < len(sys.argv):
                    source_id = sys.argv[i + 1]; i += 2
                elif sys.argv[i] == "--desc" and i + 1 < len(sys.argv):
                    desc = sys.argv[i + 1]; i += 2
                else:
                    i += 1
            result = kg.add_entity(name, etype, layer, source_id, desc, source="manual")
            print(json.dumps(result, ensure_ascii=False))

        elif cmd == "add-relation":
            subject_id = sys.argv[2]
            predicate = sys.argv[3]
            object_id = sys.argv[4]
            confidence = 1.0
            evidence = ""
            layer_source = ""
            i = 5
            while i < len(sys.argv):
                if sys.argv[i] == "--confidence" and i + 1 < len(sys.argv):
                    confidence = float(sys.argv[i + 1]); i += 2
                elif sys.argv[i] == "--evidence" and i + 1 < len(sys.argv):
                    evidence = sys.argv[i + 1]; i += 2
                elif sys.argv[i] == "--layer" and i + 1 < len(sys.argv):
                    layer_source = sys.argv[i + 1]; i += 2
                else:
                    i += 1
            result = kg.add_relation(subject_id, predicate, object_id,
                                    confidence, evidence, layer_source, source="manual")
            print(json.dumps(result, ensure_ascii=False))

        elif cmd == "auto-extract":
            min_len = 50
            if "--min-length" in sys.argv:
                idx = sys.argv.index("--min-length")
                if idx + 1 < len(sys.argv):
                    min_len = int(sys.argv[idx + 1])
            result = kg.auto_extract(min_length=min_len)
            print(json.dumps(result, ensure_ascii=False, indent=2))

        elif cmd == "search":
            query = sys.argv[2]
            limit = 10
            if "--limit" in sys.argv:
                idx = sys.argv.index("--limit")
                if idx + 1 < len(sys.argv):
                    limit = int(sys.argv[idx + 1])
            results = kg.search(query, limit)
            for r in results:
                match = r.get("match_type", "?")
                if match == "entity":
                    print(f"  [E] {r['id']}: {r['name']} ({r['type']})")
                elif match == "relation":
                    print(f"  [R] {r['id']}: {r['subject_id']} -{r['predicate']}-> {r['object_id']}")

        elif cmd == "traverse":
            entity_id = sys.argv[2]
            depth = 2
            direction = "both"
            if "--depth" in sys.argv:
                idx = sys.argv.index("--depth")
                if idx + 1 < len(sys.argv):
                    depth = int(sys.argv[idx + 1])
            if "--direction" in sys.argv:
                idx = sys.argv.index("--direction")
                if idx + 1 < len(sys.argv):
                    direction = sys.argv[idx + 1]
            result = kg.traverse(entity_id, depth, direction)
            print(json.dumps(result, ensure_ascii=False, indent=2, default=str))

        elif cmd == "path":
            from_id = sys.argv[2]
            to_id = sys.argv[3]
            max_depth = 4
            if "--max-depth" in sys.argv:
                idx = sys.argv.index("--max-depth")
                if idx + 1 < len(sys.argv):
                    max_depth = int(sys.argv[idx + 1])
            result = kg.path(from_id, to_id, max_depth)
            print(json.dumps(result, ensure_ascii=False, indent=2, default=str))

        elif cmd == "neighbors":
            entity_id = sys.argv[2]
            result = kg.neighbors(entity_id)
            print(json.dumps(result, ensure_ascii=False, indent=2, default=str))

        elif cmd == "list-entities":
            etype = ""
            layer = ""
            limit = 20
            if "--type" in sys.argv:
                idx = sys.argv.index("--type")
                if idx + 1 < len(sys.argv):
                    etype = sys.argv[idx + 1]
            if "--layer" in sys.argv:
                idx = sys.argv.index("--layer")
                if idx + 1 < len(sys.argv):
                    layer = sys.argv[idx + 1]
            if "--limit" in sys.argv:
                idx = sys.argv.index("--limit")
                if idx + 1 < len(sys.argv):
                    limit = int(sys.argv[idx + 1])
            results = kg.list_entities(etype, layer, limit)
            for r in results:
                print(f"  {r['id']}: {r['name']} ({r['type']}) layer={r['layer_source']}")

        elif cmd == "list-relations":
            predicate = ""
            limit = 20
            if "--predicate" in sys.argv:
                idx = sys.argv.index("--predicate")
                if idx + 1 < len(sys.argv):
                    predicate = sys.argv[idx + 1]
            if "--limit" in sys.argv:
                idx = sys.argv.index("--limit")
                if idx + 1 < len(sys.argv):
                    limit = int(sys.argv[idx + 1])
            results = kg.list_relations(predicate, limit)
            for r in results:
                print(f"  {r['id']}: {r['subject_id']} -{r['predicate']}-> {r['object_id']}")

        elif cmd == "info":
            item_id = sys.argv[2]
            result = kg.info(item_id)
            print(json.dumps(result, ensure_ascii=False, indent=2, default=str))

        elif cmd == "merge":
            primary_id = sys.argv[2]
            secondary_id = sys.argv[3]
            result = kg.merge(primary_id, secondary_id)
            print(json.dumps(result, ensure_ascii=False))

        elif cmd == "push":
            push_all = "--all" in sys.argv
            result = kg.push_to_feishu(push_all)
            print(json.dumps(result, ensure_ascii=False, indent=2, default=str))

        elif cmd == "pull":
            print("Pull requires Feishu MCP query results as input")
            print("Use: kg.pull_from_feishu(feishu_records=[...]) via Python API")

        elif cmd == "sync-status":
            result = kg.get_sync_status()
            print(json.dumps(result, ensure_ascii=False, indent=2))

        elif cmd == "snapshot":
            result = kg.snapshot()
            print(json.dumps(result, ensure_ascii=False))

        elif cmd == "status":
            result = kg.status()
            print(json.dumps(result, ensure_ascii=False, indent=2))

        elif cmd == "log":
            limit = 20
            if "--limit" in sys.argv:
                idx = sys.argv.index("--limit")
                if idx + 1 < len(sys.argv):
                    limit = int(sys.argv[idx + 1])
            results = kg.get_log(limit)
            for r in results:
                ts = datetime.fromtimestamp(r["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
                print(f"  {ts} | {r['action']} | {r['target']} | {r['detail']}")

        else:
            print(f"Unknown command: {cmd}")
            print(__doc__)

    finally:
        kg.close()


if __name__ == "__main__":
    main()
