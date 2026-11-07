# ファクトチェックレポート

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_03.md
検証日: 2026-11-07
検証クレーム数: 37件
  ✅ 検証済み: 30件
  ⚠️ 要確認: 4件
  ❌ 要修正: 3件（原稿修正済み）

主な一次情報（取得日 2026-11-07）:
- Messages API リファレンス: https://platform.claude.com/docs/en/api/messages.md（Request / Response スキーマ、StopReason、RefusalStopDetails、Usage）
- Migration 2026-10-21: https://platform.claude.com/docs/en/api/migration-2026-10-21.md
- Versions: https://platform.claude.com/docs/en/api/versioning.md
- Errors（Common validation errors 含む）: https://platform.claude.com/docs/en/api/errors.md
- Handling stop reasons / Thinking / Effort / Models overview / Pricing / Prompt caching / Rate limits / Authentication
- httpx timeouts: https://www.python-httpx.org/advanced/timeouts/

---

## ✅ 検証済み（正確）

### クレーム1
**記述**: メソッドは `POST`、URLは `https://api.anthropic.com/v1/messages`
**検証結果**: Messages API リファレンス。

### クレーム2
**記述**: 「本書では最新版の `2026-10-21` を使います」「同じボディでも、指定するバージョンによって受け付けられる項目が変わる」
**検証結果**: Versions ページで 2026-10-21 が最新。2023-06-01 との差分（sampling パラメータ削除など）あり。

### クレーム3
**記述**: 「`httpx` の `json=` 引数でボディを渡すと、このヘッダー（content-type）は自動で付きます」
**検証結果**: httpx の `json=` は `Content-Type: application/json` を設定する。

### クレーム4
**記述**: ベータ機能は `anthropic-beta: <ベータ名>` ヘッダー
**検証結果**: Messages リファレンスおよび beta-headers ドキュメント。

### クレーム5
**記述**: 必須3項目 `model`・`max_tokens`・`messages`、`max_tokens` を省略すると400
**検証結果**: リファレンスで `max_tokens: number` は optional 表記なし（必須）。

### クレーム6
**記述**: 「モデルIDに日付の接尾辞は付きません」
**検証結果**: Models overview「Every Claude model ID is a pinned snapshot, including the dateless IDs used from the 4.6 generation on.」

### クレーム7
**記述**: 任意項目表（`system` 文字列またはブロック配列、`stop_sequences`、`output_config`（effort / format）、`tools`、`tool_choice`、`stream`）
**検証結果**: Messages リファレンスと一致。`output_config.format` は `{"type":"json_schema","schema":...}`。

### クレーム8
**記述**: `content` の文字列とブロック配列は同じ意味（文字列は text ブロック1つの省略形）
**検証結果**: リファレンスの MessageParam.content（string または ContentBlockParam 配列）。

### クレーム9
**記述**: 「連続した同じ `role` のメッセージは、API側で1つのターンにまとめて扱われます」
**検証結果**: リファレンス「Consecutive `user` or `assistant` turns in your request will be combined into a single turn.」

### クレーム10
**記述**: 「2026-10-21版では、既定値と同じ値を送った場合でも400エラーになります」（temperature / top_p / top_k）
**検証結果**: Migration「returns a 400 error, even at the parameter’s default value.」

### クレーム11
**記述**: Opus 5.5 は adaptive thinking が常に有効、思考トークンも `max_tokens` に含まれる
**検証結果**: Models overview「Adaptive (always on)」。Thinking「they count toward `max_tokens` alongside the response text」。

### クレーム12
**記述**: レスポンスの `id`（msg_）・`type`（"message"）・`role`（常に "assistant"）・`model`
**検証結果**: リファレンス Message オブジェクト。

### クレーム13
**記述**: 「既定では `thinking` フィールドの中身は空文字」「signature（改ざん検知用の署名）」
**検証結果**: Thinking「`"omitted"`: thinking blocks are returned with an empty `thinking` field. The `signature` field still carries the encrypted full thinking」。Opus 5.5 は omitted が既定。

### クレーム14
**記述**: `stop_reason` 表（end_turn / max_tokens / stop_sequence / tool_use / pause_turn / refusal）
**検証結果**: リファレンスの StopReason 列挙と一致（pause_turn「we paused a long-running turn. You may provide the response back as-is」）。

### クレーム15
**記述**: `stop_details` の `type` は `"refusal"`、`category` に `"cyber"`・`"bio"` など、該当なしなら `null`、`explanation` は文言が変わり得る
**検証結果**: RefusalStopDetails: category = cyber / bio / frontier_llm / reasoning_extraction / general_harms / null、explanation「not guaranteed to be stable」。`stop_details` は refusal 以外で null。

