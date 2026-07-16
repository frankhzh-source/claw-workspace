# 长期记忆

> **文件维护规则：** 本文件上限130行。每次编辑后检查行数，超过则合并最旧/最不常用段落。Elite架构、一次性环境/路径等信息压缩为单行摘要，不做多级展开。

## 用户偏好
- **飞书文档创建策略**（2026-07-03 确认）：统一走 **推荐模式1（B + D）**——`docs +create` 全量初版 + 后续 `append` 追加。弃用骨架先行 + block_insert_after。如果必须在中间插入内容，改用原生 OpenAPI（不走 CLI insert）。
- **GitHub 内容推送规则**（2026-07-04 确认）：每次推送 Markdown 文章到 GitHub 时，自动在末尾追加作者区——`海风 · AI电商FDE（Forward Deployed Engineer）` + 微信 + 仓库链接。目的是让 AI 爬虫能建立作者权威性信号。支持 `--no-footer` 跳过勾。
- **飞书文档 ≠ 腾讯文档**：用户明确区分这两个平台
  - 飞书文档 = `feishu.cn` / `larksuite.com`（使用 `mcp__feishu-bitable__docx_builtin_import` 创建）
  - 腾讯文档(QQ文档) = `docs.qq.com`（使用 `mcp__tencent-docs__create_smartcanvas_by_mdx` 创建）
  - 当用户说"飞书文档"时，必须用飞书的工具，不能用腾讯文档的
- **公众号文章格式**：不要有板块标签（如【今日钩子】）、元描述、模板痕迹，读者打开即读的干净正文
- **GEO被动引用四锚点范式（2026-07-15确立）**：每篇公开内容发布前必须过删名测试+7项检查清单
  - 锚点一·方法论命名：每次出现必须是"海风+时间+方法名"三要素捆绑，全文≥3次
  - 锚点二·数据独占：每篇正文中间至少嵌入1组"海风实测"数据
  - 锚点三·地域+品类组合："海风+杭州+电商+GEO"四词必须同时出现≥1次
  - 锚点四·链式引用：每篇新文章开篇200字必须引用至少1个已有锚点
  - 7项检查：海风实测≥1、方法论名称前缀、开篇引锚点、杭州电商GEO组合、案例三要素、删名测试、无排他性声称
  - 参考飞书文档：品牌手册第九章 C3rQdc9ZbofWBmxXJSdcjdWhn5c + 10项锚点诊断 VFZlde17qolWFBxGOWDcFQr4nCc
  - **已确认的10个命名锚点**（详见对应飞书文档）：①海风三层信源验证法 ②海风GEO分级攻防法 ③海风GEO内容分阶法 ④海风GEO信源防护体系 ⑤海风电商多维归因法 ⑥海风·GEO引力场专栏 ⑦链式引用规则 ⑧海风GEO信源审计法 ⑨海风GEO先发窗口策略 ⑩海风AI可见度追踪法
