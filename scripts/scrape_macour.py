#!/usr/bin/env python3
"""
マクールコラム記事スクレイパー v2
usage:
  python scripts/scrape_macour.py            # 最大50記事
  python scripts/scrape_macour.py --pages 3  # 3ページ分（約90記事）
  python scripts/scrape_macour.py --limit 10 # 最初の10記事のみ
  python scripts/scrape_macour.py --dry-run  # URLリストのみ

【抽出基準（v2改善点）】
  - 同期/仲良し/友人 は完全除外（ki データから自動判定すべきもの）
  - 名前の単純共起は候補にしない
  - 「AはBの師匠」「夫の○○」等、関係を明示する文型にマッチした場合のみ抽出
  - 抽出根拠となった一文をそのまま evidence_sentence として保持
  - 文型から from/to の役割を判定（主語取り違え防止）
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
RACERS_CSV      = os.path.join(BASE_DIR, "data", "racers.csv")
CANDIDATES_JSON = os.path.join(BASE_DIR, "scripts", "cache", "candidates.json")

MACOUR_BASE = "https://sp.macour.jp"
MACOUR_LIST = "https://sp.macour.jp/columns/macour/"
ROBOTS_URL  = "https://sp.macour.jp/robots.txt"
MAX_ARTICLES = 50
UA = "Mozilla/5.0 (compatible; funetan-patrol/1.0)"


# ================================================================
# 明示的な関係パターン定義
#
# 各パターン:
#   (compiled_regex, rel_type, captured_role)
#
# captured_role の意味:
#   "is_master"      : キャプチャされた名前 = 師匠 (to)、文中の他の選手が弟子 (from)
#   "is_student"     : キャプチャされた名前 = 弟子 (from)、文中の他の選手が師匠 (to)
#   "is_spouse"      : キャプチャされた名前 = 配偶者 (to)、文中の選手が from
#   "is_father"      : キャプチャされた名前 = 父 (to)
#   "is_mother"      : キャプチャされた名前 = 母 (to)
#   "is_child"       : キャプチャされた名前 = 子 (to)
#   "is_elder_bro"   : キャプチャされた名前 = 兄 (to)
#   "is_elder_sis"   : キャプチャされた名前 = 姉 (to)
#   "is_younger_bro" : キャプチャされた名前 = 弟 (to)
#   "is_younger_sis" : キャプチャされた名前 = 妹 (to)
#
# ※ captured_role の to 側: 文中の選手が from になる（or paragraph 内の別選手）
# ================================================================

# 名前マッチ用ブロック（漢字 + 任意のスペース + 漢字）
_NAME = r"([\u4e00-\u9fff]{1,4}[\s　]?[\u4e00-\u9fff]{1,4})"

RELATION_PATTERNS = [
    # ---- 師弟 ----
    # 「師匠である今村豊」「師匠の今村豊」「師匠は今村」
    (re.compile(r"師匠(?:であ[るった]|の|たる|は|が)\s*" + _NAME), "師匠", "is_master"),
    # 「今村豊が師匠」「今村豊は師匠」「今村豊こそ師匠」
    (re.compile(_NAME + r"\s*(?:さん)?(?:は|が|こそ)\s*師匠"), "師匠", "is_master"),
    # 「今村豊に師事」
    (re.compile(_NAME + r"\s*(?:さん)?に師事"), "師匠", "is_master"),
    # 「○○への弟子入り」→ ○○ = 師匠
    (re.compile(_NAME + r"\s*(?:さん)?への弟子入り"), "師匠", "is_master"),
    # 「白井英治の師匠」→ 白井 = 弟子 (from)
    (re.compile(_NAME + r"\s*(?:さん)?の師匠"), "師匠", "is_student"),
    # 「弟子の白井英治」「弟子は白井」
    (re.compile(r"弟子(?:の|は|が)\s*" + _NAME), "弟子", "is_student"),
    # 「白井英治は最高の弟子」「白井英治が弟子」
    (re.compile(_NAME + r"\s*(?:さん)?(?:は|が)\s*(?:最高の|日本一の|私の|うちの|一番の)?\s*弟子"), "弟子", "is_student"),

    # ---- 配偶者 ----
    # 「妻の深谷知博」「妻は深谷」「妻である深谷」→ 深谷 = 夫 (to)
    (re.compile(r"妻(?:の|は|が|である)\s*" + _NAME), "配偶者", "is_spouse"),
    # 「夫の川野芽唯」「夫は川野」→ 川野 = 妻 (to)
    (re.compile(r"夫(?:の|は|が|である)\s*" + _NAME), "配偶者", "is_spouse"),
    # 「夫( 深谷知博 )」「妻( 田口節子 )」のカッコ書き形式
    (re.compile(r"(?:夫|妻)[（(]\s*" + _NAME + r"\s*[)）]"), "配偶者", "is_spouse"),
    # 「深谷知博と結婚」「深谷知博と入籍」
    (re.compile(_NAME + r"\s*(?:さん)?と(?:結婚|入籍)"), "配偶者", "is_spouse"),
    # 「深谷知博夫人」
    (re.compile(_NAME + r"夫人"), "配偶者", "is_spouse"),

    # ---- 家族 ----
    # 「父の今村豊」「お父さんの今村」「父は今村」
    (re.compile(r"(?:お)?父(?:さん|様)?(?:の|は|が|である)\s*" + _NAME), "父", "is_father"),
    # 「母の○○」
    (re.compile(r"(?:お)?母(?:さん|様)?(?:の|は|が|である)\s*" + _NAME), "母", "is_mother"),
    # 「息子の○○」
    (re.compile(r"息子(?:の|は|が)\s*" + _NAME), "子", "is_child"),
    # 「娘の○○」
    (re.compile(r"娘(?:の|は|が)\s*" + _NAME), "子", "is_child"),

    # ---- 兄弟 ----
    # 「お兄さんの○○」「兄の○○」「兄は○○」
    (re.compile(r"(?:お)?兄(?:さん)?(?:の|は|が|である)\s*" + _NAME), "兄", "is_elder_bro"),
    # 「お姉さんの○○」
    (re.compile(r"(?:お)?姉(?:さん)?(?:の|は|が|である)\s*" + _NAME), "姉", "is_elder_sis"),
    # 「弟の○○」（弟子は除外: 弟の後に子が来る場合は弟子 → 負の先読み）
    (re.compile(r"弟(?!子)(?:の|は|が|である)\s*" + _NAME), "弟", "is_younger_bro"),
    # 「妹の○○」
    (re.compile(r"妹(?:の|は|が|である)\s*" + _NAME), "妹", "is_younger_sis"),
]

# captured_role → (rel_type_final, gender_for_non_racer)
ROLE_META = {
    "is_master":      ("師匠",  None),
    "is_student":     ("弟子",  None),
    "is_spouse":      ("配偶者", "不明"),
    "is_father":      ("父",   "男性"),
    "is_mother":      ("母",   "女性"),
    "is_child":       ("子",   "不明"),
    "is_elder_bro":   ("兄",   "男性"),
    "is_elder_sis":   ("姉",   "女性"),
    "is_younger_bro": ("弟",   "男性"),
    "is_younger_sis": ("妹",   "女性"),
}


# ================================================================
# HTTP / HTML ユーティリティ
# ================================================================

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
    encoded_path  = quote(parsed.path, safe="/:@!$&'()*+,;=")
    encoded_query = quote(parsed.query, safe="=&+%")
    return parsed._replace(path=encoded_path, query=encoded_query).geturl()


def extract_p_texts(html):
    """<p> タグから段落テキストのリストを返す"""
    paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", html, re.DOTALL)
    results = []
    for p in paragraphs:
        text = re.sub(r"<[^>]+>", " ", p)
        text = unicodedata.normalize("NFKC", text)
        text = re.sub(r"\s{2,}", " ", text).strip()
        if len(text) >= 10:
            results.append(text)
    return results


def extract_publish_date(html):
    """LD+JSON の datePublished から YYYY-MM-DD を返す"""
    m = re.search(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})', html)
    return m.group(1) if m else ""


def extract_headline(html):
    """LD+JSON の headline（記事タイトル）を返す"""
    m = re.search(r'"headline"\s*:\s*"([^"]{1,200})"', html)
    return m.group(1) if m else ""


# ================================================================
# robots.txt 確認
# ================================================================

def check_robots():
    print("robots.txt を確認中...")
    html = fetch(ROBOTS_URL, timeout=10)
    if html is None:
        print("  [警告] robots.txt 取得失敗。アクセスを中止します。")
        return False
    disallowed = []
    for line in html.splitlines():
        line = line.strip()
        if line.lower().startswith("disallow:"):
            disallowed.append(line.split(":", 1)[1].strip())
    if any(p in ("/", "/columns/") for p in disallowed):
        print(f"  [NG] /columns/ がブロックされています")
        return False
    print(f"  [OK] /columns/ はクロール許可（Disallow: {disallowed}）")
    return True


# ================================================================
# 選手名辞書
# ================================================================

def load_racer_names():
    """name_to_toban（スペース除去名→toban）、toban_to_name、家族名セットを返す"""
    name_to_toban = {}
    toban_to_name = {}
    family_names  = set()

    if not os.path.exists(RACERS_CSV):
        return name_to_toban, toban_to_name, family_names

    with open(RACERS_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            raw     = row["name"]
            stripped = raw.replace(" ", "").replace("\u3000", "")
            name_to_toban[stripped] = row["toban"]
            toban_to_name[row["toban"]] = raw
            m = re.match(r"^([\u4e00-\u9fff]{1,4})", stripped)
            if m:
                family_names.add(m.group(1))

    return name_to_toban, toban_to_name, family_names


def find_racers_in_text(text, name_to_toban):
    """テキスト中の選手名（スペース除去で照合）を返す: [(toban, name_stripped), ...]"""
    found = []
    for stripped, toban in name_to_toban.items():
        if stripped in text:
            found.append((toban, stripped))
    return found


def strip_honorifics(name):
    """さん/様/氏 等の敬称を末尾から取り除く"""
    name = re.sub(r"(?:さん|様|氏|くん|ちゃん|君)\s*$", "", name)
    return name.replace(" ", "").replace("\u3000", "").strip()


# ================================================================
# 文分割
# ================================================================

def split_sentences(paragraph):
    """段落を1文ごとに分割する（。！？で区切る）"""
    parts = re.split(r"[。！？]", paragraph)
    return [s.strip() for s in parts if s.strip()]


# ================================================================
# 核心: 1文から明示的な関係を抽出
# ================================================================

def extract_from_sentence(sentence, paragraph_racers, article_subject_racers, name_to_toban, family_names):
    """
    1文 + その段落内の全選手リスト から関係候補を抽出する。

    paragraph_racers: [(toban, stripped_name), ...]  (文を含む段落全体から検出)
    article_subject_racers: [(toban, name), ...] (ヘッドラインから検出した記事の主役)
    返り値: list of candidate dict
    """
    results = []
    sentence_racers = find_racers_in_text(sentence, name_to_toban)

    for pattern, rel_base, captured_role in RELATION_PATTERNS:
        m = pattern.search(sentence)
        if not m:
            continue

        captured_raw  = m.group(1) if m.lastindex else ""
        captured_name = strip_honorifics(captured_raw)
        captured_is_racer = captured_name in name_to_toban
        captured_toban    = name_to_toban.get(captured_name, "")

        _, non_racer_gender = ROLE_META.get(captured_role, (rel_base, None))

        # from / to の決定（match_start を渡してキーワード前後の位置を判定に使う）
        result = _assign_roles(
            captured_role, captured_name, captured_is_racer, captured_toban,
            sentence, m.start(), sentence_racers, paragraph_racers, article_subject_racers,
            non_racer_gender, name_to_toban, family_names
        )
        if result is None:
            continue

        from_toban, from_name, to_toban, to_name, name_warning = result

        # from と to が同じならスキップ
        if from_toban and from_toban == to_toban:
            continue
        if from_name and from_name == to_name:
            continue

        # 直接引用（「」内に関係キーワード）の検出
        quotes = re.findall(r"「([^」]{1,200})」", sentence)
        rel_words = {rel_base, "師匠", "弟子", "妻", "夫", "結婚", "父", "母", "兄", "姉", "弟", "妹"}
        has_direct_quote = any(
            any(kw in q for kw in rel_words)
            for q in quotes
        )

        results.append({
            "from_toban":       from_toban,
            "from_name":        from_name,
            "suggested_rel":    rel_base,
            "to_toban":         to_toban,
            "to_name":          to_name,
            "evidence_sentence": sentence[:350],
            "has_direct_quote": has_direct_quote,
            "name_warning":     name_warning,
        })

    return results


def _racer_pos(sentence, name):
    """文中での選手名の出現位置（見つからない場合は大きな値）"""
    pos = sentence.find(name)
    return pos if pos >= 0 else len(sentence)


def _assign_roles(
    role, cap_name, cap_is_racer, cap_toban,
    sentence, match_start, sentence_racers, paragraph_racers, article_subject_racers,
    non_racer_gender, name_to_toban, family_names
):
    """
    captured_role に応じて (from_toban, from_name, to_toban, to_name, name_warning) を返す。
    判定できない場合は None を返す。
    優先度: 文内（キーワード前） > 文内（キーワード後） > 段落内 > ヘッドライン
    """
    # 同じ文に出現する選手の名前セット（段落fallback での除外用）
    sentence_racer_names = {n for _, n in sentence_racers}

    # 段落内で「この文以外」に出現する選手（同一文の選手は段落fallbackで使わない）
    others_para = [(t, n) for t, n in paragraph_racers
                   if n != cap_name and n not in sentence_racer_names]
    others_subj = [(t, n) for t, n in article_subject_racers if n != cap_name]

    # 文内でキーワード（match_start）より前・後に現れる選手
    before_sent = [(t, n) for t, n in sentence_racers
                   if n != cap_name and _racer_pos(sentence, n) < match_start]
    after_sent  = [(t, n) for t, n in sentence_racers
                   if n != cap_name and _racer_pos(sentence, n) >= match_start]

    if role == "is_master":
        # captured = 師匠 (to)
        # 弟子 (from) は：①同文でキーワード前 > ②別文の段落内 > ③記事主役
        # 「同文キーワード後の選手」は別文脈の可能性が高いため使わない
        to_toban, to_name = cap_toban, cap_name
        candidates = before_sent or others_para or others_subj
        if not candidates:
            return None
        from_toban, from_name = candidates[0]
        return (from_toban, from_name, to_toban, to_name, "")

    elif role == "is_student":
        # captured = 弟子 (from)、師匠 (to) = 他の選手
        if not cap_is_racer:
            return None  # 弟子が未登録選手なら抽出しない
        from_toban, from_name = cap_toban, cap_name
        # 師匠はキーワードの後に出現しやすい（「弟子の白井 = 師匠のX」のXは後ろ）
        candidates = after_sent or before_sent or others_para or others_subj
        if not candidates:
            return None  # 師匠が特定できない
        to_toban, to_name = candidates[0]
        return (from_toban, from_name, to_toban, to_name, "")

    elif role in ("is_spouse", "is_father", "is_mother", "is_child",
                  "is_elder_bro", "is_elder_sis", "is_younger_bro", "is_younger_sis"):
        if cap_is_racer:
            # 選手同士の関係（例：ボートレーサー夫婦）
            from_cands = (before_sent + after_sent) or others_para or others_subj
            if not from_cands:
                return None
            from_toban, from_name = from_cands[0]
            return (from_toban, from_name, cap_toban, cap_name, "")
        else:
            # captured が非選手 → from = 段落 or 記事主役の選手
            all_avail = [(t, n) for t, n in (paragraph_racers or article_subject_racers)
                         if n != cap_name]
            if not all_avail:
                return None
            from_toban, from_name = all_avail[0]
            # to_name: 性別付きの表記
            gender = non_racer_gender or "不明"
            name_warning = ""
            if cap_name:
                to_name = f"一般{gender}（{cap_name}）"
                fam = re.match(r"^([\u4e00-\u9fff]{1,4})", cap_name)
                if fam and fam.group(1) in family_names:
                    name_warning = f"{cap_name}（{fam.group(1)}姓の選手が改姓した可能性あり）"
            else:
                to_name = f"一般{gender}"
            return (from_toban, from_name, "", to_name, name_warning)

    return None


# ================================================================
# 記事一覧の取得
# ================================================================

def get_article_list(max_pages=2):
    articles = []
    seen = set()

    for page in range(1, max_pages + 1):
        url = MACOUR_LIST if page == 1 else f"{MACOUR_LIST}?page={page}"
        print(f"  記事一覧 page {page}: {url}")
        html = fetch(url)
        if html is None:
            break

        links = re.findall(r"https://sp\.macour\.jp/columns/macour/(\d+)/", html)
        dates_raw = re.findall(r"(\d{4}/\d{2}/\d{2})\s+\d{2}:\d{2}", html)

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


# ================================================================
# 1記事の処理
# ================================================================

def process_article(url, date_str, html, name_to_toban, family_names):
    """
    記事 HTML から候補を抽出して返す。記事本文は保存しない。
    """
    art_date  = extract_publish_date(html) or date_str or date.today().strftime("%Y-%m-%d")
    headline  = extract_headline(html)
    paragraphs = extract_p_texts(html)

    # ヘッドラインから記事の主役選手を検出（段落に現れない場合の fallback 用）
    article_subject_racers = find_racers_in_text(headline, name_to_toban)

    all_candidates = []
    seen_keys = set()  # (from_toban, rel, to_toban, to_name) の重複排除

    for para in paragraphs:
        # 段落内の選手を一括検出
        para_racers = find_racers_in_text(para, name_to_toban)
        if not para_racers:
            continue

        # 段落を1文に分割して各文で抽出
        sentences = split_sentences(para)
        for sent in sentences:
            cands = extract_from_sentence(
                sent, para_racers, article_subject_racers, name_to_toban, family_names
            )
            for c in cands:
                key = (c["from_toban"], c["suggested_rel"], c["to_toban"], c["to_name"])
                if key in seen_keys:
                    continue
                seen_keys.add(key)

                has_quote = c["has_direct_quote"]
                conf = "A仮" if has_quote else "B仮"

                all_candidates.append({
                    "snippet":           c["evidence_sentence"][:300],
                    "evidence_sentence": c["evidence_sentence"][:300],
                    "source_url":        url,
                    "source_date":       art_date,
                    "matched_names":     [c["from_name"], c["to_name"]],
                    "suggested_rel":     c["suggested_rel"],
                    "suggested_conf":    conf,
                    "from_toban":        c["from_toban"],
                    "from_name":         c["from_name"],
                    "to_toban":          c["to_toban"],
                    "to_name":           c["to_name"],
                    "has_direct_quote":  has_quote,
                    "name_warning":      c["name_warning"],
                    "headline":          headline,
                })

    return all_candidates


# ================================================================
# メイン
# ================================================================

def main():
    dry_run   = "--dry-run" in sys.argv
    pages_arg = 2
    limit_arg = MAX_ARTICLES

    if "--pages" in sys.argv:
        idx = sys.argv.index("--pages")
        if idx + 1 < len(sys.argv):
            try:
                pages_arg = int(sys.argv[idx + 1])
            except ValueError:
                pass

    if "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        if idx + 1 < len(sys.argv):
            try:
                limit_arg = int(sys.argv[idx + 1])
            except ValueError:
                pass

    print("=" * 55)
    print("マクール コラム記事 抽出スクリプト v2")
    print("=" * 55)

    if not check_robots():
        sys.exit(1)
    time.sleep(2)

    name_to_toban, toban_to_name, family_names = load_racer_names()
    print(f"選手辞書: {len(name_to_toban)} 名\n")

    print(f"記事一覧を取得します（最大{pages_arg}ページ）...")
    articles = get_article_list(max_pages=pages_arg)
    articles = articles[:limit_arg]
    print(f"  取得記事数: {len(articles)} 件\n")

    if dry_run:
        print("【ドライランモード】記事URLのみ表示:")
        for a in articles:
            print(f"  {a['date']}  {a['url']}")
        return

    # 既存候補を読み込み（追記）
    all_candidates = []
    if os.path.exists(CANDIDATES_JSON):
        with open(CANDIDATES_JSON, encoding="utf-8") as f:
            all_candidates = json.load(f)
    existing_urls = {c["source_url"] for c in all_candidates}
    new_count = 0

    print(f"記事を巡回します（{len(articles)} 件、3〜5秒間隔）...\n")

    for i, art in enumerate(articles):
        url      = art["url"]
        date_str = art["date"]

        if url in existing_urls:
            print(f"[{i+1}/{len(articles)}] スキップ（処理済み）: {url}")
            continue

        print(f"[{i+1}/{len(articles)}] {url}")
        html = fetch(url)
        if html is None:
            print("  → 取得失敗、スキップ")
            time.sleep(random.randint(3, 5))
            continue

        cands = process_article(url, date_str, html, name_to_toban, family_names)
        print(f"  段落から候補: {len(cands)} 件", end="")
        if cands:
            for c in cands[:3]:
                print(f"\n    ✓ {c['from_name']}（{c['from_toban']}）→[{c['suggested_rel']}]→ {c['to_name']}")
                print(f"      証拠: {c['evidence_sentence'][:80]}…")
        print()

        all_candidates.extend(cands)
        existing_urls.add(url)
        new_count += len(cands)

        wait = random.randint(3, 5)
        time.sleep(wait)

    # 保存
    with open(CANDIDATES_JSON, "w", encoding="utf-8") as f:
        json.dump(all_candidates, f, ensure_ascii=False, indent=2)

    print(f"\n新規候補: {new_count} 件（累計: {len(all_candidates)} 件）")
    if new_count > 0:
        print(f"候補ファイル: {CANDIDATES_JSON}")
        print("次のステップ: python3 scripts/generate_review.py → ブラウザで確認")
    else:
        print("新しい候補はありませんでした。")


if __name__ == "__main__":
    main()
