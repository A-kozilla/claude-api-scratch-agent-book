# ファクトチェックレポート

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_01.md
検証日: 2026-11-08
検証クレーム数: 24件
  ✅ 検証済み: 21件
  ⚠️ 要確認: 3件
  ❌ 要修正: 0件

主な一次情報（取得日 2026-11-08）:
- Models overview / Pricing / Token counting（https://platform.claude.com/docs/en/build-with-claude/token-counting.md）
- Thinking（https://platform.claude.com/docs/en/build-with-claude/thinking.md）
- Handling stop reasons（https://platform.claude.com/docs/en/build-with-claude/handling-stop-reasons.md）
- Messages API リファレンス（https://platform.claude.com/docs/en/api/messages.md）/ Errors / Versioning
- ReAct 論文: https://arxiv.org/abs/2210.03629
- Building effective agents: https://www.anthropic.com/engineering/building-effective-agents
- 章間参照: chapter_05.md（COLUMN「よくあるつまずきポイントTOP3」L1174〜）、chapter_06.md（サーバーツール L166〜）、chapter_08.md（モデルの使い分け L124）

## 前回（2026-11-07）指摘の反映状況

| 前回 | 内容 | 状況 |
|---|---|---|
| ❌21 | 「20倍以上」→「20倍近い」 | ✅ 反映済み（L397）。計算も再確認し正しい（下記クレーム19） |
| ⚠️19 | 表の「1回だけ呼ぶ」3,500 と10往復の初回2,000の前提不一致 | ❌ 未反映 → 下記⚠️クレーム22に継続 |
| ⚠️20 | 終わり方4種に `model_context_window_exceeded` 等がない | ❌ 未反映 → 下記⚠️クレーム23に継続 |

---

## ✅ 検証済み（正確）

### クレーム1
**記述**: 「`/v1/messages/count_tokens`というエンドポイントがあります」（L53）
**検証結果**: Token counting「Token counting is **free to use**」「The token count is an **estimate**」、エンドポイント `/v1/messages/count_tokens`。

### クレーム2
**記述**: 「実際に送ったリクエストのトークン数は、レスポンスの`usage`という項目に毎回記録」（L53）
**検証結果**: Messages API の `usage`（input_tokens / output_tokens / cache_creation_input_tokens / cache_read_input_tokens ほか）。

### クレーム3
**記述**: 「文章は`text`ブロック、道具を使いたいという要求は`tool_use`ブロック」（L75）
**検証結果**: Messages API の content block 型で確認。

### クレーム4
**記述**: 「道具の名前・説明・引数の形をJSON Schemaで定義して」（L83）
**検証結果**: Token counting のツール例・Tool use 概要で `name`／`description`／`input_schema`（JSON Schema）。

### クレーム5
**記述**: 「Claudeはツールを実行しません」「サーバーツールという種類のツールも用意」「第6章で…紹介」（L89・L96）
**検証結果**: クライアントツールはアプリ側で実行し `tool_result` を返す。web search / web fetch はサーバーツール。chapter_06.md L166「サーバーツール: Anthropic側で実行されるツール」で使い分けを扱っている（第5章 L149 でも概要紹介あり）。

### クレーム6
**記述**: 「`stop_reason`が`"tool_use"`ならツールを実行…`"end_turn"`なら…ループを抜けて」（L106）
**検証結果**: Handling stop reasons の `end_turn`／`tool_use` の定義と一致。

### クレーム7
**記述**: 「並列ツール呼び出し…Claude APIでは既定で有効」（L306）
**検証結果**: Messages API「`disable_parallel_tool_use` … defaults to `false`」。

### クレーム8
**記述**: 「`claude-opus-5-5`では、この思考が常に有効」「`effort`という設定で調整」「`thinking`ブロックとして含まれることがあり」（L308）
**検証結果**: Models overview「Thinking: Adaptive (always on)」「Default effort: `medium`」。Errors「Thinking cannot be disabled … Claude Opus 5.5」。

### クレーム9
**記述**: 「上限に達すると、`stop_reason`は`max_tokens`」「拒否…`refusal`」（L320・L322）
**検証結果**: Handling stop reasons の列挙で確認。`refusal` 時は `stop_details` にカテゴリが入る。

