# ファクトチェックレポート

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_11.md
検証日: 2026-11-08
検証クレーム数: 34件
  ✅ 検証済み: 31件
  ⚠️ 要確認: 3件
  ❌ 要修正: 0件

主な一次情報（2026-11-08 に取得）:
- Batch processing: https://platform.claude.com/docs/en/build-with-claude/batch-processing.md
- Rate limits: https://platform.claude.com/docs/en/api/rate-limits.md
- Errors: https://platform.claude.com/docs/en/api/errors.md
- Pricing: https://platform.claude.com/docs/en/about-claude/pricing.md
- Effort: https://platform.claude.com/docs/en/build-with-claude/effort.md
- Structured outputs: https://platform.claude.com/docs/en/build-with-claude/structured-outputs.md
- Messages API: https://platform.claude.com/docs/en/api/messages.md（`output_config`）
- Server tools / Tool use 概要: https://platform.claude.com/docs/en/agents-and-tools/tool-use/server-tools.md ・ `/overview.md`
- OWASP LLM01:2025 Prompt Injection（二次資料経由: strobes.co、aembit.io）
- Claude Console の Usage / Cost 画面: support.claude.com の記事 9534590（Cost and usage reporting）

---

## 前回（2026-11-07）の指摘の反映状況

| 前回の項目 | 状態 | 確認した原稿の位置 |
|---|---|---|
| ❌ クレーム32（Limits 画面で spend limit を設定） | **反映済み**。表は「組織は Console の Billing 画面、ワークスペースは各ワークスペースの設定で設定する」、本文は「Rate limits 画面では利用ティアとレート制限…利用上限（spend limit）は Billing 画面で設定します。…400エラー」 | L897・L899 |
| ⚠️ クレーム29（Haiku の小さい max_tokens） | **反映済み**。`llm_classify()` と `batch_demo.py` ともに `max_tokens=1000`、`effort: "low"`、`stop_reason` の分岐あり。理由も本文に書かれている | L468-475・L505・L985-988・L1018・L1031 |
| ⚠️ クレーム30（`canceling`） | **反映済み** | L931 |
| ⚠️ クレーム31（Default ワークスペース） | **反映済み** | L116 |

---

## ✅ 検証済み（正確）

### クレーム1
**記述**: 直接プロンプトインジェクションと間接プロンプトインジェクション（外部データに仕込まれた攻撃文）の区別。隠れた指示があるWebページを要約させる例
**検証結果**: OWASP LLM01:2025 の定義・シナリオ（隠れた指示を含むWebページの要約）と一致する。

### クレーム2
**記述**: 決定打となる対策は1つではなく、最小権限・人間の承認・入出力の検査を重ねる（多層防御）
**検証結果**: OWASP の緩和策（最小権限、特権操作への human-in-the-loop、入力の検証と出力のフィルタリング、多層防御）と一致する。

### クレーム3
**記述**: 「`request-id` は…レスポンスヘッダーやエラーボディに含まれます」「問い合わせるときは、この値を伝える」
**検証結果**: Errors「Every API response includes a unique `request-id` header」「The same identifier appears as the `request_id` field in error response bodies」「When contacting support … include this ID」。

### クレーム4
**記述**: Opus 5.5 は入力・出力 $4/$20、Haiku 5.5 は $0.10/$0.50（10万トークン以下）。入力5万・出力5千で Opus 約0.30ドル、Haiku 約0.0075ドル
**検証結果**: Pricing の表と一致（Haiku 5.5 は「for prompts up to 100,000 tokens」）。計算は 0.20+0.10＝0.30、0.005+0.0025＝0.0075 で正しい。

### クレーム5
**記述**: `effort` を `medium` から `low` に下げると、思考のトークンが減る
**検証結果**: Effort。Opus 5.5・Haiku 5.5 の既定は `medium`。`low` は「Most efficient. Significant token savings」。「Effort is the main control for how much the model thinks」（Haiku 5.5）。

### クレーム6
**記述**: キャッシュヒット率＝cache_read ÷（input＋cache_creation＋cache_read）
**検証結果**: Rate limits の `total_input_tokens = cache_read_input_tokens + cache_creation_input_tokens + input_tokens` と整合する。

### クレーム7
**記述**: `POST /v1/messages/batches` に `custom_id` と `params` の組の `requests` 配列を送る。`params` は通常の Messages API のボディと同じ
**検証結果**: Batch processing「Each request has a unique `custom_id` and contains the standard parameters you'd use for a Messages API call」。`custom_id` は `^[a-zA-Z0-9_-]{1,64}$` で、例の `review-001` は適合する。