### クレーム16
**記述**: 「ほかに `model_context_window_exceeded`…という値も載っています」
**検証結果**: StopReason 列挙に含まれる。

### クレーム17
**記述**: usage 表（`input_tokens` はキャッシュを使わなかった分、`output_tokens` は思考を含む、cache_creation / cache_read）
**検証結果**: リファレンス「Total input tokens in a request is the summation of `input_tokens`, `cache_creation_input_tokens`, and `cache_read_input_tokens`.」

### クレーム18
**記述**: 「`output_tokens_details.thinking_tokens` を見ると、そのうち思考に使った量がわかります」
**検証結果**: リファレンス Usage.output_tokens_details.thinking_tokens（「Always ≤ `output_tokens`」）。

### クレーム19
**記述**: 「`thinking` ブロックの中身が空でも、思考の分は出力トークンとして課金される」
**検証結果**: Thinking「billed as output tokens, even when the thinking text isn’t returned to you」。

### クレーム20
**記述**: 「usage には、ここに挙げた以外の項目が含まれることもあります」
**検証結果**: `cache_creation`・`inference_geo`・`server_tool_use`・`service_tier`・`speed` 等がある。Versions「Add additional values to the output」。

### クレーム21
**記述**: `request-id` ヘッダー（`req_`）、エラーボディの `request_id` も同じ値
**検証結果**: Errors「Request ID」節。

### クレーム22
**記述**: 「`httpx` の既定のタイムアウトは5秒」
**検証結果**: httpx「raise a TimeoutException after 5 seconds of network inactivity」。

### クレーム23
**記述**: 「値は `low`・`medium`・`high`・`xhigh`・`max` の5段階で、Opus 5.5 の既定は `medium`」
**検証結果**: リファレンス output_config.effort の列挙、Models overview「Default effort: medium」（Sonnet 5.5 は high、Haiku 5.5 は medium）。

### クレーム24
**記述**: モデル料金表（$4/$20、$2/$10、$0.10/$0.50（10万トークン以下））
**検証結果**: Pricing と一致（Haiku の閾値はプロンプト長）。

### クレーム25
**記述**: 実行結果の概算コスト（$0.00095 / $0.00088 / $0.00432 / $0.01318 / $0.00013）、「コストが3倍ほど」「およそ30分の1」
**検証結果**: 単価から再計算しすべて一致（0.01318/0.00432≒3.05、0.00432/0.000126≒34）。

### クレーム26
**記述**: 「止まった文字列そのものは、回答の本文には含まれません」「`stop_sequence` フィールドに、実際に当たった文字列が入ります」
**検証結果**: リファレンス「the response `stop_sequence` value will contain the matched stop sequence」。

### クレーム27
**記述**: 「思考のブロックは、削除や改変をせずに送り返すことが求められています」
**検証結果**: Errors「Thinking blocks cannot be modified」／Thinking「pass them unchanged」。

### クレーム28
**記述**: エラーボディ `{"type":"error","error":{"type":"not_found_error","message":...},"request_id":...}`
**検証結果**: Errors「Error shapes」の例と同形。

### クレーム29
**記述**: 「404は、モデルIDの誤りでもURLの誤りでも返ります」
**検証結果**: Errors「404 - not_found_error: The requested resource was not found」。

### クレーム30
**記述**: `is_retryable()`: 408・409・429・5xx をリトライ対象
**検証結果**: Errors「409 - conflict_error… Resolve the conflict, then retry」「500… Retry the request with exponential backoff」、公式SDKも 408/409/429/5xx をリトライ。

---

## ⚠️ 要確認（古い可能性あり）

### クレーム31
**記述**: 「Messages APIに送るリクエストには、次の3つのヘッダーが必須です」（`x-api-key`）
**懸念点**: 公式は `Authorization: Bearer <key>` を主に記載し、`x-api-key` を「legacy」と表記。両方とも受け付けられる。
**検索結果**: auth.md「You can also send the key in the legacy `x-api-key: YOUR_API_KEY` header in place of `Authorization`.」
**推奨対処**: 3.1節の表の下に「認証は `Authorization: Bearer <APIキー>` でも可能（公式ドキュメントはこちらを主に記載）」と NOTE を追加。

### クレーム32
**記述**: エラー表（400/401/403/404/413/429/500/529）
**懸念点**: 一次情報には 402 `billing_error`（支払い・残高の問題）、409 `conflict_error`、504 `timeout_error` もある。`is_retryable()` は 409 を扱っているのに表に無い。
**検索結果**: Errors ページの HTTP errors 一覧。
**推奨対処**: 表に 402（リトライしない・Billing を確認）、504 `timeout_error`（する／長い処理はストリーミング）を追加。409 は本文の説明で十分。

