# コード検証レポート（再検証）

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_10.md
検証日: 2026-11-08
コードブロック数: 32個（python 15 / bash 6 / text 5 / markdown 3 / jsonc 2 / toml 1）
  ✅ 動作確認済み: 24個
  ⚠️ 要確認: 1個
  ❌ エラーあり: 0個
  🔍 構文チェックのみ: 7個

## 前回からの経緯

- 午前の検証で ⚠️ が2件あった。#16 は `server_tool_use` が null のとき `AttributeError` になる件、#22 は出力例の最終行が地の文になっていた件。再チェックでは、さらに L505（現 L513）のコメントの不一致も見つかった。
- 3件とも原稿で修正済み（L933〜934、L1276、L513）。今回、現在の原稿から組み立て直して、修正後の動作を確認した。

## 検証環境と方法

- Python 3.12.7 / uv 0.13.5 の venv（httpx 0.28.1・python-dotenv・pytest 9.2.0）。実APIキーは使わず、外部への通信もない。
- 第4〜10章の現在の原稿からコードブロックを抽出し直した。前回の抽出物は使っていない。プロジェクトも新しいフォルダに組み立て直した。
  - `llm_client.py`: 第4章の完成版、第7章の追加、第8章の非同期版、本章の `set_transport()`／`_get_async_client()`。
  - `agent.py`: 第6章（6.2・6.3・6.4）、第7章の `run_agent`、第8章の `Agent`（同期版＋`async_handlers`／`arun`）。
  - `tool_registry.py`（6.3 の `validate_input` 付き `execute`）・`tools/`・`context.py`。
- 本章のコードは、本文の手順どおりに配置した。
  - `report_agent/` の6ファイル。orchestrator はブロック1〜6を順に連結した（ブロック5・6はクラス内の続き。L580 の指示どおり）。
  - `tests/test_report_agent.py`（ブロック1＋2）。
  - `pyproject.toml` の末尾に pytest の設定を追記した。
  - `workspace/sources/` に資料2つを置いた。
- 実行したこと:
  1. `pytest -q`（APIキーなし）→ `5 passed`。L1545 の出力例と件数・形式が一致した。
  2. `search_local_docs('コストが増える原因')` → L896〜897 の出力例と完全に一致した。
  3. CLI `main(["テーマ","--budget","1.0"])` を、台本付きの偽APIで実行した。偽APIは system プロンプトで役割を見分ける。台本の流れは次のとおり。計画 → 調査（並列2本、各1回 `search_local_docs`）→ 執筆 → 採点（evidence=3 で不合格）→ 書き直し → 再採点（合格）→ 終了。
     - 結果: 終了コード0。`plan.json`・`notes/`・`drafts/`・`reviews/`・`report.md`・`cost.json` を出力した。判定は「合格」、`draft_versions: 2`。
     - 画面に出たのは `report_agent.*` の進捗だけだった（httpx・llm_client・agent の INFO 行は0件）。偽APIへの仕様違反（temperature・prefill）も0件。
  4. `--budget 0` → `report_agent: error: --budget には正の数を指定してください`。
  5. `research_web()` の単体試験（MockTransport）。1回目は `pause_turn`、2回目は `end_turn` を返す。`usage.server_tool_use` を3通りに変えて確かめた。
     - 通常値（`web_search_requests: 2` ×2回）: `search_usd 0.04`（4回×$0.01）。
     - `null`: 例外なしで `search_usd 0.0`。
     - キーなし: 例外なしで `search_usd 0.0`。
     - 3通りとも、再開のリクエストに `container: "cntr_1"` が入り、messages は user → assistant の順だった。tools は同じ `WEB_SEARCH_TOOL` で、citations から `## 出典一覧（citations から自動生成）` が作られた。
  6. `pyproject.toml` の `pythonpath` を外して `pytest` を実行した → `ModuleNotFoundError: No module named 'llm_client'`（L1381 の説明どおり）。
  7. `asyncio.Lock` の生成位置: `_orchestrate()` の先頭（L691）で作る。L513 のコメント・L569 の説明と一致する。

## 修正箇所の確認

| 箇所 | 内容 | 結果 |
|---|---|---|
| L933〜934 | `server_use = response["usage"].get("server_tool_use") or {}` | ✅ null・通常値・キーなしの3通りとも正常（上記5） |
| L513 | `# _orchestrate() の中で作る` | ✅ 実装（L691）と本文 L569 に一致 |
| L1276 | 出力例の集計行 `calls=24 input=205,800 output=26,000 cache_write=8,320 cache_read=45,500 total=$0.3920` | ✅ `tracker.summary()` の形式と一致。役割別コストの合計 $0.392 とも合う。ローカル版なので検索料金はなく、「使用金額 $0.392」と一致。第4章の単価表で、実現できる内訳がある（下記） |

**L1276 の金額の照合**（単価は per MTok。Opus $4/$20/書込$5/読込$0.20、Sonnet $2/$10/$2.50/$0.10、Haiku $0.10/$0.50/$0.125/$0.01）:
- 調査（Haiku）: 入力 125,000・出力 12,000・cache_read 20,000 → $0.0187。
- 計画＋オーケストレーター（Opus）: 入力 12,000・出力 1,800・cache_write 2,000・cache_read 13,500 → $0.0967（= $0.0213＋$0.0754）。
- 執筆＋レビュー（Sonnet）: 入力 68,800・出力 12,200・cache_write 6,320・cache_read 12,000 → $0.2766（= $0.1964＋$0.0802）。
- 合計はトークン数・金額とも集計行と一致する。ログの「残り」の推移（$0.957 → $0.921 → $0.812 → $0.768 → $0.661 → 終了時 $0.608）も、各委譲の役割別コストとオーケストレーターの呼び出し分で説明できる。

