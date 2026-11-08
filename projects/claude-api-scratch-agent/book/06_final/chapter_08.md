# 第8章: マルチエージェントを自作する
# EN-TITLE: MULTI-AGENT FROM SCRATCH
# TAGS: サブエージェント, 委譲ツール, asyncio, 並列実行, 最小権限

## この章で学ぶこと

本章では以下を学びます：

- 単一エージェントの限界を説明し、サブエージェント（独立した `messages` 配列で動く子ループ）の利点とコストを判断できるようになる
- `Agent` クラスと委譲ツール `delegate_research` を実装し、子エージェントの結果だけを親に返せるようになる
- 複数のサブエージェントを安全に並列実行できるようになる。使う道具は `httpx.AsyncClient` と `asyncio.gather`・`asyncio.Semaphore`

前章では、コンテキストを管理する方法を学びました。
トークンを数え、履歴を圧縮し、Prompt caching（プロンプトキャッシュ）と長期メモリを使う方法です。
本章では、その「コンテキストを管理する」という発想をもう一歩進めます。1つのコンテキストに詰め込むのではなく、仕事ごとに別のコンテキストを用意して、複数のエージェントに分担させる仕組みを自分の手で組み立てます。

---

## 8.1 単一エージェントの限界とマルチエージェント

ここまで育ててきたエージェントは、1つの `messages` 配列を持ち、1つのループの中でツールを呼び続ける作りでした。
天気を調べる、ファイルを読む、メモを保存するといった仕事なら、これで十分に役立ちます。
では、調べる対象が10件に増え、それぞれに何ファイルも読む必要があるとしたらどうでしょうか。
1つのループがすべてを抱え込むと、どこかで無理が出てきます。
この節では、その「無理」の正体を3つに分けて整理し、マルチエージェントという解決策の利点とコストを見ていきます。

### 単一エージェントで起きる3つの問題

1つ目の問題は**ツール過多**です。
エージェントに機能を足すたびにツールが増え、やがて20個、30個と並ぶようになります。
ツールの定義は毎回のリクエストで `tools` として送られ、そのぶんの入力トークンを消費します。
さらに困るのは、選択肢が増えるほどモデルが「どのツールを使うべきか」で迷いやすくなることです。
似た名前のツールを取り違えたり、本来不要なツールを呼んだりする失敗は、ツールの数に比例して増えていきます。

2つ目の問題は**長大な履歴**です。
第7章で見たとおり、エージェントのループは毎ターン、これまでの会話とツール結果をすべて送り直します。
調査のためにファイルを10個読めば、その中身がすべて履歴に積み上がります。
最終的な回答に必要なのは各ファイルの要点だけでも、履歴には全文が残り続けます。
圧縮（compaction）で抑えることはできますが、要約のたびに細部が失われるという別の問題も生まれます。

3つ目の問題は**役割の混在**です。
「資料を調べる」「比較表をまとめる」「文章を校正する」は、性質の違う仕事です。
これらを1つの system プロンプトに書き込むと、指示どうしがぶつかります。
「調査では網羅的に」「まとめでは簡潔に」という指示が同じプロンプトに並ぶと、モデルはどちらを優先すべきか判断しにくくなります。
人間の組織でも、1人に調査・執筆・校正をすべて任せると、どれも中途半端になりがちですよね。
LLM（Large Language Model、大規模言語モデル）でも同じことが起きます。

| 問題 | 何が起きるか | 典型的な症状 |
|---|---|---|
| ツール過多 | 定義のトークンが増え、選択を誤りやすくなる | 似たツールの取り違え、不要なツール呼び出し |
| 長大な履歴 | 不要な詳細が履歴に残り続ける | コスト増、応答の遅れ、重要な指示の見落とし |
| 役割の混在 | 性質の違う指示が1つのプロンプトで衝突する | 出力の粒度がぶれる、手順の取りこぼし |

3つの問題には共通点があります。
いずれも「1つのコンテキストにすべてを入れている」ことが原因です。
第7章では、このコンテキストを削ったり再利用したりする工夫を学びました。
本章では発想を変えて、コンテキストそのものを分けることを考えます。

### コンテキストの汚染という考え方

もう少し具体的な場面で考えてみましょう。
3つの製品の資料を読み比べて、料金・対応OS・サポート体制の比較表を作るエージェントを想像してください。
単一エージェントは、製品Aの資料を読み、製品Bの資料を読み、製品Cの資料を読み、最後に表をまとめます。
このとき、製品Cについて考えている最中の履歴には、製品Aと製品Bの資料の全文が残っています。

製品Cの料金を読み取るとき、製品Aの資料の細部はまったく必要ありません。
それどころか、似た表現が並んでいるせいで、製品Aの数字を製品Cのものとして書いてしまう事故も起こり得ます。
このように、今の仕事に関係のない情報がコンテキストに混ざり、判断の質を下げる状態を、本書では**コンテキストの汚染**と呼びます。
コンテキストが長くなるほど、モデルが本当に注目すべき部分を見つけにくくなるという性質は、第7章でも触れたとおりです。

汚染を防ぐいちばん素直な方法は、「製品Aだけを考えるコンテキスト」「製品Bだけを考えるコンテキスト」を別々に用意することです。
それぞれの調査が終わったら、要点だけを取り出して、まとめ役のコンテキストに渡します。
まとめ役は資料の全文を見ることなく、整理された要点だけをもとに比較表を作れます。
これが、マルチエージェントの基本的な発想です。

<figure id="fig-8-1">
<svg width="605" height="385" viewBox="0 0 605 385" xmlns="http://www.w3.org/2000/svg" font-family="'Noto Sans JP',sans-serif">
  <defs>
    <marker id="f8_1_ar81" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#2b6cb0" stroke-width="1.5"/>
    </marker>
  </defs>
  <!-- 左: 単一エージェント -->
  <text x="105" y="30" text-anchor="middle" font-size="13" fill="#1a1a1a" font-weight="bold">単一エージェント</text>
  <text x="105" y="48" text-anchor="middle" font-size="11" fill="#1a1a1a">1本の長い履歴</text>
  <rect x="40" y="62" width="130" height="24" fill="#f5f5f5" stroke="#333" stroke-width="1"/>
  <text x="105" y="78" text-anchor="middle" font-size="11" fill="#1a1a1a">依頼</text>
  <rect x="40" y="86" width="130" height="70" fill="#f5f5f5" stroke="#333" stroke-width="1"/>
  <text x="105" y="125" text-anchor="middle" font-size="11" fill="#1a1a1a">資料Aの全文</text>
  <rect x="40" y="156" width="130" height="70" fill="#f5f5f5" stroke="#333" stroke-width="1"/>
  <text x="105" y="195" text-anchor="middle" font-size="11" fill="#1a1a1a">資料Bの全文</text>
  <rect x="40" y="226" width="130" height="70" fill="#f5f5f5" stroke="#333" stroke-width="1"/>
  <text x="105" y="265" text-anchor="middle" font-size="11" fill="#1a1a1a">資料Cの全文</text>
  <rect x="40" y="296" width="130" height="24" fill="#f5f5f5" stroke="#333" stroke-width="1"/>
  <text x="105" y="312" text-anchor="middle" font-size="11" fill="#1a1a1a">比較表を作成</text>
  <text x="105" y="344" text-anchor="middle" font-size="11" fill="#1a1a1a">製品Cを考える時も</text>
  <text x="105" y="360" text-anchor="middle" font-size="11" fill="#1a1a1a">A・Bの全文が残る（汚染）</text>
  <!-- 区切り -->
  <line x1="210" y1="15" x2="210" y2="370" stroke="#999" stroke-width="1" stroke-dasharray="4,4"/>
  <!-- 右: マルチエージェント -->
  <text x="410" y="30" text-anchor="middle" font-size="13" fill="#1a1a1a" font-weight="bold">マルチエージェント</text>
  <text x="410" y="48" text-anchor="middle" font-size="11" fill="#1a1a1a">親1本＋子3本の短い履歴</text>
  <!-- 親 -->
  <text x="335" y="128" text-anchor="end" font-size="12" fill="#1a1a1a" font-weight="bold">親</text>
  <rect x="345" y="62" width="130" height="24" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.2"/>
  <text x="410" y="78" text-anchor="middle" font-size="11" fill="#1a1a1a">依頼</text>
  <rect x="345" y="86" width="130" height="24" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.2"/>
  <text x="410" y="102" text-anchor="middle" font-size="11" fill="#1a1a1a">報告A</text>
  <rect x="345" y="110" width="130" height="24" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.2"/>
  <text x="410" y="126" text-anchor="middle" font-size="11" fill="#1a1a1a">報告B</text>
  <rect x="345" y="134" width="130" height="24" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.2"/>
  <text x="410" y="150" text-anchor="middle" font-size="11" fill="#1a1a1a">報告C</text>
  <rect x="345" y="158" width="130" height="24" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.2"/>
  <text x="410" y="174" text-anchor="middle" font-size="11" fill="#1a1a1a">比較表を作成</text>
  <text x="485" y="128" font-size="11" fill="#2b6cb0" font-weight="bold">報告だけが</text>
  <text x="485" y="144" font-size="11" fill="#2b6cb0" font-weight="bold">親に戻る</text>
  <!-- 子から親への報告 -->
  <path d="M282 214 L372 188" stroke="#2b6cb0" stroke-width="1.3" marker-end="url(#f8_1_ar81)"/>
  <path d="M407 214 L410 188" stroke="#2b6cb0" stroke-width="1.3" marker-end="url(#f8_1_ar81)"/>
  <path d="M532 214 L448 188" stroke="#2b6cb0" stroke-width="1.3" marker-end="url(#f8_1_ar81)"/>
  <!-- 子A -->
  <text x="282" y="229" text-anchor="middle" font-size="11" fill="#1a1a1a">子A（Alpha）</text>
  <rect x="230" y="236" width="105" height="22" fill="#f5f5f5" stroke="#333" stroke-width="1"/>
  <text x="282" y="251" text-anchor="middle" font-size="10" fill="#1a1a1a">指示</text>
  <rect x="230" y="258" width="105" height="70" fill="#f5f5f5" stroke="#333" stroke-width="1"/>
  <text x="282" y="297" text-anchor="middle" font-size="10" fill="#1a1a1a">資料Aの全文</text>
  <rect x="230" y="328" width="105" height="22" fill="#f5f5f5" stroke="#333" stroke-width="1"/>
  <text x="282" y="343" text-anchor="middle" font-size="10" fill="#1a1a1a">報告</text>
  <!-- 子B -->
  <text x="407" y="229" text-anchor="middle" font-size="11" fill="#1a1a1a">子B（Beta）</text>
  <rect x="355" y="236" width="105" height="22" fill="#f5f5f5" stroke="#333" stroke-width="1"/>
  <text x="407" y="251" text-anchor="middle" font-size="10" fill="#1a1a1a">指示</text>
  <rect x="355" y="258" width="105" height="70" fill="#f5f5f5" stroke="#333" stroke-width="1"/>
  <text x="407" y="297" text-anchor="middle" font-size="10" fill="#1a1a1a">資料Bの全文</text>
  <rect x="355" y="328" width="105" height="22" fill="#f5f5f5" stroke="#333" stroke-width="1"/>
  <text x="407" y="343" text-anchor="middle" font-size="10" fill="#1a1a1a">報告</text>
  <!-- 子C -->
  <text x="532" y="229" text-anchor="middle" font-size="11" fill="#1a1a1a">子C（Gamma）</text>
  <rect x="480" y="236" width="105" height="22" fill="#f5f5f5" stroke="#333" stroke-width="1"/>
  <text x="532" y="251" text-anchor="middle" font-size="10" fill="#1a1a1a">指示</text>
  <rect x="480" y="258" width="105" height="70" fill="#f5f5f5" stroke="#333" stroke-width="1"/>
  <text x="532" y="297" text-anchor="middle" font-size="10" fill="#1a1a1a">資料Cの全文</text>
  <rect x="480" y="328" width="105" height="22" fill="#f5f5f5" stroke="#333" stroke-width="1"/>
  <text x="532" y="343" text-anchor="middle" font-size="10" fill="#1a1a1a">報告</text>
  <text x="407" y="372" text-anchor="middle" font-size="11" fill="#666">子の履歴は終了後に捨てられ、親には持ち込まれない</text>
</svg>
  <figcaption>図8.1: 単一エージェントとマルチエージェントのコンテキスト</figcaption>
</figure>

### サブエージェントとは何か

本書でいう**サブエージェント**とは、親エージェントから仕事を任される子のエージェンティックループのことです。
子は、親とは独立した `messages` 配列で動きます。
「独立した」というのが最大のポイントです。
子は親の会話履歴を一切見ません。
親から渡されるのは、仕事の内容を書いた1つのメッセージだけです。

子は、受け取ったメッセージを最初の user メッセージとして、新しい `messages` 配列を作ります。
そこから先は、第5章から作ってきたループとまったく同じです。
モデルを呼び、`stop_reason` が `tool_use` ならツールを実行し、結果を返してまた呼びます。
`end_turn` になったら、最後のテキストを結果として親に返し、子の `messages` 配列は捨てられます。

ここで改めて、第1章で説明した「APIはステートレス（状態を持たない）」という性質を思い出してください。
Messages API（メッセージズ エーピーアイ）は、送られてきた `messages` 配列だけを見て応答を作ります。
サーバー側に「前の会話」を覚えておく仕組みはありません。
つまり、別の `messages` 配列を作って送れば、それだけで完全に別のエージェントになるということです。
特別な仕組みは何も要りません。
マルチエージェントを「自作できる」のは、このステートレス性のおかげなんです。

