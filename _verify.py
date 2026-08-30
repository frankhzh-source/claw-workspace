# -*- coding: utf-8 -*-
"""
信息核验工具 _verify.py

用途：交付前扫描 Markdown 文档，自动提取所有事实性断言，
      对照「已核实信息库」输出待核实清单，防止未核实信息流入交付物。

用法：
    python _verify.py <文件.md>

输出：
    1. 🚨 黑名单命中（已否证信息，必须删除）
    2. ⚠️  待核实清单（数字/公司名/条款/链接，需逐条核）
    3. ✅ 已核实引用（来自信息库，可放心用）

作者：海风 · AI 落地咨询 & GEO 优化 ｜ 微信：frankhzheng
"""

import re
import sys
from pathlib import Path

# ============================================================
# 已否证信息（黑名单）—— 出现即报警
# ============================================================
BLACKLIST = {
    '鉴真数检': '仅见于一篇搜狐软文，无官网/工商/独立信源 → 不可考，删除',
    '恢复周期': '标准原文逐词检索 0 次 → 删除，改用「责任错位 + 重建证据链」',
    '七大维度': '百度百科「市场衍生框架」，非标准内容 → 改为「5 大方面 10 大要求项」',
    '32 项': '同上，非标准内容',
    '32项': '同上，非标准内容',
    '91.7': '迪普智见自报数据（阿里云/腾讯云软文）→ 删除数字，只讲方法',
    '34.2': '同上',
    'T/CAPT 026—2024': '官方公告笔误 → 正确为 T/CAPT 026—2026',
    'T/CAPT 026-2024': '官方公告笔误 → 正确为 T/CAPT 026—2026',
    'YD/T 3980': '错误编号 → 正确为 AIIA/T 0277—2026',
}

# ============================================================
# 已核实信息（白名单）—— 命中即放行
# ============================================================
WHITELIST_TERMS = [
    # 标准条款（已核到页码）
    '7.2 语料接入与发布', '黑名单管理机制', '定期复核',
    '6.2 核心事实主张证据核验', '九项溯源要素', '九项证据要素',
    '7.6 应急处置', '全部费用由服务商承担',
    '8.1 违规分级说明', '可恢复性',
    '9.4 四大核心指标', '有效提及', '信息准确率',
    '9.5 评价结果应用', '应判定服务不合格',
    '5 大方面', '10 大要求项', '10大要求项',
    'AIIA/T 0277—2026', 'T/CAPT 026—2026', 'T/CGCC 119—2026',
    '8.4 异常熔断', '1 小时内启动初步响应', '4 小时内完成初步止损',
    # 公司（已三重验证）
    'AIDSO 爱搜', '搜极星', 'sougeo.com', '有赞', '加我推荐官',
    '信通院', '中国信通院', '中国泰尔实验室',
    # 已核实事件
    'T/CAPT 026', 'T/CGCC 119', 'AIIA/T 0277',
]

# ============================================================
# 提取规则
# ============================================================

# 数字类断言：带单位的数字（百分比/金额/时长/规模/次数）
NUM_PATTERNS = [
    (r'\d+(?:\.\d+)?\s*%', '百分比'),
    (r'\d+(?:\.\d+)?\s*(?:亿|万|千)\s*(?:元|人民币)?', '金额/规模'),
    (r'\d+(?:\.\d+)?\s*(?:年|个月|天|小时|分钟|周)', '时间长度'),
    (r'\d+(?:\.\d+)?\s*(?:家|个|次|条|项|万次)', '计数'),
]

# 标准条款引用
CLAUSE_PATTERN = r'(?:T/[A-Z]{2,5}\s?\d{2,4}[-—]\d{4}|AIIA/T\s?\d{2,4}[-—]\d{4})'

# 链接
URL_PATTERN = r'https?://[^\s\)\]（(]+'


