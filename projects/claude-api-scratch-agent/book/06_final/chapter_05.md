# 第5章: 最初のAIエージェントを作る
# EN-TITLE: BUILD YOUR FIRST AGENT
# TAGS: Tool Use, JSON Schema, tool_result, エージェンティックループ, Open-Meteo

## この章で学ぶこと

本章では以下を学びます：

- Tool Use（ツールユース）の往復の流れを説明できるようになる。そして、「Claudeはツールを実行しない」という原則を自分の言葉で語れるようになる
- JSON Schema（ジェイソン・スキーマ）でツールを定義できるようになる。そのうえで、`tool_use` と `tool_result` の往復を手書きで実装できるようになる
- `while` ループと終了条件・ガードを備えたエージェンティックループ（`agent.py`）を自分で書けるようになる
- ダミーのツールを、キー不要の天気API（Open-Meteo）を呼ぶ本物のツールへ差し替えられるようになる

前章では、`httpx` で Messages API を呼び出す共通モジュールを完成させました。
それが `llm_client.py` です。
リトライ、ストリーミング、ログ、コスト計測までそろい、APIを安心して呼べる土台ができています。
本章では、その土台の上に「ツール」と「ループ」を載せて、最初のAIエージェントを組み立てます。
第1章で紹介した「LLM・ツール・ループ」の3要素が、ここで初めて1本のプログラムとしてつながります。

---

## 5.1 Tool Useの仕組み

ここまでの章で、私たちはClaudeに質問を送り、文章で答えを受け取ってきました。
しかし、文章を返すだけでは「エージェント」とは呼べません。
たとえば「東京の今の天気は？」と聞かれても、Claudeは今この瞬間の天気を知りません。
学習データに含まれない最新の情報や、社内のデータベースの中身には手が届かないからです。
では、Claudeに「外の世界」を調べさせるには、どうすればよいのでしょうか。
その答えが、本節で扱う Tool Use の仕組みです。

### Tool Useとは何か

Tool Use とは、Claudeに「使える道具の一覧」を渡し、必要に応じて道具の使用を依頼させる仕組みです。
他社のAPIでは Function Calling（ファンクション・コーリング）とも呼ばれる考え方です。
開発者はリクエストの `tools` パラメータに、ツールの名前・説明・引数の形を書いて渡します。
Claudeは質問を読み、ツールが必要だと判断すると、「このツールをこの引数で使いたい」と返してきます。
開発者のコードはその依頼を受けてツールを実行し、結果をClaudeに送り返します。
Claudeは結果を読んで、最終的な回答を文章にまとめます。

ここで、本章でもっとも大切な原則を先に示します。
**Claudeはツールを実行しません。実行するのは、あなたのコードです。**
Claudeが返してくるのは、あくまで「この関数をこの引数で呼んでください」という依頼の文書にすぎません。
実際に天気APIへアクセスしたり、ファイルを読んだりするのは、あなたが書いたPythonの関数です。
この原則を押さえると、Tool Use の挙動で迷うことがほとんどなくなります。

たとえるなら、Claudeはレストランの「注文を取る係」で、あなたのコードは「厨房」です。
注文係はお客さんの要望を聞き、「オムライスを1つ、卵は半熟で」と伝票に書いて厨房へ渡します。
料理を作るのは厨房で、注文係ではありません。
できあがった料理を受け取った注文係が、お客さんに「お待たせしました」と届けます。
`tool_use` が伝票、`tool_result` ができあがった料理、という対応で考えると覚えやすいでしょう。

この原則を理解しておくと、セキュリティや設計の判断にも役立ちます。
Claudeが勝手にファイルを消したり、勝手にメールを送ったりすることは、仕組み上起こりません。
起こるとすれば、あなたのコードが「依頼されたら何でも実行する」作りになっている場合です。
つまり、ツールの安全性はツールを実装する側、すなわち私たちの責任になります。
この考え方は、第6章で安全なファイル操作ツールを作るときの土台にもなります。

### 往復の流れを追いかける

Tool Use の流れを、天気を例に1ステップずつ追いかけてみましょう。
全体は大きく5つの段階に分かれます。

1. **ツールを定義して質問を送る**: リクエストに `tools` を含め、「東京の天気は？」と送ります。
2. **Claudeがツールの使用を依頼する**: 応答の `content` に `tool_use` ブロックが入ります。このとき `stop_reason` は `"tool_use"` になります。
3. **自分のコードでツールを実行する**: `tool_use` の `name` と `input` を読みます。そして、対応するPython関数を呼びます。
4. **結果を `tool_result` として送り返す**: 実行結果を user メッセージに入れ、もう一度APIを呼びます。
5. **Claudeが最終回答を返す**: 結果を読んだClaudeが文章で答えます。このとき `stop_reason` は `"end_turn"` になります。

<figure id="fig-5-1">
<svg width="605" height="428" viewBox="0 0 605 428"
     xmlns="http://www.w3.org/2000/svg"
     font-family="'Noto Sans JP',sans-serif">
  <defs>
    <marker id="f5_1_arr51" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#333" stroke-width="1.5"/>
    </marker>
    <marker id="f5_1_arr51a" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#2b6cb0" stroke-width="1.5"/>
    </marker>
  </defs>
  <rect x="0" y="0" width="605" height="428" fill="#ffffff"/>
  <rect x="20" y="15" width="140" height="44" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="90.0" y="29.3" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a">ツール関数</text>
  <text x="90.0" y="45.4" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">get_weather()</text>
  <rect x="222" y="15" width="160" height="44" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="302.0" y="37.0" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a" font-weight="bold">あなたのコード</text>
  <rect x="435" y="15" width="160" height="44" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="515.0" y="29.3" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a">Claude</text>
  <text x="515.0" y="45.4" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">（Messages API）</text>
  <path d="M90 59 L90 372" fill="none" stroke="#999" stroke-width="1.2" stroke-dasharray="4,3"/>
  <path d="M302 59 L302 372" fill="none" stroke="#999" stroke-width="1.2" stroke-dasharray="4,3"/>
  <path d="M515 59 L515 372" fill="none" stroke="#999" stroke-width="1.2" stroke-dasharray="4,3"/>
  <path d="M302 100 L513 100" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f5_1_arr51)"/>
  <text x="408" y="89" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">① tools ＋「東京の天気は？」</text>
  <text x="408" y="112" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#666">（1回目のリクエスト）</text>
  <path d="M515 152 L304 152" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f5_1_arr51)"/>
  <text x="408" y="141" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">② tool_use（get_weather）</text>
  <text x="408" y="164" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">stop_reason: "tool_use"</text>
  <path d="M302 205 L92 205" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f5_1_arr51)"/>
  <text x="196" y="194" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#2b6cb0" font-weight="bold">③ 関数を実行</text>
  <path d="M90 240 L300 240" fill="none" stroke="#333" stroke-width="1.3" stroke-dasharray="4,3" marker-end="url(#f5_1_arr51)"/>
  <text x="196" y="229" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">実行結果（JSON文字列）</text>
  <path d="M302 292 L513 292" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f5_1_arr51)"/>
  <text x="408" y="281" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">④ tool_result を送る</text>
  <text x="408" y="304" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#666">（2回目のリクエスト）</text>
  <path d="M515 345 L304 345" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f5_1_arr51)"/>
  <text x="408" y="334" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">⑤ 最終回答（text）</text>
  <text x="408" y="357" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">stop_reason: "end_turn"</text>
  <text x="302" y="392" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#2b6cb0" font-weight="bold">Claude はツールを実行しない。実行するのはあなたのコード</text>
</svg>
  <figcaption>図5.1: Tool Useの往復</figcaption>
</figure>

注目してほしいのは、APIを呼ぶ回数です。
天気を1回調べるだけでも、APIは最低2回呼ばれます。
1回目でツールの使用依頼を受け取り、2回目で結果を渡して最終回答を受け取るからです。
第3章で学んだように、Messages API はステートレス（状態を持たない）でした。
そのため2回目のリクエストには、1回目の質問、Claudeの依頼、ツールの結果をすべて含める必要があります。
「会話の履歴は自分で積み直す」という第3章の感覚が、ここでそのまま生きてきます。

この往復は、1回で終わるとは限りません。
たとえば「東京と札幌の気温差を教えて」と頼むと、Claudeは2つの都市について天気を調べたがります。
1つの応答で2つの `tool_use` をまとめて依頼することもあれば、1つずつ順番に依頼することもあります。
さらに結果を見て「念のため別の情報も確認したい」と、もう一度依頼してくることもあります。
この「依頼→実行→結果→次の判断」を、Claudeが満足するまで繰り返すのがエージェンティックループです。
本章の後半では、この繰り返しを `while` ループで自動化します。

### `stop_reason: "tool_use"` の意味

第3章で、応答の `stop_reason` は「Claudeがなぜ生成を止めたか」を表すと学びました。
通常の会話では、答え終わったことを示す `"end_turn"` がもっともよく見る値です。
ツールを渡したリクエストでは、ここに新しく `"tool_use"` という値が現れます。
これは「答え終わったのではなく、ツールの結果を待つために一時停止した」という意味です。
言い換えると、Claudeからのボールがこちらに渡された状態を表しています。

`"tool_use"` で止まった応答の `content` を見てみましょう。
そこには、少なくとも1つの `tool_use` ブロックが入っています。
その前に「東京の天気を確認しますね」といった `text` ブロックが付くこともあります。
大切なのは、この時点の `text` は最終回答ではないという点です。
「確認します」と言ったまま止まっているので、ここで処理を終えるとユーザーは答えを受け取れません。
`stop_reason` を見ずに `text` だけを取り出して表示すると、この不完全な応答をそのまま見せてしまいます。

そこで、エージェントのコードは必ず次の順で判断します。
まず `stop_reason` を確認し、`"tool_use"` ならツールを実行して続行します。
`"end_turn"` なら、そこで初めて `text` を最終回答として取り出します。
第3章・第4章で「本文を読む前に `stop_reason` を判定する」と繰り返してきたのは、このためでした。
本章のループは、この判定を中心に組み立てていきます。

| `stop_reason` | 意味 | エージェントの対応 |
|---|---|---|
| `end_turn` | 回答を自然に終えた | `text` を最終回答として返し、ループを終える |
| `tool_use` | ツールの結果を待っている | ツールを実行し、`tool_result` を返して続行する |
| `max_tokens` | 出力上限に達して途中で切れた | 警告付きで打ち切る（または上限を見直す） |
| `refusal` | 安全上の理由で応答を控えた | 中断し、`stop_details` をログに残す |
| `pause_turn` | サーバーツールの長い処理を一時停止した | 本章では扱わない（第6章で概要を紹介） |

> **POINT**: `stop_reason` が `"tool_use"` の応答にも、`text` が含まれることがあります。この `text` は「途中経過のつぶやき」です。最終回答として扱ってはいけません。エージェントのコードは、必ず `stop_reason` を先に判定してから本文を読みます。

### Claudeはなぜ正しい引数を作れるのか

ここで素朴な疑問が浮かぶかもしれません。
Claudeは関数のコードを見ていないのに、なぜ正しい引数を組み立てられるのでしょうか。
答えは、ツール定義に書いた「説明」と「引数の型の説明」を読んでいるからです。
私たちが `tools` に書いた内容は、Claudeにとって「道具の取扱説明書」になります。
Claudeはその説明書と会話の内容を照らし合わせ、使うべき道具と渡すべき値を決めています。

裏を返すと、説明書が不十分だとClaudeは迷います。
たとえば説明に「天気を返す」としか書いていなければ、都市名を日本語で渡すべきか英語で渡すべきか分かりません。
気温の単位を指定できることを書いていなければ、華氏で聞かれても単位を切り替えられません。
Claudeの判断の質は、私たちが書く説明の質に大きく左右されるということです。
この点は 5.2 節で、ツールの説明文の書き方として詳しく扱います。

