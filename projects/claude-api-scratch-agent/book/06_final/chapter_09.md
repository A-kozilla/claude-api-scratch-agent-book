# 第9章: エージェント設計パターン
# EN-TITLE: AGENT DESIGN PATTERNS
# TAGS: ワークフロー, プロンプトチェーン, ルーティング, 並列化, 評価者-最適化者

## この章で学ぶこと

本章では以下を学びます：

- 単一呼び出し・ワークフロー・エージェントの違いを理解し、課題に合った段階を判断基準に沿って選べるようになる
- 4つのパターンを、`httpx`ベースの自前コードで実装できるようになる。プロンプトチェーン・ルーティング・並列化（セクショニングと投票）・評価者-最適化者の4つ
- オーケストレーター-ワーカーと第8章のマルチエージェント実装の関係を説明できる。また、エージェント間の情報連携の方式を使い分けられるようになる

前章では、`Agent`クラスへのリファクタリングを学びました。
また、非同期版の`acall_messages()`による、サブエージェントの並列実行も学びました。
本章では、それらの部品を「どう組み合わせると、どんな問題に強い構造になるか」という設計の観点から整理します。

ここまでの章で、読者のみなさんの手元には一通りの道具がそろいました。
HTTPでClaude APIを呼ぶ`llm_client.py`、ツールを回す`Agent`クラス、そして非同期の並列実行です。
しかし道具がそろうと、今度は「どれをどう使えばよいのか」という新しい悩みが生まれます。
本章はその悩みに答えるための章です。
地図として使うのは、Anthropicが公開している記事「Building effective agents」のパターン分類です。
それぞれのパターンを、ひとつずつ手を動かして確かめていきます。

---

## 9.1 ワークフローとエージェントの選び方

前章までの内容を学んだ読者の多くは、こう感じているかもしれません。
「せっかくエージェントを作れるようになったのだから、何でもエージェントに任せればよいのではないか」。
筆者も最初はそう考えていました。
しかし実際の開発現場では、エージェントにすべてを任せた結果、遅くて高くて不安定なシステムができあがることが少なくありません。
この節では、LLM（Large Language Model：大規模言語モデル）を使ったシステムを3つの段階に分けます。
そのうえで、どの段階を選ぶべきかを判断する基準を身につけます。

### 「エージェントを作る」前に立ち止まる理由

最初に、本章でもっとも大切な考え方を述べておきます。
それは「**必要になるまで複雑にしない**」という原則です。
Anthropicの記事「Building effective agents」でも、同じ趣旨のことが述べられています。
成功している実装の多くは、複雑なフレームワークではなく、シンプルで組み合わせやすい部品から作られているというのです。
本書がSDKを使わずに`httpx`で直接APIを呼んできたのも、この考え方と通じるところがあります。
仕組みが見えていれば、必要な分だけ複雑にできるからです。

なぜ複雑さを避けるべきなのでしょうか。
理由は大きく3つあります。
1つめは**コスト**です。
エージェントはツールを呼ぶたびにAPIを往復するため、呼び出し回数が増え、そのぶん料金と待ち時間がかさみます。
2つめは**予測可能性**です。
エージェントは次に何をするかをモデル自身が決めるので、同じ入力でも毎回同じ手順になるとは限りません。
3つめは**デバッグのしやすさ**です。
手順が固定されていれば、「どの段階で失敗したか」がすぐに分かります。
一方、エージェントの場合は会話履歴を追いかける必要があります。

もちろん、これはエージェントが悪いという意味ではありません。
手順を前もって決められない問題では、エージェントだけが解ける領域があります。
大切なのは、課題の性質に合った段階を選ぶことです。
そのために、まずは3つの段階を整理しておきましょう。

### 単一呼び出し・ワークフロー・エージェントの3段階

LLMを使ったシステムは、複雑さの順に次の3段階に分けて考えると整理しやすくなります。

**第1段階は単一呼び出し**です。
これは、1回のAPI呼び出しで仕事を終える形です。
第2章で作った`hello_claude.py`や、要約・翻訳・分類のような単発の処理がこれにあたります。
必要に応じて、検索結果やツールの定義、過去の会話などで入力を補強することもあります。
Anthropicの記事では、こうした補強を受けたLLMを「拡張されたLLM（augmented LLM）」と呼んでいます。
そして、すべてのパターンの基本部品と位置づけています。

**第2段階はワークフロー（workflow）**です。
ワークフローとは、複数のLLM呼び出しやツール実行を、**あらかじめコードで決めた手順**に沿ってつなげる形です。
「まず要点を抜き出し、次に下書きを書き、最後に翻訳する」というように、処理の流れはプログラマーが設計します。
モデルは各段階の中身を担当しますが、次に何をするかは決めません。
本章の9.2〜9.4節で扱うパターンは、すべてこのワークフローに属します。

**第3段階はエージェント（agent）**です。
エージェントとは、**次に何をするかをモデル自身が動的に決める**形です。
第5章から第8章で作ってきたツール使用のループがこれにあたります。
モデルは環境から結果を受け取り、それを見て次のツールを選び、ゴールに達したと判断したら止まります。
手順が事前に決まっていないため、想定外の状況にも柔軟に対応できます。
その代わり、何回ループするか、どのツールを呼ぶかは実行してみるまで分かりません。

<figure id="fig-9-1">
<svg width="605" height="350" viewBox="0 0 605 350" xmlns="http://www.w3.org/2000/svg" font-family="'Noto Sans JP',sans-serif">
  <defs>
    <marker id="f9_1_ar91" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#333" stroke-width="1.5"/>
    </marker>
  </defs>
  <!-- 第1段階 -->
  <rect x="25" y="230" width="170" height="70" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="110" y="252" text-anchor="middle" font-size="14" fill="#1a1a1a" font-weight="bold">単一呼び出し</text>
  <text x="110" y="272" text-anchor="middle" font-size="11" fill="#1a1a1a">API呼び出し1回で完結</text>
  <text x="110" y="290" text-anchor="middle" font-size="11" fill="#1a1a1a">例：要約・翻訳・分類</text>
  <!-- 第2段階 -->
  <rect x="215" y="160" width="170" height="140" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="300" y="182" text-anchor="middle" font-size="14" fill="#1a1a1a" font-weight="bold">ワークフロー</text>
  <text x="300" y="202" text-anchor="middle" font-size="11" fill="#1a1a1a">手順をコードで決める</text>
  <text x="300" y="220" text-anchor="middle" font-size="11" fill="#1a1a1a">例：抽出→執筆→翻訳</text>
  <text x="300" y="240" text-anchor="middle" font-size="10" fill="#666">（9.2〜9.5節）</text>
  <!-- 第3段階 -->
  <rect x="405" y="90" width="175" height="210" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.4"/>
  <text x="492" y="112" text-anchor="middle" font-size="14" fill="#1a1a1a" font-weight="bold">エージェント</text>
  <text x="492" y="132" text-anchor="middle" font-size="11" fill="#1a1a1a">次の一手をモデルが決める</text>
  <text x="492" y="150" text-anchor="middle" font-size="11" fill="#1a1a1a">例：ツール使用ループ</text>
  <text x="492" y="170" text-anchor="middle" font-size="10" fill="#666">（第5〜8章）</text>
  <text x="110" y="222" text-anchor="middle" font-size="11" fill="#666">第1段階</text>
  <text x="300" y="152" text-anchor="middle" font-size="11" fill="#666">第2段階</text>
  <text x="492" y="82" text-anchor="middle" font-size="11" fill="#2b6cb0" font-weight="bold">第3段階</text>
  <!-- 軸 -->
  <path d="M25 318 L578 318" stroke="#333" stroke-width="1.3" marker-end="url(#f9_1_ar91)"/>
  <text x="25" y="338" font-size="11" fill="#1a1a1a">予測しやすい・安い</text>
  <text x="302" y="338" text-anchor="middle" font-size="12" fill="#1a1a1a" font-weight="bold">複雑さと自律性</text>
  <text x="580" y="338" text-anchor="end" font-size="11" fill="#1a1a1a">柔軟・高コスト</text>
</svg>
  <figcaption>図9.1: 単一呼び出しからエージェントへの3段階</figcaption>
</figure>

この3段階の違いを、料理にたとえてみましょう。
単一呼び出しは、レトルト食品を温めるようなものです。
手順は1つで、結果もほぼ予想どおりになります。
ワークフローは、レシピに沿って料理をするようなものです。
工程は複数ありますが、順番はレシピが決めています。
エージェントは、冷蔵庫の中身を見てから献立を考える料理人のようなものです。
何が作れるかは材料しだいで、料理人がその場で判断します。

どの料理法が優れているという話ではありません。
毎日同じ弁当を大量に作るならレシピが最適ですし、冷蔵庫の中身が毎日違うなら料理人の判断が必要になります。
システム設計でも同じで、問題の性質に合った段階を選ぶことがもっとも重要です。

### ワークフローとエージェントを分ける一点

ワークフローとエージェントの境界は、ときにあいまいに見えます。
たとえば、ワークフローの中でツールを使うこともありますし、エージェントの中に固定の前処理が入ることもあります。
本書では、両者を分ける基準を次の一点に絞ります。

**「処理の流れ（次に何をするか）を決めているのは、コードか、モデルか」**

コードが決めているならワークフロー、モデルが決めているならエージェントです。
この基準で考えると、迷いが減ります。
たとえば、9.2節で作るルーティングでは、モデルが問い合わせの分類を行います。
一見するとモデルが流れを決めているようですが、分類結果をどの処理に渡すかはコードの辞書で決まっています。
モデルは「分類」という1つの仕事をしているだけなので、これはワークフローです。

一方、第8章で作ったオーケストレーター役の`Agent`は違いました。
どのサブエージェントに何を頼むかを、ツール呼び出しを通じて自分で決めていました。
呼び出す回数や順番もモデルしだいです。
これはエージェントです。
9.5節では、この違いをもう少し詳しく見ていきます。

> **POINT**: ワークフローかエージェントかは「LLMを何回呼ぶか」では決まりません。「次の一手をコードが決めるか、モデルが決めるか」で判断します。10回呼び出しても手順が固定ならワークフローです。

### 段階を選ぶための4つの判断基準

では、実際の課題に対して、どの段階を選べばよいのでしょうか。
本書では、次の4つの基準で考えることをおすすめします。

**1つめは「複雑さ」です。**
タスクの手順を前もって書き出せるかどうかを考えます。
「要約して、翻訳して、整形する」のように手順が明確なら、ワークフローで十分です。
「このバグの原因を調べて直して」のように、調べてみないと次の手順が決まらないなら、エージェントが向いています。
判断に迷ったら、実際に人間が作業するときの手順書を書いてみるとよいでしょう。
手順書が分岐の少ない1枚の紙に収まるなら、それはワークフローで実装できます。

**2つめは「価値」です。**
そのタスクの結果に、エージェントのコストと待ち時間に見合う価値があるかを考えます。
エージェントは単一呼び出しの何倍、ときには何十倍ものトークンを使います。
1件あたり数円の価値しかない大量処理にエージェントを使うと、採算が合わなくなります。
反対に、専門家が数時間かける調査を数十円で肩代わりできるなら、多少コストがかかっても十分に見合います。

**3つめは「実現性」です。**
モデルがそのタスクの中核となる能力を、実際に十分な水準で発揮できるかを確かめます。
たとえば、社内システムの独自の操作をエージェントに任せたくても、適切なツールが用意できなければ実現できません。
また、ツールを用意しても、モデルがそのツールを正しく使いこなせるかは試してみないと分かりません。
小さな試作で、最も難しい部分が本当に動くかを先に確かめるのが鉄則です。

**4つめは「失敗時のコスト」です。**
モデルが間違えたときに、どれくらいの損害が出るか、そしてその間違いに気づけるかを考えます。
下書きの作成のように、人間が最後に確認するなら、多少の失敗は許容できます。
一方、本番データベースの更新や送金のように、取り返しのつかない操作を伴う場合は慎重さが必要です。
自律性を高めるほど、失敗に気づく機会は減ります。
失敗のコストが高いなら、ワークフローで手順を固定するか、エージェントに人間の承認ステップを組み込むべきです。

この4つの基準を、表にまとめておきます。

| 判断基準 | 確認する問い | 単一呼び出し・ワークフロー寄り | エージェント寄り |
|---|---|---|---|
| 複雑さ | 手順を前もって書き出せるか | 書き出せる | 調べないと決まらない |
| 価値 | 結果にコストと時間に見合う価値があるか | 1件あたりの価値が小さい・大量処理 | 1件あたりの価値が大きい |
| 実現性 | 中核の能力をモデルとツールで実現できるか | 一部の段階だけモデルに任せたい | 一連の作業をモデルが通しでこなせる |
| 失敗時のコスト | 間違えたときの損害と、気づけるか | 損害が大きい・気づきにくい | 損害が小さい・検証しやすい |

4つの基準がすべてエージェントを指すことは、実はそれほど多くありません。
コーディング支援がエージェントの代表例として挙げられるのは、この4つがそろいやすいからです。
手順は問題ごとに違い、結果の価値は高く、モデルの能力は十分で、テストを実行すれば正しさを検証できます。
読者のみなさんが扱う課題も、この表に当てはめてみると、どの段階が向いているかが見えてくるはずです。

### 段階を上げるのは「測ってから」

もう1つ大切なのは、段階を一気に上げないことです。
まずは単一呼び出しで試し、プロンプトを工夫しても品質が足りない場合に、はじめてワークフローを検討します。
ワークフローでも対応しきれない柔軟さが必要になったときに、エージェントへ進みます。

ここで言う「品質が足りない」は、感覚ではなく測定で判断するのが理想です。
たとえば、20件ほどのテスト入力を用意し、単一呼び出しでの正答率を数えます。
次にワークフロー化して、同じ20件で正答率がどれだけ上がるか、コストと時間がどれだけ増えるかを比べます。
改善幅がコストの増加に見合わなければ、単一呼び出しのままで十分です。
評価の仕組みについては第11章で詳しく扱いますが、本章のパターンを試すときにも、この比較の視点を持っておいてください。

> **NOTE**: 単一呼び出しの品質は、プロンプトの工夫でかなり上がります。まずは、具体例を示す、出力形式を構造化出力で固定する、`output_config`の`effort`を上げるといった手を試しましょう。パターン化を考えるのは、それからでも遅くはありません。

### 代表的な設計パターンの全体マップ

ここからは、本章で扱う設計パターンの全体像を見ておきましょう。
Anthropicの「Building effective agents」では、ワークフローの代表的なパターンとして5つが紹介されています。
そこに自律的なエージェントを加えた6つが、本章の地図になります。

