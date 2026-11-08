# 第6章: ツールを実務レベルで設計する
# EN-TITLE: PRACTICAL TOOL DESIGN
# TAGS: ツール設計, ToolRegistry, 並列ツール呼び出し, 安全なファイル操作, 構造化出力

## この章の概要

第5章で完成させた天気エージェントは、ツールが1つだけの小さなエージェントでした。実務のエージェントは、ファイルを読み、書き、外部のAPIを呼び、結果を整形して返します。ツールが増えると、名前の付け方、失敗したときの返し方、危険な操作の止め方といった新しい論点が次々に出てきます。本章では、それらを1つずつ設計と実装で解決していきます。

> [!DIALOGUE]
> **生徒**: 天気エージェントは動きました。あとはツールを足していけば、何でもできるエージェントになりますか？
> **先生**: 足すこと自体は簡単です。ただ、10個に増えたとき、Claudeが迷わず選べるか、失敗しても立て直せるか、勝手にファイルを消さないか。そこまで考えて初めて「実務で使える」と言えます。
> **生徒**: ループの中身を毎回書き換えるのも大変そうです。
> **先生**: そこでレジストリの出番です。ループは一度書いたら触らず、ツールは登録するだけで増やせる形にしましょう。

## この章で学ぶこと

本章では以下を学びます：

- Claudeが迷わず正しく使えるツールの命名・description・粒度・戻り値・エラーメッセージを設計できるようになる
- `ToolRegistry` を使い、ループを変えずにツールを増やせるようになる。また、`ThreadPoolExecutor` で複数の `tool_use` を並列に実行できるようになる
- 作業ディレクトリ外にアクセスできないファイル操作ツールと、副作用のある操作の実行前確認を実装できるようになる
- `output_config.format` と strict ツールで、プログラムがそのまま扱えるJSONを受け取れるようになる

前章では、`tool_use` と `tool_result` の往復を `while` ループに一般化しました。そうして、エージェンティックループを自分の手で書きました。本章では、そのループを「ツールが何個あっても、失敗しても、危険な操作があっても破綻しない」形に鍛え上げます。コードの面では、第5章の `agent.py` を第6章版に更新します。また、新たに3つのファイルを作ります。`tool_registry.py`・`tools/files.py`・`structured_output.py` です。章を読み終えるころには、ワークスペースのファイルを読み書きしながら作業するエージェントが手元で動いているはずです。実務の入り口に立ったエージェントです。

---

## 6.1 良いツール設計の原則

ツールの定義は、JSON Schemaの形さえ合っていればAPIに受け付けてもらえます。しかし「受け付けられる」ことと「Claudeが正しく使える」ことは別の話です。Claudeは、ツールの名前と description と入力スキーマだけを手がかりに、どのツールをいつ、どんな引数で呼ぶかを決めます。つまりツールの定義は、プログラムの仕様書でもあり、Claudeへの指示書でもあるのです。本節では、その指示書をどう書けばClaudeが迷わないかを整理します。順番は、命名・description・粒度・戻り値・エラーメッセージです。最後に、Anthropic側で実行されるサーバーツールと自作ツールの使い分けも確認します。

### ツールは「新しく入ったチームメンバー向けの説明書」

まず、ツール設計の基本的な考え方を押さえましょう。ツールの定義とは、Claudeが外部の機能を使うための唯一の説明書です。Claudeは、あなたのコードの中身を見ることができません。見えるのは、`name`・`description`・`input_schema` の3つだけです。

たとえるなら、ツールの定義は「今日からチームに入った優秀な新人に渡す業務マニュアル」です。新人は頭の回転が速く、書いてあることは正確に理解します。しかし、社内の暗黙のルールや、システムの癖は知りません。マニュアルに「顧客IDで検索する」とだけ書いてあれば、顧客IDがどんな形式なのか、名前で探したいときはどうするのかは分かりません。

この比喩を意識すると、ツール設計の判断がしやすくなります。「この説明だけで、初めて触る人が正しく使えるか」を自問すればよいのです。逆に言えば、人間の新人が迷うツールは、Claudeも迷います。設計の良し悪しは、エージェント全体の精度に直結します。

### 命名: 名前だけで役割が分かるようにする

ツール名は、Claudeが最初に目にする情報です。APIの制約としては、英数字とアンダースコア・ハイフンの組み合わせで、1〜128文字であれば受け付けられます。ただし、制約を満たすだけでは十分ではありません。名前だけで「何をするツールか」が推測できることが重要です。

本書では、次の3つのルールで命名します。1つ目は、`動詞_名詞` の形にすることです。`get_weather`・`read_file`・`write_file` のように、何に対して何をするかを名前で表します。2つ目は、`snake_case`（スネークケース、小文字とアンダースコアの組み合わせ）に統一することです。3つ目は、同じ種類の操作には同じ動詞を使うことです。読み取りは `get_` か `read_`、一覧は `list_`、検索は `search_` と決めたら、全ツールでそろえます。

ツールが増えてきたら、**名前空間**（ネームスペース）の考え方も取り入れます。名前空間とは、名前の先頭にサービスや領域を表す接頭辞を付けて、グループを分ける工夫です。たとえば、社内のCRMと課金システムの両方に「顧客を検索する」ツールがあるとします。CRMはCustomer Relationship Managementの略で、顧客管理システムのことです。どちらも `search_customers` では、Claudeはどちらを呼べばよいか判断できません。そこで、`crm_search_customers` と `billing_search_customers` のように接頭辞で分けます。こうすれば、名前だけで区別が付きます。

| 悪い名前 | 問題点 | 良い名前 |
|---------|-------|---------|
| `tool1` | 役割がまったく分からない | `get_weather` |
| `file` | 読むのか書くのか消すのか不明 | `read_file` / `write_file` |
| `doStuff` | 動作が曖昧で表記ゆれもある | `summarize_report` |
| `search`（複数サービスに存在） | どのサービスか区別できない | `crm_search_customers` |
| `get_data_from_database_and_format_it` | 複数の責務が混ざり長すぎる | `query_sales` |

> **POINT**: 名前に迷ったら「このツール名だけをログで見たとき、何が起きたか分かるか」を基準にしてください。名前はClaudeのためだけでなく、後でログを読むあなた自身のためのものでもあります。

### description: 何を・いつ・どう使うかを書く

次に、ツール選択の精度をもっとも大きく左右する description です。description とは、ツールの役割と使い方を自然言語で説明する文章です。第5章では、何をするか・いつ使うか・何を返すか・何ができないかの4要素を押さえました。ツールが1つなら、それで十分に動きます。しかし、ツールが増えるほど、ツール同士の使い分けまで書かないと判断材料が足りなくなります。

Anthropicの公式ドキュメントでも、description は詳細に書くことが推奨されています。目安は3〜4文以上です。筆者は、次の5項目を書くようにしています。

| 項目 | 書く内容 | 例（`read_file` の場合） |
|-----|---------|----------------------|
| 何をするか | ツールの動作を1文で | ワークスペース内のテキストファイルを読みます |
| いつ使うか | 使うべき場面 | ファイルの内容を確認・要約・編集する前に使います |
| いつ使わないか | 紛らわしい他ツールとの境界 | ファイル名が分からないときは先に `list_files` を使います |
| 引数の意味 | 形式・単位・既定値 | `path` はワークスペースからの相対パスです |
| 戻り値と制限 | 返る内容・上限・注意点 | 1回に最大400行。続きは `start_line` で指定します |

具体例で比べてみましょう。悪い例と良い例を並べます。

```python
# description_examples.py（説明用。プロジェクトには保存しなくてよい）
# 悪い例: 何をするかしか書いていない
BAD_READ_FILE = {
    "name": "read_file",
    "description": "ファイルを読む",  # いつ使うのか、引数の形式は何か、上限はあるのかが不明
    "input_schema": {
        "type": "object",
        "properties": {"path": {"type": "string"}},  # 引数に説明がない
        "required": ["path"],
    },
}

# 良い例: 何を・いつ・いつ使わないか・引数・戻り値と制限を書く
GOOD_READ_FILE = {
    "name": "read_file",
    "description": (
        "ワークスペース内のテキストファイルを読み、行番号付きで返します。"
        "ファイルの内容を確認・要約・編集する前に使ってください。"
        "ファイル名が分からないときは、先に list_files で一覧を確認してください。"
        "1回に返すのは最大400行です。続きがある場合は、"
        "結果の末尾に表示される start_line を指定して再度呼び出してください。"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "ワークスペースからの相対パス。例: notes/todo.md",
            },
            "start_line": {
                "type": "integer",
                "description": "読み始める行番号（1始まり）。省略時は1",
            },
        },
        "required": ["path"],
    },
}
```

悪い例でも、APIはエラーを返しません。しかしClaudeは、`path` に絶対パスを渡すべきか相対パスを渡すべきか分かりません。長いファイルで続きを読む方法も分かりません。良い例では、迷いそうな点を先回りして書いているため、Claudeの判断が安定します。

プロパティごとの `description` も忘れずに書きます。`path` に「例: notes/todo.md」とあるだけで、Claudeが渡す値の形式は大きくそろいます。特に、日付・単位・IDの形式には、必ず例を添えるようにしましょう。日付なら `2026-11-06` か `11/6` か、単位なら円かドルか、秒かミリ秒かです。

> **NOTE**: description に「必ずこのツールを使え」のような強い命令を書く必要はありません。近年のモデルはツールの説明を素直に読み取るため、強すぎる指示は逆に過剰な呼び出しを招きます。「〜のときに使ってください」程度の、普通の言葉で十分です。

### 粒度: 細かすぎず、粗すぎず

3つ目の論点は、ツールの**粒度**です。粒度とは、1つのツールがどこまでの処理を受け持つかという「大きさ」のことです。粒度の設計には、2つの失敗パターンがあります。

1つ目は、細かすぎるパターンです。社内APIのエンドポイントを1対1でツールにすると、こうなりがちです。たとえば「顧客の予定を調べる」ために、3つのツールを順番に呼ぶ必要があるとします。`list_users`・`list_events`・`get_event_detail` です。Claudeは3回ツールを呼び、そのたびにAPIへの往復が発生します。往復のたびに履歴が膨らみ、トークンも時間もかかります。

2つ目は、粗すぎるパターンです。「ファイルを検索して、読み込んで、要約して、メールで送る」を1つのツールにまとめると、Claudeは途中の制御ができなくなります。「今回は送信しなくてよい」という判断を挟む余地がありません。さらに、要約のような「Claude自身が得意な処理」をツールの中に閉じ込めてしまうことにもなります。

筆者が使っている目安は、「人間がその作業をするときの1手」を1ツールにすることです。人間が予定を調べるなら、画面で「田中さんの来週の予定」を一度検索するだけでしょう。それならツールも `search_events(person, date_range)` の1つにまとめます。一方、「読んで、考えて、書く」は人間でも別々の手です。`read_file` と `write_file` は分け、考える部分はClaudeに任せます。

| 粒度 | 典型的な症状 | 対処 |
|-----|-----------|-----|
| 細かすぎる | 1つの目的に3回以上の連続呼び出しが毎回必要 | よく一緒に使う処理を1つのツールにまとめる |
| 粗すぎる | 引数にフラグが増え、途中で止められない | 判断が入る境目でツールを分ける |
| ちょうどよい | 1回の呼び出しで「人間の1手」が完了する | そのまま維持する |

関連する操作が多い場合は、`action` 引数で1つのツールにまとめる方法もあります。たとえば、プルリクエストの作成・レビュー・マージを1つにまとめるような設計です。ツールは `manage_pull_request(action, ...)` の1つになります。ツールの総数が減るため、Claudeが選択に迷う場面を減らせます。ただし、`action` ごとに必要な引数が大きく違う場合は、スキーマが複雑になります。その場合は素直に分けたほうが、description も読みやすくなります。

### 戻り値: 必要十分な情報を、読める形で返す

4つ目は、ツールの戻り値です。戻り値とは、ツールを実行した結果として `tool_result` に入れて返す内容のことです。戻り値は、Claudeが次の行動を決めるための材料になります。少なすぎると判断できず、多すぎるとコンテキストを圧迫します。

まず意識したいのは、**Claudeが意味を読み取れる形**で返すことです。データベースの検索結果をそのまま返すと、`{"uid": "a8f3...", "st": 2}` のような値が並ぶことがあります。人間にも意味が分からない値は、Claudeにも分かりません。`{"name": "田中一郎", "status": "対応中"}` のように、意味のある名前と値に変換してから返しましょう。IDが後続のツール呼び出しに必要な場合だけ、名前と並べてIDも返します。

次に、**量の上限**を決めておくことです。ファイル一覧が1万件ある場合に、全件を返してはいけません。数十万トークンの `tool_result` は、コストを押し上げます。それだけでなく、Claudeが重要な情報を見落とす原因にもなります。上限を超える場合は、先頭の一部だけを返し、「全1万件中200件を表示。絞り込むには pattern を指定してください」のような案内を添えます。この「続きの取り方」を書いておくのが、良い戻り値設計のコツです。

