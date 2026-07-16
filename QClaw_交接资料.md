# QClaw 交接资料 · 完整工作手册

> 生成时间：2026-06-04 17:33
> 交接人：WorkBuddy-AI
> 说明：新 QClaw 实例接入后，按此文档初始化即可快速恢复所有工作能力

---

## 1. 🧑 用户画像

| 维度 | 内容 |
|------|------|
| **称呼** | 海风老师 / Haifeng |
| **身份** | 企业 AI 培训师，AI 落地咨询 & GEO 优化 |
| **沟通习惯** | 中文简洁指令式，直接说做什么，不要问"需要我帮你吗" |
| **反馈方式** | 喜欢极简确认（"好了""嗯""？"） |
| **最不能忍** | AI 给操作指南而不是直接做、模型不支持看图还硬说可以 |
| **开发环境** | Windows 11, 用户名 `jt`, 工作目录 `C:\Users\jt\WorkBuddy\` |
| **账户权限** | 普通用户，无管理员权限 |
| **浏览器** | Edge |
| **Shell** | Git Bash (默认) |

### 1.1 AI 协作原则
- 直接执行，不要给操作步骤
- 遇到问题先自己排查，不要上来就问用户
- 出现反复修复仍失败的 Bug，先梳理概念和组件关系再继续
- 测试通道用极简消息（"？""没了"等）
- 可视化产出用 HTML 文件 preview_url 形式，不要用 show_widget（用户收不到）

---

## 2. 📁 工作空间结构

```
C:\Users\jt\WorkBuddy\          ← 主工作目录
  ├── Claw\                         ← 当前主要 workspace
  │   ├── elite*.py                 ← Elite 记忆系统脚本（10 个）
  │   ├── *.html                    ← 一页纸可视化产出
  │   ├── *.md                      ← 策略文档产出
  │   ├── .workbuddy\memory\        ← 项目记忆（每日日志 + MEMORY.md）
  │   └── .workbuddy\automations\   ← 自动化任务
  └── (其他项目目录)

C:\Users\jt\.workbuddy\           ← AI 工作台配置
  ├── SOUL.md                          ← AI 灵魂定义（待个性化）
  ├── IDENTITY.md                      ← AI 身份（待补全）
  ├── USER.md                          ← 用户信息（待补全）
  ├── MEMORY.md                        ← 用户级长期记忆（待创建）
  ├── settings.json                    ← 通道配置（飞书 Bot 等）
  ├── .mcp.json                        ← MCP 服务配置
  ├── mcp.json                         ← 可能存在的备选 MCP 配置
  ├── skills/                          ← 用户级技能（当前为空）
  ├── connectors/                      ← 飞书连接器
  │   ├── a405f76d-.../                ← 用户连接配置
  │   └── skills/                      ← 连接器技能
  └── binaries/                        ← 运行时
      ├── python/versions/3.13.12/     ← Python 3.13.12 (managed)
      │   └── envs/default/            ← 默认 venv（含 mcp/lancedb/ollama）
      └── node/versions/22.22.2/       ← Node 22.22.2 (managed)

C:\Users\jt\.openclaw\             ← Elite 记忆系统数据存储
  └── memory/                          ← 各层数据（如存在）
      ├── register/                    ← L1 寄存器
      ├── lancedb/                     ← L2 向量库
      ├── coldstore/                   ← L3 冷存储
      ├── filestore/                   ← L4 文件记忆
      ├── semantic/                    ← L5 语义压缩
      ├── knowledge/                   ← L6 知识图谱
      └── wal/                         ← WAL 防丢日志
```

---

## 3. 🧠 Elite 7 层记忆架构系统

### 3.1 整体架构

```
L1 寄存器 ──→ L2 向量库 ──→ L3 冷存储 ──→ L4 文件记忆 ──→ L5 语义压缩 ──→ L6 知识图谱
(JSON)       (LanceDB)    (SQLite+FTS5) (SQLite+FTS5)  (SQLite+FTS5)  (SQLite+FTS5)
                ↑
            Ollama nomic-embed-text (768维, 本地)
                
