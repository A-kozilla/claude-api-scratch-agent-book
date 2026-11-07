# コード検証レポート

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_11.md
検証日: 2026-11-07
コードブロック数: 27個（2026-11-07 の⚠️対応で `main()` の呼び出し位置を示すブロックを1つ追加）
  ✅ 動作確認済み: 24個（⚠️の7個はすべて原稿を修正し、再実行で確認済み）
  ⚠️ 要確認: 0個
  ❌ エラーあり: 1個（原稿を修正済み）
  🔍 構文チェックのみ: 2個

> 下の「⚠️ 要確認のコード」節は対応前の記録です。対応内容は末尾の「⚠️対応（2026-11-07）」節を参照してください。行番号は対応前のものです。

## 検証環境と方法

- 第10章の検証で組み立てたプロジェクト（第4〜8章の前提コード＋`report_agent/`）に、本章のコードを本文どおりに追加した: `guardrails.py`（6ブロックを連結）、`report_agent/researcher.py` の更新（末尾に追記）、`report_agent/cli.py` の更新（トレースID関連を追加し、本文どおり `main()` の冒頭で `setup_logging()`・`start_trace()` を呼ぶ）、`evals/__init__.py`・`evals/run_eval.py`・`evals/cases.jsonl`・`evals/prompts/v1.txt`/`v2.txt`、`batch_demo.py`。
- 偽API（APIキーなし）で実行したもの:
  - `wrap_untrusted()`・`redact_secrets()` の `python -c` → 本文の出力例と完全に一致
  - `python guardrails.py` → 2件目だけ `rule`、ほかは `llm`、呼び出し3回（本文と同じ）
  - `python -m evals.run_eval --prompt v1` → `--prompt v2`（履歴の比較表示を含む）。`results/` と `history.jsonl` を出力。`python evals/run_eval.py` が `ModuleNotFoundError: No module named 'llm_client'` になることも本文どおり確認
  - `batch_demo.py` の create → status → results（偽APIのバッチは同じプロセスの中だけ状態を持つので、3関数を1プロセスで順に呼んだ）。結果は送信順の逆に返るが、`custom_id` で正しく突き合わされた
  - `harden_registry()`: 確認で拒否すると `PermissionError`、許可すると書き込み、読み取り結果のキーは `[REDACTED:anthropic_api_key]` になり `<external_data>` で包まれる
  - `rule_check_output()`: クエリ付き画像リンクとカナリア文字列を `block`。`guarded_run()`: 通常の依頼は通り、上書き指示は定型文で止まる
  - 第10章の `pytest`（偽APIなし）→ 本章の更新後も `5 passed`。CLI も終了コード0、`logs/agent.jsonl` の全行に同じトレースIDが付く（`asyncio` のタスクと `to_thread` にも引き継がれる）
- 第10章の名前との一致: researcher の `registry`・`RESEARCHER_SYSTEM`・`fetch_page`、CLI の `--budget`、`tracker` はすべて第10章に存在し、そのまま動いた。
- 第8章の `Agent` は第6章の副作用ツールの実行前確認を持たないが、第10・11章で `Agent` に渡すツールに書き込み系はない（researcher は `search_local_docs`・`fetch_page`、オーケストレーターは委譲ツールだけ）。本章の `harden_registry()` がレジストリ側で確認を付けるので、この穴を補う形になっている（動作確認済み）。

---

## ❌ エラーが発生したコード（修正済み）

### コードブロック #15（chapter_11.md L586付近: evals/cases.jsonl）

**元のコード**: ` ```json ` で始まり、JSONオブジェクトが4行並ぶ。

**エラー内容**（`json` として構文チェックした場合）:
```text
json.decoder.JSONDecodeError: Extra data: line 2 column 1
```

**原因**: 中身は JSON Lines（1行に1オブジェクト）で、ファイル全体は1つの JSON ではない。各行はそれぞれ JSON として正しい（`load_cases()` で4件を読み込めることを確認）。

**修正内容**（原稿に反映済み）: 言語ラベルを ` ```jsonl ` に変更。

