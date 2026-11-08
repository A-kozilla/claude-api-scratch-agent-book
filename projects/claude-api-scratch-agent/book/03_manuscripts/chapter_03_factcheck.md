# ファクトチェックレポート

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_03.md
検証日: 2026-11-08（前回 2026-11-07 の再検証。原稿修正後の版を対象）
検証クレーム数: 40件
  ✅ 検証済み: 33件
  ⚠️ 要確認: 7件
  ❌ 要修正: 0件

主な一次情報（2026-11-08 取得）:
- Messages API リファレンス: https://platform.claude.com/docs/en/api/messages.md（Request / Message / StopReason / RefusalStopDetails / Usage）
- Versions: https://platform.claude.com/docs/en/api/versioning.md
- Migration 2026-10-21: https://platform.claude.com/docs/en/api/migration-2026-10-21.md
- Errors（Common validation errors 含む）: https://platform.claude.com/docs/en/api/errors.md
- Rate limits: https://platform.claude.com/docs/en/api/rate-limits.md
- Models overview: https://platform.claude.com/docs/en/about-claude/models/overview.md
- Effort: https://platform.claude.com/docs/en/build-with-claude/effort.md
- Thinking: https://platform.claude.com/docs/en/build-with-claude/thinking.md
- Pricing: https://platform.claude.com/docs/en/about-claude/pricing.md
- Authentication: https://platform.claude.com/docs/en/manage-claude/authentication.md
- httpx: インストール済み httpx 0.28.1 の `DEFAULT_TIMEOUT_CONFIG`（`Timeout(timeout=5.0)`）

---

## 前回（2026-11-07）指摘の反映状況

| 前回 | 内容 | 反映 |
|---|---|---|
| ❌35 | prefill 不可を API バージョンの変更として説明 | ✅ 反映済み（L192 見出し「2026-10-21版と最新モデルでの注意点」、L206「APIバージョンの変更ではなく、Claude 4.6以降のモデルの制約」、L1421 まとめ） |
| ❌36 | 強制 `tool_choice` の400を全モデルに適用 | ✅ 反映済み（L140「本書の既定の Opus 5.5 と Sonnet 5.5 では400」、L1276「Opus 5.5・Sonnet 5.5 では使えない」） |
| ❌37 | Opus 5.5 を「最上位」と表現 | ✅ 反映済み（L817「3つの中でもっとも高性能」、L821「高性能なモデル」） |
| ⚠️31 | `x-api-key` は公式では legacy 扱い | **未反映**（下記⚠️1） |
| ⚠️32 | エラー表に 402 / 504 がない | **未反映**（下記⚠️2。第4章側では反映済み） |
| ⚠️33 | 自分で設定した spend limit は400、ティア上限の429はリトライ不可 | **未反映**（下記⚠️3。第4章側では反映済み） |
| ⚠️34 | `role: "system"` メッセージの存在 | 未反映（本章は現状でよいとした項目。下記⚠️4） |

---

## ✅ 検証済み（正確）

### クレーム1（L51）
**記述**: メソッドは `POST`、URLは `https://api.anthropic.com/v1/messages`
**検証結果**: Messages リファレンス・Errors の cURL 例と一致。

### クレーム2（L75–76）
**記述**: 「本書では最新版の `2026-10-21` を使います」「指定するバージョンによって受け付けられる項目が変わる」
**検証結果**: Versions の Version history で `2026-10-21` が最新。2023-06-01 との差分（sampling パラメータ削除、assistant 直下の `document`、user の `citations`）あり。

### クレーム3（L80）
**記述**: `httpx` の `json=` で渡すと content-type は自動で付く
**検証結果**: httpx の `json=` は `Content-Type: application/json` を設定する（偽APIの受信ヘッダーでも確認）。

### クレーム4（L84）
**記述**: ベータ機能は `anthropic-beta: <ベータ名>` ヘッダー
**検証結果**: Errors ページ（`thinking-binding-controls-2026-08-01` beta header 等の記述）と beta-headers ドキュメント。

### クレーム5（L89・L112）
**記述**: 必須3項目 `model`・`max_tokens`・`messages`、`max_tokens` 省略で400
**検証結果**: リファレンスで3項目とも optional 表記なし。

### クレーム6（L104）
**記述**: 「モデルIDに日付の接尾辞は付きません」
**検証結果**: Models overview「Every Claude model ID is a pinned snapshot, including the dateless IDs used from the 4.6 generation on.」ID は `claude-opus-5-5` / `claude-sonnet-5-5` / `claude-haiku-5-5`。

