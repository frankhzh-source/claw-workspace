"""
Elite L2 Warm Store — LanceDB ↔ 飞书多维表格 双向同步
- push: LanceDB 新增 → 飞书多维表格
- pull: 飞书多维表格 新增/编辑 → LanceDB
- pull --with-cold: 飞书 → LanceDB → L3 冷存储（逆向同步完整链路）
- sync-cold: 手动将 LanceDB 所有记录归档到 L3（新机器恢复后执行）
- 状态标记避免重复同步
"""
import json
import time
import hashlib
import lancedb
import httpx
from pathlib import Path
from datetime import datetime

# ===================== 配置 =====================
# LanceDB
LANCEDB_PATH = str(Path.home() / ".openclaw" / "memory" / "lancedb")
TABLE_NAME = "elite_memory"

# Ollama
OLLAMA_BASE = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"

# 飞书多维表格
FEISHU_APP_TOKEN = "G56JbFHC0abrj2sdgIwcE9Cenn2"
FEISHU_TABLE_ID = "tblZxOCAmGAk84cJ"

# 飞书字段映射
FEISHU_FIELDS = {
    "text":       "记忆文本",    # type 1 (文本)
    "layer":      "记忆层级",    # type 3 (单选)
    "source":     "来源",        # type 1 (文本)
    "timestamp":  "写入时间",    # type 5 (日期)
    "lancedb_id": "LanceDB_ID",  # type 1 (文本)
    "sync_status":"同步状态",    # type 3 (单选)
}

# 同步状态文件
SYNC_STATE_FILE = str(Path.home() / ".openclaw" / "memory" / "sync_state.json")

# ===================== Embedding =====================
def embed(text: str) -> list[float]:
    resp = httpx.post(
        f"{OLLAMA_BASE}/api/embed",
        json={"model": EMBED_MODEL, "input": text},
        timeout=60.0,
    )
    resp.raise_for_status()
    return resp.json()["embeddings"][0]

# ===================== 同步状态管理 =====================
def load_sync_state() -> dict:
    path = Path(SYNC_STATE_FILE)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"last_push_ts": 0, "last_pull_ts": 0, "synced_feishu_ids": [], "synced_lancedb_hashes": []}