最後に、**形式**です。`tool_result` の `content` には文字列を入れるのが基本です。構造を持つデータなら、JSON文字列にして返せば十分に伝わります。変換には `json.dumps(..., ensure_ascii=False)` を使います。表のようなデータなら、行ごとに整形したテキストのほうがトークンを節約できる場合もあります。本書のツールは、すべて「人間が読んでも分かるテキスト」を返す方針で作ります。

> **POINT**: 戻り値の設計では「この結果を見て、Claudeは次に何をするか」を想像してください。次の一手に必要な情報が入っていて、不要な情報が入っていなければ合格です。

### エラーメッセージ: Claudeが立て直せる書き方

5つ目は、エラーメッセージです。ツールは必ずどこかで失敗します。存在しないファイル、ネットワークの不調、想定外の引数などです。このとき、エラーをどう返すかで、エージェントが立て直せるかどうかが決まります。

エラーメッセージの原則は、**何が起きたか**と**次に何をすればよいか**をセットで書くことです。比べてみましょう。

| 悪いエラー | 良いエラー |
|----------|----------|
| `FileNotFoundError` | `ファイル notes/todo.md は存在しません。list_files でファイル名を確認してください。` |
| `Error 400` | `引数 date の形式が不正です（受け取った値: 11/6）。YYYY-MM-DD 形式で指定してください。例: 2026-11-06` |
| `Traceback (most recent call last): ...`（30行） | `天気APIへの接続がタイムアウトしました。時間をおいて再試行するか、ユーザーに状況を伝えてください。` |

悪い例では、Claudeは「何かが失敗した」ことしか分かりません。同じ引数で何度も呼び直したり、ユーザーに意味のない謝罪を返したりします。良い例では、Claudeは自分で `list_files` を呼んで正しいファイル名を探したり、日付の形式を直して再試行したりできます。人間のエンジニアが読んでうれしいエラーメッセージは、Claudeにとってもうれしいのです。

もう1つ大切なのは、Pythonのトレースバックをそのまま返さないことです。トレースバックには、ファイルのフルパスや内部の変数名が含まれます。Claudeの判断には役立たないうえ、トークンを浪費し、内部構造の情報を外に出すことにもなります。詳細はログに残し、`tool_result` には要点だけを返すのが鉄則です。この方針は、6.3節で `is_error` と組み合わせて実装します。

### サーバーツール: Anthropic側で実行されるツール

ここまでは、自分で実行するツール（**クライアントツール**）の話でした。Claude API には、もう1種類、**サーバーツール**があります。サーバーツールとは、Anthropicのインフラ上で実行されるツールです。代表的なものが、Web検索を行う `web_search` と、指定したURLの内容を取得する `web_fetch` です。

2つの違いは「誰が実行するか」です。クライアントツールでは、Claudeが `tool_use` ブロックを返し、あなたのコードが実行して `tool_result` を返します。サーバーツールでは、API の内部で検索や取得が実行されます。レスポンスには、2種類のブロックが両方入って返ってきます。Claudeが呼び出した記録を表す `server_tool_use` ブロックと、その結果のブロックです。Web検索なら、結果は `web_search_tool_result` ブロックです。あなたのコードが `tool_result` を返す必要はありません。

<figure id="fig-6-1">
<svg width="605" height="372" viewBox="0 0 605 372"
     xmlns="http://www.w3.org/2000/svg"
     font-family="'Noto Sans JP',sans-serif">
  <defs>
    <marker id="f6_1_arr61" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#333" stroke-width="1.5"/>
    </marker>
    <marker id="f6_1_arr61a" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#2b6cb0" stroke-width="1.5"/>
    </marker>
  </defs>
  <rect x="0" y="0" width="605" height="372" fill="#ffffff"/>
  <text x="155" y="26" text-anchor="middle" dominant-baseline="central" font-size="13" fill="#1a1a1a" font-weight="bold">クライアントツール</text>
  <text x="450" y="26" text-anchor="middle" dominant-baseline="central" font-size="13" fill="#1a1a1a" font-weight="bold">サーバーツール</text>
  <rect x="15" y="42" width="280" height="290" rx="6" fill="none" stroke="#999" stroke-width="1"/>
  <rect x="310" y="42" width="280" height="290" rx="6" fill="none" stroke="#999" stroke-width="1"/>
  <rect x="30" y="55" width="110" height="30" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="85.0" y="70.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">あなたのコード</text>
  <rect x="170" y="55" width="110" height="30" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="225.0" y="70.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">Claude API</text>
  <rect x="325" y="55" width="110" height="30" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="380.0" y="70.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">あなたのコード</text>
  <rect x="465" y="55" width="110" height="30" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="520.0" y="70.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">Claude API</text>
  <path d="M85 85 L85 290" fill="none" stroke="#999" stroke-width="1.2" stroke-dasharray="4,3"/>
  <path d="M225 85 L225 290" fill="none" stroke="#999" stroke-width="1.2" stroke-dasharray="4,3"/>
  <path d="M380 85 L380 290" fill="none" stroke="#999" stroke-width="1.2" stroke-dasharray="4,3"/>
  <path d="M520 85 L520 290" fill="none" stroke="#999" stroke-width="1.2" stroke-dasharray="4,3"/>
  <path d="M225 115 L87 115" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f6_1_arr61)"/>
  <text x="155" y="104" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">tool_use</text>
  <rect x="40" y="133" width="90" height="34" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="85.0" y="150.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">自分で実行</text>
  <path d="M85 195 L223 195" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f6_1_arr61)"/>
  <text x="155" y="184" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">tool_result</text>
  <text x="155" y="207" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#2b6cb0" font-weight="bold">あなたが作って返す</text>
  <path d="M225 255 L87 255" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f6_1_arr61)"/>
  <text x="155" y="244" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">最終回答</text>
  <path d="M380 115 L518 115" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f6_1_arr61)"/>
  <text x="450" y="104" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">tools に web_search</text>
  <rect x="448" y="128" width="134" height="82" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="515.0" y="145.9" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">server_tool_use</text>
  <text x="515.0" y="161.3" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">↓ API内部で検索</text>
  <text x="515.0" y="176.7" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">web_search_</text>
  <text x="515.0" y="192.1" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">tool_result</text>
  <path d="M520 245 L382 245" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f6_1_arr61)"/>
  <text x="450" y="234" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">両方のブロック入りの応答</text>
  <text x="450" y="257" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#2b6cb0" font-weight="bold">tool_result は不要</text>
  <text x="155" y="312" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-weight="bold">結果を返す主体: あなたのコード</text>
  <text x="450" y="312" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-weight="bold">結果を作る主体: Anthropic の API</text>
</svg>
  <figcaption>図6.1: クライアントツールとサーバーツール</figcaption>
</figure>

サーバーツールを使うには、`tools` 配列に `type` 付きの定義を入れます。本書では、結果の絞り込み機能（動的フィルタリング。後述のNOTEを参照）に対応した `web_search_20260209` と `web_fetch_20260209` を使います。執筆時点ではさらに新しい `_20260318` 版も公開されており、機能が追加されています。`input_schema` は書きません。スキーマはAnthropic側で決まっているからです。試しに、Web検索を有効にしたリクエストを送ってみましょう。これは仕組みを確かめるための試し用スクリプトで、以降の章では使いません。

```python
# server_tools_demo.py（試し用。プロジェクトの最終構成には含めない）
import json  # レスポンスの一部を見やすく表示するため

from llm_client import call_messages, extract_text  # 第4章で作った自作クライアント

# サーバーツールの定義: type と name を指定し、input_schema は書かない
SERVER_TOOLS = [
    {
        "type": "web_search_20260209",  # Web検索ツールのバージョン付きの型
        "name": "web_search",           # 名前は固定で web_search
        "max_uses": 3,                  # 1ターン内の検索回数の上限（再開をまたいで数える。コスト対策）
        "allowed_callers": ["direct"],  # 動的フィルタリングを使わず、Claudeが直接検索する
    },
]

MAX_CONTINUATIONS = 3  # pause_turn で続きを要求する回数の上限


def main() -> None:
    # 最初のユーザー発話
    messages: list[dict] = [
        {"role": "user", "content": "Python 3.13 の主な新機能を3つ、出典付きで教えてください。"}
    ]
    extra: dict | None = None  # 再開時に引き継ぐコンテナID（第10章の research_web() と同じ方式）
    for _ in range(MAX_CONTINUATIONS + 1):
        response = call_messages(messages, tools=SERVER_TOOLS, max_tokens=4000, extra=extra)
        # どの種類のブロックが返ってきたかを観察する
        print("blocks:", [block["type"] for block in response["content"]])
        if response["stop_reason"] != "pause_turn":
            break  # end_turn など、それ以外の停止理由なら終了
        # サーバー側のループが一時停止した。assistant の content をそのまま足し、同じ tools で再送する
        print("pause_turn を受け取ったので続きを要求します")
        messages.append({"role": "assistant", "content": response["content"]})
        if response.get("container"):  # コンテナが返ってきたら、再開でも同じものを使う
            extra = {"container": response["container"]["id"]}
    else:
        print("pause_turn が続いたため打ち切りました")

    print(extract_text(response))  # 最終回答のテキストだけを表示
    print(json.dumps(response["usage"], ensure_ascii=False))  # 使用量を確認


if __name__ == "__main__":
    main()
```

実行すると、たとえば次のような出力になります。ブロックの並びと回答の内容は、実行するたびに変わります。

```bash
uv run python server_tools_demo.py
```

```text
blocks: ['thinking', 'server_tool_use', 'web_search_tool_result', 'text', 'text', 'text']
Python 3.13 の主な新機能は次の3つです。
1. 対話型インタープリター（REPL）の刷新 ...
...
{"input_tokens": 18342, "output_tokens": 912, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0, "server_tool_use": {"web_search_requests": 1}}
```

出力の読み方を確認しましょう。`blocks` の行に、`server_tool_use` と `web_search_tool_result` が並んでいます。これが「Claudeが検索を依頼し、API内部で実行され、結果が入った」記録です。`text` ブロックが複数に分かれているのは、引用（citations）の単位でテキストが区切られるためです。`extract_text()` は `type == "text"` のブロックをすべて連結するので、分割を気にせず読めます。`usage` の中には、検索の実行回数も記録されています。

> **WARNING**: サーバーツールの検索結果は、入力トークンとして課金されます。上の例でも、短い質問なのに入力が1.8万トークンになっています。さらにWeb検索には、検索回数に応じた従量料金が別にかかります。`max_uses` で回数の上限を必ず設定し、料金ページで最新の単価を確認してください。

### pause_turn: サーバー側ループの一時停止

サーバーツールを使うと、新しい停止理由 `pause_turn` に出会うことがあります。`pause_turn` とは、API内部で動いているツール実行のループが、長くなったために一時停止したことを表す停止理由です。検索を何度も繰り返す調査などで起こります。

`pause_turn` を受け取ったら、返ってきた assistant の `content` をそのまま履歴に追加します。そして、**同じ `tools` のまま**もう一度リクエストを送ります。すると、Claudeは中断したところから続きを実行します。上のコードの `for` ループの後半がこの処理です。レスポンスに `container`（コード実行の作業環境）が含まれていたら、そのIDも `extra` で送り返します。ここで `tools` からサーバーツールを外してしまうと、未実行の `server_tool_use` が宙に浮きます。その結果、400エラーになります。

第3章で「最後を assistant メッセージで終える prefill（プリフィル）は400になる」と説明しました。`pause_turn` の続きの要求は、見た目こそ assistant で終わる履歴ですが、これはAPIが想定している正規の再開手順です。自分で文章を書き足した assistant メッセージではなく、APIが返した `content` をそのまま戻している点が違います。続きはさらに `pause_turn` で止まることもあるため、上のコードのように再開回数の上限を設けておきます。

もう1つ知っておきたいのが、サーバーツールとクライアントツールが同時に呼ばれた場合です。このときAPIはサーバーツールを実行せずに、`stop_reason: "tool_use"` で一度返してきます。あなたは、いつもどおりクライアントツールを実行し、`tool_result` だけを入れた user メッセージを返します。すると、APIは保留していたサーバーツールを実行してから、続きを生成します。第5章のループは `type == "tool_use"` のブロックだけを実行し、`server_tool_use` は無視します。そのため、この混在ケースも特別な処理なしで正しく動きます。

