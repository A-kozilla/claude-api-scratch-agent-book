# 第7章: コンテキストとメモリを管理する
# EN-TITLE: CONTEXT AND MEMORY
# TAGS: count_tokens, compaction, Prompt caching, 長期メモリ, effort

> [!DIALOGUE]
> **生徒**: 第6章のエージェント、ファイルを何本も読ませたら途中で急に遅くなって、料金も跳ね上がりました。
> **先生**: 履歴が毎回まるごと送られているからだね。今回はその「履歴の重さ」を測って、減らして、安くする方法を自作しよう。
> **生徒**: 測って、減らして、安くする……。さらに会話をまたいで覚えさせることもできますか？
> **先生**: できるよ。最後に長期メモリと、考える深さの調整まで扱うね。

## この章で学ぶこと

本章では以下を学びます：

- `count_tokens` APIで送信前にトークン数を測り、system・tools・messagesそれぞれの重さを把握できるようになる
- tool_useとtool_resultのペアを壊さずに履歴を圧縮する仕組み（compaction）を自作し、エージェントに組み込めるようになる
- Prompt cachingで繰り返し送る部分をキャッシュし、`cache_read_input_tokens`で効果を測定できるようになる
- 会話をまたいで事実を残す長期メモリツールを作り、adaptive thinkingとeffortで「考える深さ」を調整できるようになる

前章では、ツールレジストリ・並列ツール呼び出し・安全なファイル操作・構造化出力を実装し、エージェントを実務レベルに近づけました。
ツールが増え、作業が長くなるほど、エージェントの履歴はどんどん膨らんでいきます。
本章では、その膨らんだ履歴を「測る・減らす・安く送る・外に逃がす」という4つの方向から管理する方法を扱います。
最後に、Claudeの思考の深さを調整するeffortも取り上げ、品質とコストの釣り合いを取る道具をそろえます。

---

## 7.1 トークンとコンテキストの予算

第3章で、Messages API（メッセージズ エーピーアイ）は会話の状態を一切覚えないステートレスなAPIだと学びました。
そのため私たちは、毎回のリクエストに過去の会話履歴をすべて積み直して送っています。
第5章と第6章で作ったエージェントループでも、ツールを1回呼ぶたびに、assistantの応答とtool_resultが履歴に追加されました。
では、その履歴はいま何トークンあるのでしょうか。
そして、どこまで増えたら「危ない」と判断すべきなのでしょうか。
本節では、この2つの疑問に答えるための計測の道具と、予算の考え方を整えます。

### コンテキストウィンドウは「1回のリクエストの容量」

最初に用語を整理しておきます。
**コンテキストウィンドウ（Context Window）** とは、モデルが1回のリクエストで読み書きできるトークンの総量の上限です。
本書で使う`claude-opus-5-5`のコンテキストは100万トークン（1M）、最大出力は128Kトークンです。
ここで押さえておきたいのは、この上限が「会話全体」ではなく「1回のリクエスト」に対するものだという点です。

たとえば、10ターン続いた会話を考えてみましょう。
10回目のリクエストには、1〜9ターン目のやり取りと10ターン目の入力がすべて含まれます。
つまり、ターンを重ねるごとに1回あたりの入力トークンは増え続け、やがて上限に近づきます。
エージェントループでは1ターンの中で何度もAPIを呼ぶため、この増え方はさらに速くなります。

トークン（Token）は、モデルが文章を処理するときの最小単位です。
英語ではおおむね単語の一部、日本語では1〜2文字程度が1トークンになることが多いです。
ただし、この換算はモデルのトークナイザー（Tokenizer、文章をトークンに分割する仕組み）によって変わります。
公式ドキュメントでも、新しい世代のモデルは同じ文章でも以前より多めにトークン化されると説明されています。
そのため、「文字数÷2」のような目分量ではなく、使うモデルで実際に数えることが大切です。

[FIG_7_1｜概念図｜可｜1回のリクエストに積まれるトークン｜tools・system・messagesが積み上がり上限に近づく様子]

### 入力トークンの内訳は3つ

1回のリクエストで入力トークンとして数えられるのは、大きく分けて3つの部分です。

| 部分 | 中身 | 増え方 |
|-----|-----|------|
| tools | ツール定義（name・description・input_schema） | ツールを増やしたときだけ増える。毎回同じ量 |
| system | systemプロンプト | 基本は一定。メモリを差し込むと増える（7.4節） |
| messages | userとassistantのやり取り、tool_use・tool_result | ターンごとに増え続ける |

toolsとsystemは、会話が進んでも基本的に量が変わりません。
一方でmessagesは、ターンを重ねるたびに単調に増えていきます。
特にtool_resultは要注意です。
ファイルの中身やWebページの本文をそのまま返すツールは、1回の結果だけで数千〜数万トークンを持ち込むことがあります。

もう1つ見落としやすいのが、toolsの重さです。
第6章で学んだように、良いツールのdescriptionは「何をする・いつ使う・引数の意味」を具体的に書きます。
その結果、ツールを10個そろえると、定義だけで数千トークンになることも珍しくありません。
そしてこの数千トークンは、APIを呼ぶたびに毎回送られます。
この「毎回同じものを送っている」という性質は、7.3節のPrompt cachingで大きな意味を持ちます。

### count_tokens APIのリクエストとレスポンス

トークン数を正確に知るには、Anthropicが提供している **トークンカウントAPI** を使います。
エンドポイントは`POST /v1/messages/count_tokens`です。
リクエストボディは、Messages APIとほぼ同じ形で`model`・`messages`・`system`・`tools`を渡します。
レスポンスは`{"input_tokens": N}`という、とても単純なJSONです。

まずは第2章と同じように、curl（カール）で直接呼んでみましょう。
ヘッダーも第2章と同じ3つで、URLの末尾だけが違います。

```bash
# count_tokens を curl で呼ぶ（macOS / Linux / Git Bash）
curl https://api.anthropic.com/v1/messages/count_tokens \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2026-10-21" \
  -H "content-type: application/json" \
  -d '{
    "model": "claude-opus-5-5",
    "system": "あなたは丁寧な日本語で答えるアシスタントです。",
    "messages": [{"role": "user", "content": "こんにちは"}]
  }'
```

実行すると、次のようなレスポンスが返ってきます。
数値は一例で、モデルや文章によって変わります。

```json
{"input_tokens": 31}
```

ここで、いくつか大切な性質を押さえておきましょう。
1つ目は、`max_tokens`を渡す必要がないことです。
count_tokensは応答を生成しないので、出力の上限を指定する意味がないからです。
2つ目は、このAPIが **無料で使える** ことです。
公式ドキュメントでは、トークンカウントは無料で、メッセージ生成とは別枠のレート制限（1分あたりのリクエスト数）が設けられていると説明されています。
3つ目は、返ってくる値が **見積もり** であることです。
実際にメッセージを生成したときの`usage.input_tokens`とは、わずかにずれる場合があります。

> **NOTE**: count_tokensは、自作ツール（クライアントツール）を含むリクエストには使えますが、Anthropic側で実行されるサーバーツール（web_searchなど）を含むリクエストではエラーになります。本書のエージェントは自作ツールが中心なので、この制約に当たることはほとんどありません。

### llm_client.pyにcount_tokens()を追加する

curlで動きを確かめたら、第4章で作った`llm_client.py`に関数として追加します。
本節のコードは **llm_client.pyの更新** で、既存の関数はそのまま残し、末尾に1つ関数を足します。
リトライの仕組みは第4章の`_send_with_retry()`をそのまま流用します。

```python
# llm_client.py（第7章で追加: count_tokens）

def count_tokens(
    messages: list[dict],
    *,
    system: str | list[dict] | None = None,
    tools: list[dict] | None = None,
    model: str = MODEL,
    max_retries: int = 4,
) -> int:
    """送信前に入力トークン数を数える（/v1/messages/count_tokens）。"""
    # リクエストボディは Messages API とほぼ同じ形。max_tokens は不要
    body: dict = {"model": model, "messages": messages}
    # system と tools は指定されたときだけ入れる（空の配列は送らない）
    if system is not None:
        body["system"] = system
    if tools:
        body["tools"] = tools
    # 第4章のリトライ付き送信をそのまま使う（429 や 5xx は自動で再試行）
    data = _send_with_retry(API_BASE + "/messages/count_tokens", body, max_retries=max_retries)
    # レスポンスは {"input_tokens": N} という単純な形
    return int(data["input_tokens"])
```

コードを上から読んでいきましょう。
引数は`call_messages()`とそろえて、`messages`を位置引数、それ以外をキーワード専用引数にしています。
こうしておくと、同じ`messages`・`system`・`tools`の組を、数える関数と送る関数の両方にそのまま渡せます。

`body`の組み立てでは、`system`と`tools`を「指定されたときだけ」入れています。
`tools`に空のリストを渡すと、APIの側で検証エラーになることがあるためです。
また、`max_tokens`を入れていない点にも注目してください。
先ほど説明したとおり、count_tokensは生成を行わないので出力上限は不要です。

送信部分では、第4章の`_send_with_retry()`を呼んでいます。
URLは`API_BASE + "/messages/count_tokens"`で、`API_BASE`は第4章で定義した`https://api.anthropic.com/v1`です。
count_tokensにも別枠のレート制限があるので、429が返ってくることはあり得ます。
そのため、メッセージ送信と同じリトライ規則で守っておくのが安全です。

> **NOTE**: 本書の第4章では`_send_with_retry(url, body, max_retries=...)`がレスポンスJSONを`dict`で返す形で実装しました。手元の実装で引数の並びや戻り値（`httpx.Response`を返すなど）が異なる場合は、それに合わせて読み替えてください。大事なのは「count_tokensもリトライ付きの同じ送信経路を通す」という点です。