### クレーム10
**記述**: 「Claude APIは**ステートレス**です」（L330）
**検証結果**: Messages API は毎回 `messages` に過去のターンを渡す設計。

### クレーム11
**記述**: 「`toolu_01A`という同じIDで結び付けて読み取ります」（L356）
**検証結果**: `tool_result.tool_use_id` が `tool_use.id` に対応。偽APIでも ID 不一致を 400 にして検証（コード検証レポート参照）。

### クレーム12
**記述**: 「`anthropic-version: 2026-10-21`というヘッダーで…バージョンを指定」（L358）
**検証結果**: Migration「set the `anthropic-version` header to `2026-10-21`」。

### クレーム13
**記述**: 「最大100万（1M）トークンのコンテキストウィンドウ」「最大12万8,000（128K）トークン」（L383）
**検証結果**: Models overview: Opus/Sonnet/Haiku 5.5 とも Context window 1M、Max output 128K（同期 Messages API）。

### クレーム14
**記述**: 「`claude-opus-5-5`の料金は、入力100万トークンあたり4ドル、出力…20ドル」（L395）
**検証結果**: Pricing と一致。

### クレーム15
**記述**: 「ReActは、2022年に発表された論文「ReAct: Synergizing Reasoning and Acting in Language Models」」（L294）
**検証結果**: arXiv 2210.03629、v1 は 2022-10-06（Yao ほか）。

### クレーム16
**記述**: 「Building effective agents」でエージェンティックシステムをワークフローとエージェントに分ける／「まずは最も単純な方法から」（L171・L185）
**検証結果**: 同記事「Workflows are systems where LLMs and tools are orchestrated through predefined code paths」「Agents … dynamically direct their own processes and tool usage」「finding the simplest solution possible, and only increasing complexity when needed」。

### クレーム17
**記述**: 「すべての`tool_result`を1つのメッセージにまとめて返すのがルール」「`response["content"]`は、手を加えずにそのまま履歴へ」（L161）
**検証結果**: Errors「Thinking blocks cannot be modified … pass back every `thinking` and `redacted_thinking` block … exactly as received」。

### クレーム18
**記述**: 「より安いモデルとして`claude-haiku-5-5`や`claude-sonnet-5-5`」「第8章で扱います」（L406）
**検証結果**: Pricing（Sonnet 5.5 $2/$10、Haiku 5.5 $0.10/$0.50〜）。chapter_08.md L124「モデルの使い分け」で確認。

### クレーム19
**記述**: 10往復で入力8万7,500トークン・入力約0.35ドル・合計約0.45ドル、「1回だけ…約0.02ドル…20倍近い差」（L397〜402）
**検証結果**: Σ(2,000+1,500k, k=0..9)=87,500。87,500×$4/1M=$0.35、5,000×$20/1M=$0.10、計$0.45。1回（3,500/500）は $0.014+$0.010=$0.024、比は約18.8倍で「20倍近い」は正しい（前回❌の修正を確認）。

### クレーム20
**記述**: 「1日に1,000件…450ドル近く」「往復の回数が2倍になれば…コストは2倍以上」（L404）
**検証結果**: $0.45×1,000=$450。20往復は入力 Σ(2,000+1,500k, k=0..19)=325,000（$1.30）＋出力10,000（$0.20）=$1.50 で、10往復の約3.3倍。記述どおり。

### クレーム21
**記述**: 「「入力として送るもの」と「出力として返ってくるもの」の合計が、コンテキストウィンドウに収まらなければなりません」（L381）
**検証結果**: Thinking「Thinking and the context window」: 入力＋`max_tokens` が窓を超えるリクエスト自体は受け付けられるが、生成が窓の上限に達すると `model_context_window_exceeded` で停止する。概念説明として正しい（停止理由の扱いは⚠️クレーム23で補足推奨）。

---

## ⚠️ 要確認（古い可能性あり）

### クレーム22
**記述**: 表「1回だけ呼ぶ: 入力 3,500」と本文「1回目は2,000トークン」（L397〜402）
**懸念点**: 10往復側の初回が2,000トークンなのに、1回だけ呼ぶ側が3,500で前提がそろっていない。読者が再計算すると混乱する（前回⚠️19・未反映）。
**検索結果**: 計算上、1回だけ側を2,000にすると $0.008+$0.010=$0.018、比は25倍。
**推奨対処**: 表の直前に前提を一文追加する。
修正案: 「なお「1回だけ呼ぶ」場合は、systemプロンプトとツール定義に依頼文と1往復分の内容を加えた3,500トークンを送ると仮定しています。」

