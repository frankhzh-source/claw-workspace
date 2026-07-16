"""
Elite WAL Protocol — Write-Ahead Log 防丢上下文机制
Step 7 of Elite 6-Layer Memory Architecture

核心流程：
  收到消息 → 提取记忆 → 写L1落盘(WAL) → 处理业务 → 回复前确认持久化 → 长期同步L2/L4

架构：
  SQLite WAL日志
  ├── wal.db            — WAL记录（每条消息的上下文快照+状态机）
  ├── wal_checkpoints/  — 检查点快照目录（定期全量快照）
  └── wal_meta.json     — 元信息（统计、恢复次数、最近检查点）

WAL记录生命周期：
  PENDING   → 收到消息，已写入WAL，尚未处理
  PROCESSING → 正在处理业务逻辑
  CONFIRMED  → 业务处理完毕，已确认持久化到L1
  SYNCED     → 长期信息已同步到L2/L4
  EXPIRED    → 已过期清理（保留元数据供审计）

防丢机制：
  1. 每条消息先写WAL再处理（先写日志原则）
  2. 崩溃恢复：重启时扫描PENDING/PROCESSING记录，重放未完成操作
  3. 确认机制：回复前必须CONFIRM，否则下次恢复时重试
  4. 同步保障：CONFIRMED记录异步晋升到L2/L4，失败时重试
  5. 检查点：定期全量快照，加速恢复

与L1-L6的关系：
  WAL → L1:  上下文写入L1寄存器（TASK/CONTEXT/RECENT槽位）
  L1 → L2:  高价值记忆晋升到LanceDB
  L1 → L4:  文件操作记录写入FileStore
  WAL本身独立于L1-L6，是横切关注点（类似数据库的WAL日志）

CLI:
  python elite_wal.py begin <message> [--source user|system|agent]
  python elite_wal.py confirm <wal_id>
  python elite_wal.py sync <wal_id>
  python elite_wal.py status
  python elite_wal.py recover [--dry-run]
  python elite_wal.py checkpoint
  python elite_wal.py list [--status PENDING|PROCESSING|CONFIRMED|SYNCED] [--limit 20]
  python elite_wal.py info <wal_id>
  python elite_wal.py clean [--days 7] [--dry-run]
  python elite_wal.py stats
"""
import json
import time
import hashlib
import sqlite3
import sys
import os
import shutil
from pathlib import Path
from datetime import datetime
from enum import Enum

# ===================== 配置 =====================
WAL_DIR = str(Path.home() / ".openclaw" / "memory" / "wal")
WAL_DB = str(Path(WAL_DIR) / "wal.db")
WAL_META = str(Path(WAL_DIR) / "wal_meta.json")
CHECKPOINT_DIR = str(Path(WAL_DIR) / "wal_checkpoints")

# WAL记录状态
class WALStatus(str, Enum):
    PENDING = "PENDING"         # 已写入WAL，尚未处理
    PROCESSING = "PROCESSING"   # 正在处理
    CONFIRMED = "CONFIRMED"     # 已确认持久化
    SYNCED = "SYNCED"           # 已同步到L2/L4
    EXPIRED = "EXPIRED"         # 已过期

# 过期策略
DEFAULT_EXPIRE_DAYS = 7        # CONFIRMED/SYNCED记录7天后过期
DEFAULT_CLEAN_DAYS = 30        # EXPIRED记录30天后物理删除
MAX_RETRIES = 3                # 最大重试次数

# 检查点间隔
CHECKPOINT_INTERVAL = 100      # 每处理100条消息做一次检查点


