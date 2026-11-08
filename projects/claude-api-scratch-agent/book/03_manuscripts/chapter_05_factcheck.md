# ファクトチェックレポート

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_05.md
検証日: 2026-11-08
検証クレーム数: 41件
  ✅ 検証済み: 38件
  ⚠️ 要確認: 3件
  ❌ 要修正: 0件

主な一次情報（2026-11-08 取得）:
- Tool use 概要: https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview.md
- Define tools: https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools.md
- Handle tool calls: https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls.md
- Parallel tool use / Strict tool use / Server tools / Web search tool: https://platform.claude.com/docs/en/agents-and-tools/tool-use/
- Handling stop reasons: https://platform.claude.com/docs/en/build-with-claude/handling-stop-reasons.md
- Structured outputs（JSON Schema の制約）: https://platform.claude.com/docs/en/build-with-claude/structured-outputs.md
- Thinking / Errors: https://platform.claude.com/docs/en/build-with-claude/thinking.md ・ https://platform.claude.com/docs/en/api/errors.md
- Open-Meteo: https://open-meteo.com/en/docs ・ https://open-meteo.com/en/docs/geocoding-api ・ https://open-meteo.com/en/terms（指示どおり API への実通信はしていない。ドキュメントのみ確認）

## 前回（2026-11-07）の指摘の反映状況

| 前回の指摘 | 状態 |
|---|---|
| ❌1 ツール名の長さ（64→128文字） | ✅ 反映済み（232行「1〜128文字」） |
| ⚠️2 strict と `minimum`・`maxLength` などの制約 | ✅ 反映済み（270行の NOTE。`maxItems`・`minItems` も公式と一致） |
| ⚠️1 サーバーツールの版（`_20260318` がある） | 現状維持（下の⚠️3。第6章で言及済みなので問題なし） |
| コード検証側の出力例・pycon・httpx ログ・`東京都` | ✅ すべて反映済み（chapter_05_code_verify.md 参照） |

---

## ✅ 検証済み（正確）

### 1. Claude はクライアントツールを実行せず、開発者のコードが実行する（40行）
**検証結果**: Tool use 概要「Your code runs the operation and sends back a `tool_result`.」

### 2. 5段階の流れ。ツール使用時は `stop_reason: "tool_use"`、結果を返したあとは `end_turn`（62〜66行）
**検証結果**: Tool use 概要の client tool の往復例と一致。

### 3. Messages API はステートレスで、2回目のリクエストに質問・依頼・結果をすべて含める（73〜74行）
**検証結果**: 公式の往復例が `messages += [assistant(response.content), user(tool_result)]` の形で再送している。

### 4. 1つの応答に複数の `tool_use` が入ることがある（79行）
**検証結果**: Parallel tool use「By default, Claude may call multiple tools in a single response.」

### 5. `tool_use` の前に `text` ブロックが付くことがある（93行）
**検証結果**: Define tools「Model responses with tools」の例が `text` → `tool_use` の順。

### 6. `stop_reason` の表（end_turn / tool_use / max_tokens / refusal＋`stop_details` / pause_turn）（104〜110行）
**検証結果**: Handling stop reasons。refusal のとき `stop_details` が policy category を示し、ほかの停止理由では null。

### 7. ツール定義は入力トークンとして課金され、ツール用の system プロンプトで数百トークン上乗せされる（128〜131行）
**検証結果**: Tool use 概要「Pricing」。Opus 5.5・Sonnet 5.5・Haiku 5.5 は auto/none で 286 tokens。

### 8. `tool_choice` の既定は auto で、`none` ならツールを使わない（137〜138行）
**検証結果**: Define tools「`auto` … This is the default value when `tools` are provided」「`none` prevents Claude from using any tools」。

### 9. `any`／`tool` による強制は Opus 5.5・Sonnet 5.5 で 400（141〜147行）
**検証結果**: Errors「Forced tool use not supported」: Opus 5.5・Sonnet 5.5・Fable 5.1・Mythos 5.1 で 400 `invalid_request_error`。

### 10. Tool Use は他社 API では Function Calling と呼ばれる（33行）
**検証結果**: Tool use 概要「Tool use (also called function calling)」。

### 11. サーバーツールは Anthropic 側で実行され、開発者は `tool_result` を作らない（154〜160行・表169〜171行）
**検証結果**: Server tools「Unlike client `tool_use` blocks, you don't need to respond with a `tool_result`.」

### 12. `web_search_20260209`／`web_fetch_20260209` が存在し、末尾の数字はバージョン（157〜158行）
**検証結果**: Web search（`_20250305`／`_20260209`／`_20260318`）、Server tools「The `_20260209` versions of the web tools」。

### 13. サーバーツールの処理が長いと `pause_turn` になり、続きを要求する必要がある（161行）
**検証結果**: Handling stop reasons「A server-tool loop reached its iteration limit」（既定はリクエストごとに10回）。

### 14. サーバーツールとクライアントツールは1つのリクエストで混ぜて使える（182行）
**検証結果**: Server tools「Mixing server tools and client tools in one turn」。

