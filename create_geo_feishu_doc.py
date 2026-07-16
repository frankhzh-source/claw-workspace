#!/usr/bin/env python3
"""Convert GEO framework Markdown to Feishu XML and append - All Batches."""

import subprocess
import sys

DOC_ID = "TR9nd7lfso2nU0xnipyc4vcpnpd"

def append_content(xml_content, label=""):
    """Append XML content to the Feishu doc"""
    cmd = [
        "lark-cli", "docs", "+update", "--api-version", "v2",
        "--doc", DOC_ID, "--command", "append", "--content", xml_content
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"FAIL [{label}]: {result.stderr[:200]}")
        return False
    print(f"OK [{label}]: {len(xml_content)} chars")
    return True

# ============================================================
# Batch 1: Intro + Phase 0 + Phase 1 (already done, skip)
# ============================================================

# ============================================================
# Batch 2: Phase 2 (Strategy Design)
# ============================================================
batch2 = "\n".join([
    '<h2>Phase 2：策略设计（Strategy Design）</h2>',
    '<h3>目标</h3>',
    '<p>基于 Phase 1 的差距分析，设计可执行的 GEO 优化策略。</p>',

    '<h3>方法论：GEO 策略金字塔（Pyramid Principle）</h3>',
    '<pre lang="text">                    ┌──────────────────────┐\n                    │  GEO 北极星指标       │\n                    │  AI 引用率提升 X%      │\n                    └──────────┬───────────┘\n                               │\n          ┌────────────────────┼────────────────────┐\n          │                    │                    │\n    ┌─────┴─────┐      ┌──────┴──────┐      ┌─────┴─────┐\n    │  内容支柱  │      │  技术基建   │      │  权威构建  │\n    └─────┬─────┘      └──────┬──────┘      └─────┬─────┘\n          │                    │                    │\n    ┌─────┼─────┐       ┌─────┼─────┐       ┌─────┼─────┐\n    │主题│专栏│       │Schema│速度│       │链接│品牌│\n    │矩阵│体系│       │标签  │优化│       │建设│信号│\n    └─────┴─────┘       └─────┴─────┘       └─────┴─────┘</pre>',

    '<h3>策略输出物</h3>',
    '<table><colgroup><col width="140"/><col width="80"/><col width="200"/></colgroup><thead><tr><th>交付物</th><th>格式</th><th>详细内容</th></tr></thead><tbody>',
    '<tr><td>GEO 策略蓝图（Blueprint）</td><td>PPT</td><td>包含现状→目标→路径→时间线</td></tr>',
    '<tr><td>内容矩阵规划</td><td>Excel/多维表格</td><td>主题/关键词/格式/优先级/责任人</td></tr>',
    '<tr><td>Schema 实施路线图</td><td>Excel</td><td>页面级 Schema 类型映射和时间表</td></tr>',
    '<tr><td>权威构建计划</td><td>文档</td><td>外链策略/行业合作/白皮书规划</td></tr>',
    '<tr><td>ROI 预测模型</td><td>Excel</td><td>投入产出测算，3/6/12 个月预测</td></tr>',
    '<tr><td>KPI 框架</td><td>Excel</td><td>关键绩效指标 + 目标值 + 监测方式</td></tr>',
    '</tbody></table>',

    '<h3>优先级矩阵（Impact × Effort）</h3>',
    '<pre lang="text">影响\n 高 │ ╔══════════════════════╗\n    │ ║  QUICK WINS         ║    ← 先做\n    │ ║  (现做现得)          ║\n    │ ╚══════════════════════╝\n     │\n 中  │    ╔══════════════╗    ← 中期规划\n     │    ║  STRATEGIC   ║\n     │    ║  INITIATIVES ║\n     │    ╚══════════════╝\n     │\n 低  │         ╔══════╗        ← 长期部署\n     │         ║ NICE ║\n     │         ║ TO   ║\n     │         ║ HAVE ║\n     │         ╚══════╝\n     └─────────────────────────\n        低      中       高     投入</pre>',

    '<h3>退出标准</h3>',
    '<checkbox done="false">策略蓝图经客户高层确认</checkbox>',
    '<checkbox done="false">内容矩阵完成，Phase 3 内容日历启动</checkbox>',
    '<checkbox done="false">ROI 模型交付并完成敏感性分析</checkbox>',
    '<checkbox done="false">实施团队确认资源和时间线</checkbox>',
])

