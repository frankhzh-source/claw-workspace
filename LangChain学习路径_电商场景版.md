# LangChain 学习路径 — 电商AI版

> 不是从零学 Python，是从你已经会的东西出发，补上缺口。

---

## 一、你的起点

| 你已经会的 | 还缺的 |
|-----------|--------|
| 调 DeepSeek/豆包 API | LangChain 的统一封装方式 |
| 写 Prompt（手写+迭代） | LCEL 表达式、模板化管理 |
| 用 Qdrant + 向量检索 | LangChain Retrieval 的检索器抽象 |
| JSON 结构化输出 | Output Parsers 的声明式写法 |
| Git | 版本管理思路有，但没用过 Prompt Hub |

---

## 二、学习路径（按优先级）

### Phase 1: 基础速通（1周）

**目标：** 把你现在手写的代码，改成 LangChain 方式，感受差异。

| 天数 | 学习内容 | 产出 |
|------|---------|------|
| Day 1 | ChatModels + Prompts | 把你现在的 DeepSeek 调用改成 LangChain 方式 |
| Day 2 | Output Parsers + LCEL | 把 JSON 解析从手写 regex 改成 PydanticParser |
| Day 3 | Chains（LCEL 串联） | 把"写脚本→翻译→格式化"三步串成一条链 |
| Day 4 | Retrieval 基础 | 用 LangChain 连你现有的 Qdrant 向量库 |
| Day 5 | RAG 完整链路 | 做一条"用户提问→检索知识库→生成回答"的完整链 |
| Day 6-7 | 综合练习 | 把你现有的电商视频分镜工作流完整跑一遍 |

**前置知识：** Python 基础（你已经有）
**每天投入：** 1-2 小时
**产出：** 能用 LangChain 重建你现在 80% 的工作流

### Phase 2: Agent 入门（2周）

**目标：** 让 Agent 自己调用工具，而不是你手写 if-else。

| 学习内容 | 所需前置 | 电商应用场景 |
|---------|---------|------------|
| Tools 自定义 | Phase 1 | 让 Agent 自己查库存/查物流/算优惠券 |
| Tool Calling 机制 | Tools | 理解模型怎么决定调哪个工具 |
| Simple Agent（ReAct 模式） | Tool Calling | 一个 Agent 完成"查询→分析→回复"闭环 |
| Memory 持久化 | Phase 1 | 跨会话记住用户偏好尺码 |
| LangGraph 基础（节点+边） | Agent | 状态机思维，理解循环和分支 |

**前置知识：** Phase 1
**每天投入：** 1-2 小时
**产出：** 一个能自主调用 3-5 个工具的电商客服 Agent 原型

### Phase 3: 生产就绪（1个月，可选）

**目标：** Agent 能稳定跑在生产环境。

| 学习内容 | 难度 | 什么时候需要 |
|---------|------|------------|
| LangSmith 基础调试 | ⭐⭐ | Agent 上线后，出问题需要定位 |
| 评估数据集构建 | ⭐⭐⭐ | 需要量化 Agent 精度、做回归测试 |
| LangGraph 复杂状态机 | ⭐⭐⭐⭐ | 需要多 Agent 协作（如写稿+出图+审核三条线） |
| 生产部署（Docker + API） | ⭐⭐⭐ | 要把 Agent 封装成服务 |

**什么时候进入 Phase 3：** 当你发现"改了一个 Prompt，不知道影响多大"或"运营说昨天回复不对，查了半小时没找到原因"时。

---

## 三、不需要学的

| 模块 | 原因 |
|------|------|
| LangChain 文档加载器（Document Loaders） | 你不需要从 PDF/网页读数据，电商数据都是结构化的 |
| 100 种向量库对接 | 你只用 Qdrant，Chroma/Pinecone 那些暂时和你没关系 |
| 历史版本的 Chain 写法（LLMChain 等） | 官方已废弃，全部走 LCEL |
| Callbacks 深度定制 | 等到你要做自定义监控时才需要 |

---

## 四、电商场景的"最小学习包"

如果你只有 1 周时间，只学这几项就够了：

```
1. LCEL 管道符 | 语法           ← 取代你现在的函数串联
2. ChatPromptTemplate          ← 取代你硬编码的 Prompt 字符串
3. StrOutputParser / JsonOutputParser ← 取代你的 JSON 解析
4. QdrantVectorStore           ← 取代你手写的向量检索代码
5. BaseTool 自定义             ← 让 Agent 自己调库存/物流 API
```

**学完这 5 项，你就能把现在 80% 的手写代码改成 LangChain。** 改不改都行，但你会的这些概念——模板化、声明式、标准化——比 LangChain 本身重要。

---

## 五、一句话建议

> LangChain 不是你必须要学的框架，但它背后那套**组件化思维**是你必须要会的。不学 LangChain，自己手写也能实现同样的功能，只是多花一倍时间。等你哪天觉得"改一个 Prompt 要改 3 个文件太烦了"，就是该上 LangChain 的时候了。
