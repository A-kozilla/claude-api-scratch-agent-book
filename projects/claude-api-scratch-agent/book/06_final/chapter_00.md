# はじめに
# EN-TITLE: INTRODUCTION
# TAGS: AIエージェント, Claude API, スクラッチ開発, httpx, 5部構成

## この章で学ぶこと

本章では以下を学びます：

- SDKもフレームワークも使わずに、AIエージェントを「スクラッチから」作る意義を説明できる
- 本書の対象読者・前提知識・扱わないものを確認し、自分に合った読み方を選べる
- 5部構成の全体像と、1つのコードベースを育てながら進む学び方を把握できる

本章は本書の入り口のため、前提となる章はありません。ここでは本書の狙いと歩き方を確認し、第1章からの学習に備えます。

---

## 本書を手に取ってくださった皆様へ

AIエージェントという言葉を、この1〜2年で何度も目にしてきたと思います。興味を持った方の多くは、まずフレームワークのサンプルを動かしてみます。ところが少し手を加えたとたん、ツールが呼ばれない、同じ処理を繰り返す、エラーで止まるといった問題が起きます。そのとき、どこを見ればよいのかが分からないのです。原因は読者の力不足ではなく、便利な道具が内部の処理を上手に隠しているからです。

本書は、その壁を越えるための本です。使うのはClaude API（クロード・エーピーアイ）のMessages APIです。これをHTTP（エイチティーティーピー）のリクエストで直接呼び出します。APIは Application Programming Interface の略です。プログラムから別のサービスの機能を呼び出す窓口を指します。SDK（エスディーケー、Software Development Kit）もエージェント用フレームワークも使いません。外部ライブラリは、HTTP通信用の `httpx` と設定を読む `python-dotenv` の2つだけです。

筆者自身も、フレームワークのサンプルから入って苦労した一人です。霧が晴れたのは、APIに送るJSONを自分の手で組み立てたときでした。「ツール呼び出しとは、この配列を往復させることだったのか」と腑に落ちたのです。本書は、その瞬間を読者の皆様に体験していただくために書いています。

本書を読み終えるころには、次のことができるようになっているはずです。

- AIエージェントの基本構造（LLM＋ツール＋ループ＋コンテキスト）を、自分のコードで説明できる
- Messages APIをHTTPで直接呼び、リクエスト・レスポンス・エラーを正しく扱える
- リトライ・ストリーミング・コスト計測を備えた自作APIクライアントを実装できる
- ツールとエージェンティックループ、マルチエージェント構成を自分で設計・実装できる
- 安全性・評価・コスト管理を押さえ、業務を自動化するエージェントを一人で作れる

LLM（エルエルエム、Large Language Model）は大規模言語モデルのことで、Claudeもその一つです。新しい用語は、登場するたびに意味を添えていきます。

---

## なぜ「スクラッチから」作るのか

便利なSDKがあるのに、なぜわざわざ自分で書くのでしょうか。理由は3つあります。

**1つ目は、中で何が起きているかがすべて見えることです。** エージェントの正体は素朴な仕組みです。LLMに履歴とツールの説明を送り、「このツールを使いたい」と返ってきたらツールを実行し、結果を履歴に足してまた送ります。これを終わるまで繰り返すだけです。本書ではこの繰り返しを `while` ループとして自分で書くため、何が送られ何が返るのかを自分の目で確かめられます。

**2つ目は、困ったときに自分で直せることです。** エージェントは思いどおりに動かないことが当たり前の技術です。自分で書いたコードなら、送ったJSON（ジェイソン）を保存して何度でも読み返せます。仕組みが分かっていれば、エラーメッセージは「次に見る場所」を教える地図になります。

**3つ目は、道具が変わっても通用することです。** AI関連の道具は驚くほどの速さで入れ替わります。一方、HTTP・JSON・SSE・JSON Schemaは長く使われてきた標準技術です。SSE（エスエスイー）は Server-Sent Events の略です。その上に組み立てた理解は、他のモデルや道具にも応用できます。

