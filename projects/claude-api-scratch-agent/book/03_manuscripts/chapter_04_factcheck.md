# ファクトチェックレポート

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_04.md
検証日: 2026-11-08（前回 2026-11-07 の再検証。原稿修正後の版を対象）
検証クレーム数: 42件
  ✅ 検証済み: 41件
  ⚠️ 要確認: 1件
  ❌ 要修正: 0件

主な一次情報（2026-11-08 取得）:
- Errors: https://platform.claude.com/docs/en/api/errors.md
- Rate limits: https://platform.claude.com/docs/en/api/rate-limits.md
- Streaming: https://platform.claude.com/docs/en/build-with-claude/streaming.md
- Pricing: https://platform.claude.com/docs/en/about-claude/pricing.md
- Thinking: https://platform.claude.com/docs/en/build-with-claude/thinking.md
- Messages API リファレンス: https://platform.claude.com/docs/en/api/messages.md
- Versions / Migration 2026-10-21: https://platform.claude.com/docs/en/api/versioning.md ・ migration-2026-10-21.md
- httpx: インストール済み httpx 0.28.1 の実装（`DEFAULT_TIMEOUT_CONFIG`、例外階層）で確認

---

## 前回（2026-11-07）指摘の反映状況

| 前回 | 内容 | 反映 |
|---|---|---|
| ⚠️1 | 408 は API の一覧にない | ✅ 反映済み（L461「408はAPIのエラー一覧にはありませんが、プロキシなどが返す場合に備え…」） |
| ⚠️2 | 自分で設定した spend limit は400 | ✅ 反映済み（L461「429ではなく400（`invalid_request_error`）が返ります」、表 L457「429（ティアの月の利用上限）」） |
| ⚠️3 | delta の種類に `citations_delta` | ✅ 反映済み（L741「本書で扱う主な種類が4つ…`citations_delta` も届きますが…無視します」、L1040「主な4種類」） |
| ⚠️4 | SDK の10分チェックは警告ではなくエラー | ✅ 反映済み（L1385「送信前にエラーにする」） |
| ⚠️5 | `retry-after` が明記されているのは429 | ✅ 反映済み（L475「429の応答には…（他のステータスでも、付いていれば従います）」） |
| 推奨4 | 402 / 504 の扱い | ✅ 反映済み（L177 NOTE、L454 表の402行、L458「500 / 504 / 529」、`_TYPE_TO_ERROR` の `timeout_error`） |

---

## ✅ 検証済み（正確）

### 1. 必須ヘッダーと `anthropic-version: 2026-10-21`（L85・L266–270）
**検証結果**: Errors / Migration の cURL 例は `x-api-key` / `anthropic-version: 2026-10-21` / `content-type` の3ヘッダー。

### 2. `temperature`・`top_p`・`top_k` は400（L89–90・L100）
**検証結果**: Migration「returns a 400 error, even at the parameter’s default value.」

### 3. エラーボディの形（L181）
**検証結果**: Errors「Error shapes」と一致。

### 4. 402 `billing_error`・409 `conflict_error`・504 `timeout_error` も返り得る（L177）
**検証結果**: Errors の HTTP errors 一覧に3つとも記載。

### 5. SSE の `error` イベントで `timeout_error` が届く場合に `InternalServerError` にそろえる（L177・L205）
**検証結果**: Errors「The API also returns `timeout_error` with other status codes, such as a 500 when a request reaches the server’s time limit before the response starts.」— 型名でサーバー側の一時的失敗と判断するのは妥当。

### 6. エラー型と例外クラスの対応（L186–207）
**検証結果**: invalid_request_error / authentication_error / permission_error / not_found_error / request_too_large / rate_limit_error / api_error / overloaded_error が Errors の一覧と一致。

### 7. 400・401・403・404・413 はリトライしない（L453）
**検証結果**: いずれもリクエスト内容・権限・サイズの問題（Errors の各説明）。

### 8. 402 はリトライしない（L454）
**検証結果**: Errors「402 … Check your payment details in the Claude Console」。

### 9. 409 はリトライ（L455）
**検証結果**: Errors「Resolve the conflict, then retry the request.」

### 10. 429（レート制限）はリトライ（L456）
**検証結果**: Rate limits「When the response has a `retry-after` header, wait that many seconds before retrying.」

### 11. ティアの月の上限の429は `retry-after` なし・`error.details.error_code == "enforced_spend_limit_reached"`・リトライしない（L457・L461・コード L500）
**検証結果**: Rate limits「Reaching your spend cap」: `rate_limit_error`、`retry-after` なし、`error_code` は `enforced_spend_limit_reached`、翌月1日 00:00 UTC まで停止。※上位ティアへの移行でも解除される（「翌月まで回復しない」は自動回復の意味として正確）。

### 12. 自分で設定した spend limit は400 `invalid_request_error`（L461）
**検証結果**: Rate limits「When usage reaches a spend limit you set, requests return HTTP 400 with error type `invalid_request_error`.」Errors の400の説明にも同旨。

