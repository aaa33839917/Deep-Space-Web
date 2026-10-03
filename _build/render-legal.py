#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""渲染两个协议页（terms / privacy）—— 构建期跑，也挂进 deploy.sh

    python3 _build/render-legal.py            # 写入
    python3 _build/render-legal.py --dry      # 只看会改什么，不写

真源是项目根 `法律文本/*.md`（只读）。正文之外的头（版本 / 更新时间 / 生效日期 / 状态）
**全部从源稿读出来**，本脚本一个字都不写死。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import legal_render as L                                          # noqa: E402

ROOT = L.ROOT


def main():
    os.chdir(ROOT)
    dry = "--dry" in sys.argv
    changed = 0
    for doc in L.DOCS:
        page, meta = L.build(doc)
        old = open(doc["page"], encoding="utf-8").read() if os.path.exists(doc["page"]) else None
        state = "新建" if old is None else ("有改动" if old != page else "已是最新")
        if old != page and not dry:
            os.makedirs(os.path.dirname(doc["page"]) or ".", exist_ok=True)
            open(doc["page"], "w", encoding="utf-8").write(page)
            changed += 1
        print("  %-18s %-6s 章节 %d 个  源稿 sha256 %s…" %
              (doc["page"], state, meta["sec"], meta["src_sha"][:12]))
        print("      版本行（源稿）：%s" % meta["version"])
        print("      状态行（源稿）：%s" % meta["status"])
        if meta["title_note"]:
            print("      ⚠️  %s" % meta["title_note"])
        if meta["dropped_links"]:
            print("      ⚠️  未做成链接（内部文档，不该在公网可点）：%s"
                  % "、".join(meta["dropped_links"]))
    print("  → %s：%d/%d 个页面%s" % ("干跑" if dry else "写入", changed, len(L.DOCS),
                                     "" if dry else "（内容有变才写盘）"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
