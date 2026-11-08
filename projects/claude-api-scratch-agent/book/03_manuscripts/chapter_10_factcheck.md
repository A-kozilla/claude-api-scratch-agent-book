# ファクトチェックレポート

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_10.md
検証日: 2026-11-08
検証クレーム数: 33件
  ✅ 検証済み: 32件
  ⚠️ 要確認: 1件
  ❌ 要修正: 0件

参照した一次情報（2026-11-08 に取得）:
- Web search tool: https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool.md
- Server tools（pause_turn・container・allowed_callers）: https://platform.claude.com/docs/en/agents-and-tools/tool-use/server-tools.md
- Programmatic tool calling（supportedModels）: https://platform.claude.com/docs/en/agents-and-tools/tool-use/programmatic-tool-calling.md
- Messages API リファレンス: https://platform.claude.com/docs/en/api/messages.md
- Structured outputs / Effort / Pricing / 2026-10-21 移行ガイド（platform.claude.com の `.md`）
- ローカルで実験したもの: Python 3.12.7（asyncio.Lock）、httpx 0.28.1（MockTransport）、pytest、uv 0.13.5（`uv add --help`）

## 前回（2026-11-07）の指摘の反映状況

| 前回 | 内容 | 反映状況 |
|---|---|---|
| ❌30 | `max_uses` は「1ターン」の上限。動的フィルタリングの検索は再開をまたいで数えられない | ✅ 反映済み（L995 WARNING。`max_uses` ×（`MAX_CONTINUES` + 1）回の検索が起こり得ると明記） |
| ❌31 | pause_turn の再開で container ID を引き継ぐ | ✅ 反映済み（L920・L931-932 のコード、L979 の説明） |
| ⚠️28 | Opus 5.5 を「最上位モデル」と書いている | ✅ 反映済み（L105「本書で使う3つの中でもっとも高性能な Opus 5.5」） |
| ⚠️29 | ロックを後で作る理由づけが古い | ❌ **未反映**（L561 は前回の文のまま）。下記 ⚠️クレーム33 |
| code #16 | pause_turn の再送が prefill 扱いにならないか（一次情報の確認待ち） | ✅ 今回、一次情報で確認できた（クレーム6）。原稿の送り方は正しい |

---

## ✅ 検証済み（正確）

### クレーム1: `web_search_20260209` は動的フィルタリングに対応した版（L896, L979）
**検証結果**: Web search tool「`web_search_20260209`: adds dynamic filtering」。より新しい `web_search_20260318`（response inclusion）もあるが、本書の版で問題はない。

### クレーム2: リサーチャー（`claude-haiku-5-5`）で `web_search_20260209` を使える（L101, L218, L900）
**検証結果**: Web search tool の supportedModels に `claude-haiku-5-5` が含まれる。動的フィルタリングはプログラマティックツール呼び出しに対応したモデルで使える。Programmatic tool calling の supportedModels にも `claude-haiku-5-5` が含まれるので、`allowed_callers: ["direct"]` は不要。コード実行ツールを `tools` に加える必要もない（「You don't need to add the code execution tool to `tools` yourself.」）。

### クレーム3: トークン料金とは別に、検索1,000回あたり10ドル（L222-223, L896, L1317）
**検証結果**: Pricing／Web search tool「**$10 USD per 1,000 searches**, plus standard token costs」。動的フィルタリングのコード実行は追加料金なし（Pricing「Code execution is free when used with web search or web fetch.」）。

### クレーム4: 組織の管理者が Console で無効にしていると400エラー（L896, L1325）
**検証結果**: Web search tool の Note。無効のときは「a Messages API request that includes the tool fails with a 400 `invalid_request_error` that says web search is not enabled」。

### クレーム5: `usage.server_tool_use.web_search_requests` で検索回数を数える（L388, L925）
**検証結果**: Web search tool の Usage and pricing の例、および Messages API リファレンスの `ServerToolUsage.web_search_requests`。※この項目は null になり得る。コードへの影響は chapter_10_code_verify.md の ⚠️ #16 を参照。

