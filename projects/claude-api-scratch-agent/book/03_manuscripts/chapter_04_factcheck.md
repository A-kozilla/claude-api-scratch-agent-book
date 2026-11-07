# ファクトチェックレポート

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_04.md
検証日: 2026-11-07
検証クレーム数: 35件
  ✅ 検証済み: 30件
  ⚠️ 要確認: 5件
  ❌ 要修正: 0件

主な一次情報（2026-11-07 取得）:
- Errors: https://platform.claude.com/docs/en/api/errors.md
- Rate limits: https://platform.claude.com/docs/en/api/rate-limits.md
- Streaming: https://platform.claude.com/docs/en/build-with-claude/streaming.md
- Pricing: https://platform.claude.com/docs/en/about-claude/pricing.md
- Thinking / Adaptive thinking: https://platform.claude.com/docs/en/build-with-claude/thinking.md ・ adaptive-thinking.md
- 2026-10-21 移行ガイド: https://platform.claude.com/docs/en/api/migration-2026-10-21.md
- httpx Timeouts: https://www.python-httpx.org/advanced/timeouts/

---

## ✅ 検証済み（正確）

### 1. `anthropic-version: 2026-10-21` と必須ヘッダー（85行・267行）
**検証結果**: 公式の cURL 例はすべて `x-api-key` / `anthropic-version: 2026-10-21` / `content-type` の3ヘッダー。

### 2. `temperature`・`top_p`・`top_k` は400（100行）
**検証結果**: 移行ガイド「In `2026-10-21`, a request that sends `temperature`, `top_p`, or `top_k` returns a 400 error, even at the parameter's default value.」

### 3. エラーボディの形 `{"type":"error","error":{"type","message"},"request_id"}`（181行）
**検証結果**: Errors「Error shapes」と一致。

### 4. 402 `billing_error`・409 `conflict_error`・504 `timeout_error` も返り得る（177行）
**検証結果**: Errors の HTTP errors 一覧に3つとも記載。

### 5. エラー型と例外クラスの対応表（400/401/403/404/413/429/500/529 と `error.type`）（186〜207行）
**検証結果**: Errors の一覧（invalid_request_error / authentication_error / permission_error / not_found_error / request_too_large / rate_limit_error / api_error / overloaded_error）と一致。

### 6. 400・401・403・404・413 はリトライしない（452行）
**検証結果**: いずれもリクエスト内容・権限・サイズの問題。Errors の説明と整合。

### 7. 409 はリトライ対象（453行）
**検証結果**: Errors「409 … Resolve the conflict, then retry the request.」。Messages API で409が出る場面は少ないが、再試行対象とする判断は公式の記述と矛盾しない。

### 8. 429（レート制限）はリトライ、`retry-after` を優先（454・473行）
**検証結果**: Rate limits「When the response has a `retry-after` header, wait that many seconds before retrying.」「Earlier retries fail.」

### 9. 月の上限到達の429は `retry-after` なし・`error.details.error_code == "enforced_spend_limit_reached"`・リトライしても回復しない（455・459行、コード498行）
**検証結果**: Rate limits「Reaching your spend cap」: 型は `rate_limit_error`、`retry-after` なし、`error.details.error_code` は `enforced_spend_limit_reached`、翌月1日 00:00 UTC まで停止（上位ティアへの移行で解除）。

### 10. 500・529 などの5xxはリトライ（456行）
**検証結果**: Errors「500 … Retry the request with exponential backoff」、529 は一時的な過負荷。

### 11. レート制限ヘッダー `anthropic-ratelimit-requests-remaining` 等（473行）
**検証結果**: Rate limits「Response headers」の表に `anthropic-ratelimit-requests-*` / `-tokens-*` / `-input-tokens-*` / `-output-tokens-*`（limit / remaining / reset）が記載。

### 12. 非ストリーミングで10分を超える長いリクエストにはストリーミングかBatchを推奨（56行）
**検証結果**: Errors「Long requests」に記載。

### 13. httpx の既定タイムアウトは5秒（54行）
**検証結果**: httpx 公式「HTTPX … timing out after 5 seconds of network inactivity」。

### 14. Opus 5.5 は思考が常に有効、既定で中身が空の `thinking` ブロックが返る（358・430行）
**検証結果**: Thinking「`display` defaults to `"omitted"` on these models」（Claude 5 以降・Opus 5.5 を含む）。Errors「On … Claude Opus 5.5 … thinking is always on」。

### 15. `request-id` レスポンスヘッダー（420・1063行）
**検証結果**: Errors「Every API response includes a unique `request-id` header」。

### 16. SSE のイベント順序（message_start → content_block_start/delta/stop の繰り返し → message_delta → message_stop）（720行・表724〜733行）
**検証結果**: Streaming「Event types」の event flow と一致（`message_delta` は "one or more"）。

