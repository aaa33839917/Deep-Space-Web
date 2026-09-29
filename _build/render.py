#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成页面里可编辑的区块。

    python3 _build/render.py

★ 数据从哪来（用户 2026-09-29 定的规则）：
   **没有配置文件。** 每个项目的卡片信息写在它自己的详情页里
   （`<script type="application/json" data-card-meta>`，见 _build/cardmeta.py）。
   本脚本扫一遍站点，把各页面里的卡片信息收集起来，再生成：

     · products/index.html 的卡片区      ← 只放 visible 的项目
     · products/index.html 的副标题      ← 同上
     · index.html  的「我们在做的东西」表 ← 同上
     · index.html  的「关于深空」产品句   ← 同上

   隐藏的项目：详情页照常上传、URL 照常能访问，只是**不列出来**。

由 deploy.sh 在每次发布前自动调用；_admin/ 后台保存后也会调用它。
"""
import os
import re
import sys
import html

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cardmeta  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

TAG_CLASS = {"": "tag", "live": "tag tag--live", "dev": "tag tag--dev"}


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def safe_href(h):
    """链接只允许相对路径或 http(s)，挡掉 javascript: 之类。"""
    h = str(h or "").strip()
    if re.match(r"^(https?:)?//", h) or not re.match(r"^[a-zA-Z][a-zA-Z0-9+.\-]*:", h):
        return esc(h)
    return "#"


def render_cards(projects, prefix):
    out = []
    for it in projects:
        p = it["meta"]
        tags = "".join(
            '      <span class="%s">%s</span>\n'
            % (TAG_CLASS.get(t.get("kind", ""), "tag"), esc(t.get("text", "")))
            for t in (p.get("tags") or [])
        )
        desc = "<br>\n      ".join(
            ln.strip() for ln in str(p.get("desc", "")).split("\n") if ln.strip()
        )
        out.append(
            "  <!-- project: %s -->\n"
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
                esc(it["id"]),
                prefix,
                safe_href(p.get("href") or (it["id"] + "/")),
                prefix,
                esc(p.get("name")),
                esc(p.get("en")),
                desc,
                tags,
                esc(p.get("cta")),
            )
        )
    if not out:
        out.append('  <div class="card"><div class="tip">暂无项目。</div></div>')
    return "\n\n".join(out)


def render_names(projects):
    names = [esc(it["meta"].get("name")) for it in projects if it["meta"].get("name")]
    return " · ".join(names) if names else "暂未添加"


def render_table(projects):
    rows = [
        "      <tr><th>%s</th><td>%s</td></tr>"
        % (esc(it["meta"].get("name")), esc(it["meta"].get("home_desc")))
        for it in projects
    ]
    return "\n".join(rows) if rows else "      <tr><td>暂无内容</td></tr>"


def render_about(projects):
    """首页「关于深空」里列项目的那一句。

    隐藏某个项目时，它对应的半句会一起消失 —— 否则「隐藏」只藏了一半。
    """
    clauses = [str(it["meta"].get("about", "")).strip() for it in projects]
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
    allp = cardmeta.scan(ROOT)
    shown = [it for it in allp if it["meta"].get("visible", True)]

    print("   扫描到 %d 个项目：%d 个显示 / %d 个隐藏"
          % (len(allp), len(shown), len(allp) - len(shown)))
    for it in allp:
        if not it["meta"].get("visible", True):
            print("     · 隐藏：%s（详情页仍可访问 /%s）" % (it["id"], it["meta"].get("href")))

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
