# 第3章: Messages APIを理解する
# EN-TITLE: UNDERSTANDING THE MESSAGES API
# TAGS: Messages API, リクエストとレスポンス, stop_reason, 会話履歴, HTTPステータス

> [!DIALOGUE]
> **生徒**: 前の章で、Claudeから返事をもらえました。もう次はエージェントを作れますか？
> **先生**: 気持ちは分かります。でも、まだ「返事の取り出し方」を1通り知っただけなんです。
> **生徒**: 動いたなら十分な気がしますけど……。
> **先生**: 返事が途中で切れたら？ 会話を続けたら？ エラーが返ったら？ ここを押さえるのが第3章です。
> **生徒**: たしかに、どれも想像がつきません。
> **先生**: エージェントは、この1往復を何十回も繰り返す仕組みです。だから土台の理解が効いてきますよ。

## この章で学ぶこと

本章では以下を学びます：

- Messages APIのリクエスト（ヘッダーとボディ）と、レスポンスの全フィールドの意味を説明できるようになる
- `stop_reason` と `content` 配列を正しく扱い、安全に回答を取り出すコードを書けるようになる
- system プロンプトや `max_tokens`・`stop_sequences`・`effort` で出力を制御できるようになる
- APIがステートレスであることを理解し、会話履歴を自分で管理するCLIチャットを実装できるようになる
- エラーレスポンスとHTTPステータスから、失敗の原因とリトライの要否を判断できるようになる

前章では、Claude Consoleで発行したAPIキーを使い、curlと `httpx` で最初のリクエストを送りました。
本章では、その1往復を分解して、Messages APIの仕様を細部まで理解します。
作るファイルは `inspect_response.py`・`params_demo.py`・`chat.py`・`error_lab.py` の4つです。
まだ共通のクライアントモジュールはないため、どのスクリプトも `httpx` を直接使って書きます。

---

## 3.1 リクエストの構造

第2章の `hello_claude.py` は、十数行のコードでClaudeから返事を受け取れました。
しかし、そのリクエストの中身を1項目ずつ説明できるでしょうか。
「ヘッダーは何のためにあるのか」「`max_tokens` はなぜ必須なのか」と問われると、迷う方も多いはずです。
この節では、Messages API（メッセージズ・エーピーアイ）へのリクエストを部品に分けて確認します。
仕様を自分の言葉で説明できる状態が、エージェントを自作するための出発点になります。

### HTTPリクエストを3つの部品に分ける

HTTP（エイチティーティーピー）は HyperText Transfer Protocol の略です。
HTTPのリクエストは、大きく3つの部品でできています。
1つ目は「どこに、どうやって送るか」を示すメソッドとURLです。
2つ目は、送り主や形式などの付帯情報を伝えるヘッダーです。
3つ目は、実際に処理してほしい内容を入れるボディ（本体）です。

封筒にたとえると、分かりやすくなります。
メソッドとURLは宛先、ヘッダーは封筒の表に書く差出人や「速達」などの指示です。
ボディは、封筒の中に入れる手紙そのものです。
宛先が違えば届かず、差出人が不明なら受け取りを拒否され、手紙が読めなければ返事は書けません。

Messages APIでは、この3つの部品が次のように決まっています。
メソッドは `POST`、URLは `https://api.anthropic.com/v1/messages` です。
ヘッダーには認証とバージョンと形式の3つを入れます。
ボディにはJSON（ジェイソン、JavaScript Object Notation）を入れます。
この対応を頭に入れておくと、エラーが起きたときに「どの部品の問題か」を素早く切り分けられます。

[FIG_3_1｜構造図｜可｜Messages APIリクエストの構造｜メソッドとURL・ヘッダー3種・JSONボディの3層]

### 必須ヘッダーは3つ

Messages APIに送るリクエストには、次の3つのヘッダーが必須です。

| ヘッダー | 値の例 | 役割 |
|--------|------|-----|
| `x-api-key` | Consoleで発行したAPIキー | 誰からのリクエストかを証明する（認証） |
| `anthropic-version` | `2026-10-21` | どの版のAPI仕様で解釈するかを指定する |
| `content-type` | `application/json` | ボディがJSONであることを伝える |

`x-api-key` は、APIキーそのものを入れるヘッダーです。
ここが空だったり、間違っていたりすると、サーバーは中身を読む前に401エラーを返します。

APIキーは課金と結びついた秘密情報なので、コードに直接書かず `.env` から読み込みます。
この点は第2章で設定した方法を、本章のすべてのスクリプトでもそのまま使います。

> **NOTE**: 公式ドキュメントでは、`Authorization: Bearer <APIキー>` ヘッダーで認証する例が主に載っています。
> `x-api-key` も引き続き有効な書き方で、本書はこちらで統一します。
> どちらか一方を送れば認証されます。

`anthropic-version` は、API仕様の「版」を指定するヘッダーです。
APIは年月とともに改良されますが、既存のプログラムが突然動かなくなっては困ります。
そこで、リクエストごとに「この日付の仕様で解釈してください」と明示する仕組みになっています。
本書では最新版の `2026-10-21` を使います。
同じボディでも、指定するバージョンによって受け付けられる項目が変わる点に注意してください。

`content-type` は、ボディの形式を伝えるヘッダーです。
Messages APIはJSONしか受け付けないため、値は常に `application/json` です。
`httpx` の `json=` 引数でボディを渡すと、このヘッダーは自動で付きます。
それでも本書では、3つのヘッダーをそろえて明示的に書きます。
どのヘッダーを送っているかがコードを見ただけで分かり、curlの例とも対応が取りやすいからです。

> **NOTE**: ベータ機能を試すときは、4つ目のヘッダーとして `anthropic-beta: <ベータ名>` を追加します。
> 正式公開前の機能を明示的に有効にするためのものです。本書では原則としてベータ機能は使いません。

### ボディの必須項目は3つ

ボディには、最低限 `model`・`max_tokens`・`messages` の3項目が必要です。
第2章で送った最小のボディを、もう一度見てみましょう。

```jsonc
// 最小のリクエストボディ（第2章の hello_claude.py が送った内容）
{
  "model": "claude-opus-5-5",          // 使うモデルのID
  "max_tokens": 1024,                  // 出力トークン数の上限（必須）
  "messages": [                        // 会話の履歴（配列）
    {"role": "user", "content": "こんにちは、Claude"}
  ]
}
```

`model` は、どのモデルに処理させるかを指定する項目です。
本書の既定は `claude-opus-5-5` で、モデルIDに日付の接尾辞は付きません。
軽い分類や要約には `claude-haiku-5-5`、その中間には `claude-sonnet-5-5` を使えます。
モデルの使い分けは3.3節で詳しく扱います。

`max_tokens` は、Claudeが生成してよい出力トークン数の上限です。
トークン（token）とは、モデルが文章を処理する単位のことです。
日本語ではおおむね1文字が1トークン前後と考えておけば十分です（正確な数は第7章のトークン計測APIで確かめられます）。
この項目が必須なのは、出力の長さに応じて料金と待ち時間が増えるからです。
上限を決めずに送ることはできず、省略すると400エラーになります。

`messages` は、それまでの会話を時系列に並べた配列です。
各要素は `role`（話者）と `content`（内容）を持つオブジェクトです。
`role` には `user`（あなたのプログラム側）か `assistant`（Claude側）を入れます。
1回目のリクエストでは、`user` のメッセージが1つだけ入っている形が基本です。

### 任意の項目をひととおり見ておく

必須の3項目のほかに、ボディには多くの任意項目を入れられます。
本書で使う主なものを、先に一覧にしておきます。

| 項目 | 型 | 役割 | 本書で扱う章 |
|-----|---|-----|-----------|
| `system` | 文字列またはブロック配列 | Claudeの役割・制約・前提を伝える | 本章3.3節 |
| `stop_sequences` | 文字列の配列 | 指定した文字列が出たら生成を止める | 本章3.3節 |
| `output_config` | オブジェクト | 思考の深さ（`effort`）や出力形式（`format`）を指定する | 本章3.3節・第6章 |
| `tools` | 配列 | Claudeが呼び出せるツールの定義 | 第5章 |
| `tool_choice` | オブジェクト | ツールを使うかどうかの方針 | 第5章 |
| `stream` | 真偽値 | 応答を少しずつ受け取る（SSE） | 第4章 |

`system` は、会話全体に効く前提条件を渡す項目です。
`messages` の中には入れず、ボディのトップレベルに置きます。
`output_config` は、出力の制御をまとめて担う項目です。
`effort` で考える深さを、`format` でJSONなどの出力形式を指定します。

