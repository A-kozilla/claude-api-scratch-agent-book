# コード検証レポート

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_10.md
検証日: 2026-11-07
コードブロック数: 32個
  ✅ 動作確認済み: 22個
  ⚠️ 要確認: 1個
  ❌ エラーあり: 3個（3個とも原稿を修正済み）
  🔍 構文チェックのみ: 6個

## 検証環境と方法

- Python 3.12 の venv（httpx・python-dotenv・pytest）。APIキーなし。
- 前提コードは前章の原稿から組み立てた: 第4章の完成版 `llm_client.py`、第7章の `count_tokens`・`cached_system`/`cached_tools`、第8章の `acall_messages`・`aclose_client`・`_get_async_client`、第5・6章の `tools/`・`tool_registry.py`（6.3の検証付き `execute`）、第7章の `context.py`、第8章の `Agent`（`run`・`arun`・`async_handlers`）。第8章は検証中に他の担当が更新したため、更新後の版で組み立て直して再確認した。
- 第10章のコードは本文どおりに組み立てた: `report_agent/`（6ファイル）、`llm_client.set_transport`、`tests/test_report_agent.py`、`pyproject.toml` の pytest 設定、`workspace/sources/` の資料2つ。
- 実行したもの:
  - `python -c "from report_agent.researcher import search_local_docs; ..."` → 本文の出力例と完全に一致
  - `pytest -q`（**偽APIなし・APIキーなし**）→ `5 passed`。通信はテスト自身の MockTransport だけ
  - `python -m report_agent.cli "…" --budget 1.0 --source local`（偽API付き）。素の偽APIでは計画の問いIDが `サンプルid` になり委譲がすべて `ERROR` で返るため、計画とオーケストレーターの応答だけを台本化したハンドラーでも実行した → 調査（並列2本・ツール2回ずつ）→ 執筆 → 採点 → 修正 → 再採点 → `report.md`・`cost.json`・`notes/`・`drafts/`・`reviews/` を出力して終了コード0
  - `--source web --max-questions 2 --budget 0.5`（偽APIは web_search を無視するので配線のみ確認）
  - `research_web()` の単体試験（`pause_turn` から再開・`server_tool_use.web_search_requests` の加算・citations からの出典一覧作成）
  - `--max-rounds 0`（2回目の執筆が `LIMIT_REACHED` になり v1 で終了）、`--budget 0`（argparse のエラー）
- 偽APIへの仕様違反（temperature・prefill・tool_result 欠落など）は0件。

---

## ❌ エラーが発生したコード（すべて修正済み）

### コードブロック #9（chapter_10.md L574付近: orchestrator.py ブロック5）
### コードブロック #10（chapter_10.md L641付近: orchestrator.py ブロック6）

**元のコード**（冒頭）:
```python
# report_agent/orchestrator.py（ブロック5 / 各委譲の本体）
    async def _research(self, question_ids: list[str], extra_questions: list[str]) -> str:
```

**エラー内容**（ブロック単体で構文チェックした場合）:
```text
IndentationError: unexpected indent
```

**原因**: ブロック5・6は `ReportOrchestrator` クラスのメソッドの続き（インデント付きの抜粋）だが、本文にもファイル名コメントにもその旨がなかった。ブロック4の後ろにクラス内のインデントのまま続けて書けば正しく動く（組み立てて実行確認済み）。

**修正内容**（原稿に反映済み）:
- ファイル名コメントを `（ブロック5 / 各委譲の本体。ReportOrchestrator クラス内の続き）`・`（ブロック6 / 補助メソッド・実行の入口・最終出力。ReportOrchestrator クラス内の続き）` に変更
- L572 の導入文に「ブロック5と6は `ReportOrchestrator` クラスのメソッドの続きなので、ブロック4の末尾に、クラスの中のインデント（空白4つ）のまま書き足してください。」を追記

### コードブロック #20（chapter_10.md L1155付近: report_agent/cli.py）

**元のコード**:
```python
    if not args.verbose:  # 通常は進捗だけを表示し、1回ごとの通信ログは隠す
        logging.getLogger("llm_client").setLevel(logging.WARNING)
        logging.getLogger("agent").setLevel(logging.WARNING)
```

