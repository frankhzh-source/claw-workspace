"""
Elite L3 Cold Store — 冷存储归档层
写一次、读偶尔。永久保存，版本可追溯。类似 Git Notes 的冷数据保险箱。

架构：
  SQLite 时间分片归档（替代 Git Notes，Windows 友好）
  ├── coldstore.db       — 主归档库（条目+版本+全文索引）
  ├── coldstore.json     — 元信息（归档策略、统计、上次同步）
  └── snapshots/         — 时间快照目录（每日/每周自动快照）

与 Elite 架构的关系：
  L1(寄存器) → L2(向量库) → L3(冷存储) → L4(文件记忆)
                         ↓
                    老化策略：L2 中超过 N 天未访问的条目自动归档到 L3
                    恢复策略：L3 中被搜索命中的条目可恢复到 L2
                    飞书同步：归档时标记同步状态

核心能力：
  - archive:  L2 条目 → L3 归档（手动/自动老化）
  - restore:  L3 条目 → L2 恢复
  - search:   全文搜索（SQLite FTS5 或 LIKE）
  - log:      版本日志（每次归档/恢复都记录）
  - aging:    自动老化策略（N 天未访问 → 归档）
  - snapshot: 时间快照（JSON 导出）

CLI:
  python elite_coldstore.py archive [--days 30] [--auto]
  python elite_coldstore.py restore <archive_id>
  python elite_coldstore.py search <query> [--limit 10]
  python elite_coldstore.py log [--limit 20]
  python elite_coldstore.py aging [--dry-run] [--days 30]
  python elite_coldstore.py snapshot
  python elite_coldstore.py status
  python elite_coldstore.py list [--layer L1|L2|L4] [--limit 20]
"""
import json
import time
import hashlib
import sqlite3
import sys
import os
from pathlib import Path
from datetime import datetime

# ===================== 配置 =====================
COLD_DIR = str(Path.home() / ".openclaw" / "memory" / "coldstore")
COLD_DB = str(Path(COLD_DIR) / "coldstore.db")
COLD_META = str(Path(COLD_DIR) / "coldstore.json")
SNAPSHOT_DIR = str(Path(COLD_DIR) / "snapshots")

# 老化策略：默认 30 天未访问自动归档
DEFAULT_AGING_DAYS = 30


