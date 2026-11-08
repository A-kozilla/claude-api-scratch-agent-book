# ファクトチェックレポート

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_12.md
検証日: 2026-11-08
検証クレーム数: 22件
  ✅ 検証済み: 17件
  ⚠️ 要確認: 5件
  ❌ 要修正: 0件

検証方法: 12.3.1 の表と 12.3.2 の全URLに `curl -L` でアクセスし、HTTPステータスとリダイレクト先を確認した（2026-11-08）。API仕様は Errors・移行ガイド（2026-10-21）・Versioning・Server tools・Tool use 概要を `.md` で取得して照合した。12.1 の振り返りと 12.2 のチェックリストの「第N章」の参照は、chapter_01〜11.md を Grep し、第4〜10章のコードブロックを抽出して照合した。

---

## 前回（2026-11-07）の指摘の反映状況

| 前回の項目 | 状態 |
|---|---|
| ⚠️ クレーム19（prefill を `2026-10-21` 版の変更とする説明） | **反映済み**。L35「`2026-10-21` 版では `temperature` などが使えないこと、Claude 4.6 以降のモデルでは prefill が使えないことも確認しました」 |
| ⚠️ クレーム20（`about-claude/models/overview` のリダイレクト） | **未反映**（L236 のまま）。下記クレーム18 |
| ⚠️ クレーム21（`build-with-claude/adaptive-thinking` のリダイレクト） | **未反映**（L239 のまま）。下記クレーム19 |
| ⚠️ クレーム22（Tool use のページに `pause_turn` の詳しい説明がある） | **未反映**（L244 のまま）。下記クレーム20 |
| コード検証の L79（`Agent.arun()`/`acall_messages()`）・L63・L65 の注記・「トレースID」 | すべて反映済み |

---

## ✅ 検証済み（正確）

### クレーム1: 公式ドキュメントのURLが実在する（HTTP 200、リダイレクトなし）
**記述**: 12.3.1 の表のページ
**検証結果**: `api/messages`・`api/versioning`・`api/migration-2026-10-21`・`api/errors`・`api/rate-limits`・`build-with-claude/streaming`・`about-claude/pricing`・`agents-and-tools/tool-use/overview`・`build-with-claude/prompt-caching`・`build-with-claude/token-counting`・`build-with-claude/effort`・`build-with-claude/batch-processing` の12ページすべて 200。

### クレーム2
**記述**: 「多くのページは、URLの末尾に `.md` を付けると Markdown で取得できます」
**検証結果**: 上記のページと Server tools・Rate limits などを `.md` で取得できた（frontmatter 付きの Markdown が返る）。

### クレーム3
**記述**: 「`2026-10-21` で `temperature` が廃止された」「`2026-10-21` 版では `temperature` などが使えない」
**検証結果**: 移行ガイド「In `2026-10-21`, a request that sends `temperature`, `top_p`, or `top_k` returns a 400 error, even at the parameter's default value.」。

### クレーム4
**記述**: 「Claude 4.6 以降のモデルでは prefill が使えない」
**検証結果**: Errors「Claude 4.6 and later models and Claude Mythos Preview do not support prefilling assistant messages」（400 `invalid_request_error`）。

### クレーム5
**記述**: assistant の応答は thinking ブロックも含めて改変せず履歴に戻す
**検証結果**: Errors「Thinking blocks cannot be modified」。「pass back every `thinking` and `redacted_thinking` block … exactly as received, including blocks whose `thinking` field is empty」。

### クレーム6
**記述**: 429・5xx・接続エラーは再試行し、400系（429を除く）は再試行しない。408・409 も再試行対象（L149）
**検証結果**: Errors。500 は「Retry the request with exponential backoff」、409 は「Resolve the conflict, then retry」、SDK は「connection errors, rate limits, and 5xx server errors」を再試行し `retry-after` を尊重する。408 は API の一覧にない SDK 慣例で、第4章の実装（`claude-api-facts.md`）と一致する。

### クレーム7
**記述**: 「`request-id` は、サポートへの問い合わせで呼び出しを特定するのに必要です」
**検証結果**: Errors「When contacting support about a specific request, include this ID」。

### クレーム8
**記述**: 公式クライアントSDKは、HTTP呼び出しやリトライを各言語向けに提供するライブラリ
**検証結果**: Errors「The official SDK automatically retries transient failures … twice by default」。Python・TypeScript・C#・Go・Java・PHP・Ruby の SDK がある。

### クレーム9
**記述**: Claude Code＝エージェント型コーディングツール、Claude Agent SDK＝エージェントの仕組みをアプリに組み込むSDK
**検証結果**: 公式の位置づけと一致（本文は位置づけの紹介のみ）。

