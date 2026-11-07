# ファクトチェックレポート

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_07.md
検証日: 2026-11-07
検証クレーム数: 35件
  ✅ 検証済み: 29件
  ⚠️ 要確認: 6件
  ❌ 要修正: 0件

参照した一次情報:
- Token counting: https://platform.claude.com/docs/en/build-with-claude/token-counting.md
- Prompt caching: https://platform.claude.com/docs/en/build-with-claude/prompt-caching.md
- Thinking: https://platform.claude.com/docs/en/build-with-claude/thinking.md
- Steering thinking（adaptive-thinking.md のリダイレクト先）: https://platform.claude.com/docs/en/build-with-claude/thinking-steering-and-cost
- Effort: https://platform.claude.com/docs/en/build-with-claude/effort.md
- Pricing: https://platform.claude.com/docs/en/about-claude/pricing.md
- Models overview: https://platform.claude.com/docs/en/about-claude/models/overview.md

---

## ✅ 検証済み（正確）

### 1. コンテキストと最大出力（L40）
**記述**: 「`claude-opus-5-5`のコンテキストは100万トークン（1M）、最大出力は128Kトークン」
**検証結果**: Models overview の表で Opus 5.5 は Context window 1M tokens / Max output 128K tokens。

### 2. 新しい世代のモデルはトークン数が多めになる（L51）
**記述**: 「新しい世代のモデルは同じ文章でも以前より多めにトークン化される」
**検証結果**: Token counting「Claude 4.7 and later models … use a newer tokenizer. The same input text produces approximately 30 percent more tokens」。

### 3. エンドポイント（L80, L143, L158）
**記述**: 「`POST /v1/messages/count_tokens`」
**検証結果**: Token counting の curl 例と「Applicable endpoints: `/v1/messages/count_tokens`」で一致。

### 4. 渡せるフィールドとレスポンス形（L81-82, L104）
**記述**: 「`model`・`messages`・`system`・`tools`を渡す」「`{"input_tokens": N}`」
**検証結果**: 「accepts the same structured list of inputs for creating a message, including support for system prompts, tools, images, and PDFs」。出力例 `{ "input_tokens": 14 }`。

### 5. max_tokens 不要（L108）
**記述**: 「`max_tokens`を渡す必要がない」
**検証結果**: 公式の curl/Python 例はいずれも `max_tokens` を含まずに呼んでいる。

### 6. 無料・別枠のレート制限（L110-111, L159, L362）
**記述**: 「無料で、メッセージ生成とは別枠のレート制限（1分あたりのリクエスト数）」
**検証結果**: 「Token counting is free to use but subject to requests per minute rate limits」「Token counting and message creation have separate and independent rate limits」。

### 7. 見積もり値（L112-113）
**記述**: 「返ってくる値が見積もり…わずかにずれる場合がある」
**検証結果**: 「The token count is an estimate. In some cases, the actual number of input tokens … might differ by a small amount.」

### 8. サーバーツールを含むとエラー（L115 NOTE）
**記述**: 「サーバーツール（web_searchなど）を含むリクエストではエラー」
**検証結果**: 「returns an invalid_request_error for … Server tools such as web search, web fetch, code execution, and tool search (every server tool except the advisor tool)」。advisor tool は例外だが本書の範囲外のため問題なし。

### 9. 入力単価とコスト計算（L319-320）
**記述**: 「入力単価は100万トークンあたり4ドル」「80万トークンで約3.2ドル」
**検証結果**: Pricing で Opus 5.5 Base input $4/MTok。0.8×4＝3.2ドル。

### 10. Haiku 5.5 の入力単価と比率（L612-613）
**記述**: 「`claude-haiku-5-5`の入力単価は100万トークンあたり0.10ドル」「40分の1」
**検証結果**: Pricing「Claude Haiku 5.5 (for prompts up to 100,000 tokens) $0.10 / MTok」。4/0.10＝40。※100K超の料金は ⚠️-2 参照。

### 11. 要約ログのコスト（L844）
**記述**: `model=claude-haiku-5-5 … in=702 out=188 … cost=$0.0002`
**検証結果**: 702×$0.10/M＋188×$0.50/M＝$0.000164 → 表示 $0.0002 で整合。

