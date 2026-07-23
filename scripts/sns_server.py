#!/usr/bin/env python3
"""
SNS確認ローカルサーバー
usage: python3 scripts/sns_server.py
→ ブラウザが自動で開きます。確認後「反映する」ボタンを押すと自動更新されます。
"""
import csv
import json
import os
import subprocess
import sys
import threading
import webbrowser
from datetime import date
from http.server import BaseHTTPRequestHandler, HTTPServer

BASE_DIR     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR     = os.path.join(BASE_DIR, "data")
SCRIPTS_DIR  = os.path.join(BASE_DIR, "scripts")
RACERS_CSV   = os.path.join(DATA_DIR, "racers.csv")
PROFILES_CSV = os.path.join(DATA_DIR, "profiles.csv")

PORT = 8765

SNS_FIELDS = [
    ("sns_x",         "X (Twitter)", "https://x.com/{}"),
    ("sns_instagram", "Instagram",   "https://www.instagram.com/{}/"),
    ("sns_youtube",   "YouTube",     "https://www.youtube.com/@{}"),
    ("sns_tiktok",    "TikTok",      "https://www.tiktok.com/@{}"),
]

# ---- データ読み込み ----

def load_racers():
    racers = {}
    with open(RACERS_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            racers[row["toban"]] = row["name"]
    return racers

def load_profiles():
    rows = []
    with open(PROFILES_CSV, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return rows

def build_entries(racers, profiles):
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

# ---- profiles.csv 更新 ----

def apply_results(results, reviewed_at):
    rows = load_profiles()
    fieldnames = list(rows[0].keys()) if rows else []
    changed = []

    for row in rows:
        toban = row["toban"]
        if toban not in results:
            continue
        verdicts = results[toban]
        note = row.get("note", "") or ""
        ng_fields = []

        for field, verdict in verdicts.items():
            if verdict == "ok":
                if "要本人確認" in note:
                    note = note.replace("要本人確認", "確認済み")
                else:
                    # 「macour掲載」→「macour掲載・確認済み」に更新
                    prefix_map = {
                        "sns_x": "X:", "sns_instagram": "Instagram:",
                        "sns_youtube": "YouTube:", "sns_tiktok": "TikTok:",
                    }
                    pre = prefix_map.get(field, "")
                    if pre and pre + "macour掲載" in note and pre + "macour掲載・確認済み" not in note:
                        note = note.replace(pre + "macour掲載", pre + "macour掲載・確認済み", 1)
            elif verdict == "ng":
                if row.get(field, "").strip():
                    ng_fields.append(f"{field}={row[field]}")
                    row[field] = ""

        if ng_fields:
            note += f" NG削除({reviewed_at}):{','.join(ng_fields)}"

        row["note"] = note.strip()
        changed.append(toban)

    with open(PROFILES_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return changed

# ---- ページ再生成・git ----

def run_step(cmd, cwd=BASE_DIR):
    result = subprocess.run(
        cmd, shell=True, cwd=cwd,
        capture_output=True, text=True
    )
    return result.returncode, result.stdout + result.stderr

# ---- HTML生成 ----

def make_page(entries):
    data_json = json.dumps(entries, ensure_ascii=True, indent=2)
    today = str(date.today())
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SNS確認作業｜舟☆探</title>
<style>
  :root{{--ink:#1C2530;--paper:#F7F5F0;--navy:#0E2A3C;
        --green:#1E7A41;--red:#C0392B;--line:#D8D3C8;--muted:#6B7280}}
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{background:var(--paper);color:var(--ink);font-family:'Helvetica Neue',Arial,sans-serif;font-size:15px;line-height:1.6}}
  header{{background:var(--navy);color:#fff;padding:18px 24px}}
  header h1{{font-size:20px;font-weight:700}}
  header p{{font-size:12px;opacity:.7;margin-top:4px}}
  .wrap{{max-width:760px;margin:0 auto;padding:24px 20px 60px}}
  .bar{{background:#fff;border:1px solid var(--line);border-radius:6px;padding:14px 18px;margin-bottom:16px;display:flex;gap:20px;flex-wrap:wrap;align-items:center}}
  .bar b{{font-size:22px}}
  .ok-c{{color:var(--green)}} .ng-c{{color:var(--red)}} .td-c{{color:var(--muted)}}
  .apply-btn{{margin-left:auto;background:var(--green);color:#fff;border:none;padding:11px 28px;border-radius:5px;font-size:14px;font-weight:700;cursor:pointer;letter-spacing:.04em}}
  .apply-btn:hover{{opacity:.85}}
  .apply-btn:disabled{{opacity:.35;cursor:default}}
  .prog{{height:6px;background:var(--line);border-radius:3px;margin-bottom:20px;overflow:hidden}}
  .prog-fill{{height:100%;background:var(--green);border-radius:3px;transition:width .3s}}
  .card{{background:#fff;border:1px solid var(--line);border-radius:6px;margin-bottom:14px;overflow:hidden}}
  .ch{{background:#EFEBE2;padding:10px 16px;display:flex;align-items:center;gap:8px}}
  .ct{{font-family:monospace;font-size:12px;color:var(--muted);font-weight:600}}
  .cn{{font-size:16px;font-weight:700}}
  .cl{{font-size:11px;color:var(--navy);text-decoration:none;margin-left:6px}}
  .cl:hover{{text-decoration:underline}}
  .cnote{{font-size:11px;color:var(--muted);margin-left:auto;max-width:260px;text-align:right}}
  .sr{{display:flex;align-items:center;gap:10px;padding:10px 16px;border-top:1px solid var(--line)}}
  .sp{{font-size:12px;font-weight:700;width:100px;flex-shrink:0;color:var(--muted)}}
  .si{{font-family:monospace;font-size:13px;flex:1}}
  .ob{{font-size:12px;padding:5px 12px;border-radius:14px;border:1px solid var(--line);background:#fff;text-decoration:none;color:var(--navy);font-weight:500;white-space:nowrap}}
  .ob:hover{{border-color:var(--navy)}}
  .jg{{display:flex;gap:6px;flex-shrink:0}}
  .jb{{font-size:13px;font-weight:700;padding:6px 18px;border-radius:14px;border:2px solid var(--line);background:#fff;cursor:pointer;transition:all .15s}}
  .jb.ok{{border-color:var(--green);color:var(--green)}}
  .jb.ok.active{{background:var(--green);color:#fff}}
  .jb.ng{{border-color:var(--red);color:var(--red)}}
  .jb.ng.active{{background:var(--red);color:#fff}}
  .jb:hover:not(.active){{opacity:.7}}
  /* 結果モーダル */
  #overlay{{display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:100;align-items:center;justify-content:center}}
  #overlay.show{{display:flex}}
  #modal{{background:#fff;border-radius:8px;padding:32px 28px;max-width:480px;width:90%;text-align:center}}
  #modal h2{{font-size:20px;margin-bottom:12px}}
  #modal p{{font-size:13px;color:var(--muted);margin-bottom:20px;white-space:pre-wrap;text-align:left}}
  #modal .close-btn{{background:var(--navy);color:#fff;border:none;padding:10px 28px;border-radius:5px;font-size:14px;font-weight:700;cursor:pointer}}
</style>
</head>
<body>
<header>
  <h1>SNS確認作業</h1>
  <p>各リンクを開いて本人か確認し OK / NG を選択 → 「反映する」で自動保存・ページ更新・GitHub反映まで完了します</p>
</header>

<div class="wrap">
  <div class="bar">
    <div class="ok-c">&#10003; OK <b id="cnt-ok">0</b></div>
    <div class="ng-c">&#10007; NG <b id="cnt-ng">0</b></div>
    <div class="td-c">未確認 <b id="cnt-todo">0</b></div>
    <button class="apply-btn" id="apply-btn" disabled>反映する &#9654;</button>
  </div>
  <div class="prog"><div class="prog-fill" id="prog" style="width:0%"></div></div>
  <div id="cards"></div>
</div>

<div id="overlay">
  <div id="modal">
    <h2 id="modal-title"></h2>
    <p id="modal-body"></p>
    <button class="close-btn" onclick="document.getElementById('overlay').classList.remove('show')">閉じる</button>
  </div>
</div>

<script>
const DATA = {data_json};
const SK = 'sns_review_state_{today}';
let state = {{}};

function key(toban, field) {{ return toban + ':' + field; }}

function loadState() {{
  try {{ const s = localStorage.getItem(SK); if(s) state = JSON.parse(s); }} catch(e){{}}
}}
function saveState() {{ localStorage.setItem(SK, JSON.stringify(state)); }}

function setJudge(toban, field, verdict) {{
  const k = key(toban, field);
  state[k] = (state[k] === verdict) ? null : verdict;
  saveState();
  renderBtns(toban, field);
  updateBar();
}}

function renderBtns(toban, field) {{
  const k = key(toban, field);
  const v = state[k];
  const ok = document.getElementById('ok-' + k);
  const ng = document.getElementById('ng-' + k);
  if(ok) ok.classList.toggle('active', v === 'ok');
  if(ng) ng.classList.toggle('active', v === 'ng');
}}

function updateBar() {{
  let ok=0, ng=0, total=0;
  DATA.forEach(function(r) {{
    r.sns.forEach(function(s) {{
      total++;
      const v = state[key(r.toban, s.field)];
      if(v==='ok') ok++; else if(v==='ng') ng++;
    }});
  }});
  document.getElementById('cnt-ok').textContent = ok;
  document.getElementById('cnt-ng').textContent = ng;
  document.getElementById('cnt-todo').textContent = total - ok - ng;
  document.getElementById('prog').style.width = (total>0 ? Math.round((ok+ng)/total*100) : 0) + '%';
  document.getElementById('apply-btn').disabled = (ok+ng === 0);
}}

function renderCards() {{
  const cont = document.getElementById('cards');
  DATA.forEach(function(r) {{
    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML =
      '<div class="ch">' +
        '<span class="ct">' + r.toban + '</span>' +
        '<span class="cn">' + esc(r.name) + '</span>' +
        '<a class="cl" href="http://localhost:{PORT}/racer/' + r.toban + '.html" target="_blank">選手ページ</a>' +
        (r.note ? '<span class="cnote">' + esc(r.note) + '</span>' : '') +
      '</div>';
    r.sns.forEach(function(s) {{
      const k = key(r.toban, s.field);
      const row = document.createElement('div');
      row.className = 'sr';
      row.innerHTML =
        '<span class="sp">' + s.label + '</span>' +
        '<span class="si">@' + esc(s.id) + '</span>' +
        '<a class="ob" href="' + s.url + '" target="_blank" rel="noopener">開く &#8599;</a>' +
        '<div class="jg">' +
          '<button class="jb ok" id="ok-' + k + '" data-t="' + r.toban + '" data-f="' + s.field + '" data-v="ok">&#10003; OK</button>' +
          '<button class="jb ng" id="ng-' + k + '" data-t="' + r.toban + '" data-f="' + s.field + '" data-v="ng">&#10007; NG</button>' +
        '</div>';
      card.appendChild(row);
    }});
    cont.appendChild(card);
  }});
}}

function esc(s) {{
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}}

// イベント委譲
document.addEventListener('click', function(e) {{
  const b = e.target.closest('.jb');
  if(b) setJudge(b.dataset.t, b.dataset.f, b.dataset.v);
}});

// 反映ボタン
document.getElementById('apply-btn').addEventListener('click', function() {{
  const results = {{}};
  DATA.forEach(function(r) {{
    const v = {{}};
    r.sns.forEach(function(s) {{ const val = state[key(r.toban, s.field)]; if(val) v[s.field]=val; }});
    if(Object.keys(v).length) results[r.toban] = v;
  }});

  const btn = document.getElementById('apply-btn');
  btn.textContent = '処理中...';
  btn.disabled = true;

  fetch('/apply', {{
    method: 'POST',
    headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify({{reviewed_at: '{today}', results: results}})
  }})
  .then(function(res) {{ return res.json(); }})
  .then(function(data) {{
    const overlay = document.getElementById('overlay');
    const title   = document.getElementById('modal-title');
    const body    = document.getElementById('modal-body');
    if(data.ok) {{
      title.textContent = '&#10003; 反映完了！';
      body.textContent  = data.message;
      localStorage.removeItem(SK);
    }} else {{
      title.textContent = '&#9888; エラー';
      body.textContent  = data.message;
    }}
    overlay.classList.add('show');
    btn.textContent = '反映する &#9654;';
    btn.disabled = false;
  }})
  .catch(function(e) {{
    alert('通信エラー: ' + e.message);
    btn.textContent = '反映する &#9654;';
    btn.disabled = false;
  }});
}});

// 選手ページをサーバー経由で提供
loadState();
renderCards();
DATA.forEach(function(r) {{ r.sns.forEach(function(s) {{ renderBtns(r.toban, s.field); }}); }});
updateBar();
</script>
</body>
</html>"""

# ---- HTTP サーバー ----

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # アクセスログを抑制

    def do_GET(self):
        path = self.path.split("?")[0]

        # 確認ページ
        if path in ("/", "/index.html"):
            racers  = load_racers()
            profiles = load_profiles()
            entries = build_entries(racers, profiles)
            body = make_page(entries).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)

        # 選手ページ（racer/*.html）
        elif path.startswith("/racer/"):
            fpath = os.path.join(BASE_DIR, "docs", path.lstrip("/"))
            if os.path.exists(fpath):
                with open(fpath, "rb") as f:
                    body = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(body)
            else:
                self._404()
        else:
            self._404()

    def do_POST(self):
        if self.path != "/apply":
            self._404()
            return

        length = int(self.headers.get("Content-Length", 0))
        body   = json.loads(self.rfile.read(length))
        results     = body.get("results", {})
        reviewed_at = body.get("reviewed_at", str(date.today()))

        log = []

        try:
            # 1. profiles.csv 更新
            changed = apply_results(results, reviewed_at)
            ok_cnt = sum(1 for v in results.values() for vv in v.values() if vv == "ok")
            ng_cnt = sum(1 for v in results.values() for vv in v.values() if vv == "ng")
            log.append(f"✓ profiles.csv 更新（OK:{ok_cnt}件 NG:{ng_cnt}件）")

            # 2. ページ再生成
            rc, out = run_step(f"python3 scripts/generate_racer_page.py")
            if rc != 0:
                raise RuntimeError("ページ再生成失敗:\n" + out)
            log.append("✓ 選手ページ再生成完了")

            # 3. SNS確認ページも更新
            run_step("python3 scripts/generate_sns_review.py")

            # 4. git commit + push
            rc, out = run_step(
                'git add data/profiles.csv docs/racer/ docs/sns_review/ && '
                f'git commit -m "SNS確認結果反映 {reviewed_at}（OK:{ok_cnt} NG:{ng_cnt}）" && '
                'git push origin main'
            )
            if rc != 0:
                raise RuntimeError("git push 失敗:\n" + out)
            log.append("✓ GitHub Pages に反映完了")

            msg = "\n".join(log) + "\n\nページをリロードすると最新の状態になります。"
            self._json({"ok": True, "message": msg})
            print("[完了]", ", ".join(log))

        except Exception as e:
            msg = str(e)
            self._json({"ok": False, "message": msg})
            print("[エラー]", msg)

    def _json(self, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _404(self):
        self.send_response(404)
        self.end_headers()


def main():
    server = HTTPServer(("localhost", PORT), Handler)
    url = f"http://localhost:{PORT}"
    print(f"サーバー起動: {url}")
    print("ブラウザで確認作業をしてください。終了は Ctrl+C です。")
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n終了しました。")


if __name__ == "__main__":
    main()
