# ファクトチェックレポート

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_07.md
検証日: 2026-11-08
検証クレーム数: 37件
  ✅ 検証済み: 31件
  ⚠️ 要確認: 5件
  ❌ 要修正: 1件

参照した一次情報（2026-11-08 に WebFetch で取得）:
- Token counting: https://platform.claude.com/docs/en/build-with-claude/token-counting.md
- Prompt caching: https://platform.claude.com/docs/en/build-with-claude/prompt-caching.md
- Thinking: https://platform.claude.com/docs/en/build-with-claude/thinking.md
- Steering thinking（adaptive-thinking のリダイレクト先）: https://platform.claude.com/docs/en/build-with-claude/thinking-steering-and-cost
- Effort: https://platform.claude.com/docs/en/build-with-claude/effort.md
- Pricing: https://platform.claude.com/docs/en/about-claude/pricing.md
- Models overview: https://platform.claude.com/docs/en/about-claude/models/overview.md（models/overview へリダイレクト）

## 前回（2026-11-07）指摘の反映状況

| 前回の指摘 | 状況 |
|---|---|
| ⚠️1 effort 変更とキャッシュ（L1125, L1386-1387） | ✅ 反映済み。「トップレベルのeffort」「モデルによってはtools・systemも」「既定値の明示は省略と同じ」がいずれも入り、Prompt caching／Steering thinking の記述と一致 |
| ⚠️2 Haiku 5.5 の100K超料金（L612） | ✅ 反映済み。「入力10万トークン以下の場合。超えると単価が上がります」 |
| ⚠️3 count_tokens と assistant 終わり（L831） | 未対応 → 今回も ⚠️-2 |
| ⚠️4 count_tokens は空の messages 不可（L240） | 未対応 → 今回も ⚠️-3 |
| ⚠️5 空の tools 配列で検証エラー（L153） | 未対応 → 今回も ⚠️-4 |
| ⚠️6 7.4節の cache_write=1,920 の不整合（L1307） | 未対応 → 今回も ⚠️-5 |
| 総評の signature の補足（L1351） | 未対応 → 今回 ⚠️-1 として計上 |

---

## ✅ 検証済み（正確）

### 1. コンテキストと最大出力（L40）
**記述**: 「`claude-opus-5-5`のコンテキストは100万トークン（1M）、最大出力は128Kトークン」
**検証結果**: Models overview の表で Claude Opus 5.5 は Context window 1M tokens／Max output 128K tokens。

### 2. 新しい世代のモデルはトークン数が多め（L51）
**検証結果**: Token counting「Claude 4.7 and later models … use a newer tokenizer. The same input text produces approximately 30 percent more tokens than on earlier models」。

### 3. エンドポイント（L80, L143, L158）
**検証結果**: Token counting の curl 例と「Applicable endpoints: `/v1/messages/count_tokens`」で一致。

### 4. 渡せるフィールドとレスポンス形（L81-82, L104）
**検証結果**: 「accepts the same structured list of inputs for creating a message, including support for system prompts, tools, images, and PDFs」。出力例は `{ "input_tokens": 14 }` の形。

### 5. max_tokens は不要（L108）
**検証結果**: 公式の curl 例はいずれも `max_tokens` なしで呼んでいる。

### 6. 無料・別枠のレート制限（L110-111, L159, L362）
**検証結果**: 「Token counting is free to use but subject to requests per minute rate limits」「Token counting and message creation have separate and independent rate limits」。

### 7. 見積もり値（L112-113）
**検証結果**: 「The token count is an estimate. … might differ by a small amount.」。さらに「Token counts might include tokens added automatically by Anthropic for system optimizations」とあり、L241 の「内部で付与される固定のオーバーヘッド」とも整合。

### 8. サーバーツールを含むとエラー（L115 NOTE）
**検証結果**: 「returns an invalid_request_error for … Server tools such as web search, web fetch, code execution, and tool search (every server tool except the advisor tool)」。advisor tool は本書の範囲外。

### 9. count_tokens に cache_control 付きのブロックを渡してよい（L1050・maybe_compact が cached_system／cached_tools の結果をそのまま数える設計）
**検証結果**: Token counting FAQ「Although you may provide `cache_control` blocks in your token counting request, prompt caching only occurs during actual message creation.」。送る内容と数える内容をそろえる本文の方針（L1089-1090）は API 上も成り立つ。

### 10. 入力単価とコスト計算（L319-320）
**検証結果**: Pricing で Opus 5.5 Base input $4/MTok。0.8M×$4＝$3.2。