### 15. Opus 5.5 では adaptive thinking が常に有効で、既定では `thinking` フィールドが空文字（187〜190・545行）
**検証結果**: Thinking の表（Opus 5.5 で `"disabled"` は 400）。「`display` defaults to `"omitted"`」「the response contains `thinking` blocks with an empty `thinking` field」。

### 16. thinking ブロックには `signature` があり、削除・改変すると 400 になり得る（193〜199行）
**検証結果**: Errors「Thinking blocks cannot be modified」（edited・reordered・filtered out は 400）。

### 17. ツール名は英数字・アンダースコア・ハイフンの1〜128文字（232行）
**検証結果**: Define tools「Must match the regex `^[a-zA-Z0-9_-]{1,128}$`.」

### 18. ツール定義の3項目 `name`／`description`／`input_schema`（222〜228行）
**検証結果**: Define tools のパラメータ表。

### 19. description は詳しく、少なくとも3〜4文（275〜276行）
**検証結果**: Define tools「Aim for at least 3–4 sentences for each tool description」。

### 20. 通常の Tool Use はスキーマ準拠を保証しない。strict では `minimum`・`maximum`・`minLength`・`maxLength`・`maxItems` が使えず 400、`minItems` は0か1のみ（270行）
**検証結果**: Strict tool use「Without strict mode, Claude might return incompatible types … or omit required fields」。Structured outputs「Not supported: Numerical constraints (`minimum`, `maximum`, `multipleOf`)、String constraints (`minLength`, `maxLength`)、Array constraints beyond `minItems` of 0 or 1 … you'll receive a 400 error」。

### 21. `tool_use` ブロックの `id`（`toolu_` で始まる）・`name`・`input`（パース済みのオブジェクト）（527〜531行）
**検証結果**: Handle tool calls の例 `"id": "toolu_01A09q90qw90lq917835lq9"`。`input` は「An object containing the input」。

### 22. `tool_result` の `type`／`tool_use_id`／`content`（任意）／`is_error`（任意）（616〜623行）
**検証結果**: Handle tool calls。`content` は optional。（`content` に入れられる型の範囲は⚠️1）

### 23. `tool_use_id` を間違えると 400（628・822〜824行）
**検証結果**: Server tools／Handle tool calls のエラー例「`tool_use` ids were found without `tool_result` blocks immediately after」。対応のない ID も検証エラーになる。

### 24. `tool_result` は配列の先頭に置き、`text` は後ろ。前に置くと 400。すべての `tool_use` に `tool_result` が必要（637行）
**検証結果**: Handle tool calls「the `tool_result` blocks must come FIRST」「this causes a 400 error」の例。

### 25. assistant の応答を履歴に戻し忘れると 400（816〜820・830行）
**検証結果**: Handle tool calls「Tool result blocks must immediately follow their corresponding tool use blocks」。

### 26. role は user と assistant の2つで、ツール結果は user 側から送る（593〜595行）
**検証結果**: Handle tool calls「Unlike APIs that … use special roles like `tool` or `function`, the Claude API integrates tools directly into the `user` and `assistant` message structure.」

### 27. `content` の文字列は text ブロック配列の省略形（725行）
**検証結果**: 公式例で文字列と配列の両方の形を使っている。

### 28. 複数の結果は1つの user メッセージにまとめる。分けると並列呼び出しが減る（747・996〜997・1185〜1188行）
**検証結果**: Parallel tool use「Wrong: a separate user message for each tool result … This "teaches" Claude to avoid parallel calls.」

### 29. `max_tokens` で止まると、最後の `tool_use` の引数が不完全な場合がある（1001行）
**検証結果**: Handling stop reasons「the truncated response contains an incomplete tool use block」。

### 30. refusal では `stop_details` に理由の分類が入る（1002行）
**検証結果**: Handling stop reasons（stop_details は policy category を示す）。

### 31. Open-Meteo は非商用なら無料で、登録・キー不要（1057〜1059行）
**検証結果**: 規約「You may only use the free API services for non-commercial purposes」。Docs「apikey … Only required to commercial use」。（帰属表示と呼び出し上限は⚠️2）

### 32. ジオコーディング `https://geocoding-api.open-meteo.com/v1/search` と予報 `https://api.open-meteo.com/v1/forecast`、パラメータ `name`／`count`／`language`／`format`（1064〜1065行・1097行）
**検証結果**: Geocoding API ドキュメント（count の既定は10、format の既定は json、language で地名を翻訳）。

### 33. `current` に4変数、`temperature_unit` で celsius／fahrenheit、`timezone=auto`、風速は km/h（1113〜1128・1146行）
**検証結果**: Forecast ドキュメント「Every weather variable available in hourly data, is available as current condition」「If fahrenheit is set, all temperature values are converted」、wind speed の既定は kmh、「auto resolves the time zone from the coordinates」。