def check_blacklist(text: str):
    """检查黑名单（已否证信息）

    区分两种情况：
    - 实际误用（当作事实引用）→ 🚨 必改
    - 更正说明中引用（明确标注其不可考）→ ⚠️ 可保留
    """
    hits = []
    notes = []
    # 出现这些标记，说明是在做「更正/否证/修订说明」，不是误用
    note_marks = ['❌', '⚠️', '已否证', '不可考', '已撤回', '删除', '错误',
                  '虚构', '存疑', '不采信', '不是标准', '0 次', '仅见于',
                  '改为', '→', '修订', 'v1', '旧',
                  # 对比说明（引用错误说法是为了否定它）
                  '为什么这比', '而非', '而不是', '并非', '实为', '真实结构是',
                  '正确为', '应为', '实为',
                  # 否证引用（说明这是别人的/不靠谱的说法）
                  '自报', '自测', '流传', '传闻', '声称', '宣称', '市面上',
                  '不引用', '不采信', '不可考', '未核实', '溯源下来',
                  # 错误清单表（文档自身在记录错误）
                  '二手源污染', '一手源读取失误', '判断摇摆', '类型']
    # 白名单词出现即视为「同行有正确说法」→ 判定为对比说明
    lines = text.split('\n')
    for i, line in enumerate(lines, 1):
        for term, reason in BLACKLIST.items():
            if term not in line:
                continue
            has_note_mark = any(m in line for m in note_marks)
            has_whitelist = any(w in line for w in WHITELIST_TERMS)
            # 表格行（含 |）且同行有正确说法 → 也是对比说明
            is_table = '|' in line
            if has_note_mark or has_whitelist or (is_table and has_whitelist):
                notes.append((term, i, reason, line.strip()[:70]))
            else:
                hits.append((term, i, reason, line.strip()[:70]))
    return hits, notes


def extract_numbers(text: str):
    """提取数字类断言，过滤白名单上下文"""
    results = []
    lines = text.split('\n')
    for i, line in enumerate(lines, 1):
        # 跳过白名单行（已核实）
        if any(w in line for w in WHITELIST_TERMS):
            continue
        for pat, kind in NUM_PATTERNS:
            for m in re.finditer(pat, line):
                ctx = line.strip()
                if len(ctx) > 90:
                    ctx = ctx[:90] + '…'
                results.append((kind, m.group(), i, ctx))
    return results


def extract_clauses(text: str):
    """提取标准条款引用"""
    results = []
    lines = text.split('\n')
    for i, line in enumerate(lines, 1):
        for m in re.finditer(CLAUSE_PATTERN, line):
            ctx = line.strip()
            if len(ctx) > 90:
                ctx = ctx[:90] + '…'
            results.append((m.group(), i, ctx))
    return results


def extract_companies(text: str):
    """启发式提取可能的公司名（书名号/引号内 + 「公司/科技/数据」等后缀）"""
    results = []
    lines = text.split('\n')
    # 公司后缀关键词
    suffix = r'(?:科技|技术|数据|信息|网络|智能|传媒|文化|数字)(?:有限公司|股份|集团|公司)?'
    pat = rf'[一-鿿A-Za-z0-9]{{2,12}}{suffix}'
    for i, line in enumerate(lines, 1):
        if any(w in line for w in WHITELIST_TERMS):
            continue
        for m in re.finditer(pat, line):
            name = m.group()
            if len(name) < 4:
                continue
            results.append((name, i))
    return results