### クレーム33
**記述**: 「400番台は、同じリクエストを何度送っても同じ結果になるので、リトライしません。ただし429だけは例外で、時間をおけば成功する一時的な制限です」
**懸念点**: (a) 自分で設定した spend limit に達した場合も 400 `invalid_request_error` が返る（ボディは正しい）。(b) 使用ティアの月額上限（spend cap）到達時の 429 は `retry-after` が付かず、翌月まで失敗し続ける（`error.details.error_code` = `enforced_spend_limit_reached`）。
**検索結果**: Rate limits「When usage reaches a spend limit you set, requests return HTTP 400」「A tier spend-cap 429 has no `retry-after` header and keeps failing until access resumes」。
**推奨対処**: 「よくある400エラー」に「Console で設定した利用上限に達した（message が “You have reached your specified … usage limits”）」を追加。429 の扱いは第4章のリトライ実装で `enforced_spend_limit_reached` を非リトライにする旨を追記。

### クレーム34
**記述**: 「`role` には `user`（あなたのプログラム側）か `assistant`（Claude側）を入れます」
**懸念点**: Opus 5.5・Sonnet 5.5・Haiku 5.5 などでは、会話途中に `{"role": "system"}` メッセージを追加できる機能がある（キャッシュを壊さずに system 指示を足す用途）。本書の範囲では user/assistant の説明で足りる。
**検索結果**: Prompt caching「Append a `{"role": "system"}` message to `messages` instead of editing the top-level `system` field」（mid-conversation system messages）。
**推奨対処**: 本章は現状でよい。第7章（キャッシュ）で触れるかを検討。

---

## ❌ 要修正（誤りの可能性が高い）

### クレーム35
**記述**: 見出し「2026-10-21版での注意点」の下で prefill 不可を2つ目の注意点として列挙／まとめ「2026-10-21版では `temperature` などとprefillは400エラーになり」
**問題**: prefill 不可は API バージョン 2026-10-21 の変更ではなく、**Claude 4.6 以降のモデルの制約**。Migration ガイド・Versions の 2026-10-21 変更点に prefill の記載はない（記載は document ブロック・citations・sampling パラメータのみ）。
**正しい情報**: Errors「Prefill not supported: Claude 4.6 and later models and Claude Mythos Preview do not support prefilling assistant messages… returns a 400 `invalid_request_error`」。
**修正案（適用済み）**: 見出しを「2026-10-21版と最新モデルでの注意点」、導入文を「APIバージョン `2026-10-21` と、本書で使うモデルの注意点」に変更。prefill の段落に「こちらはAPIバージョンの変更ではなく、Claude 4.6以降のモデルの制約です。」を追加。まとめを「2026-10-21版では `temperature` などが、本書で使うモデルではprefillが400エラーになり」に修正。

### クレーム36
**記述**: 「`tool_choice` は…特定のツールを強制する指定は、本書で使うモデルでは400エラーになります」／「`tool_choice` で特定のツールを強制した（本書のモデルでは使えない）」
**問題**: 強制（`any` / `tool`）が 400 になるのは Opus 5.5・Sonnet 5.5（と Fable 5.1・Mythos 5.1）。本書で使う Haiku 5.5 は対応している（Pricing の tool use system prompt 表で Haiku 5.5 に「any, tool: 406 tokens」がある）。
**正しい情報**: Errors「Claude Opus 5.5, Claude Sonnet 5.5, Claude Fable 5.1, and Claude Mythos 5.1 don’t support forced tool use.」
**修正案（適用済み）**: 「特定のツールを強制する指定（`any`・`tool`）は、本書の既定の Opus 5.5 と Sonnet 5.5 では400エラーになります。」／「（Opus 5.5・Sonnet 5.5 では使えない）」

### クレーム37
**記述**: モデル表「`claude-opus-5-5`｜本書の既定。もっとも高性能」／「すべてを最上位モデルで処理する必要はありません」
**問題**: 現行ラインナップでは Claude Fable 5.1（$10/$50、「demanding reasoning and long-horizon agentic work」）が Opus 5.5 より上位。Opus 5.5 を無条件に「もっとも高性能」「最上位」とするのは誤り。
**正しい情報**: Models overview「start with Claude Opus 5.5 for most workloads. Use Claude Fable 5.1 for demanding reasoning…」
**修正案（適用済み）**: 「本書の既定。3つの中でもっとも高性能」／「すべてを高性能なモデルで処理する必要はありません。」

---

## 総評

レスポンス構造（content・stop_reason 全値・stop_details・usage・output_tokens_details）、エラー形状、effort、料金・コスト計算は一次情報と正確に一致しており、品質は高い。修正は (1) prefill 不可を API バージョンの変更として説明していた点、(2) 強制 tool_choice の 400 を Haiku 5.5 にも当てはめていた点、(3) Opus 5.5 を「最上位」と表現していた点の3つ。利用上限到達時の 400 と、ティア上限での 429（retry-after なし）は第4章のリトライ設計に直結するため追記を推奨する。

