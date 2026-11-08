# ファクトチェックレポート

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_06.md
検証日: 2026-11-08
検証クレーム数: 46件
  ✅ 検証済み: 43件
  ⚠️ 要確認: 3件
  ❌ 要修正: 0件

主な一次情報（2026-11-08 取得）:
- Define tools（ベストプラクティス・tool_choice）: https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools.md
- Server tools（pause_turn・container・混在・ZDR／allowed_callers）: https://platform.claude.com/docs/en/agents-and-tools/tool-use/server-tools.md
- Web search tool: https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool.md
- Handle tool calls / Parallel tool use / Strict tool use: https://platform.claude.com/docs/en/agents-and-tools/tool-use/
- Structured outputs: https://platform.claude.com/docs/en/build-with-claude/structured-outputs.md
- Thinking / Effort / Errors: build-with-claude/thinking.md ・ build-with-claude/effort.md ・ api/errors.md
- Prompting best practices: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices.md
- Python: docs.python.org（whatsnew 3.13、concurrent.futures、pathlib）

## 前回（2026-11-07）の指摘の反映状況

| 前回の指摘 | 状態 |
|---|---|
| ❌1 ツール名の長さ（本文・正規表現・メッセージ） | ✅ 42・332〜333・373行すべて `1〜128` |
| ❌2 「最新版は `_20260209`」 | ✅ 174行で修正済み |
| ⚠️1 動的フィルタリングと `pause_turn` の container | ✅ `allowed_callers: ["direct"]`（188行）、container の引き継ぎ（210〜211行）、再開回数の上限、NOTE（251行） |
| ⚠️2 「原理的に起きない」 | ✅ 1063行で refusal／max_tokens を除くと限定し、1154行に補足あり |
| ⚠️3 strict と `required` | ✅ 1162行（任意の引数はスキーマ全体で24個まで） |
| ⚠️4 比較表 | ✅ 262〜263行 |
| ⚠️5 `max_uses` | ✅ 187行のコメント |
| ⚠️6 Haiku 5.5 と `max_tokens=2000` | ✅ `"effort": "low"` を追加し、1154行で説明 |

---

## ✅ 検証済み（正確）

### 1. Claude がツールについて見えるのは `name`・`description`・`input_schema`（34行）
**検証結果**: Define tools のツール定義パラメータ。

### 2. ツール名は英数字・`_`・`-` の1〜128文字。合わない名前は 400（42・333・430行）
**検証結果**: Define tools「Must match the regex `^[a-zA-Z0-9_-]{1,128}$`.」

### 3. description は詳しく、目安は3〜4文以上（62行）
**検証結果**: Define tools「Aim for at least 3–4 sentences」「by far the most important factor」。

### 4. サービスを表す接頭辞で名前空間を分ける（46行）
**検証結果**: Define tools「Use meaningful namespacing in tool names … prefix names with the service (for example, `github_list_prs`)」。

### 5. 関連する操作を `action` 引数で1つのツールにまとめる（PR の作成・レビュー・マージの例）（136行）
**検証結果**: Define tools「Rather than creating a separate tool for every action (`create_pr`, `review_pr`, `merge_pr`), group them into a single tool with an `action` parameter.」

### 6. 戻り値は意味の分かる値で、必要十分にする（142〜144行）
**検証結果**: Define tools「Return semantic, stable identifiers … include only the fields Claude needs … Bloated responses waste context」。

### 7. 強すぎる指示は過剰な呼び出しを招くので「〜のときに使ってください」程度でよい（118行）
**検証結果**: Prompting best practices「these models might now overtrigger. The fix is to soften any aggressive language … "CRITICAL: You MUST use this tool when..." → "Use this tool when..."」。

### 8. サーバーツールは Anthropic のインフラで実行され、代表は `web_search`・`web_fetch`（168行）
**検証結果**: Tool use 概要「Server tools (such as `web_search`, `web_fetch`, …) run on Anthropic's infrastructure」。

### 9. 応答に `server_tool_use` と結果ブロック（`web_search_tool_result`）が入り、`tool_result` は不要（170行）
**検証結果**: Server tools「The server_tool_use block」と Web search の Response の例。

### 10. `tools` には `type` と `name` を書き、`input_schema` は書かない。名前は `web_search`（174・183〜186行）
**検証結果**: Web search の Tool definition。

