#!/usr/bin/env python3
"""
マクールコラム記事スクレイパー
usage:
  python scripts/scrape_macour.py            # 最新50記事を対象
  python scripts/scrape_macour.py --pages 3  # 記事一覧を3ページ分取得（約90記事）
  python scripts/scrape_macour.py --dry-run  # URLリストだけ表示（記事取得なし）

【方針】
  - robots.txt を確認してから開始
  - 1記事ごとに3〜5秒待機。1回最大50記事まで
  - 記事本文は保存しない
  - 抽出するのは：記事URL・日付・選手名・関係タイプ・本人発言有無のみ
  - 本人発言あり→A仮、なし→B仮（承認時に確定させる）
  - 相手が非選手の場合は to_name="一般男性/一般女性"
  - 選手名がracers.csvと一致しない場合は警告フラグを付ける
"""

import csv
import json
import os
import re
import sys
import time
import unicodedata
import random
from datetime import date
from html.parser import HTMLParser
from urllib.parse import urlparse, quote
from urllib.request import Request, urlopen

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RACERS_CSV     = os.path.join(BASE_DIR, "data", "racers.csv")
CANDIDATES_JSON = os.path.join(BASE_DIR, "scripts", "cache", "candidates.json")

MACOUR_BASE   = "https://sp.macour.jp"
MACOUR_LIST   = "https://sp.macour.jp/columns/macour/"
ROBOTS_URL    = "https://sp.macour.jp/robots.txt"
MAX_ARTICLES  = 50
UA = "Mozilla/5.0 (compatible; funetan-patrol/1.0)"

# 関係キーワード（辞書全種類）
REL_KEYWORDS = [
    "師匠", "弟子", "師弟",
    "配偶者", "夫婦", "結婚", "入籍", "夫", "妻", "元妻", "元夫",
    "父", "母", "息子", "娘", "親子", "子供",
    "兄", "姉", "弟", "妹", "兄弟", "兄妹", "姉弟", "姉妹",
    "親族", "同期", "仲良し", "友人", "友達", "友",
    "引退", "登録抹消",
]

# rel_type の推定マッピング（CLAUDE.md 辞書に合わせる）
REL_TYPE_MAP = [
    (["師弟", "師匠", "恩師"], "師匠"),
    (["弟子", "教え子"], "弟子"),
    (["夫婦", "結婚", "入籍", "配偶者"], "配偶者"),
    (["元妻", "元夫", "離婚"], "元配偶者"),
    (["父", "お父", "パパ", "父親"], "父"),
    (["母", "お母", "ママ", "母親"], "母"),
    (["息子", "長男", "次男"], "子"),
    (["娘", "長女", "次女"], "子"),
    (["兄", "お兄"], "兄"),
    (["姉", "お姉"], "姉"),
    (["弟"], "弟"),
    (["妹"], "妹"),
    (["兄弟", "兄妹", "姉弟", "姉妹"], "兄"),  # 人間が修正
    (["同期"], "同期"),
    (["仲良し", "仲がいい", "親友", "親しい", "友人", "友達"], "仲良し"),
    (["親族", "親戚"], "親族"),
]

# 性別推定キーワード
FEMALE_WORDS = ["妻", "嫁", "彼女", "母", "お母", "ママ", "娘", "姉", "妹", "女性"]
MALE_WORDS   = ["夫", "旦那", "彼氏", "父", "お父", "パパ", "息子", "兄", "弟", "男性"]


# ---- HTML → テキスト変換 ----

class TextExtractor(HTMLParser):
    SKIP_TAGS = {"script", "style", "head", "noscript", "meta", "link"}

    def __init__(self):
        super().__init__()
        self.texts = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP_TAGS:
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS and self._skip > 0:
            self._skip -= 1

    def handle_data(self, data):
        if self._skip == 0:
            t = data.strip()
            if t:
                self.texts.append(t)


def html_to_text(html):
    parser = TextExtractor()
    parser.feed(html)
    lines = []
    for t in parser.texts:
        t = unicodedata.normalize("NFKC", t)
        t = re.sub(r"\s+", " ", t).strip()
        if t:
            lines.append(t)
    return "\n".join(lines)


def extract_p_texts(html):
    """<p>タグのテキストだけ抽出（記事本文に相当）"""
    paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", html, re.DOTALL)
    results = []
    for p in paragraphs:
        text = re.sub(r"<[^>]+>", " ", p)
        text = unicodedata.normalize("NFKC", text)
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) >= 10:
            results.append(text)
    return results


