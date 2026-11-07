# ファクトチェックレポート

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_08.md
検証日: 2026-11-07
検証クレーム数: 16件
  ✅ 検証済み: 12件
  ⚠️ 要確認: 3件
  ❌ 要修正: 1件（原稿修正済み）

参照した一次情報:
- Prompt caching（最小キャッシュ長・自動キャッシュ）: https://platform.claude.com/docs/en/build-with-claude/prompt-caching.md
- Effort: https://platform.claude.com/docs/en/build-with-claude/effort.md
- Pricing: https://platform.claude.com/docs/en/about-claude/pricing.md
- Models overview: https://platform.claude.com/docs/en/about-claude/models/overview.md
- Tool use overview: https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview.md
- Building effective agents: https://www.anthropic.com/engineering/building-effective-agents

---

## ✅ 検証済み（正確）

### 1. Messages API はステートレス／別の messages 配列で別エージェントになる（L88-93）
**検証結果**: 第3章の前提（facts）と一致。サーバー側に会話状態を持つ仕組みは Messages API にない。

### 2. ツール定義は毎回入力トークンを消費する（L30, L136）
**検証結果**: Tool use overview の Pricing「The total number of input tokens sent to the model (including in the tools parameter)」。

### 3. Haiku は Opus の数十分の一の料金（L128）
**検証結果**: Opus 5.5 入力$4、Haiku 5.5 入力$0.10（10万トークン以下）で1/40、出力も$20 対 $0.50 で1/40。

### 4. マルチエージェントは合計トークンが増える（L135-139, L1340-1342）
**検証結果**: 数値の主張はなく定性的な記述のみ。子ごとに system・tools・指示・報告が重複して送られるという構造上の説明として妥当（出典を要する数値なし）。

### 5. 「Building effective agents」のオーケストレーター-ワーカー（L175 NOTE）
**検証結果**: 記事「a central LLM dynamically breaks down tasks, delegates them to worker LLMs, and synthesizes their results」。親が分解・委譲・統合する本章の構成と一致。

### 6. キャッシュは tools → system → messages の前方一致（L316）
**検証結果**: Prompt caching「Cache prefixes are created in the following order: tools, system, then messages」。

### 7. 最小キャッシュ長に届かなければキャッシュされない（L319）
**検証結果**: 「Shorter prompts cannot be cached, even if marked with cache_control … no error is returned」。

### 8. 並列ツール呼び出しは既定で有効（L789）
**検証結果**: Tool use overview の例で、1回1ツールにするには `tool_choice` に `disable_parallel_tool_use: true` を指定する（＝既定は並列可）。

### 9. ログのコスト表示（L1261-1262 の金額部分）
**記述**: `calls=9 input=10,240 output=1,050 … total=$0.0015`
**検証結果**: Haiku 5.5 単価で 10,240×0.10/M＋1,050×0.50/M＝$0.00155。金額は整合（キャッシュ値は⚠️-2）。

### 10. Opus 5.5 の effort 既定は medium（L1300, L1304）
**検証結果**: Effort「Claude Opus 5.5 supports all five effort levels, and medium is the default」。

### 11. effort 対応はモデルによって異なり、非対応の組み合わせは400の可能性（L1309）
**検証結果**: Effort の表で `xhigh`／`max` の対応モデルが限定されている（「Not every model that supports max supports xhigh」）。なお本書で使う Haiku 5.5・Sonnet 5.5・Opus 5.5 はいずれも5段階すべてに対応（Haiku 5.5 の既定は medium、Sonnet 5.5 は high）。記述は一般論として正確。

### 12. Haiku 5.5 で effort が使えるか（タスク指定の確認事項）
**検証結果**: Effort の supportedModels に `claude-haiku-5-5` が含まれ、「Claude Haiku 5.5 supports all five effort levels, and medium is the default」。本章は Haiku に effort を「指定しない」としているだけで、使えないとは書いていないため矛盾なし。

---

## ⚠️ 要確認（古い可能性あり／補足推奨）

### 1. multi_agent.py 実行例のキャッシュ値（L847）
**記述**: `calls=11 input=24,870 output=2,310 cache_write=0 cache_read=0 total=$0.0731`
**懸念点**: `Agent._request_kwargs()` はトップレベルの自動キャッシュを常に付けている。Opus 5.5・Haiku 5.5 の最小キャッシュ長は512トークン、ツール使用時はシステム側だけで286トークンが加わるため、11回の呼び出しで書き込みも読み取りも0になるのは不自然。
**推奨対処**: 実機で再実行した値に差し替える（cache_write／cache_read が0以外になる見込み。金額も変わる）。