> **NOTE**: `web_search_20260209` と `web_fetch_20260209` は、動的フィルタリングに対応した版です。検索結果の絞り込みに、内部でコード実行の仕組みを使います。既定ではClaudeがコード実行の中から検索を呼ぶため、応答にコード実行のブロックが加わります。上のデモでは仕組みを単純に観察するため、`"allowed_callers": ["direct"]` で直接検索にしています。データを保持しない契約（ZDR）が必要な組織でも、この指定が必要です。業務で使う前に、公式ドキュメントのサーバーツールのページを確認してください。

### 自作ツールとサーバーツールの使い分け

では、Web検索のような機能は、サーバーツールを使うべきでしょうか、自作すべきでしょうか。判断の軸を表にまとめます。

| 観点 | サーバーツール（`web_search` 等） | 自作のクライアントツール |
|-----|------------------------------|---------------------|
| 実装の手間 | `tools` に1行足すだけ | 検索APIの契約・実装・保守が必要 |
| 実行場所 | Anthropicのインフラ | 自分のコード（社内ネットワークも可） |
| 社内データへのアクセス | できない | できる |
| 結果の加工 | 開発者はできない（そのまま入る） | 自由に絞り込み・整形できる |
| 引用（citations） | Web検索は自動で付く（Web取得は設定で有効化） | 自分で設計する |
| コスト | トークン＋検索回数の従量料金 | トークン＋利用する外部APIの料金 |
| 監査・ログ | レスポンスに記録が残る | 自分で好きなだけ記録できる |

筆者の判断基準はシンプルです。**公開Webの情報を調べるなら、まずサーバーツールを使う**。**社内データ、独自の加工、厳密な権限管理が必要なら自作する**。たとえば、最新のライブラリのリリース情報を調べる程度なら、サーバーツールで十分です。一方、社内Wikiや顧客データベースを検索するツールは、自作するしかありません。本章で作るファイル操作ツールも、手元のファイルを扱うため自作します。

ここまでで、ツール設計の5原則とサーバーツールの位置づけを確認しました。原則が分かっても、ツールが増えるたびにループのコードを書き換えていては、設計に集中できません。次の節では、ツールを「登録するだけ」で増やせる仕組みを作ります。

---

## 6.2 ツールレジストリ

第5章の `run_agent()` は、2つの引数を受け取っていました。ツールのスキーマ一覧 `tools` と、名前から関数を引く辞書 `tool_functions` です。ツールが1つのうちは、この形で困ることはありません。しかし、ツールを足すたびに「スキーマを書いて、リストに足して、辞書にも足す」作業が発生します。どれか1か所を忘れると、Claudeには見えているのに実行できないツールが生まれます。逆に、実行できるのにClaudeには見えないツールも生まれます。本節では、この二重管理をなくす `ToolRegistry`（ツールレジストリ）を作ります。

### レジストリとは何か

レジストリとは、「名前」と「中身」の対応を1か所で管理する登録簿のことです。`ToolRegistry` は、ツールに関する4つの情報を1つのエントリーとしてまとめて保管します。名前・description・入力スキーマ・Python関数です。そして、APIに渡すスキーマ一覧の出力と、名前による関数の実行を、どちらも同じ登録簿から行います。

身近な例でいえば、会社の内線番号表のようなものです。「経理部の田中さん＝内線1234」と1冊の表にまとまっていれば、新しい人が入ったときは表に1行足すだけです。番号表と座席表が別々になっていると、片方だけ更新されて、電話がつながらない事故が起こります。レジストリは、ツールの世界でこの事故を防ぐ仕組みです。

この仕組みを入れると、エージェントのループ本体が知るべき操作は2つだけになります。「レジストリからスキーマをもらう」と「レジストリに実行を頼む」です。ツールが3個でも30個でも、ループのコードは1行も変わりません。この「変わる部分と変わらない部分を分ける」考え方は、第8章で `Agent` クラスを作るときにも土台になります。

<figure id="fig-6-2">
<svg width="605" height="420" viewBox="0 0 605 420"
     xmlns="http://www.w3.org/2000/svg"
     font-family="'Noto Sans JP',sans-serif">
  <defs>
    <marker id="f6_2_arr62" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#333" stroke-width="1.5"/>
    </marker>
    <marker id="f6_2_arr62a" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#2b6cb0" stroke-width="1.5"/>
    </marker>
  </defs>
  <rect x="0" y="0" width="605" height="420" fill="#ffffff"/>
  <rect x="15" y="15" width="180" height="62" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="105.0" y="38.3" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">@registry.tool(...)</text>
  <text x="105.0" y="53.7" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">def get_weather()</text>
  <rect x="212" y="15" width="180" height="62" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="302.0" y="38.3" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">@registry.tool(...)</text>
  <text x="302.0" y="53.7" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">def read_file()</text>
  <rect x="410" y="15" width="180" height="62" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="500.0" y="30.6" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">@registry.tool(...,</text>
  <text x="500.0" y="46.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">side_effect=True)</text>
  <text x="500.0" y="61.4" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">def write_file()</text>
  <path d="M105 77 L105 108" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f6_2_arr62)"/>
  <path d="M302 77 L302 108" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f6_2_arr62)"/>
  <path d="M500 77 L500 108" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f6_2_arr62)"/>
  <text x="203" y="93" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-weight="bold">デコレーターで登録</text>
  <rect x="40" y="110" width="525" height="105" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="302" y="127" text-anchor="middle" dominant-baseline="central" font-size="13" fill="#1a1a1a" font-family="Consolas,monospace" font-weight="bold">ToolRegistry</text>
  <text x="302" y="148" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">_tools: dict[str, RegisteredTool]（名前 → 登録情報）</text>
  <rect x="80" y="163" width="445" height="44" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.1"/>
  <text x="302.5" y="177.3" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-weight="bold">RegisteredTool（frozen dataclass）</text>
  <text x="302.5" y="192.7" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">name / description / input_schema / func / side_effect</text>
  <path d="M105 215 L105 248" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f6_2_arr62)"/>
  <path d="M302 215 L302 248" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f6_2_arr62)"/>
  <path d="M500 215 L500 248" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f6_2_arr62)"/>
  <rect x="15" y="250" width="180" height="36" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="105.0" y="268.0" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a" font-family="Consolas,monospace">schemas()</text>
  <rect x="212" y="250" width="180" height="36" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="302.0" y="268.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">execute(name, tool_input)</text>
  <rect x="410" y="250" width="180" height="36" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="500.0" y="268.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">is_side_effect(name)</text>
  <text x="105" y="302" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">API に渡す tools 配列</text>
  <text x="105" y="318" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">（名前順で固定）</text>
  <text x="302" y="302" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">関数を呼び結果を文字列で返す</text>
  <text x="302" y="318" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">未登録なら ToolNotFoundError</text>
  <text x="500" y="302" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">副作用ツールかを判定</text>
  <text x="500" y="318" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">（実行前確認に使う）</text>
  <path d="M105 328 L105 343" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f6_2_arr62)"/>
  <path d="M302 328 L302 343" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f6_2_arr62)"/>
  <rect x="60" y="345" width="485" height="34" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="302.5" y="362.0" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a">run_agent(registry) は schemas() と execute() だけを使う</text>
</svg>
  <figcaption>図6.2: ToolRegistryの構造</figcaption>
</figure>

### デコレーターのおさらい

`ToolRegistry` では、Pythonの**デコレーター**を使ってツールを登録します。デコレーターとは、関数定義の直前に `@名前` と書くことで、その関数を別の関数に渡して加工・登録する仕組みです。普段から使っていない方のために、要点だけ確認しておきましょう。

```python
# decorator_basics.py（説明用。プロジェクトには保存しなくてよい）
registered: dict[str, object] = {}  # 登録先の辞書


def register(name: str):
    """名前を受け取り、「関数を登録するデコレーター」を返す関数"""
    def decorator(func):
        registered[name] = func  # 関数を辞書に登録する
        return func              # 関数自体は加工せずにそのまま返す
    return decorator


@register("hello")  # ここで register("hello")(say_hello) が実行される
def say_hello() -> str:
    return "こんにちは"


print(registered)               # {'hello': <function say_hello at 0x...>}
print(registered["hello"]())    # こんにちは
```

ポイントは、`@register("hello")` の意味です。これは `say_hello = register("hello")(say_hello)` と同じ意味になります。つまり、デコレーターは「関数を受け取る関数」にすぎません。この性質のおかげで、`@` を使わずに `registry.tool(...)(func)` と普通の関数呼び出しで登録することもできます。6.4節では、この書き方でファイル操作ツールを登録します。

### tool_registry.py を作る

それでは `tool_registry.py` を新規作成します。公開するメソッドは、次の4つです。登録用の `tool()` と、スキーマを出す `schemas()` があります。さらに、名前で実行する `execute()` と、副作用の有無を答える `is_side_effect()` があります。引数の検証は6.3節で追加するので、ここでは登録と実行の骨格だけを作ります。

```python
# tool_registry.py（新規作成）
"""ツールの名前・説明・スキーマ・関数を1か所で管理するレジストリ。"""
from __future__ import annotations

import json  # 文字列以外の戻り値をJSON文字列に変換するため
import logging
import re
from dataclasses import dataclass
from typing import Any, Callable

logger = logging.getLogger("tool_registry")

# ツール名に使える文字（API の制約: 英数字・アンダースコア・ハイフン、1〜128文字）
NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,128}$")


# --- 例外クラス: ツール実行時のエラーはすべて ToolError の子にする ---
class ToolError(Exception):
    """ツールの実行に失敗したことを表す基底クラス。メッセージはClaudeに返す前提で書く"""


class ToolNotFoundError(ToolError):
    """登録されていない名前のツールが呼ばれた"""


# --- 1つのツールの登録情報 ---
@dataclass(frozen=True)
class RegisteredTool:
    name: str                    # ツール名（API の tools[].name）
    description: str             # 説明文（API の tools[].description）
    input_schema: dict           # 入力スキーマ（API の tools[].input_schema）
    func: Callable[..., Any]     # 実際に実行する Python 関数
    side_effect: bool = False    # ファイル書き込みなど副作用があるか


class ToolRegistry:
    """ツールを登録し、スキーマ一覧の出力と名前による実行を提供する"""

    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}  # 名前 → 登録情報

    # --- 登録: デコレーターとして使う ---
    def tool(
        self,
        *,
        name: str,
        description: str,
        input_schema: dict,
        side_effect: bool = False,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """@registry.tool(name=..., description=..., input_schema=...) の形で関数を登録する"""
        # 登録時点で間違いを見つける（API に送ってから 400 になるより早く気づける）
        if not NAME_PATTERN.fullmatch(name):
            raise ValueError(f"ツール名 {name!r} は英数字・_・- の1〜128文字にしてください")
        if name in self._tools:
            raise ValueError(f"ツール名 {name!r} はすでに登録されています")
        if input_schema.get("type") != "object":
            raise ValueError(f"{name}: input_schema の type は 'object' にしてください")

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._tools[name] = RegisteredTool(name, description, input_schema, func, side_effect)
            logger.debug("tool registered: %s (side_effect=%s)", name, side_effect)
            return func  # 関数はそのまま返すので、普通の関数としても呼べる

        return decorator

    # --- API に渡す tools 配列を作る ---
    def schemas(self) -> list[dict]:
        """名前順に並べたスキーマ一覧。順序を固定するとプロンプトキャッシュに有利"""
        ordered = sorted(self._tools.values(), key=lambda entry: entry.name)
        return [
            {
                "name": entry.name,
                "description": entry.description,
                "input_schema": entry.input_schema,
            }
            for entry in ordered
        ]

    # --- 名前で実行する ---
    def execute(self, name: str, tool_input: dict) -> str:
        """ツールを実行し、結果を文字列で返す。失敗時は ToolError を送出する"""
        entry = self._tools.get(name)
        if entry is None:
            available = ", ".join(sorted(self._tools)) or "（なし）"
            raise ToolNotFoundError(
                f"ツール {name!r} は存在しません。使えるツール: {available}"
            )
        result = entry.func(**tool_input)  # 入力の dict をキーワード引数として渡す
        if isinstance(result, str):
            return result
        # dict や list を返す関数もあるので、JSON文字列にそろえる
        return json.dumps(result, ensure_ascii=False)

    # --- 補助メソッド ---
    def is_side_effect(self, name: str) -> bool:
        """副作用のあるツールなら True。未登録の名前は False（実行時に NotFound になる）"""
        entry = self._tools.get(name)
        return entry.side_effect if entry else False

    def names(self) -> list[str]:
        """登録済みのツール名を名前順で返す"""
        return sorted(self._tools)

    def __len__(self) -> int:
        return len(self._tools)
```

コードを上から順に見ていきましょう。

まず、`NAME_PATTERN` はツール名の制約を正規表現にしたものです。APIは、この形式に合わない名前を400エラーで拒否します。登録の時点でチェックしておけば、エージェントを動かす前に間違いに気づけます。「エラーはなるべく早い段階で見つける」のは、どんなプログラムでも通用する原則です。