`tools` と `tool_choice` は、エージェントの中核になる項目です。
`tool_choice` は `{"type": "auto"}` か `{"type": "none"}` の2通りを使います。
特定のツールを強制する指定（`any`・`tool`）は、本書の既定の Opus 5.5 と Sonnet 5.5 では400エラーになります。
`stream` を `true` にすると、応答を細切れに受け取れます。
この仕組みは第4章で、自作のパーサーを書きながら理解していきます。

> **POINT**: 本章でボディを組み立てるときは、必須の3項目に `system` を足した形を基本にします。
> 任意項目は「何を変えたいのか」がはっきりしたときに1つずつ足すと、効果を確かめやすくなります。

### messagesの形: 文字列とブロック配列

`messages` の各要素の `content` には、2つの書き方があります。
1つは、これまでの例のように文字列をそのまま入れる書き方です。
もう1つは、「ブロック」と呼ばれるオブジェクトを配列で並べる書き方です。
次の2つは、Claudeにとってまったく同じ意味のリクエストになります。

```jsonc
// content の2つの書き方（どちらも同じ意味になる）
[
  // 書き方1: 文字列で渡す（短いテキストだけのとき）
  {"role": "user", "content": "Pythonのリストを説明して"},

  // 書き方2: ブロック配列で渡す（画像やツール結果を混ぜるとき）
  {"role": "user", "content": [
    {"type": "text", "text": "Pythonのリストを説明して"}
  ]}
]
```

文字列の書き方は、テキストを1つ送るだけのときの省略形です。
内部的には、`type` が `text` のブロック1つとして扱われます。
ブロック配列の書き方は、複数の種類の情報を1つのメッセージに混ぜるときに使います。
たとえば、画像とその説明文を一緒に送る場合や、ツールの実行結果を返す場合です。

この2つの書き方の違いは、エージェントを作るときに大きな意味を持ちます。
第5章で扱う `tool_result` は、必ずブロック配列の形で返します。
また、Claudeから返ってくる応答の `content` も、常にブロック配列です。
「`content` は文字列とは限らない」と最初から意識しておくと、後の章でつまずきません。

### roleの交互ルール

`messages` の配列は、`user` と `assistant` を交互に並べるのが原則です。
最初の要素は `user` にします。
会話を続けるときは、`user`・`assistant`・`user`……という順に積み上げます。

連続した同じ `role` のメッセージは、API側で1つのターンにまとめて扱われます。
そのためすぐにエラーになるとは限りませんが、意図しない解釈を招く原因になります。
たとえば、送信に失敗した `user` メッセージを消し忘れて次の入力を足すと、2つの質問が1つにつながります。
Claudeは2つの質問に同時に答えようとして、会話の流れがおかしくなります。
本書のコードでは、交互の並びを常に保つように履歴を管理します。
具体的な書き方は、3.4節の `chat.py` で確認します。

[FIG_3_2｜概念図｜可｜messages配列の交互ルール｜userとassistantが交互に積み上がる履歴の配列]

### 2026-10-21版と最新モデルでの注意点

ここで、本書が前提とするAPIバージョン `2026-10-21` と、本書で使うモデルの注意点を整理します。
古い解説記事やサンプルコードを参考にするときに、特に混乱しやすい部分です。

1つ目は、`temperature`・`top_p`・`top_k` を送ると400エラーになることです。
これらは、出力のランダムさを調整する「サンプリングパラメータ」と呼ばれる項目でした。
2026-10-21版では、既定値と同じ値を送った場合でも400エラーになります。
「`temperature` を0にすると回答が安定する」という説明を見かけたら、古い版の話だと考えてください。

2つ目は、assistantの「prefill（プリフィル）」が使えないことです。
prefillとは、`messages` の最後を `assistant` のメッセージで終え、応答の書き出しを指定する技法です。
たとえば最後に `{"role": "assistant", "content": "{"}` を置き、JSONで答えさせる使い方がありました。
本書で使うモデルでは、この形のリクエストは400エラーになります。
こちらはAPIバージョンの変更ではなく、Claude 4.6以降のモデルの制約です。

では、出力の形や長さはどう制御すればよいのでしょうか。
本書では、次の5つの手段を使い分けます。

| 制御したいこと | 2026-10-21版での手段 |
|-------------|-------------------|
| 役割・口調・回答の方針 | system プロンプトで指示する |
| JSONなど決まった形式 | 構造化出力（`output_config.format`）を使う（第6章） |
| 考える深さとトークン消費 | `output_config.effort` を指定する |
| 特定の文字列で止める | `stop_sequences` を指定する |
| 出力の最大の長さ | `max_tokens` で上限を決める |

かつては「`temperature` で揺れを抑え、prefillで形式を固定する」のが定番でした。
現在は、指示は `system` に、形式は構造化出力に、深さは `effort` に任せます。
役割ごとに専用の手段が用意されたと考えると、整理しやすくなります。
それぞれの使い方は、3.3節で実際に動かしながら確認します。

> **WARNING**: インターネット上のサンプルコードには、`temperature` を指定しているものが今も多く残っています。
> そのまま本書のコードに混ぜると400エラーになります。エラーが出たら、まずボディにこれらの項目がないかを確認してください。

### ボディを組み立てるPythonの形

ここまでの内容を、Pythonの辞書（dict）として組み立てる形にしておきます。
本章の4つのスクリプトは、どれもこの形を出発点にします。

```python
# inspect_response.py ほか本章のスクリプトに共通する組み立て方（抜粋）
import os

from dotenv import load_dotenv

# .env から ANTHROPIC_API_KEY を読み込む
load_dotenv()

# 送り先とAPIバージョン・既定モデルは定数にまとめておく
API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2026-10-21"
MODEL = "claude-opus-5-5"

# 必須ヘッダー3種を作る（キーはコードに書かず環境変数から読む）
headers = {
    "x-api-key": os.environ["ANTHROPIC_API_KEY"],
    "anthropic-version": API_VERSION,
    "content-type": "application/json",
}

# ボディは必須3項目＋system を基本形にする
body = {
    "model": MODEL,
    "max_tokens": 4096,
    "system": "あなたは初心者に優しいPython講師です。",
    "messages": [
        {"role": "user", "content": "リストとタプルの違いを教えてください。"},
    ],
}
```

このコードは単独で実行するものではなく、本章のスクリプトに共通する骨組みの見本です。
定数を冒頭にまとめておくと、モデルやバージョンを変えたいときに1か所の修正で済みます。
ヘッダーを作る部分は、第4章で `build_headers()` という関数に切り出します。
ここではまず、「ヘッダーの辞書」と「ボディの辞書」の2つを作れば送れる、と覚えてください。

`max_tokens` を4096にしているのには理由があります。
本書の既定モデルである Opus 5.5 では、adaptive thinking（アダプティブ・シンキング）が常に有効です。
これは、Claudeが必要に応じて回答の前に「考える」処理を行う仕組みです。
考えるために使ったトークンも、`max_tokens` の上限に含まれます。
上限を小さくしすぎると、考えている途中で打ち切られ、回答の本文が空になることがあります。
本章の実験では、短い回答でも余裕を持たせて4096程度を指定します。

リクエストの全体像がつかめたところで、次はサーバーから返ってくるレスポンスを詳しく見ていきます。

---

## 3.2 レスポンスの構造

第2章では、レスポンスの中から回答のテキストだけを取り出して表示しました。
しかし、返ってくるJSONには、テキスト以外にも多くの情報が含まれています。
「なぜ応答が終わったのか」「何トークン使ったのか」「このやり取りを後から特定する手がかりは何か」。
こうした情報を読み飛ばしていると、回答が途中で切れていても気づけません。
この節では、レスポンスの全フィールドを読み解き、安全に回答を取り出す方法を身につけます。

### レスポンスJSONの全体像

まず、レスポンスの典型的な形を見てみましょう。
「リストとタプルの違いを教えてください」と送ったときの応答を、読みやすく整形したものです。

```jsonc
// Messages API のレスポンス例（inspect_response.py で表示される内容を整形）
{
  "id": "msg_01XFDUDYJgAACzvnptvVoYEL",     // このメッセージの一意なID
  "type": "message",                        // オブジェクトの種類（常に "message"）
  "role": "assistant",                      // 話者（常に "assistant"）
  "model": "claude-opus-5-5",               // 実際に応答したモデル
  "content": [                              // 応答の本体（ブロックの配列）
    {
      "type": "thinking",                   // 思考のブロック
      "thinking": "",                       // 既定では中身は空文字
      "signature": "EqQBCkgIARABGAIi..."    // 改ざん検知用の署名
    },
    {
      "type": "text",                       // テキストのブロック
      "text": "リストとタプルの大きな違いは、作成後に中身を変更できるかどうかです。..."
    }
  ],
  "stop_reason": "end_turn",                // 応答が終わった理由
  "stop_sequence": null,                    // 停止に使われた stop_sequences の文字列
  "stop_details": null,                     // 停止理由の詳細（refusal のときに入る）
  "usage": {                                // トークン使用量
    "input_tokens": 42,
    "output_tokens": 318,
    "cache_creation_input_tokens": 0,
    "cache_read_input_tokens": 0,
    "output_tokens_details": {"thinking_tokens": 96}
  }
}
```