なお、ツール定義はリクエストのたびに送られ、入力トークンとして課金されます。
APIの内部では、ツールの一覧が system プロンプトの一部のような形でモデルに渡されています。
そのため、ツールを増やしたり説明を長くしたりすると、毎回の入力トークンが少しずつ増えます。
ツールを渡すだけで数百トークン程度の上乗せが発生することもあるので、覚えておきましょう。
第4章で作った `tracker` を使えば、この増加分も実際の数字で確かめられます。

### `tool_choice` は「auto」に任せる

Claudeにツールを使わせるかどうかは、`tool_choice` パラメータで指定できます。
何も指定しない場合は `{"type": "auto"}` と同じ扱いで、ツールを使うかどうかをClaudeが判断します。
`{"type": "none"}` を指定すると、ツールを定義していても使わずに文章だけで答えさせられます。
本書では、基本的に `auto`（省略）を使います。

APIの仕様には、特定のツールを強制する指定もあります。
`{"type": "any"}` や `{"type": "tool", "name": ...}` がそれです。
しかし本書で既定モデルとして使う `claude-opus-5-5` では、強制の指定は 400 エラーになります。
中間モデルの `claude-sonnet-5-5` でも同様です。
「必ずツールを使わせたい」場面では、強制ではなく system プロンプトとツールの説明で誘導します。
決まった形式のデータを確実に得たい場合は、第6章で扱う構造化出力が適しています。

> **WARNING**: 古い記事や他社APIの解説には、ある例がよく載っています。「`tool_choice` で特定のツールを強制する」例です。本書の環境は `anthropic-version: 2026-10-21`、Opus 5.5 です。この環境でそのまま書くと `invalid_request_error`（400）になります。コピーする前に、`tool_choice` の値を確認してください。

### クライアントツールとサーバーツール

Tool Use には、実行する場所によって2つの種類があります。
1つは、ここまで説明してきた**クライアントツール**です。
ツールの定義も実行も開発者側で行い、結果を `tool_result` で返すタイプのツールを指します。
もう1つは、**サーバーツール**です。
こちらはAnthropic社のサーバー側で実行されるツールで、開発者は実行コードを書きません。

サーバーツールの代表例は、Web検索の `web_search_20260209` です。
Webページ取得の `web_fetch_20260209` も代表例の1つです。
名前の末尾の数字はツールのバージョンを表します。
これらをリクエストの `tools` に含めると、Claudeは検索や取得をAPIの内部で済ませてから回答を返します。
応答には検索の過程を示す専用のブロックが含まれますが、開発者が `tool_result` を作る必要はありません。
処理が長くなると `stop_reason` が `pause_turn` になり、続きを促すリクエストを送る必要があります。

<figure id="fig-5-2">
<svg width="605" height="345" viewBox="0 0 605 345"
     xmlns="http://www.w3.org/2000/svg"
     font-family="'Noto Sans JP',sans-serif">
  <defs>
    <marker id="f5_2_arr52" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#333" stroke-width="1.5"/>
    </marker>
    <marker id="f5_2_arr52a" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#2b6cb0" stroke-width="1.5"/>
    </marker>
  </defs>
  <rect x="0" y="0" width="605" height="345" fill="#ffffff"/>
  <text x="155" y="28" text-anchor="middle" dominant-baseline="central" font-size="13" fill="#1a1a1a" font-weight="bold">クライアントツール</text>
  <rect x="15" y="45" width="280" height="255" rx="6" fill="none" stroke="#999" stroke-width="1"/>
  <rect x="30" y="60" width="250" height="38" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="155.0" y="79.0" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a">Claude が tool_use を返す</text>
  <path d="M155 98 L155 113" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f5_2_arr52)"/>
  <rect x="30" y="115" width="250" height="38" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="155.0" y="134.0" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a">あなたのコードが実行する</text>
  <path d="M155 153 L155 168" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f5_2_arr52)"/>
  <rect x="30" y="170" width="250" height="38" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="155.0" y="189.0" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a">tool_result を作って送り返す</text>
  <path d="M30 220 L280 220" fill="none" stroke="#999" stroke-width="1"/>
  <text x="32" y="240" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">実行場所: 手元のPC・自社サーバー</text>
  <text x="32" y="264" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">定義: name・description・input_schema</text>
  <text x="32" y="288" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">主な stop_reason: tool_use</text>
  <text x="450" y="28" text-anchor="middle" dominant-baseline="central" font-size="13" fill="#1a1a1a" font-weight="bold">サーバーツール</text>
  <rect x="310" y="45" width="280" height="255" rx="6" fill="none" stroke="#999" stroke-width="1"/>
  <rect x="325" y="60" width="250" height="38" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="450.0" y="79.0" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a">Claude がツールの使用を決める</text>
  <path d="M450 98 L450 113" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f5_2_arr52)"/>
  <rect x="325" y="115" width="250" height="38" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="450.0" y="134.0" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a">Anthropic のサーバーで実行</text>
  <path d="M450 153 L450 168" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f5_2_arr52)"/>
  <rect x="325" y="170" width="250" height="38" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="450.0" y="189.0" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a">結果は応答に含まれて返る</text>
  <path d="M325 220 L575 220" fill="none" stroke="#999" stroke-width="1"/>
  <text x="327" y="240" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">実行場所: Anthropic社のサーバー</text>
  <text x="327" y="264" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">定義: type（例: web_search_20260209）</text>
  <text x="327" y="288" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">主な stop_reason: end_turn・pause_turn</text>
</svg>
  <figcaption>図5.2: クライアントツールとサーバーツール</figcaption>
</figure>

2つの違いを表に整理しておきます。

| 観点 | クライアントツール | サーバーツール |
|---|---|---|
| 実行する場所 | 自分のコード（手元のPC・自社サーバー） | Anthropic社のサーバー |
| 定義の書き方 | `name`・`description`・`input_schema` を自分で書く | `type`（例: `web_search_20260209`）と設定を書く |
| 結果の返し方 | 自分で `tool_result` を作って返す | API内部で処理され、応答に含まれる |
| 主な `stop_reason` | `tool_use` | `end_turn`・`pause_turn` |
| 向いている用途 | 社内データ、自作の処理、外部API | Web検索、Webページの取得 |
| 本書での扱い | 第5章以降の中心 | 第6章で概要と使い分けを紹介 |

本書がクライアントツールを中心に扱うのは、エージェントの仕組みがすべて見えるからです。
サーバーツールは便利ですが、ループの中身がAPIの内側に隠れてしまいます。
一方、クライアントツールではループを自分で回すため、何が起きているかを1行ずつ追えます。
「スクラッチから作る」という本書の目的には、こちらがぴったりです。
本章で作る天気ツールも、もちろんクライアントツールです。

> **NOTE**: サーバーツールとクライアントツールは、1つのリクエストの中で混ぜて使えます。たとえば「Web検索はサーバーツール、社内DBの検索はクライアントツール」という構成も可能です。使い分けの指針は第6章で整理します。

### Adaptive thinkingとthinkingブロック

最後に、本章のコードを動かすと出会うかもしれない `thinking` ブロックについて触れておきます。
本書の既定モデル `claude-opus-5-5` では、adaptive thinking（適応的思考）が常に有効です。
これは、問題の難しさに応じてClaudeが自分で「考える量」を調整する仕組みです。
その結果、応答の `content` に `type: "thinking"` のブロックが含まれることがあります。
既定の設定では、このブロックの `thinking` フィールドは空文字で、中身は見えません。

Tool Use との関係で大切なのは、履歴の扱いです。
`thinking` ブロックには `signature`（署名）というフィールドが付いています。
これはAPI側が「この思考は確かに自分が生成したもの」と確認するための値です。
そのため、応答を履歴に戻すときは `content` 配列を**そのまま**追加します。
`thinking` ブロックを消したり書き換えたりはしません。
逆に言えば、「`content` をそのまま戻す」という1つのルールを守るだけで済みます。
それだけで、`thinking` の存在を意識する必要はなくなります。

もし `text` と `tool_use` だけを抜き出して履歴を作り直すと、思考の連続性が途切れてしまいます。
場合によっては、署名の検証に失敗して 400 エラーになることもあります。
本章のコードはすべて `response["content"]` をそのまま履歴へ渡す作りにしています。
`thinking` ブロックが混ざっていてもいなくても、同じコードで正しく動きます。
思考の深さを調整する `effort` パラメータについては、第7章で詳しく扱います。

> **POINT**: 応答の `content` は「加工せず、そのまま履歴に戻す」。これだけで `thinking` ブロック・`text`・`tool_use` の順序や署名をすべて正しく保てます。自分で並べ直したり、要らなそうなブロックを削ったりしないことが、トラブルを防ぐ一番の近道です。

ここまでで、Tool Use の全体像がつかめました。
Claudeは道具の使用を「依頼」し、私たちのコードが「実行」して結果を返します。
次の節では、その依頼の出発点となるツール定義を、天気ツールを題材に実際に書いていきます。

---

## 5.2 ツール定義とJSON Schema

Tool Use の流れが分かったところで、いよいよツールを作ります。
ツールを作るとは、具体的に何を書くことなのでしょうか。
答えは「Claudeに渡す説明書」と「実際に動くPython関数」の2つを、ペアで書くことです。
説明書だけでは何も実行されず、関数だけではClaudeがその存在を知りません。
本節では、天気を返す `get_weather` ツールを例にします。
この2つをそろえて、`tools/weather.py` にまとめます。

### ツール定義の3つの項目

APIに渡すツール定義は、次の3つの項目を持つ辞書です。

| 項目 | 役割 | 例 |
|---|---|---|
| `name` | ツールの名前。Claudeが `tool_use` で指定してくる識別子 | `"get_weather"` |
| `description` | ツールの説明。いつ・何のために使うかをClaudeに伝える | `"指定した都市の現在の天気を取得します。…"` |
| `input_schema` | 引数の形。JSON Schema で書く | `{"type": "object", "properties": {...}}` |

`name` は、英小文字とアンダースコアを使った、動詞から始まる名前にするのが一般的です。
理想は、何をするかが名前だけで伝わる形です。
たとえば `get_weather`、`search_documents`、`create_ticket` のような名前です。
名前に使える文字には制限があり、英数字・アンダースコア・ハイフンで1〜128文字にします。
日本語やスペースは使えないので注意してください。
この `name` は、後でClaudeからの依頼を受けたときに「どの関数を呼ぶか」を決めるキーにもなります。

`description` は、Claudeがツールを選ぶときにもっとも重視する項目です。
`input_schema` は、Claudeが引数を組み立てるときの設計図になります。
この2つの書き方は奥が深いので、順番に見ていきましょう。

