# ファクトチェックレポート

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_11.md
検証日: 2026-11-07
検証クレーム数: 32件
  ✅ 検証済み: 28件
  ⚠️ 要確認: 3件
  ❌ 要修正: 1件（原稿修正済み）

主な一次情報:
- Batch processing: https://platform.claude.com/docs/en/build-with-claude/batch-processing.md
- Rate limits: https://platform.claude.com/docs/en/api/rate-limits.md
- Errors: https://platform.claude.com/docs/en/api/errors.md
- Pricing / Effort / Structured outputs / Messages API リファレンス / Server tools
- OWASP LLM01:2025 Prompt Injection（二次資料経由）

---

## ✅ 検証済み（正確）

### クレーム1
**記述**: 直接プロンプトインジェクションと間接プロンプトインジェクション（外部データに仕込まれた攻撃文）の区別
**検証結果**: OWASP LLM01:2025 の定義（Direct／Indirect = websites や files などの外部入力）と一致。隠し指示で画像リンクを挿入させて会話を流出させる例も、OWASP のシナリオと同じ。

### クレーム2
**記述**: 対策は1つでは不十分で、最小権限・人間の承認・入出力の検査を重ねる
**検証結果**: OWASP の緩和策（least privilege、human approval、input/output filtering）と一致。

### クレーム3
**記述**: 「`request-id` は ... レスポンスヘッダーやエラーボディに含まれます」
**検証結果**: Errors。すべてのレスポンスに `request-id` ヘッダーがあり、エラーボディにも `request_id` がある。

### クレーム4
**記述**: Opus 5.5 は $4/$20、Haiku 5.5 は $0.10/$0.50（10万トークン以下）。入力5万・出力5千で Opus 約0.30ドル、Haiku 約0.0075ドル
**検証結果**: Pricing と一致し、計算も正しい（0.20+0.10、0.005+0.0025）。

### クレーム5
**記述**: `output_config` の `effort` を下げると思考のトークンが減る
**検証結果**: Effort の説明と一致。

### クレーム6
**記述**: キャッシュヒット率 = cache_read ÷（input＋cache_creation＋cache_read）
**検証結果**: Rate limits の「total_input_tokens = cache_read + cache_creation + input_tokens」と整合する。

### クレーム7
**記述**: `POST /v1/messages/batches` に `custom_id` と `params` の組の `requests` 配列を送る。params は通常の Messages API のボディと同じ
**検証結果**: Batch processing。`custom_id` は `^[a-zA-Z0-9_-]{1,64}$`。例の `review-001` は適合する。

### クレーム8
**記述**: `GET /v1/messages/batches/{id}` で `processing_status` が `in_progress` から `ended` になる
**検証結果**: Batch processing と一致（取り消し中は `canceling` もある。⚠️クレーム30を参照）。

### クレーム9
**記述**: 完了後に設定される `results_url` から JSONL を取得する。取得にも認証が必要
**検証結果**: 作成直後の例では `results_url: null`。結果は .jsonl。公式の curl 例も `x-api-key` を付けている。

### クレーム10
**記述**: 「結果の順序は保証されない」ので `custom_id` で突き合わせる
**検証結果**: 「Batch results can be returned in any order ... always use the custom_id field.」

### クレーム11
**記述**: `request_counts` のキー（processing / succeeded / errored / canceled / expired）
**検証結果**: Batch processing の例と完全に一致。

### クレーム12
**記述**: `result.type` は succeeded / errored / canceled / expired で、それぞれの意味（errored＝リクエスト内容やサーバー側の問題、canceled＝取り消し、expired＝期限内に処理されなかった）
**検証結果**: 4種類の結果型の表と一致。errored・canceled・expired は課金されない。

### クレーム13
**記述**: 料金は通常の50%
**検証結果**: 「All usage is charged at 50 percent of the standard API prices.」