<figure id="fig-9-2">
<svg width="605" height="370" viewBox="0 0 605 370" xmlns="http://www.w3.org/2000/svg" font-family="'Noto Sans JP',sans-serif">
  <defs>
    <marker id="f9_2_ar92" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#333" stroke-width="1.5"/>
    </marker>
  </defs>
  <!-- ワークフローの枠 -->
  <rect x="12" y="22" width="508" height="238" rx="6" fill="none" stroke="#999" stroke-width="1" stroke-dasharray="5,4"/>
  <text x="24" y="232" font-size="12" fill="#1a1a1a" font-weight="bold">ワークフロー</text>
  <text x="24" y="250" font-size="10" fill="#666">流れはコードが決める（9.2〜9.5節）</text>
  <rect x="20" y="30" width="200" height="38" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="120" y="46" text-anchor="middle" font-size="12" fill="#1a1a1a" font-weight="bold">プロンプトチェーン</text>
  <text x="120" y="61" text-anchor="middle" font-size="10" fill="#1a1a1a" font-family="Consolas,monospace">patterns/chain.py</text>
  <rect x="93" y="76" width="200" height="38" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="193" y="92" text-anchor="middle" font-size="12" fill="#1a1a1a" font-weight="bold">ルーティング</text>
  <text x="193" y="107" text-anchor="middle" font-size="10" fill="#1a1a1a" font-family="Consolas,monospace">patterns/router.py</text>
  <rect x="166" y="122" width="200" height="38" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="266" y="138" text-anchor="middle" font-size="12" fill="#1a1a1a" font-weight="bold">並列化（セクショニング・投票）</text>
  <text x="266" y="153" text-anchor="middle" font-size="10" fill="#1a1a1a" font-family="Consolas,monospace">patterns/parallel.py</text>
  <rect x="239" y="168" width="200" height="38" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="339" y="184" text-anchor="middle" font-size="12" fill="#1a1a1a" font-weight="bold">評価者-最適化者</text>
  <text x="339" y="199" text-anchor="middle" font-size="10" fill="#1a1a1a" font-family="Consolas,monospace">patterns/evaluator_optimizer.py</text>
  <rect x="312" y="214" width="200" height="38" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="412" y="230" text-anchor="middle" font-size="12" fill="#1a1a1a" font-weight="bold">オーケストレーター-ワーカー</text>
  <text x="412" y="245" text-anchor="middle" font-size="10" fill="#1a1a1a">分解はモデル・実行はコード</text>
  <!-- エージェント -->
  <rect x="385" y="274" width="200" height="38" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.4"/>
  <text x="485" y="290" text-anchor="middle" font-size="12" fill="#1a1a1a" font-weight="bold">自律エージェント</text>
  <text x="485" y="305" text-anchor="middle" font-size="10" fill="#1a1a1a">第5〜8章の <tspan font-family="Consolas,monospace">Agent</tspan></text>
  <text x="24" y="290" font-size="12" fill="#2b6cb0" font-weight="bold">エージェント</text>
  <text x="24" y="306" font-size="10" fill="#666">流れはモデルが決める</text>
  <!-- 軸 -->
  <path d="M20 330 L585 330" stroke="#333" stroke-width="1.3" marker-end="url(#f9_2_ar92)"/>
  <text x="20" y="350" font-size="11" fill="#1a1a1a">コードが流れを決める</text>
  <text x="302" y="350" text-anchor="middle" font-size="12" fill="#1a1a1a" font-weight="bold">自律性</text>
  <text x="585" y="350" text-anchor="end" font-size="11" fill="#1a1a1a">モデルが流れを決める</text>
</svg>
  <figcaption>図9.2: 設計パターンの全体マップ</figcaption>
</figure>

**プロンプトチェーン（prompt chaining）**は、タスクを順番に並んだ段階に分けるパターンです。
前の段階の出力を、次の段階の入力にします。
段階の間に、コードで出力を検査する「ゲート」を置けるのが特徴です。
9.2節で`patterns/chain.py`として実装します。

**ルーティング（routing）**は、入力を分類し、分類結果に応じて専用の処理へ振り分けるパターンです。
問い合わせの種類ごとに、プロンプトやモデルを使い分けたい場面で役立ちます。
9.2節で`patterns/router.py`として実装します。

**並列化（parallelization）**は、複数のLLM呼び出しを同時に実行し、結果を集めるパターンです。
並列化には2種類あります。
1つは、独立した部分に分けて同時に処理する「セクショニング（sectioning）」です。
もう1つは、同じ判定を複数回行って多数決をとる「投票（voting）」です。
9.3節で`patterns/parallel.py`として実装します。

**評価者-最適化者（evaluator-optimizer）**は、生成役と評価役を分けるパターンです。
評価のフィードバックをもとに、改善を繰り返します。
明確な評価基準があり、繰り返しで品質が上がる課題に向いています。
9.4節で`patterns/evaluator_optimizer.py`として実装します。

**オーケストレーター-ワーカー（orchestrator-workers）**は、中心となるLLMがタスクを動的に分解するパターンです。
分解したタスクをワーカーに割り振り、結果を統合します。
サブタスクの数や内容が入力ごとに変わる点が、並列化との大きな違いです。
9.5節で、第8章の実装との関係を整理します。

**自律エージェント（autonomous agents）**は、モデルが自分で次の行動を決めてループするものです。
モデルは、ツールの結果を見ながら次の行動を決めます。
これは第5章から第8章で作ってきた`Agent`そのものです。

| パターン | 処理の流れを決めるもの | 向いている課題 | 本書での実装 |
|---|---|---|---|
| プロンプトチェーン | コード（固定の順番） | 段階に分けると各段が簡単になるタスク | `patterns/chain.py` |
| ルーティング | コード（分類→振り分け表） | 入力の種類で最適な処理が違うタスク | `patterns/router.py` |
| 並列化（セクショニング） | コード（固定の分担） | 独立した観点に分けられるタスク | `patterns/parallel.py` |
| 並列化（投票） | コード（同じ判定を複数回） | 判定の信頼度を上げたいタスク | `patterns/parallel.py` |
| 評価者-最適化者 | コード（ループと終了条件） | 評価基準が明確で、改善の余地があるタスク | `patterns/evaluator_optimizer.py` |
| オーケストレーター-ワーカー | モデル（分解）＋コード（実行） | サブタスクが入力しだいで変わるタスク | 第8章・第10章 |
| 自律エージェント | モデル | 手順を前もって決められないタスク | 第5〜8章の`Agent` |

表の上から下へ進むほど、モデルが流れを決める度合いが強くなります。
本章では、この順番に沿って実装を進めます。
上のパターンほどシンプルで、コストも予測しやすいことを意識しながら読み進めてください。

### 本章のコードの置き場所と動かし方

本章のコードは、プロジェクト`agent-from-scratch/`の中に`patterns/`ディレクトリを作って配置します。
各ファイルは、単独で実行できるスクリプトになっています。
いずれも、第4章の`llm_client.py`を使います。並列化の`parallel.py`では、第8章の`acall_messages()`も使います。

```text
agent-from-scratch/
├── llm_client.py            # 第4章で作成・第7章と第8章で拡張済み
├── agent.py                 # 第8章の Agent クラス
└── patterns/                # 本章で新規作成
    ├── __init__.py          # 構造化出力の共通ヘルパー
    ├── chain.py             # 9.2 プロンプトチェーン
    ├── router.py            # 9.2 ルーティング
    ├── parallel.py          # 9.3 並列化（セクショニングと投票）
    └── evaluator_optimizer.py  # 9.4 評価者-最適化者
```

`patterns/`の中のファイルは、プロジェクト直下の`llm_client.py`をimportします。
そのため、実行するときはプロジェクトのルートで、`-m`オプションを付けてモジュールとして起動します。

```bash
# プロジェクトのルート（agent-from-scratch/）で実行する
uv run python -m patterns.chain
```

`uv run python patterns/chain.py`のように、ファイルのパスを直接指定したとします。
すると、Pythonは`patterns/`ディレクトリを基準にimportを探します。
その結果、`ModuleNotFoundError: No module named 'llm_client'`というエラーになります。
`-m patterns.chain`と書けば、カレントディレクトリ（プロジェクトのルート）が基準になります。
そのため、`llm_client`も`patterns`も見つかります。
本章で何度も使う起動方法なので、ここで覚えておいてください。

### 共通ヘルパーを用意する

本章のパターンでは、モデルの出力をJSONとして受け取る場面が何度も出てきます。
そのときに使うのが、構造化出力（structured outputs）です。
第6章で学んだとおり、構造化出力は`output_config`の`format`に`json_schema`を指定して使います。
受け取ったJSONは、テキストブロックの中身として返ってきます。
毎回同じ処理を書くのは手間なので、`patterns/__init__.py`に共通ヘルパーをまとめておきます。

```python
# patterns/__init__.py
"""第9章 設計パターン集の共通ヘルパー（新規作成）"""
import json

from llm_client import extract_text


class PatternError(Exception):
    """パターンの途中で処理を続けられなくなったことを表す例外"""


def json_format(schema: dict) -> dict:
    """構造化出力を使うための output_config を組み立てる"""
    # output_config={"format": {"type": "json_schema", "schema": ...}} の形にする
    return {"format": {"type": "json_schema", "schema": schema}}


def parse_json_response(response: dict) -> dict:
    """stop_reason を確認してから、テキストブロックの JSON を dict に変換する"""
    stop_reason = response.get("stop_reason")
    # 拒否された場合は本文を読まずに止める（stop_details に理由が入る）
    if stop_reason == "refusal":
        raise PatternError(f"モデルが応答を拒否しました: {response.get('stop_details')}")
    # max_tokens で打ち切られた JSON は途中で切れているので解析しない
    if stop_reason == "max_tokens":
        raise PatternError("max_tokens に達したため、JSON が途中で切れています")
    # thinking ブロックなどを除き、text ブロックだけを連結して取り出す
    text = extract_text(response)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        # 解析に失敗したら、原因調査のために先頭部分をエラーに含める
        raise PatternError(f"JSON として解釈できません: {text[:200]}") from exc
```

このヘルパーは小さいですが、本章のすべてのパターンの土台になります。
1行ずつ確認しておきましょう。

`PatternError`は、本章のパターンで「これ以上処理を続けられない」ときに投げる独自の例外です。
第4章で作った`APIError`は、HTTP通信の失敗を表します。
これに対し、`PatternError`は「通信には成功したが、中身が使えない」ことを表します。
両者を分けておくと、呼び出し側で「リトライすべき失敗」と「設計を見直すべき失敗」を区別しやすくなります。

`json_format()`は、スキーマを受け取って`output_config`の形に包むだけの関数です。
わざわざ関数にしているのは、`output_config`の入れ子の形を書き間違えないためです。
入れ子の形は、`{"format": {"type": "json_schema", "schema": ...}}`です。
これを何度も手で書いていると、どこかで間違えます。

`parse_json_response()`は、もっとも重要な関数です。
最初に`stop_reason`を確認しているのは、第3章で学んだ原則に従うためです。
その原則とは、「本文を読む前に必ず`stop_reason`を判定する」というものです。
`refusal`のときは、モデルが安全上の理由で応答を拒否しているので、本文を読んでも意味がありません。
`max_tokens`のときは、JSONが途中で切れている可能性が高く、`json.loads()`は必ず失敗します。
どちらの場合も、原因がすぐに分かるメッセージを付けて例外にします。

その後の`extract_text()`は、第4章で作った関数です。
`content`配列から`type`が`text`のブロックだけを連結して返します。
Opus 5.5では、adaptive thinking（アダプティブ・シンキング）が常に有効です。
そのため、`content`の先頭に`thinking`ブロックが入ることがあります。
`content[0]`を決め打ちで読むと、この`thinking`ブロックを読んでしまいます。
`extract_text()`を使えば、この問題を避けられます。

> **WARNING**: 構造化出力を使っていても、`json.loads()`の前に`stop_reason`を確認してください。`max_tokens`が小さすぎると、スキーマに沿ったJSONが途中で切れて返ってきます。分類のような短い出力でも、思考の分だけ出力トークンを使う点に注意が必要です。

これで準備が整いました。
次の節から、地図の上の方にあるシンプルなパターンから順に実装していきます。

---

## 9.2 プロンプトチェーンとルーティング

1回の呼び出しに「抜き出して、書いて、翻訳して」と全部を頼むと、どこかが雑になりがちです。
また、問い合わせの種類がばらばらなのに、1つのプロンプトですべてに答えさせると、どの種類にも中途半端な回答になります。
この節では、こうした悩みに効く2つのワークフロー、プロンプトチェーンとルーティングを実装します。

### プロンプトチェーンとゲート

プロンプトチェーンとは、タスクを順番に並んだ段階に分け、各段階の出力を次の段階に渡していくパターンです。
1回の呼び出しで頼む仕事が小さくなるので、各段階の精度が上がります。
その代わり、呼び出し回数が増えるため、時間とコストは増えます。
つまり、**速さを少し犠牲にして、正確さを買う**パターンです。

チェーンのもう1つの利点は、段階の間に**ゲート（gate）**を置けることです。
ゲートとは、前の段階の出力をコードで検査し、条件を満たさなければ先に進ませない関門のことです。
たとえば「価格が抜き出せていなければ、宣伝文を書かせない」という具合です。
問題を早い段階で止められるので、無駄な呼び出しと、誤った情報を含む成果物の両方を防げます。