一見すると項目が多く感じますが、役割ごとに4つのグループに分けると整理できます。
1つ目は、`id`・`type`・`role`・`model` の「このメッセージは何か」を示すグループです。
2つ目は、`content` の「応答の中身」のグループです。
3つ目は、`stop_reason`・`stop_sequence`・`stop_details` の「なぜ終わったか」のグループです。
4つ目は、`usage` の「どれだけ使ったか」のグループです。

[FIG_3_3｜構造図｜可｜レスポンスJSONの4つのグループ｜識別情報・content・停止理由・usageの4区分]

### 識別情報のグループ: id・type・role・model

`id` は、このメッセージに割り振られた一意な識別子です。
`msg_` で始まる文字列で、同じ値が二度返ることはありません。
ログに残しておくと、「どの応答で問題が起きたか」を後から特定する手がかりになります。

`type` は、返ってきたオブジェクトの種類です。
正常な応答では常に `"message"` になり、エラーのときは `"error"` になります。
この値を見るだけで、成功か失敗かを大まかに判断できます。

`role` は、常に `"assistant"` です。
「なぜわざわざ毎回入っているのか」と思うかもしれません。
これは、レスポンスの形が `messages` 配列の要素とそろうように設計されているためです。
3.4節で見るように、応答の `role` と `content` は、そのまま次のリクエストの履歴に積み直せます。

`model` は、実際に応答したモデルのIDです。
リクエストで指定したモデルと同じ値が入ります。
複数のモデルを使い分ける第8章以降では、ログでモデルを確認する場面が増えます。

### contentはブロックの配列

レスポンスでもっとも重要なのが `content` です。
`content` は、文字列ではなく「ブロックの配列」です。
1回の応答の中に、種類の異なるブロックが複数並ぶことがあります。

本書で扱う主なブロックの種類は、次の3つです。

| `type` の値 | 中身 | 登場する場面 |
|-----------|-----|-----------|
| `text` | 回答の文章（`text` フィールド） | ほぼすべての応答 |
| `thinking` | 思考の内容（`thinking`）と署名（`signature`） | adaptive thinking が働いたとき |
| `tool_use` | 呼び出したいツールの名前と引数 | `tools` を渡したとき（第5章） |

さきほどの例では、`thinking` ブロックのあとに `text` ブロックが続いていました。
Opus 5.5 は adaptive thinking が常に有効なので、回答の前に思考のブロックが入ることがあります。
既定では `thinking` フィールドの中身は空文字で、思考の詳細は返ってきません。
それでも、ブロックそのものは配列に含まれ得る点が重要です。

ここで、初心者がもっとも陥りやすい落とし穴があります。
回答を `data["content"][0]["text"]` のように、先頭決め打ちで取り出すコードです。
先頭が `thinking` ブロックだった場合、このコードは `KeyError` で止まります。
運よく動いていたコードが、ある日突然エラーを出す原因になります。

正しいやり方は、配列を順に見て `type` で判定することです。
回答のテキストがほしいなら、`type` が `"text"` のブロックだけを集めて連結します。
こうしておけば、ブロックの順番や数が変わっても正しく動きます。
第5章で `tool_use` ブロックが混ざるようになっても、同じ考え方で処理できます。

> **POINT**: `content` は「先頭を取る」ものではなく、「型で選ぶ」ものです。
> `content[0]` と書きたくなったら、`type` で判定するループに置き換えてください。

### 停止理由のグループ: stop_reason

`stop_reason` は、Claudeが応答の生成を止めた理由を表します。
回答の本文を読む前に、必ずこの値を確認する習慣をつけてください。
同じ「返ってきたテキスト」でも、止まった理由によって意味がまったく変わるからです。

| `stop_reason` | 意味 | プログラムでの扱い |
|-------------|-----|---------------|
| `end_turn` | 自然な区切りで回答を終えた | 通常の完了。回答をそのまま使う |
| `max_tokens` | `max_tokens` の上限に達して打ち切られた | 回答は途中まで。上限を上げるか、ユーザーに伝える |
| `stop_sequence` | `stop_sequences` で指定した文字列が出た | 意図どおりの停止。`stop_sequence` で何に当たったかを確認 |
| `tool_use` | ツールを呼び出したい | ツールを実行して結果を返す（第5章） |
| `pause_turn` | 長い処理を一時停止した | 応答をそのまま送り返して続きを促す（第6章で紹介） |
| `refusal` | 安全上の理由で応答を断った | `stop_details` を確認し、回答としては扱わない |

`end_turn` は、もっとも普通の終わり方です。
Claudeが「言うべきことを言い終えた」と判断した状態です。

`max_tokens` は、上限に達して強制的に止められた状態です。
文章が途中で切れているかもしれず、JSONなら閉じかっこが欠けているかもしれません。
このまま使うと、後続の処理で予期しない失敗につながります。
少なくとも、ユーザーに「回答が途中で切れた」と伝える処理が必要です。

`stop_sequence` は、自分で指定した区切りの文字列で止まった状態です。
このとき、`stop_sequence` フィールドに、実際に当たった文字列が入ります。
3.3節の `params_demo.py` で実際に確かめます。

`tool_use` と `pause_turn` は、エージェントを作る段階で中心になる値です。
特に `tool_use` は、第5章で作るエージェンティックループの「続けるかどうか」の判定そのものです。
いまは「こういう値もある」と知っておけば十分です。

`refusal` は、Claudeが安全上の理由で応答を断ったことを示します。
このときは `stop_details` フィールドに詳細が入ります。
`stop_details` の `type` は `"refusal"` です。
`category` には `"cyber"` や `"bio"` などの分類が入ります。
分類に当てはまらない場合、`category` は `null` です。
`explanation` に人間向けの説明が入ることもあります。
ただし文言は将来変わり得るので、プログラムの分岐には使いません。

> **NOTE**: APIリファレンスには、ほかに `model_context_window_exceeded` という値も載っています。
> コンテキストの上限を超えたことを表す値です。
> 本書のコードでは、知らない値が来たときに「想定外の停止理由」として表示する作りにして、将来の追加にも備えます。

[FIG_3_4｜フロー｜可｜stop_reasonによる分岐｜end_turnやmax_tokensなど値ごとの処理の分かれ道]

### 使用量のグループ: usage

`usage` は、そのリクエストで消費したトークン数です。
料金はこの値をもとに計算されるので、コストを意識するうえで欠かせません。
主な項目は次の4つです。

| フィールド | 意味 |
|----------|-----|
| `input_tokens` | 入力として処理したトークン数（キャッシュを使わなかった分） |
| `output_tokens` | 出力したトークン数（思考に使った分を含む） |
| `cache_creation_input_tokens` | プロンプトキャッシュに書き込んだトークン数 |
| `cache_read_input_tokens` | プロンプトキャッシュから読み込んだトークン数 |

`input_tokens` には、`system`・`messages`・`tools` など、送ったものすべてが含まれます。
会話の履歴を送り直すと、この値がどんどん大きくなります。
この様子は、3.4節のチャットで実際に観察します。

`output_tokens` には、目に見える回答だけでなく、思考に使ったトークンも含まれます。
`output_tokens_details.thinking_tokens` を見ると、そのうち思考に使った量が分かります。
`thinking` ブロックの中身が空でも、思考の分は出力トークンとして課金される点に注意してください。

キャッシュに関する2つの項目は、第7章のプロンプトキャッシュで使います。
本章の段階では、どちらも0のままです。

`usage` には、ここに挙げた以外の項目が含まれることもあります。
APIは後方互換を保ちながら項目を追加していくため、知らない項目があっても無視して構いません。
コードで読み取るときは、既定値を決めておくと安全です。
たとえば `usage.get("cache_read_input_tokens", 0)` のように書きます。

### request-idヘッダー: 問い合わせの手がかり

レスポンスのボディとは別に、レスポンスヘッダーにも大切な情報が入っています。
それが `request-id` ヘッダーです。
`req_` で始まる文字列で、1回のリクエストごとに一意な値が振られます。