**エラー内容**（`-v` なしで実行したときの実際の画面）:
```text
02:04:55 INFO report_agent.orchestrator: 調査計画を作成中: …
02:04:55 INFO httpx: HTTP Request: POST https://api.anthropic.com/v1/messages "HTTP/1.1 200 OK"
02:04:55 INFO report_agent.orchestrator: 調査計画: 問い1個 / 見出し1個
02:04:55 INFO httpx: HTTP Request: POST https://api.anthropic.com/v1/messages/count_tokens "HTTP/1.1 200 OK"
```

**原因**: `logging.basicConfig(level=logging.INFO)` により、httpx ライブラリ自身の INFO ログ（リクエスト1回ごとに1行）も表示される。本文の「通常は進捗（`report_agent.*`）だけを表示し」という説明と L1243 の出力例に反していた。

**修正内容**（原稿に反映済み）:
```python
    if not args.verbose:  # 通常は進捗だけを表示し、1回ごとの通信ログは隠す
        logging.getLogger("llm_client").setLevel(logging.WARNING)
        logging.getLogger("agent").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)  # httpx の通信ログ（INFO）も隠す
```
修正後は、出力例と同じく進捗の行だけが表示されることを確認した。

---

## ⚠️ 要確認のコード

### コードブロック #16（chapter_10.md L895付近: researcher.py ブロック2 / Web検索版）

**懸念点**:
1. `pause_turn` からの再開で、最後のメッセージを assistant（APIが返した content）にして再送している。本文は「prefill とは別物」と説明しているが、2026-10-21 版では「最後を assistant で終えると400」という規則（claude-api-facts.md）があり、`pause_turn` の再開がこの例外として認められているかを一次情報で確認できていない。偽APIはこの形を prefill として 400 にするため、単体試験は MockTransport で行った（コードの処理自体は期待どおり）。
2. `web_search_20260209` を `claude-haiku-5-5`（RESEARCHER_MODEL）で使えるか、`max_uses` の指定方法、`usage.server_tool_use.web_search_requests` のフィールド名も、偽APIでは確かめられない。

**推奨対処**: `/factcheck book 10` で Tool use 概要（サーバーツールと `pause_turn`）・Web検索ツールのページを確認する。再開時の送り方が変わっていれば、`research_web()` の `messages.append(...)` の行と本文の説明を合わせて直す。

---

## 🔍 構文チェックのみ（照合）

| # | 位置 | 言語 | 内容 | 結果 |
|---|-----|-----|-----|-----|
| 1 | L127 | text | workspace/runs の構成 | 実行後のフォルダ（plan.json・notes/・drafts/・reviews/・report.md・cost.json）と一致 |
| 2 | L159 | text | 本章で追加するファイル | 組み立てた構成と一致 |
| 17 | L979 | markdown | Web検索版メモの出力例 | `research_web()` が作る見出し「## 出典一覧（citations から自動生成）」と一致 |
| 23 | L1273 | jsonc | review_v1.json の出力例 | コメント行を除いて JSON として正しい。キー（scores・issues・needs_research・summary・passed）は実際の出力と一致 |
| 24 | L1292 | jsonc | cost.json の出力例 | JSON として正しい。キーは実際の出力と一致 |
| 27 | L1353 | bash | `uv add --dev pytest` | 未実行（ネットワークを使うため）。コマンドの書式は正しい |

---

## ✅ 動作確認済みコード一覧