### 11. Haiku 5.5 の入力単価・比率（L612-613）
**検証結果**: Pricing「Claude Haiku 5.5 (for prompts up to 100,000 tokens) $0.10 / MTok」、100K超は $0.50。4/0.10＝40。注記も一致。

### 12. 要約ログのコスト（L844）
**検証結果**: 702×0.10＋188×0.50（$/M）＝$0.000164 → $0.0002 表示で整合。

### 13. キャッシュ使用時の入力合計（L302, L1116）
**検証結果**: 「total_input_tokens = cache_read_input_tokens + cache_creation_input_tokens + input_tokens」。

### 14. 前方一致と tools→system→messages の順序（L925-928）
**検証結果**: 「Cache prefixes are created in the following order: tools, system, then messages」「Modifying tool definitions … invalidates the entire cache」。

### 15. ephemeral・5分・読まれると延長（L939-943）
**検証結果**: 「By default, the cache has a 5-minute lifetime. The cache is refreshed for no additional cost each time the cached content is used.」

### 16. 最大4ブレークポイント（L941, L1094）
**検証結果**: 4 slots の記述と一致。コード検証でも実リクエストの `cache_control` は3か所。

### 17. トップレベル自動キャッシュ（L945-948）
**検証結果**: 「Add a single `cache_control` field at the top level … automatically applies the cache breakpoint to the last cacheable block and moves it forward as conversations grow」「the automatic cache breakpoint uses one of the 4 available breakpoint slots」。

### 18. 最小キャッシュ長（L960-964）
**検証結果**: 最小長は 512（Opus 5.5／Sonnet 5.5／Haiku 5.5 ほか）〜4,096（Opus 4.6／4.5、Haiku 4.5）。「processed without caching, and no error is returned」。

### 19. 料金倍率（L967-969）
**検証結果**: 5分書き込み1.25倍、読み取り0.1倍、「Cache hits and refreshes on Claude Opus 5.5 and Claude Sonnet 5.5 are priced at 0.05x」。Pricing 表で Opus 5.5 は $5／$0.20。

### 20. キャッシュの試算（L972-976）
**検証結果**: 2万×20×$4/M＝$1.60、書き込み 2万×$5/M＝$0.10、読み取り 2万×19×$0.20/M＝$0.076。合計 $0.176 で約1/9。

### 21. 7.3節ログのコスト計算（L1108-1109）
**検証結果**: 1行目 152×4＋96×20＋3,418×5＝$0.0196、2行目 1,207×4＋211×20＋3,418×0.2＝$0.0097。算術は一致（ただし usage の内訳そのものは ❌-1 参照）。

### 22. 7.4節の合計コスト（L1307, L1311）
**検証結果**: 250×4＋153×20＋1,920×5＋1,850×0.2＝$0.0140、1,630×4＋262×20＋2,410×5＋4,020×0.2＝$0.0246。算術は一致（値の妥当性は ⚠️-5）。

### 23. キャッシュを壊す要因（L1118-1123）
**検証結果**: Prompt caching の無効化ルール（tool definitions／system の変更）と最小長の記述に一致。

### 24. 圧縮で messages のキャッシュだけ作り直し（L888 WARNING）
**検証結果**: 階層ルール（変更したレベル以降が無効）から、messages の書き換えは tools・system に影響しない。

### 25. effort 変更とキャッシュ（L1125, L1386-1387）
**検証結果**: Prompt caching「Changing the output_config.effort value always invalidates message blocks, with the same model-specific effect on tool and system caches as thinking parameters」。Steering thinking「Setting `effort` explicitly to the model's default is equivalent to omitting it and does not break the cache.」

### 26. Opus 5.5 は adaptive thinking 常時有効・disabled は400（L1331-1333）
**検証結果**: Thinking「Claude … Opus 5.5 … reject `thinking: {type: "disabled"}`. Thinking can't be turned off on these models.」。Effort「Adaptive thinking is always on and can't be turned off」。

### 27. thinking は既定で空文字・課金される（L1348-1349）
**検証結果**: 「`display` defaults to "omitted" on these models」「"omitted": thinking blocks are returned with an empty `thinking` field」「the tokens Claude spends reasoning are billed as output tokens, even when the thinking text isn't returned」。

### 28. `usage.output_tokens_details.thinking_tokens`（L1344, L1350）
**検証結果**: Steering thinking「read `usage.output_tokens_details.thinking_tokens` in the response」。JSON 例も同形。

