"""
Elite L2 Warm Store — LanceDB + Ollama (nomic-embed-text) 初始化测试
无需 OpenAI API Key，完全本地运行
"""
import json
import time
import lancedb
import httpx

# === 配置 ===
OLLAMA_BASE = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"
LANCEDB_PATH = "C:/Users/jt/.openclaw/memory/lancedb"
TABLE_NAME = "elite_memory"

# === Ollama Embedding 函数 ===
def get_embedding(text: str, model: str = EMBED_MODEL) -> list[float]:
    """调用 Ollama 本地 embedding API"""
    resp = httpx.post(
        f"{OLLAMA_BASE}/api/embed",
        json={"model": model, "input": text},
        timeout=60.0,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["embeddings"][0]

# === 测试1: Ollama 连通性 ===
print("=" * 50)
print("TEST 1: Ollama 连通性")
try:
    resp = httpx.get(f"{OLLAMA_BASE}/api/tags", timeout=5.0)
    models = resp.json().get("models", [])
    model_names = [m["name"] for m in models]
    print(f"  Ollama 运行中，已加载模型: {model_names}")
    assert any("nomic" in n for n in model_names), "nomic-embed-text 未找到!"
    print("  PASS: nomic-embed-text 可用")
except Exception as e:
    print(f"  FAIL: {e}")
    exit(1)

# === 测试2: Embedding 生成 ===
print("=" * 50)
print("TEST 2: Embedding 生成")
try:
    test_text = "海风的AI培训咨询业务"
    vec = get_embedding(test_text)
    print(f"  输入: '{test_text}'")
    print(f"  向量维度: {len(vec)}")
    print(f"  前5维: {vec[:5]}")
    assert len(vec) == 768, f"维度不符，期望768，实际{len(vec)}"
    print("  PASS: Embedding 生成正常")
except Exception as e:
    print(f"  FAIL: {e}")
    exit(1)

# === 测试3: LanceDB 读写 ===
print("=" * 50)
print("TEST 3: LanceDB 读写")
try:
    db = lancedb.connect(LANCEDB_PATH)
    print(f"  LanceDB 路径: {LANCEDB_PATH}")

    # 写入测试数据
    test_records = [
        {
            "text": "海风是AI培训师，核心业务为AI落地咨询与GEO优化",
            "vector": get_embedding("海风是AI培训师，核心业务为AI落地咨询与GEO优化"),
            "layer": "L4",
            "source": "test_init",
            "timestamp": time.time(),
        },
        {
            "text": "WorkBuddy飞书机器人需要三大能力：私信回复、群@回复、主动发消息",
            "vector": get_embedding("WorkBuddy飞书机器人需要三大能力：私信回复、群@回复、主动发消息"),
            "layer": "L4",
            "source": "test_init",
            "timestamp": time.time(),
        },
        {
            "text": "Elite 6层记忆架构：L1寄存器 L2向量库 L3图记忆 L4文件 L5语义压缩 L6知识图谱",
            "vector": get_embedding("Elite 6层记忆架构：L1寄存器 L2向量库 L3图记忆 L4文件 L5语义压缩 L6知识图谱"),
            "layer": "L2",
            "source": "test_init",
            "timestamp": time.time(),
        },
    ]

    table = db.create_table(TABLE_NAME, test_records, mode="overwrite")
    print(f"  写入 {len(test_records)} 条记录到 '{TABLE_NAME}'")

    # 向量搜索测试
    query_vec = get_embedding("AI培训")
    results = table.search(query_vec).limit(2).to_list()
    print(f"  搜索 'AI培训' Top{len(results)}:")
    for row in results:
        print(f"    - [{row['layer']}] {row['text'][:40]}... (距离: {row['_distance']:.4f})")

    print("  PASS: LanceDB 读写正常")
except Exception as e:
    print(f"  FAIL: {e}")
    exit(1)

# === 汇总 ===
print("=" * 50)
print("ALL TESTS PASSED!")
print(f"  Embedding: Ollama/{EMBED_MODEL} (768维, 本地)")
print(f"  存储: LanceDB @ {LANCEDB_PATH}")
print(f"  表: {TABLE_NAME} ({len(test_records)} 条测试数据)")
print("  L2 Warm Store 初始化完成，无需 OpenAI API Key")