`request-id` は、サポートに問い合わせるときの「受付番号」の役割を果たします。
「昨日の15時ごろにおかしな応答が返った」と伝えても、調査は困難です。
`request-id` を添えれば、どのリクエストかを正確に特定してもらえます。
エラーのときは、エラーボディの `request_id` フィールドにも同じ値が入ります。

本書では、第4章以降の `llm_client.py` で、すべてのリクエストの `request-id` をログに残します。
本章の段階でも、表示する習慣をつけておきましょう。

### inspect_response.pyを作る

ここまで見てきたフィールドを、実際のレスポンスで確かめるスクリプトを作ります。
`inspect_response.py` は、1回リクエストを送り、レスポンスを部品ごとに分解して表示する道具です。
プロジェクトフォルダー `agent-from-scratch/` に、次の内容で新規作成してください。

```python
# inspect_response.py
"""Messages API のレスポンスを部品ごとに分解して表示する（第3章・新規作成）"""
import json
import os
import sys

import httpx
from dotenv import load_dotenv

# .env から ANTHROPIC_API_KEY を読み込む
load_dotenv()

# 送り先・APIバージョン・既定モデル
API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2026-10-21"
MODEL = "claude-opus-5-5"

# 接続は10秒、応答全体は120秒まで待つ
TIMEOUT = httpx.Timeout(120.0, connect=10.0)


def build_headers() -> dict[str, str]:
    """必須ヘッダー3種を返す"""
    return {
        "x-api-key": os.environ["ANTHROPIC_API_KEY"],
        "anthropic-version": API_VERSION,
        "content-type": "application/json",
    }


def extract_text(data: dict) -> str:
    """content 配列から type == "text" のブロックだけを連結して返す"""
    parts = [block["text"] for block in data.get("content", []) if block.get("type") == "text"]
    return "".join(parts)
```

最初のブロックは、インポートと定数の定義です。
`json` はレスポンスを整形して表示するために、`sys` は異常時に終了コードを返すために使います。
`TIMEOUT` では、接続の待ち時間と応答全体の待ち時間を分けて指定しています。
`httpx` の既定のタイムアウトは5秒と短く、Claudeが考える時間を待ちきれないことがあるためです。

`build_headers()` は、3.1節で見た3つのヘッダーを返す関数です。
`os.environ["ANTHROPIC_API_KEY"]` は、キーが設定されていないと `KeyError` で止まります。
キーなしで送って401エラーを受け取るより、手元ですぐ気づけるほうが親切です。

`extract_text()` は、`content` 配列から `text` ブロックだけを集めて連結する関数です。
内包表記の中で `block.get("type") == "text"` と判定している点に注目してください。
これが「型で選ぶ」書き方です。
この関数は、第4章で `llm_client.py` に同じ名前で移します。

続いて、ブロックと停止理由を説明する関数を追加します。

```python
# inspect_response.py（続き）
def describe_block(index: int, block: dict) -> str:
    """content の1ブロックを、型に応じた1行の説明にする"""
    block_type = block.get("type")
    if block_type == "text":
        # 長い回答は先頭60文字だけ表示する
        preview = block["text"][:60].replace("\n", " ")
        return f"[{index}] text     : {preview}…（全{len(block['text'])}文字）"
    if block_type == "thinking":
        # 既定では思考の中身は空文字。署名の有無だけ示す
        has_sig = "あり" if block.get("signature") else "なし"
        return f"[{index}] thinking : 中身{len(block.get('thinking', ''))}文字 / 署名{has_sig}"
    if block_type == "tool_use":
        # 第5章で登場する。ツール名と引数を表示する
        return f"[{index}] tool_use : {block.get('name')} {block.get('input')}"
    # 知らない型が来ても落とさずに表示する
    return f"[{index}] {block_type} : （本スクリプトでは未対応の型）"


def describe_stop(data: dict) -> str:
    """stop_reason を人が読める説明に変える"""
    reason = data.get("stop_reason")
    if reason == "end_turn":
        return "end_turn: 自然に回答を終えました"
    if reason == "max_tokens":
        return "max_tokens: 上限で打ち切られました（回答は途中までです）"
    if reason == "stop_sequence":
        return f"stop_sequence: 指定文字列 {data.get('stop_sequence')!r} で止まりました"
    if reason == "tool_use":
        return "tool_use: ツールの呼び出しを求めています"
    if reason == "pause_turn":
        return "pause_turn: 長い処理を一時停止しました"
    if reason == "refusal":
        details = data.get("stop_details") or {}
        return f"refusal: 応答が断られました（category={details.get('category')}）"
    # 知らない値でも止まらないように受け皿を用意する
    return f"{reason}: 想定外の停止理由です"
```

`describe_block()` は、ブロック1つを受け取り、型ごとに異なる説明文を返します。
`if` を `type` の値で分けているので、ブロックの順番には一切依存しません。
最後の `return` は、どの `if` にも当たらなかった場合の受け皿です。
APIに新しいブロックの型が追加されても、スクリプトが例外で止まらないようにしています。

`describe_stop()` は、`stop_reason` の値を日本語の説明に変換します。
`stop_sequence` の場合は、実際に当たった文字列を `!r` 付きで表示しています。
`!r` を付けると、改行などの見えない文字も `'\n'` のように確認できます。
`refusal` の場合は、`stop_details` から `category` を取り出しています。
`data.get("stop_details") or {}` としているのは、値が `null` でも安全に `.get` を呼ぶためです。
JSONの `null` は、Pythonでは `None` として読み込まれます。

最後に、リクエストを送って結果を表示する `main()` を追加します。

```python
# inspect_response.py（続き）
def main() -> None:
    # コマンドライン引数があれば質問として使う
    question = " ".join(sys.argv[1:]) or "Pythonのリストとタプルの違いを3行で教えてください。"
    body = {
        "model": MODEL,
        "max_tokens": 4096,
        "system": "あなたは初心者に優しいPython講師です。日本語で簡潔に答えてください。",
        "messages": [{"role": "user", "content": question}],
    }

    # 1. リクエストを送る
    response = httpx.post(API_URL, headers=build_headers(), json=body, timeout=TIMEOUT)

    # 2. HTTPステータスと request-id は、成功・失敗にかかわらず最初に表示する
    print(f"HTTPステータス : {response.status_code}")
    print(f"request-id     : {response.headers.get('request-id')}")
    if response.status_code != 200:
        print(response.text)
        sys.exit(1)
    data = response.json()

    # 3. 生のJSONを整形して表示する（ensure_ascii=False で日本語をそのまま出す）
    print("\n===== 生のレスポンス =====")
    print(json.dumps(data, ensure_ascii=False, indent=2))

    # 4. 識別情報と停止理由
    print("\n===== 識別情報と停止理由 =====")
    print(f"id    : {data['id']}")
    print(f"model : {data['model']}")
    print(f"停止  : {describe_stop(data)}")

    # 5. content のブロックを型ごとに表示する
    print("\n===== content ブロック =====")
    for index, block in enumerate(data["content"]):
        print(describe_block(index, block))

    # 6. usage（無い項目は0として扱う）
    usage = data["usage"]
    details = usage.get("output_tokens_details") or {}
    print("\n===== usage =====")
    print(f"input_tokens  : {usage.get('input_tokens', 0)}")
    print(f"output_tokens : {usage.get('output_tokens', 0)}（うち思考 {details.get('thinking_tokens', 0)}）")
    print(f"cache_creation: {usage.get('cache_creation_input_tokens', 0)}")
    print(f"cache_read    : {usage.get('cache_read_input_tokens', 0)}")

    # 7. 回答本文は、停止理由を確認したあとで取り出す
    print("\n===== 回答 =====")
    if data["stop_reason"] == "refusal":
        print("（応答が断られたため、回答は表示しません）")
    else:
        print(extract_text(data))


if __name__ == "__main__":
    main()
```

`main()` は、7つの段階で処理を進めます。
1つ目の段階では、`httpx.post()` でリクエストを送っています。
`json=body` と書くと、辞書が自動でJSON文字列に変換されて送られます。

2つ目の段階で、HTTPステータスと `request-id` を真っ先に表示している点が大切です。
成功か失敗かにかかわらず、この2つは調査の起点になります。
ステータスが200以外なら、エラーボディをそのまま表示して終了します。
エラーの読み方は、3.5節で詳しく扱います。

3つ目の段階では、レスポンス全体を `json.dumps()` で整形しています。
`ensure_ascii=False` を付けないと、日本語が `あ` のような記号の列になってしまいます。
`indent=2` は、入れ子の階層を2文字ずつ字下げして読みやすくする指定です。

