# -*- coding: utf-8 -*-
"""Reorganize GEO article tables: split the 6-col wide table into two PDF-safe
comparison tables, normalize all tables (bold headers, left-align, bold term
column), and emit a print-optimized HTML for guaranteed no-clip PDF export."""
import re, html

SRC = "GEO视角下的知识体系与跨学科基础.md"
OUT_MD = "GEO知识体系_完整版.md"
OUT_HTML = "GEO知识体系_打印版.html"

with open(SRC, encoding="utf-8") as f:
    text = f.read()

# ---- 1. Replace the 6-column wide table with two PDF-safe tables ----
old_block = """| 维度 | 印刷时代 | 广播时代 | 电视时代 | 搜索时代 | GEO时代 |
|-|-|-|-|-|-|
| 信息守门人 | 编辑/出版商 | 电台编辑 | 电视网 | 搜索算法 | AI知识表征 |
| 传播模型 | 一对多（慢） | 一对多（实时） | 一对多（全感官） | 多对多（交互） | AI中介（问答） |
| 可见性机制 | 版面位置 | 节目时段 | 黄金时段 | 关键词排名 | AI引用 |
| 权力结构 | 所有权中心 | 频率中心 | 频道中心 | 算法化 | 认知化 |
| 传播学理论 | 议程设置 | 两级传播 | 培养理论 | 知沟+沉默螺旋 | 涵化+拟态环境 |
| 网络模型 | 星型 | 中心化 | 高度中心化 | 无标度 | 语义网络 |
| 竞争壁垒 | 印刷机/渠道 | 牌照/发射塔 | 频道资源 | SEO技术 | 内容资产体系 |"""

new_block = """> 为兼顾阅读与导出，将完整的六维横向对比拆分为「前数字时代」与「数字时代」两组，每组列数控制在 4 列以内，避免导出 PDF 时表格被压缩或内容被遮挡。

### 前数字时代的信息传播范式（印刷 / 广播 / 电视）

| 维度 | 印刷时代 | 广播时代 | 电视时代 |
| :--- | :--- | :--- | :--- |
| **信息守门人** | 编辑/出版商 | 电台编辑 | 电视网 |
| **传播模型** | 一对多（慢） | 一对多（实时） | 一对多（全感官） |
| **可见性机制** | 版面位置 | 节目时段 | 黄金时段 |
| **权力结构** | 所有权中心 | 频率中心 | 频道中心 |
| **传播学理论** | 议程设置 | 两级传播 | 培养理论 |
| **网络模型** | 星型 | 中心化 | 高度中心化 |
| **竞争壁垒** | 印刷机/渠道 | 牌照/发射塔 | 频道资源 |

### 数字时代的信息传播范式（搜索 / GEO）

| 维度 | 搜索时代 | GEO时代 |
| :--- | :--- | :--- |
| **信息守门人** | 搜索算法 | AI知识表征 |
| **传播模型** | 多对多（交互） | AI中介（问答） |
| **可见性机制** | 关键词排名 | AI引用 |
| **权力结构** | 算法化 | 认知化 |
| **传播学理论** | 知沟+沉默螺旋 | 涵化+拟态环境 |
| **网络模型** | 无标度 | 语义网络 |
| **竞争壁垒** | SEO技术 | 内容资产体系 |"""

assert old_block in text, "6-column table block not found!"
text = text.replace(old_block, new_block)

# ---- 2. Normalize every markdown table ----
def parse_row(line):
    s = line.strip()
    if s.startswith("|"): s = s[1:]
    if s.endswith("|"): s = s[:-1]
    return [c.strip() for c in s.split("|")]

def is_sep(line):
    return bool(re.match(r"^\s*\|[\s:|\-]+\|\s*$", line))

def normalize_tables(text):
    lines = text.split("\n")
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("|"):
            run = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                run.append(lines[i]); i += 1
            if len(run) >= 2 and is_sep(run[1]):
                hcells = parse_row(run[0])
                ncol = len(hcells)
                hcells = [f"**{c.strip('*').strip()}**" for c in hcells]
                body = []
                for bl in run[2:]:
                    bc = parse_row(bl)
                    if len(bc) < ncol: bc += [""] * (ncol - len(bc))
                    if bc and bc[0].strip():
                        bc[0] = f"**{bc[0].strip('*').strip()}**"
                    body.append(bc)
                out.append("| " + " | ".join(hcells) + " |")
                out.append("| " + " | ".join([":---"] * ncol) + " |")
                for bc in body:
                    out.append("| " + " | ".join(bc) + " |")
            else:
                out.extend(run)
        else:
            out.append(line); i += 1
    return "\n".join(out)

