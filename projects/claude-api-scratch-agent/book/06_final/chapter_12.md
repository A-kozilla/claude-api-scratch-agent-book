# 第12章: まとめと次のステップ
# EN-TITLE: SUMMARY AND NEXT STEPS
# TAGS: 振り返り, 実務導入チェックリスト, 公式ドキュメント, 次の一歩

## この章で学ぶこと

本章では以下を学びます：

- 第1〜11章で作ったファイルと学んだ原理を、依存関係の地図として説明できるようになる
- 自作エージェントを実務に導入する前の確認項目を、理由とあわせて手元に持てるようになる
- 読み終えたあとに参照すべき公式ドキュメントと、次の一歩の進め方を知る

前章では、プロンプトインジェクション対策、ガードレールと評価、監視とコスト管理、Message Batches API を学びました。本章では本書の締めくくりとして、HTTPリクエスト1本から始まった道のりを振り返ります。そのうえで、実務導入の前に確かめたいことと、この先の学び方を整理します。

---

## 12.1 本書の振り返り

手を動かしてきた方の手元には、`agent-from-scratch/` というプロジェクトが育っているはずです。最初は十数行の `hello_claude.py` だけでした。今では自作のAPIクライアントから、調査レポートを作るマルチエージェントまでがそろっています。

振り返りの目的は、「なぜこの順番で、なぜこの設計なのか」を説明できるようにすることです。説明できて初めて、知識は実務で使える形に定着します。

### 12.1.1 出発点は「HTTPリクエスト1本」でした

本書は、SDKもフレームワークも使わないと決めました。SDKはSoftware Development Kit（ソフトウェア開発キット）の略です。`httpx`（エイチティーティーピーエックス）で Messages API を直接呼ぶ方針です。フレームワークのサンプルは数行で動きますが、動かなくなったときに中で何が起きているかが見えません。

HTTPから積み上げると、すべての層が自分のコードになります。第1章の「エージェント＝LLM＋ツール＋ループ」も、最終的には具体的な行に対応しました。`call_messages()`・ツール関数・`while` 文です。筆者は、この「説明できる」状態こそが、最も価値のある資産だと考えています。

> **POINT**: どれほど複雑なマルチエージェントでも、ネットワークを流れているものは同じです。「リクエストを送り、JSONを受け取り、次のリクエストを組み立てる」ことの繰り返しだけです。

この方針のおかげで、第10章では `httpx.MockTransport` を差し込めました。APIを1度も呼ばずにテストを書けたのです。通信をまるごと差し替えられるのは、HTTPを自分の手で扱っていたからこそです。

### 12.1.2 3つのパートで積み上げたもの

**基礎パート（第1〜4章）** では足場を固めました。APIがステートレス（状態を持たない）で、毎回すべての履歴を送り直していることを学びました。APIキーを `.env` で管理し、curl と httpx で最初のリクエストを送りました。第3章ではリクエストとレスポンスを1フィールドずつ読みました。`2026-10-21` 版では `temperature` などが使えないことも確認しました。Claude 4.6 以降のモデルでは prefill が使えないことも確かめました。第4章で作った `llm_client.py` は、本書の土台です。リトライ、SSE（Server-Sent Events）のパース、ログとコスト計測を備えています。

**応用パート（第5〜7章）** では、1つのエージェントを実務水準まで育てました。Claude はツールを実行せず「使いたい」と依頼するだけで、実行するのは私たちのコードです。この往復を `while` ループにした `run_agent()` から始めました。続いて、`ToolRegistry` による部品化、並列実行、`is_error` による失敗の返却、安全なファイル操作へと進みました。第7章では、トークン予算、履歴の圧縮、Prompt caching（プロンプトキャッシュ）、長期メモリ、effort を扱いました。

**実践パート（第8〜11章）** では、複数のエージェントを組み合わせました。`Agent` クラスと委譲ツールでサブエージェントを作り、`asyncio` で並列に動かしました。第9章ではAnthropicの分類に沿って6つの設計パターンを整理しました。そのうちワークフローの4種類を実装して、「エージェントにしない勇気」を学びました。第10章でレポート作成システムを完成させ、第11章で本番運用に必要な安全性・評価・監視を加えました。

| 章 | 主に学んだこと | 主な成果物 |
|---|------------|---------|
| 第1章 | LLM・ツール・ループ、ステートレスなAPI | （概念の理解） |
| 第2章 | APIキーと利用上限、uv環境、curlとhttpx | `hello_claude.py` |
| 第3章 | リクエスト・レスポンス、履歴管理、エラー | `inspect_response.py` / `params_demo.py` / `chat.py` / `error_lab.py` |
| 第4章 | 関数化、例外階層、リトライ、SSE、コスト | `llm_client.py` |
| 第5章 | Tool use の往復、エージェンティックループ | `tools/weather.py` / `one_shot_tool.py` / `agent.py` |
| 第6章 | ツール設計、レジストリ、並列実行、構造化出力 | `tool_registry.py` / `tools/files.py` / `structured_output.py` |
| 第7章 | トークン予算、圧縮、キャッシュ、メモリ | `context.py` / `tools/memory.py` |
| 第8章 | `Agent` クラス、委譲ツール、非同期並列 | `multi_agent.py` |
| 第9章 | ワークフローとエージェント、設計パターン | `patterns/` |
| 第10章 | 要件定義から CLI・テストまでの統合 | `report_agent/` / `tests/` |
| 第11章 | インジェクション対策、ガードレール、eval、バッチ | `guardrails.py` / `evals/run_eval.py` / `batch_demo.py` |

最終的なディレクトリ構成は次のとおりです。手元のプロジェクトと見比べてみてください。

