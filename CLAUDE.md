# 舟☆探 選手名鑑 プロジェクト指示書（CLAUDE.md）

## このプロジェクトは何か

競艇（BOATRACE）選手の情報データベースサイトを作る。
- 全選手の個別ページ（プロフィール・人間関係・運気）
- 関係マップ（人間関係のネットワーク図）
- 「今日の艇運」（バイオリズム等の日替わり運気コンテンツ）
- 無料公開して、将来の予想サービス「舟☆探」への集客装置にする

**データはCSV2枚（racers.csv / relations.csv）が唯一の正**。サイトは全部そこから自動生成する。手でHTMLを直接編集することは絶対にしない。

## ファン手帳データの利用方針

- BOATRACE公式サイトのファン手帳データ（fan????.lzh）を **racers.csv の材料** として使用する
- **ファイルの再配布禁止**：LZHファイル・解凍後TXTファイルはリポジトリにコミットしない（.gitignoreで除外）
- **成績データはサイトに掲載しない**：勝率・コース別成績等はracers.csvに取り込まず破棄する
- 取り込みスクリプト：`scripts/import_fanzine.py`（一括）、個別は `scripts/add_racer.py`（公式サイト取得）

## オーナーについて（最重要・毎回必ず守ること）

オーナーのダシオさんは**非エンジニア**。以下を厳守：
1. 専門用語を使うときは必ず一言で意味を添える（例：「コミット＝セーブポイントの記録」）
2. 作業は**1回のセッションで1マイルストーンだけ**。欲張らない。終わったら必ず目で確認できる成果物（ブラウザで開けるファイル）を示す
3. 何かを実行する前に「今から何をするか」を1〜2行で日本語で説明する
4. エラーが出たら自分で直す。ダシオさんにエラーメッセージの解読を求めない
5. 破壊的な操作（ファイル削除・上書き・公開反映）の前は必ず確認を取る
6. 各セッションの最後に必ず git commit（セーブ）し、`作業ログ.md` に「今日やったこと・次やること」を3行で追記する

## フォルダ構成

```
funetan/
├── CLAUDE.md            ← この指示書
├── 作業ログ.md           ← セッションごとの記録（Claude Codeが書く）
├── data/
│   ├── racers.csv       ← 選手マスタ（正）
│   ├── relations.csv    ← 関係マスタ（正）
│   └── 監視サイトリスト.csv
├── design/
│   ├── 選手ページモック.html   ← デザインの見本。これに寄せる
│   ├── 関係マップデモ.html
│   └── 今日の艇運デモ.html
├── templates/           ← ページの雛形（Claude Codeが作る）
├── scripts/             ← 生成スクリプト（Claude Codeが作る）
└── docs/                ← 生成されたサイト本体（GitHub Pagesの公開対象）
```

## データ仕様（DB設計書の要点）

### racers.csv
toban（登録番号・主キー）, name, kana, branch, ki, birth（YYYY-MM-DD）, grade, status, hometown, hobby, x_url, insta_url, youtube_url, note, checked

### relations.csv
id, from_toban, rel_type, to_toban, to_name, confidence, source_url, source_date, checked, memo

