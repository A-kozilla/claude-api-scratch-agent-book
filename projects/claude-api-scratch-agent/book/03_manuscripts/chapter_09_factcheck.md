# ファクトチェックレポート

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_09.md
検証日: 2026-11-07
検証クレーム数: 24件
  ✅ 検証済み: 21件
  ⚠️ 要確認: 3件
  ❌ 要修正: 0件

参照した一次情報:
- Building effective agents: https://www.anthropic.com/engineering/building-effective-agents
- Structured outputs: https://platform.claude.com/docs/en/build-with-claude/structured-outputs.md
- 2026-10-21 移行ガイド: https://platform.claude.com/docs/en/api/migration-2026-10-21.md
- Prompt caching / Thinking / Effort / Pricing / Models overview（第7章のチェックで取得済みの内容を再利用）

---

## ✅ 検証済み（正確）

### 1. 単純で組み合わせやすい部品から作られている（L36）
**検証結果**: 記事「the most successful implementations weren't using complex frameworks or specialized libraries」。シンプルで組み合わせやすいパターンを使っていたと述べている。

### 2. 必要になるまで複雑にしない（L35, L159-161, L1454）
**検証結果**: 記事「finding the simplest solution possible, and only increasing complexity when needed」。

### 3. 拡張されたLLM（augmented LLM）が基本部品（L61-62）
**検証結果**: 記事「The basic building block of agentic systems is an LLM enhanced with augmentations such as retrieval, tools, and memory」。

### 4. ワークフローとエージェントの区別（L64-75, L97-99）
**検証結果**: 記事は workflows を「orchestrated through predefined code paths」、agents を「dynamically direct their own processes and tool usage」と定義している。本書の「流れを決めるのはコードかモデルか」という基準と一致。

### 5. ワークフローの代表パターンは5つ（L174-175, L1481）
**検証結果**: 記事は Prompt chaining、Routing、Parallelization、Orchestrator-workers、Evaluator-optimizer の5つを挙げ、Agents は別に扱っている。「5つ＋自律エージェント＝6つ」は正確。

### 6. プロンプトチェーンとゲート、正確さとの交換（L179-180, L330-335）
**検証結果**: 記事は中間段階に programmatic checks（図中の "gate"）を置けるとし、トレードオフを「trade off latency for higher accuracy」としている。

### 7. ルーティング（L183-184, L604）
**検証結果**: 記事の例は、カスタマーサービスの問い合わせを種類別の下流処理へ振り分けることと、簡単な質問を Claude Haiku のような小さいモデルへ回すこと。本書の説明と一致。

### 8. 並列化の2種類（L187-188, L814-821）
**検証結果**: 記事「Sectioning: Breaking a task into independent subtasks run in parallel」「Voting: Running the same task multiple times to get diverse outputs」。

### 9. 評価者-最適化者と向く条件（L191-192, L1132-1136）
**検証結果**: 記事は、明確な評価基準があり反復で効果が出るときに向くとし、目安を2つ挙げている。人間のフィードバックで応答が明確に改善すること、LLM もそのフィードバックを出せること。本書の2条件と対応している。

### 10. オーケストレーター-ワーカーと並列化の違い（L195-196, L1360-1363）
**検証結果**: 記事「subtasks aren't pre-defined, but determined by the orchestrator based on the specific input」。

### 11. 自律エージェントと、コーディングを代表例とすること（L153-154, L199）
**検証結果**: 記事は、エージェントを必要な手順数を予測しにくい open-ended な問題向けとし、SWE-bench を解くコーディングエージェントを例に挙げている。

### 12. 構造化出力のリクエスト形（L249, L265-268）
**検証結果**: Structured outputs「output_config.format」に `{"type": "json_schema", "schema": {...}}`。

### 13. JSON はテキストブロックに入る（L250, L281）
**検証結果**: 「The JSON is in the response's text content block … There is no separate JSON field in the raw API response」。

### 14. refusal・max_tokens では JSON がスキーマどおりとは限らない（L274-279, L312）
**検証結果**: refusal「The output may not match your schema」、max_tokens「The output may be incomplete and may not match the schema」。

### 15. additionalProperties: false と required（L377, L406, L942）
**検証結果**: 「additionalProperties … must be set to false for objects」。入れ子のオブジェクトにも必要という本書の説明と一致。

### 16. enum でカテゴリーを固定できる（L610, L661-662）
**検証結果**: 「enum (strings, numbers, booleans, or nulls only; no complex types)」は対応キーワード。

### 17. 範囲（1〜5）はスキーマで制約していない（L1255, L1291）
**検証結果**: 「Numerical constraints: minimum, maximum, multipleOf」は非対応。コード側で丸める設計は仕様と整合している。

### 18. temperature・top_p・top_k は400（L831）
**検証結果**: 移行ガイド「In 2026-10-21, a request that sends temperature, top_p, or top_k returns a 400 error, even at the parameter's default value.」

### 19. Opus 5.5 は adaptive thinking 常時有効、thinking は出力トークンを使う（L308, L312, L477）
**検証結果**: Models overview「Adaptive (always on)」。Thinking「count toward max_tokens alongside the response text」。

