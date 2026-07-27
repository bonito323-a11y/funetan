#!/usr/bin/env python3
"""
generate_stadium_pages.py
data/stadiums.csv を読み込み、docs/stadium/ 以下に
 - index.html（一覧ページ）
 - 01.html ～ 24.html（各レース場の個別ページ）
を生成する。
"""
import csv
import os
from datetime import date

# ─────────────────────────────────────────
# パス設定
# ─────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(BASE_DIR, "data", "stadiums.csv")
OUT_DIR  = os.path.join(BASE_DIR, "docs", "stadium")
TODAY    = date.today().strftime("%Y-%m-%d")

# コース入着率（静的データ：全国平均値の目安）
COURSE_WIN_RATES = {
    "1": ("43.8", "35.9", "13.1", "5.3", "2.2", "0.8"),  # 1コース〜6コース
    "2": ("10.0", "17.9", "20.3", "18.9", "19.2", "13.7"),
    "3": ("7.4",  "14.9", "17.1", "23.4", "22.3", "14.9"),
    "4": ("5.6",  "13.3", "17.3", "20.9", "24.2", "18.7"),
    "5": ("3.6",  "10.6", "15.4", "19.8", "24.7", "25.9"),
    "6": ("1.8",  "6.7",  "12.3", "18.4", "22.3", "38.5"),
}

# 場ごとの補足特性（簡易）
STADIUM_NOTES = {
    "01": ("桐生は標高が高く空気が薄いため、モーターの出力が落ちやすい。インが強いコースとして知られる。", "30.5"),
    "02": ("戸田はコース幅が狭く、差しや捲り差しが決まりにくい。淡水のため水面が柔らかく出足重視。", "43.2"),
    "03": ("江戸川は潮の影響で水面が荒れやすく、技術力が試される難水面。外枠の台頭が多い。", "38.1"),
    "04": ("平和島は海水コースで波が立ちやすい。風の影響を受けやすくアウトが活躍しやすい。", "40.7"),
    "05": ("多摩川は淡水の静水面でスタートが決まりやすい。イン逃げ率がやや高い。", "41.5"),
    "06": ("浜名湖は広大な湖上のコース。風向きによって水面状況が大きく変わる。", "44.2"),
    "07": ("蒲郡は海水コースでプール型水面。イン勝率が全国屈指の高さ。", "55.1"),
    "08": ("常滑は海水コースで比較的安定した水面。スタートラインが長くアウト有利になりやすい。", "47.8"),
    "09": ("津は伊勢湾に面した海水コース。潮の干満で水面が変化し、起こしが重要。", "45.3"),
    "10": ("三国は日本海に面し、波が荒れやすい。外枠の活躍が目立つアウト有利のコース。", "36.9"),
    "11": ("びわこは琵琶湖の淡水コース。比叡おろしと呼ばれる強風が吹くと外枠有利になる。", "38.4"),
    "12": ("住之江はナイターレース（ドリームナイター）の開催が多い。大阪のメイン場。", "47.2"),
    "13": ("尼崎は大阪湾の内湾でプール型水面。比較的静水面でイン有利。", "49.3"),
    "14": ("鳴門は鳴門海峡の近くで潮流の影響を受ける。独特の波でアウト勢が台頭しやすい。", "39.7"),
    "15": ("丸亀は瀬戸内海に面した海水コース。穏やかな水面でイン勝率が高め。", "51.2"),
    "16": ("児島は倉敷の海水コース。海風の影響が出やすく、モーターの仕上がりが重要。", "44.8"),
    "17": ("宮島は世界遺産・厳島神社近くのコース。瀬戸内の穏やかな海面でイン有利。", "50.1"),
    "18": ("徳山は周南市の海水コース。追い風・向かい風でインの有利不利が変わる。", "45.6"),
    "19": ("下関は関門海峡に近く潮流の影響大。引き潮・満ち潮でインの勝率が変動する。", "42.3"),
    "20": ("若松は響灘に面した海水コース。強風が吹くと荒れレースになりやすい。", "40.1"),
    "21": ("芦屋は遠賀川河口の海水コース。波が立ちやすく技術力が問われる。", "41.8"),
    "22": ("福岡は博多湾の海水コース。内湾で比較的穏やか。ナイター設備あり。", "46.5"),
    "23": ("唐津は玄界灘に近い海水コース。風の影響が強く、スタートの難易度が高い。", "39.2"),
    "24": ("大村は大村湾の内湾コース。波が穏やかでイン逃げ率が全国最高レベル。", "56.3"),
}

