#!/usr/bin/env python3
"""
承認UI生成スクリプト
usage: python scripts/generate_review.py

candidates.json を読み込み、ブラウザで確認・承認できる
docs/review/index.html を生成する。
"""

import csv
import json
import os
from datetime import date

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANDIDATES_JSON = os.path.join(BASE_DIR, "scripts", "cache", "candidates.json")
RACERS_CSV      = os.path.join(BASE_DIR, "data", "racers.csv")
OUT_DIR         = os.path.join(BASE_DIR, "docs", "review")
OUT_HTML        = os.path.join(OUT_DIR, "index.html")

os.makedirs(OUT_DIR, exist_ok=True)

REL_TYPES = [
    "父", "母", "子", "兄", "姉", "弟", "妹",
    "配偶者", "元配偶者", "師匠", "弟子", "親族",
    "友人", "同期", "仲良し",
]

CONF_OPTIONS = [
    ("A", "◎ 本人公表"),
    ("B", "○ 報道・信頼できる媒体"),
]


def load_racers():
    racers = {}
    if not os.path.exists(RACERS_CSV):
        return racers
    with open(RACERS_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            racers[row["toban"]] = row["name"]
    return racers


def load_candidates():
    if not os.path.exists(CANDIDATES_JSON):
        return []
    with open(CANDIDATES_JSON, encoding="utf-8") as f:
        return json.load(f)


def rel_options_html(selected=""):
    opts = []
    for r in REL_TYPES:
        sel = ' selected' if r == selected else ''
        opts.append(f'<option value="{r}"{sel}>{r}</option>')
    return "\n".join(opts)


def conf_options_html(selected="B"):
    opts = []
    for val, label in CONF_OPTIONS:
        sel = ' selected' if val == selected else ''
        opts.append(f'<option value="{val}"{sel}>{label}</option>')
    return "\n".join(opts)


def generate(candidates, racers):
    today = date.today().strftime("%Y年%-m月%-d日")
    candidates_json = json.dumps(candidates, ensure_ascii=False)

    # 候補カードHTML
    cards = []
    for i, c in enumerate(candidates):
        rel_opts  = rel_options_html(c.get("suggested_rel", ""))
        conf_opts = conf_options_html(c.get("suggested_conf", "B"))
        src_url   = c.get("source_url", "")
        snippet   = c.get("snippet", "").replace("<", "&lt;").replace(">", "&gt;")
        from_toban = c.get("from_toban", "")
        from_name  = c.get("from_name", "")
        to_toban   = c.get("to_toban", "")
        to_name    = c.get("to_name", "")

        cards.append(f'''
    <div class="card" id="card-{i}">
      <label class="card-check">
        <input type="checkbox" class="approve-cb" data-idx="{i}">
        <span class="cb-label">承認</span>
      </label>

      <div class="card-body">
        <div class="snippet">📄 {snippet}</div>
        <div class="src-link">
          <a href="{src_url}" target="_blank" rel="noopener">🔗 出典を確認する（新しいタブ）</a>
        </div>

        <div class="fields">
          <div class="field-group">
            <label>登録番号（from）</label>
            <input class="f-from-toban" type="text" value="{from_toban}" placeholder="例: 4444">
            <label>選手名（from）</label>
            <input class="f-from-name" type="text" value="{from_name}" placeholder="例: 桐生順平">
          </div>

          <div class="field-rel">
            <label>関係タイプ</label>
            <select class="f-rel-type">
              {rel_opts}
            </select>
          </div>

          <div class="field-group">
            <label>登録番号（to）</label>
            <input class="f-to-toban" type="text" value="{to_toban}" placeholder="例: 4422">
            <label>選手名（to）※一般人は空欄でも可</label>
            <input class="f-to-name" type="text" value="{to_name}" placeholder="例: 田口節子">
          </div>

          <div class="field-conf">
            <label>確度</label>
            <select class="f-conf">
              {conf_opts}
            </select>
          </div>

          <div class="field-memo">
            <label>メモ（任意）</label>
            <input class="f-memo" type="text" value="" placeholder="例: 本人インタビューで言及">
          </div>

          <div class="field-date">
            <label>出典日付</label>
            <input class="f-date" type="text" value="{c.get('source_date','')}" placeholder="YYYY-MM-DD">
          </div>
        </div>
      </div>
    </div>''')

    cards_html = "\n".join(cards)
    total = len(candidates)

    html = f'''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>関係候補 承認UI｜舟☆探</title>
<style>
  :root{{
    --navy:#0E2A3C; --red:#E33A2E; --blue:#2E5FE3;
    --yellow:#F2C21F; --green:#2FA65A; --line:#D8D3C8;
    --paper:#F7F5F0; --ink:#1C2530; --muted:#6B7280;
  }}
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{background:var(--paper);color:var(--ink);font-family:'Helvetica Neue',Arial,'Hiragino Kaku Gothic ProN',sans-serif;font-size:14px;line-height:1.6}}

  .lane-strip{{display:flex;height:6px}}
  .lane-strip span{{flex:1}}
  .l1{{background:#fff;border-bottom:1px solid var(--line)}}.l2{{background:#222}}
  .l3{{background:var(--red)}}.l4{{background:var(--blue)}}
  .l5{{background:var(--yellow)}}.l6{{background:var(--green)}}

  header{{background:var(--navy);color:#fff;padding:14px 20px}}
  header h1{{font-size:18px;font-weight:bold}}
  header p{{font-size:12px;opacity:.7;margin-top:4px}}

  .toolbar{{background:#fff;border-bottom:1px solid var(--line);padding:12px 20px;display:flex;gap:10px;align-items:center;flex-wrap:wrap;position:sticky;top:0;z-index:10}}
  .count{{font-size:13px;color:var(--muted);margin-right:auto}}

  button{{font-size:13px;font-weight:bold;padding:9px 20px;border-radius:4px;border:none;cursor:pointer}}
  .btn-all{{background:#EFEBE2;color:var(--ink)}}
  .btn-none{{background:#EFEBE2;color:var(--ink)}}
  .btn-download{{background:var(--navy);color:#fff;font-size:14px;padding:10px 28px}}
  .btn-download:disabled{{opacity:.4;cursor:not-allowed}}

  main{{max-width:860px;margin:24px auto;padding:0 16px 60px}}

  .empty{{text-align:center;padding:60px;color:var(--muted);font-size:16px}}

  .card{{background:#fff;border:1px solid var(--line);border-left:4px solid var(--line);border-radius:6px;margin-bottom:16px;overflow:hidden;transition:border-color .15s}}
  .card.approved{{border-left-color:var(--green);background:#F3FAF5}}
  .card-check{{display:flex;align-items:center;gap:8px;padding:12px 16px;background:#F9F7F3;border-bottom:1px solid var(--line);cursor:pointer}}
  .card-check input[type=checkbox]{{width:18px;height:18px;cursor:pointer}}
  .cb-label{{font-weight:bold;font-size:13px}}

  .card-body{{padding:14px 16px}}
  .snippet{{background:#F0EDE6;border-radius:4px;padding:10px 12px;font-size:12px;color:#374151;margin-bottom:10px;word-break:break-all;line-height:1.7}}
  .src-link{{margin-bottom:14px}}
  .src-link a{{color:var(--blue);font-size:13px;font-weight:bold}}
  .src-link a:hover{{opacity:.8}}

  .fields{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}
  @media(max-width:600px){{.fields{{grid-template-columns:1fr}}}}
  .field-group{{display:flex;flex-direction:column;gap:4px}}
  .field-rel,.field-conf,.field-memo,.field-date{{display:flex;flex-direction:column;gap:4px}}
  .fields label{{font-size:11px;font-weight:bold;color:var(--muted);letter-spacing:.05em}}
  .fields input,.fields select{{padding:7px 10px;border:1px solid var(--line);border-radius:4px;font-size:13px;font-family:inherit;background:#fff}}
  .fields input:focus,.fields select:focus{{outline:2px solid var(--blue);border-color:var(--blue)}}
  .field-memo,.field-date{{grid-column:span 1}}

  .result-msg{{margin-top:16px;padding:12px 16px;background:#E7F3EB;border-radius:6px;font-weight:bold;color:#1E7A41;display:none}}
</style>
</head>
<body>

<div class="lane-strip"><span class="l1"></span><span class="l2"></span><span class="l3"></span><span class="l4"></span><span class="l5"></span><span class="l6"></span></div>
<header>
  <h1>関係候補 承認UI</h1>
  <p>巡回日: {today} ／ 候補: {total} 件 ／ 出典URLを必ず確認してから承認してください</p>
</header>

<div class="toolbar">
  <span class="count" id="countMsg">0 / {total} 件を承認済み</span>
  <button class="btn-all" onclick="selectAll()">すべて選択</button>
  <button class="btn-none" onclick="selectNone()">すべて解除</button>
  <button class="btn-download" id="dlBtn" onclick="download()" disabled>✅ 承認済みをダウンロード</button>
</div>

<main>
{'<p class="empty">候補がありません。巡回後に再度実行してください。</p>' if not candidates else cards_html}
  <div class="result-msg" id="resultMsg"></div>
</main>

<script>
const candidates = {candidates_json};

function updateCount() {{
  const checked = document.querySelectorAll('.approve-cb:checked').length;
  document.getElementById('countMsg').textContent = checked + ' / {total} 件を承認済み';
  document.getElementById('dlBtn').disabled = checked === 0;
}}

function selectAll() {{
  document.querySelectorAll('.approve-cb').forEach(cb => {{
    cb.checked = true;
    cb.closest('.card').classList.add('approved');
  }});
  updateCount();
}}

function selectNone() {{
  document.querySelectorAll('.approve-cb').forEach(cb => {{
    cb.checked = false;
    cb.closest('.card').classList.remove('approved');
  }});
  updateCount();
}}

document.querySelectorAll('.approve-cb').forEach(cb => {{
  cb.addEventListener('change', function() {{
    this.closest('.card').classList.toggle('approved', this.checked);
    updateCount();
  }});
}});

function download() {{
  const approved = [];
  document.querySelectorAll('.approve-cb:checked').forEach(cb => {{
    const idx = parseInt(cb.dataset.idx);
    const card = document.getElementById('card-' + idx);
    approved.push({{
      from_toban:  card.querySelector('.f-from-toban').value.trim(),
      from_name:   card.querySelector('.f-from-name').value.trim(),
      rel_type:    card.querySelector('.f-rel-type').value,
      to_toban:    card.querySelector('.f-to-toban').value.trim(),
      to_name:     card.querySelector('.f-to-name').value.trim(),
      confidence:  card.querySelector('.f-conf').value,
      source_url:  candidates[idx].source_url,
      source_date: card.querySelector('.f-date').value.trim(),
      memo:        card.querySelector('.f-memo').value.trim(),
    }});
  }});

  const blob = new Blob([JSON.stringify(approved, null, 2)], {{type: 'application/json'}});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'approved.json';
  a.click();

  const msg = document.getElementById('resultMsg');
  msg.style.display = 'block';
  msg.textContent = '✅ approved.json をダウンロードしました。ターミナルで python scripts/approve.py ~/Downloads/approved.json を実行してください。';
}}
</script>

</body>
</html>
'''

    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[生成] {OUT_HTML}")
    return OUT_HTML


def main():
    candidates = load_candidates()
    racers = load_racers()

    if not candidates:
        print("[情報] candidates.json が空か存在しません。")
        print("  先に python scripts/patrol.py を実行してください。")

    path = generate(candidates, racers)
    print(f"ブラウザで開いてください: {path}")


if __name__ == "__main__":
    main()