### クレーム7（L124–131）
**記述**: 任意項目表（`system` は文字列またはブロック配列、`stop_sequences`、`output_config`（effort / format）、`tools`、`tool_choice`、`stream`）
**検証結果**: リファレンス「system: optional string or array of TextBlockParam」ほか一致。

### クレーム8（L139–140）
**記述**: `tool_choice` は `auto` / `none` を使う。`any`・`tool` は Opus 5.5 と Sonnet 5.5 で400
**検証結果**: Errors「Forced tool use not supported: Claude Opus 5.5, Claude Sonnet 5.5, Claude Fable 5.1, and Claude Mythos 5.1 … returns a 400」「`auto` (the default) and `none` are accepted」。Haiku 5.5 は対象外（前回❌36の修正が正しい）。

### クレーム9（L167–168）
**記述**: 文字列の `content` は text ブロック1つの省略形
**検証結果**: リファレンス MessageParam.content（string または ContentBlockParam 配列）。

### クレーム10（L183）
**記述**: 「連続した同じ `role` のメッセージは、API側で1つのターンにまとめて扱われます」
**検証結果**: リファレンス「Consecutive `user` or `assistant` turns in your request will be combined into a single turn.」

### クレーム11（L197–199）
**記述**: `temperature`・`top_p`・`top_k` は既定値と同じ値でも400
**検証結果**: Migration「returns a 400 error, even at the parameter’s default value.」Versions「returns a 400 error on every model.」

### クレーム12（L202–206）
**記述**: prefill は本書のモデルで400。「APIバージョンの変更ではなく、Claude 4.6以降のモデルの制約」
**検証結果**: Errors「Prefill not supported: Claude 4.6 and later models and Claude Mythos Preview do not support prefilling assistant messages … returns a 400」。Versions の 2026-10-21 変更点に prefill はない。

### クレーム13（L270–273）
**記述**: Opus 5.5 は adaptive thinking が常に有効、思考トークンも `max_tokens` に含まれる
**検証結果**: Models overview「Adaptive (always on)」。Thinking「they count toward `max_tokens` alongside the response text」。

### クレーム14（L296–299・L334–348）
**記述**: `id`（msg_）・`type`（"message"）・`role`（常に "assistant"）・`model`
**検証結果**: リファレンス Message「This will always be `"assistant"`」等。

### クレーム15（L303–304・L367）
**記述**: 既定では `thinking` フィールドは空文字、`signature` は改ざん検知用
**検証結果**: Thinking「`"omitted"`: thinking blocks are returned with an empty `thinking` field. The `signature` field still carries the encrypted full thinking」「`"omitted"` (the default on these models)」。

### クレーム16（L389–396）
**記述**: `stop_reason` 表（end_turn / max_tokens / stop_sequence / tool_use / pause_turn / refusal）
**検証結果**: リファレンス StopReason 列挙と一致。pause_turn「You may provide the response back as-is in a subsequent request to let the model continue.」

### クレーム17（L414–419）
**記述**: `stop_details.type` は `"refusal"`、`category` に `"cyber"`・`"bio"` など、該当なしなら `null`、`explanation` の文言は変わり得る
**検証結果**: RefusalStopDetails: category = cyber / bio / frontier_llm / reasoning_extraction / general_harms / null、explanation「This text is not guaranteed to be stable.」

### クレーム18（L421）
**記述**: `model_context_window_exceeded` も載っている
**検証結果**: StopReason「`"model_context_window_exceeded"`: we exceeded the model's context window」。

### クレーム19（L432–437）
**記述**: usage 表（`input_tokens` はキャッシュを使わなかった分、`output_tokens` は思考を含む、cache_creation / cache_read）
**検証結果**: リファレンス「Total input tokens in a request is the summation of `input_tokens`, `cache_creation_input_tokens`, and `cache_read_input_tokens`.」Rate limits「`input_tokens` (tokens after the last cache breakpoint)」。

### クレーム20（L444）
**記述**: `output_tokens_details.thinking_tokens` で思考の量がわかる
**検証結果**: リファレンス「Number of output tokens the model generated as internal reasoning … Always ≤ `output_tokens`」。

### クレーム21（L445）
**記述**: 中身が空でも思考分は出力トークンとして課金
**検証結果**: Thinking「billed as output tokens, even when the thinking text isn’t returned to you」。

### クレーム22（L450–451）
**記述**: usage にはほかの項目が含まれることもある
**検証結果**: `cache_creation`・`inference_geo`・`server_tool_use` 等がある。Versions「Add additional values to the output」。