<figure id="fig-0-1">
<svg width="605" height="360" viewBox="0 0 605 360"
     xmlns="http://www.w3.org/2000/svg"
     font-family="'Noto Sans JP',sans-serif">
  <defs>
    <marker id="f0_1_arrow" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#333" stroke-width="1.5"/>
    </marker>
    <marker id="f0_1_arrowA" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#2b6cb0" stroke-width="1.5"/>
    </marker>
  </defs>
  <rect x="0" y="0" width="605" height="360" fill="#ffffff"/>
  <path d="M302 20 L302 320" fill="none" stroke="#bbb" stroke-width="1.0" stroke-dasharray="4 3"/>
  <text x="155" y="28" text-anchor="middle" dominant-baseline="central" font-size="13" fill="#1a1a1a" font-weight="bold">フレームワークを使う</text>
  <rect x="55" y="48" width="200" height="34" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="155.0" y="65.0" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a">あなたのコード（数行）</text>
  <path d="M155 82 L155 100" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f0_1_arrow)"/>
  <rect x="30" y="100" width="250" height="140" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="155" y="116" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a" font-weight="bold">フレームワーク（中身は見えない）</text>
  <rect x="60" y="130" width="190" height="22" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.2" stroke-dasharray="5 3"/>
  <text x="155.0" y="141.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">履歴の管理</text>
  <rect x="60" y="156" width="190" height="22" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.2" stroke-dasharray="5 3"/>
  <text x="155.0" y="167.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">リトライ</text>
  <rect x="60" y="182" width="190" height="22" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.2" stroke-dasharray="5 3"/>
  <text x="155.0" y="193.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">ツールのループ</text>
  <rect x="60" y="208" width="190" height="22" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.2" stroke-dasharray="5 3"/>
  <text x="155.0" y="219.0" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">stop_reason の分岐</text>
  <path d="M155 240 L155 262" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f0_1_arrow)"/>
  <rect x="55" y="262" width="200" height="34" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="155.0" y="279.0" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a">Claude API</text>
  <text x="155" y="312" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#555">内部処理が箱の中に隠れている</text>
  <text x="450" y="28" text-anchor="middle" dominant-baseline="central" font-size="13" fill="#2b6cb0" font-weight="bold">スクラッチで作る（本書）</text>
  <rect x="325" y="48" width="250" height="192" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="450" y="64" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a" font-weight="bold">自分で書くコード（すべて見える）</text>
  <rect x="340" y="80" width="220" height="30" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.2"/>
  <text x="350" y="95" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">messages 配列で履歴を管理</text>
  <text x="552" y="95" text-anchor="end" dominant-baseline="central" font-size="11" fill="#2b6cb0">第3章</text>
  <rect x="340" y="118" width="220" height="30" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.2"/>
  <text x="350" y="133" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">リトライ・ストリーミング</text>
  <text x="552" y="133" text-anchor="end" dominant-baseline="central" font-size="11" fill="#2b6cb0">第4章</text>
  <rect x="340" y="156" width="220" height="30" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.2"/>
  <text x="350" y="171" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">while ループでツールを実行</text>
  <text x="552" y="171" text-anchor="end" dominant-baseline="central" font-size="11" fill="#2b6cb0">第5章</text>
  <rect x="340" y="194" width="220" height="30" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.2"/>
  <text x="350" y="209" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">stop_reason で分岐</text>
  <text x="552" y="209" text-anchor="end" dominant-baseline="central" font-size="11" fill="#2b6cb0">第3・5章</text>
  <path d="M450 240 L450 262" fill="none" stroke="#2b6cb0" stroke-width="1.3" marker-end="url(#f0_1_arrowA)"/>
  <text x="462" y="251" text-anchor="start" dominant-baseline="central" font-size="11" font-family="Consolas,monospace" fill="#2b6cb0">httpx（HTTP）</text>
  <rect x="350" y="262" width="200" height="34" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="450.0" y="279.0" text-anchor="middle" dominant-baseline="central" font-size="12" fill="#1a1a1a">Claude API（Messages API）</text>
  <text x="450" y="312" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#555">送る JSON・返る JSON を自分の目で確かめられる</text>
  <text x="302" y="346" text-anchor="middle" font-size="11" fill="#666">図0.1 フレームワーク利用とスクラッチ開発の違い</text>
</svg>
  <figcaption>図0.1: フレームワーク利用とスクラッチ開発の違い</figcaption>
</figure>

図0.1の左側では、履歴管理・リトライ・ツールループが箱の中に隠れています。右側では、それらがすべて自分のコードとして並んでいます。

