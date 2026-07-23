#!/usr/bin/env python3
"""
SNS確認レビューページ生成スクリプト
usage: python scripts/generate_sns_review.py
→ docs/sns_review/index.html を生成
"""
import csv
import json
import os
from datetime import date

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR  = os.path.join(BASE_DIR, "data")
DOCS_DIR  = os.path.join(BASE_DIR, "docs", "sns_review")

RACERS_CSV   = os.path.join(DATA_DIR, "racers.csv")
PROFILES_CSV = os.path.join(DATA_DIR, "profiles.csv")

os.makedirs(DOCS_DIR, exist_ok=True)

SNS_FIELDS = [
    ("sns_x",        "𝕏 X",        "https://x.com/{}"),
    ("sns_instagram","Instagram",   "https://www.instagram.com/{}/"),
    ("sns_youtube",  "YouTube",     "https://www.youtube.com/@{}"),
    ("sns_tiktok",   "TikTok",      "https://www.tiktok.com/@{}"),
]

def load_racers():
    racers = {}
    with open(RACERS_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            racers[row["toban"]] = row["name"]
    return racers

def load_profiles():
    profiles = []
    with open(PROFILES_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            profiles.append(row)
    return profiles

def build_entries(racers, profiles):
    """SNS IDが1つ以上登録されている行のみ抽出"""
    entries = []
    for p in profiles:
        toban = p["toban"]
        name  = racers.get(toban, f"登録番号{toban}")
        snss  = []
        for field, label, url_tmpl in SNS_FIELDS:
            uid = p.get(field, "").strip()
            if uid:
                snss.append({
                    "field": field,
                    "label": label,
                    "id":    uid,
                    "url":   url_tmpl.format(uid),
                })
        if snss:
            entries.append({
                "toban": toban,
                "name":  name,
                "note":  p.get("note", ""),
                "sns":   snss,
            })
    return entries

def generate(entries):
    data_json = json.dumps(entries, ensure_ascii=False, indent=2)
    today = str(date.today())

    html = f'''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SNS確認作業｜舟☆探 管理</title>
<style>
  :root{{
    --ink:#1C2530; --paper:#F7F5F0; --navy:#0E2A3C;
    --green:#1E7A41; --red:#C0392B; --yellow:#F2C21F;
    --line:#D8D3C8; --muted:#6B7280;
    --sans:'Helvetica Neue',Arial,sans-serif;
  }}
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{background:var(--paper);color:var(--ink);font-family:var(--sans);font-size:15px;line-height:1.6}}
  header{{background:var(--navy);color:#fff;padding:18px 24px}}
  header h1{{font-size:20px;font-weight:700;letter-spacing:.04em}}
  header p{{font-size:12px;opacity:.7;margin-top:4px}}
  .wrap{{max-width:760px;margin:0 auto;padding:24px 20px 60px}}
  .summary{{background:#fff;border:1px solid var(--line);border-radius:6px;padding:14px 18px;margin-bottom:24px;font-size:13px;display:flex;gap:20px;flex-wrap:wrap;align-items:center}}
  .summary b{{font-size:20px}}
  .summary .ok-count{{color:var(--green)}}
  .summary .ng-count{{color:var(--red)}}
  .summary .todo-count{{color:var(--muted)}}
  .save-btn{{margin-left:auto;background:var(--navy);color:#fff;border:none;padding:10px 22px;border-radius:5px;font-size:13px;font-weight:700;cursor:pointer;letter-spacing:.04em}}
  .save-btn:hover{{opacity:.85}}
  .save-btn:disabled{{opacity:.4;cursor:default}}

  .racer-card{{background:#fff;border:1px solid var(--line);border-radius:6px;margin-bottom:16px;overflow:hidden}}
  .racer-header{{background:#EFEBE2;padding:10px 16px;display:flex;align-items:center;gap:10px}}
  .racer-toban{{font-family:monospace;font-size:12px;color:var(--muted);font-weight:600}}
  .racer-name{{font-size:16px;font-weight:700}}
  .racer-note{{font-size:11px;color:var(--muted);margin-left:auto;max-width:260px;text-align:right}}
  .racer-link{{font-size:11px;color:var(--navy);text-decoration:none;margin-left:6px}}
  .racer-link:hover{{text-decoration:underline}}

  .sns-row{{display:flex;align-items:center;gap:10px;padding:10px 16px;border-top:1px solid var(--line)}}
  .sns-row:first-child{{border-top:none}}
  .platform{{font-size:12px;font-weight:700;width:90px;flex-shrink:0;color:var(--muted)}}
  .sns-id{{font-family:monospace;font-size:13px;flex:1}}
  .open-btn{{font-size:12px;padding:5px 12px;border-radius:14px;border:1px solid var(--line);background:#fff;text-decoration:none;color:var(--navy);font-weight:500;white-space:nowrap}}
  .open-btn:hover{{border-color:var(--navy)}}

  .judge-group{{display:flex;gap:6px;flex-shrink:0}}
  .judge-btn{{font-size:12px;font-weight:700;padding:5px 16px;border-radius:14px;border:2px solid var(--line);background:#fff;cursor:pointer;transition:all .15s}}
  .judge-btn.ok{{border-color:var(--green);color:var(--green)}}
  .judge-btn.ok.active{{background:var(--green);color:#fff}}
  .judge-btn.ng{{border-color:var(--red);color:var(--red)}}
  .judge-btn.ng.active{{background:var(--red);color:#fff}}
  .judge-btn:hover:not(.active){{opacity:.7}}

  .progress-bar{{height:6px;background:var(--line);border-radius:3px;margin-bottom:20px;overflow:hidden}}
  .progress-fill{{height:100%;background:var(--green);border-radius:3px;transition:width .3s}}

  footer{{text-align:center;font-size:11px;color:var(--muted);padding:20px;border-top:1px solid var(--line);margin-top:40px}}
</style>
</head>
<body>

<header>
  <h1>SNS確認作業</h1>
  <p>各SNSリンクを開いて本人アカウントか確認し、OK / NG を押してください。最後に「結果を保存」してください。</p>
</header>

<div class="wrap">
  <div class="summary">
    <div class="ok-count">✓ OK <b id="cnt-ok">0</b></div>
    <div class="ng-count">✗ NG <b id="cnt-ng">0</b></div>
    <div class="todo-count">未確認 <b id="cnt-todo">0</b></div>
    <button class="save-btn" id="save-btn" onclick="saveJSON()">結果を保存（JSONダウンロード）</button>
  </div>

  <div class="progress-bar"><div class="progress-fill" id="progress" style="width:0%"></div></div>

  <div id="cards"></div>
</div>

<footer>舟☆探 管理ページ ｜ このページはローカル専用です。インターネットには公開しないでください。</footer>

<script>
const DATA = {data_json};
const STORAGE_KEY = 'sns_review_state';

// ---- 状態管理 ----
let state = {{}};  // key: "toban:field" → "ok" | "ng" | null

function stateKey(toban, field) {{ return toban + ':' + field; }}

function loadState() {{
  try {{
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) state = JSON.parse(saved);
  }} catch(e) {{}}
}}

function saveState() {{
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}}

function setJudge(toban, field, verdict, btn) {{
  const key = stateKey(toban, field);
  // 同じボタンをもう一度押したらクリア
  if (state[key] === verdict) {{
    state[key] = null;
  }} else {{
    state[key] = verdict;
  }}
  saveState();
  renderButtons(toban, field);
  updateSummary();
}}

function renderButtons(toban, field) {{
  const key = stateKey(toban, field);
  const current = state[key];
  const okBtn = document.getElementById('ok-' + key);
  const ngBtn = document.getElementById('ng-' + key);
  if (!okBtn || !ngBtn) return;
  okBtn.classList.toggle('active', current === 'ok');
  ngBtn.classList.toggle('active', current === 'ng');
}}

function updateSummary() {{
  let ok = 0, ng = 0, total = 0;
  DATA.forEach(function(racer) {{
    racer.sns.forEach(function(sns) {{
      total++;
      const v = state[stateKey(racer.toban, sns.field)];
      if (v === 'ok') ok++;
      else if (v === 'ng') ng++;
    }});
  }});
  document.getElementById('cnt-ok').textContent   = ok;
  document.getElementById('cnt-ng').textContent   = ng;
  document.getElementById('cnt-todo').textContent = total - ok - ng;
  const pct = total > 0 ? Math.round((ok + ng) / total * 100) : 0;
  document.getElementById('progress').style.width = pct + '%';
}}

// ---- カード描画 ----
function renderCards() {{
  const container = document.getElementById('cards');
  DATA.forEach(function(racer) {{
    const card = document.createElement('div');
    card.className = 'racer-card';

    const noteHtml = racer.note
      ? '<span class="racer-note">' + escHtml(racer.note) + '</span>'
      : '';

    card.innerHTML =
      '<div class="racer-header">' +
        '<span class="racer-toban">' + racer.toban + '</span>' +
        '<span class="racer-name">' + escHtml(racer.name) + '</span>' +
        '<a class="racer-link" href="../racer/' + racer.toban + '.html" target="_blank">選手ページ</a>' +
        noteHtml +
      '</div>';

    racer.sns.forEach(function(sns) {{
      const key = stateKey(racer.toban, sns.field);
      const row = document.createElement('div');
      row.className = 'sns-row';
      row.innerHTML =
        '<span class="platform">' + sns.label + '</span>' +
        '<span class="sns-id">@' + escHtml(sns.id) + '</span>' +
        '<a class="open-btn" href="' + sns.url + '" target="_blank" rel="noopener">開く ↗</a>' +
        '<div class="judge-group">' +
          '<button class="judge-btn ok" id="ok-' + key + '"' +
            ' onclick="setJudge(\'' + racer.toban + '\',\'' + sns.field + '\',\'ok\',this)">✓ OK</button>' +
          '<button class="judge-btn ng" id="ng-' + key + '"' +
            ' onclick="setJudge(\'' + racer.toban + '\',\'' + sns.field + '\',\'ng\',this)">✗ NG</button>' +
        '</div>';
      card.appendChild(row);
    }});

    container.appendChild(card);
  }});
}}

function escHtml(str) {{
  return String(str)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}}

// ---- 保存 ----
function saveJSON() {{
  const results = {{}};
  DATA.forEach(function(racer) {{
    const verdicts = {{}};
    racer.sns.forEach(function(sns) {{
      const v = state[stateKey(racer.toban, sns.field)];
      if (v) verdicts[sns.field] = v;
    }});
    if (Object.keys(verdicts).length > 0) {{
      results[racer.toban] = verdicts;
    }}
  }});

  const output = {{
    reviewed_at: '{today}',
    results: results
  }};

  const blob = new Blob([JSON.stringify(output, null, 2)], {{type:'application/json'}});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'sns_review_{today}.json';
  a.click();
}}

// ---- 初期化 ----
loadState();
renderCards();
// 保存済みの状態を反映
DATA.forEach(function(racer) {{
  racer.sns.forEach(function(sns) {{
    renderButtons(racer.toban, sns.field);
  }});
}});
updateSummary();
</script>
</body>
</html>
'''

    out_path = os.path.join(DOCS_DIR, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[生成] {out_path}")
    print(f"  対象選手: {len(entries)} 名 / SNSエントリ: {sum(len(e['sns']) for e in entries)} 件")


if __name__ == "__main__":
    racers   = load_racers()
    profiles = load_profiles()
    entries  = build_entries(racers, profiles)
    generate(entries)
    print("完了")