### クレーム6: pause_turn では、返ってきた assistant の content を変更せずに末尾へ付けて再送する。prefill とは別物（L929-930, L977）
**検証結果**: Server tools「Pass the paused response back as-is in a subsequent request to let Claude continue its turn.」。公式のコード例も、`{"role": "assistant", "content": response.content}` を末尾に付けて再送している。Messages API リファレンスの stop_reason の説明も同じ（「You may provide the response back as-is in a subsequent request」）。前回のコード検証で「確認待ち」だった点は、これで解消した。

### クレーム7: 再開時も同じ tools を送る（L922 で `WEB_SEARCH_TOOL` を再利用）
**検証結果**: Server tools「Include the same tools in the continuation request.」

### クレーム8: `container` の ID を次のリクエストに入れる。省くと新しいコンテナになり途中経過が失われる（L931-932, L979）
**検証結果**: Server tools「Keep the container: If the response includes a `container` … send its ID back in the continuation request. Without it, the request runs in a new container, and files from earlier in the turn are lost.」。リクエストの `container` は文字列ID（またはオブジェクト）を受け付け、レスポンスの `container` は `{id, expires_at}` または null（Messages API リファレンス）。コードの `if response.get("container")` と `extra={"container": id}` は、どちらとも整合している。

### クレーム9: 再開を繰り返す場合も、一時停止した応答を順に履歴に残す（L926-932 のループ）
**検証結果**: Server tools「A continued turn can pause again … capping the number of continuations … Keep every paused response in `messages`, in order.」。`MAX_CONTINUES` の上限と、毎回 `messages.append` する実装は、この指示と一致する。

### クレーム10: サーバーツールは検索と推論をAPIの中で繰り返し、長引くと pause_turn で一時停止する（L977）
**検証結果**: Server tools「the API executes tool calls in a server-side agentic loop. On a long-running turn, the API might pause that loop and return a `pause_turn` stop reason.」

### クレーム11: 動的フィルタリングではコード実行のブロックも混ざる（L979）
**検証結果**: Web search tool「the response also contains the result blocks of the code execution tool」。

### クレーム12: `max_uses` は1ターンの上限。動的フィルタリングの検索は、再開すると前のリクエストの分が数えられない（L995）
**検証結果**: Web search tool の Max uses「limits the number of searches in a single turn」「Searches from earlier requests in that turn count against the limit, unless Claude ran them from code execution through dynamic filtering.」

### クレーム13: Web検索では引用が常に有効で、`url`・`title`・`cited_text` が入る（L981）
**検証結果**: Web search tool「Citations are always enabled for web search」。`web_search_result_location` のフィールドは `url`・`title`・`encrypted_index`・`cited_text`。

### クレーム14: 検索結果は入力トークンとしても課金される（L995）
**検証結果**: Pricing「Web search results retrieved throughout a conversation are counted as input tokens」。

### クレーム15: `output_config` に `effort` と `format` を同時に指定できる（L336-339, L357）
**検証結果**: Messages API リファレンスの `output_config` は `effort` と `format` を兄弟フィールドとして持ち、両方を指定した例がある。

### クレーム16: Opus 5.5 の `effort`（`low`／`medium`）。既定値は medium（L337, L514）
**検証結果**: Effort「Claude Opus 5.5 supports all five effort levels, and `medium` is the default」。

### クレーム17: スキーマでは個数を縛れない／整数は保証されても範囲は保証されない（L346, L1139）
**検証結果**: Structured outputs。`minItems` は0と1のみ、それ以外の配列の制約と `minimum`・`maximum` は非対応（送ると400）。

### クレーム18: `enum`・`required`・`additionalProperties: False` のスキーマ（L304-326, L1090-1109）
**検証結果**: Structured outputs。enum は対応している。オブジェクトの `additionalProperties` は false でなければならない。

### クレーム19: モデルIDと役割の割り当て（L98-105, L216-220）
**検証結果**: Pricing／Models に `claude-opus-5-5`・`claude-sonnet-5-5`・`claude-haiku-5-5` がある。料金表では Opus 5.5 より上位に Claude Fable 5.1（$10/$50）がある。本文は「本書で使う3つの中でもっとも高性能」としており、正確。

### クレーム20: 試用資料「出力の単価は入力の5倍程度」（L761）
**検証結果**: Pricing。Opus 5.5 は $4/$20、Sonnet 5.5 は $2/$10、Haiku 5.5 は $0.10/$0.50 で、いずれも5倍。