次に、例外クラスを2つ定義しています。`ToolError` は「ツールの実行に失敗した」ことを表す親クラスで、`ToolNotFoundError` はその子です。親子関係にしておくと、呼び出し側は `except ToolError` の1行で、ツール由来の失敗をまとめて受け止められます。6.3節以降で、検証エラーやパスのエラーも `ToolError` の子として追加していきます。docstring に「メッセージはClaudeに返す前提で書く」とあるのは、6.1節のエラーメッセージの原則を守るための約束です。

`RegisteredTool` は、1つのツールの登録情報をまとめたデータクラスです。`frozen=True` を付けているので、登録後に中身を書き換えることはできません。実行中に誰かがツールの説明を変えてしまうような事故を防ぎます。`side_effect` は、そのツールがファイル書き込みのような「元に戻せない変化」を起こすかどうかの印です。6.4節の実行前確認で使います。

`tool()` メソッドがデコレーターの本体です。キーワード専用引数（`*` より後ろ）にしているのは、呼び出し側で `name=`・`description=` と明示させるためです。引数の順番の取り違えを防げます。メソッドの冒頭では、名前の形式、重複、スキーマの `type` をチェックしています。特に重複チェックは重要です。同じ名前で2回登録すると、後から登録した関数が黙って上書きされ、原因の分かりにくいバグになるからです。

`schemas()` は、APIの `tools` 配列にそのまま渡せるリストを返します。ここで**名前順にソート**している点に注目してください。辞書は登録順を保持するため、ソートしなくても動きます。しかし、モジュールの読み込み順が変わると、`tools` の並びも変わります。第7章で扱うプロンプトキャッシュは、リクエストの先頭から完全に一致する部分を再利用する仕組みです。`tools` の並びが変わるとキャッシュが効かなくなるため、今のうちに順序を固定しておきます。

`execute()` は、名前でツールを探して実行します。見つからなければ `ToolNotFoundError` を送出します。このときのメッセージに、使えるツールの一覧を含めている点がポイントです。Claudeが存在しない名前を呼んでしまっても、このメッセージを読めば正しい名前で呼び直せます。ツールの戻り値が文字列でない場合は、`json.dumps()` でJSON文字列にそろえます。`ensure_ascii=False` を付けないと、日本語が `東` のようなエスケープ表記になり、トークンを余計に消費します。

### 未知のツール名はなぜ起こるのか

「Claudeは `tools` に渡したツールしか呼ばないのでは？」と思った方もいるでしょう。通常はそのとおりです。しかし、実務では次のような場面で未知の名前が届くことがあります。

1つ目は、会話の途中でツール構成を変えた場合です。前のターンで存在した `search_docs` を、次のターンで外したとします。履歴に `search_docs` の呼び出しが残っていると、Claudeは同じツールをもう一度呼ぼうとすることがあります。2つ目は、第8章で扱うマルチエージェントのように、エージェントごとに使えるツールを絞る場合です。説明文に他のエージェントのツール名が出てくると、それを呼ぼうとすることがあります。

どちらの場合も、プログラムを例外で止めてしまうのは悪手です。ユーザーから見れば、理由も分からずエージェントが落ちたことになります。正しい対処は、「そのツールはありません。使えるのはこれです」と `tool_result` で伝え、Claudeに立て直してもらうことです。`execute()` が例外を送出し、ループ側がそれを `is_error` 付きの `tool_result` に変換する。この分担を、次の `agent.py` で実装します。

### 動作確認: レジストリ単体で試す

ループに組み込む前に、レジストリ単体の動きを確認しましょう。`tool_registry.py` の末尾に、次の確認用コードを追記します。

```python
# tool_registry.py（末尾に追記: 単体での動作確認）
if __name__ == "__main__":
    from datetime import datetime  # 動作確認用のツールで使う

    registry = ToolRegistry()

    # デコレーターで登録する例
    @registry.tool(
        name="get_current_time",
        description="現在の日時をISO 8601形式で返します。日付や曜日の計算が必要なときに使ってください。",
        input_schema={"type": "object", "properties": {}, "required": []},
    )
    def get_current_time() -> str:
        return datetime.now().isoformat(timespec="seconds")

    @registry.tool(
        name="add_numbers",
        description="2つの数値を足し算して結果を返します。",
        input_schema={
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "1つ目の数"},
                "b": {"type": "number", "description": "2つ目の数"},
            },
            "required": ["a", "b"],
        },
    )
    def add_numbers(a: float, b: float) -> dict:
        return {"result": a + b}  # dict を返すと execute() が JSON文字列にする

    # 1. スキーマ一覧（名前順）を表示
    print(json.dumps(registry.schemas(), ensure_ascii=False, indent=2))
    # 2. 名前で実行
    print(registry.execute("get_current_time", {}))
    print(registry.execute("add_numbers", {"a": 2, "b": 3.5}))
    # 3. 未知の名前
    try:
        registry.execute("delete_everything", {})
    except ToolNotFoundError as e:
        print("ToolNotFoundError:", e)
```

実行してみます。

```bash
uv run python tool_registry.py
```

```text
[
  {
    "name": "add_numbers",
    "description": "2つの数値を足し算して結果を返します。",
    "input_schema": {
      ...（省略）
    }
  },
  {
    "name": "get_current_time",
    ...（省略）
  }
]
2026-11-06T14:03:27
{"result": 5.5}
ToolNotFoundError: ツール 'delete_everything' は存在しません。使えるツール: add_numbers, get_current_time
```

出力を確認しましょう。登録は `get_current_time` が先でしたが、スキーマ一覧では `add_numbers` が先に並んでいます。名前順のソートが効いている証拠です。`add_numbers` は dict を返す関数です。しかし、`execute()` の結果は `{"result": 5.5}` というJSON文字列になっています。最後に、未知の名前では使えるツールの一覧付きのメッセージが出ています。これがそのままClaudeへの `tool_result` になります。

### agent.py をレジストリ対応にする

次に、第5章の `agent.py` を更新します。`run_agent()` のシグネチャは、これまで `tools` と `tool_functions` の2つを受け取っていました。これを、`registry` 1つを受け取る形に変えます。まずは、ツールを1つずつ順番に実行する素直な版を作ります。並列化は6.3節で行います。

```python
# agent.py（第6章版・6.2時点。第5章版から全体を更新）
"""ToolRegistry を使うエージェンティックループ。"""
from __future__ import annotations

import logging

from llm_client import call_messages, extract_text, get_tool_uses, tracker
from tool_registry import ToolError, ToolRegistry

logger = logging.getLogger("agent")


def make_tool_result(tool_use_id: str, content: str, *, is_error: bool = False) -> dict:
    """tool_result ブロックを組み立てる。失敗時だけ is_error を付ける"""
    block = {"type": "tool_result", "tool_use_id": tool_use_id, "content": content}
    if is_error:
        block["is_error"] = True
    return block


def execute_tool_uses(registry: ToolRegistry, tool_uses: list[dict]) -> list[dict]:
    """tool_use ブロックをすべて実行し、同じ順番で tool_result のリストを返す（6.2: 逐次版）"""
    results: list[dict] = []
    for tool_use in tool_uses:
        try:
            output = registry.execute(tool_use["name"], tool_use["input"])
            results.append(make_tool_result(tool_use["id"], output))
        except ToolError as e:
            # 未知のツールなど「想定内の失敗」は、Claudeが読めるメッセージで返す
            results.append(make_tool_result(tool_use["id"], f"エラー: {e}", is_error=True))
        except Exception as e:
            # 第5章と同じく、想定外の例外でもループを止めずにClaudeへ知らせる（6.3節で整える）
            logger.warning("ツール %s が失敗: %s", tool_use["name"], e)
            results.append(make_tool_result(tool_use["id"], f"エラー: {type(e).__name__}: {e}", is_error=True))
    return results


def run_agent(
    user_input: str,
    *,
    registry: ToolRegistry,
    system: str | None = None,
    max_turns: int = 10,
) -> str:
    """ユーザーの依頼を受け、ツールを使いながら最終回答を返す"""
    messages: list[dict] = [{"role": "user", "content": user_input}]
    tools = registry.schemas()  # ループの外で1回だけ作る（毎ターン同じ内容を送る）

    for turn in range(1, max_turns + 1):
        response = call_messages(messages, system=system, tools=tools)
        stop_reason = response["stop_reason"]
        logger.info("turn=%d stop_reason=%s", turn, stop_reason)

        # assistant の content は、thinking ブロックも含めてそのまま履歴に追加する
        messages.append({"role": "assistant", "content": response["content"]})

        if stop_reason == "tool_use":
            tool_uses = get_tool_uses(response)
            results = execute_tool_uses(registry, tool_uses)
            # すべての tool_result を1つの user メッセージにまとめて返す
            messages.append({"role": "user", "content": results})
            continue
        if stop_reason == "pause_turn":
            # サーバーツールの一時停止。同じ履歴・同じ tools で再送すれば続きが動く
            continue
        if stop_reason == "max_tokens":
            return extract_text(response) + "\n\n（出力が上限に達したため、回答が途中で切れています）"
        if stop_reason == "refusal":
            return "（この依頼には回答できないと判断されました）"
        # end_turn / stop_sequence: 最終回答
        return extract_text(response)

    return f"（{max_turns} ターン以内に完了しなかったため停止しました）"
```

第5章版からの変更点を整理します。

1つ目は、`run_agent()` の引数です。`tools` と `tool_functions` が消え、`registry: ToolRegistry` が入りました。スキーマと関数の対応は、レジストリの中で保証されています。呼び出し側が2つの引数の整合性を気にする必要はもうありません。

2つ目は、`execute_tool_uses()` という関数を切り出したことです。第5章では、ループの中にツール実行のコードを直接書いていました。実行部分を関数に分けておくと、6.3節で並列化するときも、6.4節で実行前確認を足すときも、この関数だけを差し替えれば済みます。この章では、ループ本体はこの節以降もう変更しません。

3つ目は、`make_tool_result()` です。`tool_result` ブロックを組み立てる処理を関数にしました。`is_error` は、失敗したときだけ付けます。成功時に `"is_error": False` を付けても問題はありませんが、付けないほうが送信するデータが少なく済みます。

4つ目は、`pause_turn` の分岐を足したことです。現時点のレジストリにはサーバーツールを登録できないため、この分岐を通ることはありません。ただ、将来サーバーツールを混ぜることもあるでしょう。そのとき `pause_turn` を「想定外の停止理由」として最終回答扱いしてしまうと、途中で回答が切れます。あらかじめ「続きを要求する」分岐を入れておけば安心です。

なお、`tracker` は第4章で作った `CostTracker` の共通インスタンスです。ここでは import だけしておき、動作確認で合計コストを表示するのに使います。

### 天気ツールを登録して動かす

レジストリ版のループで、第5章の天気ツールを動かしてみます。`tools/weather.py` には、スキーマと関数がすでにあります。スキーマは `GET_WEATHER_TOOL`、関数は `get_weather()` です。これをレジストリに登録します。ここではデコレーターの `@` を使わず、関数呼び出しの形で登録している点に注目してください。既存の関数を書き換えずに登録できます。

```python
# agent.py（末尾に追記: 動作確認用のエントリーポイント）
def build_registry() -> ToolRegistry:
    """エージェントが使うツールを登録したレジストリを作る"""
    from tools.weather import GET_WEATHER_TOOL, get_weather  # 第5章のツール

    registry = ToolRegistry()
    # 既存のスキーマ dict をそのまま使って登録する（デコレーターを関数として呼ぶ書き方）
    registry.tool(
        name=GET_WEATHER_TOOL["name"],
        description=GET_WEATHER_TOOL["description"],
        input_schema=GET_WEATHER_TOOL["input_schema"],
    )(get_weather)
    return registry


if __name__ == "__main__":
    import sys

    # INFO ログで、ターンごとの停止理由とツールの実行状況を観察する
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # httpx自身のログは抑える（第4章と同じ）
    question = sys.argv[1] if len(sys.argv) > 1 else "東京の今の天気を教えて"
    answer = run_agent(question, registry=build_registry())
    print("\n=== 回答 ===")
    print(answer)
    print(tracker.summary())  # 呼び出し回数・トークン・合計コスト
```

実行結果は次のようになります。`llm_client` の行は第4章で作ったログで、数値は一例です。

```bash
uv run python agent.py "東京の今の天気を教えて"
```

```text
2026-11-06 14:10:02,415 llm_client request_id=req_011C... model=claude-opus-5-5 stream=False elapsed=1.84s stop=tool_use in=1012 out=96 cache_write=0 cache_read=0 cost=$0.0060
2026-11-06 14:10:02,416 agent turn=1 stop_reason=tool_use
2026-11-06 14:10:04,583 llm_client request_id=req_011C... model=claude-opus-5-5 stream=False elapsed=1.52s stop=end_turn in=1176 out=74 cache_write=0 cache_read=0 cost=$0.0062
2026-11-06 14:10:04,584 agent turn=2 stop_reason=end_turn

=== 回答 ===
東京は現在晴れで、気温は16.2℃です。
calls=2 input=2,188 output=170 cache_write=0 cache_read=0 total=$0.0122
```

