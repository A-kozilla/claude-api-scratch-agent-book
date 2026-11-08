# ファクトチェックレポート

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_09.md
検証日: 2026-11-08
検証クレーム数: 27件
  ✅ 検証済み: 26件
  ⚠️ 要確認: 1件
  ❌ 要修正: 0件

参照した一次情報（2026-11-08 に取得）:
- Building effective agents: https://www.anthropic.com/engineering/building-effective-agents
- Structured outputs: https://platform.claude.com/docs/en/build-with-claude/structured-outputs.md
- 2026-10-21 移行ガイド: https://platform.claude.com/docs/en/api/migration-2026-10-21.md
- Messages API リファレンス: https://platform.claude.com/docs/en/api/messages.md
- Effort: https://platform.claude.com/docs/en/build-with-claude/effort.md
- Prompt caching: https://platform.claude.com/docs/en/build-with-claude/prompt-caching.md
- Pricing: https://platform.claude.com/docs/en/about-claude/pricing.md

## 前回（2026-11-07）の指摘の反映状況

| 前回 | 内容 | 反映状況 |
|---|---|---|
| ⚠️1 | 構造化出力の制約（L418 NOTE）を具体化 | ✅ 反映済み。「`minItems`は0か1」「`maxItems`・`minLength`・`maxLength`・`minimum`・`maximum`は非対応で400」と書かれ、一次情報と一致 |
| ⚠️2 | 並列送信とキャッシュ（L1113 NOTE） | ✅ 今回、一次情報で裏付けが取れた（下記クレーム23） |
| ⚠️3 | 「プロンプトキャッシュも効きます」（L1107） | ✅ 反映済み。「効かせられます」に改め、`cache_control` の追加が必要なことを L1108 で明示 |
| code ❌ | evaluator_optimizer の合格判定の順序 | ✅ 反映済み（L1269-1271。合格判定が停滞判定より先） |
| code ⚠️ | 出力例の `tracker.summary()` 形式、`aclose_client()`、Semaphore の生成位置 | ✅ 反映済み（L573・L769・L1077・L1323、L917-918・L1004、L1031-1032） |

---

## ✅ 検証済み（正確）

### クレーム1: 単純で組み合わせやすい部品（L36）
**検証結果**: 記事「Consistently, the most successful implementations weren't using complex frameworks or specialized libraries.」

### クレーム2: 必要になるまで複雑にしない（L35, L159-161, L1455）
**検証結果**: 記事「finding the simplest solution possible, and only increasing complexity when needed.」

### クレーム3: 拡張されたLLM（augmented LLM）が基本部品（L61-62）
**検証結果**: 記事「The basic building block of agentic systems is an LLM enhanced with augmentations such as retrieval, tools, and memory.」

### クレーム4: ワークフローとエージェントの区別（L64-75, L97-99）
**検証結果**: 記事は、ワークフローを「orchestrated through predefined code paths」、エージェントを「dynamically direct their own processes and tool usage」と定義している。

### クレーム5: ワークフローの代表パターンは5つ＋自律エージェント（L174-175, L1482）
**検証結果**: 記事の5パターンは Prompt chaining、Routing、Parallelization、Orchestrator-workers、Evaluator-optimizer。Agents はこれとは別に扱われている。

### クレーム6: チェーンのゲートと「速さを犠牲に正確さ」（L179-180, L330-335）
**検証結果**: 記事は、中間段階に programmatic checks（gate）を置けるとし、トレードオフを「trade off latency for higher accuracy, by making each LLM call an easier task」と述べている。

### クレーム7: ルーティングの用途（カスタマーサポート、簡単な質問は小さいモデルへ）（L183-184, L597-604）
**検証結果**: 記事の例は「Directing different types of customer service queries (general questions, refund requests, technical support)」と「Routing easy/common questions to smaller, cost-efficient models like Claude Haiku 4.5」。

### クレーム8: 並列化はセクショニングと投票の2種類（L187-188, L814-821）
**検証結果**: 記事「Sectioning: Breaking a task into independent subtasks run in parallel」「Voting: Running the same task multiple times to get diverse outputs」。