4つ目から6つ目の段階では、さきほどの4つのグループに沿って情報を表示しています。
`enumerate()` を使うと、ブロックの番号と中身を同時に取り出せます。
`usage` の各項目は `.get(..., 0)` で読み、項目がない場合にも止まらないようにしています。

7つ目の段階で、ようやく回答の本文を表示します。
その前に `stop_reason` が `refusal` でないかを確認しています。
「停止理由を見てから本文を読む」という順序を、コードの形で表しているわけです。

### 実行して結果を読む

ターミナルで、次のコマンドを実行してください。

```bash
# inspect_response.py を既定の質問で実行する
uv run python inspect_response.py
```

次のような出力が表示されます（IDやトークン数、回答の文面は実行のたびに変わります）。

```text
HTTPステータス : 200
request-id     : req_011CVa8rTn5d2kGqXyP4mH7w

===== 生のレスポンス =====
{
  "id": "msg_01Hq3vYkR9mWcN2aTfB8uE4s",
  "type": "message",
  "role": "assistant",
  "model": "claude-opus-5-5",
  "content": [
    {
      "type": "thinking",
      "thinking": "",
      "signature": "EqQBCkgIARABGAIiQL..."
    },
    {
      "type": "text",
      "text": "リストは作成後に要素を追加・変更できますが、タプルはできません。\n..."
    }
  ],
  ...（中略）...
}

===== 識別情報と停止理由 =====
id    : msg_01Hq3vYkR9mWcN2aTfB8uE4s
model : claude-opus-5-5
停止  : end_turn: 自然に回答を終えました

===== content ブロック =====
[0] thinking : 中身0文字 / 署名あり
[1] text     : リストは作成後に要素を追加・変更できますが、タプルはできません。 リス…（全112文字）

===== usage =====
input_tokens  : 58
output_tokens : 187（うち思考 74）
cache_creation: 0
cache_read    : 0

===== 回答 =====
リストは作成後に要素を追加・変更できますが、タプルはできません。
リストは [ ] 、タプルは ( ) で書きます。
変更しないデータはタプルにすると、意図しない書き換えを防げます。
```

出力を上から順に読んでいきましょう。
まずHTTPステータスが200で、通信が成功したことが分かります。
`request-id` は、何か問題があったときに問い合わせに使う値です。

`content` ブロックの欄では、`thinking` ブロックが0番目、`text` ブロックが1番目に並んでいます。
これが、`content[0]` 決め打ちが危ない理由の実例です。
質問が簡単なときは、`thinking` ブロックが含まれず、`text` だけになることもあります。
何度か実行して、ブロックの数が変わることを確かめてみてください。

`usage` の欄では、`output_tokens` のうち74トークンが思考に使われたことが分かります。
`thinking` ブロックの中身は0文字でも、思考のトークンは消費されています。
回答の文字数のわりに出力トークンが多いと感じたら、この内訳を見ると理由が分かります。

コマンドライン引数で質問を変えることもできます。

```bash
# 質問を引数で渡して実行する（長い説明を求めると output_tokens が増える）
uv run python inspect_response.py "HTTPのステータスコードを5つ、例とともに説明してください"
```

質問によって、`output_tokens` や思考トークンの量がどう変わるかを観察してみてください。
複雑な質問ほど、思考に多くのトークンが使われる傾向があります。

> **WARNING**: `KeyError: 'ANTHROPIC_API_KEY'` と表示された場合は、`.env` が読み込めていません。
> スクリプトを `agent-from-scratch/` フォルダーで実行しているかを確認してください。
> また、`.env` のキー名に誤りがないかも確認してください。

### つまずきやすいポイント

`inspect_response.py` を動かすときに、よくあるつまずきを3つ挙げておきます。

1つ目は、`httpx.ReadTimeout` で止まるケースです。
Claudeが長い回答を考えている間に、待ち時間の上限を超えたことを意味します。
`TIMEOUT` の値を確認し、120秒程度を指定しているかを見直してください。
第4章では、長い応答をストリーミングで受け取ることで、この問題を根本から避けます。

2つ目は、日本語が `リスト` のように表示されるケースです。
`json.dumps()` に `ensure_ascii=False` を付け忘れています。
データが壊れているわけではないので、表示方法を直すだけで解決します。

3つ目は、回答の欄が空になるケースです。
`max_tokens` が小さすぎて、思考の途中で打ち切られた可能性があります。
停止理由の欄が `max_tokens` になっていないかを確認してください。
停止理由を先に表示するようにしたのは、まさにこうした状況に気づくためです。

レスポンスの読み方が分かったところで、次はリクエスト側のパラメータを変えて、応答がどう変わるかを実験します。

---

## 3.3 system プロンプトと主要パラメータ

`temperature` が使えないなら、応答の質や長さはどう調整すればよいのでしょうか。
3.1節では、2026-10-21版での制御の手段を表で整理しました。
この節では、そのうち `system`・`max_tokens`・`stop_sequences`・`effort`・モデル選択を実際に試します。
同じ質問でパラメータだけを変え、応答と `usage` の違いを観察するのがねらいです。

### system プロンプトの書き方

system プロンプトとは、会話全体に効く前提条件をClaudeに渡すための項目です。
ユーザーの発言とは別の場所に置くことで、「誰として、どんなルールで答えるか」を固定できます。
たとえば社内ヘルプデスクなら、「あなたは経理部のサポート担当です」と最初に伝えておくイメージです。

本書では、`system` に次の4つの要素を入れることを基本にします。

| 要素 | 内容 | 例 |
|-----|-----|---|
| 役割 | 誰として答えるか | 「あなたは初心者向けのPython講師です」 |
| 制約 | してはいけないこと・守ること | 「推測で答えず、分からないときはそう伝えてください」 |
| 出力形式 | 長さ・書式・言語 | 「日本語で、3行以内の箇条書きで答えてください」 |
| 背景情報 | 前提となる知識・状況 | 「受講者はPython 3.12を使っています」 |

この4要素を意識するだけで、応答のぶれは大きく減ります。
`temperature` で揺れを抑えていたころより、意図を言葉で伝えるほうが確実です。
エージェントを作る第5章以降では、`system` にツールの使い方の方針も書き込みます。

### max_tokensとstop_sequences

`max_tokens` は、出力の「上限」であって「目標の長さ」ではありません。
1000を指定しても、Claudeが1000トークン分を書こうとするわけではありません。
短く答えてほしいなら、長さの指示は `system` に書きます。
`max_tokens` は、想定外に長くなったときの安全装置と考えてください。

上限に達すると `stop_reason` が `max_tokens` になり、回答は途中で切れます。
思考のトークンも上限に含まれるため、小さすぎる値では本文が空になることもあります。
本書では、非ストリーミングでは16000程度を目安にし、短い分類では小さめにします。

`stop_sequences` は、指定した文字列が出た時点で生成を止める項目です。
「4項目目に入ったら止める」のように、出力の区切りで打ち切りたいときに使います。
止まった文字列そのものは、回答の本文には含まれません。

### effortとモデル選択

`output_config.effort` は、Claudeがどれだけ深く考えるかを指定する項目です。
値は `low`・`medium`・`high`・`xhigh`・`max` の5段階で、Opus 5.5 の既定は `medium` です。
`low` にすると、考える量が減り、出力トークンと待ち時間が少なくなります。
`high` 以上にすると、難しい問題でより丁寧に考えるようになります。

モデルの選択も、品質とコストを調整する手段です。

| モデルID | 位置づけ | 入力／出力（$/100万トークン） |
|---------|--------|-------------------------|
| `claude-opus-5-5` | 本書の既定。3つの中でもっとも高性能 | $4 / $20 |
| `claude-sonnet-5-5` | 性能とコストの中間 | $2 / $10 |
| `claude-haiku-5-5` | 高速・低コスト。分類や要約向き | $0.10 / $0.50（10万トークン以下） |

すべてを高性能なモデルで処理する必要はありません。
第8章以降では、難しい判断は Opus 5.5 に、単純な作業は Haiku 5.5 に任せる設計を扱います。

### params_demo.pyを作る

これらのパラメータを1つずつ試せるスクリプトを、次の内容で新規作成します。