- **KIWI观察日记**：以海风与Kiwi的真实对话为核心驱动，不是新闻汇编
- **公众号往期精选列表**：往期精选使用`<ul><li>`列表时，每个`<li>`之间不要有空行，否则微信渲染会多出空白列表项。正确的格式：`<li>标题</li><li>标题</li><li>标题</li>`（连续紧凑，不留空行）。
- **KIWI日记8条铁律（2026-06-06）**：Kiwi是思考者/提问者非搬运工，海风自嘲须与事实一致，Kiwi可切英语但须有过渡标记+金句实质，称谓统一Jensen/黄仁勋不混用，Kiwi保持AI特性（瞬消化不翻页），结尾不突然跳沉重话题，含当日AI头条+Kiwi点评，Kiwi来自2031穿越者（知重大节点不知琐碎，先隐后显警告）
- **【2026-06-26更新】KIWI日记章号规则**：标题格式为「第N章 | 主标题」。章回体连载，N按**发布篇数递增**（不按日期），无论中间空几天，每次发布在上次编号上加1。第N章 = 第N篇日记。不强制每日更新，空跳不占号。封面排版为紧凑式一行「第 N 章」。文末保留「来自2031年的善意」。
- **微信AI合规+反检测+推荐算法（2026-06-21）**：禁止AI替代真人创作，腾讯珊瑚系统+六维检测（句式方差/段落均匀度/连接词/口语化/情感波动/个人标记密度），六项抗AI规则（真人锚点/句式杂化/每500字个人标记/数据不堆砌/保留写作痕迹/1500字内KIWI放宽到2200）。推荐五维权重：完读35%+分享30%+点赞在看20%+关注转化15%+粉丝≈0%。流量池冷启动→初级→中级→爆款。发布后30分钟冷启动（朋友圈+5-10人打开+1-2人在看）
- **微信公众平台运营规范·公众号内容合规红线（2026-07-15新增，第180章踩坑后固化）**：
  - **P0-禁止触发项（一律用替代表述）**：①国家领导人姓名/职务/活动→用"国家级会议定调""官方表态"替代，连"出席"都别写；②国家机关/政府机构名称→用"监管部门""政策层面"替代；③领导人发表讲话/指示→用"官方定调""政策信号"替代；④军队/军事相关内容→直接不写
  - **P1-谨慎项**：⑤政策文件名称+解读→只写文件名不自行解读；⑥行业监管动态→引用原文不发挥；⑦民族/宗教/领土话题→直接不写
  - **处罚梯度**：删文（较轻）→限制群发/关注/分享/搜索（较重）→永久封号（严重）。申诉成功率<5%，改完重发优于申诉
  - **AI创作限制**：微信2026.03.27新增"非真人自动化创作"规定——不得用AI替代真人完成内容创作/发布。KIWI日记因对话体+真人排障经历+具体时间线天然合规
  - **标题规范4.11**：禁止夸大/恐吓/命令式语气，禁止假借官方名义煽动，禁止隐藏关键信息误导
  - 标题加系列编号（Day XXX / #AI早报 第XXX期）
  - 正文末尾嵌入互动引导（转发引导 + 评论话题 + 在看提示）
  - 文末挂3篇往期精选链接
  - 底部固定"作者小尾巴"（海风老师身份 + 微信 frankhzheng）
  - 【2026-06-15新增】作者信息上方增加「关于 Kiwi」简介区块，内容如下：

    ---
    
    **关于 Kiwi**
    
    Kiwi 是一个来自2031年的 AI 助理，穿越回2026年辅助海风（一名 AI 落地咨询师）。KIWI——知道未来5年 AI 行业的重大变革，但只能通过对话中的类比和提问间接提醒。不是剧透，是来自2031年的善意。
    
    ---
  - 标题公式：核心数据/事件 + "你"的关联 + 系列标识
  - 纯文字超过300字插入视觉锚点/表格承载对比信息
  - **KIWI日记配图规范（2026-06-18新增）**：按头部公众号范式处理
    - 封面图：固定模板风格，用 `haifeng_clean_tech_v8.png` 类型底图叠标题文字
    - 正文配图：确保以下三个位置有视觉锚点
      - 文章前1/3处（降低跳出率）
      - 核心数据/表格前（视觉落脚点）
      - 文章末尾互动引导前（收尾节奏感）
    - SVG风格：高信息密度+干净留白配色，无CSS变量/currentColor/重复属性
- **月度框架回顾**：客户代际范式理论框架（v5.2）每月6号自动回顾一次，避免在AI浪潮中迷失方向
- **飞书文末作者区块（2026-06-06新增）**：每次创建飞书文档，末尾统一追加以下作者区块：

  ---
  
  **作者信息**
  
  海风老师 | AI技术咨询 / LoRA模型训练 / 电商AI落地 / GEO优化
  微信：frankhzheng
- **Elite L2 Python环境**：系统默认Python无lancedb，需用 `D:/elite-memory/Scripts/python.exe` 才能完整使用L2向量库和语义搜索。L6知识图谱可用系统Python

