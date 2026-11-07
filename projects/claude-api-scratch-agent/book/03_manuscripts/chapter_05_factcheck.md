# ファクトチェックレポート

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_05.md
検証日: 2026-11-07
検証クレーム数: 31件
  ✅ 検証済み: 28件
  ⚠️ 要確認: 2件
  ❌ 要修正: 1件（原稿修正済み）

主な一次情報（2026-11-07 取得）:
- Tool use 概要: https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview.md
- Define tools: https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools.md
- Handle tool calls: https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls.md
- Parallel tool use: https://platform.claude.com/docs/en/agents-and-tools/tool-use/parallel-tool-use.md
- Server tools / Web search / Web fetch: https://platform.claude.com/docs/en/agents-and-tools/tool-use/server-tools.md ほか
- Handling stop reasons: https://platform.claude.com/docs/en/build-with-claude/handling-stop-reasons.md
- Errors / Thinking: https://platform.claude.com/docs/en/api/errors.md ・ build-with-claude/thinking.md
- Open-Meteo: 実際に API を呼び出して確認（geocoding-api.open-meteo.com / api.open-meteo.com）、利用規約 https://open-meteo.com/en/terms

---

## ✅ 検証済み（正確）

### 1. クライアントツールは Claude が実行せず、開発者のコードが実行する（40行）
**検証結果**: Tool use 概要「Your code runs the operation and sends back a `tool_result`.」

### 2. Tool use の5段階の流れ、ツール使用時の `stop_reason: "tool_use"`、結果後の `end_turn`（62〜66行）
**検証結果**: Tool use 概要「How tool use works」と一致。

### 3. Messages API はステートレスで、2回目のリクエストに質問・依頼・結果をすべて含める（73〜74行）
**検証結果**: 公式のクライアントツール往復例が同じ形（assistant の content と tool_result を messages に追加して再送）。

### 4. 1つの応答で複数の `tool_use` を出すことがある（並列ツール呼び出し）（79行）
**検証結果**: Parallel tool use。既定で有効（`disable_parallel_tool_use` で無効化）。

### 5. `tool_use` の前に `text` ブロックが付くことがある（93行）
**検証結果**: Web search 応答例・公式例で `text` → `tool_use`（server_tool_use）の並びを確認。

### 6. `stop_reason` 表（end_turn / tool_use / max_tokens / refusal＋`stop_details` / pause_turn）（104〜110行）
**検証結果**: Handling stop reasons。refusal 時は `stop_details` が policy category を示す。

### 7. ツール定義は入力トークンとして課金され、ツール用 system プロンプトで数百トークン上乗せ（128〜131行）
**検証結果**: Tool use 概要「Pricing」: Opus 5.5・Sonnet 5.5・Haiku 5.5 はいずれも 286 tokens（auto/none）。

### 8. `tool_choice` 既定は auto、`none` でツールを使わせない（137〜138行）
**検証結果**: Tool use 概要「With the default `tool_choice` of `{"type": "auto"}`」。Errors「`{"type": "auto"}` (the default) and `{"type": "none"}` are accepted」。

### 9. `any` / `tool` の強制は Opus 5.5・Sonnet 5.5 で400（141〜147行）
**検証結果**: Errors「Forced tool use not supported」: Opus 5.5・Sonnet 5.5（ほか Fable 5.1・Mythos 5.1）で 400 `invalid_request_error`。

### 10. サーバーツールは Anthropic 側で実行され、開発者は `tool_result` を作らない（154〜160行・表169〜173行）
**検証結果**: Tool use 概要「Server tools … run on Anthropic's infrastructure」。

### 11. `web_search_20260209` / `web_fetch_20260209` が存在し、末尾の数字はバージョン（157〜158行）
**検証結果**: Web search（`web_search_20250305` / `_20260209` / `_20260318`）、Web fetch（`_20250910` / `_20260209` / `_20260309` / `_20260318`）。（より新しい版がある点は⚠️1）

