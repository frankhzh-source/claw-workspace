"""
Elite L1 Register — 寄存器级工作记忆
最快速、最短命的记忆层。类似 CPU 寄存器：<1ms 读写，KB 级容量，会话级生命周期。

架构：
  6 个功能槽位
  ├── TASK     — 当前活跃任务（TTL: 会话级）
  ├── CONTEXT  — 活跃上下文摘要（TTL: 会话级）
  ├── PENDING  — 待决事项（TTL: 7天）
  ├── TEMP     — 临时事实/缓存（TTL: 1小时）
  ├── RECENT   — 近期交互摘要（TTL: 24小时）
  └── SCRATCH  — 草稿/暂存（TTL: 会话级）

数据流：
  用户输入 → L1写入 → 处理业务 → 晋升到L2(语义搜索) → 沉淀到L4(MEMORY.md)
  过期项自动清除 → 高价值项手动/自动晋升

CLI:
  python elite_register.py set <slot> <key> <value> [--ttl <seconds>]
  python elite_register.py get <slot> [key]
  python elite_register.py list [--slot <slot>]
  python elite_register.py expire
  python elite_register.py promote <slot> <key>
  python elite_register.py snapshot
  python elite_register.py status
  python elite_register.py clear [--slot <slot>]
"""
import json
import time
import hashlib
import sys
from pathlib import Path
from datetime import datetime

# ===================== 配置 =====================
REGISTER_DIR = str(Path.home() / ".openclaw" / "memory" / "register")
REGISTER_FILE = str(Path(REGISTER_DIR) / "register.json")
SESSION_FILE = str(Path(REGISTER_DIR) / "session.json")
PROMOTION_LOG = str(Path(REGISTER_DIR) / "promotion_log.json")

# 槽位定义：名称 → 默认 TTL（秒），0 = 永不过期（会话级）
SLOTS = {
    "TASK":    0,       # 会话级，随会话生灭
    "CONTEXT": 0,       # 会话级
    "PENDING": 7 * 86400,  # 7天
    "TEMP":    3600,    # 1小时
    "RECENT":  86400,   # 24小时
    "SCRATCH": 0,       # 会话级
}

# 槽位描述（用于 status 展示）
SLOT_DESC = {
    "TASK":    "当前活跃任务",
    "CONTEXT": "活跃上下文摘要",
    "PENDING": "待决事项",
    "TEMP":    "临时事实/缓存",
    "RECENT":  "近期交互摘要",
    "SCRATCH": "草稿/暂存",
}


