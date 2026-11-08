# コード検証レポート（再検証）

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_04.md
検証日: 2026-11-08
検証環境: Windows 11 / uv 0.13.5 / Python 3.12.7 / httpx 0.28.1 / python-dotenv（uv venv の隔離環境）/ 偽Claude API（`httpx.MockTransport`、非ストリーミングと SSE の両方に対応）。実APIキーは使用していない。`time.sleep` は境界テストでのみ差し替えた。
コードブロック数: 36個（うち出力例・SSE の生データの `text` 7個＝L423・L656・L692・L869・L981・L1032・L1364 は照合用のため判定数に含めない → 判定対象 29個）
  ✅ 動作確認済み: 28個
  ⚠️ 要確認: 1個
  ❌ エラーあり: 0個
  🔍 構文チェックのみ: 0個

## 前回からの経緯
- 2026-11-07 の ❌ #25 stream_demo.py（「同じ文字列か」の判定）と、ファクトチェックで追加された `_TYPE_TO_ERROR["timeout_error"]` は、同日午前の検証で反映を確認済み（✅29）。
- その後の変更はコードブロックの外のみで、36ブロックの中身は前回と同一だった。今回は抽出し直したブロックから4段階の組み立てをやり直した。⚠️1件は本文の誘導文（L1403）についての新規指摘で、コード自体は全件動作する。

---

## 検証の進め方
本文の「新規作成」「追加」「更新（差し替え）」の指示どおりに、llm_client.py を4段階で組み立てた。各段階でデモを実行した。
1. 4.1節: #1〜#6 を順に新規作成 → client_demo.py
2. 4.2節: #10 を「定数のブロックの下」（`FORBIDDEN_PARAMS` の直後）に挿入し、#11・#12 を追加。`call_messages` を #13 に差し替え → client_demo.py・retry_demo.py
3. 4.3節: #18・#19・#21 を追加 → sse_demo.py・stream_demo.py・retry_demo.py
4. 4.4節: #28・#30 を追加し、`call_messages` を #31、`stream_messages` を #32 に差し替え → client / retry / sse / stream / cost の各デモと main.py

**完成版との一致（課題3）**: 段階4のファイルと L1405 の完成版を AST で比較した。トップレベル定義60個はすべて一致し、欠落・余分・差分はいずれも0。完成版のファイル単体でも全デモが正常に終了した。ただし定義の**並び順**は一致しない（下記 ⚠️）。

codebase-spec.md の契約との照合（すべて一致）:
- 定数 `API_URL` / `API_BASE` / `API_VERSION="2026-10-21"` / `MODEL="claude-opus-5-5"` / `FAST_MODEL="claude-haiku-5-5"`
- 例外9種と属性 `status` / `error_type` / `message` / `request_id` / `error_code`
- `build_headers()`、`call_messages()` / `stream_messages()` のシグネチャ（キーワード専用引数、`max_tokens` の既定は 16000 / 64000、`max_retries=4`、`on_text`）
- `extract_text()` / `get_tool_uses()`、`CostTracker.add / summary / reset`、`tracker`
- 内部名 `_send_with_retry` / `_request_with_retry` / `_is_retryable` / `_retry_delay` / `_error_from_response` / `_make_error` / `_error_class` / `_TYPE_TO_ERROR` / `_client`
- INFO ログ `request_id=... model=... stream=False elapsed=...s stop=... in=.. out=.. cache_write=0 cache_read=0 cost=$...`、`summary()` の `calls=2 input=.. output=.. cache_write=0 cache_read=0 total=$...`

## 出力例との照合
| 出力例 | 実行結果 | 一致 |
|---|---|---|
| L423 client_demo.py | `stop_reason: end_turn` / `blocks: ['thinking', 'text']` / `text: …` / `NotFoundError: [404 not_found_error] model: claude-opus-9-9 (request_id=…)` / `ValueError: このAPIバージョンでは使えません: ['temperature']`（段階1・2・4・完成版） | ✅ |
| L656 retry_demo.py | `WARNING llm_client: retry 1/4 in 0.5〜0.8s: [529 …]` → `retry 2/4 in 1.0s: [429 …]` → `3回目で成功しました (試行回数: 3)`。段階4・完成版では INFO 行が1行増える（L662 に記載あり） | ✅ |
| L981 sse_demo.py | `diff` で完全一致（イベント7行＋`stop_reason: tool_use`＋tool_uses） | ✅ |
| L1032 stream_demo.py | 逐次表示 → `stop_reason: end_turn` / `blocks: ['thinking', 'text']` / `usage: {...}` / `同じ文字列か: True` | ✅ |
| L1364 cost_demo.py | INFO 2行（Opus / Haiku、Haiku は `cost=$0.0000`）＋`calls=2 … total=$0.0025` | ✅ |

