#!/usr/bin/env python3
"""
選手追加スクリプト
usage:
  python scripts/add_racer.py <toban> [期待する名前]

例:
  python scripts/add_racer.py 4444
  python scripts/add_racer.py 4444 桐生順平

やること:
  1. boatrace.jp 公式プロフィールページを取得（1秒待機）
  2. 氏名・よみがな・支部・期・生年月日・級別・出身地を解析
  3. 名前照合チェック（引数で期待名を渡した場合）
  4. 内容を表示して確認を求める
  5. 確認後に racers.csv へ追記
"""

import csv
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
RACERS_CSV = os.path.join(BASE_DIR, "data", "racers.csv")

PROFILE_URL = "https://boatrace.jp/owpc/pc/data/racersearch/profile?toban={toban}"
UA = "Mozilla/5.0 (compatible; funetan-bot/1.0; +research)"

# ---- HTMLパーサー ----

class ProfileParser(HTMLParser):
    """boatrace.jp プロフィールページから必要項目を抽出する。

    ページ構造（実測）:
      <p class="racer1_bodyName">桐生　　順平</p>
      <p class="racer1_bodyKana">キリュウ　ジュンペイ</p>
      <dl>
        <dt>登録番号</dt><dd>4444</dd>
        <dt>生年月日</dt><dd>1986/10/07</dd>
        <dt>支部</dt><dd>埼玉</dd>
        <dt>出身地</dt><dd>福島県</dd>
        <dt>登録期</dt><dd>100期</dd>
        <dt>級別</dt><dd>A1級</dd>
      </dl>
    """

    def __init__(self):
        super().__init__()
        self.data = {}
        self._cur_class = ""
        self._in_target_p = False
        self._p_buf = ""
        self._in_dt = False
        self._in_dd = False
        self._dt_buf = ""
        self._last_dt = ""
        self._dd_buf = ""
        self._error = False

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        cls = attr_dict.get("class", "")

        if tag == "p" and ("racer1_bodyName" in cls or "racer1_bodyKana" in cls):
            self._in_target_p = True
            self._cur_class = cls
            self._p_buf = ""

        if tag == "dt":
            self._in_dt = True
            self._dt_buf = ""

        if tag == "dd":
            self._in_dd = True
            self._dd_buf = ""
            self._last_dt = self._dt_buf.strip()

    def handle_endtag(self, tag):
        if tag == "p" and self._in_target_p:
            self._in_target_p = False
            raw = unicodedata.normalize("NFKC", self._p_buf)
            raw = re.sub(r"\s+", "", raw).strip()
            if "racer1_bodyName" in self._cur_class and raw:
                self.data["name"] = raw
            elif "racer1_bodyKana" in self._cur_class and raw:
                self.data["kana"] = raw

        if tag == "dt":
            self._in_dt = False

        if tag == "dd":
            self._in_dd = False
            key = self._last_dt
            val = unicodedata.normalize("NFKC", self._dd_buf).strip()
            self._store(key, val)

    def handle_data(self, data):
        if self._in_target_p:
            self._p_buf += data
        if self._in_dt:
            self._dt_buf += data
        if self._in_dd:
            self._dd_buf += data
        if "データが存在しない" in data or "ページを表示できません" in data:
            self._error = True

    def _store(self, key, value):
        if "登録番号" in key:
            self.data["toban_check"] = value
        elif "生年月日" in key:
            self.data["birth"] = value.replace("/", "-")
        elif key == "支部":
            self.data["branch"] = value
        elif "出身地" in key:
            self.data["hometown"] = value
        elif "登録期" in key:
            self.data["ki"] = re.sub(r"[^\d]", "", value)
        elif "級別" in key:
            self.data["grade"] = re.sub(r"級$", "", value)


def katakana_to_hiragana(text):
    result = []
    for ch in text:
        cp = ord(ch)
        if 0x30A1 <= cp <= 0x30F6:
            result.append(chr(cp - 0x60))
        else:
            result.append(ch)
    return "".join(result)


def fetch_profile(toban):
    url = PROFILE_URL.format(toban=toban)
    req = Request(url, headers={"User-Agent": UA, "Accept-Language": "ja,en;q=0.9"})
    try:
        with urlopen(req, timeout=15) as resp:
            charset = "utf-8"
            ct = resp.headers.get("Content-Type", "")
            m = re.search(r"charset=([\w-]+)", ct)
            if m:
                charset = m.group(1)
            html_bytes = resp.read()
            # charset が EUC-JP 系の場合は変換
            for enc in [charset, "utf-8", "euc-jp", "shift_jis"]:
                try:
                    return html_bytes.decode(enc)
                except (UnicodeDecodeError, LookupError):
                    continue
            return html_bytes.decode("utf-8", errors="replace")
    except URLError as e:
        print(f"[エラー] 通信失敗: {e}")
        return None


def normalize_name(name):
    """比較用：全角スペース・スペース・記号を除去して正規化"""
    return re.sub(r"[\s　\u3000]+", "", unicodedata.normalize("NFKC", name))