# ===================== 数据库初始化 =====================
def _init_db(conn: sqlite3.Connection):
    """创建表结构（幂等）"""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS wal_records (
            id TEXT PRIMARY KEY,
            message TEXT NOT NULL,
            message_hash TEXT NOT NULL,
            source TEXT DEFAULT 'user',
            status TEXT NOT NULL DEFAULT 'PENDING',
            retry_count INTEGER DEFAULT 0,
            -- L1 上下文快照
            context_snapshot TEXT DEFAULT '{}',
            -- 提取的记忆片段（JSON数组）
            memory_fragments TEXT DEFAULT '[]',
            -- 持久化确认
            l1_confirmed INTEGER DEFAULT 0,
            l1_slot TEXT DEFAULT '',
            l1_key TEXT DEFAULT '',
            -- 同步状态
            l2_synced INTEGER DEFAULT 0,
            l2_hash TEXT DEFAULT '',
            l4_synced INTEGER DEFAULT 0,
            l4_hash TEXT DEFAULT '',
            -- 时间戳
            created_at REAL NOT NULL,
            processing_at REAL DEFAULT 0,
            confirmed_at REAL DEFAULT 0,
            synced_at REAL DEFAULT 0,
            expired_at REAL DEFAULT 0,
            -- 元数据
            session_id TEXT DEFAULT '',
            agent_id TEXT DEFAULT '',
            error_log TEXT DEFAULT ''
        );

        CREATE INDEX IF NOT EXISTS idx_wal_status ON wal_records(status);
        CREATE INDEX IF NOT EXISTS idx_wal_created ON wal_records(created_at);
        CREATE INDEX IF NOT EXISTS idx_wal_session ON wal_records(session_id);
        CREATE INDEX IF NOT EXISTS idx_wal_message_hash ON wal_records(message_hash);
        CREATE INDEX IF NOT EXISTS idx_wal_l1_confirmed ON wal_records(l1_confirmed);

        CREATE TABLE IF NOT EXISTS wal_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wal_id TEXT NOT NULL,
            action TEXT NOT NULL,
            detail TEXT DEFAULT '',
            timestamp REAL NOT NULL,
            FOREIGN KEY (wal_id) REFERENCES wal_records(id)
        );

        CREATE INDEX IF NOT EXISTS idx_wallog_ts ON wal_log(timestamp);
        CREATE INDEX IF NOT EXISTS idx_wallog_walid ON wal_log(wal_id);
    """)

    # FTS5 全文索引（消息内容）
    try:
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS wal_fts
            USING fts5(message, context_snapshot, content='wal_records', content_rowid=rowid,
                       tokenize='unicode61 tokenchars _')
        """)
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS wal_fts_insert AFTER INSERT ON wal_records BEGIN
                INSERT INTO wal_fts(rowid, message, context_snapshot)
                VALUES (new.rowid, new.message, new.context_snapshot);
            END
        """)
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS wal_fts_delete AFTER DELETE ON wal_records BEGIN
                INSERT INTO wal_fts(wal_fts, rowid, message, context_snapshot)
                VALUES('delete', old.rowid, old.message, old.context_snapshot);
            END
        """)
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS wal_fts_update AFTER UPDATE ON wal_records BEGIN
                INSERT INTO wal_fts(wal_fts, rowid, message, context_snapshot)
                VALUES('delete', old.rowid, old.message, old.context_snapshot);
                INSERT INTO wal_fts(rowid, message, context_snapshot)
                VALUES (new.rowid, new.message, new.context_snapshot);
            END
        """)
    except sqlite3.OperationalError:
        pass  # FTS5 不可用，降级
    conn.commit()

    # 安全添加飞书同步字段（幂等）
    try:
        conn.execute("ALTER TABLE wal_records ADD COLUMN feishu_id TEXT DEFAULT ''")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # 字段已存在


# ===================== 核心引擎 =====================
class WALProtocol:
    """WAL 协议引擎 — Write-Ahead Log 防丢上下文"""

    def __init__(self):
        Path(WAL_DIR).mkdir(parents=True, exist_ok=True)
        Path(CHECKPOINT_DIR).mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(WAL_DB)
        self.conn.row_factory = sqlite3.Row
        _init_db(self.conn)
        self._meta = self._load_meta()

    # ---------- 元信息 ----------
    def _load_meta(self) -> dict:
        path = Path(WAL_META)
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return {
            "created_at": time.time(),
            "total_records": 0,
            "total_recoveries": 0,
            "last_checkpoint_ts": 0,
            "last_checkpoint_id": "",
            "records_since_checkpoint": 0,
        }

    def _save_meta(self):
        Path(WAL_META).write_text(
            json.dumps(self._meta, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    # ---------- 日志 ----------
    def _log(self, wal_id: str, action: str, detail: str = ""):
        self.conn.execute("""
            INSERT INTO wal_log (wal_id, action, detail, timestamp)
            VALUES (?, ?, ?, ?)
        """, (wal_id, action, time.time(), detail))
        self.conn.commit()

    # ---------- 哈希 ----------
    @staticmethod
    def _message_hash(message: str) -> str:
        return hashlib.md5(message.encode("utf-8")).hexdigest()[:12]

    # ===================== 核心流程 =====================

    def begin(self, message: str, source: str = "user",
              session_id: str = "", agent_id: str = "",
              context_snapshot: dict = None) -> dict:
        """Step 1: 收到消息，写入WAL（先写日志原则）

        流程位置：收到消息 → begin() → 处理业务 → confirm() → sync()
        返回：WAL记录ID，后续操作使用此ID追踪
        """
        message_hash = self._message_hash(message)
        wal_id = f"WAL-{int(time.time())}-{message_hash}"

        snapshot_json = json.dumps(context_snapshot or {}, ensure_ascii=False)
        now = time.time()

        self.conn.execute("""
            INSERT INTO wal_records
            (id, message, message_hash, source, status, context_snapshot,
             created_at, session_id, agent_id)
            VALUES (?, ?, ?, ?, 'PENDING', ?, ?, ?, ?)
        """, (wal_id, message, message_hash, source, snapshot_json,
              now, session_id, agent_id))

        self.conn.commit()
        self._log(wal_id, "begin", f"source={source} hash={message_hash}")

        # 更新元信息
        self._meta["total_records"] += 1
        self._meta["records_since_checkpoint"] += 1
        self._save_meta()

        # 自动检查点
        if self._meta["records_since_checkpoint"] >= CHECKPOINT_INTERVAL:
            self.checkpoint()

        return {
            "wal_id": wal_id,
            "status": WALStatus.PENDING.value,
            "message_hash": message_hash,
        }

    def processing(self, wal_id: str, memory_fragments: list = None) -> dict:
        """Step 2: 标记为处理中，记录提取的记忆片段

        流程位置：begin() → processing() → 业务逻辑 → confirm()
        """
        row = self.conn.execute(
            "SELECT * FROM wal_records WHERE id = ?", (wal_id,)
        ).fetchone()
        if row is None:
            return {"status": "error", "message": f"WAL记录不存在: {wal_id}"}

        if row["status"] not in (WALStatus.PENDING.value, WALStatus.PROCESSING.value):
            return {"status": "error", "message": f"状态不可变更: {row['status']}"}

        fragments_json = json.dumps(memory_fragments or [], ensure_ascii=False)
        self.conn.execute("""
            UPDATE wal_records
            SET status = 'PROCESSING', processing_at = ?, memory_fragments = ?
            WHERE id = ?
        """, (time.time(), fragments_json, wal_id))
        self.conn.commit()
        self._log(wal_id, "processing", f"fragments={len(memory_fragments or [])}")

        return {"wal_id": wal_id, "status": WALStatus.PROCESSING.value}

    def confirm(self, wal_id: str,
                l1_slot: str = "", l1_key: str = "",
                memory_fragments: list = None) -> dict:
        """Step 3: 确认持久化到L1，业务处理完毕

        流程位置：processing() → 业务逻辑完成 → confirm()
        保证：调用此方法前，上下文已写入L1寄存器
        """
        row = self.conn.execute(
            "SELECT * FROM wal_records WHERE id = ?", (wal_id,)
        ).fetchone()
        if row is None:
            return {"status": "error", "message": f"WAL记录不存在: {wal_id}"}

        if row["status"] not in (WALStatus.PENDING.value, WALStatus.PROCESSING.value):
            return {"status": "error", "message": f"状态不可确认: {row['status']}"}

        # 更新记忆片段（如果传入了新的）
        fragments_json = row["memory_fragments"]
        if memory_fragments:
            fragments_json = json.dumps(memory_fragments, ensure_ascii=False)

        now = time.time()
        self.conn.execute("""
            UPDATE wal_records
            SET status = 'CONFIRMED', confirmed_at = ?,
                l1_confirmed = 1, l1_slot = ?, l1_key = ?,
                memory_fragments = ?, processing_at = COALESCE(processing_at, ?)
            WHERE id = ?
        """, (now, l1_slot, l1_key, fragments_json, now, wal_id))
        self.conn.commit()
        self._log(wal_id, "confirm", f"l1={l1_slot}/{l1_key}")

        return {
            "wal_id": wal_id,
            "status": WALStatus.CONFIRMED.value,
            "l1_slot": l1_slot,
            "l1_key": l1_key,
        }

    def sync(self, wal_id: str,
             l2_hash: str = "", l4_hash: str = "") -> dict:
        """Step 4: 标记长期同步完成

        流程位置：confirm() → L2/L4同步完成 → sync()
        """
        row = self.conn.execute(
            "SELECT * FROM wal_records WHERE id = ?", (wal_id,)
        ).fetchone()
        if row is None:
            return {"status": "error", "message": f"WAL记录不存在: {wal_id}"}

        if row["status"] != WALStatus.CONFIRMED.value:
            return {"status": "error", "message": f"尚未确认，无法同步: {row['status']}"}

        updates = ["status = 'SYNCED'", "synced_at = ?"]
        params = [time.time()]

        if l2_hash:
            updates.append("l2_synced = 1")
            updates.append("l2_hash = ?")
            params.append(l2_hash)
        if l4_hash:
            updates.append("l4_synced = 1")
            updates.append("l4_hash = ?")
            params.append(l4_hash)

        params.append(wal_id)
        self.conn.execute(
            f"UPDATE wal_records SET {', '.join(updates)} WHERE id = ?",
            params
        )
        self.conn.commit()
        self._log(wal_id, "sync", f"l2={'ok' if l2_hash else 'skip'} l4={'ok' if l4_hash else 'skip'}")

        return {
            "wal_id": wal_id,
            "status": WALStatus.SYNCED.value,
            "l2_hash": l2_hash,
            "l4_hash": l4_hash,
        }

    # ===================== 一条龙快捷方法 =====================

    def write_through(self, message: str, source: str = "user",
                      session_id: str = "", agent_id: str = "",
                      context_snapshot: dict = None,
                      l1_slot: str = "RECENT", l1_key: str = "",
                      memory_fragments: list = None) -> dict:
        """一条龙：begin → processing → confirm

        最常用的快捷方法：收到消息 → 提取记忆 → 写L1 → 确认持久化
        适合大多数场景：消息进来后立即落盘，不需要异步处理
        """
        # Step 1: begin
        result = self.begin(message, source, session_id, agent_id, context_snapshot)
        wal_id = result["wal_id"]

        # Step 2: processing
        self.processing(wal_id, memory_fragments)

        # Step 3: 写入L1寄存器
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from elite_register import Register

            reg = Register()
            if not l1_key:
                l1_key = f"msg_{int(time.time())}"
            reg.set(l1_slot, l1_key, message)
        except Exception as e:
            self._log(wal_id, "l1_error", str(e))

        # Step 4: confirm
        confirm_result = self.confirm(wal_id, l1_slot, l1_key, memory_fragments)

        return {
            **confirm_result,
            "wal_id": wal_id,
            "l1_slot": l1_slot,
            "l1_key": l1_key,
        }

    # ===================== 崩溃恢复 =====================

    def recover(self, dry_run: bool = False) -> dict:
        """崩溃恢复：扫描未完成的WAL记录，重放未完成操作

        恢复策略：
        1. PENDING记录：重放到L1（消息可能丢失，从WAL恢复）
        2. PROCESSING记录：重新确认（业务逻辑可能未完成）
        3. CONFIRMED记录但L1未写入：重新写L1
        4. SYNCED但L2/L4未同步：重新触发同步
        """
        recovered = {
            "pending": 0,
            "processing": 0,
            "confirmed_no_l1": 0,
            "synced_incomplete": 0,
            "errors": [],
            "actions": [],
        }

        # 1. 恢复 PENDING 记录
        pending_rows = self.conn.execute(
            "SELECT * FROM wal_records WHERE status = 'PENDING'"
        ).fetchall()

        for row in pending_rows:
            if row["retry_count"] >= MAX_RETRIES:
                self._mark_expired(row["id"], "max_retries_exceeded")
                recovered["actions"].append({
                    "wal_id": row["id"], "action": "expired",
                    "reason": "max_retries_exceeded"
                })
                continue

            if dry_run:
                recovered["pending"] += 1
                recovered["actions"].append({
                    "wal_id": row["id"], "action": "would_replay",
                    "message": row["message"][:50]
                })
                continue

            # 重放到L1
            try:
                l1_result = self._replay_to_l1(row)
                recovered["pending"] += 1
                recovered["actions"].append({
                    "wal_id": row["id"], "action": "replayed_to_l1",
                    "l1_key": l1_result.get("l1_key", "")
                })
            except Exception as e:
                self._increment_retry(row["id"])
                recovered["errors"].append({
                    "wal_id": row["id"], "error": str(e)
                })

        # 2. 恢复 PROCESSING 记录
        processing_rows = self.conn.execute(
            "SELECT * FROM wal_records WHERE status = 'PROCESSING'"
        ).fetchall()

        for row in processing_rows:
            if row["retry_count"] >= MAX_RETRIES:
                self._mark_expired(row["id"], "max_retries_exceeded")
                continue

            if dry_run:
                recovered["processing"] += 1
                continue

            # 重新确认
            try:
                l1_result = self._replay_to_l1(row)
                self.confirm(row["id"],
                            l1_slot=l1_result.get("l1_slot", "RECENT"),
                            l1_key=l1_result.get("l1_key", ""))
                recovered["processing"] += 1
            except Exception as e:
                self._increment_retry(row["id"])
                recovered["errors"].append({
                    "wal_id": row["id"], "error": str(e)
                })

        # 3. CONFIRMED 但 L1 未写入
        unconfirmed_rows = self.conn.execute(
            "SELECT * FROM wal_records WHERE status = 'CONFIRMED' AND l1_confirmed = 0"
        ).fetchall()

        for row in unconfirmed_rows:
            if dry_run:
                recovered["confirmed_no_l1"] += 1
                continue

            try:
                l1_result = self._replay_to_l1(row)
                self.conn.execute(
                    "UPDATE wal_records SET l1_confirmed = 1, l1_slot = ?, l1_key = ? WHERE id = ?",
                    (l1_result.get("l1_slot", ""), l1_result.get("l1_key", ""), row["id"])
                )
                self.conn.commit()
                recovered["confirmed_no_l1"] += 1
            except Exception as e:
                recovered["errors"].append({
                    "wal_id": row["id"], "error": str(e)
                })

        # 4. SYNCED 但 L2/L4 未同步
        incomplete_sync = self.conn.execute("""
            SELECT * FROM wal_records
            WHERE status = 'SYNCED' AND (l2_synced = 0 OR l4_synced = 0)
        """).fetchall()

        for row in incomplete_sync:
            if dry_run:
                recovered["synced_incomplete"] += 1
                continue

            try:
                sync_result = self._replay_sync(row)
                recovered["synced_incomplete"] += 1
            except Exception as e:
                recovered["errors"].append({
                    "wal_id": row["id"], "error": str(e)
                })

        if not dry_run:
            self._meta["total_recoveries"] += 1
            self._save_meta()
            self._log("system", "recover",
                      f"pending={recovered['pending']} processing={recovered['processing']} "
                      f"confirmed_no_l1={recovered['confirmed_no_l1']} "
                      f"synced_incomplete={recovered['synced_incomplete']}")

        return recovered

    def _replay_to_l1(self, row) -> dict:
        """将WAL记录重放到L1寄存器"""
        sys.path.insert(0, str(Path(__file__).parent))
        from elite_register import Register

        reg = Register()
        l1_slot = row["l1_slot"] or "RECENT"
        l1_key = row["l1_key"] or f"recovered_{int(time.time())}"

        # 写入L1
        reg.set(l1_slot, l1_key, row["message"])

        # 如果有记忆片段，也写入
        fragments = json.loads(row["memory_fragments"] or "[]")
        for i, frag in enumerate(fragments[:3]):
            frag_key = f"frag_{l1_key}_{i}"
            reg.set("TEMP", frag_key, str(frag))

        return {"l1_slot": l1_slot, "l1_key": l1_key}

    def _replay_sync(self, row) -> dict:
        """重放L2/L4同步"""
        sys.path.insert(0, str(Path(__file__).parent))
        result = {"l2": "", "l4": ""}

        # L2 同步
        if not row["l2_synced"]:
            try:
                from elite_sync import LanceStore
                lance = LanceStore()
                content_hash = lance.add(
                    text=row["message"],
                    layer="L1",
                    source=f"wal_replay:{row['id']}",
                    feishu_id=""
                )
                self.conn.execute(
                    "UPDATE wal_records SET l2_synced = 1, l2_hash = ? WHERE id = ?",
                    (content_hash, row["id"])
                )
                self.conn.commit()
                result["l2"] = content_hash
            except Exception as e:
                result["l2_error"] = str(e)

        # L4 同步（如果涉及文件操作）
        if not row["l4_synced"] and row["l1_slot"] in ("TASK", "CONTEXT"):
            try:
                from elite_filestore import FileStore
                fs = FileStore()
                # 对于上下文类信息，记录到L4
                fs._log(str(Path(__file__).parent), "wal_replay",
                       f"Replayed from WAL: {row['id']}")
                self.conn.execute(
                    "UPDATE wal_records SET l4_synced = 1 WHERE id = ?",
                    (row["id"],)
                )
                self.conn.commit()
                result["l4"] = "ok"
            except Exception as e:
                result["l4_error"] = str(e)

        return result

    def _mark_expired(self, wal_id: str, reason: str = ""):
        """标记为过期"""
        self.conn.execute("""
            UPDATE wal_records SET status = 'EXPIRED', expired_at = ?, error_log = ?
            WHERE id = ?
        """, (time.time(), reason, wal_id))
        self.conn.commit()
        self._log(wal_id, "expired", reason)

    def _increment_retry(self, wal_id: str):
        """增加重试计数"""
        self.conn.execute(
            "UPDATE wal_records SET retry_count = retry_count + 1 WHERE id = ?",
            (wal_id,)
        )
        self.conn.commit()

    # ===================== 检查点 =====================

    def checkpoint(self, label: str = "") -> dict:
        """创建检查点：全量快照当前WAL状态

        检查点用途：
        1. 加速崩溃恢复（从最近检查点开始扫描）
        2. 审计追踪（查看任意时间点的系统状态）
        """
        # 统计当前状态
        stats = {}
        for status in WALStatus:
            count = self.conn.execute(
                "SELECT COUNT(*) as c FROM wal_records WHERE status = ?",
                (status.value,)
            ).fetchone()["c"]
            stats[status.value] = count

        # 全量快照
        all_records = self.conn.execute(
            "SELECT * FROM wal_records WHERE status NOT IN ('EXPIRED')"
        ).fetchall()

        snapshot = {
            "timestamp": time.time(),
            "label": label or f"checkpoint-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            "stats": stats,
            "records_count": len(all_records),
            "records": [dict(r) for r in all_records],
        }

        # 保存快照
        filename = f"cp-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        filepath = Path(CHECKPOINT_DIR) / filename
        filepath.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        # 更新元信息
        checkpoint_id = f"CP-{int(time.time())}"
        self._meta["last_checkpoint_ts"] = time.time()
        self._meta["last_checkpoint_id"] = checkpoint_id
        self._meta["records_since_checkpoint"] = 0
        self._save_meta()
        self._log("system", "checkpoint",
                  f"id={checkpoint_id} records={len(all_records)}")

        return {
            "checkpoint_id": checkpoint_id,
            "path": str(filepath),
            "stats": stats,
            "records_count": len(all_records),
        }

    # ===================== 查询 =====================

    def list_records(self, status: str = None, limit: int = 20,
                     offset: int = 0, session_id: str = None) -> list:
        """列出WAL记录"""
        sql = "SELECT * FROM wal_records WHERE 1=1"
        params = []
        if status:
            sql += " AND status = ?"
            params.append(status)
        if session_id:
            sql += " AND session_id = ?"
            params.append(session_id)
        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def info(self, wal_id: str) -> dict:
        """查看WAL记录详情"""
        row = self.conn.execute(
            "SELECT * FROM wal_records WHERE id = ?", (wal_id,)
        ).fetchone()
        if row is None:
            return {"status": "error", "message": f"WAL记录不存在: {wal_id}"}

        rd = dict(row)
        # 获取日志
        logs = self.conn.execute(
            "SELECT * FROM wal_log WHERE wal_id = ? ORDER BY timestamp",
            (wal_id,)
        ).fetchall()
        rd["logs"] = [dict(l) for l in logs]

        return {"status": "ok", "data": rd}

    def search(self, query: str, limit: int = 10) -> list:
        """全文搜索WAL记录"""
        results = []
        seen = set()

        # FTS5
        try:
            from elite_coldstore import ColdStore
            fts_q = ColdStore._make_fts_query(query)
            rows = self.conn.execute("""
                SELECT w.* FROM wal_fts f
                JOIN wal_records w ON w.rowid = f.rowid
                WHERE wal_fts MATCH ?
                ORDER BY w.created_at DESC LIMIT ?
            """, (fts_q, limit)).fetchall()
            for r in rows:
                rd = dict(r)
                if rd["id"] not in seen:
                    seen.add(rd["id"])
                    results.append(rd)
        except (sqlite3.OperationalError, sqlite3.DatabaseError):
            pass

        # LIKE 兜底
        rows = self.conn.execute("""
            SELECT * FROM wal_records
            WHERE message LIKE ? AND id NOT IN ({})
            ORDER BY created_at DESC LIMIT ?
        """.format(",".join(["?"] * len(seen)) if seen else "SELECT ''"),
            [f"%{query}%"] + list(seen) + [limit]
        ).fetchall()
        for r in rows:
            results.append(dict(r))

        return results[:limit]

    # ===================== 清理 =====================

    def clean(self, days: int = None, dry_run: bool = False) -> dict:
        """清理过期WAL记录

        策略：
        - CONFIRMED/SYNCED超过N天 → 标记EXPIRED
        - EXPIRED超过30天 → 物理删除
        """
        days = days or DEFAULT_EXPIRE_DAYS
        cutoff_ts = time.time() - days * 86400
        deep_cutoff = time.time() - DEFAULT_CLEAN_DAYS * 86400

        result = {"expired": 0, "deleted": 0, "actions": []}

        # 标记过期
        rows = self.conn.execute("""
            SELECT id, message FROM wal_records
            WHERE status IN ('CONFIRMED', 'SYNCED')
            AND confirmed_at > 0 AND confirmed_at < ?
        """, (cutoff_ts,)).fetchall()

        for row in rows:
            if dry_run:
                result["actions"].append({
                    "wal_id": row["id"], "action": "would_expire",
                    "message": row["message"][:50]
                })
            else:
                self._mark_expired(row["id"], "auto_expired")
            result["expired"] += 1

        # 物理删除
        old_expired = self.conn.execute("""
            SELECT id, message FROM wal_records
            WHERE status = 'EXPIRED' AND expired_at > 0 AND expired_at < ?
        """, (deep_cutoff,)).fetchall()

        for row in old_expired:
            if dry_run:
                result["actions"].append({
                    "wal_id": row["id"], "action": "would_delete",
                    "message": row["message"][:50]
                })
            else:
                self.conn.execute("DELETE FROM wal_log WHERE wal_id = ?", (row["id"],))
                self.conn.execute("DELETE FROM wal_records WHERE id = ?", (row["id"],))
            result["deleted"] += 1

        if not dry_run:
            self.conn.commit()
            self._log("system", "clean",
                      f"expired={result['expired']} deleted={result['deleted']}")

        return result

    # ===================== 统计 =====================

    def stats(self) -> dict:
        """WAL统计概览"""
        total = self.conn.execute("SELECT COUNT(*) as c FROM wal_records").fetchone()["c"]

        status_dist = {}
        for status in WALStatus:
            count = self.conn.execute(
                "SELECT COUNT(*) as c FROM wal_records WHERE status = ?",
                (status.value,)
            ).fetchone()["c"]
            status_dist[status.value] = count

        # 需要恢复的记录数
        needs_recovery = (
            status_dist.get("PENDING", 0) +
            status_dist.get("PROCESSING", 0)
        )

        # L1确认率
        confirmed_total = status_dist.get("CONFIRMED", 0) + status_dist.get("SYNCED", 0)
        l1_unconfirmed = self.conn.execute(
            "SELECT COUNT(*) as c FROM wal_records WHERE status = 'CONFIRMED' AND l1_confirmed = 0"
        ).fetchone()["c"]

        # 同步率
        l2_unsynced = self.conn.execute("""
            SELECT COUNT(*) as c FROM wal_records
            WHERE status = 'SYNCED' AND l2_synced = 0
        """).fetchone()["c"]

        # 时间范围
        earliest = self.conn.execute(
            "SELECT MIN(created_at) as t FROM wal_records"
        ).fetchone()["t"]
        latest = self.conn.execute(
            "SELECT MAX(created_at) as t FROM wal_records"
        ).fetchone()["t"]

        # 检查点信息
        checkpoint_count = len(list(Path(CHECKPOINT_DIR).glob("cp-*.json")))

        db_size = os.path.getsize(WAL_DB) / 1024 if os.path.exists(WAL_DB) else 0

        return {
            "total_records": total,
            "status_distribution": status_dist,
            "needs_recovery": needs_recovery,
            "l1_unconfirmed": l1_unconfirmed,
            "l2_unsynced": l2_unsynced,
            "confirmed_total": confirmed_total,
            "earliest": datetime.fromtimestamp(earliest).strftime("%Y-%m-%d %H:%M") if earliest else "N/A",
            "latest": datetime.fromtimestamp(latest).strftime("%Y-%m-%d %H:%M") if latest else "N/A",
            "checkpoints": checkpoint_count,
            "last_checkpoint": datetime.fromtimestamp(self._meta["last_checkpoint_ts"]).strftime("%Y-%m-%d %H:%M")
                if self._meta.get("last_checkpoint_ts") else "从未",
            "total_recoveries": self._meta.get("total_recoveries", 0),
            "db_size_kb": round(db_size, 1),
            "db_path": WAL_DB,
        }

    # ===================== 飞书同步 =====================

    # 飞书多维表配置
    FEISHU_APP_TOKEN = "G56JbFHC0abrj2sdgIwcE9Cenn2"
    FEISHU_TABLE_ID = "tblZxOCAmGAk84cJ"

    def sync_to_feishu(self, wal_ids: list = None, batch_size: int = 5) -> dict:
        """将WAL记录同步到飞书多维表

        映射关系：
          记忆文本 ← message + [status]
          记忆层级 ← "WAL-防丢日志"
          来源     ← source
          写入时间 ← created_at (ms)
          LanceDB_ID ← wal_id (本地ID)
          同步状态 ← "已同步"

        Args:
            wal_ids: 指定要同步的WAL ID列表，None则同步所有未同步记录
            batch_size: 每批推送数量（飞书API限制，建议≤5）
        """
        # 查询待同步记录
        if wal_ids:
            placeholders = ",".join(["?"] * len(wal_ids))
            rows = self.conn.execute(f"""
                SELECT * FROM wal_records
                WHERE id IN ({placeholders}) AND (feishu_id IS NULL OR feishu_id = '')
            """, wal_ids).fetchall()
        else:
            rows = self.conn.execute("""
                SELECT * FROM wal_records
                WHERE (feishu_id IS NULL OR feishu_id = '')
                AND status NOT IN ('EXPIRED')
                ORDER BY created_at ASC
            """).fetchall()

        if not rows:
            return {"pushed": 0, "errors": [], "message": "无待同步记录"}

        # 分批推送
        total_pushed = 0
        total_errors = []
        all_results = []

        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            records = []
            wal_id_map = {}  # feishu fields key -> wal_id

            for row in batch:
                rd = dict(row)
                # 构建飞书记录
                msg_display = rd["message"][:200]
                status_tag = f" [{rd['status']}]"
                l1_info = ""
                if rd["l1_slot"] and rd["l1_key"]:
                    l1_info = f" L1={rd['l1_slot']}/{rd['l1_key']}"

                record_fields = {
                    "记忆文本": msg_display + status_tag + l1_info,
                    "记忆层级": "WAL-防丢日志",
                    "来源": f"WAL:{rd['source']}",
                    "写入时间": int(rd["created_at"] * 1000),
                    "LanceDB_ID": rd["id"],
                    "同步状态": "已同步",
                }
                records.append({"fields": record_fields})

            # 调用飞书API
            try:
                import subprocess
                import json as _json

                # 通过MCP推送（直接构造参数调用）
                result = self._feishu_batch_create(records)
                if result and result.get("records"):
                    for j, feishu_rec in enumerate(result["records"]):
                        if j < len(batch):
                            wal_id = dict(batch[j])["id"]
                            feishu_id = feishu_rec.get("record_id", "")
                            # 回写feishu_id到本地
                            self.conn.execute(
                                "UPDATE wal_records SET feishu_id = ? WHERE id = ?",
                                (feishu_id, wal_id)
                            )
                            self._log(wal_id, "sync_feishu", f"feishu_id={feishu_id}")
                            all_results.append({
                                "wal_id": wal_id,
                                "feishu_id": feishu_id,
                            })
                            total_pushed += 1
                else:
                    total_errors.append({
                        "batch": i // batch_size + 1,
                        "error": str(result)
                    })
            except Exception as e:
                total_errors.append({
                    "batch": i // batch_size + 1,
                    "error": str(e)
                })

        self.conn.commit()
        return {
            "pushed": total_pushed,
            "total": len(rows),
            "errors": total_errors,
            "results": all_results,
        }

    def _feishu_batch_create(self, records: list) -> dict:
        """调用飞书MCP批量创建记录

        由于WAL运行在CLI环境，不能直接调用MCP工具，
        此方法生成飞书API的curl命令或返回records供外部调用。
        实际同步由外部调用者（WorkBuddy）通过MCP完成。
        """
        # 标记：此方法返回待推送的records数据，由外部MCP调用完成
        # 在CLI模式下，返回None表示需要外部调用
        return None

    def update_feishu_id(self, wal_id: str, feishu_id: str):
        """回写飞书记录ID到本地WAL数据库"""
        self.conn.execute(
            "UPDATE wal_records SET feishu_id = ? WHERE id = ?",
            (feishu_id, wal_id)
        )
        self.conn.commit()
        self._log(wal_id, "feishu_id_set", feishu_id)

    def get_unsynced_records(self, limit: int = 50) -> list:
        """获取所有未同步到飞书的WAL记录（供外部MCP调用使用）"""
        rows = self.conn.execute("""
            SELECT * FROM wal_records
            WHERE (feishu_id IS NULL OR feishu_id = '')
            AND status NOT IN ('EXPIRED')
            ORDER BY created_at ASC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]

    def get_feishu_batch_data(self, records: list) -> list:
        """将WAL记录转为飞书多维表格式的records列表"""
        feishu_records = []
        for rd in records:
            msg_display = rd["message"][:200]
            status_tag = f" [{rd['status']}]"
            l1_info = ""
            if rd.get("l1_slot") and rd.get("l1_key"):
                l1_info = f" L1={rd['l1_slot']}/{rd['l1_key']}"

            feishu_records.append({
                "fields": {
                    "记忆文本": msg_display + status_tag + l1_info,
                    "记忆层级": "WAL-防丢日志",
                    "来源": f"WAL:{rd.get('source', 'user')}",
                    "写入时间": int(rd.get("created_at", 0) * 1000),
                    "LanceDB_ID": rd["id"],
                    "同步状态": "已同步",
                }
            })
        return feishu_records

    def close(self):
        self.conn.close()


