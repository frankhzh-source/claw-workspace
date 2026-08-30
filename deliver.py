# -*- coding: utf-8 -*-
"""
deliver.py · 文档交付流水线（防呆卡点 v1）

============================================================
设计原则：把「信息核验」从【可选项】变成【强制项】
============================================================

传统流程（会漏）：
    写 MD → （可选）核验 → 转 PDF → 交付
              ↑ 这一步经常跳过，未核实信息流入交付物

防呆流程（本脚本）：
    写 MD → 【强制卡点】verify → 不通过则拒绝出 PDF → 通过后转 PDF → 交付
                    ↑ 跳过核验 = 无法生成交付物

这是 poka-yoke（防呆法）的核心思路：
不是「提醒你去做」，而是「不做就不让你往下走」。

用法：
    python deliver.py <文件.md>               # 核验 + 生成 PDF（同名）
    python deliver.py <文件.md> "自定义标题"    # 指定 PDF 标题
    python deliver.py <文件.md> --check        # 只核验，不生成 PDF
    python deliver.py --batch                  # 全库回归扫描（所有 md）
    python deliver.py <文件.md> --force        # 强制生成（会打印红色警告，慎用）

退出码：
    0 = 通过 / 成功
    1 = 核验未通过，已拒绝生成
    2 = 参数错误

作者：海风 · AI 落地咨询 & GEO 优化 ｜ 微信：frankhzheng
版本：v1（2026-08-30）
"""

import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
VERIFY = HERE / '_verify.py'
MD2PRINT = HERE / '_md2print.py'
CHROME = (r'C:\Users\admin\AppData\Local\ms-playwright'
          r'\chromium-1228\chrome-win64\chrome.exe')

# 全库回归扫描的目标文档（核心交付物）
BATCH_TARGETS = [
    'GEO合规验证_操作范式与产品方案_v2.md',
    '信通院GEO可信评测解读手册_v2.md',
    'GEO命中率压力测试操作手册_v1.md',
    '信息核验规范与已核实信息库_v1.md',
    '标准原文核校记录_v1.md',
    'GEO标准体系全景索引_v1.md',
    'T-CAPT026原文详解与引用手册_v1.md',
    '美妆行业分类与GEO主攻点分析_v1.md',
    '美妆食品行业术语采集表_v1.md',
    '海风100天GEO挑战_企划案_v3.3_第十四章修正版_v1.md',
    'GEO标准源头资料清单_已验证版.md',
]


def run_verify(md: Path) -> tuple[int, str, int]:
    """运行核验脚本，返回 (必改数, 原始输出, 待核总数)"""
    r = subprocess.run(
        [sys.executable, str(VERIFY), str(md)],
        capture_output=True, text=True, encoding='utf-8', errors='ignore',
    )
    out = r.stdout or ''
    m = re.search(r'必改】黑名单实际误用\s*(\d+)\s*处', out)
    blocking = int(m.group(1)) if m else 0

    total = 0
    for label in ['数字类断言', '标准条款引用', '疑似公司名', '外链']:
        mm = re.search(rf'待核】{label}\s*(\d+)\s*(?:处|个)', out)
        if mm:
            total += int(mm.group(1))
    return blocking, out, total


def make_pdf(md: Path, title: str) -> bool:
    """生成 PDF：md2print → Chromium 打印"""
    html = HERE / f'_deliver_{md.stem}.html'
    pdf = HERE / f'{md.stem}.pdf'

    r1 = subprocess.run(
        [sys.executable, str(MD2PRINT), str(md), str(html), title],
        capture_output=True, text=True, encoding='utf-8', errors='ignore',
    )
    if not html.exists():
        print(f'❌ md2print 失败：{r1.stderr[:300]}')
        return False

    r2 = subprocess.run(
        [str(CHROME), '--headless=new', '--disable-gpu',
         '--no-pdf-header-footer', '--run-all-compositor-stages-before-draw',
         '--virtual-time-budget=15000',
         f'--print-to-pdf={pdf}',
         f'file:///{html.as_posix()}'],
        capture_output=True, text=True, encoding='utf-8', errors='ignore',
    )
    # 清理临时 html
    try:
        html.unlink()
    except Exception:
        pass

    if pdf.exists():
        size_kb = pdf.stat().st_size // 1024
        print(f'✅ PDF 已生成：{pdf.name}（{size_kb} KB）')
        return True
    print(f'❌ PDF 生成失败：{r2.stderr[:300]}')
    return False


