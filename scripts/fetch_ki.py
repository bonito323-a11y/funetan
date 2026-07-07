#!/usr/bin/env python3
"""
ki（養成期）一括取得スクリプト
usage:
  python3 scripts/fetch_ki.py           # ki が空の選手を全員取得
  python3 scripts/fetch_ki.py --limit 50  # 最初の50人だけ（動作確認用）

【仕様】
  - 取得元: boatrace.jp 公式プロフィールページ（robots.txt 許可済み）
  - 2秒間隔でアクセス（相手サーバへの配慮）
  - 中断しても次回から続きを取得（ki が空の選手だけ対象）
  - 完了後に racers.csv を上書き保存
"""

import csv
import os
import re
import sys
import time
import unicodedata
from datetime import date
from urllib.request import Request, urlopen
from urllib.error import URLError

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RACERS_CSV = os.path.join(BASE_DIR, "data", "racers.csv")

PROFILE_URL = "https://boatrace.jp/owpc/pc/data/racersearch/profile?toban={toban}"
UA = "Mozilla/5.0 (compatible; funetan-patrol/1.0)"

FIELDNAMES = [
    "toban", "name", "kana", "branch", "ki", "birth",
    "grade", "status", "hometown", "hobby",
    "x_url", "insta_url", "youtube_url", "note", "checked"
]


def fetch_ki(toban):
    """公式プロフィールページから ki（登録期）の数字だけ取得する。失敗時は None。"""
    url = PROFILE_URL.format(toban=toban)
    req = Request(url, headers={"User-Agent": UA, "Accept-Language": "ja,en;q=0.9"})
    try:
        with urlopen(req, timeout=15) as resp:
            raw = resp.read()
        html = ""
        for enc in ["utf-8", "euc-jp", "shift_jis"]:
            try:
                html = raw.decode(enc)
                break
            except (UnicodeDecodeError, LookupError):
                continue
        if not html:
            html = raw.decode("utf-8", errors="replace")
    except Exception as e:
        return None, str(e)

    # dt/dd から「登録期」を探す（add_racer.py と同じロジック）
    m = re.search(r"<dt>\s*登録期\s*</dt>\s*<dd>\s*([\d]+)\s*期\s*</dd>", html)
    if m:
        return m.group(1), None

    # 存在しないページかチェック
    if "データが存在しない" in html or "404" in html[:500]:
        return None, "404 / データなし"

    return None, "登録期 未検出"


def load_racers():
    with open(RACERS_CSV, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def save_racers(rows):
    with open(RACERS_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in FIELDNAMES})


def main():
    limit = None
    if "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        if idx + 1 < len(sys.argv):
            try:
                limit = int(sys.argv[idx + 1])
            except ValueError:
                pass

    rows = load_racers()

    # ki が空の選手だけ対象
    targets = [r for r in rows if not r.get("ki", "").strip()]
    if limit:
        targets = targets[:limit]

    total = len(targets)
    print(f"ki が空の選手: {total} 人")
    if total == 0:
        print("全員 ki 取得済みです。")
        return

    if limit:
        print(f"（--limit {limit} 指定のため最初の {limit} 人のみ取得）")

    print(f"2秒間隔でアクセスします（合計約 {total * 2 // 60} 分）\n")

    # toban → row のマップ（更新用）
    row_map = {r["toban"]: r for r in rows}

    ok_count   = 0
    fail_count = 0

    for i, row in enumerate(targets):
        toban = row["toban"]
        name  = row["name"]
        print(f"[{i+1}/{total}] {name}（{toban}）", end=" ", flush=True)

        ki, err = fetch_ki(toban)

        if ki:
            row_map[toban]["ki"] = ki
            ok_count += 1
            print(f"→ {ki}期 ✓")
        else:
            fail_count += 1
            print(f"→ 取得失敗（{err}）")

        # 10件ごとに中間保存（中断しても損失を最小化）
        if (i + 1) % 10 == 0:
            save_racers(list(row_map.values()))
            print(f"  ── 中間保存: {i+1}/{total} 件処理済み ──")

        time.sleep(2)

    # 最終保存
    save_racers(list(row_map.values()))

    print(f"\n完了: 成功 {ok_count} 件 / 失敗 {fail_count} 件")
    print(f"racers.csv を更新しました。")
    if ok_count > 0:
        print("次のステップ: python3 scripts/generate_racer_page.py  ← 全選手ページを再生成")


if __name__ == "__main__":
    main()