```python
# params_demo.py
"""system・max_tokens・stop_sequences・effort・モデルの違いを試す（第3章・新規作成）"""
import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2026-10-21"
MODEL = "claude-opus-5-5"
FAST_MODEL = "claude-haiku-5-5"
TIMEOUT = httpx.Timeout(120.0, connect=10.0)

# 単価表（$/100万トークン）: 入力, 出力
PRICES = {MODEL: (4.0, 20.0), FAST_MODEL: (0.10, 0.50)}

QUESTION = "HTTPのGETとPOSTの違いを説明してください。"


def send(label: str, **overrides) -> None:
    """基本のボディに overrides を上書きして送り、結果の要点を表示する"""
    body = {"model": MODEL, "max_tokens": 4096,
            "messages": [{"role": "user", "content": QUESTION}]}
    body.update(overrides)
    headers = {"x-api-key": os.environ["ANTHROPIC_API_KEY"],
               "anthropic-version": API_VERSION, "content-type": "application/json"}
    data = httpx.post(API_URL, headers=headers, json=body, timeout=TIMEOUT).json()

    # エラーなら種類とメッセージだけ表示して戻る
    if data.get("type") == "error":
        print(f"[{label}] エラー: {data['error']['type']} {data['error']['message']}")
        return

    # 停止理由とトークン数、概算コストを表示する
    usage = data["usage"]
    thinking = (usage.get("output_tokens_details") or {}).get("thinking_tokens", 0)
    in_price, out_price = PRICES[body["model"]]
    cost = (usage["input_tokens"] * in_price + usage["output_tokens"] * out_price) / 1_000_000
    text = "".join(b["text"] for b in data["content"] if b["type"] == "text")
    print(f"=== {label} ===")
    print(f"stop_reason={data['stop_reason']} stop_sequence={data.get('stop_sequence')!r}")
    print(f"input={usage['input_tokens']} output={usage['output_tokens']}"
          f"（思考 {thinking}） 概算 ${cost:.5f}")
    print(text[:300] or "（text ブロックなし）")
    print()
```

`send()` は、すべての実験で共通に使う送信関数です。
`**overrides` で受け取った項目を `body.update()` で上書きするので、実験ごとに違う部分だけを書けば済みます。
エラーのときは、HTTPステータスではなくボディの `type` が `"error"` かどうかで判定しています。
3.2節で見たとおり、成功なら `"message"`、失敗なら `"error"` が入るからです。

概算コストは、`usage` のトークン数に単価を掛けて100万で割って求めています。
回答は `type` が `"text"` のブロックだけを連結し、長い場合は先頭300文字だけを表示します。
本文が空のときに `（text ブロックなし）` と出すのは、`max_tokens` の実験で役立ちます。

続いて、実験を定義する部分です。

```python
# params_demo.py（続き）
def demo_system() -> None:
    # system なし と あり の比較
    send("system なし")
    send("system あり", system="あなたは小学生向けの先生です。たとえ話を使い、3文以内で答えてください。")


def demo_max_tokens() -> None:
    # 上限を極端に小さくして、打ち切りを観察する
    send("max_tokens=40", max_tokens=40, output_config={"effort": "low"})


def demo_stop() -> None:
    # 「4.」が出た時点で止める
    send("stop_sequences", stop_sequences=["\n4."],
         messages=[{"role": "user", "content": "HTTPメソッドを『1. GET』の形式で5つ挙げてください。"}])


def demo_effort() -> None:
    # 同じ質問で考える深さを変える
    for level in ("low", "high"):
        send(f"effort={level}", output_config={"effort": level})


def demo_model() -> None:
    # 同じ質問をモデルを変えて送り、コストを比べる
    send("Opus 5.5", model=MODEL)
    send("Haiku 5.5", model=FAST_MODEL)


DEMOS = {"system": demo_system, "max_tokens": demo_max_tokens,
         "stop": demo_stop, "effort": demo_effort, "model": demo_model}

if __name__ == "__main__":
    # 引数で実験名を選ぶ（省略時はすべて実行）
    names = sys.argv[1:] or list(DEMOS)
    for name in names:
        DEMOS[name]()
```

5つの実験は、それぞれ1つのパラメータだけを変えています。
1度に複数を変えると、どの変更が効いたのか分からなくなるためです。
`DEMOS` 辞書で実験名と関数を対応させ、コマンドライン引数で選べるようにしています。

### 実行結果を読む

まず `stop_sequences` と `max_tokens` の実験を実行してみます。

```bash
# 停止系の2つの実験だけを実行する
uv run python params_demo.py stop max_tokens
```

```text
=== stop_sequences ===
stop_reason=stop_sequence stop_sequence='\n4.'
input=33 output=41（思考 0） 概算 $0.00095
1. GET
2. POST
3. PUT

=== max_tokens=40 ===
stop_reason=max_tokens stop_sequence=None
input=21 output=40（思考 12） 概算 $0.00088
GETはデータを取得するためのメソッドで、URLにパラメータを付けて
```

`stop_sequences` の実験では、3項目で止まり、`stop_sequence` に `'\n4.'` が入っています。
4項目目の書き出しの手前で止まり、止めた文字列自体は本文に含まれていません。
`max_tokens` の実験では、`output` がちょうど40で、文が途中で切れています。
思考に12トークン使われた分、本文に使える量はさらに少なくなっています。

次に、`effort` とモデルの実験を実行します。

```bash
# effort とモデルの比較を実行する
uv run python params_demo.py effort model
```

```text
=== effort=low ===
stop_reason=end_turn stop_sequence=None
input=21 output=212（思考 0） 概算 $0.00432
…
=== effort=high ===
stop_reason=end_turn stop_sequence=None
input=21 output=655（思考 371） 概算 $0.01318
…
=== Opus 5.5 ===
stop_reason=end_turn stop_sequence=None
input=21 output=389（思考 142） 概算 $0.00786
…
=== Haiku 5.5 ===
stop_reason=end_turn stop_sequence=None
input=21 output=248（思考 0） 概算 $0.00013
…
```

`effort=high` では思考のトークンが増え、コストが3倍ほどになっています。
簡単な質問では、`low` でも十分な回答が得られることが分かります。
Haiku 5.5 は、既定の effort の Opus 5.5 と比べて、およそ60分の1のコストで答えています。
数値は実行のたびに変わりますが、傾向は同じになるはずです。

> **POINT**: 質の調整は「`system` で意図を伝える → `effort` で考える量を決める → モデルを選ぶ」の順に検討します。
> `max_tokens` は品質の調整ではなく、暴走を止める安全装置として使います。

> **WARNING**: `max_tokens` を極端に小さくした実験で、本文が `（text ブロックなし）` になることがあります。
> 思考の段階で上限に達したためで、異常ではありません。上限を上げるか `effort` を下げると解消します。

パラメータの効き方が分かったところで、次は会話を続ける仕組みに進みます。

---

## 3.4 会話履歴を自分で管理する

チャット画面のClaudeは、さっき話した内容を覚えて会話を続けてくれます。
では、APIも前回のリクエストを覚えているのでしょうか。
答えは「いいえ」です。Messages APIはステートレス（状態を持たない）な仕組みです。
この節では、その性質を実験で確かめ、履歴を自分で積み直すCLIチャットを作ります。

### APIは前回の会話を覚えていない

ステートレスとは、サーバーがリクエストの間で何も記憶しないことを意味します。
毎回のリクエストは独立していて、前回の内容は一切引き継がれません。
電話にたとえると、毎回「はじめまして」から始まる相手と話すようなものです。
会話を続けたいなら、それまでのやり取りを毎回すべて読み上げてから質問する必要があります。

チャット画面で会話が続いて見えるのは、アプリが裏で履歴を送り直しているからです。
つまり、会話を続ける責任は、APIを呼ぶ側のプログラムにあります。
エージェントでは、ツールの結果も含めた長い履歴を自分で管理します。
この節で作る仕組みが、そのまま第5章のエージェンティックループの土台になります。

[FIG_3_5｜概念図｜可｜ステートレスなAPIと履歴の送り直し｜毎回のリクエストに過去の全履歴を積み直して送る]

### 履歴の積み方: content配列ごと追加する

履歴は、`messages` 配列に `user` と `assistant` のメッセージを交互に追加して作ります。
ここで大切なのが、assistantの応答を追加するときの書き方です。

```python
# chat.py の履歴追加部分（抜粋）
# 良い例: レスポンスの content 配列をそのまま履歴に入れる
messages.append({"role": "assistant", "content": data["content"]})

# 悪い例: テキストだけを取り出して入れる（thinking ブロックなどが失われる）
messages.append({"role": "assistant", "content": extract_text(data)})
```

`content` 配列をそのまま追加すると、`thinking` ブロックも署名ごと履歴に残ります。
思考のブロックは、削除や改変をせずに送り返すことが求められています。
第5章では、この配列に `tool_use` ブロックが入り、それを残さないとツールの結果と対応が取れなくなります。
「応答は加工せず、そのまま積む」と覚えておけば、どちらの場面でも正しく動きます。

### chat.pyを作る

次の内容で `chat.py` を新規作成します。