### 12. キャッシュ使用時の入力合計（L302, L1116）
**記述**: 「入力の合計は`input_tokens`・`cache_creation_input_tokens`・`cache_read_input_tokens`の3つを足した値」
**検証結果**: Prompt caching「total_input_tokens = cache_read_input_tokens + cache_creation_input_tokens + input_tokens」。`input_tokens` は最後のブレークポイントより後ろの部分（L1115 の説明とも一致）。

### 13. 前方一致と tools→system→messages の順序（L922-928）
**記述**: 「`tools`→`system`→`messages`の順」「ツール定義を1つ変えると、systemとmessagesのキャッシュも無効」
**検証結果**: 「Cache prefixes are created in the following order: tools, system, then messages」「Modifying tool definitions … invalidates the entire cache」。

### 14. ephemeral と 5分 TTL・読み取りで延長（L939-943）
**記述**: 「`cache_control: {"type": "ephemeral"}`」「既定では5分間」「読まれるたびに寿命は延長」
**検証結果**: 「ephemeral is the only supported cache type, which by default has a 5-minute lifetime」「The cache is refreshed for no additional cost each time the cached content is used」。

### 15. 最大4ブレークポイント（L941, L1094）
**記述**: 「ブレークポイントは1リクエストに最大4つまで」
**検証結果**: 「You can define up to 4 cache breakpoints.」

### 16. トップレベル自動キャッシュ（L945-948, L1057）
**記述**: 「リクエストのトップレベルに`cache_control`を置く方法」「キャッシュ可能な最後のブロックに自動で置かれ、会話が伸びると後ろへ移動」「4つの枠のうち1つを使う」
**検証結果**: 「Add a single cache_control field at the top level of your request body」「automatically applies the cache breakpoint to the last cacheable block and moves it forward as conversations grow」「the automatic cache breakpoint uses one of the 4 available breakpoint slots」。

### 17. 最小キャッシュ長（L960-964）
**記述**: 「512〜4,096トークンの範囲」「短い部分はエラーにならず黙ってキャッシュなしで処理」
**検証結果**: 最小長表は 512（Opus 5.5/Sonnet 5.5/Haiku 5.5 ほか）〜4,096（Opus 4.6/4.5, Haiku 4.5）。「processed without caching, and no error is returned」。

### 18. 料金倍率（L967-969）
**記述**: 「書き込み（5分）は1.25倍」「読み取りは0.1倍が基本」「`claude-opus-5-5`と`claude-sonnet-5-5`の読み取りは0.05倍」
**検証結果**: 「Cache write tokens with a 5-minute TTL are 1.25 times」「Cache hits and refreshes on Claude Opus 5.5 and Claude Sonnet 5.5 are priced at 0.05x」。Pricing 表でも Opus 5.5 cache hit $0.20/MTok。

### 19. キャッシュの試算（L972-976）
**記述**: 「キャッシュなし1.6ドル」「書き込み0.1ドル、読み取り19回で約0.08ドル」「約9分の1」
**検証結果**: 2万×20×$4/M＝$1.60、2万×$5/M＝$0.10、2万×19×$0.20/M＝$0.076。合計$0.176で約1/9。

### 20. 実行ログのコスト（L1108-1109）
**検証結果**: 1行目 152×4＋96×20＋3418×5（$/M）＝$0.0196、2行目 1207×4＋211×20＋3418×0.2＝$0.0097。いずれも一致。

### 21. 長期メモリ実行例の合計（L1307, L1311）
**検証結果**: $0.0140・$0.0246 とも Opus 5.5 の単価（入力4・出力20・書き込み5・読み取り0.2）で再計算して一致。

### 22. キャッシュを壊す要因（L1118-1125）
**記述**: 「systemに可変値」「ツールの並び順や定義の変化」「最小長未満」
**検証結果**: Prompt caching の無効化表（tool definitions／system）と最小長の記述に一致。

### 23. 圧縮でmessagesのキャッシュが作り直しになる（L888 WARNING）
**検証結果**: 階層ルール「Changes at each level invalidate that level and all subsequent levels」から、messages だけを書き換えれば tools・system のキャッシュは保たれる。