### クレーム14
**記述**: 件数・サイズ上限、処理期限、結果の取得期間には制約がある。取り消しのエンドポイントもある
**検証結果**: 100,000件または256MB、24時間で期限切れ、結果は作成から29日間取得できる、`POST /v1/messages/batches/{id}/cancel`。原稿は数値を書かずに公式を参照させており、正確。

### クレーム15
**記述**: バッチでもプロンプトキャッシュが使えるが、効くかどうかは保証されない
**検証結果**: 「cache hits are provided on a best-effort basis」（30〜98%）。割引は併用できる。

### クレーム16
**記述**: バッチで構造化出力（`output_config`）をそのまま使える
**検証結果**: Structured outputs の「Works with: Batch processing」。

### クレーム17
**記述**: `judge()` で `output_config` に `effort` と `format` を併用
**検証結果**: Messages API リファレンス。兄弟フィールドで併用でき、例もある。

### クレーム18
**記述**: 構造化出力には `additionalProperties: False` と `required` が必須、`enum` で値を限定できる
**検証結果**: Structured outputs と一致。

### クレーム19
**記述**: 「`stop_reason` が `refusal`」の扱い
**検証結果**: Messages API の stop_reason。

### クレーム20
**記述**: ガードレール出力例 `calls=3 input=1,152 output=147 total=$0.0002`、1件あたり0.0001ドル未満
**検証結果**: Haiku 5.5 の単価で $0.00019、1件あたり約 $0.00006。

### クレーム21
**記述**: eval 出力例 `total=$0.1042` / `$0.1050`（Opus 5.5）
**検証結果**: 6,480×$4/M+3,912×$20/M=$0.1042、6,912×$4/M+3,870×$20/M=$0.1050。

### クレーム22
**記述**: JSONログ例 `in=8214 out=1032 cost=$0.0535`（Opus 5.5）
**検証結果**: $0.03286+$0.02064=$0.0535。

### クレーム23
**記述**: asyncio のタスクは作成時のコンテキストを引き継ぐ。`ThreadPoolExecutor` は引き継がないので `contextvars.copy_context().run` を使う
**検証結果**: Python の contextvars・asyncio の仕様どおり。

### クレーム24
**記述**: ロガーに付けたフィルターは子ロガーから伝播したレコードには効かず、ハンドラーに付ければ全レコードに効く
**検証結果**: logging のドキュメント（伝播したレコードには、祖先ロガーのフィルターは適用されない）と一致。

### クレーム25
**記述**: `basicConfig()` はルートロガーにハンドラーがあると何もしない
**検証結果**: logging のドキュメント（`force=True` を付けない場合）。

### クレーム26
**記述**: サーバーツールの結果は自分のコードを通らずに文脈へ入る
**検証結果**: Server tools。「The API runs the tool internally ... you don't handle execution.」

### クレーム27
**記述**: 設定した利用上限に達するとAPIがエラーを返す
**検証結果**: Rate limits。自分で設定した上限に達すると 400 `invalid_request_error`（ティアの上限なら 429）。

### クレーム28
**記述**: `python -m evals.run_eval` で実行しないと `ModuleNotFoundError`
**検証結果**: Python の `-m` の仕様どおり。

---

## ⚠️ 要確認（古い可能性あり）

### クレーム29
**記述**: Haiku 5.5 を使う分類で `max_tokens=512`（guardrails の `llm_classify`）、`max_tokens=256`（batch_demo）
**懸念点**: Effort「Claude Haiku 5.5 ... Thinking is on by default and counts toward max_tokens, so leave room for it.」。思考が長引くと `max_tokens` で切れ、JSONが壊れる恐れがある（guardrails は JSONDecodeError を `review` に倒すので安全側には倒れるが、過検知になる）。
**推奨対処**: `output_config` に `"effort": "low"` を加えるか、`max_tokens` を1,000〜2,000程度に上げる。`/verify-code` の実API検証で `stop_reason` を確認する。

### クレーム30
**記述**: 「処理中は `in_progress`、完了すると `ended` になります」
**懸念点**: 取り消し後は `canceling` を経て `ended` になる（Batch processing）。誤りではないが、取り消しに触れている段落と合わせると不完全。
**推奨対処**: 「取り消した場合は `canceling` を経て `ended` になります」を1文追加する。