# ===================== 核心引擎 =====================
class Register:
    """L1 寄存器引擎 — 纯文件持久化，零依赖"""

    def __init__(self):
        self._data = self._load()

    # ---------- 持久化 ----------
    def _load(self) -> dict:
        path = Path(REGISTER_FILE)
        if path.exists():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                # 确保结构完整
                for slot in SLOTS:
                    if slot not in raw:
                        raw[slot] = {}
                return raw
            except (json.JSONDecodeError, OSError):
                pass
        # 初始化空结构
        return {slot: {} for slot in SLOTS}

    def _save(self):
        path = Path(REGISTER_FILE)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    # ---------- 核心 CRUD ----------
    def set(self, slot: str, key: str, value: str, ttl: int = None,
            wal_enabled: bool = True) -> dict:
        """写入寄存器，返回写入的条目

        wal_enabled: 是否自动写入WAL日志（防丢上下文）
        流程：收到消息 → WAL begin → L1 set → WAL confirm
        """
        slot = slot.upper()
        if slot not in SLOTS:
            raise ValueError(f"未知槽位: {slot}，可选: {list(SLOTS.keys())}")

        default_ttl = SLOTS[slot]
        effective_ttl = ttl if ttl is not None else default_ttl
        expires_at = time.time() + effective_ttl if effective_ttl > 0 else 0  # 0=永不过期

        entry = {
            "value": value,
            "created_at": time.time(),
            "updated_at": time.time(),
            "expires_at": expires_at,
            "access_count": 0,
            "content_hash": hashlib.md5(value.encode()).hexdigest()[:12],
        }
        self._data[slot][key] = entry
        self._save()

        # WAL 集成：自动记录写入日志
        if wal_enabled:
            self._wal_log(slot, key, value)

        return entry

    def _wal_log(self, slot: str, key: str, value: str):
        """WAL日志记录：L1写入时自动触发"""
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from elite_wal import WALProtocol
            wal = WALProtocol()
            wal_id = f"auto-L1-{int(time.time())}-{hashlib.md5(f'{slot}/{key}'.encode()).hexdigest()[:8]}"
            # 直接写入WAL并确认（L1已落盘，可安全confirm）
            wal.conn.execute("""
                INSERT OR REPLACE INTO wal_records
                (id, message, message_hash, source, status, l1_confirmed,
                 l1_slot, l1_key, context_snapshot, created_at, confirmed_at)
                VALUES (?, ?, ?, 'l1_auto', 'CONFIRMED', 1, ?, ?, '{}', ?, ?)
            """, (wal_id, f"[L1] {slot}/{key}: {value[:100]}",
                  hashlib.md5(value.encode()).hexdigest()[:12],
                  slot, key, time.time(), time.time()))
            wal.conn.commit()
            wal._log(wal_id, "l1_auto_confirm", f"{slot}/{key}")
            wal.close()
        except Exception:
            pass  # WAL写入失败不影响L1主流程

    def get(self, slot: str, key: str) -> str | None:
        """读取寄存器值，自动检查过期"""
        slot = slot.upper()
        if slot not in self._data:
            return None
        entry = self._data[slot].get(key)
        if entry is None:
            return None
        # 过期检查
        if entry["expires_at"] > 0 and time.time() > entry["expires_at"]:
            del self._data[slot][key]
            self._save()
            return None
        entry["access_count"] += 1
        entry["updated_at"] = time.time()
        self._save()
        return entry["value"]

    def get_entry(self, slot: str, key: str) -> dict | None:
        """读取完整条目（含元数据）"""
        slot = slot.upper()
        if slot not in self._data:
            return None
        entry = self._data[slot].get(key)
        if entry is None:
            return None
        if entry["expires_at"] > 0 and time.time() > entry["expires_at"]:
            del self._data[slot][key]
            self._save()
            return None
        return entry

    def delete(self, slot: str, key: str) -> bool:
        """删除条目"""
        slot = slot.upper()
        if slot in self._data and key in self._data[slot]:
            del self._data[slot][key]
            self._save()
            return True
        return False

    def list_slot(self, slot: str = None) -> dict:
        """列出槽位内容，自动过滤过期项"""
        self.expire()  # 先清理
        if slot:
            slot = slot.upper()
            return {slot: dict(self._data.get(slot, {}))}
        return {s: dict(items) for s, items in self._data.items()}

    # ---------- 过期管理 ----------
    def expire(self) -> int:
        """清除所有过期条目，返回清除数量"""
        now = time.time()
        removed = 0
        for slot in self._data:
            expired_keys = [
                k for k, v in self._data[slot].items()
                if v["expires_at"] > 0 and now > v["expires_at"]
            ]
            for k in expired_keys:
                del self._data[slot][k]
                removed += 1
        if removed:
            self._save()
        return removed

    # ---------- 晋升到 L2 ----------
    def promote(self, slot: str, key: str) -> dict:
        """将条目晋升到 L2 Warm Store（LanceDB）
        返回晋升结果，包含 L2 写入状态
        """
        entry = self.get_entry(slot, key)
        if entry is None:
            return {"status": "error", "message": f"条目不存在或已过期: {slot}/{key}"}

        # 尝试写入 L2
        try:
            # 导入 L2 模块
            sys.path.insert(0, str(Path(__file__).parent))
            from elite_sync import LanceStore

            lance = LanceStore()
            content_hash = lance.add(
                text=entry["value"],
                layer="L1",
                source=f"register:{slot}/{key}",
                feishu_id=""
            )
            result = {
                "status": "ok",
                "message": f"已晋升到 L2: {slot}/{key}",
                "l2_hash": content_hash,
                "slot": slot,
                "key": key,
            }
        except Exception as e:
            result = {
                "status": "error",
                "message": f"L2 写入失败: {e}",
                "slot": slot,
                "key": key,
            }

        # 记录晋升日志
        self._log_promotion(slot, key, result)
        return result

    def promote_all_pending(self) -> list:
        """将所有 PENDING 槽位的条目批量晋升到 L2"""
        results = []
        for key in list(self._data.get("PENDING", {}).keys()):
            results.append(self.promote("PENDING", key))
        return results

    def _log_promotion(self, slot: str, key: str, result: dict):
        """记录晋升日志"""
        path = Path(PROMOTION_LOG)
        log = []
        if path.exists():
            try:
                log = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        log.append({
            "timestamp": time.time(),
            "slot": slot,
            "key": key,
            "result": result.get("status"),
            "l2_hash": result.get("l2_hash", ""),
        })
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(log[-100:], ensure_ascii=False, indent=2),  # 保留最近100条
            encoding="utf-8"
        )

    # ---------- 会话管理 ----------
    def new_session(self, task: str = "", context: str = "") -> str:
        """开启新会话：清空会话级槽位，设置新任务"""
        session_id = f"S-{int(time.time())}"

        # 清空会话级槽位
        for slot, default_ttl in SLOTS.items():
            if default_ttl == 0:  # 会话级
                self._data[slot] = {}

        if task:
            self.set("TASK", "active_task", task)
        if context:
            self.set("CONTEXT", "session_context", context)

        # 记录会话元信息
        session_meta = {
            "session_id": session_id,
            "started_at": time.time(),
            "task": task,
        }
        path = Path(SESSION_FILE)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(session_meta, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        self._save()
        return session_id

    def get_session(self) -> dict:
        """获取当前会话信息"""
        path = Path(SESSION_FILE)
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    # ---------- 快照与统计 ----------
    def snapshot(self) -> dict:
        """完整快照：所有槽位 + 会话信息 + 统计"""
        self.expire()
        stats = {}
        for slot in SLOTS:
            items = self._data.get(slot, {})
            active = sum(1 for v in items.values()
                       if v["expires_at"] == 0 or v["expires_at"] > time.time())
            stats[slot] = {
                "total": len(items),
                "active": active,
                "description": SLOT_DESC.get(slot, ""),
            }
        return {
            "timestamp": time.time(),
            "session": self.get_session(),
            "slots": stats,
            "data": self._data,
        }

    def status(self) -> dict:
        """精简状态概览"""
        self.expire()
        slot_summary = {}
        for slot in SLOTS:
            items = self._data.get(slot, {})
            slot_summary[slot] = {
                "count": len(items),
                "desc": SLOT_DESC.get(slot, ""),
                "ttl_default": SLOTS[slot] if SLOTS[slot] > 0 else "session",
            }

        session = self.get_session()
        return {
            "session_id": session.get("session_id", "N/A"),
            "started_at": datetime.fromtimestamp(session["started_at"]).strftime("%Y-%m-%d %H:%M")
                if session.get("started_at") else "N/A",
            "task": session.get("task", "N/A"),
            "slots": slot_summary,
            "total_entries": sum(s["count"] for s in slot_summary.values()),
        }

    def clear(self, slot: str = None):
        """清空指定槽位或全部"""
        if slot:
            slot = slot.upper()
            if slot in self._data:
                self._data[slot] = {}
        else:
            for s in SLOTS:
                self._data[s] = {}
        self._save()


# ===================== CLI =====================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    reg = Register()
    cmd = sys.argv[1]

    if cmd == "set":
        if len(sys.argv) < 5:
            print("Usage: elite_register.py set <slot> <key> <value> [--ttl <seconds>]")
            sys.exit(1)
        slot, key, value = sys.argv[2], sys.argv[3], sys.argv[4]
        ttl = None
        if "--ttl" in sys.argv:
            ttl = int(sys.argv[sys.argv.index("--ttl") + 1])
        entry = reg.set(slot, key, value, ttl)
        ttl_str = f"TTL={ttl}s" if ttl else f"默认TTL={SLOTS.get(slot.upper(), 0)}s"
        print(f"[L1] SET {slot}/{key} = {value[:50]}... ({ttl_str})")

    elif cmd == "get":
        if len(sys.argv) < 4:
            print("Usage: elite_register.py get <slot> <key>")
            sys.exit(1)
        slot, key = sys.argv[2], sys.argv[3]
        val = reg.get(slot, key)
        if val is None:
            print(f"[L1] {slot}/{key} = (不存在或已过期)")
        else:
            print(f"[L1] {slot}/{key} = {val}")

    elif cmd == "list":
        slot = sys.argv[3] if len(sys.argv) > 3 and sys.argv[2] == "--slot" else None
        if slot is None and len(sys.argv) > 2 and sys.argv[2] != "--slot":
            slot = sys.argv[2]
        data = reg.list_slot(slot)
        for s, items in data.items():
            if not items:
                continue
            print(f"\n[{s}] {SLOT_DESC.get(s, '')}")
            for k, v in items.items():
                exp = ""
                if v["expires_at"] > 0:
                    remain = v["expires_at"] - time.time()
                    if remain > 0:
                        exp = f" (剩余{remain:.0f}s)"
                    else:
                        exp = " (已过期)"
                print(f"  {k}: {v['value'][:60]}{exp} [访问{v['access_count']}次]")

    elif cmd == "expire":
        removed = reg.expire()
        print(f"[L1] 清除了 {removed} 条过期项")

    elif cmd == "promote":
        if len(sys.argv) < 4:
            print("Usage: elite_register.py promote <slot> <key>")
            sys.exit(1)
        slot, key = sys.argv[2], sys.argv[3]
        result = reg.promote(slot, key)
        if result["status"] == "ok":
            print(f"[L1→L2] 晋升成功: {slot}/{key} → L2 hash={result['l2_hash']}")
        else:
            print(f"[L1→L2] 晋升失败: {result['message']}")

    elif cmd == "snapshot":
        snap = reg.snapshot()
        print(json.dumps(snap, ensure_ascii=False, indent=2))

    elif cmd == "status":
        s = reg.status()
        print(f"会话: {s['session_id']} | 任务: {s['task']}")
        print(f"总条目: {s['total_entries']}")
        print("-" * 50)
        for slot, info in s["slots"].items():
            print(f"  {slot:8s} | {info['count']:3d} 条 | TTL: {info['ttl_default']} | {info['desc']}")

    elif cmd == "clear":
        slot = sys.argv[2] if len(sys.argv) > 2 else None
        reg.clear(slot)
        target = slot or "全部"
        print(f"[L1] 已清空: {target}")

    elif cmd == "session":
        if len(sys.argv) < 3:
            session = reg.get_session()
            print(json.dumps(session, ensure_ascii=False, indent=2))
        elif sys.argv[2] == "new":
            task = sys.argv[3] if len(sys.argv) > 3 else ""
            sid = reg.new_session(task)
            print(f"[L1] 新会话: {sid}")
        else:
            print(f"Usage: session [new <task>]")

    else:
        print(f"未知命令: {cmd}")
        print("可用命令: set, get, list, expire, promote, snapshot, status, clear, session")
