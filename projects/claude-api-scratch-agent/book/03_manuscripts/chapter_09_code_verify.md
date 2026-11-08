# コード検証レポート（再検証）

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_09.md
検証日: 2026-11-08
検証環境: Python 3.12.7 / uv 0.13.5 の venv / httpx 0.28.1・python-dotenv・pytest 9.2.0（APIキーはダミー、外部への通信なし）
コードブロック数: 22個（python 11 / bash 5 / text 6）
  ✅ 動作確認済み: 22個
  ⚠️ 要確認: 0個
  ❌ エラーあり: 0個
  🔍 構文チェックのみ: 0個

## 前回からの経緯

- 午前の検証（✅22）では、L1366 の合計金額 `$0.0611` がトークン数と合わない件を factcheck 側の ⚠️ として扱った。その後、`$0.0480` に修正された。
- 用語統一の一括置換と長文の分割は、コードブロックの外だけに入っていた。抽出し直したコードブロックは、出力例の1行（L1366）を除いて前回と同一。

## 検証方法

- 第4〜9章の現在の原稿からコードブロックを抽出し直した。前回の抽出物は使っていない。そのうえで、プロジェクトを新しいフォルダに組み立て直した。
  - `llm_client.py`: 第4章の完成版（L1405）、第7章の `count_tokens`・`cached_system`/`cached_tools`、第8章の非同期版。偽APIを差し込むために、第10章の `set_transport()` も加えた。
  - `agent.py`: 第6章の 6.2・6.3・6.4 版、第7章の `run_agent`、第8章の `Agent` クラス（同期版＋非同期版）。第6章は、今回の抽出で `except Exception`・`(ToolError, ValueError)` の版になっている。
  - `tool_registry.py`・`tools/`・`context.py`: 第5〜7章の版。
- 第9章の `patterns/`（4ファイル＋`__init__.py`）と `orchestrator_sketch.py` を、本文（L232〜260）どおりに配置した。実行は、プロジェクトのルートで `python -m patterns.xxx` とした。
- 偽APIには `httpx.MockTransport` を使った。構造化出力を指定されたときは、スキーマに沿ったJSONを返す。先頭には thinking ブロックを付ける。次の仕様違反は 400 で返し、記録する。
  - `temperature`/`top_p`/`top_k`
  - assistant で終わる messages（prefill）
  - Opus/Sonnet への強制 `tool_choice`
  - スキーマの非対応キーワード（`minLength`・`maxLength`・`minimum`・`maximum`・`maxItems`・`multipleOf`・`minItems>1`、`additionalProperties` が false でないオブジェクト）
- 偽APIの固定応答では通らない分岐は、`call_messages`/`acall_messages` を差し替えた18件のシナリオで確かめた。

---

## ❌ エラーが発生したコード

該当なし。

---

## ⚠️ 要確認のコード

該当なし。

---

## 重点確認の結果