### クレーム31
**記述**: 「Claude Console のワークスペースごとに利用上限を設定しておくと」
**懸念点**: Rate limits「You can't set spend limits on the default workspace.」
**推奨対処**: 「（Default ワークスペースには設定できないので、本番用のワークスペースを作る）」と補足する。

---

## ❌ 要修正（誤りの可能性が高い）→ 原稿修正済み

### クレーム32
**記述**: 「組織・ワークスペース | Claude Console の利用上限（spend limit） | Console の Limits 画面で設定する」「Limits 画面では利用上限やレート制限を確認できます」
**問題**: Rate limits のドキュメントでは、Limits（Rate limits, `platform.claude.com/usage/limits`）画面で見るのはティアとレート制限。利用上限（spend limit）を設定するのは Billing 画面（`platform.claude.com/settings/billing`）で、ワークスペースの上限は各ワークスペースの設定で決める。
**修正内容**: 表のセルを「組織は Console の Billing 画面、ワークスペースは各ワークスペースの設定で設定する」に直した。本文も「Rate limits 画面では利用ティアとレート制限を確認できます。利用上限（spend limit）は Billing 画面で設定します。設定した上限に達するとAPIが400エラーを返すので」に直した。

---

## 総評

Message Batches API の記述（エンドポイント、custom_id と params、processing_status、request_counts、results_url、結果型、50%割引、順序非保証、キャッシュは best-effort）は、すべて公式と一致した。出力例の金額も単価表と整合している。修正したのは Console の画面名の1点のみ。残る注意点は、Haiku 5.5 の思考が既定で有効なため、小さい `max_tokens` で分類JSONが切れるリスク（クレーム29）。実行検証で確かめること。

---

## 対応（2026-11-07）

| 項目 | 対応 | 原稿の位置（対応後） |
|---|---|---|
| クレーム29（Haiku の max_tokens） | `llm_classify()` を `max_tokens=1000`・`output_config={"effort": "low", ...}` に変更し、`stop_reason == "max_tokens"` なら `review / guard_error` を返す分岐を追加（`refusal` は従来どおり `block`）。`batch_demo.py` も `"max_tokens": 1000`・`"effort": "low"` に変更し、`results()` で `stop_reason` が `end_turn` 以外の結果はJSONとして読まず「確認・再送の候補」として表示する。本文に理由（思考も `max_tokens` に数えられる）を各1〜2文追記 | L468-476・L505、L982-985・L1012-1018・L1028 |
| クレーム30（`canceling`） | STEP 2 に「取り消した場合は `canceling` を経て `ended` になります」を追加 | L928 |
| クレーム31（Default ワークスペース） | NOTE に「Default ワークスペースには利用上限を設定できないので、本番用のワークスペースを作って使いましょう」を追加 | L116 |
| 実行例の `cache_write=0`（4か所） | **0 のまま維持**。4か所とも `cache_control` を付けない呼び出しのため。L561 は `llm_classify()`（system は文字列）、L736・L754 は `evals/run_eval.py` の `call_messages()` 直呼び（回答・採点とも）、L869 のログは `ReportOrchestrator.run()` が最初に呼ぶ `make_plan()`（`call_messages()`・`effort: "low"`・キャッシュ指定なし）の行で、Agent（`cached_system()`・トップレベル `cache_control` 付き）の呼び出しではない。L869 の cost も Opus 5.5 単価で 8,214×$4/M＋1,032×$20/M＝$0.0535 と整合 | — |

検証: `scratchpad/verify/fix_ch07_09_11/proj/` で偽APIにより `guardrails.py`・`evals.run_eval`・`batch_demo`（create→status→results）を再実行し正常終了。`llm_classify()` に `stop_reason=max_tokens` を返す応答を差し替えて `review / guard_error`、`refusal` で `block` になることを確認。第10章の `pytest`（偽APIなし）は `5 passed`。