### クレーム23（L457–463）
**記述**: `request-id` ヘッダー（`req_`）、エラーボディの `request_id` も同じ値
**検証結果**: Errors「Every API response includes a unique `request-id` header … The same identifier appears as the `request_id` field in error response bodies.」

### クレーム24（L514）
**記述**: 「`httpx` の既定のタイムアウトは5秒」
**検証結果**: httpx 0.28.1 の `DEFAULT_TIMEOUT_CONFIG` = `Timeout(timeout=5.0)`。

### クレーム25（L723）
**記述**: 簡単な質問では `thinking` ブロックが含まれず `text` だけになることもある
**検証結果**: Thinking「When you use `thinking.type: "adaptive"` and the model skips thinking for a simple request, no thinking block is produced regardless of `display`.」

### クレーム26（L804・L958–959）
**記述**: 止まった文字列は本文に含まれず、`stop_sequence` フィールドに当たった文字列が入る
**検証結果**: リファレンス「the response `stop_sequence` value will contain the matched stop sequence」「Which custom stop sequence was generated」。

### クレーム27（L809）
**記述**: effort は `low`・`medium`・`high`・`xhigh`・`max` の5段階、Opus 5.5 の既定は `medium`
**検証結果**: リファレンス enum、Effort「Claude Opus 5.5 supports all five effort levels, and `medium` is the default」。

### クレーム28（L815–819）
**記述**: モデル表（$4/$20、$2/$10、$0.10/$0.50（10万トークン以下））、Opus 5.5「3つの中でもっとも高性能」
**検証結果**: Pricing「Claude Haiku 5.5 (for prompts up to 100,000 tokens) $0.10 / $0.50」ほか一致。Models overview で上位に Fable 5.1 があり、「3つの中で」の限定は正確。

### クレーム29（L947–987）
**記述**: 実行結果の概算コスト（$0.00095 / $0.00088 / $0.00432 / $0.01318 / $0.00013）、「3倍ほど」「およそ30分の1」
**検証結果**: 単価から再計算しすべて一致（13184/4324≒3.05、4324/126≒34）。※比較対象の表示については code_verify の⚠️を参照。

### クレーム30（L1035–1036）
**記述**: 思考のブロックは削除や改変をせずに送り返す
**検証結果**: Errors「Thinking blocks cannot be modified … pass back every `thinking` and `redacted_thinking` block … exactly as received, including blocks whose `thinking` field is empty.」

### クレーム31（L1229–1236）
**記述**: エラーボディ `{"type":"error","error":{"type":"not_found_error","message":...},"request_id":...}`
**検証結果**: Errors「Error shapes」と同形（request_id の例 `req_011CSHoEeqs5C35K2UUqR7Fy` も公式例と同一）。

### クレーム32（L1402）
**記述**: 404 はモデルIDの誤りでもURLの誤りでも返る
**検証結果**: Errors「404 … Check the endpoint path and any resource IDs in the request URL.」

### クレーム33（L1004）
**記述**: Messages API はステートレスで、履歴は呼び出し側が毎回送る
**検証結果**: リファレンスの `messages`（会話全体を毎回渡す設計）と一致。

---

## ⚠️ 要確認（古い可能性あり）

### ⚠️1（L59–67）認証ヘッダー【前回⚠️31・未反映】
**記述**: 「Messages APIに送るリクエストには、次の3つのヘッダーが必須です」（`x-api-key`）
**懸念点**: 公式は `Authorization: Bearer <key>` を主に記載し、`x-api-key` を legacy と表記（どちらも有効）。読者が公式ドキュメントと見比べたときに混乱する。
**検索結果**: Authentication「You can also send the key in the legacy `x-api-key: YOUR_API_KEY` header in place of `Authorization`.」
**推奨対処**: L67 の段落の後に NOTE を追加。
> **NOTE**: 公式ドキュメントでは `Authorization: Bearer <APIキー>` ヘッダーで認証する例が主に載っています。`x-api-key` も引き続き有効な（従来からの）書き方で、本書はこちらで統一します。どちらか一方を送れば認証されます。

### ⚠️2（L1249–1258・L1336）エラー表の網羅性と408【前回⚠️32・未反映】
**記述**: エラー表（400/401/403/404/413/429/500/529）、「表にはない408（タイムアウト）と409（競合）も…リトライ対象」
**懸念点**: 一次情報には 402 `billing_error`、409 `conflict_error`、504 `timeout_error` がある。また 408 は API のエラー一覧にない（プロキシ等が返す想定。第4章 L461 では説明済み）。
**検索結果**: Errors の HTTP errors 一覧（402 / 409 / 504 を含む。408 なし）。
**推奨対処**: 表に2行追加し、L1336 を補足。
- `| 402 | billing_error | 支払い情報の問題 | しない（Consoleで支払い情報を確認） |`
- `| 504 | timeout_error | 処理中のタイムアウト | する（長い処理はストリーミングに） |`
- L1336:「表にはない409（競合）と、APIの一覧にはないもののプロキシなどが返すことのある408（タイムアウト）も、一時的な失敗としてリトライ対象に含めています。」