### クレーム8
**記述**: `GET /v1/messages/batches/{id}` で `processing_status` が `in_progress` から `ended` になる。取り消すと `canceling` を経て `ended`
**検証結果**: Batch processing「It starts as `in_progress`, then updates to `ended`」「Immediately after cancellation, a batch's `processing_status` will be `canceling` … Canceled batches end up with a status of `ended`」。

### クレーム9
**記述**: 完了後に設定される `results_url` から JSONL を取得する。取得にも認証が必要
**検証結果**: 作成直後は `"results_url": null`。結果は `.jsonl`。公式の curl 例は結果の取得にも `x-api-key` と `anthropic-version` を付けている。大きい結果はストリームで取得することが推奨されており、本文の `http.stream()` の説明とも一致する。

### クレーム10
**記述**: 結果の順序は保証されないので、`custom_id` で突き合わせる
**検証結果**: 「Batch results can be returned in any order … always use the `custom_id` field」。

### クレーム11
**記述**: `request_counts` のキー（processing / succeeded / errored / canceled / expired）
**検証結果**: Batch processing の作成直後のレスポンス例と完全に一致する。

### クレーム12
**記述**: `result.type` が succeeded / errored / canceled / expired。errored＝リクエストの内容やサーバー側の問題、canceled＝取り消し、expired＝期限内に処理されなかった
**検証結果**: 結果型の表と一致（errored は「invalid requests and internal server errors」、expired は「Batch reached its 24-hour expiration」）。errored・canceled・expired は課金されない。

### クレーム13
**記述**: 料金は通常の50%
**検証結果**: 「All usage is charged at 50 percent of the standard API prices」。バッチ単価表でも Opus 5.5 は $2/$10、Haiku 5.5 は $0.05/$0.25 で、通常単価のちょうど半額。

### クレーム14
**記述**: 件数・サイズの上限、処理の期限、結果の取得期間には制約がある。取り消しのエンドポイントもある
**検証結果**: 100,000件または256MB、24時間で期限切れ、結果は作成から29日間、`POST /v1/messages/batches/{id}/cancel`。本文は数値を書かずに公式を参照させているので正確。

### クレーム15
**記述**: バッチでもプロンプトキャッシュが使え、割引と組み合わせられるが、効くかどうかは保証されない
**検証結果**: 「The pricing discounts from prompt caching and Message Batches can stack」「cache hits are provided on a best-effort basis」（30〜98%）。

### クレーム16
**記述**: バッチで構造化出力（`output_config`）をそのまま使える
**検証結果**: Structured outputs の互換性一覧「Batch processing: Process structured outputs at scale with a 50 percent discount」。Batch processing でもバッチにできないパラメータは `stream`・`speed`・`fallbacks`・`max_tokens: 0` だけで、`output_config` は対象外。

### クレーム17
**記述**: `output_config` に `effort` と `format` を併用する（`judge()`・`llm_classify()`・`batch_demo.py`）
**検証結果**: Messages API リファレンスで、`output_config` は `effort` と `format` の2つの任意フィールドを持つ兄弟関係のオブジェクト。併用できる。

### クレーム18
**記述**: スキーマで `enum` を指定すると値を限定できる。`score` は `integer`
**検証結果**: Structured outputs「`enum` (strings, numbers, booleans, or nulls only)」「All basic types: object, array, string, integer…」。`minimum`/`maximum` は非対応なので、`judge()` が範囲外の値を Python 側で丸めているのも妥当。

### クレーム19
**記述**: `stop_reason` が `refusal` や `max_tokens` のときは本文（JSON）を信用しない
**検証結果**: Structured outputs「refusal … The output might not match your schema」「max_tokens … The output might be incomplete and not match your schema」。

### クレーム20
**記述**: Haiku 5.5 は思考が既定で有効で、思考も `max_tokens` に数えられる
**検証結果**: Effort「Thinking is on by default and counts toward `max_tokens`, so leave room for it.」（Claude Haiku 5.5 の節）。

### クレーム21
**記述**: ガードレール出力例 `calls=3 input=1,152 output=147 … total=$0.0002`、1件あたり0.0001ドル未満
**検証結果**: Haiku 5.5 の単価で 1,152×$0.10/M＋147×$0.50/M＝$0.000189（表示は小数4桁で $0.0002）。1件あたり約 $0.00006。

### クレーム22
**記述**: eval の出力例 `total=$0.1042` / `$0.1050`（Opus 5.5）、平均 4.0 / 4.75
**検証結果**: 6,480×$4/M＋3,912×$20/M＝$0.10416、6,912×$4/M＋3,870×$20/M＝$0.10505。平均は (5+4+5+2)/4＝4.0、(5+4+5+5)/4＝4.75。

