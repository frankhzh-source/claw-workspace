"""
Elite L2 Warm Store — LanceDB + Ollama 向量记忆服务
替代 OpenAI embedding，使用本地 Ollama/nomic-embed-text (768维)
"""
import json
import time
import lancedb
import httpx
from pathlib import Path

# === 配置 ===
OLLAMA_BASE = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"
LANCEDB_PATH = str(Path.home() / ".openclaw" / "memory" / "lancedb")
TABLE_NAME = "elite_memory"

# === Embedding ===
def embed(text: str) -> list[float]:
    """调用 Ollama 本地 embedding"""
    resp = httpx.post(
        f"{OLLAMA_BASE}/api/embed",
        json={"model": EMBED_MODEL, "input": text},
        timeout=60.0,
    )
    resp.raise_for_status()
    return resp.json()["embeddings"][0]

# === 核心操作 ===
class WarmStore:
    def __init__(self):
        self.db = lancedb.connect(LANCEDB_PATH)
        if TABLE_NAME in self.db.table_names():
            self.table = self.db.open_table(TABLE_NAME)
        else:
            self.table = None

    def _ensure_table(self):
        if self.table is None:
            # 创建空表（需要至少一条数据来推断 schema）
            self.table = self.db.create_table(TABLE_NAME, [
                {
                    "text": "__init__",
                    "vector": embed("__init__"),
                    "layer": "system",
                    "source": "auto",
                    "timestamp": time.time(),
                }
            ])

    def add(self, text: str, layer: str = "L4", source: str = "manual"):
        """写入一条记忆"""
        self._ensure_table()
        record = {
            "text": text,
            "vector": embed(text),
            "layer": layer,
            "source": source,
            "timestamp": time.time(),
        }
        self.table.add([record])

    def search(self, query: str, limit: int = 5, layer: str = None):
        """向量搜索记忆"""
        self._ensure_table()
        query_vec = embed(query)
        search = self.table.search(query_vec).limit(limit)
        if layer:
            search = search.where(f"layer = '{layer}'")
        return search.to_list()

    def stats(self):
        """返回存储统计"""
        tables = self.db.table_names()
        result = {"tables": tables}
        if TABLE_NAME in tables:
            t = self.db.open_table(TABLE_NAME)
            result["elite_memory_count"] = len(t)
        return result

# === CLI 入口 ===
if __name__ == "__main__":
    import sys
    store = WarmStore()

    if len(sys.argv) < 2:
        print("Usage: elite_warmstore.py [add|search|stats] [args...]")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "add":
        text = sys.argv[2]
        layer = sys.argv[3] if len(sys.argv) > 3 else "L4"
        source = sys.argv[4] if len(sys.argv) > 4 else "cli"
        store.add(text, layer, source)
        print(f"Added: [{layer}] {text[:50]}...")

    elif cmd == "search":
        query = sys.argv[2]
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        results = store.search(query, limit)
        for i, r in enumerate(results):
            print(f"{i+1}. [{r['layer']}] {r['text'][:60]}... (dist: {r['_distance']:.4f})")

    elif cmd == "stats":
        s = store.stats()
        print(json.dumps(s, indent=2))

    else:
        print(f"Unknown command: {cmd}")
