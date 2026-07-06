#!/usr/bin/env python3
"""
ファン手帳データ一括インポートスクリプト
usage: python scripts/import_fanzine.py <fan????.txt>

【フィールドマップ（実測・Shift-JIS固定長）】
  0:4    登番
  4:20   名前漢字（16bytes, 全角）
  20:35  名前カナ（15bytes, 半角カナ）
  35:39  支部（4bytes）
  39:41  級別（A1/A2/B1/B2）
  41:42  年号（S=昭和/H=平成）
  42:48  生年月日（YYMMDD）
  48:49  性別（1=男/2=女）
  ...成績データ...
  410:416 出身地（6bytes, 全角）

【注意】
  - ファン手帳ファイルの再配布禁止
  - 成績データはサイトに掲載しない
  - ki（登録期）はこのデータから取得できないため空欄→後日 add_racer.py で補完可
"""

import csv
import os
import re
import sys
import unicodedata

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RACERS_CSV = os.path.join(BASE_DIR, "data", "racers.csv")

FIELDNAMES = [
    "toban", "name", "kana", "branch", "ki", "birth",
    "grade", "status", "hometown", "hobby",
    "x_url", "insta_url", "youtube_url", "note", "checked"
]

# ---- 変換ユーティリティ ----

# 半角カナ → 全角カナ 変換テーブル（濁点・半濁点の合成含む）
_HALF_TO_FULL = {
    '\uff66': '\u30f2', '\uff67': '\u30a1', '\uff68': '\u30a3',
    '\uff69': '\u30a5', '\uff6a': '\u30a7', '\uff6b': '\u30a9',
    '\uff6c': '\u30e3', '\uff6d': '\u30e5', '\uff6e': '\u30e7',
    '\uff6f': '\u30c3', '\uff70': '\u30fc',
    '\uff71': '\u30a2', '\uff72': '\u30a4', '\uff73': '\u30a6',
    '\uff74': '\u30a8', '\uff75': '\u30aa',
    '\uff76': '\u30ab', '\uff77': '\u30ad', '\uff78': '\u30af',
    '\uff79': '\u30b1', '\uff7a': '\u30b3',
    '\uff7b': '\u30b5', '\uff7c': '\u30b7', '\uff7d': '\u30b9',
    '\uff7e': '\u30bb', '\uff7f': '\u30bd',
    '\uff80': '\u30bf', '\uff81': '\u30c1', '\uff82': '\u30c4',
    '\uff83': '\u30c6', '\uff84': '\u30c8',
    '\uff85': '\u30ca', '\uff86': '\u30cb', '\uff87': '\u30cc',
    '\uff88': '\u30cd', '\uff89': '\u30ce',
    '\uff8a': '\u30cf', '\uff8b': '\u30d2', '\uff8c': '\u30d5',
    '\uff8d': '\u30d8', '\uff8e': '\u30db',
    '\uff8f': '\u30de', '\uff90': '\u30df', '\uff91': '\u30e0',
    '\uff92': '\u30e1', '\uff93': '\u30e2',
    '\uff94': '\u30e4', '\uff95': '\u30e6', '\uff96': '\u30e8',
    '\uff97': '\u30e9', '\uff98': '\u30ea', '\uff99': '\u30eb',
    '\uff9a': '\u30ec', '\uff9b': '\u30ed',
    '\uff9c': '\u30ef', '\uff9d': '\u30f3',
    '\uff9e': '\u309b',  # 濁点
    '\uff9f': '\u309c',  # 半濁点
}
_DAKUTEN_MAP = {
    '\u30ab': '\u30ac', '\u30ad': '\u30ae', '\u30af': '\u30b0',
    '\u30b1': '\u30b2', '\u30b3': '\u30b4',
    '\u30b5': '\u30b6', '\u30b7': '\u30b8', '\u30b9': '\u30ba',
    '\u30bb': '\u30bc', '\u30bd': '\u30be',
    '\u30bf': '\u30c0', '\u30c1': '\u30c2', '\u30c4': '\u30c5',
    '\u30c6': '\u30c7', '\u30c8': '\u30c9',
    '\u30cf': '\u30d0', '\u30d2': '\u30d3', '\u30d5': '\u30d6',
    '\u30d8': '\u30d9', '\u30db': '\u30dc',
    '\u30a6': '\u30f4',  # ヴ
}
_HANDAKUTEN_MAP = {
    '\u30cf': '\u30d1', '\u30d2': '\u30d4', '\u30d5': '\u30d7',
    '\u30d8': '\u30da', '\u30db': '\u30dd',
}