親から見ると、サブエージェントはツールの1つにすぎません。
親のモデルは `delegate_research` のようなツールを呼び出し、その tool_result として子の調査結果を受け取ります。
親の履歴に残るのは「この観点で調べて」という依頼と、「調べた結果はこうでした」という報告だけです。
子が途中で読んだファイルの全文や、試行錯誤のやり取りは、親の履歴には一切入りません。

<figure id="fig-8-2">
<svg width="605" height="345" viewBox="0 0 605 345" xmlns="http://www.w3.org/2000/svg" font-family="'Noto Sans JP',sans-serif">
  <defs>
    <marker id="f8_2_ar82" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#333" stroke-width="1.5"/>
    </marker>
    <marker id="f8_2_ar82b" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#2b6cb0" stroke-width="1.5"/>
    </marker>
  </defs>
  <!-- 親ループ -->
  <text x="20" y="110" font-size="12" fill="#1a1a1a" font-weight="bold">親ループ（orchestrator）</text>
  <rect x="20" y="40" width="150" height="40" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="95" y="65" text-anchor="middle" font-size="12" fill="#1a1a1a">親：モデルを呼ぶ</text>
  <rect x="220" y="40" width="160" height="40" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="300" y="57" text-anchor="middle" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">tool_use</text>
  <text x="300" y="72" text-anchor="middle" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">delegate_research</text>
  <rect x="430" y="40" width="145" height="40" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="502" y="65" text-anchor="middle" font-size="12" fill="#1a1a1a">ツール関数を実行</text>
  <path d="M170 60 L218 60" stroke="#333" stroke-width="1.3" marker-end="url(#f8_2_ar82)"/>
  <path d="M380 60 L428 60" stroke="#333" stroke-width="1.3" marker-end="url(#f8_2_ar82)"/>
  <!-- 親へ戻る -->
  <path d="M592 265 L598 265 L598 22 L95 22 L95 38" fill="none" stroke="#2b6cb0" stroke-width="1.5" marker-end="url(#f8_2_ar82b)"/>
  <text x="300" y="16" text-anchor="middle" font-size="11" fill="#2b6cb0" font-weight="bold">tool_result（報告のテキストだけ）</text>
  <!-- 子ループの枠 -->
  <rect x="185" y="130" width="400" height="200" rx="6" fill="none" stroke="#2b6cb0" stroke-width="1.2" stroke-dasharray="5,4"/>
  <text x="200" y="150" font-size="12" fill="#2b6cb0" font-weight="bold">子ループ（researcher）</text>
  <!-- ツール関数から子ループを起動 -->
  <path d="M485 80 L485 163" stroke="#333" stroke-width="1.3" marker-end="url(#f8_2_ar82)"/>
  <text x="478" y="118" text-anchor="end" font-size="10" fill="#1a1a1a" font-family="Consolas,monospace">researcher.run(task)</text>
  <rect x="400" y="165" width="170" height="40" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="485" y="182" text-anchor="middle" font-size="11" fill="#1a1a1a">新しい messages を作成</text>
  <text x="485" y="197" text-anchor="middle" font-size="10" fill="#1a1a1a">（指示を最初の user に）</text>
  <rect x="200" y="165" width="160" height="40" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.2"/>
  <text x="280" y="190" text-anchor="middle" font-size="12" fill="#1a1a1a">子：モデルを呼ぶ</text>
  <path d="M400 185 L362 185" stroke="#333" stroke-width="1.3" marker-end="url(#f8_2_ar82)"/>
  <rect x="200" y="245" width="160" height="40" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.2"/>
  <text x="280" y="262" text-anchor="middle" font-size="10" fill="#1a1a1a" font-family="Consolas,monospace">list_files / read_file</text>
  <text x="280" y="277" text-anchor="middle" font-size="11" fill="#1a1a1a">を実行</text>
  <path d="M255 205 L255 243" stroke="#333" stroke-width="1.3" marker-end="url(#f8_2_ar82)"/>
  <text x="250" y="228" text-anchor="end" font-size="10" fill="#1a1a1a" font-family="Consolas,monospace">tool_use</text>
  <path d="M305 245 L305 207" stroke="#333" stroke-width="1.3" marker-end="url(#f8_2_ar82)"/>
  <text x="310" y="228" font-size="10" fill="#1a1a1a" font-family="Consolas,monospace">tool_result</text>
  <rect x="400" y="245" width="170" height="40" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="485" y="262" text-anchor="middle" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">end_turn</text>
  <text x="485" y="277" text-anchor="middle" font-size="11" fill="#1a1a1a">最後のテキストを報告</text>
  <path d="M360 195 L410 243" stroke="#333" stroke-width="1.3" marker-end="url(#f8_2_ar82)"/>
  <path d="M570 265 L592 265" stroke="#2b6cb0" stroke-width="1.5"/>
  <text x="385" y="315" text-anchor="middle" font-size="11" fill="#666">終了後、子の messages は捨てられる（親の履歴には入らない）</text>
</svg>
  <figcaption>図8.2: サブエージェントは子のループ</figcaption>
</figure>

> **POINT: サブエージェントの正体**
> サブエージェントは特別なAPI機能ではありません。親のツール関数の中で、新しい `messages` 配列を作ってエージェンティックループをもう1本回しているだけです。HTTPリクエストの送り先も、ヘッダーも、これまでとまったく同じです。

### マルチエージェントの利点

サブエージェントに仕事を分けると、3つの利点が得られます。

1つ目は**集中**です。
子のコンテキストには、その子の仕事に必要な情報しか入りません。
system プロンプトも「資料を調べて要点を返す」という1つの役割に絞って書けます。
ツールも、その仕事に必要なものだけを渡せばよくなります。
選択肢が少なく、指示が明確で、履歴が短い。
この3つがそろうと、モデルは自分の仕事に集中でき、出力の質が安定します。

2つ目は**並列**です。
製品A・B・Cの調査は互いに依存していません。
製品Aの結果を見なくても、製品Bの調査は始められます。
単一エージェントでは順番に処理するしかありませんが、子エージェントに分ければ、3つを同時に走らせることができます。
API呼び出しの待ち時間の多くは、モデルが文章を生成している時間です。
この待ち時間を重ね合わせれば、全体の所要時間を大きく短縮できます。
8.3節では、この並列化を `asyncio` で実装します。

3つ目は**モデルの使い分け**です。
単一エージェントでは、すべての仕事を同じモデルで処理するしかありません。
難しい判断が1か所でもあれば、全体を高性能なモデルで動かすことになります。
仕事を分ければ、役割ごとに最適なモデルを選べます。
たとえば、まとめ役は `claude-opus-5-5`、資料の読み取りは `claude-haiku-5-5` という分け方です。
Haiku（ハイク）の料金は、1回のプロンプトが10万トークン以下なら Opus（オーパス）の40分の1です。
そのため、大量の資料を読む仕事を任せると、コストを大きく抑えられます。

### マルチエージェントのコスト

もちろん、良いことばかりではありません。
マルチエージェントには、見落としやすいコストがいくつもあります。

最も大きいのは**トークン消費の増加**です。
子エージェントは、それぞれが自分の system プロンプトとツール定義を毎ターン送ります。
親も、子に仕事を頼むための指示文を生成し、子の報告を読み込みます。
同じ仕事を単一エージェントで処理するより、合計のトークン数は多くなるのが普通です。
「コンテキストを分ければ節約になる」と思われがちですが、節約できるのは1本あたりの履歴の長さであり、全体の合計ではない点に注意してください。

次に**情報の欠落**があります。
子から親に渡るのは要約された結果だけです。
子が「重要ではない」と判断して省いた情報は、親からは見えません。
後になって「やはりあの細部が必要だった」と分かっても、子の履歴はすでに捨てられています。
もう一度子を起動して調べ直すしかなく、そのぶんコストも時間もかかります。

さらに**調整とデバッグの難しさ**も増えます。
単一エージェントなら、1本の履歴を上から読めば何が起きたか分かります。
マルチエージェントでは、親の履歴と複数の子の履歴を突き合わせないと、失敗の原因が見えてきません。
親の指示があいまいだったのか、子の読み取りが誤っていたのか、切り分けるだけでも手間がかかります。
ログの設計が単一エージェント以上に重要になるのは、このためです。

| 観点 | 単一エージェント | マルチエージェント |
|---|---|---|
| 1本あたりの履歴 | 長くなりやすい | 短く保てる |
| 合計のトークン数 | 少なめ | 多め（指示・報告・定義の重複） |
| 所要時間 | 処理を順番に積み上げる | 独立した仕事を並列化できる |
| モデルの選択 | 全体で1つ | 役割ごとに選べる |
| 情報の流れ | すべて履歴に残る | 要約された結果だけが親に届く |
| デバッグ | 1本の履歴を読めばよい | 複数の履歴を突き合わせる必要がある |

### どんなときに分けるべきか

利点とコストを比べると、マルチエージェントが向いている仕事の条件が見えてきます。
本書では、次の3つのうち少なくとも1つに当てはまるときに、サブエージェントへの分割を検討することをおすすめします。

- **独立した部分に分けられる**: 製品ごと、資料ごと、観点ごとのように、互いの結果を待たずに進められる
- **途中経過が大きく、結果は小さい**: 大量に読むが、親が必要とするのは要点だけ
- **役割の性質が大きく違う**: 網羅的な調査と、簡潔なまとめのように、指示や適したモデルが異なる

逆に、仕事が順番に強く依存している場合や、途中経過の細部が最終判断に必要な場合は、無理に分けないほうがうまくいきます。
たとえば、1つのバグを追いかけるデバッグ作業は、前の手がかりが次の調査を決めるため、分割にはあまり向きません。
この判断については、章末のコラムでもう一度取り上げます。

> **NOTE**: 親が仕事を分解して子に任せ、結果をまとめる形には名前があります。Anthropic社の記事「Building effective agents」で紹介されているパターンです。記事では、**オーケストレーター-ワーカー**（Orchestrator-workers）と呼ばれています。第9章では、このパターンをほかの設計パターンと並べて整理します。本章では、その土台となる「子ループを起動して結果を受け取る仕組み」を実装することに集中します。

ここまでで、なぜコンテキストを分けるのか、分けると何が得られ何を失うのかを整理できました。
次の節では、いよいよコードに入ります。
まず第6・7章で育てた `run_agent()` を `Agent` クラスに作り替え、その上に委譲ツールを載せていきます。

---

## 8.2 サブエージェントをツールとして実装する

サブエージェントを作るには、エージェンティックループを「何本でも」「設定を変えて」起動できる必要があります。
ところが、第6・7章の `run_agent()` は関数なので、system プロンプトやツール、モデルを毎回引数で渡さなければなりません。
親と子で設定が違い、子が何種類もあるとなると、引数の受け渡しだけで混乱してしまいます。
そこでこの節では、まずエージェントの設定とループを1つにまとめた `Agent` クラスを作ります。
そのうえで、親のツールから子の `Agent` を起動する委譲ツール `delegate_research` を実装します。

### 第7章までの run_agent を振り返る

リファクタリング（動作を変えずにコードの構造を整理すること）の前に、出発点を確認しておきましょう。
第7章の時点で、`agent.py` の `run_agent()` はおおよそ次の流れになっていました。

1. ユーザーの入力を最初の user メッセージとして `messages` を作る
2. 各ターンの前に `maybe_compact()` で履歴が長すぎないか確認する
3. `call_messages()` に system・ツール定義を渡してモデルを呼ぶ
4. assistant の `content` を、thinking ブロックも含めてそのまま履歴に追加する
5. `stop_reason` が `end_turn` なら最後のテキストを返す
6. `tool_use` なら、第6章の `execute_tool_uses()` でツールを実行する（読み取り系は並列、副作用系は承認後に1件ずつ）
7. すべての `tool_result` を1つの user メッセージにまとめて履歴に追加し、2に戻る
8. `max_turns` に達したら打ち切る

この流れは、本章でも一切変えません。
変えるのは「設定をどこに持つか」だけです。
関数の引数としてばらばらに渡していた system・ツール・モデル・effort・最大ターン数を、1つのオブジェクトの属性としてまとめます。
こうすると、「調査担当の設定一式」「まとめ役の設定一式」を変数として作っておき、必要なときに `run()` を呼ぶだけで済むようになります。

### Agent クラスを作る

それでは `agent.py` を更新します。
第6・7章で作った関数や定数は、消さずに残します。
関数では、`run_agent()`・`execute_tool_uses()`・`build_registry()` などです。
定数では、`BASE_SYSTEM` などです。
そのうえで、同じ流れを `Agent` クラスの `run()` メソッドとして追加します。
import の2行は既存の import 群に足し、クラスは `if __name__ == "__main__":` の前に置いてください。
非同期版の `arun()` は8.3節で追加するので、ここでは同期版だけを示します。

