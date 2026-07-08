# 舟☆探 データ仕様書

> 対象読者：黒田さん（馬☆探開発者）  
> 競艇経験なしを前提に、用語には都度説明を付けます。  
> 最終更新：2026-07-08

---

## 競艇用語クイックリファレンス

| 用語 | 意味 |
|------|------|
| **登番（とうばん）** | 登録番号。選手ごとに付く4桁の通し番号。全データの主キー |
| **支部（しぶ）** | 選手が所属する地域組織（18支部）。東京・大阪など都道府県名で管理 |
| **期（き）** | 養成所（ヤマト競艇学校）の入学コース番号。数字が大きいほど新人。同期＝同じ期の選手 |
| **級別（きゅうべつ）** | 選手のランク。A1＞A2＞B1＞B2の4段階。半期ごとに成績で昇降格 |
| **節（せつ）** | レースの開催単位。通常3〜6日間。"今節"は現在開催中の節 |
| **艇運（ていうん）** | 本サイト独自の造語。バイオリズム等から算出する日々の運気指標 |

---

## 1. リポジトリ構成

```
funetan/
├── data/                    ← 【唯一の正】手動管理するマスターデータ
│   ├── racers.csv           選手マスタ（1644行）
│   ├── relations.csv        人間関係マスタ（現在5行）
│   └── 監視サイトリスト.csv  巡回対象サイト一覧（15サイト）
│
├── scripts/                 ← Pythonで書いた生成・収集スクリプト群
│   ├── generate_racer_page.py   選手個別ページ生成
│   ├── generate_index.py        トップページ生成
│   ├── generate_map.py          関係マップページ生成
│   ├── generate_unki_page.py    艇運ページ生成
│   ├── generate_summary_pages.py まとめページ4種生成
│   ├── add_racer.py         選手1人を公式サイトから取得しCSVに追記
│   ├── add_relation.py      関係情報を対話形式でCSVに追記
│   ├── import_fanzine.py    公式ファン手帳（LZH）を一括インポート
│   ├── fetch_ki.py          期（養成期）を公式サイトから一括取得
│   ├── patrol.py            監視サイト巡回→差分を候補に出力
│   ├── scrape_macour.py     マクールコラムから関係候補を自動抽出
│   ├── generate_review.py   承認UI（docs/review/index.html）を生成
│   ├── approve.py           承認済みJSONをrelations.csvに追記
│   └── cache/               巡回キャッシュ（git管理外）
│       ├── candidates.json  承認待ち候補リスト
│       └── patrol_meta.json 各サイトの前回取得ハッシュ
│
├── docs/                    ← GitHub Pages 公開対象（静的HTML/CSS/JS）
│   ├── index.html           トップページ
│   ├── map.html             関係マップ（d3.js フォースグラフ）
│   ├── couples.html         夫婦一覧
│   ├── siblings.html        兄弟姉妹一覧
│   ├── shitei.html          師弟一覧
│   ├── hobby.html           趣味別逆引き（データ投入後に自動反映）
│   ├── review/index.html    関係情報の承認UI（公開しない運用）
│   ├── js/
│   │   └── comments.js      艇運コメント文面ライブラリ（全ページ共通）
│   ├── racer/{toban}.html   選手個別ページ（1644ファイル）
│   └── unki/{toban}.html    艇運ページ（1644ファイル）
│
├── templates/               （将来用・現在は未使用）
├── design/                  デザインモック（HTMLプロトタイプ）
├── CLAUDE.md                Claude Code への指示書（開発仕様書）
└── DATA_SPEC.md             本ファイル
```

### データフロー