def save_sync_state(state: dict):
    path = Path(SYNC_STATE_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

# ===================== LanceDB 操作 =====================
class LanceStore:
    def __init__(self):
        self.db = lancedb.connect(LANCEDB_PATH)
        if TABLE_NAME in self.db.table_names():
            self.table = self.db.open_table(TABLE_NAME)
        else:
            self.table = None

    def _ensure_table(self):
        if self.table is None:
            self.table = self.db.create_table(TABLE_NAME, [
                {"text": "__init__", "vector": embed("__init__"),
                 "layer": "system", "source": "auto",
                 "timestamp": time.time(), "feishu_id": "", "content_hash": ""}
            ])

    def add(self, text: str, layer: str = "L4", source: str = "feishu_sync",
            feishu_id: str = "") -> str:
        self._ensure_table()
        content_hash = hashlib.md5(text.encode()).hexdigest()[:12]
        record = {
            "text": text,
            "vector": embed(text),
            "layer": layer,
            "source": source,
            "timestamp": time.time(),
            "feishu_id": feishu_id,
            "content_hash": content_hash,
        }
        self.table.add([record])
        return content_hash

    def _query_all(self) -> list:
        """查询所有记录，返回 list of dict"""
        self._ensure_table()
        try:
            arrow = self.table.head(10000).to_pydict()
            n = len(arrow.get("text", []))
            records = []
            for i in range(n):
                rec = {}
                for key in arrow:
                    rec[key] = arrow[key][i]
                records.append(rec)
            return [r for r in records if r.get("text") != "__init__"]
        except Exception:
            return []

    def get_all_hashes(self) -> set:
        records = self._query_all()
        return {r.get("content_hash", "") for r in records if r.get("content_hash")}

    def get_records_since(self, since_ts: float) -> list:
        records = self._query_all()
        return [r for r in records if r.get("timestamp", 0) > since_ts]

    def search(self, query: str, limit: int = 5):
        self._ensure_table()
        query_vec = embed(query)
        return self.table.search(query_vec).limit(limit).to_list()

# ===================== 飞书 API 操作 =====================
class FeishuStore:
    def __init__(self, app_token: str, table_id: str):
        self.app_token = app_token
        self.table_id = table_id
        self.field_ids = {}
        self._load_field_ids()

    def _load_field_ids(self):
        """通过 MCP 工具预加载字段 ID — 这里用硬编码（从创建结果获取）"""
        self.field_ids = {
            "text":        "flddqsJunh",
            "layer":       "fldPWyTy3n",
            "source":      "fldUS3pnGC",
            "timestamp":   "fldTx1H5Ol",
            "lancedb_id":  "fldCZfrSoj",
            "sync_status": "fldqQgTDH1",
        }

    def _make_fields_dict(self, record: dict) -> dict:
        """将内部字段名映射为飞书字段ID + 值"""
        result = {}
        field_map = {
            "text":        (1,  record.get("text", "")),
            "layer":       (3,  record.get("layer", "L4-文件")),
            "source":      (1,  record.get("source", "")),
            "timestamp":   (5,  int(record.get("timestamp", time.time()) * 1000)),
            "lancedb_id":  (1,  record.get("lancedb_id", "")),
            "sync_status": (3,  record.get("sync_status", "已同步")),
        }
        for key, (ftype, value) in field_map.items():
            fid = self.field_ids.get(key)
            if fid:
                result[fid] = value
        return result

# ===================== 双向同步引擎 =====================
class EliteSync:
    def __init__(self):
        self.lance = LanceStore()
        self.feishu = FeishuStore(FEISHU_APP_TOKEN, FEISHU_TABLE_ID)
        self.state = load_sync_state()

    def push_to_feishu(self, records: list) -> list:
        """LanceDB → 飞书：将记录推送到飞书多维表格"""
        results = []
        existing_hashes = set(self.state.get("synced_lancedb_hashes", []))

        for rec in records:
            content_hash = rec.get("content_hash", "")
            if content_hash in existing_hashes:
                continue

            feishu_record = {
                "text":        rec.get("text", ""),
                "layer":       rec.get("layer", "L4-文件").replace("L4", "L4-文件").replace("L2", "L2-向量库").replace("L1", "L1-寄存器").replace("L3", "L3-图记忆").replace("L5", "L5-语义压缩").replace("L6", "L6-知识图谱"),
                "source":      rec.get("source", ""),
                "timestamp":   rec.get("timestamp", time.time()),
                "lancedb_id":  content_hash,
                "sync_status": "已同步",
            }
            results.append(feishu_record)
            existing_hashes.add(content_hash)

        self.state["synced_lancedb_hashes"] = list(existing_hashes)
        save_sync_state(self.state)
        return results

    def pull_from_feishu(self, feishu_records: list, to_cold: bool = False) -> list:
        """飞书 → LanceDB：将飞书新增/编辑记录写入 LanceDB
        to_cold=True 时同步写入 L3 冷存储
        """
        results = []
        existing_hashes = self.lance.get_all_hashes()
        cold = None
        if to_cold:
            sys.path.insert(0, str(Path(__file__).parent))
            from elite_coldstore import ColdStore
            cold = ColdStore()

        for rec in feishu_records:
            text = rec.get("text", "")
            if not text or text == "__init__":
                continue

            content_hash = hashlib.md5(text.encode()).hexdigest()[:12]
            if content_hash in existing_hashes:
                continue

            layer_raw = rec.get("layer", "L4-文件")
            # 归一化层级名
            layer_map = {
                "L1-寄存器": "L1", "L2-向量库": "L2", "L3-图记忆": "L3",
                "L4-文件": "L4", "L5-语义压缩": "L5", "L6-知识图谱": "L6",
            }
            layer = layer_map.get(layer_raw, "L4")

            feishu_id = rec.get("feishu_id", "")
            hash_id = self.lance.add(text, layer=layer, source="feishu_sync", feishu_id=feishu_id)

            # 同步写入 L3 冷存储
            if cold:
                try:
                    archive_id = cold.archive(
                        text=text, layer=layer, source="feishu_pull_cold",
                        feishu_id=feishu_id, original_ts=time.time()
                    )
                    results.append({
                        "text": text[:50], "hash": hash_id, "feishu_id": feishu_id,
                        "cold_archive_id": archive_id
                    })
                except Exception as e:
                    results.append({
                        "text": text[:50], "hash": hash_id, "feishu_id": feishu_id,
                        "cold_error": str(e)
                    })
            else:
                results.append({"text": text[:50], "hash": hash_id, "feishu_id": feishu_id})

        if cold:
            cold.close()
        return results

    def sync_l2_to_cold(self) -> list:
        """将 LanceDB 所有记录归档到 L3 冷存储（新机器逆向恢复用）"""
        sys.path.insert(0, str(Path(__file__).parent))
        from elite_coldstore import ColdStore
        cold = ColdStore()

        all_records = self.lance._query_all()
        results = []
        for rec in all_records:
            if rec.get("text") == "__init__":
                continue
            try:
                archive_id = cold.archive_from_l2(rec)
                results.append({
                    "archive_id": archive_id,
                    "text": rec.get("text", "")[:50],
                    "layer": rec.get("layer", ""),
                })
            except Exception as e:
                results.append({"text": rec.get("text", "")[:50], "error": str(e)})

        cold.close()
        return results

    def get_unsynced_lance_records(self) -> list:
        """获取 LanceDB 中未同步到飞书的记录"""
        existing_hashes = set(self.state.get("synced_lancedb_hashes", []))
        all_records = self.lance._query_all()
        return [r for r in all_records if r.get("content_hash", "") not in existing_hashes]

    def mark_push_done(self):
        self.state["last_push_ts"] = time.time()
        save_sync_state(self.state)

    def mark_pull_done(self):
        self.state["last_pull_ts"] = time.time()
        save_sync_state(self.state)

# ===================== CLI 入口 =====================
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Elite L2 双向同步工具")
        print("Usage:")
        print("  elite_sync.py push                # LanceDB → 飞书")
        print("  elite_sync.py pull                # 飞书 → LanceDB")
        print("  elite_sync.py pull --with-cold   # 飞书 → LanceDB + L3冷存储")
        print("  elite_sync.py sync-cold           # LanceDB 全部 → L3冷存储（新机器恢复）")
        print("  elite_sync.py add <text> [layer] [source]  # 添加记忆并同步")
        print("  elite_sync.py search <query> [limit]       # 语义搜索")
        print("  elite_sync.py status              # 查看同步状态")
        sys.exit(0)

    cmd = sys.argv[1]
    sync = EliteSync()

    if cmd == "status":
        state = sync.state
        print(f"上次推送: {datetime.fromtimestamp(state.get('last_push_ts', 0)).strftime('%Y-%m-%d %H:%M:%S') if state.get('last_push_ts') else '从未'}")
        print(f"上次拉取: {datetime.fromtimestamp(state.get('last_pull_ts', 0)).strftime('%Y-%m-%d %H:%M:%S') if state.get('last_pull_ts') else '从未'}")
        print(f"已同步飞书记录数: {len(state.get('synced_feishu_ids', []))}")
        print(f"已同步LanceDB哈希数: {len(state.get('synced_lancedb_hashes', []))}")
        stats = sync.lance.get_records_since(0)
        print(f"LanceDB 总记录数: {len(stats)}")

    elif cmd == "push":
        unsynced = sync.get_unsynced_lance_records()
        if not unsynced:
            print("没有待推送的记录")
        else:
            push_records = sync.push_to_feishu(unsynced)
            print(f"准备推送 {len(push_records)} 条记录到飞书")
            # 输出 JSON 供外部脚本调用飞书 MCP 写入
            output = []
            for rec in push_records:
                fields = sync.feishu._make_fields_dict(rec)
                output.append({"fields": fields})
            print(json.dumps(output, ensure_ascii=False, indent=2))
            sync.mark_push_done()
            print(f"推送完成，{len(push_records)} 条记录已标记为已同步")

    elif cmd == "pull":
        with_cold = "--with-cold" in sys.argv
        if with_cold:
            print("拉取模式（含L3冷存储）：从飞书多维表格读取 → LanceDB → L3冷存储")
        else:
            print("拉取模式：从飞书多维表格读取待同步记录 → LanceDB")
        print(f"飞书 App Token: {FEISHU_APP_TOKEN}")
        print(f"飞书 Table ID: {FEISHU_TABLE_ID}")
        print(f"L3 冷存储: {'已启用' if with_cold else '未启用（加 --with-cold 启用）'}")
        print("请使用飞书 MCP 工具查询同步状态='待同步'的记录")

    elif cmd == "sync-cold":
        print("[L2→L3] 正在将 LanceDB 所有记录归档到 L3 冷存储...")
        results = sync.sync_l2_to_cold()
        if not results:
            print("[L2→L3] 没有需要归档的记录（可能已全部归档）")
        else:
            ok_count = sum(1 for r in results if "error" not in r)
            err_count = sum(1 for r in results if "error" in r)
            for r in results:
                if "error" in r:
                    print(f"  [错误] {r['text']}... → {r['error']}")
                else:
                    print(f"  [归档] {r['archive_id']} | [{r['layer']}] {r['text']}...")
            print(f"[L2→L3] 完成：成功 {ok_count} 条，失败 {err_count} 条")

    elif cmd == "add":
        if len(sys.argv) < 3:
            print("Usage: elite_sync.py add <text> [layer] [source]")
            sys.exit(1)
        text = sys.argv[2]
        layer = sys.argv[3] if len(sys.argv) > 3 else "L4"
        source = sys.argv[4] if len(sys.argv) > 4 else "cli"
        content_hash = sync.lance.add(text, layer=layer, source=source)
        print(f"已添加: [{layer}] {text[:50]}... (hash: {content_hash})")

    elif cmd == "search":
        if len(sys.argv) < 3:
            print("Usage: elite_sync.py search <query> [limit]")
            sys.exit(1)
        query = sys.argv[2]
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        results = sync.lance.search(query, limit)
        for i, r in enumerate(results):
            print(f"{i+1}. [{r.get('layer','?')}] {r.get('text','')[:60]}... (dist: {r.get('_distance',0):.4f})")

    else:
        print(f"未知命令: {cmd}")