<figure id="fig-5-3">
<svg width="605" height="420" viewBox="0 0 605 420"
     xmlns="http://www.w3.org/2000/svg"
     font-family="'Noto Sans JP',sans-serif">
  <defs>
    <marker id="f5_3_arr53" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#333" stroke-width="1.5"/>
    </marker>
    <marker id="f5_3_arr53a" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#2b6cb0" stroke-width="1.5"/>
    </marker>
  </defs>
  <rect x="0" y="0" width="605" height="420" fill="#ffffff"/>
  <rect x="15" y="15" width="420" height="370" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="25" y="32" text-anchor="start" dominant-baseline="central" font-size="12" fill="#1a1a1a" font-weight="bold">GET_WEATHER_TOOL（ツール定義の dict）</text>
  <rect x="30" y="45" width="390" height="30" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.1"/>
  <text x="40" y="60.0" text-anchor="start" dominant-baseline="central" font-size="12" fill="#1a1a1a" font-family="Consolas,monospace">"name": "get_weather"</text>
  <rect x="30" y="85" width="390" height="30" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.1"/>
  <text x="40" y="100.0" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">"description": "指定した都市の「現在の」天気を取得します。…"</text>
  <rect x="30" y="125" width="390" height="250" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="40" y="141" text-anchor="start" dominant-baseline="central" font-size="12" fill="#1a1a1a" font-family="Consolas,monospace">"input_schema": {</text>
  <text x="55" y="162" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">"type": "object",</text>
  <rect x="50" y="176" width="355" height="152" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.1"/>
  <text x="60" y="192" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">"properties": {</text>
  <rect x="65" y="205" width="325" height="50" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="227.5" y="222.3" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">"city": {"type": "string",</text>
  <text x="227.5" y="237.7" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">"description": "天気を調べる都市名…"}</text>
  <rect x="65" y="265" width="325" height="50" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="227.5" y="282.3" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">"unit": {"type": "string",</text>
  <text x="227.5" y="297.7" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">"enum": ["celsius", "fahrenheit"]}</text>
  <text x="55" y="350" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">"required": ["city"]</text>
  <path d="M420 60 L445 60" fill="none" stroke="#999" stroke-width="1.2" stroke-dasharray="4,3"/>
  <text x="450" y="52" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">tool_use で指定される</text>
  <text x="450" y="68" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">識別子（関数を選ぶキー）</text>
  <path d="M420 100 L445 100" fill="none" stroke="#999" stroke-width="1.2" stroke-dasharray="4,3"/>
  <text x="450" y="92" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">いつ・何のために</text>
  <text x="450" y="108" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">使うかを伝える</text>
  <path d="M420 150 L445 150" fill="none" stroke="#999" stroke-width="1.2" stroke-dasharray="4,3"/>
  <text x="450" y="142" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">引数の形を</text>
  <text x="450" y="158" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">JSON Schema で書く</text>
  <path d="M390 230 L445 230" fill="none" stroke="#999" stroke-width="1.2" stroke-dasharray="4,3"/>
  <text x="450" y="222" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">キー ＝ 引数名</text>
  <text x="450" y="238" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">type ＝ 型ヒント</text>
  <path d="M390 290 L445 290" fill="none" stroke="#999" stroke-width="1.2" stroke-dasharray="4,3"/>
  <text x="450" y="282" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">enum で値の</text>
  <text x="450" y="298" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">候補を限定する</text>
  <path d="M420 350 L445 350" fill="none" stroke="#999" stroke-width="1.2" stroke-dasharray="4,3"/>
  <text x="450" y="342" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">必須の引数</text>
  <text x="450" y="358" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">（unit は省略可）</text>
</svg>
  <figcaption>図5.3: ツール定義の構造</figcaption>
</figure>

### JSON Schemaの基本

JSON Schema とは、JSONデータの「形」を記述するための標準的な書き方です。
「このデータはオブジェクトで、`city` という文字列のキーを必ず持つ」といった約束を、JSONそのもので表現します。
Web APIの仕様書やフォームの入力チェックなど、幅広い場面で使われています。
ツールの `input_schema` では、その中でもごく基本的なキーワードだけを使えば十分です。
本書で使うキーワードは、次の5つです。

| キーワード | 意味 | 例 |
|---|---|---|
| `type` | 値の型 | `"object"`・`"string"`・`"number"`・`"integer"`・`"boolean"`・`"array"` |
| `properties` | オブジェクトが持つキーと、それぞれの形 | `{"city": {"type": "string"}}` |
| `required` | 必ず指定しなければならないキーの一覧 | `["city"]` |
| `enum` | 取りうる値の候補を限定する | `["celsius", "fahrenheit"]` |
| `description` | そのキーの意味の説明 | `"都市名（英語表記）"` |

`input_schema` の一番外側は、必ず `"type": "object"` にします。
ツールの引数は「キーと値の組」として渡されるので、全体はオブジェクトになるからです。
その中の `properties` に、引数ごとの名前と型を書いていきます。
Pythonの関数に置き換えると、`properties` のキーが引数名、`type` が型ヒントに相当します。
`required` は、デフォルト値を持たない引数の一覧だと捉えるとよいでしょう。

`enum` は、値の候補が決まっている引数でとても役立ちます。
たとえば気温の単位は「摂氏」か「華氏」のどちらかしかありません。
そこで、`enum` で `["celsius", "fahrenheit"]` と限定します。
こうすれば、`"C"` や `"摂氏"` のような予想外の値が届く心配が減ります。
受け取る側の関数も、2通りの値だけを想定して書けるので、実装が単純になります。
候補が少なく決まっている引数には、積極的に `enum` を使いましょう。

> **NOTE**: JSON Schema には、ほかにも多くのキーワードがあります。たとえば `minimum`（最小値）、`maxLength`（最大文字数）、`items`（配列の要素の形）などです。ただし、スキーマに書いた制約をClaudeが必ず守る保証は、通常の Tool Use にはありません。型や必須キーを確実に守らせたい場合は、第6章で扱う `strict: true` を使います。なお、strict では数値・長さの制約は使えず、書くと400エラーになります。`minimum`・`maximum`・`minLength`・`maxLength`・`maxItems` などが該当します。`minItems` も0か1のみです。こうした範囲の確認は、受け取る側の関数で必ず行いましょう。

### Claudeが迷わない description の書き方

`description` は、ツールの成否を左右するもっとも重要な項目です。
Anthropic の公式ドキュメントでも、ツールの説明はできるだけ詳しく書くことが推奨されています。
目安として、少なくとも3〜4文程度は書くとよいでしょう。
説明に盛り込みたい要素は、次の4つです。

1. **何をするツールか**: 「指定した都市の現在の天気を取得します」
2. **いつ使うべきか**: 「ユーザーが天気・気温・湿度について尋ねたときに使います」
3. **何を返すか**: 「天気の概況、気温、湿度をJSON形式で返します」
4. **何ができないか**: 「天気予報や過去の天気は取得できません」

4つ目の「できないこと」は、つい書き忘れがちです。
しかし、これを書いておくと、Claudeが「明日の天気」を聞かれたときに無理にこのツールを使わなくなります。
代わりに「このツールでは明日の予報は分かりません」と正直に答えてくれるようになります。
ツールの限界を伝えることは、Claudeの誤用を防ぐうえで、機能の説明と同じくらい大切です。

悪い例と良い例を比べてみましょう。

```text
# 悪い例（短すぎて、いつ・どう使うかが分からない）
天気を取得する。

# 良い例（目的・使う場面・戻り値・限界・引数の注意が書かれている）
指定した都市の「現在の」天気を取得します。
ユーザーが天気・気温・湿度・風について尋ねたときに使います。
天気の概況、気温、湿度、風速をJSON形式で返します。
天気予報（明日以降）や過去の天気は取得できません。
都市名は英語表記（例: Tokyo, Osaka）で指定してください。
```

良い例の最後の1文にも注目してください。
「都市名は英語表記で」という、引数の渡し方に関する注意が書かれています。
これは、後で接続する天気APIが英語の都市名で検索するほうが確実だから入れている一文です。
ツール側の都合を書いておけば、ユーザーが「東京」と書いても、Claudeは `"Tokyo"` に変換して渡します。
説明文は、Claudeとツールのあいだの「通訳」の役割も果たしているわけです。

> **POINT**: description は「Claudeに読ませる文章」です。人間向けの簡潔なコメントではなく、新しく入った同僚にツールの使い方を説明するつもりで書きましょう。目的・使う場面・戻り値・限界の4点に、引数の渡し方の注意を添えると、ツールの誤用が目に見えて減ります。

### `tools/weather.py` を作る（ダミー版）

それでは、天気ツールを書きます。
最初は外部APIを呼ばず、決まった値を返す「ダミー版」から始めます。
いきなり本物のAPIをつなぐと、うまく動かないときに原因の切り分けが難しくなるからです。
まずはダミーでループの仕組みを完成させ、5.4 節の最後で本物の天気APIに差し替えます。
「動く最小構成を作ってから、部品を本物に替えていく」のは、エージェント開発の基本的な進め方です。

まず、プロジェクトのルートに `tools` フォルダーを作ります。
ルートとは、第2章から使っている `agent-from-scratch/` のことです。
その中に、空の `__init__.py` を置きます。

```bash
# agent-from-scratch/ で実行する: tools パッケージを作る
mkdir tools
# 空の __init__.py を作る（macOS / Linux / Git Bash）
touch tools/__init__.py
```

WindowsのPowerShellには `touch` がありません。
代わりに `New-Item tools/__init__.py` を使います。
VS Codeのエクスプローラーから「新しいファイル」で作ってもかまいません。
中身が空でも、ファイルさえあれば `tools` は1つのパッケージとして扱われます。

```python
# tools/__init__.py
# このフォルダーを Python パッケージとして扱うための目印（中身は空でよい）
```

`__init__.py` は、「このフォルダーはPythonのパッケージです」という目印になるファイルです。
最近のPythonでは、このファイルがなくても import できる場合があります。
しかし、明示しておくほうがエディタの補完やテストツールとの相性がよく、意図も伝わります。
本書では第6章以降も、`tools/files.py`、`tools/memory.py` とツールを増やします。
そのため、ここで器を作っておきます。

続いて、本体の `tools/weather.py` を新規作成します。

```python
# tools/weather.py
"""天気ツール（第5章・ダミー版）。

Claude に渡す「説明書」（GET_WEATHER_TOOL）と、
実際に動く Python 関数（get_weather）をペアで定義する。
"""

import json

# --- Claude に渡すツール定義（説明書） -------------------------------
GET_WEATHER_TOOL: dict = {
    # Claude が tool_use で指定してくる名前。関数を選ぶキーにもなる
    "name": "get_weather",
    # いつ・何のために使うか。Claude はここを読んでツールを選ぶ
    "description": (
        "指定した都市の「現在の」天気を取得します。"
        "ユーザーが天気・気温・湿度・風について尋ねたときに使います。"
        "天気の概況、気温、湿度、風速をJSON形式で返します。"
        "天気予報（明日以降）や過去の天気は取得できません。"
        "都市名は英語表記（例: Tokyo, Osaka）で指定してください。"
    ),
    # 引数の形を JSON Schema で書く
    "input_schema": {
        "type": "object",  # 引数全体はキーと値の組（オブジェクト）
        "properties": {
            "city": {
                "type": "string",
                "description": "天気を調べる都市名。英語表記（例: Tokyo, Sapporo）。",
            },
            "unit": {
                "type": "string",
                "enum": ["celsius", "fahrenheit"],  # 取りうる値を2つに限定
                "description": "気温の単位。指定がなければ celsius（摂氏）。",
            },
        },
        "required": ["city"],  # city は必須、unit は省略可
    },
}

# --- ダミーの天気データ（5.4 節で本物の API に差し替える） ---------------
_DUMMY_WEATHER: dict[str, dict] = {
    "tokyo": {"name": "東京", "condition": "晴れ", "temp_c": 18.5, "humidity": 55, "wind_kmh": 9.0},
    "osaka": {"name": "大阪", "condition": "曇り", "temp_c": 20.1, "humidity": 62, "wind_kmh": 6.5},
    "sapporo": {"name": "札幌", "condition": "雪", "temp_c": 2.3, "humidity": 80, "wind_kmh": 14.2},
}


# --- 実際に動く関数（厨房） -----------------------------------------
def get_weather(city: str, unit: str = "celsius") -> str:
    """都市名を受け取り、天気情報を JSON 文字列で返す。"""
    # 大文字小文字や前後の空白の揺れを吸収してから辞書を引く
    data = _DUMMY_WEATHER.get(city.strip().lower())
    if data is None:
        # 知らない都市は例外にする（5.4 節で is_error 付きの結果に変換する）
        known = ", ".join(key.title() for key in _DUMMY_WEATHER)
        raise ValueError(f"都市 '{city}' のデータがありません。対応都市: {known}")

    # 単位に合わせて気温を換算する
    if unit == "fahrenheit":
        temperature = round(data["temp_c"] * 9 / 5 + 32, 1)
        unit_label = "°F"
    else:
        temperature = data["temp_c"]
        unit_label = "°C"

    # Claude が読みやすいよう、キー名の分かる JSON 文字列で返す
    result = {
        "city": data["name"],
        "condition": data["condition"],
        "temperature": f"{temperature}{unit_label}",
        "humidity": f"{data['humidity']}%",
        "wind_speed": f"{data['wind_kmh']} km/h",
        "source": "dummy",  # ダミーデータであることを明示しておく
    }
    return json.dumps(result, ensure_ascii=False)


# --- 単体テスト用: python -m tools.weather で関数だけを試す ---------------
if __name__ == "__main__":
    print(get_weather("Tokyo"))
    print(get_weather("sapporo", unit="fahrenheit"))
```

### コードを1ブロックずつ読む

まず冒頭の `GET_WEATHER_TOOL` です。
これがAPIの `tools` に渡す説明書で、Python上はただの辞書です。
名前を大文字の定数にしているのは、プログラムの実行中に書き換えない値だと示すためです。
`description` は長いので、括弧で囲んだ複数の文字列を並べています。
Pythonでは、隣り合う文字列リテラルは自動で1つにつながるので、1本の長い説明文になります。

`input_schema` の中身は、先ほどの JSON Schema の表をそのまま使っています。
`city` は文字列で必須、`unit` は `celsius` と `fahrenheit` の2択で省略可能です。
各引数にも `description` を付けている点に注目してください。
ツール全体の説明とは別に、引数ごとの説明もClaudeは読んでいます。
「英語表記」という注意を、ツールの説明と引数の説明の両方に書いているのは、念押しのためです。

次の `_DUMMY_WEATHER` は、3都市分の固定データです。
名前の先頭のアンダースコアは、「このモジュールの内部でだけ使う」という慣習的な目印です。
外部から import すること自体はできますが、そうしないでほしいという意思表示になります。
5.4 節で本物のAPIに差し替えると、このデータは丸ごと不要になります。

`get_weather` 関数が、実際の処理を行う「厨房」です。
引数名 `city` と `unit` は、`input_schema` の `properties` のキーと完全に一致させています。
これは後で、Claudeが送ってくる `input` の辞書をそのまま関数に渡すためです。
`unit` のデフォルト値を `"celsius"` にしているのは、`required` に含めていない引数だからです。
Claudeが `unit` を省略してきても、関数が困らないようにしています。

知らない都市を渡されたときは、`ValueError` を投げています。
エラーメッセージに対応都市の一覧を入れているのは、Claudeがこのメッセージを読むからです。
5.4 節では、この例外を捕まえて「失敗した」という印の付いた結果としてClaudeに返します。
メッセージを読んだClaudeは、対応都市にないと理解し、ユーザーに説明したり別の都市で試したりできます。
エラーメッセージも、Claudeへの説明書の一部だと考えて書くのがコツです。

戻り値は、辞書を `json.dumps` で文字列にしたものです。
`ensure_ascii=False` は、日本語を `東` のようなエスケープにせず、そのまま出力するための指定です。
エスケープされた文字列でもClaudeは読めますが、トークン数が増えるうえ、ログも読みにくくなります。
`"source": "dummy"` を入れているのは、デバッグ中に本物とダミーを取り違えないための工夫です。
5.4 節の本物版では、ここが `"open-meteo"` に変わります。

> **NOTE**: ツールの戻り値は文字列にしています。`tool_result` の `content` に、文字列をそのまま入れられるからです。`content` には、テキストや画像などのブロックの配列を入れることもできます。本書では、扱いやすさを優先して文字列（JSON形式の文字列を含む）で統一します。

### 関数だけを単体で動かす

ツールをClaudeにつなぐ前に、関数が正しく動くかを単体で確認しておきます。
ファイルの末尾には `if __name__ == "__main__":` のブロックがあります。
このブロックは、ファイルを直接実行したときだけ動きます。
`tools` パッケージの中のファイルなので、`-m` オプションを付けてモジュールとして実行します。

```bash
# agent-from-scratch/ で実行する: tools/weather.py を単体で動かす
uv run python -m tools.weather
```

```text
{"city": "東京", "condition": "晴れ", "temperature": "18.5°C", "humidity": "55%", "wind_speed": "9.0 km/h", "source": "dummy"}
{"city": "札幌", "condition": "雪", "temperature": "36.1°F", "humidity": "80%", "wind_speed": "14.2 km/h", "source": "dummy"}
```

1行目は東京の摂氏、2行目は札幌の華氏です。
`sapporo` を小文字で渡しても正しく引けていることから、表記の揺れの吸収も確認できます。
2.3°C を華氏に換算すると 36.14°F で、小数第1位に丸めて 36.1°F になっています。
ここでエラーが出る場合は、Claudeとは関係のない、純粋なPythonの問題です。
APIを呼ぶ前に関数単体を確かめておくと、後で問題が起きたときの切り分けがとても楽になります。

> **WARNING**: このファイルは、ファイルパスで実行しても動きます。たとえば `uv run python tools/weather.py` のような実行方法です。ただし、`from tools.weather import ...` を使うほかのファイルと、実行方法をそろえておきたいところです。そのため、パッケージ内のファイルは `-m tools.weather` の形で実行する習慣をつけておくと安心です。

### tool_useブロックを観察する

関数が動いたので、次はClaudeにこのツールを渡したとき、どんな応答が返ってくるかを観察します。
ここではファイルを作らず、Pythonの対話モード（REPL）で1行ずつ試してみましょう。
対話モードは、結果をその場で確かめながら進められるので、APIの観察に向いています。
第4章で作った `llm_client.py` がプロジェクトのルートにあることを確認してから始めてください。

```bash
# agent-from-scratch/ で実行する: Python の対話モードを起動する
uv run python
```

```pycon
# 対話モードで1行ずつ入力する（>>> はプロンプトなので入力しない）
>>> from llm_client import call_messages, get_tool_uses
>>> from tools.weather import GET_WEATHER_TOOL
>>> messages = [{"role": "user", "content": "東京の今の天気を教えてください。"}]
>>> response = call_messages(messages, tools=[GET_WEATHER_TOOL])
>>> response["stop_reason"]
'tool_use'
>>> for block in response["content"]:
...     print(block)
...
{'type': 'text', 'text': '東京の現在の天気を確認しますね。'}
{'type': 'tool_use', 'id': 'toolu_01Hq7cJxW8vPz3sN5kRbT2aL', 'name': 'get_weather', 'input': {'city': 'Tokyo'}}
```

`stop_reason` が `'tool_use'` になっていることが、まず確認できます。
Claudeは「答え終わった」のではなく、「ツールの結果待ち」で止まっています。
`content` の中には2つのブロックが入っています。
1つ目は「確認しますね」という `text` ブロックで、先ほど説明した途中経過のつぶやきです。
2つ目が、本命の `tool_use` ブロックです。

`tool_use` ブロックには、3つの大切なフィールドがあります。

| フィールド | 中身 | 使いみち |
|---|---|---|
| `id` | `toolu_` で始まる一意の識別子 | `tool_result` の `tool_use_id` に入れて、結果と依頼を対応させる |
| `name` | 使いたいツールの名前 | どのPython関数を呼ぶかを決める |
| `input` | 引数の辞書（JSONとしてパース済み） | 関数にそのまま渡す |

注目してほしいのは `input` の中身です。
ユーザーは日本語で「東京」と書いたのに、Claudeは `{'city': 'Tokyo'}` と英語に変換しています。
description に書いた「英語表記で指定してください」という指示が、きちんと効いていることが分かります。
また `unit` は省略されています。
`required` に含めておらず、ユーザーも単位を指定していないので、Claudeは送る必要がないと判断したのです。

もう1つ大切なのは、`input` が文字列ではなく、すでにPythonの辞書になっている点です。
`llm_client.py` がレスポンスのJSONをパースしているので、`input` も辞書として取り出せます。
`block["input"]["city"]` のように、キーで直接扱いましょう。
`"Tokyo" in str(block)` のように文字列として照合すると、表記の揺れに弱いコードになってしまいます。
`id` の値は呼び出すたびに変わるので、表示される文字列はあなたの環境と一致しなくて問題ありません。

> **NOTE**: 実行すると、`content` の先頭に次のようなブロックが表示されることがあります。`{'type': 'thinking', 'thinking': '', 'signature': '...'}` という形です。5.1 節で触れた adaptive thinking のブロックです。中身は空で、気にする必要はありません。次の節で履歴に戻すときも、`content` をそのまま使えば正しく扱えます。

続けて、`get_tool_uses` ヘルパーも試しておきましょう。
第4章で作ったこの関数は、`content` の中から `type` が `tool_use` のブロックだけを集めて返します。

```pycon
# 対話モードの続き: tool_use ブロックだけを取り出す
>>> tool_uses = get_tool_uses(response)
>>> len(tool_uses)
1
>>> tool_uses[0]["name"], tool_uses[0]["input"]
('get_weather', {'city': 'Tokyo'})
>>> exit()
```

`content[0]` のように位置を決め打ちせず、`type` で判定して取り出すのが大切です。
今回は `text` が先頭にありましたが、`tool_use` だけの応答や、`thinking` が先頭に来る応答もあります。
`content[1]` と決め打ちしたコードは、そうした応答で簡単に壊れます。
`get_tool_uses` のように `type` で判定するヘルパーを通しておけば、ブロックの並びが変わっても安全です。
これで「依頼」の形が分かりました。次は、この依頼に「結果」を返す側を実装します。

---

## 5.3 tool_useとtool_resultの往復

前節で、Claudeが `tool_use` ブロックで「ツールを使いたい」と依頼してくる様子を観察しました。
しかし、依頼を受け取っただけでは、まだ東京の天気は分かりません。
依頼に応えて関数を実行し、その結果をClaudeに届けて初めて、最終回答が返ってきます。
では、結果はどんな形で、どのメッセージに入れて送ればよいのでしょうか。
本節では、この1往復をループを使わずに手書きし、`one_shot_tool.py` として動かします。

### 履歴はどう積み上がるのか

コードを書く前に、1往復のあいだに `messages` がどう育っていくかを確認しておきます。
第3章で作った会話アプリでは、user と assistant が交互に並ぶ履歴を自分で管理しました。
Tool Use でも、この「交互に並べる」というルールは変わりません。
変わるのは、assistant と user の `content` に、文字列ではなくブロックの配列が入る点です。
1往復を終えた時点の `messages` は、次の4つのメッセージになります。

| 順番 | role | content の中身 | 誰が作るか |
|---|---|---|---|
| 1 | `user` | 「東京の今の天気を教えてください。」 | ユーザー（私たちのコード） |
| 2 | `assistant` | `text`（確認します）＋ `tool_use`（get_weather / Tokyo） | Claude（1回目の応答をそのまま） |
| 3 | `user` | `tool_result`（tool_use_id と天気のJSON） | 私たちのコード |
| 4 | `assistant` | `text`（東京は晴れ、18.5°Cです…） | Claude（2回目の応答） |

2回目のAPI呼び出しでは、1〜3番目までを送ります。
4番目は、その呼び出しの応答として返ってくるものです。
ここで意外に感じるかもしれないのが、3番目の `role` が `user` になっている点です。
ツールの結果を送っているのは、ユーザー本人ではありません。
しかし、APIの上では「Claudeではない側」はすべて `user` です。
Messages API の役割は `user` と `assistant` の2つしかありません。
そのため、ツールの結果も `user` 側から届ける決まりになっています。

<figure id="fig-5-4">
<svg width="605" height="345" viewBox="0 0 605 345"
     xmlns="http://www.w3.org/2000/svg"
     font-family="'Noto Sans JP',sans-serif">
  <defs>
    <marker id="f5_4_arr54" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#333" stroke-width="1.5"/>
    </marker>
    <marker id="f5_4_arr54a" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#2b6cb0" stroke-width="1.5"/>
    </marker>
  </defs>
  <rect x="0" y="0" width="605" height="345" fill="#ffffff"/>
  <rect x="20" y="20" width="440" height="55" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="30" y="38" text-anchor="start" dominant-baseline="central" font-size="12" fill="#1a1a1a" font-family="Consolas,monospace" font-weight="bold">1  user</text>
  <text x="30" y="57" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">ユーザーの質問</text>
  <rect x="130" y="28" width="320" height="39" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.1"/>
  <text x="290.0" y="47.5" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">「東京の今の天気を教えてください。」</text>
  <rect x="20" y="90" width="440" height="55" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="30" y="108" text-anchor="start" dominant-baseline="central" font-size="12" fill="#1a1a1a" font-family="Consolas,monospace" font-weight="bold">2  assistant</text>
  <text x="30" y="127" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">1回目の応答</text>
  <rect x="130" y="98" width="110" height="39" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.1"/>
  <text x="185.0" y="109.8" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">text</text>
  <text x="185.0" y="125.2" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">確認します</text>
  <rect x="250" y="98" width="200" height="39" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="350.0" y="109.8" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace" font-weight="bold">tool_use</text>
  <text x="350.0" y="125.2" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">get_weather / Tokyo</text>
  <rect x="20" y="160" width="440" height="55" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="30" y="178" text-anchor="start" dominant-baseline="central" font-size="12" fill="#1a1a1a" font-family="Consolas,monospace" font-weight="bold">3  user</text>
  <text x="30" y="197" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">私たちのコード</text>
  <rect x="130" y="168" width="320" height="39" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="290.0" y="179.8" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace" font-weight="bold">tool_result</text>
  <text x="290.0" y="195.2" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">tool_use_id ＋ 天気のJSON</text>
  <rect x="20" y="230" width="440" height="55" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="30" y="248" text-anchor="start" dominant-baseline="central" font-size="12" fill="#1a1a1a" font-family="Consolas,monospace" font-weight="bold">4  assistant</text>
  <text x="30" y="267" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">2回目の応答</text>
  <rect x="130" y="238" width="320" height="39" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.1"/>
  <text x="290.0" y="249.8" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">text</text>
  <text x="290.0" y="265.2" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">東京は晴れ、18.5°Cです…</text>
  <path d="M350 137 L350 168" fill="none" stroke="#2b6cb0" stroke-width="1.3" stroke-dasharray="4,3"/>
  <text x="358" y="152.5" text-anchor="start" dominant-baseline="central" font-size="11" fill="#2b6cb0" font-weight="bold">id が対応</text>
  <path d="M468 20 L476 20 L476 215 L468 215" fill="none" stroke="#333" stroke-width="1.3"/>
  <text x="486" y="102" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-weight="bold">2回目の</text>
  <text x="486" y="118" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-weight="bold">呼び出しで</text>
  <text x="486" y="134" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-weight="bold">送る</text>
  <path d="M468 230 L476 230 L476 285 L468 285" fill="none" stroke="#333" stroke-width="1.3"/>
  <text x="486" y="250" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-weight="bold">その応答</text>
  <text x="486" y="266" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">（4番目）</text>
</svg>
  <figcaption>図5.4: 1往復で積み上がる履歴</figcaption>
</figure>

### tool_resultの形

3番目のメッセージに入れる `tool_result` ブロックの形を確認しましょう。

```json
{
  "role": "user",
  "content": [
    {
      "type": "tool_result",
      "tool_use_id": "toolu_01Hq7cJxW8vPz3sN5kRbT2aL",
      "content": "{\"city\": \"東京\", \"condition\": \"晴れ\", \"temperature\": \"18.5°C\"}"
    }
  ]
}
```

`tool_result` ブロックのフィールドは、次の4つです。

| フィールド | 必須 | 中身 |
|---|---|---|
| `type` | 必須 | 常に `"tool_result"` |
| `tool_use_id` | 必須 | 対応する `tool_use` ブロックの `id` をそのまま入れる |
| `content` | 任意 | ツールの実行結果。文字列、またはテキスト・画像・ドキュメントなどのブロックの配列 |
| `is_error` | 任意 | 実行に失敗したときに `true` を入れる。省略時は成功扱い |

もっとも大切なのは `tool_use_id` です。
これは「どの依頼に対する結果か」を示す、伝票番号のようなものです。
1つの応答に `tool_use` が複数ある場合、Claudeは結果の順番ではなく、この番号で依頼と結果を対応させます。
番号を間違えたり、存在しない番号を入れたりすると、APIは 400 エラーを返します。
`tool_use` の `id` を、手で書き写さずに変数からそのまま入れることが大切です。

`is_error` は、ツールの実行が失敗したことをClaudeに伝えるためのフラグです。
たとえば天気APIに接続できなかったときは、`content` にエラーの内容を書きます。
そして、`is_error` を `true` にして返します。
Claudeはそれを読んで、別の方法を試したり、ユーザーに失敗を説明したりします。
本節の `one_shot_tool.py` では、まず成功の場合だけを扱います。
`is_error` を使った失敗の扱いは、次の 5.4 節の `agent.py` で組み込みます。

> **WARNING**: `tool_result` を含む user メッセージに、説明の文章も添えたい場合があります。その場合は、`tool_result` ブロックを配列の先頭に置き、`text` ブロックはその後ろに置きます。`text` を先に置くと 400 エラーになります。また、`tool_result` の数にも決まりがあります。直前の assistant メッセージにある `tool_use` すべてに対して、1つずつ用意する必要があります。

### one_shot_tool.pyを書く

それでは、1往復を手書きするスクリプトをプロジェクトのルートに新規作成します。
このファイルは「仕組みを目で見るため」の教材用スクリプトです。
ループを使わず、1回目の呼び出し、ツールの実行、2回目の呼び出しを、上から順に並べて書きます。
各段階で `print` を入れ、何が起きているかを確認できるようにしています。

```python
# one_shot_tool.py
"""Tool Use の1往復を、ループを使わずに手書きで確かめるスクリプト（第5章）。"""

import json

from llm_client import call_messages, extract_text, get_tool_uses, tracker
from tools.weather import GET_WEATHER_TOOL, get_weather

# Claude に渡すツールの一覧（今回は天気ツール1つだけ）
TOOLS = [GET_WEATHER_TOOL]


def main() -> None:
    # --- 1. ユーザーの質問で履歴を始める ------------------------------
    messages: list[dict] = [
        {"role": "user", "content": "東京の今の天気を教えてください。"},
    ]

    # --- 2. 1回目の呼び出し: ツールを渡して質問する ----------------------
    first = call_messages(messages, tools=TOOLS)
    print(f"[1回目] stop_reason = {first['stop_reason']}")

    # ツールを使わずに答えた場合は、その回答を表示して終わる
    if first["stop_reason"] != "tool_use":
        print(extract_text(first))
        return

    # --- 3. assistant の応答を「そのまま」履歴に追加する --------------------
    messages.append({"role": "assistant", "content": first["content"]})

    # --- 4. 依頼されたツールを実行し、tool_result を作る -------------------
    tool_results: list[dict] = []
    for tool_use in get_tool_uses(first):
        print(f"[依頼] id={tool_use['id']} name={tool_use['name']} input={tool_use['input']}")
        # input はパース済みの辞書なので、キーワード引数として展開して渡す
        result = get_weather(**tool_use["input"])
        print(f"[結果] {result}")
        tool_results.append(
            {
                "type": "tool_result",
                "tool_use_id": tool_use["id"],  # どの依頼への結果かを対応させる
                "content": result,
            }
        )

    # --- 5. すべての結果を1つの user メッセージにまとめて追加する -------------
    messages.append({"role": "user", "content": tool_results})

    # --- 6. 2回目の呼び出し: 結果を踏まえた最終回答を受け取る ----------------
    second = call_messages(messages, tools=TOOLS)
    print(f"[2回目] stop_reason = {second['stop_reason']}")
    print("[最終回答]")
    print(extract_text(second))

    # --- 7. 履歴の形とコストを確認する -------------------------------------
    print(f"[履歴] メッセージ数 = {len(messages)}")
    for i, message in enumerate(messages, start=1):
        # content が配列なら、ブロックの type だけを並べて表示する
        content = message["content"]
        kinds = content if isinstance(content, str) else [block["type"] for block in content]
        print(f"  {i}. {message['role']}: {json.dumps(kinds, ensure_ascii=False)}")
    print(tracker.summary())


if __name__ == "__main__":
    main()
```

### コードを1ブロックずつ読む

冒頭の import では、第4章の `llm_client.py` から4つの名前を読み込んでいます。
それぞれの役割は次のとおりです。

- `call_messages`: APIの呼び出し
- `extract_text`: `text` ブロックの連結
- `get_tool_uses`: `tool_use` ブロックの抽出

`tracker` は、呼び出しごとのトークン数とコストを自動で集計しているモジュール共通のインスタンスでした。
HTTPのヘッダーやリトライの処理は、すべて `call_messages` の中に隠れています。
第4章で土台を作っておいたおかげで、本章のコードは Tool Use の本質だけに集中できます。

1番目のブロックでは、ユーザーの質問で履歴を始めています。
`content` には文字列をそのまま入れています。
文字列は `[{"type": "text", "text": "..."}]` の省略形です。
APIはどちらの書き方も受け付けます。
ユーザーの質問のような単純なテキストは、読みやすい文字列の形で書くのがおすすめです。

2番目のブロックが、1回目の呼び出しです。
`tools=TOOLS` で天気ツールの説明書を渡しています。
直後の `if` 文では、`stop_reason` が `"tool_use"` でなければ、回答を表示して終えています。
「天気」とは関係のない質問に差し替えると、Claudeはツールを使わずに `"end_turn"` で答えるからです。
ツールを渡しても、使うかどうかを決めるのはClaudeだという点を、この分岐が表しています。

3番目のブロックが、本節でもっとも大切な1行です。
ここでは `first["content"]` を加工せずに使っています。
そのまま assistant メッセージの `content` に入れているのです。
`text` ブロックも `tool_use` ブロックも、`thinking` ブロックがあればそれも、すべてそのまま残ります。
ここで `tool_use` だけを抜き出したり、`text` だけを文字列にしたりしてはいけません。
2回目のリクエストで、Claudeは自分が出した `tool_use` を履歴の中に見つけます。
そして、それを `tool_result` と照合するからです。

4番目のブロックでは、`get_tool_uses` で依頼を取り出し、1つずつ実行しています。
`get_weather(**tool_use["input"])` の `**` は、辞書をキーワード引数に展開する書き方です。
`{"city": "Tokyo"}` は `get_weather(city="Tokyo")` として渡されます。
引数名をスキーマのキーと一致させておいたのは、この展開を可能にするためでした。
結果は `tool_use_id` を添えた `tool_result` ブロックにして、リストに集めていきます。

5番目のブロックでは、集めた `tool_result` をまとめて1つの user メッセージとして追加しています。
今回は依頼が1つなので結果も1つですが、依頼が複数でも1つのメッセージにまとめるのがルールです。
`for` ループの中で1つずつ `messages.append` すると、user メッセージが連続してしまいます。
これはコラムで紹介する「よくあるつまずき」の1つなので、ここで形を覚えておきましょう。

6番目のブロックが2回目の呼び出しです。
1回目と同じ `tools` を渡している点に注意してください。
履歴の中に `tool_use` があるので、その定義がリクエストに含まれているほうが一貫しています。
また、結果を見たClaudeが「もう1回調べたい」と考えたときに、ツールが使える状態にしておく意味もあります。
最後の7番目のブロックは、履歴の形とコストを確認するための表示です。

> **NOTE**: このスクリプトは、2回目の応答が再び `"tool_use"` になった場合を考慮していません。たとえば「東京と大阪」のように複数の調べものが必要な質問では、2回目でも追加の依頼が来ることがあります。この「何往復になるか分からない」問題を解決するのが、次節のループです。

### 実行して1往復を確かめる

スクリプトを実行してみましょう。

```bash
# agent-from-scratch/ で実行する: Tool Use の1往復を試す
uv run python one_shot_tool.py
```

```text
[1回目] stop_reason = tool_use
[依頼] id=toolu_01Hq7cJxW8vPz3sN5kRbT2aL name=get_weather input={'city': 'Tokyo'}
[結果] {"city": "東京", "condition": "晴れ", "temperature": "18.5°C", "humidity": "55%", "wind_speed": "9.0 km/h", "source": "dummy"}
[2回目] stop_reason = end_turn
[最終回答]
東京の現在の天気は晴れです。気温は18.5°C、湿度は55%で、風速は9.0 km/hと穏やかです。
過ごしやすい陽気なので、外出には軽い上着があれば十分でしょう。
[履歴] メッセージ数 = 3
  1. user: "東京の今の天気を教えてください。"
  2. assistant: ["text", "tool_use"]
  3. user: ["tool_result"]
calls=2 input=1,454 output=190 cache_write=0 cache_read=0 total=$0.0096
```

出力を上から読んでいきましょう。
1回目の `stop_reason` は `tool_use` で、Claudeが天気ツールの使用を依頼しています。
`[依頼]` の行で、`id`・`name`・`input` の3つがそろっていることが確認できます。
`[結果]` の行は、私たちの `get_weather` 関数が返した文字列です。
ここまでで、Claudeが依頼し、私たちのコードが実行するという役割分担が、出力の上でもはっきり分かれています。

2回目の `stop_reason` は `end_turn` になりました。
Claudeは `tool_result` の中身を読み、気温や湿度を自然な文章にまとめて答えています。
「軽い上着があれば十分」という一言は、ツールの結果には書かれていません。
これは、Claudeが結果の数値を解釈して付け加えたものです。
ツールが「事実」を提供し、Claudeが「解釈と表現」を担当する、という分担がよく分かる例です。

`[履歴]` の表示では、メッセージ数が3になっています。
2回目の応答は表示しただけで、`messages` には追加していないからです。
会話を続けるなら、2回目の応答も assistant メッセージとして追加することになります。
assistant の `content` も確認しておきましょう。
`["text", "tool_use"]` の配列になっているはずです。
環境によっては、ここに `"thinking"` が加わって3要素になることもあります。

最後の行には、`tracker.summary()` による集計が表示されます。
呼び出し回数が `calls=2` になっていること、`input` が2回分の入力トークンの合計であることを確認してください。
2回目は、1回目の質問と応答、ツールの結果をすべて含めて送っているので、入力が増えるのは自然なことです。
ツールを1回使うだけで、APIの呼び出しは2回、入力トークンは2回分以上かかります。
この感覚は、エージェントのコストを見積もるときにとても大切です。

<figure id="fig-5-5">
<svg width="605" height="368" viewBox="0 0 605 368"
     xmlns="http://www.w3.org/2000/svg"
     font-family="'Noto Sans JP',sans-serif">
  <defs>
    <marker id="f5_5_arr55" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#333" stroke-width="1.5"/>
    </marker>
    <marker id="f5_5_arr55a" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#2b6cb0" stroke-width="1.5"/>
    </marker>
  </defs>
  <rect x="0" y="0" width="605" height="368" fill="#ffffff"/>
  <text x="155" y="26" text-anchor="middle" dominant-baseline="central" font-size="13" fill="#1a1a1a" font-weight="bold">1回目のリクエスト</text>
  <rect x="15" y="42" width="280" height="250" rx="6" fill="none" stroke="#999" stroke-width="1"/>
  <rect x="30" y="55" width="250" height="30" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.1"/>
  <text x="155.0" y="70.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">tools: [get_weather]</text>
  <text x="32" y="107" text-anchor="start" dominant-baseline="central" font-size="12" fill="#1a1a1a" font-family="Consolas,monospace">messages:</text>
  <rect x="30" y="120" width="250" height="32" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="155.0" y="136.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">user: 東京の今の天気を…</text>
  <text x="155" y="270" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-weight="bold">質問だけを送る</text>
  <text x="450" y="26" text-anchor="middle" dominant-baseline="central" font-size="13" fill="#1a1a1a" font-weight="bold">2回目のリクエスト</text>
  <rect x="310" y="42" width="280" height="250" rx="6" fill="none" stroke="#999" stroke-width="1"/>
  <rect x="325" y="55" width="250" height="30" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.1"/>
  <text x="450.0" y="70.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">tools: [get_weather]</text>
  <text x="327" y="107" text-anchor="start" dominant-baseline="central" font-size="12" fill="#1a1a1a" font-family="Consolas,monospace">messages:</text>
  <rect x="325" y="120" width="250" height="32" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="450.0" y="136.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">user: 東京の今の天気を…</text>
  <rect x="325" y="162" width="250" height="32" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="450.0" y="178.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">assistant: text ＋ tool_use</text>
  <rect x="325" y="204" width="250" height="32" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="450.0" y="220.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">user: tool_result</text>
  <text x="450" y="270" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#2b6cb0" font-weight="bold">2・3番目が新しく加わった分</text>
  <path d="M296 170 L308 170" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f5_5_arr55)"/>
  <text x="302" y="314" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">API はステートレス。2回目は質問・tool_use・tool_result を全部含めて送る</text>
  <text x="302" y="332" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">→ ツールを1回使うだけで、呼び出しは2回、入力トークンは2回分以上</text>
