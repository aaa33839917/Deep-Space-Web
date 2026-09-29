#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 _data/site.json 生成页面里可编辑的区块。

由 deploy.sh 在每次发布前自动调用；_admin/ 后台保存后也会调用它。
手动跑也行：

    python3 _build/render.py

原理：页面里被一对标记包住的区块会被整段重写

    <!-- PRODUCTS:START -->   ...自动生成，不要手改...   <!-- PRODUCTS:END -->
    <!-- PRODUCTS_TABLE:START --> ... <!-- PRODUCTS_TABLE:END -->

★ 要改产品，改 _data/site.json（或用 _admin/ 后台），不要改生成出来的那段。
"""
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

DATA = "_data/site.json"

TAG_CLASS = {"": "tag", "live": "tag tag--live", "dev": "tag tag--dev"}


def esc(s):
    """转义纯文本字段。"""
    return html.escape(str(s or ""), quote=True)


def safe_href(h):
    """链接只允许相对路径或 http(s)，挡掉 javascript: 之类。"""
    h = str(h or "").strip()
    if re.match(r"^(https?:)?//", h) or not re.match(r"^[a-zA-Z][a-zA-Z0-9+.\-]*:", h):
        return esc(h)
    return "#"


def render_cards(products, prefix):
    """产品页的入口卡片。"""
    out = []
    for p in products:
        tags = "".join(
            '      <span class="%s">%s</span>\n'
            % (TAG_CLASS.get(t.get("kind", ""), "tag"), esc(t.get("text", "")))
            for t in p.get("tags", [])
        )
        desc = "<br>\n      ".join(
            ln.strip() for ln in str(p.get("desc", "")).split("\n") if ln.strip()
        )
        out.append(
            "  <!-- product: %s -->\n"
            '  <a class="entry" href="%s%s">\n'
            '    <div class="entry__top">\n'
            '      <img class="brandmark--sm" src="%sassets/mark-navy.svg" alt="" width="42" height="42">\n'
            "      <div>\n"
            '        <div class="entry__title">%s</div>\n'
            '        <div class="entry__en">%s</div>\n'
            "      </div>\n"
            "    </div>\n"
            '    <div class="entry__desc">\n'
            "      %s\n"
            "    </div>\n"
            '    <div class="tagline">\n'
            "%s"
            "    </div>\n"
            '    <div class="entry__go">%s</div>\n'
            "  </a>"
            % (
                esc(p.get("id", "")),
                prefix,
                safe_href(p.get("href", "")),
                prefix,
                esc(p.get("name", "")),
                esc(p.get("en", "")),
                desc,
                tags,
                esc(p.get("cta", "")),
            )
        )
    if not out:
        out.append(
            '  <div class="card"><div class="tip">暂无产品。</div></div>'
        )
    return "\n\n".join(out)


def render_table(products):
    """首页「我们在做的东西」表格行。"""
    rows = [
        "      <tr><th>%s</th><td>%s</td></tr>"
        % (esc(p.get("name", "")), esc(p.get("home_desc", "")))
        for p in products
    ]
    return "\n".join(rows) if rows else "      <tr><td>暂无内容</td></tr>"


def render_names(products):
    """产品页顶部副标题：产品名用 · 连起来。"""
    names = [esc(p.get("name", "")) for p in products if p.get("name")]
    return " · ".join(names) if names else "暂未添加"


def render_about(products):
    """首页「关于深空」里列产品的那一句。

    隐藏某个产品时，它对应的半句会一起消失 —— 否则「隐藏」只藏了卡片，
    正文里还提着一个已经下线的产品。
    """
    clauses = [str(p.get("about", "")).strip() for p in products]
    clauses = [c for c in clauses if c]
    if not clauses:
        return "目前还没有对外提供的内容。"
    if len(clauses) == 1:
        return "目前对外提供：" + clauses[0] + "。"
    return "目前对外提供：" + "；".join(clauses[:-1]) + "；以及" + clauses[-1] + "。"


def inject(path, start, end, body):
    if not os.path.exists(path):
        raise SystemExit("❌ 缺页面：%s" % path)
    src = open(path, encoding="utf-8").read()
    new, n = re.subn(
        re.escape(start) + r".*?" + re.escape(end),
        lambda m: start + "\n" + body + "\n" + end,
        src,
        flags=re.S,
    )
    if n != 1:
        raise SystemExit("❌ %s：标记 %s 匹配到 %d 处（应为 1）" % (path, start, n))
    if new != src:
        open(path, "w", encoding="utf-8").write(new)
        return True
    return False


def main():
    if not os.path.exists(DATA):
        raise SystemExit("❌ 找不到内容文件：%s" % DATA)
    try:
        data = json.load(open(DATA, encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit("❌ %s 不是合法 JSON：%s" % (DATA, e))

    products = data.get("products") or []
    ids = [p.get("id") for p in products]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        raise SystemExit("❌ 产品 id 重复：%s" % ", ".join(sorted(dup)))

    shown = [p for p in products if p.get("visible", True)]
    print("   数据：%d 个产品，%d 个显示 / %d 个隐藏" % (len(products), len(shown), len(products) - len(shown)))

    changed = []
    if inject("products/index.html", "<!-- PRODUCTS:START -->", "<!-- PRODUCTS:END -->",
              render_cards(shown, "../")):
        changed.append("products/index.html 的卡片区")
    if inject("products/index.html", "<!-- PRODUCT_NAMES:START -->", "<!-- PRODUCT_NAMES:END -->",
              render_names(shown)):
        changed.append("products/index.html 的副标题")
    if inject("index.html", "<!-- PRODUCTS_TABLE:START -->", "<!-- PRODUCTS_TABLE:END -->",
              render_table(shown)):
        changed.append("index.html 的产品表")
    if inject("index.html", "<!-- ABOUT_PRODUCTS:START -->", "<!-- ABOUT_PRODUCTS:END -->",
              render_about(shown)):
        changed.append("index.html 的「关于深空」产品句")

    for c in changed:
        print("   ✏️  %s" % c)
    if not changed:
        print("   ·  已是最新")
    return 0


if __name__ == "__main__":
    sys.exit(main())