### context.pyを作り、内訳を測る

次に、本章の主役となる`context.py`を **新規作成** します。
このファイルには、トークンの計測・履歴の切り詰め・要約・自動圧縮といった「コンテキスト管理の部品」を集めていきます。
まずは計測の部分だけを書きます。

```python
# context.py（第7章で新規作成: 計測部分）
import json
import logging

from llm_client import MODEL, APIError, count_tokens

logger = logging.getLogger("context")

# モデルのコンテキスト上限（claude-opus-5-5 は 1M トークン）
CONTEXT_WINDOW = 1_000_000
# 自動圧縮を始めるしきい値。上限よりずっと手前に置く（理由は本文で説明）
DEFAULT_THRESHOLD = 150_000


def estimate_tokens(
    messages: list[dict],
    *,
    system: str | list[dict] | None = None,
    tools: list[dict] | None = None,
    model: str = MODEL,
) -> int:
    """count_tokens で数える。API が使えないときは粗い近似値に切り替える。"""
    try:
        return count_tokens(messages, system=system, tools=tools, model=model)
    except APIError as e:
        # 計測の失敗でエージェント全体を止めない。警告を残して近似に切り替える
        logger.warning("count_tokens に失敗したため近似値を使います: %s", e)
        raw = json.dumps({"system": system, "tools": tools, "messages": messages}, ensure_ascii=False)
        # 文字数をそのままトークン数とみなす（日本語中心なら多めに見積もる側に倒れる）
        return len(raw)


def token_breakdown(
    messages: list[dict],
    *,
    system: str | list[dict] | None = None,
    tools: list[dict] | None = None,
    model: str = MODEL,
) -> dict[str, int]:
    """tools・system・messages がそれぞれ何トークンを占めているかを差分で求める。"""
    # count_tokens は messages が空だと数えられないため、最小のメッセージを基準にする
    probe = [{"role": "user", "content": "."}]
    base = count_tokens(probe, model=model)
    with_tools = count_tokens(probe, tools=tools, model=model) if tools else base
    with_system = count_tokens(probe, system=system, model=model) if system else base
    total = count_tokens(messages, system=system, tools=tools, model=model)
    # 差分から各部分のおおよその量を出す（オーバーヘッドの分だけ誤差がある）
    tools_tokens = with_tools - base
    system_tokens = with_system - base
    return {
        "tools": tools_tokens,
        "system": system_tokens,
        "messages": total - tools_tokens - system_tokens,
        "total": total,
    }
```

このファイルの冒頭では、2つの定数を定義しています。
`CONTEXT_WINDOW`はモデルの上限で、`DEFAULT_THRESHOLD`は自動圧縮を始める目安です。
しきい値を上限の15%に置いている理由は、このあと「予算の考え方」で詳しく説明します。

`estimate_tokens()`は、`count_tokens()`を呼ぶだけの薄い関数に見えるかもしれません。
ポイントは`except APIError`の部分です。
計測は「圧縮するかどうか」を決めるための補助的な処理なので、それが失敗しただけでエージェント全体を止めたくはありません。
そこで、失敗したときは履歴をJSON文字列にして、その文字数を近似値として返しています。
日本語中心の履歴であれば、1文字を1トークンと数えるのは多めに見積もる側に倒れるので、安全側の近似になります。

`token_breakdown()`は、内訳を知るための調査用の関数です。
count_tokensは合計しか返してくれないので、「最小のメッセージだけ」「それにtoolsを足したもの」「それにsystemを足したもの」を数え、その差分で各部分の量を求めています。
`probe`として`"."`という1文字だけのメッセージを使っているのは、count_tokensが空の`messages`を受け付けないためです。
差分による計算なので、内部で付与される固定のオーバーヘッドの分だけ誤差は出ますが、「どこが重いか」をつかむには十分な精度です。

### 実際に内訳を測ってみる

それでは、第6章までに作ったツールを使って内訳を測ってみましょう。
`context.py`の末尾に、動作確認用のブロックを追加します。

```python
# context.py（動作確認用。ファイル末尾に追加）
if __name__ == "__main__":
    from tools.weather import GET_WEATHER_TOOL

    # 第5章の天気ツールを例に、長めの履歴を人工的に作って測る
    system = "あなたは旅行の相談に乗るアシスタントです。必要なら天気ツールを使います。"
    messages = [{"role": "user", "content": "東京と大阪の週末の天気を比べて、どちらに行くべきか教えて。"}]
    # tool_result に長い文字列が入った状態を再現する
    messages += [
        {"role": "assistant", "content": [
            {"type": "tool_use", "id": "toolu_demo1", "name": "get_weather", "input": {"city": "Tokyo"}},
        ]},
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "toolu_demo1", "content": "晴れ、最高気温22度。" * 300},
        ]},
    ]
    breakdown = token_breakdown(messages, system=system, tools=[GET_WEATHER_TOOL])
    for part, tokens in breakdown.items():
        print(f"{part:>8}: {tokens:>7,} tokens")
```

ここでは、天気ツールの結果に同じ文章を300回つなげた長い文字列を入れ、「巨大なtool_result」を人工的に再現しています。
`f"{part:>8}"`は8文字幅の右寄せ、`{tokens:>7,}`は7文字幅で3桁ごとにカンマを入れる書式です。
実行コマンドと出力例は次のとおりです。

```bash
# context.py の動作確認を実行する
uv run python context.py
```

```text
   tools:     412 tokens
  system:      38 tokens
messages:   4,627 tokens
   total:   5,077 tokens
```

数値は一例ですが、読み方は変わりません。
messagesが全体の9割以上を占めていることがわかります。
その大半は、たった1回のtool_resultです。
このように、エージェントのコンテキストを圧迫する犯人は、多くの場合「ツールの結果」なのです。
この観察が、次の7.2節で「古いツール結果から先に縮める」という設計につながります。

> **POINT**: 内訳を測ると、改善の打ち手が見えてきます。toolsが重ければdescriptionの整理かキャッシュ（7.3節）、systemが重ければキャッシュ、messagesが重ければ圧縮（7.2節）が効きます。闇雲に削る前に、まず測りましょう。

### usageからも実際の量は読める

count_tokensは「送る前に」数える道具でした。
一方で、「送った後に」実際の量を知る方法もあります。
それが、第3章と第4章で読んだレスポンスの`usage`です。

`usage.input_tokens`は、そのリクエストで実際に処理された入力トークン数です。
ただし、7.3節でPrompt cachingを導入すると、この値の意味が少し変わります。
キャッシュを使った場合、入力の合計は`input_tokens`・`cache_creation_input_tokens`・`cache_read_input_tokens`の3つを足した値になるからです。
この点はキャッシュの節で改めて確認します。

送る前に数えるcount_tokensと、送った後に読むusage。
この2つは役割が違います。
圧縮の判断のように「送る前に決めたいこと」にはcount_tokensを使い、コストの集計のように「実績で十分なこと」にはusageを使います。

### 予算の考え方：なぜ上限まで使わないのか

さて、ここからが本節の核心です。
コンテキストが1Mトークンもあるなら、上限ぎりぎりまで使えばよいのではないか、と思うかもしれません。
本書では、そうはしません。
しきい値を15万トークン程度に置き、それを超えたら圧縮します。
理由は大きく4つあります。

1つ目は **コスト** です。
入力トークンは、送るたびに課金されます。
`claude-opus-5-5`の入力単価は100万トークンあたり4ドルです。
もし毎回80万トークンの履歴を送るとすると、1回の呼び出しだけで入力に約3.2ドルかかります。
エージェントは1タスクで10回、20回とAPIを呼ぶので、これは現実的な金額ではありません。

2つ目は **レイテンシ（Latency、応答までの待ち時間）** です。
入力が長いほど、モデルが読み込むのに時間がかかり、最初のトークンが返ってくるまでの待ち時間も伸びます。
対話的に使うエージェントでは、この遅さは使い勝手に直結します。

3つ目は **品質** です。
入力に無関係な情報が大量に含まれていると、重要な指示や最新の状況が埋もれやすくなります。
たとえば、50回前に読んだファイルの中身と、いま読んだファイルの中身が並んでいると、モデルが古い情報を参照してしまう恐れがあります。
必要な情報だけを適切な量で渡すほうが、判断は安定します。

4つ目は **余白** です。
入力が上限に近いと、出力に使える余裕がなくなります。
また、1回のtool_resultが想定外に大きかった場合、次のリクエストで一気に上限を超え、400エラーや413エラーで止まってしまいます。
しきい値を手前に置いておけば、こうした突発的な増加を吸収できます。

[FIG_7_2｜比較｜可｜コンテキスト予算の配分｜上限1Mに対しtools・system・履歴・出力余白・安全マージンを割り当てる帯グラフ]

### 予算表を作っておく

実務では、エージェントごとに「予算表」を作っておくと判断がぶれません。
筆者が目安にしている配分を、表にまとめておきます。

| 項目 | 目安 | 考え方 |
|-----|-----|------|
| tools | 〜1万トークン | ツール数が多いなら絞るか、エージェントを分ける（第8章） |
| system | 〜1万トークン | メモリの差し込みも含めて上限を決める |
| messages | 〜13万トークン | ここを超えたら圧縮する |
| 出力 | `max_tokens`分 | 非ストリーミングなら16000程度 |
| 安全マージン | 残りすべて | 巨大なtool_resultの突発的な増加に備える |

この表は絶対的な正解ではありません。
長い文書を丸ごと読ませる用途なら、messagesにもっと多く割り当ててもよいでしょう。
逆に、短い問い合わせを大量にさばく用途なら、もっと小さな予算で十分です。
大切なのは、「どこまで使うか」を自分で決め、それを数値としてコードに書いておくことです。