```text
# agent-from-scratch/ の最終構成
agent-from-scratch/
├── .env / .gitignore / pyproject.toml   # 第2章（第10章で pytest を追加）
├── hello_claude.py                      # 第2章
├── inspect_response.py / params_demo.py / chat.py / error_lab.py  # 第3章
├── llm_client.py                        # 第4章 → 第7・8・10章で拡張
├── one_shot_tool.py                     # 第5章
├── agent.py                             # 第5章 関数版 → 第6・7章 → 第8章 Agentクラス
├── tool_registry.py / structured_output.py  # 第6章
├── context.py                           # 第7章
├── multi_agent.py                       # 第8章
├── tools/                               # weather.py / files.py / memory.py
├── patterns/                            # 第9章
├── report_agent/ / tests/               # 第10章
└── guardrails.py / evals/ / batch_demo.py   # 第11章
```

<figure id="fig-12-1">
<svg width="605" height="430" viewBox="0 0 605 430"
     xmlns="http://www.w3.org/2000/svg"
     font-family="'Noto Sans JP',sans-serif">
  <defs>
    <marker id="f12_1_arr12_1" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#333" stroke-width="1.5"/>
    </marker>
  </defs>
  <!-- 最上段: アプリケーション -->
  <rect x="20" y="20" width="180" height="60" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="110" y="45" text-anchor="middle" font-size="12" fill="#1a1a1a" font-family="Consolas,monospace" font-weight="bold">patterns/</text>
  <text x="110" y="66" text-anchor="middle" font-size="10" fill="#1a1a1a">第9章 設計パターン</text>
  <rect x="212" y="20" width="180" height="60" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="302" y="45" text-anchor="middle" font-size="12" fill="#1a1a1a" font-family="Consolas,monospace" font-weight="bold">report_agent/</text>
  <text x="302" y="66" text-anchor="middle" font-size="10" fill="#1a1a1a">第10章 レポート作成システム</text>
  <rect x="404" y="20" width="180" height="60" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="494" y="38" text-anchor="middle" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace" font-weight="bold">guardrails.py・evals/</text>
  <text x="494" y="54" text-anchor="middle" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace" font-weight="bold">batch_demo.py</text>
  <text x="494" y="71" text-anchor="middle" font-size="10" fill="#1a1a1a">第11章 本番運用</text>
  <!-- 3段目 -->
  <rect x="20" y="108" width="276" height="56" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="158" y="131" text-anchor="middle" font-size="12" fill="#1a1a1a" font-family="Consolas,monospace" font-weight="bold">agent.py</text>
  <text x="158" y="152" text-anchor="middle" font-size="10" fill="#1a1a1a">第5章 関数版→第8章 Agent</text>
  <rect x="308" y="108" width="276" height="56" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="446" y="131" text-anchor="middle" font-size="12" fill="#1a1a1a" font-family="Consolas,monospace" font-weight="bold">multi_agent.py</text>
  <text x="446" y="152" text-anchor="middle" font-size="10" fill="#1a1a1a">第8章 委譲ツール・非同期並列</text>
  <!-- 2段目 -->
  <rect x="20" y="192" width="180" height="56" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="110" y="215" text-anchor="middle" font-size="12" fill="#1a1a1a" font-family="Consolas,monospace" font-weight="bold">context.py</text>
  <text x="110" y="236" text-anchor="middle" font-size="10" fill="#1a1a1a">第7章 トークン予算・履歴の圧縮</text>
  <rect x="212" y="192" width="180" height="56" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="302" y="215" text-anchor="middle" font-size="12" fill="#1a1a1a" font-family="Consolas,monospace" font-weight="bold">tool_registry.py</text>
  <text x="302" y="236" text-anchor="middle" font-size="10" fill="#1a1a1a">第6章 ツールの部品化</text>
  <rect x="404" y="192" width="180" height="56" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="494" y="215" text-anchor="middle" font-size="12" fill="#1a1a1a" font-family="Consolas,monospace" font-weight="bold">tools/</text>
  <text x="494" y="236" text-anchor="middle" font-size="10" fill="#1a1a1a">weather・files・memory</text>
  <!-- 土台 -->
  <rect x="20" y="276" width="564" height="60" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.5"/>
  <text x="302" y="301" text-anchor="middle" font-size="14" fill="#2b6cb0" font-family="Consolas,monospace" font-weight="bold">llm_client.py</text>
  <text x="302" y="322" text-anchor="middle" font-size="11" fill="#1a1a1a">第4章 呼び出し・リトライ・SSE・ログ・コスト計測（CostTracker）</text>
  <rect x="20" y="356" width="564" height="30" rx="6" fill="#fff" stroke="#999" stroke-width="1" stroke-dasharray="4,3"/>
  <text x="302" y="376" text-anchor="middle" font-size="11" fill="#1a1a1a">Messages API（httpx で HTTP を直接呼ぶ）</text>
  <!-- 依存の向き（上の層が下の層を使う） -->
  <path d="M302 80 L302 106" stroke="#333" stroke-width="1.3" marker-end="url(#f12_1_arr12_1)"/>
  <path d="M302 164 L302 190" stroke="#333" stroke-width="1.3" marker-end="url(#f12_1_arr12_1)"/>
  <path d="M302 248 L302 274" stroke="#333" stroke-width="1.3" marker-end="url(#f12_1_arr12_1)"/>
  <path d="M302 336 L302 354" stroke="#333" stroke-width="1.3" marker-end="url(#f12_1_arr12_1)"/>
  <text x="310" y="97" font-size="9" fill="#1a1a1a">使う</text>
  <text x="310" y="181" font-size="9" fill="#1a1a1a">使う</text>
  <text x="310" y="265" font-size="9" fill="#1a1a1a">使う</text>
</svg>
  <figcaption>図12.1: agent-from-scratchの依存関係</figcaption>
</figure>

図12.1は、ファイルの依存関係です。一番下に `llm_client.py` があり、その上に `agent.py` と `tool_registry.py` が乗ります。さらにその上に、`context.py` や `multi_agent.py` が乗ります。上の層は下の層の関数だけで組み立てられています。そのため、章が進んでも前のコードをほとんど書き直さずに済みました。