追加の実験として、L993 の「`RAW` の最後の `message_stop` を消して実行」も試した。結果は `APIConnectionError: … message_stop の前にストリームが終了しました` で、本文の説明どおり。main.py（#29）は実行後に `agent.log` ができることを確認した。

## 境界テスト（完成版 llm_client.py、MockTransport）
結果は前回と同じ。

| ケース | 試行 | 結果 |
|---|---|---|
| ConnectError ×3 → 成功 / ConnectError が続く | 4 / 5 | 成功 / `APIConnectionError` |
| ReadTimeout → 成功、408・409・504・500(timeout_error) → 成功 | 2 | 成功 |
| 429 `enforced_spend_limit_reached` / 400（自分で設定した上限）/ 402 / 401 | 1 | 再試行なし（`RateLimitError` / `InvalidRequestError` / `APIError` / `AuthenticationError`） |
| 502 HTML 本文 / 529 が続く | 5 | `InternalServerError`（本文の先頭が message に入る）/ `OverloadedError` |
| 429 `retry-after: 100` | 3 | 60秒で頭打ち。合計120秒の上限で中止 |
| 429 `retry-after` が日付形式 | 2 | バックオフで待って成功 |
| SSE 正常（LF/CRLF）・未知のイベント・`citations_delta`・`fallback` ブロック | 1 | 正しく復元 |
| SSE `error`（overloaded / timeout_error） | 1 | `OverloadedError` / `InternalServerError`（status=None） |
| `message_stop` 前の切断 / 受信途中の `ReadError` | 1 | `APIConnectionError`（再試行しない） |
| ストリーム開始前の 529 → 成功 | 2 | 成功 |
| Haiku 5.5 の 100,000 / 100,001 トークン、単価表にないモデル | - | 通常単価 / 高い単価、`None` |

---

## ❌ エラーが発生したコード

該当なし。

---

## ⚠️ 要確認のコード

### コードブロック #36（chapter_04.md L1405 完成版 llm_client.py）の直前の誘導文 L1403

**元の文**:
> 本章で作った `llm_client.py` の全体を掲載します。節ごとに示したコードを、この順番で1つのファイルにまとめたものです。手元のファイルと見比べて、抜けや順番の違いがないかを確認してください。

**懸念点**: 本文の「追加」の指示どおりに組み立てると、定義の中身は完成版と完全に一致する。しかし並び順は次の3か所で完成版と食い違う。
- 段階版: `build_headers → _build_body → call_messages → extract_text → get_tool_uses → _is_retryable … _send_with_retry → _iter_sse → _StreamAccumulator → stream_messages → _log_call → PRICES …`
- 完成版: `build_headers → _build_body → _is_retryable … _send_with_retry → _log_call → call_messages → _iter_sse → _StreamAccumulator → stream_messages → extract_text → get_tool_uses → PRICES …`

食い違うのは、`call_messages` の位置、`extract_text` / `get_tool_uses` の位置（完成版では末尾近く）、`_log_call` の位置（完成版では `call_messages` の前）。「節ごとに示した順番」でまとめたわけではないため、「順番の違いがないか確認」と指示された読者は、正しく作ったのに間違えたと思い込むおそれがある。動作への影響はない（Python は呼び出し時に名前を解決する）。

**推奨対処**: 誘導文を、実際の作りに合わせて次のように直す。
> 本章で作った `llm_client.py` の全体を掲載します。節ごとに示したコードを1つのファイルにまとめ、読みやすいように関数の並びを整理したものです。手元のファイルと関数の順番が違っていても、動作は変わりません。抜けている関数や、差し替え忘れ（`call_messages()` と `stream_messages()` が完成版になっているか）がないかを確認してください。

完成版の並びを段階版に合わせる方法もある。ただし完成版は読みやすさのために整理されているので、文を直すほうが変更は小さい。

---

## ✅ 動作確認済みコード一覧