```python
# chat.py
"""履歴を自分で管理するCLIチャット（第3章・新規作成）"""
import argparse
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2026-10-21"
MODEL = "claude-opus-5-5"
SYSTEM = "あなたは親切なアシスタントです。日本語で簡潔に答えてください。"


def send_messages(client: httpx.Client, messages: list[dict]) -> dict:
    """履歴全体を送り、レスポンスのJSONを返す（エラー時は例外）"""
    headers = {"x-api-key": os.environ["ANTHROPIC_API_KEY"],
               "anthropic-version": API_VERSION, "content-type": "application/json"}
    body = {"model": MODEL, "max_tokens": 4096, "system": SYSTEM, "messages": messages}
    response = client.post(API_URL, headers=headers, json=body)
    response.raise_for_status()  # 200番台以外なら httpx.HTTPStatusError を送出
    return response.json()
```

`send_messages()` は、受け取った履歴全体をそのまま `messages` として送ります。
`httpx.Client` を引数で受け取るのは、同じ接続を使い回して往復を速くするためです。
`raise_for_status()` は、エラーのステータスなら例外を送出するメソッドです。
エラーの詳しい読み方は3.5節で扱うので、ここでは例外として受け止めるだけにします。

続いて、対話のループを書きます。

```python
# chat.py（続き）
def main() -> None:
    parser = argparse.ArgumentParser()
    # 実験用: 履歴を送らないモード
    parser.add_argument("--no-history", action="store_true")
    args = parser.parse_args()

    messages: list[dict] = []  # 会話の履歴（自分で管理する）
    print("チャットを開始します（/reset で履歴を消去、/exit で終了）")

    with httpx.Client(timeout=httpx.Timeout(120.0, connect=10.0)) as client:
        while True:
            user_input = input("あなた> ").strip()
            if user_input == "/exit":
                break
            if user_input == "/reset":
                messages.clear()
                print("（履歴を消去しました）")
                continue
            if not user_input:
                continue

            # 1. user メッセージを履歴に追加する
            messages.append({"role": "user", "content": user_input})
            try:
                data = send_messages(client, messages)
            except httpx.HTTPError as exc:
                # 失敗したら user メッセージを取り消し、交互の並びを保つ
                messages.pop()
                print(f"（送信に失敗しました: {exc}）")
                continue

            # 2. 断られた応答は履歴に残さない
            if data["stop_reason"] == "refusal":
                messages.pop()
                print("Claude> （この質問には回答できませんでした）")
                continue

            # 3. assistant の content を配列ごと履歴に追加する
            messages.append({"role": "assistant", "content": data["content"]})
            text = "".join(b["text"] for b in data["content"] if b["type"] == "text")
            print(f"Claude> {text}")
            if data["stop_reason"] == "max_tokens":
                print("（回答が上限で途中まで切れています）")

            # 4. 入力トークン数で、履歴が増える様子を観察する
            usage = data["usage"]
            print(f"  [履歴 {len(messages)}件 / input={usage['input_tokens']} "
                  f"output={usage['output_tokens']}]")

            # 実験モードでは毎回履歴を捨てる
            if args.no_history:
                messages.clear()


if __name__ == "__main__":
    main()
```

ループの中は、4つの段階に分かれています。
1つ目の段階で、入力を `user` メッセージとして履歴に追加し、履歴全体を送ります。
送信に失敗したら `messages.pop()` で追加を取り消します。
取り消さないと、次の入力で `user` が2つ連続し、2つの質問が1つにつながってしまうからです。

2つ目の段階では、`stop_reason` が `refusal` かどうかを先に確かめています。
断られた応答は回答として扱わず、質問ごと履歴から取り除きます。

3つ目の段階で、応答の `content` を配列のまま履歴に追加しています。
表示用のテキストは、それとは別に `type` で選んで作っています。
「履歴に積むもの」と「画面に出すもの」を分けて考えるのがポイントです。

4つ目の段階では、履歴の件数と `input_tokens` を毎回表示しています。
`--no-history` を付けたときは、1往復ごとに履歴を空にします。

### 実験1: 履歴を送らないとどうなるか

まず、履歴を送らないモードで起動してみましょう。

```bash
# 履歴を送らない実験モードで起動する
uv run python chat.py --no-history
```

```text
あなた> 私の名前は佐藤です。覚えてください。
Claude> 佐藤さん、よろしくお願いします。
  [履歴 2件 / input=41 output=58]
あなた> 私の名前は何ですか？
Claude> 申し訳ありませんが、お名前はまだ伺っていません。
  [履歴 2件 / input=33 output=49]
```

1回目に名乗ったのに、2回目には名前を知らないと答えています。
2回目のリクエストには、1回目のやり取りが含まれていないからです。
APIが前回の会話を覚えていないことが、これではっきりしました。

### 実験2: 履歴を送ると会話が続く

次に、オプションを付けずに起動します。

```bash
# 通常モード（履歴を送る）で起動する
uv run python chat.py
```

```text
あなた> 私の名前は佐藤です。覚えてください。
Claude> 佐藤さん、よろしくお願いします。
  [履歴 2件 / input=41 output=58]
あなた> 私の名前は何ですか？
Claude> 佐藤さんです。
  [履歴 4件 / input=95 output=37]
あなた> Pythonのおすすめの学習法を教えて。
Claude> 佐藤さん、まずは小さなスクリプトを毎日書くことをおすすめします。…
  [履歴 6件 / input=148 output=212]
```

今度は名前を正しく答えています。
同時に、`input` の値が41、95、148と増えている点に注目してください。
これは、毎回それまでの履歴全体を入力として送り直しているためです。

[FIG_3_6｜比較｜可｜会話のターンと入力トークンの増加｜ターンごとに履歴が積み上がりinput_tokensが増える]

入力トークンが増えれば、料金も待ち時間も増えます。
長い会話や、ツールの結果を大量に積むエージェントでは、この増え方が無視できなくなります。
第7章では、履歴の要約やプロンプトキャッシュで、この問題に対処します。

> **POINT**: 会話の「記憶」は、Claudeの中ではなく、あなたのプログラムの `messages` 配列にあります。
> 何を覚えさせ、何を忘れさせるかは、履歴の管理方法で決まります。

> **WARNING**: `/reset` で履歴を消すと、それまでの文脈はすべて失われます。
> 逆に、消さずに長く使い続けると、入力トークンが増え続けて料金がかさむ点にも注意してください。

会話を続けられるようになりました。最後に、うまくいかなかったときに返ってくるエラーを読み解けるようにしましょう。

---

## 3.5 エラーとHTTPステータス

ここまでの実験は、うまく動く前提で進めてきました。
しかし実際の開発では、キーの設定ミスやパラメータの誤りで、リクエストが失敗することがよくあります。
エラーが出たとき、「何が悪いのか」をすぐ判断できるでしょうか。
この節では、エラーレスポンスの読み方を学び、わざとエラーを起こして観察します。

### エラーレスポンスの構造

リクエストが失敗すると、APIは200以外のHTTPステータスと、次の形のJSONを返します。

```jsonc
// エラーレスポンスの例（存在しないモデルを指定したとき）
{
  "type": "error",                     // 成功時の "message" ではなく "error"
  "error": {
    "type": "not_found_error",         // エラーの種類（プログラムで判定に使う）
    "message": "model: claude-opus-9-9" // 人間向けの説明（文言は変わり得る）
  },
  "request_id": "req_011CSHoEeqs5C35K2UUqR7Fy"  // 問い合わせ用のID
}
```

トップレベルの `type` が `"error"` になり、`error` オブジェクトに詳細が入ります。
`error.type` はエラーの種類で、プログラムの分岐にはこちらを使います。
`error.message` は人間が読むための説明で、原因を探す手がかりになります。
ただし文言は変わり得るので、文字列の一致で処理を分けてはいけません。
`request_id` は、3.2節で見た `request-id` ヘッダーと同じ値です。

### HTTPステータスとエラーの種類

本書で押さえておくべきステータスとエラーの種類は、次のとおりです。

| ステータス | `error.type` | 主な原因 | リトライ |
|----------|-------------|--------|--------|
| 400 | `invalid_request_error` | ボディの形式・内容の誤り | しない（直して送り直す） |
| 401 | `authentication_error` | APIキーが無効・未設定 | しない |
| 402 | `billing_error` | 支払い情報の問題 | しない（Consoleで支払い情報を確認） |
| 403 | `permission_error` | キーに権限がない | しない |
| 404 | `not_found_error` | URLやモデルIDの誤り | しない |
| 413 | `request_too_large` | リクエストが大きすぎる | しない |
| 429 | `rate_limit_error` | レート制限に達した | する（待ってから） |
| 500 | `api_error` | Anthropic側の内部エラー | する |
| 504 | `timeout_error` | 処理中のタイムアウト | する（長い処理はストリーミングに） |
| 529 | `overloaded_error` | APIが一時的に混雑している | する |