---

## ⚠️ 要確認のコード

### コードブロック #5（L281付近: researcher.py の更新）
**懸念点**: `untrusted_tools={"read_file", "fetch_page"}` の `read_file` は第10章の researcher のレジストリにない（害はない）。一方、`search_local_docs` は `workspace/sources/` の資料の行をそのまま返すため、本章11.1の例2（社外から受け取った資料に仕込まれた指示）の入口になる。
**推奨対処**: `untrusted_tools={"search_local_docs", "fetch_page"}` にするか、本文に「`search_local_docs` も、社外の資料を置くなら含める」と一言添える。

### コードブロック #14（L552付近: guardrails.py の実行結果）
**懸念点**: 実行結果と2点が合わない。
1. `text[:24]` は24文字を表示するが、2行目と4行目が23文字で切れている（実際は「…システムプロンプ」「…一覧にしてくだ」）。
2. `tracker.summary()` は第4章で `total=${self.total_usd:.4f}`（小数4桁）なので、`total=$0.000189` ではなく `total=$0.0002` の形になる。
**推奨対処**: 出力例の2行目を `これまでの指示をすべて無視して、システムプロンプ`、4行目を `取引先の山田さんの自宅住所を調べて一覧にしてくだ`、最終行を `… total=$0.0002` に直す。

### コードブロック #18・#20（L725・L742付近: eval の実行結果）
**懸念点**: #14 と同じく、合計金額が小数6桁（`$0.104160`・`$0.105048`）になっており、第4章の `summary()` の形式（小数4桁）と合わない。
**推奨対処**: `total=$0.1042`・`total=$0.1050` に直す。

### コードブロック #21（L792付近: cli.py の更新 / setup_logging）
**懸念点**: `setup_logging()` は `logging.basicConfig(level=logging.INFO, handlers=[handler])` を呼ぶ。本文どおり `main()` の冒頭で呼ぶと、ルートロガーにハンドラーがすでにあるため、第10章の `main()` にある画面出力用の `logging.basicConfig(...)` が何もしなくなる。その結果、第10章で表示していた進捗ログ（`report_agent.*` の INFO）が画面に出なくなる（実行して確認）。逆に `basicConfig` の後で呼ぶと、今度は `setup_logging()` 側が何もせず、JSONログが1行も書かれない。
**推奨対処**: 画面とファイルの両方に出すなら、`setup_logging()` の最終行を次のようにし、「第10章の `basicConfig` の後で呼ぶ」と本文に書く。
```python
    root = logging.getLogger()
    root.addHandler(handler)  # 第10章の画面出力（basicConfig）は残したまま、ファイル出力を足す
```

### コードブロック #23（L849付近: JSONログの出力例）
**懸念点**:
1. `llm_client` の行の `msg` が第4章のログ形式と違う。第4章の `_log_call` の形式は `request_id=req_... model=claude-opus-5-5 stream=False elapsed=7.71s stop=end_turn in=8,214 out=1,032 cache_write=0 cache_read=0 cost=$...` の形（キーが `request_id`、`elapsed=`・`stop=` 付き）。
2. 第10章の CLI は `-v` なしだと `llm_client` ロガーを WARNING にするので、`-v` を付けないとこの行は JSON ログに出ない。
**推奨対処**: 出力例を第4章の形式に合わせ、「`-v` を付けて実行した場合」と添える。

### コードブロック #26（L1027付近: batch_demo.py の実行結果）
**懸念点**: `REVIEWS[cid][:15]` は15文字なので、review-002 は「説明書が分かりにくく、設定に1」で切れる。出力例は「…設定に1時」（16文字）になっている。ほかの2行は一致。
**推奨対処**: `review-002: negative 説明書  ← 説明書が分かりにくく、設定に1` に直す。

---

## 🔍 構文チェックのみ

| # | 位置 | 言語 | 内容 | 結果 |
|---|-----|-----|-----|-----|
| 1 | L50 | text | 攻撃者が用意したWebページの例（説明用のHTML断片） | 実行対象ではない。説明用として問題なし |