> **POINT**: 本書はSDKやフレームワークを否定しているわけではありません。狙いは、道具に頼る前に「道具が何をしているか」を知ることです。

---

## 本書で作るもの

本書では、章ごとに使い捨てのサンプルを作るわけではありません。1つのプロジェクト `agent-from-scratch` を最後まで育てます。出発点は、第2章で作る次のような小さなプログラムです。いまは雰囲気をつかめれば十分です。

```python
# hello_claude.py（第2章で作るファイルの骨格）
import os  # 環境変数を読むための標準ライブラリ

import httpx  # HTTPリクエストを送るためのライブラリ
from dotenv import load_dotenv  # .env ファイルを読み込むためのライブラリ

load_dotenv()  # .env に書いた ANTHROPIC_API_KEY を環境変数として読み込む

# Messages API のエンドポイントに POST リクエストを送る
response = httpx.post(
    "https://api.anthropic.com/v1/messages",
    headers={
        "x-api-key": os.environ["ANTHROPIC_API_KEY"],  # APIキー（コードに直接書かない）
        "anthropic-version": "2026-10-21",  # 本書が準拠するAPIバージョン
        "content-type": "application/json",  # ボディがJSONであることを伝える
    },
    json={
        "model": "claude-opus-5-5",  # 使用するモデル
        "max_tokens": 1024,  # 出力の上限トークン数
        "messages": [{"role": "user", "content": "こんにちは、Claude！"}],  # 会話の履歴
    },
    timeout=60.0,  # 応答を待つ秒数
)
response.raise_for_status()  # エラーのステータスなら例外にする

# content はブロックの配列なので、type が text のものだけを取り出して表示する
for block in response.json()["content"]:
    if block["type"] == "text":
        print(block["text"])
```

送るのはヘッダー3つとJSONのボディだけで、返ってくる `content` は種類ごとのブロックの配列です。この配列を正しく扱えることが、エージェント開発の土台になります。

ここから第4章で共通モジュール `llm_client.py` を作り、以降の章はすべてこれを読み込んで使います。第5章で `agent.py`、第6章で `tool_registry.py` を加えます。続いて第7章で `context.py`、第8章で `multi_agent.py` を加えます。第10章では、調査レポートを自動作成するマルチエージェントを完成させます。テーマを与えると司令塔役のエージェントが作業を計画し、調査役・執筆役・レビュー役が仕事を分担します。レビューで不足が見つかれば書き直し、コストの上限を守ってレポートを書き出します。自分の業務に合わせて役割やツールを差し替えれば、別の自動化にも応用できます。