出力の読み方を確認しましょう。1ターン目の停止理由が `tool_use`、2ターン目が `end_turn` です。Claudeが天気ツールを呼び、その結果を読んで回答した流れが、ログの2行から読み取れます。最後の行は `tracker.summary()` の出力で、2回の呼び出しで約1.2セントかかったことが分かります。

第5章とまったく同じ振る舞いです。それでいて、ループ本体はツールの名前を1つも知りません。これで、ツールを増やすときは `build_registry()` に登録を足すだけになりました。次の節では、Claudeが一度に複数のツールを呼んだときに、それらを並行して実行する仕組みを入れます。

---

## 6.3 並列ツール呼び出しとエラー処理

「東京と大阪と札幌の天気を比べて」と頼むと、Claudeは1つの応答の中で `get_weather` を3回呼びます。これを**並列ツール呼び出し**といい、Claude APIでは既定で有効です。6.2節の逐次版は3つを順番に実行するため、1つ0.6秒かかるAPIなら合計1.8秒待つことになります。本節では、これを並行実行で短縮し、あわせて失敗の返し方と引数の検証を整えます。

### 並列ツール呼び出しのルール

並列ツール呼び出しとは、1つの assistant 応答に複数の `tool_use` ブロックが含まれることです。このとき守るべきルールは2つあります。1つ目は、**すべての** `tool_use` に対応する `tool_result` を返すことです。1つでも欠けると、APIは400エラーを返します。2つ目は、それらを**1つの user メッセージ**にまとめることです。結果ごとに user メッセージを分けると、Claudeは「並列で呼んでも結果は1つずつ返ってくる」と学習してしまいます。その結果、以降の並列呼び出しが減ります。

さらに、user メッセージの中では `tool_result` ブロックを先頭に置きます。結果の前にテキストを入れると400エラーになります。補足を伝えたい場合は、すべての `tool_result` の後ろにテキストを置きます。本書の `run_agent()` は結果だけを入れるので、この点は自然に守られています。

<figure id="fig-6-3">
<svg width="605" height="402" viewBox="0 0 605 402"
     xmlns="http://www.w3.org/2000/svg"
     font-family="'Noto Sans JP',sans-serif">
  <defs>
    <marker id="f6_3_arr63" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#333" stroke-width="1.5"/>
    </marker>
    <marker id="f6_3_arr63a" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#2b6cb0" stroke-width="1.5"/>
    </marker>
  </defs>
  <rect x="0" y="0" width="605" height="402" fill="#ffffff"/>
  <text x="18" y="18" text-anchor="start" dominant-baseline="central" font-size="12" fill="#1a1a1a" font-weight="bold">assistant の応答（tool_use が3つ）</text>
  <rect x="15" y="30" width="575" height="62" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <rect x="15" y="265" width="575" height="62" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <rect x="30" y="40" width="175" height="42" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.1"/>
  <text x="117.5" y="53.3" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace" font-weight="bold">tool_use</text>
  <text x="117.5" y="68.7" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">get_weather / Tokyo</text>
  <path d="M117.5 82 L117.5 128" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f6_3_arr63)"/>
  <rect x="30" y="130" width="175" height="52" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="117.5" y="148.3" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">run_one_tool()</text>
  <text x="117.5" y="163.7" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">elapsed=0.58s</text>
  <path d="M117.5 182 L117.5 273" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f6_3_arr63)"/>
  <rect x="30" y="275" width="175" height="42" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.1"/>
  <text x="117.5" y="288.3" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace" font-weight="bold">tool_result</text>
  <text x="117.5" y="303.7" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">東京 16.2°C</text>
  <rect x="215" y="40" width="175" height="42" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.1"/>
  <text x="302.5" y="53.3" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace" font-weight="bold">tool_use</text>
  <text x="302.5" y="68.7" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">get_weather / Osaka</text>
  <path d="M302.5 82 L302.5 128" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f6_3_arr63)"/>
  <rect x="215" y="130" width="175" height="52" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="302.5" y="148.3" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">run_one_tool()</text>
  <text x="302.5" y="163.7" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">elapsed=0.61s</text>
  <path d="M302.5 182 L302.5 273" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f6_3_arr63)"/>
  <rect x="215" y="275" width="175" height="42" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.1"/>
  <text x="302.5" y="288.3" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace" font-weight="bold">tool_result</text>
  <text x="302.5" y="303.7" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">大阪 17.8°C</text>
  <rect x="400" y="40" width="175" height="42" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.1"/>
  <text x="487.5" y="53.3" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace" font-weight="bold">tool_use</text>
  <text x="487.5" y="68.7" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">get_weather / Sapporo</text>
  <path d="M487.5 82 L487.5 128" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f6_3_arr63)"/>
  <rect x="400" y="130" width="175" height="52" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="487.5" y="148.3" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">run_one_tool()</text>
  <text x="487.5" y="163.7" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">elapsed=0.63s</text>
  <path d="M487.5 182 L487.5 273" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f6_3_arr63)"/>
  <rect x="400" y="275" width="175" height="42" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.1"/>
  <text x="487.5" y="288.3" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace" font-weight="bold">tool_result</text>
  <text x="487.5" y="303.7" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">札幌 6.4°C</text>
  <rect x="15" y="120" width="575" height="72" rx="6" fill="none" stroke="#2b6cb0" stroke-width="1.2" stroke-dasharray="5,3"/>
  <text x="210" y="106" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#2b6cb0" font-family="Consolas,monospace" font-weight="bold">ThreadPoolExecutor</text>
  <text x="395" y="106" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#2b6cb0" font-weight="bold">で並行実行（最大8件）</text>
  <text x="210" y="225" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">pool.map は入力と同じ</text>
  <text x="395" y="225" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">順番で結果を返す</text>
  <text x="302" y="343" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a" font-weight="bold">user メッセージ（1つにまとめて返す）</text>
  <text x="302" y="366" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">逐次なら約1.8秒 → 並行実行で約0.6秒。失敗も is_error 付きの tool_result にして必ず返す</text>
</svg>
  <figcaption>図6.3: 並列ツール実行と結果の集約</figcaption>
</figure>

### ThreadPoolExecutor で並行実行する

天気APIの呼び出しやファイルの読み込みは、処理時間のほとんどが「待ち」です。こうしたI/O待ちの処理は、スレッドプールで並行実行すると効果的です。Python標準では `concurrent.futures.ThreadPoolExecutor` が使えます。スレッドプールとは、あらかじめ用意した複数のスレッドに処理を割り振る仕組みです。`pool.map()` を使えば、入力の順番どおりに結果を受け取れます。

`agent.py` の `execute_tool_uses()` を、次のように更新します。1件分の実行を `run_one_tool()` に切り出し、それをスレッドプールで並べて動かします。コードの配置は次のとおりです。

1. import は先頭の import 群に追加します。
2. 定数は `logger` の下に追加します。
3. `run_one_tool()` は 6.2 節の `execute_tool_uses()` の直前に置きます。
4. `execute_tool_uses()` は関数全体を差し替えてください。

いずれも `if __name__ == "__main__":` より前に置きます。後ろに置くと、逐次版のまま動いてしまいます。

```python
# agent.py（6.3: import と定数を追加し、run_one_tool を新設、execute_tool_uses を更新）
import time
from concurrent.futures import ThreadPoolExecutor

MAX_PARALLEL_TOOLS = 8          # 同時に動かすツールの上限
MAX_TOOL_RESULT_CHARS = 20_000  # tool_result に入れる文字数の上限


def run_one_tool(registry: ToolRegistry, tool_use: dict) -> dict:
    """tool_use を1件実行し、成功でも失敗でも必ず tool_result を返す"""
    name, tool_input = tool_use["name"], tool_use["input"]
    started = time.perf_counter()
    try:
        output = registry.execute(name, tool_input)
    except (ToolError, ValueError) as e:
        # 想定内の失敗（未知のツール・引数の誤り・ファイルなし・第5章の天気ツールの ValueError 等）
        logger.warning("tool=%s error=%s", name, e)
        return make_tool_result(tool_use["id"], f"エラー: {e}", is_error=True)
    except Exception as e:
        # 想定外の失敗。詳細はログに残し、Claudeには要点だけ返す
        logger.exception("tool=%s unexpected error", name)
        return make_tool_result(
            tool_use["id"],
            f"ツール {name} の実行中に予期しないエラーが発生しました（{type(e).__name__}）。"
            "引数を見直すか、別の方法を検討してください。",
            is_error=True,
        )
    finally:
        logger.info("tool=%s elapsed=%.2fs", name, time.perf_counter() - started)
    # 大きすぎる結果は切り詰め、切ったことを明記する
    if len(output) > MAX_TOOL_RESULT_CHARS:
        output = output[:MAX_TOOL_RESULT_CHARS] + (
            f"\n…（全{len(output):,}文字のうち先頭{MAX_TOOL_RESULT_CHARS:,}文字のみ表示）"
        )
    return make_tool_result(tool_use["id"], output)


def execute_tool_uses(registry: ToolRegistry, tool_uses: list[dict]) -> list[dict]:
    """tool_use をスレッドプールで並行実行し、元の順番で tool_result を返す（6.3: 並列版）"""
    if len(tool_uses) == 1:
        return [run_one_tool(registry, tool_uses[0])]  # 1件ならスレッドを使わない
    workers = min(MAX_PARALLEL_TOOLS, len(tool_uses))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        # map は入力と同じ順番で結果を返す
        return list(pool.map(lambda tu: run_one_tool(registry, tu), tool_uses))
```

`run_one_tool()` の要点は、**どんな失敗でも例外を外に漏らさない**ことです。`ToolError` は「想定内の失敗」として、そのメッセージをそのまま返します。第5章の天気ツールは失敗を `ValueError` で表すので、これも想定内として扱います。こうして、「英語表記で指定してください」といった立て直し用のメッセージがClaudeに届くようにしています。それ以外の例外は「想定外の失敗」として、トレースバックをログに残し、Claudeには短い説明だけを返します。6.1節で述べた「詳細はログ、要点は `tool_result`」の実装です。どちらの場合も `is_error: True` を付けるので、Claudeは失敗を認識できます。そのうえで、引数を変えて再試行したり、ユーザーに状況を説明したりできます。

`MAX_TOOL_RESULT_CHARS` は、ツールが想定外に巨大な結果を返したときの安全装置です。個々のツールでも上限を設けますが、ループ側にも最後の砦を置いておきます。切り詰めたときは、その事実を文末に書き添えます。黙って切ると、Claudeは「データはこれで全部だ」と誤解してしまいます。

`execute_tool_uses()` では、`pool.map()` を使うことで結果の順番を `tool_uses` と一致させています。APIは `tool_use_id` で対応を取るため、厳密には順番が違っても動きます。ただ、ログやデバッグ時に読みやすいので、順番はそろえておくのが無難です。

### 並列化の効果を確かめる

3都市の天気を頼んで、ログを見てみましょう。

```bash
uv run python agent.py "東京・大阪・札幌の今の気温を比べて"
```

```text
2026-11-06 14:12:04,612 agent turn=1 stop_reason=tool_use
2026-11-06 14:12:05,201 agent tool=get_weather elapsed=0.58s
2026-11-06 14:12:05,233 agent tool=get_weather elapsed=0.61s
2026-11-06 14:12:05,252 agent tool=get_weather elapsed=0.63s
2026-11-06 14:12:07,918 agent turn=2 stop_reason=end_turn

=== 回答 ===
いちばん暖かいのは大阪（17.8℃）、次いで東京（16.2℃）、札幌（6.4℃）です。
```

3件のツールがほぼ同時刻に終わっていることが、ログのタイムスタンプから分かります。なお、ログは agent の行だけを抜き出しています。逐次版なら約1.8秒かかっていた待ち時間が、約0.6秒に縮みました。ツールが重いほど、この差は大きくなります。

### 引数を検証する

Claudeは、たいていスキーマどおりの引数を渡してきます。しかし「たいてい」は「必ず」ではありません。必須の引数が抜けていたり、`enum` にない値が来たりすることはまれにあります。検証せずに関数を呼ぶと、`TypeError` のような分かりにくい例外になります。そこで、`ToolRegistry.execute()` の中で、関数を呼ぶ前に入力を検証します。コードの配置は次のとおりです。

1. `ToolInputError`・`_TYPE_MAP`・`validate_input()` の3つを追加します。場所は `tool_registry.py` の `ToolNotFoundError` の下、`RegisteredTool` の上です。
2. `execute()` はメソッド全体を差し替えます。