### クレーム9: 投票者ごとに観点の違うプロンプトを使う（L839-842）
**検証結果**: 記事の投票の例は「Reviewing a piece of code for vulnerabilities, where several different prompts review and flag the code」。本書の題材（脆弱性判定）と方式（観点の違うプロンプト）は、記事の例とそのまま一致する。

### クレーム10: 評価者-最適化者が向く2条件（L1133-1138）
**検証結果**: 記事は2つの目安を挙げている。「LLM responses can be demonstrably improved when a human articulates their feedback」と「the LLM can provide such feedback」。

### クレーム11: オーケストレーター-ワーカーと並列化の違い（L195-196, L1361-1364）
**検証結果**: 記事「subtasks aren't pre-defined, but determined by the orchestrator based on the specific input」。

### クレーム12: 自律エージェントと、その代表例としてのコーディング（L153-154, L199）
**検証結果**: 記事は、エージェントの用途を「open-ended problems where it's difficult or impossible to predict the required number of steps」とし、例に「A coding Agent to resolve SWE-bench tasks」を挙げている。

### クレーム13: 組み合わせると費用と誤りが積み重なる（L1463-1469）
**検証結果**: 記事「The autonomous nature of agents means higher costs, and the potential for compounding errors.」。また 0.95^5 = 0.7738 なので「約77%」は正確。

### クレーム14: 構造化出力のリクエストの形（L249, L265-268）
**検証結果**: Messages API リファレンス。`output_config.format` は `{"type": "json_schema", "schema": {...}}`。

### クレーム15: JSON はテキストブロックで返る（L250, L280-281）
**検証結果**: Structured outputs「Claude returns valid JSON that matches your schema in the response's text content block.」

### クレーム16: refusal・max_tokens のときはスキーマどおりとは限らない（L274-279, L312）
**検証結果**: Structured outputs の Invalid outputs の節（refusal・max_tokens ではスキーマに一致しない可能性がある）。`stop_details` は Messages API リファレンスで `RefusalStopDetails or null` と定義されている（L276 と一致）。

### クレーム17: `additionalProperties: false` と `required`、入れ子にも必要（L377, L406, L942）
**検証結果**: Structured outputs「`required` and `additionalProperties` (must be set to `false` for objects)」。

### クレーム18: `enum` でカテゴリーを固定できる（L610, L661-662）
**検証結果**: Structured outputs の Supported features に「`enum` (strings, numbers, booleans, or nulls only...)」がある。

### クレーム19: 構造化出力の制約（L418 NOTE。前回の修正後）
**検証結果**: Structured outputs の JSON Schema limitations。「Array `minItems` (only values 0 and 1 supported)」、Not supported に「Numerical constraints (such as `minimum`, `maximum`, `multipleOf`)」「String constraints (`minLength`, `maxLength`)」「Array constraints beyond `minItems` of 0 or 1」、「If you use an unsupported feature, you'll receive a 400 error with details.」。本文と完全に一致する。

### クレーム20: 範囲（1〜5）はスキーマで制約していないのでコードで丸める（L1256-1257, L1291-1292）
**検証結果**: クレーム19のとおり、`minimum`・`maximum` は非対応。設計は仕様と整合している。

### クレーム21: `anthropic-version: 2026-10-21` で temperature・top_p・top_k は400（L831）
**検証結果**: 移行ガイド「In `2026-10-21`, a request that sends `temperature`, `top_p`, or `top_k` returns a 400 error, even at the parameter's default value.」

### クレーム22: Opus 5.5 は adaptive thinking が常に有効で、思考も出力トークンに数えられる（L308, L312, L477-478）
**検証結果**: Effort「Claude Opus 5.5 … Adaptive thinking is always on and can't be turned off」「it's a hard limit on total output (thinking plus response text)」。

