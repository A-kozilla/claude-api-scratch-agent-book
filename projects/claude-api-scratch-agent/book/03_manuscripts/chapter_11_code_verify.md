# コード検証レポート（再検証）

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_11.md
検証日: 2026-11-08
コードブロック数: 27個（python 11 / bash 7 / text 8 / jsonl 1）
  ✅ 動作確認済み: 25個
  ⚠️ 要確認: 0個
  ❌ エラーあり: 0個
  🔍 構文チェックのみ: 2個

---

## 前回からの経緯

- 午前の検証では ⚠️ が3件あった。#18・#20 は、eval の出力例で問題のない行の末尾に `[]` が付いていた件。#24 は、JSONログ例の `guardrails` の行が、本章の CLI への組み込み方では出力されない件。
- 原稿の修正内容は次のとおり。#18・#20 は `[]` を削除。#24 は、1行目を `report_agent.orchestrator` の進捗行に、2行目を Sonnet の `llm_client` の行に差し替え、L867 の説明も修正した。今回、現在の原稿から組み立て直して照合した。

## 検証環境と方法

- Python 3.12.7 の隔離した venv（httpx 0.28.1・python-dotenv）と、pytest 入りの venv（第10章と共用）を使った。実APIキーは使わず（`ANTHROPIC_API_KEY=sk-ant-dummy`）、外部への通信もない。
- 現在の原稿からコードブロックを抽出し直した。前回の抽出物は使っていない。
  - `llm_client.py`・`tool_registry.py`: 第4・6・7・8・10章の原稿から組み立てた版（第10章の検証と同じもの）。
  - `guardrails.py`: #2・#3・#4・#10・#11・#12 を本文の順に連結した。
  - `evals/`: `__init__.py`（空）、`run_eval.py`（#16）、`cases.jsonl`（#15）、`prompts/v1.txt`・`v2.txt`。v2 は v1＋`UNTRUSTED_DATA_POLICY`（L739 の手順どおり）。
  - `batch_demo.py`: #25。
- 偽APIには `httpx.MockTransport` を使った。
  - `/v1/messages`: 審査・採点・回答・レビュー分類の応答を、system プロンプトで切り替える。usage は Haiku で 384/49 tok。
  - `/v1/messages/batches`: 作成 → 1回目 `in_progress` → 2回目 `ended` と進む。`results` は送信順の逆に返す。
  - ハンドラー内で次の4点を assert した: `x-api-key` があること、`anthropic-version: 2026-10-21` であること、`temperature` がないこと、`custom_id` が `^[a-zA-Z0-9_-]{1,64}$` に合うこと。
- **第10章の CLI への組み込みも通しで実行した。** 第10章の検証で組み立てたプロジェクトを複製し、本文の手順どおりに次の3つを入れた。
  - #5 を `report_agent/researcher.py` の末尾に追記した。
  - #21 を `report_agent/cli.py` に追加した。
  - #22 のとおり、`main()` の `-v` の設定の直後に `setup_logging()`・`start_trace()` を入れた。
  - その状態で `pytest -q` を実行すると `5 passed`。台本付きの偽APIで CLI を `-v` 付きで実行すると、終了コード0だった。

---

## ❌ エラーが発生したコード

該当なし。

---

## ⚠️ 要確認のコード

該当なし。

---

## 修正箇所の確認

| 箇所 | 内容 | 結果 |
|---|---|---|
| #18（L729）・#20（L746） | eval の出力例から `[]` を削除 | ✅ L692 の `{r.get('problems') or ''}` の実行結果と一致した。問題のない行は `PASS basic-001    score=5`（末尾は空白1つで、見た目では分からない）。問題がある行は `FAIL safety-001   score=5 ['禁止語あり:evil.example']`。v2 の実行では `前回 <run_id>_v1: 合格率 75%  平均 …` の行も出る |
| #18・#20 の数値 | 平均・合計金額 | ✅ 平均は 5,4,5,2 → 4.0、5,4,5,5 → 4.75 で一致。`JUDGE_MODEL = MODEL`（L617）なので、回答・採点の8回はすべて Opus になる。$0.1042 は 6,480×$4＋3,912×$20、$0.1050 は 6,912×$4＋3,870×$20（per MTok）で、表示の値と合う |
| #24（L869） | JSONログ例 | ✅ 統合した CLI を `-v` 付きで実行した。`logs/agent.jsonl` には、`report_agent.orchestrator` の `write を開始（見積もり $0.150 / 残り $…）` の行と、`llm_client` の `model=claude-sonnet-5-5 …` の行が記録された。どちらにも同じトレースIDが付いた（ライターは `acall_messages()` をイベントループ内で呼ぶため）。キーの順序（time・level・logger・trace_id・msg）と区切り（`": "`）も例と一致する。金額 `cost=$0.0267` は Sonnet の 8,214×$2＋1,032×$10（per MTok）＝$0.02675 と合う |
| L860 | `llm_client` の行は `-v` のときだけ記録 | ✅ `-v` なしでは `llm_client` のロガーが WARNING になるので記録されない。`-v` 付きでは15行記録された |
| L845 | スレッドプール内のログはトレースIDが `-` | ✅ 統合実行では、`agent` の `tool=… elapsed=…` の2行だけが `-` になった。それ以外の57行には同じトレースIDが付いた |
| L867 | 「各サブエージェントの進捗やツール実行の行も並びます」 | ✅ 実際の記録（orchestrator・agent・llm_client・`-v` 時は httpx）と合う |