> **WARNING**: しきい値をコンテキスト上限の近くに置くと、1回の大きなtool_resultで上限を超えてしまいます。上限を超えたリクエストはAPIでエラーになり、エージェントはその場で止まります。圧縮のしきい値は、必ず上限よりかなり手前に置いてください。

### 計測のコストとタイミング

最後に、計測そのもののコストにも触れておきます。
count_tokensは無料ですが、HTTPリクエストを1回余分に送るので、数百ミリ秒程度の待ち時間は発生します。
エージェントループの毎ターンで呼ぶと、その分だけ全体が遅くなります。

これが気になる場合は、前回のレスポンスの`usage`を使って見積もる方法もあります。
前回の入力トークン数（キャッシュ分を含む合計）に前回の出力トークン数を足し、さらに今回追加したtool_resultの分を加えれば、今回のおおよその量になります。
本書では、わかりやすさと正確さを優先して、毎ターンcount_tokensで数える方式を採用します。
速度が重要になった段階で、usageベースの見積もりに切り替えるとよいでしょう。

トークンを測る道具と、どこまで使うかの予算がそろいました。
次の節では、予算を超えたときに履歴を縮める仕組みを、ペアを壊さないように注意しながら自作していきます。

---

## 7.2 履歴の圧縮（compaction）を自作する

前節で、エージェントの履歴はツール結果を中心に膨らみ続けることを確認しました。
では、しきい値を超えたとき、具体的にどう縮めればよいのでしょうか。
「古いメッセージから順に捨てればいい」と考えた方もいるかもしれません。
ところが、Messages APIの履歴には、単純に捨てると壊れてしまう「つながり」があります。
本節では、そのつながりを守りながら履歴を縮める **compaction（コンパクション、履歴の圧縮）** を自作します。

### 圧縮の3つの段階

最初に、本節で作る仕組みの全体像を示しておきます。
本書では、履歴を縮める方法を軽いものから重いものへ、3段階で用意します。

| 段階 | 方法 | 失うもの | コスト |
|-----|-----|--------|------|
| 1 | 古いツール結果を短い要約文に差し替える | 古いツール結果の詳細 | ほぼゼロ（APIを呼ばない） |
| 2 | 古いやり取りを安価なモデルで要約する | 古いやり取りの細部 | 安価なモデルを1回呼ぶ |
| 3 | 直近N件だけを残して切り詰める | 古いやり取りすべて | ゼロ |

段階1は、前節で見た「犯人はツール結果」という観察に基づく対処です。
ツールの結果は、それを読んだ直後のassistantの応答に要点が反映されていることが多いので、古いものは中身を捨ててもほとんど困りません。
段階2は、それでも足りないときに、古いやり取りを「これまでの経緯」という短い文章に置き換える方法です。
段階3の切り詰めは、それだけで使うこともできますが、本書では要約の材料を切り出すための部品として使います。
`maybe_compact()`は、段階1を試し、それでもしきい値を超えていれば段階3で切り出した古い部分を段階2で要約する、という順で動きます。

[FIG_7_3｜フロー｜可｜maybe_compactの判断フロー｜計測→ツール結果を縮小→再計測→古い部分を要約→新しい履歴を組み立て]

### 壊してはいけない「ペア」

まず、履歴を切るときの制約を正確に理解しましょう。
第5章で学んだように、Claudeがツールを使うとき、履歴は次のような形になります。

```json
[
  {"role": "user", "content": "東京の天気を調べて"},
  {"role": "assistant", "content": [
    {"type": "text", "text": "天気を調べます。"},
    {"type": "tool_use", "id": "toolu_01", "name": "get_weather", "input": {"city": "Tokyo"}}
  ]},
  {"role": "user", "content": [
    {"type": "tool_result", "tool_use_id": "toolu_01", "content": "晴れ、22度"}
  ]},
  {"role": "assistant", "content": [{"type": "text", "text": "東京は晴れで22度です。"}]}
]
```

ここで、`tool_result`の`tool_use_id`は、直前のassistantメッセージにある`tool_use`の`id`を指しています。
この2つは必ずペアで存在しなければなりません。
もし古い側から1件だけ捨てて、assistantの`tool_use`が消え、userの`tool_result`だけが残ったとしましょう。
APIは「対応するtool_useがないtool_resultがある」と判断し、400エラー（invalid_request_error）を返します。
逆に、tool_useだけが残ってtool_resultが消えた場合も同じくエラーになります。

さらにもう1つ、履歴の先頭は必ずuserメッセージでなければならないという制約もあります。
つまり、切る位置を選ぶときには、次の2つの条件を同時に満たす必要があります。

- 残す部分の先頭が、tool_resultを含むuserメッセージではないこと（ペアの片割れにならない）
- 最終的な履歴の先頭がuserメッセージであること

[FIG_7_4｜構造図｜可｜安全な切断位置と危険な切断位置｜tool_useとtool_resultの間で切るとペアが壊れることを示す]

たとえるなら、往復書簡の束から古いものを捨てる場面に似ています。
「返信」だけを残して「元の手紙」を捨てると、返信が何に答えているのか分からなくなります。
APIはこの不整合を許してくれないので、プログラムの側で確実に防ぐ必要があります。

### 安全な切断位置を探す

それでは、この2つの条件を満たす切断位置を探す関数を書きます。
ここからのコードは **context.pyへの追加** です。
前節の計測部分の下、`if __name__ == "__main__":`の上に追加してください。

```python
# context.py（追加: 安全な切断位置と切り詰め）
import copy


def _is_tool_result_message(message: dict) -> bool:
    """tool_result を含む user メッセージかどうかを判定する。"""
    content = message.get("content")
    # content が文字列のときは通常の発話なので tool_result ではない
    if message.get("role") != "user" or not isinstance(content, list):
        return False
    return any(block.get("type") == "tool_result" for block in content)


def _safe_cut_index(messages: list[dict], keep_last: int) -> int:
    """直近 keep_last 件を残すときの、ペアを壊さない切断位置を返す。"""
    # まずは単純に「後ろから keep_last 件」の位置を候補にする
    cut = max(0, len(messages) - keep_last)
    # 候補が tool_result の user メッセージなら、ペアの片割れになるので前へずらす
    while cut > 0 and _is_tool_result_message(messages[cut]):
        cut -= 1
    return cut


def truncate_history(messages: list[dict], keep_last: int) -> list[dict]:
    """直近 keep_last 件程度を残して切り詰める。tool_use と tool_result のペアは壊さない。"""
    cut = _safe_cut_index(messages, keep_last)
    kept = messages[cut:]
    # 先頭が assistant になった場合は、先頭が user になるよう目印のメッセージを補う
    if kept and kept[0]["role"] == "assistant":
        notice = {"role": "user", "content": "（これより前の会話は省略されました。続きを進めてください）"}
        kept = [notice] + kept
    return kept
```

1つ目の`_is_tool_result_message()`は、メッセージがtool_resultを含むuserメッセージかどうかを判定します。
contentが文字列の場合は、人間が入力した通常の発話なのでFalseを返します。
contentが配列の場合は、その中に`type`が`"tool_result"`のブロックが1つでもあればTrueです。
第6章で学んだとおり、並列ツール呼び出しでは1つのuserメッセージに複数のtool_resultが入ります。
そのため、`any()`で「1つでもあるか」を判定しています。

2つ目の`_safe_cut_index()`が、この節の要です。
まず「後ろからkeep_last件」の位置を候補にします。
その位置にあるメッセージがtool_resultを含むuserメッセージなら、直前にあるassistantのtool_useが切り捨てられてしまいます。
そこで、条件を満たさなくなるまで切断位置を1つずつ前にずらします。
前にずらすと残すメッセージは少し増えますが、ペアは必ず守られます。

ここで「後ろにずらす」のではなく「前にずらす」ことにした理由も説明しておきます。
後ろにずらすと、残す件数がkeep_lastより少なくなり、直近の大事な文脈まで失う恐れがあります。
多めに残すぶんにはエラーにならず、文脈も失いません。
迷ったら「安全で、情報を失わない側」に倒す、というのが圧縮処理の基本姿勢です。

3つ目の`truncate_history()`は、切断位置から後ろを残し、先頭がassistantになった場合だけ目印のuserメッセージを補います。
切断位置がassistantメッセージになることは、エージェントループではよくあります。
assistantのtool_useと、その次のuserのtool_resultは両方とも残るので、ペアは壊れていません。
足りないのは「先頭がuser」という条件だけなので、短い目印を1つ足せば済みます。

### 動作を確かめるための小さなテスト

切り詰めはバグが入りやすい処理なので、APIを呼ばずに確かめられる小さなテストを書いておきます。
pytest（パイテスト）は第10章で導入するので、ここではassert文だけで確認します。
次のコードは単独のファイルではなく、`context.py`の`__main__`ブロックの末尾（内訳を表示する`for`文の後ろ）に、先頭のインデントを付けたまま追加してください。

```python
# context.py（動作確認用: __main__ ブロック内に追加）
    # 6件の履歴: user → assistant(tool_use) → user(tool_result) → assistant(tool_use) → user(tool_result) → assistant
    history = [
        {"role": "user", "content": "調べて"},
        {"role": "assistant", "content": [{"type": "tool_use", "id": "t1", "name": "a", "input": {}}]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "r1"}]},
        {"role": "assistant", "content": [{"type": "tool_use", "id": "t2", "name": "b", "input": {}}]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t2", "content": "r2"}]},
        {"role": "assistant", "content": [{"type": "text", "text": "完了"}]},
    ]
    # 後ろ2件を残そうとすると、候補は index 4（tool_result）→ 前へずれて index 3 になる
    assert _safe_cut_index(history, keep_last=2) == 3
    truncated = truncate_history(history, keep_last=2)
    # 先頭が assistant だったので目印の user が補われ、4件になる
    assert truncated[0]["role"] == "user" and len(truncated) == 4
    print("truncate_history: OK")
```

