#!/usr/bin/env python3
"""
今日の艇運ページ一括生成スクリプト
usage:
  python3 scripts/generate_unki_page.py          # 全選手分
  python3 scripts/generate_unki_page.py 4444     # 登録番号を指定して1人だけ

【仕様】
  - 生年月日があれば生成。なければスキップ。
  - バイオリズム・厄年・星座・九星・方位はすべてJSで計算（毎日再生成不要）
  - docs/unki/{toban}.html に出力
"""

import csv
import os
import sys
from datetime import date

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RACERS_CSV = os.path.join(BASE_DIR, "data", "racers.csv")
OUT_DIR    = os.path.join(BASE_DIR, "docs", "unki")

os.makedirs(OUT_DIR, exist_ok=True)

TODAY_STR = date.today().strftime("%Y年%-m月%-d日")

BRANCH_LIST = [
    "桐生","戸田","江戸川","平和島","多摩川","浜名湖",
    "蒲郡","常滑","津","三国","びわこ","住之江",
    "尼崎","鳴門","丸亀","児島","宮島","徳山",
    "下関","若松","芦屋","福岡","唐津","大村",
]

BRANCH_COORDS = {
    "桐生":  (36.41, 139.39), "戸田":    (35.82, 139.68), "江戸川": (35.71, 139.88),
    "平和島":(35.59, 139.73), "多摩川":  (35.54, 139.69), "浜名湖": (34.70, 137.72),
    "蒲郡":  (34.82, 137.22), "常滑":    (34.88, 136.83), "津":     (34.72, 136.51),
    "三国":  (36.21, 136.17), "びわこ":  (35.20, 136.05), "住之江": (34.60, 135.47),
    "尼崎":  (34.73, 135.40), "鳴門":    (34.15, 134.62), "丸亀":   (34.27, 133.80),
    "児島":  (34.47, 133.82), "宮島":    (34.27, 132.32), "徳山":   (34.05, 131.81),
    "下関":  (33.95, 130.95), "若松":    (33.89, 130.82), "芦屋":   (33.86, 130.66),
    "福岡":  (33.59, 130.38), "唐津":    (33.45, 129.96), "大村":   (32.91, 129.99),
}

BRANCH_NAME_MAP = {
    "東京": "江戸川", "大阪": "住之江", "兵庫": "尼崎",
    "愛知": "常滑",   "静岡": "浜名湖", "福岡": "福岡",
    "長崎": "大村",   "佐賀": "唐津",   "広島": "宮島",
    "山口": "徳山",   "岡山": "児島",   "香川": "丸亀",
    "徳島": "鳴門",   "群馬": "桐生",   "埼玉": "戸田",
    "千葉": "江戸川", "滋賀": "びわこ", "三重": "津",
    "愛媛": "三国",   "福井": "三国",   "石川": "三国",
    "富山": "三国",   "北海道": "桐生", "青森": "桐生",
    "秋田": "桐生",   "岩手": "桐生",   "宮城": "桐生",
    "山形": "桐生",   "福島": "戸田",   "茨城": "戸田",
    "栃木": "桐生",   "新潟": "桐生",   "長野": "桐生",
    "神奈川": "多摩川","東京都": "江戸川",
    "和歌山": "住之江","京都": "住之江","奈良": "住之江",
    "岐阜": "常滑",   "滋賀県": "びわこ",
    "島根": "宮島",   "鳥取": "宮島",
    "高知": "丸亀",   "熊本": "大村",   "鹿児島": "大村",
    "宮崎": "大村",   "大分": "若松",   "福岡県": "福岡",
    "山口県": "徳山", "沖縄": "大村",
}


def branch_to_venue(branch):
    """支部名からホーム艇場の名前と座標を返す（見つからない場合はNone）"""
    # 直接一致
    if branch in BRANCH_COORDS:
        return branch, BRANCH_COORDS[branch]
    # マップ経由
    mapped = BRANCH_NAME_MAP.get(branch)
    if mapped and mapped in BRANCH_COORDS:
        return mapped, BRANCH_COORDS[mapped]
    return None, None


