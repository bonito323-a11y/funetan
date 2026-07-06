#!/usr/bin/env python3
"""
監視サイト巡回スクリプト
usage:
  python scripts/patrol.py          # 初回→ベースライン保存のみ。2回目以降→差分を候補に出力
  python scripts/patrol.py --force-baseline  # 強制的にベースラインを上書き保存

【方針】
  - 初回は「ベースライン保存のみ」。既存サイトのデータを丸ごと取り込まない
  - 2回目以降は前回保存との差分テキストだけを候補として抽出
  - 1サイトごとに2秒待機（相手サーバへの配慮）
  - クロール不可サイト（Instagram・Googleアラート・YouTube）はスキップ
"""

import csv
import json
import os
import re
import sys
import time
import unicodedata
from datetime import date
from html.parser import HTMLParser
from urllib.request import Request, urlopen
from urllib.error import URLError

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(BASE_DIR, "scripts", "cache", "sites")
RACERS_CSV = os.path.join(BASE_DIR, "data", "racers.csv")
SITES_CSV  = os.path.join(BASE_DIR, "data", "監視サイトリスト.csv")
CANDIDATES_JSON = os.path.join(BASE_DIR, "scripts", "cache", "candidates.json")
META_JSON = os.path.join(BASE_DIR, "scripts", "cache", "patrol_meta.json")

os.makedirs(CACHE_DIR, exist_ok=True)

UA = "Mozilla/5.0 (compatible; funetan-patrol/1.0)"

# クロール対象外キーワード（URLに含まれる場合スキップ）
SKIP_DOMAINS = ["instagram.com", "google.com", "youtube.com", "@BOATRACE_JLC"]

# 関係キーワード
REL_KEYWORDS = [
    "師匠", "弟子", "師弟", "兄", "姉", "弟", "妹",
    "配偶者", "夫婦", "結婚", "入籍", "夫", "妻",
    "親子", "父", "母", "子供", "兄弟", "家族", "血縁",
    "引退", "登録抹消",
]

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


def html_to_text(html: str) -> str:
    parser = TextExtractor()
    parser.feed(html)
    lines = []
    for t in parser.texts:
        t = unicodedata.normalize("NFKC", t)
        t = re.sub(r"\s+", " ", t).strip()
        if t:
            lines.append(t)
    return "\n".join(lines)


def fetch_html(url: str) -> str | None:
    req = Request(url, headers={
        "User-Agent": UA,
        "Accept-Language": "ja,en;q=0.8",
        "Accept": "text/html",
    })
    try:
        with urlopen(req, timeout=20) as resp:
            raw = resp.read()
        for enc in ["utf-8", "euc-jp", "shift_jis"]:
            try:
                return raw.decode(enc)
            except (UnicodeDecodeError, LookupError):
                continue
        return raw.decode("utf-8", errors="replace")
    except URLError as e:
        print(f"  [通信エラー] {e}")
        return None


# ---- 選手名辞書の構築 ----

