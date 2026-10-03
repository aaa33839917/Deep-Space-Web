#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""协议页「书面语」闸门 —— 只扫 `terms/` 与 `privacy/` 两页

    python3 _build/check-legal-tone.py

来源：2026-10-03 服主指出协议**口语化**——"帮你连进""换个壳重新来""把封禁洗白""是什么/不是什么"…
Lead 已把两份源稿重写成正式书面语（v1.2，人称统一「您」）；本闸门防它**回归口语**。

── 为什么只扫这两页 ────────────────────────────────────────────────
站点其它页是**宣传文案**（"点一下就连上""帅的要死"这种口吻是那里的风格，本来就允许）。
把口语词判据套到全站 = 拿产品页的风格去撞法律页的规矩，**必假红**。所以这里写死只扫这两页。

── 判据两条 ──────────────────────────────────────────────────────
A. **口语词**（见 COLLOQUIAL，每条都带理由）
B. **人称**：正文出现「你」⇒ 提示应为「您」。
   ⚠️ **「你们」是合法的，绝不能误伤** —— 这就是 `ACE`/`SPACE` 那类**子串误报**的翻版
   （Lead 第一次手扫时 `ACE` 命中了 `DEEP SPACE` 里的 `SPACE`）。
   实现：先把合法的「你们」整段标记为豁免区间，再找不在区间内的「你」。
   （如果将来出现别的合法含「你」的词——例如「迷你」——请把它加进 EXEMPT 并写理由，
     不要靠"反正不会出现"。）

── 扫什么：**可见文本**（先剥 HTML 注释 / script / style / 标签）────────
     与 check-leak.py 同一条纪律：注释里的话玩家看不到，不该被判红。
"""
import html
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = ["terms/index.html", "privacy/index.html"]

# ---- A 类：口语词（每条都写理由；判据是"正式书面语里不该这么写"）───────────
COLLOQUIAL = [
    # 来自服主 2026-10-03 点名的旧版原句 —— 这四条是**事故现场用语**，最容易回来
    ("帮你连进", "旧版 §二原句「帮你连进我们自己的游戏服务器」；正式用「用于连接」"),
    ("帮你", "口语化助动词短语；正式文本用「用于」「供您」"),
    ("连进", "口语动词（正式用「连接」）。⚠️ 子串风险：将来若出现「连接进行中」会**假红**，"
             "届时把这条换成短语级（「帮你连进」已单独在列）"),
    ("认得", "旧版 §二「让服务器认得'还是这台机器'」；正式用「识别」"),
    ("换个壳", "旧版隐私 §二「识别'换个壳重新来'」；正式用「更换硬件」"),
    ("洗白", "旧版隐私 §六「等于把封禁洗白」；正式用「使封禁失效」"),
    ("是什么", "旧版章节标题「本工具是什么，不是什么」；正式用「性质与范围」"),
    ("不是什么", "同上（与「是什么」重叠时只报最具体的那条）"),
    # Lead 建议起点里的其余口语标记（现网实测均为 0 命中）
    ("拿不准", "口语（正式用「无法确定」）"),
    ("那几样", "口语指代（正式用「下列各项」）"),
    ("搞定", "口语（正式用「完成」「处理」）"),
    ("咋", "口语疑问词。⚠️ 例外：「咋舌」是正式词（令人咋舌），见 EXEMPT"),
    ("啥", "口语疑问词"),
    ("咱们", "口语第一人称（本文档用「我们」）"),
    ("说白了", "口语（正式用「即」「换言之」）"),
    ("其实就是", "口语填充（正式用「即」「换言之」）"),
    ("一大堆", "口语量词（正式用「大量」）"),
    ("请务必", "语气过强的指令式；Lead 点名的旧版用词（正式用「请您」）"),
]

# ---- 合法词：在扫描前整段豁免（每条都要写理由）--------------------------
EXEMPT = [
    ("你们", "合法人称（如「对你们的承诺」）—— 误伤它就是 ACE/SPACE 那类子串误报"),
    ("咋舌", "「咋舌」是正式书面词（令人咋舌），不是口语「咋」"),
]

# ---- 故意**不**加的词（没证据就不加；写在这里免得后人重复想一遍）------------
#   · `请`      —— 「请您阅读」是正当书面语，按单字判会假红；
#   · `务必`    —— 单独用是正当的书面强调（如「务必遵守」），只有 `请务必` 这个组合才列为口语；
#   · `那` / `这` / `什么` —— 单独出现是正常书面词，只有具体组合（`那几样`／`是什么`）才列；
#   · `你`      —— 不进词表，改由**人称判据**处理（因为要区分「你们」）。


def visible_text(s):
    """玩家看得见的字：剥注释 / script / style / 标签。"""
    s = re.sub(r"<!--.*?-->", " ", s, flags=re.S)
    s = re.sub(r"<script\b.*?</script>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<style\b.*?</style>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def exempt_spans(text):
    out = []
    for term, _why in EXEMPT:
        for m in re.finditer(re.escape(term), text):
            out.append((m.start(), m.end(), term))
    return out


def collect(text):
    """返回 [(位置, 长度, 命中的词, 类别)]；重叠的只留最靠前、最具体的一条。"""
    raw = []
    spans = exempt_spans(text)
    for term, _why in COLLOQUIAL:
        for m in re.finditer(re.escape(term), text):
            raw.append((m.start(), len(term), term, "口语词"))
    # 豁免区间（你们 / 咋舌 …）里的命中全部丢掉
    raw = [r for r in raw if not any(a <= r[0] < b for a, b, _t in spans)]
    # 人称判据：「你」但在豁免区间里的不算（★ 你们 不误伤）
    for m in re.finditer("你", text):
        if any(a <= m.start() < b for a, b, _t in spans):
            continue
        raw.append((m.start(), 1, "你", "人称（应为「您」）"))
    raw.sort(key=lambda r: (r[0], -r[1]))
    out, last_end = [], -1
    for pos, ln, term, kind in raw:
        if pos < last_end:
            continue                      # 被更靠前、更具体的词覆盖
        out.append((pos, ln, term, kind))
        last_end = pos + ln
    return out


def ctx(text, pos, n=32):
    a, b = max(0, pos - n), min(len(text), pos + n)
    return ("…" if a else "") + text[a:b] + ("…" if b < len(text) else "")


def main():
    os.chdir(ROOT)
    hits = 0
    n_pages = 0
    for page in PAGES:
        if not os.path.exists(page):
            print("  ❌ 缺页面：%s" % page)
            hits += 1
            continue
        n_pages += 1
        vis = visible_text(open(page, encoding="utf-8").read())
        for pos, _ln, term, kind in collect(vis):
            hits += 1
            print("  ❌ %s ｜ %s「%s」" % (page, kind, term))
            print("       上下文：%s" % ctx(vis, pos))
    n_words = len(COLLOQUIAL) + 1          # +1 = 人称判据
    print("  → 扫了 %d 页 × %d 个口语词（口语词 %d + 人称判据 1）"
          % (n_pages, n_words, len(COLLOQUIAL)))
    if hits:
        print("  ❌ 命中 %d 处 —— 协议正文要正式书面语（人称统一「您」）" % hits)
    else:
        print("  ✅ 未命中：两页均为正式书面语，人称统一「您」")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
