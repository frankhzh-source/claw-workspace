"""
Elite L4 File Memory — 文件系统记忆层
AI Agent 对文件世界的"感知中枢"：索引、检索、关联、变更追踪。

架构：
  SQLite + FTS5 文件索引
  ├── filestore.db       — 主索引库（文件元数据+内容全文+关系+变更日志）
  ├── filestore.json     — 元信息（索引策略、统计、上次扫描、飞书同步状态）
  └── snapshots/         — 时间快照目录

与 Elite 架构的关系：
  L1(寄存器) → L2(向量库) → L3(冷存储) → L4(文件记忆)
                                              ↓
                                    文件索引+内容检索+关系图谱
                                    L4→L2: 文件内容向量化（语义搜索）
                                    L4→L3: 旧文件记录归档
                                    L3→L4: 从冷存储恢复文件记录
                                    L4<->飞书: 文件元数据双向映射

核心能力：
  - index:   扫描目录/文件，建立元数据+内容索引
  - search:  全文搜索文件内容（FTS5+LIKE 双通道，中文友好）
  - list:    按类型/标签/日期筛选已索引文件
  - info:    查看文件详细信息
  - relate:  文件关系追踪（引用、依赖、关联）
  - watch:   变更检测（新增/修改/删除）
  - tag:     文件标签管理
  - aging:   旧文件记录 → L3 冷存储
  - push:    L4 → 飞书多维表格（文件元数据映射）
  - pull:    飞书多维表格 → L4（逆向恢复文件记录）
  - snapshot: 时间快照
  - status:  统计概览

CLI:
  python elite_filestore.py index <path> [--depth 3] [--ext .py,.md,.txt]
  python elite_filestore.py search <query> [--limit 10] [--ext .py]
  python elite_filestore.py list [--ext .py] [--tag code] [--limit 20]
  python elite_filestore.py info <file_path>
  python elite_filestore.py relate <path1> <path2> [--type references]
  python elite_filestore.py watch <path> [--depth 3]
  python elite_filestore.py tag <file_path> <tag1> [<tag2> ...]
  python elite_filestore.py aging [--days 90] [--dry-run]
  python elite_filestore.py push [--all]           # 推送到飞书（默认只推未同步的）
  python elite_filestore.py pull                    # 从飞书拉取 L4 记录
  python elite_filestore.py sync-status             # 查看飞书同步状态
  python elite_filestore.py snapshot
  python elite_filestore.py status
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

# ===================== 配置 =====================
FILE_DIR = str(Path.home() / ".openclaw" / "memory" / "filestore")
FILE_DB = str(Path(FILE_DIR) / "filestore.db")
FILE_META = str(Path(FILE_DIR) / "filestore.json")
SNAPSHOT_DIR = str(Path(FILE_DIR) / "snapshots")

# 默认索引深度和文件扩展名
DEFAULT_DEPTH = 3
DEFAULT_EXTS = {".py", ".md", ".txt", ".json", ".yaml", ".yml", ".toml",
                ".html", ".css", ".js", ".ts", ".tsx", ".jsx",
                ".csv", ".xml", ".log", ".cfg", ".ini", ".env", ".sh", ".bat"}

# 二进制文件扩展名（跳过内容索引，只存元数据）
BINARY_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg",
               ".mp3", ".mp4", ".avi", ".mov", ".wav", ".flac",
               ".zip", ".tar", ".gz", ".rar", ".7z", ".exe", ".dll", ".so",
               ".pyc", ".pyd", ".woff", ".woff2", ".ttf", ".eot", ".pdf",
               ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"}

# 文件大小上限（超过此大小不索引内容，仅元数据）
MAX_CONTENT_SIZE = 2 * 1024 * 1024  # 2MB

# 老化策略：默认 90 天未访问自动归档
DEFAULT_AGING_DAYS = 90

# 读取内容的编码尝试顺序
ENCODINGS = ["utf-8", "gbk", "gb2312", "latin-1"]

# 飞书多维表格配置（与 L2 共用同一张表，通过 记忆层级=L4-文件 区分）
FEISHU_APP_TOKEN = "G56JbFHC0abrj2sdgIwcE9Cenn2"
FEISHU_TABLE_ID = "tblZxOCAmGAk84cJ"
FEISHU_FOLDER_ID = "ERi3fwcAql5qKhdNpKacpyhXnih"


# ===================== 数据库初始化 =====================
def _init_db(conn: sqlite3.Connection):
    """创建表结构（幂等）"""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS files (
            id TEXT PRIMARY KEY,
            path TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            ext TEXT DEFAULT '',
            size INTEGER DEFAULT 0,
            modified_at REAL DEFAULT 0,
            indexed_at REAL NOT NULL,
            last_accessed REAL DEFAULT 0,
            content_hash TEXT DEFAULT '',
            file_type TEXT DEFAULT '',
            encoding TEXT DEFAULT 'utf-8',
            tags TEXT DEFAULT '[]',
            status TEXT DEFAULT 'active',
            l2_hash TEXT DEFAULT '',
            feishu_id TEXT DEFAULT '',
            line_count INTEGER DEFAULT 0,
            description TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS file_relations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_path TEXT NOT NULL,
            target_path TEXT NOT NULL,
            relation_type TEXT NOT NULL DEFAULT 'references',
            created_at REAL NOT NULL,
            detail TEXT DEFAULT '',
            FOREIGN KEY (source_path) REFERENCES files(path),
            FOREIGN KEY (target_path) REFERENCES files(path)
        );

        CREATE TABLE IF NOT EXISTS file_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT NOT NULL,
            action TEXT NOT NULL,
            timestamp REAL NOT NULL,
            detail TEXT DEFAULT ''
        );

        CREATE INDEX IF NOT EXISTS idx_files_path ON files(path);
        CREATE INDEX IF NOT EXISTS idx_files_ext ON files(ext);
        CREATE INDEX IF NOT EXISTS idx_files_name ON files(name);
        CREATE INDEX IF NOT EXISTS idx_files_content_hash ON files(content_hash);
        CREATE INDEX IF NOT EXISTS idx_files_status ON files(status);
        CREATE INDEX IF NOT EXISTS idx_files_file_type ON files(file_type);
        CREATE INDEX IF NOT EXISTS idx_relations_source ON file_relations(source_path);
        CREATE INDEX IF NOT EXISTS idx_relations_target ON file_relations(target_path);
        CREATE INDEX IF NOT EXISTS idx_log_ts ON file_log(timestamp);
    """)

    # FTS5 全文索引（文件内容）
    try:
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS file_content_fts
            USING fts5(content, path, content='files', content_rowid=rowid,
                       tokenize='unicode61 tokenchars _')
        """)
        # 触发器：保持 FTS 与主表同步
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS fts_insert AFTER INSERT ON files BEGIN
                INSERT INTO file_content_fts(rowid, content, path) VALUES (new.rowid, new.description, new.path);
            END
        """)
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS fts_delete AFTER DELETE ON files BEGIN
                INSERT INTO file_content_fts(file_content_fts, rowid, content, path) VALUES('delete', old.rowid, old.description, old.path);
            END
        """)
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS fts_update AFTER UPDATE ON files BEGIN
                INSERT INTO file_content_fts(file_content_fts, rowid, content, path) VALUES('delete', old.rowid, old.description, old.path);
                INSERT INTO file_content_fts(rowid, content, path) VALUES (new.rowid, new.description, new.path);
            END
        """)
    except sqlite3.OperationalError:
        pass  # FTS5 不可用，降级到 LIKE
    conn.commit()