### ⚠️3（L1260–1263）400系はリトライしない／429は例外【前回⚠️33・未反映】
**記述**: 「400番台は、同じリクエストを何度送っても同じ結果… ただし429だけは例外で、時間をおけば成功する一時的な制限です」
**懸念点**: (a) 自分で設定した spend limit 到達時は 400 `invalid_request_error`（ボディは正しくても失敗）。(b) ティアの月額上限（spend cap）到達の429は `retry-after` なしで翌月まで失敗し続ける。
**検索結果**: Rate limits「When usage reaches a spend limit you set, requests return HTTP 400 with error type `invalid_request_error`. The message starts with `You have reached your specified API usage limits`…」「The error type is `rate_limit_error` … but the response has no `retry-after` header. Retrying … fails until access resumes.」
**推奨対処**: 「よくある400エラー」（L1273–1276）に1行追加し、L1262 を補足。
- 追加:「Consoleで自分で設定した利用上限（spend limit）に達した（`message` が `You have reached your specified ... API usage limits` で始まる）」
- L1262:「ただし429だけは例外で、多くは時間をおけば成功する一時的な制限です（月の利用上限に達した429だけは例外で、第4章で見分け方を扱います）。」

### ⚠️4（L116）`role` の値【前回⚠️34】
**記述**: 「`role` には `user`（あなたのプログラム側）か `assistant`（Claude側）を入れます」
**懸念点**: リファレンスには `SystemMessageParam`（`role: "system"`）もある（会話途中の system 指示）。本書の範囲では user / assistant で足りる。
**推奨対処**: 本章は現状でよい。必要なら「本書で使うのは `user` と `assistant` の2つです」と限定表現にする。

### ⚠️5（L110）日本語のトークン換算
**記述**: 「日本語ではおおむね1〜2文字が1トークン前後」
**懸念点**: 公式に日本語の換算目安はない。第三者の計測では「1文字あたり約0.5〜1.5トークン」とばらつきが大きく、現行トークナイザー（Opus 4.7 で導入）では1文字≒1トークン以上になる例も報告されている。本文の「1〜2文字で1トークン」はやや少なめに見積もる方向。
**検索結果**: Models overview は英語の目安（1M tokens ≈ 555k words / 2.5M Unicode characters）のみ。第三者計測（clauder-navi.com、jangwook.net、dev.to）で幅あり。
**推奨対処**:「日本語ではおおむね1文字が1トークン前後と考えておけば十分です（正確な数は第7章のトークン計測APIで確かめられます）。」のように幅を持たせ、計測手段に誘導する。

### ⚠️6（L135）`output_config` の位置づけ
**記述**: 「`output_config` は、2026-10-21版で出力の制御をまとめて担う項目です」
**懸念点**: `output_config` は 2026-10-21 版で導入された項目ではない（Versions / Migration の 2026-10-21 変更点に記載なし。2023-06-01 版でも使える）。「この版で新しく入った」と読める。
**推奨対処**:「`output_config` は、出力の制御をまとめて担う項目です。」と版の限定を外す。

### ⚠️7（L1278・L1401）エラーメッセージに項目名が書かれている
**記述**: 「いずれも、`error.message` に問題のある項目名が書かれています」
**懸念点**: prefill の400の公式メッセージは「This model does not support assistant message prefill. The conversation must end with a user message.」で、項目名ではなく原因の説明。spend limit の400も項目名を含まない。
**推奨対処**:「いずれも、`error.message` に問題のある項目名や原因が書かれています（prefill の場合は `does not support assistant message prefill` という説明です）。」

---

## ❌ 要修正（誤りの可能性が高い）

該当なし（前回の❌3件はすべて正しく反映済み）。

---

## 総評

前回の❌3件（prefill の位置づけ、強制 `tool_choice` の対象モデル、Opus 5.5 の「最上位」表現）は一次情報どおりに修正されており、レスポンス構造・stop_reason・stop_details・usage・エラー形状・effort・料金は今回の再取得でもすべて一致した。