```python
# agent.py（更新: 第6・7章の関数と定数は残したまま、import を足し、Agent クラスを追記する）
from dataclasses import dataclass

from llm_client import MODEL


@dataclass
class Agent:
    """設定一式とエージェントループをまとめたクラス。"""

    name: str                    # ログや報告でエージェントを区別する名前
    system: str                  # このエージェントの役割を定める system プロンプト
    registry: ToolRegistry       # このエージェントが使ってよいツールの一覧
    model: str = MODEL           # 使うモデル（既定は claude-opus-5-5）
    effort: str | None = None    # output_config.effort に渡す値。None なら送らない
    max_turns: int = 10          # ループの最大反復回数（暴走防止のガード）

    # ---- リクエストの組み立て ------------------------------------------
    def _request_kwargs(self) -> dict:
        # call_messages / acall_messages に渡すキーワード引数をまとめて作る
        kwargs: dict = {
            # 第7章の補助関数で、system とツール定義の末尾にキャッシュの区切りを付ける
            "system": cached_system(self.system),
            "tools": cached_tools(self.registry.schemas()) or None,  # ツールがなければ送らない
            "model": self.model,
            # 第7章と同じトップレベルの自動キャッシュ（伸びていく messages の末尾に区切りを置く）
            "extra": {"cache_control": {"type": "ephemeral"}},
        }
        if self.effort is not None:
            kwargs["output_config"] = {"effort": self.effort}
        return kwargs

    # ---- 応答の判定 ----------------------------------------------------
    def _check_stop(self, response: dict) -> str | None:
        """ループを終えるなら最終テキストを、続けるなら None を返す。"""
        stop = response.get("stop_reason")
        if stop == "tool_use":
            return None                                   # ツールを実行して続行
        if stop == "end_turn":
            return extract_text(response)                 # 正常終了
        if stop == "max_tokens":
            logger.warning("[%s] max_tokens で出力が途切れました", self.name)
            return extract_text(response) + "\n\n[注意: 出力が途中で途切れています]"
        if stop == "refusal":
            logger.warning("[%s] refusal: %s", self.name, response.get("stop_details"))
            return f"[{self.name}] この依頼には応答できませんでした。"
        # stop_sequence など、本書で想定していない終了理由
        logger.warning("[%s] 想定外の stop_reason: %s", self.name, stop)
        return extract_text(response)

    # ---- ツールの実行 --------------------------------------------------
    def _execute_tools(self, tool_uses: list[dict]) -> list[dict]:
        for tu in tool_uses:  # どのエージェントがどのツールを呼んだかをログに残す
            logger.info("[%s] tool_use: %s %s", self.name, tu["name"], tu["input"])
        # 第6章の execute_tool_uses() をそのまま使う（読み取り系は並列、
        # 副作用系は承認後に逐次、大きすぎる結果の切り詰め、失敗は is_error）
        return execute_tool_uses(self.registry, tool_uses)

    # ---- エージェントループ（同期版） ----------------------------------
    def run(self, task: str) -> str:
        # 新しい messages 配列を作る。これがこのエージェント専用のコンテキスト
        messages: list[dict] = [{"role": "user", "content": task}]
        kwargs = self._request_kwargs()   # 毎ターン同じ内容を送る（キャッシュに有利）
        for turn in range(1, self.max_turns + 1):
            # 第7章: 送るのと同じ system・tools で数え、長くなりすぎた履歴は圧縮する
            messages = maybe_compact(messages, system=kwargs["system"], tools=kwargs["tools"])
            response = call_messages(messages, **kwargs)
            # assistant の content は thinking ブロックも含めてそのまま追加する
            messages.append({"role": "assistant", "content": response["content"]})

            final = self._check_stop(response)
            if final is not None:
                logger.info("[%s] 完了（%dターン）", self.name, turn)
                return final

            # すべての tool_result を1つの user メッセージにまとめて返す
            results = self._execute_tools(get_tool_uses(response))
            messages.append({"role": "user", "content": results})

        logger.warning("[%s] max_turns=%d に達しました", self.name, self.max_turns)
        return f"[{self.name}] 最大ターン数（{self.max_turns}）に達したため中断しました。"
```

順に読んでいきましょう。

追加する import は `dataclass` と `MODEL` の2つだけです。
第6・7章ですでに同じファイルにあるものは、そのまま使います。
`maybe_compact()`・`cached_system()`・`execute_tool_uses()`・ロガーの `logger` などです。
既存の関数を残しておくので、第7章の例もそのまま動きます。
たとえば `from agent import build_registry, run_agent` のような例です。

`@dataclass` は、属性を並べて書くだけで `__init__()` を自動生成してくれる標準ライブラリの仕組みです。
インスタンスは、キーワード引数で設定を渡して作れます。
`Agent(name="researcher", system="...", registry=reg)` のような形です。
`model`・`effort`・`max_turns` には既定値があるので、省略すればメインエージェント向けの設定になります。
属性の並びと型は、本書のコードベース仕様で決めたとおりです。
第10章でもこのクラスをそのまま使うので、名前を変えないようにしてください。

`_request_kwargs()` は、API呼び出しに渡す引数をまとめて作るメソッドです。
system とツール定義には、第7章の `cached_system()`・`cached_tools()` でキャッシュの区切りを付けています。
`extra` のトップレベルの `cache_control` も、第7章の `run_agent()` と同じです。
第7章で学んだように、キャッシュは `tools` → `system` → `messages` の順に前方一致で効きます。
子エージェントは同じ system とツールで何度も呼ばれるので、この区切りが特に効いてきます。
同じ調査担当を3回起動すれば、2回目以降は system とツール定義の部分がキャッシュから読まれる可能性があります。
ただし、プロンプトが最小キャッシュ長に届かない短さなら、キャッシュは作られません。
効果は `usage.cache_read_input_tokens` で確かめるのでしたね。
`cached_tools()` はコピーに区切りを付けるので、レジストリが持つ元の定義は書き換わりません。
共有されるデータは書き換えずにコピーするという習慣は、マルチエージェントでの思わぬ干渉を防ぎます。

`effort` が `None` のときは `output_config` 自体を送りません。
effort に対応していないモデルや、既定値のままでよい場面では、何も送らないのがいちばん安全だからです。
このメソッドを同期版と非同期版で共有することで、2つのループの設定が食い違う事故を防ぎます。

`_check_stop()` は、`stop_reason` を見てループを続けるかどうかを決めます。
`tool_use` なら `None` を返して続行し、それ以外は最終テキストを返して終了します。
第5章の `run_agent()` では、この判定がループの中に直接書かれていました。
メソッドに切り出したのは、同期版の `run()` と8.3節の非同期版 `arun()` で同じ判定を使い回すためです。
`max_tokens` のときに注意書きを付けて返しているのは、子エージェントの結果が途中で切れていることを親に知らせるためです。
親のモデルはこの注意書きを読んで、もう一度依頼するかどうかを判断できます。

`_execute_tools()` は、第6章の `execute_tool_uses()` をそのまま呼んでいます。
読み取り系ツールの並列実行、副作用ツールの実行前確認、大きすぎる結果の切り詰めも、第6章のまま引き継がれます。
加えたのは、`[名前]` 付きで tool_use をログに出す処理だけです。
ツールが例外を投げても、ループ全体は止めずに `is_error: True` の tool_result としてモデルに返します。
この性質は、後で子エージェントを呼ぶツールを作るときに重要になります。
子が失敗しても親は止まらず、「調査に失敗した」という情報を受け取って次の手を考えられるからです。

最後の `run()` が、エージェンティックループ本体です。
1行目で `messages` を新しく作っている点に注目してください。
`run()` を呼ぶたびに空の履歴から始まるので、同じ `Agent` インスタンスを何度使っても、前回の仕事の内容は持ち越されません。
これが、サブエージェントの「独立したコンテキスト」を実現している部分です。

> **WARNING: messages をインスタンス属性にしない**
> 「履歴をクラスに持たせたほうがオブジェクト指向らしい」と考えて、`self.messages` に履歴を保存したくなるかもしれません。しかし、そうすると同じインスタンスを2回使ったときに前回の履歴が混ざります。8.3節で並列実行したときには、複数の仕事が1つの履歴を奪い合って壊れます。履歴は `run()` の中のローカル変数にしておくのが、本書の設計の要です。

### Agent クラスの動作を確認する

まずは、リファクタリングで動作が変わっていないことを確かめましょう。
第6章で作ったファイル操作ツールを使い、単独のエージェントとして動かしてみます。
中身は、第6章の `tools/files.py` の `list_files(path=".")` と `read_file(path)` です。
これらを、引数名を `directory`・`path` にしたラッパーから呼びます。
同等のレジストリは、第6章の関数でも作れます。
`register_file_tools(registry, allow_write=False)` を使う方法です。
こちらも読み取り専用ですが、引数名は `path` になります。
ここでは説明を短くするため、2つだけを直接登録します。
第6章で引数名を変えている場合は、ラッパーの中の呼び出しを手元のコードに合わせてください。

```python
# check_agent.py（新規作成: Agent クラスの動作確認用。確認後は削除してよい）
import logging

from agent import Agent
from llm_client import FAST_MODEL, tracker
from tool_registry import ToolRegistry
from tools import files

# INFO 以上のログを表示し、エージェントの動きを観察できるようにする
logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)  # httpx自身のログは抑える（第4章と同じ）

# 読み取り専用のツールだけを登録したレジストリを作る
registry = ToolRegistry()


@registry.tool(
    name="list_files",
    description="workspace 配下のディレクトリにあるファイル名の一覧を返す。"
                "どんな資料があるかを確かめるときに最初に使う。",
    input_schema={
        "type": "object",
        "properties": {"directory": {"type": "string",
                                     "description": "workspace からの相対パス。例: docs"}},
        "required": ["directory"],
    },
)
def list_files(directory: str) -> str:
    return files.list_files(directory)   # 第6章の関数をそのまま呼ぶ


@registry.tool(
    name="read_file",
    description="workspace 配下のテキストファイルを読み、内容を返す。"
                "list_files で確かめたファイル名を指定する。",
    input_schema={
        "type": "object",
        "properties": {"path": {"type": "string",
                                "description": "workspace からの相対パス。例: docs/alpha.md"}},
        "required": ["path"],
    },
)
def read_file(path: str) -> str:
    return files.read_file(path)         # サイズ上限やパス検査は第6章の実装に任せる


# 1つのエージェントとして動かす
agent = Agent(
    name="checker",
    system="あなたは資料の読み取り担当です。資料に書かれていることだけを簡潔に答えてください。",
    registry=registry,
    model=FAST_MODEL,
    max_turns=6,
)
print(agent.run("workspace/docs にどんな資料があるか確認し、Alpha の月額料金を教えて"))
print(tracker.summary())
```

動作確認には、比較対象となる資料が必要です。
`workspace/docs/` フォルダーを作り、次の3つのファイルを置いてください。
内容は架空の製品の説明で、本章の例題全体で使います。

```markdown
<!-- workspace/docs/alpha.md -->
# Alpha クラウドノート
- 月額料金: 1ユーザーあたり 800円（年払いで 10% 割引）
- 対応OS: Windows 11 / macOS 14 以降 / iOS / Android
- サポート: 平日 9〜18時のメール対応。有償オプションで電話サポートあり
- 備考: 2026年4月に料金改定。それ以前は 700円
```

```markdown
<!-- workspace/docs/beta.md -->
# Beta チームメモ
- 月額料金: 1チーム（10名まで）3,000円
- 対応OS: Windows 10 以降 / macOS 13 以降 / Linux（ブラウザー版のみ）
- サポート: 24時間チャット対応（英語）。日本語は平日日中のみ
- 備考: 11名以上は 1名あたり 250円を追加
```

```markdown
<!-- workspace/docs/gamma.md -->
# Gamma ナレッジベース
- 月額料金: 無料プランあり。有料プランは 1ユーザーあたり 1,200円
- 対応OS: ブラウザー版のみ（Chrome / Edge / Safari の最新版）
- サポート: 有料プランのみ、専任担当による電話・メール対応
- 備考: 無料プランは保存容量 1GB まで
```

準備ができたら実行します。

```bash
# Agent クラス単体の動作確認
uv run python check_agent.py
```

次のような出力になれば成功です。
細かな文言、所要時間、トークン数は実行のたびに変わります。

```text
llm_client: request_id=req_01... model=claude-haiku-5-5 stream=False elapsed=1.40s stop=tool_use in=8 out=58 cache_write=1016 cache_read=0 cost=$0.0002
agent: [checker] tool_use: list_files {'directory': 'docs'}
agent: tool=list_files elapsed=0.00s
llm_client: request_id=req_01... model=claude-haiku-5-5 stream=False elapsed=1.10s stop=tool_use in=8 out=41 cache_write=185 cache_read=1016 cost=$0.0001
agent: [checker] tool_use: read_file {'path': 'docs/alpha.md'}
agent: tool=read_file elapsed=0.00s
llm_client: request_id=req_01... model=claude-haiku-5-5 stream=False elapsed=1.60s stop=end_turn in=8 out=88 cache_write=160 cache_read=1201 cost=$0.0001
agent: [checker] 完了（3ターン）
docs フォルダーには alpha.md・beta.md・gamma.md の3つがあります。
Alpha の月額料金は 1ユーザーあたり 800円で、年払いでは 10% 割引になります。
calls=3 input=24 output=187 cache_write=1,361 cache_read=2,217 total=$0.0003
```

ログの読み方を確認しておきましょう。
`llm_client:` で始まる行が第4章のロガーで、その回の応答の停止理由とトークン数を示します。
`agent:` で始まる行は、第6章から使っているロガーの出力です。
そのうち `[checker]` 付きの行が、今回足した記録です。
`tool=... elapsed=` の行は、第6章の `run_one_tool()` の記録です。
`[checker]` という名前が付いているので、どのエージェントの動きかがすぐに分かります。
この時点では1つしかエージェントがいないのでありがたみは薄いです。
しかし、子が3つ同時に動き出すと、この名前がなければログはまったく読めなくなります。

3ターンかかっているのは、「一覧を見る」「ファイルを読む」「答える」の3回モデルを呼んだからです。
最後の `tracker.summary()` は、第4章で作ったコスト集計です。
Haiku で動かしているので、コストはごくわずかです。
`cache_write` と `cache_read` に値が出ています。
これは、第7章で付けたキャッシュの区切りが Haiku でも働いているためです。
`claude-haiku-5-5` の最小キャッシュ長は512トークンなので、この程度の短いプロンプトでもキャッシュされます。
1回目に書き込んだ部分を2回目以降が読み取り、`in=` には区切りより後ろのわずかな部分だけが数えられています。
なお、`httpx` の通信ログは、第6章と同じく `setLevel(logging.WARNING)` で隠しています。