</svg>
  <figcaption>図5.5: 1回目と2回目のリクエストの違い</figcaption>
</figure>

### わざと間違えて、エラーの形を知る

仕組みを深く理解するために、わざと間違えた場合の挙動も確かめておきましょう。
エラーの出方を一度見ておくと、本番で同じエラーに出会ったときに原因をすぐ特定できます。
ここでは、よくある2つの間違いを試します。
試したあとは、必ずコードを元に戻してください。

1つ目は、assistant の応答を履歴に追加し忘れる間違いです。
3番目のブロックの `messages.append(...)` の行を、コメントアウトして実行してみてください。
すると2回目の呼び出しで、`llm_client.py` が `InvalidRequestError`（400）を送出します。
エラーメッセージには、次のような趣旨が書かれています。
`tool_result` に対応する `tool_use` が、直前のメッセージに見つからないという内容です。
伝票（`tool_use`）がないのに料理（`tool_result`）だけが届いたので、APIが受け付けなかったわけです。

2つ目は、`tool_use_id` を間違える間違いです。
コードの中の `"tool_use_id": tool_use["id"]` を書き換えます。
`"tool_use_id": "toolu_dummy"` のような適当な値に変えて実行してみてください。
こちらも 400 エラーになり、`tool_use` と `tool_result` の対応が取れていないことが示されます。
どちらのエラーも、第4章で作った例外クラスのおかげで、`InvalidRequestError` として捕まえられます。
`request_id` もログに残るので、原因を調べるときの手がかりになります。