# ============================================================
# Batch 3: Phase 3 (Implementation)
# ============================================================
batch3 = "\n".join([
    '<h2>Phase 3：实施落地（Implementation）</h2>',
    '<h3>目标</h3>',
    '<p>将策略蓝图转化为可执行的行动项，按阶段交付。</p>',

    '<h3>工作流</h3>',
    '<pre lang="text">Sprint 规划会（每 2 周）\n    ↓\n内容生产流水线\n    ┣━ 选题 → 写作 → 优化 → 发布\n    ┣━ Schema 标签实施\n    ┣━ 权威信号建设\n    ┣━ 技术优化\n    ↓\nWIP 验收（每 Sprint 末）\n    ↓\n双周进展汇报</pre>',

    '<h3>实施 Sprint 节奏</h3>',
    '<pre lang="text">Sprint 1-2                    Sprint 3-4                    Sprint 5-6\n┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐\n│ 基础建设基地     │         │ 内容规模期       │         │ 权威构建期       │\n│                 │         │                 │         │                 │\n│ • Schema标签实施 │         │ • 核心主题矩阵   │         │ • 外链获取       │\n│ • 技术优化       │         │ • 专题专栏体系   │         │ • 行业报告       │\n│ • 快速赢项       │         │ • FAQ/HowTo内容  │         │ • 合作共建       │\n│ • 内容模板标准化  │         │ • 多模态内容     │         │ • 数据/研究发布   │\n└─────────────────┘         └─────────────────┘         └─────────────────┘</pre>',

    '<h3>交付物</h3>',
    '<table><colgroup><col width="140"/><col width="60"/><col width="140"/></colgroup><thead><tr><th>交付物</th><th>频次</th><th>格式</th></tr></thead><tbody>',
    '<tr><td>Sprint 工作计划</td><td>双周</td><td>Excel/项目管理工具</td></tr>',
    '<tr><td>内容生产日历</td><td>周度</td><td>多维表格</td></tr>',
    '<tr><td>Schema 实施确认单</td><td>每次部署</td><td>检查清单</td></tr>',
    '<tr><td>双周进展报告</td><td>双周</td><td>PPT</td></tr>',
    '<tr><td>质量抽检报告</td><td>每次内容发布前</td><td>内部评分卡</td></tr>',
    '</tbody></table>',

    '<h3>质量门禁（Quality Gate）</h3>',
    '<p>每篇内容发布前，必须经过以下检查：</p>',
    '<pre lang="text">□ GEO 友好性检查\n   - 标题是否包含核心关键词（天然语义，非堆砌）\n   - 是否包含权威引用/数据/信源\n   - 是否有 FAQ 或问答式结构\n   - 是否有明确的实体标签（人物/公司/概念）\n\n□ 技术合规检查\n   - Schema.org Article/FAQ/Breadcrumb 是否正确\n   - 页面加载速度达标\n   - 移动端适配确认\n   - 无爬虫屏蔽（robots.txt 未误拦）\n\n□ 品牌一致性检查\n   - 品牌信息准确\n   - 链接指向正确\n   - 联系方式/网站引用一致</pre>',

    '<h3>退出标准</h3>',
    '<checkbox done="false">核心内容矩阵建设完成（根据合同约定的内容量）</checkbox>',
    '<checkbox done="false">Schema 标签覆盖率达标（如：≥80% 的页面）</checkbox>',
    '<checkbox done="false">AI 引用率有可量化的提升（基线对比）</checkbox>',
    '<checkbox done="false">客户方团队具备基本的独立运营能力</checkbox>',
    '<checkbox done="false">转入持续运营模式</checkbox>',
])