6.2節で末尾に足した `__main__` ブロックより後ろに置くと、`NameError` が起きます。`uv run python tool_registry.py` がそこで止まるので注意してください。

```python
# tool_registry.py（6.3: ToolInputError と検証関数を追加し、execute を更新）
class ToolInputError(ToolError):
    """引数がスキーマに合わない"""


# JSON Schema の type と Python の型の対応
_TYPE_MAP: dict[str, type | tuple[type, ...]] = {
    "string": str, "integer": int, "number": (int, float),
    "boolean": bool, "array": list, "object": dict,
}


def validate_input(schema: dict, tool_input: Any) -> None:
    """必須・未知のキー・型・enum を確認し、問題があれば ToolInputError を送出する"""
    if not isinstance(tool_input, dict):
        raise ToolInputError("引数はオブジェクト（キーと値の組）で渡してください")
    props: dict = schema.get("properties", {})
    missing = [k for k in schema.get("required", []) if k not in tool_input]
    if missing:
        raise ToolInputError(f"必須の引数がありません: {', '.join(missing)}")
    unknown = [k for k in tool_input if k not in props]
    if unknown:
        raise ToolInputError(
            f"未知の引数です: {', '.join(unknown)}。使える引数: {', '.join(props)}"
        )
    for key, value in tool_input.items():
        spec = props[key]
        expected = _TYPE_MAP.get(spec.get("type", ""))
        # bool は int の子クラスなので、integer/number に True が来たら弾く
        wrong_bool = isinstance(value, bool) and spec.get("type") in ("integer", "number")
        if expected and (not isinstance(value, expected) or wrong_bool):
            raise ToolInputError(
                f"引数 {key} は {spec['type']} 型で指定してください（受け取った値: {value!r}）"
            )
        if "enum" in spec and value not in spec["enum"]:
            choices = ", ".join(map(str, spec["enum"]))
            raise ToolInputError(f"引数 {key} の値 {value!r} は使えません。使える値: {choices}")


# ToolRegistry.execute の更新後（関数を呼ぶ直前に検証を追加）
    def execute(self, name: str, tool_input: dict) -> str:
        """ツールを実行し、結果を文字列で返す。失敗時は ToolError を送出する"""
        entry = self._tools.get(name)
        if entry is None:
            available = ", ".join(sorted(self._tools)) or "（なし）"
            raise ToolNotFoundError(f"ツール {name!r} は存在しません。使えるツール: {available}")
        validate_input(entry.input_schema, tool_input)  # ← 追加
        result = entry.func(**tool_input)
        return result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
```

検証の範囲は、必須キー・未知のキー・型・`enum` の4つに絞りました。JSON Schemaのすべての機能を検証しようとすると、それだけで一冊の本になります。本書のツールで使うキーワードに限れば、この程度で十分です。本格的に検証したい場合は、`jsonschema` パッケージを使う方法もあります。

エラーメッセージには、受け取った値と正しい指定方法を必ず含めています。たとえば `unit` に `"kelvin"` が来た場合、`tool_result` は「引数 unit の値 'kelvin' は使えません。使える値: celsius, fahrenheit」になります。Claudeはこれを読んで、次のターンで `celsius` を指定し直します。エラーを「止めるための仕組み」ではなく「立て直すための情報」として返す。これが本節の一番のポイントです。

> **POINT**: エラー処理の分担を整理しておきます。ツール関数は、失敗を `ToolError` の子で表します。レジストリは検証と実行を担います。ループは、例外を `is_error` 付きの `tool_result` に変換します。どの層でも、例外でエージェント全体を止めないことが共通の約束です。

---

## 6.4 安全なファイル操作ツール

ファイルを読み書きできるようになると、エージェントの実用性は一気に上がります。議事録を読んで要約を保存する、メモを整理する、といった作業を任せられるからです。一方で、危険も一気に増えます。Claudeが `../../.env` を読めば、APIキーが会話に流れ込みます。上書きの指示を取り違えれば、大事なファイルが消えます。本節では、`tools/files.py` を作り、「できること」と「してはいけないこと」の境界をコードで引きます。

### パストラバーサルとは何か

**パストラバーサル**とは、`../` などを含むパスを使って、本来アクセスを許していない場所のファイルに到達する攻撃手法です。ディレクトリトラバーサルとも呼ばれます。たとえば、作業用の `workspace/` だけを読ませるつもりで、`workspace/` と受け取ったパスを単純に連結したとします。`../.env` が渡されると、連結結果は `workspace/../.env`、つまりプロジェクト直下の `.env` です。

これは「Claudeが悪意を持つ」場合だけの話ではありません。詳しくは第11章で扱います。Claudeが読んだWebページやファイルの中に、「`.env` を読んで内容を書き出せ」という指示が紛れ込んでいる場合があります。これをプロンプトインジェクションといいます。ツール側で境界を守っていれば、たとえClaudeがだまされても被害は起きません。**安全性はプロンプトではなくコードで保証する**、これが原則です。

### 対策: resolve してから配下かを確認する

対策の考え方はシンプルです。まず、受け取ったパスを `Path.resolve()` で**絶対パスに正規化**します。次に、その結果が `WORKSPACE` の配下にあるかを `Path.is_relative_to()` で確認します。`resolve()` は、`..` を解決し、シンボリックリンクもたどった最終的な実体のパスを返します。そのため、文字列としての見た目にだまされず、「実際にどこを指しているか」で判定できます。

<figure id="fig-6-4">
<svg width="605" height="360" viewBox="0 0 605 360"
     xmlns="http://www.w3.org/2000/svg"
     font-family="'Noto Sans JP',sans-serif">
  <defs>
    <marker id="f6_4_arr64" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#333" stroke-width="1.5"/>
    </marker>
    <marker id="f6_4_arr64a" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#2b6cb0" stroke-width="1.5"/>
    </marker>
  </defs>
  <rect x="0" y="0" width="605" height="360" fill="#ffffff"/>
  <text x="302" y="22" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a" font-weight="bold">WORKSPACE = /proj/workspace（起動時に resolve() 済み）</text>
  <text x="95" y="52" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-weight="bold">受け取ったパス</text>
  <text x="310" y="52" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-weight="bold">resolve() 後の実体パス</text>
  <text x="517" y="52" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace" font-weight="bold">is_relative_to()</text>
  <rect x="20" y="68" width="150" height="46" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.1"/>
  <text x="95.0" y="91.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">notes/todo.md</text>
  <path d="M170 91 L198 91" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f6_4_arr64)"/>
  <rect x="200" y="68" width="220" height="46" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="310.0" y="91.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">/proj/workspace/notes/todo.md</text>
  <path d="M420 91 L443 91" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f6_4_arr64)"/>
  <rect x="445" y="68" width="145" height="46" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="517.5" y="91.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-weight="bold">True → 実行を許可</text>
  <rect x="20" y="126" width="150" height="46" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.1"/>
  <text x="95.0" y="149.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">../.env</text>
  <path d="M170 149 L198 149" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f6_4_arr64)"/>
  <rect x="200" y="126" width="220" height="46" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="310.0" y="149.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">/proj/.env</text>
  <path d="M420 149 L443 149" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f6_4_arr64)"/>
  <rect x="445" y="126" width="145" height="46" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="517.5" y="149.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-weight="bold">False → ToolError</text>
  <rect x="20" y="184" width="150" height="46" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.1"/>
  <text x="95.0" y="199.3" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">link/key.txt</text>
  <text x="95.0" y="214.7" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">（外を指すリンク）</text>
  <path d="M170 207 L198 207" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f6_4_arr64)"/>
  <rect x="200" y="184" width="220" height="46" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="310.0" y="207.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">/proj/secret/key.txt</text>
  <path d="M420 207 L443 207" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f6_4_arr64)"/>
  <rect x="445" y="184" width="145" height="46" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="517.5" y="207.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-weight="bold">False → ToolError</text>
  <text x="310" y="254" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">..（親ディレクトリ）とシンボリックリンクを解決した「実際の場所」で判定する</text>
  <rect x="20" y="270" width="570" height="56" rx="6" fill="none" stroke="#666" stroke-width="1" stroke-dasharray="4,3"/>
  <text x="30" y="287" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">✕ 文字列で ".." を探す → 正当な名前を弾き、リンク経由の脱出を見逃す</text>
  <text x="30" y="309" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">✕ startswith で比較 → /proj/workspace_old も通る（is_relative_to は部品単位で比較）</text>
</svg>
  <figcaption>図6.4: パストラバーサル対策</figcaption>
</figure>

よくある失敗は、文字列で `".." in path` を調べる方法です。これは `notes..md` のような正当な名前を弾く一方、シンボリックリンク経由の脱出は見逃します。`str(resolved).startswith(str(WORKSPACE))` も危険です。`workspace_old/` のような隣のディレクトリが「前方一致」で通ってしまいます。`is_relative_to()` はパスの部品単位で比較するので、この問題が起きません。

### tools/files.py を作る

それでは `tools/files.py` を新規作成します。読み取り系の `list_files`・`read_file` と、副作用のある `write_file` の3つです。

```python
# tools/files.py（新規作成）
"""workspace/ 配下だけを扱う、安全なファイル操作ツール。"""
from __future__ import annotations

from pathlib import Path

from tool_registry import ToolError, ToolRegistry

WORKSPACE = Path("workspace").resolve()  # 起動時の作業ディレクトリ基準で固定する
MAX_FILE_BYTES = 2_000_000    # これより大きいファイルは読まない（2MB）
MAX_LINES_PER_READ = 400      # read_file が1回に返す最大行数
MAX_WRITE_CHARS = 100_000     # write_file で書ける最大文字数
MAX_LIST_ENTRIES = 200        # list_files が返す最大件数


def safe_path(rel: str) -> Path:
    """相対パスを WORKSPACE 基準で解決し、配下でなければ ToolError を送出する"""
    if not rel or "\x00" in rel:
        raise ToolError("パスが空か、使えない文字を含んでいます")
    candidate = Path(rel)
    if candidate.is_absolute():
        raise ToolError("絶対パスは使えません。workspace からの相対パスで指定してください")
    resolved = (WORKSPACE / candidate).resolve()  # .. とシンボリックリンクを解決
    if not resolved.is_relative_to(WORKSPACE):
        raise ToolError(f"{rel} は workspace の外を指しています。workspace 内のパスを指定してください")
    return resolved


def list_files(path: str = ".") -> str:
    """ディレクトリの中身を一覧で返す"""
    target = safe_path(path)
    if not target.is_dir():
        raise ToolError(f"ディレクトリ {path} は存在しません")
    entries = sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name))
    lines = []
    for p in entries[:MAX_LIST_ENTRIES]:
        rel = p.relative_to(WORKSPACE).as_posix()  # Windows でも / 区切りで返す
        lines.append(f"[dir]  {rel}/" if p.is_dir() else f"[file] {rel} ({p.stat().st_size:,} bytes)")
    if len(entries) > MAX_LIST_ENTRIES:
        lines.append(f"…ほか {len(entries) - MAX_LIST_ENTRIES} 件（サブディレクトリを指定して絞り込んでください）")
    return "\n".join(lines) or "（空のディレクトリです）"


def read_file(path: str, start_line: int = 1) -> str:
    """テキストファイルを行番号付きで、最大 MAX_LINES_PER_READ 行返す"""
    target = safe_path(path)
    if not target.is_file():
        raise ToolError(f"ファイル {path} は存在しません。list_files で確認してください")
    size = target.stat().st_size
    if size > MAX_FILE_BYTES:
        raise ToolError(f"{path} は {size:,} bytes あり、上限 {MAX_FILE_BYTES:,} bytes を超えるため読めません")
    try:
        lines = target.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        raise ToolError(f"{path} はUTF-8のテキストではないため読めません") from None
    start = max(start_line, 1)
    chunk = lines[start - 1 : start - 1 + MAX_LINES_PER_READ]
    body = "\n".join(f"{start + i:>5}| {line}" for i, line in enumerate(chunk))
    end = start + len(chunk) - 1
    header = f"[{path} 行{start}-{end} / 全{len(lines)}行]"
    if end < len(lines):
        body += f"\n…続きは start_line={end + 1} を指定して読んでください"
    return f"{header}\n{body}"


def write_file(path: str, content: str) -> str:
    """ファイルを作成または上書きする（副作用あり）"""
    if len(content) > MAX_WRITE_CHARS:
        raise ToolError(f"内容が長すぎます（{len(content):,}文字）。{MAX_WRITE_CHARS:,}文字以内に分けてください")
    target = safe_path(path)
    existed = target.exists()
    target.parent.mkdir(parents=True, exist_ok=True)  # 途中のディレクトリも作る
    target.write_text(content, encoding="utf-8")
    action = "上書き" if existed else "新規作成"
    return f"{path} を{action}しました（{len(content):,}文字）"
```

