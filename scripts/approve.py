#!/usr/bin/env python3
"""
承認済み関係情報を relations.csv に追記するスクリプト
usage: python scripts/approve.py ~/Downloads/approved.json

ブラウザの承認UIでダウンロードした approved.json を読み込み、
重複チェック後に relations.csv へ追記する。
"""

import csv
import json
import os
import sys
from datetime import date

BASE_DIR      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RELATIONS_CSV = os.path.join(BASE_DIR, "data", "relations.csv")

FIELDNAMES = [
    "id", "from_toban", "rel_type", "to_toban", "to_name",
    "confidence", "source_url", "source_date", "checked", "memo"
]

VALID_REL_TYPES = {
    "父", "母", "子", "兄", "姉", "弟", "妹",
    "配偶者", "元配偶者", "師匠", "弟子", "親族",
    "友人", "同期", "仲良し",
}


def load_existing():
    rows = []
    if not os.path.exists(RELATIONS_CSV):
        return rows
    with open(RELATIONS_CSV, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return rows


def next_id(existing):
    ids = [int(r["id"].replace("R", "")) for r in existing if r["id"].startswith("R") and r["id"][1:].isdigit()]
    return max(ids, default=0) + 1


def main():
    if len(sys.argv) < 2:
        print("使い方: python scripts/approve.py <approved.jsonのパス>")
        print("例:     python scripts/approve.py ~/Downloads/approved.json")
        sys.exit(1)

    json_path = os.path.expanduser(sys.argv[1])
    if not os.path.exists(json_path):
        print(f"[エラー] ファイルが見つかりません: {json_path}")
        sys.exit(1)

    with open(json_path, encoding="utf-8") as f:
        approved = json.load(f)

    if not approved:
        print("[情報] 承認済み項目がありません。")
        sys.exit(0)

    existing = load_existing()
    today = date.today().strftime("%Y-%m-%d")
    next_num = next_id(existing)

    # 既存の (from_toban, rel_type, to_toban) の組合せ
    existing_keys = {
        (r["from_toban"], r["rel_type"], r["to_toban"])
        for r in existing
    }

    added = []
    skipped = []
    errors = []

    for item in approved:
        from_toban  = item.get("from_toban", "").strip()
        rel_type    = item.get("rel_type", "").strip()
        to_toban    = item.get("to_toban", "").strip()
        to_name     = item.get("to_name", "").strip()
        confidence  = item.get("confidence", "B").strip()
        source_url  = item.get("source_url", "").strip()
        source_date = item.get("source_date", "").strip()
        memo        = item.get("memo", "").strip()

        # バリデーション
        if not from_toban:
            errors.append(f"from_toban が空: {item}")
            continue
        if rel_type not in VALID_REL_TYPES:
            errors.append(f"無効な rel_type '{rel_type}': {item}")
            continue
        if not source_url:
            errors.append(f"source_url が空（出典必須）: {item}")
            continue
        if confidence not in ("A", "B"):
            errors.append(f"無効な confidence '{confidence}': {item}")
            continue

        key = (from_toban, rel_type, to_toban)
        if key in existing_keys:
            skipped.append(f"{from_toban} -{rel_type}→ {to_toban or to_name} （重複のためスキップ）")
            continue

        new_row = {
            "id":          f"R{next_num:04d}",
            "from_toban":  from_toban,
            "rel_type":    rel_type,
            "to_toban":    to_toban,
            "to_name":     to_name,
            "confidence":  confidence,
            "source_url":  source_url,
            "source_date": source_date,
            "checked":     today,
            "memo":        memo,
        }
        added.append(new_row)
        existing_keys.add(key)
        next_num += 1

    # 結果表示
    if errors:
        print(f"\n[エラー] {len(errors)} 件は追記できません：")
        for e in errors:
            print(f"  × {e}")

    if skipped:
        print(f"\n[重複スキップ] {len(skipped)} 件：")
        for s in skipped:
            print(f"  → {s}")

    if not added:
        print("\n追記できる項目がありませんでした。")
        sys.exit(0)

    print(f"\n追記予定: {len(added)} 件")
    for r in added:
        print(f"  {r['id']}: {r['from_toban']} -{r['rel_type']}→ {r['to_toban'] or r['to_name']}  [{r['confidence']}]")

    ans = input("\nrelations.csv に追記しますか？ [y/N]: ").strip().lower()
    if ans != "y":
        print("中止しました。")
        sys.exit(0)

    all_rows = existing + added
    with open(RELATIONS_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for r in all_rows:
            writer.writerow({k: r.get(k, "") for k in FIELDNAMES})

    print(f"[完了] {len(added)} 件を relations.csv に追記しました。")
    print("\n次のステップ（サイト再生成）:")
    print("  python scripts/generate_racer_page.py")
    print("  python scripts/generate_map.py")
    print("  python scripts/generate_index.py")


if __name__ == "__main__":
    main()