残る指摘は表現の補強レベル。前回の⚠️31〜33（`x-api-key` の legacy 表記、402/504、spend limit の400と spend cap の429）は第4章側では反映されたが本章は未反映のため、第3章の表と「よくある400エラー」に1〜2行ずつ足すと、第4章のリトライ表との整合が取れる。新規の⚠️は、日本語のトークン換算の目安（⚠️5）、`output_config` を2026-10-21版の項目と読める表現（⚠️6）、prefill エラーのメッセージ説明（⚠️7）の3件。

## 再チェック（2026-11-08・修正箇所）

対象: `git diff` の変更10 hunk（「よくある400エラー」の hunk は2項目に分けて計11項目）。結果: ✅9 / ⚠️1 / ❌1
一次情報: api/overview・manage-claude/authentication・api/errors・api/rate-limits・build-with-claude/effort・about-claude/pricing（本日取得）。数値はオフラインで再計算（scratchpad/recheck-a/check.py、httpx.MockTransport）。

- ❌ L70 認証NOTEの**記法**。内容は正しい（overview: `Authorization` は「Required unless `x-api-key` is set」、`x-api-key` は「Legacy fallback…, still supported」）。しかしNOTEの直後に空行がなく、次の行「APIキーは課金と結びついた…」「この点は第2章で…」がMarkdownの遅延継続でNOTEの引用ブロックに取り込まれる。また本章の他のNOTE（L423など）は1文ごとに `> ` 行を分けているのに、このNOTEは1行に3文。
  修正案: NOTEを段落「APIキーは課金と…そのまま使います。」の後ろへ移し、前後に空行を入れる。本文は `> **NOTE**: 公式ドキュメントでは、…主に載っています。` / `> \`x-api-key\` も引き続き有効な書き方で、本書はこちらで統一します。` / `> どちらか一方を送れば認証されます。` の3行に分ける。
- ✅ L113 トークン「おおむね1文字が1トークン前後（第7章のトークン計測APIで確認）」。公式の日本語換算はなく、幅を持たせた表現で第2章 L135 と一致。count_tokens エンドポイントは第7章の題材どおり。
- ✅ L138 `output_config` から「2026-10-21版で」を削除。effort.md・messages.md とも `output_config` を特定のAPI版に結び付けておらず、修正後の記述が正確。
- ✅ L983–986 出力例に `=== Opus 5.5 ===` 段を追加。`demo_model()` の送信順（Opus→Haiku）と一致。$0.00786＝(21×4＋389×20)/1M を再計算で確認。Opus 5.5 の既定 effort は `medium`（effort.md: "Claude Opus 5.5 and Claude Haiku 5.5 default to medium"）なので、出力389が low(212) と high(655) の間にあるのも妥当。
- ✅ L993「既定の effort の Opus 5.5 と比べて、およそ60分の1」。$0.00786 / $0.00013 ≒ 60（丸める前は62.4）。比較相手が明示され、code_verify の指摘は解消。
- ✅ L1260 402 `billing_error`（errors.md と一致）。リトライ「しない」は `is_retryable()` の結果（402→False）と一致。
- ✅ L1266 504 `timeout_error`（errors.md「For long-running Messages API requests, use the streaming Messages API」）。`is_retryable()` は 504→True で表の「する」と一致。
- ⚠️ L1271 429の文。spend cap の429が `retry-after` なしで回復しない点は正しい（rate-limits「Reaching your spend cap」）。ただし (1)「例外」が1文の中で二重に出てわかりにくい。(2)「月の利用上限」は、第2章や本章 L1287 では**自分で設定する spend limit（400）**の呼び名で、第4章 L457/L461 は「ティアの月の利用上限（spend cap）」と区別している。このままでは spend limit でも429になると読める。(3) 1文が約80字。
  修正案:「ただし429は例外で、多くは時間をおけば成功する一時的な制限です。」＋「ティアで決まる月の利用上限（spend cap）に達した429だけは翌月まで回復しません。見分け方は第4章で扱います。」
- ✅ L1287 「よくある400エラー」に spend limit を追加。rate-limits「HTTP 400 … starts with `You have reached your specified API usage limits`」（ワークスペース版は `specified workspace API usage limits`）。`...` はどちらにも当てはまる。※第2章の表は `specified … usage limits`（API を省略）で表記が少し違う。揃えるなら両章とも `You have reached your specified ... API usage limits` に統一。
- ✅ L1289 「項目名や原因」＋prefill の説明。errors.md「This model does not support assistant message prefill. The conversation must end with a user message.」と一致。
- ✅ L1346 408/409 の説明。errors.md に 409 `conflict_error` はあり、408 はない。「表にはない409」は本書の表を指しており正しい。第4章 L461（408はプロキシ等に備える）とも整合。※1文が約70字（任意で分割）。