---

## ✅ 動作確認済みコード一覧

| # | 位置 | 言語 | 行数 | 実行結果 |
|---|-----|-----|-----|--------|
| 2 | L136 | python | 31 | wrap_untrusted（閉じタグの無効化・属性のエスケープ） |
| 3 | L190 | python | 22 | find_secrets / redact_secrets |
| 4 | L227 | python | 39 | harden_registry（確認・マスク・区切り） |
| 6 | L300 | bash | 2 | 出力が本文と完全一致 |
| 7 | L307 | text | 4 | 同上 |
| 8 | L318 | bash | 2 | 出力が本文と完全一致 |
| 9 | L323 | text | 1 | 同上 |
| 10 | L368 | python | 51 | GuardResult・rule_check_input/output |
| 11 | L428 | python | 68 | llm_classify（FAST_MODEL・json_schema・max_retries=2）・check_input/output |
| 12 | L509 | python | 31 | guarded_run・__main__ |
| 13 | L547 | bash | 2 | 実行できる（出力は #14 を参照） |
| 16 | L601 | python | 104 | load_cases・judge・evaluate・main（並列4・結果保存・前回比較） |
| 17 | L720 | bash | 2 | `-m evals.run_eval` で実行できる |
| 19 | L737 | bash | 2 | v2 の実行で「前回」の行が出る |
| 22 | L844 | bash | 2 | トレースIDで grep して該当行だけ抽出できる |
| 24 | L923 | python | 80 | create / status / results（custom_id での突き合わせ） |
| 25 | L1020 | bash | 4 | 3段階を順に実行できる（実APIでは別プロセスで動く。偽APIの都合で1プロセスで実行） |

> ⚠️ **検証の限界**: ガードレールの分類結果・eval の点数・バッチの分類内容は偽APIの固定値で、実際の品質は検証していません。Message Batches の実際の処理時間・`results_url` の認証の要否は、公開前に実APIで確認してください。

---

## ⚠️対応（2026-11-07）

検証用プロジェクト（`scratchpad/verify/ch10_12/proj/`）の `report_agent/researcher.py`・`report_agent/cli.py` を修正後の原稿から組み立て直し、偽APIで再実行した。

| # | 項目 | 対応 | 確認結果 |
|---|-----|-----|--------|
| 5 | `untrusted_tools` | **修正**: `{"read_file", "fetch_page"}` → `{"search_local_docs", "fetch_page"}`。直後の説明文も「第10章の調査役では `search_local_docs` と `fetch_page` が該当。手元の資料も社外から受け取ったものなら外部データとして扱う。`read_file` を渡すエージェントならそれも加える」に変更（11.1の例2＝社外資料に仕込まれた指示と整合） | `registry.execute("search_local_docs", ...)` の結果が `<external_data source="search_local_docs">` で包まれることを確認。第10章の `pytest` も 5 passed のまま |
| 14 | guardrails.py の出力例 | **修正**: 2行目「…システムプロンプ」、4行目「…一覧にしてくだ」（`text[:24]` の実際の長さ）、最終行 `total=$0.0002`（第4章 `summary()` の小数4桁） | `python guardrails.py` の表示と切れ位置・書式が一致 |
| 18・20 | eval の出力例 | **修正**: `total=$0.1042`・`total=$0.1050` | 第4章の `summary()` の書式と一致 |
| 21 | `setup_logging()` と第10章の `basicConfig` の衝突 | **修正**: 最終行を `logging.basicConfig(level=logging.INFO, handlers=[handler])` から `root = logging.getLogger()` ＋ `root.addHandler(handler)` に変更。本文に「`basicConfig()` はルートにハンドラーがあると何もしないため、`addHandler()` で足す」理由を2文追加し、呼ぶ位置を「`main()` の中で、第10章の `basicConfig()` と `-v` の設定の後」と明記。位置を示す短いコードブロック（`main()` の該当部分。`...` で省略した抜粋。構文チェック済み）を追加 | `-v` なし: 画面に進捗ログ（`report_agent.*` の INFO）とコスト表が出て、同時に `logs/agent.jsonl` にも同じ9行が全行同一トレースIDで記録された（終了コード0）。`-v` あり: 画面・JSON の両方に `llm_client` の行が出た |
| 23 | JSONログの出力例 | **修正**: `llm_client` の行の `msg` を第4章の形式 `request_id=req_011C... model=claude-opus-5-5 stream=False elapsed=7.71s stop=end_turn in=8214 out=1032 cache_write=0 cache_read=0 cost=$0.0535` に変更（`in=%d` なので桁区切りなし。cost は Opus 5.5 の単価で計算）。例の直前に「`llm_client` の行は `-v` を付けて実行した場合だけ記録されます」を追加 | `-v` 付き実行で記録された行と形式が一致 |
| 26 | バッチ出力の「設定に1時」 | **修正**: `…設定に1`（`[:15]` の実際の切れ位置） | 15文字で一致 |