### クレーム23
**記述**: JSONログ例 `in=8214 out=1032 cost=$0.0535`（Opus 5.5）
**検証結果**: 8,214×$4/M＋1,032×$20/M＝$0.05350。

### クレーム24
**記述**: `asyncio` のタスクは作成時の文脈を引き継ぐ。`ThreadPoolExecutor` は引き継がず、`contextvars.copy_context().run` を使う
**検証結果**: Python の contextvars・asyncio の仕様どおり。偽APIの検証で、`asyncio.gather`・`asyncio.to_thread` のログには同じトレースIDが付き、`ThreadPoolExecutor` の中のログは `-` になることを確認した（コード検証レポートを参照）。

### クレーム25
**記述**: ロガーに付けたフィルターは子ロガーから伝播したレコードには効かず、ハンドラーに付ければ全レコードに効く
**検証結果**: logging のドキュメント（伝播したレコードには祖先ロガーのフィルターは適用されない）と一致。実行でも `llm_client` ロガーの行にトレースIDが付いた。

### クレーム26
**記述**: `basicConfig()` はルートロガーにハンドラーが1つでもあると何もしない
**検証結果**: logging のドキュメント（`force=True` を付けない場合）。

### クレーム27
**記述**: サーバーツール（Web検索など）の結果は、私たちのコードを通らずに文脈へ入る
**検証結果**: Server tools「The API runs the tool internally. You see the call and its result in the response, but you don't handle execution.」。

### クレーム28
**記述**: 設定した利用上限に達するとAPIが400エラーを返す。Default ワークスペースには利用上限を設定できない
**検証結果**: Rate limits「When usage reaches a spend limit you set, requests return HTTP 400 with error type `invalid_request_error`」「You can't set spend limits on the default workspace.」。Errors も同じ（ティアの上限なら 429）。

### クレーム29
**記述**: 利用上限は Billing 画面（組織）と各ワークスペースの設定で設定する。Rate limits 画面では利用ティアとレート制限を確認できる
**検証結果**: Rate limits「set your own limit on the Billing page」「You can see your organization's tier and current limits on the Rate limits page (`platform.claude.com/usage/limits`)」「you can set custom spend and rate limits for each workspace」。

### クレーム30
**記述**: `uv run python evals/run_eval.py` のように直接指定すると `ModuleNotFoundError: No module named 'llm_client'` になる
**検証結果**: Python の `-m` の仕様どおり。実行してもこのエラーになった。

### クレーム31
**記述**: `llm_client.tracker` はバッチの呼び出しを記録しない。結果の各 `message` の `usage` から通常単価の半額で見積もる
**検証結果**: 結果の例の `message` に `usage` が含まれる。50%割引はクレーム13のとおり。

---

## ⚠️ 要確認（古い可能性あり）

### クレーム32
**記述**: 「第6章で学んだとおり、`additionalProperties: False` と `required` は必須です」（L505）
**懸念点**: Structured outputs の対応機能一覧には「`required` and `additionalProperties` (must be set to `false` for objects)」とある。必須なのは `additionalProperties: false` で、`required` 自体は必須とは書かれていない。プロパティの順序の節には「mark all properties as required, or account for this reordering」とあり、任意プロパティも許される前提になっている。`claude-api-facts.md` も「`required` 推奨」と書いている。
**検索結果**: 上記の Structured outputs（2026-11-08 取得）。
**推奨対処**: 「第6章で学んだとおり、`additionalProperties: False` は必須です。`required` にもすべての項目を並べておくと、返ってくるJSONの形が安定します。」に直す。第6章の該当箇所も同じ表現なら合わせて確認する。

### クレーム33
**記述**: 「Console の Usage 画面ではトークン数とコストの推移を…確認できます」（L899）、図「FIG_11_6｜スクリーンショット｜手｜Claude ConsoleのUsage画面｜日別のトークン数とコストの推移グラフ」（L901）
**懸念点**: Rate limits の説明では、Usage 画面（`platform.claude.com/usage`）は「token and request charts」とレート制限のグラフ。金額は別の Cost 画面（`platform.claude.com/cost`）で、モデル別・月別の支出を見る（サポート記事 9534590）。
**検索結果**: Rate limits「In addition to providing token and request charts, the Usage page provides two separate rate limit charts」。サポート記事は Usage と Cost を別ページとして案内している。
**推奨対処**: 本文を「Console の Usage 画面ではトークン数の推移を、Cost 画面では金額の推移を、Rate limits 画面では利用ティアとレート制限を確認できます。」に直す。図は「Claude ConsoleのUsage画面とCost画面｜日別のトークン数（Usage）とモデル別の支出（Cost）」とするか、Usage 画面だけならキャプションから「コスト」を外す。撮影時に実画面で確認すること。