text = normalize_tables(text)
with open(OUT_MD, "w", encoding="utf-8") as f:
    f.write(text)
print("Wrote markdown:", OUT_MD, "lines:", text.count(chr(10)))

# ---- 3. Convert to print-optimized HTML ----
def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    return s

def md_to_html(text):
    lines = text.split("\n")
    out = []
    i = 0
    in_list = False
    def close_list():
        nonlocal in_list
        if in_list:
            out.append("</ul>"); in_list = False
    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if s.startswith("|"):
            # table block
            close_list()
            run = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                run.append(lines[i]); i += 1
            if len(run) >= 2 and is_sep(run[1]):
                hdr = parse_row(run[0]); rows = [parse_row(r) for r in run[2:]]
                out.append('<table><thead><tr>')
                for c in hdr: out.append(f"<th>{inline(c)}</th>")
                out.append("</tr></thead><tbody>")
                for r in rows:
                    out.append("<tr>")
                    for c in r: out.append(f"<td>{inline(c)}</td>")
                    out.append("</tr>")
                out.append("</tbody></table>")
            continue
        if s == "---":
            close_list(); out.append("<hr/>"); i += 1; continue
        if s.startswith(">"):
            close_list()
            out.append(f"<blockquote>{inline(s.lstrip('>').strip())}</blockquote>")
            i += 1; continue
        if re.match(r"^###\s", s):
            close_list(); out.append(f"<h3>{inline(s[3:].strip())}</h3>"); i += 1; continue
        if re.match(r"^##\s", s):
            close_list(); out.append(f"<h2>{inline(s[2:].strip())}</h2>"); i += 1; continue
        if re.match(r"^#\s", s):
            close_list(); out.append(f"<h1>{inline(s[1:].strip())}</h1>"); i += 1; continue
        if re.match(r"^- \[ \]|^- \[x\]", s):
            if not in_list: out.append("<ul class='tasks'>"); in_list = True
            checked = "x" in s[2:4]
            content = inline(s[5:].strip())
            out.append(f"<li><input type='checkbox' disabled {'checked' if checked else ''}/> {content}</li>")
            i += 1; continue
        if s.startswith("- "):
            if not in_list: out.append("<ul>"); in_list = True
            out.append(f"<li>{inline(s[2:].strip())}</li>"); i += 1; continue
        if s == "":
            close_list(); i += 1; continue
        close_list(); out.append(f"<p>{inline(s)}</p>"); i += 1
    close_list()
    return "\n".join(out)

css = """
@page { margin: 16mm 14mm; }
* { box-sizing: border-box; }
body { font-family: "Noto Sans CJK SC","Microsoft YaHei","PingFang SC",sans-serif;
       color:#1f2329; line-height:1.75; font-size:14px; max-width:980px; margin:0 auto; padding:8px; }
h1 { font-size:24px; border-bottom:3px solid #2b6cb0; padding-bottom:8px; margin:24px 0 14px; page-break-after:avoid; }
h2 { font-size:19px; color:#2b6cb0; margin:22px 0 10px; border-left:4px solid #2b6cb0; padding-left:10px; page-break-after:avoid; }
h3 { font-size:16px; margin:16px 0 8px; page-break-after:avoid; }
p { margin:8px 0; }
blockquote { border-left:4px solid #cbd5e0; background:#f7fafc; margin:10px 0; padding:8px 14px; color:#475569; }
hr { border:none; border-top:1px solid #e2e8f0; margin:18px 0; }
table { width:100%; border-collapse:collapse; table-layout:auto; margin:14px 0;
        page-break-inside:avoid; word-break:break-word; font-size:12.5px; }
th, td { border:1px solid #d0d7de; padding:7px 9px; text-align:left; vertical-align:top; }
th { background:#eef3fb; font-weight:700; color:#1a365d; }
tr { page-break-inside:avoid; }
ul { margin:8px 0; padding-left:22px; }
ul.tasks { list-style:none; padding-left:4px; }
ul.tasks li { margin:4px 0; }
input[type=checkbox]{ margin-right:6px; vertical-align:middle; }
"""

html_doc = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<title>GEO 视角下的发展史与基础知识体系</title><style>{css}</style></head>
<body>\n{md_to_html(text)}\n</body></html>"""
with open(OUT_HTML, "w", encoding="utf-8") as f:
    f.write(html_doc)
print("Wrote HTML:", OUT_HTML)
