#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
群公告海报 · 交付前自检（verify-poster.py）

用法：
    python3 verify-poster.py [海报.png]

查四件事：
  ① 画布尺寸是不是 1080x1440（发出去就是这一张图，尺寸不能飘）；
  ② **从"要发出去的那张 PNG"里把两个二维码抠出来真解一遍** ——
     二维码是这张海报里唯一"错了也看不出来"的东西；
  ③ 海报正文里的链接 / 地址 / 关键文案，逐条对着权威清单比；
  ④ 反向断言：玩家可见文案里**一个字都不许再出现**改名前的旧产品名。

依赖：
    pip install --target /vol1/.dsh-tmp/pylibs pyzbar

★ 这条规矩是 2026-10-03 定的：**二维码不靠"看着像"验收**。
  试过"用另一个二维码库逐格比对矩阵" —— 那是错的判据：两个库各自选的最优掩码不同、
  但都是合法二维码，矩阵不一致说明不了谁错。唯一说了算的判据是：
  **扫出来是不是我要的那个链接**（zbar 是本机系统里的 libzbar，与生成端无关）。
"""
import os
import re
import sys

sys.path.insert(0, "/vol1/.dsh-tmp/pylibs")

from PIL import Image, ImageDraw              # noqa: E402
from pyzbar.pyzbar import decode              # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PNG = os.path.join(HERE, "group-announce-2026-10-07.png")
HTML = os.path.join(HERE, "group-announce.html")          # ← v4 版式（宋体标题那版）

W, H = 1080, 1440

# 海报里两个二维码**白底小块**的屏幕坐标（x, y, w, h）
#   来源：浏览器里量 .qb 的 getBoundingClientRect()（1080x1440 视口、无缩放）
#   ⚠️ 改版式必须重新量，量法：page.evaluate 取 [...document.querySelectorAll('.qb')].map(getBoundingClientRect)
QR_BOXES = [
    ((832, 519, 172, 172), "https://aaa33839917.github.io/Deep-Space-Web/"),
    ((832, 765, 172, 188), "https://aaa33839917.github.io/Deep-Space-Web/accelerator/download/"),
]

# ★ 权威清单 = 服主那条群公告（产品名按 2026-10-03 改名收口为「深空联机工具」）
CANONICAL_URLS = [
    "https://aaa33839917.github.io/Deep-Space-Web/",
    "https://aaa33839917.github.io/Deep-Space-Web/accelerator/download/",
]
ADDRESS = "10.144.144.1:25565"
MUST_APPEAR = [
    "进服方式变更",
    "服务端内网穿透",
    "客户端「深空联机工具」组网连接",
    "深空工作室（DeepSpaceStudio）",
    "支持：安卓 / Windows",
    "仅限本服玩家",
    "梦之国度（Java）",
    "服务器地址",
]
# ★ 反向断言：改名后，玩家可见文案里不许再出现旧产品名
#   （只查中文词；下载地址路径里的英文 accelerator 是技术标识，URL 不动）
MUST_NOT_APPEAR = ["加速器"]

# 只认 URL 安全字符：这样"CJK 紧跟在链接后面"时不会把中文也吞进 URL
URL_RE = re.compile(r"https?://[A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=%]+")


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

    # ---------- ④ 正文：链接 / 地址 / 关键文案 / 旧名残留 ----------
    #   把标签全部剥掉再查 —— 这样"排版换行用的 <span>、<br>"都不会干扰比对
    text = re.sub(r"<[^>]+>", "", open(HTML, encoding="utf-8").read())

    found = URL_RE.findall(text)
    print(f"④ 正文比对：链接 {len(found)} 条 / 地址 1 条 / 关键文案 {len(MUST_APPEAR)} 条 / 旧名 {len(MUST_NOT_APPEAR)} 个")
    for u in found:
        good = u in CANONICAL_URLS
        print(f"   {'✅' if good else '❌'} 链接 {u}")
        if not good:
            fails.append(f"海报里的链接不在权威清单里: {u}")
    if found != CANONICAL_URLS:
        fails.append(f"链接清单不一致：{found}")

    addr_ok = ADDRESS in text
    print(f"   {'✅' if addr_ok else '❌'} 地址 {ADDRESS}")
    if not addr_ok:
        fails.append(f"正文里找不到服务器地址 {ADDRESS}")

    for key in MUST_APPEAR:
        good = key in text
        print(f"   {'✅' if good else '❌'} 文案「{key}」")
        if not good:
            fails.append(f"关键文案缺失: {key}")

    for bad in MUST_NOT_APPEAR:
        clean = bad not in text
        print(f"   {'✅' if clean else '❌'} 不该出现「{bad}」（改名前的旧产品名）")
        if not clean:
            fails.append(f"文案里还残留旧名: {bad}")

    print()
    if fails:
        print("❌ 自检未通过：")
        for f in fails:
            print("   -", f)
        sys.exit(1)
    print(f"✅ 自检通过：画布 {W}x{H}；二维码 {ok_qr}/{len(QR_BOXES)} 可扫且指向正确链接；"
          f"正文 {len(found)} 条链接 + 1 条地址 + {len(MUST_APPEAR)} 条关键文案全部对上，"
          f"且已无旧名「{'/'.join(MUST_NOT_APPEAR)}」。")


if __name__ == "__main__":
    main()
