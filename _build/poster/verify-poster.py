#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
群公告海报 · 交付前自检（verify-poster.py）

用法：
    python3 verify-poster.py [海报.png]

它只做一件事：**从"要发出去的那张 PNG"里，把二维码抠出来真解一遍**。
因为二维码是这张海报里唯一"错了也看不出来"的东西 ——
另一个库比对矩阵那种方法是错的判据（见 make-qr.py 的注释）。

依赖：
    pip install --target /vol1/.dsh-tmp/pylibs pyzbar
"""
import os
import re
import sys

sys.path.insert(0, "/vol1/.dsh-tmp/pylibs")

from PIL import Image, ImageDraw              # noqa: E402
from pyzbar.pyzbar import decode              # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PNG = os.path.join(HERE, "group-announce-2026-10-03.png")
HTML = os.path.join(HERE, "group-announce.html")

W, H = 1080, 1440

# 海报里两个二维码**白底方块**的屏幕坐标（x, y, w, h）
#   来源：浏览器里量 .qr__box 的 getBoundingClientRect()（1080x1440 视口、无缩放）
#   ⚠️ 改了海报版式就要重新量，量法与期望值会在下面的自检里体现
QR_BOXES = [
    ((811, 435, 176, 176), "https://aaa33839917.github.io/Deep-Space-Web/"),
    ((795, 715, 192, 192), "https://aaa33839917.github.io/Deep-Space-Web/accelerator/download/"),
]

CANONICAL_URLS = [
    "https://aaa33839917.github.io/Deep-Space-Web/",
    "https://aaa33839917.github.io/Deep-Space-Web/accelerator/download/",
]

ADDRESS = "10.144.144.1:25565"


def main():
    png = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PNG
    fails = []

    # ---------- ① 画布尺寸 ----------
    im = Image.open(png)
    print(f"① 画布：{os.path.basename(png)}  {im.size[0]}x{im.size[1]}  {os.path.getsize(png) // 1024} KB")
    if im.size != (W, H):
        fails.append(f"画布尺寸不是 {W}x{H}，而是 {im.size}")

    # ---------- ② 二维码：从成品图里抠出来真解 ----------
    print(f"② 二维码解码（从成品 PNG 裁切，共 {len(QR_BOXES)} 个）")
    ok_qr = 0
    for i, ((x, y, w, h), want) in enumerate(QR_BOXES, 1):
        crop = im.crop((x, y, x + w, y + h)).convert("RGB")
        got = [r.data.decode("utf-8") for r in decode(crop)]
        if got == [want]:
            ok_qr += 1
            print(f"   ✅ 第 {i} 个：解出 {got[0]}")
        else:
            print(f"   ❌ 第 {i} 个：解出 {got or '（解不出来）'}，期望 {want}")
            fails.append(f"第 {i} 个二维码解码不符")
    print(f"   → 解出 {ok_qr}/{len(QR_BOXES)} 个")

    # ---------- ③ 负向对照：把码涂花，确认这道闸门真的会拦 ----------
    x, y, w, h = QR_BOXES[0][0]
    broken = im.crop((x, y, x + w, y + h)).convert("RGB")
    d = ImageDraw.Draw(broken)
    d.rectangle([w // 4, h // 4, w * 3 // 4, h * 3 // 4], fill=(255, 255, 255))
    got_broken = [r.data.decode("utf-8") for r in decode(broken)]
    if any(g == QR_BOXES[0][1] for g in got_broken):
        fails.append("负向对照失败：涂花后仍解出原链接")
        print("③ 负向对照：❌ 涂花后居然还解得出原文 —— 闸门是假绿的")
    else:
        print(f"③ 负向对照：✅ 涂花后解出 {got_broken or '（解不出来）'}，与原文不同")

    # ---------- ④ 海报正文里的链接/地址 vs 权威清单 ----------
    html = open(HTML, encoding="utf-8").read()
    shown = re.findall(r'<span class="url">(.*?)</span>', html)
    addr = re.search(r'<span class="addr__v">(.*?)</span>', html)
    addr = addr.group(1) if addr else ""
    print(f"④ 正文比对：链接 {len(shown)} 条 / 地址 1 条")
    for u in shown:
        mark = "✅" if u in CANONICAL_URLS else "❌"
        print(f"   {mark} {u}")
        if u not in CANONICAL_URLS:
            fails.append(f"海报里的链接不在权威清单里: {u}")
    if len(shown) != len(CANONICAL_URLS):
        fails.append(f"链接条数 {len(shown)} ≠ 权威清单 {len(CANONICAL_URLS)}")
    if addr != ADDRESS:
        fails.append(f"服务器地址 {addr!r} ≠ {ADDRESS!r}")
    print(f"   {'✅' if addr == ADDRESS else '❌'} 服务器地址 {addr}")

    # ---------- ⑤ 品牌图与二维码图都已加载进成品 ----------
    print("⑤ 资源齐全性：品牌图 + 2 个二维码（见浏览器控制台无 404 / 版式无空白）")

    print()
    if fails:
        print("❌ 自检未通过：")
        for f in fails:
            print("   -", f)
        sys.exit(1)
    print(f"✅ 自检通过：画布 {W}x{H}，二维码 {ok_qr}/{len(QR_BOXES)} 可扫且指向正确链接，"
          f"正文 {len(shown)} 条链接 + 1 条地址与权威清单一致。")


if __name__ == "__main__":
    main()
