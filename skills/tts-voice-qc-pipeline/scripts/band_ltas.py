#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""band_ltas.py — 有声帧分带 LTAS 诊断（"闷 / 亮 / 刺"的客观锚点）

用途：把"听着闷 / 听着亮"落到分频段能量差上。
口径（**必须完整遵守，否则测不出问题**）：
  1. 只统计**有声音帧**（阈值 = 95 分位帧能量 − 25dB），排除近静音帧；
  2. 每条音轨**各自以 200–4000Hz 均值为 0 归一**（比谱形，不比响度）；
  3. 参照建议用**本人多份录音的均值**（先看参照之间差异，>±2dB 说明参照不可信）。

⚠️ 只报**分带实测值**，不要用"4-8k / 全带"这类比值判亮度（比值会被分母带偏）。

用法：
    python band_ltas.py --ref ref1.m4a ref2.m4a --test out.wav [out2.wav ...]
    python band_ltas.py --ref a.m4a --test b.wav --sr 16000        # 改采样率
环境变量：
    FFMPEG   ffmpeg 可执行文件路径（默认 "ffmpeg"）
"""
import argparse
import os
import subprocess
import sys

import numpy as np

FF = os.environ.get("FFMPEG", "ffmpeg")
NFFT = 1024
HOP = 256

# 判读用频带（名称 → (lo, hi) Hz）
BANDS = [
    ("100-200", 100, 200),
    ("200-350", 200, 350),
    ("350-500", 350, 500),
    ("500-800", 500, 800),
    ("800-1.2k", 800, 1200),
    ("1.2-2k", 1200, 2000),
    ("2-3k", 2000, 3000),
    ("3-4k", 3000, 4000),
    ("4-6k", 4000, 6000),
    ("6-8k", 6000, 8000),
]


def load(path, sr):
    """解码为单声道 float64。

    注：这里用 `-ac 1` 是有意为之——本脚本只比**谱形（相对量）**，各自归一化后
    绝对电平被约掉，降混带来的 ×√2 不影响结论。但凡要报**响度/峰值**这类实测值时，
    必须直读原文件或只取单声道 x[0::2]，**不能**用 `-ac 1` 的结果（会虚高 3.01dB）。
    """
    cmd = [FF, "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"]
    out = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(out, dtype="<f4").astype(np.float64)


def ltas(x, sr):
    """返回 (freqs, 归一化谱形 dB)；只统计有声音帧。"""
    if len(x) < NFFT * 2:
        return None
    win = np.hanning(NFFT)
    starts = np.arange(0, len(x) - NFFT, HOP)
    frames = x[starts[:, None] + np.arange(NFFT)[None, :]] * win[None, :]
    energy = 20 * np.log10(np.sqrt((frames ** 2).mean(1)) + 1e-12)
    thr = np.percentile(energy, 95) - 25.0
    keep = energy >= thr
    if keep.sum() < 5:
        return None
    spec = (np.abs(np.fft.rfft(frames[keep], NFFT, axis=1)) ** 2).mean(0)
    freqs = np.fft.rfftfreq(NFFT, 1.0 / sr)
    db = 10 * np.log10(spec + 1e-18)
    band = (freqs >= 200) & (freqs <= 4000)
    return freqs, db - db[band].mean()


def band_vals(freqs, db):
    out = []
    for _, lo, hi in BANDS:
        m = (freqs >= lo) & (freqs < hi)
        out.append(float(db[m].mean()) if m.any() else float("nan"))
    return np.array(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", nargs="+", required=True, help="参照音频（建议多份，取均值）")
    ap.add_argument("--test", nargs="+", required=True, help="被测音频")
    ap.add_argument("--sr", type=int, default=16000)
    args = ap.parse_args()

    refs = []
    for p in args.ref:
        r = ltas(load(p, args.sr), args.sr)
        if r is None:
            print(f"[warn] 参照过短/无声: {p}", file=sys.stderr)
            continue
        refs.append(band_vals(*r))
        print(f"[ref] {os.path.basename(p)}  " +
              " ".join(f"{n}={v:+.2f}" for (n, _, _), v in zip(BANDS, refs[-1])))
    if not refs:
        sys.exit("参照全部不可用")
    ref = np.mean(refs, axis=0)
    if len(refs) > 1:
        spread = float(np.nanmax(np.ptp(np.stack(refs), axis=0)))
        print(f"[ref] 参照之间最大极差 = {spread:.2f} dB" +
              ("  ⚠️ >2dB，参照不可信，请换参照" if spread > 2 else "  ✓ 参照可信"))

    header = "%-24s" % "band(Hz)" + "".join(f"{n:>10s}" for n, _, _ in BANDS)
    print("\n" + header)
    print("%-24s" % "参照均值(基准)" + "".join(f"{v:>10.2f}" for v in ref))

    for p in args.test:
        r = ltas(load(p, args.sr), args.sr)
        if r is None:
            print(f"[warn] 过短/无声: {p}", file=sys.stderr)
            continue
        v = band_vals(*r) - ref
        print("%-24s" % os.path.basename(p)[:24] + "".join(f"{d:>+10.2f}" for d in v))

    print("\n判读：100–800Hz 偏高 ⇒ 闷/鼻音重；800–1200Hz 偏低 ⇒ 清晰度塌；"
          "4–8k 偏低 ⇒ 暗；2.5–4k 偏高 ⇒ 刺。到位 = 各带回到 ±1dB 内。")


if __name__ == "__main__":
    main()