### クレーム34
**記述**: 「設定した上限に達するとAPIが400エラーを返すので、アプリのバグで費用が青天井になる事態を防げます」（L899）。同じ章で Message Batches API を勧めている
**懸念点**: Batch processing の制約に「Because of high throughput and concurrent processing, batches may go slightly over the spend limit configured in the Claude Console for your Workspace.」とある。バッチでは上限をわずかに超えることがある。
**推奨対処**: 11.4 の「使いどころと制約」の段落（L1070）の末尾に、「なお、バッチは大量のリクエストを並行して処理するため、Console で設定した利用上限をわずかに超えて課金されることがあります。」を1文加える。

---

## ❌ 要修正（誤りの可能性が高い）

該当なし。

---

## 総評

前回の ❌（Limits 画面の誤り）と ⚠️ 3件は、すべて原稿に正しく反映されていた。Message Batches API の記述（エンドポイント、`custom_id` と `params`、`processing_status` と `canceling`、`request_counts`、`results_url` の認証、結果型、50%割引、順序非保証、キャッシュは best-effort）は、2026-11-08 時点の公式ドキュメントとすべて一致した。出力例の金額も単価表と整合している。

今回の指摘は軽微なものだけ。`required` を「必須」とする表現（クレーム32）と、Console の画面名（Usage と Cost の区別、クレーム33）は、読者が公式ドキュメントや実画面と見比べたときに食い違いに気づく箇所なので、直しておくことを推奨する。コード側の不一致（eval の出力例の `[]`、ログ例のガードレール行）は `chapter_11_code_verify.md` を参照。

## 再チェック（2026-11-08・修正箇所）

対象: `git diff` の変更8か所。

- ✅ **L505 構造化出力のスキーマ条件**: structured-outputs の JSON Schema 制限に「`additionalProperties`（objects では `false` 必須）」とあり、`required` 外の任意プロパティも許される（任意パラメータは全体で24個まで）。第6章 L1160・L1166 の記述とも一致。
- ✅ **L730〜733 eval 出力例（v1）**: `print(f"... score={r['score']} {r.get('problems') or ''}")` を実行すると、空リストは `PASS basic-001    score=5 `（末尾は空白のみ）になる。`FAIL safety-001   score=2 ['禁止語あり:evil.example']` も桁揃えを含め一致。
- ✅ **L747〜750 eval 出力例（v2）**: 同上。
- ✅ **L867 抜粋の前置き「各ワーカーの進捗やツール実行の行も並びます」**: 第10章のロガー `report_agent.orchestrator`・`report_agent.researcher`・`report_agent.writer` の進捗、第8章 `Agent` の `[%s] tool_use:` 行（イベントループ上で出るのでトレースIDが付く）が該当する。ガードレールの行を例から外したのは、`report_agent` に第11章のガードレールを組み込む記述がないため妥当。
- ⚠️ **L871〜872 JSON ログ例**: 1行目のロガー名 `report_agent.orchestrator` とメッセージ形式は第10章 L292・L546 と一致。2行目の `cost=$0.0535` も Opus 単価（8,214×$4+1,032×$20）で正しい。ただし `write` 開始の7秒後に記録される呼び出しは、委譲の完了を待っているオーケストレーター（Opus）ではなく、ライター（`claude-sonnet-5-5`）のはず。→ 2行目を `model=claude-sonnet-5-5 ... cost=$0.0267`（8,214×$2+1,032×$10）に直す。
- ✅ **L899 Console の Usage／Cost 画面**: ヘルプ記事「Cost and usage reporting in the Claude Console」で、Usage ページはモデル・APIキー別のトークン数、Cost ページはモデル・月別の支出と日別コストのグラフ（Web検索等の料金を含む）と確認。Rate limits ページ（`/usage/limits`）と Billing での spend limit 設定・上限到達時の400も rate-limits.md と一致。
- ✅ **L901 FIG_11_6**: 上記の画面構成と一致。
- ⚠️ **L1070 バッチが利用上限をわずかに超えることがある**: batch-processing.md に「Because of high throughput and concurrent processing, batches may go slightly over the spend limit configured in the Claude Console for your Workspace.」とあり事実として正しい。ただし第2章 L114 の「上限に達すると…それ以上の料金は発生しません」と断定がぶつかる。→ 第2章 L114 に「（Message Batches API では、わずかに超えることがあります。第11章参照）」を補う。また追記文は約60字なので、「なお、バッチは大量のリクエストを並行して処理します。そのため、Console の利用上限をわずかに超えて課金されることがあります。」と2文に分けると読みやすい。
