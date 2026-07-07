#!/usr/bin/env python3
"""
選手個別ページ生成スクリプト
usage: python scripts/generate_racer_page.py [toban]
  toban を省略すると全選手分を生成
"""

import csv
import os
import sys
from datetime import date

# パス設定
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DOCS_DIR = os.path.join(BASE_DIR, "docs", "racer")

RACERS_CSV = os.path.join(DATA_DIR, "racers.csv")
RELATIONS_CSV = os.path.join(DATA_DIR, "relations.csv")

os.makedirs(DOCS_DIR, exist_ok=True)

# --------- データ読み込み ---------

def load_racers():
    racers = {}
    with open(RACERS_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            racers[row["toban"]] = row
    return racers

def load_relations():
    relations = []
    with open(RELATIONS_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if not row["source_url"].strip():
                print(f"[警告] 出典URL なし: id={row['id']}")
            relations.append(row)
    return relations

# --------- ヘルパー ---------

REL_TYPE_CLASS = {
    "配偶者": "spouse",
    "元配偶者": "spouse",
    "父": "family", "母": "family", "子": "family",
    "兄": "family", "姉": "family", "弟": "family", "妹": "family", "親族": "family",
    "師匠": "mentor", "弟子": "mentor",
    "友人": "friend", "同期": "friend", "仲良し": "friend",
}

CONF_LABEL = {
    "A": ("a", "◎ 本人公表"),
    "B": ("b", "○ 報道"),
}

STATUS_LABEL = {
    "active": "現役",
    "retired": "引退",
    "inactive": "休業",
}

def fmt_birth(birth_str):
    """1985-04-01 → 1985年4月1日"""
    try:
        y, m, d = birth_str.split("-")
        return f"{y}年{int(m)}月{int(d)}日"
    except Exception:
        return birth_str

def fmt_checked(checked_str):
    """2026-07-06 → 2026年7月6日"""
    try:
        y, m, d = checked_str.split("-")
        return f"{y}年{int(m)}月{int(d)}日"
    except Exception:
        return checked_str

def get_relations_for(toban, relations, racers):
    """
    toban の選手に関係する行を取得。
    - confidence=C は除外
    - source_url なしは除外
    - 片方向記録なので逆方向も補完する
    """
    REVERSE = {
        "父": "子", "母": "子", "子": "父/母",
        "兄": "弟/妹", "姉": "弟/妹", "弟": "兄/姉", "妹": "兄/姉",
        "師匠": "弟子", "弟子": "師匠",
        "配偶者": "配偶者", "元配偶者": "元配偶者",
        "親族": "親族", "友人": "友人", "同期": "同期", "仲良し": "仲良し",
    }

    result = []
    for r in relations:
        if r["confidence"] == "C":
            continue
        if not r["source_url"].strip():
            continue

        if r["from_toban"] == toban:
            other_toban = r["to_toban"]
            other_name = r["to_name"]
            rel = r["rel_type"]
            result.append((rel, other_toban, other_name, r["confidence"], r["source_url"]))

        elif r["to_toban"] == toban:
            other_toban = r["from_toban"]
            other_name = racers.get(other_toban, {}).get("name", "")
            rev_rel = REVERSE.get(r["rel_type"], r["rel_type"])
            result.append((rev_rel, other_toban, other_name, r["confidence"], r["source_url"]))

    return result

# --------- HTML生成 ---------

def rel_card_html(rel, other_toban, other_name, conf, source_url, racers):
    card_class = REL_TYPE_CLASS.get(rel, "")
    conf_cls, conf_label = CONF_LABEL.get(conf, ("b", "○ 報道"))

    other = racers.get(other_toban, {})
    meta_parts = []
    if other.get("branch"):
        meta_parts.append(f"{other['branch']}支部")
    if other.get("ki"):
        meta_parts.append(f"{other['ki']}期")
    if other.get("status"):
        meta_parts.append(STATUS_LABEL.get(other["status"], other["status"]))
    meta_str = "・".join(meta_parts)

    if other_toban:
        href = f"{other_toban}.html"
        name_html = f'{other_name} <span style="font-family:var(--mono);font-size:12px;color:var(--muted)">{other_toban}</span>'
    else:
        href = source_url
        name_html = other_name

    return f'''      <a class="rel-card {card_class}" href="{href}">
        <div class="rel-type">{rel}</div>
        <div class="rel-name">{name_html}</div>
        <div class="rel-meta"><span>{meta_str}</span><span class="conf {conf_cls}">{conf_label}</span></div>
      </a>'''


def generate_page(toban, racers, relations):
    r = racers.get(toban)
    if not r:
        print(f"[エラー] 登録番号 {toban} が racers.csv に見つかりません")
        return

    rel_rows = get_relations_for(toban, relations, racers)

    # 人間関係カード HTML
    if rel_rows:
        cards_html = "\n".join(
            rel_card_html(rel, ot, on, conf, src, racers)
            for rel, ot, on, conf, src in rel_rows
        )
        rel_section = f'''  <section>
    <h2>人間関係 <span class="en">RELATIONS</span></h2>
    <div class="rel-grid">
{cards_html}
    </div>
    <div class="rel-note">確度表示：◎＝本人が公表　○＝メディア報道。各カードをクリックすると選手ページへ移動します。噂レベルの情報は掲載していません。</div>
  </section>'''
    else:
        rel_section = '''  <section>
    <h2>人間関係 <span class="en">RELATIONS</span></h2>
    <p style="margin-top:14px;color:var(--muted)">現在、掲載できる人間関係情報はありません。</p>
  </section>'''

    # 基本情報テーブル
    birth_str = fmt_birth(r["birth"]) if r["birth"] else "—"
    status_str = STATUS_LABEL.get(r["status"], r["status"])
    hobby_str = r["hobby"] if r["hobby"] else "—"
    note_str = r["note"] if r["note"] else ""

    profile_rows = f"""      <tr><th>生年月日</th><td>{birth_str}</td></tr>
      <tr><th>出身地</th><td>{r['hometown'] or '—'}</td></tr>
      <tr><th>支部</th><td>{r['branch'] or '—'}支部</td></tr>
      <tr><th>期別</th><td>{r['ki'] or '—'}期</td></tr>
      <tr><th>級別</th><td>{r['grade'] or '—'}</td></tr>
      <tr><th>現況</th><td>{status_str}</td></tr>
      <tr><th>趣味</th><td>{hobby_str}</td></tr>"""
    if note_str:
        profile_rows += f"\n      <tr><th>備考</th><td>{note_str}</td></tr>"

    # 外部リンク
    links_html = f'      <a class="chip" href="https://boatrace.jp/owpc/pc/data/racersearch/profile?toban={toban}" target="_blank" rel="noopener">BOAT RACE公式プロフィール</a>\n'
    links_html += f'      <a class="chip" href="https://boatrace-db.net/racer/index2/regno/{toban}" target="_blank" rel="noopener">艇国データバンク（成績）</a>\n'
    if r["x_url"]:
        links_html += f'      <a class="chip" href="{r["x_url"]}" target="_blank" rel="noopener">X（Twitter）</a>\n'
    if r["insta_url"]:
        links_html += f'      <a class="chip" href="{r["insta_url"]}" target="_blank" rel="noopener">Instagram</a>\n'
    if r["youtube_url"]:
        links_html += f'      <a class="chip" href="{r["youtube_url"]}" target="_blank" rel="noopener">YouTube</a>\n'

    checked_str = fmt_checked(r["checked"]) if r["checked"] else str(date.today())
    name_parts = r["name"].split() if " " in r["name"] else [r["name"]]
    name_display = "　".join(name_parts) if len(name_parts) > 1 else r["name"]

    html = f'''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{r["name"]}（{toban}・{r["branch"]}）｜舟☆探 選手名鑑</title>
<link href="https://fonts.googleapis.com/css2?family=Zen+Old+Mincho:wght@600;900&family=Zen+Kaku+Gothic+New:wght@400;500;700&family=IBM+Plex+Mono:wght@500;600&display=swap" rel="stylesheet">
<style>
  :root{{
    --ink:#1C2530;
    --paper:#F7F5F0;
    --navy:#0E2A3C;
    --navy-2:#173B52;
    --red:#E33A2E;
    --blue:#2E5FE3;
    --yellow:#F2C21F;
    --green:#2FA65A;
    --line:#D8D3C8;
    --muted:#6B7280;
    --serif:'Zen Old Mincho',serif;
    --sans:'Zen Kaku Gothic New',sans-serif;
    --mono:'IBM Plex Mono',monospace;
  }}
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{background:var(--paper);color:var(--ink);font-family:var(--sans);line-height:1.7;font-size:15px}}
  a{{color:inherit}}

  .lane-strip{{display:flex;height:6px}}
  .lane-strip span{{flex:1}}
  .lane-strip .l1{{background:#fff;border-bottom:1px solid var(--line)}}
  .lane-strip .l2{{background:#222}}
  .lane-strip .l3{{background:var(--red)}}
  .lane-strip .l4{{background:var(--blue)}}
  .lane-strip .l5{{background:var(--yellow)}}
  .lane-strip .l6{{background:var(--green)}}

  header{{background:var(--navy);color:#fff}}
  .topbar{{max-width:720px;margin:0 auto;padding:14px 20px;display:flex;justify-content:space-between;align-items:baseline}}
  .brand{{font-family:var(--serif);font-weight:900;font-size:18px;letter-spacing:.08em}}
  .brand small{{font-family:var(--sans);font-weight:500;font-size:11px;opacity:.7;margin-left:8px;letter-spacing:.15em}}
  .brand a{{text-decoration:none}}
  .topbar nav{{font-size:12px;opacity:.85}}
  .topbar nav a{{text-decoration:none;margin-left:14px}}

  .hero{{background:var(--navy);color:#fff;padding:28px 20px 34px}}
  .hero-in{{max-width:720px;margin:0 auto}}
  .toban{{font-family:var(--mono);font-weight:600;font-size:14px;letter-spacing:.2em;color:var(--yellow)}}
  .toban::before{{content:"登録番号 ";font-family:var(--sans);font-weight:500;font-size:11px;letter-spacing:.1em;color:rgba(255,255,255,.55)}}
  h1{{font-family:var(--serif);font-weight:900;font-size:44px;line-height:1.15;margin:6px 0 2px;letter-spacing:.04em}}
  .kana{{font-size:13px;letter-spacing:.35em;color:rgba(255,255,255,.65)}}
  .badges{{margin-top:16px;display:flex;gap:8px;flex-wrap:wrap}}
  .badge{{font-size:12px;font-weight:700;padding:4px 12px;border-radius:3px;background:var(--navy-2);border:1px solid rgba(255,255,255,.18)}}
  .badge.grade{{background:var(--red);border-color:var(--red);font-family:var(--mono)}}
  .checked{{margin-top:14px;font-size:11px;color:rgba(255,255,255,.5)}}

  main{{max-width:720px;margin:0 auto;padding:8px 20px 40px}}
  section{{margin-top:34px}}
  h2{{font-family:var(--serif);font-weight:600;font-size:20px;letter-spacing:.06em;padding-bottom:8px;border-bottom:2px solid var(--ink);display:flex;align-items:baseline;justify-content:space-between}}
  h2 .en{{font-family:var(--mono);font-size:10px;letter-spacing:.2em;color:var(--muted);font-weight:500}}

  .rel-grid{{margin-top:16px;display:grid;grid-template-columns:1fr 1fr;gap:10px}}
  @media(max-width:480px){{.rel-grid{{grid-template-columns:1fr}}}}
  .rel-card{{background:#fff;border:1px solid var(--line);border-left:4px solid var(--navy);border-radius:4px;padding:12px 14px;text-decoration:none;display:block;transition:transform .12s ease}}
  .rel-card:hover{{transform:translateY(-2px)}}
  .rel-card.family{{border-left-color:var(--blue)}}
  .rel-card.spouse{{border-left-color:var(--red)}}
  .rel-card.mentor{{border-left-color:var(--green)}}
  .rel-type{{font-size:11px;font-weight:700;letter-spacing:.15em;color:var(--muted)}}
  .rel-name{{font-family:var(--serif);font-weight:600;font-size:18px;margin-top:2px}}
  .rel-meta{{margin-top:6px;font-size:11px;color:var(--muted);display:flex;justify-content:space-between;align-items:center}}
  .conf{{font-weight:700;padding:1px 8px;border-radius:10px;font-size:10px}}
  .conf.a{{background:#E7F3EB;color:#1E7A41}}
  .conf.b{{background:#FDF3D7;color:#9A7208}}
  .rel-note{{margin-top:14px;font-size:11px;color:var(--muted)}}

  table{{width:100%;margin-top:14px;border-collapse:collapse;background:#fff;border:1px solid var(--line);font-size:14px}}
  th,td{{padding:10px 14px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}}
  th{{width:110px;background:#EFEBE2;font-weight:700;font-size:12px;letter-spacing:.05em}}
  tr:last-child th,tr:last-child td{{border-bottom:none}}

  .links{{margin-top:14px;display:flex;flex-wrap:wrap;gap:8px}}
  .chip{{font-size:12px;font-weight:500;padding:7px 14px;background:#fff;border:1px solid var(--line);border-radius:20px;text-decoration:none}}
  .chip:hover{{border-color:var(--navy)}}

  .cta{{margin-top:40px;background:var(--navy);color:#fff;border-radius:6px;padding:26px 22px;position:relative;overflow:hidden}}
  .cta .lane-strip{{position:absolute;top:0;left:0;right:0}}
  .cta h3{{font-family:var(--serif);font-weight:900;font-size:22px;letter-spacing:.05em}}
  .cta p{{margin-top:8px;font-size:13px;color:rgba(255,255,255,.8)}}
  .unki-btn{{display:block;margin:24px 0 4px;text-align:center;background:var(--navy);color:#fff;text-decoration:none;font-weight:700;font-size:14px;padding:14px 20px;border-radius:6px;letter-spacing:.05em}}
  .unki-btn:hover{{opacity:.88}}
  .cta-btn{{display:inline-block;margin-top:16px;background:var(--red);color:#fff;text-decoration:none;font-weight:700;font-size:14px;padding:12px 28px;border-radius:4px;letter-spacing:.05em}}
  .cta-btn:hover{{opacity:.9}}

  footer{{border-top:1px solid var(--line);margin-top:48px;padding:20px;text-align:center;font-size:11px;color:var(--muted)}}
</style>
</head>
<body>

<header>
  <div class="topbar">
    <div class="brand"><a href="../index.html">舟☆探<small>選手名鑑</small></a></div>
    <nav><a href="../couples.html">夫婦一覧</a><a href="../siblings.html">兄弟一覧</a><a href="../shitei.html">師弟一覧</a></nav>
  </div>
  <div class="lane-strip"><span class="l1"></span><span class="l2"></span><span class="l3"></span><span class="l4"></span><span class="l5"></span><span class="l6"></span></div>

  <div class="hero">
    <div class="hero-in">
      <div class="toban">{toban}</div>
      <h1>{name_display}</h1>
      <div class="kana">{r["kana"]}</div>
      <div class="badges">
        <span class="badge grade">{r["grade"]}</span>
        <span class="badge">{r["branch"]}支部</span>
        <span class="badge">{r["ki"]}期</span>
        <span class="badge">{status_str}</span>
      </div>
      <div class="checked">最終確認：{checked_str}</div>
    </div>
  </div>
</header>

<main>

{rel_section}

  <section>
    <h2>基本情報 <span class="en">PROFILE</span></h2>
    <table>
{profile_rows}
    </table>
  </section>

  <section>
    <h2>公式・外部リンク <span class="en">LINKS</span></h2>
    <div class="links">
{links_html}    </div>
  </section>

  {'<a class="unki-btn" href="../unki/' + toban + '.html">🔮 ' + r["name"] + 'の今日の艇運を見る</a>' if r.get("birth") else ''}

  <div class="cta">
    <div class="lane-strip"><span class="l1"></span><span class="l2"></span><span class="l3"></span><span class="l4"></span><span class="l5"></span><span class="l6"></span></div>
    <h3>{r["name"]}の今節の狙い目は？</h3>
    <p>AI予想エンジン「舟☆探」が、データと人間関係の両面からレースを読む。<br>LINE登録で無料予想と選手の最新ニュースが届きます。</p>
    <a class="cta-btn" href="#">舟☆探の無料予想を見る</a>
  </div>

</main>

<footer>
  舟☆探 選手名鑑 ｜ 掲載情報にはすべて出典を明記しています。訂正のご連絡はこちら
</footer>

</body>
</html>
'''

    out_path = os.path.join(DOCS_DIR, f"{toban}.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[生成] {out_path}")


# --------- エントリポイント ---------

if __name__ == "__main__":
    racers = load_racers()
    relations = load_relations()

    if len(sys.argv) >= 2:
        targets = sys.argv[1:]
    else:
        targets = list(racers.keys())

    for t in targets:
        generate_page(t, racers, relations)

    print("完了")
