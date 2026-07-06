#!/usr/bin/env python3
"""
取材テンプレ：関係情報を1件ずつ対話入力して relations.csv に追記するスクリプト
usage: python scripts/add_relation.py

ダシオさんが取材・調査して確認した情報を1件ずつ登録するための対話ツール。
"""

import csv
import os
from datetime import date

BASE_DIR      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RELATIONS_CSV = os.path.join(BASE_DIR, "data", "relations.csv")
RACERS_CSV    = os.path.join(BASE_DIR, "data", "racers.csv")

FIELDNAMES = [
    "id", "from_toban", "rel_type", "to_toban", "to_name",
    "confidence", "source_url", "source_date", "checked", "memo"
]

REL_TYPES = [
    "父", "母", "子", "兄", "姉", "弟", "妹",
    "配偶者", "元配偶者", "師匠", "弟子", "親族",
    "友人", "同期", "仲良し",
]


def load_racers():
    racers = {}
    with open(RACERS_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            racers[row["toban"]] = row
    return racers


def load_existing():
    if not os.path.exists(RELATIONS_CSV):
        return []
    with open(RELATIONS_CSV, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def next_id(existing):
    ids = [int(r["id"].replace("R", "")) for r in existing if r["id"].startswith("R") and r["id"][1:].isdigit()]
    return max(ids, default=0) + 1


def ask(prompt, required=True, default=""):
    while True:
        val = input(prompt).strip()
        if not val:
            if default:
                return default
            if not required:
                return ""
            print("  ← 必須項目です。入力してください。")
        else:
            return val


def ask_choice(prompt, choices, default=""):
    print(prompt)
    for i, c in enumerate(choices, 1):
        mark = "◀" if c == default else ""
        print(f"  {i:2d}. {c} {mark}")
    while True:
        val = input("番号を入力（Enterでデフォルト）: ").strip()
        if not val and default:
            return default
        if val.isdigit() and 1 <= int(val) <= len(choices):
            return choices[int(val) - 1]
        print("  ← 有効な番号を入力してください。")


def main():
    racers = load_racers()
    today = date.today().strftime("%Y-%m-%d")

    print("=" * 50)
    print("  舟☆探 取材テンプレ ── 関係情報 入力")
    print("=" * 50)
    print("Ctrl+C で中断できます。\n")

    while True:
        existing = load_existing()
        next_num = next_id(existing)

        print(f"\n── 新規入力 (ID予定: R{next_num:04d}) ──────────────")

        # From 選手
        from_toban = ask("登録番号（from）: ")
        from_racer = racers.get(from_toban)
        if from_racer:
            print(f"  → {from_racer['name']}（{from_racer['branch']}支部・{from_racer['grade']}）")
        else:
            print(f"  [注意] {from_toban} は racers.csv に見つかりません。続けますか？")
            if input("続ける？ [y/N]: ").strip().lower() != "y":
                continue

        # 関係タイプ
        rel_type = ask_choice("\n関係タイプを選んでください:", REL_TYPES)

        # To 選手
        to_toban = ask("登録番号（to）※一般人なら空欄でOK: ", required=False)
        if to_toban:
            to_racer = racers.get(to_toban)
            if to_racer:
                print(f"  → {to_racer['name']}（{to_racer['branch']}支部・{to_racer['grade']}）")
                to_name = to_racer["name"]
            else:
                print(f"  [注意] {to_toban} は racers.csv に見つかりません。")
                to_name = ask("相手の名前（手動入力）: ", required=False)
        else:
            to_name = ask("相手の名前（例: 一般女性・田口節子）: ", required=False)

        # 確度
        print("\n確度:")
        print("  A = ◎ 本人が公表（SNS・インタビュー等）")
        print("  B = ○ 信頼できる媒体の報道")
        print("  C = △ 噂・未確認（サイト非表示、DBのみ保持）")
        confidence = ask("確度 [A/B/C]: ")
        if confidence.upper() not in ("A", "B", "C"):
            print("  無効な値です。B にします。")
            confidence = "B"
        else:
            confidence = confidence.upper()

        # 出典URL
        source_url = ask("出典URL（必須。信頼できる情報源のURL）: ")

        # 出典日付
        source_date = ask(f"出典日付 [YYYY-MM-DD、Enterで今日 ({today})]: ",
                          required=False, default=today)

        # メモ
        memo = ask("メモ（任意）: ", required=False)

        # 確認
        print("\n─── 入力内容 ────────────────────────────")
        print(f"  from  : {from_toban} {racers.get(from_toban, {}).get('name', '?')}")
        print(f"  関係  : {rel_type}")
        print(f"  to    : {to_toban or '（登録なし）'} {to_name}")
        print(f"  確度  : {confidence}")
        print(f"  出典  : {source_url}")
        print(f"  日付  : {source_date}")
        print(f"  メモ  : {memo}")
        print("─────────────────────────────────────────")

        if input("この内容で追記しますか？ [y/N]: ").strip().lower() != "y":
            print("やり直します。")
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

        all_rows = existing + [new_row]
        with open(RELATIONS_CSV, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            for r in all_rows:
                writer.writerow({k: r.get(k, "") for k in FIELDNAMES})

        print(f"[完了] R{next_num:04d} を追記しました。")

        if input("\n続けてもう1件入力しますか？ [y/N]: ").strip().lower() != "y":
            print("\n入力を終了します。")
            print("ページを再生成するには:")
            print("  python scripts/generate_racer_page.py")
            print("  python scripts/generate_map.py")
            print("  python scripts/generate_index.py")
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n中断しました。")
