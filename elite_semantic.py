"""
Elite L5 Semantic Compression - 语义压缩记忆层
对长文本进行压缩、提取关键词/实体，降低存储开销、提升检索精度。

架构：
  SQLite + FTS5 压缩索引
  ├── semantic.db       -- 压缩记录库（压缩文本+关键词+实体+元数据）
  ├── semantic.json     -- 元信息（飞书同步状态、统计）
  └── snapshots/        -- 时间快照目录

与 Elite 架构的关系：
  L1(寄存器) -> L2(向量库) -> L3(冷存储) -> L4(文件记忆) -> L5(语义压缩)
                                                          |
                                                长文本 -> 压缩摘要+关键词+实体
                                                L5 <-> L2: 压缩文本向量化（语义搜索）
                                                L5 <-> 飞书: 压缩记录双向映射（L5-压缩）
                                                L3/L4 原文 -> L5 压缩（节省存储）

压缩引擎：
  extractive（默认）: 语句评分 + 关键词提取 + 实体识别
    - 按位置/关键词密度/实体密度评分句子
    - TF-based 关键词提取（中英文分词）
    - 正则实体识别（路径/ID/大写术语）
    - 保留 top-N 句子至目标压缩比

核心能力：
  add:            压缩并添加文本
  search:         全文搜索（FTS5+LIKE 双通道，中文友好）
  list:           按层级/方法/标签筛选
  info:           查看压缩记录详情
  decompress:     尝试从源层恢复原文
  auto-compress:  自动压缩 L2/L3/L4 中超长记录
  push:           L5 -> 飞书多维表格（压缩记录映射）
  pull:           飞书多维表格 -> L5（逆向恢复）
  sync-status:    飞书同步状态
  snapshot:       时间快照
  status:         统计概览
  log:            操作日志

CLI:
  python elite_semantic.py add <text> [--ratio 0.3] [--tags tag1,tag2]
  python elite_semantic.py search <query> [--limit 10]
  python elite_semantic.py list [--layer L3] [--method extractive] [--limit 20]
  python elite_semantic.py info <record_id>
  python elite_semantic.py decompress <record_id>
  python elite_semantic.py auto-compress [--min-length 200] [--ratio 0.3]
  python elite_semantic.py push [--all]
  python elite_semantic.py pull
  python elite_semantic.py sync-status
  python elite_semantic.py snapshot
  python elite_semantic.py status
  python elite_semantic.py log [--limit 20]
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
from collections import Counter

# ===================== 配置 =====================
SEM_DIR = str(Path.home() / ".openclaw" / "memory" / "semantic")
SEM_DB = str(Path(SEM_DIR) / "semantic.db")
SEM_META = str(Path(SEM_DIR) / "semantic.json")
SNAPSHOT_DIR = str(Path(SEM_DIR) / "snapshots")

# 飞书多维表格配置（与其他层共用同一张表，通过 记忆层级=L5-压缩 区分）
FEISHU_APP_TOKEN = "G56JbFHC0abrj2sdgIwcE9Cenn2"
FEISHU_TABLE_ID = "tblZxOCAmGAk84cJ"
FEISHU_FOLDER_ID = "ERi3fwcAql5qKhdNpKacpyhXnih"

# 中文停用词
STOP_WORDS = set(
    "的 了 是 在 我 有 和 就 不 人 都 一 一个 上 也 很 到 说 要 去 你 会 着 没有 看 好 "
    "自己 这 他 她 它 们 那 些 什么 怎么 这个 那个 还 就是 可以 没 能 被 从 把 而 与 "
    "但 如果 因为 所以 所 或者 然后 这些 那些 已经 之 其 中 等 及 对 将 可能 更 需 "
    "其中 不过 然而 因此 虽然 此 该 每 当 为 以 于 及 各 该 本 此 其".split()
)

# 默认压缩比
DEFAULT_RATIO = 0.3
# 最低可压缩长度
MIN_COMPRESS_LENGTH = 100


# ===================== 压缩引擎 =====================

def segment_sentences(text: str) -> list:
    """中英文分句"""
    # 按中英文句号/问号/感叹号/分号/换行切分
    parts = re.split(r'(?<=[。！？；\n])', text)
    sentences = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        # 英文句号后切分
        sub = re.split(r'(?<=[.!?])\s+', p)
        for s in sub:
            s = s.strip()
            if s and len(s) > 3:  # 过滤过短片段
                sentences.append(s)
    return sentences


def extract_keywords(text: str, top_n: int = 10) -> list:
    """TF 关键词提取（中英文）"""
    # 中文：连续2+汉字为词
    cn_phrases = re.findall(r'[\u4e00-\u9fff]{2,6}', text)
    # 英文：3+字母
    en_words = re.findall(r'[a-zA-Z]{3,}', text.lower())

    cn_counter = Counter(w for w in cn_phrases if w not in STOP_WORDS and len(w) >= 2)
    en_counter = Counter(w for w in en_words if w not in STOP_WORDS and len(w) > 3)

    all_terms = cn_counter + en_counter
    return [term for term, _ in all_terms.most_common(top_n)]


def extract_entities(text: str) -> list:
    """简单实体识别"""
    entities = []
    # 英文大写开头词（非句首）
    cap_words = re.findall(r'(?<=[.!?。！？\s\n])[A-Z][a-zA-Z]{2,}', text)
    entities.extend(cap_words[:5])
    # 路径
    paths = re.findall(r'[A-Z]:\\[\\\\\w\-\.]+|~/[\w/\-\.]+|/[\w/\-\.]{5,}', text)
    entities.extend(paths[:3])
    # 长ID
    ids = re.findall(r'[a-zA-Z0-9]{20,}', text)
    entities.extend(ids[:3])
    # 中文人名/术语（大写英文字母+中文混合）
    tech_terms = re.findall(r'[A-Z][a-zA-Z]*[\u4e00-\u9fff]+', text)
    entities.extend(tech_terms[:3])

    return list(dict.fromkeys(entities))[:10]  # 去重保序


def compress_text(text: str, ratio: float = DEFAULT_RATIO) -> dict:
    """核心压缩引擎：extractive 压缩

    返回:
        {
            "compressed": str,        压缩后文本
            "keywords": list,         关键词
            "entities": list,         实体
            "ratio": float,           实际压缩比
            "original_length": int,
            "compressed_length": int,
            "method": "extractive",
        }
    """
    original_len = len(text)
    if original_len < MIN_COMPRESS_LENGTH:
        return {
            "compressed": text,
            "keywords": extract_keywords(text, 5),
            "entities": extract_entities(text),
            "ratio": 1.0,
            "original_length": original_len,
            "compressed_length": original_len,
            "method": "extractive",
        }

    sentences = segment_sentences(text)
    if len(sentences) <= 2:
        return {
            "compressed": text,
            "keywords": extract_keywords(text, 10),
            "entities": extract_entities(text),
            "ratio": 1.0,
            "original_length": original_len,
            "compressed_length": original_len,
            "method": "extractive",
        }

    keywords = extract_keywords(text, 10)
    entities = extract_entities(text)

    # 句子评分
    target_count = max(1, int(len(sentences) * ratio))
    scored = []
    for i, s in enumerate(sentences):
        score = 0.0
        # 位置分：首句最重，尾句次之，前20%加成
        if i == 0:
            score += 3.0
        elif i == len(sentences) - 1:
            score += 2.0
        elif i < len(sentences) * 0.2:
            score += 1.5
        # 关键词密度
        s_lower = s.lower()
        for kw in keywords[:5]:
            if kw.lower() in s_lower:
                score += 1.0
        # 实体密度
        for ent in entities:
            if ent in s:
                score += 1.5
        # 长度偏好：中等长度句子
        slen = len(s)
        if 20 < slen < 200:
            score += 0.5
        scored.append((i, s, score))

    # 选 top-N 句子，按原文顺序重组
    scored.sort(key=lambda x: -x[2])
    selected = sorted(scored[:target_count], key=lambda x: x[0])

    compressed = "".join(s[1] for s in selected)
    actual_ratio = len(compressed) / original_len if original_len > 0 else 1.0

    return {
        "compressed": compressed,
        "keywords": keywords,
        "entities": entities,
        "ratio": actual_ratio,
        "original_length": original_len,
        "compressed_length": len(compressed),
        "method": "extractive",
    }


# ===================== 数据库层 =====================

def _init_db(conn: sqlite3.Connection):
    """创建表结构（幂等）"""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS compressed (
            id TEXT PRIMARY KEY,
            compressed_text TEXT NOT NULL,
            keywords TEXT DEFAULT '[]',
            entities TEXT DEFAULT '[]',
            compression_ratio REAL DEFAULT 0.0,
            method TEXT DEFAULT 'extractive',
            original_length INTEGER DEFAULT 0,
            compressed_length INTEGER DEFAULT 0,
            original_id TEXT DEFAULT '',
            original_layer TEXT DEFAULT '',
            original_hash TEXT DEFAULT '',
            content_hash TEXT DEFAULT '',
            created_at REAL NOT NULL,
            last_accessed REAL DEFAULT 0,
            tags TEXT DEFAULT '[]',
            status TEXT DEFAULT 'active',
            feishu_id TEXT DEFAULT '',
            source TEXT DEFAULT 'manual'
        );

        CREATE TABLE IF NOT EXISTS semantic_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            record_id TEXT DEFAULT '',
            details TEXT DEFAULT '',
            timestamp REAL NOT NULL
        );
    """)

    # FTS5（unicode61 tokenizer，配合单字 OR 做中文搜索）
    try:
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS compressed_fts
            USING fts5(compressed_text, keywords, entities,
                       content=compressed, content_rowid=rowid,
                       tokenize='unicode61')
        """)
    except sqlite3.OperationalError:
        pass  # 已存在

    # FTS 同步 trigger
    conn.executescript("""
        CREATE TRIGGER IF NOT EXISTS compressed_ai AFTER INSERT ON compressed
        BEGIN
            INSERT INTO compressed_fts(rowid, compressed_text, keywords, entities)
            VALUES (new.rowid, new.compressed_text, new.keywords, new.entities);
        END;

        CREATE TRIGGER IF NOT EXISTS compressed_ad AFTER DELETE ON compressed
        BEGIN
            INSERT INTO compressed_fts(compressed_fts, rowid, compressed_text, keywords, entities)
            VALUES ('delete', old.rowid, old.compressed_text, old.keywords, old.entities);
        END;

        CREATE TRIGGER IF NOT EXISTS compressed_au AFTER UPDATE ON compressed
        BEGIN
            INSERT INTO compressed_fts(compressed_fts, rowid, compressed_text, keywords, entities)
            VALUES ('delete', old.rowid, old.compressed_text, old.keywords, old.entities);
            INSERT INTO compressed_fts(rowid, compressed_text, keywords, entities)
            VALUES (new.rowid, new.compressed_text, new.keywords, new.entities);
        END;
    """)

    conn.commit()


# ===================== SemanticStore 类 =====================

class SemanticStore:
    def __init__(self):
        os.makedirs(SEM_DIR, exist_ok=True)
        os.makedirs(SNAPSHOT_DIR, exist_ok=True)
        self.conn = sqlite3.connect(SEM_DB)
        self.conn.row_factory = sqlite3.Row
        _init_db(self.conn)
        self._meta = self._load_meta()

    # ---------- 元信息 ----------
    def _load_meta(self) -> dict:
        if os.path.exists(SEM_META):
            with open(SEM_META, encoding="utf-8") as f:
                return json.load(f)
        return {
            "feishu_sync": {
                "synced_hashes": [],
                "synced_feishu_ids": [],
                "last_push_ts": 0,
                "last_pull_ts": 0,
            }
        }

    def _save_meta(self):
        with open(SEM_META, "w", encoding="utf-8") as f:
            json.dump(self._meta, f, ensure_ascii=False, indent=2)

    # ---------- 日志 ----------
    def _log(self, action: str, record_id: str = "", details: str = ""):
        self.conn.execute(
            "INSERT INTO semantic_log (action, record_id, details, timestamp) VALUES (?, ?, ?, ?)",
            (action, record_id, details, time.time()),
        )
        self.conn.commit()

    # ---------- 工具 ----------
    @staticmethod
    def _content_hash(text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()[:12]

    @staticmethod
    def _make_fts_query(query: str) -> str:
        """中文单字 OR + 英文原词"""
        parts = []
        for ch in query:
            if "\u4e00" <= ch <= "\u9fff":
                parts.append(f'"{ch}"')
            elif ch.isalnum():
                parts.append(ch)
        if not parts:
            return f'"{query}"'
        return " OR ".join(parts)

    # ---------- 核心：压缩+添加 ----------
    def add(
        self,
        text: str,
        ratio: float = DEFAULT_RATIO,
        method: str = "extractive",
        original_id: str = "",
        original_layer: str = "",
        original_hash: str = "",
        tags: list = None,
        source: str = "manual",
    ) -> dict:
        """压缩文本并存储，返回记录信息"""
        tags = tags or []
        content_hash = self._content_hash(text)

        # 去重
        existing = self.conn.execute(
            "SELECT id FROM compressed WHERE content_hash = ?", (content_hash,)
        ).fetchone()
        if existing:
            return {"status": "dup", "id": existing["id"], "hash": content_hash}

        # 压缩
        result = compress_text(text, ratio)

        record_id = f"L5-{int(time.time())}-{content_hash}"
        now = time.time()

        self.conn.execute(
            """INSERT INTO compressed
            (id, compressed_text, keywords, entities, compression_ratio, method,
             original_length, compressed_length, original_id, original_layer,
             original_hash, content_hash, created_at, last_accessed, tags,
             status, feishu_id, source)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                record_id,
                result["compressed"],
                json.dumps(result["keywords"], ensure_ascii=False),
                json.dumps(result["entities"], ensure_ascii=False),
                result["ratio"],
                result["method"],
                result["original_length"],
                result["compressed_length"],
                original_id,
                original_layer,
                original_hash,
                content_hash,
                now,
                now,
                json.dumps(tags, ensure_ascii=False),
                "active",
                "",
                source,
            ),
        )
        self.conn.commit()
        self._log("add", record_id, f"ratio={result['ratio']:.2f} method={method}")

        return {
            "status": "ok",
            "id": record_id,
            "original_length": result["original_length"],
            "compressed_length": result["compressed_length"],
            "ratio": result["ratio"],
            "keywords": result["keywords"],
            "entities": result["entities"],
        }

    # ---------- 搜索 ----------
    def search(self, query: str, limit: int = 10) -> list:
        """FTS5 + LIKE 双通道搜索"""
        results = []
        seen = set()

        # FTS5
        fts_q = self._make_fts_query(query)
        try:
            rows = self.conn.execute(
                """SELECT * FROM compressed
                WHERE id IN (SELECT id FROM compressed_fts WHERE compressed_fts MATCH ?)
                AND status = 'active' ORDER BY last_accessed DESC LIMIT ?""",
                (fts_q, limit),
            ).fetchall()
            for r in rows:
                rd = dict(r)
                if rd["id"] not in seen:
                    seen.add(rd["id"])
                    results.append(rd)
        except sqlite3.OperationalError:
            pass

        # LIKE 兜底
        try:
            rows = self.conn.execute(
                """SELECT * FROM compressed
                WHERE (compressed_text LIKE ? OR keywords LIKE ? OR entities LIKE ?)
                AND status = 'active' ORDER BY last_accessed DESC LIMIT ?""",
                (f"%{query}%", f"%{query}%", f"%{query}%", limit),
            ).fetchall()
            for r in rows:
                rd = dict(r)
                if rd["id"] not in seen:
                    seen.add(rd["id"])
                    results.append(rd)
        except sqlite3.OperationalError:
            pass

        return results

    # ---------- 列表 ----------
    def list_records(
        self,
        layer: str = "",
        method: str = "",
        status: str = "active",
        tag: str = "",
        limit: int = 20,
    ) -> list:
        sql = "SELECT * FROM compressed WHERE 1=1"
        params = []
        if status:
            sql += " AND status = ?"
            params.append(status)
        if layer:
            sql += " AND original_layer = ?"
            params.append(layer)
        if method:
            sql += " AND method = ?"
            params.append(method)
        if tag:
            sql += " AND tags LIKE ?"
            params.append(f'%"{tag}"%')
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    # ---------- 详情 ----------
    def info(self, record_id: str) -> dict:
        row = self.conn.execute(
            "SELECT * FROM compressed WHERE id = ?", (record_id,)
        ).fetchone()
        if not row:
            return {"status": "error", "message": f"Not found: {record_id}"}
        # 更新访问时间
        self.conn.execute(
            "UPDATE compressed SET last_accessed = ? WHERE id = ?",
            (time.time(), record_id),
        )
        self.conn.commit()
        return dict(row)

    # ---------- 解压缩（从源层恢复原文） ----------
    def decompress(self, record_id: str) -> dict:
        """尝试从源层恢复原文"""
        row = self.conn.execute(
            "SELECT * FROM compressed WHERE id = ?", (record_id,)
        ).fetchone()
        if not row:
            return {"status": "error", "message": f"Not found: {record_id}"}

        original_layer = row["original_layer"]
        original_id = row["original_id"]
        original_text = None

        # L3 冷存储
        if original_layer in ("L3", "L2") and original_id:
            cs_path = str(Path.home() / ".openclaw" / "memory" / "coldstore" / "coldstore.db")
            if os.path.exists(cs_path):
                try:
                    conn2 = sqlite3.connect(cs_path)
                    conn2.row_factory = sqlite3.Row
                    r = conn2.execute("SELECT text FROM archive WHERE id = ?", (original_id,)).fetchone()
                    if r:
                        original_text = r["text"]
                    conn2.close()
                except Exception:
                    pass

        # L4 文件记忆
        if original_layer == "L4" and original_id:
            fs_path = str(Path.home() / ".openclaw" / "memory" / "filestore" / "filestore.db")
            if os.path.exists(fs_path):
                try:
                    conn2 = sqlite3.connect(fs_path)
                    conn2.row_factory = sqlite3.Row
                    r = conn2.execute("SELECT description FROM files WHERE id = ?", (original_id,)).fetchone()
                    if r and r["description"]:
                        original_text = r["description"]
                    conn2.close()
                except Exception:
                    pass

        # L2 向量库
        if original_layer == "L2" and original_id:
            try:
                import lancedb
                db = lancedb.connect(str(Path.home() / ".openclaw" / "memory" / "lancedb"))
                tbl = db.open_table("elite_memory")
                data = tbl.head(200).to_pydict()
                for i in range(len(data.get("id", []))):
                    if data["id"][i] == original_id:
                        original_text = data["text"][i]
                        break
            except Exception:
                pass

        return {
            "status": "ok",
            "id": record_id,
            "original_layer": original_layer,
            "original_id": original_id,
            "original_text": original_text,
            "compressed_text": row["compressed_text"],
            "has_original": original_text is not None,
        }

    # ---------- 自动压缩 ----------
    def auto_compress(self, min_length: int = 200, ratio: float = DEFAULT_RATIO) -> list:
        """从 L2/L3/L4 自动压缩超长记录"""
        results = []

        # ---- L3 ----
        cs_path = str(Path.home() / ".openclaw" / "memory" / "coldstore" / "coldstore.db")
        if os.path.exists(cs_path):
            try:
                conn2 = sqlite3.connect(cs_path)
                conn2.row_factory = sqlite3.Row
                rows = conn2.execute(
                    "SELECT id, text, layer, content_hash FROM archive WHERE length(text) > ?",
                    (min_length,),
                ).fetchall()
                for r in rows:
                    res = self.add(
                        r["text"],
                        original_id=r["id"],
                        original_layer=r["layer"] or "L3",
                        original_hash=r["content_hash"],
                        ratio=ratio,
                        source=f"auto:L3",
                    )
                    results.append(res)
                conn2.close()
            except Exception as e:
                results.append({"status": "error", "source": "L3", "message": str(e)})

        # ---- L4 ----
        fs_path = str(Path.home() / ".openclaw" / "memory" / "filestore" / "filestore.db")
        if os.path.exists(fs_path):
            try:
                conn2 = sqlite3.connect(fs_path)
                conn2.row_factory = sqlite3.Row
                rows = conn2.execute(
                    "SELECT id, description, content_hash FROM files WHERE length(description) > ? AND description != ''",
                    (min_length,),
                ).fetchall()
                for r in rows:
                    res = self.add(
                        r["description"],
                        original_id=r["id"],
                        original_layer="L4",
                        original_hash=r["content_hash"],
                        ratio=ratio,
                        source="auto:L4",
                    )
                    results.append(res)
                conn2.close()
            except Exception as e:
                results.append({"status": "error", "source": "L4", "message": str(e)})

        # ---- L2 ----
        try:
            import lancedb
            db = lancedb.connect(str(Path.home() / ".openclaw" / "memory" / "lancedb"))
            tbl = db.open_table("elite_memory")
            data = tbl.head(200).to_pydict()
            for i in range(len(data.get("text", []))):
                text_val = data["text"][i]
                if len(text_val) > min_length:
                    res = self.add(
                        text_val,
                        original_id=data.get("id", [""])[i],
                        original_layer=data.get("layer", [""])[i],
                        original_hash=data.get("content_hash", [""])[i],
                        ratio=ratio,
                        source="auto:L2",
                    )
                    results.append(res)
        except Exception as e:
            results.append({"status": "error", "source": "L2", "message": str(e)})

        added = sum(1 for r in results if r.get("status") == "ok")
        dups = sum(1 for r in results if r.get("status") == "dup")
        errors = sum(1 for r in results if r.get("status") == "error")
        self._log("auto_compress", "", f"added={added} dup={dups} errors={errors}")

        return results

    # ---------- L5 <-> 飞书映射 ----------

    def _make_feishu_text(self, row: dict) -> str:
        """压缩记录 -> 飞书记忆文本"""
        kw = json.loads(row.get("keywords", "[]"))
        ent = json.loads(row.get("entities", "[]"))
        tags = json.loads(row.get("tags", "[]"))

        parts = [
            row["compressed_text"],
            "[L5-压缩]",
            f"关键词: {', '.join(kw)}",
            f"实体: {', '.join(ent)}",
            f"压缩比: {row['compression_ratio']:.1%}",
            f"方法: {row['method']}",
            f"原文层: {row['original_layer']}",
            f"原文ID: {row['original_id']}",
            f"原文哈希: {row['original_hash']}",
            f"原文长度: {row['original_length']}",
            f"压缩长度: {row['compressed_length']}",
        ]
        if tags:
            parts.append(f"标签: {', '.join(tags)}")
        return "\n".join(parts)

    @staticmethod
    def _parse_feishu_text(text: str) -> dict:
        """飞书文本 -> 压缩记录字段"""
        lines = text.strip().split("\n")
        result = {
            "compressed_text": "",
            "keywords": [],
            "entities": [],
            "compression_ratio": 0.0,
            "method": "extractive",
            "original_layer": "",
            "original_id": "",
            "original_hash": "",
            "original_length": 0,
            "compressed_length": 0,
            "tags": [],
        }

        # 找到元数据开始位置
        meta_start = -1
        for i, line in enumerate(lines):
            if "[L5-压缩]" in line or "[L5]" in line:
                meta_start = i
                break

        if meta_start >= 0:
            result["compressed_text"] = "\n".join(lines[:meta_start]).strip()
            for line in lines[meta_start + 1 :]:
                if line.startswith("关键词:"):
                    result["keywords"] = [
                        k.strip() for k in line.split(":", 1)[1].split(",") if k.strip()
                    ]
                elif line.startswith("实体:"):
                    result["entities"] = [
                        e.strip() for e in line.split(":", 1)[1].split(",") if e.strip()
                    ]
                elif line.startswith("压缩比:"):
                    try:
                        val = line.split(":", 1)[1].strip().rstrip("%")
                        result["compression_ratio"] = float(val) / 100
                    except ValueError:
                        pass
                elif line.startswith("方法:"):
                    result["method"] = line.split(":", 1)[1].strip()
                elif line.startswith("原文层:"):
                    result["original_layer"] = line.split(":", 1)[1].strip()
                elif line.startswith("原文ID:"):
                    result["original_id"] = line.split(":", 1)[1].strip()
                elif line.startswith("原文哈希:"):
                    result["original_hash"] = line.split(":", 1)[1].strip()
                elif line.startswith("原文长度:"):
                    try:
                        result["original_length"] = int(line.split(":", 1)[1].strip())
                    except ValueError:
                        pass
                elif line.startswith("压缩长度:"):
                    try:
                        result["compressed_length"] = int(line.split(":", 1)[1].strip())
                    except ValueError:
                        pass
                elif line.startswith("标签:"):
                    result["tags"] = [
                        t.strip() for t in line.split(":", 1)[1].split(",") if t.strip()
                    ]
        else:
            # 无元数据标记，整个文本作为压缩文本
            result["compressed_text"] = text.strip()

        return result

    def push_to_feishu(self, push_all: bool = False) -> list:
        """L5 -> 飞书：准备推送数据（由 AI agent 调用 MCP 工具实际写入）

        返回待推送记录列表，每条含:
          text, layer, source, timestamp, lancedb_id, sync_status, content_hash, record_id
        """
        synced_hashes = set(
            self._meta.get("feishu_sync", {}).get("synced_hashes", [])
        )

        if push_all:
            rows = self.conn.execute(
                "SELECT * FROM compressed WHERE status = 'active'"
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM compressed WHERE status = 'active' AND feishu_id = ''"
            ).fetchall()

        results = []
        for row in rows:
            rd = dict(row)
            ch = rd["content_hash"]
            if not push_all and ch in synced_hashes:
                continue

            text = self._make_feishu_text(rd)
            results.append(
                {
                    "text": text,
                    "layer": "L5-压缩",
                    "source": rd.get("source", "manual"),
                    "timestamp": rd.get("created_at", time.time()),
                    "lancedb_id": rd["id"],
                    "sync_status": "已同步",
                    "content_hash": ch,
                    "record_id": rd["id"],
                }
            )

        # 更新同步元信息
        all_synced = list(synced_hashes | {r["content_hash"] for r in results})
        if "feishu_sync" not in self._meta:
            self._meta["feishu_sync"] = {}
        self._meta["feishu_sync"]["synced_hashes"] = all_synced
        self._meta["feishu_sync"]["last_push_ts"] = time.time()
        self._save_meta()

        return results

    def pull_from_feishu(self, feishu_records: list) -> list:
        """飞书 -> L5：从飞书拉取 L5-压缩 记录，写入本地

        feishu_records: 飞书 MCP 查询结果列表
          每条需含: text, layer, feishu_id, source
        """
        results = []
        synced_ids = set(
            self._meta.get("feishu_sync", {}).get("synced_feishu_ids", [])
        )

        for rec in feishu_records:
            layer = rec.get("layer", "")
            if layer not in ("L5-压缩", "L5"):
                continue

            feishu_id = rec.get("feishu_id", "")
            if feishu_id and feishu_id in synced_ids:
                continue

            text = rec.get("text", "")
            if not text:
                continue

            parsed = self._parse_feishu_text(text)
            content_hash = self._content_hash(parsed["compressed_text"])

            # 去重
            existing = self.conn.execute(
                "SELECT id FROM compressed WHERE content_hash = ?", (content_hash,)
            ).fetchone()
            if existing:
                # 更新 feishu_id
                self.conn.execute(
                    "UPDATE compressed SET feishu_id = ? WHERE id = ?",
                    (feishu_id, existing["id"]),
                )
                results.append(
                    {
                        "status": "exists",
                        "record_id": existing["id"],
                        "feishu_id": feishu_id,
                    }
                )
            else:
                record_id = f"L5-{int(time.time())}-{content_hash}"
                now = time.time()
                self.conn.execute(
                    """INSERT INTO compressed
                    (id, compressed_text, keywords, entities, compression_ratio, method,
                     original_length, compressed_length, original_id, original_layer,
                     original_hash, content_hash, created_at, last_accessed, tags,
                     status, feishu_id, source)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        record_id,
                        parsed["compressed_text"],
                        json.dumps(parsed["keywords"], ensure_ascii=False),
                        json.dumps(parsed["entities"], ensure_ascii=False),
                        parsed["compression_ratio"],
                        parsed["method"],
                        parsed["original_length"],
                        parsed["compressed_length"],
                        parsed["original_id"],
                        parsed["original_layer"],
                        parsed["original_hash"],
                        content_hash,
                        now,
                        now,
                        json.dumps(parsed["tags"], ensure_ascii=False),
                        "active",
                        feishu_id,
                        "feishu_pull",
                    ),
                )
                results.append(
                    {
                        "status": "pulled",
                        "record_id": record_id,
                        "feishu_id": feishu_id,
                    }
                )

            if feishu_id:
                synced_ids.add(feishu_id)

        # 更新同步状态
        if "feishu_sync" not in self._meta:
            self._meta["feishu_sync"] = {}
        self._meta["feishu_sync"]["synced_feishu_ids"] = list(synced_ids)
        self._meta["feishu_sync"]["last_pull_ts"] = time.time()
        self.conn.commit()
        self._save_meta()

        return results

    def update_feishu_id(self, record_id: str, feishu_id: str):
        """写入飞书返回的 record_id，建立双向映射"""
        self.conn.execute(
            "UPDATE compressed SET feishu_id = ? WHERE id = ?", (feishu_id, record_id)
        )
        self.conn.commit()
        if feishu_id:
            ids = self._meta.get("feishu_sync", {}).get("synced_feishu_ids", [])
            if feishu_id not in ids:
                ids.append(feishu_id)
            if "feishu_sync" not in self._meta:
                self._meta["feishu_sync"] = {}
            self._meta["feishu_sync"]["synced_feishu_ids"] = ids
            self._save_meta()

    def get_sync_status(self) -> dict:
        sync = self._meta.get("feishu_sync", {})
        total = self.conn.execute(
            "SELECT COUNT(*) as c FROM compressed WHERE status = 'active'"
        ).fetchone()["c"]
        synced = self.conn.execute(
            "SELECT COUNT(*) as c FROM compressed WHERE status = 'active' AND feishu_id != ''"
        ).fetchone()["c"]

        return {
            "total_records": total,
            "synced_to_feishu": synced,
            "unsynced": total - synced,
            "synced_hashes": len(sync.get("synced_hashes", [])),
            "feishu_ids": len(sync.get("synced_feishu_ids", [])),
            "last_push": datetime.fromtimestamp(sync.get("last_push_ts", 0)).strftime(
                "%Y-%m-%d %H:%M"
            )
            if sync.get("last_push_ts")
            else "从未",
            "last_pull": datetime.fromtimestamp(sync.get("last_pull_ts", 0)).strftime(
                "%Y-%m-%d %H:%M"
            )
            if sync.get("last_pull_ts")
            else "从未",
            "feishu_app_token": FEISHU_APP_TOKEN,
            "feishu_table_id": FEISHU_TABLE_ID,
        }

    # ---------- 快照 ----------
    def snapshot(self, label: str = "") -> str:
        records = self.list_records(status="", limit=10000)
        log_rows = self.conn.execute(
            "SELECT * FROM semantic_log ORDER BY id DESC LIMIT 100"
        ).fetchall()

        snap = {
            "timestamp": time.time(),
            "label": label or f"snapshot-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            "records_count": len(records),
            "log_count": len(log_rows),
            "records": records,
            "log": [dict(r) for r in log_rows],
            "meta": self._meta,
        }

        filename = f"snap-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        filepath = Path(SNAPSHOT_DIR) / filename
        filepath.write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")

        self._log("snapshot", "", f"path={filepath}")
        return str(filepath)

    # ---------- 统计 ----------
    def status(self) -> dict:
        total = self.conn.execute("SELECT COUNT(*) as c FROM compressed").fetchone()["c"]
        active = self.conn.execute(
            "SELECT COUNT(*) as c FROM compressed WHERE status = 'active'"
        ).fetchone()["c"]
        avg_ratio = self.conn.execute(
            "SELECT AVG(compression_ratio) as r FROM compressed WHERE status = 'active'"
        ).fetchone()["r"] or 0

        methods = {}
        for r in self.conn.execute(
            "SELECT method, COUNT(*) as c FROM compressed GROUP BY method"
        ).fetchall():
            methods[r["method"]] = r["c"]

        layers = {}
        for r in self.conn.execute(
            "SELECT original_layer, COUNT(*) as c FROM compressed GROUP BY original_layer"
        ).fetchall():
            layers[r["original_layer"]] = r["c"]

        db_size = os.path.getsize(SEM_DB) / 1024 if os.path.exists(SEM_DB) else 0

        return {
            "total": total,
            "active": active,
            "avg_ratio": round(avg_ratio, 3),
            "methods": methods,
            "source_layers": layers,
            "db_size_kb": round(db_size, 1),
            "db_path": SEM_DB,
        }

    # ---------- 日志 ----------
    def get_log(self, limit: int = 20) -> list:
        rows = self.conn.execute(
            "SELECT * FROM semantic_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self):
        self.conn.close()


# ===================== CLI =====================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    store = SemanticStore()
    cmd = sys.argv[1]

    try:
        if cmd == "add":
            if len(sys.argv) < 3:
                print("Usage: elite_semantic.py add <text> [--ratio 0.3] [--tags t1,t2]")
                sys.exit(1)
            text = sys.argv[2]
            ratio = DEFAULT_RATIO
            tags = []
            original_id = ""
            original_layer = ""
            if "--ratio" in sys.argv:
                ratio = float(sys.argv[sys.argv.index("--ratio") + 1])
            if "--tags" in sys.argv:
                tags = sys.argv[sys.argv.index("--tags") + 1].split(",")
            if "--original-id" in sys.argv:
                original_id = sys.argv[sys.argv.index("--original-id") + 1]
            if "--original-layer" in sys.argv:
                original_layer = sys.argv[sys.argv.index("--original-layer") + 1]

            result = store.add(text, ratio=ratio, tags=tags,
                             original_id=original_id, original_layer=original_layer)
            if result["status"] == "dup":
                print(f"[L5] Duplicate: {result['id']} (hash={result['hash']})")
            else:
                print(f"[L5] Compressed: {result['id']}")
                print(f"  Original: {result['original_length']} chars -> Compressed: {result['compressed_length']} chars ({result['ratio']:.1%})")
                print(f"  Keywords: {', '.join(result['keywords'][:5])}")
                print(f"  Entities: {', '.join(result['entities'][:3])}")

        elif cmd == "search":
            if len(sys.argv) < 3:
                print("Usage: elite_semantic.py search <query> [--limit 10]")
                sys.exit(1)
            query = sys.argv[2]
            limit = 10
            if "--limit" in sys.argv:
                limit = int(sys.argv[sys.argv.index("--limit") + 1])
            results = store.search(query, limit)
            if not results:
                print(f"[L5] No results for: {query}")
            else:
                print(f"[L5] Found {len(results)} results for: {query}")
                for r in results:
                    kw = json.loads(r.get("keywords", "[]"))
                    print(f"  {r['id']} | {r['compressed_text'][:50]}... | kw: {', '.join(kw[:3])}")

        elif cmd == "list":
            layer = ""
            method = ""
            status = "active"
            limit = 20
            if "--layer" in sys.argv:
                layer = sys.argv[sys.argv.index("--layer") + 1]
            if "--method" in sys.argv:
                method = sys.argv[sys.argv.index("--method") + 1]
            if "--status" in sys.argv:
                status = sys.argv[sys.argv.index("--status") + 1]
            if "--limit" in sys.argv:
                limit = int(sys.argv[sys.argv.index("--limit") + 1])
            records = store.list_records(layer=layer, method=method, status=status, limit=limit)
            if not records:
                print("[L5] No records")
            else:
                print(f"[L5] {len(records)} records:")
                for r in records:
                    kw = json.loads(r.get("keywords", "[]"))
                    kw_str = ", ".join(kw[:3]) if kw else ""
                    print(f"  {r['id']} | layer={r['original_layer']} | ratio={r['compression_ratio']:.1%} | {r['compressed_text'][:40]}...")
                    if kw_str:
                        print(f"    kw: {kw_str}")

        elif cmd == "info":
            if len(sys.argv) < 3:
                print("Usage: elite_semantic.py info <record_id>")
                sys.exit(1)
            info = store.info(sys.argv[2])
            if info.get("status") == "error":
                print(f"[L5] {info['message']}")
            else:
                kw = json.loads(info.get("keywords", "[]"))
                ent = json.loads(info.get("entities", "[]"))
                tags = json.loads(info.get("tags", "[]"))
                print(f"ID: {info['id']}")
                print(f"Original layer: {info['original_layer']}")
                print(f"Original ID: {info['original_id']}")
                print(f"Original hash: {info['original_hash']}")
                print(f"Method: {info['method']}")
                print(f"Compression: {info['original_length']} -> {info['compressed_length']} ({info['compression_ratio']:.1%})")
                print(f"Keywords: {', '.join(kw)}")
                print(f"Entities: {', '.join(ent)}")
                print(f"Tags: {', '.join(tags)}")
                print(f"Feishu ID: {info['feishu_id'] or '(not synced)'}")
                print(f"Source: {info['source']}")
                print(f"Created: {datetime.fromtimestamp(info['created_at']).strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"\nCompressed text:")
                print(info["compressed_text"])

        elif cmd == "decompress":
            if len(sys.argv) < 3:
                print("Usage: elite_semantic.py decompress <record_id>")
                sys.exit(1)
            result = store.decompress(sys.argv[2])
            if result.get("status") == "error":
                print(f"[L5] {result['message']}")
            elif result.get("has_original"):
                print(f"[L5] Original from {result['original_layer']} ({len(result['original_text'])} chars):")
                print(result["original_text"])
            else:
                print(f"[L5] Original not found. Compressed text only:")
                print(result["compressed_text"])

        elif cmd == "auto-compress":
            min_len = 200
            ratio = DEFAULT_RATIO
            if "--min-length" in sys.argv:
                min_len = int(sys.argv[sys.argv.index("--min-length") + 1])
            if "--ratio" in sys.argv:
                ratio = float(sys.argv[sys.argv.index("--ratio") + 1])
            results = store.auto_compress(min_len, ratio)
            added = sum(1 for r in results if r.get("status") == "ok")
            dups = sum(1 for r in results if r.get("status") == "dup")
            errors = sum(1 for r in results if r.get("status") == "error")
            print(f"[L5] Auto-compress done: added={added} dup={dups} errors={errors}")
            for r in results:
                if r.get("status") == "ok":
                    print(f"  + {r['id']} | {r['original_length']} -> {r['compressed_length']} ({r['ratio']:.1%})")

        elif cmd == "push":
            push_all = "--all" in sys.argv
            results = store.push_to_feishu(push_all)
            if not results:
                print("[L5] No records to push")
            else:
                print(f"[L5] Prepared {len(results)} records for Feishu push:")
                for r in results:
                    print(f"  {r['record_id']} | {r['content_hash']} | layer={r['layer']}")

        elif cmd == "pull":
            print("[L5] Pull requires Feishu records input via agent. Use MCP tools to query, then pass results.")

        elif cmd == "sync-status":
            status = store.get_sync_status()
            print(f"[L5] Feishu Sync Status:")
            print(f"  Total: {status['total_records']}")
            print(f"  Synced: {status['synced_to_feishu']}")
            print(f"  Unsynced: {status['unsynced']}")
            print(f"  Last push: {status['last_push']}")
            print(f"  Last pull: {status['last_pull']}")

        elif cmd == "snapshot":
            path = store.snapshot()
            print(f"[L5] Snapshot: {path}")

        elif cmd == "status":
            st = store.status()
            print(f"[L5] Semantic Compression Status:")
            print(f"  Total: {st['total']} | Active: {st['active']}")
            print(f"  Avg compression ratio: {st['avg_ratio']:.1%}")
            print(f"  Methods: {st['methods']}")
            print(f"  Source layers: {st['source_layers']}")
            print(f"  DB: {st['db_size_kb']} KB at {st['db_path']}")

        elif cmd == "log":
            limit = 20
            if "--limit" in sys.argv:
                limit = int(sys.argv[sys.argv.index("--limit") + 1])
            entries = store.get_log(limit)
            for e in entries:
                ts = datetime.fromtimestamp(e["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
                print(f"  [{ts}] {e['action']} | {e['record_id']} | {e['details']}")

        else:
            print(f"Unknown command: {cmd}")
            print("Available: add, search, list, info, decompress, auto-compress, push, pull, sync-status, snapshot, status, log")

    finally:
        store.close()