<figure id="fig-9-3">
<svg width="605" height="295" viewBox="0 0 605 295" xmlns="http://www.w3.org/2000/svg" font-family="'Noto Sans JP',sans-serif">
  <defs>
    <marker id="f9_3_ar93" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#333" stroke-width="1.5"/>
    </marker>
  </defs>
  <!-- 入力 -->
  <rect x="10" y="28" width="90" height="30" rx="6" fill="#fff" stroke="#999" stroke-width="1" stroke-dasharray="4,3"/>
  <text x="55" y="48" text-anchor="middle" font-size="12" fill="#1a1a1a">製品メモ</text>
  <path d="M55 58 L55 98" stroke="#333" stroke-width="1.3" marker-end="url(#f9_3_ar93)"/>
  <!-- 抽出 -->
  <rect x="10" y="100" width="90" height="70" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="55" y="122" text-anchor="middle" font-size="13" fill="#1a1a1a" font-weight="bold">① 抽出</text>
  <text x="55" y="140" text-anchor="middle" font-size="10" fill="#1a1a1a" font-family="Consolas,monospace">step_extract</text>
  <text x="55" y="157" text-anchor="middle" font-size="10" fill="#1a1a1a" font-family="Consolas,monospace">FAST_MODEL</text>
  <path d="M100 135 L136 135" stroke="#333" stroke-width="1.3" marker-end="url(#f9_3_ar93)"/>
  <!-- ゲート1 -->
  <polygon points="178,100 218,135 178,170 138,135" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="178" y="132" text-anchor="middle" font-size="11" fill="#1a1a1a" font-weight="bold">ゲート</text>
  <text x="178" y="147" text-anchor="middle" font-size="9" fill="#1a1a1a" font-family="Consolas,monospace">gate_facts</text>
  <path d="M218 135 L254 135" stroke="#333" stroke-width="1.3" marker-end="url(#f9_3_ar93)"/>
  <text x="237" y="127" text-anchor="middle" font-size="10" fill="#1a1a1a">合格</text>
  <!-- 執筆 -->
  <rect x="256" y="100" width="90" height="70" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="301" y="122" text-anchor="middle" font-size="13" fill="#1a1a1a" font-weight="bold">② 執筆</text>
  <text x="301" y="140" text-anchor="middle" font-size="10" fill="#1a1a1a" font-family="Consolas,monospace">step_draft</text>
  <text x="301" y="157" text-anchor="middle" font-size="10" fill="#1a1a1a" font-family="Consolas,monospace">MODEL</text>
  <path d="M346 135 L382 135" stroke="#333" stroke-width="1.3" marker-end="url(#f9_3_ar93)"/>
  <!-- ゲート2 -->
  <polygon points="424,100 464,135 424,170 384,135" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="424" y="132" text-anchor="middle" font-size="11" fill="#1a1a1a" font-weight="bold">ゲート</text>
  <text x="424" y="147" text-anchor="middle" font-size="9" fill="#1a1a1a" font-family="Consolas,monospace">gate_draft</text>
  <path d="M464 135 L500 135" stroke="#333" stroke-width="1.3" marker-end="url(#f9_3_ar93)"/>
  <text x="483" y="127" text-anchor="middle" font-size="10" fill="#1a1a1a">合格</text>
  <!-- 翻訳 -->
  <rect x="502" y="100" width="90" height="70" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="547" y="122" text-anchor="middle" font-size="13" fill="#1a1a1a" font-weight="bold">③ 翻訳</text>
  <text x="547" y="140" text-anchor="middle" font-size="10" fill="#1a1a1a" font-family="Consolas,monospace">step_translate</text>
  <text x="547" y="157" text-anchor="middle" font-size="10" fill="#1a1a1a" font-family="Consolas,monospace">FAST_MODEL</text>
  <path d="M547 170 L547 213" stroke="#333" stroke-width="1.3" marker-end="url(#f9_3_ar93)"/>
  <!-- 出力 -->
  <rect x="503" y="215" width="89" height="40" rx="6" fill="#fff" stroke="#999" stroke-width="1" stroke-dasharray="4,3"/>
  <text x="547" y="232" text-anchor="middle" font-size="11" fill="#1a1a1a">日本語の紹介文</text>
  <text x="547" y="248" text-anchor="middle" font-size="11" fill="#1a1a1a">＋英語版</text>
  <!-- ゲート1不合格 -->
  <path d="M178 170 L178 213" stroke="#333" stroke-width="1.3" marker-end="url(#f9_3_ar93)"/>
  <text x="184" y="196" font-size="10" fill="#1a1a1a">不合格</text>
  <rect x="128" y="215" width="100" height="40" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="178" y="232" text-anchor="middle" font-size="11" fill="#1a1a1a" font-weight="bold">ここで停止</text>
  <text x="178" y="248" text-anchor="middle" font-size="10" fill="#1a1a1a" font-family="Consolas,monospace">PatternError</text>
  <!-- ゲート2不合格 -->
  <path d="M424 170 L424 213" stroke="#333" stroke-width="1.3" marker-end="url(#f9_3_ar93)"/>
  <text x="430" y="196" font-size="10" fill="#1a1a1a">不合格</text>
  <rect x="350" y="215" width="148" height="40" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="424" y="232" text-anchor="middle" font-size="11" fill="#1a1a1a">指摘を添えて書き直し</text>
  <text x="424" y="248" text-anchor="middle" font-size="10" fill="#1a1a1a"><tspan font-family="Consolas,monospace">max_retries</tspan> 回まで</text>
  <path d="M350 235 L301 235 L301 172" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f9_3_ar93)"/>
  <text x="250" y="283" text-anchor="middle" font-size="11" fill="#666">ゲートは LLM を呼ばない Python 関数。問題を早い段階で止める</text>
</svg>
  <figcaption>図9.3: ゲート付きプロンプトチェーン</figcaption>
</figure>

本書では、製品メモから日本語の紹介文と英語版を作るチェーンを題材にします。
段階は次の3つです。

1. **抽出**：製品メモから製品名・対象ユーザー・特徴・価格を構造化出力で抜き出す（FAST_MODEL）
2. **執筆**：抜き出した事実だけを使って日本語の紹介文を書く（MODEL）
3. **翻訳**：紹介文を英語に翻訳する（FAST_MODEL）

抽出と翻訳は比較的やさしい仕事なので、安価な`FAST_MODEL`（`claude-haiku-5-5`）に任せます。
文章の質が問われる執筆だけを`MODEL`（`claude-opus-5-5`）にします。
段階ごとにモデルを選べるのも、チェーンに分ける利点です。

### patterns/chain.py を作る

それでは`patterns/chain.py`を新規作成します。
まずは、抽出の段階とそのゲートです。

```python
# patterns/chain.py
"""プロンプトチェーン: 段階ごとに呼び出しを分け、間にゲートを置く（新規作成）"""
import json
import logging
from dataclasses import dataclass, field

from llm_client import FAST_MODEL, MODEL, call_messages, extract_text, tracker
from patterns import PatternError, json_format, parse_json_response

logger = logging.getLogger("patterns.chain")

# --- 段階1: 抽出（構造化出力で事実だけを取り出す） ---
FACTS_SCHEMA = {
    "type": "object",
    "properties": {
        "product_name": {"type": "string"},
        "target_user": {"type": "string"},
        "features": {"type": "array", "items": {"type": "string"}},
        "price": {"type": "string"},
    },
    "required": ["product_name", "target_user", "features", "price"],
    "additionalProperties": False,
}


def step_extract(memo: str) -> dict:
    """製品メモから事実を抜き出す。メモにない項目は空文字・空配列にさせる"""
    response = call_messages(
        [{"role": "user", "content": f"次の製品メモから事実を抜き出してください。\n\n<memo>\n{memo}\n</memo>"}],
        system="あなたは製品情報の整理係です。メモに書かれていない情報は推測せず、空文字または空配列にしてください。",
        model=FAST_MODEL,
        max_tokens=2000,
        output_config=json_format(FACTS_SCHEMA),
    )
    return parse_json_response(response)


def gate_facts(facts: dict) -> list[str]:
    """抽出結果をコードで検査し、問題点のリストを返す（空なら合格）"""
    problems = []
    if not facts["product_name"].strip():
        problems.append("製品名がありません")
    if len(facts["features"]) < 2:
        problems.append("特徴が2つ未満です")
    if not facts["price"].strip():
        problems.append("価格がありません")
    return problems
```

`FACTS_SCHEMA`は、抽出結果の形を決めるJSON Schemaです。
第6章で学んだとおり、`additionalProperties: False`と`required`をそろえておきます。
そうすると、スキーマどおりのJSONが返ってきます。

`step_extract()`のsystem プロンプトでは「推測せず、空にする」ことを明示しています。
ここが抽出段階の肝です。
モデルは親切なので、メモに価格がなくても「それらしい価格」を補ってしまうことがあります。
空にさせておけば、次のゲートで「価格がない」ことを確実に検出できます。

`gate_facts()`はLLMを呼ばない、ただのPython関数です。
ゲートは、できるだけコードで書くのが基本です。
コードのゲートは速く、無料で、毎回同じ判定をします。
「特徴が2つ以上」のような数の条件は、スキーマの制約よりもコードで書いた方が確実です。

> **NOTE**: JSON Schemaには`minItems`や`maxLength`などの制約もあります。ただし、構造化出力では`minItems`は0か1しか使えません。また、次の5つは非対応で、送ると400エラーになります。`maxItems`・`minLength`・`maxLength`・`minimum`・`maximum`です。細かな条件はスキーマに頼らず、ゲートでコードとして検査しましょう。その方が、移植性も高く安心です。

続いて、執筆と翻訳の段階です。

```python
# patterns/chain.py（続き）
# --- 段階2: 執筆（事実だけを使って紹介文を書く） ---
BANNED_WORDS = ["業界No.1", "絶対", "100%"]  # 根拠のない誇大表現は使わせない


def step_draft(facts: dict, feedback: list[str] | None = None) -> str:
    """紹介文を書く。前回ゲートで落ちた場合は、その指摘を添えて書き直させる"""
    prompt = (
        "次の事実だけを使って、製品の紹介文を日本語で300字以内で書いてください。\n\n"
        f"<facts>\n{json.dumps(facts, ensure_ascii=False, indent=2)}\n</facts>"
    )
    if feedback:
        # ゲートの指摘をそのまま伝えると、書き直しの精度が上がる
        prompt += "\n\n前回の原稿には次の問題がありました。直してください。\n- " + "\n- ".join(feedback)
    response = call_messages(
        [{"role": "user", "content": prompt}],
        system="あなたは製品紹介文のライターです。事実にない効果や数値は書かないでください。紹介文の本文だけを出力してください。",
        model=MODEL,
        max_tokens=8000,
    )
    if response["stop_reason"] != "end_turn":
        raise PatternError(f"執筆が正常に終わりませんでした: {response['stop_reason']}")
    return extract_text(response).strip()


def gate_draft(draft: str, max_chars: int = 300) -> list[str]:
    """紹介文の長さと禁止語をコードで検査する"""
    problems = []
    if len(draft) > max_chars:
        problems.append(f"{len(draft)}字あり、上限の{max_chars}字を超えています")
    for word in BANNED_WORDS:
        if word in draft:
            problems.append(f"禁止語「{word}」が含まれています")
    return problems


# --- 段階3: 翻訳 ---
def step_translate(draft: str) -> str:
    """紹介文を英語に翻訳する"""
    response = call_messages(
        [{"role": "user", "content": f"次の紹介文を自然な英語に翻訳してください。訳文だけを出力してください。\n\n{draft}"}],
        model=FAST_MODEL,
        max_tokens=4000,
    )
    if response["stop_reason"] != "end_turn":
        raise PatternError(f"翻訳が正常に終わりませんでした: {response['stop_reason']}")
    return extract_text(response).strip()
```

`step_draft()`は、`feedback`引数を受け取れるようにしています。
ゲートで落ちたとき、その理由を添えてもう一度書かせるためです。
「300字を超えています」と具体的に伝えれば、モデルは的確に短くします。
ゲートの検査結果を、そのまま書き直しの指示として再利用しているわけです。

`max_tokens=8000`と大きめにしているのは、Opus 5.5の思考も出力トークンに含まれるからです。
紹介文が300字でも、考える分の余裕を見ておかないと`max_tokens`で止まってしまいます。

最後に、3つの段階をつなぐ`run_chain()`と、実行用の`main()`です。

```python
# patterns/chain.py（続き）
@dataclass
class ChainResult:
    """各段階の中間結果を残しておく（どこで何が起きたか後から追える）"""
    facts: dict = field(default_factory=dict)
    draft: str = ""
    translation: str = ""
    retries: int = 0


def run_chain(memo: str, *, max_retries: int = 1) -> ChainResult:
    """抽出 → ゲート → 執筆 → ゲート → 翻訳 の順に実行する"""
    result = ChainResult()

    # 段階1と1つめのゲート: 事実が足りなければ、ここで止める
    result.facts = step_extract(memo)
    logger.info("抽出完了: %s", result.facts["product_name"])
    if problems := gate_facts(result.facts):
        raise PatternError(f"抽出ゲートで停止: {problems}")

    # 段階2と2つめのゲート: 不合格なら指摘を添えて書き直す（回数に上限あり）
    feedback = None
    for attempt in range(max_retries + 1):
        result.draft = step_draft(result.facts, feedback)
        feedback = gate_draft(result.draft)
        logger.info("執筆 %d 回目: %d字 / 問題 %d件", attempt + 1, len(result.draft), len(feedback))
        if not feedback:
            break
        result.retries += 1
    else:
        raise PatternError(f"執筆ゲートで停止: {feedback}")

    # 段階3: ゲートを通過した原稿だけを翻訳する
    result.translation = step_translate(result.draft)
    logger.info("翻訳完了")
    return result


SAMPLE_MEMO = """
新製品「ポモドーロ・キューブ」。机に置くタイマー。
面を上にするだけで25分・5分・15分を計測。テレワークで集中したい会社員向け。
USB-C充電で2週間もつ。価格は税込4,980円。
"""

if __name__ == "__main__":
    # 本章のパターンのログだけを INFO で表示する
    logging.basicConfig(level=logging.WARNING, format="%(name)s: %(message)s")
    logging.getLogger("patterns").setLevel(logging.INFO)
    chain_result = run_chain(SAMPLE_MEMO)
    print("\n=== 紹介文 ===\n" + chain_result.draft)
    print("\n=== English ===\n" + chain_result.translation)
    print("\n" + tracker.summary())
```

`run_chain()`の流れは、ほぼ図9.3のとおりです。
1つめのゲートで不合格なら、書き直しはせずに例外で止めます。
メモそのものに情報が足りないので、何度書かせても直らないからです。

2つめのゲートは、`for`文と`else`節の組み合わせで書いています。
Pythonの`for ... else`は、`break`されずにループを終えたときだけ`else`節が実行されます。
つまり、上限まで書き直しても合格しなかった場合にだけ例外を投げます。
書き直しの回数に必ず上限を設けることは、本章のすべてのループに共通する鉄則です。

`ChainResult`に中間結果をすべて残しているのも大切な点です。
チェーンの最終結果がおかしいとき、どの段階で崩れたかを確かめられます。
ワークフローの強みは、「手順が見える」ことです。
その強みを、データ構造でも支えているわけです。

### 実行して結果を読む

プロジェクトのルートで実行します。

```bash
# プロジェクトのルートでモジュールとして実行する
uv run python -m patterns.chain
```

出力の例は次のとおりです。
文面は実行のたびに変わります。

```text
patterns.chain: 抽出完了: ポモドーロ・キューブ
patterns.chain: 執筆 1 回目: 214字 / 問題 0件
patterns.chain: 翻訳完了

=== 紹介文 ===
集中したい時間を、置くだけで。「ポモドーロ・キューブ」は、上に向けた面で25分・5分・15分を計れる卓上タイマーです。……

=== English ===
Focus time, just by setting it down. The Pomodoro Cube is a desk timer that ……

calls=3 input=1,512 output=1,087 cache_write=0 cache_read=0 total=$0.0213
```