```
  公式ファン手帳(LZH)
        │ import_fanzine.py
        ▼
  data/racers.csv ──────────────────────────────────────────┐
                                                            │
  人間関係取材・承認フロー:                                     │
    patrol.py / scrape_macour.py                            │
        │ 候補 → cache/candidates.json                      │
        │ generate_review.py                                │
        │ ブラウザで承認 → approved.json                     │
        │ approve.py / add_relation.py                      │
        ▼                                                   │
  data/relations.csv ──────────────────────────────────────┤
                                                            │
                                    ┌───────────────────────┘
                                    ▼
                          ┌─────────────────────────┐
                          │    Pythonスクリプト群     │
                          │  generate_*.py           │
                          └──────────┬──────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                 ▼
             docs/racer/      docs/unki/         docs/*.html
             (選手ページ)      (艇運ページ)      (index/map/一覧)
                    │
                    └─── docs/js/comments.js（コメント文面）
```

---

## 2. データファイル仕様

### 2-1. `data/racers.csv`

**文字コード：UTF-8 / 改行：LF / ヘッダー行あり**  
**現行レコード数：1644行**（2026-07-08時点）

| 列名 | 型 | 必須 | 値の例 | 空の場合の扱い |
|------|----|------|--------|---------------|
| `toban` | 文字列（数字4桁） | ◎ | `3897` | 存在しない（主キー） |
| `name` | 文字列 | ◎ | `白井英治` | 存在しない |
| `kana` | ひらがな | ◎ | `しらいえいじ` | 存在しない（検索用） |
| `branch` | 文字列 | ◎ | `山口`, `東京`, `大阪` | 存在しない |
| `ki` | 文字列（数字） | △ | `80`, `32`, `43` | **5件が空**（未取得）。ページ上の期バッジ非表示 |
| `birth` | 日付文字列 | ◎ | `1976-10-15` | 存在しない。艇運ページ生成の要件 |
| `grade` | 列挙 | ◎ | `A1`, `A2`, `B1`, `B2` | 存在しない |
| `status` | 列挙 | ◎ | `active`, `retired` | 存在しない |
| `hometown` | 文字列 | ◎ | `山口`, `千葉` | 存在しない |
| `hobby` | 文字列 | △ | 例：`釣り`, `ゴルフ` | **現在全件空**（将来入力予定） |
| `x_url` | URL文字列 | △ | `https://x.com/...` | **現在全件空** |
| `insta_url` | URL文字列 | △ | `https://instagram.com/...` | **現在全件空** |
| `youtube_url` | URL文字列 | △ | `https://youtube.com/...` | **現在全件空** |
| `note` | 自由テキスト | △ | `殿堂入り・通算最多優勝記録保持者` | **1件のみ記入**。ページ末尾に表示 |
| `checked` | 日付文字列 | ◎ | `2026-07-06` | データ確認日（表示用） |

**`grade` の値と意味：**

| 値 | 件数 | 意味 |
|----|------|------|
| `A1` | 332 | 最上位クラス。重賞レースに出走できる |
| `A2` | 329 | 上位クラス |
| `B1` | 808 | 一般クラス（最多） |
| `B2` | 175 | 下位クラス |

**`branch` の値（18支部）：**  
`三重`, `佐賀`, `兵庫`, `埼玉`, `大阪`, `山口`, `岡山`, `広島`, `徳島`, `愛知`, `東京`, `滋賀`, `福井`, `福岡`, `群馬`, `長崎`, `静岡`, `香川`

---

### 2-2. `data/relations.csv`

**文字コード：UTF-8 / 改行：LF / ヘッダー行あり**  
**現行レコード数：5行**（2026-07-08時点・承認済みのみ）

| 列名 | 型 | 必須 | 値の例 | 説明 |
|------|----|------|--------|------|
| `id` | 文字列 | ◎ | `R0001`, `R0005` | 連番（Rプレフィックス+4桁） |
| `from_toban` | 文字列（4桁） | ◎ | `3897` | 関係の起点となる選手の登番 |
| `rel_type` | 列挙（後述） | ◎ | `師匠`, `配偶者`, `弟` | 関係の種類 |
| `to_toban` | 文字列（4桁） | △ | `2992` | 相手が選手の場合。一般人なら空 |
| `to_name` | 文字列 | ◎ | `今村豊`, `深谷知博` | 相手の名前（選手・一般人問わず） |
| `confidence` | 列挙：`A`/`B`/`C` | ◎ | `A` | 確度（後述） |
| `source_url` | URL | ◎ | `https://sp.macour.jp/...` | **必須**。空行は生成時警告＆非表示 |
| `source_date` | 日付文字列 | ◎ | `2022-12-21` | 出典記事の公開日 |
| `checked` | 日付文字列 | ◎ | `2026-07-06` | データ確認日 |
| `memo` | 自由テキスト | △ | `GP表彰式で両者が師弟関係を公言` | 内部メモ。サイトには表示しない |