### クレーム21: `stop_reason == "refusal"`（L935, L1042）
**検証結果**: Messages API リファレンスの stop_reason の値は `end_turn`・`max_tokens`・`stop_sequence`・`tool_use`・`pause_turn`・`refusal`・`model_context_window_exceeded`。

### クレーム22: `anthropic-version: 2026-10-21`、`temperature` を送らない（L1455-1457）
**検証結果**: 2026-10-21 移行ガイド「a request that sends `temperature`, `top_p`, or `top_k` returns a 400 error」。

### クレーム23: Messages API はステートレス（L115）
**検証結果**: Messages API は、毎回 `messages` に会話の全履歴を送る設計（リファレンスの `messages` パラメーター）。サーバー側に会話状態を持たない。

### クレーム24: 出力例のコストと残額の整合（L1253-1266, L1302-1305）
**検証結果**: 役割別の合計は 0.0213+0.0187+0.1964+0.0802+0.0754 = 0.392 で、使用金額と一致する。残額の推移（0.957→0.921→0.812→0.768→0.661→最終0.608）から逆算したオーケストレーターの料金は約 $0.075 で、0.0754 と一致する。調査の見積もり $0.100 は、5問×$0.02 と一致する。

### クレーム25: `-m` で実行するとカレントディレクトリが検索パスに入る／`python report_agent/cli.py` だと `ModuleNotFoundError`（L179, L1246）
**検証結果**: Python のコマンドラインの仕様（`-m` は sys.path に cwd を入れる）。ローカルでも、`python patterns/chain.py` の形で同じエラーになることを確認した。

### クレーム26: argparse（`choices`・`store_true`・`--max-rounds` → `args.max_rounds`・`parser.error()`）（L1179-1205, L1232）
**検証結果**: 標準ライブラリの仕様どおり。`--budget 0` で `report_agent: error: --budget には正の数を指定してください` と表示され、終了コード2で終わることを実行して確認した。

### クレーム27: `uv add --dev pytest` で開発用の依存に入る（L1360-1362）
**検証結果**: uv 0.13.5 の `uv add --help`「--dev  Add the requirements to the development dependency group」。

### クレーム28: `pythonpath = ["."]` がないと tests/ から `import llm_client` できない（L1368, L1372）
**検証結果**: ローカルで確認した。`pythonpath` を外すと `pytest`（＝`uv run pytest` と同じ起動方法）は `ModuleNotFoundError: No module named 'llm_client'` になり、戻すと 5 passed になる（`python -m pytest` は cwd を入れるので通る点にも注意）。

### クレーム29: `httpx.MockTransport` は同期と非同期の両方に対応（L1356）
**検証結果**: httpx 0.28.1 で `MockTransport.__mro__` は `(MockTransport, AsyncBaseTransport, BaseTransport, object)`。実際に `AsyncClient` でも動作した。

### クレーム30: `asyncio.Lock` は再入できない（L568）
**検証結果**: Python の asyncio ドキュメント（Lock は非再入）。

### クレーム31: `encoding` を省略すると、Windows ではロケールの文字コード（cp932）が使われる（L263）
**検証結果**: Python 3.12 の `open()` の既定は `locale.getencoding()` で、日本語版 Windows では cp932。

### クレーム32: 並列調査から `add_searches()` を呼んでもロックは不要（L406）
**検証結果**: `research_web()` はすべて1つのイベントループ内のコルーチンで動き、`add_searches()` の中に `await` はない。そのため、加算の途中で他のタスクに切り替わることはない。`asyncio.to_thread` で動くのはローカル版のツールだけで、こちらは `add_searches()` を呼ばない。

---

## ⚠️ 要確認（古い可能性あり）