# ─────────────────────────────────────────
# 共通スタイル（CSS変数・ベース）
# ─────────────────────────────────────────
COMMON_CSS = """
  :root{
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
  }
  *{margin:0;padding:0;box-sizing:border-box}
  body{background:var(--paper);color:var(--ink);font-family:var(--sans);line-height:1.7;font-size:15px}
  a{color:inherit;text-decoration:none}

  /* 6艇カラーストライプ */
  .lane-strip{display:flex;height:6px}
  .lane-strip span{flex:1}
  .lane-strip .l1{background:#fff;border-bottom:1px solid var(--line)}
  .lane-strip .l2{background:#222}
  .lane-strip .l3{background:var(--red)}
  .lane-strip .l4{background:var(--blue)}
  .lane-strip .l5{background:var(--yellow)}
  .lane-strip .l6{background:var(--green)}

  header{background:var(--navy);color:#fff}
  .topbar{max-width:960px;margin:0 auto;padding:14px 20px;display:flex;justify-content:space-between;align-items:baseline}
  .brand{font-family:var(--serif);font-weight:900;font-size:18px;letter-spacing:.08em}
  .brand small{font-family:var(--sans);font-weight:500;font-size:11px;opacity:.7;margin-left:8px;letter-spacing:.15em}
  .topbar nav{font-size:12px;opacity:.85}
  .topbar nav a{margin-left:14px}
  .topbar nav a:hover{opacity:1}

  footer{background:var(--navy-2);color:rgba(255,255,255,.5);font-size:11px;text-align:center;padding:22px 20px;margin-top:60px}
  footer a{color:rgba(255,255,255,.5)}

  /* スピナー */
  .spinner{
    display:inline-block;width:20px;height:20px;
    border:3px solid rgba(14,42,60,.2);
    border-top-color:var(--navy);
    border-radius:50%;
    animation:spin .8s linear infinite;
    vertical-align:middle;margin-right:6px;
  }
  @keyframes spin{to{transform:rotate(360deg)}}
  .loading-msg{color:var(--muted);font-size:13px}

  /* 水面タイプバッジ */
  .badge{display:inline-block;padding:2px 10px;border-radius:20px;font-size:11px;font-weight:700;letter-spacing:.06em}
  .badge-sea{background:#1a6fa8;color:#fff}
  .badge-river{background:#2a8a4a;color:#fff}
  .badge-lake{background:#1a3a6a;color:#fff}
"""

FONT_LINK = '<link href="https://fonts.googleapis.com/css2?family=Zen+Old+Mincho:wght@600;900&family=Zen+Kaku+Gothic+New:wght@400;500;700&family=IBM+Plex+Mono:wght@500;600&display=swap" rel="stylesheet">'

def water_badge(water_type):
    cls = {"海": "badge-sea", "川": "badge-river", "湖": "badge-lake"}.get(water_type, "badge-sea")
    return f'<span class="badge {cls}">{water_type}</span>'

def water_label(water_type):
    return {"海": "海水", "川": "淡水（川）", "湖": "淡水（湖）"}.get(water_type, water_type)

def direction_label(deg):
    """角度から方位名を返す"""
    dirs = [
        (0,"北"), (22,"北北東"), (45,"北東"), (67,"東北東"),
        (90,"東"), (112,"東南東"), (135,"南東"), (157,"南南東"),
        (180,"南"), (202,"南南西"), (225,"南西"), (247,"西南西"),
        (270,"西"), (292,"西北西"), (315,"北西"), (337,"北北西"),
    ]
    deg = int(deg)
    best, name = 360, "北"
    for ref, n in dirs:
        d = abs(deg - ref) % 360
        if d > 180: d = 360 - d
        if d < best:
            best, name = d, n
    return name + "向き"