# ============================================================
# Batch 4: Phase 4 (Managed Operations)
# ============================================================
batch4 = "\n".join([
    '<h2>Phase 4：持续运营（Managed Operations）</h2>',
    '<h3>目标</h3>',
    '<p>确保 GEO 表现持续稳定提升，应对 AI 模型更新和市场变化。</p>',

    '<h3>运营节奏</h3>',
    '<pre lang="text">┌──────────────┐    ┌──────────────┐    ┌──────────────┐\n│  周度运营    │    │  月度复盘    │    │  季度战略    │\n│  (内容/监控) │    │  (数据/调整)  │    │  (方向/迭代)  │\n└──────────────┘    └──────────────┘    └──────────────┘\n       ↓                   ↓                   ↓\n   运营级报告          执行级报告           战略级报告</pre>',

    '<h3>交付物</h3>',
    '<table><colgroup><col width="140"/><col width="60"/><col width="100"/><col width="140"/></colgroup><thead><tr><th>交付物</th><th>频次</th><th>格式</th><th>备注</th></tr></thead><tbody>',
    '<tr><td>GEO 周报</td><td>每周</td><td>一页纸（PPT/PDF）</td><td>本周关键变化 + 内容产出 + 异常提醒</td></tr>',
    '<tr><td>GEO 月度报告</td><td>每月</td><td>PPT</td><td>全维度复盘，含趋势分析和优化建议</td></tr>',
    '<tr><td>GEO 季度战略报告</td><td>每季度</td><td>PPT</td><td>行业趋势、策略迭代、ROI 复盘</td></tr>',
    '<tr><td>实时监控面板</td><td>持续</td><td>飞书/DataV</td><td>AI 能见度实时数据</td></tr>',
    '</tbody></table>',

    '<h3>监控报警机制</h3>',
    '<pre lang="text">GEO 监控三级报警\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n🔴 P0 — 紧急\n  触发条件：品牌在 AI 回复中的提及率单周下降 ≥30%\n  响应时间：4 小时内\n  动作：根因分析 → 紧急内容调优 → 48 小时内恢复\n\n🟡 P1 — 警告\n  触发条件：核心关键词 AI 覆盖率下降 ≥15% 或竞品新内容超越\n  响应时间：24 小时内\n  动作：差距分析 → 内容更新计划\n\n🔵 P2 — 关注\n  触发条件：新 AI 模型上线/版本更新导致回复模式变化\n  响应时间：3 个工作日内\n  动作：适配性评估 → 策略微调</pre>',

    '<h3>退出标准（合同到期/终止）</h3>',
    '<checkbox done="false">最终复盘报告交付</checkbox>',
    '<checkbox done="false">客户方独立运营能力交接完成</checkbox>',
    '<checkbox done="false">数据资产（基线/趋势/方法论）完整移交</checkbox>',
    '<checkbox done="false">过渡期支持安排明确</checkbox>',
])