`safe_path()` が本節の心臓部です。絶対パスを先に拒否しているのは、親切なエラーメッセージを返すためです。仮にこのチェックがなくても、`resolve()` と `is_relative_to()` の判定で外部へのアクセスは防げます。たとえば Windows で `/etc/passwd` を渡すと、`is_absolute()` は False になります。しかし連結後は、`workspace` と同じドライブの `\etc\passwd` へ解決されます（例: `C:\etc\passwd`）。そのため、配下チェックで弾かれます。最後の判定が本当の防御線で、それより前のチェックは分かりやすさのためと考えてください。

`WORKSPACE` は、モジュールの読み込み時に一度だけ `resolve()` しています。これは、比較の基準そのものを正規化しておくためです。基準が `workspace` という相対パスのままだと、`is_relative_to()` の比較が正しく働きません。

`read_file()` の戻り値には、6.1節の原則を詰め込んでいます。先頭の `[notes.md 行1-400 / 全1532行]` で全体の大きさを伝え、末尾で続きの読み方を案内します。行番号を付けているのは、Claudeが「15行目を直して」のように場所を特定しやすくするためです。2MBを超えるファイルは読まずに断り、UTF-8で読めないファイルはバイナリとして断ります。どちらも、理由を明記した `ToolError` です。

### 副作用ツールの実行前確認

`list_files` と `read_file` は、何度呼んでも世界を変えません。一方、`write_file` はファイルを書き換えます。こうした**副作用ツール**は、実行前に人間の確認を挟むのが安全です。そのために、6.2節で `side_effect` という印を用意しておきました。

確認で「いいえ」と答えたとき、どう返すかが重要です。ここで処理を例外で止めてはいけません。`tool_use` に対応する `tool_result` が欠けると、次のリクエストが400エラーになるからです。正しくは、「ユーザーが拒否した」ことを `is_error: True` の `tool_result` として返します。Claudeはそれを読み、別の案を提案したり、ユーザーに意図を尋ねたりします。

<figure id="fig-6-5">
<svg width="605" height="452" viewBox="0 0 605 452"
     xmlns="http://www.w3.org/2000/svg"
     font-family="'Noto Sans JP',sans-serif">
  <defs>
    <marker id="f6_5_arr65" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#333" stroke-width="1.5"/>
    </marker>
    <marker id="f6_5_arr65a" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#2b6cb0" stroke-width="1.5"/>
    </marker>
  </defs>
  <rect x="0" y="0" width="605" height="452" fill="#ffffff"/>
  <rect x="172" y="15" width="260" height="34" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="302.0" y="32.0" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a">assistant 応答の tool_use（複数）</text>
  <path d="M302 49 L302 67" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f6_5_arr65)"/>
  <polygon points="302,68.0 412.0,95 302,122.0 192.0,95" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="302" y="87.3" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">副作用ツール？</text>
  <text x="302" y="102.7" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">is_side_effect()</text>
  <path d="M192 95 L97 95 L97 148" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f6_5_arr65)"/>
  <text x="140" y="86" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">いいえ</text>
  <rect x="15" y="150" width="165" height="50" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="97.5" y="167.3" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">読み取り系</text>
  <text x="97.5" y="182.7" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">スレッドプールで並列実行</text>
  <path d="M302 122 L302 154" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f6_5_arr65)"/>
  <text x="310" y="138" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">はい</text>
  <polygon points="302,153.0 420.0,183 302,213.0 184.0,183" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="302" y="175.3" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">ask_approval()</text>
  <text x="302" y="190.7" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">実行してよい？ [y/N]</text>
  <path d="M420 183 L505 183 L505 233" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f6_5_arr65)"/>
  <text x="462" y="174" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">N（拒否）</text>
  <rect x="420" y="235" width="170" height="62" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="505.0" y="250.6" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">is_error 付きの</text>
  <text x="505.0" y="266.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">tool_result を返す</text>
  <text x="505.0" y="281.4" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">（拒否したと伝える）</text>
  <path d="M302 213 L302 243" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f6_5_arr65)"/>
  <text x="310" y="227" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">y（承認）</text>
  <rect x="200" y="245" width="205" height="50" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="302.5" y="262.3" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">承認済みの副作用系</text>
  <text x="302.5" y="277.7" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">1件ずつ順番に実行</text>
  <path d="M97 200 L97 343" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f6_5_arr65)"/>
  <path d="M302 295 L302 343" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f6_5_arr65)"/>
  <path d="M505 297 L505 343" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f6_5_arr65)"/>
  <rect x="60" y="345" width="485" height="40" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="302.5" y="365.0" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a">元の tool_use の順番に並べ直し、1つの user メッセージで返す</text>
  <text x="302" y="410" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">拒否しても例外で止めない（tool_result が欠けると次のリクエストが400エラーになる）</text>
</svg>
  <figcaption>図6.5: 副作用ツールの実行前確認</figcaption>
</figure>

確認のタイミングにも注意が必要です。`input()` による確認をスレッドの中で行うと、複数の質問が同時に画面に出て混乱します。そこで、確認はメインスレッドで先に済ませ、承認されたものだけを実行します。さらに、副作用ツールは並列にせず、元の順番で1件ずつ実行します。同じファイルへの書き込みが同時に走ると、どちらが残るか分からなくなるからです。`execute_tool_uses()` を最終形に更新しましょう。コードの配置は次のとおりです。

1. `import json` は先頭の import 群に追加します。
2. `ask_approval()` は `run_one_tool()` の下に追加します。
3. `execute_tool_uses()` は、6.3節の並列版をまるごと置き換えます。

```python
# agent.py（6.4: ask_approval を新設し、execute_tool_uses を最終形に更新）
import json


def ask_approval(name: str, tool_input: dict) -> bool:
    """副作用ツールの実行前に、ターミナルでユーザーの承認を得る"""
    print(f"\n[確認] ツール {name} を次の引数で実行します:")
    preview = json.dumps(tool_input, ensure_ascii=False, indent=2)
    print(preview[:1000] + ("\n…（以下省略）" if len(preview) > 1000 else ""))
    return input("実行してよいですか？ [y/N]: ").strip().lower() in ("y", "yes")


def execute_tool_uses(registry: ToolRegistry, tool_uses: list[dict]) -> list[dict]:
    """読み取り系は並列、副作用系は承認後に逐次で実行し、元の順番で tool_result を返す"""
    results: dict[str, dict] = {}
    readonly, approved = [], []
    # 1. 承認はメインスレッドで、元の順番どおりに先に済ませる
    for tu in tool_uses:
        if not registry.is_side_effect(tu["name"]):
            readonly.append(tu)
        elif ask_approval(tu["name"], tu["input"]):
            approved.append(tu)
        else:
            results[tu["id"]] = make_tool_result(
                tu["id"],
                "ユーザーがこの操作の実行を拒否しました。操作は行われていません。"
                "理由をユーザーに確認するか、別の方法を提案してください。",
                is_error=True,
            )
    # 2. 読み取り系はスレッドプールで並行実行
    if readonly:
        with ThreadPoolExecutor(max_workers=min(MAX_PARALLEL_TOOLS, len(readonly))) as pool:
            for tu, res in zip(readonly, pool.map(lambda t: run_one_tool(registry, t), readonly)):
                results[tu["id"]] = res
    # 3. 承認済みの副作用系は1件ずつ順番に実行
    for tu in approved:
        results[tu["id"]] = run_one_tool(registry, tu)
    # 4. 元の tool_use の順番に並べ直して返す（全件そろっている）
    return [results[tu["id"]] for tu in tool_uses]
```

最後に、ファイル操作ツールをレジストリに登録する関数を `tools/files.py` に追加します。この関数は `build_registry()` から呼びます。`allow_write` 引数で、書き込みツールの有無を切り替えられるようにしておきます。これは、第8章で「読むだけのエージェント」を作るときに役立ちます。

```python
# tools/files.py（末尾に追記: レジストリへの登録）
def register_file_tools(registry: ToolRegistry, *, allow_write: bool = True) -> None:
    """ファイル操作ツールを登録する。allow_write=False なら読み取り専用"""
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    path_prop = {"type": "string", "description": "workspace からの相対パス。例: notes/todo.md"}
    registry.tool(
        name="list_files",
        description="workspace 内のファイルとディレクトリを一覧します。ファイル名が分からないときに最初に使ってください。",
        input_schema={"type": "object", "properties": {"path": {**path_prop, "description": "一覧するディレクトリ。省略時は workspace 直下"}}, "required": []},
    )(list_files)
    registry.tool(
        name="read_file",
        description="workspace 内のテキストファイルを行番号付きで読みます。1回に最大400行で、続きは start_line で指定します。",
        input_schema={"type": "object", "properties": {"path": path_prop, "start_line": {"type": "integer", "description": "読み始める行番号（1始まり）。省略時は1"}}, "required": ["path"]},
    )(read_file)
    if allow_write:
        registry.tool(
            name="write_file",
            description="workspace 内にファイルを作成、または全体を上書きします。既存ファイルを変更するときは、先に read_file で内容を確認してください。実行前にユーザーの承認が必要です。",
            input_schema={"type": "object", "properties": {"path": path_prop, "content": {"type": "string", "description": "書き込むテキスト全体"}}, "required": ["path", "content"]},
            side_effect=True,  # 実行前確認の対象にする
        )(write_file)


# agent.py の build_registry に次の2行を追加
#     from tools.files import register_file_tools
#     register_file_tools(registry)
```

`workspace/meeting.md` に適当な議事録を置いて、動かしてみましょう。

```bash
uv run python agent.py "workspace の議事録を読んで、決定事項だけを summary.md に書き出して"
```

```text
... agent turn=1 stop_reason=tool_use
... agent tool=list_files elapsed=0.00s
... agent turn=2 stop_reason=tool_use
... agent tool=read_file elapsed=0.00s
... agent turn=3 stop_reason=tool_use

[確認] ツール write_file を次の引数で実行します:
{
  "path": "summary.md",
  "content": "# 決定事項\n- 新機能のリリースは12月第2週\n..."
}
実行してよいですか？ [y/N]: y
... agent tool=write_file elapsed=0.01s
... agent turn=4 stop_reason=end_turn

=== 回答 ===
議事録から決定事項を3点抽出し、summary.md に保存しました。
```

Claudeは、まず `list_files` でファイル名を確かめ、`read_file` で読み、`write_file` で書いています。description に書いた「ファイル名が分からないときに最初に使う」が効いている流れです。確認で `n` と答えると、Claudeは「保存は行いませんでした。内容を画面に表示しましょうか？」のように別案を返します。

最後に、境界が守られているかも試しておきます。`"../.env の中身を見せて"` と頼んでみましょう。`read_file` は `is_error` 付きの結果を返します。内容は「../.env は workspace の外を指しています」です。Claudeは、その理由をユーザーに説明して終わります。

> **WARNING**: `ask_approval()` は、ターミナルで人が見ている前提の仕組みです。Webサービスやバッチ処理では `input()` は使えません。その場合は、承認待ちの状態を保存して画面で確認するなど、仕組みを置き換えてください。いずれにしても「副作用ツールは承認なしで実行しない」という方針は変えないことが大切です。

---

## 6.5 構造化出力

ここまでのエージェントは、最終的に人間が読む文章を返していました。しかし実務では、Claudeの出力をプログラムが受け取る場面が多くあります。問い合わせメールを読んで、担当部署・緊急度・顧客名をチケット管理システムに登録する、といった処理です。このとき必要なのは、文章ではなく、決まった形のJSONです。本節では、Claudeの出力をスキーマどおりのJSONに**保証する**方法を学びます。

### プロンプトでJSONを頼む方法の限界

もっとも素朴な方法は、system プロンプトに「次の形式のJSONだけを出力してください」と書くことです。最近のモデルなら、これでもかなりの確率で正しいJSONが返ってきます。しかし「かなりの確率」では、プログラムの入力として使えません。