<figure id="fig-0-2">
<svg width="605" height="400" viewBox="0 0 605 400"
     xmlns="http://www.w3.org/2000/svg"
     font-family="'Noto Sans JP',sans-serif">
  <defs>
    <marker id="f0_2_arrow" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#333" stroke-width="1.5"/>
    </marker>
    <marker id="f0_2_arrowA" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#2b6cb0" stroke-width="1.5"/>
    </marker>
  </defs>
  <rect x="0" y="0" width="605" height="400" fill="#ffffff"/>
  <text x="20" y="39" text-anchor="start" dominant-baseline="central" font-size="12" fill="#1a1a1a" font-weight="bold">第2章</text>
  <rect x="110" y="22" width="330" height="34" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="120" y="39" text-anchor="start" dominant-baseline="central" font-size="12" font-family="Consolas,monospace" fill="#1a1a1a" font-weight="bold">hello_claude.py</text>
  <text x="432" y="39" text-anchor="end" dominant-baseline="central" font-size="11" fill="#1a1a1a">最初の1往復（httpx で直接呼ぶ）</text>
  <path d="M150 56 L150 69" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f0_2_arrow)"/>
  <text x="20" y="86" text-anchor="start" dominant-baseline="central" font-size="12" fill="#1a1a1a" font-weight="bold">第4章</text>
  <rect x="132" y="69" width="330" height="34" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="142" y="86" text-anchor="start" dominant-baseline="central" font-size="12" font-family="Consolas,monospace" fill="#1a1a1a" font-weight="bold">llm_client.py</text>
  <text x="454" y="86" text-anchor="end" dominant-baseline="central" font-size="11" fill="#1a1a1a">共通クライアント（以降の全章で使う）</text>
  <path d="M172 103 L172 116" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f0_2_arrow)"/>
  <text x="20" y="133" text-anchor="start" dominant-baseline="central" font-size="12" fill="#1a1a1a" font-weight="bold">第5章</text>
  <rect x="154" y="116" width="330" height="34" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="164" y="133" text-anchor="start" dominant-baseline="central" font-size="12" font-family="Consolas,monospace" fill="#1a1a1a" font-weight="bold">agent.py</text>
  <text x="476" y="133" text-anchor="end" dominant-baseline="central" font-size="11" fill="#1a1a1a">エージェンティックループ</text>
  <path d="M194 150 L194 163" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f0_2_arrow)"/>
  <text x="20" y="180" text-anchor="start" dominant-baseline="central" font-size="12" fill="#1a1a1a" font-weight="bold">第6章</text>
  <rect x="176" y="163" width="330" height="34" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="186" y="180" text-anchor="start" dominant-baseline="central" font-size="12" font-family="Consolas,monospace" fill="#1a1a1a" font-weight="bold">tool_registry.py</text>
  <text x="498" y="180" text-anchor="end" dominant-baseline="central" font-size="11" fill="#1a1a1a">ツールレジストリ・並列実行</text>
  <path d="M216 197 L216 210" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f0_2_arrow)"/>
  <text x="20" y="227" text-anchor="start" dominant-baseline="central" font-size="12" fill="#1a1a1a" font-weight="bold">第7章</text>
  <rect x="198" y="210" width="330" height="34" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="208" y="227" text-anchor="start" dominant-baseline="central" font-size="12" font-family="Consolas,monospace" fill="#1a1a1a" font-weight="bold">context.py</text>
  <text x="520" y="227" text-anchor="end" dominant-baseline="central" font-size="11" fill="#1a1a1a">トークン計測・履歴圧縮</text>
  <path d="M238 244 L238 257" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f0_2_arrow)"/>
  <text x="20" y="274" text-anchor="start" dominant-baseline="central" font-size="12" fill="#1a1a1a" font-weight="bold">第8章</text>
  <rect x="220" y="257" width="330" height="34" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="230" y="274" text-anchor="start" dominant-baseline="central" font-size="12" font-family="Consolas,monospace" fill="#1a1a1a" font-weight="bold">multi_agent.py</text>
  <text x="542" y="274" text-anchor="end" dominant-baseline="central" font-size="11" fill="#1a1a1a">マルチエージェント</text>
  <path d="M260 291 L260 304" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f0_2_arrow)"/>
  <text x="20" y="321" text-anchor="start" dominant-baseline="central" font-size="12" fill="#1a1a1a" font-weight="bold">第10章</text>
  <rect x="242" y="304" width="330" height="34" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="252" y="321" text-anchor="start" dominant-baseline="central" font-size="12" font-family="Consolas,monospace" fill="#1a1a1a" font-weight="bold">report_agent</text>
  <text x="564" y="321" text-anchor="end" dominant-baseline="central" font-size="11" fill="#1a1a1a">調査レポート自動作成（完成）</text>
  <text x="20" y="362" text-anchor="start" dominant-baseline="central" font-size="11" fill="#555">※ 各章のファイルは前の章の成果物の上に積み上がる（土台は第4章の llm_client.py）</text>
  <text x="302" y="386" text-anchor="middle" font-size="11" fill="#666">図0.2 コードベースが育っていく流れ</text>
</svg>
  <figcaption>図0.2: コードベースが育っていく流れ</figcaption>
</figure>

図0.2は、ファイルが生まれて積み重なる順序を示しています。途中で迷子になったら、この図で現在地を確かめてください。

---

## 対象読者と前提知識

本書が主に想定しているのは、Pythonで小さなスクリプトやWeb APIのクライアントを書いた経験があるエンジニアです。生成AIをチャット画面では使っているが、フレームワークの中身を説明できない方に向いています。社内の業務自動化で、挙動・コスト・安全性を自分で制御したい方にも向いています。エージェント開発の経験は不要です。