**`rel_type` の値一覧（辞書制）：**  
`父`, `母`, `子`, `兄`, `姉`, `弟`, `妹`, `配偶者`, `元配偶者`, `師匠`, `弟子`, `親族`, `友人`, `同期`, `仲良し`  
※このリスト以外の値は使用禁止。

**`confidence` の意味と表示ルール：**

| 値 | ラベル | 意味 | サイト表示 |
|----|--------|------|-----------|
| `A` | ◎ 本人公表 | 本人の発言・投稿が確認できる（SNS・インタビュー等の直接引用） | **表示する** |
| `B` | ○ 報道 | 第三者による記載（記者の地の文・Wikipedia等） | **表示する** |
| `C` | （非公開） | 噂・未確認情報 | **絶対に表示しない**（DBには保持） |

**表示条件（生成スクリプトが除外する条件）：**
1. `confidence == "C"` → 除外
2. `source_url` が空 → 除外（スクリプトが警告も出力）

**方向の持ち方（重要）：**  
関係は片方向のみ記録する。逆方向はページ生成時にプログラムが補完する。  
例：`師匠→弟子` の行1本から、師匠ページにも弟子ページにも両方表示する。

---

### 2-3. `data/監視サイトリスト.csv`

**文字コード：UTF-8**

巡回スクリプト（`patrol.py`）が参照するサイト一覧。現在15サイトを登録済み。

| 列名 | 値の例 |
|------|--------|
| `サイト名` | `フネラブ(kcbn) 兄弟姉妹一覧` |
| `URL` | `https://kcbn.jp/brother-sisters/` |
| `取得対象` | `家族関係`, `師弟関係` など |
| `巡回頻度` | `週1`, `月1`, `随時` |
| `優先度` | `高`, `中`, `低` |
| `備考` | 更新頻度・特徴のメモ |

スクリプトは直接このCSVをパースしていない（URLをハードコード）。ダシオさんの運用メモとして保持。

---

### 2-4. `scripts/cache/candidates.json`

承認待ちの関係情報候補リスト。`patrol.py` または `scrape_macour.py` が書き込む。

**スキーマ（配列。各要素のキー）：**

| キー | 型 | 説明 |
|------|----|------|
| `snippet` | 文字列 | 根拠となった記事の抜粋文 |
| `evidence_sentence` | 文字列 | 関係を直接示した一文 |
| `source_url` | URL文字列 | 記事URL |
| `source_date` | 日付文字列 | 記事公開日 |
| `matched_names` | 文字列配列 | 記事内で検出した選手名 |
| `suggested_rel` | 文字列 | 推定した `rel_type` |
| `suggested_conf` | 文字列 | `A仮` または `B仮`（確定前） |
| `from_toban` | 文字列 | 起点選手の登番 |
| `from_name` | 文字列 | 起点選手の名前 |
| `to_toban` | 文字列 | 相手選手の登番（一般人なら空） |
| `to_name` | 文字列 | 相手の名前 |
| `has_direct_quote` | bool | 「」内に直接引用があるか |
| `name_warning` | 文字列 | 改姓の可能性など警告フラグ |
| `headline` | 文字列 | 記事タイトル |

このファイルは `.gitignore` に入れており、リポジトリには含まない。

---

### 2-5. `scripts/cache/patrol_meta.json`

`patrol.py` が巡回済みサイトのコンテンツハッシュを保存するファイル。差分検出に使用。

