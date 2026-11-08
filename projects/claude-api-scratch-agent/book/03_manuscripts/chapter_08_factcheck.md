# ファクトチェックレポート（再検証）

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_08.md
検証日: 2026-11-08
検証クレーム数: 28件
  ✅ 検証済み: 27件
  ⚠️ 要確認: 0件
  ❌ 要修正: 1件

参照した一次情報（2026-11-08 に WebFetch で取得）:
- Prompt caching: https://platform.claude.com/docs/en/build-with-claude/prompt-caching.md
- Pricing: https://platform.claude.com/docs/en/about-claude/pricing.md
- Effort: https://platform.claude.com/docs/en/build-with-claude/effort.md
- Rate limits: https://platform.claude.com/docs/en/api/rate-limits.md
- Tool use overview: https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview.md
- Building effective agents: https://www.anthropic.com/engineering/building-effective-agents
- Python asyncio（Coroutines and Tasks）: https://docs.python.org/3/library/asyncio-task.html
- 本書内: 第4章 `PRICES`（Opus 5.5 $4/$20/$5/$0.20、Haiku 5.5 $0.10/$0.50/$0.125/$0.01 per MTok）、第6章 `execute_tool_uses()`・`MAX_PARALLEL_TOOLS = 8`・`list_files(path=".")`・`register_file_tools()`、第7章 `BASE_SYSTEM`

## 前回からの経緯

- 2026-11-08 朝の検証で ❌2件（multi_agent.py 実行例・逐次並列比較の `cache_write=0 cache_read=0`）と ⚠️4件を指摘し、原稿を修正。修正箇所の再チェックで出た数値の不整合（L868・L1309-1310）と L355・L976 の表現も反映済み。
- その後の用語統一・長文分割（36文）・キャッシュ値の差し替えを含めて、今回は章全体を再検証した。長文分割で言い換えた文は `git diff HEAD` で元の文と照合し、意味のずれは見つからなかった。

---

## ✅ 検証済み（正確）

### 1. Messages API はステートレス／別の messages 配列で別エージェントになる（L91-96）
**記述**: 「第1章で説明した「APIはステートレス（状態を持たない）」という性質」
**検証結果**: Tool use overview の往復例は、毎回 messages 全体を送り直す形。第1章 L11・L288 も「APIがステートレス」と書いており、「LLMは」から「APIは」への変更で第1章と表現がそろった。

### 2. ツール定義は毎回入力トークンを消費する（L31, L141）
**検証結果**: Tool use overview「The total number of input tokens sent to the model (including in the `tools` parameter)」。ツールを使うと、Opus 5.5・Haiku 5.5 では 286 トークンのツール用 system プロンプトも加わる。

### 3. マルチエージェントは合計トークンが増える（L140-144, L1390-1392）
**検証結果**: 子ごとに system・tools・指示・報告が重複するという、構造から導ける説明。出典が必要な数値はない。

### 4. オーケストレーター-ワーカーの NOTE（L180。長文分割で言い換え）
**記述**: 「…形には名前があります。Anthropic社の記事「Building effective agents」で紹介されているパターンです。記事では、オーケストレーター-ワーカー（Orchestrator-workers）と呼ばれています。」
**検証結果**: 記事の定義「a central LLM dynamically breaks down tasks, delegates them to worker LLMs, and synthesizes their results」と一致する。分割前の文と意味は変わっていない。（補足: 記事ではこのパターンを「Workflow: Orchestrator-workers」としてワークフローに分類している。第9章 L206・L222 は「モデル（分解）＋コード（実行）」と整理しており、第8章 L524 の「委譲の手順をコードで固定する方法は…ワークフローの領域」とも矛盾しない。）

### 5. キャッシュは tools → system → messages の前方一致（L327）
**検証結果**: Prompt caching「Cache prefixes are created in the following order: `tools`, `system`, then `messages`」。

### 6. 最小キャッシュ長に届かなければキャッシュされない（L330）
**検証結果**: 「Shorter prompts cannot be cached, even if marked with `cache_control` … no error is returned」。

### 7. Haiku 5.5 の最小キャッシュ長は512トークン・自動キャッシュの働き（L499-502）
**検証結果**: 最小長は「512 tokens for … Claude Opus 5.5 … Claude Sonnet 5.5 … and Claude Haiku 5.5」。自動キャッシュは「applies the cache breakpoint to the last cacheable block and moves it forward」。Rate limits にも「`input_tokens` (tokens after the last cache breakpoint)」とあり、`in=` に区切りより後ろの部分だけが数えられるという説明は正しい。