# ===================== 工具函数 =====================
def _read_file_content(filepath: str) -> tuple[str, str, int]:
    """读取文件内容，返回 (content, encoding, line_count)
    二进制文件返回空内容
    """
    p = Path(filepath)
    if not p.exists():
        return "", "unknown", 0

    # 二进制文件：跳过内容
    ext = p.suffix.lower()
    if ext in BINARY_EXTS:
        return "", "binary", 0

    # 超大文件：跳过内容
    if p.stat().st_size > MAX_CONTENT_SIZE:
        return "", "too_large", 0

    for enc in ENCODINGS:
        try:
            content = p.read_text(encoding=enc)
            line_count = content.count("\n") + 1
            return content, enc, line_count
        except (UnicodeDecodeError, UnicodeError):
            continue
        except Exception:
            break

    return "", "unreadable", 0


def _classify_file(ext: str) -> str:
    """根据扩展名分类文件类型"""
    ext = ext.lower()
    type_map = {
        ".py": "code", ".js": "code", ".ts": "code", ".tsx": "code",
        ".jsx": "code", ".html": "code", ".css": "code", ".sh": "code",
        ".bat": "code", ".sql": "code",
        ".md": "document", ".txt": "document", ".rst": "document",
        ".json": "config", ".yaml": "config", ".yml": "config",
        ".toml": "config", ".ini": "config", ".cfg": "config", ".env": "config",
        ".csv": "data", ".xml": "data",
        ".png": "image", ".jpg": "image", ".jpeg": "image", ".gif": "image",
        ".svg": "image", ".bmp": "image", ".ico": "image",
        ".mp3": "media", ".mp4": "media", ".wav": "media", ".avi": "media",
        ".pdf": "document",
        ".log": "log",
    }
    return type_map.get(ext, "other")


def _extract_description(content: str, max_len: int = 500) -> str:
    """从文件内容提取简要描述（前几行 + 关键信息）"""
    if not content:
        return ""
    lines = content.strip().split("\n")
    # 取前20行，去掉空行
    non_empty = [l.strip() for l in lines[:20] if l.strip()]
    desc = "\n".join(non_empty[:5])
    if len(desc) > max_len:
        desc = desc[:max_len] + "..."
    return desc


