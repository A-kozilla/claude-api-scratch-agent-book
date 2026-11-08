# 第2章: 開発環境を整える
# EN-TITLE: SETTING UP YOUR ENVIRONMENT
# TAGS: Claude Console, APIキー, uv, httpx, curl

## この章で学ぶこと

本章では以下を学びます：

- Claude Console（クロード・コンソール）でAPIキーを発行できるようになる。あわせて利用上限（spend limit）を設定し、安心してAPIを試せる状態を作れるようになる
- **uv（ユーブイ）** と **VS Code（ブイエスコード）** を使えるようになる。これらで、Python 3.12のプロジェクト `agent-from-scratch` を作って実行できるようになる
- APIキーを `.env` と `.gitignore` で安全に管理し、万一漏えいしたときの対処手順を説明できるようになる
- curl（カール）とPythonの **httpx（エイチティーティーピーエックス）** を使う。これらで、Claude APIに最初のリクエストを送り、返ってきた回答を取り出せるようになる

前章では、AIエージェントが「LLM＋ツール＋ループ」という3つの要素でできていることを学びました。
本章では、その構造を自分の手で組み立てるための土台として、Claude APIを呼び出せる開発環境を整えます。

> [!DIALOGUE]
> **読者**: いよいよコードを書くんですね。でも、何から準備すればいいのか見当がつきません。
> **筆者**: 準備するものは、実は4つだけです。APIキー、Python環境、キーの保管場所、そして最初の1回のリクエストです。
> **読者**: 最初の1回は、いきなりPythonで書くんですか？
> **筆者**: いいえ、まずはcurlという道具でHTTPの生のやり取りを見ます。そのあとで同じことをPythonで書くと、コードの1行1行が何をしているのかがはっきり見えてきますよ。

本章の作業は、すべて手元のパソコンで完結します。Windows・macOS・Linuxのどれを使っていても進められるよう、OSごとに手順が異なる箇所はそれぞれ書き分けています。読み進めながら、実際に手を動かしてみてください。章の終わりには、Claude APIから返ってきた最初の回答が、あなたのターミナルに表示されているはずです。

---

## 2.1 Claude APIの全体像とAPIキーの発行

「Claude」という名前は、チャットのWebサービスでもAPIでも使われています。そのため、最初に「本書で使うClaudeはどれなのか」を整理しておかないと、アカウントの作成や支払いの段階で迷ってしまいがちです。たとえば、すでにチャット版の有料プランを契約している方は、「それでAPIも使えるのでは？」と考えるかもしれません。結論から言うと、両者は別の製品で、契約も支払いも別々です。ただし、一部のプランには毎月のAPIクレジットが付きます（後述）。本節では、まずこの関係を整理してから、APIキーの発行と利用上限の設定までを進めます。

### Claude APIとclaude.aiの違い

**claude.ai（クロード・ドット・エーアイ）** は、Claudeと対話するためのチャット製品です。ブラウザやデスクトップアプリ、スマートフォンアプリから使えます。画面に文章を入力すると、Claudeが返答してくれます。料金は月額の定額制が基本で、無料プランと有料のサブスクリプションプランが用意されています。人間が画面を見ながら使うことを前提にした製品だと言えます。

一方、**Claude API（クロード・エーピーアイ）** は、プログラムからClaudeを呼び出すための窓口です。API（Application Programming Interface）とは、ソフトウェア同士がやり取りするための決まりごとを指します。Claude APIでは、プログラムがHTTP（エイチティーティーピー）という通信の仕組みでリクエストを送ります。すると、Claudeの回答がJSON（ジェイソン）という形式で返ってきます。料金は使った分だけ支払う従量課金制です。

たとえるなら、claude.aiは「お店のカウンターで店員さんと話す」形です。一方のClaude APIは「お店の裏口から業務用の注文票を出す」形です。カウンターでは店員さんが会話の流れを覚えていてくれますが、注文票は1枚ずつ独立して処理されます。会話の流れを保つには、注文票にこれまでのやり取りを毎回書き添える必要があるわけです。前章で「APIはステートレス（状態を持たない）」と説明したのは、まさにこの性質のことでした。

本書で作るエージェントは、プログラムがClaudeを何度も呼び出し、その結果を見て次の行動を決める仕組みです。人間が画面に入力するのではなく、コードがループの中で自動的に呼び出すので、使うのは必ずClaude APIのほうになります。claude.aiの有料プランの料金に、API利用料は含まれません。ただし、Max・Teamプランには毎月一定額のAPIクレジットが付きます。claude.aiの請求設定でConsoleの組織を紐づけると受け取れ、Claude Codeには使えません。逆に、APIを使うだけならclaude.aiの有料プランは必要ありません。この区別を最初に押さえておくと、請求の確認や問い合わせの際にも混乱せずに済みます。

| 観点 | claude.ai（チャット製品） | Claude API（本書で使う） |
|---|---|---|
| 使い方 | ブラウザ・アプリの画面で対話する | プログラムからHTTPで呼び出す |
| 料金 | 無料プランと月額の定額プラン | 使ったトークン量に応じた従量課金 |
| 管理画面 | claude.ai の設定画面 | Claude Console（platform.claude.com） |
| 会話の記憶 | 製品側が会話履歴を保持する | 保持しない。毎回すべての履歴を送る |
| 認証 | メールアドレス等でログイン | APIキーをリクエストのヘッダーに付ける |

> **POINT**: claude.aiのサブスクリプションとClaude APIの利用料は、別の契約です。本書のコードを動かすには、Claude ConsoleでAPI用のクレジット（前払いの利用残高）を用意する必要があります。Max・Teamプランの方は、毎月付くAPIクレジットも使えます（請求期間の終わりに失効し、繰り越せません）。

### Claude Consoleと「組織・ワークスペース・APIキー」の関係

Claude APIのユーザーが操作する管理画面が、**Claude Console** です。アドレスは https://platform.claude.com です。以前は別のアドレスで提供されていた時期もあるため、古い記事を見かけたときは、アドレスが変わっていることに注意してください。Consoleでは、APIキーの発行、クレジットの購入、利用量の確認、利用上限の設定などをまとめて行います。

Consoleの中には、いくつかの「入れ物」が階層になって存在します。いちばん外側が **組織（Organization）** で、請求先や支払い方法はこの単位で管理されます。その中に **ワークスペース（Workspace）** があり、APIキーや利用上限をプロジェクトごとに分けて管理できます。そして、それぞれのワークスペースの中で **APIキー** を発行します。

たとえば、会社の中で「社内チャットボット」と「本書の学習用」を同じ組織で扱うとします。ワークスペースを分けておけば、学習用のキーで使った金額だけを確認したり、学習用だけに低い上限を設けたりできます。学習中のコードが暴走しても、本番用の予算には影響しません。個人で学ぶ場合でも、この「入れ物を分ける」考え方は覚えておく価値があります。

<figure id="fig-2-1">
<svg width="605" height="355" viewBox="0 0 605 355"
     xmlns="http://www.w3.org/2000/svg"
     font-family="'Noto Sans JP',sans-serif">
  <defs>
    <marker id="f2_1_arrow" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#333" stroke-width="1.5"/>
    </marker>
    <marker id="f2_1_arrowA" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#2b6cb0" stroke-width="1.5"/>
    </marker>
  </defs>
  <rect x="0" y="0" width="605" height="355" fill="#ffffff"/>
  <rect x="20" y="20" width="565" height="280" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.2"/>
  <text x="35" y="38" text-anchor="start" dominant-baseline="central" font-size="13" fill="#1a1a1a" font-weight="bold">組織（Organization）</text>
  <text x="575" y="38" text-anchor="end" dominant-baseline="central" font-size="11" fill="#555">請求先・支払い方法・組織全体の利用上限</text>
  <rect x="35" y="56" width="170" height="230" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="120" y="74" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#555">ワークスペース</text>
  <text x="120" y="93" text-anchor="middle" dominant-baseline="central" font-size="12" font-family="Consolas,monospace" fill="#1a1a1a" font-weight="bold">Default Workspace</text>
  <text x="120" y="111" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#555">最初からある既定</text>
  <rect x="45" y="126" width="150" height="30" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.2"/>
  <text x="120.0" y="141.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">利用上限は設定できない</text>
  <text x="120" y="174" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-weight="bold">APIキー</text>
  <rect x="45" y="186" width="150" height="40" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.2"/>
  <text x="120.0" y="198.5" text-anchor="middle" dominant-baseline="central" font-size="11" font-family="Consolas,monospace" fill="#1a1a1a">既存のキー</text>
  <text x="120.0" y="213.5" text-anchor="middle" dominant-baseline="central" font-size="11" font-family="Consolas,monospace" fill="#555">sk-ant-…</text>
  <rect x="45" y="240" width="150" height="34" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.2" stroke-dasharray="5 3"/>
  <text x="120.0" y="257.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">必要に応じて追加</text>
  <rect x="218" y="56" width="170" height="230" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="303" y="74" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#555">ワークスペース</text>
  <text x="303" y="93" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a" font-weight="bold">社内チャットボット</text>
  <text x="303" y="111" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#555">本番用の例</text>
  <rect x="228" y="126" width="150" height="30" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.2"/>
  <text x="303.0" y="141.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">利用上限：本番の予算</text>
  <text x="303" y="174" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-weight="bold">APIキー</text>
  <rect x="228" y="186" width="150" height="40" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.2"/>
  <text x="303.0" y="198.5" text-anchor="middle" dominant-baseline="central" font-size="11" font-family="Consolas,monospace" fill="#1a1a1a">chatbot-prod</text>
  <text x="303.0" y="213.5" text-anchor="middle" dominant-baseline="central" font-size="11" font-family="Consolas,monospace" fill="#555">sk-ant-…</text>
  <rect x="228" y="240" width="150" height="34" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.2" stroke-dasharray="5 3"/>
  <text x="303.0" y="257.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">必要に応じて追加</text>
  <rect x="401" y="56" width="170" height="230" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="486" y="74" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#555">ワークスペース</text>
  <text x="486" y="93" text-anchor="middle" dominant-baseline="central" font-size="12" font-family="Consolas,monospace" fill="#1a1a1a" font-weight="bold">agent-from-scratch</text>
  <text x="486" y="111" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#555">本書の学習用（推奨）</text>
  <rect x="411" y="126" width="150" height="30" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.2"/>
  <text x="486.0" y="141.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">利用上限：月10ドル程度</text>
  <text x="486" y="174" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-weight="bold">APIキー</text>
  <rect x="411" y="186" width="150" height="40" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.2"/>
  <text x="486.0" y="198.5" text-anchor="middle" dominant-baseline="central" font-size="11" font-family="Consolas,monospace" fill="#1a1a1a">laptop-book-study</text>
  <text x="486.0" y="213.5" text-anchor="middle" dominant-baseline="central" font-size="11" font-family="Consolas,monospace" fill="#555">sk-ant-…</text>
  <rect x="411" y="240" width="150" height="34" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.2" stroke-dasharray="5 3"/>
  <text x="486.0" y="257.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">必要に応じて追加</text>
  <text x="302" y="316" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#555">キーはワークスペースに属し、利用額と上限はワークスペースごとに分けて管理できる</text>
  <text x="302" y="341" text-anchor="middle" font-size="11" fill="#666">図2.1 Claude Consoleの構成</text>