### 8. check_agent.py の出力例のトークンとコスト（L474-484）
**検証結果**: 第4章の単価表で計算すると、各行は $0.000157・$0.0000546・$0.0000768 で、合計は $0.000288。表示の $0.0002・$0.0001・$0.0001・$0.0003 と一致する。read 1,201＝1,016＋185、合計の書き込み 1,361・読み取り 2,217 も各行の和と一致する。

### 9. Haiku の料金は10万トークン以下なら Opus の40分の1（L132-133）
**検証結果**: Pricing の「Claude Haiku 5.5 (for prompts up to 100,000 tokens)」は $0.10・$0.125・$0.01・$0.50、Opus 5.5 は $4・$5・$0.20・$20。入力・書き込み・出力はちょうど40分の1になる（読み取りだけは20分の1だが、趣旨に影響はない）。プロンプト長には「cache reads and cache writes」も含まれ、条件の書き方として正確。

### 10. multi_agent.py 実行例のコスト集計（L868）
**記述**: `calls=11 input=92 output=2,310 cache_write=6,500 cache_read=8,200 total=$0.0375`
**検証結果**: 内訳を Opus 2回（in 20・out 1,200・書き込み 2,400・読み取り 1,500）＝$0.03638、Haiku 9回（in 72・out 1,110・書き込み 4,100・読み取り 6,700）＝$0.0011417 とすると、合計は $0.0375。子3本はスレッドで同時に起動するので互いのキャッシュを読めず、Haiku の分が後述の「並列（キャッシュなし）」の値と同じ規模になる点も、一次情報の「a cache entry only becomes available after the first response starts」と整合する。

### 11. 第6章 `execute_tool_uses()` の要約（L206, L280-282, L346-347）
**検証結果**: 第6章 L974-1003 の実装（読み取り系は `ThreadPoolExecutor` で並列、副作用系は承認後に1件ずつ、元の順で返す）と一致する。

### 12. 残す関数と定数の列挙（L218-221。長文分割で言い換え）
**検証結果**: `run_agent()`・`execute_tool_uses()`・`build_registry()` は第6章、`BASE_SYSTEM` は第7章 L1073 で定義されている。「第6・7章で作った関数や定数」という書き方は正しく、元の文と意味も同じ。

### 13. `tools/files.py` のラッパーの説明（L365-371）
**検証結果**: 第6章の `list_files(path: str = ".")`・`read_file(path: str, start_line: int = 1)`・`register_file_tools(registry, *, allow_write=True)` と一致する。「同等」「引数名は `path` になります」という書き方も正確（朝の ⚠️ は反映済み）。

### 14. 並列ツール呼び出しは既定で有効（L810）
**検証結果**: Tool use overview は、1ターンに1ツールにしたいときだけ `tool_choice` に `"disable_parallel_tool_use": true` を指定している。

### 15. 同時8本の上限とレート制限（L1000-1003）
**検証結果**: 第6章 L702 に `MAX_PARALLEL_TOOLS = 8` がある。`delegate_research` は `side_effect` を指定しない読み取り系として扱われるので、最大8本のスレッドで並列に動く。Rate limits には「New organizations … may start in the Evaluation tier, with limits below the standard limits」「Short bursts of requests can exceed the limit」とあり、「利用ティアの上限が低いうちは…近づくことがあります」という書き方は妥当。

### 16. 子の API エラーの伝わり方（L973-982。長文分割で言い換え）
**検証結果**: 第4章の `_is_retryable()`（401・400 はリトライしない）、第6章の `run_one_tool()`（例外を `is_error: True` に変換し、種類名を含める）と一致する。分割前の文（「401 や 400 のようなリトライしないエラーや、リトライを使い切った 529 は例外として上がってきます」）と意味は同じ。

### 17. 非同期版で再利用する第4章の5つの関数（L1018-1029。箇条書きに言い換え）
**検証結果**: `_build_body()`（第4章 L273）・`_is_retryable()`（L496）・`_retry_delay()`（L506）・`_error_from_response()`（L240）・`_log_call()`（L1074）は、いずれも第4章にある。同じ名前で定義し直すと後ろの定義が前の定義を上書きするという説明は、Python の仕様どおり。