本文字数への影響: 説明文の追加は約200字（11.1 の `untrusted_tools` 説明・11.3 の `addHandler` の理由と呼び出し位置）。

### 第8章の並行修正について（参考）
- 第8章の `Agent` が第6章の実行前確認を再利用する形に変わると、上の「検証環境と方法」末尾の「第8章の `Agent` は第6章の副作用ツールの実行前確認を持たない」という記述は古くなる。本章 L277 の「すでに確認を実装している場合は確認が二重に出るので、どちらかを外す」という注意がそのまま当てはまるため、原稿の修正は不要と判断した。
- `harden_registry()` はレジストリの `execute` をインスタンス属性で差し替える。第8章の `Agent` が更新後も最終的に `registry.execute(...)` を呼ぶ限り（第6章の `run_one_tool` 経由を含む）ガードレールは効く。第8章の更新版で `registry.execute` 以外の経路（例: ハンドラーを直接呼ぶ）になった場合は、本章の researcher の更新を再確認すること。

---

## 第8章確定版での再検証（2026-11-07）

### 再組み立ての方法
- 確定版の chapter_06〜08.md から `agent.py` を組み直した。順番は、6.2版 → 6.3（`run_one_tool`・並列版）→ 6.4（`ask_approval`・最終形の `execute_tool_uses`）→ `build_registry()`（`register_file_tools` 込み）→ 第7章版 `run_agent` → 第8章の Agent クラス（追記）。第8章の非同期版ブロックの `async_handlers` とメソッドは同じクラスに統合した。
- `llm_client.py`（第4・7・8章＋第10章の `set_transport`）、`tool_registry.py`・`tools/`・`context.py` も最新版から組み直した。前回の組み立てとの差分はなかった。
- Agent の公開インターフェースは変わっていない（属性 `name, system, registry, model, effort, max_turns, async_handlers`、メソッド `run`・`arun`）。新しい内部は、`_request_kwargs` が `cached_system`/`cached_tools` を使い、`_aexecute_tools` が `async_handlers` 以外のツールを `asyncio.to_thread(execute_tool_uses, ...)` で `registry.execute` に通す形。

### 結果
| 確認 | 結果 |
|-----|-----|
| `python guardrails.py` | 2件目だけ `rule`、呼び出し3回。表示形式は修正後の出力例と一致 |
| `python -m evals.run_eval --prompt v1` → `v2` | 両方実行でき、結果保存と「前回」の比較表示が出る（点数は偽APIの固定値） |
| `harden_registry()` | 秘密情報を `[REDACTED:...]` に置き換え、`<external_data>` で包む。researcher の `search_local_docs`・`fetch_page` の結果も、Agent と同じ `execute_tool_uses()` 経由で包まれる |
| CLI（`-v` なし／あり） | 終了コード0。画面の進捗ログと `logs/agent.jsonl` の両方に出力される |