| 区分 | 内容 |
|------|------|
| 必須 | Pythonの基礎文法（変数・関数・条件分岐・ループ・辞書とリスト）、ターミナルでのコマンド実行 |
| 望ましい | HTTP（メソッド・ステータスコード・ヘッダー）とJSONの基本、`async` / `await` に触れた経験 |

APIとのやり取りは、ほとんどが辞書とリストの組み立てと読み取りです。`response["usage"]["input_tokens"]` のような入れ子のアクセスが読めれば十分です。クラスやデコレーターは中盤以降で使いますが、登場するたびに説明します。望ましい知識は、必要になる章で説明します。一方、プログラミングがまったく初めての方や、ノーコードでエージェントを作りたい方には、本書は遠回りになるかもしれません。

---

## 本書で扱わないもの

次のものは、本書の目的となる仕組みの理解に集中するため扱いません。価値が低いからではなく、まさに本書で自作する部分を隠してしまうからです。

- Anthropic（アンソロピック）の各言語向けクライアントSDK（本書のコードはSDKを読み込みません）
- Claude Agent SDK や Claude Code の使い方・設定・拡張機能
- 特定のエージェント用フレームワークの使い方
- モデルの内部構造や学習方法などの機械学習の理論

SDKが用意しているリトライやストリーミングは、第4章で自分で作ります。SDKとの対応関係は第4章のコラムで整理し、Claude Code などは第12章で次の一歩として紹介します。

> **NOTE**: チャット画面の claude.ai と、開発者向けのClaude APIは別のサービスです。契約も料金体系も別になっています。詳しくは第2章で説明します。

---

## 本書の全体構成

本書は「はじめに」と12の章を、5つの部に分けています。

<figure id="fig-0-3">
<svg width="605" height="465" viewBox="0 0 605 465"
     xmlns="http://www.w3.org/2000/svg"
     font-family="'Noto Sans JP',sans-serif">
  <defs>
    <marker id="f0_3_arrow" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#333" stroke-width="1.5"/>
    </marker>
    <marker id="f0_3_arrowA" viewBox="0 0 10 10" refX="8" refY="5"
            markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="#2b6cb0" stroke-width="1.5"/>
    </marker>
  </defs>
  <rect x="0" y="0" width="605" height="465" fill="#ffffff"/>
  <rect x="20" y="20" width="130" height="44" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="85.0" y="32.6" text-anchor="middle" dominant-baseline="central" font-size="13" fill="#1a1a1a" font-weight="bold">はじめに</text>
  <text x="85.0" y="51.4" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">本書の狙いと歩き方</text>
  <rect x="165" y="20" width="420" height="44" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.2"/>
  <text x="178" y="42.0" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">はじめに：スクラッチで作る意義・全体構成</text>
  <path d="M150 42.0 L165 42.0" fill="none" stroke="#333" stroke-width="1.3"/>
  <path d="M85 64 L85 78" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f0_3_arrow)"/>
  <rect x="20" y="78" width="130" height="94" rx="6" fill="#e8f0fa" stroke="#2b6cb0" stroke-width="1.3"/>
  <text x="85.0" y="115.6" text-anchor="middle" dominant-baseline="central" font-size="13" fill="#1a1a1a" font-weight="bold">基礎</text>
  <text x="85.0" y="134.4" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">第1〜4章</text>
  <rect x="165" y="78" width="420" height="94" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.2"/>
  <text x="178" y="98.0" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">第1章　エージェントの定義と限界</text>
  <text x="178" y="116.0" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">第2章　環境構築とAPIキー管理</text>
  <text x="178" y="134.0" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">第3章　Messages API の読み解き</text>
  <text x="178" y="152.0" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">第4章　自作クライアント llm_client.py</text>
  <path d="M150 125.0 L165 125.0" fill="none" stroke="#333" stroke-width="1.3"/>
  <path d="M85 172 L85 186" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f0_3_arrow)"/>
  <rect x="20" y="186" width="130" height="76" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="85.0" y="214.6" text-anchor="middle" dominant-baseline="central" font-size="13" fill="#1a1a1a" font-weight="bold">応用</text>
  <text x="85.0" y="233.4" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">第5〜7章</text>
  <rect x="165" y="186" width="420" height="76" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.2"/>
  <text x="178" y="206.0" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">第5章　ツール定義とエージェンティックループ</text>
  <text x="178" y="224.0" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">第6章　ツールレジストリ・並列実行・構造化出力</text>
  <text x="178" y="242.0" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">第7章　トークン計測・履歴圧縮・Prompt caching</text>
  <path d="M150 224.0 L165 224.0" fill="none" stroke="#333" stroke-width="1.3"/>
  <path d="M85 262 L85 276" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f0_3_arrow)"/>
  <rect x="20" y="276" width="130" height="94" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="85.0" y="313.6" text-anchor="middle" dominant-baseline="central" font-size="13" fill="#1a1a1a" font-weight="bold">実践</text>
  <text x="85.0" y="332.4" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">第8〜11章</text>
  <rect x="165" y="276" width="420" height="94" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.2"/>
  <text x="178" y="296.0" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">第8章　マルチエージェントと asyncio</text>
  <text x="178" y="314.0" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">第9章　設計パターン</text>
  <text x="178" y="332.0" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">第10章　調査レポート自動作成プロジェクト</text>
  <text x="178" y="350.0" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">第11章　安全性・評価・コスト管理</text>
  <path d="M150 323.0 L165 323.0" fill="none" stroke="#333" stroke-width="1.3"/>
  <path d="M85 370 L85 384" fill="none" stroke="#333" stroke-width="1.3" marker-end="url(#f0_3_arrow)"/>
  <rect x="20" y="384" width="130" height="44" rx="6" fill="#f5f5f5" stroke="#333" stroke-width="1.2"/>
  <text x="85.0" y="396.6" text-anchor="middle" dominant-baseline="central" font-size="13" fill="#1a1a1a" font-weight="bold">まとめ</text>
  <text x="85.0" y="415.4" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#1a1a1a">第12章</text>
  <rect x="165" y="384" width="420" height="44" rx="6" fill="#ffffff" stroke="#333" stroke-width="1.2"/>
  <text x="178" y="406.0" text-anchor="start" dominant-baseline="central" font-size="11" fill="#1a1a1a">第12章　振り返り・実務導入チェックリスト・次の一歩</text>
  <path d="M150 406.0 L165 406.0" fill="none" stroke="#333" stroke-width="1.3"/>
  <text x="302" y="451" text-anchor="middle" font-size="11" fill="#666">図0.3 5部構成の学習ロードマップ</text>