たとえば第10章の CLI を実行してみましょう。`asyncio.run()` の中で、オーケストレーターの `Agent.arun()` がループを回します。各ターンで `maybe_compact()` が履歴を確認し、`acall_messages()` が API を呼びます。そして、`CostTracker` がコストを積み上げます。同期版の `run()` と `call_messages()` でも、手順は同じです。委譲ツールの中では子の `Agent` が独自の履歴で動き、結果の文字列だけが親に戻ります。どこを切り取っても、本書で1行ずつ書いたコードです。

### 12.1.3 学んだ原理の地図

個々の手順は、仕様変更で古くなるかもしれません。しかし、章をまたいで繰り返し登場した次の6つの原理は、簡単には変わりません。

1. **状態は自分で持つ**: APIはステートレスです。料金が履歴とともに増えるのも、圧縮やキャッシュが効くのも、毎回すべてを送り直しているからです（第1・3・7章）。
2. **content は type で判定し、そのまま返す**: `content[0]` を決め打ちしません。assistant の応答は、thinking ブロックも含めて改変せず履歴に戻します（第3・5・7章）。
3. **失敗は種類で扱いを分ける**: 429・5xx・接続エラーは再試行し、400系は再試行しません。ツールの失敗は `is_error` で Claude に伝えます（第3・4・6章）。
4. **コンテキストは予算です**: 100万トークンあっても上限まで使いません。サブエージェントに結果だけを返させるのも、親の予算を守る設計です（第7・8章）。
5. **権限は最小にし、取り消せない操作は人が確認する**: 渡したツールでできることは、すべて起こり得ると考えます（第6・8・11章）。
6. **単純な構成から始める**: 単一呼び出し、ワークフロー、エージェント、マルチエージェントの順に、必要なときだけ複雑にします（第9章）。

<figure id="fig-12-2">
<svg width="605" height="340" viewBox="0 0 605 340"
     xmlns="http://www.w3.org/2000/svg"
     font-family="'Noto Sans JP',sans-serif">
  <!-- 1段目 -->
  <rect x="15" y="20" width="185" height="118" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="29" y="44" font-size="14" fill="#2b6cb0" font-weight="bold">① 状態</text>
  <text x="29" y="68" font-size="11" fill="#1a1a1a">状態は自分で持つ</text>
  <text x="29" y="86" font-size="10" fill="#1a1a1a">APIはステートレス。毎回</text>
  <text x="29" y="100" font-size="10" fill="#1a1a1a">すべてを送り直している</text>
  <rect x="29" y="110" width="90" height="18" rx="9" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1"/>
  <text x="74" y="123" text-anchor="middle" font-size="10" fill="#1a1a1a">第1・3・7章</text>
  <rect x="210" y="20" width="185" height="118" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="224" y="44" font-size="14" fill="#2b6cb0" font-weight="bold">② ブロック</text>
  <text x="224" y="68" font-size="11" fill="#1a1a1a">content は type で判定し、</text>
  <text x="224" y="84" font-size="11" fill="#1a1a1a">そのまま返す</text>
  <text x="224" y="100" font-size="10" fill="#1a1a1a">thinking も改変せず履歴へ</text>
  <rect x="224" y="110" width="90" height="18" rx="9" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1"/>
  <text x="269" y="123" text-anchor="middle" font-size="10" fill="#1a1a1a">第3・5・7章</text>
  <rect x="405" y="20" width="185" height="118" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="419" y="44" font-size="14" fill="#2b6cb0" font-weight="bold">③ 失敗</text>
  <text x="419" y="68" font-size="11" fill="#1a1a1a">失敗は種類で扱いを分ける</text>
  <text x="419" y="86" font-size="10" fill="#1a1a1a">429・5xx は再試行、400系は</text>
  <text x="419" y="100" font-size="10" fill="#1a1a1a">しない。ツールは is_error</text>
  <rect x="419" y="110" width="90" height="18" rx="9" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1"/>
  <text x="464" y="123" text-anchor="middle" font-size="10" fill="#1a1a1a">第3・4・6章</text>
  <!-- 2段目 -->
  <rect x="15" y="152" width="185" height="118" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="29" y="176" font-size="14" fill="#2b6cb0" font-weight="bold">④ 予算</text>
  <text x="29" y="200" font-size="11" fill="#1a1a1a">コンテキストは予算である</text>
  <text x="29" y="218" font-size="10" fill="#1a1a1a">上限まで使わない。子には</text>
  <text x="29" y="232" font-size="10" fill="#1a1a1a">結果だけを返させる</text>
  <rect x="29" y="242" width="90" height="18" rx="9" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1"/>
  <text x="74" y="255" text-anchor="middle" font-size="10" fill="#1a1a1a">第7・8章</text>
  <rect x="210" y="152" width="185" height="118" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="224" y="176" font-size="14" fill="#2b6cb0" font-weight="bold">⑤ 権限</text>
  <text x="224" y="200" font-size="11" fill="#1a1a1a">権限は最小にし、取り消せ</text>
  <text x="224" y="216" font-size="11" fill="#1a1a1a">ない操作は人が確認する</text>
  <text x="224" y="232" font-size="10" fill="#1a1a1a">渡したツールは使われ得る</text>
  <rect x="224" y="242" width="90" height="18" rx="9" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1"/>
  <text x="269" y="255" text-anchor="middle" font-size="10" fill="#1a1a1a">第6・8・11章</text>
  <rect x="405" y="152" width="185" height="118" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="419" y="176" font-size="14" fill="#2b6cb0" font-weight="bold">⑥ 単純さ</text>
  <text x="419" y="200" font-size="11" fill="#1a1a1a">単純な構成から始める</text>
  <text x="419" y="218" font-size="10" fill="#1a1a1a">単一呼び出し→ワークフロー</text>
  <text x="419" y="232" font-size="10" fill="#1a1a1a">→エージェント→マルチ</text>
  <rect x="419" y="242" width="90" height="18" rx="9" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1"/>
  <text x="464" y="255" text-anchor="middle" font-size="10" fill="#1a1a1a">第9章</text>
  <text x="302" y="296" text-anchor="middle" font-size="11" fill="#1a1a1a">新しい機能も「状態は？ 失敗したら？ 予算は？」とこの地図に当てはめる</text>
