#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
群公告海报 · 二维码生成器（离线，不联网）

用法：
    python3 make-qr.py

依赖（只装在本机，不进仓库）：
    pip install --target /vol1/.dsh-tmp/pylibs qrcode[pil] pyzbar

为什么生成完还要再解一遍：
    二维码画错一格，扫出来就是另一个链接 —— 而**肉眼完全看不出来**。
    所以这里不靠"看着像"，而是**用独立解码器（zbar）把生成出来的 PNG 真解一次**，
    解出来的字符串必须与目标链接**逐字节相等**，否则 exit 1、不产出文件。

    ⚠️ 曾试过"用另一个二维码库(segno)逐格比对矩阵" —— 那是**错的判据**：
    两个库各自选的最优编码/掩码不同，但**都是合法二维码**，
    于是"矩阵不一致"只能说明比对方法不对，说明不了谁错。
    真正说了算的只有一件事：**扫出来是不是我要的那个链接。**
"""
import os
import sys

sys.path.insert(0, "/vol1/.dsh-tmp/pylibs")

import qrcode                       # noqa: E402
from PIL import Image               # noqa: E402
from pyzbar.pyzbar import decode    # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

# ★ 链接唯一真源（改这里，海报 HTML 与它的一致性由 verify-poster.py 复查）
TARGETS = [
    ("qr-site.png",     "https://aaa33839917.github.io/Deep-Space-Web/"),
    ("qr-download.png", "https://aaa33839917.github.io/Deep-Space-Web/accelerator/download/"),
]

EC     = qrcode.constants.ERROR_CORRECT_M   # 纠错 M（约 15%）：海报会被转发/压缩，留余量
BOX    = 4       # 每个模组 4px —— 与海报里的显示尺寸 1:1（见 HTML 的 .qr__box img）
BORDER = 2       # 静区 2 个模组（外面还会套一层白色圆角底，见 HTML）


def decode_file(path):
    """用独立解码器（zbar）读回一个图片文件里的二维码内容"""
    return [r.data.decode("utf-8") for r in decode(Image.open(path))]


def negative_control(tmp_path, text):
    """负向对照：故意把码弄坏，确认"解码比对"这道闸门真的会拦住"""
    img = qrcode.make(text, error_correction=EC, border=BORDER, box_size=BOX).convert("RGB")
    px = img.load()
    w, h = img.size
    # 把中间 1/4 区域整块涂白（远超 M 级 15% 的纠错余量）—— 应当解不出来
    for x in range(w // 4, w * 3 // 4):
        for y in range(h // 4, h * 3 // 4):
            px[x, y] = (255, 255, 255)
    img.save(tmp_path)
    got = decode_file(tmp_path)
    if any(g == text for g in got):
        print("❌ 负向对照失败：把码涂掉一大块，居然还解出了原文 —— 这道闸门是假绿的")
        return False
    print(f"✅ 负向对照通过：故意涂坏后解出 {got or '（解不出来）'}，与原文不同")
    return True


def main():
    ok = True
    tmp = os.path.join(HERE, ".negative-control.png")

    ok &= negative_control(tmp, TARGETS[0][1])

    for name, text in TARGETS:
        out = os.path.join(HERE, name)
        qrcode.make(text, error_correction=EC, border=BORDER, box_size=BOX).save(out)

        got = decode_file(out)
        if got != [text]:
            print(f"❌ {name}: 解码回来是 {got}，与目标链接不一致 —— 拒绝交付")
            ok = False
            continue

        img = Image.open(out)
        mods = (img.size[0] // BOX) - 2 * BORDER
        print(f"✅ {name}  版本{mods}x{mods} 模组 + 静区{BORDER}  "
              f"画布 {img.size[0]}x{img.size[1]}px（每模组 {BOX}px）")
        print(f"   解码验证: {got[0]}")
        print(f"   目标链接: {text}   逐字节相等 ✔")

    if os.path.exists(tmp):
        os.remove(tmp)
    if not ok:
        sys.exit(1)
    print("\n全部通过：两个二维码都能被独立解码器还原成目标链接。")


if __name__ == "__main__":
    main()