# ============================================================
# Batch 5: Part 2 - Data Infrastructure
# ============================================================
batch5 = "\n".join([
    '<h1>第二部分：数据基础设施</h1>',
    '<h2>2.1 数据架构全景</h2>',
    '<p>数据架构分为四个层次：采集层 → 存储层 → 分析层 → 消费层。</p>',
    '<pre lang="text">                    ┌──────────────────────────────────────┐\n                    │           数据消费层                  │\n                    │  ├─ 客户仪表盘（实时可见度）            │\n                    │  ├─ 内部管理面板（运营指标）            │\n                    │  ├─ 报表自动生成引擎                   │\n                    │  └─ AI 趋势预警系统                    │\n                    └──────────────┬───────────────────────┘\n                                   │\n                    ┌──────────────┴───────────────────────┐\n                    │           数据分析层                   │\n                    │  ├─ GEO SCORE 评分引擎                │\n                    │  ├─ 竞品对标分析                      │\n                    │  ├─ 内容效果归因模型                   │\n                    │  ├─ 趋势预测                          │\n                    │  └─ ROI 测算模型                      │\n                    └──────────────┬───────────────────────┘\n                                   │\n                    ┌──────────────┴───────────────────────┐\n                    │           数据存储层                   │\n                    │  ├─ 客户维度数据                      │\n                    │  ├─ AI 回复快照库（时间序列）           │\n                    │  ├─ 竞品数据库                        │\n                    │  ├─ 关键词库                          │\n                    │  └─ 内容资产库                        │\n                    └──────────────┬───────────────────────┘\n                                   │\n                    ┌──────────────┴───────────────────────┐\n                    │           数据采集层                   │\n                    │  ├─ AI 搜索查询采集脚本                │\n                    │  ├─ 搜索引擎 API 集成                  │\n                    │  ├─ 爬虫数据管道                      │\n                    │  ├─ 客户数据对接                      │\n                    │  └─ 第三方工具数据源                   │\n                    └──────────────────────────────────────┘</pre>',

    '<h2>2.2 核心数据表结构</h2>',
    '<h3>客户维度表（client_dim）</h3>',
    '<table><colgroup><col width="120"/><col width="80"/><col width="200"/></colgroup><thead><tr><th>字段</th><th>类型</th><th>说明</th></tr></thead><tbody>',
    '<tr><td>client_id</td><td>string</td><td>唯一客户 ID</td></tr>',
    '<tr><td>company_name</td><td>string</td><td>公司名</td></tr>',
    '<tr><td>industry</td><td>string</td><td>行业分类</td></tr>',
    '<tr><td>geo_maturity</td><td>int</td><td>GEO 成熟度评分（0-100）</td></tr>',
    '<tr><td>contract_start</td><td>date</td><td>合同开始日期</td></tr>',
    '<tr><td>contract_end</td><td>date</td><td>合同结束日期</td></tr>',
    '<tr><td>status</td><td>enum</td><td>active/paused/completed</td></tr>',
    '<tr><td>account_manager</td><td>string</td><td>负责人</td></tr>',
    '<tr><td>engagement_phase</td><td>enum</td><td>0/1/2/3/4</td></tr>',
    '</tbody></table>',

    '<h3>AI 能见度快照表（ai_visibility_snapshot）</h3>',
    '<table><colgroup><col width="140"/><col width="80"/><col width="200"/></colgroup><thead><tr><th>字段</th><th>类型</th><th>说明</th></tr></thead><tbody>',
    '<tr><td>snapshot_id</td><td>string</td><td>快照 ID</td></tr>',
    '<tr><td>client_id</td><td>string</td><td>客户 ID</td></tr>',
    '<tr><td>platform</td><td>enum</td><td>ChatGPT/Perplexity/SGE/豆包/文心一言</td></tr>',
    '<tr><td>query</td><td>string</td><td>查询关键词</td></tr>',
    '<tr><td>brand_mentioned</td><td>boolean</td><td>是否被引用</td></tr>',
    '<tr><td>mention_position</td><td>int</td><td>引用位置（1=首条，0=未出现）</td></tr>',
    '<tr><td>mention_snippet</td><td>text</td><td>引用原文片段</td></tr>',
    '<tr><td>competitor_count</td><td>int</td><td>同查询中被引用的竞品数</td></tr>',
    '<tr><td>snapshot_date</td><td>datetime</td><td>采集时间戳</td></tr>',
    '</tbody></table>',

    '<h3>内容资产表（content_assets）</h3>',
    '<table><colgroup><col width="120"/><col width="80"/><col width="200"/></colgroup><thead><tr><th>字段</th><th>类型</th><th>说明</th></tr></thead><tbody>',
    '<tr><td>content_id</td><td>string</td><td>内容 ID</td></tr>',
    '<tr><td>client_id</td><td>string</td><td>客户 ID</td></tr>',
    '<tr><td>title</td><td>string</td><td>标题</td></tr>',
    '<tr><td>url</td><td>string</td><td>发布链接</td></tr>',
    '<tr><td>content_type</td><td>enum</td><td>article/video/infographic/report</td></tr>',
    '<tr><td>publish_date</td><td>date</td><td>发布日期</td></tr>',
    '<tr><td>schema_types</td><td>json</td><td>使用的 Schema 类型列表</td></tr>',
    '<tr><td>word_count</td><td>int</td><td>字数</td></tr>',
    '<tr><td>keywords</td><td>json</td><td>核心关键词</td></tr>',
    '<tr><td>ai_citation_count</td><td>int</td><td>被 AI 引用的次数</td></tr>',
    '<tr><td>last_updated</td><td>datetime</td><td>最后更新时间</td></tr>',
    '</tbody></table>',
])