### 29. thinking は max_tokens に含まれる・対処（L1353-1355）
**検証結果**: 「`max_tokens` is a hard cap on total output for the request, thinking and response text combined」。対処は「Raise `max_tokens`」「Lower the effort level」で本文と一致。

### 30. effort の段階・既定値・各段階の説明（L1359-1371）
**検証結果**: Effort「Claude Opus 5.5 supports all five effort levels, and `medium` is the default」。Steering thinking の表（low＝Skips thinking for simple tasks／medium＝Might skip thinking for simple queries／high＝thinks on most requests／xhigh＝more readily and at greater depth than at high／max＝no constraint on thinking length）。「Effort is a behavioral signal, not a strict token budget」「At every level, Claude determines for each request whether to think」。

### 31. thinking ブロックを改変せずに履歴へ戻す（L1061, L1395-1403）
**検証結果**: Thinking「Modified thinking blocks are rejected with a 400 error」「If you pass thinking blocks back in multi-turn conversations, pass them unchanged」。Steering thinking「When you have thinking blocks, pass them back unmodified, particularly during tool use」。

---

## ⚠️ 要確認（古い可能性あり／補足推奨）

### 1. signature の説明（L1351）
**記述**: 「`signature`は、思考の内容が改ざんされていないことを確かめるための署名です。」
**懸念点**: 公式は「検証用」だけでなく「思考全文を暗号化したもの」と説明しており、既定（omitted）で中身が空でも次のターンに推論が引き継がれる理由はこちらにある。L1398-1399 の「中身が空だからといって削除しない」の根拠として、暗号化の説明があるほうが正確。
**検索結果**: Thinking「Each thinking block also carries a `signature` field, an encrypted copy of the full reasoning that you pass back unchanged」「The API uses the signature to verify that thinking blocks were generated by Claude when you pass them back.」
**推奨対処**: 「`signature`には思考の全文が暗号化して入っており、APIはこれを使って、送り返されたthinkingブロックがClaude自身の生成したものかを確かめます。中身が空でも、次のターンの推論はこの署名から復元されます。」に差し替える。

### 2. count_tokens と assistant 終わりの履歴（L831）
**記述**: 「assistantで終わる履歴はprefillとみなされ、count_tokensが400エラーを返すことがあるからです。」
**懸念点**: Messages API で prefill（最後が assistant）が不可なのは Claude 4.6 以降のモデルの制約として事実だが、count_tokens エンドポイントで 400 になるかは一次情報に記載がない（Token counting のエラー対象リストにもない）。
**推奨対処**: count_tokens の挙動を断定しない書き方にする。文案: 「6件目のassistantを除いたのは、実際のエージェントループと同じく『userで終わる履歴』にそろえるためです。Messages APIは、最後がassistantの履歴（prefill）を受け付けません。」 実APIで確認できた場合のみ現行の記述に戻す。

### 3. count_tokens は空の messages を受け付けない（L211, L240）
**懸念点**: 一次情報で明示を確認できず（Messages API と同じ入力を受ける以上、妥当な推定ではある）。
**推奨対処**: 「count_tokensもMessages APIと同じく、少なくとも1件のmessagesが必要なため」と根拠を Messages API 側に寄せるか、実APIで確認する。

### 4. 空の tools 配列で検証エラーになることがある（L153）
**懸念点**: 一次情報で確認できず。
**推奨対処**: 「空の配列を送っても意味がなく、リクエストが無駄に大きくなるだけなので、指定されたときだけ入れます。」と理由を差し替える（第4章 `_build_body()` の `if tools:` と同じ方針である、と添えると一貫する）。

### 5. 7.4節の実行例のキャッシュ値（L1307）
**記述**: 1回目 `calls=2 … cache_write=1,920 cache_read=1,850`
**懸念点**: 7.3節ではファイル操作ツールだけで tools＋system の書き込みが 3,418 トークンだったのに、7.4節ではメモリツール2つと記憶入りの system を足した状態で、2回の呼び出しの書き込み合計が 1,920 トークンしかない。初回の書き込みだけで 3,418 を超えるのが自然。
**推奨対処**: 実APIの値に差し替える。仮の値のままにするなら、たとえば1回目を `calls=2 input=16 output=153 cache_write=4,410 cache_read=3,920 total=$0.0260`（16×4＋153×20＋4,410×5＋3,920×0.2＝$0.02596）のように、7.3節より書き込みが大きい形にそろえる（2回目も同様に見直す）。

---

## ❌ 要修正（誤りの可能性が高い）