| 確認項目 | 結果 |
|---|---|
| 4パターンを `-m` で実行 | ✅ chain（calls=3、haiku→opus→haiku）・router（分類4件）・parallel（calls=8、opus×3＋haiku×5）・evaluator_optimizer。仕様違反はすべて0件 |
| `parse_json_response` | ✅ 先頭に thinking ブロックがあっても text だけを読む。`refusal`・`max_tokens`・不正JSONは、それぞれ `PatternError` になる |
| チェーン | ✅ 価格なしで `抽出ゲートで停止: ['価格がありません']`（L609 と一致）。禁止語は1回書き直して合格（retries=1）。禁止語が残り続けると `執筆ゲートで停止` |
| ルーティング | ✅ confidence=low と category=other は escalation になり、回答の呼び出しはない。technical(high) は `claude-opus-5-5` で回答する |
| 並列化 | ✅ 1つの観点が例外でも、残りを重要度順に返す。投票では失敗票を数えない（valid_votes=4）。セマフォを関数内で作るので、`asyncio.run()` を2回続けても成功する |
| 評価者-最適化者 | ✅ 終了条件4パターン（v2で合格／合計点が下がっても合格を採用／停滞でv1／上限でv3）と、範囲外の点数の丸め |
| `python patterns/chain.py` で直接起動 | ✅ 本文（L255〜257）どおり `ModuleNotFoundError: No module named 'llm_client'` |
| orchestrator_sketch.py | ✅ 分解（構造化出力）→ 第8章の `Agent.arun()` を gather → リストを返す（calls=3、違反0件） |
| 出力例の金額（第4章の単価表: Opus $4/$20、Haiku $0.10/$0.50 per MTok） | ✅ 4例とも、モデルの内訳で実現できる範囲に収まる。L1366 の `$0.0480` は、生成2回（Opus）と評価2回（Haiku）に分けた試算と合う。例: Opus 2,015/1,976 tok、Haiku 1,200/500 tok で $0.04795。全トークンを Opus で計算した上限は $0.0624。chain（$0.0213、上限 $0.0278）、router（$0.0335、上限 $0.0578）、parallel（$0.0644、上限 $0.0815）も範囲内 |
| 出力例の形式 | ✅ 最終行は4か所とも `tracker.summary()` の形式（`calls=.. input=.. output=.. cache_write=.. cache_read=.. total=$..`）。router の calls=7（分類4＋回答3）はコードの分岐と一致 |

> コードブロック外の気づき（件数に数えない）: L233「いずれも、第4章の`llm_client.py`と第8章の`acall_messages()`を使います」とあるが、`acall_messages()` を使うのは `parallel.py` だけ。chain・router・evaluator_optimizer は同期版の `call_messages()` を使う。「`parallel.py`は第8章の`acall_messages()`も使います」とする案がある。

---

## ✅ 動作確認済みコード一覧

| # | 位置 | 言語 | 行数 | 実行結果 |
|---|---|---|---|---|
| 1 | L235 | text | 9 | 構成どおりに配置して実行できた |
| 2 | L250 | bash | 2 | `python -m patterns.chain` で起動できた |
| 3 | L270 | python | 33 | 正常（PatternError・json_format・parse_json_response） |
| 4 | L376 | python | 47 | 正常（抽出と抽出ゲート） |
| 5 | L444 | python | 47 | 正常（執筆・執筆ゲート・翻訳） |
| 6 | L504 | python | 52 | 正常（run_chain の分岐3通り） |
| 7 | L577 | bash | 2 | 正常（calls=3） |
| 8 | L585 | text | 11 | 形式が実際の出力と一致。金額は範囲内 |
| 9 | L607 | text | 2 | 実際の最終行と一致 |
| 10 | L643 | python | 41 | 正常（enum による分類） |
| 11 | L704 | python | 51 | 正常（エスカレーション2通り、MODEL で回答） |
| 12 | L778 | bash | 2 | 正常 |
| 13 | L785 | text | 13 | 形式が一致。calls=7 はコードの分岐と一致 |
| 14 | L882 | python | 78 | 正常（セクショニング） |
| 15 | L999 | python | 72 | 正常（投票、main の try/finally） |
| 16 | L1090 | bash | 2 | 正常（calls=8 で本文と一致。Event loop のエラーなし） |
| 17 | L1097 | text | 13 | 形式が一致 |
| 18 | L1204 | python | 47 | 正常 |
| 19 | L1269 | python | 57 | 正常（終了条件4パターン＋丸め） |
| 20 | L1351 | bash | 2 | 正常 |
| 21 | L1358 | text | 8 | 形式が一致。`total=$0.0480` は単価表の計算と合う |
| 22 | L1430 | python | 27 | 正常（説明用の骨格） |

> ⚠️ **検証の限界**: 実際の Claude API（モデルの応答内容・構造化出力の実際の振る舞い）は検証していません。公開前に、実APIで4つのパターンを各1回実行して確認してください。