| # | 位置 | 言語 | 行数 | 実行結果 |
|---|-----|-----|-----|--------|
| 3 | L196 | bash | 2 | フォルダ作成 |
| 4 | L204 | python | 50 | RunWorkspace が safe_path 経由で runs/<ID>/ に保存 |
| 5 | L271 | python | 79 | make_plan（effort low + json_schema、問い数の切り詰め） |
| 6 | L366 | python | 33 | Budget（tracker.total_usd との差分・検索料金の加算） |
| 7 | L414 | python | 53 | 委譲ツールのスキーマ登録 |
| 8 | L478 | python | 76 | _guarded（ロック・予算確認・役割別コスト） |
| 11 | L758 | markdown | 6 | 試用の資料として使用 |
| 12 | L767 | markdown | 5 | 試用の資料として使用 |
| 13 | L777 | python | 89 | search_local_docs・fetch_page（偽HTMLの本文抽出） |
| 14 | L879 | bash | 2 | 出力が本文の例と完全一致 |
| 15 | L884 | text | 2 | 同上 |
| 18 | L997 | python | 46 | write_draft（題の行の補完を含む） |
| 19 | L1056 | python | 70 | review_draft（スキーマ・点数の丸め・合否のコード判定） |
| 21 | L1234 | bash | 2 | 台本化した偽APIで終了コード0、成果物一式を出力 |
| 22 | L1243 | text | 17 | 出力の形式（ログ行・コスト表・tracker.summary）が一致（#20 修正後） |
| 25 | L1309 | bash | 2 | `--source web` の配線（偽APIは web_search を実行しない） |
| 26 | L1327 | python | 19 | set_transport で同期・非同期の両方に MockTransport が入る |
| 28 | L1358 | toml | 4 | pytest が pythonpath・testpaths を読む |
| 29 | L1371 | python | 62 | テストの道具（install・isolated） |
| 30 | L1442 | python | 71 | テスト5件 |
| 31 | L1524 | bash | 2 | `pytest -q` → 5 passed（偽APIなし・キーなし） |
| 32 | L1529 | text | 2 | 件数が一致 |

---

## 補足（検証環境についての注意。原稿の問題ではない）

- 共有の偽API（`mock/sitecustomize.py`）は `kwargs.setdefault("transport", ...)` で差し込むため、本章の `_get_async_client()` のように **`transport=None` を明示して** `httpx.AsyncClient` を作ると偽APIに繋がらない。最初の CLI 実行では、非同期の1回が本物の `api.anthropic.com` に送られ、偽キーのため 401 で止まった（料金は発生しない）。本検証では `transport is None` も置き換える専用のラッパーを作業フォルダに用意して実行した。第10章以降のコードを共有の偽APIで動かす場合は、sitecustomize を `if kwargs.get("transport") is None:` で置き換える形に直すことを推奨する。
- 第8章の `llm_client.py` 非同期版は、検証開始時点では `_is_retryable(status)`・`_retry_delay(attempt, headers)` を同名で再定義しており、第4章の同名関数（引数が `APIError`・`Response`）を上書きして同期版のリトライを壊す内容だった。検証中に第8章が更新され、第4章の関数をそのまま使う形になったため、更新後の版で組み立て直し、本章のテスト・CLI がすべて動くことを確認した。

> ⚠️ **検証の限界**: 実際の Claude API（モデルの応答内容・Web検索・`pause_turn` の発生）は検証していません。公開前に実APIで `--source local` と `--source web` を1回ずつ実行して確認してください。

---

## ⚠️対応（2026-11-07）

| # | 項目 | 対応 |
|---|-----|-----|
| 16 | `pause_turn` 再開時に最後のメッセージが assistant になる点／`web_search_20260209` の対応モデル・`max_uses`・`usage.server_tool_use.web_search_requests` | **未修正（一次情報の確認待ち）**。偽APIでは判定できないため本文は変更しない。**`/factcheck book 10` で Tool use 概要（サーバーツールと `pause_turn`）と Web検索ツールのページを確認すること**。再開時の送り方が変わっていれば `research_web()` の `messages.append(...)` の行と本文の説明を合わせて直す |