# ===================== CLI =====================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    wal = WALProtocol()
    cmd = sys.argv[1]

    if cmd == "begin":
        if len(sys.argv) < 3:
            print("Usage: elite_wal.py begin <message> [--source user|system|agent]")
            sys.exit(1)
        message = sys.argv[2]
        source = "user"
        session_id = ""
        if "--source" in sys.argv:
            source = sys.argv[sys.argv.index("--source") + 1]
        if "--session" in sys.argv:
            session_id = sys.argv[sys.argv.index("--session") + 1]
        result = wal.begin(message, source, session_id)
        print(f"[WAL] BEGIN: {result['wal_id']} (status={result['status']})")

    elif cmd == "confirm":
        if len(sys.argv) < 3:
            print("Usage: elite_wal.py confirm <wal_id> [--slot RECENT] [--key msg_xxx]")
            sys.exit(1)
        wal_id = sys.argv[2]
        slot = "RECENT"
        key = ""
        if "--slot" in sys.argv:
            slot = sys.argv[sys.argv.index("--slot") + 1]
        if "--key" in sys.argv:
            key = sys.argv[sys.argv.index("--key") + 1]
        result = wal.confirm(wal_id, slot, key)
        if result.get("status") == "error":
            print(f"[WAL] ERROR: {result['message']}")
        else:
            print(f"[WAL] CONFIRM: {wal_id} → L1={slot}/{key}")

    elif cmd == "sync":
        if len(sys.argv) < 3:
            print("Usage: elite_wal.py sync <wal_id> [--l2-hash xxx] [--l4-hash xxx]")
            sys.exit(1)
        wal_id = sys.argv[2]
        l2_hash = ""
        l4_hash = ""
        if "--l2-hash" in sys.argv:
            l2_hash = sys.argv[sys.argv.index("--l2-hash") + 1]
        if "--l4-hash" in sys.argv:
            l4_hash = sys.argv[sys.argv.index("--l4-hash") + 1]
        result = wal.sync(wal_id, l2_hash, l4_hash)
        if result.get("status") == "error":
            print(f"[WAL] ERROR: {result['message']}")
        else:
            print(f"[WAL] SYNC: {wal_id} → L2={'ok' if l2_hash else 'skip'} L4={'ok' if l4_hash else 'skip'}")

    elif cmd == "status" or cmd == "stats":
        s = wal.stats()
        print("WAL Protocol 状态")
        print(f"  总记录: {s['total_records']}")
        print(f"  状态分布:")
        for status, count in s["status_distribution"].items():
            marker = " <-- 需恢复!" if status in ("PENDING", "PROCESSING") else ""
            print(f"    {status:12s}: {count}{marker}")
        print(f"  需恢复: {s['needs_recovery']}")
        print(f"  L1未确认: {s['l1_unconfirmed']}")
        print(f"  L2未同步: {s['l2_unsynced']}")
        print(f"  检查点: {s['checkpoints']}个 | 上次: {s['last_checkpoint']}")
        print(f"  历史恢复: {s['total_recoveries']}次")
        print(f"  时间范围: {s['earliest']} ~ {s['latest']}")
        print(f"  数据库: {s['db_path']} ({s['db_size_kb']:.1f}KB)")

    elif cmd == "recover":
        dry = "--dry-run" in sys.argv
        result = wal.recover(dry_run=dry)
        mode = "预览" if dry else "执行"
        print(f"[WAL] 崩溃恢复{mode}:")
        print(f"  PENDING恢复: {result['pending']}")
        print(f"  PROCESSING恢复: {result['processing']}")
        print(f"  L1未确认修复: {result['confirmed_no_l1']}")
        print(f"  同步不完整修复: {result['synced_incomplete']}")
        if result["errors"]:
            print(f"  错误: {len(result['errors'])}")
            for e in result["errors"][:5]:
                print(f"    {e['wal_id']}: {e['error']}")
        if result["actions"]:
            print(f"  操作详情:")
            for a in result["actions"][:10]:
                print(f"    {a['wal_id']}: {a['action']}")

    elif cmd == "checkpoint":
        result = wal.checkpoint()
        print(f"[WAL] 检查点已创建: {result['checkpoint_id']}")
        print(f"  路径: {result['path']}")
        print(f"  记录数: {result['records_count']}")
        print(f"  状态: {result['stats']}")

    elif cmd == "list":
        status = None
        limit = 20
        if "--status" in sys.argv:
            status = sys.argv[sys.argv.index("--status") + 1]
        if "--limit" in sys.argv:
            limit = int(sys.argv[sys.argv.index("--limit") + 1])
        records = wal.list_records(status, limit)
        for r in records:
            ts = datetime.fromtimestamp(r["created_at"]).strftime("%m-%d %H:%M")
            l1_tag = "L1ok" if r["l1_confirmed"] else "L1no"
            l2_tag = "L2ok" if r["l2_synced"] else "L2no"
            print(f"  {r['id']} | {ts} | {r['status']:10s} | {l1_tag} {l2_tag} | {r['message'][:40]}")

    elif cmd == "info":
        if len(sys.argv) < 3:
            print("Usage: elite_wal.py info <wal_id>")
            sys.exit(1)
        result = wal.info(sys.argv[2])
        if result.get("status") == "error":
            print(f"[WAL] {result['message']}")
        else:
            d = result["data"]
            print(f"WAL ID: {d['id']}")
            print(f"状态: {d['status']}")
            print(f"来源: {d['source']}")
            print(f"消息: {d['message'][:200]}")
            print(f"会话: {d['session_id'] or 'N/A'}")
            print(f"L1: confirmed={d['l1_confirmed']} slot={d['l1_slot']} key={d['l1_key']}")
            print(f"L2: synced={d['l2_synced']} hash={d['l2_hash']}")
            print(f"L4: synced={d['l4_synced']} hash={d['l4_hash']}")
            print(f"记忆片段: {d['memory_fragments'][:200]}")
            print(f"重试: {d['retry_count']}")
            print(f"创建: {datetime.fromtimestamp(d['created_at']).strftime('%Y-%m-%d %H:%M:%S')}")
            if d["confirmed_at"]:
                print(f"确认: {datetime.fromtimestamp(d['confirmed_at']).strftime('%Y-%m-%d %H:%M:%S')}")
            if d["synced_at"]:
                print(f"同步: {datetime.fromtimestamp(d['synced_at']).strftime('%Y-%m-%d %H:%M:%S')}")
            if d["logs"]:
                print("日志:")
                for l in d["logs"]:
                    ts = datetime.fromtimestamp(l["timestamp"]).strftime("%H:%M:%S")
                    print(f"  {ts} | {l['action']} | {l['detail'][:50]}")

    elif cmd == "clean":
        days = DEFAULT_EXPIRE_DAYS
        dry = "--dry-run" in sys.argv
        if len(sys.argv) > 2 and sys.argv[2].isdigit():
            days = int(sys.argv[2])
        result = wal.clean(days, dry)
        mode = "预览" if dry else "执行"
        print(f"[WAL] 清理{mode} (>{days}天):")
        print(f"  标记过期: {result['expired']}")
        print(f"  物理删除: {result['deleted']}")

    elif cmd == "sync-feishu":
        # 输出待同步记录的JSON，供外部MCP调用使用
        import json as _json
        unsynced = wal.get_unsynced_records()
        if not unsynced:
            print("[WAL] 无待同步到飞书的记录")
        else:
            feishu_data = wal.get_feishu_batch_data(unsynced)
            print(_json.dumps({
                "total": len(unsynced),
                "records": feishu_data,
                "wal_ids": [r["id"] for r in unsynced],
            }, ensure_ascii=False, indent=2))

    elif cmd == "write-through":
        # 快捷方式：一条龙 begin → processing → confirm
        if len(sys.argv) < 3:
            print("Usage: elite_wal.py write-through <message> [--source user] [--slot RECENT]")
            sys.exit(1)
        message = sys.argv[2]
        source = "user"
        slot = "RECENT"
        if "--source" in sys.argv:
            source = sys.argv[sys.argv.index("--source") + 1]
        if "--slot" in sys.argv:
            slot = sys.argv[sys.argv.index("--slot") + 1]
        result = wal.write_through(message, source, l1_slot=slot)
        print(f"[WAL] WRITE-THROUGH: {result['wal_id']} → L1={result['l1_slot']}/{result['l1_key']}")

    else:
        print(f"未知命令: {cmd}")
        print("可用: begin, processing, confirm, sync, write-through, recover, checkpoint, list, info, clean, status/stats")

    wal.close()