</svg>
  <figcaption>図2.1: Claude Consoleの構成</figcaption>
</figure>

> **NOTE**: Consoleの画面構成やメニューの名前は、改善のために変更されることがあります。本書では執筆時点（2026年11月）の画面をもとに説明します。名前が少し違っていても、次の4つに相当するメニューを探せば同じ操作ができます。「APIキー（API keys）」「請求（Billing）」「ワークスペース（Workspaces）」「利用量（Usage）」です。

### アカウントの作成とクレジットの購入

それでは、実際にConsoleのアカウントを作成しましょう。手順は次のとおりです。

> **STEP 1**: Claude Consoleにアクセスする
> ブラウザで https://platform.claude.com を開き、サインアップ（新規登録）を選びます。メールアドレスか、Googleアカウントなどで登録できます。

> **STEP 2**: メールアドレスを確認する
> 登録したアドレスに確認メールが届くので、メール内のリンクから認証を済ませます。

> **STEP 3**: 組織の情報を入力する
> 初回ログイン時に、組織名や利用目的などを尋ねられます。個人で学ぶ場合は、組織名に自分の名前を入れて構いません。

> **STEP 4**: 支払い方法を登録し、クレジットを購入する
> 請求（Billing）の画面でクレジットカードを登録し、前払いのクレジットを購入します。学習目的なら、最初は少額で十分です。

Claude APIは、基本的にクレジットを前払いで購入し、そこから利用料が差し引かれる仕組みです。残高がなくなるとAPIの呼び出しがエラーになるため、意図しない高額請求が起きにくい構造になっています。請求画面には、残高が少なくなったら自動で買い足す「自動リロード」の設定もあります。学習中は自動リロードをオフにしておくと、使いすぎの心配がさらに減ります。

本書のサンプルコードを最後まで動かしても、使う金額はそれほど大きくありません。第10章の実践プロジェクトのように、複数のエージェントが何度もAPIを呼ぶ場面でも、本書の題材の規模なら数ドル程度に収まる見込みです。ただし、ループの書き間違いで無限に呼び出し続けると、金額は簡単に膨らみます。次の小見出しで扱う「利用上限」は、その保険として必ず設定しておきましょう。

> **WARNING**: クレジットの購入額や最低購入額、税の扱いは、国や時期によって変わることがあります。購入前に、Consoleの請求画面に表示される金額を必ず確認してください。

### APIキーを発行する

**APIキー** とは、「このリクエストは確かにあなたのアカウントから送られたものです」と証明するための、長い文字列の合言葉です。Claude APIにリクエストを送るとき、プログラムはこのキーをヘッダーに付けて送ります。APIの側はキーを見て、どの組織・どのワークスペースのリクエストかを判断し、その組織に料金を請求します。つまりAPIキーは、あなたのクレジットカードにつながった「合鍵」のようなものだと考えてください。

キーの発行は、次の手順で行います。

> **STEP 1**: 学習用のワークスペースを作る（任意・推奨）
> 設定（Settings）のワークスペースの画面で、新しいワークスペースを作ります。名前は `agent-from-scratch` など、用途が分かるものにしておきましょう。

> **STEP 2**: APIキーの画面を開く
> 設定の中にある「API keys」の画面を開き、キーの作成（Create key）を選びます。

> **STEP 3**: キーに名前を付け、ワークスペースを必ず選ぶ
> キーの名前には「どのパソコンで・何に使うか」が分かるものを付けます。たとえば `laptop-book-study` のような名前です。ワークスペースは、STEP 1で作ったもの（作らなかった場合は既定の Default Workspace）を**必ず選んでください**。ワークスペースを選ばずに作ったキーでは、リクエストのたびにワークスペースを指定する必要があります。指定には `anthropic-workspace-id` ヘッダーを使います。本書の手順のままでは400エラーになります。
> 有効期限（Expiration）は学習期間に合わせて選びます（例: 30日）。期限が切れたキーは401エラーになるので、そのときは作り直します。Linked account は自分（自分のアカウント）のままで構いません。

> **STEP 4**: 表示されたキーをコピーする
> 作成が終わると、`sk-ant-` で始まる長い文字列が表示されます。これがAPIキーです。コピーして、次の節で作る `.env` ファイルに貼り付けるまで、一時的に安全な場所に控えておきます。

<figure id="fig-2-2" class="figure-placeholder">
  <div style="width:605px; height:200px; border:2px dashed #ccc; border-radius:8px; display:flex; flex-direction:column; align-items:center; justify-content:center; background:#f9f9f9; color:#999; font-family:sans-serif; font-size:14px;">
    <div style="font-size:32px; margin-bottom:8px;">📷</div>
    <div>図2.2: APIキーの作成画面</div>
    <div style="font-size:12px; margin-top:4px;">スクリーンショット — 入稿待ち</div>
  </div>
  <figcaption>図2.2: APIキーの作成画面（入稿待ち）</figcaption>
</figure>

ここで最も大切なのは、**キーの全体が表示されるのは作成直後の一度だけ** だという点です。画面を閉じてしまうと、Consoleで同じキーの全体をもう一度見ることはできません。一覧画面には、キーの末尾の数文字など、見分けるための一部しか表示されない仕組みになっています。

もしコピーし忘れてしまっても、慌てる必要はありません。そのキーを削除して、新しいキーを作り直せば済みます。キーは必要なときにいつでも新しく発行できるので、「失くしたら作り直す」が正しい運用です。逆に言えば、「どこかに保存しておいたキーを探し回る」よりも、「不要なキーは消して作り直す」ほうが安全です。

> **POINT**: APIキーの命名には、使う場所を含めておくのがおすすめです。万一漏えいしたとき、「どのパソコンの、どのキーを止めればよいか」がすぐに分かります。キーを複数のパソコンや用途で使い回さないことも、被害を小さくするための基本です。

### 利用上限（spend limit）を設定する

APIキーを発行したら、続けて **利用上限（spend limit）** を設定します。利用上限とは、「1か月にこの金額までしか使わない」という上限額のことです。上限に達すると、それ以降のリクエストはエラーで拒否されます。そのため、それ以上の料金は発生しません。ただし、Message Batches API では、わずかに超えることがあります（第11章参照）。Consoleでは、組織全体の上限に加えて、ワークスペースごとにも上限を設けられます。

なぜ、わざわざ上限を設定するのでしょうか。理由は、エージェントが「ループで自動的にAPIを呼び出すプログラム」だからです。前章で学んだとおり、エージェントは結果を観察しながら何度もLLMを呼び出します。もしループの終了条件を書き間違えると、プログラムは人間が気づくまでAPIを呼び続けます。チャットなら人間が入力しない限り何も起きませんが、エージェントは人間が寝ている間にも動き続けられるのです。

> **STEP 1**: 組織全体の上限を確認する
> 設定の中にある請求（Billing）の画面を開き、利用上限（Spend limits）の欄で組織全体の月額上限を確認・設定します。

> **STEP 2**: 学習用ワークスペースに上限を設ける
> 学習用のワークスペースを作った場合は、ワークスペース（Workspaces）の画面でそのワークスペースを選びます。そして、利用上限（Spend limits）から月額の上限を設定します。学習目的なら、10ドル程度でも十分に足ります。なお、最初からある既定のワークスペース（Default Workspace）には上限を設定できません。

> **STEP 3**: 通知の設定を確認する
> 利用額が一定の割合に達したときにメールで知らせる設定があれば、あわせて有効にしておきます。

<figure id="fig-2-3" class="figure-placeholder">
  <div style="width:605px; height:200px; border:2px dashed #ccc; border-radius:8px; display:flex; flex-direction:column; align-items:center; justify-content:center; background:#f9f9f9; color:#999; font-family:sans-serif; font-size:14px;">
    <div style="font-size:32px; margin-bottom:8px;">📷</div>
    <div>図2.3: 利用上限の設定画面</div>
    <div style="font-size:12px; margin-top:4px;">スクリーンショット — 入稿待ち</div>
  </div>
  <figcaption>図2.3: 利用上限の設定画面（入稿待ち）</figcaption>
</figure>

利用状況は、利用量（Usage）やコスト（Cost）の画面で確認できます。日ごと・モデルごと・APIキーごとに、使ったトークン数や金額がグラフで表示されます。本章の最後に最初のリクエストを送ったら、ぜひこの画面を開いてみてください。自分のリクエストがグラフに反映される様子を見ると、「APIを呼ぶとお金がかかる」という感覚が具体的になります。なお、画面への反映には少し時間がかかることがあります。

> **NOTE**: 組織には、利用実績などに応じて自動で決まる「利用ティア（Usage tier）」があります。ティアごとに、設定できる上限額の最大値や、レート制限が決まっています。レート制限とは、一定時間あたりに送れるリクエスト数やトークン数の上限のことです。アカウントを作ったばかりの段階ではレート制限が低めに設定されていますが、本書の学習には十分な水準です。レート制限については第4章で詳しく扱います。

### 料金の考え方：入力トークンと出力トークン

Claude APIの料金は、**トークン（token）** という単位で計算されます。トークンとは、LLMが文章を処理するときの最小単位で、英語ならおおむね単語の一部、日本語ならおおむね1文字前後に相当します。前章で、コンテキストウィンドウの大きさをトークンで数えると説明しました。料金も同じトークンという物差しで測られるわけです。

料金は「入力トークン」と「出力トークン」に分けて計算されます。入力トークンは、こちらから送った文章（会話履歴やsystem プロンプト、ツールの定義など）の量です。出力トークンは、Claudeが生成した文章の量です。出力トークンのほうが単価が高く設定されている点が特徴です。

本書で使う3つのモデルの単価は、次のとおりです（100万トークンあたりの米ドル。執筆時点）。

| 用途 | モデルID | 入力 | 出力 |
|---|---|---|---|
| 既定（メインのエージェント） | `claude-opus-5-5` | $4 | $20 |
| 中間 | `claude-sonnet-5-5` | $2 | $10 |
| 低コストのワーカー・分類 | `claude-haiku-5-5` | $0.10 | $0.50 |

※ `claude-haiku-5-5` の単価は、1回のリクエストの入力が10万トークン以下の場合です。超えると入力0.50ドル・出力2.50ドルになります。

