#!/usr/bin/env python3
"""
まとめページ4種一括生成スクリプト
usage: python3 scripts/generate_summary_pages.py

生成するページ:
  docs/couples.html  ── 夫婦・元夫婦一覧
  docs/siblings.html ── 兄弟姉妹一覧
  docs/shitei.html   ── 師弟一覧
  docs/hobby.html    ── 趣味別逆引き

【仕様】
  - relations.csv の confidence=C 行・source_url なし行は除外
  - 双方向補完あり（師匠→弟子 の行から「弟子の一覧」に師匠名も表示）
  - racers.csv に登録番号がある人のみ内部リンク
"""

import csv
import os
from datetime import date
from collections import defaultdict

BASE_DIR      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RACERS_CSV    = os.path.join(BASE_DIR, "data", "racers.csv")
RELATIONS_CSV = os.path.join(BASE_DIR, "data", "relations.csv")
DOCS_DIR      = os.path.join(BASE_DIR, "docs")

TODAY_STR = date.today().strftime("%Y年%-m月%-d日")

# 配偶者系
SPOUSE_TYPES  = {"配偶者", "元配偶者"}
# 兄弟姉妹系
SIBLING_TYPES = {"兄", "姉", "弟", "妹"}
# 師弟系
SHITEI_TYPES  = {"師匠", "弟子"}


# ──────────────────────────────────────────
# データ読み込み
# ──────────────────────────────────────────