def load_racer_names() -> dict:
    """toban → name のマップ + 名前 → toban の逆引き"""
    name_to_toban = {}
    toban_to_name = {}
    if not os.path.exists(RACERS_CSV):
        return name_to_toban, toban_to_name
    with open(RACERS_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name_to_toban[row["name"]] = row["toban"]
            toban_to_name[row["toban"]] = row["name"]
    return name_to_toban, toban_to_name


# ---- 差分から候補を抽出 ----

def extract_candidates(diff_lines: list[str], url: str,
                        name_to_toban: dict) -> list[dict]:
    """
    差分テキスト行から、関係キーワード + 選手名が含まれる行を候補として返す。
    既存サイトの全データを取り込まず、あくまで「新規追加された行」だけ対象。
    """
    candidates = []
    today = date.today().strftime("%Y-%m-%d")

    for line in diff_lines:
        # 関係キーワードを含むか
        has_kw = any(kw in line for kw in REL_KEYWORDS)
        if not has_kw:
            continue

        # 選手名が含まれるか（部分一致・複数名）
        matched_names = [n for n in name_to_toban if n in line]
        if not matched_names:
            continue

        # 候補として登録（関係タイプ・確度は後で人間が編集）
        candidates.append({
            "snippet": line[:300],
            "source_url": url,
            "source_date": today,
            "matched_names": matched_names,
            "suggested_rel": guess_rel_type(line),
            "suggested_conf": "B",  # 初期値：メディア報道扱い
            "from_toban": name_to_toban.get(matched_names[0], "") if matched_names else "",
            "from_name": matched_names[0] if matched_names else "",
            "to_toban": name_to_toban.get(matched_names[1], "") if len(matched_names) > 1 else "",
            "to_name": matched_names[1] if len(matched_names) > 1 else "",
        })

    return candidates


def guess_rel_type(text: str) -> str:
    """テキストから関係タイプを推測する（あくまで初期値）"""
    if any(k in text for k in ["夫婦", "結婚", "入籍", "配偶者", "妻", "夫"]):
        return "配偶者"
    if any(k in text for k in ["師匠", "師弟"]) and "弟子" not in text:
        return "師匠"
    if "弟子" in text:
        return "弟子"
    if any(k in text for k in ["兄", "弟", "姉", "妹", "兄弟", "兄妹", "姉弟"]):
        return "兄弟"  # 仮。人間が修正
    if any(k in text for k in ["父", "母", "親子", "子供"]):
        return "親族"
    if "引退" in text or "登録抹消" in text:
        return "_引退情報"  # relations.csvではなく racers.csv の status 更新に使う
    return "友人"


# ---- サイト ID 生成 ----

def site_id(url: str) -> str:
    return re.sub(r"[^\w]", "_", url)[:60]


# ---- メタ情報の読み書き ----

def load_meta() -> dict:
    if os.path.exists(META_JSON):
        with open(META_JSON, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_meta(meta: dict):
    with open(META_JSON, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


# ---- メイン ----

def main():
    force_baseline = "--force-baseline" in sys.argv

    # サイトリスト読み込み
    sites = []
    with open(SITES_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            url = row.get("URL", "").strip()
            priority = row.get("優先度", "").strip()
            if not url or priority == "低":
                continue
            if any(d in url for d in SKIP_DOMAINS):
                print(f"  [スキップ] クロール不可: {url}")
                continue
            sites.append(row)

    print(f"巡回対象: {len(sites)} サイト\n")

    meta = load_meta()
    is_first_run = not meta  # メタ情報がなければ初回

    if is_first_run or force_baseline:
        print("=" * 50)
        print("【初回巡回 / ベースライン保存モード】")
        print("既存データは候補として出力しません。")
        print("=" * 50)

    all_candidates = []
    today = date.today().strftime("%Y-%m-%d")
    name_to_toban, _ = load_racer_names()

    for i, site in enumerate(sites):
        url  = site["URL"].strip()
        name = site["サイト名"].strip()
        sid  = site_id(url)
        base_path = os.path.join(CACHE_DIR, f"{sid}_base.txt")

        print(f"[{i+1}/{len(sites)}] {name}")
        print(f"  URL: {url}")

        html = fetch_html(url)
        if html is None:
            print("  → 取得失敗、スキップ")
            time.sleep(2)
            continue

        new_text = html_to_text(html)
        new_lines = set(new_text.splitlines())

        if is_first_run or force_baseline or not os.path.exists(base_path):
            # ベースライン保存
            with open(base_path, "w", encoding="utf-8") as f:
                f.write(new_text)
            meta[sid] = {"url": url, "name": name, "saved": today}
            print(f"  → ベースライン保存完了（{len(new_lines)} 行）")
        else:
            # 差分比較
            with open(base_path, encoding="utf-8") as f:
                base_lines = set(f.read().splitlines())

            added = [l for l in new_lines - base_lines if l.strip()]
            print(f"  → 差分: +{len(added)} 行")

            if added:
                cands = extract_candidates(added, url, name_to_toban)
                print(f"  → 候補: {len(cands)} 件")
                all_candidates.extend(cands)

            # ベースラインを最新で更新
            with open(base_path, "w", encoding="utf-8") as f:
                f.write(new_text)
            meta[sid]["saved"] = today

        time.sleep(2)

    save_meta(meta)

    if is_first_run or force_baseline:
        print(f"\n✅ ベースライン保存完了（{len(meta)} サイト）")
        print("次回の巡回から差分が候補として出力されます。")
        return

    # 候補を保存
    with open(CANDIDATES_JSON, "w", encoding="utf-8") as f:
        json.dump(all_candidates, f, ensure_ascii=False, indent=2)

    print(f"\n候補合計: {len(all_candidates)} 件")
    if all_candidates:
        print(f"候補ファイル: {CANDIDATES_JSON}")
        print("次のステップ: python scripts/generate_review.py → ブラウザで確認")
    else:
        print("新しい候補はありませんでした。")


if __name__ == "__main__":
    main()
