# ファクトチェックレポート

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_12.md
検証日: 2026-11-07
検証クレーム数: 22件
  ✅ 検証済み: 18件
  ⚠️ 要確認: 4件
  ❌ 要修正: 0件

検証方法: 12.3.1 の表の全URLに `curl -L` でアクセスし、HTTPステータスとリダイレクト先を確認した（2026-11-07）。API仕様は第10・11章の検証で取得した一次情報（Errors、移行ガイド、Pricing、Effort、Server tools）と照合した。

---

## ✅ 検証済み（正確）

### クレーム1〜8: 公式ドキュメントのURLが実在する（HTTP 200、リダイレクトなし）
**記述**: 12.3.1 の表のページ
**検証結果**:
- `api/messages` → 200
- `api/versioning` / `api/migration-2026-10-21` → 200
- `api/errors` / `api/rate-limits` → 200
- `build-with-claude/streaming` → 200
- `about-claude/pricing` → 200
- `agents-and-tools/tool-use/overview` → 200
- `build-with-claude/prompt-caching` / `build-with-claude/token-counting` → 200
- `build-with-claude/effort` / `build-with-claude/batch-processing` → 200

### クレーム9
**記述**: 「Building effective agents」（https://www.anthropic.com/engineering/building-effective-agents）
**検証結果**: HTTP 200。

### クレーム10
**記述**: 「多くのページは、URLの末尾に `.md` を付けると Markdown で取得できます」
**検証結果**: batch-processing.md、web-search-tool.md などを実際に Markdown で取得できた。

### クレーム11
**記述**: 「`2026-10-21` で `temperature` が廃止された」
**検証結果**: 移行ガイド。`temperature`/`top_p`/`top_k` を送ると、既定値でも400。

### クレーム12
**記述**: assistant の応答は thinking ブロックも含めて改変せずに履歴に戻す
**検証結果**: Errors「Thinking blocks cannot be modified」（改変すると400）。

### クレーム13
**記述**: 429・5xx・接続エラーは再試行し、`retry-after` を優先する。400系（429を除く）は再試行しない
**検証結果**: Errors / Rate limits と一致。補足すると、ティアの上限による429には `retry-after` がなく、再試行しても回復しない（Rate limits）。

### クレーム14
**記述**: `request-id` はサポートへの問い合わせで呼び出しを特定するのに必要
**検証結果**: Errors の Request ID の節。

### クレーム15
**記述**: 公式クライアントSDKは、HTTP呼び出しやリトライを提供するライブラリ
**検証結果**: Errors「The official SDK automatically retries transient failures ... twice by default」。

### クレーム16
**記述**: Claude Code ＝エージェント型コーディングツール、Claude Agent SDK ＝エージェントの仕組みをアプリに組み込むSDK
**検証結果**: 公式の位置づけと一致（本文は位置づけの紹介だけ）。

### クレーム17
**記述**: サーバーツールは `tools` に専用の型を書き、結果ブロックが返り、`pause_turn` で止まることがあり、Anthropic 側で実行され、結果はコンテキストを消費する
**検証結果**: Server tools / Web search tool（検索結果は入力トークンとして課金される）と一致。

### クレーム18
**記述**: `claude-opus-5-5` で品質を確かめ、`claude-haiku-5-5` に置き換える。モデルIDの定数化
**検証結果**: どちらのモデルIDも Pricing / Models に存在する。

---

## ⚠️ 要確認（古い可能性あり）

### クレーム19
**記述**: 「`2026-10-21` 版では `temperature` や prefill が使えないことも確認しました」
**懸念点**: prefill の禁止はAPIバージョンの変更ではない。モデルの制約（「Claude 4.6 and later models ... do not support prefilling assistant messages」、Errors）。2026-10-21 移行ガイドの破壊的変更に prefill はない。本書が使う Opus/Sonnet/Haiku 5.5 では結果は同じだが、原因の説明が不正確。
**推奨対処**: 「`2026-10-21` 版では `temperature` が送れず、本書で使うモデル（Claude 4.6 以降）では prefill も使えないことを確認しました」とする。第3章の該当箇所と `claude-api-facts.md` も同様に直す。

### クレーム20
**記述**: モデル一覧 `about-claude/models/overview`
**懸念点**: アクセスすると `https://platform.claude.com/docs/en/models/overview` にリダイレクトされる（リンク切れではない）。
**推奨対処**: 表のパスを `models/overview` に更新する（reference-doc.md も同様）。

### クレーム21
**記述**: Adaptive thinking `build-with-claude/adaptive-thinking`
**懸念点**: `build-with-claude/thinking-steering-and-cost` にリダイレクトされる。Errors などの公式内リンクは `build-with-claude/thinking` を使っている。
**推奨対処**: 実際の移転先を確認して、表のパスを更新する（例: `build-with-claude/thinking`）。

### クレーム22
**記述**: 「Tool use のページには、本書では概要にとどめたサーバーツールと `pause_turn` の詳しい説明もあります」
**懸念点**: `pause_turn` の詳しい説明があるのは、Server tools ページ（`agents-and-tools/tool-use/server-tools`）と Web search tool ページ。
**推奨対処**: 表に「サーバーツール / Web検索 | `agents-and-tools/tool-use/server-tools` / `agents-and-tools/tool-use/web-search-tool` | 第10章」の行を追加し、本文の案内先をそちらにする。

---

## 総評

URLはすべて到達可能で、リンク切れはない（2件はリダイレクト）。API仕様の振り返りも、prefill の扱いの説明を除けば一次情報と一致する。prefill を「2026-10-21 版の変更」とする説明は、第3章や `claude-api-facts.md` にも由来していると考えられるので、まとめて直すことを推奨する。