# ─────────────────────────────────────────
# JavaScript（天気・日の出日の入り・風効果）
# ─────────────────────────────────────────
def make_weather_js(jma_area_code, lat, lng, start_dir, stadium_code):
    """各ページ共通の天気取得・描画JS"""
    return f"""
<script>
// ─── 設定値（Pythonから埋め込み）───
const JMA_AREA  = '{jma_area_code}';
const LAT       = {lat};
const LNG       = {lng};
const START_DIR = {start_dir};
const STADIUM   = '{stadium_code}';

// ─── 風向き→度数変換 ───
const WIND_DIR = {{
  '北':0,'北北東':22,'北東':45,'東北東':67,
  '東':90,'東南東':112,'南東':135,'南南東':157,
  '南':180,'南南西':202,'南西':225,'西南西':247,
  '西':270,'西北西':292,'北西':315,'北北西':337
}};

// ─── 風効果（向かい風・追い風・横風）───
function windEffect(windFromDeg, startDir) {{
  let diff = Math.abs(windFromDeg - startDir) % 360;
  if (diff > 180) diff = 360 - diff;
  if (diff <= 45)  return {{label:'向かい風', impact:'向かい風はスタートがシビアになりアウト艇に不利な傾向'}};
  if (diff >= 135) return {{label:'追い風',   impact:'追い風はイン艇が加速しやすく逃げが決まりやすい傾向'}};
  return {{label:'横風', impact:'横風はスタート難易度が上がり技術差・実力差が出やすい'}};
}}

// ─── 日の出・日の入り（簡易アルゴリズム）───
function sunriseSunset(lat, lng, date) {{
  const rad = Math.PI / 180;
  const N = Math.floor((date - new Date(date.getFullYear(), 0, 0)) / 86400000);
  const B = (360 / 365.25) * (N - 80) * rad;
  const EqT = (-7.655 * Math.sin(B) + 9.873 * Math.sin(2*B + 3.588)
             + 0.439 * Math.sin(3*B)) / 60;
  const D = -23.45 * Math.cos((360*(N+10)/365.25)*rad) * rad;
  const latRad = lat * rad;
  const cosHA = -Math.tan(latRad) * Math.tan(D);
  if (cosHA < -1) return {{sunrise:'終日昼', sunset:'終日昼'}};
  if (cosHA >  1) return {{sunrise:'終日夜', sunset:'終日夜'}};
  const HA = Math.acos(cosHA) / rad;
  const tz = 9; // JST
  const noon = 12 - EqT - (lng - 135) / 15 + tz;
  const riseH = noon - HA / 15;
  const setH  = noon + HA / 15;
  const fmt = h => {{
    const hh = Math.floor(h) % 24;
    const mm = Math.round((h % 1) * 60);
    return String(hh).padStart(2,'0') + ':' + String(mm).padStart(2,'0');
  }};
  return {{sunrise: fmt(riseH), sunset: fmt(setH)}};
}}

// ─── 天気テキストを整形（main/detailに分離）───
function parseWeatherText(raw) {{
  if (!raw) return {{main:'—', detail:''}};
  let text = raw.replace(/[\u3000\s]+/g,' ').trim();
  // 「後」で分割：「晴れ 後 くもり」→ main:晴れ / detail:後にくもり
  const m = text.match(/^(.+?)\s+後\s+(.+)$/);
  if (m) {{
    const main   = m[1].replace(/\s*時々\s*/g,'・時々').trim();
    const detail = '後に' + m[2].replace(/\s*から\s*/g,'から').replace(/\s*時々\s*/g,'・時々').replace(/\s+/g,' ').trim();
    return {{main, detail}};
  }}
  const main = text.replace(/\s*時々\s*/g,'・時々').trim().slice(0,24);
  return {{main, detail:''}};
}}

// ─── 気温文字列をパース ───
function parseTemp(arr, idx) {{
  if (!arr || !arr[idx]) return null;
  const v = arr[idx];
  if (v === '' || v === null || v === undefined) return null;
  return v;
}}

// ─── 風テキストから方向を抽出 ───
function extractWindDir(windText) {{
  if (!windText) return null;
  for (const dir of Object.keys(WIND_DIR).sort((a,b) => b.length - a.length)) {{
    if (windText.includes(dir)) return WIND_DIR[dir];
  }}
  return null;
}}

// ─── メイン：JMA天気API呼び出し ───
async function loadWeather() {{
  const url = `https://www.jma.go.jp/bosai/forecast/data/forecast/${{JMA_AREA}}.json`;

  // 日の出・日の入りは先に計算（APIと無関係）
  const sun = sunriseSunset(LAT, LNG, new Date());
  const elSunrise = document.getElementById('w-sunrise');
  const elSunset  = document.getElementById('w-sunset');
  if (elSunrise) elSunrise.textContent = sun.sunrise;
  if (elSunset)  elSunset.textContent  = sun.sunset;

  try {{
    const resp = await fetch(url, {{cache: 'no-store'}});
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    const data = await resp.json();

    // timeSeries[0]: 天気・風（当日〜3日）
    const ts0    = data[0].timeSeries[0];
    const area0  = ts0.areas[0];
    const rawWeather = area0.weathers ? area0.weathers[0] : null;
    const wx     = parseWeatherText(rawWeather);
    const wind   = area0.winds ? area0.winds[0] : null;

    // timeSeries[1]: 降水確率
    let pop = '—';
    try {{
      const ts1   = data[0].timeSeries[1];
      const pops  = ts1.areas[0].pops;
      // popは6時間ごと（00-06/06-12/12-18/18-24）。今日の最大値を使用
      const maxPop = Math.max(...pops.map(p => parseInt(p, 10) || 0));
      pop = maxPop + '%';
    }} catch(e) {{}}

    // timeSeries[2]: 気温（tempMin / tempMax）
    let tempMin = null, tempMax = null;
    try {{
      const ts2   = data[0].timeSeries[2];
      const tArea = ts2.areas[0];
      // tempsMin/tempsMax フィールド名で取得
      if (tArea.tempsMin) {{
        tempMin = parseTemp(tArea.tempsMin, 0);
        if (!tempMin || tempMin === '') tempMin = parseTemp(tArea.tempsMin, 1);
      }}
      if (tArea.tempsMax) {{
        tempMax = parseTemp(tArea.tempsMax, 0);
        if (!tempMax || tempMax === '') tempMax = parseTemp(tArea.tempsMax, 1);
      }}
      // 旧フォーマット temps[] フォールバック
      if ((!tempMin && !tempMax) && tArea.temps) {{
        tempMin = parseTemp(tArea.temps, 0);
        tempMax = parseTemp(tArea.temps, 1);
      }}
    }} catch(e) {{}}

    // 風効果
    const windDeg = extractWindDir(wind);
    let effectLabel = '—', effectImpact = '';
    if (windDeg !== null) {{
      const we = windEffect(windDeg, START_DIR);
      effectLabel  = we.label;
      effectImpact = we.impact;
    }}

    // DOM更新
    const set = (id, val) => {{ const el = document.getElementById(id); if(el) el.textContent = val || '—'; }};
    set('w-weather',      wx.main);
    set('w-weather-sub',  wx.detail);
    set('w-wind',         wind ? wind.replace(/[\u3000\s]+/g,' ').trim().slice(0,30) : null);
    set('w-pop',          pop);
    set('w-tempmin',      tempMin ? tempMin + '℃' : null);
    set('w-tempmax',      tempMax ? tempMax + '℃' : null);
    set('w-effect-label', effectLabel);
    set('w-effect-impact',effectImpact);

    // スピナー消去
    document.querySelectorAll('.weather-loading').forEach(el => el.style.display = 'none');
    document.querySelectorAll('.weather-data').forEach(el => el.style.display = '');

  }} catch(err) {{
    console.warn('JMA API error:', err);
    document.querySelectorAll('.weather-loading').forEach(el => {{
      el.innerHTML = '<span style="color:var(--muted);font-size:12px">データ取得中または取得に失敗しました</span>';
    }});
  }}
}}

document.addEventListener('DOMContentLoaded', loadWeather);
</script>
"""