### 11. `_20260209` は動的フィルタリング対応で、より新しい `_20260318` もある（174行）
**検証結果**: Web search「Three versions … `web_search_20260209`: adds dynamic filtering / `web_search_20260318`: adds response inclusion」。

### 12. `max_uses` は1ターン内の上限で、再開をまたいで数える（187行）
**検証結果**: Web search「limits the number of searches in a single turn … Searches from earlier requests in that turn count against the limit, unless Claude ran them from code execution」。デモは `direct` なので、再開をまたいで数えられる。

### 13. `allowed_callers: ["direct"]` で動的フィルタリングを使わず直接検索する。既定ではコード実行のブロックが加わる（188・251行）
**検証結果**: Web search「`allowed_callers` field defaults to `["code_execution_20260120"]` … To call web search directly, without dynamic filtering, set `allowed_callers: ["direct"]`」。

### 14. `text` ブロックが引用（citations）の単位で分かれる（237行）
**検証結果**: Web search の Response の例。

### 15. `usage.server_tool_use.web_search_requests` に検索の回数が入る（234・237行）
**検証結果**: Web search「Usage and pricing」の usage の例。

### 16. 検索結果は入力トークンとして課金され、検索回数の従量料金が別にかかる（239行）
**検証結果**: Web search「$10 USD per 1,000 searches, plus standard token costs … results … are counted as input tokens」。

### 17. `pause_turn` はサーバー側ループの一時停止（243行）
**検証結果**: Server tools「On a long-running turn, the API might pause that loop and return a `pause_turn` stop reason.」

### 18. 再開時は assistant の content をそのまま追加し、同じ tools で送る。`container` があれば ID を送り返す（245行・コード207〜211行）
**検証結果**: Server tools「Pass the paused response back as-is」「Include the same tools」「Keep the container: … send its ID back in the continuation request」。

### 19. tools からサーバーツールを外すと、未実行の `server_tool_use` が宙に浮いてエラーになる（245行）
**検証結果**: Server tools「A paused turn can end with a `server_tool_use` block whose tool has not run yet, and the API returns a validation error if that tool is missing from the continuation.」

### 20. assistant で終わる再開は prefill ではなく正規の手順（247行）
**検証結果**: Server tools の公式例が assistant で終わる messages を再送している。「you continue it by re-sending the assistant content as-is」。

### 21. 再開がさらに `pause_turn` になることがあるので回数に上限を設ける（247行）
**検証結果**: Server tools「A continued turn can pause again … capping the number of continuations」。

### 22. サーバーツールとクライアントツールが同時に呼ばれると `stop_reason: "tool_use"` で返り、tool_result だけの user メッセージを返すと保留中のサーバーツールが実行される（249行）
**検証結果**: Server tools「Mixing server tools and client tools in one turn」。「The follow-up user message must contain nothing except `tool_result` blocks」。

### 23. ZDR には `allowed_callers: ["direct"]` が必要（251行）
**検証結果**: Server tools「ZDR and allowed_callers」。

### 24. 引用は Web 検索では自動、Web 取得では設定で有効化（263行）
**検証結果**: Web search「Citations are always enabled for web search」。Web fetch は前回確認（既定で無効）。

### 25. 並列ツール呼び出しは既定で有効（670行）
**検証結果**: Parallel tool use「By default, Claude may call multiple tools in a single response.」

### 26. すべての `tool_use` に `tool_result` を返し、1つの user メッセージにまとめる。分けると以降の並列呼び出しが減る（674行）
**検証結果**: Parallel tool use「Wrong: a separate user message for each tool result」「This "teaches" Claude to avoid parallel calls.」

### 27. user メッセージの中では `tool_result` を先頭に置く。前にテキストがあると 400（676行）
**検証結果**: Handle tool calls の 400 の例。

### 28. I/O 待ちの処理には `ThreadPoolExecutor` が効果的で、`map` は入力の順に結果を返す（682・730行）
**検証結果**: concurrent.futures「often used to overlap I/O instead of CPU work」。`map` は組み込みの `map` と同様（公式例は `zip(PRIMES, executor.map(...))` で順序に依存している）。

### 29. API は `tool_use_id` で対応を取るので順番が違っても動く（738行）
**検証結果**: Parallel tool use「The API doesn't prescribe an execution order」。結果は `tool_use_id` で対応付けられる。