---

## facts.md（references/claude-api-facts.md）への修正案

第0〜3章の確認で使った一次情報に基づく修正案です（facts.md 自体は編集していません）。

1. **uv の記述（❌）**: 「uv 0.13 以降は既定で src 構成」→ **「uv 0.12 以降」**。uv 公式「Prior to v0.12, uv did not define a build system for applications by default.」（2026-11-07時点の最新は 0.13.7）
2. **prefill（❌・表現）**: 「リクエストの注意（2026-10-21 版）」の中に prefill 不可を置いているが、これは **Claude 4.6 以降のモデルの制約**で API バージョンの変更ではない。見出しを「リクエストの注意（2026-10-21 版・5.5 世代モデル）」とし、prefill の行に「モデル側の制約（Claude 4.6 以降）」と明記。2026-10-21 版の Messages API の破壊的変更は (a) sampling パラメータ削除、(b) assistant メッセージ直下の `document` ブロックは 400、(c) user メッセージの text ブロックに空でない `citations` は 400、の3点。
3. **認証ヘッダー（⚠️）**: 公式は `Authorization: Bearer <key>` を主に記載し `x-api-key` を「legacy」と表記（両方受け付け）。本教材は `x-api-key` を継続してよいが、「公式は Bearer を主に記載。`x-api-key` も有効（legacy）」と注記し、第2・3章で一言触れる方針を明記。
4. **tool_choice**: 「`any` / `tool` は Opus 5.5・Sonnet 5.5 で 400」は正しいが、**Haiku 5.5 は強制に対応**する旨を追記（本教材のワーカーで使うため誤用されやすい）。count_tokens でも同じく 400 になる。
5. **thinking**: 「既定では中身が空文字」に「`display` の既定が `"omitted"`（5.x 世代すべて）。`thinking: {"type":"adaptive","display":"summarized"}` で要約が返る」を追記。Sonnet 5.5 は `disabled` 不可（最小は `{"type":"between_tools"}`）、Haiku 5.5 は `disabled` 可。effort 既定は Opus 5.5=medium、Sonnet 5.5=high、Haiku 5.5=medium。
6. **stop_reason**: 一覧に **`model_context_window_exceeded`** を追加。`stop_details` は refusal 以外 null、category は `cyber` / `bio` / `frontier_llm` / `reasoning_extraction` / `general_harms` / null。
7. **usage**: `output_tokens_details.thinking_tokens`（思考トークンの内訳、`output_tokens` に含まれる）を追加。
8. **エラー**: 402 `billing_error`、409 `conflict_error`、504 `timeout_error` を一覧に追加。「**自分で設定した spend limit 到達は 400 `invalid_request_error`**（message: `You have reached your specified (workspace) API usage limits`）」「**ティアの月額上限到達は 429 だが `retry-after` なし・`error.details.error_code` = `enforced_spend_limit_reached`** → リトライしない」を追記（第4章のリトライ判定に必須）。
9. **料金**: Haiku 5.5 の閾値は「プロンプト（キャッシュ読み書きを含む全入力）10万トークン」。超過時は $0.50 / $2.50（キャッシュ読み $0.05）。キャッシュ読み 0.05 倍（Opus/Sonnet 5.5）は Pricing で確認済み（Opus $0.20、Sonnet $0.10）。1h TTL 書き込みは 2 倍。
10. **Console**: 「利用上限（spend limit）の設定を推奨」に、**組織の spend limit は Billing 画面（settings/billing）の Spend limits、ワークスペースの spend limit は Workspaces 画面のパネル、Limits 画面（usage/limits）はティアとレート制限の表示・設定、Default Workspace には spend limit を設定できない**を追記。APIキー作成時に Expiration と Linked account を選ぶこと、使用ティアは Start / Build / Scale（新規は Evaluation）であることも追記。
11. **サーバーツール**: `web_search_20260209` / `web_fetch_20260209` に加え、リファレンスには新しい `web_search_20260318` / `web_fetch_20260318`（web_fetch は 20260309 も）がある。第6章執筆・チェック時に推奨版を確認すること。
12. **モデル位置づけ**: 現行最上位は Claude Fable 5.1（$10/$50、`claude-fable-5-1`）。「Opus 5.5 は本教材の既定（多くのワークロードの推奨）」とし、「最上位」とは書かない旨を明記。
13. （参考）Opus 5.5 / Sonnet 5.5 / Haiku 5.5 では会話途中の `{"role": "system"}` メッセージが使える（キャッシュを壊さずに指示を追加）。第7章で扱うか判断。