> **NOTE**: 第6・7章の `run_agent()` と `build_registry()` は `agent.py` に残してあります。そのため、`uv run python agent.py "..."` や第7章の effort の例はそのまま動きます。これから書くコードでは、`Agent` クラスを使ってください。`Agent(name=..., system=..., registry=...).run(user_input)` という形です。

### 委譲ツールという考え方

`Agent` クラスができたので、いよいよ親と子をつなぎます。
つなぎ方はとても単純です。
親の `ToolRegistry` に「子の `run()` を呼ぶだけの関数」をツールとして登録します。
本書では、このように仕事を別のエージェントに任せるためのツールを**委譲ツール**と呼びます。

委譲ツールを使うと、親のモデルから見た世界は第5・6章とまったく変わりません。
親のモデルは「`delegate_research` というツールがある」と知っていて、必要だと判断したら tool_use を出します。
私たちのコードは、その tool_use を受けて関数を実行し、戻り値を tool_result として返します。
違うのは、その関数の中で、もう1本のエージェンティックループが丸ごと動くことだけです。

この設計には、大きな利点が2つあります。
1つは、これまで作ってきた仕組みがすべてそのまま使えることです。
ツールの例外処理も、`is_error` の返し方も、第6章の並列実行も、委譲ツールに対して何の変更もなく働きます。
もう1つは、「いつ、何を、何回委譲するか」をモデル自身に判断させられることです。
調査対象が2つなら2回、5つなら5回というように、仕事の量に合わせて親が委譲の回数を決めてくれます。
委譲の手順をコードで固定する方法もありますが、それは第9章で扱う「ワークフロー」の領域になります。

<figure id="fig-8-3">
<svg width="605" height="420" viewBox="0 0 605 420" xmlns="http://www.w3.org/2000/svg" font-family="'Noto Sans JP',sans-serif">
  <defs>
    <marker id="f8_3_ar83" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#333" stroke-width="1.5"/>
    </marker>
    <marker id="f8_3_ar83b" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#2b6cb0" stroke-width="1.5"/>
    </marker>
  </defs>
  <!-- 登場人物 -->
  <rect x="20" y="12" width="150" height="42" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="95" y="30" text-anchor="middle" font-size="12" fill="#1a1a1a" font-weight="bold">親エージェント</text>
  <text x="95" y="46" text-anchor="middle" font-size="10" fill="#1a1a1a" font-family="Consolas,monospace">orchestrator</text>
  <rect x="215" y="12" width="170" height="42" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="300" y="30" text-anchor="middle" font-size="12" fill="#1a1a1a" font-weight="bold">委譲ツールの関数</text>
  <text x="300" y="46" text-anchor="middle" font-size="10" fill="#1a1a1a" font-family="Consolas,monospace">delegate_research()</text>
  <rect x="430" y="12" width="150" height="42" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.2"/>
  <text x="505" y="30" text-anchor="middle" font-size="12" fill="#1a1a1a" font-weight="bold">子エージェント</text>
  <text x="505" y="46" text-anchor="middle" font-size="10" fill="#1a1a1a" font-family="Consolas,monospace">researcher</text>
  <!-- ライフライン -->
  <line x1="95" y1="54" x2="95" y2="410" stroke="#999" stroke-width="1" stroke-dasharray="4,4"/>
  <line x1="300" y1="54" x2="300" y2="410" stroke="#999" stroke-width="1" stroke-dasharray="4,4"/>
  <line x1="505" y1="54" x2="505" y2="410" stroke="#999" stroke-width="1" stroke-dasharray="4,4"/>
  <!-- ① -->
  <path d="M95 85 L298 85" stroke="#333" stroke-width="1.3" marker-end="url(#f8_3_ar83)"/>
  <text x="197" y="78" text-anchor="middle" font-size="10" fill="#1a1a1a">① tool_use（topic・aspects・context）</text>
  <!-- ② -->
  <rect x="222" y="100" width="156" height="40" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="300" y="116" text-anchor="middle" font-size="10" fill="#1a1a1a" font-family="Consolas,monospace">② build_child_task()</text>
  <text x="300" y="132" text-anchor="middle" font-size="10" fill="#1a1a1a">4部構成の指示文に組み立て</text>
  <!-- ③ -->
  <path d="M300 165 L496 165" stroke="#333" stroke-width="1.3" marker-end="url(#f8_3_ar83)"/>
  <text x="402" y="158" text-anchor="middle" font-size="10" fill="#1a1a1a" font-family="Consolas,monospace">③ researcher.run(task)</text>
  <!-- ④ 子ループ -->
  <rect x="497" y="165" width="16" height="120" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.2"/>
  <rect x="330" y="185" width="160" height="70" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.2"/>
  <text x="410" y="204" text-anchor="middle" font-size="11" fill="#1a1a1a">④ 子ループ（新しい履歴）</text>
  <text x="410" y="223" text-anchor="middle" font-size="10" fill="#1a1a1a" font-family="Consolas,monospace">list_files → read_file</text>
  <text x="410" y="242" text-anchor="middle" font-size="10" fill="#1a1a1a"><tspan font-family="Consolas,monospace">→ end_turn</tspan>（3ターン）</text>
  <!-- ⑤ -->
  <path d="M497 285 L302 285" stroke="#2b6cb0" stroke-width="1.4" stroke-dasharray="5,3" marker-end="url(#f8_3_ar83b)"/>
  <text x="402" y="278" text-anchor="middle" font-size="10" fill="#1a1a1a">⑤ 報告のテキストだけ返す</text>
  <!-- ⑥ -->
  <rect x="222" y="298" width="156" height="40" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="300" y="314" text-anchor="middle" font-size="10" fill="#1a1a1a" font-family="Consolas,monospace">⑥ clip_report()</text>
  <text x="300" y="330" text-anchor="middle" font-size="10" fill="#1a1a1a">3000字を超えたら切り詰め</text>
  <!-- ⑦ -->
  <path d="M300 360 L97 360" stroke="#2b6cb0" stroke-width="1.4" stroke-dasharray="5,3" marker-end="url(#f8_3_ar83b)"/>
  <text x="197" y="353" text-anchor="middle" font-size="10" fill="#1a1a1a">⑦ tool_result として親に返る</text>
  <!-- ⑧ -->
  <rect x="20" y="372" width="150" height="34" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="95" y="393" text-anchor="middle" font-size="11" fill="#1a1a1a">⑧ 報告から最終回答</text>
  <text x="530" y="320" font-size="10" fill="#666">子の履歴は</text>
  <text x="530" y="334" font-size="10" fill="#666">ここで破棄</text>
</svg>
  <figcaption>図8.3: 委譲ツールによる親子の呼び出し</figcaption>
</figure>

### 委譲ツールのスキーマを設計する

委譲ツールで最も大切なのは、親が子に「何を渡すか」の設計です。
ここがあいまいだと、親は毎回違う書き方で依頼を出し、子の出来も毎回ばらつきます。
本書では、親に自由な文章を書かせるのではなく、項目を分けた入力スキーマで依頼させる方針をとります。

| 引数 | 型 | 役割 |
|---|---|---|
| `topic` | 文字列（必須） | 調査対象。1回の呼び出しで1つだけ |
| `aspects` | 文字列の配列（必須） | 調べる観点の一覧 |
| `context` | 文字列（任意） | 子が知っておくべき背景や前提 |

`topic` を「1回の呼び出しで1つだけ」と決めているのは、並列化のためです。
3製品をまとめて1回で依頼されると、子は3つの資料を順番に読むことになり、分けた意味がなくなります。
対象ごとに呼び出させれば、親は1回の応答で3つの tool_use を並べてくれ、それぞれを別の子が同時に処理できます。

`aspects` を配列にしているのは、調べる観点の抜け漏れを防ぐためです。
自由文で「料金や対応OSなどを調べて」と書かせると、「など」の中身が子ごとに変わってしまいます。
配列で観点を明示させれば、3つの子が同じ観点で調べるので、親が表にまとめるときに項目がそろいます。

`context` は任意の背景情報です。
たとえば「10名のチームでの導入を検討中」という背景があれば、子は「11名以上は追加料金」という条件に注目して報告できます。
子は親の会話履歴を見られないので、ユーザーが最初に伝えた前提は、親がこの欄で明示的に渡すしかありません。
「子は何も知らない」という前提に立って、必要な情報を引数で渡す設計にすることが大切です。

### 子への指示の書き方

親から受け取った引数は、そのまま子に渡すのではなく、決まった型の指示文に組み立ててから渡します。
子にとって、この指示文は会話の最初の1通であり、仕事について知り得る唯一の情報です。
本書では、子への指示を次の4つの部分で構成することをおすすめします。

- **タスク**: 何を対象に、どの観点で調べるのか
- **背景**: なぜ調べるのか、どんな前提があるのか
- **出力形式**: どんな形で報告すればよいのか
- **制約**: やってはいけないこと、迷ったときの扱い

このうち、見落とされやすいのが出力形式と制約です。
出力形式を決めておかないと、子は長い文章で丁寧に報告し、親のコンテキストを圧迫します。
制約を書いておかないと、子は資料にないことを「一般的にはこうです」と補ってしまいます。
親はその報告が資料に基づくものか推測かを区別できないので、誤った情報がそのまま最終結果に入り込みます。

> [!DIALOGUE]
> **読者**: 子への指示は、親のモデルに自由に書かせたほうが柔軟ではありませんか？
> **筆者**: 柔軟さは増えますが、そのぶん品質がぶれます。親に任せるのは「何を調べるか」の判断だけにして、「どう報告するか」はコードで固定しておくと、子の出力が安定します。
> **読者**: 出力形式をコード側で決めておけば、親は報告の読み方に迷わなくて済むんですね。
> **筆者**: そのとおりです。報告の形がそろっていれば、親は3つの報告を並べるだけで表を作れます。

悪い指示と良い指示を比べてみましょう。
悪い例は「Alpha について調べてください」の1文だけです。
子は何の観点で調べればよいのか分からず、資料全体を要約して返すかもしれません。
良い例は、次の節で作る `build_child_task()` が組み立てる指示文です。
対象・観点・背景・出力形式・制約がすべて書かれているので、子は迷わずに仕事を進められます。

### multi_agent.py を作る

それでは、親と子を組み立てる `multi_agent.py` を作ります。
ファイル操作ツールの登録は、先ほどの `check_agent.py` から移してきます。

```python
# multi_agent.py（新規作成: 調査担当の子エージェントと、委譲ツールを持つ親エージェント）
from __future__ import annotations

import logging

from agent import Agent
from llm_client import FAST_MODEL, MODEL, tracker
from tool_registry import ToolRegistry
from tools import files

logger = logging.getLogger("multi_agent")

# 子から親に返す報告の上限文字数（親のコンテキストを守るための安全弁）
MAX_REPORT_CHARS = 3000

# ---- 子（調査担当）の設定 --------------------------------------------
RESEARCHER_SYSTEM = """あなたは資料調査の担当者です。
workspace/docs/ にある資料だけを根拠に、依頼された観点を調べて報告します。

進め方:
1. list_files で資料の一覧を確認する
2. 調査対象に関係する資料を read_file で読む
3. 観点ごとに、資料に書かれている事実だけを抜き出す

報告のルール:
- 依頼に書かれた出力形式に必ず従う
- 各事実の末尾に根拠のファイル名を（）で付ける
- 資料に書かれていないことは推測せず「記載なし」と書く
- 前置きや感想は書かない"""


def build_research_registry() -> ToolRegistry:
    # 調査担当に渡すのは読み取り専用のツールだけ（write_file は渡さない）
    registry = ToolRegistry()

    @registry.tool(
        name="list_files",
        description="workspace 配下のディレクトリにあるファイル名の一覧を返す。"
                    "どんな資料があるかを確かめるときに最初に使う。",
        input_schema={
            "type": "object",
            "properties": {"directory": {"type": "string",
                                         "description": "workspace からの相対パス。例: docs"}},
            "required": ["directory"],
        },
    )
    def list_files(directory: str) -> str:
        return files.list_files(directory)

    @registry.tool(
        name="read_file",
        description="workspace 配下のテキストファイルを読み、内容を返す。"
                    "list_files で確かめたファイル名を指定する。",
        input_schema={
            "type": "object",
            "properties": {"path": {"type": "string",
                                    "description": "workspace からの相対パス。例: docs/alpha.md"}},
            "required": ["path"],
        },
    )
    def read_file(path: str) -> str:
        return files.read_file(path)

    return registry


def build_researcher() -> Agent:
    # 資料の読み取りは定型的なので、低コストの FAST_MODEL に任せる
    return Agent(name="researcher", system=RESEARCHER_SYSTEM,
                 registry=build_research_registry(), model=FAST_MODEL, max_turns=8)


# ---- 委譲ツール ------------------------------------------------------
DELEGATE_RESEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "topic": {"type": "string",
                  "description": "調査対象。1回の呼び出しで1つだけ指定する。例: 製品 Alpha"},
        "aspects": {"type": "array", "items": {"type": "string"},
                    "description": "調べる観点の一覧。例: [\"月額料金\", \"対応OS\"]"},
        "context": {"type": "string",
                    "description": "調査担当が知っておくべき背景（任意）。例: 10名のチームで導入を検討中"},
    },
    "required": ["topic", "aspects"],
}


def build_child_task(topic: str, aspects: list[str], context: str = "") -> str:
    # 親から受け取った引数を、タスク・背景・出力形式・制約の4部構成の指示文にする
    aspect_lines = "\n".join(f"- {a}" for a in aspects)
    return (
        f"## タスク\n{topic} について、次の観点を調べてください。\n{aspect_lines}\n\n"
        f"## 背景\n{context or '特になし'}\n\n"
        "## 出力形式\n"
        "観点ごとに「- 観点: 内容（根拠ファイル名）」の形で1行ずつ書く。\n"
        "最後に「- 注意点: 」として、比較するときに気を付ける条件を1〜2行で書く。\n\n"
        "## 制約\n"
        f"- {topic} 以外の資料から事実を書かない\n"
        "- 資料に記載がなければ「記載なし」と書き、推測で補わない"
    )


def clip_report(report: str, limit: int = MAX_REPORT_CHARS) -> str:
    # 子の報告が長すぎる場合は切り詰め、切り詰めたことを親に知らせる
    if len(report) <= limit:
        return report
    return report[:limit] + f"\n\n[報告が長いため {limit} 文字で切り詰めました]"


def build_orchestrator_registry(researcher: Agent) -> ToolRegistry:
    # 親が使えるのは委譲ツールだけ。資料を直接読むツールは渡さない
    registry = ToolRegistry()

    @registry.tool(
        name="delegate_research",
        description=(
            "調査担当のサブエージェントに、1つの対象についての資料調査を依頼する。"
            "調査担当は workspace/docs/ の資料を読み、観点ごとの事実を根拠付きで報告する。"
            "互いに独立した複数の対象を調べるときは、1回の応答でこのツールを対象の数だけ呼び出すこと。"
        ),
        input_schema=DELEGATE_RESEARCH_SCHEMA,
    )
    def delegate_research(topic: str, aspects: list[str], context: str = "") -> str:
        task = build_child_task(topic, aspects, context)
        logger.info("delegate_research -> %s %s", topic, aspects)
        report = researcher.run(task)   # 子のループを1本回す。子の履歴はここで捨てられる
        return clip_report(report)      # 親に返るのは報告のテキストだけ

    return registry


# ---- 親（まとめ役）の設定 --------------------------------------------
ORCHESTRATOR_SYSTEM = """あなたは製品比較レポートのまとめ役です。
あなた自身は資料を読めません。調査は delegate_research ツールで調査担当に依頼します。

進め方:
1. 比較の対象と観点を決める
2. 対象ごとに delegate_research を呼ぶ。互いに独立した調査は、1回の応答でまとめて呼び出す
3. 報告がそろったら、Markdown の比較表と、選び方の助言を3行以内で書く

ルール:
- すべての対象に同じ観点の一覧を渡す
- 報告に「記載なし」とある項目は、表でも「記載なし」と書く
- 報告が食い違う、または情報が足りない場合に限り、追加の調査を依頼する"""


def build_orchestrator() -> Agent:
    # まとめ役は判断の質が全体を左右するので、既定の MODEL を使う
    researcher = build_researcher()
    return Agent(name="orchestrator", system=ORCHESTRATOR_SYSTEM,
                 registry=build_orchestrator_registry(researcher), model=MODEL, max_turns=6)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # httpx自身のログは抑える
    orchestrator = build_orchestrator()
    answer = orchestrator.run(
        "workspace/docs にある Alpha・Beta・Gamma の3製品について、"
        "月額料金・対応OS・サポート体制を比較してください。10名のチームで使う予定です。"
    )
    print("\n===== 最終回答 =====")
    print(answer)
    print("\n===== コスト =====")
    print(tracker.summary())


if __name__ == "__main__":
    main()
```