# ---- HTTP取得 ----

def fetch(url, timeout=20):
    safe_url = _encode_url(url)
    req = Request(safe_url, headers={
        "User-Agent": UA,
        "Accept-Language": "ja,en;q=0.8",
        "Accept": "text/html",
    })
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        for enc in ["utf-8", "euc-jp", "shift_jis"]:
            try:
                return raw.decode(enc)
            except (UnicodeDecodeError, LookupError):
                continue
        return raw.decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  [通信エラー] {e}")
        return None


def _encode_url(url):
    parsed = urlparse(url)
    encoded_path = quote(parsed.path, safe="/:@!$&'()*+,;=")
    encoded_query = quote(parsed.query, safe="=&+%")
    return parsed._replace(path=encoded_path, query=encoded_query).geturl()


# ---- robots.txt 確認 ----

def check_robots():
    """sp.macour.jp/robots.txt を取得し /columns/ がブロックされていないか確認"""
    print("robots.txt を確認中...")
    html = fetch(ROBOTS_URL, timeout=10)
    if html is None:
        print("  [警告] robots.txt 取得失敗。アクセスを中止します。")
        return False
    disallowed = []
    for line in html.splitlines():
        line = line.strip()
        if line.lower().startswith("disallow:"):
            path = line.split(":", 1)[1].strip()
            disallowed.append(path)
    blocked = any(
        "/columns/" == p or p == "/"
        for p in disallowed
    )
    if blocked:
        print(f"  [NG] /columns/ がブロックされています: {disallowed}")
        return False
    print(f"  [OK] /columns/ はクロール許可（Disallow: {disallowed}）")
    return True


# ---- 選手名辞書の構築 ----

def load_racer_names():
    """toban → name のマップ + 名前（スペース除去）→ toban の逆引き"""
    name_to_toban = {}   # "白井英治" → "3897"
    toban_to_name = {}   # "3897" → "白井 英治"
    family_names = set() # 苗字セット（改姓検出用）

    if not os.path.exists(RACERS_CSV):
        return name_to_toban, toban_to_name, family_names
    with open(RACERS_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            raw = row["name"]
            stripped = raw.replace(" ", "").replace("\u3000", "")
            name_to_toban[stripped] = row["toban"]
            toban_to_name[row["toban"]] = raw
            # 苗字（最初の漢字ブロック）
            m = re.match(r"^([\u4e00-\u9fff]+)", stripped)
            if m:
                family_names.add(m.group(1))
    return name_to_toban, toban_to_name, family_names


# ---- 記事一覧ページから URL・日付を取得 ----

def get_article_list(max_pages=2):
    """記事一覧を最大 max_pages ページ分取得し、(url, date_str) のリストを返す"""
    articles = []
    seen = set()

    for page in range(1, max_pages + 1):
        url = MACOUR_LIST if page == 1 else f"{MACOUR_LIST}?page={page}"
        print(f"  記事一覧 page {page}: {url}")
        html = fetch(url)
        if html is None:
            break

        # 記事URLを抽出（/columns/macour/{数字}/）
        links = re.findall(
            r'https://sp\.macour\.jp/columns/macour/(\d+)/',
            html
        )
        # 日付を抽出（YYYY/MM/DD HH:MM形式）
        dates_raw = re.findall(r'(\d{4}/\d{2}/\d{2})\s+\d{2}:\d{2}', html)

        # リンクと日付を対応付ける（同数であれば順番で対応）
        for i, art_id in enumerate(links):
            art_url = f"{MACOUR_BASE}/columns/macour/{art_id}/"
            if art_url in seen:
                continue
            seen.add(art_url)
            date_str = dates_raw[i].replace("/", "-") if i < len(dates_raw) else ""
            articles.append({"url": art_url, "date": date_str})

        if len(articles) >= MAX_ARTICLES:
            break
        time.sleep(3)

    return articles[:MAX_ARTICLES]


# ---- 記事から日付をLD+JSONで取得 ----

def extract_publish_date(html):
    """LD+JSON の datePublished から日付（YYYY-MM-DD）を取得"""
    matches = re.findall(
        r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})',
        html
    )
    if matches:
        return matches[0]
    return ""


# ---- 関係タイプの推定 ----