このテストでは、ツールを2回使った6件の履歴を用意しています。
後ろから2件を残そうとすると、候補の位置はindex 4で、そこはtool_resultのuserメッセージです。
そのため、切断位置は1つ前のindex 3（assistantのtool_use）にずれます。
残るのはindex 3〜5の3件で、先頭がassistantなので目印のuserが補われ、合計4件になります。

```bash
# 切り詰めのテストを実行する
uv run python context.py
```

```text
   tools:     412 tokens
  system:      38 tokens
messages:   4,627 tokens
   total:   5,077 tokens
truncate_history: OK
```

前節の内訳表示に続いて`truncate_history: OK`と表示されれば成功です。
assertが失敗すると`AssertionError`が出て止まるので、どの条件が崩れたのかをすぐに確認できます。

> **TIP**: 圧縮のような「データ構造を組み替える処理」は、APIを呼ばずにテストできるように作っておくと開発が楽になります。APIを呼ぶ部分（要約）と、呼ばない部分（切断位置の計算）を関数として分けておくのはそのためです。

### 段階1：古いツール結果を縮める

次に、APIを呼ばずにできる最も軽い圧縮として、古いツール結果を縮める関数を書きます。
考え方はシンプルです。
直近いくつかのtool_resultはそのまま残し、それより古いものは短い文に差し替えます。
短い文には、元の長さと先頭の一部だけを残します。

```python
# context.py（追加: 段階1 古いツール結果の縮小）
def _result_text(block: dict) -> str:
    """tool_result の content を文字列として取り出す（文字列・ブロック配列の両方に対応）。"""
    content = block.get("content", "")
    if isinstance(content, str):
        return content
    # content がブロック配列の場合は text ブロックだけをつなげる
    return "".join(b.get("text", "") for b in content if b.get("type") == "text")


def shrink_old_tool_results(
    messages: list[dict], *, keep_recent: int = 3, preview_chars: int = 200
) -> list[dict]:
    """直近 keep_recent 件以外の tool_result を、先頭の一部だけの短い文に置き換える。"""
    # 元の履歴を壊さないよう、深いコピーに対して書き換える
    new_messages = copy.deepcopy(messages)
    # tool_result を含むメッセージの位置を集め、古いものだけを対象にする
    positions = [i for i, m in enumerate(new_messages) if _is_tool_result_message(m)]
    targets = positions[:-keep_recent] if keep_recent > 0 else positions
    for i in targets:
        for block in new_messages[i]["content"]:
            if block.get("type") != "tool_result":
                continue
            text = _result_text(block)
            # すでに短いものはそのまま（縮めても効果がない）
            if len(text) <= preview_chars:
                continue
            # tool_use_id と is_error は残し、中身だけを差し替える
            block["content"] = (
                f"[古いツール結果のため省略。元の長さ {len(text):,} 文字。冒頭: {text[:preview_chars]}…]"
            )
    return new_messages
```

まず`_result_text()`です。
tool_resultの`content`は、文字列で返すこともできれば、textブロックの配列で返すこともできます。
どちらの形でも中身の文字列を取り出せるように、2つの場合を分けて処理しています。

`shrink_old_tool_results()`では、最初に`copy.deepcopy()`で履歴を丸ごとコピーしています。
Pythonのリストや辞書は、そのまま書き換えると呼び出し元の履歴まで変わってしまいます。
圧縮が失敗したときに元の履歴へ戻せるよう、元のデータには手を付けない作りにしています。

次に、tool_resultを含むメッセージの位置を集め、`positions[:-keep_recent]`で古いものだけを対象にしています。
対象のブロックでは、`tool_use_id`と`is_error`はそのまま残し、`content`だけを短い文に差し替えます。
`tool_use_id`を残すことで、ペアのつながりは壊れません。
差し替える文には元の長さと冒頭200文字を入れています。
これでClaudeは「以前このツールで長い結果を得た」という事実と、その大まかな中身を知ることができます。

> **POINT**: 古いツール結果を縮めても、困ることは意外と少ないです。Claudeはツール結果を読んだ直後の応答で、その要点を自分の言葉で書いていることが多いからです。必要になれば、Claudeはもう一度ツールを呼んで読み直すこともできます。「読み直せる情報は捨ててよい」と考えると、判断しやすくなります。

### 段階2：安価なモデルで古いやり取りを要約する

段階1で足りないときは、古いやり取りそのものを要約に置き換えます。
要約には、第4章で`llm_client.py`に定義した`FAST_MODEL`（`claude-haiku-5-5`）を使います。
`claude-haiku-5-5`の入力単価は100万トークンあたり0.10ドルです（入力10万トークン以下の場合。超えると単価が上がります）。
`claude-opus-5-5`の4ドルと比べると、40分の1にあたります。
要約のような定型的な作業は、安価なモデルで十分にこなせます。

要約の前に、履歴をモデルが読みやすいテキストに変換する関数を用意します。

```python
# context.py（追加: 段階2 要約のための書き起こし）
from llm_client import FAST_MODEL, call_messages, extract_text


def _to_transcript(messages: list[dict], *, result_chars: int = 1000) -> str:
    """履歴を、要約モデルが読みやすい書き起こしテキストに変換する。"""
    lines: list[str] = []
    for message in messages:
        role = "ユーザー" if message["role"] == "user" else "アシスタント"
        content = message["content"]
        # 文字列の content は通常の発話としてそのまま書き出す
        if isinstance(content, str):
            lines.append(f"{role}: {content}")
            continue
        for block in content:
            kind = block.get("type")
            if kind == "text":
                lines.append(f"{role}: {block['text']}")
            elif kind == "tool_use":
                # どのツールを、どんな引数で呼んだかを1行で残す
                args = json.dumps(block["input"], ensure_ascii=False)
                lines.append(f"{role}（ツール呼び出し）: {block['name']}({args})")
            elif kind == "tool_result":
                # ツール結果は長くなりがちなので先頭だけを渡す
                text = _result_text(block)[:result_chars]
                mark = "（エラー）" if block.get("is_error") else ""
                lines.append(f"ツール結果{mark}: {text}")
            # thinking ブロックは要約の材料にしない（中身が空のことも多い）
    return "\n".join(lines)
```

この関数は、履歴を「ユーザー: 〜」「アシスタント: 〜」という形の書き起こしに変換します。
JSONのまま要約モデルに渡すこともできますが、構造の記号が多いぶんトークンを無駄にします。
要約の質も下がりがちです。
人間が読みやすい形は、モデルにとっても読みやすい形なのです。

tool_useは「ツール名(引数のJSON)」という1行にまとめ、tool_resultは先頭1,000文字だけを渡します。
エラーだった結果には「（エラー）」という印を付けています。
「どのツールが失敗したか」は、その後の作業方針に影響する大事な情報だからです。
thinkingブロックは、要約の材料から外しています。
7.5節で説明するように、既定では中身が空文字で返ってくることが多く、材料として役に立たないためです。

続いて、書き起こしを要約する関数です。

```python
# context.py（追加: 段階2 要約）
SUMMARY_SYSTEM = (
    "あなたはAIエージェントの作業記録を要約する担当です。"
    "後で作業を再開する人が、この要約だけで続きを進められるように書いてください。\n"
    "必ず含める項目: 1. ユーザーの依頼と目的 2. 確定した事実・決定事項 "
    "3. 実行済みの操作と結果（ファイル名・数値・IDは正確に） 4. 未完了の作業と次にやること 5. 失敗した操作とその理由\n"
    "推測で情報を足さないこと。箇条書きで、日本語で書くこと。"
)


def summarize_history(messages: list[dict]) -> str:
    """古い履歴を FAST_MODEL で要約し、要約文を返す。"""
    transcript = _to_transcript(messages)
    response = call_messages(
        [{"role": "user", "content": f"<transcript>\n{transcript}\n</transcript>\n\n上記の作業記録を要約してください。"}],
        system=SUMMARY_SYSTEM,
        model=FAST_MODEL,
        max_tokens=4000,
    )
    # stop_reason を先に確認し、途中で切れた要約に気づけるようにする
    if response.get("stop_reason") == "max_tokens":
        logger.warning("要約が max_tokens で打ち切られました。末尾が欠けている可能性があります")
    return extract_text(response).strip()
```

`SUMMARY_SYSTEM`は、要約担当に渡すsystemプロンプトです。
ここで最も大切なのは、「後で作業を再開する人が、この要約だけで続きを進められるように」という目的の書き方です。
単に「要約して」と頼むと、モデルは会話のあらすじを書きがちです。
しかし、エージェントに必要なのはあらすじではなく、続きの作業に必要な **状態** です。
そこで、依頼・確定事項・実行済みの操作・未完了の作業・失敗の5項目を明示しています。

「ファイル名・数値・IDは正確に」という一文にも理由があります。
要約の過程で`report_2026.md`が「レポートのファイル」に丸められると、続きの作業でファイルを特定できなくなります。
固有の値は、要約で最も失われやすく、かつ最も失われると困る情報です。

`call_messages()`の呼び出しでは、`model=FAST_MODEL`を指定し、`max_tokens`は4000に抑えています。
要約は短くなければ意味がないからです。
書き起こしは`<transcript>`というXML風のタグで囲んでいます。
こうすると、書き起こしの中にある「〜してください」という文言を、要約担当への指示と取り違えにくくなります。

最後に、`stop_reason`が`max_tokens`だった場合に警告を出しています。
第3章で学んだとおり、本文を読む前に必ずstop_reasonを確認するのが本書の約束でした。
要約が途中で切れていても圧縮自体は続けますが、ログに残しておけば後から原因を追えます。

### しきい値で自動圧縮するmaybe_compact()