最後の行は、第4章で作った`tracker.summary()`の出力です（呼び出し回数、4種類のトークン数、合計金額）。
3回の呼び出しのうち、コストの大半は`MODEL`を使った執筆の段階が占めているはずです。
抽出と翻訳を`FAST_MODEL`にした効果が、ここで確認できます。

ゲートの働きも試してみましょう。
`SAMPLE_MEMO`から価格の行を消して実行すると、次のように1つめのゲートで止まります。
トレースバックは、最後の行だけを示します。

```text
patterns.chain: 抽出完了: ポモドーロ・キューブ
patterns.PatternError: 抽出ゲートで停止: ['価格がありません']
```

執筆と翻訳の呼び出しは1回も行われません。
価格のない紹介文を作ってしまう事故と、その分のコストを、ゲートが同時に防いでいます。

> **WARNING**: ゲートの検査をLLMに任せたくなることがありますが、まずはコードで書ける条件を探してください。LLMによる検査は便利ですが、それ自体が誤判定することがあります。LLMの判定が必要な品質の検査は、9.4節の評価者-最適化者で扱います。

### ルーティング：分類してから振り分ける

次はルーティングです。
ルーティングとは、入力を最初に分類し、その結果に応じて専用の処理に振り分けるパターンです。
カスタマーサポートの窓口を思い浮かべると分かりやすいでしょう。
受付係が用件を聞き、請求の話なら経理担当へ、故障の話なら技術担当へ回します。
専門の担当者は自分の分野に集中できるので、回答の質が上がります。

LLMでも同じことが言えます。
1つのsystem プロンプトに、請求・技術・アカウントのすべての対応方針を詰め込んだとします。
すると、プロンプトが長くなります。
また、ある種類への最適化が、別の種類の品質を下げることがあります。
ルーティングで処理を分ければ、種類ごとにプロンプトを磨き込めます。
さらに、簡単な種類は安価なモデル、難しい種類は高性能なモデルと、モデルも使い分けられます。

<figure id="fig-9-4">
<svg width="605" height="370" viewBox="0 0 605 370" xmlns="http://www.w3.org/2000/svg" font-family="'Noto Sans JP',sans-serif">
  <defs>
    <marker id="f9_4_ar94" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#333" stroke-width="1.5"/>
    </marker>
  </defs>
  <!-- 入力 -->
  <rect x="10" y="150" width="110" height="60" rx="6" fill="#fff" stroke="#999" stroke-width="1" stroke-dasharray="4,3"/>
  <text x="65" y="176" text-anchor="middle" font-size="12" fill="#1a1a1a">問い合わせ</text>
  <text x="65" y="194" text-anchor="middle" font-size="10" fill="#1a1a1a" font-family="Consolas,monospace">inquiry</text>
  <path d="M120 180 L148 180" stroke="#333" stroke-width="1.3" marker-end="url(#f9_4_ar94)"/>
  <!-- 分類器 -->
  <rect x="150" y="135" width="150" height="90" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.4"/>
  <text x="225" y="156" text-anchor="middle" font-size="13" fill="#1a1a1a" font-weight="bold">分類器</text>
  <text x="225" y="175" text-anchor="middle" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">classify()</text>
  <text x="225" y="193" text-anchor="middle" font-size="10" fill="#1a1a1a" font-family="Consolas,monospace">FAST_MODEL</text>
  <text x="225" y="211" text-anchor="middle" font-size="10" fill="#1a1a1a">enum で4分類＋確信度</text>
  <text x="225" y="250" text-anchor="middle" font-size="10" fill="#666">振り分けは</text>
  <text x="225" y="265" text-anchor="middle" font-size="10" fill="#666"><tspan font-family="Consolas,monospace">ROUTES</tspan> 辞書（コード）</text>
  <!-- 分岐 -->
  <path d="M300 180 L378 50" stroke="#333" stroke-width="1.3" marker-end="url(#f9_4_ar94)"/>
  <path d="M300 180 L378 135" stroke="#333" stroke-width="1.3" marker-end="url(#f9_4_ar94)"/>
  <path d="M300 180 L378 220" stroke="#333" stroke-width="1.3" marker-end="url(#f9_4_ar94)"/>
  <path d="M300 180 L378 305" stroke="#333" stroke-width="1.3" stroke-dasharray="5,3" marker-end="url(#f9_4_ar94)"/>
  <!-- 振り分け先 -->
  <rect x="380" y="20" width="210" height="60" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="485" y="45" text-anchor="middle" font-size="12" fill="#1a1a1a" font-weight="bold"><tspan font-family="Consolas,monospace">billing</tspan>：料金担当</text>
  <text x="485" y="64" text-anchor="middle" font-size="10" fill="#1a1a1a" font-family="Consolas,monospace">FAST_MODEL</text>
  <rect x="380" y="105" width="210" height="60" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="485" y="130" text-anchor="middle" font-size="12" fill="#1a1a1a" font-weight="bold"><tspan font-family="Consolas,monospace">technical</tspan>：技術サポート担当</text>
  <text x="485" y="149" text-anchor="middle" font-size="10" fill="#1a1a1a" font-family="Consolas,monospace">MODEL</text>
  <rect x="380" y="190" width="210" height="60" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="485" y="215" text-anchor="middle" font-size="12" fill="#1a1a1a" font-weight="bold"><tspan font-family="Consolas,monospace">account</tspan>：アカウント担当</text>
  <text x="485" y="234" text-anchor="middle" font-size="10" fill="#1a1a1a" font-family="Consolas,monospace">FAST_MODEL</text>
  <rect x="380" y="275" width="210" height="60" rx="6" fill="#fff" stroke="#333" stroke-width="1.2" stroke-dasharray="5,3"/>
  <text x="485" y="300" text-anchor="middle" font-size="12" fill="#1a1a1a" font-weight="bold">人間へエスカレーション</text>
  <text x="485" y="319" text-anchor="middle" font-size="10" fill="#1a1a1a"><tspan font-family="Consolas,monospace">other</tspan> または確信度が <tspan font-family="Consolas,monospace">low</tspan></text>
  <text x="302" y="360" text-anchor="middle" font-size="11" fill="#666">分類だけをモデルに任せ、行き先はコードが決める（ワークフロー）</text>
</svg>
  <figcaption>図9.4: ルーティングによる問い合わせ振り分け</figcaption>
</figure>

分類の役は、`FAST_MODEL`と構造化出力の組み合わせが最適です。
分類は短い出力で済むので、安価で速いモデルで十分な精度が出ます。
そして構造化出力で`enum`を使えば、カテゴリー名が必ず決められた値のどれかになります。
「請求関係」や「billing（請求）」のような表記ゆれに悩まされることがありません。

### patterns/router.py を作る

`patterns/router.py`を新規作成します。

```python
# patterns/router.py
"""ルーティング: FAST_MODEL で分類し、カテゴリーごとの専用処理へ振り分ける（新規作成）"""
import logging
from dataclasses import dataclass

from llm_client import FAST_MODEL, MODEL, call_messages, extract_text, tracker
from patterns import PatternError, json_format, parse_json_response

logger = logging.getLogger("patterns.router")

# --- 分類器: enum でカテゴリーを固定する ---
CATEGORIES = ["billing", "technical", "account", "other"]
CLASSIFY_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": CATEGORIES},
        "confidence": {"type": "string", "enum": ["high", "low"]},
        "reason": {"type": "string"},
    },
    "required": ["category", "confidence", "reason"],
    "additionalProperties": False,
}

CLASSIFIER_SYSTEM = """あなたはサポート窓口の受付係です。問い合わせを次のどれか1つに分類してください。
- billing: 料金・請求書・支払い方法・返金
- technical: 製品の不具合・エラー・使い方の技術的な質問
- account: ログイン・パスワード・登録情報の変更・退会
- other: 上のどれにも当てはまらないもの
判断に迷う場合は confidence を low にしてください。"""


def classify(inquiry: str) -> dict:
    """問い合わせを分類し、category・confidence・reason を返す"""
    response = call_messages(
        [{"role": "user", "content": f"<inquiry>\n{inquiry}\n</inquiry>"}],
        system=CLASSIFIER_SYSTEM,
        model=FAST_MODEL,
        max_tokens=1000,
        output_config=json_format(CLASSIFY_SCHEMA),
    )
    return parse_json_response(response)
```

`CLASSIFY_SCHEMA`の`category`には`enum`で4つの値を指定しています。
これで、モデルの出力は必ずこの4つのどれかになります。
`confidence`（確信度）も`high`と`low`の2値の`enum`にしました。
0〜1の数値で確信度を出させる方法もあります。
ただし、モデルが出す数値は較正されていないことが多く、しきい値の調整が難しくなります。
2値にしておけば「迷ったら`low`」という単純な指示で済みます。

`reason`（理由）は、振り分けには使いませんが、ログに残すために出力させています。
誤分類が起きたとき、モデルがなぜその分類を選んだかが分かるとします。
それが、`CLASSIFIER_SYSTEM`のどこを直せばよいかの手がかりになります。

`CLASSIFIER_SYSTEM`では、各カテゴリーの定義を具体的に書いています。
「billing」という名前だけでは、返金が請求に入るのかが曖昧です。
定義を書いておくことは、人間の受付係にマニュアルを渡すのと同じです。

続いて、振り分け先の定義と、ルーティング本体です。

```python
# patterns/router.py（続き）
@dataclass(frozen=True)
class Route:
    """振り分け先の設定: どのモデルに、どんな system プロンプトで答えさせるか"""
    model: str
    system: str


ROUTES: dict[str, Route] = {
    "billing": Route(FAST_MODEL, "あなたは料金担当です。料金表の範囲で答え、返金の可否は断定せず担当窓口を案内してください。"),
    "technical": Route(MODEL, "あなたは技術サポート担当です。再現手順を確認し、原因の候補と対処を順に示してください。"),
    "account": Route(FAST_MODEL, "あなたはアカウント担当です。パスワードなどの秘密情報は決して尋ねず、手続きの手順を案内してください。"),
}
ESCALATION_MESSAGE = "担当者から改めてご連絡します。しばらくお待ちください。"


def route(inquiry: str) -> tuple[str, str]:
    """分類してから振り分け、(振り分け先の名前, 回答) を返す"""
    label = classify(inquiry)
    logger.info("分類: %s (%s) - %s", label["category"], label["confidence"], label["reason"])

    # 確信度が低い、または該当する振り分け先がないときは人間に回す
    if label["confidence"] == "low" or label["category"] not in ROUTES:
        return "escalation", ESCALATION_MESSAGE

    target = ROUTES[label["category"]]
    response = call_messages(
        [{"role": "user", "content": inquiry}],
        system=target.system,
        model=target.model,
        max_tokens=8000,
    )
    if response["stop_reason"] != "end_turn":
        raise PatternError(f"回答が正常に終わりませんでした: {response['stop_reason']}")
    return label["category"], extract_text(response).strip()


SAMPLE_INQUIRIES = [
    "先月の請求額がいつもより2,000円高いのですが、内訳を教えてください。",
    "アプリを起動すると「E-104」というエラーが出て進めません。",
    "登録しているメールアドレスを会社のものに変更したいです。",
    "御社の製品について、雑誌の取材をお願いできますか。",
]

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING, format="%(name)s: %(message)s")
    logging.getLogger("patterns").setLevel(logging.INFO)
    for text in SAMPLE_INQUIRIES:
        name, answer = route(text)
        print(f"[{name}] {answer[:60]}…\n")
    print(tracker.summary())
```

`Route`は、振り分け先ごとのモデルとsystem プロンプトをまとめたデータクラスです。
`frozen=True`にして、実行中に書き換えられないようにしています。

`ROUTES`辞書が、このパターンの「振り分け表」です。
処理の流れを決めているのはこの辞書であり、モデルではありません。
9.1節で述べたとおり、だからルーティングはワークフローに分類されます。
技術的な問い合わせだけ`MODEL`にしているのは、原因の切り分けには推論力が必要だからです。
料金とアカウントは定型的な案内が多いので、`FAST_MODEL`で十分です。

`route()`の中で特に注目してほしいのは、**エスカレーション（escalation：人間への引き継ぎ）**の条件です。
`other`は、`ROUTES`に登録していません。
そのため、`label["category"] not in ROUTES`の条件で人間に回ります。
確信度が`low`の場合も同様です。
分類を誤って別の担当に回すより、人間に引き継ぐ方が安全だからです。
ルーティングでは「どこにも当てはまらないもの」の行き先を、必ず設計しておいてください。

### 実行して振り分けを確かめる

実行します。

```bash
# 4件の問い合わせを順に分類・回答する
uv run python -m patterns.router
```

出力の例です。

```text
patterns.router: 分類: billing (high) - 請求額の内訳についての質問のため
[billing] 請求額の内訳は、マイページの「ご利用明細」から確認できます。…

patterns.router: 分類: technical (high) - アプリ起動時のエラーコードに関する質問のため
[technical] 「E-104」が表示される場合、まずアプリを最新版に更新して…

patterns.router: 分類: account (high) - 登録メールアドレスの変更手続きのため
[account] メールアドレスの変更は、設定画面の「アカウント情報」から…

patterns.router: 分類: other (high) - 取材依頼でありサポートの範囲外のため
[escalation] 担当者から改めてご連絡します。しばらくお待ちください。

calls=7 input=2,904 output=2,311 cache_write=0 cache_read=0 total=$0.0335
```

呼び出し回数が7回になっている点を確認してください。
分類が4回、回答が3回です。
取材依頼は分類だけで人間に回したので、回答の呼び出しは発生していません。

### ルーティングのつまずきと対処

ルーティングで起きやすい問題を3つ挙げておきます。

1つめは、**カテゴリーの境界があいまいなこと**です。
「返金してほしいのにログインできない」のように、複数の種類にまたがる問い合わせは必ず来ます。
対処法は、`CLASSIFIER_SYSTEM`に優先順位を書くことです。
たとえば「ログインできないことが原因なら account を優先」のように決めておきます。
それでも決めきれないものは、確信度を`low`にさせて人間に回します。

2つめは、**分類の精度を測っていないこと**です。
振り分けが間違っていても、回答はそれらしく生成されるので、誤りに気づきにくいのです。
正解ラベル付きの問い合わせを20〜30件用意し、`classify()`だけを回して正解率を測りましょう。
分類器は単独で評価できるのが、ルーティングの利点でもあります。

