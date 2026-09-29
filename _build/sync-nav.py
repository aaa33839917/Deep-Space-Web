#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 _build/nav.html（全站导航栏的唯一真源）注入所有页面的导航块。

由 deploy.sh 在每次发布前自动调用。手动跑也行：

    python3 _build/sync-nav.py

原理：页面里的导航块被一对标记包住

    <!-- NAV:START -->
    ...自动生成，不要手改...
    <!-- NAV:END -->

本脚本会把两个标记之间的内容整段替换掉。所以：
  ★ 要改导航栏，改 _build/nav.html，不要改各页面里生成出来的那段。
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

TPL_PATH = "_build/nav.html"
START = "<!-- NAV:START -->"
END = "<!-- NAV:END -->"

# 页面 → (相对路径前缀, 激活项)
PAGES = {
    "index.html":              ("./",  "HOME"),
    "products/index.html":     ("../", "PRODUCTS"),
    "mzgd/index.html":         ("../", "PRODUCTS"),        # 产品详情页，「产品」保持高亮
    "accelerator/index.html":          ("../",   "PRODUCTS"),
    "accelerator/tutorial/index.html": ("../../", "PRODUCTS"),   # 加速器子页
    "accelerator/download/index.html": ("../../", "PRODUCTS"),
    "wordcard/index.html":     ("../", "PRODUCTS"),
    "thanks/index.html":       ("../", "THANKS"),
}
KEYS = ("HOME", "PRODUCTS", "THANKS")


def render(prefix, active):
    """把模板里的占位符替换掉，并统一缩进。"""
    body = open(TPL_PATH, encoding="utf-8").read()
    # 去掉模板顶部的说明注释，只取真正的 <a> 行
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    body = body.replace("{P}", prefix)
    for k in KEYS:
        body = body.replace("{ON_%s}" % k, ' class="on"' if k == active else "")
    lines = [ln.strip() for ln in body.split("\n") if ln.strip()]
    return "\n".join("    " + ln for ln in lines)


def main():
    if not os.path.exists(TPL_PATH):
        print("❌ 找不到导航模板：%s" % TPL_PATH, file=sys.stderr)
        return 1
    for k in KEYS:
        if "{ON_%s}" % k not in open(TPL_PATH, encoding="utf-8").read():
            print("❌ 导航模板缺少占位符 {ON_%s}" % k, file=sys.stderr)
            return 1

    failed = 0
    for page, (prefix, active) in sorted(PAGES.items()):
        if not os.path.exists(page):
            print("  ❌ 缺页面：%s" % page)
            failed += 1
            continue
        src = open(page, encoding="utf-8").read()
        block = "%s\n%s\n%s" % (START, render(prefix, active), END)
        new, n = re.subn(re.escape(START) + r".*?" + re.escape(END),
                         block.replace("\\", "\\\\"), src, flags=re.S)
        if n != 1:
            print("  ❌ %s：NAV 标记匹配到 %d 处（应为 1）" % (page, n))
            failed += 1
            continue
        if new != src:
            open(page, "w", encoding="utf-8").write(new)
            print("  ✏️  %-26s 前缀=%-4s 高亮=%s" % (page, repr(prefix), active))
        else:
            print("  ·  %-26s 已是最新" % page)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