### 17. `ping` イベント・`error` イベント（`overloaded_error` の例）（732〜733・865〜872行）
**検証結果**: Streaming「Ping events」「Error events」。例文のJSONも公式と同一。

### 18. `message_delta` の `usage` は累積値（735行）
**検証結果**: Streaming「The token counts shown in the `usage` field of the `message_delta` event are *cumulative*.」

### 19. 未知のイベント型は無視する（735行）
**検証結果**: Streaming「Other events … your code should handle unknown event types gracefully.」

### 20. `signature_delta` はブロック終了直前に届く／`omitted` では空の `thinking_delta` の後に `signature_delta` だけが届く（739行）
**検証結果**: Streaming「a special `signature_delta` event is sent just before the `content_block_stop` event」「When `display: "omitted"` is set … receives a `thinking_delta` with an empty `thinking` string and then a single `signature_delta`」。

### 21. `input_json_delta` は部分JSON文字列で、`content_block_stop` 後にパース（741・863行）
**検証結果**: Streaming「Input JSON delta」と一致。

### 22. ストリーム途中の失敗の回復は、受信済み部分を user メッセージに含めて続きを依頼（931行）
**検証結果**: Streaming「Error recovery / Claude 4.6 and later」と一致。

### 23. 思考ブロックを改変・欠落させると400（1038行）
**検証結果**: Errors「Thinking blocks cannot be modified」。署名の欠けたブロックも「reconstructed」に該当。

### 24. `usage` の4フィールドの意味と、入力合計＝3つの入力系の和、20万＋50トークンの例（1101〜1106行）
**検証結果**: Rate limits「Cache-aware ITPM」の注記（`total_input_tokens = cache_read + cache_creation + input_tokens`、200k cached + 50 の例）と一致。

### 25. 中身が空の思考でも思考トークンは `output_tokens` として課金（1106行）
**検証結果**: Thinking「the tokens Claude spends reasoning are billed as output tokens, even when the thinking text isn't returned」。

### 26. レート制限の入力トークン（ITPM）にキャッシュ読み取りは数えない（1110行）
**検証結果**: Rate limits「`cache_read_input_tokens` … Do NOT count toward ITPM」。

### 27. 単価表（Opus 5.5 $4/$20/$5/$0.20、Sonnet 5.5 $2/$10/$2.50/$0.10、Haiku 5.5 $0.10/$0.50/$0.125/$0.01）と倍率（書き込み1.25倍、読み取り基本0.1倍・Opus/Sonnet 5.5 は0.05倍）、Haiku 5.5 の10万トークン超（$0.50/$2.50/$0.625/$0.05）、1時間キャッシュ2倍（1137〜1145行、コード1152〜1160行）
**検証結果**: Pricing「Model pricing」表・脚注2・「Prompt caching」倍率表・「Long context pricing」と完全一致。Haiku 5.5 のプロンプト長にキャッシュ読み書きを含める点もコード（`prompt_tokens`）の方針と整合。

### 28. データの処理地域の指定による割増（1373行）
**検証結果**: Pricing「`inference_geo` … incurs a 1.1x multiplier」。

### 29. コスト計算例（1,200入力＋350出力＝$0.0118、1万トークンのキャッシュ読み取り $0.002＝通常入力の1/20）（1242行）
**検証結果**: 単価表から再計算して一致。

### 30. コラム: 公式SDKの自動リトライは既定2回で `retry-after` を尊重、型付き例外・ストリーミングヘルパー・同期/非同期を提供（1383〜1388行）
**検証結果**: Errors「The official SDK automatically retries transient failures … with exponential backoff, twice by default, honoring the `retry-after` header when present」、SDK error types、Streaming「Get the final message without handling events」。

---

## ⚠️ 要確認（古い可能性あり）

### 1. 408 をリトライ対象とする（453行・485行 `RETRYABLE_STATUS`・まとめ2017行）
**記述**: 「408（タイムアウト）/ 409（競合）| `APIError` | する」
**懸念点**: 公式 Errors ページの HTTP エラー一覧に 408 は載っていない（タイムアウトは 504 `timeout_error`、または 500 の `timeout_error` として説明）。
**検索結果**: 408 の再試行は公式 SDK（Python/TS）の実装上の慣例（408/409/429/5xx を再試行）で、API ドキュメントの明記ではない。
**推奨対処**: コードはそのままでよい（害はない）。本文に「408 は API の一覧にはないが、プロキシ等が返す場合に備え SDK と同様に再試行対象とする」と一言添えるとより正確。