### 20. キャッシュは前方一致、最小長未満は作られない（L1107-1110）
**検証結果**: Prompt caching の前方一致（tools→system→messages）と最小長（Opus 5.5・Haiku 5.5 は512）の記述と一致。

### 21. 誤りの掛け算（L1467）
**記述**: 「各段階の成功率が95%でも、5段階をつなぐと全体の成功率は約77%」
**検証結果**: 0.95^5＝0.7738。計算は正確。

---

## ⚠️ 要確認（補足推奨）

### 1. 構造化出力の制約の書き方（L418 NOTE）
**記述**: 「JSON Schemaには`minItems`や`maxLength`などの制約もありますが、構造化出力でサポートされる制約には制限があります。」
**懸念点**: 誤りではないが、具体性に欠ける。公式では `minItems` は0と1のみ対応し、`maxItems`・`minLength`・`maxLength`・`minimum`・`maximum` は非対応。非対応のキーワードを raw API に送ると、無視されるのではなく **400エラー** になる。読者がスキーマに `minItems: 2` を書いて400で詰まるおそれがある。
**検索結果**: Structured outputs「Array minItems, only values 0 and 1」「Not supported: minimum, maximum, multipleOf / minLength, maxLength」「Unsupported features on the raw API return a 400 error」。
**修正案**: 「JSON Schemaには`minItems`や`maxLength`などの制約もありますが、構造化出力では`minItems`は0か1しか使えず、`maxLength`や`minimum`などは非対応で、送ると400エラーになります。細かな条件はスキーマに頼らず、ゲートでコードとして検査しましょう。」

### 2. 並列で同時に送るとキャッシュを読めないことがある（L1112 NOTE）
**懸念点**: 内容は妥当で、Prompt caching の FAQ にも「batch requests can be processed concurrently … cache hits are provided on a best-effort basis」とある。ただし、通常のリクエストを同時に送ったときの挙動（最初の応答が始まってからキャッシュが使える、など）を明記した一次情報の記述は、今回取得した範囲では見つからなかった。
**推奨対処**: 現状の「読めないことがあります」という断定しない表現で問題ない。出典を示すなら、Prompt caching ページで該当の記述を確認してから引用する。

### 3. 実行例のキャッシュ値（L573, L769, L1077, L1322）
**懸念点**: 本章の `patterns/` は `cache_control` を付けずに `call_messages()`／`acall_messages()` を呼んでいるため、`cache_write=0 cache_read=0` は整合している。一方、L1107 の「第7章のプロンプトキャッシュも効きます」は、`cache_control`（`extra` のトップレベル指定など）を追加した場合の話である。
**推奨対処**: L1107 を「…`extra={"cache_control": {"type": "ephemeral"}}`を足せば、第7章のプロンプトキャッシュも効かせられます」とし、追加の設定が必要なことを明示する。

---

## ❌ 要修正

該当なし。

---

## 総評

「Building effective agents」のパターン分類と各パターンの説明は、記事の内容と正確に対応しています。5つのワークフローと自律エージェント、ゲート、セクショニングと投票、オーケストレーター-ワーカーと並列化の違い、評価者-最適化者の適用条件のいずれも一致しました。
temperature 等が使えない点と構造化出力の基本仕様も、一次情報と一致しています。
要対応は、L418 NOTE を具体化することです。`minItems` は0か1のみ、`maxLength` などは非対応で、送ると400エラーになります。読者のつまずき防止のため、修正案の反映を推奨します。
4つの判断基準（複雑さ・価値・実現性・失敗時のコスト）は「本書では」と明示した独自の整理で、記事の主張としては書かれていないため問題ありません。

---

## 対応（2026-11-07）

| ⚠️ | 対応 | 原稿の位置（対応後） |
|---|---|---|
| 1. 構造化出力の制約 | NOTE を「構造化出力では`minItems`は0か1しか使えません。`maxItems`・`minLength`・`maxLength`・`minimum`・`maximum`は非対応で、送ると400エラーになります。」と具体化。ゲートでコード検査する方針はそのまま。本章のスキーマ（本文・検証用 `patterns/`）にこれらのキーワードが含まれていないことを grep で確認（個数の条件は既に `gate_facts()` などのコードで検査している） | L418 |
| 2. 並列送信とキャッシュ | 現状の表現で問題ないため変更なし | — |
| 3. 「プロンプトキャッシュも効きます」 | 「効かせられます」に改め、「本章の`patterns/`は`cache_control`を付けていないので、効かせるには第7章の`cached_system()`やトップレベルの`cache_control`などの設定を足す必要があります」を1文追加。コードは変更しない（実行例の `cache_write=0 cache_read=0` と整合） | L1107-1108 |

コードの変更はないが、`scratchpad/verify/fix_ch07_09_11/proj2/` で偽APIにより `python -m patterns.chain|router|parallel|evaluator_optimizer` を再実行し、従来どおり動作することを確認（chain は偽APIの固定応答のため抽出ゲートで停止する。従来の検証と同じ挙動）。