具体的に計算してみましょう。本章の最後に送るリクエストは、入力がおよそ30トークン、出力がおよそ150トークンになる見込みです。`claude-opus-5-5` の場合、入力は 30 ÷ 1,000,000 × 4 = 0.00012ドルです。出力は 150 ÷ 1,000,000 × 20 = 0.003ドルです。合計でも0.0031ドル程度で、日本円にすると1円にも届きません。

ところが、エージェントになると話が変わります。エージェントは、会話履歴とツールの実行結果を毎回すべて送り直すため、ループが進むほど入力トークンが積み上がっていきます。たとえば1回あたり5万トークンの入力を20回繰り返すと、入力だけで100万トークン、つまり4ドルになります。1回の呼び出しは安くても、ループと履歴の積み重ねによって費用が膨らむ点が、エージェント開発ならではの注意点です。

> **POINT**: Claude Opus 5.5は、回答の前に内部で考える「思考（thinking）」を自動的に行います。この思考に使われたトークンも、出力トークンとして課金されます。レスポンスに含まれる `usage` の値を見れば、実際に課金されたトークン数が分かります。

ここまでで、APIキーと利用上限という「APIを使うための鍵と安全装置」が手元にそろいました。次の節では、このキーを使うPythonの開発環境を作っていきます。

---

## 2.2 uvとVS CodeでPython環境を作る

APIキーが手に入ったら、次はそれを使うプログラムを書く環境です。Pythonでの開発を始めるとき、多くの人が最初につまずくのが「環境づくり」です。Python本体のバージョンが合わない。ライブラリを入れたはずなのに見つからない。別のプロジェクトのライブラリと衝突する。こうした経験がある方も多いのではないでしょうか。本節では、これらの悩みをまとめて解決してくれる **uv** というツールを使って、本書のプロジェクトを作ります。

### uvとは何か

**uv** は、Pythonのプロジェクトを管理するためのツールです。Astral（アストラル）という会社が開発しており、Rust（ラスト）という言語で書かれているため、動作が非常に高速です。uvひとつで、次の3つの仕事をまとめて引き受けてくれます。

- **Python本体の管理**: 必要なバージョンのPythonを自動でダウンロードし、プロジェクトごとに使い分ける
- **仮想環境の管理**: プロジェクト専用のライブラリ置き場（仮想環境）を自動で作る
- **依存関係の管理**: どのライブラリのどのバージョンを使うかを記録し、別のパソコンでも同じ環境を再現する

従来は、これらの仕事を別々のツールで行うのが一般的でした。Python本体はpyenv（パイエンブ）、仮想環境はvenv（ブイエンブ）、ライブラリのインストールはpip（ピップ）、という具合です。それぞれのツールには独自の使い方があります。そのため、組み合わせ方を間違えると「どのPythonで、どのライブラリが入っているのか」が分からなくなりがちでした。uvは、これらをひとつのコマンド体系にまとめることで、そうした混乱をなくしてくれます。

ここで、**仮想環境** という言葉を補足しておきましょう。仮想環境とは、プロジェクトごとに用意される、独立したライブラリ置き場のことです。たとえば、プロジェクトAではhttpxのバージョン0.27を、プロジェクトBではバージョン0.28を使いたい場面があるとします。パソコン全体で1か所にライブラリを入れていると、どちらか一方しか置けません。仮想環境を使えば、プロジェクトごとに別々の置き場を持てるので、こうした衝突が起きなくなります。

本書がuvを選んだ理由は、手順の短さにあります。本書のプロジェクトでは、`uv init` でプロジェクトを作り、`uv add` でライブラリを加えます。そして `uv run` で実行します。覚えるコマンドは実質この3つだけです。仮想環境の「有効化（activate）」という、初学者がつまずきやすい手順も、`uv run` を使えば意識する必要がありません。環境づくりで消耗せず、エージェントの中身に集中できるようにするための選択です。

### uvをインストールする

uvのインストール方法は、OSによって異なります。公式に案内されているインストールスクリプトを使うのが、最も手軽で確実です。

Windowsの場合は、PowerShell（パワーシェル）を開いて次のコマンドを実行します。スタートメニューで「PowerShell」と検索すれば起動できます。

```powershell
# Windows（PowerShell）: 公式のインストールスクリプトでuvを入れる
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

macOSやLinuxの場合は、ターミナルを開いて次のコマンドを実行します。

```bash
# macOS / Linux（ターミナル）: 公式のインストールスクリプトでuvを入れる
curl -LsSf https://astral.sh/uv/install.sh | sh
```

パッケージ管理ツールを普段から使っている方は、そちらからインストールしても構いません。

```bash
# macOS（Homebrewを使う場合）
brew install uv

# Windows（WinGetを使う場合。PowerShellで実行）
winget install --id=astral-sh.uv -e
```

Windows向けのコマンドには `-ExecutionPolicy ByPass` という指定があります。これは「このコマンドの実行中だけ、スクリプトの実行制限を緩める」という意味です。Windowsは、インターネットから取得したスクリプトを勝手に実行しないよう、初期状態で制限をかけています。この指定は、その制限を今回の1回だけ外すためのものです。パソコン全体の設定を変えるわけではないので、安心して実行してください。

インストールが終わったら、**ターミナルを一度閉じて、開き直してください**。インストールスクリプトは、uvの置き場所を環境変数PATH（パス）に追加します。PATHとは、コマンド名から実行ファイルを探すための「住所録」のようなものです。すでに開いているターミナルは古い住所録を持ったままなので、開き直さないとuvを見つけられません。

開き直したら、次のコマンドでuvが使えることを確認します。

```bash
# uvのバージョンを表示して、インストールを確認する（全OS共通）
uv --version
```

次のように、`uv` に続けてバージョン番号が表示されれば成功です。数字の部分は、インストールした時期によって異なります。

```text
uv 0.13.5
```

> **WARNING**: `uv` が「認識されません」「command not found」と表示されることがあります。その場合は、まずターミナルを開き直したかを確認してください。それでも解決しない場合は、パソコンを再起動するとPATHの変更が確実に反映されます。会社のパソコンでは、スクリプトの実行が組織のポリシーで禁止されている場合があります。その場合は、情報システム部門に相談するか、WinGetなど許可されている方法を使いましょう。

### Python 3.12を用意する

本書のコードは、Python 3.12で動作を確認しています。uvを使えば、Python本体もuv経由で用意できます。すでにPythonをインストールしている方も、プロジェクトごとにバージョンを固定するために、次のコマンドを実行しておくと安心です。

```bash
# uvでPython 3.12をダウンロードして、uvの管理下に置く（全OS共通）
uv python install 3.12

# uvが認識しているPythonの一覧を表示する
uv python list
```

`uv python install` は、uvの管理用フォルダーにPython 3.12をダウンロードします。パソコンにもともと入っているPythonを上書きしたり、削除したりすることはありません。`uv python list` を実行すると、uvが使えるPythonの一覧が表示されます。その中に `cpython-3.12` で始まる行があり、インストール済みであることが示されていれば準備完了です。

### プロジェクトを作る：uv init

いよいよ、本書全体で育てていくプロジェクトを作ります。プロジェクト名は `agent-from-scratch` です。第3章以降のすべてのコードは、このフォルダーの中に作っていきます。まず、プロジェクトを置きたい場所にターミナルで移動してください。たとえば、ホームフォルダーの下の `projects` フォルダーなどです。移動したら、次のコマンドを実行してください。

```bash
# プロジェクトを作成し、作成したフォルダーに移動する（全OS共通）
uv init agent-from-scratch --python 3.12 --no-package
cd agent-from-scratch
```

`uv init` は、新しいプロジェクトの雛形を作るコマンドです。`--python 3.12` は、このプロジェクトでPython 3.12を使うという指定です。`--no-package` は、配布用のパッケージ構成（`src` フォルダー）にせず、スクリプトを直接置く平らな構成にする指定です。新しいuvは何も指定しないとパッケージ構成で作り、`main.py` も作られないため、本書では必ず付けてください。実行すると、`agent-from-scratch` という名前のフォルダーが作られ、その中にいくつかのファイルが用意されます。`cd` は、そのフォルダーに移動するためのコマンドです。

作られたファイルを確認してみましょう。

```bash
# フォルダーの中身を、隠しファイルも含めて一覧表示する（macOS / Linux / Git Bash）
ls -a
```

```powershell
# フォルダーの中身を、隠しファイルも含めて一覧表示する（PowerShell）
Get-ChildItem -Force
```

おおむね次のようなファイルが並んでいるはずです。

```text
.git/            # Gitのリポジトリ（Gitがインストールされている場合のみ）
.gitignore       # Gitで管理しないファイルの一覧
.python-version  # このプロジェクトで使うPythonのバージョン
README.md        # プロジェクトの説明書き
main.py          # 動作確認用のサンプルスクリプト
pyproject.toml   # プロジェクトの設定と依存ライブラリの一覧
```

`.git` フォルダーと `.gitignore` ファイルにも注目してください。パソコンにGit（ギット）がインストールされていると、`uv init` はプロジェクトのフォルダーを自動的に初期化します。Gitのリポジトリとして使える状態にするわけです。Gitは、ファイルの変更履歴を管理するためのツールです。次の節でAPIキーの漏えいを防ぐ設定をするときに、このGitの仕組みが関わってきます。

> **NOTE**: Gitがまだ入っていない方は、この機会にインストールしておくことをおすすめします。Windowsなら、Git for Windows（https://git-scm.com）を入れましょう。Git本体と一緒に、**Git Bash（ギット・バッシュ）** というターミナルも使えるようになります。Git Bashでは、macOSやLinuxと同じ書き方のコマンドが使えるので、本書のbash向けの手順をそのまま試せます。macOSでは、ターミナルで `git --version` を実行すると、必要に応じてインストールを案内してくれます。

`uv init` を実行した時点では、まだ仮想環境（`.venv` フォルダー）は作られていません。仮想環境は、次に説明する `uv add` や `uv run` を最初に実行したときに、自動で作られます。「必要になった時点で、必要なものを用意する」というのがuvの基本的な考え方です。

### ライブラリを追加する：uv add

本書のコードで使う外部ライブラリは、たった2つです。1つは、HTTPのリクエストを送るための **httpx** です。もう1つは、`.env` ファイルから設定を読み込むための **python-dotenv（パイソン・ドットエンブ）** です。プロジェクトのフォルダーの中で、次のコマンドを実行します。

```bash
# httpxとpython-dotenvをプロジェクトの依存ライブラリとして追加する（全OS共通）
uv add httpx python-dotenv
```

実行すると、次のような出力が表示されます。バージョン番号や、一緒にインストールされるライブラリの数は、実行する時期によって異なります。

```text
Using CPython 3.12.x
Creating virtual environment at: .venv
Resolved 9 packages in 120ms
Prepared 8 packages in 300ms
Installed 8 packages in 25ms
 + anyio==4.x.x
 + certifi==2026.x.x
 + h11==0.x.x
 + httpcore==1.x.x
 + httpx==0.28.x
 + idna==3.x
 + python-dotenv==1.x.x
 + typing-extensions==4.x.x
