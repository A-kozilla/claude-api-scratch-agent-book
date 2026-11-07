# ファクトチェックレポート

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_01.md
検証日: 2026-11-07
検証クレーム数: 21件
  ✅ 検証済み: 18件
  ⚠️ 要確認: 2件
  ❌ 要修正: 1件（原稿修正済み）

主な一次情報（取得日 2026-11-07）:
- Models overview / Pricing / Messages API リファレンス / Thinking（https://platform.claude.com/docs/en/build-with-claude/thinking.md）/ Handling stop reasons（https://platform.claude.com/docs/en/build-with-claude/handling-stop-reasons.md）/ Token counting / Errors
- ReAct 論文: https://arxiv.org/abs/2210.03629
- Building effective agents: https://www.anthropic.com/engineering/building-effective-agents

---

## ✅ 検証済み（正確）

### クレーム1
**記述**: 「`/v1/messages/count_tokens`というエンドポイントがあります」
**検証結果**: Token counting ドキュメントで確認。無料（RPM制限あり）、値は estimate。

### クレーム2
**記述**: 「実際に送ったリクエストのトークン数は、レスポンスの`usage`という項目に毎回記録」
**検証結果**: Messages API リファレンスの `usage`（input_tokens / output_tokens / cache_* 等）。

### クレーム3
**記述**: 「文章は`text`ブロック、道具を使いたいという要求は`tool_use`ブロックとして返ってきます」
**検証結果**: Messages API リファレンスの content block 型で確認。

### クレーム4
**記述**: 「道具の名前・説明・引数の形をJSON Schemaで定義して、リクエストと一緒に送ります」
**検証結果**: Tool use 概要／define-tools: `name`・`description`・`input_schema`（JSON Schema）。

### クレーム5
**記述**: 「Claudeはツールを実行しません」「サーバーツールという種類のツールも用意されています」
**検証結果**: クライアントツールはアプリ側が実行し `tool_result` を返す。web search / web fetch 等はサーバーツールとして Anthropic 側で実行される（server-tools ドキュメント）。

### クレーム6
**記述**: 「`stop_reason`が`"tool_use"`ならツールを実行…`"end_turn"`なら…ループを抜けて」
**検証結果**: stop_reason の定義と一致。

### クレーム7
**記述**: 「並列ツール呼び出しと呼び、Claude APIでは既定で有効」
**検証結果**: `tool_choice` の `disable_parallel_tool_use` 既定値は `false`（Messages API リファレンス）。

### クレーム8
**記述**: 「`claude-opus-5-5`では、この思考が常に有効」「思考の量は`effort`という設定で調整」「`thinking`ブロックとして含まれることがあり」
**検証結果**: Models overview「Thinking: Adaptive (always on)」「Default effort: medium」。`thinking: {"type":"disabled"}` は Opus 5.5 で 400。

### クレーム9
**記述**: 「回答がこの上限に達すると、`stop_reason`は`max_tokens`」「Claudeが応答を拒否…`stop_reason`は`refusal`」
**検証結果**: Handling stop reasons／Messages API の StopReason 列挙で確認。

### クレーム10
**記述**: 「Claude APIは**ステートレス**です」
**検証結果**: Messages API は毎回 `messages` に過去のターンを渡す設計（「you specify the prior conversational turns with the `messages` parameter」）。

### クレーム11
**記述**: 「`tool_use`と…`tool_result`を、`toolu_01A`という同じIDで結び付けて」
**検証結果**: `tool_result.tool_use_id` が `tool_use.id` に対応（Tool use ドキュメント）。

### クレーム12
**記述**: 「`anthropic-version: 2026-10-21`というヘッダーで、使うAPIのバージョンを指定」
**検証結果**: Versions ページ「you must send an `anthropic-version` request header. For example, `anthropic-version: 2026-10-21`」。

### クレーム13
**記述**: 「最大100万（1M）トークンのコンテキストウィンドウ」「1回の出力の上限は、最大12万8,000（128K）トークン」
**検証結果**: Models overview: Opus/Sonnet/Haiku 5.5 いずれも Context window 1M、Max output 128K（同期 Messages API）。