def guess_rel_type(text):
    for keywords, rel in REL_TYPE_MAP:
        if any(k in text for k in keywords):
            return rel
    return "仲良し"


def guess_non_racer_gender(text, rel_type):
    """非選手の相手の性別を推定して to_name を返す"""
    if rel_type in ("配偶者", "元配偶者"):
        # 文脈から性別推定
        if any(w in text for w in FEMALE_WORDS):
            return "一般女性"
        if any(w in text for w in MALE_WORDS):
            return "一般男性"
        return "一般（性別不明）"
    if rel_type in ("母",):
        return "一般女性"
    if rel_type in ("父",):
        return "一般男性"
    return "一般（性別不明）"


# ---- 本文から候補を抽出 ----

def extract_candidates_from_article(url, date_str, paragraphs, name_to_toban, family_names):
    """
    記事の段落テキストリストから関係情報の候補を抽出する。
    記事本文の文字列はこの関数内でのみ使い、candidates に含めない。
    """
    candidates = []
    today = date.today().strftime("%Y-%m-%d")
    art_date = date_str or today

    for para in paragraphs:
        # 関係キーワードを含むか
        matched_kws = [kw for kw in REL_KEYWORDS if kw in para]
        if not matched_kws:
            continue

        # 選手名の検出（スペースあり・なし両対応）
        found_racers = []  # [(toban, name_raw)]
        for stripped_name, toban in name_to_toban.items():
            if stripped_name in para:
                found_racers.append((toban, stripped_name))

        if not found_racers:
            continue

        # 本人発言（「」内に選手名 + 関係キーワード）の検出
        quotes = re.findall(r"「([^」]{1,200})」", para)
        has_quote = False
        for q in quotes:
            if any(kw in q for kw in matched_kws):
                has_quote = True
                break

        confidence = "A仮" if has_quote else "B仮"
        rel_type = guess_rel_type(para)

        # スニペット（本文そのものではなく、キーワード周辺の断片）
        snippet = _make_snippet(para, matched_kws, max_len=200)

        if len(found_racers) >= 2:
            # 選手同士の関係
            from_toban, from_name = found_racers[0]
            to_toban, to_name = found_racers[1]
            candidates.append({
                "snippet": snippet,
                "source_url": url,
                "source_date": art_date,
                "matched_names": [from_name, to_name],
                "suggested_rel": rel_type,
                "suggested_conf": confidence,
                "from_toban": from_toban,
                "from_name": from_name,
                "to_toban": to_toban,
                "to_name": to_name,
                "has_direct_quote": has_quote,
                "name_warning": "",
            })
        else:
            # 選手1人 + 非選手（配偶者・親族等）
            from_toban, from_name = found_racers[0]
            # 非選手が関係する rel_type のみ候補化
            non_racer_rels = {
                "配偶者", "元配偶者", "父", "母", "子", "兄", "姉", "弟", "妹", "親族"
            }
            if rel_type not in non_racer_rels:
                # 仲良し・同期など選手同士が前提のものは2名以上の場合のみ
                continue
            to_name_gen = guess_non_racer_gender(para, rel_type)
            candidates.append({
                "snippet": snippet,
                "source_url": url,
                "source_date": art_date,
                "matched_names": [from_name],
                "suggested_rel": rel_type,
                "suggested_conf": confidence,
                "from_toban": from_toban,
                "from_name": from_name,
                "to_toban": "",
                "to_name": to_name_gen,
                "has_direct_quote": has_quote,
                "name_warning": "",
            })

        # 改姓警告チェック：苗字だけ一致するが選手として登録されていない人名パターン
        name_warning = _check_name_warning(para, name_to_toban, family_names, found_racers)
        if name_warning and candidates:
            candidates[-1]["name_warning"] = name_warning

    return candidates


def _make_snippet(text, keywords, max_len=200):
    """キーワードの前後を含む短いスニペットを返す（本文全体は含めない）"""
    for kw in keywords:
        idx = text.find(kw)
        if idx >= 0:
            start = max(0, idx - 40)
            end = min(len(text), idx + max_len - 40)
            snippet = ("…" if start > 0 else "") + text[start:end]
            if end < len(text):
                snippet += "…"
            return snippet
    return text[:max_len]