```

この出力からは、uvが裏側で行ったことが読み取れます。1行目は、Python 3.12を使うことを示しています。2行目は、仮想環境 `.venv` を作ったことを示しています。「Resolved」は、必要なライブラリとそのバージョンの組み合わせを決めたことを意味します。「Installed」は、それらを仮想環境にインストールしたことを意味します。

`uv add` は、ライブラリをインストールするだけではありません。`pyproject.toml` に「このプロジェクトはこのライブラリを使う」と書き込みます。ここが、従来の `pip install` との大きな違いです。`pip install` はライブラリを入れるだけで、記録は残しません。そのため、あとから「このプロジェクトに何が必要だったか」が分からなくなることがよくありました。

### pyproject.tomlとuv.lockの役割

`uv add` を実行したあとの `pyproject.toml` を開いてみましょう。次のような内容になっているはずです。

```toml
# pyproject.toml（uv init と uv add によって自動生成された内容）
[project]
name = "agent-from-scratch"            # プロジェクト名
version = "0.1.0"                      # プロジェクトのバージョン
description = "Add your description here"  # 説明文（自由に書き換えてよい）
readme = "README.md"                   # 説明書きのファイル
requires-python = ">=3.12"             # 必要なPythonのバージョン
dependencies = [                       # 依存ライブラリの一覧（uv add で追記される）
    "httpx>=0.28.1",
    "python-dotenv>=1.2.1",
]
```

`pyproject.toml` は、TOML（トムル）という形式で書かれたプロジェクトの設定ファイルです。Pythonの世界で標準的に使われている形式で、uv以外のツールも読むことができます。`dependencies` の欄に、さきほど追加した2つのライブラリが書き込まれていることを確認してください。`>=0.28.1` は「0.28.1以上のバージョン」という意味で、実際の数字は追加した時期によって変わります。なお、上の例の行末コメントは説明のために筆者が加えたもので、実際のファイルには書かれていません。

フォルダーの中には、もう1つ `uv.lock` というファイルも作られています。こちらは、**実際にインストールされたすべてのライブラリの、正確なバージョン** を記録したファイルです。httpxの依存ライブラリであるanyioやhttpcoreのバージョンまで、すべてが固定されて書き込まれています。中身は長く複雑ですが、uvが自動で管理するので、人間が手で編集することはありません。

この2つのファイルの関係は、料理にたとえると分かりやすいかもしれません。`pyproject.toml` は「カレーにはジャガイモとニンジンを使う」という **レシピ** です。`uv.lock` は「このときは、この産地の、この重さのジャガイモを使った」という **調達記録** です。レシピだけでもカレーは作れますが、調達記録があれば、まったく同じ味を再現できます。

<figure id="fig-2-4">
<svg width="605" height="380" viewBox="0 0 605 380"
     xmlns="http://www.w3.org/2000/svg"
     font-family="'Noto Sans JP',sans-serif">
  <defs>
    <marker id="f2_4_arrow" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#333" stroke-width="1.5"/>
    </marker>
    <marker id="f2_4_arrowA" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#2b6cb0" stroke-width="1.5"/>
    </marker>
  </defs>
  <rect x="0" y="0" width="605" height="380" fill="#ffffff"/>
  <rect x="20" y="20" width="270" height="300" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.2"/>
  <text x="32" y="40" text-anchor="start" dominant-baseline="central" font-size="13" font-family="Consolas,monospace" fill="#1a1a1a" font-weight="bold">agent-from-scratch/</text>
  <text x="40" y="66" text-anchor="start" dominant-baseline="central" font-size="12" font-family="Consolas,monospace" fill="#1a1a1a">├─ .git/</text>
  <text x="40" y="96" text-anchor="start" dominant-baseline="central" font-size="12" font-family="Consolas,monospace" fill="#1a1a1a">├─ .gitignore</text>
  <text x="40" y="126" text-anchor="start" dominant-baseline="central" font-size="12" font-family="Consolas,monospace" fill="#1a1a1a">├─ .python-version</text>
  <text x="40" y="156" text-anchor="start" dominant-baseline="central" font-size="12" font-family="Consolas,monospace" fill="#1a1a1a">├─ README.md</text>
  <text x="40" y="186" text-anchor="start" dominant-baseline="central" font-size="12" font-family="Consolas,monospace" fill="#1a1a1a">├─ main.py</text>
  <text x="40" y="216" text-anchor="start" dominant-baseline="central" font-size="12" font-family="Consolas,monospace" fill="#2b6cb0" font-weight="bold">├─ pyproject.toml</text>
  <text x="40" y="246" text-anchor="start" dominant-baseline="central" font-size="12" font-family="Consolas,monospace" fill="#2b6cb0" font-weight="bold">├─ uv.lock</text>
  <text x="40" y="276" text-anchor="start" dominant-baseline="central" font-size="12" font-family="Consolas,monospace" fill="#2b6cb0" font-weight="bold">└─ .venv/</text>
  <path d="M200 56 L210 56 L210 226 L200 226" fill="none" stroke="#333" stroke-width="1.2"/>
  <text x="218" y="134" text-anchor="start" dominant-baseline="central" font-size="11" font-family="Consolas,monospace" fill="#1a1a1a">uv init</text>
  <text x="218" y="150" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">で作成</text>
  <path d="M200 232 L210 232 L210 286 L200 286" fill="none" stroke="#2b6cb0" stroke-width="1.2"/>
  <text x="218" y="252" text-anchor="start" dominant-baseline="central" font-size="11" font-family="Consolas,monospace" fill="#2b6cb0">uv add</text>
  <text x="218" y="268" text-anchor="start" dominant-baseline="central" font-size="11" fill="#2b6cb0">で作成</text>
  <rect x="320" y="30" width="265" height="58" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="452.5" y="43.0" text-anchor="middle" dominant-baseline="central" font-size="12" font-family="Consolas,monospace" fill="#1a1a1a" font-weight="bold">pyproject.toml</text>
  <text x="452.5" y="59.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">使うライブラリの一覧（レシピ）</text>
  <text x="452.5" y="75.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">uv add が dependencies に追記</text>
  <path d="M360 88 L360 118" fill="none" stroke="#2b6cb0" stroke-width="1.3" marker-end="url(#f2_4_arrowA)"/>
  <text x="370" y="103" text-anchor="start" dominant-baseline="central" font-size="11" fill="#2b6cb0">uv add が解決して記録</text>
  <rect x="320" y="118" width="265" height="58" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="452.5" y="131.0" text-anchor="middle" dominant-baseline="central" font-size="12" font-family="Consolas,monospace" fill="#1a1a1a" font-weight="bold">uv.lock</text>
  <text x="452.5" y="147.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">全ライブラリの正確なバージョン</text>
  <text x="452.5" y="163.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">（調達記録・手で編集しない）</text>
  <path d="M360 176 L360 206" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f2_4_arrow)"/>
  <text x="370" y="191" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">uv sync / uv run で作る</text>
  <rect x="320" y="206" width="265" height="58" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="452.5" y="219.0" text-anchor="middle" dominant-baseline="central" font-size="12" font-family="Consolas,monospace" fill="#1a1a1a" font-weight="bold">.venv/</text>
  <text x="452.5" y="235.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">仮想環境（httpx・python-dotenv など）</text>
  <text x="452.5" y="251.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">いつでも uv.lock から作り直せる</text>
  <rect x="320" y="272" width="130" height="48" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.2"/>
  <text x="385.0" y="282.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-weight="bold">Git で管理する</text>
  <text x="385.0" y="296.0" text-anchor="middle" dominant-baseline="central" font-size="11" font-family="Consolas,monospace" fill="#1a1a1a">pyproject.toml</text>
  <text x="385.0" y="310.0" text-anchor="middle" dominant-baseline="central" font-size="11" font-family="Consolas,monospace" fill="#1a1a1a">uv.lock</text>
  <rect x="455" y="272" width="130" height="48" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.2"/>
  <text x="520.0" y="282.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-weight="bold">Git で管理しない</text>
  <text x="520.0" y="296.0" text-anchor="middle" dominant-baseline="central" font-size="11" font-family="Consolas,monospace" fill="#1a1a1a">.venv/</text>
  <text x="520.0" y="310.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">（.gitignore 済み）</text>
  <text x="20" y="346" text-anchor="start" dominant-baseline="central" font-size="11" fill="#555">※ .git/ は Git がインストールされている場合のみ作られる</text>
  <text x="302" y="366" text-anchor="middle" font-size="11" fill="#666">図2.4 agent-from-scratchの初期構成</text>
</svg>
  <figcaption>図2.4: agent-from-scratchの初期構成</figcaption>
</figure>

この仕組みは、別のパソコンで同じ環境を作り直すときに力を発揮します。`pyproject.toml` と `uv.lock` を別のパソコンにコピーして、`uv sync` を実行します。すると、まったく同じバージョンのライブラリがそろった仮想環境ができあがります。チームで開発するときや、パソコンを買い替えたときに、「自分の環境では動いたのに」という問題を防げるわけです。逆に、`.venv` フォルダーそのものはコピーする必要がありません。いつでも `uv.lock` から作り直せるからです。

> **POINT**: `pyproject.toml` と `uv.lock` は、Gitで管理する（コミットする）ファイルです。`.venv` は管理しないファイルです。`uv init` が作る `.gitignore` には、最初から `.venv` が含まれています。

### uv runでスクリプトを実行する

環境が整ったら、`uv init` が用意してくれたサンプルの `main.py` を実行してみましょう。

```bash
# 仮想環境のPythonでmain.pyを実行する（全OS共通）
uv run main.py
```

次のように表示されれば、プロジェクトの環境は正しく動いています。

```text
Hello from agent-from-scratch!
```

`uv run` は、「このプロジェクトの仮想環境のPythonで、指定したスクリプトを実行する」コマンドです。実行の直前には、`pyproject.toml` と `uv.lock`、そして `.venv` の中身が一致しているかを確認します。ずれていれば、自動で同期してくれます。そのため、ライブラリを追加した直後でも、何も意識せずに最新の状態で実行できます。

従来の方法では、スクリプトを実行する前に、仮想環境を「有効化」する手順が必要でした。Windowsなら `.venv\Scripts\activate` といったコマンドです。macOSなら `source .venv/bin/activate` を使います。この手順を忘れると、パソコン全体のPythonで実行されてしまい、「httpxが見つからない」というエラーに悩まされることになります。`uv run` を使えば、この有効化の手順そのものが不要になります。

ライブラリが正しく入ったかどうかも、この1行コマンドで確かめておきましょう。

```bash
# httpxとpython-dotenvが読み込めるか確認し、httpxのバージョンを表示する（全OS共通）
uv run python -c "import httpx, dotenv; print('httpx', httpx.__version__)"
```

`httpx 0.28.1` のようにバージョンが表示されれば、2つのライブラリはどちらも問題なく読み込めています。`ModuleNotFoundError` と表示される場合は、フォルダーを確認してください。`uv add` を実行したフォルダーと、いまいるフォルダーが同じかどうかです。外側を二重引用符、内側を一重引用符で書いているのは、PowerShellでもbashでも同じように動かすための工夫です。

### VS Codeを準備する

コードを書くためのエディタには、**VS Code（Visual Studio Code）** を使います。VS Codeは、Microsoftが無料で提供しているコードエディタで、Windows・macOS・Linuxのいずれでも動きます。拡張機能を入れることで、Pythonのコード補完やエラー表示、デバッグなどが使えるようになります。

まだインストールしていない方は、公式サイト（https://code.visualstudio.com）を開いてください。そこから、自分のOS向けのインストーラーをダウンロードして実行します。Windowsのインストーラーでは、途中の「追加タスクの選択」の画面で「PATHへの追加」にチェックが入っていることを確認しておきましょう。これにより、ターミナルから `code` コマンドでVS Codeを起動できるようになります。macOSでも、VS Codeのコマンドパレットから同じことができます。「Shell Command: Install 'code' command in PATH」を実行してください。

VS Codeを起動したら、次の手順でPythonの開発環境を整えます。

> **STEP 1**: Python拡張機能をインストールする
> 左側のアクティビティバーにある拡張機能のアイコン（四角が4つ並んだ形）をクリックし、検索欄に「Python」と入力します。発行元がMicrosoftの「Python」拡張機能をインストールします。コード補完のPylance（パイランス）なども、一緒にインストールされます。

> **STEP 2**: プロジェクトのフォルダーを開く
> メニューの「ファイル」→「フォルダーを開く」から、`agent-from-scratch` フォルダーを選びます。ターミナルでプロジェクトのフォルダーにいるなら、`code .` と入力しても開けます。「このフォルダー内のファイルの作成者を信頼しますか？」と尋ねられたら、自分で作ったフォルダーなので「信頼する」を選びます。

> **STEP 3**: インタープリターに .venv を選ぶ
> `Ctrl+Shift+P`（macOSは `Cmd+Shift+P`）でコマンドパレットを開きます。そこで「Python: Select Interpreter」（Python: インタープリターを選択）を実行します。一覧から、`.venv` の中のPythonを選びます。

STEP 3で選ぶ **インタープリター** とは、Pythonのコードを読んで実行するプログラム、つまりPython本体のことです。VS Codeは、ここで選んだPythonを使って、コードの補完やエラーのチェックを行います。一覧に表示される `.venv` のPythonの場所は、Windowsでは `.venv\Scripts\python.exe` です。macOSやLinuxでは `.venv/bin/python` です。多くの場合、VS Codeが `.venv` を自動で見つけて「推奨」と表示してくれます。

<figure id="fig-2-5" class="figure-placeholder">
  <div style="width:605px; height:200px; border:2px dashed #ccc; border-radius:8px; display:flex; flex-direction:column; align-items:center; justify-content:center; background:#f9f9f9; color:#999; font-family:sans-serif; font-size:14px;">
    <div style="font-size:32px; margin-bottom:8px;">📷</div>
    <div>図2.5: VS Codeのインタープリター選択</div>
    <div style="font-size:12px; margin-top:4px;">スクリーンショット — 入稿待ち</div>
  </div>
  <figcaption>図2.5: VS Codeのインタープリター選択（入稿待ち）</figcaption>
</figure>

なぜインタープリターの選択が大切なのでしょうか。もし、パソコン全体のPythonが選ばれたままだと、VS Codeは「httpxというライブラリは見つかりません」と判断します。その結果、`import httpx` の行に波線の警告が表示され、コード補完も効かなくなります。コード自体は `uv run` で正しく動くのに、エディタだけがエラーを表示するという、紛らわしい状態になってしまうのです。

正しく設定できたかは、VS Codeの画面右下のステータスバーで確認できます。Pythonのバージョンの横に `.venv` や `agent-from-scratch` といった表示があるかを見てください。あれば、プロジェクトの仮想環境が選ばれています。また、VS Codeの統合ターミナルを新しく開くと、Python拡張機能が自動的に仮想環境を有効化してくれることもあります。統合ターミナルは `` Ctrl+` ``（日本語キーボードでは `` Ctrl+@ ``）で開けます。ただし本書では、どの状態でも同じ結果になるよう、実行には常に `uv run` を使います。