</svg>
  <figcaption>図0.3: 5部構成の学習ロードマップ</figcaption>
</figure>

| 部 | 章 | 主な内容 |
|----|----|--------|
| はじめに | はじめに | 本書の狙い、前提知識、学び方 |
| 基礎 | 第1章〜第4章 | エージェントの定義と限界、環境構築とAPIキー管理、Messages APIの読み解き、自作クライアント `llm_client.py` |
| 応用 | 第5章〜第7章 | ツール定義とエージェンティックループ、ツールレジストリと並列実行・構造化出力、トークン計測・履歴圧縮・Prompt caching |
| 実践 | 第8章〜第11章 | マルチエージェントと `asyncio`、設計パターン、調査レポート自動作成プロジェクト、安全性・評価・コスト管理 |
| まとめ | 第12章 | 全体の振り返り、実務導入チェックリスト、次に学ぶリソース |

基礎編では、エージェントを「LLM＋ツール＋ループ」として定義します。また、APIが会話を覚えていないステートレスな性質を確認します。そのうえで環境を整え、リクエストとレスポンスを一つずつ読み解きます。最後に、リトライやストリーミングを備えた自作クライアントにまとめます。

応用編では、天気を答える小さなエージェントから始めて、ツールの数と質を高めます。ツールの失敗をLLMへ正しく伝える方法や、安全なファイル操作も扱います。長く動くエージェントのために、トークンを数えて履歴を圧縮し、繰り返し送る部分をキャッシュで安くする仕組みも作ります。

実践編では、サブエージェントを「ツールとして呼ぶ子のループ」として実装し、並列に動かします。そもそもエージェントが必要かという判断基準と設計パターンを整理し、第10章の総合演習ですべての部品を組み合わせます。第11章では、プロンプトインジェクションへの備えや評価（eval）など、本番で安心して任せるための論点を扱います。

> **POINT**: 各章は前の章の成果物を前提に積み上がっています。特に第4章の `llm_client.py` は第5章以降のすべての章で使うため、必ず自分で作ってください。