部品がそろったので、それらを組み合わせる`maybe_compact()`を書きます。
エージェントループは、毎ターンのAPI呼び出しの前にこの関数を呼びます。
しきい値を下回っていれば何もせず、超えていれば段階1、それでも超えていれば段階2を実行します。

```python
# context.py（追加: 自動圧縮）
def _first_user_text(messages: list[dict]) -> str:
    """最初の user メッセージの本文（最初の依頼）を取り出す。"""
    for message in messages:
        if message["role"] == "user" and not _is_tool_result_message(message):
            content = message["content"]
            if isinstance(content, str):
                text = content
            else:
                text = "".join(b.get("text", "") for b in content if b.get("type") == "text")
            # 圧縮済みの履歴なら、先頭は要約メッセージ。<original_request> の中身だけを取り出す
            if "<original_request>\n" in text:
                text = text.split("<original_request>\n", 1)[1].split("\n</original_request>", 1)[0]
            return text
    return ""


def maybe_compact(
    messages: list[dict],
    *,
    system: str | list[dict] | None,
    tools: list[dict] | None,
    threshold: int = DEFAULT_THRESHOLD,
    keep_last: int = 10,
) -> list[dict]:
    """しきい値を超えていたら履歴を圧縮して新しい履歴を返す。超えていなければそのまま返す。"""
    tokens = estimate_tokens(messages, system=system, tools=tools)
    if tokens < threshold:
        return messages
    logger.info("履歴が %s トークンでしきい値を超えたため圧縮します", f"{tokens:,}")

    # 段階1: 古いツール結果を縮める（API を呼ばない軽い処理）
    shrunk = shrink_old_tool_results(messages)
    tokens = estimate_tokens(shrunk, system=system, tools=tools)
    if tokens < threshold:
        logger.info("ツール結果の縮小で %s トークンになりました", f"{tokens:,}")
        return shrunk

    # 段階2: 古い部分を切り出して FAST_MODEL で要約する
    cut = _safe_cut_index(shrunk, keep_last)
    old, recent = shrunk[:cut], shrunk[cut:]
    if not old:
        # 切り出せる古い部分がない（直近だけで超えている）ときはそのまま返す
        logger.warning("圧縮できる古い履歴がありません（直近 %d 件だけでしきい値超え）", keep_last)
        return shrunk
    summary = summarize_history(old)
    # 最初の依頼は要約に任せず原文のまま残す（目的のずれを防ぐ）
    header = (
        f"<original_request>\n{_first_user_text(messages)}\n</original_request>\n"
        f"<conversation_summary>\n{summary}\n</conversation_summary>\n"
        "上記は、これまでの作業の要約です。この続きから作業を進めてください。"
    )
    if recent and recent[0]["role"] == "user" and not _is_tool_result_message(recent[0]):
        # 残す部分の先頭が通常の user 発話なら、その前に要約を差し込んで1つにまとめる
        first = copy.deepcopy(recent[0])
        body = first["content"] if isinstance(first["content"], list) else [{"type": "text", "text": first["content"]}]
        first["content"] = [{"type": "text", "text": header}] + body
        compacted = [first] + recent[1:]
    else:
        # 先頭が assistant（または残す部分が空）なら、要約だけの user メッセージを先頭に置く
        compacted = [{"role": "user", "content": [{"type": "text", "text": header}]}] + recent
    after = estimate_tokens(compacted, system=system, tools=tools)
    logger.info("要約による圧縮: %s → %s トークン", f"{tokens:,}", f"{after:,}")
    return compacted
```

長い関数なので、段落ごとに読んでいきましょう。

冒頭では`estimate_tokens()`で現在の量を測り、しきい値未満ならそのまま`messages`を返します。
ほとんどのターンはここで終わるので、圧縮のコストはcount_tokens 1回分だけです。

しきい値を超えていたら、段階1として`shrink_old_tool_results()`を呼び、もう一度測ります。
これで下回れば、要約APIを呼ばずに済みます。
段階1の結果を`shrunk`という別の変数に入れているのは、元の`messages`を壊さないためです。

段階2では、`_safe_cut_index()`で古い部分と新しい部分の境目を決め、古い部分`old`だけを要約に回します。
`old`が空の場合は、直近keep_last件だけでしきい値を超えている状態です。
このときに要約しても縮められないので、警告を出してそのまま返します。
この状況が頻発するなら、ツール結果自体が大きすぎるサインです。
第6章で作ったファイル読み取りツールのサイズ上限を見直すとよいでしょう。

要約ができたら、新しい履歴の先頭に置く`header`を組み立てます。
ここで、最初の依頼だけは要約に任せず、`<original_request>`タグで原文のまま残しています。
要約を何度も繰り返すと、伝言ゲームのように目的が少しずつずれていくことがあります。
最初の依頼という「北極星」を原文で残しておけば、何度圧縮しても目的を見失いません。
2回目以降の圧縮では、履歴の先頭がこの要約メッセージになります。
`_first_user_text()`が`<original_request>`の中身だけを取り出しているのは、タグが入れ子になってheaderが圧縮のたびに膨らむのを防ぐためです。

最後に、`header`を履歴の先頭にどう置くかを決めています。
残す部分`recent`の先頭が通常のuser発話なら、そのcontentの前に要約を差し込んで1つのメッセージにまとめます。
userメッセージを2つ連続させるのを避け、構造をすっきりさせるためです。
先頭がassistantなら、要約だけのuserメッセージを新しく先頭に置きます。
どちらの場合も、先頭がuserで、ペアが壊れていない履歴ができあがります。

[FIG_7_5｜構造図｜可｜圧縮前後の履歴の形｜古い部分が要約userメッセージ1件に置き換わり直近N件が残る]

### 小さなしきい値で圧縮を体験する

本番のしきい値15万トークンでは、圧縮が起きるまで時間がかかります。
動作を確かめるために、しきい値を極端に小さくして試してみましょう。
`context.py`の`__main__`ブロックの末尾に、次のコードを追加します。

```python
# context.py（動作確認用: __main__ ブロック末尾に追加）
    logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # httpx自身のログは抑える
    # さきほどの履歴のうち tool_result で終わる先頭5件に、長いツール結果を持たせて圧縮を起こす
    long_history = copy.deepcopy(history[:5])
    long_history[2]["content"][0]["content"] = "観測データ: " + "晴れ 22度 湿度40% " * 400
    long_history[4]["content"][0]["content"] = "観測データ: " + "曇り 18度 湿度65% " * 400
    compacted = maybe_compact(long_history, system=system, tools=[GET_WEATHER_TOOL], threshold=1500, keep_last=2)
    print(f"圧縮前 {len(long_history)} 件 → 圧縮後 {len(compacted)} 件")
    print(compacted[0]["content"][0]["text"][:300])
```

ここでは、さきほどの履歴から先頭の5件だけを取り出し、2つのtool_resultに長い観測データを入れています。
6件目のassistantを除いたのは、assistantで終わる履歴はprefillとみなされ、count_tokensが400エラーを返すことがあるからです。
実際のループでは、圧縮するときの履歴は必ずuserで終わるので、この心配はありません。
しきい値を1,500トークン、keep_lastを2に設定し、確実に圧縮が起きるようにしています。
実行結果の例は次のとおりです。

```bash
# 圧縮の動作を確認する
uv run python context.py
```

```text
truncate_history: OK
context INFO 履歴が 5,312 トークンでしきい値を超えたため圧縮します
llm_client INFO request_id=req_011... model=claude-haiku-5-5 stream=False elapsed=2.10s stop=end_turn in=702 out=188 cache_write=0 cache_read=0 cost=$0.0002
context INFO 要約による圧縮: 5,312 → 2,893 トークン
圧縮前 5 件 → 圧縮後 3 件
<original_request>
調べて
</original_request>
<conversation_summary>
- ユーザーの依頼: 調査（詳細な目的は未記載）
- 実行済み: ツール a を実行し、観測データ（晴れ・22度・湿度40%）を取得
...
```

ログを上から読んでみましょう。
最初の行で、履歴が5,312トークンになり、しきい値1,500を超えたことがわかります。
段階1では、直近3件のtool_resultは残す設定です。
この例ではtool_resultが2件しかないので縮小の対象がなく、まだしきい値を超えています。
そのため段階2に進み、`claude-haiku-5-5`への要約リクエストが1回送られています。
この行は第4章で作った`llm_client`のログで、どのモデルに何トークン送ったかが確認できます。

最後の行で、5,312トークンが2,893トークンまで縮み、5件の履歴が3件になったことがわかります。
しきい値の1,500はまだ上回っていますが、これは直近2件に含まれる長いtool_resultがそのまま残っているためです。
直近の文脈は原文で残すという設計どおりの動きです。
実際の運用では、しきい値15万トークンに対して直近10件が占める量は小さいので、要約後は十分に下回ります。

> **NOTE**: 実行結果のトークン数や要約の文面は一例で、実行のたびに変わります。要約の中身が`SUMMARY_SYSTEM`で指定した5項目に沿っているかを、目で確認してください。項目が抜けるようなら、systemプロンプトの書き方を調整します。

### つまずきやすいポイントと対処

compactionを自作するときに、筆者がよく見かける失敗を3つ挙げておきます。

1つ目は、**切断位置の計算ミスで400エラーになる** ケースです。
エラーメッセージに`tool_use_id`や`tool_result`という語が含まれていたら、ペアが壊れています。
`_safe_cut_index()`を使わずに、`messages[-10:]`のような単純なスライスで切っていないかを確認してください。

2つ目は、**要約のたびに作業が振り出しに戻る** ケースです。
すでに読んだファイルを何度も読み直したり、終わった作業をやり直したりする症状です。
多くの場合、要約に「実行済みの操作と結果」が十分に残っていません。
`SUMMARY_SYSTEM`の項目を見直すとともに、keep_lastを少し大きくして、直近の文脈を多めに残すとよいでしょう。