3つめは、**分類のコストを忘れること**です。
すべての問い合わせで分類の呼び出しが1回増えます。
`FAST_MODEL`なら1件あたりの費用はごくわずかですが、件数が多いと積み重なります。
大量の分類をリアルタイムで返す必要がなければ、まとめて処理する方法もあります。
使うのは、第11章で扱うMessage Batches API（メッセージ・バッチ）です。

> **POINT**: プロンプトチェーンは「順番に分ける」、ルーティングは「種類で分ける」パターンです。どちらも、1回の呼び出しに頼む仕事を小さくして、各段階のプロンプトとモデルを最適化できるようにするのが狙いです。

チェーンとルーティングは、どちらも処理を直列に進めるパターンでした。
次の節では、複数の呼び出しを同時に走らせる並列化に進みます。

---

## 9.3 並列化：セクショニングと投票

コードレビューを1回の呼び出しで頼むと、セキュリティの指摘ばかりで読みやすさに触れていなかったり、その逆だったりします。
1人のレビュアーにすべての観点を同時に求めるのは、人間でも難しいことです。
では、観点ごとに別のレビュアーを立て、同時に作業してもらったらどうでしょうか。
この節では、そうした「同時に複数の呼び出しを走らせる」並列化のパターンを実装します。

### セクショニングと投票の違い

並列化には、目的の異なる2つの形があります。

**セクショニング（sectioning）**は、タスクを独立した部分に分け、それぞれを同時に処理して最後に統合する形です。
コードレビューを「セキュリティ」「性能」「読みやすさ」の3観点に分けるのが典型例です。
各呼び出しは1つの観点に集中できるので、見落としが減ります。
また、互いに独立しているので、同時に実行すれば待ち時間は「一番遅い1件」とほぼ同じで済みます。

**投票（voting）**は、同じ問いを複数回判定させ、結果を集計する形です。
「このコードに脆弱性はあるか」を5回判定させ、多数決をとるといった使い方をします。
1回の判定よりも誤判定に強くなり、さらに票の割れ方から「判定の難しさ」も分かります。

両者の違いは、**分けているものが「仕事」か「判定者」か**です。
セクショニングは仕事を分け、投票は同じ仕事を複数の判定者に任せます。

<figure id="fig-9-5">
<svg width="605" height="300" viewBox="0 0 605 300" xmlns="http://www.w3.org/2000/svg" font-family="'Noto Sans JP',sans-serif">
  <defs>
    <marker id="f9_5_ar95" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#333" stroke-width="1.5"/>
    </marker>
  </defs>
  <!-- 左: セクショニング -->
  <text x="152" y="26" text-anchor="middle" font-size="13" fill="#1a1a1a" font-weight="bold">セクショニング：仕事を分ける</text>
  <rect x="67" y="42" width="170" height="32" rx="6" fill="#fff" stroke="#999" stroke-width="1" stroke-dasharray="4,3"/>
  <text x="152" y="63" text-anchor="middle" font-size="12" fill="#1a1a1a">レビュー対象のコード</text>
  <path d="M152 74 L57 113" stroke="#333" stroke-width="1.2" marker-end="url(#f9_5_ar95)"/>
  <path d="M152 74 L152 113" stroke="#333" stroke-width="1.2" marker-end="url(#f9_5_ar95)"/>
  <path d="M152 74 L247 113" stroke="#333" stroke-width="1.2" marker-end="url(#f9_5_ar95)"/>
  <rect x="15" y="115" width="85" height="46" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.2"/>
  <text x="57" y="135" text-anchor="middle" font-size="11" fill="#1a1a1a">セキュリティ</text>
  <text x="57" y="152" text-anchor="middle" font-size="10" fill="#1a1a1a" font-family="Consolas,monospace">security</text>
  <rect x="110" y="115" width="85" height="46" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.2"/>
  <text x="152" y="135" text-anchor="middle" font-size="11" fill="#1a1a1a">性能</text>
  <text x="152" y="152" text-anchor="middle" font-size="10" fill="#1a1a1a" font-family="Consolas,monospace">performance</text>
  <rect x="205" y="115" width="85" height="46" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.2"/>
  <text x="247" y="135" text-anchor="middle" font-size="11" fill="#1a1a1a">読みやすさ</text>
  <text x="247" y="152" text-anchor="middle" font-size="10" fill="#1a1a1a" font-family="Consolas,monospace">readability</text>
  <path d="M57 161 L120 198" stroke="#333" stroke-width="1.2" marker-end="url(#f9_5_ar95)"/>
  <path d="M152 161 L152 198" stroke="#333" stroke-width="1.2" marker-end="url(#f9_5_ar95)"/>
  <path d="M247 161 L184 198" stroke="#333" stroke-width="1.2" marker-end="url(#f9_5_ar95)"/>
  <rect x="47" y="200" width="210" height="34" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="152" y="222" text-anchor="middle" font-size="12" fill="#1a1a1a">重要度順に統合（コード）</text>
  <text x="152" y="262" text-anchor="middle" font-size="11" fill="#1a1a1a">観点ごとに別の仕事 × 3（<tspan font-family="Consolas,monospace">MODEL</tspan>）</text>
  <text x="152" y="281" text-anchor="middle" font-size="11" fill="#666">各観点に集中でき、見落としが減る</text>
  <!-- 区切り -->
  <line x1="302" y1="12" x2="302" y2="288" stroke="#999" stroke-width="1" stroke-dasharray="4,4"/>
  <!-- 右: 投票 -->
  <text x="452" y="26" text-anchor="middle" font-size="13" fill="#1a1a1a" font-weight="bold">投票：判定者を分ける</text>
  <rect x="347" y="42" width="210" height="32" rx="6" fill="#fff" stroke="#999" stroke-width="1" stroke-dasharray="4,3"/>
  <text x="452" y="63" text-anchor="middle" font-size="12" fill="#1a1a1a">同じ問い：脆弱性はある？</text>
  <path d="M452 74 L338 113" stroke="#333" stroke-width="1.2" marker-end="url(#f9_5_ar95)"/>
  <path d="M452 74 L394 113" stroke="#333" stroke-width="1.2" marker-end="url(#f9_5_ar95)"/>
  <path d="M452 74 L450 113" stroke="#333" stroke-width="1.2" marker-end="url(#f9_5_ar95)"/>
  <path d="M452 74 L506 113" stroke="#333" stroke-width="1.2" marker-end="url(#f9_5_ar95)"/>
  <path d="M452 74 L562 113" stroke="#333" stroke-width="1.2" marker-end="url(#f9_5_ar95)"/>
  <rect x="313" y="115" width="50" height="46" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="338" y="142" text-anchor="middle" font-size="11" fill="#1a1a1a">攻撃者</text>
  <rect x="369" y="115" width="50" height="46" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="394" y="142" text-anchor="middle" font-size="11" fill="#1a1a1a">入力</text>
  <rect x="425" y="115" width="50" height="46" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="450" y="142" text-anchor="middle" font-size="11" fill="#1a1a1a">文字列</text>
  <rect x="481" y="115" width="50" height="46" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="506" y="142" text-anchor="middle" font-size="11" fill="#1a1a1a">本番</text>
  <rect x="537" y="115" width="50" height="46" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="562" y="142" text-anchor="middle" font-size="11" fill="#1a1a1a">チェック</text>
  <path d="M338 161 L420 198" stroke="#333" stroke-width="1.2" marker-end="url(#f9_5_ar95)"/>
  <path d="M394 161 L436 198" stroke="#333" stroke-width="1.2" marker-end="url(#f9_5_ar95)"/>
  <path d="M450 161 L452 198" stroke="#333" stroke-width="1.2" marker-end="url(#f9_5_ar95)"/>
  <path d="M506 161 L468 198" stroke="#333" stroke-width="1.2" marker-end="url(#f9_5_ar95)"/>
  <path d="M562 161 L484 198" stroke="#333" stroke-width="1.2" marker-end="url(#f9_5_ar95)"/>
  <rect x="337" y="200" width="230" height="34" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.2"/>
  <text x="452" y="222" text-anchor="middle" font-size="11" fill="#1a1a1a">集計：<tspan font-family="Consolas,monospace">vulnerable</tspan> が2票以上なら要対応</text>
  <text x="452" y="262" text-anchor="middle" font-size="11" fill="#1a1a1a">観点の違う5人で同じ判定（<tspan font-family="Consolas,monospace">FAST_MODEL</tspan>）</text>
  <text x="452" y="281" text-anchor="middle" font-size="11" fill="#666">誤判定に強く、票の割れ方で難しさもわかる</text>
</svg>
  <figcaption>図9.5: セクショニングと投票の比較</figcaption>
</figure>

### temperatureが使えない中での「多様性」

投票を実装する前に、1つ注意があります。
`anthropic-version: 2026-10-21`では、次の3つを送ると400エラーになります。
`temperature`・`top_p`・`top_k`の3つです。
以前は、同じプロンプトでも`temperature`を上げて答えのばらつきを作り、投票させる手法がよく紹介されていました。
本書の環境では、その方法は使えません。

また、仮に同じプロンプトで5回呼んでも、得られる答えは互いに似通う傾向があります。
同じ視点から同じ問題を見れば、同じところを見落とすからです。
これでは、多数決をとっても誤りを打ち消し合う効果が小さくなります。

そこで本書では、**投票者ごとに観点の違うプロンプトを使う**ことで多様性を出します。
「攻撃者の視点で見る投票者」「入力の検証に注目する投票者」のように、問いは同じでも見方を変えるのです。
これは人間の審査会で、立場の違う審査員を集めるのと同じ発想です。
必要であれば、投票者ごとにモデルを変えるのも有効です。

> **POINT**: 投票で大切なのは「回数」より「独立性」です。同じ見方の判定を何回重ねても、同じ誤りを何回も数えるだけになります。観点の違うプロンプトで、誤り方が互いに異なる判定者を用意しましょう。

### patterns/parallel.py を作る：セクショニング

`patterns/parallel.py`を新規作成します。
第8章で追加した非同期版の`acall_messages()`と、`asyncio.gather()`を使います。

```python
# patterns/parallel.py
"""並列化: セクショニング（観点別レビュー）と投票（多数決）（新規作成）"""
import asyncio
import logging
from collections import Counter

from llm_client import FAST_MODEL, MODEL, acall_messages, aclose_client, tracker
from patterns import json_format, parse_json_response

logger = logging.getLogger("patterns.parallel")

# 同時に送るリクエスト数の上限（レート制限 429 を避けるため）
MAX_CONCURRENCY = 4

# --- セクショニング: 観点ごとに独立したレビューを行う ---
FINDINGS_SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "severity": {"type": "string", "enum": ["high", "medium", "low"]},
                    "issue": {"type": "string"},
                    "suggestion": {"type": "string"},
                },
                "required": ["severity", "issue", "suggestion"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["findings"],
    "additionalProperties": False,
}

ASPECTS = {
    "security": "セキュリティ（インジェクション、認証、秘密情報の扱い）だけを見てください。",
    "performance": "性能（計算量、無駄なI/O、メモリ使用量）だけを見てください。",
    "readability": "読みやすさ（命名、関数の長さ、コメント、型ヒント）だけを見てください。",
}


async def review_aspect(aspect: str, instruction: str, code: str,
                        semaphore: asyncio.Semaphore) -> list[dict]:
    """1つの観点だけでレビューし、指摘のリストを返す"""
    async with semaphore:  # 同時実行数を制限する
        response = await acall_messages(
            [{"role": "user", "content": f"次のコードをレビューしてください。\n\n```python\n{code}\n```"}],
            system=f"あなたはコードレビュアーです。{instruction} 他の観点の問題には触れないでください。問題がなければ findings は空配列にしてください。",
            model=MODEL,
            max_tokens=8000,
            output_config=json_format(FINDINGS_SCHEMA),
        )
    findings = parse_json_response(response)["findings"]
    logger.info("%s: %d件", aspect, len(findings))
    # どの観点からの指摘かを付けておく（統合の段階で使う）
    return [{"aspect": aspect, **f} for f in findings]


SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


async def sectioned_review(code: str) -> list[dict]:
    """全観点を同時に実行し、重要度順に統合する"""
    # セマフォは asyncio.run() のイベントループの中（この関数内）で作る
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
    tasks = [review_aspect(name, inst, code, semaphore) for name, inst in ASPECTS.items()]
    # return_exceptions=True で、1観点の失敗が全体を止めないようにする
    results = await asyncio.gather(*tasks, return_exceptions=True)
    merged: list[dict] = []
    for name, result in zip(ASPECTS, results):
        if isinstance(result, Exception):
            logger.warning("%s のレビューに失敗: %s", name, result)
            continue
        merged.extend(result)
    # 統合はコードで行う: 重要度の高い順に並べる
    return sorted(merged, key=lambda f: SEVERITY_ORDER[f["severity"]])
```

コードの要点を順に見ていきます。

`MAX_CONCURRENCY`と`asyncio.Semaphore`は、同時に送るリクエストの数を制限する仕組みです。
並列化は速い反面、短時間に多数のリクエストを送るため、レート制限（429）に当たりやすくなります。
第4章のリトライが429を処理してくれますが、待ち時間が増えては並列化の意味が薄れます。
セマフォ（semaphore）で同時実行数を抑えるのは、並列化の基本的な作法です。
セマフォはモジュールの最上位ではなく、`sectioned_review()`と`vote()`の中で作って渡しています。
`asyncio.run()`が動かすイベントループの中で作っておきます。
そうすれば、別の`asyncio.run()`から呼んでも前のループに縛られません。

`FINDINGS_SCHEMA`は、指摘のリストを返すためのスキーマです。
配列の要素もオブジェクトです。
そのため、内側にも`required`と`additionalProperties: False`を書いています。
入れ子のオブジェクトごとに、この2つを忘れないようにしてください。

`ASPECTS`辞書は、観点名と、その観点に絞るための指示を対応させたものです。
system プロンプトで「他の観点の問題には触れない」と念を押しているのがポイントです。
これがないと、各レビュアーが親切に他の観点にも触れてしまい、統合したときに重複だらけになります。

`review_aspect()`の最後で、各指摘に`aspect`キーを追加しています。
`{"aspect": aspect, **f}`は、辞書`f`の中身に`aspect`を足した新しい辞書を作る書き方です。
統合したあとでも「どの観点からの指摘か」が分かるようにするためです。

`sectioned_review()`では、`asyncio.gather()`に`return_exceptions=True`を指定しています。
これを付けないと、3観点のうち1つが失敗しただけで、`gather()`全体が例外で終わります。
付けておけば、失敗した観点は例外オブジェクトとして返り、成功した観点の結果は使えます。
一部の観点が欠けても、残りの指摘を返す方が実用的だからです。

