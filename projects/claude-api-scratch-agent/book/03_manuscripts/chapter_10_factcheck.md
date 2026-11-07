# ファクトチェックレポート

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_10.md
検証日: 2026-11-07
検証クレーム数: 31件
  ✅ 検証済み: 27件
  ⚠️ 要確認: 2件
  ❌ 要修正: 2件（原稿修正済み）

主な一次情報:
- Web search tool: https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool.md
- Server tools（pause_turn）: https://platform.claude.com/docs/en/agents-and-tools/tool-use/server-tools.md
- Programmatic tool calling: https://platform.claude.com/docs/en/agents-and-tools/tool-use/programmatic-tool-calling.md
- Pricing / Effort / Structured outputs / Errors / Messages API リファレンス / 2026-10-21 移行ガイド（platform.claude.com）
- pytest Good Integration Practices / customize、uv dependency groups（pydevtools 経由）、httpx Transports

---

## ✅ 検証済み（正確）

### クレーム1
**記述**: 「`web_search_20260209` は、検索結果をコードで絞り込んでから読む『動的フィルタリング』に対応した版」
**検証結果**: Web search tool。`web_search_20260209: adds dynamic filtering`。

### クレーム2
**記述**: リサーチャー（`claude-haiku-5-5`）で `web_search_20260209` を使う
**検証結果**: web search の supportedModels と programmatic tool calling の supportedModels の両方に `claude-haiku-5-5` が含まれる。PTC非対応モデルで必要な `allowed_callers: ["direct"]` は不要。

### クレーム3
**記述**: 「トークン料金とは別に、検索1,000回あたり10ドル」（`WEB_SEARCH_USD = 10 / 1000`）
**検証結果**: Pricing / Web search tool「$10 USD per 1,000 searches, plus standard token costs」。動的フィルタリングのコード実行は追加料金なし。

### クレーム4
**記述**: 「組織の管理者が Console で無効にしている場合は、400エラー」
**検証結果**: Web search tool の Note。無効時は 400 `invalid_request_error`。

### クレーム5
**記述**: `usage.server_tool_use.web_search_requests` で検索回数を数える
**検証結果**: Web search tool の Usage and pricing の例と一致。

### クレーム6
**記述**: pause_turn では、返ってきた assistant の `content` を変更せずに履歴の末尾に付けて再送する。prefill とは別物
**検証結果**: Server tools「Pass the paused response back as-is」。公式の例も最後が assistant メッセージのまま再送している。prefill 禁止（Claude 4.6 以降のモデル）は、自作の部分的な assistant メッセージが対象。pause_turn の再送は対象外（Errors / Server tools）。再送する assistant の text ブロックに付いた citations も受け付けられる（2026-10-21 移行ガイド）。

### クレーム7
**記述**: 動的フィルタリングではレスポンスにコード実行のブロックも混ざる
**検証結果**: Web search tool「the response also contains the result blocks of the code execution tool」。

### クレーム8
**記述**: 「Web検索では引用が常に有効で、`url`・`title`・`cited_text` が入ります」（`web_search_result_location`）
**検証結果**: 「Citations are always enabled for web search」。フィールドはこの3つに `encrypted_index` を加えた4つ。

### クレーム9
**記述**: 「検索結果は入力トークンとしても課金されます」
**検証結果**: Pricing「Web search results ... are counted as input tokens」。

### クレーム10
**記述**: 再開時に同じ `tools` を送る（コードで `WEB_SEARCH_TOOL` を再利用）
**検証結果**: Server tools「Include the same tools in the continuation request」。

### クレーム11
**記述**: `output_config` には `effort` と `format` を同時に指定できる
**検証結果**: Messages API リファレンス。`output_config` は `effort` と `format` を兄弟フィールドとして持ち、両方を指定した例がある。

### クレーム12
**記述**: `effort: "low"`／`"medium"` の指定（Opus 5.5）
**検証結果**: Effort。Opus 5.5 は5段階すべてに対応し、既定は medium。

### クレーム13
**記述**: 「スキーマでは個数を縛れない」「スキーマで整数であることは保証されますが、範囲までは保証されない」
**検証結果**: Structured outputs。`minimum`/`maximum` は非対応、配列の `minItems` は0と1のみ、`maxItems` は非対応。

### クレーム14
**記述**: `enum`・`required`・`additionalProperties: False` を使ったスキーマ
**検証結果**: Structured outputs。enum は対応、`additionalProperties` は false が必須。

### クレーム15
**記述**: モデル割り当て（`claude-opus-5-5` / `claude-sonnet-5-5` / `claude-haiku-5-5`）
**検証結果**: Pricing・Models に3つのIDがある。

### クレーム16
**記述**: 試用資料「出力の単価は入力の5倍程度」
**検証結果**: Opus 5.5 $4/$20、Sonnet 5.5 $2/$10、Haiku 5.5 $0.10/$0.50で、いずれも5倍。

### クレーム17
**記述**: `stop_reason == "refusal"` の扱い
**検証結果**: Messages API の stop_reason に `refusal` がある。

### クレーム18
**記述**: テストで `anthropic-version` が `2026-10-21`、`temperature` を送らない
**検証結果**: 2026-10-21 移行ガイド。`temperature`/`top_p`/`top_k` を送ると400。

