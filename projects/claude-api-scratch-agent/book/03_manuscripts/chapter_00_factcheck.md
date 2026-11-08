# ファクトチェックレポート

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_00.md
検証日: 2026-11-08
検証クレーム数: 13件
  ✅ 検証済み: 11件
  ⚠️ 要確認: 2件
  ❌ 要修正: 0件

主な一次情報（取得日 2026-11-08）:
- Models overview: https://platform.claude.com/docs/en/about-claude/models/overview.md
- Pricing: https://platform.claude.com/docs/en/about-claude/pricing.md
- Migration 2026-10-21: https://platform.claude.com/docs/en/api/migration-2026-10-21.md
- Errors: https://platform.claude.com/docs/en/api/errors.md
- Authentication: https://platform.claude.com/docs/en/manage-claude/authentication.md
- Rate limits（spend limit）: https://platform.claude.com/docs/en/api/rate-limits.md
- Thinking: https://platform.claude.com/docs/en/build-with-claude/thinking.md
- PyPI（httpx 0.28.1 / python-dotenv 1.2.4）

## 前回（2026-11-07）指摘の反映状況

| 前回 | 内容 | 状況 |
|---|---|---|
| ⚠️10 | `x-api-key` が公式で legacy 表記 | 未反映（本章は骨格コードのみなので本文修正は不要。第2章側のNOTE追加で対応すべき。下記⚠️クレーム12に継続） |

---

## ✅ 検証済み（正確）

### クレーム1
**記述**: 「外部ライブラリは、HTTP通信用の `httpx` と設定を読む `python-dotenv` の2つだけです」（L21）
**検証結果**: PyPI で httpx 0.28.1・python-dotenv 1.2.4 が最新（2026-11-08）。uv での導入時に anyio 等の推移的依存が入るが、直接の依存は2つで正しい。

### クレーム2
**記述**: `"model": "claude-opus-5-5"`／`"anthropic-version": "2026-10-21"`（L73・L77）
**検証結果**: Models overview の Claude API ID は `claude-opus-5-5`（日付サフィックスなし）。Migration ガイドで `2026-10-21` が現行版。

### クレーム3
**記述**: 「この版では `temperature` などの項目が使えなくなっているため、古い記事のコードを写すと400番のエラーになることがあります」（L168）
**検証結果**: Migration「In `2026-10-21`, a request that sends `temperature`, `top_p`, or `top_k` returns a 400 error, even at the parameter’s default value.」

### クレーム4
**記述**: 料金表 Opus 5.5 $4/$20・Sonnet 5.5 $2/$10・Haiku 5.5 $0.10/$0.50（L170〜174）
**検証結果**: Pricing の Model pricing 表と一致。

### クレーム5
**記述**: 「$0.10 / $0.50（入力10万トークン以下）」（L174）
**検証結果**: Pricing「Claude Haiku 5.5 (for prompts up to 100,000 tokens)」。閾値はプロンプト（入力）長で、超過時は $0.50 / $2.50。表記は正確。

### クレーム6
**記述**: 「返ってくる `content` は種類ごとのブロックの配列」「type が text のものだけを取り出す」（L85〜91）
**検証結果**: Thinking「`display` defaults to `"omitted"` on these models」— Opus 5.5 では空の `thinking` ブロックが text の前に入り得るため、type 判定は正しい作法。

### クレーム7
**記述**: 「Claude APIのエラーは `type` と `message` を含むJSONで返り」（L160）
**検証結果**: Errors「a top-level `error` object that always includes a `type` and `message` value」。

### クレーム8
**記述**: 「チャット画面の claude.ai と、開発者向けのClaude APIは別のサービスです。契約も料金体系も別」（L125）
**検証結果**: API は Console の Billing での前払いクレジット、claude.ai はサブスクリプション（Pricing・Rate limits の Billing 記述）。

### クレーム9
**記述**: 「Claude Consoleで必ず利用上限を設定してください」（L178）
**検証結果**: Rate limits「Setting your own spend limit」— Billing ページの Spend limits で設定、到達時は 400 `invalid_request_error`。

### クレーム10（参照整合）
**記述**: 「SDKとの対応関係は第4章のコラムで整理し、Claude Code などは第12章で次の一歩として紹介」（L123）
**検証結果**: chapter_04.md L1379「COLUMN: SDKは何をしてくれているのか」、chapter_12.md 12.3「さらに学ぶためのリソース」で確認。

### クレーム11
**記述**: Python 3.12・uv・VS Code、Windows・macOS・Linux いずれでも可（L166）
**検証結果**: uv 公式インストールページに3OS向けの手順あり。実環境（Windows 11 / uv 0.13.5 / Python 3.12.7）で第2章の手順が通ることを確認。

---

## ⚠️ 要確認（古い可能性あり）

### クレーム12
**記述**: 「送るのはヘッダー3つとJSONのボディだけ」（L91、コード中 `x-api-key`）
**懸念点**: Authentication・get-api-key は直接HTTPの認証を `Authorization: Bearer <key>` と記載し、`x-api-key` を「legacy」と表記。動作上は両方有効（Migration「The Claude API accepts a key in either header.」、公式 cURL 例も `x-api-key`）。
**検索結果**: authentication.md「You can also send the key in the legacy `x-api-key: YOUR_API_KEY` header in place of `Authorization`.」
**推奨対処**: 本章は現状でよい。facts.md の方針（`x-api-key` で統一）どおりで、第2章のヘッダー表直後に補足NOTEを入れる（chapter_02_factcheck.md クレーム38参照）。

### クレーム13
**記述**: 「`response["content"][0]["text"]` のような入れ子のアクセスが読めれば十分です」（L110）
**懸念点**: 事実誤りではないが、Opus 5.5 は既定で先頭に `thinking` ブロック（`text` キーなし）を返すため、この式をそのまま実行すると `KeyError: 'text'` になる。本書自身が L85 や第2章で「`content[0]` と決め打ちしない」と教えているので、例として矛盾して見える。
**検索結果**: Thinking「`"omitted"`: thinking blocks are returned with an empty `thinking` field」（Opus 5.5 の既定）。
**推奨対処**: 例を差し替える。
修正案: 「`response["usage"]["input_tokens"]` のような入れ子のアクセスが読めれば十分です。」

---

## ❌ 要修正（誤りの可能性が高い）

該当なし。

---

## 総評

モデルID・料金・APIバージョン・2026-10-21 版の破壊的変更・エラー形式はすべて一次情報と一致した。新たに、前提知識の説明で例示している `response["content"][0]["text"]` が、本書が繰り返し戒める「`content[0]` 決め打ち」になっている点を⚠️とした（Opus 5.5 では実際に KeyError になる）。認証ヘッダーの legacy 表記問題は第2章側で一言補足すれば十分。

## 再チェック（2026-11-08・修正箇所）

対象: `git diff` の変更1か所。結果: ✅1 / ⚠️0 / ❌0

- ✅ L110 入れ子アクセスの例を `response["content"][0]["text"]` → `response["usage"]["input_tokens"]` に変更。第2章「`content[0]` と決め打ちにしてはいけません」との矛盾が解消。`usage.input_tokens` はレスポンスの正式フィールド（api/messages）。※直前のコードで `response` は `httpx.Response` なので厳密には `response.json()[...]` だが、「のような」の例示であり許容範囲。