最後の統合は、LLMではなくコードで重要度順に並べているだけです。
統合をLLMに任せて要約させる方法もありますが、指摘が消えたり、言い換えで意味が変わったりする危険があります。
統合はまずコードで行い、必要なら最後に要約を1回追加する、という順番で考えてください。

### patterns/parallel.py を作る：投票

続いて、同じファイルに投票を追加します。

```python
# patterns/parallel.py（続き）
# --- 投票: 観点の違う投票者に同じ問いを判定させ、多数決をとる ---
VOTE_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["vulnerable", "safe"]},
        "reason": {"type": "string"},
    },
    "required": ["verdict", "reason"],
    "additionalProperties": False,
}

# temperature は使えないので、見方の違うプロンプトで判定の多様性を出す
VOTERS = [
    "攻撃者の立場で、このコードを悪用できるかを考えてください。",
    "外部から来る入力がどこでどう検証されているかを追跡してください。",
    "データベースやOSに渡る文字列の組み立て方に注目してください。",
    "このコードが本番環境で動くと仮定し、事故の起き方を想像してください。",
    "セキュアコーディングのチェックリストに照らして確認してください。",
]


async def cast_vote(perspective: str, code: str, semaphore: asyncio.Semaphore) -> str:
    """1人の投票者として判定し、'vulnerable' か 'safe' を返す"""
    async with semaphore:
        response = await acall_messages(
            [{"role": "user", "content": f"このコードに脆弱性はありますか。\n\n```python\n{code}\n```"}],
            system=f"あなたはセキュリティ審査員です。{perspective}",
            model=FAST_MODEL,
            max_tokens=2000,
            output_config=json_format(VOTE_SCHEMA),
        )
    return parse_json_response(response)["verdict"]


async def vote(code: str, *, threshold: int = 2) -> dict:
    """全員の票を集め、vulnerable が threshold 票以上なら要対応と判定する"""
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
    results = await asyncio.gather(*(cast_vote(p, code, semaphore) for p in VOTERS),
                                   return_exceptions=True)
    verdicts = [r for r in results if isinstance(r, str)]  # 失敗した票は数えない
    counts = Counter(verdicts)
    # 偽陰性（見逃し）のコストが高いので、過半数より低いしきい値で安全側に倒す
    flagged = counts["vulnerable"] >= threshold
    return {"flagged": flagged, "counts": dict(counts), "valid_votes": len(verdicts)}


SAMPLE_CODE = '''
def find_user(conn, name: str):
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM users WHERE name = '{name}'")
    return cur.fetchone()
'''


async def main() -> None:
    try:
        findings = await sectioned_review(SAMPLE_CODE)
        print("=== セクショニング（観点別レビュー） ===")
        for f in findings:
            print(f"[{f['severity']}] ({f['aspect']}) {f['issue']}")
        print("\n=== 投票（脆弱性の判定） ===")
        print(await vote(SAMPLE_CODE))
        print("\n" + tracker.summary())
    finally:
        await aclose_client()  # 第8章: ループを閉じる前に非同期クライアントを閉じる


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING, format="%(name)s: %(message)s")
    logging.getLogger("patterns").setLevel(logging.INFO)
    asyncio.run(main())
```

`VOTERS`には、5人の投票者の「見方」を並べています。
問いはすべて「脆弱性はあるか」で同じですが、注目する場所が違います。
投票者を奇数にしておくと、2択の多数決で同数になりません。

`vote()`の`threshold`（しきい値）には、あえて過半数の3ではなく2を既定値にしました。
脆弱性の判定では、問題を見逃す「偽陰性」の方が、問題のないコードを疑う「偽陽性」よりずっと高くつくからです。
5票中2票でも「怪しい」と言う投票者がいれば、人間が確認する価値があります。
逆に、スパム判定のように誤検出の害が大きい課題なら、しきい値を上げます。
**しきい値は、2種類の誤りのどちらが高くつくかで決める**ものです。

返り値に`counts`と`valid_votes`を含めているのは、票の割れ方を後から確認するためです。
5対0なら判定は明確ですが、3対2なら判定が難しい入力だと分かります。
割れた入力を集めて人間が見直すと、プロンプトの改善点が見つかります。

### 実行して結果を読む

```bash
# セクショニングと投票を続けて実行する
uv run python -m patterns.parallel
```

出力の例です。

```text
patterns.parallel: readability: 2件
patterns.parallel: performance: 1件
patterns.parallel: security: 1件
=== セクショニング（観点別レビュー） ===
[high] (security) f文字列でSQLを組み立てているため、SQLインジェクションが可能です
[medium] (performance) SELECT * で不要な列まで取得しています
[low] (readability) 戻り値の型ヒントがありません
[low] (readability) カーソルを閉じていません

=== 投票（脆弱性の判定） ===
{'flagged': True, 'counts': {'vulnerable': 5}, 'valid_votes': 5}

calls=8 input=4,630 output=3,148 cache_write=0 cache_read=0 total=$0.0644
```

ログの順番が`readability`、`performance`、`security`になっている点に注目してください。
3つのレビューは同時に走っているので、終わった順にログが出ます。
一方で、最終的な指摘は重要度順に並んでいます。
完了順に左右されないよう、統合の段階で並べ直しているからです。

また、`[low] (readability) カーソルを閉じていません`のように、観点の境界にある指摘が出ることもあります。
リソースの解放は性能の問題とも読みやすさの問題とも言えます。
観点の境界をまたぐ指摘が重複して出ることもあるので、気になる場合は統合の段階で似た指摘をまとめる処理を加えてください。

### コストとのトレードオフ

並列化で減るのは「待ち時間」であり、「費用」ではありません。
ここは誤解しやすいので、はっきりさせておきます。

セクショニングでは、同じコードを3回送るので、入力トークンはおよそ3倍になります。
投票では5回送るので、およそ5倍です。
実行例でも、8回の呼び出しで約6セントかかっています。
1件のレビューならわずかですが、毎日数千件のプルリクエストに適用すると無視できない額になります。

| 方式 | 呼び出し回数 | 待ち時間の目安 | 費用の目安 |
|---|---|---|---|
| 単一呼び出しでレビュー | 1 | 1回分 | 1倍 |
| セクショニング（3観点） | 3 | 最も遅い1回分 | 約3倍 |
| 投票（5票） | 5 | 最も遅い1回分 | 約5倍（FAST_MODELなら安価） |

費用を抑える工夫もあります。
投票者は`FAST_MODEL`にし、セクショニングでも観点によっては`FAST_MODEL`で十分か試してみましょう。
同じコードを何度も送る構成なので、第7章のプロンプトキャッシュも効かせられます。
ただし、本章の`patterns/`は`cache_control`を付けていません。
効かせるには、設定を足す必要があります。
第7章の`cached_system()`や、トップレベルの`cache_control`などです。
ただし、キャッシュは前方一致なので、観点ごとに変わるsystem プロンプトを先頭に置くと共有できません。
共通部分を前に、観点ごとの指示を後ろに置くように並べ替えると、キャッシュが効きやすくなります。
また、最小キャッシュ長に満たない短い入力では、キャッシュは作られない点にも注意してください。

> **NOTE**: 並列で同時に送った最初のリクエスト群は、まだキャッシュが作られる前です。そのため、互いのキャッシュを読めないことがあります。キャッシュを確実に効かせたい場合は、1件目だけ先に送り、完了後に残りを並列で送る方法があります。

並列化は、費用を払って効果を買うパターンです。
目的は、「待ち時間を減らしたい」「見落としを減らしたい」「判定を確かにしたい」の3つです。
費用に見合うかどうかは、9.1節の「価値」の基準で判断してください。

次の節では、生成と評価を分けて品質を高める評価者-最適化者を実装します。

---

## 9.4 評価者-最適化者

文章を書いたあと、誰かに読んでもらって直すと、文章は見違えるほど良くなります。
では、LLMに「書く役」と「読んで指摘する役」を分けて担当させたらどうでしょうか。
この節では、生成と評価を分け、基準を満たすまで改善を繰り返す評価者-最適化者パターンを実装します。

### 生成役と評価役を分ける理由

評価者-最適化者とは、生成と採点を繰り返すループのパターンです。
まず、**最適化者（optimizer）**が成果物を作ります。
次に、**評価者（evaluator）**がそれを基準に照らして採点します。
そのフィードバックで、最適化者が改善します。
人間の作家と編集者の関係を思い浮かべてください。

このパターンが向いているのは、次の2つの条件がそろう課題です。
1つめは、**評価基準を明確に書けること**です。
基準があいまいだと、評価者の指摘もあいまいになり、改善が進みません。
2つめは、**フィードバックによって実際に品質が上がること**です。
人間が指摘すれば良くなる種類の課題なら、LLMの指摘でも良くなる見込みがあります。
翻訳の言い回しの調整や、文章を規定に合わせる作業は、この2つを満たす典型例です。

<figure id="fig-9-6">
<svg width="605" height="315" viewBox="0 0 605 315" xmlns="http://www.w3.org/2000/svg" font-family="'Noto Sans JP',sans-serif">
  <defs>
    <marker id="f9_6_ar96" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#333" stroke-width="1.5"/>
    </marker>
  </defs>
  <!-- テーマ -->
  <rect x="30" y="10" width="180" height="30" rx="6" fill="#fff" stroke="#999" stroke-width="1" stroke-dasharray="4,3"/>
  <text x="120" y="30" text-anchor="middle" font-size="12" fill="#1a1a1a">テーマ（<tspan font-family="Consolas,monospace">topic</tspan>）</text>
  <path d="M120 40 L120 63" stroke="#333" stroke-width="1.3" marker-end="url(#f9_6_ar96)"/>
  <!-- 生成役 -->
  <rect x="30" y="65" width="180" height="55" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="120" y="88" text-anchor="middle" font-size="12" fill="#1a1a1a" font-weight="bold">最適化者（生成役）</text>
  <text x="120" y="107" text-anchor="middle" font-size="10" fill="#1a1a1a" font-family="Consolas,monospace">generate() / MODEL</text>
  <path d="M210 92 L328 92" stroke="#333" stroke-width="1.3" marker-end="url(#f9_6_ar96)"/>
  <text x="270" y="84" text-anchor="middle" font-size="11" fill="#1a1a1a">原稿</text>
  <!-- 評価役 -->
  <rect x="330" y="65" width="230" height="55" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="445" y="83" text-anchor="middle" font-size="12" fill="#1a1a1a" font-weight="bold">評価者（評価役）</text>
  <text x="445" y="99" text-anchor="middle" font-size="10" fill="#1a1a1a" font-family="Consolas,monospace">evaluate() / FAST_MODEL</text>
  <text x="445" y="113" text-anchor="middle" font-size="10" fill="#1a1a1a">ルーブリック4項目で採点</text>
  <path d="M445 120 L445 143" stroke="#333" stroke-width="1.3" marker-end="url(#f9_6_ar96)"/>
  <text x="455" y="137" font-size="10" fill="#666"><tspan font-family="Consolas,monospace">passed()</tspan>：コードで判定</text>
  <!-- 判定 -->
  <polygon points="445,145 530,175 445,205 360,175" fill="#fff" stroke="#333" stroke-width="1.2"/>
  <text x="445" y="179" text-anchor="middle" font-size="11" fill="#1a1a1a">全項目が4点以上？</text>
  <!-- 合格 -->
  <path d="M445 205 L445 243" stroke="#333" stroke-width="1.3" marker-end="url(#f9_6_ar96)"/>
  <text x="452" y="228" font-size="11" fill="#1a1a1a">はい</text>
  <rect x="360" y="245" width="170" height="40" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.4"/>
  <text x="445" y="270" text-anchor="middle" font-size="12" fill="#1a1a1a" font-weight="bold">終了：その版を返す</text>
  <!-- 不合格 -->
  <path d="M360 175 L212 175" stroke="#333" stroke-width="1.3" marker-end="url(#f9_6_ar96)"/>
  <text x="290" y="168" text-anchor="middle" font-size="11" fill="#1a1a1a">いいえ</text>
  <rect x="30" y="155" width="180" height="42" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.2"/>
  <text x="120" y="172" text-anchor="middle" font-size="11" fill="#1a1a1a">改善点（<tspan font-family="Consolas,monospace">improvements</tspan>）</text>
  <text x="120" y="189" text-anchor="middle" font-size="11" fill="#1a1a1a">を添えて再生成</text>
  <path d="M120 155 L120 122" stroke="#333" stroke-width="1.3" marker-end="url(#f9_6_ar96)"/>
  <!-- ほかの終了条件 -->
  <text x="30" y="232" font-size="11" fill="#1a1a1a" font-weight="bold">ほかの終了条件</text>
  <text x="30" y="250" font-size="10" fill="#1a1a1a">・<tspan font-family="Consolas,monospace">max_rounds</tspan>（既定3回）に到達</text>
  <text x="30" y="266" font-size="10" fill="#1a1a1a">・前回より点数が上がらない（停滞）</text>
  <text x="30" y="282" font-size="10" fill="#1a1a1a">→ 最高得点の版 <tspan font-family="Consolas,monospace">best</tspan> を返す</text>
</svg>
  <figcaption>図9.6: 評価者-最適化者の改善ループ</figcaption>
</figure>

### ルーブリックで評価を構造化する

評価の基準は、**ルーブリック（rubric：評価基準表）**として書き出します。
ルーブリックとは、評価項目ごとに「何点ならどういう状態か」を定めた表のことです。
「良い文章か」と聞くと評価者の答えはぶれますが、「具体例が1つ以上あるか」と聞けば答えは安定します。

本書では、技術ブログ記事の導入段落を題材にし、次の4項目で採点します。

| 評価項目 | 5点の状態 | 1点の状態 |
|---|---|---|
| 正確性 | 技術的な誤りがない | 明らかな誤りがある |
| 具体性 | 読者の具体的な悩みや場面が書かれている | 一般論だけ |
| 読みやすさ | 1文が短く、専門用語に説明がある | 1文が長く、用語が説明なしに出る |
| 誘導 | 記事を読む利点が最後に示されている | 読む理由が分からない |

評価者には、この各項目の点数と改善点を構造化出力で返させます。
合格かどうかの判定は、評価者に任せずに**コードで**行います。
評価者に「合格ですか」と聞くと甘くなりやすいうえ、合格の基準を変えたいときにプロンプトを直す必要が出るからです。

### patterns/evaluator_optimizer.py を作る

`patterns/evaluator_optimizer.py`を新規作成します。