> **NOTE**: 本書では、コマンドの実行にVS Codeの統合ターミナルを使うことをおすすめします。エディタでファイルを編集し、すぐ下のターミナルで `uv run` を実行する、という流れが1つの画面で完結するからです。Windowsの統合ターミナルは、初期状態ではPowerShellが開きます。右上の「＋」の横にある下向き矢印から、Git Bashに切り替えることもできます。

### つまずきやすいポイント

本節の作業で、よく見られるつまずきと対処法をまとめておきます。

**`uv init` で「already exists」と表示される** 場合は、同じ名前のフォルダーがすでにあります。以前に途中まで作業したフォルダーが残っているのかもしれません。中身が不要なら削除してから、やり直してください。

**`uv add` が「Failed to download」などで失敗する** 場合は、ネットワークの問題が考えられます。会社のネットワークでは、プロキシ（中継サーバー）を経由しないと外部に接続できないことがあります。その場合は、環境変数 `HTTPS_PROXY` にプロキシのアドレスを設定してから再実行します。設定値は、社内の情報システム部門に確認してください。

**VS Codeで `import httpx` に波線が表示される** 場合は、インタープリターの選択を確認します。STEP 3の手順で、`.venv` のPythonを選び直してください。それでも直らない場合は、VS Codeの画面を再読み込みします。コマンドパレットから「Developer: Reload Window」を実行してください。

**`uv run main.py` で「No such file」と表示される** 場合は、ターミナルの現在位置を疑います。プロジェクトのフォルダーではない可能性があります。`pwd`（PowerShellでは `Get-Location`）で現在位置を確認してください。そして、`agent-from-scratch` フォルダーに移動してから実行します。本書のコマンドは、すべてプロジェクトのフォルダーの中で実行することを前提にしています。

**OneDriveなどの同期フォルダーの中にプロジェクトを作った** 場合は、`.venv` の中の大量の小さなファイルが同期の対象になります。その結果、動作が遅くなったり、ファイルがロックされてエラーになったりすることがあります。Windowsでは、ドキュメントフォルダーやデスクトップがOneDriveと同期されている場合があるので注意してください。`C:\dev` のような、同期の対象外のフォルダーにプロジェクトを置くと安全です。

これで、Pythonのコードを書いて実行できる環境が整いました。次の節では、2.1節で発行したAPIキーを、この環境から安全に使うための設定を行います。

---

## 2.3 APIキーを安全に管理する

APIキーは、プログラムがClaude APIを呼ぶたびに必要になります。いちばん手っ取り早いのは、キーの文字列をコードに直接書く方法でしょう。しかし、それは「家の合鍵を玄関のドアに貼り付けておく」ようなものです。本節では、キーをコードから切り離して保管し、うっかり公開する事故を防ぐ仕組みを整えます。

### なぜキーをコードに書いてはいけないのか

コードにキーを書くと、そのコードを共有した瞬間に、キーも一緒に共有されます。たとえば、学習の記録としてGitHub（ギットハブ）の公開リポジトリにコードを置いたとします。公開リポジトリから各種サービスのキーを自動で探し出すプログラムは、常に動いていると考えてください。キーが第三者に渡れば、その利用料はあなたに請求されます。

もう1つの理由は、差し替えやすさです。キーがコードの外の1か所にまとまっていれば、キーを作り直したときの変更もその1か所で済みます。ファイルが増えていく後の章ほど、この利点が効いてきます。

### .envファイルと環境変数

コードの外にキーを置く場所として使うのが **環境変数** です。環境変数とは、OSやターミナルが持つ「名前と値の組」の一覧で、そこから起動したプログラムが値を読み取れます。Pythonでは `os.environ["名前"]` の形で読み取ります。ただ、毎回ターミナルで設定するのは面倒です。そこで、**`.env`（ドットエンブ）ファイル** に書いておきます。それを、python-dotenvの `load_dotenv()` で環境変数に読み込みます。

VS Codeで、プロジェクトのフォルダー直下に `.env` というファイルを作り、次のように書いてください。

```text
# .env（プロジェクトのフォルダー直下に置く。絶対にGitにコミットしない）
ANTHROPIC_API_KEY=sk-ant-ここに自分のAPIキーを貼り付ける
```

`=` の前後にスペースは入れず、値を引用符で囲む必要もありません。Windowsのメモ帳で作ると `.env.txt` になってしまうことがあるので、VS Codeで作成するのが確実です。変数名の `ANTHROPIC_API_KEY` は、本書の全章で共通して使う名前です。