</svg>
  <figcaption>図12.2: 本書を貫く6つの原理</figcaption>
</figure>

図12.2は、6つの原理と章の対応です。新しい機能に出会ったら、この地図に当てはめて考えてみてください。「状態はどこに持つか」「失敗したらどうなるか」「予算にどう響くか」という問いです。

不具合の調査でも同じです。いきなりプロンプトを書き換えず、まずログで `request-id`・`stop_reason`・トークン数を確かめます。HTTP・ループ・ツール・プロンプトのどの層の問題かが分かれば、直す場所は自然に決まります。

### 12.1.4 困ったときに読み返す章の道案内

実務で不具合に出会ったときは、症状から原因の候補を絞り、該当する章に戻るのが近道です。よくある組み合わせを次の表にまとめました。

| 起きている症状 | まず疑う原因 | 読み返す章 |
|-----------|---------|--------|
| 400エラーが返る | 送ってはいけないパラメータ、prefill、交互ルール違反 | 第3章 |
| 回答が途中で切れる | `max_tokens` 不足、`stop_reason` の未判定 | 第3・4章 |
| 429や529が頻発する | リトライ設定、同時実行数の上限 | 第4・8章 |
| tool_result を返すと400になる | `tool_use_id` の不一致、結果の分割返却 | 第5・6章 |
| ループが終わらない | 終了条件、最大反復回数のガード | 第5章 |
| 違うツールばかり使う | 名前や description のあいまいさ、ツールの多すぎ | 第6・8章 |
| 会話が長いと品質が落ちる | 履歴の肥大化、圧縮のしきい値 | 第7章 |
| キャッシュが効かない | system の可変値、ツール順序の変化 | 第7章 |
| 外部データの指示に従ってしまう | 間接プロンプトインジェクション、権限の過剰 | 第11章 |

この表ですべてを網羅できるわけではありません。それでも、多くの不具合はこのどれかに当てはまります。該当章のコードと自分のコードを見比べるだけで、解決の糸口が見つかることが少なくありません。

---

## 12.2 実務導入チェックリスト

手元で動いたデモと、毎日だれかが頼りにするシステムの間には、大きな距離があります。本節では、その距離を埋めるための確認項目を9つの観点にまとめました。項目を機械的に埋めるのではなく、理由に納得したうえで判断してください。

<figure id="fig-12-3">
<svg width="605" height="420" viewBox="0 0 605 420"
     xmlns="http://www.w3.org/2000/svg"
     font-family="'Noto Sans JP',sans-serif">
  <!-- 見出し -->
  <rect x="15" y="16" width="280" height="40" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.3"/>
  <text x="155" y="34" text-anchor="middle" font-size="13" fill="#1a1a1a" font-weight="bold">API連携に共通（4観点）</text>
  <text x="155" y="49" text-anchor="middle" font-size="10" fill="#1a1a1a">どのシステムにも必要な土台</text>
  <rect x="310" y="16" width="280" height="40" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.5"/>
  <text x="450" y="34" text-anchor="middle" font-size="13" fill="#2b6cb0" font-weight="bold">エージェント固有（5観点）</text>
  <text x="450" y="49" text-anchor="middle" font-size="10" fill="#1a1a1a">自律的に動くからこそ必要な項目</text>
  <!-- 左列 -->
  <g stroke="#333" stroke-width="1.1" fill="#f5f5f5">
    <rect x="15" y="68" width="280" height="54" rx="6"/>
    <rect x="15" y="130" width="280" height="54" rx="6"/>
    <rect x="15" y="192" width="280" height="54" rx="6"/>
    <rect x="15" y="254" width="280" height="54" rx="6"/>
  </g>
  <text x="29" y="90" font-size="12" fill="#1a1a1a" font-weight="bold">1 APIキーと秘密情報</text>
  <text x="29" y="110" font-size="10" fill="#1a1a1a">.env と .gitignore、環境ごとにキーを分ける</text>
  <text x="29" y="152" font-size="12" fill="#1a1a1a" font-weight="bold">2 コスト上限</text>
  <text x="29" y="172" font-size="10" fill="#1a1a1a">spend limit・1回の予算・反復回数のガード</text>
  <text x="29" y="214" font-size="12" fill="#1a1a1a" font-weight="bold">3 信頼性</text>
  <text x="29" y="234" font-size="10" fill="#1a1a1a">再試行の線引き・タイムアウト・stop_reason</text>
  <text x="29" y="276" font-size="12" fill="#1a1a1a" font-weight="bold">4 ログと監視</text>
  <text x="29" y="296" font-size="10" fill="#1a1a1a">request-id・トレースID・急変の検知</text>
  <!-- 右列 -->
  <g stroke="#2b6cb0" stroke-width="1.1" fill="#fff">
    <rect x="310" y="68" width="280" height="54" rx="6"/>
    <rect x="310" y="130" width="280" height="54" rx="6"/>
    <rect x="310" y="192" width="280" height="54" rx="6"/>
    <rect x="310" y="254" width="280" height="54" rx="6"/>
    <rect x="310" y="316" width="280" height="54" rx="6"/>
  </g>
  <text x="324" y="90" font-size="12" fill="#1a1a1a" font-weight="bold">5 評価（eval）</text>
  <text x="324" y="110" font-size="10" fill="#1a1a1a">変更のたびに eval、本番の失敗事例を追加</text>
  <text x="324" y="152" font-size="12" fill="#1a1a1a" font-weight="bold">6 権限と人間の確認</text>
  <text x="324" y="172" font-size="10" fill="#1a1a1a">ツールは最小限、取り消せない操作は承認</text>
  <text x="324" y="214" font-size="12" fill="#1a1a1a" font-weight="bold">7 プロンプトインジェクション対策</text>
  <text x="324" y="234" font-size="10" fill="#1a1a1a">外部データは資料扱い、読む役と行動する役を分離</text>
  <text x="324" y="276" font-size="12" fill="#1a1a1a" font-weight="bold">8 モデル選定と effort</text>
  <text x="324" y="296" font-size="10" fill="#1a1a1a">定数に集約、役割ごとにモデルと effort を配分</text>
  <text x="324" y="338" font-size="12" fill="#1a1a1a" font-weight="bold">9 データと運用体制</text>
  <text x="324" y="358" font-size="10" fill="#1a1a1a">責任者・停止手順・小さく試して広げる</text>
  <text x="155" y="340" text-anchor="middle" font-size="10" fill="#1a1a1a">満たしていない項目は</text>
  <text x="155" y="355" text-anchor="middle" font-size="10" fill="#1a1a1a">「意識して保留」し、段階ごとに見直す</text>