構造：`{ "URLを正規化したキー": { ... ハッシュ情報 ... } }`

このファイルも `.gitignore` に入れており、リポジトリには含まない。

---

## 3. 共通取り決め

| 項目 | 取り決め |
|------|---------|
| **主キー** | `toban`（登録番号）4桁整数。文字列型で保持（ゼロ埋めなし） |
| **日付形式** | `YYYY-MM-DD`（ISO 8601）で統一。例：`1976-10-15` |
| **文字コード** | UTF-8（BOMなし）|
| **改行** | LF（Unix形式）|
| **数値** | 数字でも文字列型で保持（CSV の都合上） |
| **空値** | 空文字列 `""` で表現。NULL相当 |
| **ファイル命名** | スクリプトは `scripts/*.py`、出力は `docs/**/*.html` |

---

## 4. 同期・同支部の設計

**CSVには保存しない。ページ生成時に ki / branch から自動算出する。**

```python
# scripts/generate_racer_page.py より

def build_ki_map(racers):
    """ki（期）をキーに、同期選手リストを返す辞書を構築"""
    # ki が空の選手はこのマップに含まれない

def build_branch_map(racers):
    """branch（支部）をキーに、同支部選手リストを返す辞書を構築"""
```

選手ページ生成時にインメモリで算出し、HTMLに埋め込む。relations.csv には書き込まない。

ki 未取得の選手（現在5件）は「同期」ブロックが表示されない。取得後に `generate_racer_page.py` を再実行すれば自動反映する設計。

**関係マップ（map.html）でも同様：**  
グラフ上に描画済みのノード（relations.csvから登場した選手）同士が同期なら、細い点線（opacity 0.28）で自動表示する。

---

## 5. 艇運（今日の艇運）の設計

**サーバー不要。ページ表示時にブラウザのJSが計算する。毎日再生成不要。**

`docs/unki/{toban}.html` 1枚の中に選手の生年月日が埋め込まれており、表示時に JavaScript が今日の日付と掛け合わせて計算する。

### 計算ロジックの場所

| 計算内容 | ロジックの場所 |
|----------|---------------|
| バイオリズム（身体23日・感情28日・知性33日） | `docs/unki/{toban}.html` 内の `<script>` ブロック（`bioVal`, `bioStab` 関数） |
| 六曜 | 同上（`getRokuyou` 関数。旧暦近似計算） |
| 月齢・月相・潮回り | 同上（`getMoonTideData` 関数） |
| 星座 | 同上（`getZodiac` 関数） |
| 九星（数え年から算出） | 同上（`getKyusei` 関数） |
| 厄年判定（数え年） | 同上（`getYakudoshi` 関数） |
| 吉方位 | 同上（`getLuckyDirs` 関数。年盤・年運） |
| **コメント文面（全ページ共通）** | **`docs/js/comments.js`**（外部ファイルとして共有） |

`comments.js` だけ更新すれば全1644選手のコメントが同時に変わる（HTML再生成不要）。

### 日付シード

コメントは日付シードで選択する（`seedPick` 関数）。同じ日は全選手が同じ文面を参照するため、A選手→B選手と見比べても矛盾しない。

---

## 6. 更新フロー

### 6-1. スクリプト実行順

| 何を変えたか | 実行するスクリプト | 出力先 |
|-------------|------------------|--------|
| 選手マスタ（racers.csv）を変更 | `python3 scripts/generate_racer_page.py` | `docs/racer/*.html` |
| 〃 | `python3 scripts/generate_index.py` | `docs/index.html` |
| 〃 | `python3 scripts/generate_unki_page.py` | `docs/unki/*.html` |
| 〃 | `python3 scripts/generate_summary_pages.py` | `docs/*.html` |
| 関係情報（relations.csv）を変更 | `python3 scripts/generate_racer_page.py` | `docs/racer/*.html` |
| 〃 | `python3 scripts/generate_map.py` | `docs/map.html` |
| 〃 | `python3 scripts/generate_summary_pages.py` | `docs/*.html` |
| コメント文面のみ変更 | **スクリプト不要**。`docs/js/comments.js` を直接編集 | — |