### 18. `httpx.AsyncClient` と `Event loop is closed` の WARNING（L1104。言い換え）
**検証結果**: 朝の検証で、ローカル HTTP サーバーを使って再現を確認済み（`aclose_client()` を呼ばずに `asyncio.run()` を2回 → `RuntimeError: Event loop is closed`）。言い換え後も「原因 → 症状 → 対策」の内容は変わっていない。

### 19. `asyncio.to_thread()` でブロッキング処理を別スレッドへ（L1161-1163, L1182-1183）
**検証結果**: Python 公式「Asynchronously run function func in a separate thread … primarily intended to be used for executing IO-bound functions/methods that would otherwise block the event loop」。

### 20. `asyncio.gather()` の結果の順序と `return_exceptions=True`（L1188-1194）
**検証結果**: Python 公式「The order of result values corresponds to the order of awaitables in aws」「If return_exceptions is True, exceptions are treated the same as successful results, and aggregated in the result list」。

### 21. `time.sleep()` はほかの子も止める（L1099）
**検証結果**: イベントループは1本のスレッドで動くので、同期の sleep はループ全体を止める。Python 公式の `to_thread` の説明（「would otherwise block the event loop」）とも一致する。

### 22. レート制限は組織単位・1分あたりのリクエスト数とトークン数・超えると429（L1199-1200）
**検証結果**: Rate limits「Limits are set at the organization level」「measured in requests per minute (RPM), input tokens per minute (ITPM), and output tokens per minute (OTPM) … If you exceed any of the rate limits, you get a 429 error」。

### 23. Semaphore で子の数を絞れば同時リクエスト数もほぼ同じになる（L1289-1290）
**検証結果**: `arun()` は1本の中で `acall_messages()` を順に await するので、子1本が同時に送るリクエストは最大1件。正しい（親の呼び出しの分だけ「ほぼ」になる）。

### 24. 上限3で6件なら2巡（L1319）
**検証結果**: Semaphore(3) のもとでの単純な計算。正しい。

### 25. Opus 5.5 の effort 既定は medium、Haiku 5.5 は「指定しない」（L1350-1357）
**検証結果**: Effort「Claude Opus 5.5 supports all five effort levels, and `medium` is the default」「Claude Haiku 5.5 supports all five effort levels, and `medium` is the default」「With no value, the model's default level applies」。Sonnet 5.5 の既定は `high`。表の内容と矛盾しない。

### 26. effort への対応はモデルで異なり、対応しない組み合わせでは400の可能性（L1359-1360）
**検証結果**: Effort の表では `xhigh`・`max` に対応するモデルが限られ、「Not every model that supports `max` supports `xhigh`」とある。本書で使う3モデルは5段階すべてに対応する。一般論として正確。

### 27. 構造化出力は `output_config.format`（L1381）
**検証結果**: references/claude-api-facts.md（`output_config: {"format": {"type": "json_schema", ...}}`）と一致する。

---

## ⚠️ 要確認（古い可能性あり／補足推奨）

該当なし。

---

## ❌ 要修正（誤りの可能性が高い）

### 1. 逐次・並列比較の出力例と「並列ではキャッシュを読めない」の説明（L1309-1310, L1314-1317）
**記述**:
```text
逐次: 19.8s  calls=9 input=72 output=1,050 cache_write=2,200 cache_read=8,600 total=$0.0009
並列: 7.1s  calls=9 input=72 output=1,062 cache_write=4,100 cache_read=6,700 total=$0.0011
```
「むしろ並列では、最初の子の応答が始まる前にほかの子のリクエストが送られます。そのためsystemとツール定義のキャッシュを読めず、書き込みが増えてわずかに高くなることがあります。」

**問題**: 計算そのものは単価表と一致します（逐次 $0.00089、並列 $0.00112）。説明も一般論としては一次情報どおりです。しかし、本章の `compare()`（L1237-1260）では、この説明がこの出力に当てはまりません。
- `compare()` は**逐次を先に実行し、約20秒後に並列を実行**する。
- 2つの実行は、同じ `researcher`（同じ system・tools）と同じ `build_child_task(t, aspects)`（context なしで同じ文字列）を使う。
- キャッシュの有効期間は既定で5分なので、並列の子3本の1回目の呼び出しは、逐次の実行で書き込まれた「tools＋system＋依頼文」のキャッシュをそのまま読める。