def extract_urls(text: str):
    """提取链接"""
    results = []
    lines = text.split('\n')
    for i, line in enumerate(lines, 1):
        for m in re.finditer(URL_PATTERN, line):
            url = m.group().rstrip('。，、；）)】]')
            # 跳过 GitHub / 微信等自有链接
            if any(d in url for d in ['github.com', 'frankhzh']):
                continue
            results.append((url, i))
    return results


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.exists():
        print(f'文件不存在: {path}')
        sys.exit(1)

    text = path.read_text(encoding='utf-8')

    print('=' * 72)
    print(f'信息核验报告：{path.name}')
    print('=' * 72)

    # 1. 黑名单（最高优先级）
    bl, notes = check_blacklist(text)
    print()
    if bl:
        print(f'🚨 【必改】黑名单实际误用 {len(bl)} 处（已否证信息被当事实引用）')
        print('-' * 72)
        for term, line, reason, ctx in bl:
            print(f'  行 {line:>4}  「{term}」')
            print(f'          | {ctx}')
            print(f'          → {reason}')
    else:
        print('✅ 【通过】无黑名单实际误用')

    if notes:
        print()
        print(f'📝 【可保留】更正说明中引用黑名单 {len(notes)} 处（已标注不可考，属正常）')
        print('-' * 72)
        seen = set()
        for term, line, reason, ctx in notes:
            if term in seen:
                continue
            seen.add(term)
            print(f'  行 {line:>4}  「{term}」→ {ctx}')

    # 2. 数字类断言
    nums = extract_numbers(text)
    print()
    print(f'⚠️  【待核】数字类断言 {len(nums)} 处')
    print('-' * 72)
    if nums:
        by_kind = {}
        for kind, val, line, ctx in nums:
            by_kind.setdefault(kind, []).append((val, line, ctx))
        for kind, items in by_kind.items():
            print(f'  ▸ {kind}（{len(items)} 处）')
            for val, line, ctx in items[:8]:
                print(f'      行 {line:>4}  {val:<14} | {ctx}')
            if len(items) > 8:
                print(f'      … 还有 {len(items) - 8} 处')
    print('  核验要求：① 谁测的 ② 怎么测的 ③ 有无利益关系')

    # 3. 标准条款引用
    clauses = extract_clauses(text)
    print()
    print(f'⚠️  【待核】标准条款引用 {len(clauses)} 处')
    print('-' * 72)
    seen = set()
    for c, line, ctx in clauses:
        key = (c, line // 10)
        if key in seen:
            continue
        seen.add(key)
        print(f'  行 {line:>4}  {c}')
        print(f'          | {ctx}')
    print('  核验要求：打开原文 PDF，确认章节号 + 物理页码 + 50 字符上下文')

    # 4. 公司名
    comps = extract_companies(text)
    uniq = {}
    for name, line in comps:
        uniq.setdefault(name, line)
    print()
    print(f'⚠️  【待核】疑似公司名 {len(uniq)} 个')
    print('-' * 72)
    for name, line in list(uniq.items())[:15]:
        print(f'  行 {line:>4}  {name}')
    if len(uniq) > 15:
        print(f'      … 还有 {len(uniq) - 15} 个')
    print('  核验要求（三重）：① 工商注册 ② 官网可打开 ③ 独立信源或官方名单')

    # 5. 链接
    urls = extract_urls(text)
    uniq_urls = []
    for u, line in urls:
        if u not in [x[0] for x in uniq_urls]:
            uniq_urls.append((u, line))
    print()
    print(f'⚠️  【待核】外链 {len(uniq_urls)} 个')
    print('-' * 72)
    for u, line in uniq_urls[:12]:
        print(f'  行 {line:>4}  {u}')
    print('  核验要求（四重）：状态码 + 标题 + 关键词 + PDF 文件头')

    # 6. 总结
    print()
    print('=' * 72)
    total = len(bl) + len(nums) + len(clauses) + len(uniq) + len(uniq_urls)
    if bl:
        print(f'❌ 不可交付：黑名单实际误用 {len(bl)} 处，必须先修正')
    elif total == 0:
        print('✅ 未发现待核实项')
    else:
        print(f'⚠️  共 {total} 项需核验。核验后请更新「已核实信息库」')
    print()
    print('口诀：数字问出处，条款翻原文，公司查工商，链接点一遍。')
    print('=' * 72)


if __name__ == '__main__':
    main()