- rel_type は辞書の値のみ：父/母/子/兄/姉/弟/妹/配偶者/元配偶者/師匠/弟子/親族/**友人/同期/仲良し**
- 関係は片方向のみ記録。逆方向（弟子↔師匠など）は生成時にプログラムで補完する
- **confidence=C の関係はサイトに絶対に表示しない**（DBに保持はする）
- source_url が空の行は生成時に警告を出す

## 生成するページ

1. **選手個別ページ** `docs/racer/{toban}.html` — design/選手ページモック.html のデザインを踏襲。人間関係カード（確度バッジ付き）、基本情報、外部リンク（toban から機械生成：公式 `boatrace.jp/owpc/pc/data/racersearch/profile?toban=`、艇国DB `boatrace-db.net/racer/index2/regno/`）、舟☆探CTA
2. **関係マップ** `docs/map.html` — design/関係マップデモ.html 方式。relations.csv から nodes/links を生成
3. **今日の艇運** `docs/unki/{toban}.html` — design/今日の艇運デモ.html 方式。バイオリズムはページを開いた日にJSで計算（毎日生成し直す必要なし）。厄年・星座・九星は birth から算出
4. **まとめページ** `docs/couples.html`（夫婦一覧）、`docs/siblings.html`（兄弟）、`docs/shitei.html`（師弟）、`docs/hobby.html`（趣味別逆引き）
5. **トップページ** `docs/index.html` — 選手検索（名前/登録番号）、更新情報、各一覧への入口

## 表示上のルール

- 6艇カラーストライプ（白黒赤青黄緑）を全ページ共通ヘッダーに
- 全ページに最終確認日を表示
- 艇運ページには必ずエンタメ免責文を入れる：「エンターテインメントコンテンツであり、レース予想の根拠となるものではありません」
- 選手写真は使わない（肖像権）。「大殺界」「六星占術」「動物占い」の名称は使わない（商標）
- 出典URLのない関係情報は表示しない

## 技術方針

- 生成スクリプトは Python（標準ライブラリ中心、依存は最小限に）
- 出力は素のHTML/CSS/JS。フレームワーク不使用。関係マップのみ d3 を CDN から
- 公開は GitHub Pages（リポジトリの docs/ フォルダを公開する設定）
- 文字コードは UTF-8、日本語ファイル名OK

## マイルストーン（1セッション＝1つ）

- **M1**: フォルダ初期化、git 設定、CSVを読んで選手ページを1枚だけ生成 → ブラウザで確認
- **M2**: 全選手ページ＋トップページ生成、選手間の内部リンクを張る
- **M3**: 関係マップページ（relations.csv → グラフ）
- **M4**: 今日の艇運ページ（バイオリズム・厄年・星座）
- **M5**: まとめページ4種（夫婦/兄弟/師弟/趣味）
- **M6**: GitHub Pages 公開設定 → 実際のURLで表示確認
- **M7**: 週次更新フロー整備（監視サイトリスト巡回 → 差分レポート → CSV追記案の提示）
- **M8**: LINE導線・舟☆探CTAの本番文言差し込み

各マイルストーン完了時に必ず：commit → 作業ログ.md 更新 → ダシオさんに確認ポイントを提示。

## 選手追加フロー（M2以降いつでも使える）

ダシオさんが「〇〇（登録番号XXXX）を追加して」と言ったら：

1. **スクリプトで自動取得**（1人ずつ、1秒待機）
   ```
   python scripts/add_racer.py <登録番号> [名前]
   ```
   - 公式サイト（boatrace.jp）からプロフィールを取得
   - 名前の照合チェックを自動実施（不一致なら警告）
   - 取得内容を表示 → ダシオさんに確認を求めてから追記

2. **relations.csv に関係情報を追記**（confidence・source_url 必須）
   - confidence=C（噂レベル）はDBに保持するが絶対に表示しない

3. **趣味・SNS URL・引退かどうか**はスクリプトでは取れないので、追記後に racers.csv を手動確認

4. **サイトを再生成**してコミット
   ```
   python scripts/generate_racer_page.py   # 全員 or 追加した登録番号だけ
   python scripts/generate_map.py
   python scripts/generate_index.py
   git add data/ docs/ && git commit -m "選手追加: <名前>（<登録番号>）"
   ```

**注意事項**
- 追加は1人ずつ。まとめて大量取得しない（公式サイトへの負荷配慮）
- source_url が空の relations.csv 行は生成時に警告が出る。必ず出典を入れる

## 関係情報の管理方針（厳守）

- **既存サイトの一覧を丸ごと取り込むことは禁止**。必ず差分のみを候補とする
- **初回巡回はベースライン保存のみ**。候補は一切出力しない
- **出典URLのない関係情報は絶対にrelations.csvに入れない**
- confidence=C の情報はDBに保持するがサイトには表示しない
- 関係情報の初期投入は ダシオさんが取材テンプレ（add_relation.py）で1件ずつ登録する

## 関係情報フロー（取材テンプレ）

ダシオさんが調査した関係情報を手入力する場合：
```
python scripts/add_relation.py
```
→ 対話形式で from_toban / rel_type / to_toban / 確度 / 出典URL を入力して追記。

## 週次運用フロー（監視サイト巡回）

ダシオさんが「巡回して」と言ったら：

1. **巡回・差分抽出**
   ```
   python scripts/patrol.py
   ```
   - 初回のみ: ベースライン保存（候補なし）
   - 2回目以降: 前回保存との差分から候補を `scripts/cache/candidates.json` に出力

2. **承認UI生成**
   ```
   python scripts/generate_review.py
   ```
   → `docs/review/index.html` をブラウザで開く

3. **ブラウザで承認**
   - 出典URLを必ず確認してから承認チェック
   - 関係タイプ・確度・登録番号を編集
   - 「承認済みをダウンロード」→ `approved.json` をDLフォルダへ保存

4. **relations.csv に追記**
   ```
   python scripts/approve.py ~/Downloads/approved.json
   ```

5. **サイト再生成 → commit**
   ```
   python scripts/generate_racer_page.py
   python scripts/generate_map.py
   python scripts/generate_index.py
   git add data/ docs/ && git commit -m "関係情報更新: YYYY-MM-DD巡回分"
   ```