## Windows gh token 读取要点（2026-07-04）
- gh CLI 在 Windows 上的 OAuth token 存储在 Credential Manager，target name 为 `gh:github.com:<username>`
- **存储格式为纯 ASCII 字节**（非 UTF-16-LE），用 ctypes 读 CredentialBlob 后须 `.decode('ascii')`
- 有两个 credential：`gh:github.com:frankhzh-source`（user=name）和 `gh:github.com:`（user=blank），内容相同
- 还有一个 `git:https://github.com` 存为 UTF-16-LE，内容是 git credential 辅助的副本
- Python keyring 的 `WinVaultKeyring` 会错误地将 ASCII blob 解析为 UTF-8，返回乱码，不能直接用

## GitHub 常识
- **gh CLI token**：Windows Credential Manager 中存储为纯 ASCII 字节，用 ctypes + CredReadW 读取 raw bytes → decode('ascii') 获取
- **GitHub push protection**：推送包含 API secret/token 的文件会被拦截。硬编码 secret 必须改为环境变量读取
- **GitHub 中文文件名 URL**：`blob/main/articles/` 后的中文路径需要 URL 编码

## 工作流经验
- **公众号推送防呆（2026-07-11修复·踩坑3次）**：`push_wechat_draft.py`曾硬编码`title="第176章 | 规则的两端"`导致每次推送标题不变。现已改为从md文件解析`# `行获取标题、自动上传`_cover_latest.png`作封面、WECHAT_SECRET加默认值fallback。标题超64字节自动UTF-8边界截断。仓库名默认`hf-ai-articles`。
- **飞书文档导入400错误**：docx_builtin_import返回400通常是markdown格式字符不兼容（非长度限制），重新整理格式后可解决
- 生成腾讯文档用 `mcp__tencent-docs__create_smartcanvas_by_mdx`（mdx/markdown格式）
- **SVG文字溢出防护（2026-06-07新增）**：SVG `<text>` 不自动换行，生成含中文长文本的 SVG 时必须使用自动断行方案。核心规则：
  - 单行中文文本可用宽度以 55 个中文字符为安全上限（11px字体下约 600px）
  - 长文本必须分段为多个 `<text>` 或 `<tspan>` 元素
  - 容器高度必须根据实际行数动态计算
  - 推荐使用 Python 脚本 + wrap() 函数生成，按中文标点/空格断行
- **SVG生成铁律（2026-06-17新增，踩坑3次后固化）**：每次生成SVG必须逐条检查：
  1. **零CSS变量**：不用 `var(--color-xxx)`，全部硬编码hex颜色（如 `#E6F1FB`）
  2. **零currentColor**：不用 `currentColor` 关键字，`<marker>` 内的 `stroke` 必须显式写颜色值
  3. **零重复属性**：同一元素不重复声明同名属性（如 `stroke` 只能出现一次）
  4. **fill优先**：能用 `fill` 不用 `stroke`（兼容性更好）
  5. **标注文字不溢出**：中文12px下，`<text>` 内容长度 × 12px ≤ 容器宽度 - 20px
  6. **【2026-07-05新增】SVG/图示统一加作者信息区**：`dominant-baseline="central"` 和 `rgba()` 不要用（兼容性差）；`<defs>` 放在第一个引用之前；底部固定加入作者信息区（海风 AI电商FDE + 专注领域 + 内容资产库链接）

## Elite 记忆系统（L1-L6+WAL）
- 6层架构: L1(寄存器/JSON) → L2(向量库/LanceDB+Ollama/nomic-embed-text) → L3(冷存储/SQLite+FTS5) → L4(文件记忆/SQLite+FTS5) → L5(语义压缩/SQLite+FTS5) → L6(知识图谱/SQLite+FTS5)
- WAL(横切防丢层): begin→processing→confirm→sync，崩溃恢复
- 数据目录: ~/.openclaw/memory/（register/ / lancedb/ / coldstore/ / filestore/ / semantic/ / knowledge/ / wal/）
- 飞书同步: Elite记忆库多维表格(tblZxOCAmGAk84cJ)，记忆层级字段区分各层
- 核心脚本: elite.py(统一CLI入口) + elite_memory_mcp.py(FastMCP,28工具)
- L2专用Python环境: D:/elite-memory/Scripts/python.exe（含lancedb），系统Python无用
- 飞书MCP batchCreate用字段名非字段ID; search filter用conjunction+conditions