# ===================== 核心引擎 =====================
class FileStore:
    """L4 文件记忆引擎 — SQLite + FTS5 + 文件关系"""

    def __init__(self):
        Path(FILE_DIR).mkdir(parents=True, exist_ok=True)
        Path(SNAPSHOT_DIR).mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(FILE_DB)
        self.conn.row_factory = sqlite3.Row
        _init_db(self.conn)
        self._meta = self._load_meta()

    # ---------- 元信息管理 ----------
    def _load_meta(self) -> dict:
        path = Path(FILE_META)
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return {
            "created_at": time.time(),
            "last_index_ts": 0,
            "last_watch_ts": 0,
            "last_aging_ts": 0,
            "last_snapshot_ts": 0,
            "total_indexed": 0,
            "total_relations": 0,
            "feishu_sync": {
                "last_push_ts": 0,
                "last_pull_ts": 0,
                "synced_file_hashes": [],
                "synced_feishu_ids": [],
            },
        }

    def _save_meta(self):
        Path(FILE_META).write_text(
            json.dumps(self._meta, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    # ---------- 文件索引 ----------
    def index_file(self, filepath: str, content_override: str = None) -> dict:
        """索引单个文件，返回索引结果"""
        p = Path(filepath)
        if not p.exists():
            return {"status": "error", "message": f"文件不存在: {filepath}"}

        filepath = str(p.resolve())
        ext = p.suffix.lower()
        name = p.name
        size = p.stat().st_size
        modified_at = p.stat().st_mtime

        # 读取内容
        if content_override is not None:
            content = content_override
            encoding = "override"
            line_count = content.count("\n") + 1
        else:
            content, encoding, line_count = _read_file_content(filepath)

        content_hash = hashlib.md5(content.encode()).hexdigest()[:12] if content else hashlib.md5(filepath.encode()).hexdigest()[:12]
        file_type = _classify_file(ext)
        description = _extract_description(content)

        file_id = f"F4-{int(time.time())}-{content_hash}"

        # 检查是否已索引（按路径去重）
        existing = self.conn.execute(
            "SELECT id, content_hash FROM files WHERE path = ?", (filepath,)
        ).fetchone()

        if existing:
            # 已存在：检查是否需要更新
            if existing["content_hash"] == content_hash:
                # 内容未变，更新访问时间
                self.conn.execute(
                    "UPDATE files SET last_accessed = ? WHERE path = ?",
                    (time.time(), filepath)
                )
                self.conn.commit()
                return {"status": "unchanged", "file_id": existing["id"], "path": filepath}

            # 内容变化：更新记录
            file_id = existing["id"]
            self.conn.execute("""
                UPDATE files SET name=?, ext=?, size=?, modified_at=?,
                    indexed_at=?, content_hash=?, file_type=?, encoding=?,
                    line_count=?, description=?, status='active'
                WHERE path = ?
            """, (name, ext, size, modified_at, time.time(),
                  content_hash, file_type, encoding, line_count, description, filepath))
            self._log(filepath, "update", f"content changed (hash: {content_hash})")
        else:
            # 新文件：插入
            self.conn.execute("""
                INSERT INTO files (id, path, name, ext, size, modified_at, indexed_at,
                    last_accessed, content_hash, file_type, encoding, tags, status, line_count, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '[]', 'active', ?, ?)
            """, (file_id, filepath, name, ext, size, modified_at, time.time(),
                  time.time(), content_hash, file_type, encoding, line_count, description))
            self._log(filepath, "index", f"new file (type: {file_type})")
            self._meta["total_indexed"] += 1

        self.conn.commit()
        self._save_meta()

        return {
            "status": "indexed",
            "file_id": file_id,
            "path": filepath,
            "name": name,
            "ext": ext,
            "size": size,
            "type": file_type,
            "lines": line_count,
            "hash": content_hash,
        }

    def index_dir(self, dirpath: str, depth: int = DEFAULT_DEPTH,
                  exts: set = None, content_index: bool = True) -> list:
        """扫描目录，索引所有匹配文件"""
        p = Path(dirpath)
        if not p.exists() or not p.is_dir():
            return [{"status": "error", "message": f"目录不存在: {dirpath}"}]

        exts = exts or DEFAULT_EXTS
        results = []

        for root, dirs, files in os.walk(dirpath):
            # 深度控制
            rel = os.path.relpath(root, dirpath)
            if rel != "." and rel.count(os.sep) + 1 >= depth:
                dirs.clear()  # 不再深入
                continue

            # 跳过隐藏目录和常见忽略目录
            dirs[:] = [d for d in dirs if not d.startswith(".")
                       and d not in {"__pycache__", "node_modules", ".git",
                                     "venv", ".venv", "dist", "build", ".next"}]

            for fname in files:
                fpath = Path(root) / fname
                if exts and fpath.suffix.lower() not in exts:
                    # 非目标扩展名：如果不在 BINARY_EXTS 中也索引（仅元数据）
                    if fpath.suffix.lower() in BINARY_EXTS:
                        continue
                    # 其他文件只索引元数据
                    result = self.index_file(str(fpath), content_override="" if not content_index else None)
                else:
                    result = self.index_file(str(fpath))
                results.append(result)

        self._meta["last_index_ts"] = time.time()
        self._save_meta()
        return results

    # ---------- 文件搜索 ----------
    def search(self, query: str, limit: int = 10, ext: str = None,
               file_type: str = None, tag: str = None) -> list:
        """全文搜索文件（FTS5 + LIKE 双通道，中文友好）"""
        results = []
        fts_ids = set()

        # 通道 1：FTS5
        try:
            fts_query = self._make_fts_query(query)
            sql = """
                SELECT f.*, fts.rank
                FROM file_content_fts fts
                JOIN files f ON f.rowid = fts.rowid
                WHERE file_content_fts MATCH ? AND f.status = 'active'
            """
            params = [fts_query]
            if ext:
                sql += " AND f.ext = ?"
                params.append(ext)
            if file_type:
                sql += " AND f.file_type = ?"
                params.append(file_type)
            sql += " ORDER BY fts.rank LIMIT ?"
            params.append(limit)

            rows = self.conn.execute(sql, params).fetchall()
            fts_ids = {r["id"] for r in rows}
            results = [dict(r) for r in rows]
        except (sqlite3.OperationalError, sqlite3.DatabaseError):
            pass

        # 通道 2：LIKE 兜底（搜文件名+路径+描述）
        sql = "SELECT * FROM files WHERE status = 'active' AND (path LIKE ? OR name LIKE ? OR description LIKE ?)"
        params = [f"%{query}%", f"%{query}%", f"%{query}%"]
        if ext:
            sql += " AND ext = ?"
            params.append(ext)
        if file_type:
            sql += " AND file_type = ?"
            params.append(file_type)
        if tag:
            sql += " AND tags LIKE ?"
            params.append(f'%"{tag}"%')
        sql += " ORDER BY last_accessed DESC LIMIT ?"
        params.append(limit)

        rows = self.conn.execute(sql, params).fetchall()
        for r in rows:
            if r["id"] not in fts_ids:
                results.append(dict(r))

        return results

    @staticmethod
    def _make_fts_query(query: str) -> str:
        """将查询转为 FTS5 友好格式：中文拆单字 OR，英文保持"""
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', query)
        if chinese_chars:
            return ' OR '.join(chinese_chars)
        return query

    # ---------- 文件列表 ----------
    def list_files(self, ext: str = None, file_type: str = None,
                   tag: str = None, limit: int = 20, offset: int = 0,
                   status: str = "active") -> list:
        """列出已索引文件"""
        sql = "SELECT * FROM files WHERE status = ?"
        params = [status]
        if ext:
            sql += " AND ext = ?"
            params.append(ext)
        if file_type:
            sql += " AND file_type = ?"
            params.append(file_type)
        if tag:
            sql += " AND tags LIKE ?"
            params.append(f'%"{tag}"%')
        sql += " ORDER BY last_accessed DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = self.conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    # ---------- 文件详情 ----------
    def info(self, filepath: str) -> dict:
        """获取文件详细信息"""
        filepath = str(Path(filepath).resolve())
        row = self.conn.execute(
            "SELECT * FROM files WHERE path = ?", (filepath,)
        ).fetchone()
        if row is None:
            return {"status": "error", "message": f"文件未索引: {filepath}"}

        result = dict(row)
        # 获取关系
        rels = self.conn.execute(
            "SELECT * FROM file_relations WHERE source_path = ? OR target_path = ?",
            (filepath, filepath)
        ).fetchall()
        result["relations"] = [dict(r) for r in rels]
        return result

    # ---------- 文件关系 ----------
    def relate(self, source_path: str, target_path: str,
               relation_type: str = "references", detail: str = "") -> dict:
        """建立文件关系"""
        source_path = str(Path(source_path).resolve())
        target_path = str(Path(target_path).resolve())

        # 检查是否已存在
        existing = self.conn.execute("""
            SELECT id FROM file_relations
            WHERE source_path = ? AND target_path = ? AND relation_type = ?
        """, (source_path, target_path, relation_type)).fetchone()

        if existing:
            return {"status": "exists", "id": existing["id"]}

        self.conn.execute("""
            INSERT INTO file_relations (source_path, target_path, relation_type, created_at, detail)
            VALUES (?, ?, ?, ?, ?)
        """, (source_path, target_path, relation_type, time.time(), detail))

        self._log(source_path, "relate", f"{relation_type} → {Path(target_path).name}")
        self._meta["total_relations"] += 1
        self.conn.commit()
        self._save_meta()

        return {"status": "created", "source": source_path, "target": target_path, "type": relation_type}

    def get_relations(self, filepath: str, direction: str = "both") -> list:
        """获取文件关系"""
        filepath = str(Path(filepath).resolve())
        if direction == "outgoing":
            rows = self.conn.execute(
                "SELECT * FROM file_relations WHERE source_path = ?", (filepath,)
            ).fetchall()
        elif direction == "incoming":
            rows = self.conn.execute(
                "SELECT * FROM file_relations WHERE target_path = ?", (filepath,)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM file_relations WHERE source_path = ? OR target_path = ?",
                (filepath, filepath)
            ).fetchall()
        return [dict(r) for r in rows]

    # ---------- 变更检测 ----------
    def watch(self, dirpath: str, depth: int = DEFAULT_DEPTH) -> dict:
        """检测目录变更：新增/修改/删除"""
        p = Path(dirpath)
        if not p.exists():
            return {"error": f"目录不存在: {dirpath}"}

        # 获取已索引的文件
        indexed = self.conn.execute(
            "SELECT path, content_hash, modified_at FROM files WHERE status = 'active'"
        ).fetchall()
        indexed_map = {r["path"]: {"hash": r["content_hash"], "modified": r["modified_at"]} for r in indexed}

        # 扫描当前文件
        current_files = set()
        exts = DEFAULT_EXTS | BINARY_EXTS  # watch 覆盖所有类型
        for root, dirs, files in os.walk(dirpath):
            rel = os.path.relpath(root, dirpath)
            if rel != "." and rel.count(os.sep) + 1 >= depth:
                dirs.clear()
                continue
            dirs[:] = [d for d in dirs if not d.startswith(".")
                       and d not in {"__pycache__", "node_modules", ".git", "venv", ".venv"}]
            for fname in files:
                current_files.add(str((Path(root) / fname).resolve()))

        indexed_paths = set(indexed_map.keys())

        # 新增文件
        new_files = current_files - indexed_paths
        # 已删除文件
        deleted_files = indexed_paths - current_files
        # 修改文件（同路径但 hash 不同）
        modified_files = set()
        for fp in current_files & indexed_paths:
            fp_path = Path(fp)
            if not fp_path.exists():
                continue
            ext = fp_path.suffix.lower()
            if ext in BINARY_EXTS:
                # 二进制文件用修改时间判断
                mtime = fp_path.stat().st_mtime
                if mtime > indexed_map[fp]["modified"] + 1:
                    modified_files.add(fp)
            else:
                try:
                    content = fp_path.read_text(encoding="utf-8")
                    h = hashlib.md5(content.encode()).hexdigest()[:12]
                    if h != indexed_map[fp]["hash"]:
                        modified_files.add(fp)
                except Exception:
                    pass

        result = {
            "new": sorted(new_files),
            "modified": sorted(modified_files),
            "deleted": sorted(deleted_files),
            "total_indexed": len(indexed_paths),
            "total_current": len(current_files),
        }

        self._meta["last_watch_ts"] = time.time()
        self._save_meta()
        return result

    # ---------- 标签管理 ----------
    def tag(self, filepath: str, tags: list) -> dict:
        """为文件添加标签"""
        filepath = str(Path(filepath).resolve())
        row = self.conn.execute(
            "SELECT tags FROM files WHERE path = ?", (filepath,)
        ).fetchone()
        if row is None:
            return {"status": "error", "message": f"文件未索引: {filepath}"}

        current_tags = json.loads(row["tags"])
        new_tags = [t for t in tags if t not in current_tags]
        updated_tags = current_tags + new_tags

        self.conn.execute(
            "UPDATE files SET tags = ? WHERE path = ?",
            (json.dumps(updated_tags, ensure_ascii=False), filepath)
        )
        self.conn.commit()

        return {"status": "ok", "added": new_tags, "tags": updated_tags}

    def untag(self, filepath: str, tags: list) -> dict:
        """移除文件标签"""
        filepath = str(Path(filepath).resolve())
        row = self.conn.execute(
            "SELECT tags FROM files WHERE path = ?", (filepath,)
        ).fetchone()
        if row is None:
            return {"status": "error", "message": f"文件未索引: {filepath}"}

        current_tags = json.loads(row["tags"])
        updated_tags = [t for t in current_tags if t not in tags]

        self.conn.execute(
            "UPDATE files SET tags = ? WHERE path = ?",
            (json.dumps(updated_tags, ensure_ascii=False), filepath)
        )
        self.conn.commit()

        return {"status": "ok", "removed": tags, "tags": updated_tags}

    # ---------- L4 → L2 向量化 ----------
    def promote_to_l2(self, filepath: str) -> dict:
        """将文件内容推送到 L2 LanceDB（语义搜索）"""
        filepath = str(Path(filepath).resolve())
        row = self.conn.execute(
            "SELECT * FROM files WHERE path = ?", (filepath,)
        ).fetchone()
        if row is None:
            return {"status": "error", "message": f"文件未索引: {filepath}"}

        # 读取文件内容
        content, _, _ = _read_file_content(filepath)
        if not content:
            return {"status": "error", "message": "文件内容为空或无法读取"}

        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from elite_sync import LanceStore

            lance = LanceStore()
            content_hash = lance.add(
                text=content[:2000],  # 限制长度，避免超长文本
                layer="L4",
                source=f"file:{filepath}",
                feishu_id=""
            )
            # 更新 L2 hash
            self.conn.execute(
                "UPDATE files SET l2_hash = ? WHERE path = ?",
                (content_hash, filepath)
            )
            self.conn.commit()
            return {"status": "ok", "l2_hash": content_hash, "path": filepath}
        except Exception as e:
            return {"status": "error", "message": f"L2 写入失败: {e}"}

    # ---------- 老化策略 ----------
    def aging(self, days: int = None, dry_run: bool = False) -> list:
        """L4 旧文件记录 → L3 冷存储"""
        days = days or self._meta.get("aging_days", DEFAULT_AGING_DAYS)
        cutoff_ts = time.time() - days * 86400

        rows = self.conn.execute("""
            SELECT * FROM files
            WHERE status = 'active' AND last_accessed < ? AND last_accessed > 0
        """, (cutoff_ts,)).fetchall()

        results = []
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from elite_coldstore import ColdStore
            cold = ColdStore()

            for row in rows:
                # 构造归档内容
                archive_text = f"[文件] {row['path']} | {row['name']} | {row['description'][:200]}"
                content_hash = row["content_hash"]

                if dry_run:
                    results.append({
                        "path": row["path"],
                        "name": row["name"],
                        "age_days": (time.time() - row["last_accessed"]) / 86400,
                        "action": "would_archive"
                    })
                else:
                    # 归档到 L3
                    archive_id = cold.archive(
                        text=archive_text,
                        layer="L4",
                        source=f"file_aging:{row['path']}",
                        lancedb_hash=row.get("l2_hash", ""),
                        original_ts=row["indexed_at"],
                    )
                    # 标记为已归档
                    self.conn.execute(
                        "UPDATE files SET status = 'archived' WHERE path = ?",
                        (row["path"],)
                    )
                    results.append({
                        "path": row["path"],
                        "name": row["name"],
                        "archive_id": archive_id,
                        "age_days": (time.time() - row["last_accessed"]) / 86400,
                        "action": "archived"
                    })
                    self._log(row["path"], "aging", f"→ L3 ({archive_id})")

            cold.close()
        except Exception as e:
            results.append({"error": str(e)})

        self._meta["last_aging_ts"] = time.time()
        self._save_meta()
        self.conn.commit()
        return results

    # ---------- 日志 ----------
    def _log(self, filepath: str, action: str, detail: str = ""):
        self.conn.execute("""
            INSERT INTO file_log (file_path, action, timestamp, detail)
            VALUES (?, ?, ?, ?)
        """, (filepath, action, time.time(), detail))

    def get_log(self, limit: int = 20) -> list:
        rows = self.conn.execute(
            "SELECT * FROM file_log ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    # ---------- 快照 ----------
    def snapshot(self, label: str = "") -> str:
        """导出完整快照"""
        files = self.list_files(limit=10000)
        relations = self.conn.execute("SELECT * FROM file_relations LIMIT 1000").fetchall()
        log = self.get_log(limit=100)

        snap = {
            "timestamp": time.time(),
            "label": label or f"snapshot-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            "meta": self._meta,
            "files_count": len(files),
            "relations_count": len(relations),
            "files": files,
            "relations": [dict(r) for r in relations],
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
        total = self.conn.execute("SELECT COUNT(*) as c FROM files").fetchone()["c"]
        active = self.conn.execute(
            "SELECT COUNT(*) as c FROM files WHERE status = 'active'"
        ).fetchone()["c"]
        archived = self.conn.execute(
            "SELECT COUNT(*) as c FROM files WHERE status = 'archived'"
        ).fetchone()["c"]
        relations = self.conn.execute(
            "SELECT COUNT(*) as c FROM file_relations"
        ).fetchone()["c"]

        # 按文件类型统计
        type_stats = {}
        rows = self.conn.execute(
            "SELECT file_type, COUNT(*) as c FROM files WHERE status = 'active' GROUP BY file_type"
        ).fetchall()
        for r in rows:
            type_stats[r["file_type"]] = r["c"]

        # 按扩展名 Top 10
        ext_stats = {}
        rows = self.conn.execute(
            "SELECT ext, COUNT(*) as c FROM files WHERE status = 'active' GROUP BY ext ORDER BY c DESC LIMIT 10"
        ).fetchall()
        for r in rows:
            ext_stats[r["ext"] or "(无扩展名)"] = r["c"]

        # FTS5 可用性
        fts_available = False
        try:
            self.conn.execute("SELECT * FROM file_content_fts LIMIT 1")
            fts_available = True
        except (sqlite3.OperationalError, sqlite3.DatabaseError):
            pass

        # 总大小
        total_size = self.conn.execute(
            "SELECT SUM(size) as s FROM files WHERE status = 'active'"
        ).fetchone()["s"] or 0

        return {
            "total": total,
            "active": active,
            "archived": archived,
            "relations": relations,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "types": type_stats,
            "top_exts": ext_stats,
            "fts5": fts_available,
            "aging_days": self._meta.get("aging_days", DEFAULT_AGING_DAYS),
            "last_index": datetime.fromtimestamp(self._meta["last_index_ts"]).strftime("%Y-%m-%d %H:%M")
                if self._meta.get("last_index_ts") else "从未",
            "last_watch": datetime.fromtimestamp(self._meta["last_watch_ts"]).strftime("%Y-%m-%d %H:%M")
                if self._meta.get("last_watch_ts") else "从未",
            "last_aging": datetime.fromtimestamp(self._meta["last_aging_ts"]).strftime("%Y-%m-%d %H:%M")
                if self._meta.get("last_aging_ts") else "从未",
            "db_path": FILE_DB,
        }

    # ---------- L4 ↔ 飞书映射 ----------
    def _make_feishu_text(self, row: dict) -> str:
        """将文件记录转为飞书记忆文本格式"""
        tags = json.loads(row.get("tags", "[]"))
        tag_str = ",".join(tags) if tags else ""
        parts = [
            f"[文件] {row['name']}",
            f"路径: {row['path']}",
            f"类型: {row.get('file_type', '')} | 扩展名: {row.get('ext', '')} | 大小: {row.get('size', 0)}B | 行数: {row.get('line_count', 0)}",
        ]
        if tag_str:
            parts.append(f"标签: {tag_str}")
        desc = row.get("description", "")
        if desc:
            parts.append(f"描述: {desc[:300]}")
        return "\n".join(parts)

    def push_to_feishu(self, push_all: bool = False) -> list:
        """L4 → 飞书：将文件元数据推送到飞书多维表格
        push_all=False: 只推未同步的文件
        push_all=True:  推送所有活跃文件
        返回飞书记录列表（供 MCP 工具写入）
        """
        synced_hashes = set(
            self._meta.get("feishu_sync", {}).get("synced_file_hashes", [])
        )

        if push_all:
            rows = self.conn.execute(
                "SELECT * FROM files WHERE status = 'active'"
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM files WHERE status = 'active' AND feishu_id = ''"
            ).fetchall()

        results = []
        for row in rows:
            row_dict = dict(row)
            content_hash = row_dict["content_hash"]
            if not push_all and content_hash in synced_hashes:
                continue

            text = self._make_feishu_text(row_dict)
            results.append({
                "text": text,
                "layer": "L4-文件",
                "source": row_dict["path"],
                "timestamp": row_dict.get("indexed_at", time.time()),
                "lancedb_id": row_dict.get("l2_hash", "") or content_hash,
                "sync_status": "已同步",
                "content_hash": content_hash,
                "file_id": row_dict["id"],
            })

        # 更新同步状态
        all_synced = list(synced_hashes | {r["content_hash"] for r in results})
        if "feishu_sync" not in self._meta:
            self._meta["feishu_sync"] = {}
        self._meta["feishu_sync"]["synced_file_hashes"] = all_synced
        self._meta["feishu_sync"]["last_push_ts"] = time.time()
        self._save_meta()

        return results

    def pull_from_feishu(self, feishu_records: list) -> list:
        """飞书 → L4：从飞书拉取 L4-文件 记录，写入本地索引
        feishu_records: 飞书 MCP 查询结果，需包含 text/layer/source 等字段
        """
        results = []
        synced_ids = set(
            self._meta.get("feishu_sync", {}).get("synced_feishu_ids", [])
        )

        for rec in feishu_records:
            # 只处理 L4 层级
            layer = rec.get("layer", "")
            if layer not in ("L4-文件", "L4"):
                continue

            feishu_id = rec.get("feishu_id", "")
            if feishu_id and feishu_id in synced_ids:
                continue

            text = rec.get("text", "")
            source = rec.get("source", "")

            # 从文本中解析文件信息
            file_info = self._parse_feishu_text(text, source)

            # 写入本地 L4 索引
            content_hash = hashlib.md5(text.encode()).hexdigest()[:12]

            # 检查是否已存在（按路径或 hash）
            existing = self.conn.execute(
                "SELECT id FROM files WHERE path = ? OR content_hash = ?",
                (file_info.get("path", source), content_hash)
            ).fetchone()

            if existing:
                # 更新 feishu_id
                self.conn.execute(
                    "UPDATE files SET feishu_id = ? WHERE id = ?",
                    (feishu_id, existing["id"])
                )
                results.append({
                    "status": "exists",
                    "file_id": existing["id"],
                    "feishu_id": feishu_id,
                    "path": file_info.get("path", source),
                })
            else:
                # 新建记录
                file_id = f"F4-{int(time.time())}-{content_hash}"
                self.conn.execute("""
                    INSERT INTO files (id, path, name, ext, size, modified_at, indexed_at,
                        last_accessed, content_hash, file_type, encoding, tags, status,
                        feishu_id, line_count, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '[]', 'active', ?, ?, ?)
                """, (
                    file_id,
                    file_info.get("path", source),
                    file_info.get("name", Path(source).name if source else "unknown"),
                    file_info.get("ext", Path(source).suffix.lower() if source else ""),
                    file_info.get("size", 0),
                    file_info.get("modified_at", 0),
                    time.time(),
                    time.time(),
                    content_hash,
                    file_info.get("file_type", "other"),
                    "feishu_pull",
                    feishu_id,
                    file_info.get("line_count", 0),
                    file_info.get("description", ""),
                ))
                self._log(file_info.get("path", source), "pull_from_feishu", f"feishu_id={feishu_id}")
                results.append({
                    "status": "pulled",
                    "file_id": file_id,
                    "feishu_id": feishu_id,
                    "path": file_info.get("path", source),
                })

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

    @staticmethod
    def _parse_feishu_text(text: str, source: str) -> dict:
        """从飞书记忆文本中解析文件信息"""
        info = {"path": source, "description": text}
        for line in text.split("\n"):
            if line.startswith("[文件] "):
                info["name"] = line.replace("[文件] ", "").strip()
            elif line.startswith("路径: "):
                info["path"] = line.replace("路径: ", "").strip()
            elif line.startswith("类型: "):
                parts = line.replace("类型: ", "").split("|")
                info["file_type"] = parts[0].strip() if parts else "other"
                for p in parts:
                    p = p.strip()
                    if p.startswith("扩展名:"):
                        info["ext"] = p.replace("扩展名:", "").strip()
                    elif p.startswith("大小:"):
                        size_str = p.replace("大小:", "").replace("B", "").strip()
                        try:
                            info["size"] = int(size_str)
                        except ValueError:
                            pass
                    elif p.startswith("行数:"):
                        try:
                            info["line_count"] = int(p.replace("行数:", "").strip())
                        except ValueError:
                            pass
            elif line.startswith("标签: "):
                info["tags"] = line.replace("标签: ", "").strip().split(",")
            elif line.startswith("描述: "):
                info["description"] = line.replace("描述: ", "").strip()
        return info

    def get_sync_status(self) -> dict:
        """获取飞书同步状态"""
        sync = self._meta.get("feishu_sync", {})
        total = self.conn.execute(
            "SELECT COUNT(*) as c FROM files WHERE status = 'active'"
        ).fetchone()["c"]
        synced = len(sync.get("synced_file_hashes", []))
        unsynced = self.conn.execute(
            "SELECT COUNT(*) as c FROM files WHERE status = 'active' AND feishu_id = ''"
        ).fetchone()["c"]

        return {
            "total_files": total,
            "synced_to_feishu": synced,
            "unsynced": unsynced,
            "last_push": datetime.fromtimestamp(sync.get("last_push_ts", 0)).strftime("%Y-%m-%d %H:%M")
                if sync.get("last_push_ts") else "从未",
            "last_pull": datetime.fromtimestamp(sync.get("last_pull_ts", 0)).strftime("%Y-%m-%d %H:%M")
                if sync.get("last_pull_ts") else "从未",
            "feishu_app_token": FEISHU_APP_TOKEN,
            "feishu_table_id": FEISHU_TABLE_ID,
        }

    def close(self):
        self.conn.close()


# ===================== CLI =====================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    fs = FileStore()
    cmd = sys.argv[1]

    if cmd == "index":
        if len(sys.argv) < 3:
            print("Usage: elite_filestore.py index <path> [--depth 3] [--ext .py,.md]")
            sys.exit(1)
        target = sys.argv[2]
        depth = DEFAULT_DEPTH
        exts = DEFAULT_EXTS

        if "--depth" in sys.argv:
            depth = int(sys.argv[sys.argv.index("--depth") + 1])
        if "--ext" in sys.argv:
            ext_str = sys.argv[sys.argv.index("--ext") + 1]
            exts = set(ext_str.split(","))

        p = Path(target)
        if p.is_dir():
            print(f"[L4] 索引目录: {target} (深度={depth}, 扩展名={len(exts)}种)")
            results = fs.index_dir(target, depth=depth, exts=exts)
            new_count = sum(1 for r in results if r.get("status") == "indexed")
            unchanged = sum(1 for r in results if r.get("status") == "unchanged")
            errors = sum(1 for r in results if r.get("status") == "error")
            print(f"[L4] 完成：新增 {new_count} | 未变 {unchanged} | 错误 {errors}")
        elif p.is_file():
            result = fs.index_file(target)
            if result["status"] == "error":
                print(f"[L4] 错误: {result['message']}")
            elif result["status"] == "unchanged":
                print(f"[L4] 未变化: {result['path']} (hash: {result['hash']})")
            else:
                print(f"[L4] 已索引: {result['name']} | {result['type']} | {result['lines']}行 | {result['size']}B")

    elif cmd == "search":
        if len(sys.argv) < 3:
            print("Usage: elite_filestore.py search <query> [--limit 10] [--ext .py]")
            sys.exit(1)
        query = sys.argv[2]
        limit = 10
        ext = None
        file_type = None
        tag = None
        if "--limit" in sys.argv:
            limit = int(sys.argv[sys.argv.index("--limit") + 1])
        if "--ext" in sys.argv:
            ext = sys.argv[sys.argv.index("--ext") + 1]
        if "--type" in sys.argv:
            file_type = sys.argv[sys.argv.index("--type") + 1]
        if "--tag" in sys.argv:
            tag = sys.argv[sys.argv.index("--tag") + 1]

        results = fs.search(query, limit, ext, file_type, tag)
        if not results:
            print(f"[L4] 搜索 '{query}' 无结果")
        else:
            for i, r in enumerate(results):
                ts = datetime.fromtimestamp(r.get("indexed_at", 0)).strftime("%m-%d %H:%M")
                print(f"  {i+1}. [{r.get('file_type','')}] {r.get('name','')} | {r.get('path','')[:60]} | {ts}")

    elif cmd == "list":
        limit = 20
        ext = None
        file_type = None
        tag = None
        if "--limit" in sys.argv:
            limit = int(sys.argv[sys.argv.index("--limit") + 1])
        if "--ext" in sys.argv:
            ext = sys.argv[sys.argv.index("--ext") + 1]
        if "--type" in sys.argv:
            file_type = sys.argv[sys.argv.index("--type") + 1]
        if "--tag" in sys.argv:
            tag = sys.argv[sys.argv.index("--tag") + 1]

        entries = fs.list_files(ext, file_type, tag, limit)
        for e in entries:
            tags_str = f" [{','.join(json.loads(e.get('tags', '[]')))}]" if e.get('tags', '[]') != '[]' else ""
            ts = datetime.fromtimestamp(e.get("indexed_at", 0)).strftime("%m-%d %H:%M")
            print(f"  {e.get('name',''):30s} | {e.get('ext',''):6s} | {e.get('file_type',''):8s} | {ts}{tags_str}")

    elif cmd == "info":
        if len(sys.argv) < 3:
            print("Usage: elite_filestore.py info <file_path>")
            sys.exit(1)
        result = fs.info(sys.argv[2])
        if result.get("status") == "error":
            print(f"[L4] {result['message']}")
        else:
            print(f"文件: {result['path']}")
            print(f"名称: {result['name']} | 扩展名: {result['ext']} | 类型: {result['file_type']}")
            print(f"大小: {result['size']}B | 行数: {result['line_count']} | 编码: {result['encoding']}")
            print(f"索引: {datetime.fromtimestamp(result['indexed_at']).strftime('%Y-%m-%d %H:%M')}")
            print(f"修改: {datetime.fromtimestamp(result['modified_at']).strftime('%Y-%m-%d %H:%M') if result.get('modified_at') else 'N/A'}")
            print(f"Hash: {result['content_hash']} | L2: {result.get('l2_hash', 'N/A')}")
            print(f"标签: {', '.join(json.loads(result.get('tags', '[]')))}")
            print(f"描述: {result.get('description', '')[:200]}")
            if result.get("relations"):
                print(f"关系:")
                for rel in result["relations"]:
                    direction = "→" if rel["source_path"] == result["path"] else "←"
                    other = rel["target_path"] if direction == "→" else rel["source_path"]
                    print(f"  {direction} [{rel['relation_type']}] {Path(other).name}")

    elif cmd == "relate":
        if len(sys.argv) < 4:
            print("Usage: elite_filestore.py relate <path1> <path2> [--type references]")
            sys.exit(1)
        path1, path2 = sys.argv[2], sys.argv[3]
        rel_type = "references"
        if "--type" in sys.argv:
            rel_type = sys.argv[sys.argv.index("--type") + 1]
        result = fs.relate(path1, path2, rel_type)
        if result["status"] == "exists":
            print(f"[L4] 关系已存在: {Path(path1).name} --{rel_type}--> {Path(path2).name}")
        else:
            print(f"[L4] 已建立关系: {Path(path1).name} --{rel_type}--> {Path(path2).name}")

    elif cmd == "watch":
        if len(sys.argv) < 3:
            print("Usage: elite_filestore.py watch <path> [--depth 3]")
            sys.exit(1)
        target = sys.argv[2]
        depth = DEFAULT_DEPTH
        if "--depth" in sys.argv:
            depth = int(sys.argv[sys.argv.index("--depth") + 1])
        result = fs.watch(target, depth)
        print(f"[L4] 变更检测: {target}")
        print(f"  已索引: {result['total_indexed']} | 当前: {result['total_current']}")
        if result["new"]:
            print(f"  新增 ({len(result['new'])}):")
            for f in result["new"][:10]:
                print(f"    + {Path(f).name}")
        if result["modified"]:
            print(f"  修改 ({len(result['modified'])}):")
            for f in result["modified"][:10]:
                print(f"    ~ {Path(f).name}")
        if result["deleted"]:
            print(f"  删除 ({len(result['deleted'])}):")
            for f in result["deleted"][:10]:
                print(f"    - {Path(f).name}")
        if not result["new"] and not result["modified"] and not result["deleted"]:
            print("  无变更")

    elif cmd == "tag":
        if len(sys.argv) < 4:
            print("Usage: elite_filestore.py tag <file_path> <tag1> [<tag2> ...]")
            print("       elite_filestore.py tag --remove <file_path> <tag1> [<tag2> ...]")
            sys.exit(1)
        if sys.argv[2] == "--remove":
            filepath = sys.argv[3]
            tags = sys.argv[4:]
            result = fs.untag(filepath, tags)
        else:
            filepath = sys.argv[2]
            tags = sys.argv[3:]
            result = fs.tag(filepath, tags)
        if result["status"] == "ok":
            print(f"[L4] 标签: {result['tags']}")
        else:
            print(f"[L4] {result['message']}")

    elif cmd == "aging":
        days = DEFAULT_AGING_DAYS
        dry = "--dry-run" in sys.argv
        if len(sys.argv) > 2 and sys.argv[2].isdigit():
            days = int(sys.argv[2])
        results = fs.aging(days, dry)
        mode = "预览" if dry else "执行"
        print(f"[L4] 老化{mode} (>{days}天未访问):")
        if not results:
            print("  无超龄文件")
        else:
            for r in results:
                if "error" in r:
                    print(f"  错误: {r['error']}")
                else:
                    print(f"  {r.get('action','')}: {r.get('name','')} (age: {r.get('age_days',0):.0f}天)")

    elif cmd == "promote":
        if len(sys.argv) < 3:
            print("Usage: elite_filestore.py promote <file_path>")
            sys.exit(1)
        result = fs.promote_to_l2(sys.argv[2])
        if result["status"] == "ok":
            print(f"[L4→L2] 已向量化: {result['path']} → L2 hash={result['l2_hash']}")
        else:
            print(f"[L4→L2] 失败: {result['message']}")

    elif cmd == "snapshot":
        label = sys.argv[2] if len(sys.argv) > 2 else ""
        path = fs.snapshot(label)
        print(f"[L4] 快照已保存: {path}")

    elif cmd == "push":
        push_all = "--all" in sys.argv
        results = fs.push_to_feishu(push_all=push_all)
        if not results:
            print("[L4→飞书] 没有待推送的文件记录")
        else:
            mode = "全量" if push_all else "增量"
            print(f"[L4→飞书] {mode}推送 {len(results)} 条文件记录到飞书")
            print(f"  飞书 App Token: {FEISHU_APP_TOKEN}")
            print(f"  飞书 Table ID: {FEISHU_TABLE_ID}")
            print(f"  记忆层级: L4-文件")
            # 输出 JSON 供飞书 MCP 工具写入
            for i, r in enumerate(results[:10]):
                print(f"  {i+1}. [{r.get('content_hash','')}] {r.get('text','')[:60]}...")
            if len(results) > 10:
                print(f"  ... 还有 {len(results) - 10} 条")
            # 输出完整 JSON（供 MCP 调用）
            print("\n--- 飞书记录 JSON ---")
            print(json.dumps(results, ensure_ascii=True, indent=2))

    elif cmd == "pull":
        print("[飞书→L4] 从飞书多维表格拉取 L4-文件 记录")
        print(f"  飞书 App Token: {FEISHU_APP_TOKEN}")
        print(f"  飞书 Table ID: {FEISHU_TABLE_ID}")
        print("  请使用飞书 MCP 工具查询 记忆层级='L4-文件' 的记录")
        print("  然后将结果传入 pull_from_feishu() 方法")

    elif cmd == "sync-status":
        s = fs.get_sync_status()
        print(f"L4 <-> 飞书同步状态")
        print(f"  总文件: {s['total_files']} | 已同步: {s['synced_to_feishu']} | 未同步: {s['unsynced']}")
        print(f"  上次推送: {s['last_push']}")
        print(f"  上次拉取: {s['last_pull']}")
        print(f"  飞书表: {s['feishu_app_token']} / {s['feishu_table_id']}")

    elif cmd == "status":
        s = fs.status()
        print(f"L4 文件记忆状态")
        print(f"  总文件: {s['total']} | 活跃: {s['active']} | 已归档: {s['archived']}")
        print(f"  关系数: {s['relations']} | 总大小: {s['total_size_mb']:.2f}MB")
        print(f"  FTS5: {'可用' if s['fts5'] else '不可用(降级LIKE)'}")
        print(f"  老化策略: >{s['aging_days']}天 | 上次老化: {s['last_aging']}")
        print(f"  上次索引: {s['last_index']} | 上次检测: {s['last_watch']}")
        if s['types']:
            print(f"  文件类型:")
            for t, c in sorted(s['types'].items(), key=lambda x: -x[1]):
                print(f"    {t}: {c}")
        if s['top_exts']:
            print(f"  扩展名 Top:")
            for ext, c in sorted(s['top_exts'].items(), key=lambda x: -x[1])[:5]:
                print(f"    {ext}: {c}")
        print(f"  数据库: {s['db_path']}")

    elif cmd == "log":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        logs = fs.get_log(limit)
        for l in logs:
            ts = datetime.fromtimestamp(l["timestamp"]).strftime("%m-%d %H:%M")
            print(f"  {ts} | {l['action']:8s} | {l.get('detail','')[:50]}")

    else:
        print(f"未知命令: {cmd}")
        print("可用: index, search, list, info, relate, watch, tag, aging, promote, push, pull, sync-status, snapshot, status, log")
