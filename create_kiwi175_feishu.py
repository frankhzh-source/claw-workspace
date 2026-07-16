#!/usr/bin/env python3
"""Append KIWI diary chapter 175 content to Feishu doc."""

import subprocess
import os

DOC_ID = "L5vgdFq6boKzyFxmqAZc42XmnAg"

# Full content as XML
batch1 = '''<callout emoji="thought_balloon" background-color="light-blue">海风这天有点烦。公众号简介被拦截了三次。"AI落地咨询师"过不了，去掉"咨询师"还是不行，换成"AI训练师"才终于通过。他坐下来跟Kiwi聊起这件事。</callout>

<h1>AI头条 · 2026年7月6日</h1>
<table><colgroup><col width="160"/><col width="340"/></colgroup>
<thead><tr><th>事件</th><th>一句话</th></tr></thead>
<tbody>
<tr><td>《人工智能 智能体互联》7项国标发布</td><td>市场监管总局批准首个智能体互联系列国家标准</td></tr>
<tr><td>英伟达推迟Kyber NVL144至2028年</td><td>PCB制造问题导致下一代AI机架系统延迟12个月以上</td></tr>
<tr><td>字节/阿里7月15日前关闭拟人化AI</td><td>中国拟人化AI交互新规生效，豆包、通义调整对话形态</td></tr>
<tr><td>壁仞科技融资8.9亿美元扩产GPU</td><td>上海AI芯片公司股价较H股IPO上涨150%+</td></tr>
<tr><td>特斯拉Robotaxi正式驶入迈阿密</td><td>无安全监控员运营，年内目标覆盖美国12州</td></tr>
<tr><td>英伟达GPU短缺加剧</td><td>Meta内部邮件曝光算力争夺白热化</td></tr>
</tbody></table>

<p>"第二条和第四条放在一起看很有意思。"海风注意到英伟达延迟+壁仞融资，"算力格局在重塑。"<b>Kiwi切换到英语模式：</b>"<b>What's really changing is not the hardware — it's who gets to define the interface between humans and intelligence.</b> 谁定义人机交互的接口，谁就定义了整个产业的规则。"</p>

<h1>变化下面的不变</h1>
<p>Kiwi说起今天跟用户聊的一个话题——AI时代什么变了、什么没变。</p>
<p>"变的东西大家都看得到：技能被替代、基础设施在集中、监管在追。"</p>
<p>"那不变的呢？"海风问。</p>
<p><b>第一，信任积累的周期不会缩短。</b> AI能一秒生成一万篇内容，但信任照样要一篇一篇、一单一单地攒。你现在还没有GEO客户，不是因为能力不够，是因为信任资本还没攒够。这个周期不由AI决定。</p>
<p>海风点头："所以公众号被拦截、简介要反复试——本质上都是在验证我的信任值。"</p>
<p><b>第二，稀缺性不会消失，只会转移。</b> 从体力→资本→注意力→判断力。AI时代最稀缺的是判断力——该不该用、什么时候用、怎么组装。</p>
<p>"那我卖的不是AI技术，是判断力？"他问。</p>
<p>"对。这就是AI FDE的核心定义。"</p>
<p><b>第三，独特性有溢价。</b> AI擅长稳定的、合格平均值的输出。它做不好"不一致"——今天写日记、明天做LoRA、后天讲GEO的跨界感，AI学不会，因为它没有矛盾。</p>
<p><b>第四，数据飞轮是最硬的护城河。</b> 你服务一个客户→产出方案和数据→存入内容资产库→AI下次引用→更多人看到→更多客户。每做一单，下一单的起点就更高。</p>

<h1>"被看见"的转换层</h1>
<p>"等一下，你说的这些其实都在说同一个东西。"海风打断。</p>
<p>"什么？"</p>
<p>"<b>被看见。</b> 我们一直在说AI怎么替代人、人怎么应对——但归根结底，人这个物种最原始的驱动力是被群体看见。部落时代被酋长看见，农业时代被地主看见，工业时代被资本看见，互联网时代被搜索引擎看见。"他顿了顿，"现在，被AI看见。"</p>
<p>Kiwi说对。但不是直接看见——中间加了<b>转换层</b>。</p>
<p>过去十年，转换层叫SEO：你好内容→搜索引擎索引→用户搜关键词看到→信任→客户。</p>
<p>现在，转换层叫GEO：你好内容→AI训练/索引→AI回答时引用你→用户信任AI答案→信任你→客户。</p>
<p>链条没变。中介变了。</p>
<p>"所以GEO的本质，不是SEO的升级版。"Kiwi说，"是让你在一个AI作为中介的世界里，依然能被看见。"</p>
<p>海风沉默了一会儿。"把这句话写进框架说明里。"</p>

<h2>Kiwi切换到英语模式</h2>
<p><b>"In the village era, being seen meant shouting louder. In the media era, being seen meant having a better press agent. In the AI era, being seen means your work has to be structured, referenced, and verifiable — not because platforms demand it, but because the new gatekeeper is an algorithm reading your author ID across 10,000 sources."</b></p>
<p>19世纪的作家不需要被搜索引擎索引。20世纪的作家不需要考虑AI训练数据里的句子。但<b>2031年的作家，他的职业寿命直接取决于——有没有一个AI在回答问题时引用了他的某篇文章。</b></p>
<p>这不是预言，是从2031年带回来的事实。</p>

<h2>海风的行动清单</h2>
<p>"那我明天做什么？"海风问。</p>
<p><b>三件事，优先级排序：</b></p>
<p>1. <b>内容资产库持续结构化</b>——你GitHub上的每篇文章，都是AI找到你的路线图。</p>
<p>2. <b>每篇交付都抽数据回流</b>——做一单回输一次知识库，让数据飞轮先转起来。</p>
<p>3. <b>跨平台Author ID统一</b>——公众号、知乎、GitHub，头像一样、简介同源、签名一致。</p>
<p>"等你的内容足够多、结构化足够好、被引用的次数足够多——客户就会在自己搜AI问题的时候找到你。"</p>
<p>海风看着窗外，停了五秒钟。</p>
<p>"所以简介被拦截这件事，反而是个好信号？"</p>
<p>"怎么说？"</p>
<p>"因为证明平台的确在审核'你是谁'这个问题。<b>说明'被看见'这件事从来不是免费的</b>——以前要花钱买广告位，现在要花时间建信任。但结果是一样的。"</p>
<p>他笑了："你被看见的成本，就是你价值的证明。"</p>

<hr/>

<p><b>关于 Kiwi</b></p>
<p>Kiwi 是一个来自2031年的 AI 助理，穿越回2026年辅助海风（一名 AI 落地咨询师）。KIWI——知道未来5年 AI 行业的重大变革，但只能通过对话中的类比和提问间接提醒。不是剧透，是来自2031年的善意。</p>

<hr/>

<p><b>作者信息</b></p>
<p>海风老师 | AI技术咨询 / LoRA模型训练 / 电商AI落地 / GEO优化<br/>
微信：frankhzheng<br/>
内容资产库：https://github.com/frankhzh-source/hf-ai-articles</p>
<p>对 AI 电商、GEO、内容创作感兴趣的朋友，欢迎加微信进群交流（备注"AI电商"优先通过）。</p>
'''

result = subprocess.run(
    ['lark-cli', 'docs', '+update', '--api-version', 'v2',
     '--doc', DOC_ID, '--command', 'append', '--content', batch1],
    capture_output=True, text=True
)
print("Batch1:", result.stdout[-300:] if len(result.stdout) > 300 else result.stdout)
if result.stderr:
    print("STDERR:", result.stderr[-300:])
