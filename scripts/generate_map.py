#!/usr/bin/env python3
"""
関係マップページ（docs/map.html）生成スクリプト
relations.csv → d3.js フォースグラフ
"""

import csv
import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DOCS_DIR = os.path.join(BASE_DIR, "docs")

RACERS_CSV = os.path.join(DATA_DIR, "racers.csv")
RELATIONS_CSV = os.path.join(DATA_DIR, "relations.csv")

# 関係タイプ → d3 カラーキー
REL_TYPE_MAP = {
    "配偶者":   "spouse",
    "元配偶者": "spouse",
    "父": "family", "母": "family", "子": "family",
    "兄": "family", "姉": "family", "弟": "family", "妹": "family", "親族": "family",
    "師匠": "mentor", "弟子": "mentor",
    "友人": "friend", "仲良し": "friend",
    "同期": "douki",
}

STATUS_LABEL = {
    "active": "現役",
    "retired": "引退",
    "inactive": "休業",
}

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
            relations.append(row)
    return relations

def build_graph(racers, relations):
    """
    nodes と links を構築する。
    - confidence=C の関係は除外
    - source_url なしは除外
    - 片方向記録を双方向リンクとして1本に統一
    - 同期リンク: グラフ内ノード間だけ追加（細い薄色線で表示）
    """
    from collections import defaultdict

    # --- relations.csv から明示関係リンクを構築 ---
    seen_links = set()
    links = []

    for r in relations:
        if r["confidence"] == "C":
            continue
        if not r["source_url"].strip():
            continue

        src = r["from_toban"]
        tgt = r["to_toban"]
        if not tgt:  # to_toban が空（一般人など）はスキップ
            continue

        rel_type = r["rel_type"]
        d3type = REL_TYPE_MAP.get(rel_type, "friend")
        key = tuple(sorted([src, tgt]))

        if key not in seen_links:
            seen_links.add(key)
            links.append({
                "source": src,
                "target": tgt,
                "type": d3type,
                "label": rel_type,
            })

    # 両端ともracers.csvに登録されているリンクのみ残す
    # （引退選手・to_toban=0 など未登録は除外 → D3クラッシュ防止）
    links = [l for l in links if l["source"] in racers and l["target"] in racers]

    # グラフに登場するノードだけを nodes に含める
    involved = set()
    for l in links:
        involved.add(l["source"])
        involved.add(l["target"])

    nodes = []
    for toban, r in racers.items():
        if toban not in involved:
            continue
        nodes.append({
            "id": toban,
            "name": r["name"],
            "branch": r["branch"],
            "grade": r["grade"],
            "ki": r.get("ki", ""),
            "hobby": r["hobby"] or "",
            "status": STATUS_LABEL.get(r["status"], r["status"]),
            "retired": r["status"] == "retired",
        })

    # --- 同期リンク: グラフ内ノード同士で ki が一致するペアだけ追加 ---
    ki_to_nodes = defaultdict(list)
    for n in nodes:
        if n["ki"]:
            ki_to_nodes[n["ki"]].append(n["id"])

    for ki, tobans in ki_to_nodes.items():
        if len(tobans) < 2:
            continue
        for i in range(len(tobans)):
            for j in range(i + 1, len(tobans)):
                key = tuple(sorted([tobans[i], tobans[j]]))
                if key not in seen_links:
                    seen_links.add(key)
                    links.append({
                        "source": tobans[i],
                        "target": tobans[j],
                        "type": "douki",
                        "label": f"{ki}期 同期",
                    })

    return nodes, links