```python
# patterns/evaluator_optimizer.py
"""評価者-最適化者: ルーブリックで採点し、合格するまで改善を繰り返す（新規作成）"""
import json
import logging
from dataclasses import dataclass

from llm_client import FAST_MODEL, MODEL, call_messages, extract_text, tracker
from patterns import PatternError, json_format, parse_json_response

logger = logging.getLogger("patterns.evaluator_optimizer")

CRITERIA = ["accuracy", "specificity", "readability", "call_to_read"]
RUBRIC = """各項目を1〜5の整数で採点してください。
- accuracy（正確性）: 5=技術的な誤りがない / 1=明らかな誤りがある
- specificity（具体性）: 5=読者の具体的な悩みや場面がある / 1=一般論だけ
- readability（読みやすさ）: 5=1文が短く用語に説明がある / 1=長文で用語の説明がない
- call_to_read（誘導）: 5=記事を読む利点が最後に示されている / 1=読む理由がわからない
4点以下の項目には、具体的な改善点を1つずつ書いてください。"""

EVAL_SCHEMA = {
    "type": "object",
    "properties": {
        "scores": {
            "type": "object",
            "properties": {c: {"type": "integer"} for c in CRITERIA},
            "required": CRITERIA,
            "additionalProperties": False,
        },
        "improvements": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["scores", "improvements"],
    "additionalProperties": False,
}


@dataclass
class Evaluation:
    scores: dict[str, int]
    improvements: list[str]

    @property
    def total(self) -> int:
        return sum(self.scores.values())

    def passed(self, min_score: int = 4) -> bool:
        """合格判定はコードで行う: 全項目が min_score 以上なら合格"""
        return all(s >= min_score for s in self.scores.values())
```

`RUBRIC`は、評価者に渡すルーブリックの文章です。
各項目の5点と1点の状態を書いておくと、評価者の採点がぶれにくくなります。
最後の1文では、「4点以下の項目に改善点を書く」よう指示しています。
点数だけでは、最適化者が何を直せばよいか分からないからです。

`EVAL_SCHEMA`の`scores`は、評価項目をキーにしたオブジェクトです。
4項目分のプロパティは、辞書内包表記で作っています。
`{c: {"type": "integer"} for c in CRITERIA}`の部分です。
項目名を`CRITERIA`の1か所で管理しているので、項目を増やすときも修正が1か所で済みます。

`Evaluation`の`passed()`が、合格判定をコードで行う部分です。
「全項目4点以上」という基準は、`min_score`で調整できます。

続いて、生成役・評価役・ループです。

```python
# patterns/evaluator_optimizer.py（続き）
def generate(topic: str, previous: str | None, improvements: list[str]) -> str:
    """最適化者: 初回は新規に書き、2回目以降は指摘を反映して書き直す"""
    prompt = f"技術ブログ記事「{topic}」の導入段落を200〜300字で書いてください。"
    if previous:
        prompt += f"\n\n<previous>\n{previous}\n</previous>\n次の改善点を反映して書き直してください。\n- " + "\n- ".join(improvements)
    response = call_messages(
        [{"role": "user", "content": prompt}],
        system="あなたは技術ブログの書き手です。導入段落の本文だけを出力してください。",
        model=MODEL,
        max_tokens=8000,
    )
    if response["stop_reason"] != "end_turn":
        raise PatternError(f"生成が正常に終わりませんでした: {response['stop_reason']}")
    return extract_text(response).strip()


def evaluate(topic: str, draft: str) -> Evaluation:
    """評価者: 生成の経緯を知らない独立した呼び出しで採点する"""
    response = call_messages(
        [{"role": "user", "content": f"記事のテーマ: {topic}\n\n<draft>\n{draft}\n</draft>"}],
        system=f"あなたは厳しい技術編集者です。書き手の事情は考慮せず、原稿だけを評価してください。\n{RUBRIC}",
        model=FAST_MODEL,
        max_tokens=4000,
        output_config=json_format(EVAL_SCHEMA),
    )
    data = parse_json_response(response)
    # スキーマでは範囲を制約していないので、1〜5 にそろえる
    scores = {k: min(5, max(1, v)) for k, v in data["scores"].items()}
    return Evaluation(scores, data["improvements"])


def optimize(topic: str, *, max_rounds: int = 3, min_score: int = 4) -> tuple[str, Evaluation]:
    """合格・上限到達・改善の停滞のいずれかで止め、最高得点の版を返す"""
    best: tuple[str, Evaluation] | None = None
    draft, improvements = None, []
    for round_no in range(1, max_rounds + 1):
        draft = generate(topic, draft, improvements)
        evaluation = evaluate(topic, draft)
        logger.info("第%d版: 合計%d点 %s", round_no, evaluation.total, json.dumps(evaluation.scores))
        if evaluation.passed(min_score):
            logger.info("合格しました")
            return draft, evaluation  # 合格した版をそのまま採用する
        if best is None or evaluation.total > best[1].total:
            best = (draft, evaluation)
        elif round_no > 1:
            logger.info("改善が止まったため終了します")  # 停滞: 前回より良くならない
            break
        improvements = evaluation.improvements
    return best


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING, format="%(name)s: %(message)s")
    logging.getLogger("patterns").setLevel(logging.INFO)
    text, ev = optimize("httpxでClaude APIを直接呼んでみよう")
    print(f"\n=== 採用版（合計{ev.total}点） ===\n{text}\n\n{tracker.summary()}")
```

`generate()`は、前回の原稿と改善点を受け取って書き直します。
前回の原稿は、`<previous>`タグで囲んで渡します。
どこが前回の原稿でどこが指示かを、モデルが取り違えないようにするためです。

`evaluate()`の最後では、点数を1〜5の範囲に丸めています。
スキーマでは`integer`としか指定していないので、まれに範囲外の値が返る可能性に備えた防御です。
受け取った値をそのまま信じず、コードで整えるのは、9.2節のゲートと同じ考え方です。

`optimize()`には、3つの終了条件があります。
**合格したとき**、**上限回数に達したとき**、そして**改善が止まったとき**です。
3つめの条件が重要です。
評価者-最適化者では、書き直すほど点数が下がることが実際に起こります。
指摘に合わせて直した結果、別の項目が崩れるからです。
そのため、`best`で最高得点の版を覚えておき、点数が上がらなくなったら打ち切ります。
合格判定は、停滞の判定より先に置いています。
合計点が前の版より低くても、全項目が基準を満たした版を確実に採用するためです。
合格しないまま終わった場合に返すのは、最後の版ではなく最高得点の版です。

> **WARNING**: 終了条件が「合格したら終了」だけのループは危険です。評価者が厳しすぎると永遠に合格せず、呼び出しが続きます。上限回数と停滞の検出を必ず併用し、ループの費用に天井を設けてください。

### 実行して改善の過程を読む

```bash
# 最大3回の改善ループを実行する
uv run python -m patterns.evaluator_optimizer
```

出力の例です。

```text
patterns.evaluator_optimizer: 第1版: 合計14点 {"accuracy": 5, "specificity": 3, "readability": 4, "call_to_read": 2}
patterns.evaluator_optimizer: 第2版: 合計18点 {"accuracy": 5, "specificity": 4, "readability": 5, "call_to_read": 4}
patterns.evaluator_optimizer: 合格しました

=== 採用版（合計18点） ===
「SDKなしでAPIを呼ぶなんて面倒そう」と感じていませんか。……

calls=4 input=3,215 output=2,476 cache_write=0 cache_read=0 total=$0.0480
```

第1版では、具体性と誘導の点数が低くなっています。
評価者の改善点を受けて、第2版ではどちらも4点に上がり、合格しました。
ログに項目ごとの点数を残しておくと、どの項目がループで改善しやすいかが見えてきます。
何回回しても上がらない項目があれば、それはループではなく最初のプロンプトで指示すべき点です。

### 評価者の独立性

このパターンでもっとも大切なのは、**評価者を最適化者から独立させること**です。
LLMには、自分が書いたものを高く評価しやすい傾向があります。
同じ会話の中で「今書いた文章を採点して」と頼むと、書いた経緯を知っているぶん、甘い採点になりがちです。

本書の実装では、次の3つの工夫で独立性を保っています。

1. **会話履歴を共有しない**：`evaluate()`は新しいメッセージ配列で呼び、生成の経緯を見せません。評価者が見るのは原稿とテーマだけです。
2. **役割を分ける**：評価者のsystem プロンプトで「厳しい技術編集者」とし、「書き手の事情は考慮しない」と明示しています。
3. **モデルを分ける**：生成は`MODEL`、評価は`FAST_MODEL`にしています。同じモデルの偏りを持ち込みにくくなり、評価の費用も抑えられます。

ただし、3つめは課題しだいです。
技術的な正確性を厳密に見る必要があるなら、評価者にも`MODEL`を使う方が確実です。
評価者の採点が信頼できるかどうかは、人間の採点と比べて確かめるのが理想です。
評価者自体を評価する方法は、第11章で扱います。

> **POINT**: 評価者-最適化者の品質の上限は、評価者の目の確かさで決まります。ルーブリックを具体的に書き、評価者を最適化者から切り離すことに、もっとも力を注いでください。

---

## 9.5 オーケストレーター-ワーカーと情報連携

ここまでのパターンでは、仕事の分け方をすべてコードで決めていました。
観点は3つ、投票者は5人、と前もって決まっています。
しかし「このテーマについて調べてレポートにして」と頼まれたら、何を何件調べるべきかは、テーマを見るまで分かりません。
この節では、分解そのものをモデルに任せるオーケストレーター-ワーカーを整理します。
あわせて、エージェント同士が情報を受け渡す方法も整理します。

### オーケストレーター-ワーカーとは

オーケストレーター-ワーカーとは、中心となるLLMがタスクを動的にサブタスクへ分解するパターンです。
この中心となるLLMを、オーケストレーター（指揮者）と呼びます。
オーケストレーターは、サブタスクをワーカーに割り振り、結果を統合します。
見た目は9.3節のセクショニングに似ています。
決定的な違いは、**サブタスクの数と内容を、実行時にモデルが決める**ことです。
セクショニングはコードが分担を決め、オーケストレーター-ワーカーはモデルが分担を決めます。

<figure id="fig-9-7">
<svg width="605" height="325" viewBox="0 0 605 325" xmlns="http://www.w3.org/2000/svg" font-family="'Noto Sans JP',sans-serif">
  <defs>
    <marker id="f9_7_ar97" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#333" stroke-width="1.5"/>
    </marker>
  </defs>
  <!-- 目標 -->
  <rect x="200" y="10" width="205" height="32" rx="6" fill="#fff" stroke="#999" stroke-width="1" stroke-dasharray="4,3"/>
  <text x="302" y="31" text-anchor="middle" font-size="12" fill="#1a1a1a">目標（<tspan font-family="Consolas,monospace">goal</tspan>）</text>
  <path d="M302 42 L302 63" stroke="#333" stroke-width="1.3" marker-end="url(#f9_7_ar97)"/>
  <!-- オーケストレーター -->
  <rect x="130" y="65" width="345" height="55" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.4"/>
  <text x="302" y="87" text-anchor="middle" font-size="13" fill="#1a1a1a" font-weight="bold">オーケストレーター（<tspan font-family="Consolas,monospace">MODEL</tspan>）</text>
  <text x="302" y="108" text-anchor="middle" font-size="11" fill="#1a1a1a">サブタスクの数と内容を実行時に決めて分解する</text>
  <!-- 配る -->
  <path d="M200 120 L95 163" stroke="#333" stroke-width="1.3" marker-end="url(#f9_7_ar97)"/>
  <path d="M260 120 L245 163" stroke="#333" stroke-width="1.3" marker-end="url(#f9_7_ar97)"/>
  <path d="M345 120 L395 163" stroke="#333" stroke-width="1.3" marker-end="url(#f9_7_ar97)"/>
  <path d="M420 120 L532 163" stroke="#333" stroke-width="1.3" stroke-dasharray="4,3" marker-end="url(#f9_7_ar97)"/>
  <text x="20" y="140" font-size="11" fill="#1a1a1a">サブタスクを配る</text>
  <!-- ワーカー -->
  <rect x="30" y="165" width="130" height="45" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="95" y="184" text-anchor="middle" font-size="12" fill="#1a1a1a">ワーカー1</text>
  <text x="95" y="200" text-anchor="middle" font-size="10" fill="#1a1a1a" font-family="Consolas,monospace">FAST_MODEL</text>
  <rect x="180" y="165" width="130" height="45" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="245" y="184" text-anchor="middle" font-size="12" fill="#1a1a1a">ワーカー2</text>
  <text x="245" y="200" text-anchor="middle" font-size="10" fill="#1a1a1a" font-family="Consolas,monospace">FAST_MODEL</text>
  <rect x="330" y="165" width="130" height="45" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="395" y="184" text-anchor="middle" font-size="12" fill="#1a1a1a">ワーカー3</text>
  <text x="395" y="200" text-anchor="middle" font-size="10" fill="#1a1a1a" font-family="Consolas,monospace">FAST_MODEL</text>
  <rect x="480" y="165" width="105" height="45" rx="6" fill="#fff" stroke="#999" stroke-width="1" stroke-dasharray="4,3"/>
  <text x="532" y="184" text-anchor="middle" font-size="12" fill="#1a1a1a">…</text>
  <text x="532" y="200" text-anchor="middle" font-size="10" fill="#1a1a1a">上限はコードで</text>
  <!-- 返す -->
  <path d="M95 210 L200 253" stroke="#333" stroke-width="1.3" marker-end="url(#f9_7_ar97)"/>
  <path d="M245 210 L260 253" stroke="#333" stroke-width="1.3" marker-end="url(#f9_7_ar97)"/>
  <path d="M395 210 L345 253" stroke="#333" stroke-width="1.3" marker-end="url(#f9_7_ar97)"/>
  <path d="M532 210 L420 253" stroke="#333" stroke-width="1.3" stroke-dasharray="4,3" marker-end="url(#f9_7_ar97)"/>
  <text x="20" y="240" font-size="11" fill="#1a1a1a">結果を返す</text>
  <!-- 統合 -->
  <rect x="130" y="255" width="345" height="40" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.4"/>
  <text x="302" y="280" text-anchor="middle" font-size="12" fill="#1a1a1a" font-weight="bold">統合：結果をまとめて最終回答にする</text>
  <text x="302" y="316" text-anchor="middle" font-size="11" fill="#666">セクショニングとの違い：分担を決めるのはコードではなくモデル</text>
</svg>
  <figcaption>図9.7: オーケストレーター-ワーカーの構造</figcaption>
</figure>

複数ファイルにまたがるコード修正や、複数の情報源を調べる調査が典型例です。
どのファイルを直すべきか、どの観点で調べるべきかは、課題を読んで初めて決まります。

### 第8章の実装との関係