### 2. 自分で設定した spend limit に達したときの挙動に触れていない（459行・1373行）
**記述**: 「組織の月の利用上限に達した429には `retry-after` ヘッダーがなく…」「Consoleの利用上限（spend limit）と組み合わせて身を守ってください。」
**懸念点**: 本文の429は「ティアの月額上限（spend cap）」のケースで正しい。しかし本書が推奨する「自分で設定した spend limit」に達した場合は、**HTTP 400 `invalid_request_error`**（メッセージ `You have reached your specified API usage limits` / workspace 版）になる。読者が設定した上限で止まったとき「429ではなく400」になる点が書かれていない。
**検索結果**: Rate limits「Setting your own spend limit」「When usage reaches a spend limit you set, requests return HTTP 400 with error type `invalid_request_error`」。Errors の 400 の説明にも同旨。
**推奨対処**: 459行の後に1文追加。例:「なお、Consoleで自分で設定した利用上限（spend limit）に達した場合は、429ではなく400（`invalid_request_error`）が返ります。400系なので本書のクライアントは再試行せず、すぐに例外になります。」（コード変更は不要。400はもともとリトライ対象外）

### 3. 「`content_block_delta` の `delta` には4つの種類があります」（739行・1038行）
**記述**: 「`text_delta`・`thinking_delta`・`signature_delta`・`input_json_delta`」の4種
**懸念点**: Messages API リファレンスには `citations_delta` もある（引用付き応答。第6章の Web 検索などで出現し得る）。`_apply_delta()` は `case other:` で未知の delta を無視するので落ちはしないが、`stream_messages()` で Web 検索を使うと復元した `text` ブロックから引用（citations）が欠ける。
**推奨対処**: 「本書で扱う主な種類は4つです（引用付きの応答では `citations_delta` も届きますが、本書のパーサーは無視します）」のように限定表現にする。

### 4. コラム「公式SDK: 10分を超えそうな非ストリーミングは事前に警告」（1383行）
**記述**: 「同様（10分を超えそうな非ストリーミングは事前に警告）」
**懸念点**: 公式は「validates that your non-streaming Messages API requests are not expected to exceed a 10-minute timeout」。Python SDK の実装では警告ではなくエラー（例外）を送出する。
**推奨対処**: 「10分を超えそうな非ストリーミングは送信前にエラーにする」に修正。

### 5. 「429や529の応答には `retry-after` ヘッダーが付くことがあります」（473行）
**記述**: 「429や529の応答には…」
**懸念点**: 公式で `retry-after` が明記されているのは 429（レート制限・fast mode・Claude Code workspace）のみ。529 で付くとの記述はない。
**推奨対処**: 「429の応答には `retry-after` が付くことがあります（他のステータスでも付いていれば従います）」程度に弱める。コードは全ステータスでヘッダーを見るので変更不要。

---

## ❌ 要修正（誤りの可能性が高い）

該当なし。

---

## 総評

第4章のAPI仕様（エラー型、リトライ対象、spend cap の 429 判定、SSE のイベント順序・delta・error イベント、usage と料金・倍率）は、公式ドキュメントと高い精度で一致しています。単価表は Haiku 5.5 の10万トークン超の価格まで正確です。指摘はいずれも表現の補強レベルで、特に⚠️2（自分で設定した spend limit は400）は読者が実際に遭遇しやすいため、1文の追記を推奨します。SDK の既定リトライ2回・`retry-after` 尊重はErrorsページで確認済みです。

---

## 対応（2026-11-07）

- ⚠️1（408）: 4.2節の上限の段落に「408はAPIのエラー一覧にはないが、プロキシなどが返す場合に備え、公式SDKと同様に再試行の対象にする」を追記。コードは変更なし。
- ⚠️2（spend limit）: 同じ段落に「Consoleで自分で設定した利用上限（spend limit）に達すると429ではなく400（`invalid_request_error`）。400系なので再試行せず即例外」を追記。既存の429の説明は「ティアで決まる組織の月の利用上限（spend cap）」と明確化し、表の行名も「429（ティアの月の利用上限）」に変更（`enforced_spend_limit_reached`・`retry-after` なしの記述は従来どおり）。
- 402 / 504（統合レポートの推奨4）: 4.1節のNOTEを「402と409は `APIError`、504は `InternalServerError`（5xx）として扱う。SSEの `error` イベントで届く `timeout_error` も `InternalServerError` にそろえる」と具体化。4.2節のリトライ表に「402（支払いの問題）| `APIError` | しない」行を追加し、5xx行を「500 / 504 / 529」に。
  - コード: `_TYPE_TO_ERROR` に `"timeout_error": InternalServerError` の1行を追加（4.1節と完成版の2か所）。公開インターフェース・例外クラスの一覧（codebase-spec）は変更なし。リトライ判定は従来どおりで、402は再試行せず（4xx）、504は再試行する（5xx）ことを確認。
- ⚠️3（delta の種類）: 「本書で扱う主な種類が4つ（引用付きの応答では `citations_delta` も届くが本書のパーサーは無視）」に限定。後段の「4種類のdelta」も「主な4種類」に。
- ⚠️4（SDKの10分チェック）: コラム表を「送信前にエラーにする」に修正。
- ⚠️5（retry-after）: 「429の応答には `retry-after` が付くことがある（他のステータスでも付いていれば従う）」に弱めた。