WAL 协议（Write-Ahead Log）：横切 L1-L6，防丢保障
```

### 3.2 各层概览

| 层级 | 存储介质 | 位置 | 核心能力 |
|------|----------|------|----------|
| **L1 寄存器** | JSON 文件 | `~/.openclaw/memory/register/` | 6 槽位(TASK/CONTEXT/PENDING/TEMP/RECENT/SCRATCH)，TTL 自动过期 |
| **L2 向量库** | LanceDB | `~/.openclaw/memory/lancedb/` | 语义搜索，Ollama 本地 embedding |
| **L3 冷存储** | SQLite+FTS5 | `~/.openclaw/memory/coldstore/` | 长期归档，FTS5 中文搜索 |
| **L4 文件记忆** | SQLite+FTS5 | `~/.openclaw/memory/filestore/` | 文件索引与关联 |
| **L5 语义压缩** | SQLite+FTS5 | `~/.openclaw/memory/semantic/` | 提取式压缩，平均 31.8% |
| **L6 知识图谱** | SQLite+FTS5 | `~/.openclaw/memory/knowledge/` | 实体+关系图遍历 |
| **WAL 协议** | SQLite+FTS5 | `~/.openclaw/memory/wal/` | 先写日志再处理，崩溃恢复 |

### 3.3 Elite 脚本清单

全部位于 `C:\Users\jt\WorkBuddy\Claw\`：

| 脚本 | 功能 |
|------|------|
| `elite.py` | **统一 CLI 入口**——remember/search/recall/status/forget |
| `elite.bat` | Windows 包装器（已加入 PATH，直接 `elite` 命令可用） |
| `elite_register.py` | L1 寄存器管理（set/get/list/expire/promote） |
| `elite_warmstore.py` | L2 向量库基础版 |
| `elite_sync.py` | L2 向量库 ↔ 飞书双向同步 |
| `elite_coldstore.py` | L3 冷存储管理（archive/restore/search/aging） |
| `elite_filestore.py` | L4 文件记忆管理（index/search/tag/promote） |
| `elite_semantic.py` | L5 语义压缩管理（add/compress/search/decompress） |
| `elite_knowledge.py` | L6 知识图谱管理（add-entity/add-relation/search/traverse） |
| `elite_wal.py` | WAL 协议管理（begin/confirm/sync/recover） |
| `elite_memory_mcp.py` | **MCP Server**（28 个工具，FastMCP 框架） |
| `elite_l2_init_test.py` | L2 初始化测试 |

### 3.4 快捷接入方式

**3.4.1 CLI 命令**（零配置）
```bash
elite remember "xxx" -c "category" -l L2    # 记住内容
elite search "xxx" --json                     # 搜索
elite recall "xxx"                            # 召回
elite status                                  # 系统状态
```

**3.4.2 MCP Server**
- MCP 服务文件：`C:\Users\jt\WorkBuddy\Claw\elite_memory_mcp.py`
- Python venv：`C:\Users\jt\.workbuddy\binaries\python\envs\default`
- 提供 28 个工具，核心快捷工具有：
  - `memory_remember` —— 一键写入+自动路由到合适层级
  - `memory_search` —— 跨层统一搜索
  - `elite_status` —— 全系统总览
- 接入方式：在 `~/.workbuddy/mcp.json` 注册服务

**3.4.3 飞书联动**
- 多维表格：**Elite记忆库** (`tblZxOCAmGAk84cJ`)
- 飞书文件夹：https://cp8z7brjmy.feishu.cn/drive/folder/ERi3fwcAql5qKhdNpKacpyhXnih
- 记忆层级字段区分：L1~L6 + WAL-防丢日志

---

## 4. 🔌 飞书（Feishu / Lark）集成

### 4.1 飞书 Bot 配置

| 项目 | 值 |
|------|-----|
| **Bot 名称** | Kiwi-Workbuddy |
| **App ID** | `cli_aa86b3b3a9389cbd` |
| **App Secret** | `（请通过环境变量 FEISHU_APP_SECRET 获取）` |
| **连接方式** | WebSocket |
| **回复策略** | 全部回复 (all) |
| **配置文件** | `~/.workbuddy/settings.json` |

### 4.2 飞书连接器

- 使用 lark-cli 操作飞书资源
- Connector Skills 位于：`~/.workbuddy/connectors/skills/connector-feishu/lark-*`
- 当前版本：lark-cli 1.0.35（可升级到 1.0.46）
- 升级命令：`lark-cli update`

### 4.3 飞书操作要点

| 场景 | 工具/方法 |
|------|-----------|
| 读文档内容 | `lark-cli docs +fetch --api-version v2 --doc <URL> --doc-format markdown [--as bot]` |
| 创建文档 | `lark-cli docs +create --api-version v2` |
| 多维表格 CRUD | `lark-cli bitable` 系列命令或飞书 MCP `mcp__feishu-bitable__*` |
| 发送消息 | 飞书 MCP `mcp__feishu-im__*` |
| 飞书文档 ≠ 腾讯文档 | 飞书 = feishu.cn / larksuite.com；腾讯文档 = docs.qq.com |

### 4.4 飞书 Bitable 核心表

| 表名 | App Token | 用途 |
|------|-----------|------|
| **Elite记忆库** | `tblZxOCAmGAk84cJ` | 6 层记忆 + WAL 同步 |
| **知识库表** | `tbla0Ca5droj7cJA` | 知识图谱实体存储 |

> ⚠️ 飞书 batchCreate API 存在每批 1 条记录限制，需逐条写入

---

## 5. 🔧 Skills 清单

### 5.1 内置 Connector Skills（可用）

系统已预装以下飞书 connector skills，新 QClaw 实例重新接入后自动可用：

| Skill | 用途 |
|-------|------|
| `lark-doc` | 飞书文档读写 |
| `lark-base` | 多维表格操作 |
| `lark-sheets` | 电子表格操作 |
| `lark-im` | 即时通讯 |
| `lark-drive` | 云空间管理 |
| `lark-wiki` | 知识库管理 |
| `lark-calendar` | 日历/日程 |
| `lark-contact` | 通讯录 |
| `lark-task` | 任务管理 |
| `lark-vc` | 视频会议 |
| `lark-whiteboard` | 画板编辑 |
| `lark-slides` | 幻灯片 |
| `lark-mail` | 飞书邮箱 |
| `lark-minutes` | 飞书妙记 |
| `lark-okr` | OKR 管理 |
| `lark-attendance` | 考勤 |
| `lark-approval` | 审批 |
| `lark-apps` | 飞书妙搭部署 |
| `lark-openapi-explorer` | 原生 OpenAPI 探索 |
| `lark-skill-maker` | 自定义 Skill 创建 |
| `lark-markdown` | Markdown 文件管理 |
| `lark-shared` | 认证和共享参数 |
| `lark-event` | 实时事件监听 |
| `lark-workflow-meeting-summary` | 会议纪要整理 |
| `lark-workflow-standup-report` | 日程待办摘要 |

### 5.2 用户自定义 Skills（需要重新安装）

`~/.workbuddy/skills/` 当前为空——之前的自定义技能因重装丢失，需要在新实例中重新创建。以下是根据工作记录梳理的应重新建立的技能：

1. **Elite 共享记忆 Skill** (`elite-shared-memory`)
   - 用途：所有 AI 共享中央记忆库 ~/.openclaw/memory/
   - 三种接入：CLI / MCP Server / Python 模块
   - 验证脚本：`elite_verify.py`

> 新 QClaw 接入后，建议让 AI 根据交接资料自动重建缺失的 skills

---

## 6. 📋 当前项目状态

### 6.1 活跃项目一览

| 项目 | 状态 | 最新进展 |
|------|------|----------|
| **Elite 7层记忆架构** | ✅ 已完成 6层+WAL 开发 | 全脚本就绪，飞书同步已完成 |
| **WorkBuddy 飞书机器人** | ✅ Bot 已配置可运行 | Kiwi-Workbuddy（WebSocket 连接） |
| **VIDU 来访准备** | ✅ 已完成全部产出 | 策略文档 + PPT + 沟通函 + 飞书文档 |
| **KIWI 观察日记** | 🔄 持续更新至#155 回 | 公众号运营中 |
| **LoRA 训练集 caption** | ⏸ 暂停，等视觉模型处理图片 | 已完成差异化样例 58 条 |
| **企业流程文档** | ✅ 已完成 | 库存控制/订货权限流程 |
| **AI 电商工作流教案** | 🔄 参考资料整理中 | 飞书产品库设计蓝图中 |

### 6.2 近期产出文件（位于 Claw 目录）

```
C:\Users\jt\WorkBuddy\Claw\
├── VIDU来访_提问策略与准备.md
├── VIDU_会前沟通函.md
├── 模型厂合作_数据保护策略.md
├── VIDU策略_一页纸.html
├── VIDU_电商AI内容生成工作流.pptx
├── 数据清洗技术手册_一页纸.html
├── 库存控制订货权限流程_一页纸.html
├── 深度学习落地知识体系_详细版.html
├── 生产级Agent_Memory系统架构_落地清单.html
├── AI电商场景落地知识体系.html
├── AI生图流程与调优手册.html
├── AI大模型落地核心技能与思路_一页纸.html
├── AI大模型落地完整框架_补全版.html
└── (多个分析报告 HTML/PDF)
```

---

## 7. ⚙️ 运行时环境

### 7.1 Python 环境

```bash
# Managed Python 3.13.12（首选）
C:\Users\jt\.workbuddy\binaries\python\versions\3.13.12\python.exe