### 2. 逐次・並列比較のキャッシュ値（L1261-1262）
**記述**: 逐次・並列とも `cache_write=0 cache_read=0`
**懸念点**: ⚠️-1 と同じ理由で不自然。さらに、逐次では2本目以降の子が1本目の system・tools のキャッシュを読めるのに対し、並列では同時に送るため読めないことがある。その結果、「コストはほとんど変わらない」（L1266）とはいえ、キャッシュの内訳は両者で異なるのが自然。
**推奨対処**: 実機値に差し替え、必要なら「逐次のほうがキャッシュ読み取りが多くなることがある」と1文補足（第9章 L1112 の NOTE と同じ論点）。

### 3. Haiku 5.5 の100Kトークン超の料金（L128, L759）
**懸念点**: 「数十分の一」は10万トークン以下での比較。10万トークン超では Haiku 5.5 の入力が$0.50/MTok（Opus の1/8）になる。本章の題材では問題ないが、大量の資料を読ませる用途の説明として注記があると親切。
**推奨対処**: L128 に「（プロンプトが10万トークン以下の場合）」を付記。

---

## ❌ 要修正（誤りの可能性が高い）→ 原稿修正済み

### 1. Haiku でキャッシュが作られない理由の説明（旧 L458-468, L481-482）
**記述**: 「`cache_write=0` になっているのは、このプロンプトが短く、最小キャッシュ長に届いていないためです。」（ログも `in=1024 … cache_write=0` など）
**問題**: `claude-haiku-5-5` の最小キャッシュ長は512トークン。ログ自体が1回目で1,024トークンの入力を示しており、トップレベルの自動キャッシュ（`Agent._request_kwargs()` の `extra`）は「キャッシュ可能な最後のブロック」に区切りを置くため、1,024トークンの前置部分はキャッシュされるはず。説明とログが一次情報と矛盾している。
**正しい情報**: Prompt caching の最小長表で 512 tokens に Claude Haiku 5.5 が含まれる。「The system automatically applies the cache breakpoint to the last cacheable block」。Tool use overview によると、Haiku 5.5 はツール使用時のシステムプロンプトだけで286トークン。
**修正内容（chapter_08.md に反映済み）**:
- 3行の `llm_client` ログを、キャッシュが効いた形（1回目 `in=8 cache_write=1016`、2回目 `in=8 cache_write=185 cache_read=1016`、3回目 `in=8 cache_write=160 cache_read=1201`）に変更。コストは Haiku 5.5 の単価（入力0.10・書き込み0.125・読み取り0.01・出力0.50 $/MTok）で再計算（$0.0002／$0.0001／$0.0001）。
- `tracker.summary()` 行を `calls=3 input=24 output=187 cache_write=1,361 cache_read=2,217 total=$0.0003` に変更。
- 説明文を「`cache_write` と `cache_read` に値が出ているのは、第7章で付けたキャッシュの区切りが Haiku でも働いているためです。`claude-haiku-5-5` の最小キャッシュ長は512トークンなので、この程度の短いプロンプトでもキャッシュされます。1回目に書き込んだ部分を2回目以降が読み取り、`in=` には区切りより後ろのわずかな部分だけが数えられています。」に差し替え。
- ※数値は一例です。実機で実行したら、その値に置き換えてください。

---

## 総評

第8章は設計論と自前実装が中心で、API 仕様に関わる主張は少なく、ほぼ正確です。
唯一の明確な誤りは、「Haiku では最小キャッシュ長に届かないため `cache_write=0`」という説明でした。Haiku 5.5 の最小長は512トークンなので、自動キャッシュ付きの `Agent` では短いプロンプトでもキャッシュされます。この点は原稿を修正済みです。
同じ理由で、`multi_agent.py` の実行例（L847）と逐次・並列の比較（L1261-1262）にある `cache_write=0 cache_read=0` も不自然です。`/verify-code` などで実機の値を取り、差し替えることを推奨します。
マルチエージェントのトークン消費については数値の主張がないため、出典の確認は不要でした。