### クレーム23
**記述**: 「ループの終わり方を次の4種類に整理して扱います」（L316〜324）
**懸念点**: `stop_reason` には `stop_sequence`・`pause_turn`・`model_context_window_exceeded` もある。特に `model_context_window_exceeded`（応答がコンテキストウィンドウを埋めて停止）は長いエージェントループで起こり得て、`max_tokens` と同じく「途中で切れた」扱いが必要（前回⚠️20・未反映）。
**検索結果**: Handling stop reasons「`model_context_window_exceeded`: The response filled the model's context window」— quick reference は truncated として扱うよう指示。
**推奨対処**: 2つ目の段落末尾に追記。
修正案: 「履歴が長くなってコンテキストウィンドウが埋まった場合も、`stop_reason`が`model_context_window_exceeded`になり、同じく回答は途中で切れています。」

### クレーム24
**記述**: 「ツールの結果を履歴に追加し忘れると、Claudeは「まだ天気を調べていない」と判断し、同じツールを何度も呼び続けることがあります。第5章のコラムで紹介する「よくあるつまずき」の第1位は、まさにこの履歴の追加漏れです。」（L369）
**懸念点**: 第5章 COLUMN（L1179）の第1位は「**assistant の応答**を履歴に追加し忘れる」で、症状は「2回目の呼び出しで 400 エラー」。第1章の説明（tool_result の追加漏れ→同じツールの呼び直し）とずれている。「同じツールを呼び直す」のは assistant の応答も tool_result も両方とも履歴に入れなかった場合で、片方だけ欠けると第5章の記述どおりエラーになりやすい（tool_use と tool_result の対応はAPIが検証する。公式ドキュメント上の正確なエラー文言は未確認）。
**検索結果**: chapter_05.md L1179〜1183。
**推奨対処**: 第5章と症状をそろえる。
修正案: 「Claudeの返答やツールの結果を履歴に追加し忘れると、APIがエラーを返したり、Claudeが「まだ天気を調べていない」と判断して同じツールを呼び直したりします。第5章のコラムで紹介する「よくあるつまずき」の第1位も、この履歴の追加漏れです。」

---

## ❌ 要修正（誤りの可能性が高い）

該当なし（前回❌21は修正済みを確認）。

---

## 総評

概念章のため API 仕様の主張は少ないが、モデル仕様・stop_reason・並列ツール・thinking・料金・コスト試算はすべて一次情報・再計算と一致した。前回の⚠️2件（表の前提、`model_context_window_exceeded`）が未反映のまま残っている。新たに、第5章コラムへの参照でつまずきの症状が食い違う点を⚠️とした。いずれも1文の追記・差し替えで解消できる。

## 再チェック（2026-11-08・修正箇所）

対象: `git diff` の変更3か所。結果: ✅2 / ⚠️1 / ❌0

- ⚠️ L320 `model_context_window_exceeded` の追記。値自体は正しい（handling-stop-reasons: "The response filled the model's context window"／"Treat the response as truncated"、Sonnet 4.5以降はベータヘッダー不要）。ただし発生条件は「生成中に窓の上限に達した」場合で、入力だけで窓を超えると400になる。また1文が約70字。
  修正案:「履歴が長く、出力の途中でコンテキストウィンドウの上限に達した場合は、`stop_reason`が`model_context_window_exceeded`になります。この場合も回答は途中で切れています。」
- ✅ L369 WARNING「Claudeの返答やツールの結果を…APIがエラーを返したり…呼び直したり」。第5章コラム第1位（assistant の content 追加漏れ → 400「tool_use が見つからない」）と症状が一致し、前回の食い違いは解消。
- ✅ L397「1回だけ呼ぶ」の前提追記。検算（Opus 5.5 $4/$20）: 3,500×4/1M＋500×20/1M＝$0.024≒約0.02ドル、10往復は入力87,500→$0.35＋出力5,000→$0.10＝$0.45、比は約19倍で「20倍近い」と整合。表（3,500／500）とも一致。※1文が約65字とやや長い（任意で2文に分割）。
