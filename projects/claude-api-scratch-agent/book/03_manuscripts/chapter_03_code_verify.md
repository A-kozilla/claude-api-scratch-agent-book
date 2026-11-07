# コード検証レポート

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_03.md
検証日: 2026-11-07
検証環境: Python 3.12 / uv 0.13.5 / httpx 0.28.1 / python-dotenv 1.2.4 / 偽Claude API（FAKEAPI_LOG で呼び出しと違反を記録）
コードブロック数: 28個（うち出力例の `text` 6個は照合用のため判定数に含めない → 判定対象 22個）
  ✅ 動作確認済み: 17個
  ⚠️ 要確認: 0個
  ❌ エラーあり: 0個
  🔍 構文チェックのみ: 5個

---

## 確認したポイント
- 4本のスクリプト（inspect_response.py・params_demo.py・chat.py・error_lab.py）は「（続き）」ブロックを順に連結して組み立て、すべて正常終了。
- 正常系のリクエストで 2026-10-21 仕様違反（temperature・prefill・強制 tool_choice 等）は0件。
- error_lab.py の6実験は、偽APIの記録どおり 401 / 400（temperature）/ 400（prefill）/ 400（max_tokens 欠落）/ 404（モデル）/ 404（URL）となり、本文の表・出力例と一致。
- chat.py は `/reset`・空行・`/exit`・`--no-history` を標準入力で流して確認。履歴あり: 履歴2件→4件で input が増加、`--no-history`: 毎回2件。本文の観察内容と同じ傾向。
- params_demo.py の出力例の概算コスト（$0.00095 / $0.00088 / $0.00432 / $0.01318 / $0.00013）は単価表から再計算して一致。「約3倍」「約30分の1」も妥当。

## 検証の限界（参考）
- 偽APIは `stop_sequences` と小さい `max_tokens` による打ち切りを再現しないため、params_demo.py の `stop_reason=stop_sequence` / `max_tokens` の出力は「形」のみ確認（コード上の分岐・表示は正しい）。実キーでの確認を推奨。
- `output_tokens_details.thinking_tokens` は偽APIが返さないため「思考 0」と表示（`.get(..., 0)` で安全に処理されることを確認）。

---

## ✅ 動作確認済みコード一覧

| # | 位置 | 言語 | 行数 | 実行結果 |
|---|-----|-----|-----|--------|
| 3 | L231 共通の組み立て方（抜粋） | python | 29行 | 単独実行でエラーなし |
| 5 | L473 inspect_response.py（冒頭） | python | 34行 | 連結して実行。正常 |
| 6 | L526 inspect_response.py（続き） | python | 37行 | 同上。thinking → text の順を `[0] thinking / [1] text` と表示 |
| 7 | L580 inspect_response.py（続き・main） | python | 56行 | 同上。出力の7区分が本文例と同じ形 |
| 8 | L664 `uv run python inspect_response.py` | bash | 1行 | 正常 |
| 10 | L731 引数付き実行 | bash | 1行 | 正常 |
| 11 | L827 params_demo.py（send） | python | 48行 | 正常 |
| 12 | L889 params_demo.py（続き） | python | 38行 | 5実験・8回の送信がすべて200 |
| 13 | L938 `params_demo.py stop max_tokens` | bash | 1行 | 正常（出力の形のみ確認） |
| 15 | L964 `params_demo.py effort model` | bash | 1行 | 正常。Haiku のコストが小さく出ることを確認 |
| 18 | L1043 chat.py（send_messages） | python | 24行 | 正常 |
| 19 | L1077 chat.py（続き） | python | 57行 | 正常 |
| 20 | L1156 `chat.py --no-history` | bash | 1行 | 毎回「履歴 2件」 |
| 22 | L1178 `chat.py` | bash | 1行 | 「履歴 2件→4件」、input 増加 |
| 25 | L1285 error_lab.py | python | 42行 | 正常 |
| 26 | L1341 error_lab.py（続き） | python | 22行 | 6実験が本文の表どおりのステータス・error.type |
| 27 | L1372 `uv run python error_lab.py` | bash | 1行 | 正常 |

## 🔍 構文チェックのみ

| # | 位置 | 言語 | 結果 |
|---|-----|-----|-----|
| 1 | L92 最小のリクエストボディ | jsonc | コメント除去後 JSON として妥当 |
| 2 | L154 content の2つの書き方 | jsonc | 同上 |
| 4 | L292 レスポンス例 | jsonc | 同上 |
| 17 | L1025 履歴追加の良い例・悪い例（抜粋） | python | 構文OK（単独実行しない断片） |
| 24 | L1226 エラーレスポンス例 | jsonc | 同上。形は facts のエラーボディどおり |

## ⚠️対応（2026-11-07）

⚠️ 要確認は0件のため対応なし。第4章の確定ログ形式・`tracker.summary()` 形式との照合: 本章の出力例（L945〜L980 の `stop_reason=... input=.. output=..（思考 ..） 概算 $...`）は第3章独自スクリプトの print 形式で、第4章の `llm_client` ログとは別物のため変更不要。