### 1. 7.3節「効果を測る」のログと usage の読み方（L1107-1116）
**記述**:
```text
… stop=tool_use in=152 out=96 cache_write=3418 cache_read=0 cost=$0.0196
… stop=end_turn in=1207 out=211 cache_write=0 cache_read=3418 cost=$0.0097
```
「2回目の`input_tokens`は、新しく足されたtool_resultなど、キャッシュされていない部分だけの量です。」
**問題**: 本章の `run_agent()` はトップレベルの `cache_control`（自動キャッシュ）を毎回付けている（L1057）。自動キャッシュでは区切りが「キャッシュ可能な最後のブロック」に置かれ、会話が伸びると前へ移動するため、2回目のリクエストでは前回までの部分を読み取り、新しく足された assistant 応答と tool_result を **書き込む**。したがって2回目が `cache_write=0`・`in=1207` になるのは、明示的な区切りを tools・system にしか置かない構成の挙動で、本章のコードの挙動と食い違う。1回目の `in=152` も、区切りが最後の user メッセージに置かれる以上は数トークン程度になるのが自然。第8章の check_agent の出力例（`in=8 cache_write=1016` → `in=8 cache_write=185 cache_read=1016`）とも食い違っている。
**正しい情報**: Prompt caching「The system automatically applies the cache breakpoint to the last cacheable block and moves it forward as conversations grow」、複数ターンの例「Request 2 … System through User(2) read from cache; Asst(2) + User(3) written to cache」。usage「`input_tokens`: … tokens after the last cache breakpoint」。
**修正案**（数値は単価表で再計算済み。実APIの値があればそれに置き換える）:
```text
llm_client INFO request_id=req_011CZa... model=claude-opus-5-5 stream=False elapsed=2.41s stop=tool_use in=6 out=96 cache_write=3564 cache_read=0 cost=$0.0198
llm_client INFO request_id=req_011CZb... model=claude-opus-5-5 stream=False elapsed=3.05s stop=end_turn in=6 out=211 cache_write=1353 cache_read=3564 cost=$0.0117
```
本文 L1113-1116 の文案:
「1回目は`cache_creation_input_tokens`（ログのcache_write）が3,564で、tools・system・最初の依頼までがキャッシュに書き込まれています。
2回目は`cache_read_input_tokens`（ログのcache_read）が3,564で、前回の内容がそのまま読み取られています。
同時に、新しく足されたassistantの応答とtool_resultの1,353トークンが、次のターンのために書き込まれています。
`input_tokens`は最後のブレークポイントより後ろの部分だけなので、自動キャッシュを使うとごく小さな値になります。
入力の合計は、この3つを足した値です。」
（L1118 の「2回目以降もcache_readが0のままなら…」はそのまま成り立つ）

---

## 総評

第7章の API 仕様（count_tokens、Prompt caching、adaptive thinking、effort）は一次情報とよく一致しており、前回の ⚠️1・2 は正しく反映されています。count_tokens に `cache_control` 付きのブロックを渡してよいことも公式 FAQ で確認できたため、`maybe_compact()` に送信用と同じ `system_blocks`・`tools` を渡す設計は API 上も問題ありません。

唯一の要修正は、7.3節の実行例のログと「2回目の input_tokens」の説明です。本章のコードはトップレベルの自動キャッシュを使っているので、2回目以降も新しく伸びた部分が書き込まれ、`input_tokens` はごく小さくなります。いまのログは「tools・system にだけ区切りを置いた場合」の形になっており、第8章の出力例とも食い違っています。7.4節の `cache_write=1,920`（⚠️-5）も同じ観点でそろえ直すと、読者が数字を比べたときの違和感がなくなります。

count_tokens のエッジケース（assistant 終わり・空 messages・空 tools）は今回も一次情報で確認できませんでした。実APIで確かめるか、挙動を断定しない書き方に改めてください。

---

## 対応（2026-11-08）

- ❌ 1: 原稿を修正済み。7.3節の実行ログを自動キャッシュの挙動（in=6 / cache_write=3564 → in=6 / cache_write=1353 / cache_read=3564）に差し替え、usage の読み方の説明を書き換えた。数値は単価表で再計算した例で、実APIの実測値に差し替えることを推奨。

---

## 再チェック（2026-11-08・修正箇所）

対象: `git diff` の変更 8か所。一次情報: build-with-claude/token-counting.md、prompt-caching.md、thinking.md、api/messages.md。数値は第4章の単価表（Opus 5.5: in $4 / out $20 / cache_write $5 / cache_read $0.20 per MTok）で検算。

