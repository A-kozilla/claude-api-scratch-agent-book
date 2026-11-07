# ファクトチェックレポート

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_06.md
検証日: 2026-11-07
検証クレーム数: 39件
  ✅ 検証済み: 31件
  ⚠️ 要確認: 6件
  ❌ 要修正: 2件（原稿修正済み）

主な一次情報（2026-11-07 取得）:
- Web search tool: https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool.md
- Web fetch tool: https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-fetch-tool.md
- Server tools（pause_turn・混在・ZDR と allowed_callers）: https://platform.claude.com/docs/en/agents-and-tools/tool-use/server-tools.md
- Define tools / Handle tool calls / Parallel tool use / Strict tool use: https://platform.claude.com/docs/en/agents-and-tools/tool-use/
- Structured outputs: https://platform.claude.com/docs/en/build-with-claude/structured-outputs.md
- Pricing / Errors: https://platform.claude.com/docs/en/about-claude/pricing.md ・ api/errors.md

---

## ✅ 検証済み（正確）

### 1. Claude がツールについて見えるのは `name`・`description`・`input_schema`（34行）
**検証結果**: Define tools のツール定義パラメータ。

### 2. description は詳しく、目安は3〜4文以上（62行）
**検証結果**: Define tools「Aim for at least 3–4 sentences for each tool description」。

### 3. サーバーツールは Anthropic のインフラで実行、代表は `web_search` と `web_fetch`（168行）
**検証結果**: Tool use 概要「Server tools (such as `web_search`, `web_fetch`, `code_execution`, and `tool_search`) run on Anthropic's infrastructure」。

### 4. 応答に `server_tool_use` と結果ブロック（Web検索は `web_search_tool_result`）が入り、`tool_result` は不要（170行）
**検証結果**: Web search「Response」の例。

### 5. `tools` に `type` と `name` を書き、`input_schema` は書かない。名前は `web_search`（174・183〜188行）
**検証結果**: Web search「Tool definition」。

### 6. `text` ブロックが引用（citations）単位で分かれる（233行）
**検証結果**: Web search の応答例で `text` が citations ごとに分割されている。

### 7. `usage.server_tool_use.web_search_requests` に検索回数（230・233行）
**検証結果**: Web search「Usage and pricing」の `usage` 例。

### 8. 検索結果は入力トークンとして課金され、検索回数の従量料金が別にかかる（235行）
**検証結果**: Pricing / Web search「$10 USD per 1,000 searches, plus standard token costs … Web search results … are counted as input tokens」。失敗した検索は課金されない。

### 9. `pause_turn` はサーバー側ループが長くなって一時停止したことを示す（239行）
**検証結果**: Server tools「On a long-running turn, the API might pause that loop and return a `pause_turn` stop reason.」

### 10. `pause_turn` の再開は、返ってきた assistant の `content` をそのまま追加し、同じ `tools` で再送。ツールを外すとエラー（241行・コード205〜208行・583〜585行）
**検証結果**: Server tools「Pass the paused response back as-is in a subsequent request」「Include the same tools in the continuation request … the API returns a validation error if that tool is missing」。公式 Python 例も `messages = [user, {"role": "assistant", "content": response.content}]` を再送している。

### 11. 最後が assistant で終わる再送は prefill ではなく正規の再開手順（243行）
**検証結果**: Server tools の公式例が assistant で終わる messages を送っており、「you continue it by re-sending the assistant content as-is」と明記。prefill 禁止（Errors「Prefill not supported」）とは区別される。

### 12. 続きがさらに `pause_turn` になることがあり、再開回数に上限を設ける（243行・コード191行）
**検証結果**: Server tools「A continued turn can pause again … capping the number of continuations as you would any retry loop. Keep every paused response in `messages`, in order.」

### 13. サーバーツールとクライアントツールが同時に呼ばれると、API はサーバーツールを実行せず `stop_reason: "tool_use"` で返し、`tool_result` だけの user メッセージを返すと次のリクエストでサーバーツールを実行（245行）
**検証結果**: Server tools「Mixing server tools and client tools in one turn」、Handle tool calls「the user message must contain only `tool_result` blocks」。

### 14. `_20260209` 版は内部でコード実行を使うため、ZDR では `"allowed_callers": ["direct"]` が必要（247行）
**検証結果**: Server tools「ZDR and allowed_callers」: `_20260209` 以降は既定で ZDR 対象外、`"allowed_callers": ["direct"]` で動的フィルタリングを無効化すると ZDR で使える。