コードの量は多く見えますが、やっていることは「子を作る」「委譲ツールを作る」「親を作る」の3つだけです。
上から順に見ていきましょう。

`MAX_REPORT_CHARS` は、子から親に返す報告の上限です。
子への指示で出力形式を決めていても、モデルが指示を守らずに長い報告を返すことはあり得ます。
上限を設けておけば、どんな場合でも親のコンテキストに入る量を一定以下に抑えられます。
3,000文字という値は、この例題の報告が数百文字程度なのを踏まえ、十分な余裕を持たせた目安です。
扱う題材に応じて調整してください。

`RESEARCHER_SYSTEM` は、子の役割を定める system プロンプトです。
進め方と報告のルールを箇条書きで具体的に書いています。
注目してほしいのは、このプロンプトに「Alpha」や「料金」といった具体的な対象が一切出てこないことです。
system には役割と仕事の進め方だけを書き、個別の依頼内容は user メッセージで渡します。
こうしておくと system が毎回同じ文字列になるので、第7章のキャッシュが効きやすくなります。

`build_research_registry()` は、`check_agent.py` と同じ2つのツールを使います。
これらを、関数の中で新しいレジストリに登録しています。
モジュールの最上位ではなく関数の中で作っているのは、エージェントごとに別のレジストリを持たせるためです。
ここで `write_file` を登録していない点が重要です。
調査担当は資料を読むだけなので、書き込む権限は必要ありません。
この「必要な権限だけを渡す」考え方は、8.4節で改めて整理します。

`build_researcher()` では、調査担当を `FAST_MODEL`（`claude-haiku-5-5`）で作っています。
指定された資料から事実を抜き出す仕事は、高度な推論をあまり必要としません。
`max_turns=8` は、一覧を見て数ファイルを読み、報告するのに十分な回数です。
子は親よりも暴走に気づかれにくいので、親よりも少し厳しめの上限を設けておくと安心です。

`DELEGATE_RESEARCH_SCHEMA` は、先ほど表で整理したスキーマをそのままコードにしたものです。
各引数の `description` に具体例を入れているのは、親のモデルが引数の書き方を迷わないようにするためです。
第5章で学んだとおり、ツールの説明はモデルにとって唯一の取扱説明書です。
例を1つ添えるだけで、引数の粒度がぐっとそろいます。

`build_child_task()` は、親から受け取った引数を4部構成の指示文に組み立てる関数です。
見出し付きの Markdown にしているのは、子のモデルが各部分の役割を取り違えないようにするためです。
制約の1行目で `topic` を埋め込み、「対象以外の資料から事実を書かない」と明示しています。
これは、8.1節で触れたコンテキストの汚染を、子の側でも防ぐための一文です。
子は `list_files` で3製品すべての資料名を目にするので、ほかの製品の資料を読んでしまう可能性があるからです。

`clip_report()` は、報告の切り詰めを行う小さな関数です。
切り詰めたときに、その旨を末尾に書き添えているのがポイントです。
黙って切ると、親は報告が完全なものだと思い込んでしまいます。
「切り詰めた」と知らせれば、親は「必要なら観点を絞って再依頼する」という判断ができます。

`build_orchestrator_registry()` が、本節の主役となる委譲ツールです。
引数として子の `Agent` を受け取り、その `run()` を呼ぶ関数をツールとして登録しています。
関数の中身はわずか4行です。
指示文を組み立て、ログを出し、子のループを回し、報告を切り詰めて返す。
子のループの中で何ターンやり取りがあっても、何ファイル読まれても、この関数の戻り値は報告のテキストだけです。
子の `messages` 配列は `run()` のローカル変数なので、関数を抜けた時点で捨てられます。

ツールの `description` の最後の一文にも注目してください。
「互いに独立した複数の対象を調べるときは、1回の応答でこのツールを対象の数だけ呼び出すこと」と書いています。
Messages API の並列ツール呼び出しは既定で有効ですが、モデルが実際に並べて呼ぶかどうかは、説明や指示に左右されます。
この一文と、system の「1回の応答でまとめて呼び出す」という指示が、次の項で説明する並列実行の鍵になります。

`ORCHESTRATOR_SYSTEM` の冒頭で「あなた自身は資料を読めません」と書いているのにも理由があります。
この一文がないと、親のモデルが委譲せずに自分の知識で比較表を作ってしまうことがあるからです。
親は資料にアクセスするツールを持っていないので、そうして作られた表は資料に基づかない推測になります。
「自分ではできない」とはっきり伝えることで、委譲ツールを使う動機を与えています。

最後の `build_orchestrator()` は、子を1つ作り、それを委譲ツールに渡して親を作ります。
親は `MODEL`（`claude-opus-5-5`）で動かし、`max_turns=6` としています。
親のターン数は「委譲する」「報告を受けて表を作る」の2〜3ターンが普通なので、6あれば十分です。

> **POINT: 子に委譲ツールを渡さない**
> 調査担当のレジストリに `delegate_research` を登録すると、子が孫を、孫がひ孫を起動できてしまいます。コストも所要時間も際限なく膨らみ、ログを追うのも困難になります。本書では、委譲は親から子への1段だけに限定します。子のレジストリには、子が自分で使う作業用のツールだけを登録してください。

### 実行して動きを確かめる

それでは実行してみましょう。

```bash
# 親（まとめ役）と子（調査担当）を動かす
uv run python multi_agent.py
```

次のような出力が得られます。
実際の出力ではもっと多くのログ行が並びますが、ここでは流れが分かるよう一部を省略しています。

```text
agent: [orchestrator] tool_use: delegate_research {'topic': '製品 Alpha', 'aspects': ['月額料金', '対応OS', 'サポート体制'], 'context': '10名のチームで使う予定'}
agent: [orchestrator] tool_use: delegate_research {'topic': '製品 Beta', 'aspects': ['月額料金', '対応OS', 'サポート体制'], 'context': '10名のチームで使う予定'}
agent: [orchestrator] tool_use: delegate_research {'topic': '製品 Gamma', 'aspects': ['月額料金', '対応OS', 'サポート体制'], 'context': '10名のチームで使う予定'}
multi_agent: delegate_research -> 製品 Alpha ['月額料金', '対応OS', 'サポート体制']
multi_agent: delegate_research -> 製品 Beta ['月額料金', '対応OS', 'サポート体制']
multi_agent: delegate_research -> 製品 Gamma ['月額料金', '対応OS', 'サポート体制']
agent: [researcher] tool_use: list_files {'directory': 'docs'}
agent: [researcher] tool_use: list_files {'directory': 'docs'}
agent: [researcher] tool_use: list_files {'directory': 'docs'}
agent: [researcher] tool_use: read_file {'path': 'docs/beta.md'}
agent: [researcher] tool_use: read_file {'path': 'docs/alpha.md'}
agent: [researcher] tool_use: read_file {'path': 'docs/gamma.md'}
agent: [researcher] 完了（3ターン）
agent: [researcher] 完了（3ターン）
agent: [researcher] 完了（3ターン）
agent: [orchestrator] 完了（2ターン）

===== 最終回答 =====
| 製品 | 月額料金（10名） | 対応OS | サポート体制 |
|---|---|---|---|
| Alpha | 800円×10名＝8,000円（年払いで10%割引） | Windows 11 / macOS 14以降 / iOS / Android | 平日9〜18時メール、電話は有償オプション |
| Beta | 3,000円（10名まで定額） | Windows 10以降 / macOS 13以降 / Linux（ブラウザー版） | 24時間チャット（英語）、日本語は平日日中 |
| Gamma | 1,200円×10名＝12,000円（無料プランあり） | ブラウザー版のみ | 有料プランのみ専任担当が電話・メール対応 |

選び方の助言:
- コスト重視なら Beta。ただし11名以上は1名あたり250円が加算されます。
- 日本語での手厚いサポートが必要なら Gamma の有料プランが向いています。
- 複数OSのネイティブアプリが必要なら Alpha が候補になります。

===== コスト =====
calls=11 input=92 output=2,310 cache_write=6,500 cache_read=8,200 total=$0.0375
```

ログを上から読んでいきましょう。
最初の3行は、親が1回の応答で `delegate_research` を3回呼び出したことを示しています。
3つの tool_use が同じ assistant メッセージに並んでいたということです。
観点の一覧がすべて同じになっているのは、system の「すべての対象に同じ観点の一覧を渡す」というルールが効いているからです。
`context` にユーザーの「10名のチーム」という前提が入っている点も確認してください。

次に、`multi_agent:` のログが3行続き、その後に `[researcher]` のログが入り混じって出てきます。
`list_files` が3回続き、`read_file` が Beta・Alpha・Gamma という順不同で並んでいます。
これは、3つの子エージェントが同時に動いていることを示しています。
第6章で作った `ThreadPoolExecutor` による並列ツール実行が、委譲ツールに対してもそのまま働いた結果です。
委譲ツールの関数は普通の同期関数なので、スレッドで並列に実行され、その中でそれぞれの子のループが回ります。

ここで1つ疑問が浮かぶかもしれません。
3つのスレッドが、同じ `researcher` インスタンスの `run()` を同時に呼んでいて大丈夫なのか、という点です。
答えは「大丈夫」です。
`run()` は呼ばれるたびにローカル変数として新しい `messages` を作るので、3つの呼び出しは互いの履歴に触れません。
インスタンスの属性（system やモデル名）は読むだけで書き換えないため、同時に読んでも問題は起きないのです。
先ほどの WARNING で「履歴をインスタンス属性にしない」と強調したのは、まさにこの場面のためでした。

最後に `[orchestrator] 完了（2ターン）` とあります。
親は「3件を委譲する」で1ターン、「報告をもとに表を作る」で1ターンの、合計2ターンで仕事を終えました。
子はそれぞれ3ターンなので、API呼び出しは親2回と子9回の合計11回です。
コスト集計の `calls=11` と一致していますね。

最終回答の表では、Alpha と Gamma の料金が10名分に換算されています。
これは親が `context` の情報と子の報告を組み合わせて計算した結果です。
Beta の「11名以上は追加料金」という条件が助言に入っているのは、子への指示の「注意点」が効いた結果です。
子が注意点として報告し、親がそれを拾って助言に反映したわけです。

### 親の履歴には何が残っているか

ここで、親の `messages` 配列の中身を想像してみましょう。
本当に「結果だけ」が残っているのかを確かめることは、この設計を理解するうえでとても大切です。
親の2ターン目の直前、つまり報告を受け取った時点の履歴は、おおよそ次の形になっています。