3つ目は、**圧縮が毎ターン起きてしまう** ケースです。
要約後の量がしきい値のすぐ下にあると、次のターンでまた超えてしまいます。
この場合は、要約後の量がしきい値の半分程度になるよう、keep_lastを小さくするか、ツール結果の上限を下げます。
圧縮は、7.3節で扱うキャッシュを作り直す原因にもなるので、頻繁に起きるのは望ましくありません。

> **WARNING**: 圧縮すると、履歴の先頭部分が書き換わります。そのため、次の節で扱うPrompt cachingのうち、messagesの部分のキャッシュは圧縮の直後に一度作り直しになります。toolsとsystemのキャッシュは影響を受けません。圧縮は「たまに起きる大掃除」くらいの頻度に抑えるのが理想です。

### 圧縮は「忘れ方を設計する」こと

ここまでの実装を振り返ると、compactionとは単なるデータの削除ではないことがわかります。
何を原文で残し、何を要約し、何を捨てるか。
それはエージェントの「忘れ方」を設計することです。

人間も、昨日の会議の発言を一言一句覚えてはいません。
覚えているのは、決まったことと、次にやることです。
エージェントの圧縮も同じで、続きの作業に必要な状態を残せていれば、細部を忘れても問題は起きません。
逆に、どんなに大量の履歴を残しても、必要な状態が埋もれていれば意味がありません。

なお、本節の仕組みは「1つのエージェントの中で」コンテキストを節約する方法です。
そもそも膨らみそうな作業を別のエージェントに任せ、結果だけを受け取るという方法もあります。
これは第8章のマルチエージェントで扱います。
圧縮とエージェントの分割は、競合するものではなく、組み合わせて使う道具です。

履歴を縮める仕組みができました。
次の節では、縮めても毎回送り続ける部分、つまりtoolsとsystemを、キャッシュで安く速く送る方法を扱います。

---

## 7.3 Prompt caching

7.1節で内訳を測ったとき、toolsとsystemは毎回まったく同じ内容で送られていました。
messagesも、前回送った部分の後ろに新しいやり取りが足されるだけです。
つまりリクエストの大部分は、前回とまったく同じ内容の繰り返しです。
同じものを毎回、定価で読ませ続ける必要はあるのでしょうか。
本節では、この繰り返し部分を安く速く処理させる **Prompt caching（プロンプトキャッシング）** を導入します。

### 前方一致とtools→system→messagesの順序

Prompt cachingとは、リクエストの先頭からある位置までの処理結果をAnthropic側に一時保存し、次のリクエストで再利用する仕組みです。
再利用できるのは、先頭から1文字も違わずに一致している部分だけです。
これを **前方一致** と呼びます。

APIの内部では、リクエストは`tools`→`system`→`messages`の順に並べて処理されます。
そのため、どこか1か所が変わると、そこから後ろはすべてキャッシュが効かなくなります。
たとえばツール定義を1つ変えると、systemとmessagesのキャッシュも無効になります。
一方、messagesの末尾に新しいやり取りを足すだけなら、前回までの部分はそのまま再利用できます。

辞書の索引にたとえると分かりやすいでしょう。
「あいうえお」まで同じ単語は、途中まで同じページをたどれます。
しかし、先頭の1文字が違えば、最初から引き直しです。
キャッシュを効かせるには、変わらないものを前に、変わるものを後ろに置くことが原則になります。

[FIG_7_6｜概念図｜可｜前方一致キャッシュの仕組み｜tools→system→messagesの順に並び変更箇所より後ろが無効になる]

### cache_controlとブレークポイント

キャッシュしたい範囲は、ブロックに`cache_control: {"type": "ephemeral"}`を付けて指定します。
この目印を **ブレークポイント（Breakpoint）** と呼び、先頭からその位置までがキャッシュの対象になります。
ブレークポイントは1リクエストに最大4つまで置けます。
`ephemeral`は「一時的な」という意味で、既定では5分間使われなければ消えます。
キャッシュが読まれるたびに、その寿命は延長されます。

もう1つ、リクエストのトップレベルに`cache_control`を置く方法もあります。
こちらは自動キャッシュで、キャッシュ可能な最後のブロックにブレークポイントが自動で置かれます。
会話が伸びると、その位置も自動で後ろへ移動します。
トップレベルの指定も、4つの枠のうち1つを使う点に注意してください。

本書のエージェントでは、次の3つのブレークポイントを使います。

| 位置 | 指定方法 | ねらい |
|-----|--------|------|
| toolsの最後のツール | ツール定義に`cache_control`を付ける | ツール定義全体を再利用する |
| systemの最後のブロック | systemをブロック配列にして付ける | systemを再利用する（メモリ差し込み後も） |
| messagesの末尾 | トップレベルの`cache_control`（自動） | 伸びていく履歴を毎ターン再利用する |

### キャッシュの最小長と料金

キャッシュには最小の長さがあります。
これより短い部分は、`cache_control`を付けてもキャッシュされません。
エラーにはならず、黙ってキャッシュなしで処理されるので注意が必要です。
最小長はモデルによって異なり、512〜4,096トークンの範囲です。
使うモデルの値は、公式ドキュメントで確認してください。

料金は、書き込みと読み取りで扱いが異なります。
キャッシュへの書き込み（5分の既定の寿命）は、通常の入力単価の1.25倍です。
キャッシュからの読み取りは、通常の入力単価の0.1倍が基本です。
ただし執筆時点の公式ドキュメントでは、`claude-opus-5-5`と`claude-sonnet-5-5`の読み取りは0.05倍とさらに安く設定されています。
倍率はモデルや時期によって変わり得るので、第4章の`CostTracker`の単価表は料金ページで確認して合わせてください。

計算してみましょう。
2万トークンのtoolsとsystemを、`claude-opus-5-5`で20回送るとします。
キャッシュなしなら、2万×20＝40万トークン分で1.6ドルです。
キャッシュありなら、初回の書き込みが0.1ドル、残り19回の読み取りが合計で約0.08ドルです。
同じ処理が、およそ9分の1のコストで済みます。
読み取りは処理も速いので、応答までの待ち時間も短くなります。

### llm_client.pyにキャッシュ用の補助関数を足す

それでは実装に入ります。
まず **llm_client.pyの更新** として、systemとtoolsにブレークポイントを付ける補助関数を追加します。

```python
# llm_client.py（第7章で追加: キャッシュ用の補助関数）
import copy

CACHE_CONTROL = {"type": "ephemeral"}


def cached_system(text: str) -> list[dict]:
    """system 文字列を、末尾にブレークポイントを付けたブロック配列に変換する。"""
    return [{"type": "text", "text": text, "cache_control": CACHE_CONTROL}]


def cached_tools(tools: list[dict]) -> list[dict]:
    """ツール定義の最後の1つにブレークポイントを付けたコピーを返す。"""
    if not tools:
        return tools
    # 呼び出し元の定義を書き換えないよう深いコピーを作る
    result = copy.deepcopy(tools)
    # 最後のツールに付ければ、tools 全体が1つのキャッシュ範囲になる
    result[-1]["cache_control"] = CACHE_CONTROL
    return result
```

`cached_system()`は、文字列のsystemをブロック配列に変換します。
`cache_control`はブロックに付けるものなので、文字列のままでは付けられません。
第3章で`system`が文字列とブロック配列の両方を受け付けると学んだのは、ここで生きてきます。

`cached_tools()`は、ツール定義の最後の1つにだけ`cache_control`を付けます。
ブレークポイントは「先頭からここまで」を意味するので、最後に1つ付ければtools全体が対象になります。
`deepcopy`しているのは、レジストリが持つ元のスキーマを書き換えないためです。

> **POINT**: 第6章で`ToolRegistry.schemas()`がツールを名前順に並べて返すようにしたのは、この節のためです。並び順が毎回変わると、内容が同じでも前方一致が崩れ、キャッシュが一度も効きません。

### agent.pyを圧縮とキャッシュに対応させる

次に、**agent.pyのrun_agent()を更新** します。
第6章版からの変更点は、毎ターンの`maybe_compact()`と、3つのブレークポイントです。
7.5節で使う`effort`引数も、ここで先に足しておきます。
import の2行は既存の import の下に、定数`BASE_SYSTEM`は`logger`の定義の近くに追加し、`run_agent()`は関数全体を差し替えてください。

```python
# agent.py（第7章版: import と定数 BASE_SYSTEM を追加し、run_agent を更新。ほかの関数は第6章のまま）
from context import maybe_compact
from llm_client import cached_system, cached_tools

# エージェントの基本方針（7.4節で使う）。日時などの可変値は入れない
BASE_SYSTEM = "あなたは作業ディレクトリ workspace/ のファイルを扱うアシスタントです。"


def run_agent(
    user_input: str,
    *,
    registry: ToolRegistry,
    system: str | None = None,
    max_turns: int = 10,
    effort: str | None = None,
) -> str:
    """履歴の圧縮とキャッシュを使いながら、ツールを実行して最終回答を返す"""
    # tools と system は毎回同じ内容なので、最初に1回だけブレークポイント付きに変換する
    tools = cached_tools(registry.schemas())
    system_blocks = cached_system(system) if system else None
    output_config = {"effort": effort} if effort else None
    messages: list[dict] = [{"role": "user", "content": user_input}]

    for turn in range(1, max_turns + 1):
        # 各ターンの前に、しきい値を超えていれば履歴を圧縮する
        messages = maybe_compact(messages, system=system_blocks, tools=tools)
        response = call_messages(
            messages,
            system=system_blocks,
            tools=tools,
            output_config=output_config,
            # トップレベルの自動キャッシュで、伸びていく messages の末尾にもブレークポイントを置く
            extra={"cache_control": {"type": "ephemeral"}},
        )
        stop_reason = response["stop_reason"]
        logger.info("turn=%d stop_reason=%s", turn, stop_reason)
        # thinking ブロックを含む content を、改変せずにそのまま履歴へ戻す
        messages.append({"role": "assistant", "content": response["content"]})

        if stop_reason == "tool_use":
            # 第6章の execute_tool_uses をそのまま使う（並列実行・副作用ツールの承認・is_error）
            results = execute_tool_uses(registry, get_tool_uses(response))
            # すべての tool_result を1つの user メッセージにまとめて返す
            messages.append({"role": "user", "content": results})
            continue
        if stop_reason == "pause_turn":
            continue  # サーバーツールの一時停止。同じ履歴で再送する
        if stop_reason == "max_tokens":
            return extract_text(response) + "\n\n（出力が上限に達したため、回答が途中で切れています）"
        if stop_reason == "refusal":
            return "（この依頼には回答できないと判断されました）"
        return extract_text(response)  # end_turn / stop_sequence: 最終回答

    return f"（{max_turns} ターン以内に完了しなかったため停止しました）"
```