# ===================== 数据库初始化 =====================
def _init_db(conn: sqlite3.Connection):
    """创建表结构（幂等）"""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS archive (
            id TEXT PRIMARY KEY,
            text TEXT NOT NULL,
            layer TEXT NOT NULL DEFAULT 'L2',
            source TEXT DEFAULT '',
            lancedb_hash TEXT DEFAULT '',
            feishu_id TEXT DEFAULT '',
            archived_at REAL NOT NULL,
            original_ts REAL DEFAULT 0,
            access_count INTEGER DEFAULT 0,
            restored INTEGER DEFAULT 0,
            tags TEXT DEFAULT '[]',
            content_hash TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS version_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            archive_id TEXT NOT NULL,
            action TEXT NOT NULL,
            timestamp REAL NOT NULL,
            detail TEXT DEFAULT '',
            FOREIGN KEY (archive_id) REFERENCES archive(id)
        );

        CREATE INDEX IF NOT EXISTS idx_archive_layer ON archive(layer);
        CREATE INDEX IF NOT EXISTS idx_archive_archived_at ON archive(archived_at);
        CREATE INDEX IF NOT EXISTS idx_archive_content_hash ON archive(content_hash);
        CREATE INDEX IF NOT EXISTS idx_version_log_ts ON version_log(timestamp);
    """)
    # 尝试创建 FTS5 虚拟表（unicode61 支持中文按字符分词）
    try:
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS archive_fts
            USING fts5(text, content='archive', content_rowid=rowid,
                       tokenize='unicode61 tokenchars _')
        """)
        # 触发器：INSERT 时自动同步到 FTS
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS archive_fts_insert AFTER INSERT ON archive BEGIN
                INSERT INTO archive_fts(rowid, text) VALUES (new.rowid, new.text);
            END
        """)
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS archive_fts_delete AFTER DELETE ON archive BEGIN
                INSERT INTO archive_fts(archive_fts, rowid, text) VALUES('delete', old.rowid, old.text);
            END
        """)
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS archive_fts_update AFTER UPDATE ON archive BEGIN
                INSERT INTO archive_fts(archive_fts, rowid, text) VALUES('delete', old.rowid, old.text);
                INSERT INTO archive_fts(rowid, text) VALUES (new.rowid, new.text);
            END
        """)
    except sqlite3.OperationalError:
        pass  # FTS5 不可用，降级到 LIKE 搜索
    conn.commit()


# ===================== 核心引擎 =====================
class ColdStore:
    """L3 冷存储引擎 — SQLite + 版本日志 + 老化策略"""

    def __init__(self):
        Path(COLD_DIR).mkdir(parents=True, exist_ok=True)
        Path(SNAPSHOT_DIR).mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(COLD_DB)
        self.conn.row_factory = sqlite3.Row
        _init_db(self.conn)
        self._meta = self._load_meta()

    # ---------- 元信息管理 ----------
    def _load_meta(self) -> dict:
        path = Path(COLD_META)
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return {
            "created_at": time.time(),
            "last_aging_ts": 0,
            "last_snapshot_ts": 0,
            "aging_days": DEFAULT_AGING_DAYS,
            "total_archived": 0,
            "total_restored": 0,
        }

    def _save_meta(self):
        Path(COLD_META).write_text(
            json.dumps(self._meta, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    # ---------- 归档操作 ----------
    def archive(self, text: str, layer: str = "L2", source: str = "",
                lancedb_hash: str = "", feishu_id: str = "",
                original_ts: float = 0, tags: list = None) -> str:
        """归档一条记忆到 L3"""
        content_hash = hashlib.md5(text.encode()).hexdigest()[:12]
        archive_id = f"C3-{int(time.time())}-{content_hash}"

        # 去重：同 content_hash 不重复归档
        existing = self.conn.execute(
            "SELECT id FROM archive WHERE content_hash = ?", (content_hash,)
        ).fetchone()
        if existing:
            return existing["id"]

        self.conn.execute("""
            INSERT INTO archive (id, text, layer, source, lancedb_hash, feishu_id,
                                 archived_at, original_ts, access_count, tags, content_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
        """, (archive_id, text, layer, source, lancedb_hash, feishu_id,
              time.time(), original_ts, json.dumps(tags or [], ensure_ascii=False), content_hash))

        # 版本日志
        self._log(archive_id, "archive", f"[{layer}] {text[:50]}")

        self.conn.commit()
        self._meta["total_archived"] += 1
        self._save_meta()
        return archive_id

    def archive_from_l2(self, l2_record: dict) -> str:
        """从 L2 LanceDB 条目归档到 L3"""
        return self.archive(
            text=l2_record.get("text", ""),
            layer=l2_record.get("layer", "L2"),
            source=l2_record.get("source", "l2_aging"),
            lancedb_hash=l2_record.get("content_hash", ""),
            feishu_id=l2_record.get("feishu_id", ""),
            original_ts=l2_record.get("timestamp", 0),
        )

    # ---------- 恢复操作 ----------
    def restore(self, archive_id: str) -> dict:
        """从 L3 恢复条目到 L2 LanceDB"""
        row = self.conn.execute(
            "SELECT * FROM archive WHERE id = ?", (archive_id,)
        ).fetchone()
        if row is None:
            return {"status": "error", "message": f"归档条目不存在: {archive_id}"}

        # 写入 L2
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from elite_sync import LanceStore

            lance = LanceStore()
            content_hash = lance.add(
                text=row["text"],
                layer=row["layer"],
                source=f"l3_restore:{archive_id}",
                feishu_id=row["feishu_id"] or ""
            )
            result = {
                "status": "ok",
                "message": f"已恢复到 L2: {archive_id}",
                "l2_hash": content_hash,
                "archive_id": archive_id,
            }
        except Exception as e:
            result = {
                "status": "error",
                "message": f"L2 写入失败: {e}",
                "archive_id": archive_id,
            }

        # 标记为已恢复（不删除，保留历史）
        self.conn.execute(
            "UPDATE archive SET restored = 1 WHERE id = ?", (archive_id,)
        )
        self._log(archive_id, "restore", result.get("message", ""))
        self.conn.commit()
        self._meta["total_restored"] += 1
        self._save_meta()
        return result

    # ---------- 搜索 ----------
    def search(self, query: str, limit: int = 10, layer: str = None) -> list:
        """全文搜索归档（FTS5 + LIKE 双通道，中文友好）"""
        results = []

        # 通道 1：FTS5（对中文按单字 OR 搜索）
        try:
            # 中文查询拆成单字 OR，英文保持原样
            fts_query = self._make_fts_query(query)
            sql = """
                SELECT a.*, fts.rank
                FROM archive_fts fts
                JOIN archive a ON a.rowid = fts.rowid
                WHERE archive_fts MATCH ?
            """
            params = [fts_query]
            if layer:
                sql += " AND a.layer = ?"
                params.append(layer)
            sql += " ORDER BY fts.rank LIMIT ?"
            params.append(limit)

            rows = self.conn.execute(sql, params).fetchall()
            fts_ids = {r["id"] for r in rows}
            results = [dict(r) for r in rows]
        except (sqlite3.OperationalError, sqlite3.DatabaseError):
            fts_ids = set()

        # 通道 2：LIKE 兜底（补充 FTS5 未命中的中文短语）
        sql = "SELECT * FROM archive WHERE text LIKE ?"
        params = [f"%{query}%"]
        if layer:
            sql += " AND layer = ?"
            params.append(layer)
        sql += " ORDER BY archived_at DESC LIMIT ?"
        params.append(limit)

        rows = self.conn.execute(sql, params).fetchall()
        for r in rows:
            if r["id"] not in fts_ids:
                results.append(dict(r))

            rows = self.conn.execute(sql, params).fetchall()
            results = [dict(r) for r in rows]

        return results

    @staticmethod
    def _make_fts_query(query: str) -> str:
        """将查询转为 FTS5 友好格式：中文拆单字 OR，英文保持"""
        import re
        # 如果包含中文字符，拆成单字 OR 搜索
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', query)
        if chinese_chars:
            # 用 OR 连接每个中文字
            return ' OR '.join(chinese_chars)
        # 英文/数字：直接用原查询
        return query

    # ---------- 列表 ----------
    def list_entries(self, layer: str = None, limit: int = 20, offset: int = 0,
                     restored: bool = None) -> list:
        """列出归档条目"""
        sql = "SELECT * FROM archive WHERE 1=1"
        params = []
        if layer:
            sql += " AND layer = ?"
            params.append(layer)
        if restored is not None:
            sql += " AND restored = ?"
            params.append(1 if restored else 0)
        sql += " ORDER BY archived_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = self.conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    # ---------- 老化策略 ----------
    def aging(self, days: int = None, dry_run: bool = False) -> list:
        """从 L2 自动老化归档：超过 N 天未访问的条目 → L3
        
        返回归档的条目列表
        """
        days = days or self._meta.get("aging_days", DEFAULT_AGING_DAYS)
        cutoff_ts = time.time() - days * 86400
        archived = []

        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from elite_sync import LanceStore

            lance = LanceStore()
            all_records = lance._query_all()

            for rec in all_records:
                # 跳过系统初始化记录
                if rec.get("text") == "__init__":
                    continue
                # 跳过已归档的（content_hash 去重）
                content_hash = rec.get("content_hash", "")
                if not content_hash:
                    continue

                # 检查是否已归档
                existing = self.conn.execute(
                    "SELECT id FROM archive WHERE content_hash = ?", (content_hash,)
                ).fetchone()
                if existing:
                    continue

                # 按时间判断
                ts = rec.get("timestamp", 0)
                if ts < cutoff_ts:
                    if dry_run:
                        archived.append({
                            "text": rec.get("text", "")[:50],
                            "layer": rec.get("layer", ""),
                            "age_days": (time.time() - ts) / 86400,
                            "action": "would_archive"
                        })
                    else:
                        aid = self.archive_from_l2(rec)
                        archived.append({
                            "archive_id": aid,
                            "text": rec.get("text", "")[:50],
                            "layer": rec.get("layer", ""),
                            "age_days": (time.time() - ts) / 86400,
                            "action": "archived"
                        })

        except Exception as e:
            archived.append({"error": str(e)})

        self._meta["last_aging_ts"] = time.time()
        self._save_meta()
        return archived

    # ---------- 版本日志 ----------
    def _log(self, archive_id: str, action: str, detail: str = ""):
        self.conn.execute("""
            INSERT INTO version_log (archive_id, action, timestamp, detail)
            VALUES (?, ?, ?, ?)
        """, (archive_id, action, time.time(), detail))

    def get_log(self, limit: int = 20) -> list:
        rows = self.conn.execute(
            "SELECT * FROM version_log ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    # ---------- 快照 ----------
    def snapshot(self, label: str = "") -> str:
        """导出完整快照到 JSON 文件"""
        entries = self.list_entries(limit=10000)
        log = self.get_log(limit=100)

        snap = {
            "timestamp": time.time(),
            "label": label or f"snapshot-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            "meta": self._meta,
            "entries_count": len(entries),
            "log_count": len(log),
            "entries": entries,
            "log": log,
        }

        filename = f"snap-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        filepath = Path(SNAPSHOT_DIR) / filename
        filepath.write_text(
            json.dumps(snap, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        self._meta["last_snapshot_ts"] = time.time()
        self._save_meta()
        return str(filepath)

    # ---------- 统计 ----------
    def status(self) -> dict:
        total = self.conn.execute("SELECT COUNT(*) as c FROM archive").fetchone()["c"]
        restored = self.conn.execute(
            "SELECT COUNT(*) as c FROM archive WHERE restored = 1"
        ).fetchone()["c"]
        active = total - restored

        # 按层级统计
        layer_stats = {}
        rows = self.conn.execute(
            "SELECT layer, COUNT(*) as c FROM archive GROUP BY layer"
        ).fetchall()
        for r in rows:
            layer_stats[r["layer"]] = r["c"]

        # 最早/最晚归档时间
        earliest = self.conn.execute(
            "SELECT MIN(archived_at) as t FROM archive"
        ).fetchone()["t"]
        latest = self.conn.execute(
            "SELECT MAX(archived_at) as t FROM archive"
        ).fetchone()["t"]

        # FTS5 可用性
        fts_available = False
        try:
            self.conn.execute("SELECT * FROM archive_fts LIMIT 1")
            fts_available = True
        except (sqlite3.OperationalError, sqlite3.DatabaseError):
            pass

        return {
            "total": total,
            "active": active,
            "restored": restored,
            "layers": layer_stats,
            "earliest": datetime.fromtimestamp(earliest).strftime("%Y-%m-%d %H:%M") if earliest else "N/A",
            "latest": datetime.fromtimestamp(latest).strftime("%Y-%m-%d %H:%M") if latest else "N/A",
            "fts5": fts_available,
            "aging_days": self._meta.get("aging_days", DEFAULT_AGING_DAYS),
            "last_aging": datetime.fromtimestamp(self._meta["last_aging_ts"]).strftime("%Y-%m-%d %H:%M")
                if self._meta.get("last_aging_ts") else "从未",
            "db_path": COLD_DB,
        }

    def close(self):
        self.conn.close()


# ===================== CLI =====================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cs = ColdStore()
    cmd = sys.argv[1]

    if cmd == "archive":
        # 从 L2 归档所有超龄条目
        days = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else DEFAULT_AGING_DAYS
        auto = "--auto" in sys.argv
        if auto or len(sys.argv) <= 2:
            results = cs.aging(days=days)
            if not results:
                print("[L3] 没有需要归档的条目")
            else:
                for r in results:
                    if "error" in r:
                        print(f"[L3] 错误: {r['error']}")
                    else:
                        status = r.get("action", "archived")
                        print(f"[L3] {status}: [{r.get('layer','')}] {r.get('text','')} (age: {r.get('age_days',0):.0f}天)")
        else:
            # 手动归档指定文本
            text = sys.argv[2]
            layer = sys.argv[3] if len(sys.argv) > 3 else "L4"
            aid = cs.archive(text, layer=layer)
            print(f"[L3] 已归档: {aid} | {text[:50]}")

    elif cmd == "restore":
        if len(sys.argv) < 3:
            print("Usage: elite_coldstore.py restore <archive_id>")
            sys.exit(1)
        result = cs.restore(sys.argv[2])
        if result["status"] == "ok":
            print(f"[L3→L2] 恢复成功: {result['archive_id']} → L2 hash={result['l2_hash']}")
        else:
            print(f"[L3→L2] 恢复失败: {result['message']}")

    elif cmd == "search":
        if len(sys.argv) < 3:
            print("Usage: elite_coldstore.py search <query> [--limit N]")
            sys.exit(1)
        query = sys.argv[2]
        limit = 10
        if "--limit" in sys.argv:
            limit = int(sys.argv[sys.argv.index("--limit") + 1])
        layer = None
        if "--layer" in sys.argv:
            layer = sys.argv[sys.argv.index("--layer") + 1]
        results = cs.search(query, limit, layer)
        if not results:
            print(f"[L3] 搜索 '{query}' 无结果")
        else:
            for i, r in enumerate(results):
                restored_tag = " [已恢复]" if r.get("restored") else ""
                print(f"  {i+1}. [{r.get('layer','')}] {r.get('text','')[:60]}{restored_tag}")

    elif cmd == "log":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        logs = cs.get_log(limit)
        for l in logs:
            ts = datetime.fromtimestamp(l["timestamp"]).strftime("%m-%d %H:%M")
            print(f"  {ts} | {l['action']:8s} | {l.get('detail','')[:50]}")

    elif cmd == "aging":
        days = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else DEFAULT_AGING_DAYS
        dry = "--dry-run" in sys.argv
        results = cs.aging(days=days, dry_run=dry)
        mode = "预览" if dry else "执行"
        print(f"[L3] 老化{mode} (>{days}天未访问):")
        if not results:
            print("  无超龄条目")
        else:
            for r in results:
                if "error" in r:
                    print(f"  错误: {r['error']}")
                else:
                    print(f"  [{r.get('layer','')}] {r.get('text','')} (age: {r.get('age_days',0):.0f}天)")

    elif cmd == "snapshot":
        label = sys.argv[2] if len(sys.argv) > 2 else ""
        path = cs.snapshot(label)
        print(f"[L3] 快照已保存: {path}")

    elif cmd == "status":
        s = cs.status()
        print(f"L3 冷存储状态")
        print(f"  总条目: {s['total']} | 活跃: {s['active']} | 已恢复: {s['restored']}")
        print(f"  FTS5: {'可用' if s['fts5'] else '不可用(降级LIKE)'}")
        print(f"  老化策略: >{s['aging_days']}天 | 上次老化: {s['last_aging']}")
        print(f"  时间范围: {s['earliest']} ~ {s['latest']}")
        if s['layers']:
            print(f"  层级分布:")
            for layer, count in s['layers'].items():
                print(f"    {layer}: {count} 条")
        print(f"  数据库: {s['db_path']}")

    elif cmd == "list":
        layer = None
        limit = 20
        if "--layer" in sys.argv:
            layer = sys.argv[sys.argv.index("--layer") + 1]
        if "--limit" in sys.argv:
            limit = int(sys.argv[sys.argv.index("--limit") + 1])
        entries = cs.list_entries(layer=layer, limit=limit)
        for e in entries:
            restored_tag = " [已恢复]" if e.get("restored") else ""
            ts = datetime.fromtimestamp(e["archived_at"]).strftime("%m-%d %H:%M")
            print(f"  {e['id']} | {ts} | [{e['layer']}] {e['text'][:50]}{restored_tag}")

    else:
        print(f"未知命令: {cmd}")
        print("可用: archive, restore, search, log, aging, snapshot, status, list")

    cs.close()