```python
# 親（orchestrator）の messages の概略（説明用。実際の id や thinking の中身は省略）
[
    # 1通目: ユーザーの依頼
    {"role": "user", "content": "workspace/docs にある Alpha・Beta・Gamma の3製品について…"},
    # 2通目: 親の応答。3つの tool_use が1つの assistant メッセージに並ぶ
    {"role": "assistant", "content": [
        {"type": "thinking", "thinking": "", "signature": "..."},
        {"type": "tool_use", "id": "toolu_A", "name": "delegate_research",
         "input": {"topic": "製品 Alpha", "aspects": ["月額料金", "対応OS", "サポート体制"]}},
        {"type": "tool_use", "id": "toolu_B", "name": "delegate_research", "input": {"...": "..."}},
        {"type": "tool_use", "id": "toolu_C", "name": "delegate_research", "input": {"...": "..."}},
    ]},
    # 3通目: 3つの報告を1つの user メッセージにまとめて返す
    {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": "toolu_A",
         "content": "- 月額料金: 1ユーザーあたり800円（alpha.md）\n- 対応OS: …\n- 注意点: …"},
        {"type": "tool_result", "tool_use_id": "toolu_B", "content": "- 月額料金: …"},
        {"type": "tool_result", "tool_use_id": "toolu_C", "content": "- 月額料金: …"},
    ]},
]
```

親の履歴に入っているのは、ユーザーの依頼、3件の依頼内容、3件の報告だけです。
子が `list_files` で見たファイル一覧も、`read_file` で読んだ資料の全文も、どこにも入っていません。
この例では資料が短いので差は小さいですが、資料が1件数万トークンあったとしても、親の履歴の大きさはほとんど変わりません。
これが「子のコンテキストを親に持ち込まない」設計の効果です。

一方で、親は資料の原文を一度も見ていないことにも注意が必要です。
親が知っているのは、子が「こう書いてあった」と報告した内容だけです。
もし子が読み間違えていたら、親はそれに気づく手段を持っていません。
報告に根拠のファイル名を付けさせているのは、後から人間が確認できるようにするためでもあります。
報告の正確さをさらに高めたい場合は、第9章の評価者-最適化者パターンのように、別の子に報告を検証させる方法があります。

> **NOTE: 子の履歴を残したいとき**
> デバッグのために子の履歴を見たいことがあります。その場合は、`run()` の最後に `messages` を JSON ファイルへ書き出すログ機能を足すとよいでしょう。ただし、親に返す値は報告のテキストだけにしておきます。「調査のために残す記録」と「親のコンテキストに入れる情報」を分けて考えるのがコツです。

### つまずきやすいポイントと対処

マルチエージェントは、単一エージェントよりも失敗のパターンが増えます。
本書の読者がつまずきやすい場面と、その対処をまとめておきます。

1つ目は、**親が委譲せずに自分で答えてしまう**ケースです。
最終回答に資料と違う数字が並んでいたら、まずログに `delegate_research` の行があるか確認してください。
行がなければ、親は委譲を飛ばして推測で答えています。
対処は、system に「あなた自身は資料を読めない」「調査は必ず委譲する」と明記することです。
本節のコードではすでにこの対策を入れています。

2つ目は、**親が1件ずつ順番に委譲する**ケースです。
ログで、`[orchestrator] tool_use` の行が1行ずつ、間に子のログを挟んで出てくる場合がこれにあたります。
3つの対象を3ターンかけて1件ずつ調べるので、並列化の効果がまったく得られません。
対処は、ツールの説明と system の両方に「独立した調査は1回の応答でまとめて呼び出す」と書くことです。
それでも逐次になる場合は、親のプロンプトで最初に「調べる対象の一覧」を書き出させてから委譲させると、まとめて呼び出しやすくなります。

3つ目は、**子がほかの対象の資料まで読む**ケースです。
`[researcher] tool_use: read_file` のログに、対象と関係のないファイル名が出てきたら、このケースです。
害がないこともありますが、別製品の数字が報告に混ざる原因になります。
対処は、子への指示の制約に「対象以外の資料から事実を書かない」と明記することです。
ファイル名と対象の対応が分かりにくい題材なら、親から子に読むべきファイル名を `context` で伝える方法もあります。

4つ目は、**子が最大ターン数に達して中断する**ケースです。
親に返る報告が「最大ターン数に達したため中断しました」になっていたら、子が迷走しています。
多くの場合、目的のファイルが見つからずに `list_files` を何度も繰り返しています。
あるいは、指示があいまいで、何を報告すべきか決められずにいます。
子の `max_turns` を増やす前に、まず指示の書き方を見直してください。
上限を増やすのは、指示が明確で、それでも手数が足りないと分かったときだけにします。

5つ目は、**子の中で API エラーが起きる**ケースです。
第4章の `call_messages()` はリトライを行います。
ただし、401 や 400 のようなリトライしないエラーは、例外として上がってきます。
リトライを使い切った 529 も同じです。
このとき、例外は委譲ツールの関数から `registry.execute()` を経て伝わります。
そして、親の側の第6章の `run_one_tool()` で捕まります。
親には `is_error: True` の tool_result として、エラーの種類を含む文字列が届きます。
エラーの種類とは、`OverloadedError` などです。
親のモデルはそれを読み、もう一度委譲するか、その製品を「調査失敗」として表に書くかを判断します。
親のループ全体が止まらないのは、`run_one_tool()` が例外を tool_result に変換しているおかげです。

> **WARNING: 子の失敗を握りつぶさない**
> 委譲ツールの中で `try/except` を書き、子の例外を「調査できませんでした」という普通の文字列にして返したくなることがあります。しかし、そうすると `is_error` が付かず、親は失敗を正常な報告として扱ってしまうかもしれません。例外はそのまま投げて、`run_one_tool()` に `is_error` 付きで返させるのが安全です。

ここまでで、同期版のマルチエージェントが完成しました。
第6章の仕組みのおかげで、親が複数の委譲をまとめて要求すれば、子はスレッドで並列に動きます。
しかし、スレッドによる並列化には限界があります。
同時に動かす子の数を細かく制御するには、スレッドより `asyncio` が向いています。
子の中のツール実行まで含めて、効率よく待ち時間を重ねる場合も同様です。
次の節では、`llm_client.py` に非同期版の呼び出しを追加し、`Agent` に `arun()` を実装します。

---

## 8.3 asyncioによる並列実行

前節では、第6章のスレッドによる並列ツール実行のおかげで、3つの子が同時に動きました。
では、調査対象が30件に増えたらどうなるでしょうか。
第6章のツール実行には、同時8本の上限（`MAX_PARALLEL_TOOLS`）があります。
ただし、子1本の中でもAPIを何度も呼びます。
利用ティアの上限が低いうちは、子を8本同時に走らせると、レート制限（429）に近づくことがあります。
しかもこの上限はツール実行のスレッド数で、子の数をきめ細かく制御するものではありません。
この節では、`asyncio`（エーシンクアイオー）で子を並列に動かす仕組みを作ります。
同時実行数は、`asyncio.Semaphore`（セマフォ）で制限します。

### なぜ asyncio なのか

エージェントの処理時間のほとんどは、APIの応答を「待っている」時間です。
`asyncio` は、1本のスレッドの中で、待ち時間に入った処理を脇に置いて別の処理を進める仕組みです。
スレッドと違って、待ちの区切りが `await` で明示されるため、同時に何本動いているかを数えて制御しやすいのが利点です。
本書では、`httpx.AsyncClient` で非同期にHTTPを送る `acall_messages()` を作ります。
その上に、`Agent.arun()` を載せます。

### llm_client.py に acall_messages を追加する

非同期版でも、リトライの規則は第4章と同じでなければなりません。
そこで、第4章で作った次の5つの関数を、非同期版でもそのまま呼び出します。

- `_build_body()`
- `_is_retryable()`
- `_retry_delay()`
- `_error_from_response()`
- `_log_call()`

判定のロジックが1か所にまとまっていれば、同期版と非同期版でリトライの規則が食い違うことはありません。
同じ名前の関数を引数の形を変えて定義し直すことには、注意してください。
ファイルの後ろの定義が第4章の関数を上書きしてしまいます。
その結果、同期版の `call_messages()` のエラー処理まで壊れます。

```python
# llm_client.py（更新: 非同期版を追加。既存の import に asyncio を足す）
import asyncio

# ---- 非同期クライアント（イベントループごとに1つ作って再利用） --------
_async_client: httpx.AsyncClient | None = None


def _get_async_client() -> httpx.AsyncClient:
    global _async_client
    if _async_client is None:
        _async_client = httpx.AsyncClient(timeout=httpx.Timeout(600.0, connect=10.0))
    return _async_client


async def aclose_client() -> None:
    # asyncio.run() を抜ける前に呼び、接続を閉じて次のループ用に作り直せるようにする
    global _async_client
    if _async_client is not None:
        await _async_client.aclose()
        _async_client = None


async def acall_messages(
    messages: list[dict], *, system: str | list[dict] | None = None,
    tools: list[dict] | None = None, model: str = MODEL, max_tokens: int = 16000,
    tool_choice: dict | None = None, output_config: dict | None = None,
    extra: dict | None = None, max_retries: int = 4,
) -> dict:
    """call_messages と同じ引数・同じリトライ規則の非同期版。"""
    # ボディの組み立ては同期版と同じ _build_body() を使う（None の項目は送らない）
    body = _build_body(messages, system=system, tools=tools, model=model,
                       max_tokens=max_tokens, tool_choice=tool_choice,
                       output_config=output_config, extra=extra, stream=False)
    client = _get_async_client()
    headers = build_headers()
    started = time.perf_counter()
    total_wait = 0.0
    for attempt in range(max_retries + 1):
        response: httpx.Response | None = None
        try:
            response = await client.post(API_URL, headers=headers, json=body)
        except httpx.TransportError as exc:      # 接続失敗・タイムアウト
            error: APIError = APIConnectionError(f"{type(exc).__name__}: {exc}", status=None)
            error.__cause__ = exc
        else:
            if response.status_code < 400:
                message: dict = response.json()
                cost = tracker.add(message)                    # コストを自動で集計
                _log_call(message, response.headers.get("request-id"),
                          time.perf_counter() - started, cost, False)
                return message
            error = _error_from_response(response)  # 第4章の「ステータス→例外クラス」変換

        # ここに来たら失敗。判定と待ち時間は第4章の関数をそのまま使う
        wait = _retry_delay(attempt, response)
        if (not _is_retryable(error) or attempt >= max_retries
                or total_wait + wait > MAX_TOTAL_WAIT):
            raise error
        logger.warning("retry %d/%d in %.1fs: %s", attempt + 1, max_retries, wait, error)
        await asyncio.sleep(wait)                # time.sleep は使わない
        total_wait += wait
    raise AssertionError("unreachable")
```

同期版との違いは3か所だけです。
`httpx.Client` の代わりに `httpx.AsyncClient` を使い、`post()` の前に `await` を付けます。
待ち時間は `time.sleep()` ではなく `await asyncio.sleep()` にします。
`time.sleep()` はスレッド全体を止めてしまい、ほかの子もすべて待たされるからです。
`_error_from_response()` は、第4章で作った処理を指します。
ステータスコードを、`RateLimitError` などの例外に変換する処理です。
名前が違う場合は手元の関数に読み替えてください。

> **WARNING: Event loop is closed エラー**
> `httpx.AsyncClient` は、作られたときのイベントループに結び付きます。`asyncio.run()` を2回呼ぶスクリプトで、同じクライアントを使い回したとします。すると、2回目に `RuntimeError: Event loop is closed` が出ます。対策として、`asyncio.run()` に渡す関数の最後で `await aclose_client()` を呼んでください。こうすると、次のループでは新しいクライアントが作られます。

### Agent に arun を追加する

次に、`Agent` に非同期版のループ `arun()` を追加します。
ループの流れは `run()` と同じで、`_request_kwargs()` と `_check_stop()` もそのまま共有します。
新しく、非同期で実行したいツールの実体を登録する `async_handlers` を足します。
既定値は空の dict なので、これまでの `Agent(...)` の呼び出し方は何も変わりません。

```python
# agent.py（更新: import と属性を追加し、非同期版のメソッドを足す）
import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from llm_client import acall_messages


@dataclass
class Agent:
    # …（name・system・registry・model・effort・max_turns と 8.2 のメソッドはそのまま）…
    # ツール名 → 非同期関数。arun() では registry より優先してこちらを await する
    async_handlers: dict[str, Callable[..., Awaitable[str]]] = field(default_factory=dict)

    async def _aexecute_one(self, tool_use: dict) -> dict:
        # async_handlers にある非同期ツール（委譲ツールなど）を1件実行する
        name, tool_input = tool_use["name"], tool_use["input"]
        try:
            content = await self.async_handlers[name](**tool_input)
            return make_tool_result(tool_use["id"], content)
        except Exception as exc:  # 子の失敗も is_error 付きでモデルに伝える
            logger.warning("[%s] tool error: %s: %s", self.name, name, exc)
            return make_tool_result(tool_use["id"], f"{type(exc).__name__}: {exc}", is_error=True)

    async def _aexecute_tools(self, tool_uses: list[dict]) -> list[dict]:
        for tu in tool_uses:
            logger.info("[%s] tool_use: %s %s", self.name, tu["name"], tu["input"])
        handled = [tu for tu in tool_uses if tu["name"] in self.async_handlers]
        others = [tu for tu in tool_uses if tu["name"] not in self.async_handlers]

        async def run_others() -> list[dict]:
            # 通常のツールは第6章の execute_tool_uses()（承認・切り詰め込み）を別スレッドで実行
            if not others:
                return []
            return await asyncio.to_thread(execute_tool_uses, self.registry, others)

        # 非同期ツールと通常のツールを同時に進め、元の tool_use の順番に並べ直す
        sync_results, *async_results = await asyncio.gather(
            run_others(), *(self._aexecute_one(tu) for tu in handled))
        by_id = {r["tool_use_id"]: r for r in [*sync_results, *async_results]}
        return [by_id[tu["id"]] for tu in tool_uses]

    async def arun(self, task: str) -> str:
        messages: list[dict] = [{"role": "user", "content": task}]
        kwargs = self._request_kwargs()
        for turn in range(1, self.max_turns + 1):
            # maybe_compact は同期関数（内部で count_tokens を呼ぶ）なのでスレッドに逃がす
            messages = await asyncio.to_thread(
                maybe_compact, messages, system=kwargs["system"], tools=kwargs["tools"])
            response = await acall_messages(messages, **kwargs)
            messages.append({"role": "assistant", "content": response["content"]})

            final = self._check_stop(response)
            if final is not None:
                logger.info("[%s] 完了（%dターン）", self.name, turn)
                return final

            # 1ターン内の tool_use をすべて同時に実行する。結果の順序は入力と同じ
            results = await self._aexecute_tools(get_tool_uses(response))
            messages.append({"role": "user", "content": results})

        logger.warning("[%s] max_turns=%d に達しました", self.name, self.max_turns)
        return f"[{self.name}] 最大ターン数（{self.max_turns}）に達したため中断しました。"
```