</svg>
  <figcaption>図12.3: 実務導入チェックリストの9観点</figcaption>
</figure>

図12.3の左側の4観点（キー、コスト、信頼性、ログ）は、どのAPI連携にも共通する土台です。右側の5観点は、エージェントだからこそ必要になる項目です。

### 12.2.1 APIキーと秘密情報

- [ ] キーをコード・ログ・チケットに書かず、`.env` を `.gitignore` に登録しているか（第2章）
- [ ] 開発用と本番用でキーとワークスペースを分けているか（第2章）
- [ ] 漏えい時に Console でキーを無効化・再発行する手順を全員が知っているか（第2章）

キーは、組織の名前で料金を発生させる権利そのものです。環境ごとに分けておけば、漏えいの被害を限定でき、Usage 画面で用途別の利用も確認できます。

見落としやすいのがログへの混入です。デバッグ用にヘッダーを丸ごと出力するコードを書き、そのまま残す事故はよく起こります。リリース前に、ログ出力の箇所を一度検索して確かめてください。

> **WARNING**: Git の履歴に一度でもキーが入ったら、ファイルを消すだけでは不十分です。まずキーそのものを無効化して再発行してください。

### 12.2.2 コスト上限

- [ ] Console で利用上限（spend limit）を設定しているか（第2章）
- [ ] 1回の実行の予算と、ループの最大反復回数のガードがあるか（第5・10章）
- [ ] `CostTracker` で実行ごとのトークンとコストを記録しているか（第4章）
- [ ] Prompt caching や Message Batches API を活用できる余地を検討したか（第7・11章）

エージェントは、1回の依頼でAPIを何回呼ぶかが事前に決まりません。組織全体・1回の実行・1回のループという3段階で上限を持つと、どこかの穴から想定外の請求が生まれるのを防げます。月間コストは、代表的な依頼を10件ほど実行した平均に想定件数を掛けて求めます。2〜3倍の余裕を見ておくと、最初の見積もりとして十分です。

### 12.2.3 信頼性

- [ ] 408・409・429・5xx・接続エラーを、`retry-after` 優先で再試行しているか（第4章）
- [ ] 400系（429を除く）を再試行していないか（第3・4章）
- [ ] 接続と全体のタイムアウト、最大試行回数を設定しているか（第4章）
- [ ] 本文より先に `stop_reason` を判定しているか（第3・5章）

`max_tokens` で打ち切られた応答は、文章や JSON が途中で切れています。本文だけを見て進むと、壊れたデータを下流に流してしまいます。「まず止まった理由を見る」1行が、品質を静かに支えます。

待ち時間にジッター（ランダムなばらつき）を入れるのは、第4章で学んだサンダリングハード問題を避けるためです。多数のクライアントが同じ秒数だけ待って一斉に再試行すると、回復した瞬間にまた混雑が起こります。外部のWeb APIやデータベースを呼ぶツールにも、個別のタイムアウトとリトライ方針を決めておきましょう。

### 12.2.4 ログと監視

- [ ] 全呼び出しで `request-id`・モデル・所要時間・トークン数を記録しているか（第4章）
- [ ] 1回の依頼に共通のトレースIDを振り、エージェント名とターン番号を残しているか（第5・8・11章）
- [ ] キーや個人情報をログに出していないか（第4・11章）
- [ ] コスト・ターン数・エラー率の急変に気づく仕組みがあるか（第11章）

`request-id` は、サポートへの問い合わせで呼び出しを特定するのに必要です。平均ターン数は特に役立つ指標で、Claude がツールの使い方に迷うと、コストより先にターン数が増えます。

### 12.2.5 評価（eval）

- [ ] 正常系・境界ケース・攻撃的な入力を含む eval セットがあるか（第11章）
- [ ] プロンプト・ツール・モデル・effort を変えたら eval を回しているか（第11章）
- [ ] APIを呼ばない単体テストでループや例外処理を検証しているか（第10章）
- [ ] 本番の失敗事例を eval セットに追加する運用になっているか

エージェントの出力は毎回少しずつ異なるため、「一度試して良さそうだった」では品質を保証できません。本番で起きた失敗を1件ずつテストケースにすれば、同じ失敗を繰り返さない仕組みになります。

単体テストと eval は役割が違います。単体テストはコードが仕様どおりに動くかを、APIを呼ばずに速く確かめます。eval は Claude の判断を含めた全体の品質を、実際にAPIを呼んで確かめます。前者はコミットごとに、後者はプロンプトやモデルを変えたときに回すのが現実的です。

### 12.2.6 権限と人間の確認

- [ ] 各エージェントのツールを、役割に必要な最小限に絞っているか（第8章）
- [ ] ファイル操作が作業ディレクトリの外に出られないか（第6章）
- [ ] 削除・送信・決済など取り消せない操作の前に、人間の承認があるか（第6・11章）

権限は「動作確認後に絞る」と絞り忘れが起こります。最初から最小にし、足りないものを1つずつ足しましょう。確認の範囲が広すぎると、ユーザーは読まずに承認するようになります。止めるのは取り消せない操作だけ、と線を引くのが基本です。確認画面には、何を・どこに・どう変えるのかを具体的に表示します。拒否されたら、その旨を `tool_result` で Claude に伝えます。