### クレーム14
**記述**: 「`claude-opus-5-5`の料金は、入力100万トークンあたり4ドル、出力…20ドル」
**検証結果**: Pricing と一致。

### クレーム15
**記述**: 「ReActは、2022年に発表された論文「ReAct: Synergizing Reasoning and Acting in Language Models」」
**検証結果**: arXiv 2210.03629、2022-10-06 投稿。

### クレーム16
**記述**: 「Building effective agents」…「エージェンティックシステム」を「ワークフロー」と「エージェント」に分ける／「まずは最も単純な方法から」
**検証結果**: 同記事「finding the simplest solution possible, and only increasing complexity when needed」、agentic systems を workflows と agents に区別。

### クレーム17
**記述**: 「すべての`tool_result`を1つのメッセージにまとめて返すのがルール」「`response["content"]`は、手を加えずにそのまま履歴へ」
**検証結果**: Tool use（parallel tool use）ドキュメント、および Thinking「Pass every `thinking` block back to the API complete and unmodified」。

### クレーム18
**記述**: 「より安いモデルとして`claude-haiku-5-5`や`claude-sonnet-5-5`も用意」
**検証結果**: Pricing（Sonnet 5.5 $2/$10、Haiku 5.5 $0.10/$0.50〜）。

---

## ⚠️ 要確認（古い可能性あり）

### クレーム19
**記述**: 表「1回だけ呼ぶ: 入力3,500」と「10往復: 1回目は2,000トークン」
**懸念点**: 10往復側の1回目が2,000トークン（systemとツール定義のみ）なのに、1回だけ呼ぶ側は3,500トークンで、前提がそろっていない。数値自体の計算（87,500トークン・約0.45ドル）は正しい。
**検索結果**: 計算検証: Σ(2,000+1,500k, k=0..9)=87,500。87,500×$4/1M=$0.35、5,000×$20/1M=$0.10。
**推奨対処**: 「1回目は2,000トークン（system・ツール定義に最初の依頼を含む）」のように前提を明記するか、1回だけ呼ぶ側を「2,000」にそろえる（その場合 約0.018ドル、比は約25倍）。

### クレーム20
**記述**: 「本書のエージェントでは、ループの終わり方を次の4種類に整理」（end_turn / max_tokens / refusal / max_turns）
**懸念点**: 誤りではないが、stop_reason には `stop_sequence`・`pause_turn`・`model_context_window_exceeded` もある。特に `model_context_window_exceeded`（コンテキストウィンドウが埋まって停止）は長いエージェントループで現実に起こり得る。
**検索結果**: Messages API の StopReason 列挙: end_turn / max_tokens / stop_sequence / tool_use / pause_turn / refusal / model_context_window_exceeded。
**推奨対処**: 2つ目の「出力の上限による中断」に「コンテキストウィンドウが埋まった場合の `model_context_window_exceeded` も同様に途中で切れた扱い」と一文添える（第5章のループ実装でも扱うこと）。

---

## ❌ 要修正（誤りの可能性が高い）

### クレーム21
**記述**: 「1回だけ呼び出す場合の約0.02ドルと比べると、20倍以上の差です」
**問題**: 1回だけ呼ぶ場合の正確なコストは 3,500×$4/1M + 500×$20/1M = $0.024。$0.45 ÷ $0.024 ≒ 18.8倍で、「20倍以上」にはならない。
**正しい情報**: 約19倍。
**修正案（適用済み）**: 「1回だけ呼び出す場合の約0.02ドルと比べると、20倍近い差です。」

---

## 総評

概念章のためAPI仕様の主張は少ないが、モデル仕様・stop_reason・並列ツール・thinking・料金はすべて一次情報と一致した。コスト試算の倍率表現を1か所修正。表の前提の不一致（⚠️19）は読者が自分で再計算したときに混乱しやすいので、直しておくことを推奨する。