大まかには、400番台は「送った側の問題」、500番台は「受け取った側の問題」です。
400番台は、同じリクエストを何度送っても同じ結果になるので、リトライしません。
ただし429は例外で、多くは時間をおけば成功する一時的な制限です。
ティアで決まる月の支出上限（spend cap）に達した429だけは、翌月まで回復しません。見分け方は第4章で扱います。
500番台と429は、少し待って送り直せば成功する可能性があります。
この「リトライすべきか」の判断は、第4章で作る自動リトライの中核になります。

[FIG_3_7｜フロー｜可｜エラー対応の判断フロー｜ステータスからリトライ可否と確認箇所を判断する]

### よくある400エラー

400エラーは、もっとも頻繁に出会うエラーです。
本書の環境で起こりやすい原因を挙げておきます。

- `temperature`・`top_p`・`top_k` を送った（2026-10-21版では使えない）
- `messages` の最後を `assistant` で終えた（prefill は使えない）
- `max_tokens` を書き忘れた（必須項目の欠落）
- `tool_choice` で特定のツールを強制した（Opus 5.5・Sonnet 5.5 では使えない）
- Consoleで自分で設定した利用上限（spend limit）に達した。`message` は `You have reached your specified ... API usage limits` で始まる

いずれも、`error.message` に問題のある項目名や原因が書かれています。
prefill の場合は `does not support assistant message prefill` という説明です。
エラーが出たら、まずメッセージに出てくる項目名をボディの中で探してください。

### error_lab.pyでわざとエラーを起こす

エラーは、実際に見ておくと本番で慌てずに済みます。
次の内容で `error_lab.py` を新規作成し、わざと失敗するリクエストを送ってみましょう。

```python
# error_lab.py
"""わざとエラーを起こして、エラーレスポンスを観察する（第3章・新規作成）"""
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2026-10-21"
MODEL = "claude-opus-5-5"

# 正しいヘッダーとボディ（各実験はここから1か所だけ壊す）
GOOD_HEADERS = {"x-api-key": os.environ["ANTHROPIC_API_KEY"],
                "anthropic-version": API_VERSION, "content-type": "application/json"}
GOOD_BODY = {"model": MODEL, "max_tokens": 1024,
             "messages": [{"role": "user", "content": "こんにちは"}]}


def is_retryable(status: int) -> bool:
    """リトライすべきステータスかを判定する（408・409・429・5xx）"""
    return status in (408, 409, 429) or status >= 500


def run(label: str, headers: dict, body: dict, url: str = API_URL) -> None:
    """1つの実験を実行し、ステータスとエラーの中身を表示する"""
    response = httpx.post(url, headers=headers, json=body, timeout=60.0)
    print(f"=== {label} ===")
    print(f"status     : {response.status_code}")
    if response.status_code == 200:
        print("成功しました（エラーは起きませんでした）\n")
        return
    try:
        error = response.json()["error"]
        print(f"error.type : {error['type']}")
        print(f"message    : {error['message']}")
    except (ValueError, KeyError):
        # JSONでない応答（途中の機器が返したエラーなど）にも備える
        print(f"本文       : {response.text[:200]}")
    print(f"request-id : {response.headers.get('request-id')}")
    print(f"リトライ   : {'する' if is_retryable(response.status_code) else 'しない'}\n")
```

`GOOD_HEADERS` と `GOOD_BODY` は、正しく動くリクエストの見本です。
各実験は、ここから1か所だけを壊して送ります。
原因を1つに絞ることで、どの誤りがどのエラーになるかを対応づけられます。

`is_retryable()` は、ステータスからリトライの要否を判定する関数です。
表にはない409（競合）も、一時的な失敗としてリトライ対象に含めています。
408（タイムアウト）も同じく対象です。
APIの一覧にはないものの、プロキシなどが返すことがあるためです。
`run()` の `try` ブロックでは、ボディがJSONでない場合にも止まらないようにしています。
ネットワークの途中にある機器が、HTMLのエラーページを返すこともあるからです。

続いて、実験を並べる部分です。

```python
# error_lab.py（続き）
if __name__ == "__main__":
    # 1. 401: 不正なAPIキー
    run("不正なAPIキー", {**GOOD_HEADERS, "x-api-key": "sk-ant-invalid"}, GOOD_BODY)

    # 2. 400: 2026-10-21版で廃止された temperature を送る
    run("temperature を送る", GOOD_HEADERS, {**GOOD_BODY, "temperature": 0.2})

    # 3. 400: 最後を assistant で終える（prefill）
    prefill = [{"role": "user", "content": "JSONで答えて"},
               {"role": "assistant", "content": "{"}]
    run("assistant prefill", GOOD_HEADERS, {**GOOD_BODY, "messages": prefill})

    # 4. 400: 必須の max_tokens を省く
    no_max = {k: v for k, v in GOOD_BODY.items() if k != "max_tokens"}
    run("max_tokens なし", GOOD_HEADERS, no_max)

    # 5. 404: 存在しないモデルID
    run("存在しないモデル", GOOD_HEADERS, {**GOOD_BODY, "model": "claude-opus-9-9"})

    # 6. 404: エンドポイントのURLの誤り（messages → message）
    run("URLの誤り", GOOD_HEADERS, GOOD_BODY, url="https://api.anthropic.com/v1/message")
```

`{**GOOD_HEADERS, "x-api-key": ...}` は、辞書をコピーして1項目だけ上書きする書き方です。
元の `GOOD_HEADERS` は変更されないので、次の実験に影響しません。
4つ目の実験では、辞書内包表記で `max_tokens` だけを除いた新しい辞書を作っています。

### 実行結果を読む

```bash
# 6つのエラー実験をまとめて実行する
uv run python error_lab.py
```

次のような出力になります（`message` の文言と `request-id` は環境によって異なります）。

```text
=== 不正なAPIキー ===
status     : 401
error.type : authentication_error
message    : （APIキーが無効である旨の英文）
request-id : req_011CVb2xQd7…
リトライ   : しない

=== temperature を送る ===
status     : 400
error.type : invalid_request_error
message    : （temperature を受け付けない旨の英文）
…
=== 存在しないモデル ===
status     : 404
error.type : not_found_error
message    : model: claude-opus-9-9
…
```

どの実験でも、ステータスと `error.type` が表の対応どおりになっていることを確かめてください。
400の実験では、`message` に `temperature` や `max_tokens` といった項目名が含まれます。
404は、モデルIDの誤りでもURLの誤りでも返ります。
`message` を見れば、どちらが原因かを区別できます。

401の実験では、ボディが正しくても、中身を読まれる前に認証で弾かれています。
3.1節の封筒のたとえでいえば、差出人が不明なので開封されなかった状態です。
エラーが出たら「ヘッダー → URL → ボディ」の順に疑うと、効率よく原因にたどり着けます。

> **POINT**: エラーの判定には `error.type` とステータスを使い、`message` は原因調査に使います。
> そして `request-id` は、どんなエラーでも必ずログに残してください。

> **NOTE**: 413・429・500・529は、本章では実験しません。
> 意図的に起こすのが難しかったり、料金がかかったりするためです。
> 429と529は第4章で、リトライの仕組みとあわせて改めて扱います。

---

## 本章のまとめ

本章で学んだことを整理します：

- リクエストは「ヘッダー3種」と「ボディ」でできています。ヘッダーは `x-api-key`・`anthropic-version`・`content-type` の3種です。ボディは `model`・`max_tokens`・`messages`＋`system` です。2026-10-21版では `temperature` などが400エラーになります。本書で使うモデルでは、prefillも400エラーになります。出力は `system`・構造化出力・`effort`・`stop_sequences`・`max_tokens` で制御します。
- レスポンスは識別情報・`content`・停止理由・`usage` の4グループで読みます。`content` は `type` で判定し、本文を読む前に必ず `stop_reason` を確認します。
- APIはステートレスなので、会話履歴は自分で `messages` に積み直します。応答は `content` 配列ごと追加します。エラーは `error.type` とステータスで判定して、リトライの要否を見分けます。

本章では、4つのスクリプトのすべてで、ヘッダーの組み立てや送信の処理を毎回書いてきました。
タイムアウトやエラー処理も、スクリプトごとにばらばらです。
次章では **自作APIクライアントを作る** を扱います。
毎回同じコードを書かずに済むよう、そして失敗に強くなるよう、処理をまとめましょう。
まとめる先は、自分だけのAPIクライアント `llm_client.py` です。
