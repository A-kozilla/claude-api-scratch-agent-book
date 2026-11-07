# ファクトチェックレポート

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_00.md
検証日: 2026-11-07
検証クレーム数: 10件
  ✅ 検証済み: 9件
  ⚠️ 要確認: 1件
  ❌ 要修正: 0件

主な一次情報（取得日 2026-11-07）:
- Models overview: https://platform.claude.com/docs/en/about-claude/models/overview.md
- Pricing: https://platform.claude.com/docs/en/about-claude/pricing.md
- Migration 2026-10-21: https://platform.claude.com/docs/en/api/migration-2026-10-21.md
- Versions: https://platform.claude.com/docs/en/api/versioning.md
- Errors: https://platform.claude.com/docs/en/api/errors.md
- Authentication: https://platform.claude.com/docs/en/manage-claude/authentication.md
- Rate limits（spend limit）: https://platform.claude.com/docs/en/api/rate-limits.md

---

## ✅ 検証済み（正確）

### クレーム1
**記述**: 「外部ライブラリは、HTTP通信用の `httpx` と設定を読む `python-dotenv` の2つだけです」
**検証結果**: 本書方針どおり。httpx 0.28.1・python-dotenv 1.2.4 が PyPI の最新（2026-11-07時点）で、いずれも利用可能。

### クレーム2
**記述**: 「"model": "claude-opus-5-5"」「"anthropic-version": "2026-10-21"」（hello_claude.py の骨格）
**検証結果**: Models overview で Claude API ID `claude-opus-5-5`（日付サフィックスなし）を確認。Versions ページで `2026-10-21` が最新版。

### クレーム3
**記述**: 「この版では `temperature` などの項目が使えなくなっているため、古い記事のコードを写すと400番のエラーになる」
**検証結果**: Migration ガイド「Sampling parameters are removed」: `temperature`・`top_p`・`top_k` を送ると、既定値でも 400。

### クレーム4
**記述**: 料金表（Opus 5.5 $4/$20、Sonnet 5.5 $2/$10、Haiku 5.5 $0.10/$0.50）
**検証結果**: Pricing ページと一致。

### クレーム5
**記述**: 「$0.10 / $0.50（入力10万トークン以下）」
**検証結果**: Pricing「Claude Haiku 5.5 (for prompts up to 100,000 tokens)」。超える場合は $0.50 / $2.50（プロンプト長はキャッシュ読み書きを含む全入力トークンで判定）。

### クレーム6
**記述**: 「返ってくる `content` は種類ごとのブロックの配列」「type が text のものだけを取り出す」
**検証結果**: Messages API リファレンスの Response スキーマで確認。Opus 5.5 は既定で `thinking` ブロック（`display: "omitted"` で中身は空文字）が先頭に入り得るため、type 判定は正しい作法。

### クレーム7
**記述**: 「Claude APIのエラーは `type` と `message` を含むJSONで返り」
**検証結果**: Errors「Error shapes」: `{"type":"error","error":{"type":...,"message":...},"request_id":...}`。

### クレーム8
**記述**: 「チャット画面の claude.ai と、開発者向けのClaude APIは別のサービスです。契約も料金体系も別」
**検証結果**: API は Console でのクレジット前払い（Billing）、claude.ai はサブスクリプション。サポート記事・Pricing で確認。

### クレーム9
**記述**: 「Claude Consoleで必ず利用上限を設定してください」
**検証結果**: Rate limits「Setting your own spend limit」で、Console の Billing 画面から組織の spend limit を設定できることを確認。上限到達時は 400 `invalid_request_error` で拒否される。

---

## ⚠️ 要確認（古い可能性あり）

### クレーム10
**記述**: 「送るのはヘッダー3つとJSONのボディだけ」（コード中 `"x-api-key": os.environ["ANTHROPIC_API_KEY"]`）
**懸念点**: Authentication ドキュメントは直接HTTPでの認証を `Authorization: Bearer <key>` を主とし、`x-api-key` を「legacy」と表記するようになった。`x-api-key` も引き続き受け付けられ（「The Claude API accepts a key in either header」）、公式の cURL 例も `x-api-key` を使っているため動作上の問題はない。
**検索結果**: auth.md「You can also send the key in the legacy `x-api-key: YOUR_API_KEY` header in place of `Authorization`.」／migration-2026-10-21「The Claude API accepts a key in either header.」
**推奨対処**: 本文は現状のままでよいが、第2・3章（ヘッダー解説）で「`x-api-key` の代わりに `Authorization: Bearer` でも送れる（公式はこちらを推奨表記）」と一言補足することを推奨。全章のコード規約に関わるため facts.md 側で方針を決めること（chapter_03_factcheck.md 末尾参照）。

---

## 総評

はじめにの事実主張はモデルID・料金・APIバージョン・2026-10-21 版の破壊的変更ともに一次情報と一致した。唯一、認証ヘッダー `x-api-key` が公式ドキュメント上「legacy」扱いになった点は、全章共通の論点として facts.md で方針決定が必要（動作上の誤りではない）。