### 30. `resolve()` は `..` とシンボリックリンクを解決し、`is_relative_to()` で配下かを判定する（837行）
**検証結果**: pathlib「Make the path absolute, resolving any symlinks … ".." components are also eliminated」、`is_relative_to` は 3.9 で追加。

### 31. `startswith` で判定すると `workspace_old/` が前方一致で通る。`is_relative_to` は部品単位で比べる（841行）
**検証結果**: pathlib の等価式 `u == p or u in p.parents`。`../workspace_old/x` が拒否されることも実行で確認。

### 32. 承認を拒否したときに例外で止めると `tool_result` が欠けて 400 になる。`is_error` で返す（935行）
**検証結果**: Server tools／Handle tool calls「`tool_use` ids were found without `tool_result` blocks immediately after」。

### 33. 現行モデルでは prefill が 400（1057行）
**検証結果**: Errors「Prefill not supported」（Claude 4.6 以降）。

### 34. 構造化出力は `output_config.format`（`json_schema`）で、文法の制約で生成される。refusal／max_tokens は例外（1063・1154行）
**検証結果**: Structured outputs の Invalid outputs（refusal・max_tokens ではスキーマに合わないことがある）。

### 35. Haiku 5.5 は思考が既定で有効で、思考トークンも `max_tokens` に数える。`effort: "low"` が使える（1108〜1111・1154行）
**検証結果**: Thinking の表（Haiku 5.5 は省略時 adaptive）。「they count toward `max_tokens`」。Effort「Claude Haiku 5.5 supports all five effort levels」。

### 36. オブジェクトには `additionalProperties: false` が必須で、`anyOf` で null を許せる（1076・1156行）
**検証結果**: Structured outputs「`required` and `additionalProperties` (must be set to `false` for objects)」「`anyOf` … null」。

### 37. `minLength`・`maxLength`・`minimum`・`maximum` は使えず 400（1156行）
**検証結果**: Structured outputs「If you use an unsupported feature, you'll receive a 400 error」。

### 38. 初回は文法の作成で遅く、文法は一定期間キャッシュされる（1158行）
**検証結果**: Structured outputs「Compiled grammars are cached for 24 hours from last use」。

### 39. `strict: true` でツールの引数を保証できる。`additionalProperties: false` が必須で、任意の引数はスキーマ全体で24個まで（1162行）
**検証結果**: Strict tool use と Structured outputs の「Optional parameters 24」。

### 40. `any`／`tool` による強制は Opus 5.5・Sonnet 5.5 で 400、`auto`／`none` のみ（1189・1203行）
**検証結果**: Errors「Forced tool use not supported」。Define tools の表「`auto` with strict tool use … or structured outputs」。

### 41. strict ツールは1リクエストあたり20個まで（1211行）
**検証結果**: Structured outputs「Strict tools per request 20」。

### 42. Python 3.13 の新機能に REPL の刷新がある（出力例 232行）
**検証結果**: What's New in Python 3.13「A greatly improved interactive interpreter」。

### 43. 6.2 の出力例のコスト（652〜659行）
**検証結果**: $0.0060＋$0.0062＝$0.0122（入力 2,188／出力 170）。単価表どおり。

---

## ⚠️ 要確認（古い可能性あり）

### 1. Windows で `/etc/passwd` を渡すと `C:\etc\passwd` に解決される（925行）
**記述**: 「しかし連結後に `C:\etc\passwd` へ解決されるため、配下チェックで弾かれます。」
**懸念点**: 実際には **WORKSPACE と同じドライブ** のルートに解決される。C: 以外のドライブでは `D:\etc\passwd` などになる（結論の「弾かれる」は正しい）。
**検索結果**: pathlib「On Windows, the drive is not reset when the argument is a rooted relative path」。C: 上で実行し、`C:\etc\passwd` に解決されて拒否されることを確認した。
**推奨対処**: 「連結後に `workspace` と同じドライブの `\etc\passwd`（例: `C:\etc\passwd`）へ解決されるため、配下チェックで弾かれます。」

### 2. 並列化の効果を「ログのタイムスタンプから分かります」（759行）
**記述**: 「3件のツールがほぼ同時刻に終わっていることが、ログのタイムスタンプから分かります。」
**懸念点**: 748〜753行の出力例はタイムスタンプを `...` で省略しており、読者は確認できない。
**推奨対処**: 出力例の3行をタイムスタンプ付きにする（例: `2026-11-06 14:12:05,201 agent tool=get_weather elapsed=0.58s` ／ `…05,233 … elapsed=0.61s` ／ `…05,252 … elapsed=0.63s`）。または本文を「各ツールの所要時間（elapsed）が約0.6秒ずつで、全体もほぼ同じ時間で終わっています」に変える。