### 34. 天気の概況は WMO 天気コードで返る。0/1/2/3/45/48/51/53/55/61/63/65/71/73/75/80/81/82/95 の対応（1087〜1092・1147行）
**検証結果**: Forecast ドキュメントの WMO コード表。表にない 56・57・66・67・77・85・86・96・99 は `コードNN` で表示されるフォールバックがあり、問題なし。

### 35. `language=ja` で都市名がジオコーディング結果の表記（例: `東京都`）で返る（1156・1166行）
**検証結果**: Geocoding「name: Localized following the &language= parameter, if possible」。`東京都` は 2026-11-07 の実測値。

### 36. 見つからないときは `results` キー自体がない（1100行）
**検証結果**: ドキュメントには明記がない。2026-11-07 の実測（`{"generationtime_ms": ...}` のみ）と一致する。コードは `.get("results")` と `if not results` で、キーがない場合も空配列の場合も扱えるので安全。

### 37. 出力例のコスト・合計（780・1015〜1022・1040〜1048・1157〜1163行）
**検証結果**: Opus 5.5 の単価 $4／$20（1M tok）で全件を再計算し、一致した（例: in=718 out=132 → $0.0055、合計 1,723／256 → $0.0120）。偽 API で実行した `tracker.summary()` も同じ値を出した。

### 38. 換算・差の計算（486・1020・1162行）
**検証結果**: 2.3°C → 36.14°F → 36.1°F、18.5−2.3＝16.2、71.8−48.6＝23.2。

---

## ⚠️ 要確認（古い可能性あり）

### 1. `tool_result` の `content` に入れられるブロックの種類（466行・622行）
**記述**: 「`content` には、テキストや画像のブロックの配列を入れることもできます。」／表「文字列、またはテキスト・画像ブロックの配列」
**懸念点**: 誤りではないが不完全。
**検索結果**: Handle tool calls「These content blocks can use the `text`, `image`, `document`, or `search_result` types.」
**推奨対処**: 622行の表を「文字列、またはテキスト・画像・ドキュメントなどのブロックの配列」にする（466行も同様に「テキストや画像などのブロック」）。

### 2. Open-Meteo の利用条件（帰属表示と呼び出し上限）（1058〜1059行）
**記述**: 「Open-Meteo は非商用であれば無料で使える…商用で使う場合や大量に呼び出す場合は、公式サイトの利用条件を確認してください。」
**懸念点**: 無料枠の条件に CC BY 4.0（帰属表示）と呼び出し上限があるが、本文で触れていない。読者が作品を公開する場合に関係する。
**検索結果**: 規約「You accept to the CC-BY 4.0 licence」「Less than 10'000 API calls per day, 5'000 per hour and 600 per minute」。
**推奨対処**: 1059行の後に次の1文を追加する。「無料枠には1日1万回などの呼び出し上限があり、データは CC BY 4.0 で提供されます。取得した天気を公開する場合は、出典として Open-Meteo を表示しましょう。」

### 3. サーバーツールの版（157行・170行）
**記述**: 「サーバーツールの代表例は、Web検索の `web_search_20260209` や、Webページ取得の `web_fetch_20260209` です。」
**懸念点**: 誤りではない。より新しい `web_search_20260318` などもある（前回と同じ指摘）。
**推奨対処**: 第6章174行で新しい版に触れているので、現状のままでよい。

---

## ❌ 要修正（誤りの可能性が高い）

なし。

---

## 総評

前回の❌（ツール名128文字）と⚠️（strict と数値・長さの制約）はどちらも正しく反映されています。Tool Use の往復、`tool_result` の形と配置、並列呼び出し、`tool_choice` の制約、thinking ブロックの扱い、`stop_reason` の各値は、いずれも 2026-11-08 時点の公式ドキュメントと一致しました。出力例のコストもすべて単価表どおりです。残りは補足レベルで、`tool_result` の content の種類と、Open-Meteo の帰属表示・上限への言及の2点を推奨します。

---

## 再チェック（2026-11-08・修正箇所）

対象: `git diff` の変更 3か所。一次情報: agents-and-tools/tool-use/handle-tool-calls.md、open-meteo.com/en/terms、open-meteo.com/en/licence。

- ✅ L466 NOTE「`content` には、テキストや画像などのブロックの配列を入れることもできます」
  handle-tool-calls.md「These content blocks can use the `text`, `image`, `document`, or `search_result` types」と一致（「など」で document 等を含められている）。
- ✅ L622 表「文字列、またはテキスト・画像・ドキュメントなどのブロックの配列」
  同上。NOTE の書き方とも整合。表の記法も周囲の行と揃っている。
- ✅ L1060-1061「無料枠には1日1万回などの呼び出し上限があり、データは CC BY 4.0 で提供されます」「出典として Open-Meteo を表示しましょう」
  Terms「Less than 10'000 API calls per day, 5'000 per hour and 600 per minute」「You accept to the CC-BY 4.0 licence」、Licence「You must include a link next to any location Open-Meteo data are displayed」と一致。直前の「非商用であれば無料」とも矛盾なし。1行1文・50字以内で周囲と揃っている。
