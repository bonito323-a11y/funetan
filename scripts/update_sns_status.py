#!/usr/bin/env python3
"""
SNS確認結果をprofiles.csvに反映するスクリプト
usage: python scripts/update_sns_status.py ~/Downloads/sns_review_YYYY-MM-DD.json

- OK → note欄の「要本人確認」を「確認済み」に変更
- NG → そのSNSフィールドを空欄にし、noteに「(フィールド名:NG削除)」を追記
"""
import csv
import json
import os
import sys
from datetime import date

BASE_DIR     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROFILES_CSV = os.path.join(BASE_DIR, "data", "profiles.csv")

def main():
    if len(sys.argv) < 2:
        print("使い方: python scripts/update_sns_status.py <JSONファイルパス>")
        sys.exit(1)

    json_path = os.path.expanduser(sys.argv[1])
    if not os.path.exists(json_path):
        print(f"[エラー] ファイルが見つかりません: {json_path}")
        sys.exit(1)

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    results     = data.get("results", {})
    reviewed_at = data.get("reviewed_at", str(date.today()))

    # profiles.csv 読み込み
    rows = []
    with open(PROFILES_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)

    changed = 0
    for row in rows:
        toban = row["toban"]
        if toban not in results:
            continue

        verdicts = results[toban]
        note = row.get("note", "") or ""
        ng_fields = []

        for field, verdict in verdicts.items():
            if verdict == "ok":
                # note内の「要本人確認」を「確認済み」に置換
                note = note.replace("要本人確認", "確認済み")
            elif verdict == "ng":
                # SNSフィールドを空欄に
                if row.get(field):
                    ng_fields.append(f"{field}={row[field]}")
                    row[field] = ""

        if ng_fields:
            note += f" NG削除({reviewed_at}):{','.join(ng_fields)}"

        row["note"] = note.strip()
        changed += 1
        print(f"[更新] {toban} {row.get('name','')} → {verdicts}")

    # profiles.csv 書き直し
    with open(PROFILES_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n{changed} 件を更新しました → {PROFILES_CSV}")
    print("次のステップ: python scripts/generate_racer_page.py でページを再生成してください")

if __name__ == "__main__":
    main()