### 3. 「第5章とまったく同じ振る舞いです」（664行）
**記述**: 「第5章とまったく同じ振る舞いです。」
**懸念点**: 正常系は同じだが、6.2版の `execute_tool_uses()` は `ToolError` しか捕まえない。そのため、第5章では is_error で返せていた天気ツールの `ValueError`（未知の都市）や `httpx` の接続エラーで、プログラムが落ちる（コード検証で再現。chapter_06_code_verify.md の❌1）。
**推奨対処**: コード側を修正する（code_verify の❌1の修正案）。コードを変えない場合は本文を「正常に答えられる場面では、第5章と同じ振る舞いです（失敗の扱いは6.3節で整えます）」に変える。

---

## ❌ 要修正（誤りの可能性が高い）

なし。

---

## 総評

前回の❌2件と⚠️6件は、すべて原稿に正しく反映されています。サーバーツール（版・`allowed_callers`・`max_uses`・`pause_turn` の再開と container・混在時の挙動・ZDR）、並列ツール呼び出し、構造化出力・strict ツールの制約、Haiku 5.5 の思考と effort は、2026-11-08 時点の公式ドキュメントと一致します。6.1節の設計原則（名前空間・action 引数・戻り値・強い指示の回避）も、Define tools と Prompting best practices に裏付けがあります。最も注意すべきなのは⚠️3で、6.2節のコードが第5章より失敗に弱くなっている点です（コード検証の❌1）。

---

## 再チェック（2026-11-08・修正箇所）

対象: `git diff` の変更 5か所（コード2か所の実行結果は chapter_06_code_verify.md の同名節）。

- ✅ L559-562（6.2版 `execute_tool_uses` の `except Exception`）
  オフライン実行で、未知の都市（ValueError）と接続エラー（httpx.ConnectError）が `is_error: true` の tool_result になり、ループが止まらないことを確認。第5章 L907 の `except Exception` と同じ振る舞いで、L664「第5章とまったく同じ振る舞いです」とも整合。
- ⚠️ L705-706（6.3版 `run_one_tool` の `except (ToolError, ValueError)`）
  動作は正しい（天気ツールの「英語表記で指定してください」がそのまま Claude に届く）。ただし第11章 L275「ほかの例外だと『予期しないエラー』という定型文になり」は、ValueError も文面がそのまま届くようになったため厳密でなくなった。
  修正案（第11章）:「`ToolError`（と `ValueError`）以外の例外だと、『予期しないエラー』という定型文になり…」。
- ✅ L738 本文「第5章の天気ツールは失敗を `ValueError` で表すので…」
  第5章 `_geocode()` が `raise ValueError(f"都市 '{city}' が見つかりません。英語表記（例: Tokyo）で指定してください。")` であることをコードで確認。
  （文体メモ: この1文は約85字。「…`ValueError` で表します。そこで、これも想定内として扱い、…届くようにしています。」と2文に分けると50字前後に収まる。任意）
- ⚠️ L753-757（6.3 実行ログにタイムスタンプを付与）
  時刻と elapsed の関係（turn=1 の 04,612 から約0.58〜0.63秒後に3件が完了）は整合し、`%(asctime)s %(name)s %(message)s` の書式とも一致。ただし、実際には `llm_client` の行も出るのに省略の注記がない（6.2節 L655 の例では `llm_client` 行を載せている）。また 6.4節 L1025 の例は `... agent` のままで、章内で表記が揃っていない。
  修正案: L752 のコードブロックの直前に「（`agent` の行だけを抜き出しています）」を添える。6.4節の例も時刻付きに揃えるか、同じ注記を付ける。
- ✅ L929「連結後に `workspace` と同じドライブの `\etc\passwd`（例: `C:\etc\passwd`）へ解決される」
  `PureWindowsPath('C:/proj/workspace') / '/etc/passwd'` → `C:\etc\passwd`、`PureWindowsPath('/etc/passwd').is_absolute()` → False を実行で確認。ドライブは WORKSPACE 側のものになるので、修正後の表現が正確。