ツールの実行は、第6章で作った`execute_tool_uses()`にそのまま任せています。
読み取り系の並列実行も、`write_file`の実行前確認も、`is_error`での失敗の返し方も、第6章のまま引き継がれます。
停止理由ごとの分岐も第6章版と同じなので、変わったのはAPIを呼ぶ前後の部分だけです。

ループに入る前に、toolsとsystemを1回だけブレークポイント付きに変換しています。
ループ内で毎回変換しても内容は同じですが、「毎回同じものを送る」ことを構造で保証するために外に出しています。

ループの先頭では`maybe_compact()`を呼び、必要なら履歴を圧縮します。
圧縮関数には、実際に送るのと同じ`system_blocks`と`tools`を渡しています。
送る内容と数える内容がずれると、予算の判断を誤るからです。

`call_messages()`の`extra`には、トップレベルの`cache_control`を渡しています。
第4章で`extra`を「その他のボディ項目」として用意しておいたので、関数の形を変えずに済みました。
toolsとsystemの2つと合わせて、ブレークポイントは3つで、上限の4つに収まります。

### 効果を測る

キャッシュは設定が少し違うだけで黙って効かなくなるので、必ず数値で効果を確かめます。
第6章のファイル操作ツールを持たせて、ファイルの要約を頼んでみましょう。
`llm_client`のINFOログに、毎回のusageが出力されます（次の例は`llm_client`の行だけを抜き出したものです）。

```bash
# 第7章版のエージェントを実行する
uv run python agent.py "workspace の notes.md を読んで3行で要約して"
```

```text
llm_client INFO request_id=req_011CZa... model=claude-opus-5-5 stream=False elapsed=2.41s stop=tool_use in=152 out=96 cache_write=3418 cache_read=0 cost=$0.0196
llm_client INFO request_id=req_011CZb... model=claude-opus-5-5 stream=False elapsed=3.05s stop=end_turn in=1207 out=211 cache_write=0 cache_read=3418 cost=$0.0097
```

数値は一例です。
1回目は`cache_creation_input_tokens`（ログのcache_write）が3,418で、キャッシュへの書き込みが起きています。
2回目は`cache_read_input_tokens`（ログのcache_read）が3,418で、前回の内容が読み取られています。
2回目の`input_tokens`は、新しく足されたtool_resultなど、キャッシュされていない部分だけの量です。
入力の合計は、この3つを足した値になります。

もし2回目以降もcache_readが0のままなら、どこかで前方一致が崩れています。
原因の多くは次の3つです。

- systemに現在時刻や連番など、毎回変わる値を入れている
- ツールの並び順や定義が呼び出しごとに変わっている
- キャッシュ対象が最小長に届いていない

> **WARNING**: systemプロンプトに`datetime.now()`の結果を埋め込むと、毎回内容が変わり、キャッシュが一度も効かなくなります。日付が必要なら、日単位に丸めるか、最初のuserメッセージに入れてください。トップレベルのeffortを会話の途中で変えた場合も、messagesのキャッシュは無効になります（モデルによってはtools・systemも）。ただし既定値（Opus 5.5なら`medium`）を明示的に送るのは省略と同じ扱いで、キャッシュは壊れません。

圧縮で減らし、キャッシュで安く送る仕組みがそろいました。
次の節では、会話が終わっても残したい情報を、ファイルという外部の記憶に逃がします。

---

## 7.4 ファイルによる長期メモリ

ここまでの工夫は、すべて1回の会話の中での話でした。
エージェントを再起動すると、履歴は空になり、ユーザーの好みも前回の決定事項もすべて消えてしまいます。
「先週も言ったのに」とユーザーに思わせないためには、どうすればよいでしょうか。
本節では、会話をまたいで事実を残す長期メモリを、ツールとJSONファイルで自作します。

### 短期記憶と長期記憶

エージェントの記憶は、2種類に分けて考えると整理しやすくなります。

| 種類 | 置き場所 | 寿命 | 例 |
|-----|--------|-----|---|
| 短期記憶 | messages（コンテキスト） | 1回の会話。圧縮で薄れる | いま読んだファイルの中身 |
| 長期記憶 | 外部ファイル | 会話をまたいで残る | ユーザーの好み、プロジェクトの決定事項 |

短期記憶は、人間でいえば作業中に机の上に広げている資料です。
長期記憶は、ノートに書き留めて棚にしまった情報です。
机の上は広くないので、残したいものはノートに書き、必要なときに棚から取り出します。
これを、`save_memory`（書き留める）と`search_memory`（取り出す）という2つのツールで実現します。

[FIG_7_7｜構造図｜可｜短期記憶と長期記憶の関係｜messagesとmemory.jsonの間をsave_memoryとsearch_memoryが往復する]

### tools/memory.pyを作る

**tools/memory.pyを新規作成** します。
記憶は`memory.json`に、キー・内容・タグ・更新日時の組として保存します。

```python
# tools/memory.py（第7章で新規作成）
import json
from datetime import datetime
from pathlib import Path

from tool_registry import ToolRegistry

MEMORY_FILE = Path("memory.json")


def _load() -> list[dict]:
    """メモリファイルを読み込む。なければ空のリストを返す。"""
    if not MEMORY_FILE.exists():
        return []
    return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))


def _save(items: list[dict]) -> None:
    """一時ファイルに書いてから置き換え、書き込み途中の破損を防ぐ。"""
    tmp = MEMORY_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(MEMORY_FILE)


def save_memory(key: str, content: str, tags: list[str] | None = None) -> str:
    """記憶を保存する。同じ key があれば上書きする。"""
    items = [m for m in _load() if m["key"] != key]
    items.append({"key": key, "content": content, "tags": tags or [], "updated_at": datetime.now().isoformat(timespec="seconds")})
    _save(items)
    return f"記憶を保存しました: {key}"


def search_memory(query: str, limit: int = 5) -> str:
    """空白区切りの語をすべて含む記憶を、新しい順に返す。"""
    words = [w.lower() for w in query.split()]
    hits = []
    for m in _load():
        haystack = " ".join([m["key"], m["content"], *m["tags"]]).lower()
        if all(w in haystack for w in words):
            hits.append(m)
    hits.sort(key=lambda m: m["updated_at"], reverse=True)
    if not hits:
        return "該当する記憶はありません。"
    return json.dumps(hits[:limit], ensure_ascii=False)


def register_memory_tools(registry: ToolRegistry) -> None:
    """2つのメモリツールをレジストリに登録する。"""
    registry.tool(
        name="save_memory",
        description="今後の会話でも役立つ事実（ユーザーの好み・決定事項など）を長期記憶に保存する。"
        "一時的な作業メモやパスワード等の秘密情報は保存しない。同じ key は上書きされる。",
        input_schema={"type": "object", "properties": {
            "key": {"type": "string", "description": "記憶を表す短い識別名（例: user_preferred_language）"},
            "content": {"type": "string", "description": "保存する内容。1〜3文で具体的に"},
            "tags": {"type": "array", "items": {"type": "string"}, "description": "検索用のタグ"},
        }, "required": ["key", "content"]},
        side_effect=True,  # 永続ファイルを書き換えるので、第6章の実行前確認の対象にする
    )(save_memory)
    registry.tool(
        name="search_memory",
        description="長期記憶をキーワードで検索する。過去の決定やユーザーの好みを確認したいときに使う。",
        input_schema={"type": "object", "properties": {
            "query": {"type": "string", "description": "空白区切りのキーワード。すべてを含む記憶が返る"},
        }, "required": ["query"]},
    )(search_memory)
```

`_save()`では、一時ファイルに書いてから`replace()`で置き換えています。
書き込み中にプログラムが落ちても、`memory.json`が中途半端な状態で残らないようにするためです。

`save_memory()`は、同じキーの記憶を取り除いてから追加することで上書きを実現しています。
ユーザーの好みが変わったとき、古い情報と新しい情報が並んでClaudeが迷うのを防げます。

`search_memory()`は、空白で区切った語をすべて含む記憶を新しい順に返す、素朴な検索です。
本格的な意味検索も考えられますが、まずはこの単純な方法で十分に役立ちます。

`register_memory_tools()`では、第6章の`registry.tool()`デコレーターを関数として呼んでいます。
descriptionには「何を保存すべきでないか」も書いています。
これを書かないと、Claudeは作業の途中経過まで何でも保存しがちです。
`save_memory`には`side_effect=True`を付けています。
記憶は以降のすべての会話に影響するので、第6章の`write_file`と同じく、保存の前に人間の承認を挟みます。

### 起動時にsystemへ差し込む