### 12.2.7 プロンプトインジェクション対策

- [ ] 外部データを「指示ではなく資料」として扱うよう、system で明示しているか（第11章）
- [ ] 外部データを区切りやタグで本来の指示と分けているか（第11章）
- [ ] 信頼できないデータを読むエージェントに、副作用のあるツールを渡していないか（第8・11章）
- [ ] 出力ガードレールで秘密情報や想定外のURLを確認しているか（第11章）

最も効くのは「読む役と行動する役を分ける」設計です。Webを読むリサーチャーに書き込みや送信のツールがなければ、乗っ取られても実害は限られます。対策は1つに頼らず、何層にも重ねてください。

### 12.2.8 モデル選定と effort

- [ ] モデルIDを定数 `MODEL`・`FAST_MODEL` に集約しているか（第4章）
- [ ] 単純な分類や要約に、必要以上に高価なモデルを使っていないか（第8・9章）
- [ ] `anthropic-version` を固定し、更新時に移行ガイドと eval で確かめているか（第3章）

まず `claude-opus-5-5` で目標の品質が出ることを eval で確かめます。次に、ワーカーや分類を `claude-haiku-5-5` に置き換えてスコアが保たれるかを見ます。effort も、判断の難しい役割は高めに、定型的な役割は低めに配分しましょう。

バージョンを固定するのは、予期しない挙動の変化を防ぐためです。`2026-10-21` で `temperature` が廃止されたように、バージョンによって受け付けるパラメータは変わります。

### 12.2.9 データと運用体制

- [ ] 渡すデータの種類を把握し、社内規程に照らして確認したか
- [ ] 出力に最終責任を持つ人と、異常時の停止手順が決まっているか
- [ ] 小さな範囲から試し、振り返ってから広げる計画になっているか

停止スイッチは見落とされがちですが、環境変数1つで受付を止める程度の仕組みで十分です。手作業に戻す手順もあわせて用意しておきましょう。

<figure id="fig-12-4">
<svg width="605" height="350" viewBox="0 0 605 350"
     xmlns="http://www.w3.org/2000/svg"
     font-family="'Noto Sans JP',sans-serif">
  <defs>
    <marker id="f12_4_arr12_4" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#333" stroke-width="1.5"/>
    </marker>
  </defs>
  <!-- 入口 -->
  <rect x="15" y="88" width="135" height="70" rx="6" fill="#fff" stroke="#333" stroke-width="1.2"/>
  <text x="82" y="110" text-anchor="middle" font-size="13" fill="#1a1a1a" font-weight="bold">小さく始める</text>
  <text x="82" y="130" text-anchor="middle" font-size="10" fill="#1a1a1a">影響の小さい業務を</text>
  <text x="82" y="145" text-anchor="middle" font-size="10" fill="#1a1a1a">1つ選ぶ</text>
  <path d="M150 123 L170 123 L170 58 L188 58" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f12_4_arr12_4)"/>
  <!-- 反復のサイクル -->
  <rect x="190" y="26" width="145" height="62" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="262" y="50" text-anchor="middle" font-size="13" fill="#1a1a1a" font-weight="bold">① 試行</text>
  <text x="262" y="72" text-anchor="middle" font-size="10" fill="#1a1a1a">数人で使ってみる</text>
  <rect x="440" y="26" width="145" height="62" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.5"/>
  <text x="512" y="50" text-anchor="middle" font-size="13" fill="#1a1a1a" font-weight="bold">② 計測</text>
  <text x="512" y="72" text-anchor="middle" font-size="10" fill="#1a1a1a">コスト・ターン数・エラー率</text>
  <rect x="440" y="160" width="145" height="62" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="512" y="184" text-anchor="middle" font-size="13" fill="#1a1a1a" font-weight="bold">③ 振り返り</text>
  <text x="512" y="206" text-anchor="middle" font-size="10" fill="#1a1a1a">保留した項目を見直す</text>
  <rect x="190" y="160" width="145" height="62" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="262" y="184" text-anchor="middle" font-size="13" fill="#1a1a1a" font-weight="bold">④ 範囲を広げる</text>
  <text x="262" y="206" text-anchor="middle" font-size="10" fill="#1a1a1a">数字が安定してから</text>
  <path d="M335 57 L438 57" stroke="#333" stroke-width="1.3" marker-end="url(#f12_4_arr12_4)"/>
  <path d="M512 88 L512 158" stroke="#333" stroke-width="1.3" marker-end="url(#f12_4_arr12_4)"/>
  <path d="M440 191 L337 191" stroke="#333" stroke-width="1.3" marker-end="url(#f12_4_arr12_4)"/>
  <path d="M262 160 L262 90" stroke="#333" stroke-width="1.3" marker-end="url(#f12_4_arr12_4)"/>
  <text x="387" y="120" text-anchor="middle" font-size="12" fill="#2b6cb0" font-weight="bold">反復しながら</text>
  <text x="387" y="137" text-anchor="middle" font-size="12" fill="#2b6cb0" font-weight="bold">少しずつ広げる</text>
  <!-- 見直しのタイミング -->
  <text x="302" y="258" text-anchor="middle" font-size="11" fill="#1a1a1a" font-weight="bold">チェックリストを見直すタイミング</text>
  <g stroke="#333" stroke-width="1" fill="#f5f5f5">
    <rect x="20" y="270" width="125" height="30" rx="15"/>
    <rect x="164" y="270" width="125" height="30" rx="15"/>
    <rect x="308" y="270" width="125" height="30" rx="15"/>
    <rect x="452" y="270" width="125" height="30" rx="15"/>
  </g>
  <g font-size="11" fill="#1a1a1a" text-anchor="middle">
    <text x="82" y="289">設計時</text>
    <text x="226" y="289">リリース前</text>
    <text x="370" y="289">変更時</text>
    <text x="514" y="289">定期確認</text>
  </g>
</svg>
  <figcaption>図12.4: 実務導入の段階的な進め方</figcaption>