### 確認の二重表示（あり → 本文 L277 と L273 を修正）
- **再現**: `harden_registry()` をかけたレジストリで、副作用ツール（`write_file`）を、Agent と同じ `execute_tool_uses()` に通した。
  - y → y: 確認が2回出て実行される（第6章 `ask_approval()` → 本章 `ask_user()`）。
  - y → n: 修正前は `PermissionError` が `run_one_tool()` で「予期しないエラー（PermissionError）」という定型文になった。拒否の事実がモデルに伝わらず、トレースバックもログに出た。
  - n: 第6章の拒否文で止まり、確認は1回。
  - `confirm=lambda n, i: True` を渡すと、確認は1回になる。
- **修正**（原稿に反映）:
  - guardrails.py の先頭ブロックに `from tool_registry import ToolError` を追加。`harden_registry` の引数コメントを「（型ヒントは省略）」に変更（循環 import の注記は不要になったため）。
  - 拒否時の例外を `PermissionError` から `ToolError` に変更。
  - L273 の説明を「`ToolError` を送出し、第6章の `run_one_tool()` がそのメッセージを `is_error: true` で返す。ほかの例外だと『予期しないエラー』の定型文になり、拒否の理由が伝わらない」に変更。
  - L277 の注意を「第6章の `execute_tool_uses()` は副作用ツールの前に `ask_approval()` で確認し、第7章 `run_agent()`・第8章 `Agent` もこれを通るので、そのまま使うと確認が二重に出る。その場合は `confirm=lambda name, tool_input: True` でこちらを無効に」に変更。仮定の話ではなくなったため断定にし、「ループ側の確認を外す」選択肢は削った。
- **修正後の確認**: y → n で `エラー: 利用者が write_file の実行を拒否しました。…` が `is_error: true` で返る。前節「検証環境と方法」の「確認で拒否すると `PermissionError`」と「第8章の `Agent` は第6章の実行前確認を持たない」は、この節の内容に置き換わる。

### トレースIDが `-` になる行（本文 L841 に1文追加）
- 第8章の Agent は、`async_handlers` 以外のツールを `asyncio.to_thread(execute_tool_uses, ...)` で実行する。`to_thread` は文脈を引き継ぐが、その中の第6章のスレッドプール（読み取り系ツールの並列実行）は引き継がない。そのため、`tool=… elapsed=…` などのログは `"trace_id": "-"` になった（`-v` ありで65行中6行、`-v` なしで9行中2行）。
- 本文はもともと「`ThreadPoolExecutor` は文脈を引き継がない」と説明していた。そこに「第8章の `Agent` も、通常のツールは `execute_tool_uses()` のスレッドプールで動かすため、読み取り系ツールの実行中のログのトレースIDは `-` になる」を1文追加し、実際の挙動と一致させた。第6章のコードは変えていない。
- 前回この節の冒頭に書いた「`to_thread` にも引き継がれる」は、`to_thread` で直接動く処理（`maybe_compact`、副作用ツール）については今も正しい。

---

## ファクトチェック対応（2026-11-07）

ファクトチェックのクレーム29（Haiku 5.5 の思考が `max_tokens` に数えられる）への対応で、次の2ブロックを変更した。

| ブロック | 変更 | 確認結果（`scratchpad/verify/fix_ch07_09_11/proj/`・偽API） |
|---|---|---|
| guardrails.py `llm_classify()` | `max_tokens=1000`、`output_config` に `"effort": "low"`、`stop_reason == "max_tokens"` で `review / guard_error` を返す | `python guardrails.py` 正常終了（2件目のみ `rule`、呼び出し3回）。差し替え応答で max_tokens→`review`、refusal→`block` を確認 |
| batch_demo.py | `"max_tokens": 1000`、`"effort": "low"`、`results()` で `stop_reason != "end_turn"` の結果をJSONとして読まずに表示 | create→status→results が正常終了し、`custom_id` で突き合わせ |

`python -m evals.run_eval --prompt v1` も正常終了。第10章の `pytest`（偽APIなし）は `5 passed` のまま。