`_aexecute_tools()` は、ツール名が `async_handlers` にあるかどうかを調べます。
あるものは、`_aexecute_one()` で `await` します。
それ以外は、第6章の `execute_tool_uses()` を `asyncio.to_thread()` で別スレッドに逃がして実行します。
ファイル読み込みのような同期処理をそのまま呼ぶと、その間はほかの子がすべて止まってしまうからです。
`execute_tool_uses()` を通すので、副作用ツールの実行前確認と結果の切り詰めは非同期版でも働きます。
ツールのスキーマは `registry` から取ります。
そのため、委譲ツールは「スキーマは registry、実体は async_handlers」という形で登録します。

`asyncio.gather()` は、渡した処理をすべて同時に進め、終わったら結果を渡した順のリストで返します。
親が1ターンで `delegate_research` を3つ要求すれば、3つの子の `arun()` がここで同時に走ります。
最後に `tool_use_id` で元の順番に並べ直してから、1つの user メッセージにまとめます。
`_aexecute_one()` は、例外を tool_result に変換して返します。
そのため、`gather()` 自体が例外で中断することはありません。
自前で `gather()` を使う場面では、`return_exceptions=True` を付ける方法も覚えておきましょう。
こうすると、例外を結果として受け取れます。

### Semaphore で同時実行数を制限する

並列化で最も注意すべきなのは、同時に動かす子の数です。
APIには、組織ごとに1分あたりのリクエスト数やトークン数の上限があります。
上限を超えると 429 が返り、リトライの待ち時間でかえって全体が遅くなります。
そこで、`asyncio.Semaphore` で「同時に走る子は最大N本」と制限します。
セマフォは、N枚の入場券を配る係のようなものです。
券を持つ処理だけが中に入れ、出るときに券を返すと、待っていた次の処理が入れます。

<figure id="fig-8-4">
<svg width="605" height="300" viewBox="0 0 605 300" xmlns="http://www.w3.org/2000/svg" font-family="'Noto Sans JP',sans-serif">
  <defs>
    <marker id="f8_4_ar84" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#333" stroke-width="1.5"/>
    </marker>
  </defs>
  <!-- 順番待ち -->
  <text x="95" y="32" text-anchor="middle" font-size="12" fill="#1a1a1a" font-weight="bold">順番待ち</text>
  <rect x="40" y="50" width="110" height="36" rx="6" fill="#f5f5f5" stroke="#999" stroke-width="1" stroke-dasharray="4,3"/>
  <text x="95" y="73" text-anchor="middle" font-size="12" fill="#1a1a1a">子4</text>
  <rect x="40" y="100" width="110" height="36" rx="6" fill="#f5f5f5" stroke="#999" stroke-width="1" stroke-dasharray="4,3"/>
  <text x="95" y="123" text-anchor="middle" font-size="12" fill="#1a1a1a">子5</text>
  <rect x="40" y="150" width="110" height="36" rx="6" fill="#f5f5f5" stroke="#999" stroke-width="1" stroke-dasharray="4,3"/>
  <text x="95" y="173" text-anchor="middle" font-size="12" fill="#1a1a1a">子6</text>
  <path d="M152 118 L208 118" stroke="#333" stroke-width="1.3" marker-end="url(#f8_4_ar84)"/>
  <!-- ゲート -->
  <rect x="210" y="40" width="110" height="160" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.5"/>
  <text x="265" y="62" text-anchor="middle" font-size="12" fill="#1a1a1a" font-family="Consolas,monospace">Semaphore(3)</text>
  <text x="265" y="84" text-anchor="middle" font-size="12" fill="#1a1a1a" font-weight="bold">入場券は3枚</text>
  <text x="265" y="110" text-anchor="middle" font-size="10" fill="#1a1a1a">券を持つ処理</text>
  <text x="265" y="124" text-anchor="middle" font-size="10" fill="#1a1a1a">だけが中に入れる</text>
  <text x="265" y="160" text-anchor="middle" font-size="10" fill="#1a1a1a" font-family="Consolas,monospace">async with</text>
  <text x="265" y="174" text-anchor="middle" font-size="10" fill="#1a1a1a" font-family="Consolas,monospace">semaphore:</text>
  <path d="M320 118 L358 118" stroke="#333" stroke-width="1.3" marker-end="url(#f8_4_ar84)"/>
  <!-- 実行中 -->
  <rect x="360" y="40" width="230" height="160" rx="6" fill="none" stroke="#333" stroke-width="1.2"/>
  <text x="475" y="58" text-anchor="middle" font-size="12" fill="#1a1a1a" font-weight="bold">実行中（最大3本）</text>
  <rect x="375" y="68" width="200" height="34" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="388" y="89" font-size="11" fill="#1a1a1a">子1：<tspan font-family="Consolas,monospace">arun()</tspan></text>
  <rect x="520" y="75" width="44" height="20" rx="3" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.2"/>
  <text x="542" y="89" text-anchor="middle" font-size="10" fill="#1a1a1a">券</text>
  <rect x="375" y="110" width="200" height="34" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="388" y="131" font-size="11" fill="#1a1a1a">子2：<tspan font-family="Consolas,monospace">arun()</tspan></text>
  <rect x="520" y="117" width="44" height="20" rx="3" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.2"/>
  <text x="542" y="131" text-anchor="middle" font-size="10" fill="#1a1a1a">券</text>
  <rect x="375" y="152" width="200" height="34" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="388" y="173" font-size="11" fill="#1a1a1a">子3：<tspan font-family="Consolas,monospace">arun()</tspan></text>
  <rect x="520" y="159" width="44" height="20" rx="3" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.2"/>
  <text x="542" y="173" text-anchor="middle" font-size="10" fill="#1a1a1a">券</text>
  <!-- 券を返す -->
  <path d="M475 200 L475 228 L265 228 L265 203" fill="none" stroke="#2b6cb0" stroke-width="1.4" stroke-dasharray="5,3" marker-end="url(#f8_4_ar84)"/>
  <text x="370" y="248" text-anchor="middle" font-size="11" fill="#1a1a1a">1本終わると券を返す → 待っていた次の子が入る</text>
  <text x="302" y="283" text-anchor="middle" font-size="11" fill="#666"><tspan font-family="Consolas,monospace">MAX_CONCURRENCY = 3</tspan>：同時リクエスト数を抑えて 429 を避ける</text>
</svg>
  <figcaption>図8.4: Semaphore による同時実行数の制限</figcaption>
</figure>

`multi_agent.py` に、非同期版の親を作る関数と、逐次実行と並列実行を比べる関数を追加します。

```python
# multi_agent.py（更新: 非同期版の親と、逐次・並列の比較を追加）
import asyncio
import sys
import time

import llm_client
from llm_client import CostTracker, aclose_client

MAX_CONCURRENCY = 3   # 同時に走らせる子エージェントの上限


def build_async_orchestrator(semaphore: asyncio.Semaphore) -> Agent:
    researcher = build_researcher()
    registry = build_orchestrator_registry(researcher)   # スキーマは 8.2 と共通

    async def adelegate_research(topic: str, aspects: list[str], context: str = "") -> str:
        task = build_child_task(topic, aspects, context)
        async with semaphore:                    # 券が空くまでここで待つ
            logger.info("delegate_research (async) -> %s", topic)
            report = await researcher.arun(task)
        return clip_report(report)

    return Agent(name="orchestrator", system=ORCHESTRATOR_SYSTEM, registry=registry,
                 model=MODEL, max_turns=6,
                 async_handlers={"delegate_research": adelegate_research})


async def compare(topics: list[str]) -> None:
    aspects = ["月額料金", "対応OS", "サポート体制"]
    researcher = build_researcher()

    # 1) 逐次: 1件ずつ順番に子を走らせる
    llm_client.tracker = CostTracker()            # 計測用に集計をリセット
    start = time.perf_counter()
    for t in topics:
        await researcher.arun(build_child_task(t, aspects))
    print(f"逐次: {time.perf_counter() - start:.1f}s  {llm_client.tracker.summary()}")

    # 2) 並列: Semaphore で上限をかけつつ gather で同時に走らせる
    llm_client.tracker = CostTracker()
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)

    async def limited(t: str) -> str:
        async with semaphore:
            return await researcher.arun(build_child_task(t, aspects))

    start = time.perf_counter()
    reports = await asyncio.gather(*(limited(t) for t in topics), return_exceptions=True)
    print(f"並列: {time.perf_counter() - start:.1f}s  {llm_client.tracker.summary()}")
    failed = [t for t, r in zip(topics, reports) if isinstance(r, Exception)]
    print(f"失敗: {failed or 'なし'}")


async def amain() -> None:
    try:
        if "--compare" in sys.argv:
            await compare(["製品 Alpha", "製品 Beta", "製品 Gamma"])
        else:
            orchestrator = build_async_orchestrator(asyncio.Semaphore(MAX_CONCURRENCY))
            print(await orchestrator.arun(
                "workspace/docs にある Alpha・Beta・Gamma の3製品について、"
                "月額料金・対応OS・サポート体制を比較してください。10名のチームで使う予定です。"))
            print(llm_client.tracker.summary())
    finally:
        await aclose_client()                      # 接続を必ず閉じる


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # httpx自身のログは抑える
    if "--sync" in sys.argv:
        main()                                     # 8.2 の同期版
    else:
        asyncio.run(amain())
```

`build_async_orchestrator()` では、8.2節の関数を再利用しています。
再利用しているのは、`build_orchestrator_registry()` です。
使うのはスキーマだけで、実体は非同期版に差し替えています。
`async with semaphore:` で囲んでいるのは、子の `arun()` 全体です。
1本の子の中では API 呼び出しが順番に行われるので、子の数を制限すれば同時リクエスト数もほぼ同じ数に抑えられます。

`compare()` で `llm_client.tracker = CostTracker()` と書いている点に注意してください。
`acall_messages()` はモジュールの変数 `tracker` を呼び出しのたびに参照するので、この代入で集計がリセットされます。
一方、`from llm_client import tracker` で取り込んだ名前は古いインスタンスを指したままです。
リセット後の値を読むときは、必ず `llm_client.tracker` と書いてください。

### 逐次と並列の時間・コストを比べる

比較を実行してみましょう。

```bash
# 逐次と並列の所要時間・コストを比べる
uv run python multi_agent.py --compare
```

出力例は次のとおりです（ログ行は省略。時間とトークン数は環境・時間帯によって変わります）。

```text
逐次: 19.8s  calls=9 input=72 output=1,050 cache_write=2,200 cache_read=8,600 total=$0.0009
並列: 7.1s  calls=9 input=72 output=1,062 cache_write=1,000 cache_read=9,700 total=$0.0008
失敗: なし
```

所要時間は約3分の1になりましたが、呼び出し回数とトークンの合計はほとんど変わっていません。
並列化は「同じ仕事を同時にやる」だけなので、払う金額は減らないということです。
この例で並列のほうがわずかに安いのは、直前の逐次の実行で書き込まれたキャッシュ（有効期間は既定で5分）を読めたためです。
キャッシュがない状態で同時に送ると、最初の子の応答が始まる前にほかの子のリクエストが送られます。
その場合は、system とツール定義のキャッシュを読めず、書き込みが増えることがあります（8.2節の実行例）。
時間が縮むのは、待ち時間が重なった分だけです。
上限3で6件を処理すれば、3件ずつ2巡するので、時間は逐次の3分の1程度で頭打ちになります。

並列化の効果が出にくい場面も知っておきましょう。
子1本の時間が大きくばらつくと、全体の時間はいちばん遅い子で決まります。
429 が出始めたら、`MAX_CONCURRENCY` を下げるのが先決です。
上限を上げても速くならず、リトライの待ちで逆に遅くなります。