</figure>

図12.4のように、導入は段階的に進めます。影響の小さい業務を1つ選び、数人で試し、数字が安定したら範囲を広げます。チェックリストは設計時・リリース前・変更時・定期確認のタイミングで見直してください。

> **POINT: すべてを最初から満たさなくてよい**
> 大切なのは、満たしていない項目を「意識して保留している」状態にすることです。保留した項目と理由を記録し、段階が進むたびに見直しましょう。

---

## 12.3 さらに学ぶためのリソース

エージェント開発の分野は変化が速く、本書の記述もいずれ最新の仕様と食い違うでしょう。だからこそ身につけてほしいのは、一次情報を読んで自分で確かめる力です。

### 12.3.1 Claude API 公式ドキュメント

公式ドキュメントは `https://platform.claude.com/docs/` 以下にあります。多くのページは、URLの末尾に `.md` を付けると Markdown で取得できます。

| トピック | ページ（`https://platform.claude.com/docs/en/` 以下） | 対応章 |
|--------|----------------------------------------------|------|
| Messages API リファレンス | `api/messages` | 第3章 |
| APIバージョン / 移行ガイド | `api/versioning` / `api/migration-2026-10-21` | 第3章 |
| エラー / レート制限 | `api/errors` / `api/rate-limits` | 第3・4章 |
| ストリーミング | `build-with-claude/streaming` | 第4章 |
| モデル一覧 / 料金 | `models/overview` / `about-claude/pricing` | 第2・4・7章 |
| Tool use 概要 | `agents-and-tools/tool-use/overview` | 第5・6章 |
| サーバーツール | `agents-and-tools/tool-use/server-tools` | 第6・10章 |
| Prompt caching / Token counting | `build-with-claude/prompt-caching` / `build-with-claude/token-counting` | 第7章 |
| Thinking / Effort | `build-with-claude/thinking` / `build-with-claude/effort` | 第7章 |
| Batch processing | `build-with-claude/batch-processing` | 第11章 |

特に Messages API リファレンスは定期的に読み返してください。第3章の経験があれば、以前よりずっと読みやすく感じるはずです。モデル一覧と料金のページは、`MODEL` と `CostTracker` の単価表を最新の値に合わせるために使います。

APIバージョンと移行ガイドは、`llm_client.py` の `API_VERSION` を上げる前に必ず確認するページです。エラーとレート制限のページは、本番運用を始めたら手元に置いておきましょう。429が増えてきたら、レスポンスヘッダーの情報と Console の画面を見て、リトライ設定と利用量を見直します。サーバーツールと `pause_turn` は、本書では概要にとどめました。詳しい説明は、Server tools のページにあります。

> **TIP**: ドキュメントは本書のコードを横に開いて読むのがおすすめです。対応する行が見つからない記述は、まだ取り込んでいない機能だということです。

### 12.3.2 Building effective agents

Anthropic の記事「Building effective agents」も、ぜひ読み返してください。URLは `https://www.anthropic.com/research/building-effective-agents` です。第9章の設計パターンは、この記事の考え方をもとにしています。`patterns/` や `report_agent/` を自分で書いた今なら、記事の一文ごとに具体的なコードの姿が浮かぶはずです。

### 12.3.3 別教材で扱う関連製品

本書で扱わなかった製品の位置づけだけを紹介します。

- **Claude Code**: Anthropic のエージェント型コーディングツールです（別教材で扱います）。
- **Claude Agent SDK**: エージェントの仕組みを自分のアプリケーションに組み込むためのSDKです（別教材で扱います）。
- **Anthropic 公式クライアントSDK**: 本書で自作したHTTP呼び出しやリトライを各言語向けに提供するライブラリです。別教材で扱います。

スクラッチで作った経験があれば、これらを使うときも中で何が起きているかを想像できます。

<figure id="fig-12-5">
<svg width="605" height="400" viewBox="0 0 605 400"
     xmlns="http://www.w3.org/2000/svg"
     font-family="'Noto Sans JP',sans-serif">
  <defs>
    <marker id="f12_5_arr12_5" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#333" stroke-width="1.5"/>
    </marker>
  </defs>
  <!-- 上: 公式ドキュメント -->
  <rect x="152" y="16" width="300" height="80" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="302" y="39" text-anchor="middle" font-size="13" fill="#1a1a1a" font-weight="bold">Claude API 公式ドキュメント</text>
  <text x="302" y="60" text-anchor="middle" font-size="10" fill="#1a1a1a" font-family="Consolas,monospace">https://platform.claude.com/docs/</text>
  <text x="302" y="80" text-anchor="middle" font-size="10" fill="#1a1a1a">Messages API・Tool use・Prompt caching など</text>
  <!-- 中央: 本書 -->
  <rect x="207" y="160" width="190" height="76" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.5"/>
  <text x="302" y="184" text-anchor="middle" font-size="14" fill="#2b6cb0" font-weight="bold">本書</text>
  <text x="302" y="205" text-anchor="middle" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">agent-from-scratch/</text>
  <text x="302" y="225" text-anchor="middle" font-size="10" fill="#1a1a1a">HTTPから自作した土台</text>
  <!-- 左下: 設計記事 -->
  <rect x="15" y="280" width="215" height="80" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="122" y="303" text-anchor="middle" font-size="13" fill="#1a1a1a" font-weight="bold">設計の記事</text>
  <text x="122" y="324" text-anchor="middle" font-size="10" fill="#1a1a1a">Building effective agents</text>
  <text x="122" y="344" text-anchor="middle" font-size="10" fill="#1a1a1a">第9章の設計パターンの元</text>
  <!-- 右下: 別教材 -->
  <rect x="375" y="280" width="215" height="80" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="482" y="303" text-anchor="middle" font-size="13" fill="#1a1a1a" font-weight="bold">別教材で扱う製品</text>
  <text x="482" y="324" text-anchor="middle" font-size="10" fill="#1a1a1a">Claude Code・Claude Agent SDK</text>
  <text x="482" y="344" text-anchor="middle" font-size="10" fill="#1a1a1a">公式クライアントSDK</text>
  <!-- 3方向の矢印 -->
  <path d="M302 160 L302 98" stroke="#333" stroke-width="1.3" marker-end="url(#f12_5_arr12_5)"/>
  <text x="310" y="133" font-size="10" fill="#1a1a1a">最新の仕様を一次情報で確かめる</text>
  <path d="M240 236 L160 278" stroke="#333" stroke-width="1.3" marker-end="url(#f12_5_arr12_5)"/>
  <text x="196" y="250" text-anchor="end" font-size="10" fill="#1a1a1a">考え方を深める</text>
  <path d="M364 236 L444 278" stroke="#333" stroke-width="1.3" marker-end="url(#f12_5_arr12_5)"/>
  <text x="408" y="250" font-size="10" fill="#1a1a1a">中の仕組みを想像して使う</text>
