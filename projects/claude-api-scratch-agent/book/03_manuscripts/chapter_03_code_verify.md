# コード検証レポート（再検証）

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_03.md
検証日: 2026-11-08
検証環境: Windows 11 / uv 0.13.5 / Python 3.12.7 / httpx 0.28.1 / python-dotenv（uv venv の隔離環境）/ 偽Claude API（`httpx.MockTransport`。ヘッダー・禁止パラメータ・prefill・max_tokens 欠落・未知モデル・誤URL・不正キー・強制 tool_choice を判定し、stop_sequences と max_tokens の打ち切り・思考トークン・名前の記憶を再現）。実APIキーは使用していない。
コードブロック数: 28個（うち出力例の `text` 6個＝L682・L955・L981・L1177・L1199・L1402 は照合用のため判定数に含めない → 判定対象 22個）
  ✅ 動作確認済み: 17個
  ⚠️ 要確認: 0個
  ❌ エラーあり: 0個
  🔍 構文チェックのみ: 5個

## 前回からの経緯
- 同日午前の検証で ⚠️1件（#15 `params_demo.py effort model` の出力例に `=== Opus 5.5 ===` の段がなく、「30分の1」の比較相手があいまい）を指摘した。
- ファクトチェック修正で、出力例 L981 に Opus 5.5 の段（input=21 output=389（思考 142） 概算 $0.00786）が加わった。本文 L1002 も「既定の effort の Opus 5.5 と比べて、およそ60分の1」に直っており、今回の再実行で解消を確認した。

---

## 確認したポイント
- 現在の原稿から抽出した「（続き）」ブロックを順に連結し、4本のスクリプト（inspect_response.py・params_demo.py・chat.py・error_lab.py）を組み立てた。すべて正常終了し、偽APIが記録した仕様違反は0件。
- inspect_response.py: 既定の質問・引数ありの両方で、7つの区分（HTTPステータス／生のレスポンス／識別情報と停止理由／content ブロック／usage／回答）の見出しと項目の並びが本文の例（L682〜）と一致。`[0] thinking : 中身0文字 / 署名あり`、`output_tokens : N（うち思考 M）` の形も同じ。
- params_demo.py:
  - `stop max_tokens`: `stop_reason=stop_sequence stop_sequence='\n4.'` で3項目で停止し、`max_tokens=40` では `stop_reason=max_tokens`。本文 L955 の例と同じ形。
  - `effort model`: `=== effort=low ===`・`=== effort=high ===`・`=== Opus 5.5 ===`・`=== Haiku 5.5 ===` の4段が出力され、L981 の出力例の4段と並び・書式が一致。
  - 出力例の数値を単価から計算し直した。low $0.004324、high $0.013184、Opus 5.5 $0.007864、Haiku 5.5 $0.000126 で、いずれも表示と一致。high/low ≒ 3.0 は本文の「3倍ほど」、Opus/Haiku ≒ 60.5 は「およそ60分の1」と合う。
- chat.py: 標準入力から「名乗る→名前を聞く→空行→/reset→名前を聞く→/exit」を流した。履歴は2件→4件と増えて input も増加し、/reset 後は「お名前はまだ伺っていません」。`--no-history` では毎回「履歴 2件」。本文の実験1・2（L1177・L1199）と同じ傾向で、thinking を含む `content` 配列がそのまま再送されることも確認した。
- error_lab.py: 6つの実験の結果は 401 / 400（temperature）/ 400（prefill）/ 400（max_tokens 欠落）/ 404（モデル）/ 404（URL）。`リトライ : しない` を含む6行の形が本文の表・出力例（L1402）と一致した。
- codebase-spec.md との整合: ファイル名、各ファイルで `load_dotenv()` を呼ぶ方針、`temperature` 等・prefill・強制 tool_choice を正常系で使わない点、`extract_text()` / `build_headers()` の名前（第4章と同じ）を確認。

---

## ❌ エラーが発生したコード

該当なし。

## ⚠️ 要確認のコード

該当なし。

---

## ✅ 動作確認済みコード一覧