### 15. Web検索は引用が自動で付く（259行）
**検証結果**: Web search「Citations are always enabled for web search」。（Web fetch は既定で無効。⚠️4 参照）

### 16. 社内データには届かない／公開Web向け（257・263行）
**検証結果**: Web fetch は会話中に現れた URL のみ取得可能、Web search は公開Web検索。社内ネットワークへの到達手段はない。

### 17. ツール名の制約に合わない名前は API が400で拒否（426行）
**検証結果**: Define tools の regex 制約（長さは❌1で修正）。

### 18. 並列ツール呼び出しは既定で有効（666行）
**検証結果**: Parallel tool use（`disable_parallel_tool_use: true` で無効化）。

### 19. すべての `tool_use` に `tool_result` が必要、欠けると400（670行）
**検証結果**: Handle tool calls。

### 20. 結果ごとに user メッセージを分けると以降の並列呼び出しが減る（670行）
**検証結果**: Parallel tool use「This "teaches" Claude to avoid parallel calls.」

### 21. user メッセージ内で `tool_result` を先頭に、テキストは後ろ。前に置くと400（672行）
**検証結果**: Handle tool calls「the `tool_result` blocks must come FIRST」と 400 の例。

### 22. API は `tool_use_id` で対応を取るので、順番が違っても動く（734行）
**検証結果**: Handle tool calls（`tool_use_id` で対応付け）。

### 23. 承認拒否で例外にすると `tool_result` が欠けて次のリクエストが400、拒否は `is_error: true` で返す（931行）
**検証結果**: Handle tool calls（tool_result 欠落は 400、`is_error` の用途）。

### 24. 現行モデルでは assistant の prefill は400（1053行）
**検証結果**: Errors「Prefill not supported」（Claude 4.6 以降）。

### 25. 構造化出力は `output_config.format`（`type: "json_schema"`）に書き、制約付きデコーディングで生成（1059行・コード1105行）
**検証結果**: Structured outputs「How it works」「Send it in output_config.format with `type: "json_schema"`」。

### 26. オブジェクトには `"additionalProperties": false` が必須、`anyOf` で null を許せる（1147行）
**検証結果**: Structured outputs「`required` and `additionalProperties` (must be set to `false` for objects)」「`anyOf` and `allOf` (with limitations)」、型 `null` をサポート。

### 27. `minLength`・`maxLength`・`minimum`・`maximum` は使えず400（1147行）
**検証結果**: Structured outputs「Not supported: Numerical constraints … String constraints … If you use an unsupported feature, you'll receive a 400 error」。

### 28. 初回は文法作成で遅く、文法は一定期間キャッシュされる（1149行）
**検証結果**: Structured outputs「First request latency」「Compiled grammars are cached for 24 hours from last use」。

### 29. `"strict": true` でツール引数にも同じ文法制約がかかる（1153行）
**検証結果**: Structured outputs「Strict tool use … uses the same grammar pipeline」、Strict tool use。

### 30. strict ツールは1リクエスト20個まで（1201行）
**検証結果**: Structured outputs「Explicit limits: Strict tools per request 20」。

### 31. `any` / `tool` の強制は Opus 5.5・Sonnet 5.5 で400（1193行）
**検証結果**: Errors「Forced tool use not supported」。

---

## ⚠️ 要確認（古い可能性あり）

### 1. Web検索デモの出力例と `pause_turn` 再開時のコンテナ（178〜232行 `server_tools_demo.py`）
**記述**: `"type": "web_search_20260209"`（`allowed_callers` 指定なし）で、出力例は `blocks: ['thinking', 'server_tool_use', 'web_search_tool_result', 'text', 'text', 'text']`。再開時は messages の追加のみ。
**懸念点**: `web_search_20260209` 以降は `allowed_callers` の既定が `["code_execution_20260120"]`（動的フィルタリング）。この設定では Claude は検索をコード実行の中から呼ぶため、応答にはコード実行の `server_tool_use` と結果ブロックが加わり、入れ子の検索ブロックには `caller` が付く。出力例の「直接検索」の並びとは一致しない可能性が高い。また、コード実行を伴う場合、公式は `pause_turn` の再開で `container` の ID を送り返すよう求めている（第10章の `research_web()` は対応済み、第6章デモは未対応）。
**検索結果**: Web search「Dynamic filtering … the tool's `allowed_callers` field defaults to `["code_execution_20260120"]` … To call web search directly, without dynamic filtering, set `allowed_callers: ["direct"]`」。Server tools「Keep the container: If the response includes a `container` … send its ID back in the continuation request.」
**推奨対処**（いずれか）:
- (a) デモを単純な直接検索にする: `SERVER_TOOLS` に `"allowed_callers": ["direct"],  # 動的フィルタリングを使わず直接検索する` を追加（出力例・本文はそのまま整合、ZDR の NOTE とも整合）。
- (b) 動的フィルタリングのまま使うなら、出力例をコード実行ブロックを含む形に差し替え、`pause_turn` 時に第10章と同様 `response.get("container")` の ID を `extra={"container": ...}` で渡す。
本書の流れ（第6章は概要、第10章で本格利用）からは (a) が最小差分。