# ============================================================
# Batch 6: Data Infrastructure cont. + Part 3 (Report System)
# ============================================================
batch6 = "\n".join([
    '<h3>竞品对标表（competitor_benchmark）</h3>',
    '<table><colgroup><col width="140"/><col width="80"/><col width="200"/></colgroup><thead><tr><th>字段</th><th>类型</th><th>说明</th></tr></thead><tbody>',
    '<tr><td>benchmark_id</td><td>string</td><td>对标 ID</td></tr>',
    '<tr><td>client_id</td><td>string</td><td>客户 ID</td></tr>',
    '<tr><td>competitor_name</td><td>string</td><td>竞品名称</td></tr>',
    '<tr><td>competitor_url</td><td>string</td><td>竞品域名</td></tr>',
    '<tr><td>dimension</td><td>enum</td><td>AI可见度/内容质量/技术基建/权威性</td></tr>',
    '<tr><td>client_score</td><td>float</td><td>客户得分</td></tr>',
    '<tr><td>competitor_score</td><td>float</td><td>竞品得分</td></tr>',
    '<tr><td>gap</td><td>float</td><td>差距（负值=落后）</td></tr>',
    '<tr><td>snapshot_date</td><td>datetime</td><td>采集时间</td></tr>',
    '</tbody></table>',

    '<h2>2.3 GEO SCORE 评分算法</h2>',
    '<h3>评分公式</h3>',
    '<pre lang="text">GEO SCORE = Σ(W_i × S_i) / Σ(W_i) × 100\n\n其中：\n  W_i = 第 i 个维度的权重\n  S_i = 第 i 个维度的归一化得分（0-1）</pre>',

    '<h3>权重配置（默认版）</h3>',
    '<table><colgroup><col width="100"/><col width="60"/><col width="240"/></colgroup><thead><tr><th>维度</th><th>权重</th><th>说明</th></tr></thead><tbody>',
    '<tr><td>AI 可见度</td><td>30%</td><td>最核心的输出指标</td></tr>',
    '<tr><td>内容权威性</td><td>20%</td><td>AI 模型选择内容的标准</td></tr>',
    '<tr><td>技术基建</td><td>20%</td><td>Schema/语义结构化是基础门槛</td></tr>',
    '<tr><td>内容质量</td><td>15%</td><td>影响引用深度</td></tr>',
    '<tr><td>品牌信号</td><td>10%</td><td>长期信任积累</td></tr>',
    '<tr><td>结构化知识</td><td>5%</td><td>增量优势项</td></tr>',
    '</tbody></table>',

    '<h3>子项评分规则（示例：AI 可见度）</h3>',
    '<pre lang="text">AI 可见度评分 = 0.4 × 品牌提及率 + 0.3 × 覆盖率 + 0.2 × 首屏占比 + 0.1 × 引用正面度\n\n其中：\n  - 品牌提及率 = 提及品牌的查询数 / 总查询数\n  - 覆盖率 = 品牌出现的 AI 平台数 / 总平台数\n  - 首屏占比 = 排在第一的查询数 / 总提及查询数\n  - 引用正面度 = AI 中品牌内容正向/中性回复比例</pre>',
])