### 13. 408 は API の一覧にない（L461）
**検証結果**: Errors の一覧に 408 はない。公式SDKの再試行対象（408/409/429/5xx）に合わせる説明は妥当。

### 14. 500 / 504 / 529 はリトライ（L458）
**検証結果**: Errors「500 … Retry the request with exponential backoff」「504 … timed out while processing」「529 … temporarily overloaded」。

### 15. `retry-after` は429に付くことがある（L475）
**検証結果**: Rate limits のヘッダー表「Not every 429 carries it; the spend-cap 429 never does」。

### 16. レート制限ヘッダー `anthropic-ratelimit-requests-remaining` 等（L475）
**検証結果**: Rate limits「Response headers」表に `anthropic-ratelimit-requests-*` / `-tokens-*` / `-input-tokens-*` / `-output-tokens-*` が記載。

### 17. 長いリクエストにはストリーミングか Message Batches API（L56）
**検証結果**: Errors「Long requests」「especially those over 10 minutes」「Some networks might drop idle connections」。

### 18. httpx の既定タイムアウトは5秒、`connect`/`read`/`write`/`pool` の4種類（L54）
**検証結果**: httpx 0.28.1 `DEFAULT_TIMEOUT_CONFIG = Timeout(timeout=5.0)`、`httpx.Timeout` は connect / read / write / pool を持つ。`httpx.Timeout(600.0, connect=10.0)` は connect 以外が600秒。

### 19. `httpx.TransportError` は `ConnectError`・`ReadTimeout` の親（L571）
**検証結果**: `issubclass(httpx.ConnectError, httpx.TransportError)`・`issubclass(httpx.ReadTimeout, httpx.TransportError)` ともに True（実行確認）。

### 20. Opus 5.5 は思考が常に有効、既定で中身が空の `thinking` ブロック（L359）
**検証結果**: Models overview「Adaptive (always on)」、Thinking「`"omitted"` (the default on these models)」。※L431 の断定表現は下記⚠️1。

### 21. `request-id` レスポンスヘッダー（L1065・L1070）
**検証結果**: Errors「Every API response includes a unique `request-id` header」「include this ID to help quickly resolve your issue」。

### 22. SSE のイベント順序（L722・表 L726–735）
**検証結果**: Streaming「Event flow」と一致。※公式は `message_delta` を「One or more」とする。本書のコードは `update()` で上書きするため複数回届いても正しく動く（境界テストで確認）。

### 23. SSE 例（L692–716）
**検証結果**: Streaming の Basic streaming request の Response 例と同一（`msg_...`、`input_tokens: 25`、`output_tokens: 15` 等）。

### 24. `ping` イベント・`error` イベント（`overloaded_error` の例）（L734–735・L869–872）
**検証結果**: Streaming「Event streams might also include any number of `ping` events.」「you might receive an `overloaded_error`, which would normally correspond to an HTTP 529」。JSON例も公式と同一。

### 25. `message_delta` の `usage` は累積値（L737）
**検証結果**: Streaming「The token counts shown in the `usage` field of the `message_delta` event are *cumulative*.」

### 26. 未知のイベント型は無視する（L737）
**検証結果**: Streaming「new event types may be added, and your code should handle unknown event types gracefully.」

### 27. delta は主に4種類＋`citations_delta`（L741）
**検証結果**: Streaming の Content block delta types（text / input_json / thinking / signature）。citations_delta はリファレンスに存在。

### 28. `signature_delta` はブロック終了直前、`omitted` では空の `thinking_delta` の後に `signature_delta` だけ（L741）
**検証結果**: Streaming「a special `signature_delta` event is sent just before the `content_block_stop` event」「receives a `thinking_delta` with an empty `thinking` string and then a single `signature_delta`」。

### 29. `input_json_delta` は部分JSON文字列で、`content_block_stop` 後にパース（L743）
**検証結果**: Streaming「the deltas are *partial JSON strings*, whereas the final `tool_use.input` is always an *object*」「parse the JSON once you receive a `content_block_stop` event」。

### 30. 各イベントの `index` は最終 `content` 配列での位置（L747）
**検証結果**: Streaming「Each content block has an `index` that corresponds to its index in the final Message `content` array.」

### 31. ストリーム途中の失敗の回復は、受信済み部分を user メッセージに含めて続きを依頼（L933）
**検証結果**: Streaming「Error recovery / Claude 4.6 and later: … add a user message that instructs the model to continue from where it left off.」

### 32. 思考ブロックを欠落・改変させると次のリクエストが400（L1040）
**検証結果**: Errors「Thinking blocks cannot be modified … edited, reordered, filtered out, or reconstructed … returns a 400」。

### 33. `match` 文は Python 3.10 以降（L863）
**検証結果**: PEP 634（Python 3.10 で導入）。Python 3.12 で実行確認。

### 34. `logging` は設定しなければ WARNING 以上だけが標準エラーに出る（L1057）
**検証結果**: 標準ライブラリの `logging.lastResort`（レベル WARNING、stderr）。実行でも INFO は出ないことを確認。