### クレーム10
**記述**: サーバーツールは `tools` に専用の型を書き、結果ブロックが返り、`pause_turn` で止まることがあり、Anthropic 側で実行され、結果はコンテキストを消費する
**検証結果**: Server tools「The API runs the tool internally」「The tool's result block (for example, `web_search_tool_result`) follows the `server_tool_use` block」「the API might pause that loop and return a `pause_turn` stop reason」。

### クレーム11
**記述**: `claude-opus-5-5` で品質を確かめ、`claude-haiku-5-5` に置き換える
**検証結果**: どちらのモデルIDも Pricing・Batch processing の対応モデル一覧に存在する。

### クレーム12
**記述**: `anthropic-version` を固定し、更新時は移行ガイドで確かめる
**検証結果**: Versioning「you must send an `anthropic-version` request header」。`2026-10-21` に移行ガイドへのリンクがある。

### クレーム13
**記述**: 第10章で `httpx.MockTransport` を差し込み、APIを呼ばずにテストを書いた（L31・L171）
**検証結果**: chapter_10.md の `llm_client.set_transport()` と `tests/test_report_agent.py` で確認。

### クレーム14
**記述**: 章ごとの成果物の表（L41-53）と最終ディレクトリ構成（L57-73）
**検証結果**: chapter_02〜11 の各コードブロックのファイル名コメントと一致（`hello_claude.py` 〜 `guardrails.py`/`evals/run_eval.py`/`batch_demo.py`）。`llm_client.py` の「第7・8・10章で拡張」、`agent.py` の「第6・7章 → 第8章 Agentクラス」も、第7章 `count_tokens`・キャッシュ補助、第8章の非同期版、第10章 `set_transport()`、第7章 `BASE_SYSTEM`・`effort` と整合する。

### クレーム15
**記述**: 第10章の CLI では `asyncio.run()` の中でオーケストレーターの `Agent.arun()` がループを回し、`maybe_compact()`・`acall_messages()`・`CostTracker` が動く（L79）
**検証結果**: 第8章の `arun()`（`asyncio.to_thread(maybe_compact, ...)`→`acall_messages()`）と第10章の `orchestrator.py` で確認。

### クレーム16
**記述**: ジッターは第4章で学んだサンダリングハード問題を避けるため（L156）。429・529 の頻発は第4・8章（同時実行数の上限）（L106）
**検証結果**: chapter_04.md L467 にサンダリングハードの説明、chapter_08.md に `asyncio.Semaphore` による同時実行数の制限がある。

### クレーム17
**記述**: 第2章で curl と httpx で最初のリクエストを送った。キーを `.env` で管理（L35・L128）
**検証結果**: chapter_02.md の「この章で学ぶこと」と本文で確認。

---

## ⚠️ 要確認（古い可能性あり）

### クレーム18
**記述**: モデル一覧 `about-claude/models/overview`（L236）
**懸念点**: `https://platform.claude.com/docs/en/models/overview`（タイトル「Models overview」）にリダイレクトされる。リンク切れではないが、前回から未修正。公式ドキュメント内のリンク（Batch processing の「active models」など）も `models/overview` を使っている。
**推奨対処**: L236 を `` `models/overview` / `about-claude/pricing` `` に直す。`references/reference-doc.md` の表も同じく更新する。

### クレーム19
**記述**: Adaptive thinking `build-with-claude/adaptive-thinking`（L239）
**懸念点**: `build-with-claude/thinking-steering-and-cost`（タイトル「Steering thinking」）にリダイレクトされる。Errors などの公式内リンクは、思考の総合ページとして `build-with-claude/thinking`（タイトル「Thinking」、200）を使っている。前回から未修正。
**推奨対処**: 表の行を「| Thinking / Effort | `build-with-claude/thinking` / `build-with-claude/effort` | 第7章 |」に直す。

### クレーム20
**記述**: 「Tool use のページには、本書では概要にとどめたサーバーツールと `pause_turn` の詳しい説明もあります」（L244）
**懸念点**: 2026-11-08 時点の Tool use 概要（`agents-and-tools/tool-use/overview.md`）には `pause_turn` という語が一度も出てこない。サーバーツールについても「See Server tools for the mechanics they share」と別ページへ案内している。`pause_turn` の説明があるのは Server tools ページ（`agents-and-tools/tool-use/server-tools`、200）。前回から未修正。
**推奨対処**: 表に「| サーバーツール | `agents-and-tools/tool-use/server-tools` | 第6・10章 |」の行を追加し、L244 の最終文を「サーバーツールと `pause_turn` の詳しい説明は、Server tools のページにあります。」に直す。

