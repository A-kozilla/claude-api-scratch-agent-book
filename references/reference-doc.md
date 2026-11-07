# 参考情報

---

## 技術参考情報（URL）
本教材は **Claude API（Messages API）をHTTPで直接呼び出す**ことを前提とする。
内容の正確性を一次情報で確認すべきトピックのURL一覧（`.md` で終わるURLはMarkdownで取得できる）。

| トピック | URL | 用途 |
|--------|-----|------|
| Messages API リファレンス | https://platform.claude.com/docs/en/api/messages.md | 第3章: リクエスト／レスポンス構造・パラメータ |
| API バージョン | https://platform.claude.com/docs/en/api/versioning.md | 第3章: `anthropic-version` ヘッダー |
| 2026-10-21 移行ガイド | https://platform.claude.com/docs/en/api/migration-2026-10-21.md | 第3章: `temperature` 等の廃止 |
| エラー | https://platform.claude.com/docs/en/api/errors.md | 第3・4章: HTTPステータス・エラー型・リトライ指針 |
| レート制限 | https://platform.claude.com/docs/en/api/rate-limits.md | 第4章: 429・`retry-after`・レート制限ヘッダー |
| ストリーミング | https://platform.claude.com/docs/en/build-with-claude/streaming.md | 第4章: SSEイベント種別 |
| モデル一覧 | https://platform.claude.com/docs/en/about-claude/models/overview.md（移転先へリダイレクトされる） | 第2・3章: モデルID・コンテキスト長 |
| 料金 | https://platform.claude.com/docs/en/about-claude/pricing.md | 第4・7章: コスト計算 |
| Tool use 概要 | https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview.md | 第5・6章: ツール定義・tool_choice・tool_result |
| Prompt caching | https://platform.claude.com/docs/en/build-with-claude/prompt-caching.md | 第7章: `cache_control` |
| Token counting | https://platform.claude.com/docs/en/build-with-claude/token-counting.md | 第7章: `/v1/messages/count_tokens` |
| Adaptive thinking / Effort | https://platform.claude.com/docs/en/build-with-claude/adaptive-thinking.md（thinking-steering-and-cost へリダイレクトされる） ・ https://platform.claude.com/docs/en/build-with-claude/effort.md | 第7章: 思考・effort |
| Batch processing | https://platform.claude.com/docs/en/build-with-claude/batch-processing.md | 第11章: Message Batches API |
| Building effective agents | https://www.anthropic.com/engineering/building-effective-agents | 第1・9章: ワークフロー／エージェントの設計パターン |

Spec Kit | https://github.github.com/spec-kit/ | Spec-Kitに関する内容の作成時にWebFetchで確認
---

## ローカル参考ファイル
自動読み込み対象外（サイズが大きい/特定章のみで使うため、該当コマンド内で
`Read`ツールを使って都度読み込む）。

| ファイル | 用途 |
|--------|------|
| references/claude-api-facts.md | 全章・全レクチャー共通のAPI仕様・コード規約・分量目標（執筆時は必ず読む） |
| references/codebase-spec.md | 読者プロジェクト `agent-from-scratch/` のファイル構成と関数シグネチャの契約（コードを含む執筆時は必ず読む） |