<figure id="fig-2-6">
<svg width="605" height="430" viewBox="0 0 605 430"
     xmlns="http://www.w3.org/2000/svg"
     font-family="'Noto Sans JP',sans-serif">
  <defs>
    <marker id="f2_6_arrow" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#333" stroke-width="1.5"/>
    </marker>
    <marker id="f2_6_arrowA" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#2b6cb0" stroke-width="1.5"/>
    </marker>
  </defs>
  <rect x="0" y="0" width="605" height="430" fill="#ffffff"/>
  <rect x="40" y="20" width="300" height="50" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="190.0" y="36.5" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a" font-weight="bold">Claude Console</text>
  <text x="190.0" y="53.5" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">APIキーを発行（sk-ant-…）</text>
  <path d="M345 45 L360 45" fill="none" stroke="#999" stroke-width="1.0" stroke-dasharray="4 3"/>
  <text x="366" y="45" text-anchor="start" dominant-baseline="central" font-size="11" fill="#555">作成直後に一度だけ全体が表示される</text>
  <path d="M190 70 L190 96" fill="none" stroke="#2b6cb0" stroke-width="1.3" marker-end="url(#f2_6_arrowA)"/>
  <text x="200" y="83" text-anchor="start" dominant-baseline="central" font-size="11" fill="#2b6cb0">コピーして貼り付け</text>
  <rect x="40" y="96" width="300" height="50" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="190.0" y="112.5" text-anchor="middle" dominant-baseline="central" font-size="12" font-family="Consolas,monospace" fill="#1a1a1a" font-weight="bold">.env ファイル</text>
  <text x="190.0" y="129.5" text-anchor="middle" dominant-baseline="central" font-size="11" font-family="Consolas,monospace" fill="#1a1a1a">ANTHROPIC_API_KEY=sk-ant-…</text>
  <path d="M345 121 L360 121" fill="none" stroke="#999" stroke-width="1.0" stroke-dasharray="4 3"/>
  <text x="366" y="121" text-anchor="start" dominant-baseline="central" font-size="11" fill="#555">.gitignore で Git から除外する</text>
  <path d="M190 146 L190 172" fill="none" stroke="#2b6cb0" stroke-width="1.3" marker-end="url(#f2_6_arrowA)"/>
  <text x="200" y="159" text-anchor="start" dominant-baseline="central" font-size="11" fill="#2b6cb0">load_dotenv() で読み込む</text>
  <rect x="40" y="172" width="300" height="50" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="190.0" y="188.5" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a" font-weight="bold">環境変数</text>
  <text x="190.0" y="205.5" text-anchor="middle" dominant-baseline="central" font-size="11" font-family="Consolas,monospace" fill="#1a1a1a">os.environ["ANTHROPIC_API_KEY"]</text>
  <path d="M345 197 L360 197" fill="none" stroke="#999" stroke-width="1.0" stroke-dasharray="4 3"/>
  <text x="366" y="197" text-anchor="start" dominant-baseline="central" font-size="11" fill="#555">キー本体はコードに書かない</text>
  <path d="M190 222 L190 248" fill="none" stroke="#2b6cb0" stroke-width="1.3" marker-end="url(#f2_6_arrowA)"/>
  <text x="200" y="235" text-anchor="start" dominant-baseline="central" font-size="11" fill="#2b6cb0">os.environ で取り出す</text>
  <rect x="40" y="248" width="300" height="50" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="190.0" y="264.5" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a" font-weight="bold">リクエストのヘッダー</text>
  <text x="190.0" y="281.5" text-anchor="middle" dominant-baseline="central" font-size="11" font-family="Consolas,monospace" fill="#1a1a1a">x-api-key: &lt;キー&gt;</text>
  <path d="M345 273 L360 273" fill="none" stroke="#999" stroke-width="1.0" stroke-dasharray="4 3"/>
  <text x="366" y="273" text-anchor="start" dominant-baseline="central" font-size="11" fill="#555">httpx.post(headers=...) で付ける</text>
  <path d="M190 298 L190 324" fill="none" stroke="#2b6cb0" stroke-width="1.3" marker-end="url(#f2_6_arrowA)"/>
  <text x="200" y="311" text-anchor="start" dominant-baseline="central" font-size="11" fill="#2b6cb0">HTTPS で送信</text>
  <rect x="40" y="324" width="300" height="50" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="190.0" y="340.5" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a" font-weight="bold">Claude API</text>
  <text x="190.0" y="357.5" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">キーから組織・ワークスペースを判別</text>
  <path d="M345 349 L360 349" fill="none" stroke="#999" stroke-width="1.0" stroke-dasharray="4 3"/>
  <text x="366" y="349" text-anchor="start" dominant-baseline="central" font-size="11" fill="#555">その組織に利用料を請求する</text>
  <text x="302" y="416" text-anchor="middle" font-size="11" fill="#666">図2.6 APIキーが届くまでの流れ</text>
</svg>
  <figcaption>図2.6: APIキーが届くまでの流れ</figcaption>
</figure>

正しく読み込めるかを、キー本体を表示せずに確かめます。

```bash
# .envからキーを読み込めるか確認する（キー本体は表示しない。全OS共通）
uv run python -c "from dotenv import load_dotenv; import os; load_dotenv(); k = os.environ.get('ANTHROPIC_API_KEY', ''); print(k.startswith('sk-ant-'), len(k))"
```

`True 108` のように、`True` と100前後の数字が出れば成功です。`False 0` なら、ファイル名・置き場所・変数名のつづりを確認してください。外側を二重引用符、内側を一重引用符にしているのは、PowerShellでもbashでも同じように動かすための工夫です。

> **NOTE**: `load_dotenv()` は初期設定では、同じ名前の環境変数がOS側にすでにあると、`.env` の値で上書きしません。キーを差し替えたのに認証エラーが続くときは、OSの環境変数に古いキーが残っていないかを確認してください。

### .gitignoreでキーをGitから守る

`.env` を作っただけでは、まだ安全ではありません。プロジェクトはGitのリポジトリなので、`git add .` で `.env` までコミットされてしまう恐れがあります。そこで、`uv init` が作った `.gitignore` の末尾に、次の行を追加します。

```text
# .gitignore（既存の行は残し、末尾に追記する）
# APIキーなどの秘密情報を含むファイル
.env
```

追加したら、本当に無視されているかを確認します。

```bash
# .envが無視対象になっているかを確認する（全OS共通。Gitが必要）
git check-ignore -v .env
git status
```

`.gitignore:13:.env	.env` のように表示されれば成功です。「`.gitignore` の13行目のルールで `.env` が無視されている」という意味です。行番号は環境によって変わります。`git status` の未管理ファイルの一覧に `.env` が出てこないことも確かめましょう。**最初のコミットの前に**、この確認を必ず済ませてください。

> **WARNING**: `.gitignore` は、まだコミットしていないファイルにしか効きません。すでにコミットした `.env` は、あとから無視の設定をしても履歴に残ります。その場合は、次の「漏えい時の対処」を行います。

あわせて、キーをターミナルに直接打ち込まない習慣もつけましょう。PowerShellやbashは入力したコマンドを履歴ファイルに保存するため、キーが平文で残ってしまいます。キーを用途やパソコンごとに分けておけば、漏えい時に止める範囲も小さくできます。

### キーが漏えいしたときの対処

漏えいに気づいたら、次の順番で対処します。

> **STEP 1**: 漏えいしたキーをすぐに無効化する
> Claude ConsoleのAPIキーの画面で、該当するキーを無効化（Disable）するか削除します。何よりも先に行います。

> **STEP 2**: 新しいキーを発行し、.envを書き換える
> 2.1節の手順で新しいキーを作り、`.env` の値を置き換えます。

> **STEP 3**: 利用状況を確認する
> Consoleの利用量やコストの画面で、身に覚えのない利用がないかを確かめます。不審な利用があればサポートに連絡します。

> **STEP 4**: 原因を取り除く
> `.gitignore` を整え、`.env` をGitの管理から外します。必要なら履歴を書き換えるツールで履歴からも削除します。

順番には理由があります。履歴からキーを消す作業は時間がかかり、すでに誰かがコピーしていれば意味がありません。一方、キーを無効化すれば、たとえ公開されたままでも悪用はできません。「消す」より「止める」が先、と覚えておきましょう。

> **NOTE**: GitHubには、シークレットスキャン（秘密情報の検出の仕組み）があります。公開リポジトリでClaude APIのキーが見つかると、この仕組みとの連携によって、キーが無効化され通知が届く場合があります。ただし、これは安全網にすぎません。自分で漏えいを防ぐ設定が基本です。

---

## 2.4 curlで最初のリクエストを送る

いよいよClaude APIを呼び出します。ただし、いきなりPythonで書くのではなく、まずは **curl** というコマンドを使います。curlは、ターミナルからHTTPのリクエストを送るための基本的な道具です。ライブラリを通さずに送ることで、「APIを呼ぶとは、決まった形の文字列を送って受け取ることだ」と実感できます。

### リクエストを形づくる3つの部品

Messages APIへのリクエストは、3つの部品でできています。送り先の **エンドポイント**、付帯情報の **ヘッダー**、依頼内容をJSONで書いた **ボディ** です。エンドポイントは `POST https://api.anthropic.com/v1/messages` です。ヘッダーは、次の3つが必須です。

| ヘッダー | 値 | 役割 |
|---|---|---|
| `x-api-key` | 自分のAPIキー | 誰からのリクエストかを証明する |
| `anthropic-version` | `2026-10-21` | どの版のAPI仕様で解釈するかを指定する |
| `content-type` | `application/json` | ボディがJSONであることを伝える |

`anthropic-version` は、API仕様の「版」を固定するヘッダーです。仕様が新しくなっても、この値を変えない限り同じ版で処理されます。本書では全章で `2026-10-21` を使います。ボディの最小構成は、`model`（モデルID）・`max_tokens`（出力トークン数の上限）・`messages`（会話の配列）の3項目です。

> **NOTE**: 公式ドキュメントが主に紹介しているのは、別のヘッダーでAPIキーを送る書き方です。そのヘッダーとは `Authorization: Bearer <APIキー>` です。`x-api-key` は、公式では従来からの（legacy）方法と位置づけられています。ただし引き続き使え、公式のcurlの例にも使われています。本書は一貫して `x-api-key` を使います。

<figure id="fig-2-7">
<svg width="605" height="360" viewBox="0 0 605 360"
     xmlns="http://www.w3.org/2000/svg"
     font-family="'Noto Sans JP',sans-serif">
  <defs>
    <marker id="f2_7_arrow" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#333" stroke-width="1.5"/>
    </marker>
    <marker id="f2_7_arrowA" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#2b6cb0" stroke-width="1.5"/>
    </marker>
  </defs>
  <rect x="0" y="0" width="605" height="360" fill="#ffffff"/>
  <text x="20" y="24" text-anchor="start" dominant-baseline="central" font-size="13" fill="#1a1a1a" font-weight="bold">Messages API へのリクエスト ＝ 3つの部品</text>
  <rect x="20" y="44" width="120" height="50" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="80.0" y="60.5" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a" font-weight="bold">① エンドポイント</text>
  <text x="80.0" y="77.5" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">どこへ送るか</text>
  <rect x="150" y="44" width="435" height="50" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.2"/>
  <text x="367.5" y="69.0" text-anchor="middle" dominant-baseline="central" font-size="12" font-family="Consolas,monospace" fill="#1a1a1a">POST https://api.anthropic.com/v1/messages</text>
  <rect x="20" y="108" width="120" height="98" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="80.0" y="131.5" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a" font-weight="bold">② ヘッダー</text>
  <text x="80.0" y="148.5" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">必須は3つ</text>
  <text x="80.0" y="165.5" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">誰が・どの版で・</text>
  <text x="80.0" y="182.5" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">どの形式で</text>
  <rect x="150" y="108" width="435" height="98" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.2"/>
  <text x="162" y="126" text-anchor="start" dominant-baseline="central" font-size="12" font-family="Consolas,monospace" fill="#1a1a1a">x-api-key: &lt;APIキー&gt;</text>
  <text x="575" y="126" text-anchor="end" dominant-baseline="central" font-size="11" fill="#555">認証（誰からか）</text>
  <text x="162" y="156" text-anchor="start" dominant-baseline="central" font-size="12" font-family="Consolas,monospace" fill="#1a1a1a">anthropic-version: 2026-10-21</text>
  <text x="575" y="156" text-anchor="end" dominant-baseline="central" font-size="11" fill="#555">API仕様の版</text>
  <text x="162" y="186" text-anchor="start" dominant-baseline="central" font-size="12" font-family="Consolas,monospace" fill="#1a1a1a">content-type: application/json</text>
  <text x="575" y="186" text-anchor="end" dominant-baseline="central" font-size="11" fill="#555">ボディがJSON</text>
  <rect x="20" y="220" width="120" height="98" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="80.0" y="252.0" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a" font-weight="bold">③ ボディ</text>
  <text x="80.0" y="269.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">JSON</text>
  <text x="80.0" y="286.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">何をしてほしいか</text>
  <rect x="150" y="220" width="435" height="98" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.2"/>
  <text x="162" y="240" text-anchor="start" dominant-baseline="central" font-size="12" font-family="Consolas,monospace" fill="#1a1a1a">"model": "claude-opus-5-5"</text>
  <text x="575" y="240" text-anchor="end" dominant-baseline="central" font-size="11" fill="#555">使うモデル</text>
  <text x="162" y="268" text-anchor="start" dominant-baseline="central" font-size="12" font-family="Consolas,monospace" fill="#1a1a1a">"max_tokens": 1024</text>
  <text x="575" y="268" text-anchor="end" dominant-baseline="central" font-size="11" fill="#555">出力の上限</text>
  <text x="162" y="296" text-anchor="start" dominant-baseline="central" font-size="12" font-family="Consolas,monospace" fill="#1a1a1a">"messages": [{"role": "user", ...}]</text>
  <text x="575" y="296" text-anchor="end" dominant-baseline="central" font-size="11" fill="#555">会話の配列</text>
  <text x="302" y="346" text-anchor="middle" font-size="11" fill="#666">図2.7 Messages APIリクエストの構成</text>