| # | 位置 | 言語 | 行数 | 実行結果 |
|---|-----|-----|-----|--------|
| 3 | L239 共通の組み立て方（抜粋） | python | 29行 | 単独で実行してエラーなし（送信はしない） |
| 5 | L484 inspect_response.py（冒頭） | python | 34行 | 連結して実行。正常 |
| 6 | L537 inspect_response.py（続き） | python | 37行 | 同上 |
| 7 | L591 inspect_response.py（続き・main） | python | 56行 | 同上。7つの区分の出力が本文の例と同じ形 |
| 8 | L675 `uv run python inspect_response.py` | bash | 1行 | 正常 |
| 10 | L742 引数付き実行 | bash | 1行 | 正常 |
| 11 | L839 params_demo.py（send） | python | 48行 | 正常 |
| 12 | L901 params_demo.py（続き） | python | 38行 | 5つの実験・8回の送信がすべて200 |
| 13 | L950 `params_demo.py stop max_tokens` | bash | 1行 | stop_sequence / max_tokens での停止を再現 |
| 15 | L976 `params_demo.py effort model` | bash | 1行 | 4段の出力。L981 の出力例と一致（前回 ⚠️ → 解消） |
| 18 | L1059 chat.py（send_messages） | python | 24行 | 正常 |
| 19 | L1093 chat.py（続き） | python | 57行 | /reset・空行・/exit・失敗時の pop を確認 |
| 20 | L1172 `chat.py --no-history` | bash | 1行 | 毎回「履歴 2件」 |
| 22 | L1194 `chat.py` | bash | 1行 | 「履歴 2件→4件」、input が増加 |
| 25 | L1306 error_lab.py | python | 42行 | 正常 |
| 26 | L1364 error_lab.py（続き） | python | 22行 | 6つの実験が本文の表どおりのステータス・error.type |
| 27 | L1395 `uv run python error_lab.py` | bash | 1行 | 正常 |

## 🔍 構文チェックのみ

| # | 位置 | 言語 | 結果 |
|---|-----|-----|-----|
| 1 | L99 最小のリクエストボディ | jsonc | コメントを除くと JSON として妥当 |
| 2 | L161 content の2つの書き方 | jsonc | 同上 |
| 4 | L300 レスポンス例 | jsonc | 同上。フィールドはリファレンスの Message と一致 |
| 17 | L1041 履歴追加の良い例・悪い例（抜粋） | python | 構文OK（単独では実行しない断片） |
| 24 | L1242 エラーレスポンス例 | jsonc | 同上。形は Errors の「Error shapes」どおり |

## 本文の手順・誘導の確認（長文分割の影響）
- 本章は1文ごとに改行する書き方になっている。各スクリプトの導入文は次のとおりで、指示どおりに連結して組み立てられた。
  - L482「プロジェクトフォルダー `agent-from-scratch/` に、次の内容で新規作成してください。」
  - L535「続いて、ブロックと停止理由を説明する関数を追加します。」、L589「最後に…`main()` を追加します。」
  - L837・L1057・L1304 の「新規作成」、L899・L1091・L1362 の「続いて」
- L751〜752 の分割後のトラブル対処（「`agent-from-scratch/` フォルダーで実行しているか」「`.env` のキー名に誤りがないか」）は、実行場所の前提と一致している。
- L1451〜L1452 の章末の橋渡し（「まとめる先は、自分だけのAPIクライアント `llm_client.py` です。」）は、第4章の新規作成ファイル名と一致する。

## 参考（判定に影響しない注記）
- chat.py は `input()` が EOF（Ctrl+D / Ctrl+Z）を受けると `EOFError` で終了する。本文は `/exit` で終える前提なので問題ない。気になる場合は `except (EOFError, KeyboardInterrupt): break` を足せる。
- 偽APIの思考トークン・コストの数値は実APIとは異なる。そのため出力例は、数値そのものではなく「形」と計算式で照合した。prefill・強制 tool_choice の 400 は、一次情報の挙動を偽APIに実装して確認したもの。実キーでの最終確認を推奨する。
