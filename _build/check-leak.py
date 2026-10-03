#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""发布文本「泄漏词」闸门 —— 对外页面里不许出现**内部痕迹**

    python3 _build/check-leak.py

来源：2026-10-03 事故 —— `terms/` 与 `privacy/` 把**内部说明**渲染给了玩家看
（服主在手机上看到「不要往里塞商业条款……等于把自己描述成"面向公众的服务提供者"」、
「状态：已定稿（**服主** 拍定）」、以及文末的**变更记录**）。
根因是"起草工作稿"与"发布真源"混用为一个文件，而**没有任何闸门**检查对外文本有没有内部词。
本闸门就是补上的那一半（另一半是物理分开，见 `法律文本/内部说明（不发布）.md`）。

── 两类扫描，判据不同（这是本事故的一半）───────────────────────────────
A. **内部词**（扫**可见文本**）：玩家看得见的字里不许有 `服主` / `草案` / `变更记录` / `ACE` …
   ⇒ **先剥掉 HTML 注释**再扫。生成器会在页面里留一行构建说明注释，玩家看不到它；
      若不剥注释，闸门会被**自己的生成注释**绊红（第一版差点就这么干）。
B. **内部路径**（扫**整文件**，注释也算）：`_build/`、`法律文本`、`/vol1/` … 这些**任何形式**
   都不该出现在公网文件里 —— 所以这一类**不剥注释**，宁可严一点。

── 为什么必须"带边界"匹配（假红案例，Lead 亲历）─────────────────────────
`ACE` 是 `DEEP SPACE` 里 `SPACE` 的**子串**（S-P-**ACE**）⇒ 朴素 `in` 会让**全站 11 个页面**
全部误报（而站点页脚/标题里到处是 `DEEP SPACE`）。
所以 ASCII 词一律用 `(?<![A-Za-z0-9])词(?![A-Za-z0-9])`；中文词没有这种词内边界问题，用普通包含。

── 故意**不**放进词表的两个词（都实测过，加了就是假红）────────────────────
· `内部`   —— 隐私政策 §七 有一句**合法的对外表述**：「我们对管理界面与**内部**服务设置访问控制」；
· `实测`   —— 它是**正当的对外用词**（例如「实测延迟 20ms」）。
（本项目纪律 R4.3：**假红和假绿一样有害** —— 狼来了喊多了，真出事那次就没人看了。）
"""
import html
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---- A 类：内部词（扫可见文本）--------------------------------------------
#   （词, 是否为 ASCII ⇒ 需要边界匹配）
VOCAB = [
    ("服主", False), ("拍定", False), ("拍板", False), ("定稿", False),
    ("草案", False), ("待定", False), ("变更记录", False), ("内部说明", False),
    ("法律清单", False), ("项目规则", False), ("已知取舍", False),
    ("独立验证", False), ("验证者", False), ("负向对照", False), ("假绿", False),
    ("看板", False), ("工作稿", False), ("起草", False),
    ("不要往里塞", False), ("面向公众的服务提供者", False), ("不利自认", False),
    ("腾讯", False), ("不发布", False),
    ("ACE", True), ("Trae", True), ("README", True),
]

# ---- B 类：内部路径（扫整文件，注释也算）----------------------------------
PATHS = [
    "/vol1/", "_build/", "法律文本", "服务端网关", "DeepSpaceConsole",
    "system-manager", ".dsh-tmp", "SHA256SUMS", "projsnap",
    "registry.py", "gateway.py", "task-",
]


def pages(root):
    """已发布页面 —— 与 check-links.py / sync-footer.py / deploy.sh 同一条规则。"""
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


def visible_text(s):
    """玩家看得见的字：先剥注释（★ 这条就是本事故的一半），再剥 script/style 与标签。"""
    s = re.sub(r"<!--.*?-->", " ", s, flags=re.S)          # ★ 剥注释：生成说明注释不算泄漏
    s = re.sub(r"<script\b.*?</script>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<style\b.*?</style>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def find(text, term, boundary):
    """返回全部 (位置, 命中串)。ASCII 词带边界；中文词普通包含。"""
    if boundary:
        pat = re.compile(r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])")
    else:
        pat = re.compile(re.escape(term))
    return [(m.start(), m.group(0)) for m in pat.finditer(text)]


def ctx(text, pos, n=34):
    a, b = max(0, pos - n), min(len(text), pos + n)
    return ("…" if a else "") + text[a:b].replace("\n", " ") + ("…" if b < len(text) else "")


def main():
    os.chdir(ROOT)
    hits = 0
    n_pages = 0
    for page in pages(ROOT):
        if not os.path.exists(page):
            print("  ❌ 缺页面：%s" % page)
            hits += 1
            continue
        n_pages += 1
        raw = open(page, encoding="utf-8").read()
        vis = visible_text(raw)

        for term, boundary in VOCAB:
            for pos, got in find(vis, term, boundary):
                hits += 1
                print("  ❌ %s ｜ 内部词「%s」在**可见文本**里" % (page, term))
                print("       上下文：%s" % ctx(vis, pos))
        for term in PATHS:
            for pos, _got in find(raw, term, False):
                hits += 1
                print("  ❌ %s ｜ 内部路径「%s」（注释也算）" % (page, term))
                print("       上下文：%s" % ctx(raw, pos))

    print("  → 扫了 %d 页 × %d 个词（内部词 %d + 内部路径 %d）"
          % (n_pages, len(VOCAB) + len(PATHS), len(VOCAB), len(PATHS)))
    if hits:
        print("  ❌ 命中 %d 处 —— 对外页面里不许有内部痕迹（见 _build/check-leak.py 顶部说明）" % hits)
    else:
        print("  ✅ 未命中：对外页面里没有内部词、也没有仓库内部路径")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