### 2. 構造化出力で「たまに崩れる」ことが「原理的に起きません」（1059・1145行）
**記述**: 「そのため、「たまに崩れる」ことが原理的に起きません。」
**懸念点**: 公式は「in most cases」とし、例外として `stop_reason: "refusal"`（スキーマ不一致の可能性）、`"max_tokens"`（途中で切れる）、文字列 `enum` の大文字・小文字の揺れを挙げている。
**検索結果**: Structured outputs「Invalid outputs」。
**推奨対処**: 「ただし、`stop_reason` が `refusal` や `max_tokens` の場合は形式が崩れ得るので、`json.loads()` の前に `stop_reason` が `end_turn` であることを確認します」を1文追加（`structured_output.py` でも判定するとなお良い）。

### 3. strict ツールの条件「`additionalProperties: false` と `required` が必要」（1153行）
**記述**: 「条件は構造化出力と同じで、`additionalProperties: false` と `required` が必要です。」
**懸念点**: `additionalProperties: false` は必須だが、`required` に全プロパティを入れることは必須ではない（任意パラメータは許可され、strict スキーマ全体で24個までという上限がある）。
**検索結果**: Structured outputs「Explicit limits: Optional parameters 24 — Each parameter not listed in `required` counts toward this limit.」
**推奨対処**: 「`additionalProperties: false` が必須で、任意の引数は数に上限があるため、なるべく `required` に入れて `null` 許可で表します」などに調整。`references/claude-api-facts.md` 63行の「`required` 必須」も同様に修正推奨。

### 4. サーバーツールと自作ツールの比較表（255〜261行）
**記述**: 「結果の加工 | できない（そのまま入る）」「引用（citations） | 自動で付く」
**懸念点**: `_20260209` 以降は Claude がコードで結果を絞り込む（動的フィルタリング）ため、「加工できない」は開発者側から見ての話。また Web fetch の引用は既定で無効（`"citations": {"enabled": true}` が必要）。
**推奨対処**: 「（開発者は）結果を加工できない」「Web検索は自動で付く（Web取得は設定で有効化）」のように主語・対象を明確に。

### 5. `max_uses` の説明「1リクエスト内の検索回数の上限」（187行コメント）
**懸念点**: 公式は「limits the number of searches in a single turn」で、`pause_turn` からの再開を含むターン全体で数える（動的フィルタリング経由の検索を除く）。
また、既定の動的フィルタリング（コード実行経由）の検索は、`pause_turn` からの再開をまたいでは数えられない（Web search「Searches from earlier requests in that turn count against the limit, unless Claude ran them from code execution through dynamic filtering」）。つまり既定設定のデモでは、再開のたびに最大3回ずつ検索され得る（料金は $10 / 1,000回）。
**推奨対処**: コメントを「1ターン内の検索回数の上限（コスト対策）」に変更。⚠️1 の (a) `allowed_callers: ["direct"]` を採用すれば、再開をまたいだ合計にも上限が効く。

### 6. 構造化出力・strict ツールのデモが Haiku 5.5 で `max_tokens=2000`（1103〜1104行・1181行）
**記述**: `model=FAST_MODEL`（`claude-haiku-5-5`）、`max_tokens=2000`
**懸念点**: Haiku 5.5 は `thinking` を省略すると adaptive thinking で動き、思考トークンも `max_tokens` に数えられる（Thinking「they count toward `max_tokens` alongside the response text」）。思考が長引くと `stop_reason: "max_tokens"` で JSON が途中で切れ、`json.loads()` が失敗し得る（⚠️2 と同根）。
**推奨対処**: `stop_reason` の確認を入れたうえで、`max_tokens` に余裕を持たせる（例: 8000）か、定型抽出では `output_config` に `"effort": "low"` を併用する／Haiku 5.5 では `thinking: {"type": "disabled"}` も受け付けられる（Errors「Claude Haiku 5.5 accepts `thinking: {"type": "disabled"}`」）ことを NOTE で補足。

---