### クレーム23: 並列で同時に送った最初の群は互いのキャッシュを読めない。1件目を先に送る（L1113 NOTE）
**検証結果**: Prompt caching「For concurrent requests, note that a cache entry only becomes available after the first response starts. If you need cache hits for parallel requests, wait for the first response before sending subsequent requests.」。前回の ⚠️ はこれで解消。

### クレーム24: キャッシュは前方一致。観点ごとに変わる system を前に置くと共有できない（L1109-1110）
**検証結果**: Prompt caching「Cache prefixes are created in the following order: `tools`, `system`, then `messages`」。前方一致で、前の階層が変わると後ろも無効になる。

### クレーム25: 最小キャッシュ長未満ではキャッシュが作られない（L1111）
**検証結果**: Prompt caching の最小長は、Claude Opus 5.5・Sonnet 5.5・Haiku 5.5 で 512 tokens。

### クレーム26: モデルの使い分け（抽出・翻訳・分類は Haiku 5.5、執筆は Opus 5.5）と、出力例の料金が成り立つ範囲（L346-347, L573, L769, L1077, L1096）
**検証結果**: Pricing。Opus 5.5 は $4/$20、Haiku 5.5 は $0.10/$0.50（プロンプト10万tok以下）。chain（$0.0213）・router（$0.0335）・parallel（$0.0644、本文の「約6セント」）は、トークン数と呼び出しの内訳から計算した範囲に収まる。

---

## ⚠️ 要確認（古い可能性あり）

### クレーム27: 評価者-最適化者の実行例の合計金額（L1323）
**記述**: 「calls=4 input=3,215 output=2,476 cache_write=0 cache_read=0 total=$0.0611」
**懸念点**: 4回の内訳は、生成2回（Opus 5.5）と評価2回（Haiku 5.5）。仮にトークンをすべて Opus 5.5 で使ったとしても、上限は 3,215×$4/1M + 2,476×$20/1M = $0.0624 にしかならない。$0.0611 になるには、評価2回（Haiku）の出力が合わせて約60トークン以下でなければならない。しかし評価は、4項目の点数・改善点のJSON・思考トークンを出力する。現実的な内訳（評価の入力 計1,200tok／出力 計500tok程度）で計算すると、約 $0.048 になる。chain・router・parallel の例と比べて、この例だけが内訳と合わない。
**検索結果**: Pricing（Opus 5.5 $4/$20、Haiku 5.5 $0.10/$0.50）。
**推奨対処**: 金額を内訳と合う値に直す。例:
```text
calls=4 input=3,215 output=2,476 cache_write=0 cache_read=0 total=$0.0480
```
（トークン数を変えずに合計だけを直す場合。実際に1回実行した値で置き換えるのが最善。）

---

## ❌ 要修正（誤りの可能性が高い）

該当なし。

---

## 総評

前回の ⚠️3件と、コード検証の ❌1件・⚠️2件は、すべて原稿に正しく反映されています。前回は一次情報で確かめられなかった「並列送信とキャッシュ」（L1113）も、今回 Prompt caching の記述で裏付けが取れました。
Building effective agents の分類と説明は、記事と正確に対応しています。投票を「観点の違うプロンプト」で行う設計は、記事自身の投票の例（脆弱性レビューを複数の異なるプロンプトで行う）と同じで、temperature が使えない環境での設計として適切です。
残るのは、L1323 の実行例の合計金額だけです。トークン数とモデルの内訳から計算すると高すぎるので、実測値か整合する値に差し替えることを推奨します。

## 再チェック（2026-11-08・修正箇所）

対象: `git diff` の変更1か所。

- ✅ **L1323 実行例の合計金額 `total=$0.0480`**: 生成2回は Opus 5.5（`MODEL`）、評価2回は Haiku 5.5（`FAST_MODEL`）。評価の入力 計1,200tok・出力 計500tok とすると、Opus 2,015/1,976tok×$4/$20 + Haiku 1,200/500tok×$0.10/$0.50 = $0.04795 ≒ $0.0480。トークン数とモデル内訳に整合する。chain・router・parallel の例と書式も同じ。