### クレーム21
**記述**: 「Building effective agents」（`https://www.anthropic.com/engineering/building-effective-agents`）（L250）
**懸念点**: 2026-11-08 時点で、このURLは 308 Permanent Redirect で `https://www.anthropic.com/research/building-effective-agents`（タイトル「Building effective AI agents \ Anthropic」、200）に転送される。前回（2026-11-07）はリダイレクトなしと記録しているので、最近移転した可能性がある。リンク切れではない。
**推奨対処**: 本文のURLを `https://www.anthropic.com/research/building-effective-agents` に更新する（`references/reference-doc.md` も同様）。記事名を「Building effective AI agents」とするかは、公開前に実ページの見出しで確認する。

### クレーム22
**記述**: 「1回の依頼に共通のトレースIDを振り、エージェント名とターン番号を残しているか（第11章）」（L161）
**懸念点**: トレースIDは第11章だが、エージェント名（第8章 `Agent` のログ `[%s]` の `self.name`）とターン番号（第5〜7章 `run_agent` の `turn=%d`）をログに出したのは第5・8章。第11章の「何をログに残すか」の表（chapter_11.md L774-780）にはエージェント名・ターン番号の項目がない。
**推奨対処**: 参照を「（第5・8・11章）」に直す。

---

## ❌ 要修正（誤りの可能性が高い）

該当なし。

---

## 総評

URLはすべて到達でき、リンク切れはない。ただし、3件のリダイレクト（モデル一覧・Adaptive thinking・Building effective agents）と、Tool use ページの案内先（`pause_turn` の説明は Server tools ページにある）が残っている。このうち3件は前回も指摘したまま未修正。本書は「一次情報を読んで自分で確かめる力」を勧める章なので、案内するURLは最新の正式なパスにそろえておくことを推奨する。API仕様の振り返り（temperature の廃止、prefill の制約、thinking ブロックの扱い、再試行の方針、request-id）は一次情報と一致し、前回の prefill の指摘も正しく直っていた。第1〜11章との照合でも、ファイル名・関数名・章の対応に食い違いはなかった（L161 の章番号のみ ⚠️）。

## 再チェック（2026-11-08・修正箇所）

対象: chapter_12.md の変更6か所と references/reference-doc.md の変更3か所。URL は `curl` でステータスとリダイレクト先を確認した。

### chapter_12.md
- ✅ **L161 チェックリスト（第5・8・11章）**: ターン番号は第5章（`turn=%d`）、エージェント名は第8章（`[%s]` ログ）、トレースIDは第11章 11.3 節で扱っており、対応章として正しい。
- ✅ **L236 `models/overview`**: `https://platform.claude.com/docs/en/models/overview`（`.md` 付きも）が 200、リダイレクトなし。旧パス `about-claude/models/overview.md` は 307 でここへ転送される。
- ✅ **L238 サーバーツール `agents-and-tools/tool-use/server-tools`**: 200、リダイレクトなし。ページ（title: Server tools）は server_tool_use ブロック・`pause_turn` の継続を扱う。第6章（サーバーツール20か所・`pause_turn`）と第10章（Web検索）で使っており、対応章も正しい。
- ✅ **L240 `build-with-claude/thinking` / `build-with-claude/effort`**: どちらも 200、リダイレクトなし。thinking ページは adaptive thinking・effort による深さの調整・モデル別の既定値を扱う。旧 `adaptive-thinking.md` は 307 で `thinking-steering-and-cost.md` に転送されるので、差し替えは妥当。
- ✅ **L245 `pause_turn` の詳細は Server tools のページ**: 同ページで `pause_turn` が17か所記載されていることを確認。1文は約55字で許容範囲。
- ✅ **L251 Building effective agents の URL**: `https://www.anthropic.com/research/building-effective-agents` が 200。旧 `/engineering/...` は 308 でここへ転送される。「エンジニアリングブログの記事」を「Anthropic の記事」に改めたのもパスと整合。他章・references に旧URLの残りはない（Grep 確認）。
- 表内のその他のパス（api/messages, api/versioning, api/migration-2026-10-21, api/errors, api/rate-limits, build-with-claude/streaming, about-claude/pricing, agents-and-tools/tool-use/overview, build-with-claude/prompt-caching, build-with-claude/token-counting, build-with-claude/batch-processing）もすべて 200・リダイレクトなし。

### references/reference-doc.md
- ✅ **L17 モデル一覧 `https://platform.claude.com/docs/en/models/overview.md`**: 200、リダイレクトなし。注記「（移転先へリダイレクトされる）」の削除も正しい。
- ✅ **L22 Thinking / Effort（`thinking.md`・`effort.md`）**: どちらも 200、リダイレクトなし。
- ✅ **L24 Building effective agents `https://www.anthropic.com/research/building-effective-agents`**: 200、リダイレクトなし。chapter_12.md L251 と一致。