| 間違い | 起きること | 対処 |
|---|---|---|
| assistant の応答を履歴に追加し忘れる | 400 `invalid_request_error` | `tool_result` を送る前に、必ず assistant の `content` を追加する |
| `tool_use_id` を間違える | 400 `invalid_request_error` | `tool_use["id"]` を変数からそのまま入れる |
| `tool_result` を返さずに次の質問を送る | 400 `invalid_request_error` | `tool_use` には必ず `tool_result` で応える |
| assistant の `text` だけを文字列にして追加する | 400、または文脈の欠落 | `content` 配列を加工せずにそのまま追加する |

> **POINT**: Tool Use のエラーの多くは「履歴の形が崩れている」ことが原因です。400 エラーが出たら、まず `messages` を `print` しましょう。そのうえで、次の2点を確認します。1つは、user と assistant が交互に並んでいるかです。もう1つは、`tool_use` と `tool_result` が1対1で対応しているかです。

これで、Tool Use の1往復を自分の手で組み立てられるようになりました。
しかし、`one_shot_tool.py` は「ちょうど1往復で終わる」ことを前提にしています。
実際の依頼では、何往復になるかは事前に分かりません。
次の節では、この1往復を `while` ループで一般化し、何往復でも自動で回るエージェントに仕上げます。