### 12. サーバーツールの処理が長いと `pause_turn` になり、続きを促すリクエストが必要（161行）
**検証結果**: Server tools「The server-side loop and pause_turn」。

### 13. サーバーツールとクライアントツールは1リクエスト内で混在可能（182行）
**検証結果**: Server tools「Mixing server tools and client tools in one turn」。

### 14. Opus 5.5 は adaptive thinking が常時有効、既定で `thinking` は空文字（187〜190・545行）
**検証結果**: Errors「thinking is always on」（Opus 5.5）、Thinking「`display` defaults to `"omitted"`」。

### 15. thinking ブロックには `signature` があり、改変・削除すると400になり得る（193〜199行）
**検証結果**: Errors「Thinking blocks cannot be modified」（latest assistant message の thinking を edit/reorder/filter out すると 400）。

### 16. ツール定義の3項目 `name` / `description` / `input_schema`（222〜228行）
**検証結果**: Define tools のパラメータ表。

### 17. description は詳しく、少なくとも3〜4文（275〜276行）
**検証結果**: Define tools「Aim for at least 3–4 sentences for each tool description, more if the tool is complex.」

### 18. 通常の Tool Use ではスキーマ準拠は保証されず、`strict: true` で保証できる（270行の前半）
**検証結果**: Strict tool use「Without strict mode, Claude might return incompatible types … or omit required fields」。（後半の制約キーワードについては⚠️2）

### 19. `tool_use` ブロックの `id`（`toolu_` 始まり）・`name`・`input`（パース済みオブジェクト）（527〜531行）
**検証結果**: 公式例 `"id": "toolu_01A09q90qw90lq917835lq9"`。Streaming「the final `tool_use.input` is always an *object*」。

### 20. `tool_result` のフィールド（type / tool_use_id / content（文字列またはブロック配列）/ is_error）（616〜623・466行）
**検証結果**: Handle tool calls。

### 21. `tool_use_id` の誤り・存在しないIDは400（628・824行）
**検証結果**: Handle tool calls「tool_use ids were found without tool_result blocks immediately after」系の 400。

### 22. `tool_result` を `text` より前に置かないと400、すべての `tool_use` に `tool_result` が必要（637行）
**検証結果**: Handle tool calls「the `tool_result` blocks must come FIRST in the content array」、「this causes a 400 error」の例（text が tool_result より前）。

### 23. assistant の応答を履歴に戻し忘れる／`tool_result` を返さず次の質問を送ると400（816〜832行）
**検証結果**: Handle tool calls「Tool result blocks must immediately follow their corresponding tool use blocks」。

### 24. Messages API の role は user と assistant の2つで、ツール結果は user 側（593〜595行）
**検証結果**: 公式例でツール結果は `"role": "user"`。（system はトップレベルのパラメータ）

### 25. `content` の文字列は text ブロック配列の省略形（725行）
**検証結果**: 公式例で `"content": "..."` と配列形式の両方が使われている。

### 26. 複数の結果は1つの user メッセージにまとめる。分けると並列呼び出しが減る（747・996〜997・1185〜1188行）
**検証結果**: Parallel tool use「Wrong: a separate user message for each tool result … This "teaches" Claude to avoid parallel calls.」

### 27. `max_tokens` で止まると最後の `tool_use` の引数が不完全な可能性（1001行）
**検証結果**: Handling stop reasons「the truncated response contains an incomplete tool use block」。

### 28. Open-Meteo（非商用は無料・キー不要、ジオコーディング `/v1/search` と forecast `/v1/forecast`、`name`/`count`/`language`/`format`、`current`/`temperature_unit`/`timezone`、見つからないと `results` キー自体がない、WMO天気コード、`language=ja` で「東京都」、風速は km/h）（1057〜1166行、コード）
**検証結果**: 規約ページ「free access for non-commercial use」。2026-11-07 に実際にリクエストし、`{"results":[{"name":"東京都",...}]}`、存在しない地名では `{"generationtime_ms":...}` のみ、forecast の `current` に4変数と `weather_code: "wmo code"`、`wind_speed_10m: "km/h"`、`temperature_unit=fahrenheit` で `°F` を確認。