def load_racers():
    with open(RACERS_CSV, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def generate_page(racer):
    toban  = racer["toban"]
    name   = racer["name"]
    kana   = racer["kana"] or ""
    branch = racer["branch"] or ""
    birth  = racer["birth"] or ""
    grade  = racer["grade"] or ""
    ki     = racer["ki"] or ""

    if not birth or len(birth) < 10:
        return None  # 生年月日がなければスキップ

    try:
        bd = date.fromisoformat(birth)
    except ValueError:
        return None

    birth_year  = bd.year
    birth_month = bd.month
    birth_day   = bd.day

    # ホーム艇場情報
    venue_name, venue_coord = branch_to_venue(branch)
    venue_lat  = venue_coord[0] if venue_coord else "null"
    venue_lng  = venue_coord[1] if venue_coord else "null"
    venue_name_js = f'"{venue_name}"' if venue_name else "null"

    profile_url = f"https://boatrace.jp/owpc/pc/data/racersearch/profile?toban={toban}"
    db_url      = f"https://boatrace-db.net/racer/index2/regno/{toban}/"

    html = f'''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>今日の艇運｜{name}（{toban}）｜舟☆探</title>
<style>
  :root{{
    --ink:#1C2530; --paper:#F7F5F0; --navy:#0E2A3C; --navy2:#173B52;
    --red:#E33A2E; --blue:#2E5FE3; --yellow:#F2C21F; --green:#2FA65A;
    --line:#D8D3C8; --muted:#6B7280;
  }}
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{background:var(--paper);color:var(--ink);font-family:'Helvetica Neue',Arial,'Hiragino Kaku Gothic ProN',sans-serif;line-height:1.7;font-size:15px}}

  .lane-strip{{display:flex;height:6px}}
  .lane-strip span{{flex:1}}
  .l1{{background:#fff;border-bottom:1px solid var(--line)}}.l2{{background:#222}}
  .l3{{background:var(--red)}}.l4{{background:var(--blue)}}.l5{{background:var(--yellow)}}.l6{{background:var(--green)}}

  header{{background:var(--navy);color:#fff}}
  .topbar{{max-width:720px;margin:0 auto;padding:12px 20px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px}}
  .brand{{font-weight:900;font-size:17px;letter-spacing:.06em}}
  .nav-links{{display:flex;gap:12px;font-size:12px}}
  .nav-links a{{color:rgba(255,255,255,.75);text-decoration:none}}
  .nav-links a:hover{{color:#fff}}

  .hero{{background:var(--navy);padding:20px 20px 28px}}
  .hero-in{{max-width:720px;margin:0 auto;display:flex;justify-content:space-between;align-items:flex-end;flex-wrap:wrap;gap:12px}}
  .hero h1{{font-weight:900;font-size:24px;letter-spacing:.04em;line-height:1.3}}
  .hero .date-badge{{font-family:monospace;font-size:11px;color:var(--yellow);letter-spacing:.15em;margin-bottom:6px}}
  .hero .who{{font-size:13px;color:rgba(255,255,255,.75);text-align:right}}
  .hero .who b{{font-size:16px;color:#fff;display:block}}

  main{{max-width:720px;margin:0 auto;padding:8px 20px 40px}}
  section{{margin-top:28px}}
  h2{{font-weight:900;font-size:18px;letter-spacing:.05em;padding-bottom:7px;border-bottom:2px solid var(--ink);display:flex;justify-content:space-between;align-items:baseline}}
  h2 .en{{font-family:monospace;font-size:10px;letter-spacing:.2em;color:var(--muted);font-weight:500}}
  .card{{background:#fff;border:1px solid var(--line);border-radius:6px;margin-top:12px;padding:16px 18px}}

  .score-wrap{{display:flex;align-items:center;gap:20px;flex-wrap:wrap}}
  .score-num{{font-family:monospace;font-weight:700;font-size:54px;line-height:1;color:var(--navy)}}
  .score-num small{{font-size:15px;color:var(--muted);font-weight:400}}
  .score-word{{font-weight:900;font-size:22px;color:var(--red)}}
  .score-desc{{font-size:13px;color:var(--muted);flex:1;min-width:180px}}

  .hexa-wrap{{display:flex;gap:16px;align-items:center;flex-wrap:wrap;justify-content:center}}
  .hexa-legend{{font-size:12px;min-width:170px}}
  .hexa-legend div{{display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px dashed var(--line)}}
  .hexa-legend i{{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:7px;vertical-align:middle}}
  .hexa-legend b{{font-family:monospace;font-weight:700}}

  .bio-caption{{font-size:12px;color:var(--muted);margin-top:8px}}
  .bio-vals{{display:flex;gap:8px;margin-top:10px;flex-wrap:wrap}}
  .bio-pill{{font-size:12px;font-weight:700;padding:5px 12px;border-radius:14px;color:#fff}}

  .koyomi-grid{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}
  @media(max-width:500px){{.koyomi-grid{{grid-template-columns:1fr}}}}
  .koyomi-item{{padding:10px 14px;border-radius:5px;border:1px solid var(--line)}}
  .koyomi-label{{font-size:10px;font-weight:700;color:var(--muted);letter-spacing:.1em;text-transform:uppercase;margin-bottom:4px}}
  .koyomi-val{{font-size:15px;font-weight:700}}
  .koyomi-sub{{font-size:11px;color:var(--muted);margin-top:2px}}

  .yaku-warn{{background:#FFF3CD;border:1px solid #FFDA6A;color:#856404}}
  .yaku-ok{{background:#E7F3EB;border:1px solid #A3D9B1;color:#1E7A41}}

  .houi-wrap{{display:flex;gap:16px;align-items:center;flex-wrap:wrap}}
  .houi-text{{flex:1;min-width:180px;font-size:13px}}
  .houi-text b{{font-size:15px;font-weight:900}}
  .kichi{{color:var(--green);font-weight:700}}

  .external-links{{display:flex;gap:10px;flex-wrap:wrap;margin-top:14px}}
  .ext-btn{{padding:8px 16px;border-radius:4px;font-size:12px;font-weight:700;text-decoration:none;color:#fff;background:var(--navy)}}
  .ext-btn:hover{{opacity:.85}}

  .disclaimer{{margin-top:32px;font-size:11px;color:var(--muted);background:#EFEBE2;border-radius:4px;padding:12px 14px;line-height:1.8}}
  .checked{{font-size:11px;color:var(--muted);margin-top:8px;text-align:right}}
  footer{{border-top:1px solid var(--line);margin-top:36px;padding:16px;text-align:center;font-size:11px;color:var(--muted)}}
</style>
</head>
<body>

<header>
  <div class="topbar">
    <div class="brand">舟☆探</div>
    <nav class="nav-links">
      <a href="../../index.html">トップ</a>
      <a href="../racer/{toban}.html">選手ページ</a>
      <a href="../../map.html">関係マップ</a>
    </nav>
  </div>
  <div class="lane-strip"><span class="l1"></span><span class="l2"></span><span class="l3"></span><span class="l4"></span><span class="l5"></span><span class="l6"></span></div>
  <div class="hero">
    <div class="hero-in">
      <div>
        <div class="date-badge" id="todayBadge"></div>
        <h1>今日の艇運</h1>
      </div>
      <div class="who">
        <b>{name}</b>
        {toban}・{branch}支部{'・' + grade if grade else ''}
      </div>
    </div>
  </div>
</header>

<main>

  <section>
    <h2>総合艇運 <span class="en">TODAY'S SCORE</span></h2>
    <div class="card">
      <div class="score-wrap">
        <div class="score-num" id="scoreNum">--<small>/100</small></div>
        <div>
          <div class="score-word" id="scoreWord">--</div>
          <div style="font-size:11px;color:var(--muted)">6要素の平均から算出</div>
        </div>
        <div class="score-desc" id="scoreDesc"></div>
      </div>
    </div>
  </section>

  <section>
    <h2>艇運ヘキサ <span class="en">HEXA CHART</span></h2>
    <div class="card">
      <div class="hexa-wrap">
        <svg id="hexa" width="260" height="260" viewBox="0 0 260 260"></svg>
        <div class="hexa-legend" id="hexaLegend"></div>
      </div>
      <div class="bio-caption">6艇カラーの6軸で今日の運気を採点。①〜③はバイオリズム実計算、④〜⑥は生年月日由来の暦データ。</div>
    </div>
  </section>

  <section>
    <h2>バイオリズム <span class="en">BIORHYTHM</span></h2>
    <div class="card">
      <svg id="bio" width="100%" height="170" viewBox="0 0 640 170" preserveAspectRatio="none"></svg>
      <div class="bio-vals" id="bioVals"></div>
      <div class="bio-caption">誕生日を起点に身体23日・感情28日・知性33日の周期で波を描く古典的な計算法。中央の縦線が今日。</div>
    </div>
  </section>

  <section>
    <h2>暦ノート <span class="en">KOYOMI</span></h2>
    <div class="card">
      <div class="koyomi-grid" id="koyomiGrid"></div>
    </div>
  </section>

  <section>
    <h2>今節の方位 <span class="en">DIRECTION</span></h2>
    <div class="card">
      <div class="houi-wrap">
        <svg id="compass" width="140" height="140" viewBox="0 0 140 140"></svg>
        <div class="houi-text" id="houiText">--</div>
      </div>
    </div>
  </section>

  <div class="external-links">
    <a class="ext-btn" href="{profile_url}" target="_blank" rel="noopener">BOATRACE公式プロフィール</a>
    <a class="ext-btn" href="{db_url}" target="_blank" rel="noopener">艇国DB</a>
  </div>

  <div class="disclaimer">
    「今日の艇運」は生年月日等をもとにしたエンターテインメントコンテンツです。レース予想の根拠となるものではなく、的中を示唆するものではありません。舟券の購入はご自身の判断でお楽しみください。
  </div>
  <div class="checked">データ確認日: {TODAY_STR}</div>

</main>

<footer>舟☆探 選手名鑑｜艇運はエンタメです。データで読む予想は「舟☆探」で。</footer>

<script>
// ===== 基本データ =====
const birth = new Date({birth_year}, {birth_month - 1}, {birth_day});
const venueName = {venue_name_js};
const venueLat  = {venue_lat};
const venueLng  = {venue_lng};

// ===== 今日の日付 =====
const today = new Date();
today.setHours(0,0,0,0);
document.getElementById("todayBadge").textContent =
  today.getFullYear()+"."+String(today.getMonth()+1).padStart(2,"0")+"."+String(today.getDate()).padStart(2,"0");

// ===== バイオリズム計算 =====
const daysSinceBirth = Math.floor((today - birth) / 86400000);
const bioVal  = p => Math.sin(2 * Math.PI * daysSinceBirth / p);
const bioAt   = (p, off) => Math.sin(2 * Math.PI * (daysSinceBirth + off) / p);
const pct     = v => Math.round((v + 1) * 50);

const bio = {{
  phy: bioVal(23),
  emo: bioVal(28),
  int: bioVal(33),
}};

// ===== 星座 =====
function getZodiac(m, d) {{
  const table = [
    [1,20,"みずがめ座"],[2,19,"うお座"],[3,21,"おひつじ座"],[4,20,"おうし座"],
    [5,21,"ふたご座"],[6,21,"かに座"],[7,23,"しし座"],[8,23,"おとめ座"],
    [9,23,"てんびん座"],[10,23,"さそり座"],[11,22,"いて座"],[12,22,"やぎ座"],
  ];
  for (const [cm,cd,name] of table) {{
    if (m < cm || (m === cm && d < cd)) return name;
  }}
  return "やぎ座";
}}
const zodiac = getZodiac({birth_month}, {birth_day});

// ===== 今年の星座運（週替わり擬似ランダム）=====
const weekNum = Math.floor(daysSinceBirth / 7) % 5;
const zodiacLucks = ["普通の一週間","勝負運が上昇","体力充実の時","集中力アップ","焦りは禁物"];
const zodiacLuck = zodiacLucks[weekNum];

// ===== 九星（生年月日から計算）=====
function getKyusei(year, month, day) {{
  // 節分（2/4前後）以前は前年として計算
  const adjYear = (month < 2 || (month === 2 && day < 4)) ? year - 1 : year;
  const base = (adjYear - 1) % 9;
  const stars = ["一白水星","二黒土星","三碧木星","四緑木星","五黄土星","六白金星","七赤金星","八白土星","九紫火星"];
  // 九星は降順（年が増えるごとに1つ下がる）
  const idx = (8 - base % 9 + 9) % 9;
  return stars[idx];
}}
const kyusei = getKyusei({birth_year}, {birth_month}, {birth_day});

// 今月の吉方位（九星ごとに固定パターン）
const kyuseiHoui = {{
  "一白水星": ["南","東北"],
  "二黒土星": ["西南","東北"],
  "三碧木星": ["東","北"],
  "四緑木星": ["東南","南"],
  "五黄土星": ["西","東北"],
  "六白金星": ["北西","西"],
  "七赤金星": ["西","南東"],
  "八白土星": ["東北","南西"],
  "九紫火星": ["南","東南"],
}};
const luckyDirs = kyuseiHoui[kyusei] || ["東","南"];
const luckyDirMain = luckyDirs[0];

// ===== 厄年判定（数え年）=====
function getYakudoshi(birthYear, today) {{
  const kazoedoshi = today.getFullYear() - birthYear + 1;
  // 男性の厄年（数え年）
  const yakuMen = [25, 42, 61]; // 42が大厄
  const yakuLabel = {{25:"前厄・後厄", 42:"大厄（最も注意）", 43:"本厄後の後厄", 41:"大厄の前厄", 61:"還暦厄"}};
  // 性別不明なので男性基準で判定
  if (kazoedoshi === 42) return ["大厄", "数え年42歳（最も注意が必要な年）", true];
  if (kazoedoshi === 41 || kazoedoshi === 43) return ["前後厄", `数え年${{kazoedoshi}}歳（大厄の前後）`, true];
  if (kazoedoshi === 25 || kazoedoshi === 26 || kazoedoshi === 24) return ["厄年", `数え年${{kazoedoshi}}歳`, true];
  if (kazoedoshi === 61 || kazoedoshi === 60 || kazoedoshi === 62) return ["還暦厄", `数え年${{kazoedoshi}}歳`, true];
  return ["該当なし", `数え年${{kazoedoshi}}歳`, false];
}}
const [yakuLabel, yakuSub, isYaku] = getYakudoshi({birth_year}, today);

// ===== ホーム艇場の方角計算（from支部、to艇場）=====
// 支部の大まかな座標（略式）
function calcBearing(fromLat, fromLng, toLat, toLng) {{
  const toRad = d => d * Math.PI / 180;
  const dLng = toRad(toLng - fromLng);
  const fLat = toRad(fromLat);
  const tLat = toRad(toLat);
  const y = Math.sin(dLng) * Math.cos(tLat);
  const x = Math.cos(fLat) * Math.sin(tLat) - Math.sin(fLat) * Math.cos(tLat) * Math.cos(dLng);
  return (Math.atan2(y, x) * 180 / Math.PI + 360) % 360;
}}

// 方角名
function bearingToName(deg) {{
  const dirs = ["北","北北東","北東","東北東","東","東南東","南東","南南東",
                "南","南南西","南西","西南西","西","西北西","北西","北北西"];
  return dirs[Math.round(deg / 22.5) % 16];
}}

// 方角→SVG角度（北=上=-π/2）
function dirToRad(name) {{
  // SVGでは角度0が右(East)なので、北=0°をcompensation
  const map = {{"北":0,"北東":45,"東":90,"南東":135,"南":180,"南西":225,"西":270,"北西":315,
               "北北東":22.5,"東北東":67.5,"東南東":112.5,"南南東":157.5,
               "南南西":202.5,"西南西":247.5,"北北西":337.5,"西北西":292.5}};
  return ((map[name] || 0) - 90) * Math.PI / 180;
}}

// ===== 今月の九星スコア（月ごとに変化する簡易スコア）=====
const monthOffset = (today.getFullYear() * 12 + today.getMonth()) % 9;
const kyuseiMonthScore = [72, 65, 80, 58, 75, 82, 68, 60, 78][monthOffset];

// ===== 今月の方位スコア =====
const houiScore = luckyDirMain ? 78 : 55;

// ===== 6軸データ =====
const axes = [
  {{name:"① 身体",  color:"#B9B4A6", val:pct(bio.phy)}},
  {{name:"② 感情",  color:"#222222", val:pct(bio.emo)}},
  {{name:"③ 知性",  color:"#E33A2E", val:pct(bio.int)}},
  {{name:"④ 星回り", color:"#2E5FE3", val:kyuseiMonthScore}},
  {{name:"⑤ 方位",  color:"#F2C21F", val:houiScore}},
  {{name:"⑥ 巡り",  color:"#2FA65A", val: isYaku ? 35 : 70}},
];

// ===== 総合スコア =====
const total = Math.round(axes.reduce((s,a) => s + a.val, 0) / 6);
document.getElementById("scoreNum").innerHTML = total + "<small>/100</small>";
const word = total >= 80 ? "絶好調" : total >= 65 ? "上昇気流" : total >= 45 ? "凪" : total >= 30 ? "向かい風" : "時化";
document.getElementById("scoreWord").textContent = word;
document.getElementById("scoreDesc").textContent =
  total >= 65 ? "波に乗る一日。スタート勘が冴えるかも。" :
  total >= 45 ? "平常運転。展示航走をよく見て。" :
  "無理は禁物の日。手堅い動きに注目。";

// ===== 凡例 =====
document.getElementById("hexaLegend").innerHTML =
  axes.map(a => `<div><span><i style="background:${{a.color}};${{a.color==='#B9B4A6'?'border:1px solid #999':''}}"></i>${{a.name}}</span><b>${{a.val}}</b></div>`).join("");

// ===== 六角レーダー =====
(function() {{
  const svg = document.getElementById("hexa"), C = 130, R = 100;
  const pt = (i, r) => {{
    const ang = -Math.PI/2 + i * Math.PI/3;
    return [C + r * Math.cos(ang), C + r * Math.sin(ang)];
  }};
  let g = "";
  [0.33, 0.66, 1].forEach(f => {{
    g += `<polygon points="${{[0,1,2,3,4,5].map(i => pt(i, R*f).join(",")).join(" ")}}" fill="none" stroke="#D8D3C8" stroke-width="1"/>`;
  }});
  [0,1,2,3,4,5].forEach(i => {{
    g += `<line x1="${{C}}" y1="${{C}}" x2="${{pt(i,R)[0]}}" y2="${{pt(i,R)[1]}}" stroke="#D8D3C8" stroke-width="1"/>`;
  }});
  const poly = [0,1,2,3,4,5].map(i => pt(i, R * axes[i].val / 100).join(",")).join(" ");
  g += `<polygon points="${{poly}}" fill="rgba(14,42,60,.18)" stroke="#0E2A3C" stroke-width="2.5" stroke-linejoin="round"/>`;
  [0,1,2,3,4,5].forEach(i => {{
    const [x,y] = pt(i, R * axes[i].val / 100);
    g += `<circle cx="${{x}}" cy="${{y}}" r="5" fill="${{axes[i].color}}" stroke="#fff" stroke-width="2"/>`;
    const [lx,ly] = pt(i, R + 18);
    g += `<text x="${{lx}}" y="${{ly}}" text-anchor="middle" font-size="10" font-weight="700" fill="#1C2530" dominant-baseline="middle">${{axes[i].name.slice(2)}}</text>`;
  }});
  svg.innerHTML = g;
}})();

// ===== バイオリズム波形（±10日）=====
(function() {{
  const svg = document.getElementById("bio"), W = 640, H = 170, mid = H/2, span = 10, step = W/(span*2);
  const series = [
    {{p:23, c:"#8A8577", label:"身体"}},
    {{p:28, c:"#222", label:"感情"}},
    {{p:33, c:"#E33A2E", label:"知性"}},
  ];
  let g = `<line x1="0" y1="${{mid}}" x2="${{W}}" y2="${{mid}}" stroke="#D8D3C8"/>`;
  g += `<line x1="${{W/2}}" y1="10" x2="${{W/2}}" y2="${{H-10}}" stroke="#0E2A3C" stroke-width="2" stroke-dasharray="5 4"/>`;
  g += `<text x="${{W/2}}" y="14" text-anchor="middle" font-size="11" font-weight="700" fill="#0E2A3C">今日</text>`;
  series.forEach(s => {{
    let d = "";
    for (let o = -span; o <= span; o += 0.25) {{
      const x = (o + span) * step;
      const y = mid - bioAt(s.p, o) * (H/2 - 22);
      d += (d ? "L" : "M") + x.toFixed(1) + " " + y.toFixed(1) + " ";
    }}
    g += `<path d="${{d}}" fill="none" stroke="${{s.c}}" stroke-width="2.5"/>`;
    const ty = mid - bioAt(s.p, 0) * (H/2 - 22);
    g += `<circle cx="${{W/2}}" cy="${{ty}}" r="5" fill="${{s.c}}" stroke="#fff" stroke-width="2"/>`;
  }});
  svg.innerHTML = g;
  document.getElementById("bioVals").innerHTML = series.map(s => {{
    const v = pct(bioVal(s.p));
    return `<span class="bio-pill" style="background:${{s.c}}">${{s.label}} ${{v}}</span>`;
  }}).join("");
}})();

// ===== 暦ノート =====
(function() {{
  const grid = document.getElementById("koyomiGrid");
  const yakuClass = isYaku ? "yaku-warn" : "yaku-ok";
  grid.innerHTML = `
    <div class="koyomi-item">
      <div class="koyomi-label">星座</div>
      <div class="koyomi-val">${{zodiac}}</div>
      <div class="koyomi-sub">${{zodiacLuck}}</div>
    </div>
    <div class="koyomi-item ${{yakuClass}}">
      <div class="koyomi-label">厄年</div>
      <div class="koyomi-val">${{yakuLabel}}</div>
      <div class="koyomi-sub">${{yakuSub}}</div>
    </div>
    <div class="koyomi-item">
      <div class="koyomi-label">九星</div>
      <div class="koyomi-val">${{kyusei}}</div>
      <div class="koyomi-sub">今月の吉方位：${{luckyDirs.join("・")}}</div>
    </div>
    <div class="koyomi-item">
      <div class="koyomi-label">身体リズム</div>
      <div class="koyomi-val">${{pct(bio.phy)}}<small style="font-size:11px;font-weight:400">/100</small></div>
      <div class="koyomi-sub">感情${{pct(bio.emo)}} / 知性${{pct(bio.int)}}</div>
    </div>
  `;
}})();

// ===== 方位コンパス =====
(function() {{
  const svg = document.getElementById("compass"), C = 70, R = 58;
  let g = `<circle cx="${{C}}" cy="${{C}}" r="${{R}}" fill="#fff" stroke="#0E2A3C" stroke-width="2"/>`;
  const dirs8 = ["北","北東","東","南東","南","南西","西","北西"];
  dirs8.forEach((d, i) => {{
    const ang = -Math.PI/2 + i * Math.PI/4;
    const x = C + (R-12) * Math.cos(ang);
    const y = C + (R-12) * Math.sin(ang);
    const isLucky = luckyDirs.includes(d);
    g += `<text x="${{x}}" y="${{y}}" text-anchor="middle" dominant-baseline="middle" font-size="10" font-weight="700" fill="${{isLucky ? '#2FA65A' : '#6B7280'}}">${{d}}</text>`;
  }});

  // 吉方位ハイライト扇形
  const mainRad = dirToRad(luckyDirMain);
  const a1 = mainRad - Math.PI/8, a2 = mainRad + Math.PI/8;
  g += `<path d="M${{C}} ${{C}} L${{C+R*Math.cos(a1).toFixed(2)}} ${{C+R*Math.sin(a1).toFixed(2)}} A${{R}} ${{R}} 0 0 1 ${{C+R*Math.cos(a2).toFixed(2)}} ${{C+R*Math.sin(a2).toFixed(2)}} Z" fill="rgba(47,166,90,.25)"/>`;

  // 吉方位の方向に矢印を描く
  const arrowRad = dirToRad(luckyDirMain);
  g += `<line x1="${{C}}" y1="${{C}}" x2="${{(C+(R-8)*Math.cos(arrowRad)).toFixed(2)}}" y2="${{(C+(R-8)*Math.sin(arrowRad)).toFixed(2)}}" stroke="#2FA65A" stroke-width="3" stroke-linecap="round"/>`;
  // 矢印の先端（±0.45ラジアン≒26°）
  const ax = C + (R-8)*Math.cos(arrowRad), ay = C + (R-8)*Math.sin(arrowRad);
  const a1r = arrowRad + Math.PI - 0.45, a2r = arrowRad + Math.PI + 0.45;
  g += `<line x1="${{ax.toFixed(2)}}" y1="${{ay.toFixed(2)}}" x2="${{(ax+10*Math.cos(a1r)).toFixed(2)}}" y2="${{(ay+10*Math.sin(a1r)).toFixed(2)}}" stroke="#2FA65A" stroke-width="2" stroke-linecap="round"/>`;
  g += `<line x1="${{ax.toFixed(2)}}" y1="${{ay.toFixed(2)}}" x2="${{(ax+10*Math.cos(a2r)).toFixed(2)}}" y2="${{(ay+10*Math.sin(a2r)).toFixed(2)}}" stroke="#2FA65A" stroke-width="2" stroke-linecap="round"/>`;
  g += `<circle cx="${{C}}" cy="${{C}}" r="4" fill="#0E2A3C"/>`;
  svg.innerHTML = g;

  // 方位テキスト
  const houiEl = document.getElementById("houiText");
  const venueStr = venueName ? `<b>${{venueName}}</b>` : "（艇場データなし）";
  houiEl.innerHTML = `${{venueStr}}<br>九星：<b style="color:var(--navy)">${{kyusei}}</b><br>今月の<span class="kichi">吉方位は${{luckyDirs.join("・")}}</span><br><span style="font-size:11px;color:var(--muted)">※九星気学に基づくエンタメ表示です</span>`;
}})();
</script>

</body>
</html>
'''
    return html


def main():
    target_toban = None
    if len(sys.argv) >= 2 and sys.argv[1].isdigit():
        target_toban = sys.argv[1]

    racers = load_racers()
    if target_toban:
        racers = [r for r in racers if r["toban"] == target_toban]
        if not racers:
            print(f"[エラー] 登録番号 {target_toban} が見つかりません。")
            return

    ok = skip = 0
    for racer in racers:
        html = generate_page(racer)
        if html is None:
            skip += 1
            continue
        out_path = os.path.join(OUT_DIR, f"{racer['toban']}.html")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        ok += 1

    print(f"[完了] 生成: {ok} 件 / スキップ（生年月日なし）: {skip} 件")
    print(f"出力先: {OUT_DIR}")
    if ok > 0:
        print(f"ブラウザで確認: {OUT_DIR}/<登録番号>.html")


if __name__ == "__main__":
    main()