---

## 5.4 エージェンティックループの実装

`one_shot_tool.py` は、ちょうど1往復で終わる依頼にしか対応できませんでした。
では「東京と札幌の気温差は？」のように、何回ツールを使うか分からない依頼はどう扱えばよいのでしょうか。
答えは、「Claudeが答え終わるまで、1往復を繰り返す」ことです。
本節では、1往復を `while` ループに一般化した `agent.py` を作ります。
そして最後に、天気ツールを本物のAPIに差し替えます。

### ループの骨格と終了条件

ループの考え方はシンプルです。
まずAPIを呼び、`stop_reason` が `"tool_use"` ならツールを実行して結果を返します。
そして、もう一度APIを呼びます。
`"end_turn"` になったら、`text` を最終回答として返してループを抜けます。
この判断を、Claude自身が「もう十分」と考えるまで繰り返します。
何往復するかを決めるのはコードではなくClaudeだという点が、エージェントと固定的な処理の違いです。

ただし、Claudeに任せきりにすると困る場面もあります。
ツールの結果が期待外れで、Claudeが同じ依頼を延々と繰り返すかもしれません。
そこで、ループには必ず「最大反復回数」のガードを入れます。
また、`max_tokens` や `refusal` で止まった場合にも、ループを抜ける処理が必要です。
`max_tokens` は出力が途中で切れたこと、`refusal` は応答を控えたことを表します。
これらを入れないと、APIの呼び出しが止まらず、コストだけが膨らむおそれがあります。

<figure id="fig-5-6">
<svg width="605" height="452" viewBox="0 0 605 452"
     xmlns="http://www.w3.org/2000/svg"
     font-family="'Noto Sans JP',sans-serif">
  <defs>
    <marker id="f5_6_arr56" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#333" stroke-width="1.5"/>
    </marker>
    <marker id="f5_6_arr56a" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#2b6cb0" stroke-width="1.5"/>
    </marker>
  </defs>
  <rect x="0" y="0" width="605" height="452" fill="#ffffff"/>
  <rect x="80" y="15" width="240" height="32" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="200.0" y="31.0" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a">messages = [user の質問]</text>
  <path d="M200 47 L200 64" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f5_6_arr56)"/>
  <polygon points="200,66.0 305.0,92 200,118.0 95.0,92" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="200" y="92.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">turn &lt; max_turns ？</text>
  <path d="M305 92 L388 92" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f5_6_arr56)"/>
  <text x="346" y="83" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">超えた</text>
  <rect x="390" y="76" width="195" height="32" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="487.5" y="92.0" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a">[中断] 最大ターン数に到達</text>
  <text x="210" y="127" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">はい</text>
  <path d="M200 118 L200 135" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f5_6_arr56)"/>
  <rect x="80" y="137" width="240" height="34" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="200.0" y="154.0" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a">call_messages() で API を呼ぶ</text>
  <path d="M200 171 L200 187" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f5_6_arr56)"/>
  <rect x="80" y="189" width="240" height="34" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="200.0" y="206.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">assistant の content をそのまま追加</text>
  <path d="M200 223 L200 241" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f5_6_arr56)"/>
  <polygon points="200,243.0 305.0,270 200,297.0 95.0,270" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="200" y="270.0" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a" font-weight="bold">stop_reason は？</text>
  <path d="M305 270 L388 270" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f5_6_arr56)"/>
  <text x="348" y="261" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">end_turn</text>
  <rect x="390" y="250" width="195" height="40" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="487.5" y="262.3" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a">最終回答を返す</text>
  <text x="487.5" y="278.4" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">extract_text()</text>
  <path d="M340 270 L340 345 L388 345" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f5_6_arr56)"/>
  <rect x="390" y="325" width="195" height="40" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="487.5" y="337.3" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a">警告・中断して終了</text>
  <text x="487.5" y="353.4" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">max_tokens / refusal</text>
  <path d="M200 297 L200 318" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f5_6_arr56)"/>
  <text x="208" y="308" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">tool_use</text>
  <rect x="80" y="320" width="240" height="34" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="200.0" y="337.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">全 tool_use を実行（execute_tool）</text>
  <path d="M200 354 L200 370" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f5_6_arr56)"/>
  <rect x="80" y="372" width="240" height="40" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="200.0" y="384.3" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">tool_result をまとめて</text>
  <text x="200.0" y="399.7" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">1つの user メッセージで追加</text>
  <path d="M80 392 L40 392 L40 92 L93 92" fill="none" stroke="#2b6cb0" stroke-width="1.3" marker-end="url(#f5_6_arr56a)"/>
  <text x="45" y="80" text-anchor="start" dominant-baseline="central" font-size="11" fill="#2b6cb0" font-weight="bold">次のターン</text>