---

## ⚠️ 要確認（古い可能性あり）

### 1. サーバーツールの版（157行・170行）
**記述**: 「サーバーツールの代表例は、Web検索の `web_search_20260209` や、Webページ取得の `web_fetch_20260209` です。」
**懸念点**: 誤りではないが、さらに新しい `web_search_20260318` / `web_fetch_20260318`（response_inclusion 追加）と `web_fetch_20260309`（cache bypass）が公開されている。第6章で「最新版」と書いていた箇所は修正済み。
**推奨対処**: このままでよい。必要なら「（より新しい版もあります。第6章参照）」を添える。

### 2. 「確実に形を守らせたい場合は `strict: true`」と制約キーワードの関係（270行）
**記述**: 「JSON Schema には、ほかにも `minimum`（最小値）、`maxLength`（最大文字数）、`items`…など多くのキーワードがあります。ただし、スキーマに書いた制約をClaudeが必ず守る保証は、通常の Tool Use にはありません。確実に形を守らせたい場合は、第6章で扱う `strict: true` を使います。」
**懸念点**: 文脈上「`minimum` や `maxLength` も strict なら守られる」と読める。実際には strict ツール／構造化出力は `minimum`・`maximum`・`minLength`・`maxLength` 等をサポートせず、**指定すると400**になる（第6章1147行の記述とも食い違う印象を与える）。
**検索結果**: Structured outputs「JSON Schema limitations / Not supported: Numerical constraints (such as `minimum`, `maximum`, `multipleOf`)、String constraints (`minLength`, `maxLength`) … If you use an unsupported feature, you'll receive a 400 error」。「Both JSON outputs and strict tool use share these limitations.」
**推奨対処**: 例:「確実に型や必須キーを守らせたい場合は、第6章で扱う `strict: true` を使います（ただし `minimum` や `maxLength` のような数値・長さの制約は strict では使えません）。」

---

## ❌ 要修正（誤りの可能性が高い）

### 1. ツール名の長さ制限（232行）※修正済み
**記述**: 「名前に使える文字には制限があり、英数字・アンダースコア・ハイフンで64文字以内にします。」
**問題**: 公式の制約は 1〜128 文字。
**正しい情報**: Define tools「`name` … Must match the regex `^[a-zA-Z0-9_-]{1,128}$`.」
**修正内容**: 「英数字・アンダースコア・ハイフンで1〜128文字にします。」に修正（chapter_05.md 232行）。

---

## 総評

Tool use の往復、`tool_result` の形と配置ルール、並列ツール呼び出し、`tool_choice` の制約、thinking ブロックの扱いはいずれも公式ドキュメントと一致しています。Open-Meteo の利用条件・エンドポイント・パラメータ・レスポンス形状も実際の呼び出しで確認できました。誤りはツール名の長さ（64→128文字）の1件のみで、第6章の同じ記述・正規表現とあわせて修正しました。⚠️2 は第6章の構造化出力の説明と整合させるため、1文の補足を推奨します。

---

## 対応（2026-11-07）

- ⚠️2（strict と制約キーワード）: 270行のNOTEを「型や必須キーを確実に守らせたい場合は `strict: true`。なお strict では `minimum`・`maximum`・`minLength`・`maxLength`・`maxItems` などの数値・長さの制約は使えず400（`minItems` も0か1のみ）。範囲の確認は受け取る側の関数で必ず行う」に修正。第6章1147行の記述と整合。
- ⚠️1（サーバーツールの版）: 推奨対処どおり現状維持（第6章で新しい `_20260318` 版に言及済み）。