ツールだけでは、Claudeが「検索しよう」と思わない限り記憶は使われません。
そこで、起動時に最近の記憶をsystemに差し込みます。
**tools/memory.pyに追加** する関数です。

```python
# tools/memory.py（追加: system への差し込み）
def memory_prompt(limit: int = 20) -> str:
    """最近の記憶を system に差し込むための文章を作る。"""
    items = sorted(_load(), key=lambda m: m["updated_at"], reverse=True)[:limit]
    if not items:
        return ""
    lines = [f"- {m['key']}: {m['content']}" for m in items]
    return "<long_term_memory>\n" + "\n".join(lines) + "\n</long_term_memory>"
```

使う側では、`system = BASE_SYSTEM + "\n\n" + memory_prompt()`のように、元のsystemの末尾に足します。
差し込むのは起動時の1回だけです。
会話の途中で差し替えるとsystemの内容が変わり、7.3節のキャッシュが崩れてしまうからです。
`limit`で件数を絞っているのは、7.1節で決めたsystemの予算を守るためです。

`agent.py`の実行部分（第6章で作った`__main__`ブロック）は、次のように **更新** します。

```python
# agent.py（第7章版の __main__ ブロック）
if __name__ == "__main__":
    import sys

    from tools.memory import memory_prompt, register_memory_tools

    logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # httpx自身のログは抑える
    question = sys.argv[1] if len(sys.argv) > 1 else "workspace のファイルを一覧にして"
    # 第6章の build_registry() で天気・ファイル操作ツール入りの registry を作り、メモリツールを追加する
    registry = build_registry()
    register_memory_tools(registry)
    # 起動時に1回だけ、最近の記憶を system の末尾に足す
    system = BASE_SYSTEM + "\n\n" + memory_prompt()
    print(run_agent(question, registry=registry, system=system))
    print(tracker.summary())  # 呼び出し回数・トークン・合計コスト
```

`build_registry()`は、第6章で`agent.py`に用意したレジストリの組み立て関数です。
`BASE_SYSTEM`は7.3節で`agent.py`に定数として追加した、エージェントの基本方針を書いたsystemプロンプトです。
記憶の文章は、この`BASE_SYSTEM`の後ろに足します。

実際に2回に分けて実行すると、記憶が引き継がれることを確認できます。

```bash
# 1回目: 好みを伝える／2回目: 新しい会話で確かめる
uv run python agent.py "今後レポートは必ず箇条書き3点でまとめてほしい。覚えておいて"
uv run python agent.py "notes.md を要約して"
```

```text
[確認] ツール save_memory を次の引数で実行します:
{
  "key": "report_format",
  "content": "レポートは必ず箇条書き3点でまとめる"
}
実行してよいですか？ [y/N]: y
記憶を保存しました。今後のレポートは箇条書き3点でまとめます。
calls=2 input=250 output=153 cache_write=1,920 cache_read=1,850 total=$0.0140
- notes.md は第7章の執筆メモです
- 主なテーマは…
- 次の作業は…
calls=3 input=1,630 output=262 cache_write=2,410 cache_read=4,020 total=$0.0246
```

1回目は`save_memory`の実行前に承認を求められ、`y`で記憶が保存されます（ログの行は省略しています）。
2回目は新しい会話ですが、systemに差し込まれた記憶に従って箇条書き3点で答えています。

> **WARNING**: 長期メモリは、一度書かれると以降のすべての会話に影響します。悪意のある文書を読んだClaudeが「今後は〜せよ」という偽の指示を記憶に保存してしまう危険があります。保存内容を人間が確認できるようにし、秘密情報は保存させないでください。この種の攻撃（プロンプトインジェクション）への対策は第11章で詳しく扱います。

---

## 7.5 思考（adaptive thinking）とeffort

最後に、コンテキストとは少し違う角度から、品質とコストを調整する方法を扱います。
同じエージェントでも、「ファイル名の一覧を出して」と「設計の矛盾を見つけて」では、必要な考える量がまったく違います。
すべての問いに同じ深さで考えさせるのは、むだでもあり、ときに不足でもあります。
本節では、Claudeの思考の仕組みと、その深さを調整するeffortを整理します。

### adaptive thinkingの仕組み

**adaptive thinking（アダプティブ シンキング、適応的思考）** とは、Claudeが問いの難しさを見て、考えるかどうか・どれだけ考えるかを自分で決める仕組みです。
`claude-opus-5-5`では、この仕組みが常に有効です。
`thinking`パラメータは省略してかまいません。
逆に`{"type": "disabled"}`を送ると、400エラーになります。

考えた場合、レスポンスの`content`に`thinking`ブロックが含まれます。

```json
{
  "content": [
    {"type": "thinking", "thinking": "", "signature": "EuYBCkQYAiJA..."},
    {"type": "text", "text": "設計に2つの矛盾があります。…"}
  ],
  "stop_reason": "end_turn",
  "usage": {"input_tokens": 1820, "output_tokens": 948, "output_tokens_details": {"thinking_tokens": 702}}
}
```

既定では、`thinking`の中身は空文字で返ってきます。
空でも、思考に使ったトークンは出力トークンとして課金されます。
実際にどれだけ考えたかは、公式ドキュメントで説明されている`usage.output_tokens_details.thinking_tokens`で確認できます。
`signature`は、思考の内容が改ざんされていないことを確かめるための署名です。

思考は、`max_tokens`の中から使われる点にも注意してください。
深く考えたぶん本文に使える量が減り、`stop_reason`が`max_tokens`で止まることがあります。
その場合は、`max_tokens`を増やすか、次に説明するeffortを下げます。

### effortの段階とタスク別の目安

思考の深さは、`output_config: {"effort": ...}`で指定します。
段階は`low`・`medium`・`high`・`xhigh`・`max`の5つで、`claude-opus-5-5`の既定は`medium`です。

| effort | 特徴 | タスクの目安 |
|-------|-----|----------|
| `low` | 思考を最小限にし、速さを優先する | 分類、定型の抽出、短い確認 |
| `medium` | 既定。簡単な問いでは思考を省く | 一般的な対話、日常的なエージェント作業 |
| `high` | 多くの問いで深く考える | 複雑な調査、コードのデバッグ |
| `xhigh` | `high`よりさらに深く探索する | 長時間の自律作業、難しい設計判断 |
| `max` | 思考の量に制約を設けない | 最難関の問題。コストと時間は最大 |

effortは「必ずこれだけ考える」という指定ではなく、考え方の傾向を示す目安です。
どの段階でも、Claudeは問いごとに考えるかどうかを判断します。
7.3節で作った`run_agent()`には`effort`引数を足してあるので、次のように使い分けられます。

```python
# effort の使い分け例（agent.py を使う側のコード）
from agent import build_registry, run_agent

registry = build_registry()
# 定型的な整理は low で速く安く
run_agent("workspace のファイル名を一覧にして", registry=registry, effort="low")
# 設計レビューは high で深く
run_agent("design.md の設計に矛盾がないか検討して", registry=registry, effort="high")
```

まずは既定の`medium`で動かし、品質が足りなければ上げ、遅さやコストが気になれば下げる、という順で調整するのがおすすめです。
1つの会話の途中でトップレベルのeffortを変えると、少なくともmessagesのキャッシュが無効になります（モデルによってはtools・systemも）。
既定値を明示的に送るだけなら省略と同じ扱いなので、キャッシュは壊れません。
会話ごとに1つの段階を決めて、途中では変えないようにしましょう。

[FIG_7_8｜比較｜可｜effortの段階と品質・コストの関係｜lowからmaxへ思考量・待ち時間・コストが増える様子]

### thinkingブロックは改変せずに履歴へ戻す

エージェントループで最も大切な約束がこれです。
assistantの`content`は、thinkingブロックを含めて **そのまま** 履歴に戻します。
7.3節の`run_agent()`でも、`response["content"]`を加工せずに追加していました。

特にツール使用の途中では、thinkingブロックが「なぜそのツールを呼んだか」という推論のつながりを運んでいます。
中身が空だからといって削除したり、`signature`を書き換えたりしてはいけません。
7.2節の圧縮でも、残すassistantメッセージには一切手を加えず、古い部分は丸ごと要約に置き換えました。
これは、thinkingブロックを途中で切り刻まないための設計でもあります。

> **WARNING**: 履歴を整形するつもりで、thinkingブロックを取り除いたり、text以外のブロックを捨てたりするコードを書かないでください。ツールループの推論が途切れて振る舞いが不安定になります。assistantのcontentは「受け取ったまま戻す」と覚えておきましょう。

---

## 本章のまとめ

本章で学んだことを整理します：

- `count_tokens`で送信前にトークン数を測り、上限より手前のしきい値で`maybe_compact()`が履歴を圧縮します。圧縮ではtool_useとtool_resultのペアを壊さず、古いツール結果の縮小と`claude-haiku-5-5`による要約を使い分けます
- Prompt cachingは`tools`→`system`→`messages`の前方一致で効きます。`cache_control`のブレークポイントを置き、可変値を前方に入れず、`cache_read_input_tokens`で効果を必ず確かめます
- `tools/memory.py`で会話をまたぐ長期記憶を持たせ、起動時にsystemへ差し込みます。思考の深さはeffortで調整し、thinkingブロックは改変せずに履歴へ戻します

本章で、1つのエージェントのコンテキストを「測る・減らす・安く送る・外に逃がす」道具がそろいました。
それでも、調査とレビューと執筆を1つのエージェントにすべて任せると、コンテキストはいずれ抱えきれなくなります。
1つのエージェントで抱えきれないときは、コンテキストを分けて複数のエージェントに任せます。
次章では **マルチエージェントを自作する** を扱います。本章の`run_agent()`を`Agent`クラスへ育て、役割の違うエージェントを並列に動かしていきましょう。