<figure id="fig-8-5">
<svg width="605" height="295" viewBox="0 0 605 295" xmlns="http://www.w3.org/2000/svg" font-family="'Noto Sans JP',sans-serif">
  <!-- 逐次 -->
  <text x="20" y="75" font-size="13" fill="#1a1a1a" font-weight="bold">逐次</text>
  <rect x="110" y="56" width="145" height="28" fill="#f5f5f5" stroke="#333" stroke-width="1"/>
  <text x="182" y="75" text-anchor="middle" font-size="11" fill="#1a1a1a">Alpha</text>
  <rect x="255" y="56" width="145" height="28" fill="#f5f5f5" stroke="#333" stroke-width="1"/>
  <text x="327" y="75" text-anchor="middle" font-size="11" fill="#1a1a1a">Beta</text>
  <rect x="400" y="56" width="146" height="28" fill="#f5f5f5" stroke="#333" stroke-width="1"/>
  <text x="473" y="75" text-anchor="middle" font-size="11" fill="#1a1a1a">Gamma</text>
  <text x="546" y="102" text-anchor="end" font-size="11" fill="#1a1a1a" font-weight="bold">合計 19.8s</text>
  <!-- 並列 -->
  <text x="20" y="168" font-size="13" fill="#1a1a1a" font-weight="bold">並列</text>
  <text x="20" y="184" font-size="10" fill="#666">（上限3）</text>
  <rect x="110" y="126" width="141" height="24" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.2"/>
  <text x="180" y="142" text-anchor="middle" font-size="11" fill="#1a1a1a">Alpha</text>
  <rect x="110" y="154" width="156" height="24" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.2"/>
  <text x="188" y="170" text-anchor="middle" font-size="11" fill="#1a1a1a">Beta</text>
  <rect x="110" y="182" width="147" height="24" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.2"/>
  <text x="183" y="198" text-anchor="middle" font-size="11" fill="#1a1a1a">Gamma</text>
  <line x1="266" y1="118" x2="266" y2="225" stroke="#2b6cb0" stroke-width="1.2" stroke-dasharray="4,3"/>
  <text x="276" y="160" font-size="11" fill="#2b6cb0" font-weight="bold">合計 7.1s</text>
  <text x="276" y="176" font-size="10" fill="#1a1a1a">いちばん遅い子で決まる</text>
  <!-- 時間軸 -->
  <line x1="110" y1="230" x2="555" y2="230" stroke="#333" stroke-width="1.2"/>
  <line x1="110" y1="230" x2="110" y2="236" stroke="#333" stroke-width="1"/>
  <line x1="220" y1="230" x2="220" y2="236" stroke="#333" stroke-width="1"/>
  <line x1="330" y1="230" x2="330" y2="236" stroke="#333" stroke-width="1"/>
  <line x1="440" y1="230" x2="440" y2="236" stroke="#333" stroke-width="1"/>
  <line x1="550" y1="230" x2="550" y2="236" stroke="#333" stroke-width="1"/>
  <text x="110" y="249" text-anchor="middle" font-size="10" fill="#1a1a1a">0s</text>
  <text x="220" y="249" text-anchor="middle" font-size="10" fill="#1a1a1a">5s</text>
  <text x="330" y="249" text-anchor="middle" font-size="10" fill="#1a1a1a">10s</text>
  <text x="440" y="249" text-anchor="middle" font-size="10" fill="#1a1a1a">15s</text>
  <text x="550" y="249" text-anchor="middle" font-size="10" fill="#1a1a1a">20s</text>
  <text x="20" y="30" font-size="11" fill="#1a1a1a">3製品の調査を子エージェントに任せた場合（出力例の値）</text>
  <text x="302" y="280" text-anchor="middle" font-size="11" fill="#666">時間は約3分の1。呼び出し回数（calls=9）・トークン・コストはほぼ同じ</text>
</svg>
  <figcaption>図8.5: 逐次実行と並列実行のタイムライン</figcaption>
</figure>

> **POINT: 並列化で減るのは時間、減らないのはコスト**
> 並列化は待ち時間を重ねる技術であり、トークン消費を減らす技術ではありません。コストを下げたいなら、子に安いモデルを使う、子への指示と報告を短くする、キャッシュを効かせるといった、別の工夫が必要です。

---

## 8.4 役割・モデル・権限の分離設計

仕組みができたら、次は「どう分けるか」の設計です。
ここでは、役割の切り方、モデルと effort の割り当て、ツール権限と受け渡し形式の3つを整理します。

### 役割の切り方

役割は「入力と出力がはっきりした仕事」の単位で切ります。
「Alpha を調べて観点ごとの事実を返す」は、入力も出力も明確なので良い単位です。
「いい感じに調べて」のように終わりが決まらない仕事は、子に任せても迷走するだけです。
また、子の報告だけを見て親が次の判断をできるかどうかも確かめてください。
親が結局原文を読まないと判断できないなら、その分け方は誤りです。

### モデルと effort の割り当て

モデルは、仕事の難しさと量で選びます。
判断が全体の質を左右するまとめ役には `MODEL`、量が多く定型的な読み取りには `FAST_MODEL` が基本です。
effort は `output_config` で考える深さを指定する設定で、Opus 5.5 の既定は `medium` です。

| 役割 | モデル | effort | 理由 |
|---|---|---|---|
| まとめ役（親） | `MODEL`（claude-opus-5-5） | 既定（medium） | 分解と統合の判断が全体の質を決める |
| 資料の読み取り | `FAST_MODEL`（claude-haiku-5-5） | 指定しない | 定型的で件数が多く、単価が効く |
| 難しい分析・検証 | `MODEL` | `high` | 誤りの影響が大きい箇所だけ深く考えさせる |
| 中間的な要約 | `claude-sonnet-5-5` | 指定しない | 品質とコストの中間 |

effort への対応はモデルによって異なり、対応しない組み合わせでは 400 が返る可能性があります。
`Agent` の `effort` を `None` にしておけば `output_config` は送られないので、迷ったら指定しないのが安全です。
割り当てを決めたら、8.3節の `compare()` のように実際に動かし、品質とコストを測って見直してください。

### 最小権限の原則と受け渡し形式

**最小権限の原則**とは、各エージェントに仕事に必要な最小限のツールだけを渡すという考え方です。
本章の例でも、調査担当には読み取りツールだけを、まとめ役には委譲ツールだけを渡しました。
子は外部の資料を読むので、資料の中に悪意ある指示が紛れ込む危険があります。
そうした子に書き込みツールがなければ、乗っ取られても被害は「誤った報告」にとどまります。
この攻撃（間接プロンプトインジェクション）への備えは、第11章で詳しく扱います。

<figure id="fig-8-6">
<svg width="605" height="290" viewBox="0 0 605 290" xmlns="http://www.w3.org/2000/svg" font-family="'Noto Sans JP',sans-serif">
  <!-- 見出し行 -->
  <rect x="20" y="20" width="150" height="40" fill="#f5f5f5" stroke="#333" stroke-width="1"/>
  <text x="95" y="45" text-anchor="middle" font-size="12" fill="#1a1a1a" font-weight="bold">エージェント</text>
  <rect x="170" y="20" width="103" height="40" fill="#f5f5f5" stroke="#333" stroke-width="1"/>
  <text x="221" y="45" text-anchor="middle" font-size="10" fill="#1a1a1a" font-family="Consolas,monospace">delegate_research</text>
  <rect x="273" y="20" width="103" height="40" fill="#f5f5f5" stroke="#333" stroke-width="1"/>
  <text x="324" y="45" text-anchor="middle" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">list_files</text>
  <rect x="376" y="20" width="103" height="40" fill="#f5f5f5" stroke="#333" stroke-width="1"/>
  <text x="427" y="45" text-anchor="middle" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">read_file</text>
  <rect x="479" y="20" width="103" height="40" fill="#f5f5f5" stroke="#333" stroke-width="1"/>
  <text x="530" y="45" text-anchor="middle" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">write_file</text>
  <!-- まとめ役 -->
  <rect x="20" y="60" width="150" height="50" fill="#fff" stroke="#333" stroke-width="1"/>
  <text x="95" y="81" text-anchor="middle" font-size="12" fill="#1a1a1a">まとめ役（親）</text>
  <text x="95" y="98" text-anchor="middle" font-size="10" fill="#1a1a1a" font-family="Consolas,monospace">orchestrator</text>
  <rect x="170" y="60" width="103" height="50" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.2"/>
  <text x="221" y="90" text-anchor="middle" font-size="12" fill="#2b6cb0" font-weight="bold">○ 渡す</text>
  <rect x="273" y="60" width="103" height="50" fill="#fff" stroke="#333" stroke-width="1"/>
  <text x="324" y="90" text-anchor="middle" font-size="12" fill="#999">—</text>
  <rect x="376" y="60" width="103" height="50" fill="#fff" stroke="#333" stroke-width="1"/>
  <text x="427" y="90" text-anchor="middle" font-size="12" fill="#999">—</text>
  <rect x="479" y="60" width="103" height="50" fill="#fff" stroke="#333" stroke-width="1"/>
  <text x="530" y="90" text-anchor="middle" font-size="12" fill="#999">—</text>
  <!-- 調査担当 -->
  <rect x="20" y="110" width="150" height="50" fill="#fff" stroke="#333" stroke-width="1"/>
  <text x="95" y="131" text-anchor="middle" font-size="12" fill="#1a1a1a">調査担当（子）</text>
  <text x="95" y="148" text-anchor="middle" font-size="10" fill="#1a1a1a" font-family="Consolas,monospace">researcher</text>
  <rect x="170" y="110" width="103" height="50" fill="#fff" stroke="#333" stroke-width="1"/>
  <text x="221" y="140" text-anchor="middle" font-size="12" fill="#999">—</text>
  <rect x="273" y="110" width="103" height="50" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.2"/>
  <text x="324" y="140" text-anchor="middle" font-size="12" fill="#2b6cb0" font-weight="bold">○ 渡す</text>
  <rect x="376" y="110" width="103" height="50" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.2"/>
  <text x="427" y="140" text-anchor="middle" font-size="12" fill="#2b6cb0" font-weight="bold">○ 渡す</text>
  <rect x="479" y="110" width="103" height="50" fill="#fff" stroke="#333" stroke-width="1"/>
  <text x="530" y="140" text-anchor="middle" font-size="12" fill="#999">—</text>
  <!-- 書き出し担当 -->
  <rect x="20" y="160" width="150" height="50" fill="#fff" stroke="#333" stroke-width="1"/>
  <text x="95" y="181" text-anchor="middle" font-size="12" fill="#1a1a1a">書き出し担当</text>
  <text x="95" y="198" text-anchor="middle" font-size="10" fill="#1a1a1a">（必要な場合）</text>
  <rect x="170" y="160" width="103" height="50" fill="#fff" stroke="#333" stroke-width="1"/>
  <text x="221" y="190" text-anchor="middle" font-size="12" fill="#999">—</text>
  <rect x="273" y="160" width="103" height="50" fill="#fff" stroke="#333" stroke-width="1"/>
  <text x="324" y="190" text-anchor="middle" font-size="10" fill="#999">任意</text>
  <rect x="376" y="160" width="103" height="50" fill="#fff" stroke="#333" stroke-width="1"/>
  <text x="427" y="190" text-anchor="middle" font-size="10" fill="#999">任意</text>
  <rect x="479" y="160" width="103" height="50" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.2"/>
  <text x="530" y="182" text-anchor="middle" font-size="12" fill="#2b6cb0" font-weight="bold">○ 渡す</text>
  <text x="530" y="199" text-anchor="middle" font-size="10" fill="#1a1a1a">実行前に確認</text>
  <text x="302" y="243" text-anchor="middle" font-size="12" fill="#1a1a1a" font-weight="bold">最小権限の原則：親は委譲のみ・調査担当は読み取りのみ</text>
  <text x="302" y="268" text-anchor="middle" font-size="11" fill="#666">書き込みツールがなければ、子が乗っ取られても被害は「誤った報告」にとどまる</text>
</svg>
  <figcaption>図8.6: 役割ごとのツール権限</figcaption>
</figure>

| エージェント | 渡すツール | 渡さないツール |
|---|---|---|
| まとめ役 | `delegate_research` | `read_file`・`write_file` |
| 調査担当 | `list_files`・`read_file` | `write_file`・`delegate_research` |
| 書き出し担当（必要な場合） | `write_file`（実行前に確認） | `delegate_research` |

受け渡し形式も設計の一部です。
本章では、子への指示を4部構成の Markdown に、報告を「観点: 内容（根拠）」の行に固定しました。
さらに厳密にしたければ、子の報告を構造化出力（`output_config.format`）で JSON にする方法もあります。
報告が大きくなる場合は、本文を `workspace/` にファイルとして保存し、親にはファイル名と要約だけを返す方法が有効です。
これらの受け渡し方式は、第9章で「戻り値・共有ストア・タスクリスト」として整理します。

---

## COLUMN: マルチエージェントは本当に必要か

本章でマルチエージェントを作りましたが、筆者はいつも「まず単一エージェントで足りないか」を先に考えます。
8.2節の例では、子への指示・報告・system・ツール定義が子ごとに重複して送られます。
同じ比較を単一エージェントで行うより、合計のトークン数は多くなるのが普通です。
調査が並列で進むほど、消費の速さも上がります。

単一エージェントと良いツールで足りるケースは意外と多くあります。
たとえば、`read_file` が全文ではなく必要な行だけを返すようにすれば、履歴の膨張はかなり抑えられます。
第7章の圧縮とキャッシュを組み合わせれば、数十ターンの仕事も1本のループで十分にこなせます。
分けるべきなのは、仕事が独立していて並列化の価値がある場合か、途中経過が大きく結果が小さい場合です。
迷ったら、単一エージェント版と分割版の両方を `compare()` のように計測し、時間・コスト・品質の数字で決めてください。

---

## 本章のまとめ

本章で学んだことを整理します：

- サブエージェントは、独立した `messages` 配列で動く子のループです。APIのステートレス性のおかげで、新しい配列を作るだけで別のエージェントになり、親には報告だけが返ります
- `Agent` クラスと委譲ツール `delegate_research` で、親が必要に応じて子を起動できるようになりました。子への指示はタスク・背景・出力形式・制約の4部構成で組み立てます
- 上限付きの並列実行ができます。使うのは `acall_messages()`・`Agent.arun()`・`asyncio.gather`・`Semaphore` です。並列化で減るのは時間で、コストは減りません。権限は役割ごとに最小限に絞ります

次章では **エージェント設計パターン** を扱います。部品がそろったところで、どんな形に組み立てるべきか——ワークフローとエージェントの判断基準と、代表的な設計パターンを整理します。