</svg>
  <figcaption>図2.7: Messages APIリクエストの構成</figcaption>
</figure>

### ボディをファイルに書く

ボディは `request.json` というファイルに書いておきます。コマンドにJSONを直接書くと、引用符の扱いがシェルごとに異なり、特にPowerShellで崩れやすいからです。プロジェクトのフォルダーに、次の内容で `request.json` を作成してください。JSONはコメントを書けない形式のため、ファイル名は本文で示します。

```json
{
  "model": "claude-opus-5-5",
  "max_tokens": 1024,
  "messages": [
    {"role": "user", "content": "こんにちは、Claude。自己紹介を2文でお願いします。"}
  ]
}
```

`messages` は、`role`（発言者）と `content`（発言内容）の組の配列です。ここではユーザー（`user`）の発言を1つだけ入れています。VS Codeで保存すれば、文字コードは日本語を正しく扱えるUTF-8（ユーティーエフ・エイト）になります。

### macOS・Linux・Git Bashで送る

キーをコマンドに直接書くと履歴に残るので、`.env` から読み込んでから送ります。

```bash
# .envの内容を環境変数として読み込む（macOS / Linux / Git Bash）
set -a; source .env; set +a

# Messages APIにリクエストを送る。行末の \ は行の継続を表す
curl -sS https://api.anthropic.com/v1/messages \
  --header "x-api-key: $ANTHROPIC_API_KEY" \
  --header "anthropic-version: 2026-10-21" \
  --header "content-type: application/json" \
  --data-binary @request.json
```

`set -a` は「以降に定義する変数を環境変数にする」、`source .env` は「`.env` を読み込む」という意味です。`-sS` は、進捗表示を消しつつエラーは表示する指定です。`--data-binary @request.json` は、ファイルの中身を加工せずに送る指定です。

### Windows PowerShellで送る

PowerShellでは、`.env` を1行ずつ読んで環境変数に設定してから送ります。

```powershell
# .envの「名前=値」の行を環境変数に設定する（PowerShell）
Get-Content .env | ForEach-Object { if ($_ -match '^\s*([^#=]+)=(.*)$') { Set-Item "env:$($matches[1].Trim())" $matches[2].Trim() } }

# curl.exe でリクエストを送る。行末のバッククォートは行の継続を表す
curl.exe -sS https://api.anthropic.com/v1/messages `
  --header "x-api-key: $env:ANTHROPIC_API_KEY" `
  --header "anthropic-version: 2026-10-21" `
  --header "content-type: application/json" `
  --data-binary "@request.json"
```

bashとの違いは3つです。1つ目は、`curl` ではなく `curl.exe` と書く点です。Windows PowerShell 5.1では、`curl` が別コマンドの別名になっているためです。その別コマンドとは、Invoke-WebRequest（インボーク・ウェブリクエスト）です。2つ目は、行の継続が `\` ではなくバッククォートである点です。3つ目は、`@` がPowerShellの特別な記号なので、`"@request.json"` と引用符で囲む点です。

> **WARNING**: PowerShellでは、返ってきた日本語が文字化けして見えることがあります。表示側の文字コードの問題で、応答そのものは正しく届いています。気になる場合はGit Bashで実行するか、次節のPythonで確認してください。

### 返ってきたJSONを読む

成功すると、次のようなJSONが1行で返ってきます。読みやすく整形し、一部の値を省略しています。

```json
{
  "id": "msg_01XFDUDYJgAACzvnptvVoYEL",
  "type": "message",
  "role": "assistant",
  "model": "claude-opus-5-5",
  "content": [
    {"type": "thinking", "thinking": "", "signature": "EqQBCg..."},
    {"type": "text", "text": "こんにちは！私はAnthropicが開発したAIアシスタントのClaudeです。文章作成や調べもの、プログラミングなど、さまざまな作業をお手伝いできます。"}
  ],
  "stop_reason": "end_turn",
  "stop_sequence": null,
  "usage": {
    "input_tokens": 28,
    "output_tokens": 142,
    "cache_creation_input_tokens": 0,
    "cache_read_input_tokens": 0
  }
}
```

注目したいのは `content` です。回答は1つの文字列ではなく、**ブロックの配列** で返ってきます。この例では先頭に思考（`thinking`）のブロックがあり、その後ろに回答本文の `text` ブロックがあります。思考のブロックは含まれないこともあるため、「先頭が回答だ」と決めつけず、`type` を見て `text` を探す必要があります。

`stop_reason` の `end_turn` は、回答を最後まで書き終えたことを示します。`usage` は課金の対象になったトークン数で、2.1節の料金計算はこの数字をもとに行います。各項目の詳しい意味は第3章で読み解きます。

> **POINT**: うまくいかないときは、`-sS` を `-sSi` に変えてみましょう。レスポンスのヘッダーも表示され、HTTPステータス（成功なら200）と、問い合わせに使う `request-id` を確認できます。

失敗すると、エラーを表すJSONが返ります。たとえば `{"type":"error","error":{"type":"authentication_error","message":"invalid x-api-key"}, ...}` のような形です。`authentication_error`（401）はキーの誤りです。`invalid_request_error`（400）はヘッダーやボディの誤りです。`error.message` に原因が書かれているので、まずそこを読みましょう。curlで仕組みを確かめたら、次は同じリクエストをPythonで書きます。


## 2.5 Python＋httpxで最初のリクエストを送る

curlで送ったリクエストを、今度はPythonで書きます。エージェントは、APIの応答を見て次の行動を決めるプログラムです。そのためには、応答をプログラムの中で受け取り、必要な部分を取り出せなければなりません。本節で作る `hello_claude.py` は、本書で最初のPythonファイルであり、第4章で作る自作クライアントの原型にもなります。

### hello_claude.pyを書く

プロジェクトのフォルダーに `hello_claude.py` を新規作成し、次のコードを書いてください。

```python
# hello_claude.py
# Claude API（Messages API）に httpx で最初のリクエストを送るスクリプト（新規作成）
import os  # 環境変数を読むための標準ライブラリ
import sys  # エラー時にプログラムを終了するために使う

import httpx  # HTTPリクエストを送るライブラリ
from dotenv import load_dotenv  # .env を環境変数に読み込むライブラリ

# --- 設定値（curlで使った値と同じ） ---
API_URL = "https://api.anthropic.com/v1/messages"  # エンドポイント
API_VERSION = "2026-10-21"  # anthropic-version ヘッダーの値
MODEL = "claude-opus-5-5"  # 使うモデルID
MAX_TOKENS = 1024  # 出力トークン数の上限


def main() -> None:
    # .env を読み込み、APIキーを取り出す（なければ説明を出して終了）
    load_dotenv()
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("ANTHROPIC_API_KEY が見つかりません。.env を確認してください。")

    # 必須の3つのヘッダー
    headers = {
        "x-api-key": api_key,
        "anthropic-version": API_VERSION,
        "content-type": "application/json",
    }

    # リクエストボディ（request.json と同じ内容を辞書で書く）
    body = {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "messages": [
            {"role": "user", "content": "こんにちは、Claude。自己紹介を2文でお願いします。"},
        ],
    }

    # POSTで送信する。タイムアウトは必ず明示する
    try:
        response = httpx.post(
            API_URL,
            headers=headers,
            json=body,
            timeout=httpx.Timeout(600.0, connect=10.0),
        )
        response.raise_for_status()  # 成功（2xx）でなければ例外を発生させる
    except httpx.HTTPStatusError as e:
        # APIが返したエラーの中身と request-id を表示して終了する
        print(f"HTTP {e.response.status_code}: {e.response.text}")
        print(f"request-id: {e.response.headers.get('request-id')}")
        sys.exit(1)
    except httpx.RequestError as e:
        # 接続失敗やタイムアウトなど、応答が届かなかった場合
        sys.exit(f"通信エラー: {e!r}")

    # レスポンスのJSONを辞書に変換する
    data = response.json()

    # 本文を読む前に stop_reason を確認する
    stop_reason = data["stop_reason"]
    if stop_reason != "end_turn":
        print(f"注意: stop_reason = {stop_reason}")

    # content 配列から type が text のブロックだけを取り出して連結する
    texts = [block["text"] for block in data["content"] if block["type"] == "text"]
    print("".join(texts))

    # 使ったトークン数を表示する
    usage = data["usage"]
    print(f"\n[tokens] input={usage['input_tokens']} output={usage['output_tokens']}")


if __name__ == "__main__":
    main()