# ============================================================
# Batch 7: Part 3 - Report System
# ============================================================
batch7 = "\n".join([
    '<h1>第三部分：报告体系（三级报告架构）</h1>',
    '<pre lang="text">报告体系分级\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n★ 战略级（Tier 1）\n   面向：客户 C-Level / 决策层\n   频次：月度 / 季度\n   内容：BI 呈现，讲"结果"而非"过程"\n   格式：精美 PPT（≤15 页）\n\n★★ 执行级（Tier 2）\n   面向：客户对接人 / 项目团队\n   频次：双周\n   内容：进度追踪 + 数据变化 + 下期计划\n   格式：工作 PPT（≤10 页）\n\n★★★ 运营级（Tier 3）\n   面向：内部执行团队\n   频次：每周\n   内容：原始数据 + 明细 + 问题清单\n   格式：一页纸 + 数据附件</pre>',

    '<h2>3.1 战略级报告模板（Tier 1）</h2>',
    '<pre lang="text">Page 1: 封面\n  标题：[月份/季度] GEO 表现回顾\n  副标题：[客户名称] × [咨询方]\n  日期\n\nPage 2: 执行摘要（Executive Summary）\n  一句话结论 + 3 个关键数据点 + 本期重点事项\n\nPage 3: GEO SCORE 总览\n  趋势图 + 当前分数 vs 基线 vs 目标 + 7 维度雷达图\n\nPage 4-5: AI 能见度分析\n  各平台可见度对比 + 核心关键词覆盖率 + 提及内容 Top 10\n\nPage 6-7: 竞品对标\n  竞品得分对比 + 差距变化趋势 + 竞品预警\n\nPage 8-9: 内容效果分析\n  AI 引用率 + 高绩效特征提炼 + 内容类型分布\n\nPage 10-11: ROI 回顾\n  实际产出 vs 计划 + 趋势对比\n\nPage 12-13: 下期策略建议\n  加大投入领域 + 调整方向 + 下季度目标\n\nPage 14: 附录 - 方法论说明 / 数据源说明 / 术语表</pre>',

    '<h3>呈现原则（McKinsey 标准）</h3>',
    '<pre lang="text">1. 结论先行（Pyramid Principle）\n   - 每一页第一句话就是这页的结论\n   - 后面的数据/图表是对结论的支撑\n\n2. MECE 分解\n   - 每个分析维度互斥且穷尽\n   - "其他"类别不超过总篇幅的 10%\n\n3. 数据可视化\n   - 一个图表只讲一个故事\n   - 颜色编码：绿色=达标，黄色=警告，红色=未达标\n   - 避免饼图，优先使用条形图/线图/瀑布图\n\n4. 标题即结论\n   ❌ "AI 可见度分析"\n   ✅ "Q3 核心关键词 AI 引用率提升 25%，首屏占比达 40%"\n\n5. 1-3-5 原则\n   - 每页不超过 1 个核心观点\n   - 不超过 3 个支撑论据\n   - 不超过 5 个数据点</pre>',

    '<h2>3.2 执行级报告模板（Tier 2）</h2>',
    '<p>双周汇报结构：</p>',
    '<pre lang="text">1. 本期概览（一页）\n   - GEO SCORE 变化（+/- X%）\n   - 关键指标快照\n   - 里程碑完成情况\n\n2. 内容产出统计\n   - 发布篇数 vs 计划\n   - 内容质量评分（质量门禁通过率）\n   - Schema 覆盖率变化\n\n3. AI 能见度变化\n   - 重点关键词变化（Query-level）\n   - 新增/消失的引用\n   - 异常事件\n\n4. 技术和基建进展\n   - Schema 实施进度\n   - 页面优化完成情况\n\n5. 下期计划\n   - Sprint 目标\n   - 优先级调整\n\n6. 风险与问题\n   - 风险登记表 + 待决策事项</pre>',

    '<h2>3.3 运营级报告模板（Tier 3）</h2>',
    '<p>每周一页纸结构：</p>',
    '<pre lang="text">┌──────────────────────────────────────────────┐\n│  GEO 周度运营报告                             │\n│  [客户名称] | W/W [周数] | [日期范围]          │\n├──────────────────────────────────────────────┤\n│                                               │\n│  内容产出: [N] 篇   质量评分: [N]/100           │\n│                                               │\n│  本周完成                                      │\n│  • [内容标题 1]  → 已发布                       │\n│  • [内容标题 2]  → 已发布                       │\n│  • [优化项]    → 完成                          │\n│                                               │\n│  异常监控: 🟢 正常 / 🟡 注意 / 🔴 紧急          │\n│                                               │\n│  下周计划                                      │\n│  • [内容计划]                                  │\n│  • [优化项]                                    │\n│  • [待客户确认事项]                            │\n└──────────────────────────────────────────────┘</pre>',
])

