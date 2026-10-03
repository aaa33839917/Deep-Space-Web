#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全站页脚「协议入口」条 —— 构建期注入（与 sync-nav.py 同一套纪律）

    python3 _build/sync-footer.py

唯一真源：`_build/footer.html`（普通页）与 `_build/footer-neutral.html`（异次元中性页）。
注入位置：页面自己 `<footer …>` 的**内部末尾**（由 `<!-- FOOTER:START -->` / `<!-- FOOTER:END -->` 标记），
          所以每页只会有一个页脚条，不会出现"两个深色页脚叠在一起"。

★ 相对路径用 `os.path.relpath()` 按**真实层级**算 —— 本站栽过
  「手写 `../` 层级错位 ⇒ 线上 404 且一直没人发现」（AGENTS.md 天坑 #12）。
  **不许**再按"有没有斜杠"猜层级（那正是当年那个 bug 的写法）。

★ 中性页判定：页面引用 `assets/yi.css` ⇒ 走中性版（不带运营者署名）。
  这样判定是**数据驱动**的（看它用哪套皮肤），不是写死一张页面清单。
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL = os.path.join("_build", "footer.html")
TPL_NEUTRAL = os.path.join("_build", "footer-neutral.html")
START = "<!-- FOOTER:START -->"
END = "<!-- FOOTER:END -->"


def pages(root):
    """已发布页面 —— 与 deploy.sh 的 HTMLS / check-links.py 的 pages() 同一规则。

    （跳过 `_`/`.` 开头的目录与 assets/：`_build`、`_admin` 不是发布内容。）
    """
    out = ["index.html"]
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if not d.startswith(".") and not d.startswith("_") and d != "assets"]
        rel = os.path.relpath(dp, root)
        if "index.html" not in fn:
            continue
        depth = 1 if rel == "." else rel.count(os.sep) + 2
        if 2 <= depth <= 4:
            out.append(os.path.normpath(os.path.join(rel, "index.html")))
    return out


def target(page, dest):
    """页面 → 目标目录 的相对链接（按真实层级算，末尾带 / 让服务器直接给 index.html）。"""
    rel = os.path.relpath(dest, os.path.dirname(page) or ".")
    return rel.replace(os.sep, "/") + "/"


def render(tpl_text, page):
    body = re.sub(r"<!--.*?-->", "", tpl_text, flags=re.S)          # 去掉模板里的说明注释
    body = body.replace("{TERMS}", target(page, "terms"))
    body = body.replace("{PRIVACY}", target(page, "privacy"))
    lines = [ln.rstrip() for ln in body.split("\n") if ln.strip()]
    return "\n".join(lines)


def main():
    os.chdir(ROOT)
    std = open(TPL, encoding="utf-8").read()
    neu = open(TPL_NEUTRAL, encoding="utf-8").read()

    list_pages = pages(ROOT)
    failed = 0
    changed = 0
    neutral_used = []
    for page in list_pages:
        if not os.path.exists(page):
            print("  ❌ 缺页面：%s" % page)
            failed += 1
            continue
        src = open(page, encoding="utf-8").read()
        tpl = neu if "assets/yi.css" in src else std
        if tpl is neu:
            neutral_used.append(page)
        n_mark = src.count(START) + src.count(END)
        if n_mark != 2 or src.count(START) != 1:
            print("  ❌ %s：FOOTER 标记有 %d 处（应 START/END 各 1）" % (page, n_mark))
            failed += 1
            continue
        body = render(tpl, page)
        block = "%s\n%s\n%s" % (START, body, END)
        new, n = re.subn(re.escape(START) + r".*?" + re.escape(END), lambda _m: block, src, flags=re.S)
        if n != 1:
            print("  ❌ %s：标记匹配到 %d 处（应为 1）" % (page, n))
            failed += 1
            continue
        if new != src:
            open(page, "w", encoding="utf-8").write(new)
            changed += 1
            print("  ✏️  %-34s 前缀=%-8s 皮肤=%s" % (page, repr(target(page, "terms")), "中性" if tpl is neu else "标准"))
        else:
            print("  ·  %-34s 已是最新" % page)
    print("  扫了 %d 个页面，改了 %d 个%s" %
          (len(list_pages), changed,
           "；中性版用于：" + "、".join(neutral_used) if neutral_used else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
