#!/usr/bin/env python3
"""
選手個別ページ生成スクリプト
usage: python scripts/generate_racer_page.py [toban]
  toban を省略すると全選手分を生成
"""

import csv
import os
import sys
from collections import defaultdict
from datetime import date

# パス設定
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DOCS_DIR = os.path.join(BASE_DIR, "docs", "racer")

RACERS_CSV = os.path.join(DATA_DIR, "racers.csv")
RELATIONS_CSV = os.path.join(DATA_DIR, "relations.csv")
PROFILES_CSV = os.path.join(DATA_DIR, "profiles.csv")

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

def load_profiles():
    """profiles.csv を読み込む。ファイルがなければ空 dict を返す。"""
    if not os.path.exists(PROFILES_CSV):
        return {}
    profiles = {}
    with open(PROFILES_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            profiles[row["toban"]] = row
    return profiles

# --------- インデックス構築 ---------

def build_ki_map(racers):
    """ki → [(toban, name, branch), ...] 登録番号順"""
    result = defaultdict(list)
    for toban, r in racers.items():
        ki = r.get("ki", "").strip()
        if ki:
            result[ki].append((toban, r["name"], r.get("branch", "")))
    for ki in result:
        result[ki].sort(key=lambda x: x[0])
    return result


def build_branch_map(racers):
    """branch → [(toban, name, ki), ...] 登録番号順"""
    result = defaultdict(list)
    for toban, r in racers.items():
        branch = r.get("branch", "").strip()
        if branch:
            result[branch].append((toban, r["name"], r.get("ki", "")))
    for branch in result:
        result[branch].sort(key=lambda x: x[0])
    return result


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

def get_episodes_for(toban, relations):
    """
    toban の選手に関係する全レコードからmemo（エピソード）を収集する。
    - confidence=C は除外
    - source_url なしは除外
    - memo が空のものは除外
    - 同一memoは1件のみ（重複排除）
    Returns: list of (rel_display, memo, confidence)
    """
    REVERSE = {
        "父": "子", "母": "子", "子": "父/母",
        "兄": "弟/妹", "姉": "弟/妹", "弟": "兄/姉", "妹": "兄/姉",
        "師匠": "弟子", "弟子": "師匠",
        "配偶者": "配偶者", "元配偶者": "元配偶者",
        "親族": "親族", "友人": "友人", "同期": "同期", "仲良し": "仲良し",
    }
    seen = set()
    result = []
    for r in relations:
        if r["confidence"] == "C":
            continue
        if not r["source_url"].strip():
            continue
        memo = r.get("memo", "").strip()
        if not memo:
            continue
        if r["from_toban"] == toban:
            rel_display = r["rel_type"]
        elif r["to_toban"] == toban:
            rel_display = REVERSE.get(r["rel_type"], r["rel_type"])
        else:
            continue
        if memo in seen:
            continue
        seen.add(memo)
        result.append((rel_display, memo, r["confidence"]))
    return result


def episode_section_html(episodes):
    """エピソードセクションHTML。エピソードがなければ空文字を返す。"""
    if not episodes:
        return ""
    EP_CLASS = {
        "配偶者": "spouse", "元配偶者": "spouse",
        "父": "family", "母": "family", "子": "family",
        "父/母": "family", "兄/姉": "family", "弟/妹": "family",
        "兄": "family", "姉": "family", "弟": "family", "妹": "family", "親族": "family",
        "師匠": "mentor", "弟子": "mentor",
        "友人": "friend", "同期": "friend", "仲良し": "friend",
    }
    cards = []
    for rel, memo, conf in episodes:
        cls = EP_CLASS.get(rel, "")
        unconfirmed = ' <span class="ep-unconfirmed">※情報確認中</span>' if conf == "B" else ""
        cards.append(
            f'    <div class="ep-card {cls}">'
            f'<span class="ep-badge">{rel}</span>'
            f'<span class="ep-text">{memo}{unconfirmed}</span>'
            f'</div>'
        )
    inner = "\n".join(cards)
    return f'''  <section>
    <h2>エピソード <span class="en">EPISODES</span></h2>
    <div class="ep-list">
{inner}
    </div>
  </section>'''


def get_relations_for(toban, relations, racers, retired_names=None):
    """
    toban の選手に関係する行を取得。
    - confidence=C は除外
    - source_url なしは除外
    - 片方向記録なので逆方向も補完する
    - retired_names: racers.csv未登録の引退選手名キャッシュ
    """
    REVERSE = {
        "父": "子", "母": "子", "子": "父/母",
        "兄": "弟/妹", "姉": "弟/妹", "弟": "兄/姉", "妹": "兄/姉",
        "師匠": "弟子", "弟子": "師匠",
        "配偶者": "配偶者", "元配偶者": "元配偶者",
        "親族": "親族", "友人": "友人", "同期": "同期", "仲良し": "仲良し",
    }
    if retired_names is None:
        retired_names = {}

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
            # racers.csvに存在しない引退選手はretired_namesから名前を補完
            other_name = racers.get(other_toban, {}).get("name", "") or retired_names.get(other_toban, "")
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

    in_db = (other_toban and other_toban != "0" and other_toban in racers)
    if in_db:
        href = f"{other_toban}.html"
        name_html = f'{other_name} <span style="font-family:var(--mono);font-size:12px;color:var(--muted)">{other_toban}</span>'
    else:
        href = source_url
        name_html = f'{other_name} <span style="font-family:var(--mono);font-size:12px;color:var(--muted)">引退</span>'

    return f'''      <a class="rel-card {card_class}" href="{href}">
        <div class="rel-type">{rel}</div>
        <div class="rel-name">{name_html}</div>
        <div class="rel-meta"><span>{meta_str}</span><span class="conf {conf_cls}">{conf_label}</span></div>
      </a>'''


def mini_graph_section_html(center_toban, center_name, rel_rows, racers):
    """人間関係ミニグラフ（vis-network）。関係がなければ空文字を返す。"""
    import json

    if not rel_rows:
        return ""

    EDGE_LABEL = {
        "師匠": "師弟", "弟子": "師弟",
        "配偶者": "夫婦", "元配偶者": "夫婦",
        "父": "親子", "母": "親子", "子": "親子",
        "兄": "兄弟", "姉": "兄弟", "弟": "兄弟", "妹": "兄弟",
        "親族": "親族",
        "仲良し": "仲間", "友人": "仲間", "同期": "仲間",
    }

    nodes = [{"id": center_toban, "label": center_name, "group": "center"}]
    seen  = {center_toban}
    edges = []

    for i, (rel, other_toban, other_name, conf, src) in enumerate(rel_rows):
        if not other_name:
            continue
        node_id   = other_toban if (other_toban and other_toban != "0") else f"_r{i}"
        navigable = bool(other_toban and other_toban != "0" and other_toban in racers)

        if node_id not in seen:
            nd = {"id": node_id, "label": other_name,
                  "group": "active" if navigable else "retired"}
            if navigable:
                nd["toban"] = other_toban
            nodes.append(nd)
            seen.add(node_id)

        has_arrow = rel in ("師匠", "弟子")
        ef = node_id        if rel == "師匠" else center_toban
        et = center_toban   if rel == "師匠" else node_id

        edges.append({
            "id": i, "from": ef, "to": et,
            "label": EDGE_LABEL.get(rel, rel),
            "arrows": {"to": {"enabled": has_arrow, "scaleFactor": 0.7}}
        })

    nodes_json = json.dumps(nodes, ensure_ascii=False)
    edges_json = json.dumps(edges, ensure_ascii=False)

    return f'''  <section>
    <h2>関係グラフ <span class="en">NETWORK</span></h2>
    <div id="mini-graph" style="height:260px;border:1px solid var(--line);border-radius:6px;overflow:hidden;background:#fff"></div>
    <p style="font-size:11px;color:var(--muted);margin-top:6px">ノードをクリックすると選手ページへ移動できます（矢印は師匠 → 弟子の方向）</p>
    <script>
    (function(){{
      var N={nodes_json};
      var E={edges_json};
      var el=document.getElementById('mini-graph');
      var net=new vis.Network(el,
        {{nodes:new vis.DataSet(N),edges:new vis.DataSet(E)}},
        {{
          physics:{{stabilization:{{iterations:80}},barnesHut:{{gravitationalConstant:-3000}}}},
          interaction:{{hover:true,tooltipDelay:100}},
          nodes:{{shape:'box',font:{{size:13,face:'sans-serif'}},borderWidth:1.5,margin:8,
                 shadow:{{enabled:true,size:4,x:2,y:2}}}},
          edges:{{font:{{size:10,align:'middle',vadjust:-3}},
                 smooth:{{type:'curvedCW',roundness:0.1}},
                 color:{{color:'#9CA3AF',highlight:'#4B5563',hover:'#4B5563'}}}},
          groups:{{
            center:{{color:{{background:'#0E2A3C',border:'#0E2A3C',
                           highlight:{{background:'#173B52',border:'#173B52'}}}},
                   font:{{color:'#fff',bold:true}}}},
            active:{{color:{{background:'#E7F3EB',border:'#1E7A41',
                           highlight:{{background:'#D1FAE5',border:'#065F46'}}}},
                   font:{{color:'#0E2A3C'}}}},
            retired:{{color:{{background:'#F3F4F6',border:'#9CA3AF',
                            highlight:{{background:'#E5E7EB',border:'#6B7280'}}}},
                    font:{{color:'#6B7280'}}}}
          }}
        }});
      net.on('click',function(p){{
        if(!p.nodes.length)return;
        var nd=N.find(function(n){{return n.id===p.nodes[0];}});
        if(nd&&nd.toban)window.location.href=nd.toban+'.html';
      }});
      net.on('hoverNode',function(p){{
        var nd=N.find(function(n){{return n.id===p.node;}});
        el.style.cursor=(nd&&nd.toban)?'pointer':'default';
      }});
      net.on('blurNode',function(){{el.style.cursor='default';}});
    }})();
    </script>
  </section>'''


def _peer_chip(toban, name, extra_class=""):
    return (f'<a class="peer-chip {extra_class}" href="{toban}.html">'
            f'{name} <span class="peer-toban">{toban}</span></a>')


def douki_section_html(toban, r, ki_map):
    """同期の仲間セクション HTML（ki が空なら空文字を返す）"""
    ki = r.get("ki", "").strip()
    if not ki:
        return ""
    all_peers = [(t, n, b) for t, n, b in ki_map.get(ki, []) if t != toban]
    if not all_peers:
        return ""

    my_branch = r.get("branch", "")
    same_branch = [(t, n) for t, n, b in all_peers if b == my_branch]
    others      = [(t, n) for t, n, b in all_peers if b != my_branch]
    total = len(all_peers)

    parts = []

    if same_branch:
        chips = "".join(_peer_chip(t, n, "same-branch") for t, n in same_branch)
        parts.append(
            f'<div class="peer-group-label">同支部（{my_branch}）</div>'
            f'<div class="peer-chips">{chips}</div>'
        )

    SHOW_N = 8
    shown  = others[:SHOW_N]
    hidden = others[SHOW_N:]

    if shown:
        label = '<div class="peer-group-label" style="margin-top:10px">他支部の同期</div>' if same_branch else ""
        chips_shown = "".join(_peer_chip(t, n) for t, n in shown)
        parts.append(f'{label}<div class="peer-chips">{chips_shown}</div>')

    if hidden:
        chips_hidden = "".join(_peer_chip(t, n) for t, n in hidden)
        parts.append(
            f'<div class="peer-chips peer-hidden" id="douki-hidden">{chips_hidden}</div>'
            f'<button class="peer-more-btn" onclick="showPeers(\'douki-hidden\',this)">'
            f'他の同期を見る（あと{len(hidden)}人）</button>'
        )

    inner = "\n".join(parts)
    return f'''  <section>
    <h2>{ki}期 同期の仲間 <span class="en">CLASSMATES</span><span class="peer-count">全{total}人</span></h2>
    <div class="peer-wrap">{inner}</div>
  </section>'''


def branch_section_html(toban, r, branch_map):
    """同支部の選手セクション HTML"""
    branch = r.get("branch", "").strip()
    if not branch:
        return ""
    all_peers = [(t, n, k) for t, n, k in branch_map.get(branch, []) if t != toban]
    if not all_peers:
        return ""

    total  = len(all_peers)
    SHOW_N = 12
    shown  = all_peers[:SHOW_N]
    hidden = all_peers[SHOW_N:]

    chips_shown  = "".join(_peer_chip(t, n) for t, n, k in shown)
    hidden_block = ""
    if hidden:
        chips_hidden = "".join(_peer_chip(t, n) for t, n, k in hidden)
        hidden_block = (
            f'<div class="peer-chips peer-hidden" id="branch-hidden">{chips_hidden}</div>'
            f'<button class="peer-more-btn" onclick="showPeers(\'branch-hidden\',this)">'
            f'もっと見る（あと{len(hidden)}人）</button>'
        )

    return f'''  <section>
    <h2>{branch}支部の選手 <span class="en">BRANCH MATES</span><span class="peer-count">全{total}人</span></h2>
    <div class="peer-wrap">
      <div class="peer-chips" id="branch-shown">{chips_shown}</div>
      {hidden_block}
    </div>
  </section>'''


def generate_page(toban, racers, relations, ki_map, branch_map, retired_names=None, profiles=None):
    r = racers.get(toban)
    if not r:
        print(f"[エラー] 登録番号 {toban} が racers.csv に見つかりません")
        return

    rel_rows = get_relations_for(toban, relations, racers, retired_names)
    mini_graph = mini_graph_section_html(toban, r["name"], rel_rows, racers)
    vis_tag = ('<script src="https://unpkg.com/vis-network@9.1.9/dist/vis-network.min.js">'
               '</script>') if mini_graph else ''

    # エピソードセクション
    episodes = get_episodes_for(toban, relations)
    episode_section = episode_section_html(episodes)

    # 同期・同支部セクション
    douki_section  = douki_section_html(toban, r, ki_map)
    branch_section = branch_section_html(toban, r, branch_map)

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

    # profiles.csv データ取得
    prof = (profiles or {}).get(toban, {})

    # 基本情報テーブル
    birth_str = fmt_birth(r["birth"]) if r["birth"] else "—"
    status_str = STATUS_LABEL.get(r["status"], r["status"])
    # 趣味: profiles.csv優先、なければracers.csvのhobby
    hobby_str = prof.get("hobby", "").strip() or r.get("hobby", "").strip() or ""
    food_str  = prof.get("food", "").strip()
    note_str = r["note"] if r["note"] else ""
    nickname_str = r.get("nickname", "") or ""

    profile_rows = f"""      <tr><th>生年月日</th><td>{birth_str}</td></tr>
      <tr><th>出身地</th><td>{r['hometown'] or '—'}</td></tr>
      <tr><th>支部</th><td>{r['branch'] or '—'}支部</td></tr>
      <tr><th>期別</th><td>{r['ki'] or '—'}期</td></tr>
      <tr><th>級別</th><td>{r['grade'] or '—'}</td></tr>
      <tr><th>現況</th><td>{status_str}</td></tr>"""
    if hobby_str:
        profile_rows += f"\n      <tr><th>趣味</th><td>{hobby_str}</td></tr>"
    if food_str:
        profile_rows += f"\n      <tr><th>好きな食べ物</th><td>{food_str}</td></tr>"
    if nickname_str:
        profile_rows += f"\n      <tr><th>異名</th><td>「{nickname_str}」</td></tr>"
    if note_str:
        profile_rows += f"\n      <tr><th>備考</th><td>{note_str}</td></tr>"

    # 外部リンク（公式・艇国DB）
    links_html = f'      <a class="chip" href="https://boatrace.jp/owpc/pc/data/racersearch/profile?toban={toban}" target="_blank" rel="noopener">BOAT RACE公式プロフィール</a>\n'
    links_html += f'      <a class="chip" href="https://boatrace-db.net/racer/index2/regno/{toban}" target="_blank" rel="noopener">艇国データバンク（成績）</a>\n'
    if r.get("x_url"):
        links_html += f'      <a class="chip" href="{r["x_url"]}" target="_blank" rel="noopener">X（Twitter）</a>\n'
    if r.get("insta_url"):
        links_html += f'      <a class="chip" href="{r["insta_url"]}" target="_blank" rel="noopener">Instagram</a>\n'
    if r.get("youtube_url"):
        links_html += f'      <a class="chip" href="{r["youtube_url"]}" target="_blank" rel="noopener">YouTube</a>\n'

    # SNSボタン（profiles.csvのID登録がある場合のみ表示）
    sns_btns = []
    if prof.get("sns_x", "").strip():
        uid = prof["sns_x"].strip()
        sns_btns.append(f'      <a class="sns-btn sns-x" href="https://x.com/{uid}" target="_blank" rel="noopener">𝕏&nbsp;X</a>')
    if prof.get("sns_instagram", "").strip():
        uid = prof["sns_instagram"].strip()
        sns_btns.append(f'      <a class="sns-btn sns-ig" href="https://www.instagram.com/{uid}/" target="_blank" rel="noopener">&#9711;&nbsp;Instagram</a>')
    if prof.get("sns_youtube", "").strip():
        uid = prof["sns_youtube"].strip()
        sns_btns.append(f'      <a class="sns-btn sns-yt" href="https://www.youtube.com/@{uid}" target="_blank" rel="noopener">&#9654;&nbsp;YouTube</a>')
    if prof.get("sns_tiktok", "").strip():
        uid = prof["sns_tiktok"].strip()
        sns_btns.append(f'      <a class="sns-btn sns-tt" href="https://www.tiktok.com/@{uid}" target="_blank" rel="noopener">&#9836;&nbsp;TikTok</a>')
    sns_html = ""
    if sns_btns:
        inner_btns = "\n".join(sns_btns)
        sns_html = f'    <div class="sns-row">\n{inner_btns}\n    </div>'

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
{vis_tag}
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
  .nickname{{font-size:13px;letter-spacing:.05em;color:rgba(255,255,255,.80);margin-top:5px;font-style:italic}}
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
  /* 同期・同支部チップ */
  .peer-wrap{{margin-top:10px}}
  .peer-group-label{{font-size:11px;font-weight:700;color:var(--muted);letter-spacing:.1em;margin-bottom:6px}}
  .peer-chips{{display:flex;flex-wrap:wrap;gap:6px}}
  .peer-chip{{font-size:12px;font-weight:700;padding:5px 11px;border-radius:14px;background:#fff;border:1px solid var(--line);text-decoration:none;color:var(--navy);white-space:nowrap}}
  .peer-chip:hover{{border-color:var(--navy)}}
  .peer-chip.same-branch{{border-color:var(--blue);color:var(--blue)}}
  .peer-chip.same-branch:hover{{background:var(--blue);color:#fff}}
  .peer-toban{{font-family:var(--mono);font-size:10px;opacity:.55;font-weight:400}}
  .peer-count{{font-family:var(--mono);font-size:12px;font-weight:400;color:var(--muted);margin-left:6px}}
  .peer-more-btn{{font-size:12px;font-weight:700;margin-top:8px;padding:5px 14px;border-radius:14px;background:#EFEBE2;color:var(--navy);border:1px solid var(--line);cursor:pointer;display:block}}
  .peer-more-btn:hover{{background:var(--navy);color:#fff}}
  .peer-hidden{{display:none!important}}

  .ep-list{{margin-top:14px;display:flex;flex-direction:column;gap:8px}}
  .ep-card{{background:#fff;border:1px solid var(--line);border-left:4px solid var(--navy);border-radius:4px;padding:10px 14px;display:flex;gap:10px;align-items:flex-start;line-height:1.6}}
  .ep-card.family{{border-left-color:var(--blue)}}
  .ep-card.spouse{{border-left-color:var(--red)}}
  .ep-card.mentor{{border-left-color:var(--green)}}
  .ep-badge{{flex-shrink:0;font-size:10px;font-weight:700;letter-spacing:.12em;padding:2px 8px;border-radius:10px;background:var(--navy);color:#fff;margin-top:3px}}
  .ep-card.family .ep-badge{{background:var(--blue)}}
  .ep-card.spouse .ep-badge{{background:var(--red)}}
  .ep-card.mentor .ep-badge{{background:var(--green)}}
  .ep-text{{font-size:13px;color:var(--ink)}}
  .ep-unconfirmed{{font-size:11px;color:var(--muted);margin-left:6px}}

  .sns-row{{margin-top:12px;display:flex;flex-wrap:wrap;gap:8px}}
  .sns-btn{{display:inline-flex;align-items:center;gap:5px;font-size:13px;font-weight:700;padding:8px 18px;border-radius:20px;text-decoration:none;letter-spacing:.03em;transition:opacity .15s}}
  .sns-btn:hover{{opacity:.82}}
  .sns-x{{background:#000;color:#fff}}
  .sns-ig{{background:linear-gradient(135deg,#f09433 0%,#e6683c 25%,#dc2743 50%,#cc2366 75%,#bc1888 100%);color:#fff}}
  .sns-yt{{background:#FF0000;color:#fff}}
  .sns-tt{{background:#010101;color:#fff}}

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
      {'<div class="nickname">「' + nickname_str + '」</div>' if nickname_str else ''}
      <div class="badges">
        <span class="badge grade">{r["grade"]}</span>
        <span class="badge">{r["branch"]}支部</span>
        {'<span class="badge">' + r["ki"] + '期</span>' if r.get("ki") else ''}
        <span class="badge">{status_str}</span>
      </div>
      <div class="checked">最終確認：{checked_str}</div>
    </div>
  </div>
</header>

<main>

{rel_section}

{episode_section}

{mini_graph}

{douki_section}

{branch_section}

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
{sns_html}
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

<script>
function showPeers(hiddenId, btn) {{
  document.getElementById(hiddenId).classList.remove('peer-hidden');
  btn.style.display = 'none';
}}
</script>
</body>
</html>
'''

    out_path = os.path.join(DOCS_DIR, f"{toban}.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[生成] {out_path}")


# --------- エントリポイント ---------

if __name__ == "__main__":
    racers    = load_racers()
    relations = load_relations()
    profiles  = load_profiles()

    # racers.csv未登録（引退等）の選手名をrelations.csvのto_nameから補完するキャッシュ
    # ※ racers には追加しない（ページ生成対象に含めないため）
    retired_names = {}
    for r in relations:
        if r["to_toban"] and r["to_toban"] != "0" and r["to_toban"] not in racers and r["to_name"]:
            retired_names[r["to_toban"]] = r["to_name"]

    ki_map    = build_ki_map(racers)
    branch_map = build_branch_map(racers)

    if len(sys.argv) >= 2:
        targets = sys.argv[1:]
    else:
        targets = list(racers.keys())

    for t in targets:
        generate_page(t, racers, relations, ki_map, branch_map, retired_names, profiles=profiles)

    print("完了")