# ============================================================
# Batch 8: Part 4 - Quality System + Author Info
# ============================================================
batch8 = "\n".join([
    '<h1>第四部分：交付标准与质量体系</h1>',
    '<h2>4.1 交付物质量标准（McKinsey 级）</h2>',
    '<table><colgroup><col width="80"/><col width="200"/><col width="120"/></colgroup><thead><tr><th>维度</th><th>标准</th><th>检查方式</th></tr></thead><tbody>',
    '<tr><td>结构力</td><td>每个交付物有清晰的叙事线；结论先行</td><td>内部审阅</td></tr>',
    '<tr><td>数据严谨</td><td>所有数据标注来源、采集时间、精度</td><td>数据溯源检查</td></tr>',
    '<tr><td>视觉一致性</td><td>统一色板、字体、图标体系、布局模板</td><td>模板化</td></tr>',
    '<tr><td>零错误</td><td>数据无计算错误，无错别字，无断裂链接</td><td>双人校验</td></tr>',
    '<tr><td>交付时效</td><td>按 SOW 约定时间 ±1 个工作日内</td><td>项目管理系统追踪</td></tr>',
    '</tbody></table>',

    '<h2>4.2 内部审阅流程</h2>',
    '<pre lang="text">初稿完成\n    ↓（内部）\n第一轮审阅（Peer Review）\n    ┣━ 数据准确性核对\n    ┣━ 逻辑完整性检查\n    ┣━ 拼写/格式/排版\n    ↓\n修改稿\n    ↓（内部）\n第二轮审阅（Manager Review）\n    ┣━ 战略层面：叙事线是否成立\n    ┣━ 执行层面：建议是否可落地\n    ┣━ 风险层面：有无遗漏风险\n    ↓\n终稿定版\n    ↓（客户）\n交付 → 确认 → 归档</pre>',

    '<h2>4.3 术语表（Glossary）</h2>',
    '<table><colgroup><col width="100"/><col width="120"/><col width="200"/></colgroup><thead><tr><th>术语</th><th>英文</th><th>定义</th></tr></thead><tbody>',
    '<tr><td>GEO</td><td>Generative Engine Optimization</td><td>为 AI 生成引擎优化内容</td></tr>',
    '<tr><td>AI 可见度</td><td>AI Visibility</td><td>品牌在 AI 模型回复中的出现频率</td></tr>',
    '<tr><td>AI 引用率</td><td>AI Citation Rate</td><td>品牌被引用的查询数占比</td></tr>',
    '<tr><td>Schema 标签</td><td>Structured Data Markup</td><td>使用 schema.org 标准标记网页</td></tr>',
    '<tr><td>内容权威性</td><td>Content Authority</td><td>内容被外部可信源引用的程度</td></tr>',
    '<tr><td>品牌信号</td><td>Brand Signals</td><td>品牌被 AI 识别的可信信号</td></tr>',
    '<tr><td>GEO SCORE</td><td>—</td><td>综合多维度的 GEO 评分</td></tr>',
    '<tr><td>MECE</td><td>Mutually Exclusive, Collectively Exhaustive</td><td>互斥且穷尽的分解原则</td></tr>',
    '<tr><td>Pyramid Principle</td><td>—</td><td>结论先行的沟通结构</td></tr>',
    '</tbody></table>',

    '<h2>4.4 客户验收清单</h2>',
    '<p>项目结束或里程碑交付时，客户按此清单确认：</p>',
    '<pre lang="text">□ Phase 1 交付物完整接收\n   - [ ] 当前状态评估报告\n   - [ ] GEO SCORE 基线\n   - [ ] 竞品对标矩阵\n   - [ ] 差距分析\n\n□ Phase 2 交付物完整接收\n   - [ ] GEO 策略蓝图\n   - [ ] 内容矩阵规划\n   - [ ] 实施路线图\n   - [ ] ROI 预测模型\n\n□ Phase 3 交付物完整接收\n   - [ ] 产出的内容资产\n   - [ ] Schema 实施记录\n   - [ ] 技术优化清单\n   - [ ] 质量门禁记录\n\n□ Phase 4 交付物完整接收\n   - [ ] 运营报告（按月/季归档）\n   - [ ] 监控面板\n   - [ ] 知识转移材料\n   - [ ] 最终复盘报告\n\n□ 结项确认\n   - [ ] 所有合同约定的交付物已交付\n   - [ ] 客户方已确认验收\n   - [ ] 尾款支付完成\n   - [ ] 过渡期/维护期安排确认</pre>',

    # Footer
    '<hr/>',
    '<p><b>作者信息</b></p>',
    '<p>海风老师 | AI技术咨询 / LoRA模型训练 / 电商AI落地 / GEO优化</p>',
    '<p>微信：frankhzheng</p>',
    '<p>内容资产库：https://github.com/frankhzh-source/hf-ai-articles</p>',
    '<p/><p>本文档版本 v1.0，日期 2026-07-06，基于 McKinsey 咨询方法论，结合 AI 搜索引擎生态定制。</p>',
])

# ============================================================
# Execute batches
# ============================================================
batches = [
    (batch2, "Batch 2 - Phase 2"),
    (batch3, "Batch 3 - Phase 3"),
    (batch4, "Batch 4 - Phase 4"),
    (batch5, "Batch 5 - Part 2 Data"),
    (batch6, "Batch 6 - Data cont + Score"),
    (batch7, "Batch 7 - Part 3 Reports"),
    (batch8, "Batch 8 - Part 4 Quality + Author"),
]

all_ok = True
for xml, label in batches:
    if not append_content(xml, label):
        all_ok = False
        break

if all_ok:
    print("\n=== ALL BATCHES COMPLETED SUCCESSFULLY ===")
    print("Doc URL: https://cp8z7brjmy.feishu.cn/docx/TR9nd7lfso2nU0xnipyc4vcpnpd")
else:
    print("\n=== SOME BATCHES FAILED ===")
    sys.exit(1)
