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


def shot(p, prefix):
    """★ 2026-10-23（服主：展示区换成真客户端界面图）——卡片的视觉块。

    card-meta 里没有 image ⇒ 这块整体不出现（不是"画个假的顶上"）。
    路径按页面真实层级拼 prefix（R4.9：手写 ../ 出过 404）。"""
    if not p.get("image"):
        return ""
    return ('<img class="pcard__shot" src="%s%s" alt="%s 的客户端界面（已连接）" '
            'width="760" loading="lazy">' % (prefix, esc(p.get("image")), esc(p.get("name"))))

def render_cards(projects, prefix):
    """卡片区的形状必须与站点当前版式一致。

    ★ 2026-10-23（服主拍板）：卡片区交回生成器，视觉块用真客户端界面图。
    site.css 里现在只有 `.pcard` 这一套规则（`.entry` 那套已经不存在）——
    生成器若继续输出 `.entry`，卡片会没有样式（这种错不报错、只有肉眼看得出）。
    所以这里输出 `.pcard`，字段全部来自 card-meta（没有配置文件）。
    """
    out = []
    for it in projects:
        p = it["meta"]
        kicker = " · ".join(
            str(t.get("text", "")).strip() for t in (p.get("tags") or [])
            if str(t.get("text", "")).strip())
        desc = "<br>\n      ".join(
            ln.strip() for ln in str(p.get("desc", "")).split("\n") if ln.strip()
        )
        icon = ('<span class="pcard__icon"><img src="%s%s" alt="" width="42" height="42"></span>'
                % (prefix, esc(p.get("icon")))) if p.get("icon") else '<span class="pcard__icon">◈</span>'
        out.append(
            "  <!-- project: %s -->\n"
            '  <a class="pcard pcard--wide" href="%s%s">\n'
            '    <div class="pcard__body">\n'
            '      <div class="pcard__head">\n'
            '        %s\n'
            '        <span class="pcard__kicker">%s</span>\n'
            '      </div>\n'
            '      <h2>%s</h2>\n'
            '      <p>%s</p>\n'
            '      <span class="pcard__more">%s</span>\n'
            '    </div>\n'
            '    <div class="pcard__visual">%s</div>\n'
            '  </a>'
            % (esc(it["id"]), prefix, safe_href(p.get("href") or (it["id"] + "/")),
               icon, esc(kicker), esc(p.get("name")), desc, esc(p.get("cta")), shot(p, prefix)))
    if not out:
        out.append('  <div class="card"><div class="tip">暂无项目。</div></div>')
    return "\n\n".join(out)


def render_names(projects):
    names = [esc(it["meta"].get("name")) for it in projects if it["meta"].get("name")]
    return " · ".join(names) if names else "暂未添加"


def _table_name(p):
    """首页产品表里的项目名：有 icon 就在前面加一枚 20px 小图标（不影响行高）。"""
    name = esc(p.get("name"))
    if p.get("icon"):
        return ('<img class="row-logo" src="%s" alt="" width="20" height="20">%s'
                % (esc(p.get("icon")), name))
    return name


def render_table(projects):
    rows = [
        "      <tr><th>%s</th><td>%s</td></tr>"
        % (_table_name(it["meta"]), esc(it["meta"].get("home_desc")))
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


def inject_optional(path, start, end, body):
    """★ 2026-10-23（服主拍板）：首页那两个区块在改版后的版式里没有位置了。

    ⚠️ 这里**只**允许"整页没有这个标记"这一种情况跳过，并且必须打印；
    标记还在但形状不对（少 END、匹配 0/2 处）照旧报错 —— 判据不能变软，
    否则就成了 R4.2 说的假绿（空集合永远通过）。
    """
    if not os.path.exists(path):
        raise SystemExit("❌ 缺页面：%s" % path)
    src = open(path, encoding="utf-8").read()
    if start not in src:
        print("   ·  %s 没有 %s（该页版式里已无此区块）⇒ 跳过" % (path, start))
        return False
    return inject(path, start, end, body)


def main():
    allp = cardmeta.scan(ROOT)
    shown = [it for it in allp if it["meta"].get("visible", True)]

    print("   扫描到 %d 个项目：%d 个显示 / %d 个隐藏"
          % (len(allp), len(shown), len(allp) - len(shown)))
    for it in allp:
        if not it["meta"].get("visible", True):
            print("     · 隐藏：%s（详情页仍可访问 /%s）" % (it["id"], it["meta"].get("href")))

    changed = []
    areas = 0
    if inject("products/index.html", "<!-- PRODUCTS:START -->", "<!-- PRODUCTS:END -->",
              render_cards(shown, "../")):
        changed.append("products/index.html 的卡片区"); areas += 1
    if inject("products/index.html", "<!-- PRODUCT_NAMES:START -->", "<!-- PRODUCT_NAMES:END -->",
              render_names(shown)):
        changed.append("products/index.html 的副标题"); areas += 1
    # ★ 2026-10-23：首页两处按「该页没有这个区块 ⇒ 打印跳过」（服主拍板）；
    #   判据数量照旧打印，不静默。
    if inject_optional("index.html", "<!-- PRODUCTS_TABLE:START -->", "<!-- PRODUCTS_TABLE:END -->",
                       render_table(shown)):
        changed.append("index.html 的产品表"); areas += 1
    if inject_optional("index.html", "<!-- ABOUT_PRODUCTS:START -->", "<!-- ABOUT_PRODUCTS:END -->",
                       render_about(shown)):
        changed.append("index.html 的「关于深空」产品句"); areas += 1
    print("   区块判据跑了 4 处（注入 %d 处，其中已一致/跳过的不计入改动）" % areas)

    for c in changed:
        print("   ✏️  %s" % c)
    if not changed:
        print("   ·  已是最新")
    return 0


if __name__ == "__main__":
    sys.exit(main())