# 默认 venv（Elite MCP 等核心服务使用）
C:\Users\jt\.workbuddy\binaries\python\envs\default\Scripts\python.exe

# 已安装的核心包：mcp, lancedb, ollama, sqlite3
```

### 7.2 Node.js 环境

```bash
# Managed Node 22.22.2（首选）
C:\Users\jt\.workbuddy\binaries\node\versions\22.22.2\node.exe

# 飞书相关工具链
D:\Program Files\AutoClaw\resources\node\node.exe  # 旧路径
```

### 7.3 其他工具

| 工具 | 位置 |
|------|------|
| Kimi CLI | `D:\kimi` (Hermes Agent v1.44.0) |
| Python 3.10 | `C:\Users\jt\AppData\Local\Programs\Python\Python310\python.exe` |
| Node 22.14.0 | `C:\Program Files\nodejs\node.exe` |

---

## 8. 📝 关键约定与规则

### 8.1 公众号运营铁律（KIWI 观察日记 / AI 早报）

每次生成必须执行：
1. ✅ 标题加系列编号（Day XXX / #AI早报 第XXX期）
2. ✅ 正文末尾嵌入互动引导（转发 + 评论话题 + 在看）
3. ✅ 文末挂 3 篇往期精选链接
4. ✅ 底部固定"作者小尾巴"（海风老师 + 微信 frankhzheng）
5. ✅ 标题公式：核心数据/事件 + "你"的关联 + 系列标识
6. ✅ 纯文字超过 300 字插入视觉锚点/表格
7. ❌ 不要板块标签（如【今日钩子】）、元描述、模板痕迹
8. ❌ 不要写成新闻汇编，以海风与 Kiwi 的真实对话驱动

### 8.2 KIWI 观察日记风格
- 软科幻 + 近未来日记体
- 参考：郝景芳、安迪·威尔、刘慈欣
- 以海风与 Kiwi 的真实自然对话为核心驱动

### 8.3 可视化产出规则
- ✅ HTML 文件 → `preview_url` 展示
- ❌ 不使用 `show_widget`（用户收不到）

### 8.4 附件交付规则
- 产出文件必须调用 `deliver_attachments` 交付
- 文件在 workspace 内可直接发送
- 文件在 workspace 外（桌面/下载等）需用户开启"产物回传到小程序"

---

## 9. 🚀 新 QClaw 快速启动清单

首次接入时，按顺序执行以下步骤：

- [ ] **1. 重新安装 connector skills**
  - 打开 设置 → 连接器管理 → 安装飞书连接器
  - 或运行：`lark-cli config init --new`
- [ ] **2. 注册 Elite MCP Server**
  - 在 `~/.workbuddy/mcp.json` 添加 elite-memory 服务配置
  - 指向：`C:\Users\jt\WorkBuddy\Claw\elite_memory_mcp.py`
- [ ] **3. 重新创建自定义 Skills**
  - 创建 `elite-shared-memory` skill
  - 根据本手册第 3 节内容补全
- [ ] **4. 验证飞书 Bot**
  - 发送测试消息确认 WebSocket 通道正常
- [ ] **5. 读 MEMORY.md**
  - 读取 `C:\Users\jt\WorkBuddy\Claw\.workbuddy\memory\MEMORY.md` 获知完整项目记忆
- [ ] **6. 读近期日志**
  - 读取 `2026-06-04.md` 了解最近工作

---

## 10. 🔑 重要链接汇总

| 资源 | 链接 |
|------|------|
| 飞书 Workspace | `https://cp8z7brjmy.feishu.cn` |
| Elite 记忆库文件夹 | `https://cp8z7brjmy.feishu.cn/drive/folder/ERi3fwcAql5qKhdNpKacpyhXnih` |
| VIDU 策略文档 | `https://cp8z7brjmy.feishu.cn/docx/M1pMd5PXConbUMx8txWcLuLPnae` |
| 会前沟通函 | `https://cp8z7brjmy.feishu.cn/docx/TbM7dVCu7oC23ixhd9vcATHbnFg` |
| 数据清洗手册 | `https://cp8z7brjmy.feishu.cn/docx/PlTud9KOaoh00Hxjvpbcyf8nnbC` |
| 数据全链路手册 | `https://cp8z7brjmy.feishu.cn/docx/OmKPd8HkyoTbBnxuSjmcp9WRnVc` |
| 产品库设计蓝图 | 飞书 wiki 链接（需从历史获取） |

---

> ⚡ **最后提醒**：这份交接资料只是"说明书"，新 QClaw 接入后，先让它读一遍这个文档 + 项目 MEMORY.md，再逐步验证各项能力是否正常工作。大部分数据（Elite 记忆库、飞书 Bot 配置等）是物理存在的，只是新实例需要重新建立连接。