</svg>
  <figcaption>図5.6: エージェンティックループ</figcaption>
</figure>

### agent.pyを書く

プロジェクトのルートに `agent.py` を新規作成します。
`run_agent` 関数の形は、第6章以降でも育てていく本書の「契約」なので、引数の名前もこのとおりに書いてください。

```python
# agent.py
"""第5章: 関数版のエージェンティックループ。"""

import logging
import sys
from typing import Callable

from llm_client import call_messages, extract_text, get_tool_uses, tracker
from tools.weather import GET_WEATHER_TOOL, get_weather

logger = logging.getLogger("agent")

# エージェントの振る舞いを決める system プロンプト
DEFAULT_SYSTEM = (
    "あなたは天気について答えるアシスタントです。"
    "天気の質問には必ず get_weather ツールで最新の値を確認してから答えてください。"
    "複数の都市を調べるときは、ツールをまとめて呼び出してかまいません。"
)


def execute_tool(tool_use: dict, tool_functions: dict[str, Callable[..., str]]) -> dict:
    """tool_use ブロック1つを実行し、tool_result ブロックを返す。"""
    func = tool_functions.get(tool_use["name"])
    # 定義にない名前を依頼された場合も、失敗として Claude に知らせる
    if func is None:
        return {
            "type": "tool_result",
            "tool_use_id": tool_use["id"],
            "content": f"エラー: 未知のツール '{tool_use['name']}' です。",
            "is_error": True,
        }
    try:
        # input はパース済みの辞書。キーワード引数として展開する
        result = func(**tool_use["input"])
    except Exception as exc:  # ツールの失敗でループ全体を止めない
        logger.warning("ツール %s が失敗: %s", tool_use["name"], exc)
        return {
            "type": "tool_result",
            "tool_use_id": tool_use["id"],
            "content": f"エラー: {type(exc).__name__}: {exc}",
            "is_error": True,
        }
    return {"type": "tool_result", "tool_use_id": tool_use["id"], "content": result}


def run_agent(
    user_input: str,
    *,
    tools: list[dict],
    tool_functions: dict[str, Callable[..., str]],
    system: str | None = None,
    max_turns: int = 10,
) -> str:
    """Claude が答え終わるまでツールの実行を繰り返し、最終回答を返す。"""
    messages: list[dict] = [{"role": "user", "content": user_input}]
    turn = 0

    while turn < max_turns:  # 最大反復回数のガード
        turn += 1
        response = call_messages(messages, system=system, tools=tools)
        stop_reason = response["stop_reason"]
        logger.info("turn=%d stop_reason=%s", turn, stop_reason)

        # 応答の content は加工せず、そのまま履歴に追加する（thinking も含む）
        messages.append({"role": "assistant", "content": response["content"]})

        if stop_reason == "end_turn":
            return extract_text(response)  # 正常終了

        if stop_reason == "tool_use":
            # すべての tool_use を実行し、結果を1つの user メッセージで返す
            tool_results = [execute_tool(tu, tool_functions) for tu in get_tool_uses(response)]
            messages.append({"role": "user", "content": tool_results})
            continue

        if stop_reason == "max_tokens":
            logger.warning("max_tokens に達したため打ち切ります")
            return extract_text(response) + "\n\n[警告] 出力が上限に達したため、回答が途中で切れています。"

        if stop_reason == "refusal":
            logger.warning("refusal: %s", response.get("stop_details"))
            return "[中断] この依頼には応答できませんでした。"

        # 想定外の stop_reason（stop_sequence など）は本文を返して終える
        logger.warning("想定外の stop_reason: %s", stop_reason)
        return extract_text(response)

    return f"[中断] 最大ターン数（{max_turns}）に達したため、処理を打ち切りました。"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # 通信ごとのログは抑える
    # コマンドライン引数があれば質問として使う
    question = " ".join(sys.argv[1:]) or "東京と札幌、今どちらが暖かいですか？気温差も教えてください。"
    answer = run_agent(
        question,
        tools=[GET_WEATHER_TOOL],
        tool_functions={"get_weather": get_weather},  # ツール名 → 関数 の対応表
        system=DEFAULT_SYSTEM,
    )
    print("\n" + answer)
    print(tracker.summary())


if __name__ == "__main__":
    main()
```

### コードを読む

`execute_tool` は、`tool_use` ブロックを1つ受け取る関数です。
そして、`tool_result` ブロックを1つ返します。
`tool_functions` は「ツール名 → Python関数」の辞書で、`name` から呼ぶ関数を引きます。
未知の名前や、関数が例外を投げた場合には、`is_error: True` 付きの結果を返します。
例外をループの外へ逃がさないのは、ツールの失敗を「Claudeが読める情報」に変えるためです。
たとえば存在しない都市なら、Claudeはエラーメッセージを読みます。
そのうえで、対応都市の中から選び直したり、ユーザーに説明したりできます。

`run_agent` の本体は、`while turn < max_turns` のループです。
毎回の応答を、`stop_reason` を判定する**前に**履歴へ追加している点に注目してください。
`tool_use` のときは、この追加がないと次の `tool_result` が宙に浮きます。
`end_turn` のときは、追加しなくても動きます。
ただし、同じ形にそろえておくと、第7章以降で会話を続ける拡張がしやすくなります。
`thinking` ブロックが含まれていても、`content` をそのまま追加しているので何も考える必要はありません。

`tool_use` の分岐では、リスト内包表記で全部の依頼を実行し、結果を**1つの** user メッセージにまとめています。
Claudeは1つの応答で複数の `tool_use` を出すことがあります。
その場合は、全結果を同じメッセージで返すのがルールです。
ここでは順番に実行していますが、第6章で `ThreadPoolExecutor` を使った並列実行に置き換えます。

`max_tokens` と `refusal` は、どちらも「このまま続けても正しい答えに届かない」状態です。
`max_tokens` の場合、最後の `tool_use` の引数が途中で切れている可能性もあります。
そのため、続行せずに警告付きで打ち切ります。
`refusal` の場合は、`stop_details` に理由の分類が入るので、ログに残しておきます。
最後の `return` は、`max_turns` 回まわっても終わらなかった場合の安全装置です。

> **POINT**: エージェンティックループの終了条件は「`end_turn` で正常終了」だけでは足りません。出口は、`max_tokens`・`refusal`・想定外の値・最大反復回数のすべてに用意します。そうして初めて「必ず止まるループ」になります。

### 実行して複数のtool_useを確かめる

```bash
# agent-from-scratch/ で実行する: 天気エージェントを動かす
uv run python agent.py
```

```text
INFO llm_client: request_id=req_011CZc... model=claude-opus-5-5 stream=False elapsed=2.91s stop=tool_use in=718 out=132 cache_write=0 cache_read=0 cost=$0.0055
INFO agent: turn=1 stop_reason=tool_use
INFO llm_client: request_id=req_011CZd... model=claude-opus-5-5 stream=False elapsed=3.47s stop=end_turn in=1005 out=124 cache_write=0 cache_read=0 cost=$0.0065
INFO agent: turn=2 stop_reason=end_turn

今は東京のほうが暖かいです。東京は晴れで18.5°C、札幌は雪で2.3°Cなので、気温差は16.2°Cあります。
札幌へ出かける場合は、厚手のコートや手袋などしっかりした防寒具を用意しましょう。
calls=2 input=1,723 output=256 cache_write=0 cache_read=0 total=$0.0120
```

`turn=1` の応答では、Claudeが東京と札幌の2つの `tool_use` を1つの応答にまとめて出しています。
`agent.py` は2つとも実行し、2つの `tool_result` を1つの user メッセージで返しました。
そのため、2都市を調べても往復は2ターンで済んでいます。
Claudeが1都市ずつ順番に依頼してきた場合は `turn=3` まで進みますが、ループなのでどちらでも正しく動きます。

<figure id="fig-5-7">
<svg width="605" height="348" viewBox="0 0 605 348"
     xmlns="http://www.w3.org/2000/svg"
     font-family="'Noto Sans JP',sans-serif">
  <defs>
    <marker id="f5_7_arr57" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#333" stroke-width="1.5"/>
    </marker>
    <marker id="f5_7_arr57a" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#2b6cb0" stroke-width="1.5"/>
    </marker>
  </defs>
  <rect x="0" y="0" width="605" height="348" fill="#ffffff"/>
  <text x="20" y="18" text-anchor="start" dominant-baseline="central" font-size="12" fill="#1a1a1a" font-weight="bold">assistant メッセージ（1回目の応答）</text>
  <rect x="20" y="30" width="565" height="80" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <rect x="32" y="42" width="120" height="56" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.1"/>
  <text x="92.0" y="62.3" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">text</text>
  <text x="92.0" y="77.7" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">「調べますね」</text>
  <rect x="165" y="42" width="200" height="56" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="265.0" y="62.3" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace" font-weight="bold">tool_use（id: toolu_A）</text>
  <text x="265.0" y="77.7" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">get_weather / Tokyo</text>
  <rect x="375" y="42" width="200" height="56" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="475.0" y="62.3" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace" font-weight="bold">tool_use（id: toolu_B）</text>
  <text x="475.0" y="77.7" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">get_weather / Sapporo</text>
  <text x="282" y="150" text-anchor="start" dominant-baseline="central" font-size="11" fill="#2b6cb0" font-weight="bold">tool_use_id で対応</text>
  <text x="20" y="198" text-anchor="start" dominant-baseline="central" font-size="12" fill="#1a1a1a" font-weight="bold">user メッセージ（1つだけ）</text>
  <rect x="20" y="210" width="565" height="80" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <path d="M265 98 L265 222" fill="none" stroke="#2b6cb0" stroke-width="1.3" stroke-dasharray="4,3"/>
  <path d="M475 98 L475 222" fill="none" stroke="#2b6cb0" stroke-width="1.3" stroke-dasharray="4,3"/>
  <text x="92" y="241" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">結果だけを</text>
  <text x="92" y="258" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">並べる</text>
  <rect x="165" y="222" width="200" height="56" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="265.0" y="242.3" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace" font-weight="bold">tool_result（toolu_A）</text>
  <text x="265.0" y="257.7" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">東京 晴れ 18.5°C</text>
  <rect x="375" y="222" width="200" height="56" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="475.0" y="242.3" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace" font-weight="bold">tool_result（toolu_B）</text>
  <text x="475.0" y="257.7" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">札幌 雪 2.3°C</text>
  <text x="302" y="312" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">すべての tool_use に1つずつ tool_result を返し、1つの user メッセージにまとめる</text>
</svg>
  <figcaption>図5.7: 複数tool_useの結果の返し方</figcaption>
</figure>

次に、ダミーデータにない都市を聞いて、エラー時の動きを確かめます。

```bash
# agent-from-scratch/ で実行する: 対応していない都市を聞いてみる
uv run python agent.py "那覇の天気は？"
```

```text
INFO llm_client: request_id=req_011CZe... model=claude-opus-5-5 stream=False elapsed=2.38s stop=tool_use in=702 out=74 cache_write=0 cache_read=0 cost=$0.0043
INFO agent: turn=1 stop_reason=tool_use
WARNING agent: ツール get_weather が失敗: 都市 'Naha' のデータがありません。対応都市: Tokyo, Osaka, Sapporo
INFO llm_client: request_id=req_011CZf... model=claude-opus-5-5 stream=False elapsed=3.02s stop=end_turn in=860 out=96 cache_write=0 cache_read=0 cost=$0.0054
INFO agent: turn=2 stop_reason=end_turn

申し訳ありません。現在、那覇の天気データは取得できませんでした。
対応しているのは東京・大阪・札幌です。これらの都市でよろしければお調べします。
calls=2 input=1,562 output=170 cache_write=0 cache_read=0 total=$0.0096
```

`is_error` 付きの結果を受け取ったClaudeが、失敗を理解してユーザーに説明していることが分かります。
ツールの例外でプログラムが止まらず、エラー自体が会話の材料になっている点が大切です。

### 本物の天気APIに差し替える