def generate_map(racers, relations):
    nodes, links = build_graph(racers, relations)

    nodes_json = json.dumps(nodes, ensure_ascii=False)
    links_json = json.dumps(links, ensure_ascii=False)

    html = f'''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>関係マップ｜舟☆探 選手名鑑</title>
<link href="https://fonts.googleapis.com/css2?family=Zen+Old+Mincho:wght@600;900&family=Zen+Kaku+Gothic+New:wght@400;500;700&family=IBM+Plex+Mono:wght@500&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
<style>
  :root{{
    --ink:#1C2530;--paper:#F7F5F0;--navy:#0E2A3C;--navy2:#173B52;
    --red:#E33A2E;--blue:#2E5FE3;--yellow:#F2C21F;--green:#2FA65A;
    --line:#D8D3C8;--muted:#94A3B2;
  }}
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{background:var(--navy);color:#fff;font-family:'Zen Kaku Gothic New',sans-serif;overflow:hidden;height:100vh;display:flex;flex-direction:column}}

  /* 6艇カラーストライプ */
  .lane-strip{{display:flex;height:6px;flex-shrink:0}}
  .lane-strip span{{flex:1}}
  .l1{{background:#fff}}.l2{{background:#222}}.l3{{background:var(--red)}}.l4{{background:var(--blue)}}.l5{{background:var(--yellow)}}.l6{{background:var(--green)}}

  header{{padding:10px 16px 6px;flex-shrink:0;display:flex;justify-content:space-between;align-items:center}}
  .brand{{font-family:'Zen Old Mincho',serif;font-weight:900;font-size:16px;letter-spacing:.08em}}
  .brand small{{font-family:'Zen Kaku Gothic New',sans-serif;font-weight:500;font-size:10px;opacity:.6;margin-left:8px;letter-spacing:.15em}}
  .header-right{{font-size:11px;color:var(--muted)}}
  .header-right a{{color:var(--muted);text-decoration:none;opacity:.8}}
  .header-right a:hover{{opacity:1}}

  .sub{{font-size:11px;color:var(--muted);padding:0 16px 4px;flex-shrink:0}}

  .legend{{display:flex;flex-wrap:wrap;gap:10px;padding:4px 16px 4px;font-size:10px;color:var(--muted);flex-shrink:0}}
  .legend i{{display:inline-block;width:16px;height:3px;border-radius:2px;margin-right:4px;vertical-align:middle}}

  #graph{{flex:1;touch-action:none}}

  /* 操作ボタン */
  .controls{{position:fixed;bottom:84px;left:0;right:0;display:flex;justify-content:center;gap:8px;pointer-events:none}}
  .controls button{{pointer-events:auto;font-family:inherit;font-weight:700;font-size:12px;padding:9px 18px;border-radius:20px;border:1px solid rgba(255,255,255,.25);background:var(--navy2);color:#fff;cursor:pointer;transition:opacity .15s}}
  .controls button:hover{{opacity:.85}}

  /* 下パネル */
  #panel{{position:fixed;bottom:0;left:0;right:0;background:var(--paper);color:var(--ink);border-radius:12px 12px 0 0;padding:12px 18px;min-height:74px;box-shadow:0 -4px 20px rgba(0,0,0,.35)}}
  #panel .p-header{{display:flex;align-items:baseline;justify-content:space-between}}
  #panel .p-name{{font-family:'Zen Old Mincho',serif;font-weight:900;font-size:17px}}
  #panel .p-name span{{font-family:'IBM Plex Mono',monospace;font-size:11px;color:#6B7280;margin-left:6px}}
  #panel .p-link{{font-size:11px;color:var(--navy);text-decoration:none;border-bottom:1px solid var(--navy);display:none}}
  #panel .p-link:hover{{opacity:.7}}
  #panel .p-body{{font-size:12px;margin-top:3px;color:#374151;line-height:1.7}}

  .node-label{{font-size:11px;font-weight:700;fill:#fff;pointer-events:none;text-anchor:middle;paint-order:stroke;stroke:var(--navy);stroke-width:3px}}
  .node-toban{{font-size:8px;fill:var(--muted);pointer-events:none;text-anchor:middle;font-family:'IBM Plex Mono',monospace}}
</style>
</head>
<body>

<div class="lane-strip"><span class="l1"></span><span class="l2"></span><span class="l3"></span><span class="l4"></span><span class="l5"></span><span class="l6"></span></div>

<header>
  <div class="brand">舟☆探<small>関係マップ</small></div>
  <div class="header-right"><a href="index.html">← 選手一覧に戻る</a></div>
</header>
<div class="sub">選手をタップ → 繋がりをハイライト。ドラッグで動かせます。ピンチ／スクロールで拡縮。</div>

<div class="legend">
  <span><i style="background:var(--red)"></i>夫婦・元配偶者</span>
  <span><i style="background:var(--blue)"></i>家族・親族</span>
  <span><i style="background:var(--green)"></i>師弟</span>
  <span><i style="background:var(--yellow)"></i>友人・仲良し</span>
  <span><i style="background:#7B8794"></i>同期</span>
</div>

<svg id="graph"></svg>

<div class="controls">
  <button id="resetBtn">リセット</button>
</div>

<div id="panel">
  <div class="p-header">
    <div class="p-name">関係マップ</div>
    <a class="p-link" id="panelLink" href="#" target="_blank"></a>
  </div>
  <div class="p-body">選手をタップすると、その選手の人間関係をハイライトします。</div>
</div>

<script>
const nodes = {nodes_json};
const links = {links_json};
const colors = {{spouse:"#E33A2E",family:"#2E5FE3",mentor:"#2FA65A",friend:"#F2C21F",douki:"#7B8794"}};

const svg = d3.select("#graph");
const W = () => svg.node().clientWidth;
const H = () => svg.node().clientHeight;
const g = svg.append("g");

svg.call(
  d3.zoom().scaleExtent([0.3, 3]).on("zoom", e => g.attr("transform", e.transform))
);

const sim = d3.forceSimulation(nodes)
  .force("link", d3.forceLink(links).id(d => d.id).distance(110))
  .force("charge", d3.forceManyBody().strength(-420))
  .force("center", d3.forceCenter(W() / 2, H() / 2))
  .force("collide", d3.forceCollide(40));

const link = g.selectAll("line").data(links).join("line")
  .attr("stroke", d => colors[d.type] || "#7B8794")
  .attr("stroke-width", d => d.type === "douki" ? 1.2 : 2.5)
  .attr("stroke-dasharray", d => d.type === "douki" ? "5 4" : null)
  .attr("stroke-opacity", d => d.type === "douki" ? 0.28 : 0.80);

const node = g.selectAll("g.n").data(nodes).join("g")
  .attr("class", "n")
  .style("cursor", "pointer")
  .call(
    d3.drag()
      .on("start", (e, d) => {{ if (!e.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; }})
      .on("drag",  (e, d) => {{ d.fx = e.x; d.fy = e.y; }})
      .on("end",   (e, d) => {{ if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null; }})
  );

node.append("circle")
  .attr("r", 18)
  .attr("fill", d => d.retired ? "#3E4C59" : "#173B52")
  .attr("stroke", "#fff")
  .attr("stroke-width", 1.5);

node.append("text").attr("class", "node-label").attr("dy", -26).text(d => d.name);
node.append("text").attr("class", "node-toban").attr("dy", 36).text(d => d.id);

// 隣接マップ
const adj = {{}};
links.forEach(l => {{
  const s = l.source.id || l.source;
  const t = l.target.id || l.target;
  (adj[s] = adj[s] || []).push({{ to: t, label: l.label }});
  (adj[t] = adj[t] || []).push({{ to: s, label: l.label }});
}});

const panel    = document.getElementById("panel");
const panelLink = document.getElementById("panelLink");

function setPanel(title, body, toban) {{
  panel.querySelector(".p-name").innerHTML = title;
  panel.querySelector(".p-body").innerHTML = body;
  if (toban) {{
    panelLink.href = "racer/" + toban + ".html";
    panelLink.textContent = "選手ページを開く →";
    panelLink.style.display = "inline";
  }} else {{
    panelLink.style.display = "none";
  }}
}}

function focusNode(d) {{
  const nbrs = new Set([d.id, ...(adj[d.id] || []).map(x => x.to)]);

  node.select("circle")
    .attr("opacity", n => nbrs.has(n.id) ? 1 : 0.12)
    .attr("fill", n => n.id === d.id ? "#E33A2E" : (n.retired ? "#3E4C59" : "#173B52"))
    .attr("r", n => n.id === d.id ? 22 : 18);

  node.selectAll("text").attr("opacity", n => nbrs.has(n.id) ? 1 : 0.12);

  link
    .attr("stroke-opacity", l => {{
      const active = l.source.id === d.id || l.target.id === d.id;
      if (!active) return 0.05;
      return l.type === "douki" ? 0.45 : 1;
    }})
    .attr("stroke-width", l => {{
      const active = l.source.id === d.id || l.target.id === d.id;
      if (!active) return l.type === "douki" ? 1.2 : 2.5;
      return l.type === "douki" ? 1.8 : 4;
    }});

  const rels = (adj[d.id] || []).map(x => {{
    const n2 = nodes.find(n => n.id === x.to);
    return `<b>${{x.label}}</b>：${{n2 ? n2.name : x.to}}`;
  }}).join("　");

  setPanel(
    `${{d.name}}<span>${{d.id}}・${{d.branch}}支部・${{d.status}}</span>`,
    (d.hobby ? `趣味：${{d.hobby}}　` : "") + (rels || "掲載できる関係情報なし"),
    d.id
  );
}}

node.on("click", (e, d) => {{ e.stopPropagation(); focusNode(d); }});

function reset() {{
  node.select("circle")
    .attr("opacity", 1)
    .attr("fill", d => d.retired ? "#3E4C59" : "#173B52")
    .attr("r", 18);
  node.selectAll("text").attr("opacity", 1);
  link
    .attr("stroke-opacity", l => l.type === "douki" ? 0.28 : 0.80)
    .attr("stroke-width",   l => l.type === "douki" ? 1.2 : 2.5);
  setPanel("関係マップ", "選手をタップすると、その選手の人間関係をハイライトします。", null);
}}

document.getElementById("resetBtn").onclick = reset;
svg.on("click", reset);

sim.on("tick", () => {{
  link
    .attr("x1", d => d.source.x).attr("y1", d => d.source.y)
    .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
  node.attr("transform", d => `translate(${{d.x}},${{d.y}})`);
}});

window.addEventListener("resize", () => {{
  sim.force("center", d3.forceCenter(W() / 2, H() / 2)).alpha(0.3).restart();
}});
</script>

</body>
</html>
'''

    out_path = os.path.join(DOCS_DIR, "map.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[生成] {out_path}")
    print(f"  ノード数: {len(nodes)}　リンク数: {len(links)}")

if __name__ == "__main__":
    racers = load_racers()
    relations = load_relations()
    generate_map(racers, relations)
    print("完了")
