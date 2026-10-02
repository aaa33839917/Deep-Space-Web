#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
群公告海报 · 交付前自检（verify-poster.py）

用法：
    python3 verify-poster.py [海报.png]

查三件事：
  ① 画布尺寸是不是 1080x1620（发出去就是这一张图，尺寸不能飘）；
  ② **从"要发出去的那张 PNG"里把两个二维码抠出来真解一遍** ——
     二维码是这张海报里唯一"错了也看不出来"的东西；
  ③ 海报正文里的链接 / 地址 / 关键文案，逐条对着权威清单比。

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

W, H = 1080, 1620

# 海报里两个二维码**白底方块**的屏幕坐标（x, y, w, h）
#   来源：浏览器里量 .qr__box 的 getBoundingClientRect()（1080x1620 视口、无缩放）
#   ⚠️ 改了海报版式就要重新量（量法：见本目录 README 或 git 提交说明里的那一行 JS）
QR_BOXES = [
    ((811, 566, 176, 176), "https://aaa33839917.github.io/Deep-Space-Web/"),
    ((795, 846, 192, 192), "https://aaa33839917.github.io/Deep-Space-Web/accelerator/download/"),
]

# ★ 权威清单 = 服主 2026-10-03 00:16 发来的那四条原文
CANONICAL_URLS = [
    "https://aaa33839917.github.io/Deep-Space-Web/",
    "https://aaa33839917.github.io/Deep-Space-Web/accelerator/download/",
]
ADDRESS = "10.144.144.1:25565"
MUST_APPEAR = [
    "梦之国度网络架构发生巨大变革",
    "服务端内网穿透",
    "客户端加速器组网连接",
    "深空工作室（DeepSpaceStudio）",
    "支持：安卓 / Windows",
    "梦之国度（Java）",
]


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
    ImageDraw.Draw(broken).rectangle([w // 4, h // 4, w * 3 // 4, h * 3 // 4], fill=(255, 255, 255))
    got_broken = [r.data.decode("utf-8") for r in decode(broken)]
    if any(g == QR_BOXES[0][1] for g in got_broken):
        fails.append("负向对照失败：涂花后仍解出原链接")
        print("③ 负向对照：❌ 涂花后居然还解得出原文 —— 闸门是假绿的")
    else:
        print(f"③ 负向对照：✅ 涂花后解出 {got_broken or '（解不出来）'}，与原文不同")

    # ---------- ④ 正文里的链接 / 地址 / 文案 ----------
    html = open(HTML, encoding="utf-8").read()
    shown = re.findall(r'<span class="url">(.*?)</span>', html)
    addr_m = re.search(r'<span class="addr__v">(.*?)</span>', html)
    addr = addr_m.group(1) if addr_m else ""
    # 正文可见文字（去掉标签），用于"关键文案在不在"的比对
    text = re.sub(r"<[^>]+>", "", html)

    print(f"④ 正文比对：链接 {len(shown)} 条 / 地址 1 条 / 关键文案 {len(MUST_APPEAR)} 条")
    for u in shown:
        good = u in CANONICAL_URLS
        print(f"   {'✅' if good else '❌'} 链接 {u}")
        if not good:
            fails.append(f"海报里的链接不在权威清单里: {u}")
    if len(shown) != len(CANONICAL_URLS):
        fails.append(f"链接条数 {len(shown)} ≠ 权威清单 {len(CANONICAL_URLS)}")
    print(f"   {'✅' if addr == ADDRESS else '❌'} 地址 {addr}")
    if addr != ADDRESS:
        fails.append(f"服务器地址 {addr!r} ≠ {ADDRESS!r}")
    for key in MUST_APPEAR:
        good = key in text
        print(f"   {'✅' if good else '❌'} 文案「{key}」")
        if not good:
            fails.append(f"关键文案缺失: {key}")

    print()
    if fails:
        print("❌ 自检未通过：")
        for f in fails:
            print("   -", f)
        sys.exit(1)
    print(f"✅ 自检通过：画布 {W}x{H}；二维码 {ok_qr}/{len(QR_BOXES)} 可扫且指向正确链接；"
          f"正文 {len(shown)} 条链接 + 1 条地址 + {len(MUST_APPEAR)} 条关键文案全部对上。")


if __name__ == "__main__":
    main()