ループが完成したので、ダミーの天気データを本物のAPIに差し替えます。
本書では、APIキー不要で使える Open-Meteo（オープンメテオ）を使います。
Open-Meteo は、非商用であれば無料で使える気象データのAPIです。
登録なしで、HTTPリクエストを送るだけで結果が返ってきます。
商用で使う場合や大量に呼び出す場合は、公式サイトの利用条件を確認してください。
無料枠には1日1万回などの呼び出し上限があり、データは CC BY 4.0 で提供されます。
取得した天気を公開する場合は、出典として Open-Meteo を表示しましょう。

Open-Meteo の天気APIは、都市名ではなく緯度・経度で場所を指定します。
そこで、次の2段階で天気を取得します。

1. **ジオコーディングAPI**で、都市名から緯度・経度を調べる
   - URL: `https://geocoding-api.open-meteo.com/v1/search`
2. **予報API**で、その緯度・経度の現在の天気を取得する
   - URL: `https://api.open-meteo.com/v1/forecast`

<figure id="fig-5-8">
<svg width="605" height="372" viewBox="0 0 605 372"
     xmlns="http://www.w3.org/2000/svg"
     font-family="'Noto Sans JP',sans-serif">
  <defs>
    <marker id="f5_8_arr58" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#333" stroke-width="1.5"/>
    </marker>
    <marker id="f5_8_arr58a" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#2b6cb0" stroke-width="1.5"/>
    </marker>
  </defs>
  <rect x="0" y="0" width="605" height="372" fill="#ffffff"/>
  <rect x="20" y="15" width="300" height="32" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="170.0" y="31.0" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a">city = "Tokyo"（Claude が渡す引数）</text>
  <path d="M170 47 L170 65" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f5_8_arr58)"/>
  <rect x="20" y="67" width="300" height="52" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="170.0" y="85.3" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a">① ジオコーディングAPI（_geocode）</text>
  <text x="170.0" y="101.4" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">geocoding-api.open-meteo.com/v1/search</text>
  <path d="M170 119 L170 137" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f5_8_arr58)"/>
  <rect x="20" y="139" width="300" height="32" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="170.0" y="155.0" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a">緯度・経度（latitude / longitude）</text>
  <path d="M170 171 L170 189" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f5_8_arr58)"/>
  <rect x="20" y="191" width="300" height="52" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="170.0" y="209.3" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a">② 予報API（forecast）</text>
  <text x="170.0" y="225.4" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">api.open-meteo.com/v1/forecast</text>
  <path d="M170 243 L170 261" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f5_8_arr58)"/>
  <rect x="20" y="263" width="300" height="52" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="170.0" y="281.3" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a">現在の天気を JSON 文字列で返す</text>
  <text x="170.0" y="297.4" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">概況・気温・湿度・風速・観測時刻</text>
  <path d="M320 93 L335 93" fill="none" stroke="#999" stroke-width="1.2" stroke-dasharray="4,3"/>
  <text x="340" y="85" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">name, count=1, language=ja</text>
  <text x="340" y="101" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">見つからなければ ValueError</text>
  <path d="M320 155 L335 155" fill="none" stroke="#999" stroke-width="1.2" stroke-dasharray="4,3"/>
  <text x="340" y="147" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">1件目の候補（results[0]）の</text>
  <text x="340" y="163" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">latitude と longitude を渡す</text>
  <path d="M320 217 L335 217" fill="none" stroke="#999" stroke-width="1.2" stroke-dasharray="4,3"/>
  <text x="340" y="209" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">current: 気温・湿度・天気コード・風速</text>
  <text x="340" y="225" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">temperature_unit / timezone=auto</text>
  <path d="M320 289 L335 289" fill="none" stroke="#999" stroke-width="1.2" stroke-dasharray="4,3"/>
  <text x="340" y="281" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">WEATHER_CODES で天気コードを</text>
  <text x="340" y="297" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">日本語の概況に変換する</text>
  <text x="302" y="338" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">APIキー不要。場所を緯度・経度で指定するため、都市名からの2段階になる</text>
</svg>
  <figcaption>図5.8: Open-Meteoの2段階呼び出し</figcaption>
</figure>

`tools/weather.py` を次のように更新します。
`GET_WEATHER_TOOL` は変更しないので省略し、それより下を書き換えます。
`_DUMMY_WEATHER` は削除します。

```python
# tools/weather.py（更新: get_weather を Open-Meteo 版に差し替え）
import json

import httpx

# GET_WEATHER_TOOL は第5章前半のまま（変更なし・省略）

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# 天気API用のクライアント。Claude API 用とは別にし、タイムアウトを短めにする
_http = httpx.Client(timeout=httpx.Timeout(10.0))

# WMO 天気コード → 日本語の概況（主なもの）
WEATHER_CODES: dict[int, str] = {
    0: "快晴", 1: "晴れ", 2: "一部曇り", 3: "曇り", 45: "霧", 48: "霧",
    51: "弱い霧雨", 53: "霧雨", 55: "強い霧雨", 61: "弱い雨", 63: "雨", 65: "強い雨",
    71: "弱い雪", 73: "雪", 75: "強い雪", 80: "にわか雨", 81: "にわか雨", 82: "激しいにわか雨",
    95: "雷雨",
}


def _geocode(city: str) -> dict:
    """都市名から、名前・緯度・経度を含む候補を1件返す。"""
    resp = _http.get(GEOCODING_URL, params={"name": city, "count": 1, "language": "ja", "format": "json"})
    resp.raise_for_status()  # 4xx/5xx は例外にする
    results = resp.json().get("results")
    if not results:  # 見つからないと results キー自体がない
        raise ValueError(f"都市 '{city}' が見つかりません。英語表記（例: Tokyo）で指定してください。")
    return results[0]


def get_weather(city: str, unit: str = "celsius") -> str:
    """都市名を受け取り、Open-Meteo から現在の天気を取得して JSON 文字列で返す。"""
    place = _geocode(city)
    resp = _http.get(
        FORECAST_URL,
        params={
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
            "temperature_unit": unit,  # celsius / fahrenheit をそのまま渡せる
            "timezone": "auto",  # 現地時刻で返してもらう
        },
    )
    resp.raise_for_status()
    current = resp.json()["current"]
    unit_label = "°F" if unit == "fahrenheit" else "°C"
    result = {
        "city": place.get("name", city),
        "country": place.get("country", ""),
        "time": current["time"],  # 観測時刻（現地時刻）
        "condition": WEATHER_CODES.get(current["weather_code"], f"コード{current['weather_code']}"),
        "temperature": f"{current['temperature_2m']}{unit_label}",
        "humidity": f"{current['relative_humidity_2m']}%",
        "wind_speed": f"{current['wind_speed_10m']} km/h",
        "source": "open-meteo",
    }
    return json.dumps(result, ensure_ascii=False)


if __name__ == "__main__":
    print(get_weather("Tokyo"))
```

`_geocode` は、都市名で検索して最初の候補を返します。
見つからないときは `ValueError` を投げます。
すると、`agent.py` の `execute_tool` がそのまま `is_error` 付きの結果に変換してくれます。
`raise_for_status()` による HTTP エラーも、同じく例外として扱われます。
`httpx` の接続エラー・タイムアウトも同様です。
ツール側でエラーを特別に処理しなくても、ループ側の仕組みがClaudeに失敗を伝えてくれるわけです。

`get_weather` の引数と戻り値の形は、ダミー版と同じです。
そのため、`agent.py` は1行も変更せずに本物のAPIで動きます。
「関数のシグネチャを保ったまま中身を差し替える」ことで、ループとツールを独立して育てられます。
天気APIの `current` に4つの変数名を指定し、`temperature_unit` で単位も切り替えています。
天気の概況は数値の天気コード（WMO 天気コード）で返るので、`WEATHER_CODES` で日本語に変換しています。

```bash
# agent-from-scratch/ で実行する: 本物の天気でエージェントを動かす
uv run python -m tools.weather
uv run python agent.py "那覇とニューヨーク、今の気温を華氏で比べて"
```

```text
{"city": "東京都", "country": "日本", "time": "2026-11-06T15:00", "condition": "晴れ", "temperature": "17.2°C", ...}
INFO llm_client: request_id=req_011CZg... model=claude-opus-5-5 stream=False elapsed=2.86s stop=tool_use in=712 out=128 cache_write=0 cache_read=0 cost=$0.0054
INFO agent: turn=1 stop_reason=tool_use
INFO llm_client: request_id=req_011CZh... model=claude-opus-5-5 stream=False elapsed=2.95s stop=end_turn in=1010 out=88 cache_write=0 cache_read=0 cost=$0.0058
INFO agent: turn=2 stop_reason=end_turn

那覇は71.8°F（晴れ）、ニューヨークは48.6°F（曇り）で、那覇のほうが23.2°F高くなっています。
calls=2 input=1,722 output=216 cache_write=0 cache_read=0 total=$0.0112
```

数値は実行する日時によって変わります。都市名は、`東京都` のようにジオコーディングの検索結果の表記で返ります。
ダミー版では答えられなかった那覇やニューヨークにも答えられるようになりました。
`unit` の `fahrenheit` も正しく使われています。
これで、外の世界の最新情報を自分で取りに行く、本物のエージェントが完成しました。

> **WARNING**: `"source": "open-meteo"` が表示されない場合は、ダミー版が動いています。ファイルを保存し忘れていないか確認しましょう。また、会社のネットワークなどで外部への接続が制限されている場合もあります。その場合は `ConnectError` が `is_error` として返り、Claudeが「取得できませんでした」と答えます。

---

## COLUMN: よくあるつまずきポイントTOP3

筆者がエージェントを作り始めた人のコードを見ていて、特によく出会うつまずきを3つ紹介します。
どれも本章のコードで防げていますが、自分で一から書き直すときに再発しやすいものです。

**第1位: assistant の応答を履歴に追加し忘れる。**
`tool_result` を追加することに気を取られるケースです。
その前の assistant の `content` を追加し忘れてしまいます。
2回目の呼び出しで 400 エラーになり、「`tool_use` が見つからない」という趣旨のメッセージが返ります。
`tool_use` だけを抜き出して追加した場合も、`thinking` ブロックが失われて問題になることがあります。
対策は、応答を受け取ったら判定より前に `content` をそのまま追加する、と決めておくことです。

**第2位: tool_result を分けて返す。**
複数の `tool_use` に対して、`for` ループの中で1つずつ user メッセージを追加してしまうケースです。
user メッセージが連続し、Claudeが並列にツールを呼ばなくなるなど、ふるまいが不安定になります。
正しい形は、すべての `tool_result` をリストに集めることです。
そのリストを、1つの user メッセージの `content` に入れます。

**第3位: 終了条件の不備による無限ループ。**
`while True:` の中で、`end_turn` だけを終了条件にしているケースです。
これでは、`max_tokens` や `refusal` で止まったときに抜けられません。
同じリクエストを送り続けてコストだけが積み上がる、もっとも痛いつまずきです。
最大反復回数のガードと、すべての `stop_reason` に対する出口を必ず用意しましょう。

---

## 本章のまとめ

本章で学んだことを整理します：

- Tool Use では、Claudeは `tool_use` で依頼するだけで、ツールを実行するのは自分のコードです。`stop_reason` が `"tool_use"` のときは途中経過なので、本文を最終回答として扱いません。
- ツールは `name`・`description`・`input_schema`（JSON Schema）で定義します。結果は、`tool_use_id` を対応させた `tool_result` として返します。assistant の `content` はそのまま履歴に追加し、複数の結果は1つの user メッセージにまとめます。
- `agent.py` の `run_agent` は、`end_turn` まで往復を繰り返す `while` ループです。最大反復回数・`max_tokens`・`refusal` のガードと `is_error` を備えています。これによって、必ず止まり、失敗にも強いループになりました。

次章では **ツールを実務レベルで設計する** を扱います。
1つのツールで動いたら、次は複数ツール・エラー・安全性を備えた実務レベルの設計へ進みます。
ツールレジストリ、並列実行、安全なファイル操作を加えていきます。
`agent.py` を、さらに頼れるエージェントに育てていきましょう。