def half_kana_to_full(text):
    """半角カナ文字列 → 全角カナ（濁点合成）"""
    result = []
    i = 0
    while i < len(text):
        ch = text[i]
        full = _HALF_TO_FULL.get(ch, ch)
        if i + 1 < len(text):
            nxt = text[i + 1]
            if nxt == '\uff9e':  # 濁点
                if full in _DAKUTEN_MAP:
                    result.append(_DAKUTEN_MAP[full])
                    i += 2
                    continue
            elif nxt == '\uff9f':  # 半濁点
                if full in _HANDAKUTEN_MAP:
                    result.append(_HANDAKUTEN_MAP[full])
                    i += 2
                    continue
        result.append(full)
        i += 1
    return ''.join(result)

def katakana_to_hiragana(text):
    """全角カタカナ → ひらがな"""
    result = []
    for ch in text:
        cp = ord(ch)
        if 0x30A1 <= cp <= 0x30F6:
            result.append(chr(cp - 0x60))
        else:
            result.append(ch)
    return ''.join(result)

def parse_kana(raw_bytes):
    """半角カナバイト列 → ひらがな（スペース除去）"""
    try:
        text = raw_bytes.decode("shift_jis")
    except Exception:
        return ""
    text = unicodedata.normalize("NFKC", text)  # 半角→全角変換
    # 全角化してから濁点合成
    full = half_kana_to_full(text)
    hira = katakana_to_hiragana(full)
    return re.sub(r"[\s　]+", "", hira).strip()

def parse_name(raw_bytes):
    """名前漢字バイト列 → 表示名（スペース除去）"""
    try:
        text = raw_bytes.decode("shift_jis")
    except Exception:
        return ""
    text = unicodedata.normalize("NFKC", text)
    return re.sub(r"[\s　]+", "", text).strip()

def parse_branch(raw_bytes):
    try:
        return raw_bytes.decode("shift_jis").strip()
    except:
        return ""

def parse_hometown(raw_bytes):
    try:
        text = raw_bytes.decode("shift_jis")
        text = unicodedata.normalize("NFKC", text)
        return re.sub(r"[\s　]+", "", text).strip()
    except:
        return ""

def calc_birth(era_byte, date_bytes):
    """年号(S/H) + YYMMDD → YYYY-MM-DD"""
    try:
        era  = era_byte.decode("ascii").strip()
        ymd  = date_bytes.decode("ascii").strip()
        if len(ymd) != 6:
            return ""
        yy, mm, dd = int(ymd[0:2]), int(ymd[2:4]), int(ymd[4:6])
        if era == "S":
            yyyy = 1925 + yy
        elif era == "H":
            yyyy = 1988 + yy
        elif era == "R":
            yyyy = 2018 + yy
        else:
            return ""
        return f"{yyyy:04d}-{mm:02d}-{dd:02d}"
    except Exception:
        return ""

# ---- メイン処理 ----