def load_existing_tobans():
    tobans = set()
    if not os.path.exists(RACERS_CSV):
        return tobans
    with open(RACERS_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            tobans.add(row["toban"])
    return tobans


def append_racer(row_dict):
    """racers.csv に1行追記する"""
    fieldnames = [
        "toban", "name", "kana", "branch", "ki", "birth",
        "grade", "status", "hometown", "hobby",
        "x_url", "insta_url", "youtube_url", "note", "checked"
    ]
    with open(RACERS_CSV, encoding="utf-8", newline="") as f:
        existing = list(csv.DictReader(f))

    existing.append(row_dict)
    existing.sort(key=lambda r: int(r["toban"]) if r["toban"].isdigit() else 0)

    with open(RACERS_CSV, encoding="utf-8", newline="") as f:
        pass  # check writable

    with open(RACERS_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in existing:
            writer.writerow({k: r.get(k, "") for k in fieldnames})


# ---- メイン ----

def main():
    if len(sys.argv) < 2:
        print("使い方: python scripts/add_racer.py <登録番号> [期待する名前]")
        print("例:     python scripts/add_racer.py 4444")
        print("例:     python scripts/add_racer.py 4444 桐生順平")
        sys.exit(1)

    toban = sys.argv[1].strip()
    expected_name = sys.argv[2].strip() if len(sys.argv) >= 3 else None

    # 重複チェック
    existing = load_existing_tobans()
    if toban in existing:
        print(f"[情報] 登録番号 {toban} は既に racers.csv に存在します。")
        sys.exit(0)

    print(f"公式プロフィールを取得中: toban={toban} …（1秒待機）")
    time.sleep(1)

    html = fetch_profile(toban)
    if html is None:
        sys.exit(1)

    parser = ProfileParser()
    parser.feed(html)

    if parser._error:
        print(f"[エラー] 登録番号 {toban} のデータが公式サイトに存在しません。")
        sys.exit(1)

    p = parser.data
    if "name" not in p:
        print("[エラー] 選手名を取得できませんでした。HTML構造が変わった可能性があります。")
        print("        手動で racers.csv に追記してください。")
        sys.exit(1)

    # よみがなをひらがなに変換（カタカナ→ひらがな）
    kana_raw = p.get("kana", "")
    kana = katakana_to_hiragana(kana_raw) if kana_raw else ""

    # 名前照合チェック
    if expected_name:
        fetched_norm  = normalize_name(p["name"])
        expected_norm = normalize_name(expected_name)
        if fetched_norm != expected_norm:
            print(f"[警告] 名前が一致しません！")
            print(f"  渡された名前: {expected_name}（正規化: {expected_norm}）")
            print(f"  取得した名前: {p['name']}（正規化: {fetched_norm}）")
            print("  登録番号が正しいか確認してください。")
            ans = input("それでも続けますか？ [y/N]: ").strip().lower()
            if ans != "y":
                print("中止しました。")
                sys.exit(0)
        else:
            print(f"[OK] 名前照合: {expected_name} ✓")

    today = date.today().strftime("%Y-%m-%d")

    new_row = {
        "toban":    toban,
        "name":     p.get("name", ""),
        "kana":     kana,
        "branch":   p.get("branch", ""),
        "ki":       p.get("ki", ""),
        "birth":    p.get("birth", ""),
        "grade":    p.get("grade", ""),
        "status":   "active",
        "hometown": p.get("hometown", ""),
        "hobby":    "",          # 公式サイトに掲載なし → 手動で追記
        "x_url":    "",
        "insta_url": "",
        "youtube_url": "",
        "note":     "",
        "checked":  today,
    }

    print("\n─── 取得結果 ───────────────────")
    print(f"  登録番号: {new_row['toban']}")
    print(f"  氏名    : {new_row['name']}")
    print(f"  よみがな: {new_row['kana']}")
    print(f"  支部    : {new_row['branch']}")
    print(f"  期別    : {new_row['ki']}期")
    print(f"  生年月日: {new_row['birth']}")
    print(f"  級別    : {new_row['grade']}")
    print(f"  出身地  : {new_row['hometown']}")
    print(f"  現況    : {new_row['status']}（引退の場合は後で手動修正）")
    print(f"  趣味    : （公式サイト非掲載・後で手動追記）")
    print("────────────────────────────────\n")

    ans = input("この内容で racers.csv に追記しますか？ [y/N]: ").strip().lower()
    if ans != "y":
        print("中止しました。追記はされていません。")
        sys.exit(0)

    append_racer(new_row)
    print(f"[完了] racers.csv に {new_row['name']}（{toban}）を追記しました。")
    print("次のステップ:")
    print("  1. 趣味・SNS URL・引退の有無を racers.csv で手動確認・修正")
    print("  2. python scripts/generate_racer_page.py " + toban + "  ← ページ再生成")
    print("  3. python scripts/generate_map.py             ← 関係マップ更新")
    print("  4. python scripts/generate_index.py           ← トップページ更新")


if __name__ == "__main__":
    main()