```

### コードを読み解く

前半の設定値は、curlで使った値と同じです。値をファイルの先頭に定数としてまとめておくと、モデルやAPIの版を差し替えるときに1か所の変更で済みます。APIキーは `os.environ.get()` で読み、見つからなければ `sys.exit()` でメッセージを出して終了します。原因の分からないエラーで止まるより、何をすればよいかを伝えて止まるほうが親切だからです。

`headers` と `body` は、curlの `--header` と `request.json` をそのままPythonの辞書にしたものです。`httpx.post()` の `json=` 引数に辞書を渡すと、httpxがJSON文字列に変換して送ってくれます。文字コードの心配もいりません。

`timeout` の指定は特に重要です。httpxは、何も指定しないと **5秒** で待つのをやめてしまいます。Claudeは回答の前に考える時間をとるため、5秒では足りないことがよくあります。ここでは、接続までは10秒、接続後は応答のデータが届くまで最大600秒待つように指定しています。

`raise_for_status()` は、HTTPステータスが成功（200番台）かどうかを調べます。成功でなければ、`httpx.HTTPStatusError` を発生させます。Claude APIのエラーは400番台・500番台で返るので、ここで受け止められます。`except` の中では、エラーのJSONと `request-id` ヘッダーを表示します。`httpx.RequestError` は、ネットワークの切断やタイムアウトなど、そもそも応答が届かなかった場合のエラーです。

後半では、`response.json()` で応答を辞書に変換します。回答本文を読む前には、`stop_reason` を確認しています。`max_tokens`（上限で打ち切られた）や `refusal`（回答を断った）の場合は、本文が不完全なことがあるからです。最後に、リスト内包表記で `type` が `text` のブロックだけを集め、つなげて表示します。2.4節で見たとおり、思考のブロックが先頭に来ることがあるため、`content[0]` と決め打ちにしてはいけません。

<figure id="fig-2-8">
<svg width="605" height="450" viewBox="0 0 605 450"
     xmlns="http://www.w3.org/2000/svg"
     font-family="'Noto Sans JP',sans-serif">
  <defs>
    <marker id="f2_8_arrow" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#333" stroke-width="1.5"/>
    </marker>
    <marker id="f2_8_arrowA" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#2b6cb0" stroke-width="1.5"/>
    </marker>
  </defs>
  <rect x="0" y="0" width="605" height="450" fill="#ffffff"/>
  <rect x="20" y="20" width="320" height="42" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="180.0" y="32.5" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a" font-weight="bold">① キーを読み込む</text>
  <text x="180.0" y="49.5" text-anchor="middle" dominant-baseline="central" font-size="11" font-family="Consolas,monospace" fill="#1a1a1a">load_dotenv() → os.environ.get()</text>
  <path d="M180 62 L180 76" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f2_8_arrow)"/>
  <rect x="20" y="76" width="320" height="42" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="180.0" y="88.5" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a" font-weight="bold">② ヘッダーとボディを組み立てる</text>
  <text x="180.0" y="105.5" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">必須ヘッダー3つ ＋ model・max_tokens・messages</text>
  <path d="M180 118 L180 132" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f2_8_arrow)"/>
  <rect x="20" y="132" width="320" height="42" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="180.0" y="144.5" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a" font-weight="bold">③ 送信する</text>
  <text x="180.0" y="161.5" text-anchor="middle" dominant-baseline="central" font-size="11" font-family="Consolas,monospace" fill="#1a1a1a">httpx.post() → raise_for_status()</text>
  <path d="M180 174 L180 188" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f2_8_arrow)"/>
  <rect x="20" y="188" width="320" height="42" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="180.0" y="200.5" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a" font-weight="bold">④ JSON を辞書に変換</text>
  <text x="180.0" y="217.5" text-anchor="middle" dominant-baseline="central" font-size="11" font-family="Consolas,monospace" fill="#1a1a1a">data = response.json()</text>
  <path d="M180 230 L180 244" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f2_8_arrow)"/>
  <rect x="20" y="244" width="320" height="42" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="180.0" y="256.5" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a" font-weight="bold">⑤ stop_reason を確認</text>
  <text x="180.0" y="273.5" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">end_turn 以外なら注意を表示</text>
  <path d="M180 286 L180 300" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f2_8_arrow)"/>
  <rect x="20" y="300" width="320" height="42" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="180.0" y="312.5" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a" font-weight="bold">⑥ text ブロックを抽出して表示</text>
  <text x="180.0" y="329.5" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">type が "text" のものだけ連結</text>
  <path d="M180 342 L180 356" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f2_8_arrow)"/>
  <rect x="20" y="356" width="320" height="42" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="180.0" y="368.5" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a" font-weight="bold">⑦ 使用トークン数を表示</text>
  <text x="180.0" y="385.5" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">usage の input / output</text>
  <path d="M340 41 L380 41" fill="none" stroke="#333" stroke-width="1.3" stroke-dasharray="5 3" marker-end="url(#f2_8_arrow)"/>
  <rect x="380" y="22" width="205" height="38" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.2"/>
  <text x="482.5" y="33.5" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">キーがない</text>
  <text x="482.5" y="48.5" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">→ 説明を出して終了（sys.exit）</text>
  <path d="M340 153 L380 153" fill="none" stroke="#333" stroke-width="1.3" stroke-dasharray="5 3" marker-end="url(#f2_8_arrow)"/>
  <rect x="380" y="118" width="205" height="70" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.2"/>
  <text x="482.5" y="130.5" text-anchor="middle" dominant-baseline="central" font-size="11" font-family="Consolas,monospace" fill="#1a1a1a">HTTPStatusError（4xx・5xx）</text>
  <text x="482.5" y="145.5" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">→ エラーJSON・request-id を表示</text>
  <text x="482.5" y="160.5" text-anchor="middle" dominant-baseline="central" font-size="11" font-family="Consolas,monospace" fill="#1a1a1a">RequestError</text>
  <text x="482.5" y="175.5" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">→ 通信エラーとして終了</text>
  <rect x="380" y="252" width="205" height="66" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.2"/>
  <text x="482.5" y="269.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">思考（thinking）ブロックが</text>
  <text x="482.5" y="285.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">先頭に来ることがあるので</text>
  <text x="482.5" y="301.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-weight="bold">content[0] と決め打ちしない</text>
  <path d="M380 300 L340 300" fill="none" stroke="#333" stroke-width="1.3" stroke-dasharray="5 3"/>
  <text x="302" y="436" text-anchor="middle" font-size="11" fill="#666">図2.8 hello_claude.pyの処理の流れ</text>
</svg>
  <figcaption>図2.8: hello_claude.pyの処理の流れ</figcaption>
</figure>

### 実行して結果を確かめる

VS Codeの統合ターミナルで、次のコマンドを実行します。

```bash
# hello_claude.py を実行する（全OS共通）
uv run hello_claude.py
```

次のように回答とトークン数が表示されれば成功です。回答の文面は実行のたびに変わります。

```text
こんにちは！私はAnthropicが開発したAIアシスタントのClaudeです。文章作成や調べもの、プログラミングなど、さまざまな作業をお手伝いできます。

[tokens] input=28 output=142
```

おめでとうございます。これが、あなたのプログラムがClaude APIと交わした最初の会話です。Consoleの利用量の画面を開くと、しばらくしてこの呼び出しがグラフに反映されます。

### うまくいかないときは

表示されたメッセージから、原因を切り分けましょう。

| 表示 | 主な原因 | 対処 |
|---|---|---|
| `ANTHROPIC_API_KEY が見つかりません` | `.env` がない、場所や変数名が違う | 2.3節の確認コマンドを実行する |
| `HTTP 401` | キーの誤り・無効化済み | キーを作り直し `.env` を更新する |
| `HTTP 400` | ボディやヘッダーの誤り | `error.message` を読み、つづりを確認する |
| `HTTP 400`（`You have reached your specified … usage limits`） | 自分で設定した利用上限に到達 | Consoleの請求またはワークスペースの画面で上限を確認する |
| `HTTP 400`（`This API key is not scoped to a workspace`） | ワークスペースを選ばずにキーを作った | ワークスペースを選んでキーを作り直し、`.env` を更新する |
| `HTTP 400`（`Your credit balance is too low`） | クレジット残高の不足 | 請求（Billing）の画面でクレジットを購入する |
| `HTTP 402` | 支払い情報の問題 | 請求（Billing）の画面で支払い方法を確認する |
| `HTTP 404` | モデルIDやURLの誤り | `claude-opus-5-5` と `/v1/messages` を確認する |
| `HTTP 429` / `HTTP 529` | 送りすぎ・混雑 | 少し待って再実行する（第4章で自動化） |
| `ModuleNotFoundError: httpx` | プロジェクト外のPythonで実行 | `uv run` で実行する |
| `通信エラー: ReadTimeout` | 応答待ちが長すぎた | ネットワークやプロキシを確認する |

> **POINT**: 本書では、2026-10-21版のAPIで使えない `temperature` などのパラメータは送りません。ほかの記事のコードを参考にして400エラーになったときは、こうした古いパラメータが混ざっていないかを確認してください。詳しくは第3章で扱います。

---

## COLUMN: なぜSDKを使わずhttpxで書くのか

Claude APIには、公式のSDK（ソフトウェア開発キット）も用意されています。SDKを使えば、リトライやストリーミングの処理を自分で書く必要はありません。それでも本書がhttpxで直接HTTPを送るのは、エージェントの仕組みを「見える形」で理解するためです。

本節の `hello_claude.py` を見れば、APIの呼び出しが「ヘッダーとJSONを送り、JSONを受け取る」だけだと分かります。この理解があれば、第5章のツール呼び出しも、第4章のリトライも、すべてこの往復の応用として読み解けます。SDKの便利さは、仕組みを知ったあとで味わうほうが、何をしてくれているのかがよく分かります。

---

## 本章のまとめ

本章で学んだことを整理します：

- Claude APIは、claude.aiとは別の従量課金の製品です。Claude Consoleで、ワークスペース・APIキー・利用上限（spend limit）を管理します。キーの全体が表示されるのは作成直後の一度だけで、学習用には上限を設けたワークスペースを使うと安心です。
- uvを使うと、3つのコマンドでPython 3.12の環境を作って実行できます。作成は `uv init agent-from-scratch --python 3.12 --no-package` です。追加は `uv add httpx python-dotenv`、実行は `uv run` です。VS Codeでは `.venv` のインタープリターを選びます。
- APIキーは `.env` に置いて `load_dotenv()` で読み込み、`.gitignore` でGitから外します。漏えいしたら、何よりも先にConsoleでキーを無効化します。環境が整ったら、curlとhttpxから、エンドポイント・3つの必須ヘッダー・JSONボディでMessages APIを呼び出しました。回答は、`type` が `text` のブロックから取り出しました。

本章で作った `agent-from-scratch` プロジェクトは、このあと最終章まで育てていく土台です。`.env` と `hello_claude.py` が動く状態を保ったまま、次章へ進みましょう。

次章では **Messages APIを理解する** を扱います。リクエストが通ったら、次はその中身——ヘッダー・ボディ・レスポンスの一つひとつ——を読み解き、会話を続けるチャットを自分の手で実装します。