def load_racers():
    racers = {}
    with open(RACERS_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            racers[row["toban"]] = row
    return racers


def load_relations():
    rels = []
    with open(RELATIONS_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("confidence") == "C":
                continue
            if not row.get("source_url", "").strip():
                continue
            rels.append(row)
    return rels


# ──────────────────────────────────────────
# ヘルパー
# ──────────────────────────────────────────

CONF_LABEL = {"A": "◎ 本人公表", "B": "○ 報道"}

def racer_link(toban, name, racers):
    """登録番号があれば選手ページへのリンク、なければ名前のみ"""
    r = racers.get(toban, {})
    display = name or r.get("name") or f"（{toban}）"
    if toban and toban in racers:
        return f'<a href="racer/{toban}.html" class="rlink">{display} <span class="toban">{toban}</span></a>'
    return f'<span class="rlink-plain">{display}</span>'


def meta_str(toban, racers):
    r = racers.get(toban, {})
    parts = []
    if r.get("branch"):
        parts.append(f"{r['branch']}支部")
    if r.get("ki"):
        parts.append(f"{r['ki']}期")
    grade = r.get("grade", "")
    if grade:
        parts.append(grade)
    return "・".join(parts)


def conf_badge(c):
    label = CONF_LABEL.get(c, c)
    cls = "badge-a" if c == "A" else "badge-b"
    return f'<span class="badge {cls}">{label}</span>'


# ──────────────────────────────────────────
# 共通HTML部品
# ──────────────────────────────────────────

COMMON_CSS = """
  :root{
    --ink:#1C2530; --paper:#F7F5F0; --navy:#0E2A3C;
    --red:#E33A2E; --blue:#2E5FE3; --yellow:#F2C21F; --green:#2FA65A;
    --line:#D8D3C8; --muted:#6B7280;
  }
  *{margin:0;padding:0;box-sizing:border-box}
  body{background:var(--paper);color:var(--ink);font-family:'Helvetica Neue',Arial,'Hiragino Kaku Gothic ProN',sans-serif;line-height:1.7;font-size:15px}
  a{color:inherit}

  .lane-strip{display:flex;height:6px}
  .lane-strip span{flex:1}
  .l1{background:#fff;border-bottom:1px solid var(--line)}.l2{background:#222}
  .l3{background:var(--red)}.l4{background:var(--blue)}.l5{background:var(--yellow)}.l6{background:var(--green)}

  header{background:var(--navy);color:#fff}
  .topbar{max-width:800px;margin:0 auto;padding:12px 20px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px}
  .brand{font-weight:900;font-size:17px;letter-spacing:.06em}
  .nav-links{display:flex;gap:14px;font-size:12px}
  .nav-links a{color:rgba(255,255,255,.75);text-decoration:none}
  .nav-links a:hover{color:#fff}
  .hero{background:var(--navy);padding:18px 20px 26px}
  .hero-in{max-width:800px;margin:0 auto}
  .hero h1{font-weight:900;font-size:24px;letter-spacing:.04em}
  .hero p{font-size:13px;color:rgba(255,255,255,.7);margin-top:4px}

  main{max-width:800px;margin:0 auto;padding:12px 20px 60px}
  .count{font-size:13px;color:var(--muted);margin:16px 0 8px}

  .table-wrap{overflow-x:auto;-webkit-overflow-scrolling:touch}
  table{width:100%;border-collapse:collapse;margin-top:8px;font-size:14px;min-width:480px}
  th{background:var(--navy);color:#fff;font-weight:700;font-size:12px;letter-spacing:.08em;padding:8px 12px;text-align:left}
  td{padding:10px 12px;border-bottom:1px solid var(--line);vertical-align:top}
  tr:hover td{background:#F0EDE6}
  .rlink{font-weight:700;text-decoration:none;color:var(--navy)}
  .rlink:hover{text-decoration:underline}
  .rlink-plain{font-weight:700}
  .toban{font-family:monospace;font-size:11px;color:var(--muted);font-weight:400}
  .meta{font-size:12px;color:var(--muted)}
  .badge{font-size:11px;font-weight:700;padding:2px 8px;border-radius:10px}
  .badge-a{background:#E7F3EB;color:#1E7A41;border:1px solid #A3D9B1}
  .badge-b{background:#EBF0FB;color:#1A3FA3;border:1px solid #A3BAF5}
  .src{font-size:11px}
  .src a{color:var(--blue);text-decoration:none}
  .src a:hover{text-decoration:underline}
  .empty{text-align:center;padding:60px;color:var(--muted);font-size:15px}

  .hobby-section{margin-top:28px}
  .hobby-section h2{font-weight:900;font-size:17px;padding-bottom:6px;border-bottom:2px solid var(--ink)}
  .hobby-tags{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}
  .hobby-tag{font-size:13px;font-weight:700;padding:6px 14px;border-radius:16px;background:#fff;border:1px solid var(--line);cursor:pointer;text-decoration:none;color:var(--navy)}
  .hobby-tag:hover{border-color:var(--navy);background:var(--navy);color:#fff}
  .hobby-group{margin-top:20px}
  .hobby-group h3{font-size:15px;font-weight:700;margin-bottom:8px;padding:6px 12px;background:#fff;border-left:4px solid var(--navy);border:1px solid var(--line);border-radius:4px}
  .racer-chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px}
  .racer-chip{font-size:13px;font-weight:700;padding:6px 14px;border-radius:16px;background:#fff;border:1px solid var(--line);text-decoration:none;color:var(--navy)}
  .racer-chip:hover{border-color:var(--navy)}

  .checked{font-size:11px;color:var(--muted);margin-top:24px;text-align:right}
  footer{border-top:1px solid var(--line);margin-top:40px;padding:16px;text-align:center;font-size:11px;color:var(--muted)}
"""

def page_header(title_ja, title_en, desc):
    return f'''<header>
  <div class="topbar">
    <div class="brand">舟☆探</div>
    <nav class="nav-links">
      <a href="index.html">トップ</a>
      <a href="map.html">関係マップ</a>
      <a href="couples.html">夫婦</a>
      <a href="siblings.html">兄弟</a>
      <a href="shitei.html">師弟</a>
      <a href="hobby.html">趣味</a>
    </nav>
  </div>
  <div class="lane-strip"><span class="l1"></span><span class="l2"></span><span class="l3"></span><span class="l4"></span><span class="l5"></span><span class="l6"></span></div>
  <div class="hero">
    <div class="hero-in">
      <h1>{title_ja} <span style="font-family:monospace;font-size:13px;font-weight:400;opacity:.6">{title_en}</span></h1>
      <p>{desc}</p>
    </div>
  </div>
</header>'''

def page_footer():
    return f'''  <div class="checked">データ確認日: {TODAY_STR}</div>
</main>
<footer>舟☆探 選手名鑑｜掲載情報にはすべて出典を明記しています。</footer>
</body>
</html>'''


# ──────────────────────────────────────────
# 夫婦一覧
# ──────────────────────────────────────────

def generate_couples(rels, racers):
    pairs = []
    seen = set()

    for r in rels:
        if r["rel_type"] not in SPOUSE_TYPES:
            continue
        key = tuple(sorted([r["from_toban"], r["to_toban"]]))
        if key in seen:
            continue
        seen.add(key)

        from_toban = r["from_toban"]
        from_name  = racers.get(from_toban, {}).get("name") or from_toban
        to_toban   = r["to_toban"]
        to_name    = r["to_name"] or racers.get(to_toban, {}).get("name") or to_toban
        rel        = r["rel_type"]
        conf       = r.get("confidence", "B")
        src_url    = r.get("source_url", "")
        src_date   = r.get("source_date", "")

        pairs.append((from_toban, from_name, to_toban, to_name, rel, conf, src_url, src_date))

    rows_html = ""
    for from_toban, from_name, to_toban, to_name, rel, conf, src_url, src_date in pairs:
        from_link = racer_link(from_toban, from_name, racers)
        to_link   = racer_link(to_toban, to_name, racers)
        from_meta = meta_str(from_toban, racers)
        to_meta   = meta_str(to_toban, racers)
        src_html  = f'<a href="{src_url}" target="_blank" rel="noopener">出典</a>' if src_url else "—"
        label     = "元配偶者" if rel == "元配偶者" else "配偶者"
        rows_html += f'''<tr>
  <td>{from_link}<div class="meta">{from_meta}</div></td>
  <td style="text-align:center;font-weight:700;color:var(--red)">{"💍 " + label}</td>
  <td>{to_link}<div class="meta">{to_meta}</div></td>
  <td>{conf_badge(conf)}</td>
  <td class="src">{src_html}<br><span style="color:var(--muted)">{src_date}</span></td>
</tr>'''

    if not rows_html:
        rows_html = '<tr><td colspan="5" class="empty">掲載できるデータがありません。<br>scrape_macour.py や add_relation.py で追加してください。</td></tr>'

    count = len(pairs)
    html = f'''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>夫婦・カップル一覧｜舟☆探</title>
<style>{COMMON_CSS}</style>
</head>
<body>
{page_header("夫婦・カップル一覧", "COUPLES", "競艇選手同士・選手と一般人のカップル情報。すべて出典付き。")}
<main>
  <div class="count">{count} 組を掲載</div>
  <div class="table-wrap"><table>
    <thead><tr><th>選手</th><th>関係</th><th>パートナー</th><th>確度</th><th>出典</th></tr></thead>
    <tbody>{rows_html}</tbody>
  </table></div>
{page_footer()}
'''
    out = os.path.join(DOCS_DIR, "couples.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[生成] {out}（{count}組）")


# ──────────────────────────────────────────
# 兄弟姉妹一覧
# ──────────────────────────────────────────

def generate_siblings(rels, racers):
    pairs = []
    seen = set()

    for r in rels:
        if r["rel_type"] not in SIBLING_TYPES:
            continue
        key = tuple(sorted([r["from_toban"], r["to_toban"]]))
        if key in seen:
            continue
        seen.add(key)

        from_toban = r["from_toban"]
        from_name  = racers.get(from_toban, {}).get("name") or from_toban
        to_toban   = r["to_toban"]
        to_name    = r["to_name"] or racers.get(to_toban, {}).get("name") or to_toban
        rel        = r["rel_type"]  # 兄/姉/弟/妹
        conf       = r.get("confidence", "B")
        src_url    = r.get("source_url", "")
        src_date   = r.get("source_date", "")

        # fromが兄/姉の場合: from=年上、to=年下
        # fromが弟/妹の場合: from=年下、to=年上 → 表示は年上が左に来るよう入れ替え
        if rel in ("弟", "妹"):
            elder_toban, elder_name = to_toban, to_name
            younger_toban, younger_name = from_toban, from_name
            rel_label = "兄弟姉妹"
        else:
            elder_toban, elder_name = from_toban, from_name
            younger_toban, younger_name = to_toban, to_name
            rel_label = f"{rel}（上）"

        pairs.append((elder_toban, elder_name, younger_toban, younger_name, rel_label, conf, src_url, src_date))

    rows_html = ""
    for elder_toban, elder_name, younger_toban, younger_name, rel_label, conf, src_url, src_date in pairs:
        elder_link   = racer_link(elder_toban, elder_name, racers)
        younger_link = racer_link(younger_toban, younger_name, racers)
        elder_meta   = meta_str(elder_toban, racers)
        younger_meta = meta_str(younger_toban, racers)
        src_html     = f'<a href="{src_url}" target="_blank" rel="noopener">出典</a>' if src_url else "—"
        rows_html += f'''<tr>
  <td>{elder_link}<div class="meta">{elder_meta}</div></td>
  <td style="text-align:center;font-size:18px">👨‍👦</td>
  <td>{younger_link}<div class="meta">{younger_meta}</div></td>
  <td>{conf_badge(conf)}</td>
  <td class="src">{src_html}<br><span style="color:var(--muted)">{src_date}</span></td>
</tr>'''

    if not rows_html:
        rows_html = '<tr><td colspan="5" class="empty">掲載できるデータがありません。<br>scrape_macour.py や add_relation.py で追加してください。</td></tr>'

    count = len(pairs)
    html = f'''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>兄弟・姉妹一覧｜舟☆探</title>
<style>{COMMON_CSS}</style>
</head>
<body>
{page_header("兄弟・姉妹一覧", "SIBLINGS", "競艇選手の兄弟姉妹ペア一覧。すべて出典付き。")}
<main>
  <div class="count">{count} 組を掲載</div>
  <div class="table-wrap"><table>
    <thead><tr><th>年上</th><th></th><th>年下</th><th>確度</th><th>出典</th></tr></thead>
    <tbody>{rows_html}</tbody>
  </table></div>
{page_footer()}
'''
    out = os.path.join(DOCS_DIR, "siblings.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[生成] {out}（{count}組）")


# ──────────────────────────────────────────
# 師弟一覧
# ──────────────────────────────────────────

def generate_shitei(rels, racers):
    """
    師匠→弟子 の組を正規化して一覧化。
    rel_type=師匠: from が弟子、to_name が師匠名
    rel_type=弟子: from が弟子、to_toban が師匠
    """
    pairs = []
    seen = set()

    for r in rels:
        if r["rel_type"] not in SHITEI_TYPES:
            continue

        if r["rel_type"] == "師匠":
            # from_toban=弟子、to=師匠
            deshi_toban = r["from_toban"]
            shisho_toban = r["to_toban"]
            shisho_name  = r["to_name"] or racers.get(r["to_toban"], {}).get("name") or r["to_toban"]
        else:  # 弟子
            # from_toban=弟子、to=師匠
            deshi_toban  = r["from_toban"]
            shisho_toban = r["to_toban"]
            shisho_name  = r["to_name"] or racers.get(r["to_toban"], {}).get("name") or r["to_toban"]

        key = tuple(sorted([deshi_toban, shisho_toban]))
        if key in seen:
            continue
        seen.add(key)

        deshi_name = racers.get(deshi_toban, {}).get("name") or deshi_toban
        conf    = r.get("confidence", "B")
        src_url = r.get("source_url", "")
        src_date= r.get("source_date", "")
        pairs.append((shisho_toban, shisho_name, deshi_toban, deshi_name, conf, src_url, src_date))

    rows_html = ""
    for shisho_toban, shisho_name, deshi_toban, deshi_name, conf, src_url, src_date in pairs:
        shisho_link = racer_link(shisho_toban, shisho_name, racers)
        deshi_link  = racer_link(deshi_toban, deshi_name, racers)
        shisho_meta = meta_str(shisho_toban, racers)
        deshi_meta  = meta_str(deshi_toban, racers)
        src_html    = f'<a href="{src_url}" target="_blank" rel="noopener">出典</a>' if src_url else "—"
        rows_html += f'''<tr>
  <td>{shisho_link}<div class="meta">{shisho_meta}</div></td>
  <td style="text-align:center;font-weight:700;color:var(--navy)">→</td>
  <td>{deshi_link}<div class="meta">{deshi_meta}</div></td>
  <td>{conf_badge(conf)}</td>
  <td class="src">{src_html}<br><span style="color:var(--muted)">{src_date}</span></td>
</tr>'''

    if not rows_html:
        rows_html = '<tr><td colspan="5" class="empty">掲載できるデータがありません。<br>scrape_macour.py や add_relation.py で追加してください。</td></tr>'

    count = len(pairs)
    html = f'''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>師弟一覧｜舟☆探</title>
<style>{COMMON_CSS}</style>
</head>
<body>
{page_header("師弟一覧", "MASTER & APPRENTICE", "競艇選手の師匠と弟子の関係一覧。すべて出典付き。")}
<main>
  <div class="count">{count} 組を掲載（師匠 → 弟子の順）</div>
  <div class="table-wrap"><table>
    <thead><tr><th>師匠</th><th></th><th>弟子</th><th>確度</th><th>出典</th></tr></thead>
    <tbody>{rows_html}</tbody>
  </table></div>
{page_footer()}
'''
    out = os.path.join(DOCS_DIR, "shitei.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[生成] {out}（{count}組）")


# ──────────────────────────────────────────
# 趣味別逆引き
# ──────────────────────────────────────────

def generate_hobby(racers):
    hobby_map = defaultdict(list)
    for toban, r in racers.items():
        hobby = r.get("hobby", "").strip()
        if not hobby:
            continue
        # カンマ・読点で複数趣味を分割
        for h in hobby.replace("、", ",").replace("・", ",").split(","):
            h = h.strip()
            if h:
                hobby_map[h].append((toban, r.get("name", toban)))

    sorted_hobbies = sorted(hobby_map.items(), key=lambda x: -len(x[1]))

    if not hobby_map:
        body = '<p class="empty" style="margin-top:40px">趣味データはまだ登録されていません。<br>racers.csv の hobby 列を埋めると自動的に表示されます。</p>'
    else:
        # タグクラウド
        tags = "".join(
            f'<a class="hobby-tag" href="#hobby-{i}">{h}（{len(members)}人）</a>'
            for i, (h, members) in enumerate(sorted_hobbies)
        )
        # 各趣味のグループ
        groups = ""
        for i, (h, members) in enumerate(sorted_hobbies):
            chips = "".join(
                racer_link(toban, name, racers).replace('class="rlink"', 'class="racer-chip"')
                for toban, name in sorted(members, key=lambda x: x[1])
            )
            groups += f'<div class="hobby-group" id="hobby-{i}"><h3>{h}（{len(members)}人）</h3><div class="racer-chips">{chips}</div></div>'
        body = f'<div class="hobby-tags">{tags}</div>{groups}'

    total = sum(len(m) for m in hobby_map.values())
    count_str = f"{len(hobby_map)} 種類の趣味に {total} 名が登録" if hobby_map else "趣味データなし"

    html = f'''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>趣味別選手一覧｜舟☆探</title>
<style>{COMMON_CSS}</style>
</head>
<body>
{page_header("趣味別選手逆引き", "HOBBIES", "登録された趣味から選手を逆引き。racers.csv の hobby 列に入力すると自動反映。")}
<main>
  <div class="count">{count_str}</div>
  <div class="hobby-section">{body}</div>
{page_footer()}
'''
    out = os.path.join(DOCS_DIR, "hobby.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    count = len(hobby_map)
    print(f"[生成] {out}（{count}趣味）")


# ──────────────────────────────────────────
# メイン
# ──────────────────────────────────────────

def main():
    racers = load_racers()
    rels   = load_relations()

    generate_couples(rels, racers)
    generate_siblings(rels, racers)
    generate_shitei(rels, racers)
    generate_hobby(racers)

    print(f"\n4ページを生成しました。")
    print(f"  docs/couples.html  ← 夫婦一覧")
    print(f"  docs/siblings.html ← 兄弟一覧")
    print(f"  docs/shitei.html   ← 師弟一覧")
    print(f"  docs/hobby.html    ← 趣味別")


if __name__ == "__main__":
    main()