## ❌ 要修正（誤りの可能性が高い）

### 1. ツール名の長さ制限（42行・328〜329行・369行）※修正済み
**記述**: 「英数字とアンダースコア・ハイフンの組み合わせで、64文字以内であれば受け付けられます。」／`NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")`
**問題**: 公式の制約は 1〜128 文字。64文字超の正当な名前をレジストリが誤って拒否する。
**正しい情報**: Define tools「Must match the regex `^[a-zA-Z0-9_-]{1,128}$`.」
**修正内容**: 本文を「1〜128文字であれば受け付けられます」、コメントを「1〜128文字」、正規表現を `{1,128}`、`ValueError` のメッセージを「1〜128文字にしてください」に修正。

### 2. 「本書執筆時点の最新版は `web_search_20260209` と `web_fetch_20260209`」（174行）※修正済み
**問題**: 執筆時点（2026-11）では `web_search_20260318`・`web_fetch_20260318`（および `web_fetch_20260309`）が公開されており、`_20260209` は最新版ではない。
**正しい情報**: Web search「Three versions … `web_search_20250305` / `web_search_20260209`（dynamic filtering）/ `web_search_20260318`（response inclusion）」。Web fetch「The latest web fetch tool version (`web_fetch_20260318`)…」。
**修正内容**: 「本書では、結果の絞り込み機能（動的フィルタリング。後述のNOTEを参照）に対応した `web_search_20260209` と `web_fetch_20260209` を使います。執筆時点ではさらに新しい `_20260318` 版も公開されており、機能が追加されています。」に修正（コードは `_20260209` のまま。第10章とも整合）。

---

## 総評

`pause_turn` の再開方法（assistant の content をそのまま追加し、同じ tools で再送する／最後が assistant になる再送は正規手順）、サーバーツールとクライアントツールの混在時の挙動、ZDR の `allowed_callers`、`usage.server_tool_use.web_search_requests`、構造化出力・strict ツールの制約はいずれも公式と一致しています。誤りはツール名の長さ（コード含む）と「最新版」表記の2件で、修正済みです。

最も注意すべきは⚠️1です。`web_search_20260209` の既定は動的フィルタリング（コード実行経由）なので、デモの出力例が実際と食い違う可能性が高く、`pause_turn` 再開時の `container` 引き継ぎも第10章と揃っていません。`"allowed_callers": ["direct"]` を1行足すのが最小の修正です。

---

## 対応（2026-11-07）

- ⚠️1（動的フィルタリングと `pause_turn` 再開）: 推奨対処 (a) を採用。`server_tools_demo.py` の `SERVER_TOOLS` に `"allowed_callers": ["direct"]` を追加し、出力例（直接検索のブロック並び）と整合させた。再開処理は第10章 `research_web()` と同じ方式に変更（`pause_turn` 以外なら終了／assistant content をそのまま追加／同じ tools／レスポンスに `container` があれば `extra={"container": id}` で送り返す／`MAX_CONTINUATIONS` 超過で打ち切りメッセージ）。本文の pause_turn 節に container の送り返しを1文追記し、NOTE に「既定は動的フィルタリングでコード実行のブロックが加わる。デモは仕組みを単純に観察するため直接検索にしている」を追記。
- ⚠️2（「原理的に起きない」）: 「拒否（`refusal`）や `max_tokens` による打ち切りを除けば」と限定。出力例の後に、`json.loads()` 前に停止理由を確認している理由を1文追記（コードの `refusal`／`max_tokens` 判定は既存）。
- ⚠️3（strict と `required`）: 「`additionalProperties: false` が必須。`required` に入れない任意の引数はスキーマ全体で24個までなので、なるべく `required` に入れ、値がないことは `null` で表す」に修正。
- ⚠️4（比較表）: 「開発者はできない（そのまま入る）」「Web検索は自動で付く（Web取得は設定で有効化）」に修正。
- ⚠️5（`max_uses`）: コメントを「1ターン内の検索回数の上限（再開をまたいで数える。コスト対策）」に変更（`allowed_callers: ["direct"]` により再開をまたいだ合計に上限が効く）。
- ⚠️6（Haiku 5.5 と `max_tokens=2000`）: `extract_inquiry()` の `output_config` に `"effort": "low"`（7.5節参照）を追加し、`max_tokens` に思考トークンも数える旨のコメントを付けた。`demo_strict_tool()` にも `output_config={"effort": "low"}` を追加。本文に「Haiku 5.5 は思考が既定で有効で、思考のトークンも `max_tokens` に数えられるため effort を low にしている」を追記。