### 24. Opus 5.5 の adaptive thinking 常時有効・disabled は400（L1331-1333）
**検証結果**: Effort「Adaptive thinking is always on and can't be turned off … Requests that set thinking: {"type": "disabled"} return a 400 error at every effort level」。Models overview「Adaptive (always on)」。

### 25. thinking の中身は既定で空文字・課金される（L659, L1348-1349）
**検証結果**: Thinking「display defaults to "omitted" on these models」「"omitted": thinking blocks are returned with an empty thinking field」。「the tokens Claude spends reasoning are billed as output tokens, even when the thinking text isn't returned」。

### 26. `usage.output_tokens_details.thinking_tokens`（L1344, L1350）
**検証結果**: Steering thinking「read usage.output_tokens_details.thinking_tokens in the response」。JSON 例も同形。

### 27. thinking は max_tokens に含まれる（L1353-1355）
**検証結果**: 「max_tokens is a hard cap on total output for the request, thinking and response text combined」。対処として「Raise max_tokens」「Lower the effort level」と記載があり、本文の対処と一致。

### 28. effort の段階・既定値・各段階の説明（L1359-1370）
**記述**: 「`low`・`medium`・`high`・`xhigh`・`max`の5つ」「`claude-opus-5-5`の既定は`medium`」、表の各説明、「目安であって必ずではない」
**検証結果**: Effort「Claude Opus 5.5 supports all five effort levels, and medium is the default」。Steering thinking の表（low=Skips thinking for simple tasks / medium=Might skip thinking for simple queries / high=thinks on most requests / xhigh=more readily and at greater depth than at high / max=no constraint on thinking length）と一致。「Effort is a behavioral signal, not a strict token budget.」。`output_config.effort` で指定する点も一致。

### 29. thinking ブロックを改変せずに履歴へ戻す（L1061, L1393-1402）
**検証結果**: Thinking「Pass every thinking block back to the API complete and unmodified, alongside the tool_use block it accompanied」「Modified thinking blocks are rejected with a 400 error」。

---

## ⚠️ 要確認（古い可能性あり／補足推奨）

### 1. effort 変更とキャッシュ（L1125, L1386-1387）
**記述**: 「effortを会話の途中で変えた場合も、messagesのキャッシュは無効になります」
**懸念点**: 記述自体は正しいが不完全。公式では (a) トップレベルの effort 変更は messages を「always」無効化し、tools・system もモデルによっては無効化される、(b) 既定値（Opus 5.5 は medium）を明示指定するのは省略と同じでキャッシュを壊さない、(c) Opus 5.5 は per-message effort（beta, `mid-conversation-output-config-2026-07-01`）で途中変更してもキャッシュを保てる。
**検索結果**: Prompt caching「Changing the output_config.effort value always invalidates message blocks, with the same model-specific effect on tool and system caches as thinking parameters」「Setting effort explicitly to the model's default is equivalent to omitting it and does not invalidate」。Effort「On … Claude Opus 5.5 … use a per-message effort change, which keeps the prompt cache.」
**推奨対処**: L1386 を「1つの会話の途中でトップレベルのeffortを変えると、少なくともmessagesのキャッシュが無効になります（モデルによってはtools・systemも）。」とし、NOTE で「Opus 5.5 などはベータ機能の per-message effort で途中変更してもキャッシュを保てる（本書では扱わない）」と補足。

### 2. Haiku 5.5 の料金は 100K トークン超で上がる（L611-613）
**記述**: 「`claude-haiku-5-5`の入力単価は100万トークンあたり0.10ドル」
**懸念点**: Haiku 5.5 はプロンプト長で料金が変わる。100,000トークン超のリクエストは入力$0.50/出力$2.50（キャッシュ読み取り含め全体が高い単価）。本章のしきい値は15万トークンなので、要約に渡す書き起こしが10万トークンを超えると単価が5倍になる。
**検索結果**: Pricing「Claude Haiku 5.5 (for prompts over 100,000 tokens) $0.50 / MTok … $2.50 / MTok」「a request whose prompt is over 100,000 tokens pays higher prices」。
**推奨対処**: 「（プロンプトが10万トークン以下の場合。超えると単価が上がります）」と括弧書きを追加。`_to_transcript()` の tool_result 切り詰めで通常は10万未満に収まる旨も添えるとよい。第4章 `CostTracker` が Haiku の2段階単価に対応しているかも確認。