def deliver(md_path: str, title: str | None, check_only: bool, force: bool) -> int:
    md = Path(md_path)
    if not md.is_absolute():
        md = HERE / md
    if not md.exists():
        print(f'❌ 文件不存在：{md}')
        return 2

    print('=' * 72)
    print(f'📋 交付流水线：{md.name}')
    print('=' * 72)

    # 卡点 1：强制核验
    blocking, out, total = run_verify(md)

    if blocking > 0:
        print()
        print('🚫 ' + '=' * 66)
        print(f'🚫 核验未通过：发现 {blocking} 处「已否证信息」被当事实引用')
        print('🚫 已拒绝生成 PDF —— 这是防呆卡点，不是可选项')
        print('🚫 ' + '=' * 66)
        print()
        # 打印必改详情
        lines = out.split('\n')
        grab = False
        for ln in lines:
            if '必改】' in ln:
                grab = True
            elif ln.startswith('📝') or ln.startswith('⚠️'):
                grab = False
            if grab:
                print('  ' + ln)
        print()
        print('👉 修正后重跑。如确属「更正说明引用」（非误用），')
        print('   请在同行加入 ❌/改为/自报 等标记，脚本会自动识别为正常。')
        if not force:
            return 1
        print()
        print('⚠️  检测到 --force，强制继续（不推荐）')
    else:
        print()
        print('✅ 卡点 1 通过：无「已否证信息」误用')

    if total > 0:
        print(f'⚠️  提醒：仍有 {total} 项待人工核验（数字/条款/公司名/链接）')
        print('   这些不是错误，但需要你确认每项都有出处。')

    if check_only:
        print()
        print('（--check 模式：仅核验，未生成 PDF）')
        return 0

    # 卡点 2：生成 PDF
    print()
    print('-' * 72)
    print('▶ 生成 PDF…')
    ok = make_pdf(md, title or md.stem)
    if not ok:
        return 1

    # 卡点 3：交付后提示
    print()
    print('-' * 72)
    print('📌 交付前最后一步（人工）：')
    print('   打开 PDF，确认 ① 作者区含微信 frankhzheng ② 图片完整 ③ 无溢出')
    return 0


def batch() -> int:
    """全库回归扫描"""
    print('=' * 72)
    print('🔍 全库回归扫描（防呆复查）')
    print('=' * 72)
    bad = []
    missing = []
    for name in BATCH_TARGETS:
        f = HERE / name
        if not f.exists():
            missing.append(name)
            continue
        blocking, _, total = run_verify(f)
        flag = '❌' if blocking else '✅'
        if blocking:
            bad.append((name, blocking))
        print(f'  {flag} {name:<46} 必改 {blocking} · 待核 {total}')

    if missing:
        print()
        print('  （以下文件不存在，已跳过）')
        for m in missing:
            print(f'   - {m}')

    print()
    print('=' * 72)
    if bad:
        print(f'❌ {len(bad)} 份文档有「已否证信息」误用，需修正：')
        for name, n in bad:
            print(f'   {name}（{n} 处）')
        return 1
    print('✅ 全库通过：无「已否证信息」误用')
    print('   建议每周跑一次，防止新写内容引入已知错误。')
    return 0


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2

    if args[0] == '--batch':
        return batch()

    md = args[0]
    title = None
    check_only = '--check' in args
    force = '--force' in args
    for a in args[1:]:
        if not a.startswith('--'):
            title = a
            break

    return deliver(md, title, check_only, force)


if __name__ == '__main__':
    sys.exit(main())