- 本章のほかの ⚠️ はなし（❌3件は前回修正済み）。件数表は変更なし（⚠️ 1個のまま）。
- 第11章の⚠️対応で `report_agent/researcher.py`（`untrusted_tools`）と `report_agent/cli.py`（`setup_logging()` を `basicConfig` の後で呼ぶ）を組み立て直したあとも、本章の `pytest -q`（偽APIなし・キーなし）が `5 passed`、CLI（台本化した偽API）が終了コード0で、画面の進捗ログが本章 L1243 の出力例どおりに出ることを再確認した。
- 第8章の並行修正（`Agent` が第6章の実行前確認・第7章のキャッシュを再利用し、agent.py は「追記」）について: 本章が使う `Agent(name=..., system=..., registry=..., model=..., effort=..., max_turns=...)`・`arun()`・`async_handlers` は変わらない方針のため、本章の原稿は変更していない。第8章の更新が確定したら、本章の CLI と `pytest` をもう一度通すことを推奨（特に、実行前確認が `input()` を呼ぶ形になる場合、本章の researcher／オーケストレーターのツールはすべて読み取り系・委譲ツールなので確認は出ない想定だが、`side_effect` の既定値の扱いを確認すること）。

---

## 第8章確定版での再検証（2026-11-07）

### 再組み立ての方法
- 確定版の chapter_06〜08.md から `agent.py` を組み直した。順番は、6.2版 → 6.3（`run_one_tool`・並列版）→ 6.4（`ask_approval`・最終形の `execute_tool_uses`）→ `build_registry()`（`register_file_tools` 込み）→ 第7章版 `run_agent` → 第8章の Agent クラス（追記）。第8章の非同期版ブロックの `async_handlers` とメソッドは同じクラスに統合した。
- `llm_client.py`（第4・7・8章＋第10章の `set_transport`）、`tool_registry.py`・`tools/`・`context.py` も最新版から組み直した。前回の組み立てとの差分はなかった。
- Agent の公開インターフェースは変わっていない（属性 `name, system, registry, model, effort, max_turns, async_handlers`、メソッド `run`・`arun`）。新しい内部は、`_request_kwargs` が `cached_system`/`cached_tools` を使い、`_aexecute_tools` が `async_handlers` 以外のツールを `asyncio.to_thread(execute_tool_uses, ...)` で `registry.execute` に通す形。

### 結果
| 確認 | 結果 |
|-----|-----|
| `pytest -q`（偽APIなし・キーなし） | `5 passed` |
| CLI `--source local`（`-v` なし、台本化した偽API） | 終了コード0。成果物一式を出力 |
| CLI `-v` あり | 終了コード0。`llm_client` の行が15回分、画面に出た。`cache_read` が正になる呼び出しもあり、第7章のキャッシュ区切りが効いている |

### ❌→修正: `fetch_page` の失敗が「予期しないエラー」扱いになる（chapter_10.md L858付近）
- **現象**: 第8章の Agent は、通常のツールを第6章の `run_one_tool()` 経由で実行する形になった。`run_one_tool()` は `ToolError` 以外の例外を「想定外」として扱う。そのため、`fetch_page` の `ValueError`（URLの誤り）と httpx の例外（404・接続失敗）は、次のようになった。
  1. `-v` なしでも、画面に `ERROR agent: tool=fetch_page unexpected error` とトレースバックが出る（本文の「通常は進捗だけを表示」に反する）。
  2. モデルには「予期しないエラー（ValueError）」という定型文だけが返り、「http(s) で始まるURLを」という理由が伝わらない。
- **修正**（原稿に反映）:
  - import を `from tool_registry import ToolError, ToolRegistry` に変更。
  - URL の誤りを `raise ToolError(...)` に変更。
  - `httpx.get` と `raise_for_status()` を `try` で囲み、`except httpx.HTTPError as exc: raise ToolError(f"ページを取得できませんでした: {exc}") from exc` を追加。
  - `fetch_page()` の説明段落に「URLの誤りや取得の失敗は `ToolError` にしているので、第6章の `run_one_tool()` が理由を `is_error` 付きでモデルへ返します」を1文追加。
- **確認**: 修正後の画面表示は `WARNING agent: tool=fetch_page error=http(s) で始まるURLを指定してください` の1行だけで、トレースバックは0件。モデルへは `エラー: http(s) で始まるURLを…` が `is_error: true` で返る。`pytest` は 5 passed、CLI は終了コード0。
- **件数表**: 変更なし。#13 は修正後に再実行し、✅のまま。

### 残り
- #16（`pause_turn` 再開時の送り方・Web検索ツールの仕様）は、前節のとおり `/factcheck book 10` での確認待ち。