---

## ❌ エラーが発生したコード

該当なし。

---

## ⚠️ 要確認のコード

### コードブロック #22（chapter_10.md L1275: CLI の出力例「役割別コスト」の最終行）

**元の出力例**:
```text
  オーケストレーター $0.0754
```
**懸念点**: `print_cost_report()` は `f"  {ROLE_LABELS.get(role, role):<10} ${usd:.4f}"` で表示する。「オーケストレーター」は9文字なので、10文字に埋めた後に空白が1つ付き、`$` の前の空白は2つになる。実行結果は `  オーケストレーター  $0.1080` だった。ほかの4行（計画・調査・執筆・レビュー）の空白数は、実際の出力と一致している。午前の版から変わっていない軽微な差。
**推奨対処**: 出力例の空白を2つにする。
```text
  オーケストレーター  $0.0754
```

---

## 🔍 構文チェックのみ（照合）

| # | 位置 | 言語 | 内容 | 結果 |
|---|---|---|---|---|
| 1 | L130 | text | workspace/runs の構成 | 実行後のフォルダと一致 |
| 2 | L162 | text | 本章で追加するファイル | 組み立てた構成と一致 |
| 17 | L994 | markdown | Web検索版メモの出力例 | `research_web()` が作る見出しと一致 |
| 23 | L1289 | jsonc | review_v1.json の出力例 | コメント行を除けば JSON として正しい。キー（scores・issues・needs_research・summary・passed）は実際の出力と一致 |
| 24 | L1308 | jsonc | cost.json の出力例 | JSON として正しい。キーは実際の出力と一致。by_role の合計 0.392 ＝ total_usd |
| 25 | L1325 | bash | `--source web` の実行 | 実APIを使うため未実行。配線は `research_web()` の単体試験で確認 |
| 27 | L1369 | bash | `uv add --dev pytest` | ネットワークを使うため未実行。`uv add --help` で `--dev` オプションがあることを確認 |

> コードブロック外の気づき（件数に数えない）: 本文の表記は一括置換で「フォルダー」になった。一方、コードブロック内のコメントは「フォルダ」のまま（L137 `# 実行ID（日時）ごとのフォルダ`、L205 `（フォルダを2つ作る）`）。動作には影響しない。表記をそろえるなら、コメントも「フォルダー」に直す。

---

## ✅ 動作確認済みコード一覧

| # | 位置 | 言語 | 行数 | 実行結果 |
|---|---|---|---|---|
| 3 | L204 | bash | 2 | フォルダを作成 |
| 4 | L212 | python | 50 | RunWorkspace が safe_path 経由で runs/<ID>/ に保存 |
| 5 | L279 | python | 79 | make_plan（effort low＋json_schema、問いの数の切り詰め） |
| 6 | L374 | python | 33 | Budget（tracker.total_usd との差分、検索料金の加算） |
| 7 | L422 | python | 53 | 委譲ツールのスキーマを登録 |
| 8 | L486 | python | 76 | _guarded（ロック・予算確認・役割別コスト）。L513 のコメントは実装と一致 |
| 9 | L582 | python | 56 | 委譲の本体（クラス内の続きとして連結） |
| 10 | L649 | python | 92 | 補助メソッド・run・_orchestrate（ロックの生成）・_finalize |
| 11 | L766 | markdown | 6 | 試用資料として使用 |
| 12 | L775 | markdown | 5 | 試用資料として使用 |
| 13 | L785 | python | 92 | search_local_docs・fetch_page |
| 14 | L890 | bash | 2 | 出力が本文の例と完全に一致 |
| 15 | L895 | text | 2 | 同上 |
| 16 | L906 | python | 75 | research_web: pause_turn の再開、`server_tool_use` の null・通常値・キーなしの3通りとも正常 |
| 18 | L1012 | python | 46 | write_draft（題の行の補完を含む） |
| 19 | L1071 | python | 70 | review_draft（丸めと、コードによる合否判定） |
| 20 | L1170 | python | 68 | CLI（終了コード0／`--budget 0` は argparse のエラー） |
| 21 | L1250 | bash | 2 | 台本付きの偽APIで終了コード0 |
| 26 | L1343 | python | 19 | set_transport で同期・非同期の両方に MockTransport が入る |
| 28 | L1374 | toml | 4 | pytest が pythonpath・testpaths を読む（外すと ModuleNotFoundError） |
| 29 | L1387 | python | 62 | テスト用の道具（install・isolated） |
| 30 | L1458 | python | 71 | テスト5件 |
| 31 | L1540 | bash | 2 | `5 passed`（APIキーなし） |
| 32 | L1545 | text | 2 | 件数が一致 |

> ⚠️（#22）は件数を ⚠️ に数えた。ログ行・集計行・金額の整合は確認済みで、空白1つの差だけが残っている。

> ⚠️ **検証の限界**: 実際の Claude API（モデルの応答・Web検索・pause_turn の発生・`server_tool_use` が null になるかどうか）は検証していません。公開前に、実APIで `--source local` と `--source web` を1回ずつ実行して確認してください。