---

## 本書の読み方

コードは、できるだけ自分の手で打ち込みながら読んでください。打ち間違いから生まれるエラーを自分で直す経験が、そのままデバッグの力になります。動かしたら、APIから返ってきたJSONも必ず眺めましょう。API経験者の方は、第2・3章を要点の確認にとどめ、第4章から本格的に手を動かしてもかまいません。

本文には囲み記事が登場します。**POINT** は押さえておきたい要点、**NOTE** は補足や背景、**WARNING** は失敗しやすい点です。**STEP** は順番に進める手順、**COLUMN** は余裕があるときに読む読み物です。コードブロックの1行目には必ずファイル名をコメントで書き、既存ファイルを更新する場面では変更する関数を丸ごと示します。

各章は「この章で学ぶこと」で始まり、「本章のまとめ」の3点で終わります。まとめを自分の言葉で説明できるか試し、詰まった箇所の節を読み返してください。

コードが動かないときは、まずエラーメッセージを最後まで読みましょう。Claude APIのエラーは `type` と `message` を含むJSONで返ります。そこには、どの項目がなぜ問題なのかが書かれています。次に、実際に送ったJSONを表示して本文のコードと見比べます。それでも直らなければ、ひとつ前の章の完成コードに戻り、動く状態との差分を小さくしていきます。

---

## 開発環境とAPI利用料の目安

本書のコードは、Python 3.12、パッケージ管理ツールのuv（ユーブイ）、エディタのVS Codeを前提にしています。Windows・macOS・Linuxのいずれでも進められ、具体的な手順は第2章で説明します。

本書は、APIバージョン `2026-10-21` に準拠しています。この版では `temperature` などの項目が使えなくなっています。そのため、古い記事のコードを写すと400番のエラーになることがあります。本書のコードは、すべてこの版の仕様に合わせています。本書の記述と実際の挙動が食い違ったら、公式ドキュメントを優先してください。自作のクライアントなら、仕様が変わってもヘッダーやボディの一部を書き換えるだけで追従できます。

| 用途 | モデルID | 入力 / 出力（100万トークンあたり） |
|------|---------|--------------------------|
| 既定（メインのエージェント） | `claude-opus-5-5` | $4 / $20 |
| 中間 | `claude-sonnet-5-5` | $2 / $10 |
| 低コストの分類・要約・ワーカー | `claude-haiku-5-5` | $0.10 / $0.50（入力10万トークン以下） |

トークンは、LLMが文章を処理するときの最小単位です。短い質問1回なら費用はごくわずかですが、エージェントは1つの仕事でAPIを何度も呼び出します。ハンズオン全体の費用は、試行錯誤の回数やモデルで大きく変わります。そのため第4章で、呼び出しごとの料金を計算する `CostTracker` を作ります。以降は常に費用を見える化しながら進めます。

> **WARNING**: 学習を始める前に、Claude Consoleで必ず利用上限を設定してください。ループのバグでAPIを呼び続けても、被害を小さく抑えられます。

最後に心構えを3つお伝えします。1つ目に、エージェントはLLMの判断で動くため、思いどおりに動かないのが通常運転です。落ち込まずに「なぜその判断をしたのか」を読み解きましょう。2つ目に、最初から万能のエージェントを目指さず、小さく作って確実に動かしてから育てます。3つ目に、ファイルの書き換えのような副作用のある操作の権限と、「いくらで動いたか」というコストを早いうちから意識します。この3つは、本書の章立てそのものにも反映されています。

---

## 本章のまとめ

本章で学んだことを整理します：

- 本書は、SDKもフレームワークも使わず、`httpx` でClaude APIを直接呼んでAIエージェントを作る本です。中身がすべて見えるため、自分で直せる力と長く通用する理解が身につきます
- 対象はPythonの基礎が分かるエンジニアです。Claude Code・Claude Agent SDK・クライアントSDK・フレームワークの使い方は扱いません
- 5部・12章の構成で、第4章の `llm_client.py` を土台に1つのコードベースを育てます。APIは `2026-10-21` 版に準拠し、利用上限とコスト計測で費用を管理します

次章では **AIエージェントとは何か** を扱います。まずは、これから作る「AIエージェント」を正確に定義するところから始めましょう。