### 3. count_tokens と assistant 終わりの履歴（L831）
**記述**: 「assistantで終わる履歴はprefillとみなされ、count_tokensが400エラーを返すことがある」
**懸念点**: Messages API での prefill 不可（2026-10-21）は facts と整合するが、count_tokens エンドポイントで 400 になるかは一次情報で確認できなかった。
**推奨対処**: 実機で確認するか、「Messages APIではassistantで終わる履歴（prefill）が受け付けられないため、ここでもuserで終わる形にそろえます」のように、count_tokens の挙動を断定しない書き方にする。

### 4. count_tokens は空の messages を受け付けない（L211, L240）
**懸念点**: 一次情報で明示を確認できず（Messages API の仕様上は妥当）。
**推奨対処**: `/verify-code` で実機確認。結果に応じて表現を維持または「空のmessagesは送れないため」に調整。

### 5. 空の tools 配列で検証エラーになることがある（L153）
**懸念点**: 一次情報で確認できず。「ことがある」と断定は避けているが根拠が不明。
**推奨対処**: 実機確認、または「空の配列を送っても意味がないため」と理由を差し替える。

### 6. 実行例の数値の整合（L1307 と L1108 の関係）
**懸念点**: 7.3節ではファイル操作ツールのみで tools+system のキャッシュ書き込みが3,418トークンなのに、7.4節ではメモリツールを追加したにもかかわらず2回分の書き込み合計が1,920トークンと小さい。最小長はクリアしているので誤りとまでは言えないが、読者が比べると不自然。
**推奨対処**: 実機で再実行した値に差し替える。

---

## ❌ 要修正（誤りの可能性が高い）

該当なし。

---

## 総評

第7章の API 仕様（count_tokens、Prompt caching、adaptive thinking、effort）は、一次情報とほぼ完全に一致しています。料金計算・ログのコスト表示もすべて単価から再計算して整合しました。
要対応は、effort 変更時のキャッシュ挙動の補足（per-message effort と既定値の扱い）と、Haiku 5.5 の100Kトークン超の料金の注記の2点です。
count_tokens のエッジケース（空 messages・空 tools・assistant 終わり）は一次情報に記述がないため、`/verify-code` での実機確認を推奨します。
signature の説明（L1351「改ざんされていないことを確かめるための署名」）は公式の「verify that thinking blocks were generated by Claude」と趣旨が合っています。公式は「思考全文を暗号化したもの」でもあると説明しているので、必要なら一言添えてください。

---

## 対応（2026-11-07）

| ⚠️ | 対応 | 原稿の位置（対応後） |
|---|---|---|
| 1. effort 変更とキャッシュ | WARNING の末尾を「トップレベルのeffortを会話の途中で変えた場合も、messagesのキャッシュは無効になります（モデルによってはtools・systemも）。ただし既定値（Opus 5.5なら`medium`）を明示的に送るのは省略と同じ扱いで、キャッシュは壊れません。」に修正。effort の節も「トップレベルのeffortを変えると、少なくともmessagesのキャッシュが無効（モデルによってはtools・systemも）」とし、「既定値を明示的に送るだけなら省略と同じ扱いなので、キャッシュは壊れません」を1文追加。per-message effort（ベータ）は本書の範囲外のため触れていない | L1125、L1386-1387 |
| 2. Haiku 5.5 の100K超料金 | 「（入力10万トークン以下の場合。超えると単価が上がります）」を追記（第0・2・3章の「10万トークン以下」表記に合わせた）。第4章 `CostTracker` は `LONG_PROMPT_PRICES` で2段階単価に対応済みであることを確認 | L612 |
| 3〜6 | 今回の依頼範囲外（未対応）。実機確認待ち | — |

コードの変更はないため、再実行は不要。仕様は `references/claude-api-facts.md`（L65-66・L105）と一致。
