#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
站内链接自检 —— 发布前的最后一道闸。

★ 为什么要有这个（2026-10-02 服主反馈「加速器页面底下的两个按钮全都过时了」）:
  那两个按钮写的是 `../tutorial/` 和 `../download/`，而页面本身就在 accelerator/ 里，
  `../` 一步跨出了 accelerator/ ⇒ 指到 /tutorial/ 和 /download/，两个都是 404。
  同一天还查出 accelerator/tutorial/ 和 accelerator/download/ 里的
  `<script src="../assets/cache-check.js">` 也是同一个错（少了一层 ../），
  导致那两个子页面的「页面陈旧自检」**从来没生效过** —— 根因是 deploy.sh 里
  按「有没有斜杠」猜层级，而不是按真实层数算。

★ 教训：手写的相对路径会随目录层级悄悄错位，而浏览器不会报错、只会 404。
  所以不靠人眼，靠这个脚本在每次发布前真跑一遍。

退出码 0 = 全通；1 = 有坏链（deploy.sh 会因此中止，不会推半成品）。
"""

import os
import re
import sys
import urllib.parse

SKIP_SCHEMES = ("http://", "https://", "mailto:", "data:", "javascript:", "tel:", "//")
ATTR = re.compile(r'(?:href|src)="([^"]+)"')


def pages(root):
    """与 deploy.sh 的 HTMLS 扫描规则保持一致。"""
    out = ["index.html"]
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if not d.startswith(".") and not d.startswith("_") and d != "assets"]
        rel = os.path.relpath(dp, root)
        if "index.html" not in fn:
            continue
        # ⚠️ depth 要算「到 index.html 为止」的层数：accelerator/index.html = 2。
        #    第一版忘了最后那个 +1，于是所有一层子页面都被静默跳过
        #    （症状：只扫到 3 个页面，却照样报「全部有效」—— 空集合永远通过）。
        depth = 1 if rel == "." else rel.count(os.sep) + 2
        if 2 <= depth <= 4:
            out.append(os.path.normpath(os.path.join(rel, "index.html")))
    return out


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bad = []
    checked = 0
    for page in pages(root):
        full = os.path.join(root, page)
        if not os.path.exists(full):
            continue
        pdir = os.path.dirname(page)
        text = open(full, encoding="utf-8").read()
        for m in ATTR.finditer(text):
            url = m.group(1)
            if url.startswith(SKIP_SCHEMES):
                continue
            path = urllib.parse.unquote(urllib.parse.urlparse(url).path)
            if not path:
                continue
            checked += 1
            target = os.path.normpath(os.path.join(root, pdir, path))
            if os.path.isdir(target) or path.endswith("/"):
                target = os.path.join(target, "index.html")
            if not os.path.exists(target):
                bad.append((page, url, os.path.relpath(target, root)))

    print("   扫描 %d 个页面，检查 %d 个站内链接" % (len(pages(root)), checked))
    if bad:
        print("   ❌ 有 %d 个站内链接指向不存在的文件：" % len(bad), file=sys.stderr)
        for page, url, tgt in bad:
            print("      %s  →  %s   （实际解析到 %s）" % (page, url, tgt), file=sys.stderr)
        return 1
    print("   ✅ 站内链接全部有效")
    return 0


if __name__ == "__main__":
    sys.exit(main())