### クレーム33: ロックを後で作る理由（L561）
**記述**: 「ロックを `__init__()` ではなく後で作るのは、イベントループの中で作るのが安全だからです。」
**懸念点**: 前回の ⚠️29 が反映されていない。Python 3.10 以降の `asyncio.Lock` は、作成時にはループに結び付かない。最初に待ちが発生したときのループに結び付く。ローカル（Python 3.12.7）での実験結果は次のとおり。
- ループの外で作ったロックも、1回目の `asyncio.run()` では正常に動いた。
- 同じロックを2回目の `asyncio.run()` で取り合うと、`RuntimeError: <asyncio.locks.Lock ...> is bound to a different event loop` になった。
つまり問題は「どこで作るか」ではなく、「`asyncio.run()` のたびに新しいループができるので、ループごとに新しいロックが必要」という点である。
**推奨対処**: L561 の最後の1文を次のように置き換える。
> ロックを `__init__()` ではなく `_orchestrate()` の中で作るのは、`asyncio.run()` が呼ぶたびに新しいイベントループを作り、ロックは最初に使われたループに結び付くからです。実行のたびに新しいロックを用意しておけば、別のループで使い回して `RuntimeError` になる心配がありません。

---

## ❌ 要修正（誤りの可能性が高い）

該当なし。

---

## 総評

前回の ❌2件（`max_uses` の数え方・コンテナの引き継ぎ）と ⚠️28（「最上位モデル」）は、正しく反映されていました。前回のコード検証で「一次情報の確認待ち」だった pause_turn の再送方法も、Server tools の公式手順（一時停止した応答を as-is で返し、同じ tools とコンテナIDを送り、一時停止した応答はすべて順に残す）と一致することを確認しました。Web検索サーバーツールの記述（料金・Console での無効化・citations・Haiku 5.5 対応・コード実行ツールの追加が不要なこと）は、すべて最新の一次情報と一致しています。
残る指摘は、L561 のロックの理由づけ（前回 ⚠️29 が未反映）だけです。なお、Messages API リファレンスで `usage.server_tool_use` が「ServerToolUsage or null」と定義されている件は、コードの堅牢性の問題として chapter_10_code_verify.md に ⚠️ で記載しました。

## 再チェック（2026-11-08・修正箇所）

対象: `git diff` の変更3か所（コード1か所は chapter_10_code_verify.md に詳細）。

- ⚠️ **L561 ロックを `_orchestrate()` の中で作る理由**: 内容は正しい。偽APIなしの単体検証で、ループの外で作ったロックを2回目の `asyncio.run()` で取り合うと `RuntimeError: ... is bound to a different event loop`、実行ごとに作り直すと2回とも正常、直列化も `start1→end1→start2→end2` を確認。L683 の `self._delegate_lock = asyncio.Lock()` とも一致。
  ただし (1) L505 のコメント `# arun() の中で作る` が本文の `_orchestrate()` と食い違う。→ `# _orchestrate() の中で作る` に直す。(2) 「ロックを…からです。」が約95字で長い。→ 「ロックを `__init__()` ではなく `_orchestrate()` の中で作るのには理由があります。`asyncio.run()` は呼ばれるたびに新しいイベントループを作り、ロックは最初に使われたループに結び付きます。」のように2文に分ける。
- ✅ **L925〜926 `server_use = ... or {}`**: Messages API リファレンスで `usage.server_tool_use` は「ServerToolUsage or null」、`web_search_requests` は default 0。null・キーなし・通常値の3パターンで正しく動く（chapter_10_code_verify.md 参照）。
- ⚠️ **L1268 集計行 `calls=24 input=148,320 output=21,905 cache_write=12,410 cache_read=63,880 total=$0.3920`**: `total` は「使用金額 $0.392」・役割別コストの合計（0.0213+0.0187+0.1964+0.0802+0.0754=0.3920）と一致する。しかしトークン数が役割別コストと両立しない。調査（Haiku）の $0.0187 は Sonnet 単価換算で $0.374 分のトークンに相当し、計画・オーケストレーター（Opus）と執筆・レビュー（Sonnet）の Sonnet 換算 $0.325 と合わせると $0.699 が必要。全トークンを Sonnet 単価で数えても $0.553 にしかならず、どう配分しても成り立たない。
  修正案（第4章の単価で役割別コストを再現できる値）: `calls=24 input=205,800 output=26,000 cache_write=8,320 cache_read=45,500 total=$0.3920`。配分例: 計画 Opus 1,800/700/20/0、オーケストレーター Opus 9,000/1,500/1,500/9,500、調査 Haiku 120,000/12,000/4,000/20,000、執筆 Sonnet 50,000/9,000/2,000/14,000、レビュー Sonnet 25,000/2,800/800/2,000（入力/出力/キャッシュ書込/読取）で各役割の金額に一致。