def _check_name_warning(text, name_to_toban, family_names, found_racers):
    """
    テキスト内に「既知の苗字 + 人名らしい文字列」があるが racers.csv に未登録の場合、
    改姓の可能性を警告する文字列を返す。
    """
    found_stripped = {n for _, n in found_racers}
    warnings = []
    # 「苗字（2文字以上）＋名前（1〜4文字漢字）」パターンを検出
    candidates_in_text = re.findall(r"([\u4e00-\u9fff]{2,4})\s*([\u4e00-\u9fff]{1,4})", text)
    for family, given in candidates_in_text:
        full = family + given
        if full in found_stripped:
            continue  # 既知の選手
        if full in name_to_toban:
            continue
        if family in family_names and len(given) >= 1:
            # 苗字は既知だが full name は未登録
            warnings.append(f"{full}（{family}姓の選手が改姓した可能性あり）")
    return "、".join(warnings[:3]) if warnings else ""


# ---- 既存 candidates.json の読み込み ----

def load_existing_candidates():
    if os.path.exists(CANDIDATES_JSON):
        with open(CANDIDATES_JSON, encoding="utf-8") as f:
            return json.load(f)
    return []


# ---- メイン ----

def main():
    dry_run = "--dry-run" in sys.argv
    pages_arg = 2  # デフォルト2ページ（約60記事）
    if "--pages" in sys.argv:
        idx = sys.argv.index("--pages")
        if idx + 1 < len(sys.argv):
            try:
                pages_arg = int(sys.argv[idx + 1])
            except ValueError:
                pass

    print("=" * 50)
    print("マクール コラム記事 抽出スクリプト")
    print("=" * 50)

    # robots.txt 確認
    if not check_robots():
        sys.exit(1)

    time.sleep(2)

    # 選手名辞書
    name_to_toban, toban_to_name, family_names = load_racer_names()
    print(f"選手辞書: {len(name_to_toban)} 名\n")

    # 記事一覧取得
    print(f"記事一覧を取得します（最大{pages_arg}ページ）...")
    articles = get_article_list(max_pages=pages_arg)
    print(f"  取得記事数: {len(articles)} 件\n")

    if dry_run:
        print("【ドライランモード】記事URLのみ表示:")
        for a in articles:
            print(f"  {a['date']}  {a['url']}")
        return

    # 既存候補を読み込み（追記モード）
    all_candidates = load_existing_candidates()
    existing_urls = {c["source_url"] for c in all_candidates}
    new_count = 0

    print(f"記事を巡回します（{len(articles)} 件、3〜5秒間隔）...\n")

    for i, art in enumerate(articles):
        url = art["url"]
        date_str = art["date"]

        # 既処理URLはスキップ
        if url in existing_urls:
            print(f"[{i+1}/{len(articles)}] スキップ（処理済み）: {url}")
            continue

        print(f"[{i+1}/{len(articles)}] {url}")

        html = fetch(url)
        if html is None:
            print("  → 取得失敗、スキップ")
            wait = random.randint(3, 5)
            time.sleep(wait)
            continue

        # 日付（LD+JSON優先、一覧ページのもので補完）
        ld_date = extract_publish_date(html)
        art_date = ld_date or date_str

        # 記事本文（<p>タグから）
        paragraphs = extract_p_texts(html)
        print(f"  段落数: {len(paragraphs)}")

        # 候補抽出（本文は返り値の candidates のみに使い、保存しない）
        cands = extract_candidates_from_article(
            url, art_date, paragraphs, name_to_toban, family_names
        )
        print(f"  候補: {len(cands)} 件", end="")
        if cands:
            names = [c["from_name"] + "×" + c["to_name"] for c in cands]
            print(f"  → {', '.join(names[:3])}", end="")
        print()

        all_candidates.extend(cands)
        existing_urls.add(url)
        new_count += len(cands)

        # 待機（3〜5秒ランダム）
        wait = random.randint(3, 5)
        time.sleep(wait)

    # 候補を保存
    with open(CANDIDATES_JSON, "w", encoding="utf-8") as f:
        json.dump(all_candidates, f, ensure_ascii=False, indent=2)

    print(f"\n新規候補: {new_count} 件（累計: {len(all_candidates)} 件）")
    if new_count > 0:
        print(f"候補ファイル: {CANDIDATES_JSON}")
        print("次のステップ: python scripts/generate_review.py → ブラウザで確認")
    else:
        print("新しい候補はありませんでした。")


if __name__ == "__main__":
    main()