- ⚠️ L49「日本語ではおおむね1文字が1トークン前後です」
  公式に日本語の換算値はないが、第2章 L135・第3章 L112 の「おおむね1文字前後」と揃い、章間の矛盾は解消。ただし同じ章の L199（コメント「日本語中心なら多めに見積もる側に倒れる」）と L236（「1文字を1トークンと数えるのは多めに見積もる側に倒れる」）は、旧記述（1〜2文字で1トークン）を前提にした説明のまま残っている。1文字≒1トークンなら、日本語部分は「ほぼ同じ」で、多めになるのは JSON の記号・キー名の分だけ。
  修正案（L236）:「JSON の記号やキー名は1トークンあたり数文字になるので、その分だけ多めに見積もられ、おおむね安全側の近似になります。」 L199 のコメントも「（JSON の記号の分だけ多めに見積もる側に倒れる）」に。L52「『文字数÷2』のような目分量ではなく」も、例を「『1文字＝1トークン』のような目分量だけに頼らず」などに替えると本文の換算と食い違わない（任意）。
- ✅ L153「空の配列を送っても意味がなく、リクエストが無駄に大きくなるだけなので…（第4章の`_build_body()`の`if tools:`と同じ方針です）」
  断定できない「検証エラーになる」を外した表現で、コード L140 `if tools:` と整合。（文体メモ: 約80字。括弧部分を独立した1文にすると50字前後に収まる。任意）
- ✅ L211 コメント／L240 本文「count_tokensもMessages APIと同じく、少なくとも1件の`messages`が必要」
  token-counting.md は「accepts the same structured list of inputs for creating a message」と説明し、Messages API では `messages` が必須。空配列時の明文はないが、第三者のエラー集（`at least one message is required`）とも整合し、根拠を Messages API 側に寄せた書き方で問題ない。
- ✅ L831「実際のエージェントループと同じく『userで終わる履歴』にそろえるためです。Messages APIは、最後がassistantの履歴（prefill）を受け付けません。」
  thinking.md「Claude 4.6 and later models … reject a prefilled final assistant turn with a 400 error」、messages.md「On models that don't support prefill, … returns a 400 error」。本書のモデル（Opus 5.5・Haiku 5.5）では正しい。count_tokens の挙動を断定しなくなった。（厳密には「本書で使うモデルでは」を添えるとより正確。任意）
- ✅ L1108-1117（7.3節の実行ログと usage の説明）
  検算: 1回目 6×4＋96×20＋3,564×5＝$0.019764→$0.0198、2回目 6×4＋211×20＋1,353×5＋3,564×0.2＝$0.0117218→$0.0117 で一致。prompt-caching.md「the cache point moves forward automatically … Each new request caches everything up to the last cacheable block」「`input_tokens`: … tokens after the last cache breakpoint」「total = cache_read + cache_creation + input_tokens」と一致。2回目の cache_read が1回目の cache_write と同じ 3,564 で、`in=` が数トークンなのも第8章 check_agent の例（in=8）と揃っている。
- ⚠️ L1308・L1312（7.4節のメモリ実行例）
  算術はどちらも一致（1回目 $0.025958→$0.0260、2回目 $0.022592→$0.0226）。1回目は 7.3節より書き込みが大きく（3,920＞3,564）整合。しかし2回目は「新しい会話」でメモリ入りの system が変わるため、最初の呼び出しで tools・system・依頼（約3,900トークン以上）を書き込む必要があり、3回分の書き込み合計 2,900 はそれより小さい。成り立つのは「1回目の実行から5分以内で、tools 部分（約3,500トークン）を前回のキャッシュから読めた」場合だけで、本文にその説明がない。
  修正案A（説明を足す）: L1316 の後に「2回目の実行でも、1回目から5分以内ならツール定義のキャッシュが読み取られるため、書き込みは system 以降の部分だけで済みます。」
  修正案B（数値を差し替え。前回キャッシュなし・tools＋system＋依頼≒3,950、list 結果≒200、notes.md 本文≒1,350 と仮定）: `calls=3 input=18 output=262 cache_write=5,500 cache_read=8,100 total=$0.0344`（18×4＋262×20＋5,500×5＋8,100×0.2＝$0.034432）。
- ✅ L1352「`signature`には思考の全文が暗号化して入っており、APIはこれを使って…確かめます。中身が空でも、次のターンの推論はこの署名から復元されます。」
  thinking.md「Full thinking content is encrypted and returned in the `signature` field … The API uses the signature to verify that thinking blocks were generated by Claude」「The server decrypts the `signature` to reconstruct the original thinking for prompt construction」と一致。（文体メモ: 1文目が約70字。任意）