def parse_record(line_bytes):
    """1レコードをパースして dict を返す。失敗時は None"""
    rd = line_bytes[:-1] if line_bytes.endswith(b"\r") else line_bytes
    if len(rd) < 416:
        return None

    toban = rd[0:4].decode("ascii", errors="replace").strip()
    if not toban.isdigit():
        return None

    name     = parse_name(rd[4:20])
    kana     = parse_kana(rd[20:35])
    branch   = parse_branch(rd[35:39])
    grade    = rd[39:41].decode("ascii", errors="replace").strip()
    birth    = calc_birth(rd[41:42], rd[42:48])
    hometown = parse_hometown(rd[410:416])

    if not name or not toban:
        return None

    return {
        "toban":    toban,
        "name":     name,
        "kana":     kana,
        "branch":   branch,
        "ki":       "",        # ファン手帳から確実に取得できないため空欄
        "birth":    birth,
        "grade":    grade,
        "status":   "active",  # このデータは現役選手のみ
        "hometown": hometown,
        "hobby":    "",
        "x_url":    "",
        "insta_url": "",
        "youtube_url": "",
        "note":     "",
        "checked":  "2026-07-06",
    }

def load_existing(csv_path):
    """既存 CSV の toban セットを返す"""
    if not os.path.exists(csv_path):
        return {}
    existing = {}
    with open(csv_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            existing[row["toban"]] = row
    return existing

def main():
    if len(sys.argv) < 2:
        print("使い方: python scripts/import_fanzine.py <fan????.txt>")
        sys.exit(1)

    txt_path = sys.argv[1]
    if not os.path.exists(txt_path):
        print(f"[エラー] ファイルが見つかりません: {txt_path}")
        sys.exit(1)

    with open(txt_path, "rb") as f:
        raw = f.read()

    lines = raw.split(b"\n")
    print(f"総行数: {len(lines)}")

    # パース
    new_racers = []
    errors = 0
    for line in lines:
        if len(line) < 100:
            continue
        rec = parse_record(line)
        if rec:
            new_racers.append(rec)
        else:
            errors += 1

    print(f"パース成功: {len(new_racers)} 選手 / エラー: {errors} 行")

    # 既存 CSV 読み込み（サンプルデータなどを保持する場合）
    existing = load_existing(RACERS_CSV)

    # 上書きルール: ファン手帳データが正（名前・支部・grade・birth等）
    # ただし既存に hobby/SNS/note が入っていれば引き継ぐ
    merged = {}
    for rec in new_racers:
        toban = rec["toban"]
        if toban in existing:
            ex = existing[toban]
            # 引き継ぎ項目
            rec["ki"]          = ex.get("ki", "") or rec["ki"]
            rec["hobby"]       = ex.get("hobby", "")
            rec["x_url"]       = ex.get("x_url", "")
            rec["insta_url"]   = ex.get("insta_url", "")
            rec["youtube_url"] = ex.get("youtube_url", "")
            rec["note"]        = ex.get("note", "")
            rec["checked"]     = ex.get("checked", rec["checked"])
        merged[toban] = rec

    # サンプル選手（9001〜9004）は除外
    EXCLUDE = {"9001", "9002", "9003", "9004"}
    merged = {k: v for k, v in merged.items() if k not in EXCLUDE}

    print(f"\nサンプル選手（9001〜9004）: 除外済み")
    print(f"最終レコード数: {len(merged)} 選手")

    # プレビュー
    sample = sorted(merged.values(), key=lambda r: int(r["toban"]))[:5]
    print("\n=== 先頭5件プレビュー ===")
    for r in sample:
        print(f"  {r['toban']} {r['name']:<10} {r['kana']:<15} {r['branch']} {r['grade']} {r['birth']} {r['hometown']}")

    ans = input(f"\n{len(merged)} 選手を racers.csv に書き込みますか？ [y/N]: ").strip().lower()
    if ans != "y":
        print("中止しました。")
        sys.exit(0)

    # 書き込み（登録番号順）
    sorted_racers = sorted(merged.values(), key=lambda r: int(r["toban"]) if r["toban"].isdigit() else 0)
    with open(RACERS_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for r in sorted_racers:
            writer.writerow(r)

    print(f"[完了] {RACERS_CSV} に {len(sorted_racers)} 選手を書き込みました。")
    print("\n次のステップ:")
    print("  python scripts/generate_racer_page.py   ← 全選手ページ再生成")
    print("  python scripts/generate_map.py           ← 関係マップ更新")
    print("  python scripts/generate_index.py         ← トップページ更新")

if __name__ == "__main__":
    main()
