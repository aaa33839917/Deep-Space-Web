#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""协议页「不许漂移」闸门 —— 仓库里的 HTML 必须与**现在**从源稿渲染的结果一致

    python3 _build/check-legal.py

为什么必须有这条：协议正文的真源在项目根 `法律文本/*.md`，站里是**生成物**。
只要有人手改了站里的 HTML、或改了源稿忘了重新生成，就会出现
「线上条款与源稿两个说法」——这正是本项目明令禁止的（R8.4：不许两个说法同时存在）。

比对两遍（都打印数量，R4.2：空集合/小集合永远通过，所以必须报数）：
  ① **严格**：`<!-- LEGAL:START -->…<!-- LEGAL:END -->` 之间的字节（deploy.sh 从不碰这块）—— 逐字节；
  ② **整页**：先抹掉 deploy.sh 会合法注入的三样（dsv meta / cache-check 脚本 / `?v=` 指纹），再逐字节。

不一致 ⇒ exit 1 并指名是哪一页、差在哪个区域。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import legal_render as L                                          # noqa: E402

ROOT = L.ROOT


def main():
    os.chdir(ROOT)
    bad = 0
    for doc in L.DOCS:
        want, meta = L.build(doc)
        if not os.path.exists(doc["page"]):
            print("  ❌ %s：页面不存在（先跑 render-legal.py）" % doc["page"])
            bad += 1
            continue
        have = open(doc["page"], encoding="utf-8").read()

        # ① LEGAL 区严格逐字节
        w_reg = L.legal_region(want)
        h_reg = L.legal_region(have)
        if w_reg is None:
            print("  ❌ %s：渲染结果里没有 LEGAL 标记（不该发生）" % doc["page"])
            bad += 1
            continue
        if h_reg is None:
            print("  ❌ %s：页面里没有 LEGAL 标记（被手改成别的结构了？）" % doc["page"])
            bad += 1
            continue
        same_region = (w_reg == h_reg)

        # ② 整页（抹掉 deploy.sh 的合法注入）
        same_page = (L.norm_for_gate(want) == L.norm_for_gate(have))

        mark = "✅" if (same_region and same_page) else "❌"
        print("  %s %-18s 正文区 %d 字节 %s ／ 整页 %d 字节 %s　（源稿 %s…）"
              % (mark, doc["page"], len(w_reg),
                 "一致" if same_region else "**不一致**",
                 len(L.norm_for_gate(have)),
                 "一致" if same_page else "**不一致**",
                 meta["src_sha"][:12]))
        if not same_region or not same_page:
            bad += 1
            if not same_region:
                for a, b, i in zip(w_reg.split("\n"), h_reg.split("\n"),
                                   range(1, 10 ** 6)):
                    if a != b:
                        print("       第一处不同在第 %d 行：" % i)
                        print("         源稿渲染: %s" % a.strip()[:120])
                        print("         仓库 HTML: %s" % b.strip()[:120])
                        break
            else:
                wa, ha = L.norm_for_gate(want), L.norm_for_gate(have)
                for a, b, i in zip(wa.split("\n"), ha.split("\n"), range(1, 10 ** 6)):
                    if a != b:
                        print("       （整页）第一处不同在第 %d 行：" % i)
                        print("         源稿渲染: %s" % a.strip()[:120])
                        print("         仓库 HTML: %s" % b.strip()[:120])
                        break

    print("  → 比对 %d 个页面：%d 个一致、%d 个不一致" % (len(L.DOCS), len(L.DOCS) - bad, bad))
    if bad:
        print("  ❌ 线上条款与源稿不一致 —— 跑 `python3 _build/render-legal.py` 重新生成后重试")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