### クレーム19
**記述**: 出力例のコスト（plan 0.0213 + research 0.0187 + write 0.1964 + review 0.0802 + orchestrator 0.0754 = 0.392。執筆は全体の約半分）
**検証結果**: 合計は一致し、執筆の比率は50.1%。ログの残額の推移とも矛盾しない。

### クレーム20
**記述**: 「`-m` で実行するとカレントディレクトリがモジュール検索パスに加わる」「`python report_agent/cli.py` だと `ModuleNotFoundError`」
**検証結果**: Python のコマンドラインの仕様。`-m`/`-c` は sys.path に cwd を入れ、スクリプトを直接指定するとスクリプトのディレクトリが入る。

### クレーム21
**記述**: argparse（`choices`、`store_true`、`--max-rounds` → `args.max_rounds`、`parser.error()` で使い方を表示して終了）
**検証結果**: Python 標準ライブラリの仕様どおり（`error()` は終了コード2で終了する）。

### クレーム22
**記述**: `uv add --dev pytest` で開発用の依存として追加される
**検証結果**: uv の dependency groups。`--dev` は `[dependency-groups]` の `dev` グループに追加する。

### クレーム23
**記述**: `[tool.pytest.ini_options]` の `pythonpath = ["."]`、`testpaths`
**検証結果**: pytest Good Integration Practices。`pythonpath` を pyproject で設定する例がある。rootdir は sys.path を変更しない。

### クレーム24
**記述**: 「pytest はテストファイルのフォルダを検索パスに入れますが、プロジェクトのルートは入れない」
**検証結果**: 既定の import mode（prepend）では、`__init__.py` を持たない tests/ が sys.path に入る。`uv run pytest` はルートを入れない。

### クレーム25
**記述**: `httpx.MockTransport` は同期と非同期の両方に対応
**検証結果**: httpx の Transports ドキュメントは同期の例のみ。ただし実装上 `MockTransport` は `BaseTransport` と `AsyncBaseTransport` の両方を継承し、同期の handler も `AsyncClient` で動く（httpx のソースで確認）。

### クレーム26
**記述**: 「`asyncio.Lock` は再入できません」
**検証結果**: Python asyncio のドキュメント。Lock は非再入。

### クレーム27
**記述**: `encoding` を省略すると Windows ではロケールの文字コード（cp932）が使われる
**検証結果**: Python 3.12 の `open()` の既定は `locale.getencoding()` で、日本語版Windowsでは cp932。

---

## ⚠️ 要確認（古い可能性あり）

### クレーム28
**記述**: 「オーケストレーター ... だから最上位モデルを使います」（Opus 5.5 を最上位とする表現）
**懸念点**: 料金表には Opus 5.5 より上位・高価な Claude Fable 5.1（$10/$50）がある。
**検索結果**: Pricing のモデル一覧。
**推奨対処**: 「本書の主力モデル（Opus 5.5）」または「上位モデル」と言い換える。他章の「最上位モデル」も同様。

### クレーム29
**記述**: 「ロックを `__init__()` ではなく後で作るのは、イベントループの中で作るのが安全だからです」
**懸念点**: Python 3.10 以降の `asyncio.Lock` は、作成時にはループに結び付かない（最初に待ちが発生したときに結び付く）。理由づけが古い。
**推奨対処**: 「`asyncio.run()` は呼ぶたびに新しいイベントループを作るので、ループごとに新しいロックを用意するため」と書き換える。

---

## ❌ 要修正（誤りの可能性が高い）→ 原稿修正済み

### クレーム30
**記述**: 「`max_uses` は1回の調査の検索回数の上限で、料金の上限でもあります」
**問題**: `max_uses` は「1ターン」の上限。web_search_20260209 は既定でコード実行経由（動的フィルタリング）で検索するので、pause_turn から再開すると、前のリクエストの検索は数えられない。そのため、1回の調査で `max_uses` を超える検索が起こり得る。
**正しい情報**: Web search tool の Max uses の節。「Searches from earlier requests in that turn count against the limit, unless Claude ran them from code execution through dynamic filtering.」
**修正内容**: WARNING を「1ターンの上限」に直し、最大で `max_uses` ×（`MAX_CONTINUES` + 1）回の検索が起こり得ることを追記した。

### クレーム31
**記述**: `research_web()` の pause_turn 再開処理（content だけを再送し、コンテナIDは引き継がない）
**問題**: Server tools の pause_turn の扱いには「Keep the container: If the response includes a container ... send its ID back in the continuation request. Without it, the request runs in a new container, and files from earlier in the turn are lost.」とある。動的フィルタリングではコード実行コンテナが自動で用意されるため、再開時に引き継ぐ必要がある。
**修正内容**: `extra = {"container": response["container"]["id"]}` を再開時に `acall_messages(..., extra=extra)` で送るコード（第4章の `extra` の受け口を使う）と、本文の説明を1文追加した。テストはローカル版の経路なので影響はない。

---

## 総評

Web検索サーバーツールの料金、Console での無効化、citations の形、pause_turn での「そのまま再送」は、一次情報と一致した。Haiku 5.5 で web_search_20260209（動的フィルタリング）も使える。修正したのは、動的フィルタリング特有の2点（max_uses の数え方とコンテナの引き継ぎ）。どちらも「web_search_20250305 なら正しい」記述だった。`/verify-code` で実APIを使って Web 検索版を確かめることを推奨する。