実は、読者のみなさんはこのパターンをすでに第8章で実装しています。
第8章の`multi_agent.py`では、オーケストレーター役の`Agent`がサブエージェントに仕事を頼みました。
頼む手段は、ツール呼び出しです。
そして、その結果を受け取って最終回答をまとめました。
何をどのサブエージェントに何回頼むかは、オーケストレーターのモデルが決めていました。
これは、自律エージェントの形で作ったオーケストレーター-ワーカーです。

一方、同じパターンをワークフロー寄りに作ることもできます。
「分解」だけをモデルに構造化出力で行わせ、ワーカーの実行と統合はコードで決める形です。
骨格を示します（説明用のコードで、保存は不要です）。

```python
# orchestrator_sketch.py（説明用の骨格。第10章で report_agent/ として本格的に実装する）
import asyncio

from agent import Agent
from llm_client import FAST_MODEL, MODEL, call_messages
from patterns import json_format, parse_json_response
from tool_registry import ToolRegistry

PLAN_SCHEMA = {
    "type": "object",
    "properties": {"subtasks": {"type": "array", "items": {"type": "string"}}},
    "required": ["subtasks"],
    "additionalProperties": False,
}


async def orchestrate(goal: str) -> list[str]:
    # 1. 分解: サブタスクの数と内容はモデルが決める
    plan = parse_json_response(call_messages(
        [{"role": "user", "content": f"次の目標を独立したサブタスク（最大5件）に分解してください: {goal}"}],
        model=MODEL, max_tokens=4000, output_config=json_format(PLAN_SCHEMA),
    ))
    subtasks = plan["subtasks"][:5]  # モデルの判断にもコードで上限をかける
    # 2. 実行: 第8章の Agent をワーカーとして並列に走らせる
    worker = Agent(name="worker", system="与えられたサブタスクだけを調べ、要点を報告してください。",
                   registry=ToolRegistry(), model=FAST_MODEL)
    return await asyncio.gather(*(worker.arun(t) for t in subtasks))
```

`plan["subtasks"][:5]`で件数に上限をかけている点に注目してください。
分解をモデルに任せても、暴走を防ぐ枠はコードで決めます。
本書の第10章では、このワークフロー寄りの形と、第8章のエージェント寄りの形を組み合わせます。
そして、調査レポートを作るマルチエージェントを完成させます。

| 作り方 | 分解 | 実行の順番・回数 | 長所 | 短所 |
|---|---|---|---|---|
| ワークフロー寄り（上の骨格） | モデル（構造化出力） | コード | 費用と時間が読みやすい | 途中で計画を変えられない |
| エージェント寄り（第8章） | モデル（ツール呼び出し） | モデル | 結果を見て追加調査できる | 呼び出し回数が読みにくい |

### 情報連携の3方式

オーケストレーターとワーカーが協力するには、情報の受け渡しが必要です。
本書では、受け渡しの方式を次の3つに整理します。

<figure id="fig-9-8">
<svg width="605" height="345" viewBox="0 0 605 345" xmlns="http://www.w3.org/2000/svg" font-family="'Noto Sans JP',sans-serif">
  <defs>
    <marker id="f9_8_ar98" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#333" stroke-width="1.5"/>
    </marker>
    <marker id="f9_8_ar98b" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#2b6cb0" stroke-width="1.5"/>
    </marker>
  </defs>
  <!-- 見出し -->
  <text x="105" y="26" text-anchor="middle" font-size="13" fill="#1a1a1a" font-weight="bold">① 戻り値</text>
  <text x="302" y="26" text-anchor="middle" font-size="13" fill="#1a1a1a" font-weight="bold">② 共有ストア</text>
  <text x="500" y="26" text-anchor="middle" font-size="13" fill="#1a1a1a" font-weight="bold">③ タスクリスト</text>
  <!-- オーケストレーター -->
  <rect x="15" y="40" width="180" height="36" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="105" y="63" text-anchor="middle" font-size="12" fill="#1a1a1a">オーケストレーター</text>
  <rect x="212" y="40" width="180" height="36" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="302" y="63" text-anchor="middle" font-size="12" fill="#1a1a1a">オーケストレーター</text>
  <rect x="410" y="40" width="180" height="36" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="500" y="63" text-anchor="middle" font-size="12" fill="#1a1a1a">オーケストレーター</text>
  <!-- ワーカー -->
  <rect x="15" y="210" width="180" height="36" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="105" y="233" text-anchor="middle" font-size="12" fill="#1a1a1a">ワーカー</text>
  <rect x="212" y="210" width="180" height="36" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="302" y="233" text-anchor="middle" font-size="12" fill="#1a1a1a">ワーカー</text>
  <rect x="410" y="210" width="180" height="36" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="500" y="233" text-anchor="middle" font-size="12" fill="#1a1a1a">ワーカー（複数）</text>
  <!-- ① 戻り値 -->
  <path d="M105 210 L105 78" stroke="#2b6cb0" stroke-width="1.5" marker-end="url(#f9_8_ar98b)"/>
  <rect x="45" y="122" width="120" height="44" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.2"/>
  <text x="105" y="141" text-anchor="middle" font-size="11" fill="#1a1a1a">結果そのもの</text>
  <text x="105" y="157" text-anchor="middle" font-size="10" fill="#1a1a1a">（関数の戻り値）</text>
  <!-- ② 共有ストア -->
  <rect x="318" y="115" width="74" height="56" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.2"/>
  <text x="355" y="138" text-anchor="middle" font-size="10" fill="#1a1a1a" font-family="Consolas,monospace">workspace/</text>
  <text x="355" y="156" text-anchor="middle" font-size="10" fill="#1a1a1a">ファイル</text>
  <path d="M355 210 L355 173" stroke="#333" stroke-width="1.3" marker-end="url(#f9_8_ar98)"/>
  <text x="361" y="196" font-size="10" fill="#1a1a1a">書く</text>
  <path d="M355 115 L355 78" stroke="#333" stroke-width="1.3" stroke-dasharray="4,3" marker-end="url(#f9_8_ar98)"/>
  <text x="361" y="100" font-size="10" fill="#1a1a1a">読む</text>
  <path d="M250 210 L250 78" stroke="#2b6cb0" stroke-width="1.5" marker-end="url(#f9_8_ar98b)"/>
  <text x="256" y="148" font-size="11" fill="#2b6cb0" font-weight="bold">パス</text>
  <text x="256" y="163" font-size="11" fill="#2b6cb0" font-weight="bold">だけ</text>
  <!-- ③ タスクリスト -->
  <rect x="430" y="102" width="140" height="84" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.2"/>
  <text x="500" y="120" text-anchor="middle" font-size="10" fill="#1a1a1a" font-family="Consolas,monospace">タスク一覧（JSON）</text>
  <line x1="440" y1="127" x2="560" y2="127" stroke="#2b6cb0" stroke-width="0.8"/>
  <text x="442" y="143" font-size="10" fill="#1a1a1a" font-family="Consolas,monospace">#1 status: done</text>
  <text x="442" y="159" font-size="10" fill="#1a1a1a" font-family="Consolas,monospace">#2 status: doing</text>
  <text x="442" y="175" font-size="10" fill="#1a1a1a" font-family="Consolas,monospace">#3 status: todo</text>
  <path d="M500 76 L500 100" stroke="#333" stroke-width="1.3" marker-end="url(#f9_8_ar98)"/>
  <text x="506" y="93" font-size="10" fill="#1a1a1a">登録</text>
  <path d="M500 188 L500 208" stroke="#333" stroke-width="1.3" marker-start="url(#f9_8_ar98)" marker-end="url(#f9_8_ar98)"/>
  <text x="506" y="203" font-size="10" fill="#1a1a1a">取る・状態を更新</text>
  <!-- 下段: 特徴 -->
  <line x1="15" y1="262" x2="590" y2="262" stroke="#999" stroke-width="1"/>
  <text x="105" y="282" text-anchor="middle" font-size="11" fill="#1a1a1a">結果が短い・ワーカーが少ない</text>
  <text x="105" y="300" text-anchor="middle" font-size="11" fill="#1a1a1a">注意：コンテキストの圧迫</text>
  <text x="302" y="282" text-anchor="middle" font-size="11" fill="#1a1a1a">成果物が大きい・後で確認</text>
  <text x="302" y="300" text-anchor="middle" font-size="11" fill="#1a1a1a">注意：書き込み先の衝突</text>
  <text x="500" y="282" text-anchor="middle" font-size="11" fill="#1a1a1a">仕事が多い・中断と再開</text>
  <text x="500" y="300" text-anchor="middle" font-size="11" fill="#1a1a1a">注意：排他制御が必要</text>
  <text x="302" y="332" text-anchor="middle" font-size="11" fill="#666">単純 → 複雑：まず戻り値で作り、困ったら右の方式へ進む</text>
</svg>
  <figcaption>図9.8: エージェント間の情報連携3方式</figcaption>
</figure>

**1つめは戻り値です。**
ワーカーの結果を、関数の戻り値としてオーケストレーターに返す方式です。
第8章の実装や、上の骨格の`gather()`がこれにあたります。
もっとも単純で、追加の仕組みがいりません。
ただし、ワーカーの結果がそのままオーケストレーターのコンテキストに入るため、結果が長いとすぐにコンテキストを圧迫します。
ワーカーには「要点だけを報告する」よう指示し、戻り値を短く保つのがコツです。

**2つめは共有ストアです。**
ワーカーが結果をファイルなどの共有の置き場所に書き込み、オーケストレーターには「どこに書いたか」だけを返す方式です。
第10章では`workspace/`ディレクトリを共有ストアにし、調査メモや下書きをMarkdownで保存します。
大きな成果物をコンテキストに通さずに済むのが最大の利点です。
また、途中の成果物がファイルとして残るので、人間が後から確認したり、失敗した段階からやり直したりできます。
注意点は、複数のワーカーが同じファイルに書き込まないよう、ファイル名をワーカーごとに分けることです。

**3つめはタスクリストです。**
やるべき仕事の一覧を共有し、各ワーカーが未着手の仕事を取って、状態を更新していく方式です。
項目を並べたJSONファイルを想像してください。
1つの項目は、`{"id": 3, "title": "競合製品の価格を調べる", "status": "done"}`のような形です。
仕事の進み具合が一覧で分かり、途中で止まっても未完了の項目から再開できます。
その反面、「同じ仕事を2つのワーカーが取らない」ための排他制御が必要になり、実装は最も複雑です。

| 方式 | 受け渡すもの | 向いている場面 | 注意点 |
|---|---|---|---|
| 戻り値 | 結果そのもの | 結果が短い・ワーカーが少ない | コンテキストの圧迫 |
| 共有ストア | 置き場所（パス） | 成果物が大きい・後から確認したい | 書き込み先の衝突 |
| タスクリスト | 仕事の一覧と状態 | 仕事が多い・中断と再開がある | 排他制御が必要 |

まずは戻り値で作るのがおすすめです。
コンテキストが苦しくなったら共有ストアへ、仕事の数や中断が問題になったらタスクリストへ、と段階的に進めます。
ここでも「必要になるまで複雑にしない」原則が当てはまります。

### パターンを組み合わせるときの注意

本章のパターンは、組み合わせて使えます。
ルーティングの先でチェーンを走らせたり、オーケストレーターのワーカーの中で評価者-最適化者を回したりできます。
ただし、組み合わせるときには3つの落とし穴があります。

1つめは、**費用の掛け算**です。
5件のサブタスクのそれぞれで、3回の評価ループを回すと、それだけで30回の呼び出しになります。
組み合わせる前に、最悪の場合の呼び出し回数を掛け算で見積もり、`tracker`で実際の費用を確かめてください。

2つめは、**誤りの掛け算**です。
各段階の成功率が95%でも、5段階をつなぐと全体の成功率は約77%に下がります。
段階を増やすほど、ゲートや評価で誤りを早めに止める仕組みが重要になります。

3つめは、**見通しの悪化**です。
組み合わせが深くなるほど、どこで何が起きたかを追いにくくなります。
本章の各パターンのように、段階ごとにロガーで中間結果を残しておきましょう。
そして、組み合わせる前に各パターンを単独で動かし、期待どおりに動くことを確かめてから合体させるのが鉄則です。

> **POINT**: パターンは「部品」です。複雑な構成を最初から設計するのではなく、単一呼び出しから始め、測定して足りない部分にだけパターンを足していきましょう。

---

## COLUMN: パターンの名前にこだわりすぎない

本章では、Anthropicの分類に沿って6つのパターンを紹介しました。
しかし、実際のシステムが、どれか1つのパターンにきれいに当てはまることはまれです。
9.2節のチェーンにも、書き直しという小さな評価ループが入っていました。
9.3節のセクショニングの統合段階をLLMに任せれば、それはもうチェーンとの組み合わせです。

筆者は、パターンの名前を「設計の会話を短くするための語彙」だと考えています。
「ここはルーティングで分けて、技術の問い合わせだけ評価ループを回そう」と言えば、チームの全員が構造を思い浮かべられます。
大切なのは、名前の正しさではありません。
各段階で「誰が次の一手を決めているか」「どこで誤りを止めるか」「費用の天井はどこか」を説明できることです。
本章のコードは`httpx`の上に数十行で書かれています。
仕組みが見えているからこそ、パターンを自由に崩したり組み合わせたりできるのです。

---

## 本章のまとめ

本章で学んだことを整理します：

- LLMを使うシステムは、単一呼び出し・ワークフロー・エージェントの3段階に分けられます。次の一手をコードが決めるか、モデルが決めるかが境界であり、複雑さ・価値・実現性・失敗時のコストの4基準で段階を選びます。
- ワークフローの代表パターンを、`patterns/`に実装しました。ゲート付きのプロンプトチェーンと、構造化出力で分類するルーティングです。さらに、並列化（セクショニングと投票）も作りました。使ったのは`acall_messages()`と`asyncio.gather()`です。最後は、ルーブリックで採点する評価者-最適化者です。`temperature`が使えないため、投票の多様性は観点の違うプロンプトで出します。
- オーケストレーター-ワーカーは、分解をモデルに任せるパターンで、第8章のマルチエージェントがその一例です。情報連携には戻り値・共有ストア・タスクリストの3方式があり、組み合わせるときは費用と誤りの掛け算に注意します。

次章では **実践プロジェクト — 調査レポート自動作成マルチエージェント** を扱います。
これまでの部品とパターンをすべて組み合わせて、実務で使えるマルチエージェントを完成させます。
オーケストレーターが調査を分解し、ワーカーが`workspace/`に成果を書き、レビュー役が品質を確かめる。
本章で学んだパターンが、1つのシステムの中でどう噛み合うのかを、ぜひ体感してください。