</svg>
  <figcaption>図12.5: 次に学ぶリソースの地図</figcaption>
</figure>

### 12.3.4 次の一歩の具体案

エージェント開発の力は、読んだ量より作った数で伸びます。本書のコードベースを出発点に、次の順で手を動かしてみてください。

1. **業務の小さな作業を1つ自動化する**: 議事録の要約やメールの分類など、30分程度の定型作業を選びます。まず単一呼び出しやプロンプトチェーンで解けないか試し、所要時間とコストを数字で記録します。
2. **自作ツールを3つ追加する**: 社内APIの呼び出しや、読み取り専用のデータベース検索などを `ToolRegistry` に登録します。そして、意図どおりに選ばれるかを確かめます。
3. **eval セットを育てる**: 20〜30件のケースを用意し、プロンプトや effort を1つずつ変えてスコアを比べます。調整が勘から数字に変わります。
4. **別の言語で書き直す**: `llm_client.py` と `agent.py` を TypeScript や Go で書き直します。すると、APIの本質と Python 固有の書き方が分かれて見えます。
5. **CLI 以外の入り口を作る**: 簡単なWeb画面やチャットボットにつなぎます。`stream_messages()` の `on_text` で逐次表示します。複数のユーザーの同時実行や履歴の保存など、第7・8章の知識を使う新しい課題が見えてきます。

どの案でも、`CostTracker` と Console の利用上限は必ず有効にしておきましょう。

### 12.3.5 学び続けるための習慣

最後に、変化の速い分野で学び続けるための習慣を3つ紹介します。

1つ目は、変更履歴を追うことです。月に1回でよいので公式ドキュメントの更新情報に目を通し、自分のコードに影響する変更がないかを確かめます。モデルの廃止予定やパラメータの変更は、気づかずにいると突然エラーとして表面化します。

2つ目は、小さな実験を記録することです。`params_demo.py` のような実験用ファイルを気軽に作り、結果を短いメモと一緒に残しておきましょう。数か月後の自分にとって貴重な資料になります。

3つ目は、学んだことを人に説明することです。社内の勉強会で `llm_client.py` やエージェンティックループを紹介してみてください。人に説明しようとすると、理解のあいまいな部分がはっきりします。本書が目指した「説明できる状態」は、教えることで最も確実に身につきます。

---

## COLUMN: 新しい機能に出会ったときの4つの問い

Claude API には、これからも新しい機能が追加されていくはずです。名前だけを見ると、まったく新しい仕組みに感じるかもしれません。しかし多くは、本書で学んだ要素の組み合わせとして理解できます。

筆者は新しい機能に出会うと、次の4つを順に確かめます。リクエストのどのフィールドに何を書くのか。レスポンスにどんなブロックや `stop_reason` が現れるのか。処理は Anthropic 側で動くのか、自分のコードで動くのか。料金とコンテキストの予算にどう響くのか、の4つです。

たとえばサーバーツールなら、`tools` に専用の型を書き、結果のブロックが返ります。`pause_turn` で止まることがあります。実行は Anthropic 側で、結果はコンテキストを消費します。こう整理すると、自作ツールとの違いが一目で分かります。新しい機能を「魔法」ではなく「HTTPのやり取りの拡張」として読めることが、スクラッチで学んだ人の強みです。

---

## 本章のまとめ

本章で学んだことを整理します：

- 本書は `llm_client.py` を土台に、部品を積み上げてきました。部品は `agent.py`・`tool_registry.py`・`context.py`・`multi_agent.py` と続きます。最後に `patterns/` と `report_agent/` を加えました。その全体を、状態・ブロック・失敗・予算・権限・単純さという6つの原理が貫いています。
- 実務導入の前には、キー、コスト、信頼性、ログ、評価、権限、インジェクション対策、モデル選定、運用体制の9観点を確認します。満たしていない項目は意識して保留し、小さく導入して広げましょう。
- 次の学習には、Claude API 公式ドキュメントと「Building effective agents」が役立ちます。Claude Code・Claude Agent SDK・公式クライアントSDKは別教材で扱います。

本書に次の章はありません。次の一歩は、あなたの手元の `agent-from-scratch/` から始まります。

---

## おわりに: 読者のみなさんへ

ここまで読み進めていただき、本当にありがとうございました。

第2章で curl から送った最初のリクエストに返ってきたのは、ただのJSONでした。そのJSONを読み、関数にし、ループにし、部品にして、ここまで来ました。今のあなたは、ループが止まらなければ終了条件を、コストが膨らめば履歴とキャッシュを確かめられます。この「どこを見ればよいか分かる」感覚は、どんな道具を使うときにも支えになるはずです。

モデルは賢くなり、機能は増え、今日の常識は明日には古くなるかもしれません。それでも、リクエストを送りJSONを受け取るという基本は変わりません。変化の速い分野だからこそ、変わらない土台を自分の手で作ったことに価値があります。

最後のお願いは、小さく作り続けてほしいということです。明日の業務の30分を楽にするエージェントを1つ作り、測り、直し、育ててください。あなたが次に作るエージェントが、誰かの役に立つことを心から願っています。