### 35. `%s` 書式の遅延評価・`iter_text()` は行単位ではない（L1095・L1043）
**検証結果**: logging は出力時にのみ `msg % args` を行う。httpx `iter_text()` はチャンク単位、`iter_lines()` は行単位（CRLF も含め実行確認）。

### 36. `usage` の4フィールド、入力合計＝3つの入力系の和、20万＋50トークンの例（L1101–1108）
**検証結果**: Rate limits「total_input_tokens = cache_read_input_tokens + cache_creation_input_tokens + input_tokens」「with a 200k-token cached document and a 50-token user question, you’d see `input_tokens: 50`」。

### 37. 空の思考でも `output_tokens` として課金（L1108）
**検証結果**: Thinking「billed as output tokens, even when the thinking text isn’t returned to you」。

### 38. ITPM に数えるのはキャッシュ読み取りを除いた2つ（L1112）
**検証結果**: Rate limits「only `input_tokens` + `cache_creation_input_tokens` count toward your ITPM limit」。

### 39. 単価表と倍率（L1139–1147、コード L1154–1163）
**検証結果**: Pricing と完全一致。Opus 5.5: $4 / $20 / 書込$5 / 読取$0.20、Sonnet 5.5: $2 / $10 / $2.50 / $0.10、Haiku 5.5（10万以下）: $0.10 / $0.50 / $0.125 / $0.01、（10万超）: $0.50 / $2.50 / $0.625 / $0.05。脚注「Cache hits … on Claude Opus 5.5 and Claude Sonnet 5.5 are priced at 0.05x」「All other models use the standard 0.1x」。1時間書き込み2倍（Opus $8 = 4×2）。Haiku の閾値は「A request’s prompt length counts all of its input tokens, including cache reads and cache writes」でコードの `inp + cw + cr` と一致。

### 40. 計算例と処理地域の割増（L1244・L1375）
**検証結果**: 1,200×4＋350×20＝$0.0118、1万×0.20＝$0.002（通常入力 $0.04 の1/20）を再計算で確認。Pricing「`inference_geo: "us"` applies a 1.1x pricing multiplier」。

### 41. コラム: 公式SDK（L1385–1390）
**検証結果**: Errors「The official SDK automatically retries transient failures … twice by default, honoring the `retry-after` header」「validates that your non-streaming Messages API requests are not expected to exceed a 10-minute timeout」、型付き例外（SDK error types）、Streaming「The Python SDK allows both sync and async streams」・最終メッセージ取得ヘルパー。

---

## ⚠️ 要確認（古い可能性あり）

### ⚠️1（L431）`thinking` ブロックは必ず先頭に入るか
**記述**: 「Opus 5.5は思考が常に有効で、既定では中身が空の `thinking` ブロックが先頭に入ります。」
**懸念点**: adaptive thinking では、簡単なリクエストでモデルが思考を省くと `thinking` ブロック自体が出ない。第3章 L723（「`thinking` ブロックが含まれず、`text` だけになることもあります」）や本章 L359（「入ることがあります」）とも食い違う。
**検索結果**: Thinking「When you use `thinking.type: "adaptive"` and the model skips thinking for a simple request, no thinking block is produced regardless of `display`.」
**推奨対処**: 「Opus 5.5は思考が常に有効なので、既定では中身が空の `thinking` ブロックが先頭に入ることがあります（簡単な質問では入らないこともあります）。」

---

## ❌ 要修正（誤りの可能性が高い）

該当なし。

---

## 総評

前回の⚠️5件と402/504の推奨対応はすべて一次情報どおりに反映されており、エラー型・リトライ対象（spend limit の400、spend cap の429、408/409/504 の扱い）・SSE のイベント順序と delta・usage と料金表は、今回の再取得でも完全に一致した。単価表は Haiku 5.5 の10万トークン超の価格と、閾値にキャッシュ読み書きを含める点まで正確。

新たな指摘は L431 の「thinking ブロックが先頭に入ります」という断定1件のみ（adaptive thinking は簡単な質問で思考を省き、ブロックが出ないことがある）。そのほか参考として、公式の Streaming ドキュメントには server-side fallback 時の `fallback` コンテンツブロック（deltaなしの start/stop の組）が追加されているが、本書の `_StreamAccumulator` はそのまま content に含めて処理でき、落ちないことをコード検証で確認した（本書の範囲では言及不要）。

---

## 再チェック（2026-11-08・修正箇所）

対象: `git diff` の変更 1か所。一次情報: build-with-claude/thinking.md。

- ✅ L431「Opus 5.5は思考が常に有効なので、既定では中身が空の `thinking` ブロックが先頭に入ることがあります（簡単な質問では入らないこともあります）」
  thinking.md「On Claude 5 and later models … thinking is already on」「`display` defaults to `"omitted"`」「When you use `thinking.type: "adaptive"` and the model skips thinking for a simple request, no thinking block is produced」と一致。直前の出力例（thinking と text が並ぶ）とも矛盾しない。
  （文体メモ: 括弧書きを含め約75字。「…入ることがあります。簡単な質問では入らないこともあります。」と2文に分けると読みやすい。任意）