### 6-2. 関係情報の追加フロー（半自動）

```
1. 巡回・候補抽出
   python3 scripts/patrol.py
   python3 scripts/scrape_macour.py
       → scripts/cache/candidates.json に候補を書き出し

2. 承認UI生成
   python3 scripts/generate_review.py
       → docs/review/index.html をブラウザで開く

3. ブラウザで承認・編集
   → 「承認済みをダウンロード」で approved.json を保存

4. relations.csv に追記
   python3 scripts/approve.py ~/Downloads/approved.json

5. サイト再生成
   python3 scripts/generate_racer_page.py
   python3 scripts/generate_map.py
   python3 scripts/generate_summary_pages.py

6. コミット
   git add data/ docs/ && git commit -m "関係情報更新: YYYY-MM-DD"
   git push
```

### 6-3. 選手の追加・更新フロー

```
# 1人追加
python3 scripts/add_racer.py <登録番号> [名前]
# → racers.csv に1行追記（確認後）

# 再生成
python3 scripts/generate_racer_page.py <登録番号>  # 1人だけ
python3 scripts/generate_unki_page.py <登録番号>
python3 scripts/generate_index.py
```

### 6-4. 運用方針

**手動作業は「関係情報の承認」のみ。それ以外は全自動。**

| 作業 | 自動/手動 |
|------|---------|
| 選手マスタの更新（ファン手帳） | 自動（`import_fanzine.py`） |
| ki（期）の取得 | 自動（`fetch_ki.py`） |
| 関係候補の抽出 | 自動（`patrol.py` / `scrape_macour.py`） |
| **関係情報の承認・確度確定** | **手動（ダシオさんがブラウザで承認）** |
| relations.csv への書き込み | 自動（`approve.py`） |
| HTMLページの生成 | 自動（`generate_*.py`） |
| GitHub へのデプロイ | 自動（`git push` で Pages に反映） |

---

## 7. 今後の拡張（M6.5）

### BOATRACE 公式 API からのデータ自動取得

競艇公式サービス BOATRACE（旧称：ボートレース）の公式データ提供サービス「MBRACE」から、以下のデータを毎日自動取得してDB化する計画。

| データ種別 | 内容 | 更新頻度 |
|-----------|------|---------|
| 番組表 | 各場・各節の出走表（誰が何コースに乗るか） | 節ごと（週1〜2回） |
| レース結果 | 着順・タイム・スタートタイミング | レース終了後随時 |
| 選手情報 | 勝率・コース別成績・ランキング等 | 半期更新 |
| モーター | モーター番号・整備記録・勝率 | 節ごと |

### 馬☆探方式への全面準拠

**テーブル設計・データ形式・APIレスポンス形式は馬☆探の実装に全面的に合わせる予定。**

舟☆探は「競艇版の馬☆探」として設計されており、将来的に馬☆探と同一インフラ・同一フォーマットで運用することを目指す。具体的な設計詳細は黒田さんに仕様を確認の上、実装する。

**現時点で確定している方針：**
- 成績データは `racers.csv` に含めない（別テーブルで管理）
- 登録番号（`toban`）が選手の主キーとして全テーブルで共通
- 日付形式は `YYYY-MM-DD` で統一（現行CSVと同じ）
- 文字コードは UTF-8

---

## 8. 公開情報

| 項目 | 値 |
|------|---|
| GitHub リポジトリ | https://github.com/bonito323-a11y/funetan |
| 公開URL（トップ） | https://bonito323-a11y.github.io/funetan/ |
| 公開URL（選手例） | https://bonito323-a11y.github.io/funetan/racer/3897.html |
| 公開URL（艇運例） | https://bonito323-a11y.github.io/funetan/unki/3897.html |
| ホスティング | GitHub Pages（main ブランチの docs/ フォルダ） |
| サーバー | なし（静的ファイルのみ） |