# ─────────────────────────────────────────
# 個別ページ生成
# ─────────────────────────────────────────
def make_detail_page(st):
    code  = st["code"]
    name  = st["name"]
    loc   = st["location"]
    lat   = st["lat"]
    lng   = st["lng"]
    wtype = st["water_type"]
    pref  = st["prefecture"]
    jma   = st["jma_area_code"]
    sdir  = st["start_direction"]

    note, in1_rate = STADIUM_NOTES.get(code, ("—", "—"))
    badge = water_badge(wtype)
    wlabel = water_label(wtype)
    sdir_label = direction_label(sdir)
    weather_js = make_weather_js(jma, lat, lng, sdir, code)

    # コース入着率テーブル（全国平均）
    course_table_rows = ""
    labels = ["1着率", "2着率", "3着率", "4着率", "5着率", "6着率"]
    for c in range(1, 7):
        rates = COURSE_WIN_RATES[str(c)]
        cells = "".join(f"<td>{r}%</td>" for r in rates)
        course_table_rows += f"<tr><td class='course-no c{c}'>{c}号艇</td>{cells}</tr>\n"

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{name}ボートレース場 天気・水面情報 ｜ 舟☆探</title>
{FONT_LINK}
<style>
{COMMON_CSS}

  .hero{{background:var(--navy);color:#fff;padding:36px 20px 44px;text-align:center}}
  .hero h1{{font-family:var(--serif);font-weight:900;font-size:32px;letter-spacing:.06em}}
  .hero .meta{{margin-top:8px;font-size:13px;color:rgba(255,255,255,.7);display:flex;justify-content:center;gap:12px;flex-wrap:wrap}}

  main{{max-width:900px;margin:0 auto;padding:36px 20px 60px}}

  /* セクション見出し */
  .sec-title{{font-family:var(--serif);font-weight:600;font-size:18px;letter-spacing:.06em;
    padding-bottom:6px;border-bottom:2px solid var(--ink);margin-bottom:18px;
    display:flex;align-items:baseline;justify-content:space-between}}
  .sec-title .en{{font-family:var(--mono);font-size:10px;letter-spacing:.2em;color:var(--muted);font-weight:500}}

  /* 天気カード */
  .weather-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:36px}}
  @media(max-width:600px){{.weather-grid{{grid-template-columns:1fr 1fr}}}}
  .w-card{{background:#fff;border:1px solid var(--line);border-radius:6px;padding:16px;position:relative}}
  .w-card .label{{font-size:10px;letter-spacing:.1em;color:var(--muted);font-weight:700;text-transform:uppercase}}
  .w-card .value{{font-family:var(--mono);font-size:20px;font-weight:600;margin-top:4px;line-height:1.3}}
  .w-card .value.sm{{font-size:14px}}
  .w-card .sub{{font-size:11px;color:var(--muted);margin-top:2px}}

  /* 風効果バナー */
  .wind-effect-banner{{background:#EEF4FF;border:1px solid #B8CCEE;border-left:4px solid var(--blue);
    border-radius:4px;padding:14px 18px;margin-bottom:28px;font-size:14px}}
  .wind-effect-banner .wlabel{{font-weight:700;font-family:var(--serif)}}

  /* 水面図 */
  .water-map-wrap{{background:#fff;border:1px solid var(--line);border-radius:6px;padding:20px;
    margin-bottom:28px;text-align:center}}
  .water-map-wrap img{{max-width:100%;height:auto;border-radius:4px}}
  .water-map-wrap .copyright{{font-size:10px;color:var(--muted);margin-top:8px}}

  /* コース入着率テーブル */
  .course-table{{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line);
    font-size:13px;margin-bottom:10px}}
  .course-table th{{padding:8px 10px;background:#EFEBE2;font-weight:700;font-size:11px;
    letter-spacing:.05em;border-bottom:2px solid var(--line);text-align:center}}
  .course-table td{{padding:8px 10px;border-bottom:1px solid var(--line);text-align:center}}
  .course-table tr:last-child td{{border-bottom:none}}
  .course-no{{font-family:var(--mono);font-weight:700;text-align:center}}
  .c1{{color:#1a1a1a}}.c2{{color:#555}}.c3{{color:var(--red)}}
  .c4{{color:var(--blue)}}.c5{{color:#c8900a}}.c6{{color:var(--green)}}
  .table-note{{font-size:11px;color:var(--muted);margin-bottom:28px}}

  /* 基本情報テーブル */
  .info-table{{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line);
    font-size:14px;margin-bottom:28px}}
  .info-table th{{padding:10px 14px;background:#EFEBE2;font-weight:700;font-size:12px;
    letter-spacing:.05em;border-bottom:1px solid var(--line);width:30%;text-align:left}}
  .info-table td{{padding:10px 14px;border-bottom:1px solid var(--line)}}
  .info-table tr:last-child th,.info-table tr:last-child td{{border-bottom:none}}

  /* 外部リンク */
  .links-grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:36px}}
  @media(max-width:480px){{.links-grid{{grid-template-columns:1fr}}}}
  .ext-link{{display:block;background:#fff;border:1px solid var(--line);border-radius:6px;
    padding:14px 18px;font-size:14px;transition:border-color .15s}}
  .ext-link:hover{{border-color:var(--navy)}}
  .ext-link .link-label{{font-size:10px;color:var(--muted);letter-spacing:.1em;font-weight:700}}
  .ext-link .link-name{{font-family:var(--serif);font-weight:600;font-size:16px;margin-top:2px}}
  .ext-link .link-arrow{{float:right;color:var(--muted)}}

  /* パンくず */
  .breadcrumb{{font-size:12px;color:var(--muted);margin-bottom:24px}}
  .breadcrumb a{{color:var(--muted)}}
  .breadcrumb a:hover{{color:var(--ink)}}
</style>
</head>
<body>
<header>
  <div class="topbar">
    <div class="brand">舟☆探 <small>BOATRACE NAVI</small></div>
    <nav>
      <a href="../index.html">選手名鑑</a>
      <a href="index.html">レース場</a>
      <a href="../map.html">関係マップ</a>
    </nav>
  </div>
  <div class="lane-strip">
    <span class="l1"></span><span class="l2"></span><span class="l3"></span>
    <span class="l4"></span><span class="l5"></span><span class="l6"></span>
  </div>
  <div class="hero">
    <h1>{name}ボートレース場</h1>
    <div class="meta">
      <span>📍 {loc}</span>
      <span>{badge}&nbsp;{wlabel}</span>
      <span>スタート方向 {sdir}°（{sdir_label}）</span>
    </div>
  </div>
</header>

<main>
  <div class="breadcrumb">
    <a href="../index.html">舟☆探</a> &rsaquo;
    <a href="index.html">レース場一覧</a> &rsaquo;
    {name}
  </div>

  <!-- 天気情報 -->
  <div class="sec-title">本日の天気・水面情報 <span class="en">WEATHER &amp; WATER</span></div>

  <!-- ローディング中表示 -->
  <div class="weather-loading" style="margin-bottom:20px;padding:14px;background:#fff;border:1px solid var(--line);border-radius:6px">
    <span class="spinner"></span>
    <span class="loading-msg">気象庁データを取得中...</span>
  </div>

  <!-- データ取得後に表示 -->
  <div class="weather-data" style="display:none">
    <div class="weather-grid">
      <div class="w-card" style="grid-column:1/-1">
        <div class="label">現在の天気</div>
        <div class="value sm" id="w-weather">—</div>
        <div class="sub" id="w-weather-sub" style="font-size:12px;color:var(--muted);margin-top:4px"></div>
      </div>
      <div class="w-card">
        <div class="label">風（予報テキスト）</div>
        <div class="value sm" id="w-wind">—</div>
      </div>
      <div class="w-card">
        <div class="label">降水確率（最大）</div>
        <div class="value" id="w-pop">—</div>
      </div>
      <div class="w-card">
        <div class="label">最高 / 最低気温</div>
        <div class="value"><span id="w-tempmax">—</span> / <span id="w-tempmin">—</span></div>
      </div>
      <div class="w-card">
        <div class="label">日の出</div>
        <div class="value" id="w-sunrise">—</div>
      </div>
      <div class="w-card">
        <div class="label">日の入り</div>
        <div class="value" id="w-sunset">—</div>
      </div>
    </div>

    <div class="wind-effect-banner">
      <div style="font-weight:700;margin-bottom:8px">🌊 スタートへの風の影響</div>
      <div style="padding-left:4px">
        <div>└ スタート方向（{sdir}° / {sdir_label}）に対して → <strong id="w-effect-label" style="font-size:16px">—</strong></div>
        <div style="color:var(--muted);font-size:12px;margin-top:6px;padding-left:14px">└ 影響：<span id="w-effect-impact">—</span></div>
      </div>
      <div style="font-size:11px;color:var(--muted);margin-top:10px;border-top:1px solid #B8CCEE;padding-top:6px">
        ※実際のレースは当日の実況をご確認ください
      </div>
    </div>
  </div>

  <!-- 日の出・日の入り（APIと独立して常時表示） -->
  <div style="background:#fff;border:1px solid var(--line);border-radius:6px;padding:14px 18px;
    display:flex;gap:24px;font-size:13px;margin-bottom:28px;flex-wrap:wrap">
    <span>🌅 日の出 <strong id="w-sunrise-static">計算中...</strong></span>
    <span>🌇 日の入り <strong id="w-sunset-static">計算中...</strong></span>
    <span style="font-size:11px;color:var(--muted);margin-top:2px">（{loc} / 座標から計算）</span>
  </div>

  <!-- 公式水面図 -->
  <div class="sec-title" style="margin-top:8px">公式水面図 <span class="en">WATER MAP</span></div>
  <div class="water-map-wrap">
    <img
      id="wmap-img-{code}"
      src="https://www.boatrace.jp/static_extra/pc/images/img_water1_{code}.png"
      alt="{name}ボートレース場 水面図"
      onerror="document.getElementById('wmap-img-{code}').style.display='none';document.getElementById('wmap-err-{code}').style.display='block'"
    >
    <p id="wmap-err-{code}" style="display:none;color:var(--muted);font-size:13px;padding:12px 0">
      水面図を読み込めませんでした（外部サイト画像のため、オフライン時・ブロック時は表示されません）
    </p>
    <div class="copyright">出典：BOAT RACE OFFICIAL WEB ／ 水面図画像は日本モーターボート競走会の著作物です</div>
  </div>

  <!-- コース入着率 -->
  <div class="sec-title">コース別1着率（全国平均参考値） <span class="en">COURSE WIN RATE</span></div>
  <table class="course-table">
    <thead>
      <tr>
        <th>号艇</th>
        <th>1着</th><th>2着</th><th>3着</th>
        <th>4着</th><th>5着</th><th>6着</th>
      </tr>
    </thead>
    <tbody>
      {course_table_rows}
    </tbody>
  </table>
  <p class="table-note">※全国平均の参考値です。実際の成績は公式サイトでご確認ください。</p>

  <!-- 場の特性 -->
  <div class="sec-title">コース特性 <span class="en">COURSE CHARACTER</span></div>
  <div style="background:#fff;border:1px solid var(--line);border-radius:6px;padding:18px;margin-bottom:28px;line-height:1.9;font-size:14px">
    {note}
    <div style="margin-top:10px;font-size:13px;color:var(--muted)">
      参考：1コース1着率 約 <strong style="color:var(--ink)">{in1_rate}%</strong>（目安・時期により変動）
    </div>
  </div>

  <!-- 基本情報 -->
  <div class="sec-title">基本情報 <span class="en">PROFILE</span></div>
  <table class="info-table">
    <tr><th>場コード</th><td>{code}</td></tr>
    <tr><th>所在地</th><td>{loc}</td></tr>
    <tr><th>水面タイプ</th><td>{badge} {wlabel}</td></tr>
    <tr><th>スタート方向</th><td>{sdir}°（{sdir_label}）</td></tr>
    <tr><th>都道府県</th><td>{pref}</td></tr>
    <tr><th>気象庁エリアコード</th><td><span style="font-family:var(--mono)">{jma}</span></td></tr>
  </table>

  <!-- 外部リンク -->
  <div class="sec-title">外部リンク <span class="en">LINKS</span></div>
  <div class="links-grid">
    <a class="ext-link" href="https://www.boatrace.jp/owpc/pc/race/index?jcd={code.zfill(2)}" target="_blank" rel="noopener">
      <div class="link-label">公式サイト</div>
      <div class="link-name">{name} 開催情報 <span class="link-arrow">→</span></div>
    </a>
    <a class="ext-link" href="https://www.boatrace.jp/owpc/pc/data/stadiumlist" target="_blank" rel="noopener">
      <div class="link-label">BOATRACE公式</div>
      <div class="link-name">レース場一覧 <span class="link-arrow">→</span></div>
    </a>
  </div>

  <p style="font-size:11px;color:var(--muted);text-align:center;margin-top:20px">
    最終確認日：{TODAY} ／ 天気データ：気象庁予報API（JMA）<br>
    エンターテインメントコンテンツであり、レース予想の根拠となるものではありません。
  </p>
</main>

<footer>
  <div style="margin-bottom:6px">
    <a href="../index.html">舟☆探 選手名鑑</a> ｜
    <a href="index.html">レース場一覧</a> ｜
    <a href="../map.html">関係マップ</a>
  </div>
  © 舟☆探 – BOATRACE選手名鑑 ｜ データは参考値です。公式サイトで最新情報をご確認ください。
</footer>

{weather_js}

<script>
// 日の出・日の入り（DOMContentLoaded前でも動くよう即実行）
document.addEventListener('DOMContentLoaded', function() {{
  const sun = (function(){{
    const lat={lat}, lng={lng}, date=new Date();
    const rad=Math.PI/180;
    const N=Math.floor((date-new Date(date.getFullYear(),0,0))/86400000);
    const B=(360/365.25)*(N-80)*rad;
    const EqT=(-7.655*Math.sin(B)+9.873*Math.sin(2*B+3.588)+0.439*Math.sin(3*B))/60;
    const D=-23.45*Math.cos((360*(N+10)/365.25)*rad)*rad;
    const cosHA=-Math.tan(lat*rad)*Math.tan(D);
    if(cosHA<-1)return{{rise:'終日昼',set:'終日昼'}};
    if(cosHA>1)return{{rise:'終日夜',set:'終日夜'}};
    const HA=Math.acos(cosHA)/rad;
    const tz=9;
    const noon=12-EqT-(lng-135)/15+tz;
    const fmt=h=>{{const hh=Math.floor(h)%24,mm=Math.round((h%1)*60);return String(hh).padStart(2,'0')+':'+String(mm).padStart(2,'0');}};
    return{{rise:fmt(noon-HA/15),set:fmt(noon+HA/15)}};
  }})();
  const rs = document.getElementById('w-sunrise-static');
  const ss = document.getElementById('w-sunset-static');
  if(rs) rs.textContent = sun.rise;
  if(ss) ss.textContent = sun.set;
}});
</script>

</body>
</html>
"""
    return html


# ─────────────────────────────────────────
# index.html 生成
# ─────────────────────────────────────────
def make_index_page(stadiums):
    cards_html = ""
    for st in stadiums:
        code  = st["code"]
        name  = st["name"]
        loc   = st["location"]
        wtype = st["water_type"]
        jma   = st["jma_area_code"]
        badge = water_badge(wtype)
        # 各カードにJSで天気を埋め込む
        cards_html += f"""
<a class="stadium-card" href="{code}.html" id="card-{code}">
  <div class="card-header">
    <span class="card-code">{code}</span>
    <span>{badge}</span>
  </div>
  <div class="card-name">{name}</div>
  <div class="card-loc">{loc}</div>
  <div class="card-weather" id="cw-{code}">
    <span class="spinner" style="width:14px;height:14px;border-width:2px"></span>
    <span style="font-size:11px;color:var(--muted)">取得中...</span>
  </div>
</a>
"""

    # 全場の天気を一括取得するJS
    js_area_map = "const AREA_MAP = {\n"
    for st in stadiums:
        js_area_map += f"  '{st['code']}': '{st['jma_area_code']}',\n"
    js_area_map += "};"

    weather_index_js = f"""
<script>
{js_area_map}

const fetched = {{}};

function shortWx(raw) {{
  if (!raw) return '—';
  return raw.replace(/\u3000/g,' ').replace(/　/g,' ').replace(/\s+/g,' ')
    .replace(/後\s*/g,'→').replace(/時々\s*/g,'時々').trim().slice(0,16);
}}

async function fetchAreaWeather(areaCode) {{
  if (fetched[areaCode]) return fetched[areaCode];
  try {{
    const r = await fetch(`https://www.jma.go.jp/bosai/forecast/data/forecast/${{areaCode}}.json`, {{cache:'no-store'}});
    if (!r.ok) throw new Error('HTTP '+r.status);
    const d = await r.json();
    const area0 = d[0].timeSeries[0].areas[0];
    const wx = shortWx(area0.weathers ? area0.weathers[0] : null);
    fetched[areaCode] = wx;
    return wx;
  }} catch(e) {{
    return '取得失敗';
  }}
}}

async function loadAllWeather() {{
  const codes = Object.keys(AREA_MAP);
  // 同一エリアコードは1回だけフェッチ（東京3場など）
  const uniqueAreas = [...new Set(Object.values(AREA_MAP))];
  // 並列フェッチ（JMAは同一オリジンCORSなので問題なし）
  await Promise.all(uniqueAreas.map(a => fetchAreaWeather(a)));

  for (const code of codes) {{
    const areaCode = AREA_MAP[code];
    const wx = fetched[areaCode] || '—';
    const el = document.getElementById('cw-' + code);
    if (el) el.innerHTML = `<span style="font-size:12px;color:var(--ink)">${{wx}}</span>`;
  }}
}}

document.addEventListener('DOMContentLoaded', loadAllWeather);
</script>
"""

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>レース場 天気・水面情報 ｜ 舟☆探</title>
{FONT_LINK}
<style>
{COMMON_CSS}

  .hero{{background:var(--navy);color:#fff;padding:36px 20px 44px;text-align:center}}
  .hero h1{{font-family:var(--serif);font-weight:900;font-size:32px;letter-spacing:.06em}}
  .hero p{{margin-top:8px;font-size:13px;color:rgba(255,255,255,.7)}}

  main{{max-width:960px;margin:0 auto;padding:36px 20px 60px}}

  .sec-title{{font-family:var(--serif);font-weight:600;font-size:18px;letter-spacing:.06em;
    padding-bottom:6px;border-bottom:2px solid var(--ink);margin-bottom:18px;
    display:flex;align-items:baseline;justify-content:space-between}}
  .sec-title .en{{font-family:var(--mono);font-size:10px;letter-spacing:.2em;color:var(--muted);font-weight:500}}

  /* 場カードグリッド */
  .stadium-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}}
  @media(max-width:700px){{.stadium-grid{{grid-template-columns:1fr 1fr}}}}
  @media(max-width:420px){{.stadium-grid{{grid-template-columns:1fr}}}}

  .stadium-card{{background:#fff;border:1px solid var(--line);border-radius:6px;
    padding:16px;display:block;transition:transform .12s ease, border-color .12s ease}}
  .stadium-card:hover{{transform:translateY(-2px);border-color:var(--navy)}}

  .card-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px}}
  .card-code{{font-family:var(--mono);font-size:11px;color:var(--muted);font-weight:600}}
  .card-name{{font-family:var(--serif);font-weight:600;font-size:18px;margin-bottom:2px}}
  .card-loc{{font-size:11px;color:var(--muted);margin-bottom:8px}}
  .card-weather{{min-height:20px;display:flex;align-items:center;gap:4px}}

  /* 凡例 */
  .legend{{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:24px;font-size:12px}}
</style>
</head>
<body>
<header>
  <div class="topbar">
    <div class="brand">舟☆探 <small>BOATRACE NAVI</small></div>
    <nav>
      <a href="../index.html">選手名鑑</a>
      <a href="index.html">レース場</a>
      <a href="../map.html">関係マップ</a>
    </nav>
  </div>
  <div class="lane-strip">
    <span class="l1"></span><span class="l2"></span><span class="l3"></span>
    <span class="l4"></span><span class="l5"></span><span class="l6"></span>
  </div>
  <div class="hero">
    <h1>レース場 天気・水面情報</h1>
    <p>全国24場の今日の天気をリアルタイム表示（気象庁データ）</p>
  </div>
</header>

<main>
  <div class="legend">
    <span><span class="badge badge-sea">海</span> 海水コース</span>
    <span><span class="badge badge-river">川</span> 淡水（川）</span>
    <span><span class="badge badge-lake">湖</span> 淡水（湖）</span>
  </div>

  <div class="sec-title">全国24場一覧 <span class="en">ALL 24 STADIUMS</span></div>

  <div class="stadium-grid">
    {cards_html}
  </div>

  <p style="font-size:11px;color:var(--muted);text-align:center;margin-top:28px">
    最終確認日：{TODAY} ／ 天気データ：気象庁予報API（JMA）<br>
    エンターテインメントコンテンツであり、レース予想の根拠となるものではありません。
  </p>
</main>

<footer>
  <div style="margin-bottom:6px">
    <a href="../index.html">舟☆探 選手名鑑</a> ｜
    <a href="../map.html">関係マップ</a>
  </div>
  © 舟☆探 – BOATRACE選手名鑑 ｜ データは参考値です。公式サイトで最新情報をご確認ください。
</footer>

{weather_index_js}
</body>
</html>
"""
    return html


# ─────────────────────────────────────────
# メイン処理
# ─────────────────────────────────────────
def main():
    # CSV読み込み
    stadiums = []
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            stadiums.append(row)
    print(f"読み込み完了: {len(stadiums)}場")

    # 出力ディレクトリ作成
    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"出力先: {OUT_DIR}")

    # 個別ページ生成
    generated = []
    for st in stadiums:
        code = st["code"]
        html = make_detail_page(st)
        out_path = os.path.join(OUT_DIR, f"{code}.html")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        generated.append(out_path)
        print(f"  生成: {code}.html ({st['name']})")

    # index.html 生成
    index_html = make_index_page(stadiums)
    index_path = os.path.join(OUT_DIR, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_html)
    print(f"  生成: index.html（一覧）")

    total = len(generated) + 1
    print(f"\n完了：{total}ファイルを生成しました。")
    print(f"  一覧ページ: {index_path}")
    print(f"  個別ページ: {OUT_DIR}/01.html ～ {OUT_DIR}/24.html")


if __name__ == "__main__":
    main()