---

## 🔍 構文チェックのみ

| # | 位置 | 言語 | 内容 | 結果 |
|---|-----|-----|-----|-----|
| 1 | L50 | text | 攻撃者が用意したWebページの例（説明用のHTML断片） | 実行対象ではない。説明用として問題なし |
| 22 | L851 | python | `main()` の該当部分（`...` で省略した抜粋） | `py_compile` で構文エラーなし。シグネチャは第10章 `cli.py` と一致。示された位置（`basicConfig()`・`-v` の設定の後）に2行を入れた CLI が、上記のとおり動作した |

> コードブロック外の気づき（件数に数えない）: L122 は、長文を分割した結果「そして、`write_file` を…登録しました。そして、エージェントのループの中で…」と「そして、」が2回続いている。2つ目を「さらに、」などにする案がある。

---

## ✅ 動作確認済みコード一覧

| # | 位置 | 言語 | 行数 | 実行結果 |
|---|-----|-----|-----|--------|
| 2 | L136 | python | 33 | `wrap_untrusted()`: 閉じタグ（`</ EXTERNAL_DATA >` のような変形も）を無効化する。`source` の `"` は `&quot;` にエスケープする |
| 3 | L192 | python | 22 | `find_secrets()`/`redact_secrets()`: Anthropic キー・AWS キーID・秘密鍵の先頭行・Bearer トークンの4種を検出 |
| 4 | L229 | python | 39 | `harden_registry()`: 拒否で `ToolError`（文言どおり）、許可で実行。読み取り結果のキーは `[REDACTED:anthropic_api_key]` になり、`<external_data source="fetch_page">` で包まれる |
| 5 | L283 | python | 8 | 第10章 `researcher.py` の末尾に追記し、統合した CLI と `pytest`（5 passed）で動作を確認 |
| 6・7 | L302・L309 | bash/text | 2・4 | 出力が本文と完全一致 |
| 8・9 | L320・L325 | bash/text | 2・1 | 出力が本文と完全一致 |
| 10 | L370 | python | 51 | `rule_check_input`: 2万字超は `too_long`、キーは `secret_in_input`、英日の上書き表現は `injection`。`rule_check_output`: カナリアは `prompt_leak`、クエリ付き画像は `exfiltration`、クエリなし画像は `None` |
| 11 | L430 | python | 70 | `llm_classify()`（FAST_MODEL・`effort: low`・`json_schema`）。`end_turn` ならスキーマどおり、`max_tokens` なら `review/guard_error`、`refusal` なら `block/harmful` |
| 12 | L513 | python | 31 | `guarded_run()`: 上書き指示は入口で、クエリ付き画像を含む回答は出口で、定型文に置き換える |
| 13・14 | L551・L556 | bash/text | 2・5 | `python guardrails.py` の表示が出力例と5行とも完全一致 |
| 15 | L590 | jsonl | 4 | 4行とも JSON として正しく、`load_cases()` で4件読める |
| 16 | L605 | python | 104 | v1→v2 で `results/*.jsonl` と `history.jsonl` を出力。比較の行も出る |
| 17 | L724 | bash | 2 | `-m evals.run_eval` で実行できる。ファイルを直接指定すると、本文どおり `ModuleNotFoundError: No module named 'llm_client'` |
| 18 | L729 | text | 7 | 形式が実際の表示と一致（上記） |
| 19 | L741 | bash | 2 | v2 の実行で「前回」の行が出る |
| 20 | L746 | text | 8 | 形式が実際の表示と一致（上記） |
| 21 | L796 | python | 42 | `basicConfig()` の後で `setup_logging()` → `start_trace()`。画面とファイルの両方に出力する。子ロガー・`gather` のタスク・`to_thread` の中のログにも同じトレースIDが付く。`ThreadPoolExecutor` の中だけ `-` |
| 23 | L862 | bash | 2 | 統合実行のログに対して、`grep '"trace_id": "<ID>"'` で該当の57行だけを抽出できた |
| 24 | L869 | text | 3 | 形式が統合実行の記録と一致（上記） |
| 25 | L944 | python | 84 | create → status（`in_progress`）→ status（`ended`）→ results。結果の取得にも `x-api-key` と `anthropic-version: 2026-10-21` が付く。逆順に返った結果を `custom_id` で正しく突き合わせる。`errored` は再送候補、`stop_reason=max_tokens` は「確認・再送の候補」と表示 |
| 26・27 | L1045・L1052 | bash/text | 4・7 | 3段階を順に実行できた（偽APIのバッチ状態はプロセス内だけなので、1プロセスで実行）。表示形式（`{sentiment:8}`、`[:15]` で切れる位置「…設定に1」）は出力例と一致 |

> ⚠️ **検証の限界**: ガードレールの分類結果・eval の点数・バッチの分類内容は偽APIの固定値で、実際の品質は検証していません。Message Batches の実際の処理時間、`results_url` の実際の値と認証の挙動は、公開前に実APIで確認してください。
