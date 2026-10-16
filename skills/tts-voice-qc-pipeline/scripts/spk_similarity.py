#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""spk_similarity.py — 说话人声纹相似度（"像不像本人"的一票否决尺）

做法：2~3 个说话人验证模型各算一次余弦，取均值；参照 = 本人多段自然录音。
标尺（需按自己的模型重标）：本人跨段 0.89~0.94 / 异人 ≈0.05。

依赖：numpy、onnxruntime、kaldi_native_fbank
    pip install numpy onnxruntime kaldi-native-fbank

用法：
    python spk_similarity.py --ref ref.m4a --test clip1.mp3 clip2.wav
    python spk_similarity.py --ref ref.m4a --test out.wav \\
        --model zh_en=./models/campplus_cn_en_200k.onnx \\
        --model zh_cn=./models/campplus_zh_cn_200k.onnx \\
        --model wespk=./models/wespeaker_resnet34.onnx
环境变量：
    FFMPEG   ffmpeg 可执行文件路径（默认 "ffmpeg"）

⚠️ 纪律：
  - 短句（<3s）分数不可用于定版，只能看趋势；
  - 参照不要只取一份（可能是离群值），建议多份取均值；
  - 换模型/换采样率后，历史数值不可直接比，要同实现重算。
"""
import argparse
import os
import subprocess
import sys

import numpy as np

try:
    import onnxruntime as ort
    import kaldi_native_fbank as knf
except ImportError:  # pragma: no cover
    sys.exit("缺少依赖：pip install onnxruntime kaldi-native-fbank numpy")

FF = os.environ.get("FFMPEG", "ffmpeg")
SR = 16000


def load(path):
    cmd = [FF, "-v", "error", "-i", str(path), "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"]
    x = np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout,
                      dtype="<f4").astype(np.float64)
    return x[0::2].astype(np.float32)          # 只取单声道，避免降混 ×√2


def fbank(x):
    o = knf.FbankOptions()
    o.frame_opts.samp_freq = SR
    o.frame_opts.dither = 0.0
    o.mel_opts.num_bins = 80
    o.mel_opts.low_freq = 20.0
    o.mel_opts.high_freq = 0.0
    o.use_energy = False
    f = knf.OnlineFbank(o)
    f.accept_waveform(SR, (x * 32768.0).astype(np.float32).tolist())
    f.input_finished()
    n = f.num_frames_ready
    if n < 8:
        return None
    m = np.stack([f.get_frame(i) for i in range(n)]).astype(np.float32)
    return m - m.mean(0, keepdims=True)        # 倒谱均值减（去信道）


def build(models):
    sess = {}
    for name, path in models:
        s = ort.InferenceSession(path, providers=["CPUExecutionProvider"])
        sess[name] = (s, s.get_inputs()[0].name)
    return sess


def embed(sess, name, x):
    s, inp = sess[name]
    f = fbank(x)
    if f is None:
        return None
    v = np.asarray(s.run(None, {inp: f[None]})[0], dtype=np.float64).reshape(-1)
    n = np.linalg.norm(v)
    return v / n if n > 0 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", nargs="+", required=True, help="参照音频（本人录音，建议多份）")
    ap.add_argument("--test", nargs="+", required=True, help="被测音频")
    ap.add_argument("--model", action="append", default=[], metavar="NAME=PATH",
                    help="模型，可重复；不传则用 --models-dir 下约定文件名")
    ap.add_argument("--models-dir", default="./models")
    args = ap.parse_args()

    models = []
    for item in args.model:
        if "=" not in item:
            sys.exit(f"--model 需为 NAME=PATH 形式：{item}")
        n, p = item.split("=", 1)
        models.append((n, p))
    if not models:
        for n, fn in [("zh_en", "campplus_cn_en_200k.onnx"),
                      ("zh_cn", "campplus_zh_cn_200k.onnx"),
                      ("wespk", "wespeaker_resnet34.onnx")]:
            p = os.path.join(args.models_dir, fn)
            if os.path.exists(p):
                models.append((n, p))
    if not models:
        sys.exit("未找到任何模型，请用 --model NAME=PATH 指定")

    sess = build(models)
    names = [n for n, _ in models]

    refs = {n: [] for n in names}
    for p in args.ref:
        x = load(p)
        for n in names:
            e = embed(sess, n, x)
            if e is not None:
                refs[n].append(e)
    ref = {}
    for n in names:
        if refs[n]:
            v = np.mean(np.stack(refs[n]), 0)
            ref[n] = v / np.linalg.norm(v)
    if not ref:
        sys.exit("参照无法提取声纹")

    print("模型: " + ", ".join(f"{n}(ref n={len(refs[n])})" for n in names if n in ref))
    print("%-28s%8s" % ("file", "dur")
          + "".join(f"{n:>10s}" for n in ref) + f"{'MEAN':>10s}")

    for p in args.test:
        x = load(p)
        scores = {}
        for n in ref:
            e = embed(sess, n, x)
            scores[n] = float(np.dot(ref[n], e)) if e is not None else float("nan")
        mean = float(np.nanmean(list(scores.values())))
        warn = "  ⚠️<3s，不可定版" if len(x) / SR < 3 else ""
        print("%-28s%8.2f" % (os.path.basename(p)[:28], len(x) / SR)
              + "".join(f"{scores[n]:>10.4f}" for n in ref) + f"{mean:>10.4f}" + warn)


if __name__ == "__main__":
    main()