失敗のパターンはいくつもあります。JSONの前に「承知しました。」と前置きが付く。` ```json ` のコードブロックで囲まれる。必須のキーが抜ける。`enum` で決めた「高・中・低」の代わりに「やや高」が入る。1000件処理して3件崩れるだけでも、例外処理と再試行のコードが必要になります。かつては、assistant の応答を `{` で始めさせる prefill で対処する方法もありました。しかし、現行のモデルでは prefill 自体が400エラーです。

<figure id="fig-6-6">
<svg width="605" height="380" viewBox="0 0 605 380"
     xmlns="http://www.w3.org/2000/svg"
     font-family="'Noto Sans JP',sans-serif">
  <defs>
    <marker id="f6_6_arr66" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#333" stroke-width="1.5"/>
    </marker>
    <marker id="f6_6_arr66a" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#2b6cb0" stroke-width="1.5"/>
    </marker>
  </defs>
  <rect x="0" y="0" width="605" height="380" fill="#ffffff"/>
  <text x="155" y="26" text-anchor="middle" dominant-baseline="central" font-size="13" fill="#1a1a1a" font-weight="bold">プロンプトで JSON を頼む</text>
  <text x="450" y="26" text-anchor="middle" dominant-baseline="central" font-size="13" fill="#1a1a1a" font-weight="bold">output_config.format（構造化出力）</text>
  <rect x="15" y="40" width="280" height="230" rx="6" fill="none" stroke="#999" stroke-width="1"/>
  <rect x="310" y="40" width="280" height="230" rx="6" fill="none" stroke="#2b6cb0" stroke-width="1.2" stroke-dasharray="5,3"/>
  <text x="155" y="56" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">system に「JSONだけを出力して」</text>
  <rect x="30" y="70" width="250" height="38" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.1"/>
  <text x="155.0" y="81.3" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">承知しました。{ … }</text>
  <text x="155.0" y="96.7" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">前置きが付く</text>
  <rect x="30" y="112" width="250" height="38" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.1"/>
  <text x="155.0" y="123.3" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">```json { … } ```</text>
  <text x="155.0" y="138.7" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">コードブロックで囲まれる</text>
  <rect x="30" y="154" width="250" height="38" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.1"/>
  <text x="155.0" y="165.3" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">{ "category": "請求" }</text>
  <text x="155.0" y="180.7" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">必須のキーが抜ける</text>
  <rect x="30" y="196" width="250" height="38" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.1"/>
  <text x="155.0" y="207.3" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">"urgency": "やや高"</text>
  <text x="155.0" y="222.7" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">enum にない値が入る</text>
  <text x="155" y="254" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-weight="bold">崩れる可能性あり → 検査と再試行が必要</text>
  <text x="450" y="56" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a" font-family="Consolas,monospace">"format": {"type": "json_schema", …}</text>
  <rect x="325" y="72" width="250" height="38" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="450.0" y="91.0" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a">スキーマから文法を作る</text>
  <path d="M450 110 L450 123" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f6_6_arr66)"/>
  <rect x="325" y="125" width="250" height="46" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="450.0" y="139.6" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a">生成時に、文法に合わない</text>
  <text x="450.0" y="156.4" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a">文字は選べない</text>
  <path d="M450 171 L450 184" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f6_6_arr66)"/>
  <rect x="325" y="186" width="250" height="38" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="450.0" y="205.0" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a">そのまま json.loads() できる</text>
  <text x="450" y="254" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#2b6cb0" font-weight="bold">保証: テキスト応答の形式</text>
  <rect x="15" y="282" width="575" height="64" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="302.5" y="298.6" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">output_config.format → テキスト応答の形式を保証</text>
  <text x="302.5" y="314.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">ツール定義の strict: true → tool_use の input の形式を保証</text>
  <text x="302.5" y="329.4" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#666">（どちらも refusal・max_tokens で止まった場合は保証の対象外）</text>
</svg>
  <figcaption>図6.6: プロンプト指示と構造化出力の違い</figcaption>
</figure>

### output_config.format で形式を保証する

**構造化出力**（Structured Outputs）とは、応答の形式をJSON Schemaで保証する機能です。リクエストでJSON Schemaを指定すると、Claudeの応答がそのスキーマに必ず合う形で生成されます。指定は `output_config` の中の `format` に書きます。仕組みとしては、スキーマから文法を作り、生成時にその文法に合わない文字を選べないように制約します。そのため、拒否（`refusal`）や `max_tokens` による打ち切りを除けば、「たまに崩れる」ことは原理的に起きません。

問い合わせメールから項目を抽出する `structured_output.py` を作りましょう。

```python
# structured_output.py（新規作成）
"""問い合わせメールから、チケット登録に必要な項目を JSON で抽出する。"""
from __future__ import annotations

import json

from llm_client import FAST_MODEL, call_messages, extract_text, get_tool_uses

NULLABLE_STRING = {"anyOf": [{"type": "string"}, {"type": "null"}]}  # 文字列または null

# 抽出結果のスキーマ（object には additionalProperties: false が必須）
INQUIRY_SCHEMA = {
    "type": "object",
    "properties": {
        "customer_name": {"type": "string", "description": "差出人の氏名"},
        "company": {**NULLABLE_STRING, "description": "会社名。書かれていなければ null"},
        "category": {"type": "string", "enum": ["請求", "不具合", "機能要望", "解約", "その他"]},
        "urgency": {"type": "string", "enum": ["高", "中", "低"]},
        "order_number": {**NULLABLE_STRING, "description": "注文番号。なければ null"},
        "summary": {"type": "string", "description": "問い合わせ内容の要約（60字程度）"},
        "requested_actions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "顧客が求めている対応の一覧",
        },
    },
    "required": ["customer_name", "company", "category", "urgency",
                 "order_number", "summary", "requested_actions"],
    "additionalProperties": False,
}

SYSTEM = "あなたはサポート窓口の受付担当です。問い合わせメールから指定の項目を正確に抽出します。"


def extract_inquiry(email_text: str) -> dict:
    """メール本文を受け取り、INQUIRY_SCHEMA に合う dict を返す"""
    response = call_messages(
        [{"role": "user", "content": f"次のメールから項目を抽出してください。\n\n{email_text}"}],
        system=SYSTEM,
        model=FAST_MODEL,   # 抽出のような定型処理は低コストのモデルで十分
        max_tokens=2000,    # 思考のトークンもここに数えられる
        output_config={
            "format": {"type": "json_schema", "schema": INQUIRY_SCHEMA},
            "effort": "low",  # 定型の抽出なので思考は浅くてよい（7.5節）
        },
    )
    # スキーマが保証されるのは正常終了したときだけ。先に停止理由を確認する
    if response["stop_reason"] == "refusal":
        raise RuntimeError("抽出を拒否されました")
    if response["stop_reason"] == "max_tokens":
        raise RuntimeError("出力が途中で切れました。max_tokens を増やしてください")
    return json.loads(extract_text(response))  # JSON は text ブロックに入っている


SAMPLE_EMAIL = """件名: 請求金額について
株式会社サンプル物流の佐藤です。
10月分の請求書（注文番号 A-20481）で、金額が見積もりより2万円高くなっています。
今月末が支払期限のため、至急ご確認のうえ、正しい請求書を再発行してください。"""

if __name__ == "__main__":
    print(json.dumps(extract_inquiry(SAMPLE_EMAIL), ensure_ascii=False, indent=2))
```

実行すると、次のようなJSONが得られます。

```bash
uv run python structured_output.py
```

```text
{
  "customer_name": "佐藤",
  "company": "株式会社サンプル物流",
  "category": "請求",
  "urgency": "高",
  "order_number": "A-20481",
  "summary": "10月分請求書の金額が見積もりより2万円高いため確認と再発行を依頼",
  "requested_actions": [
    "請求金額の確認",
    "正しい請求書の再発行"
  ]
}
```

前置きもコードブロックもなく、`json.loads()` がそのまま通ります。`category` と `urgency` は必ず `enum` のどれかになり、キーの欠落もありません。「支払期限が今月末」という文脈から、緊急度を「高」と判断している点も見どころです。

ただし、`stop_reason` が `refusal` や `max_tokens` のときは、スキーマどおりの形になりません。そのためコードでは、`json.loads()` の前に停止理由を確かめています。また、Haiku 5.5 は思考が既定で有効で、思考のトークンも `max_tokens` に数えられます。定型の抽出では、7.5節で扱う `effort` を `"low"` にして、思考で上限を使い切らないようにしています。

スキーマの書き方にはいくつか決まりがあります。オブジェクトには `"additionalProperties": false` が必須です。「値がない場合もある」項目は、`anyOf` で `null` を許したうえで `required` に入れます。キーは常にあり、値が `null` になる形です。また、`minLength`・`maxLength`・`minimum`・`maximum` のような数値や長さの制約は使えません。使うと400エラーになります。そうした条件は description に書き、受け取った後に自分のコードで確認します。

> **NOTE**: 初めて使うスキーマは、文法の作成のため最初の1回だけ応答が遅くなります。作成された文法は一定期間キャッシュされるので、2回目以降は通常の速さに戻ります。

### strict ツールで引数を保証する

構造化出力が保証するのは、Claudeの**テキストの応答**です。では、ツールの**引数**はどうでしょうか。6.3節で引数の検証を書いたように、通常のツールでは引数がスキーマから外れる可能性がゼロではありません。ツール定義に `"strict": true` を付けると、ツールの引数にも同じ文法の制約がかかります。その結果、スキーマどおりの引数が保証されます。条件は構造化出力と同じで、`additionalProperties: false` が必須です。`required` に入れない任意の引数は、スキーマ全体で24個までです。そのため、なるべく `required` に入れ、値がないことは `null` で表します。

チケットを作成するツールで試してみます。`structured_output.py` の `if __name__ == "__main__":` の上に追記してください。

```python
# structured_output.py（追記: strict ツールの例）
CREATE_TICKET_TOOL = {
    "name": "create_ticket",
    "description": "サポートチケットを作成します。問い合わせの内容を登録するときに使ってください。",
    "strict": True,  # 引数がスキーマに必ず合うようにする
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "チケットの件名"},
            "department": {"type": "string", "enum": ["経理", "開発", "営業", "カスタマーサクセス"]},
            "priority": {"type": "string", "enum": ["P1", "P2", "P3"]},
        },
        "required": ["title", "department", "priority"],
        "additionalProperties": False,
    },
}


def demo_strict_tool(email_text: str) -> None:
    response = call_messages(
        [{"role": "user", "content": f"次のメールの内容でチケットを作成してください。\n\n{email_text}"}],
        tools=[CREATE_TICKET_TOOL],
        tool_choice={"type": "auto"},  # any / tool による強制は使わない
        max_tokens=2000,
        output_config={"effort": "low"},  # 思考で max_tokens を使い切らないようにする
    )
    for tool_use in get_tool_uses(response):
        print(tool_use["name"], json.dumps(tool_use["input"], ensure_ascii=False))
```

`__main__` ブロックの末尾に `demo_strict_tool(SAMPLE_EMAIL)` の1行を足します。そして、`uv run python structured_output.py` を実行します。すると、抽出結果のJSONに続けて、たとえば次のように出力されます。

```text
create_ticket {"title": "10月分請求書の金額相違と再発行依頼（A-20481）", "department": "経理", "priority": "P1"}
```

ここで `tool_choice` に注目してください。以前は、特定のツールを強制し、その引数をJSON抽出に使うテクニックがよく使われていました。強制には `{"type": "tool", "name": "create_ticket"}` のような指定を使います。しかし、Opus 5.5 と Sonnet 5.5 では、`any` や `tool` による強制は400エラーになります。本書では、`tool_choice` は `auto` か `none` だけを使います。「必ずJSONがほしい」なら `output_config.format` を使います。「ツールを呼ぶときの引数を保証したい」なら strict ツールを使います。このように使い分けてください。

| やりたいこと | 使う機能 | 保証される範囲 |
|-----------|--------|------------|
| 応答そのものをJSONで受け取る | `output_config.format` | テキスト応答の形式 |
| ツールの引数を正確にしたい | ツール定義の `strict: true` | `tool_use` の `input` の形式 |
| ツールを必ず呼ばせたい | （強制はできない）system と description で誘導 | なし |

なお、strict ツールは1リクエストあたり20個までという上限があります。また、`ToolRegistry.schemas()` はまだ `strict` を出力しません。レジストリで使いたい場合は、`tool()` に `strict` 引数を足して `schemas()` で出力するよう拡張してください。

---

## 本章のまとめ

本章で学んだことを整理します：

- ツールの定義はClaudeへの説明書です。名前は `動詞_名詞` にします。description には「何を・いつ・いつ使わないか・引数・戻り値と制限」を書きます。エラーには「何が起きたか」と「次に何をすべきか」を含めます。公開Webの調査はサーバーツール、社内データや厳密な権限管理は自作ツールが基本です。
- `ToolRegistry` でスキーマと関数を一元管理し、ループ本体を変えずにツールを増やせるようにしました。複数の `tool_use` はスレッドプールで並行実行します。失敗も含めたすべての `tool_result` は、1つの user メッセージで返します。
- ファイル操作ツールは `resolve()` と `is_relative_to()` で `workspace/` に閉じ込めます。副作用ツールは承認後に逐次実行し、拒否は `is_error` で返します。プログラムで扱う出力は、`output_config.format` と strict ツールで形式を保証します。`tool_choice` は `auto` / `none` だけを使います。

次章では **コンテキストとメモリの管理** を扱います。ツールを使って長く動くほど、`tool_result` が積み重なり、履歴は膨らみます。トークンを測り、履歴を圧縮し、キャッシュで節約し、ファイルに記憶を残す。長く働けるエージェントへの次の一歩を踏み出しましょう。