| # | 位置 | 言語 | 行数 | 実行結果 |
|---|-----|-----|-----|--------|
| 1 | L62 llm_client.py 冒頭 | python | 33行 | 段階1に組み込み、正常 |
| 2 | L108 例外クラス | python | 62行 | 同上 |
| 3 | L183 エラー変換 | python | 65行 | 同上。`timeout_error` → InternalServerError |
| 4 | L257 リクエストの組み立て | python | 49行 | 同上。extra で temperature を渡すと送信前に ValueError |
| 5 | L319 call_messages 最初の版 | python | 33行 | 同上 |
| 6 | L361 extract_text / get_tool_uses | python | 15行 | 同上 |
| 7 | L385 client_demo.py | python | 28行 | 段階1・2・4・完成版で本文の例と同じ形 |
| 8 | L416 実行コマンド | bash | 1行 | 正常 |
| 10 | L485 リトライの設定（定数のブロックの下） | python | 6行 | 段階2に組み込み、正常 |
| 11 | L494 `_is_retryable` / `_retry_delay` | python | 23行 | 同上 |
| 12 | L522 `_request_with_retry` / `_send_with_retry` | python | 44行 | 同上 |
| 13 | L579 call_messages（リトライ版に差し替え） | python | 30行 | 同上 |
| 14 | L616 retry_demo.py | python | 32行 | 529 → 429(retry-after:1) → 成功。2回目の待ちは 1.0s |
| 15 | L651 実行コマンド | bash | 1行 | 正常 |
| 18 | L753 `_iter_sse` | python | 25行 | 段階3に組み込み、正常 |
| 19 | L787 `_StreamAccumulator` | python | 73行 | 同上。input_json_delta の連結・ping の無視・error イベントの例外化を確認 |
| 21 | L882 stream_messages | python | 46行 | 同上 |
| 22 | L939 sse_demo.py | python | 34行 | 出力が L981 と完全一致 |
| 23 | L976 実行コマンド | bash | 1行 | 正常 |
| 25 | L997 stream_demo.py | python | 27行 | 逐次表示、`同じ文字列か: True` |
| 26 | L1027 実行コマンド | bash | 1行 | 正常 |
| 28 | L1072 `_log_call` | python | 20行 | 段階4に組み込み、ログ形式が codebase-spec どおり |
| 29 | L1118 main.py（ログ設定の例） | python | 12行 | 実行すると agent.log ができる |
| 30 | L1151 単価表・CostTracker | python | 86行 | 単価・閾値・前方一致・未知モデルのときの警告を確認 |
| 31 | L1250 call_messages 完成版 | python | 34行 | 正常 |
| 32 | L1287 stream_messages 完成版 | python | 50行 | 正常 |
| 33 | L1344 cost_demo.py | python | 12行 | INFO 2行＋summary 1行が本文の例と同じ形 |
| 34 | L1359 実行コマンド | bash | 1行 | 正常 |

（#36 完成版 llm_client.py 605行も、コードとしては全デモと境界テストが正常に動く。判定は上記の誘導文の件で ⚠️ とした。）

## 本文の手順・誘導の確認（長文分割の影響）
- L60「プロジェクトのフォルダー `agent-from-scratch/` に、`llm_client.py` を新規作成します。」、L383「確認用の `client_demo.py` を作り」は、置き場所と新規作成が明確。
- L483「`llm_client.py` に、リトライの設定値と4つの関数を追加します。設定値は定数のブロックの下に置きます。」は #10 のコメント「定数のブロックの下に置く」と一致する。完成版でも `FORBIDDEN_PARAMS` の直後にあり、正しく誘導できている。
- L577（分割後）「`call_messages()` も、送信部分を差し替えます。4.4節では…そのため、ここでは…`_request_with_retry()` を直接呼びます。」は、#13 の「更新：…差し替え」と整合している。
- L434〜435 の分割後のトラブル対処（同じフォルダーにあるか、`agent-from-scratch/` で `uv run` しているか、`.env` の置き場所とキー名）は、実行条件と一致する。
- L662（分割後）の「偽APIの1回目を `400` に変えることも試してみてください。リトライせずに `InvalidRequestError` が即座に出ます。」は、境界テスト（400 → 1回で `InvalidRequestError`）と一致する。
- L1248「`call_messages()` と `stream_messages()` に計測とログを組み込みます」と #31・#32 の「更新」は対応している。

## 参考（判定に影響しない注記・前回から継続）
- `_iter_sse()` は、`data:` の JSON が壊れていると `json.JSONDecodeError` をそのまま送出する（公式APIでは起こらない想定）。
- `fallback` コンテンツブロック（server-side fallback）は `{"type": "fallback"}` として content に残り、処理は落ちない。
- 4.4節以降に stream_demo.py を実行すると、本文の末尾に改行がないため、INFO ログが同じ行に続けて出る。4.3節の時点の出力例とは一致している。