そのため、この順序で実行すると、並列のほうが書き込みが**少なく**、コストもわずかに**安く**なるはずです。出力例（並列のほうが書き込みが多く高い）と L1316-1317 の説明は、本章のコードの実行結果としては成り立ちません。「並列ではキャッシュを読めない」現象が実際に現れるのは、キャッシュがない状態で同時に送る場合です（8.2節の multi_agent.py の実行例 L868 がこれにあたり、こちらは整合しています）。

**正しい情報**:
- Prompt caching「By default, the cache has a 5-minute lifetime. The cache is refreshed for no additional cost each time the cached content is used.」
- 同「For concurrent requests, note that a cache entry only becomes available after the first response starts.」
- 同「Cache hits require 100 percent identical prompt segments」（依頼文が同じなので、1回目の呼び出しは全体が一致する。2回目以降は、assistant の `tool_use` の id などが実行ごとに変わるので、そこから先は新たに書き込まれる）

**修正案**（コードは変えず、出力例と説明を直す案。数値は朝と同じ前提 P≒1,020・S≒950・D1≒185・D2≒160 で計算した一例。並列は子1本あたり読み取り P＋P＋(P＋D1)、書き込み D1＋D2）:
```text
逐次: 19.8s  calls=9 input=72 output=1,050 cache_write=2,200 cache_read=8,600 total=$0.0009
並列: 7.1s  calls=9 input=72 output=1,062 cache_write=1,000 cache_read=9,700 total=$0.0008
失敗: なし
```
（並列: 7.2＋531＋125＋97＝$0.00076）

L1314-1317 の文案:
「所要時間は約3分の1になりましたが、呼び出し回数とトークンの合計はほとんど変わっていません。
並列化は「同じ仕事を同時にやる」だけなので、並列化そのものでは払う金額は減りません。
この例で並列のほうがわずかに安いのは、直前の逐次の実行で書き込まれたキャッシュを読めたためです（キャッシュの有効期間は既定で5分です）。
逆に、キャッシュがない状態で子を同時に送ると、最初の子の応答が始まるまでほかの子はキャッシュを読めません。
そのため、書き込みが増えてわずかに高くなることがあります。8.2節の実行例の `cache_write` が大きいのは、このためです。」

（別案: `compare()` で並列を先に実行するよう入れ替えると、今の数値と説明がそのまま並列について正しくなる。ただしその場合は、逐次のほうがキャッシュを読めて安くなる。どちらの順でも、後に実行したほうが有利になることを1文で注記する。）

---

## 総評

第8章の API 仕様に関わる記述（ステートレス性、ツール定義のトークン、キャッシュの順序・最小長・自動キャッシュ、effort の既定値と対応、レート制限とティア、Orchestrator-workers）は一次情報と一致しています。Python の `asyncio.gather`・`to_thread` の説明も公式ドキュメントどおりです。Haiku の料金の条件、`list_files` の引数名、同時8本の上限の説明も、第4・6章の実装と整合しています。

用語統一と長文分割（36文）は `git diff` で元の文と照合しました。L180 の NOTE、L218-221 の `BASE_SYSTEM` の文、L1018-1024 の5関数の箇条書き、L1104 の WARNING、L973-982 のエラーの伝わり方を含め、事実関係がずれた箇所はありませんでした。

要修正は1件で、逐次・並列比較（L1309-1317）です。数値の計算と説明はそれぞれ正しいのですが、`compare()` は逐次の直後に同じ依頼文で並列を実行します。そのため、並列は5分以内のキャッシュを読めて、むしろ安くなります。「並列ではキャッシュを読めない」という公式の注意点は、8.2節の multi_agent.py の例（L868）の説明として使うのが適切です。

文体メモ（事実ではないので件数に含めない）: L1317「そのためsystemとツール定義の」は、ほかの箇所にならって「そのため、system とツール定義の」と読点と半角スペースを入れるとよいでしょう。出力例の数値は、いずれも単価表から逆算した例です。公開前に実 API の実測値に差し替えることを勧めます。

---

## 対応（2026-11-08・再検証後）

- ❌ L1309〜1317: 並列の行を `cache_write=1,000 cache_read=9,700 total=$0.0008` に変え（単価表で検算済み）、直前の逐次の実行のキャッシュを読めたため並列が安い、という説明に書き換えた。
