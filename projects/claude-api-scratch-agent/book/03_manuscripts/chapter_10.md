# 第10章: 実践プロジェクト — 調査レポート自動作成マルチエージェント
# EN-TITLE: HANDS-ON PROJECT
# TAGS: マルチエージェント, オーケストレーター, 評価者-最適化者, httpx.MockTransport, コスト管理

## この章で学ぶこと

本章では以下を学びます：

- テーマを受け取ってから、調査・執筆・レビュー・修正を経てMarkdownレポートを出力するシステムを、要件定義から設計できるようになる
- オーケストレーターと3つのサブエージェント（リサーチャー・ライター・レビュアー）を、第4〜9章の部品だけで実装できるようになる
- 予算による打ち切り、CLI（コマンドラインインターフェース）化、`httpx.MockTransport` を使ったAPIを呼ばないテストまで含めて、「一人で最後まで作り切る」流れを体験する

前章では、チェーン・ルーター・並列化・評価者-最適化者といったワークフローのパターンと、「エージェントを使わない」という判断基準を学びました。
本章では、それらのパターンと、第4章の `llm_client.py`、第6章の `ToolRegistry`、第8章の `Agent` クラスを総動員して、実務で使える1つのアプリケーションを組み上げます。

これまでの章は、1つの節で1つの部品を作る構成でした。部品ごとに動作を確かめられる反面、「全部をつなげたときに何が起きるのか」は見えにくかったかもしれません。本章はその逆で、最初に完成形を決め、そこから逆算して部品を配置していきます。途中で「この部品は何章で作ったものか」を何度も振り返ることになるので、本書全体の復習としても読めるはずです。

題材は「調査レポートの自動作成」です。調べ物をして、メモを取り、文章にまとめ、誰かに見てもらって直す。これは多くの職場で日常的に行われている知的作業です。しかも、調べる・書く・評価するという性質の異なる作業が含まれるため、役割を分けたマルチエージェントの良さと難しさの両方を体験するのに向いています。

本章のコードはすべて、第2章から育ててきたプロジェクト `agent-from-scratch/` に追加します。新しいライブラリは、テスト用の pytest（パイテスト）だけです。HTTPの送受信は、これまでどおり httpx（エイチティーティーピーエックス）で Messages API を直接呼び出します。

---

## 10.1 要件定義と全体設計

いきなりコードを書き始めたくなる気持ちは、筆者にもよくわかります。しかし、複数のエージェントが協調するシステムでは、設計の曖昧さがそのままコストと品質の問題として跳ね返ってきます。どのエージェントが何を受け取り、何を返し、どこに保存するのか。それを決めないまま作ると、エージェント同士が同じ調査を繰り返したり、レビューが終わらなかったりします。

この節では、コードを1行も書かずに、システムの「契約」を決めていきます。具体的には、入力と出力、品質基準、コスト上限、役割分担、データの流れ、ファイルの置き場所の6つです。ここで決めたことは、後の節でそのままコードの定数や関数のシグネチャになります。

### 何を作るのか ── 入力と出力を1文で言えるか

最初に、システムが何を受け取り、何を返すのかを1文で言えるようにしておきます。本章で作るシステムは、次の1文で説明できます。

「調査テーマを1行受け取り、出典付きのMarkdownレポートを1ファイル出力する」。

入力は、たとえば「中小企業がAIエージェントを導入するときのコスト管理の勘所」のようなテーマ文字列です。ユーザーが渡すのはこれだけで、調査項目の分解や見出しの構成は、システム側が考えます。出力は、見出し・本文・出典一覧を含むMarkdownファイルで、そのまま社内Wikiやチャットに貼り付けられる形を想定しています。

この1文には、あえて書いていないことがあります。それは「どうやって調べるか」です。調べ方は、Web検索でもよいし、社内に蓄積した資料の検索でもかまいません。本章では、Web検索版と、手元のファイルを検索するローカル版の両方を用意します。入出力の定義から調べ方を外しておくと、後で検索手段を差し替えても、システム全体の約束は変わりません。

入出力をこのように単純に定めることには、もう1つの利点があります。CLIから呼んでも、別のプログラムから関数として呼んでも、同じ使い方になることです。10.4節でテストを書くときも、「テーマを渡すとレポートのパスが返る」という1点だけを確かめれば済みます。システムの境界が細いほど、テストも運用も楽になります。

### 処理の流れ ── 人間のチームならどう進めるか

次に、テーマからレポートができるまでの手順を決めます。迷ったときは、人間のチームならどう進めるかを考えるのが近道です。調査レポートを部署で作るとき、多くの場合は次のような流れになるでしょう。

1. 責任者がテーマを分解し、調べるべき問いと目次案を決める（計画）
2. 担当者が問いごとに手分けして調べ、出典付きのメモを残す（調査）
3. 書き手がメモをもとにレポートを書く（執筆）
4. レビュアーが基準に照らして評価し、修正点を返す（レビュー）
5. 必要なら追加で調べ、書き手が直す（修正）
6. 基準を満たすか、時間や予算が尽きたら提出する（完了）

本章のシステムも、この6段階をそのまま採用します。1の計画と6の完了判断を担うのがオーケストレーター（Orchestrator、指揮者役のエージェント）です。2〜4は、それぞれ専門のサブエージェントが担当します。5の修正は、レビュー結果を受けてオーケストレーターが「誰に何を頼むか」を決め直すことで実現します。

[FIG_10_1｜フロー｜可｜レポート作成の処理フロー｜計画→調査→執筆→レビュー→修正→完了の6段階]

この流れのうち、4と5の繰り返しは、第9章で学んだ評価者-最適化者（Evaluator-Optimizer）パターンそのものです。書く役と評価する役を分け、評価が基準を満たすまで改善を繰り返します。第9章では1つのスクリプトの中で完結させましたが、本章では、その繰り返しを「どこまで続けるか」の判断をオーケストレーターに任せます。

なぜ全部を固定のコードで書かず、オーケストレーターに判断させるのでしょうか。理由は、レビュー後の対応がケースごとに違うからです。表現の問題だけなら書き直せば済みますが、根拠が足りない場合は追加の調査が必要です。どの問いを追加で調べるべきかは、レビューの中身を読まないと決められません。こうした「中身を読んでから次の一手を選ぶ」部分こそ、LLMに判断を任せる価値がある部分です。

一方で、計画を立てる・調査を並列で走らせる・最終ファイルを書き出すといった手順は、毎回同じです。第9章で学んだとおり、決まった手順はコードで書き、判断が必要な部分だけをエージェントにします。本章のシステムは、固定のワークフローと自律的なエージェントを組み合わせた「ハイブリッド型」です。この線引きは、実務で自分のシステムを設計するときにも、そのまま使える考え方です。

### 品質基準 ── 「よいレポート」を言葉にする

レビュアーに評価をさせるには、「よいレポートとは何か」を言葉で定義しておく必要があります。人間のレビューでも、基準が曖昧だと指摘が人によってぶれます。LLMの場合はなおさらで、基準を与えないと、毎回もっともらしいけれど一貫しない指摘が返ってきます。

本章では、次の5つの観点でレポートを評価します。こうした評価の観点と段階をまとめた表を、ルーブリック（Rubric、評価基準表）と呼びます。

| 観点 | キー | 5点の状態 | 2点以下の状態 |
|---|---|---|---|
| 網羅性 | `coverage` | 調査計画の問いすべてに答えている | 問いの半分以上に触れていない |
| 根拠 | `evidence` | 主要な主張すべてに出典が付き、メモと矛盾しない | 出典のない断定が目立つ |
| 構成 | `structure` | 結論が先にあり、見出しの流れが自然 | 結論が見えず、話題が行き来する |
| 読みやすさ | `readability` | 想定読者が一読で理解できる | 専門用語が説明なしに続く |
| 実用性 | `actionability` | 読者が次に何をすべきかがわかる | 事実の羅列で終わっている |

各観点は1〜5点で採点し、合格は「すべての観点が4点以上」とします。平均点ではなく最低点で判定するのには理由があります。平均にすると、構成が5点で根拠が2点のレポートでも合格しかねないからです。調査レポートで根拠が弱いのは致命的なので、1つでも基準を下回る観点があれば修正に回します。

もう1つ大事な設計判断があります。それは、合否の判定をLLMに言わせず、コードで計算することです。レビュアーには観点ごとの点数と指摘だけを返してもらい、「全観点が4点以上か」はPythonで判定します。LLMに「合格ですか」と聞くと、点数と合否が食い違う回答がまれに返ってくるためです。数値の比較のように機械的に決まることは、機械に任せるのが確実です。

> **POINT: 基準は「観点」と「段階の説明」をセットで渡す**
> 「網羅性を5段階で評価して」とだけ頼むと、何点が何を意味するかはモデル任せになります。5点の状態と2点以下の状態を文章で添えるだけで、採点のぶれは大きく減ります。ルーブリックは、評価者への指示書だと考えてください。

### コスト上限 ── 「いくらまで使ってよいか」を最初に決める

マルチエージェントは、単一エージェントより多くのトークンを消費します。第8章のコラムで見たとおり、エージェントが増えるほど、同じ情報を何度も読み込むことになるからです。そのため、本章のシステムでは「1回の実行でいくらまで使ってよいか」を最初に決め、実行中に監視します。

既定の上限は1回あたり1.0ドルとし、CLIの `--budget` オプションで変更できるようにします。上限に近づいたら、オーケストレーターは新しい仕事を委譲せず、その時点で最もよい下書きを最終版として出力します。途中で止まっても、何も出力されないよりは、品質メモ付きの下書きが残るほうが役に立つからです。

予算の監視には、第4章で作った `llm_client.tracker`（`CostTracker` のインスタンス）を使います。`call_messages()` を呼ぶたびに、レスポンスの `usage` から料金が計算され、累計に加算される仕組みでした。本章では、実行開始時点の累計を覚えておき、「今の累計 − 開始時点の累計」をこの実行で使った金額とみなします。Web検索の料金はトークンとは別建てなので、こちらは自前で加算します。

ここで、上限の性質について正直に書いておきます。本章の予算管理は、「仕事を委譲する直前」に残額を確認する方式です。そのため、オーケストレーター自身の1ターン分など、数セント程度の超過は起こり得ます。1回の呼び出しの途中で通信を切るような厳密な上限は、第11章の運用編で扱います。まずは、仕事の単位で止められる仕組みを作ることが、実用上はもっとも効果的です。

### 役割分担とモデル割り当て

続いて、4つのエージェントの役割と、それぞれに割り当てるモデルを決めます。第2章で学んだとおり、Claude には性能と料金の異なる複数のモデルがあります。すべてを高性能なモデルにすれば品質は安定しますが、料金も最大になります。役割ごとに「どの程度の賢さが必要か」を考えて割り当てるのが、マルチエージェント設計の腕の見せどころです。

| 役割 | 主な仕事 | モデル | 理由 |
|---|---|---|---|
| オーケストレーター | 計画、委譲、完了判断 | `claude-opus-5-5` | 呼び出し回数は少ないが、判断の質が全体を左右する |
| リサーチャー | 問いごとの調査と出典付きメモ | `claude-haiku-5-5` | 件数が多く並列で動く。検索と要約は軽いモデルで十分 |
| ライター | メモからレポートを執筆 | `claude-sonnet-5-5` | 文章の質と料金のバランスがよい |
| レビュアー | ルーブリック採点と修正指示 | `claude-sonnet-5-5` | ライターと同等以上の目で評価する必要がある |

リサーチャーに軽いモデルを使うのは、問いの数だけ並列で呼び出されるからです。問いが5つあれば5倍、修正で追加調査をすればさらに増えます。1件あたりの単価を下げる効果が、ここでは最も大きく効きます。オーケストレーターは逆に、呼び出し回数は少ないものの、誤った判断をすると後続のすべてが無駄になります。だから本書で使う3つの中でもっとも高性能な Opus 5.5 を使います。

レビュアーのモデルは、ライターと同じかそれ以上にするのが原則です。自分より文章力の低い人に添削を頼んでも、的確な指摘は期待しにくいのと同じです。予算に余裕があれば、レビュアーを Opus 5.5 にすると、指摘はより厳しく具体的になります。逆に、レビュアーを Haiku にして料金を下げる設計もあり得ますが、その場合は合格基準を甘めに感じることがあると覚えておいてください。

> **NOTE**: モデルIDは本書執筆時点（2026年11月）のものです。モデルの世代が変わったら、`report_agent/__init__.py` の定数を書き換えるだけで全体に反映されるように作ります。モデル名をコードのあちこちに直接書かないことが、長く使えるシステムの条件です。

[FIG_10_2｜構造図｜可｜4つのエージェントとモデル割り当て｜指揮役Opusの下にHaiku・Sonnet・Sonnet]

### データの流れと共有ストア workspace/

役割が決まったら、エージェントの間で何を受け渡すかを決めます。ここで重要なのは、エージェント同士が会話履歴を共有しないことです。第1章で学んだとおり、Messages API はステートレス（状態を持たない）でした。リサーチャーが調べた内容は、そのままではライターに伝わりません。誰かが明示的に渡す必要があります。

受け渡しの方法は、大きく2つ考えられます。1つは、オーケストレーターが結果の文字列を受け取り、次のエージェントへの指示に貼り付けて渡す方法です。もう1つは、共有のファイル置き場に結果を保存し、次のエージェントがそこから読む方法です。本章では、後者の「共有ストア」方式を採用します。

共有ストア方式を選ぶ理由は3つあります。1つ目は、オーケストレーターのコンテキストを節約できることです。調査メモ5本の全文をオーケストレーターの履歴に積むと、判断に必要のない文字で入力トークンが膨らみます。オーケストレーターには「q1のメモを保存しました（1,240字）」という短い報告だけを返し、本文はファイルに置いておけば済みます。

2つ目は、途中経過が人間にも見えることです。ファイルとして残っていれば、レポートの品質に不満があったとき、どの段階に原因があるかを後から確かめられます。調査メモが薄いのか、執筆で情報が落ちたのか、レビューが甘いのか。原因の切り分けができることは、改善を続けるうえで欠かせません。

3つ目は、第6章で作った安全なファイル操作の仕組みをそのまま使えることです。`tools/files.py` の `safe_path()` は、渡されたパスが `workspace/` の外を指していないかを確認する関数でした。共有ストアを `workspace/` の下に置けば、エージェントの出力が意図しない場所に書き込まれる心配がありません。

共有ストアの中身は、1回の実行ごとに `workspace/runs/<実行ID>/` というフォルダにまとめます。実行IDは日時から作ります。

```text
# workspace/runs/<実行ID>/ の構成（1回の実行の成果物）
workspace/
├── sources/                      # ローカル検索版が読む資料（自分で置く）
│   ├── agent_cost_basics.md
│   └── model_selection.md
└── runs/
    └── 20261106-153012/          # 実行ID（日時）ごとのフォルダ
        ├── plan.json             # オーケストレーターの調査計画
        ├── notes/
        │   ├── q1.md             # リサーチャーの出典付きメモ（問いごと）
        │   └── q2.md
        ├── drafts/
        │   ├── draft_v1.md       # ライターの下書き（版ごと）
        │   └── draft_v2.md
        ├── reviews/
        │   ├── review_v1.json    # レビュアーの採点と指摘（版ごと）
        │   └── review_v2.json
        ├── report.md             # 最終レポート
        └── cost.json             # 役割別のコスト内訳
```

実行ごとにフォルダを分けるのは、前回の成果物と混ざらないようにするためです。同じテーマで2回実行して結果を比べたいときにも、フォルダごとに残っていれば簡単に見比べられます。下書きとレビューに版番号を付けるのも同じ理由で、修正によって何点から何点に改善したかを追えるようにしています。

[FIG_10_3｜概念図｜可｜共有ストアを介したデータの流れ｜各エージェントがworkspace経由で受け渡し]

> **WARNING**: `workspace/` には調査メモやレポートが溜まっていきます。社外秘の資料を `sources/` に置いた場合、その内容がメモやレポートにも転記されます。第2章で `.env` を `.gitignore` に入れたのと同じように、`workspace/` もGitの管理対象から外しておきましょう。

### ディレクトリ構成

最後に、ソースコードの置き場所を決めます。本章で追加するのは、`report_agent/` というパッケージと、`tests/` フォルダのテストファイルです。

```text
# agent-from-scratch/ に本章で追加するファイル
agent-from-scratch/
├── llm_client.py          # 第4章 → 本章でテスト用フック set_transport() を追加
├── agent.py               # 第8章の Agent クラス（そのまま使う）
├── tool_registry.py       # 第6章の ToolRegistry（そのまま使う）
├── tools/files.py         # 第6章の safe_path()（そのまま使う）
├── report_agent/          # ★本章で新規作成
│   ├── __init__.py        # モデル割り当て・共有ストア RunWorkspace
│   ├── orchestrator.py    # 計画・委譲・予算管理・最終出力
│   ├── researcher.py      # 調査（ローカル検索版／Web検索版）
│   ├── writer.py          # 執筆
│   ├── reviewer.py        # ルーブリック評価
│   └── cli.py             # コマンドライン入口
└── tests/
    └── test_report_agent.py  # ★本章で新規作成（APIを呼ばないテスト）
```

`report_agent/` をフォルダ（パッケージ）にしたのは、6つのファイルが1つのアプリケーションを構成するからです。これまでのようにプロジェクト直下に `orchestrator.py` や `writer.py` を並べると、第9章の `patterns/` や第11章のファイルと混ざってしまいます。関連するファイルを1つのフォルダにまとめておけば、「このアプリはどこからどこまでか」が一目でわかります。

パッケージの外にある `llm_client.py` や `agent.py` は、`report_agent/` の中から `from llm_client import ...` のように読み込みます。これが動くのは、プロジェクトのルートで `python -m report_agent.cli` を実行するからです。`-m` オプションで実行すると、カレントディレクトリが Python のモジュール検索パスに加わります。この仕組みは10.4節で改めて確認します。

設計はここまでです。入出力、処理の流れ、品質基準、コスト上限、役割とモデル、データの置き場所が決まりました。次の節では、この設計の中心にあるオーケストレーターから実装していきます。

---

## 10.2 オーケストレーターの実装

設計が固まったので、実装に入ります。最初に作るのは、全体の指揮を執るオーケストレーターです。指揮役から書くと、部下に何を頼み何を受け取るかが決まり、各サブエージェントの関数の形が自然に定まります。

この節では、共有ストアの `RunWorkspace`、調査計画を作る `make_plan()`、金額を監視する `Budget`、委譲ツールを持つ `ReportOrchestrator` の順に組み立てます。

### パッケージの土台 ── report_agent/__init__.py

> **STEP 1**: パッケージ用のフォルダを作る
> プロジェクトのルート（`agent-from-scratch/`）で、`report_agent` と `tests` の2つのフォルダを作ります。

```bash
# プロジェクトのルートで実行する（フォルダを2つ作る）
mkdir report_agent tests
```

> **STEP 2**: `report_agent/__init__.py` を新規作成する
> パッケージ全体で共有する定数と、共有ストアのクラスをここに置きます。

```python
# report_agent/__init__.py（新規作成）
"""調査レポート自動作成マルチエージェント（第10章）"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from llm_client import FAST_MODEL, MODEL  # 第4章で定義したモデル定数
from tools.files import safe_path          # 第6章: workspace/ の外に出ないパス解決

# --- 役割ごとのモデル割り当て（ここを書き換えれば全体に反映される） ---
ORCHESTRATOR_MODEL = MODEL               # 判断の要: claude-opus-5-5
RESEARCHER_MODEL = FAST_MODEL            # 件数が多い調査: claude-haiku-5-5
WRITER_MODEL = "claude-sonnet-5-5"       # 文章の質と料金のバランス
REVIEWER_MODEL = "claude-sonnet-5-5"     # ライターと同等以上の目で評価する

# --- Web検索サーバーツールの料金（$10 / 1,000回。トークン料金とは別） ---
WEB_SEARCH_USD = 10 / 1000


class RunWorkspace:
    """1回の実行の成果物を workspace/runs/<実行ID>/ にまとめる共有ストア"""

    def __init__(self, run_id: str | None = None) -> None:
        # 実行IDを省略したら、日時から作る（例: 20261106-153012）
        self.run_id = run_id or datetime.now().strftime("%Y%m%d-%H%M%S")
        self.root = safe_path(f"runs/{self.run_id}")
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, rel: str) -> Path:
        # 実行フォルダからの相対パスを、安全な絶対パスに変える
        target = safe_path(f"runs/{self.run_id}/{rel}")
        target.parent.mkdir(parents=True, exist_ok=True)  # notes/ などを自動作成
        return target

    def exists(self, rel: str) -> bool:
        return self.path(rel).exists()

    def write_text(self, rel: str, text: str) -> Path:
        target = self.path(rel)
        target.write_text(text, encoding="utf-8")  # Windowsでも文字化けしないよう明示
        return target

    def read_text(self, rel: str) -> str:
        return self.path(rel).read_text(encoding="utf-8")

    def write_json(self, rel: str, data: dict) -> Path:
        # 日本語をそのまま読めるよう ensure_ascii=False、人が読めるよう indent=2
        return self.write_text(rel, json.dumps(data, ensure_ascii=False, indent=2))
```

冒頭の2つの `import` で、第4章の `llm_client.py` と第6章の `tools/files.py` を読み込んでいます。新しいパッケージでも、通信や安全なパス解決を作り直す必要はありません。モデル割り当ての4行は、10.1節の表をそのまま定数にしたものです。モデルを変えたいときは、ここだけを書き換えれば済みます。

`WEB_SEARCH_USD` は、Web検索1回あたりの料金です。トークン料金とは別に課金されるため、`llm_client.tracker` には計上されません。10.3節のWeb検索版で回数を数え、自前で加算します。

`RunWorkspace` は、すべてのパスを `safe_path()` に通しています。モデルが出したIDがファイル名に混ざっても、`../` で `workspace/` の外へは出られません。また `path()` は親フォルダを自動で作るので、呼び出し側はフォルダの有無を気にせずに書き込めます。

> **NOTE**: `encoding="utf-8"` を省略すると、Windows では既定の文字コード（多くの環境でcp932）が使われます。日本語のメモで `UnicodeEncodeError` が出る原因になるため、本章ではすべて明示しています。

### 調査計画を構造化出力で作る

オーケストレーターの最初の仕事は、テーマを調査可能な問いに分解することです。この計画は後のコードが機械的に読みます。問いのIDでメモのファイル名を決め、見出し案をライターに渡すからです。そこで、第6章の構造化出力（`output_config.format`）で、決まった形のJSONとして受け取ります。

`report_agent/orchestrator.py` を新規作成します。長いファイルなので、ブロックに分けて示します。上から順に書き足してください。

```python
# report_agent/orchestrator.py（新規作成: ブロック1 / 読み込みと調査計画）
"""オーケストレーター: 計画・委譲・予算管理・最終出力を担当する"""
from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from pathlib import Path

import llm_client                            # tracker は llm_client.tracker で読む（第8章）
from agent import Agent                      # 第8章の Agent クラス（async_handlers 付き）
from llm_client import aclose_client, call_messages, extract_text
from tool_registry import ToolRegistry       # 第6章のツール登録の仕組み

from report_agent import ORCHESTRATOR_MODEL, WEB_SEARCH_USD, RunWorkspace
from report_agent.researcher import research_many
from report_agent.reviewer import RUBRIC, review_draft
from report_agent.writer import write_draft

logger = logging.getLogger("report_agent.orchestrator")

# --- 調査計画を作るときの system プロンプト ---
PLANNER_SYSTEM = """あなたは調査レポートの企画担当です。
与えられたテーマを、調べれば答えが出る具体的な「問い」に分解し、レポートの見出し案を作ります。
- 問いは互いに重複させず、1つの問いで1つのことだけを尋ねる
- 問いの id は q1, q2, ... の連番にする
- why には、その問いがレポートの結論にどう役立つかを1文で書く
- 見出し案は「結論」から始め、「次のアクション」で終える
- 想定読者は、テーマに詳しくない実務担当者とする"""

# --- 調査計画のJSONスキーマ（構造化出力で、この形のJSONだけを返させる） ---
PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},          # レポートの題名
        "audience": {"type": "string"},       # 想定読者
        "questions": {                        # 調べる問いの一覧
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "question": {"type": "string"},
                    "why": {"type": "string"},
                },
                "required": ["id", "question", "why"],
                "additionalProperties": False,
            },
        },
        "outline": {"type": "array", "items": {"type": "string"}},  # 見出し案
    },
    "required": ["title", "audience", "questions", "outline"],
    "additionalProperties": False,
}


def make_plan(theme: str, *, max_questions: int = 5) -> dict:
    """テーマから調査計画（問いと見出し案）を構造化出力で作る"""
    response = call_messages(
        [{"role": "user", "content": f"テーマ: {theme}\n問いは最大{max_questions}個にしてください。"}],
        system=PLANNER_SYSTEM,
        model=ORCHESTRATOR_MODEL,
        max_tokens=8000,
        output_config={
            "effort": "low",  # 分解は難しくないので思考は浅めで十分
            "format": {"type": "json_schema", "schema": PLAN_SCHEMA},
        },
    )
    # 本文を読む前に、必ず stop_reason を確認する
    if response["stop_reason"] != "end_turn":
        raise RuntimeError(f"調査計画を作れませんでした: stop_reason={response['stop_reason']}")

    plan = json.loads(extract_text(response))
    # スキーマでは個数を縛れないので、上限はコードで守る
    plan["questions"] = plan["questions"][:max_questions]
    if not plan["questions"]:
        raise RuntimeError("調査計画に問いが1つもありません。テーマを具体的にしてください")
    return plan
```

`researcher`・`reviewer`・`writer` はまだありませんが、ここで呼び方を先に決めます。10.3節では、この呼び方に合わせて各モジュールを実装します。`tracker` を `from llm_client import tracker` ではなく `import llm_client` 経由で読むのは、第8章で注意したとおり、集計をリセットしたときに古いインスタンスを指したままになるのを避けるためです。

`PLANNER_SYSTEM` の各ルールには狙いがあります。「1つの問いで1つのこと」はリサーチャーの焦点を絞るため、「id は連番」はファイル名に使うためです。`why` を書かせるのは、リサーチャーに調査の目的を伝えるためです。

`output_config` には `effort` と `format` を同時に指定しています。テーマの分解は深い推論を要しないので、`effort` は `"low"` にしました。`stop_reason` が `end_turn` 以外ならJSONが途中で切れている恐れがあるので、`json.loads()` の前に明確なメッセージで止めます。問いの数を `[:max_questions]` で切り詰めるのは、問いの数がそのまま調査件数、つまりコストになるからです。

> **POINT: 「お願い」はプロンプトで、「保証」はコードで**
> プロンプトの制約は、モデルが守ろうと努める目標にすぎません。個数の上限・合否の判定・予算の確認のように、破られると困る約束はコードに置きます。本章ではこの原則を何度も使います。

### 予算を監視する Budget クラス

次に、使った金額を監視する `Budget` クラスを作ります。

```python
# report_agent/orchestrator.py（ブロック2 / 予算の監視）

# --- 1回の委譲にかかる金額の見積もり（実測をもとに調整する） ---
ESTIMATE_USD = {
    "research": 0.02,      # ローカル検索版の調査1問あたり（Haiku）
    "research_web": 0.06,  # Web検索版の調査1問あたり（検索料金と検索結果のトークンを含む）
    "write": 0.15,         # 執筆1回（Sonnet・メモ全文を入力）
    "review": 0.06,        # レビュー1回（Sonnet）
}
RESERVE_USD = 0.05         # オーケストレーター自身の残りターンのために取っておく額


class Budget:
    """1回の実行で使った金額（トークン料金 + Web検索料金）を監視する"""

    def __init__(self, limit_usd: float) -> None:
        self.limit_usd = limit_usd
        self._start_usd = llm_client.tracker.total_usd  # 実行開始時点の累計を覚えておく
        self._search_usd = 0.0                          # Web検索の料金は自前で加算する

    def add_searches(self, count: int) -> None:
        # レスポンスの usage.server_tool_use.web_search_requests の回数を受け取る
        self._search_usd += count * WEB_SEARCH_USD

    def spent(self) -> float:
        return llm_client.tracker.total_usd - self._start_usd + self._search_usd

    def remaining(self) -> float:
        return self.limit_usd - self.spent()

    def can_afford(self, estimate_usd: float) -> bool:
        # 見積もり額 + 予備費を払っても上限を超えないかを判定する
        return self.remaining() >= estimate_usd + RESERVE_USD
```

`ESTIMATE_USD` は委譲1回あたりの見積もりで、筆者が試作で数回実行した `cost.json` の実測値を少し多めに丸めたものです。自分の環境で数回動かしたら、実測に合わせて調整してください。

見積もりを使うのは、残額ゼロまで委譲を続けると最後の1回で大きく超過するからです。残り0.05ドルで執筆（約0.15ドル）を始めれば、0.1ドル近く超えてしまいます。そこで「見積もり額を払えるか」を事前に確かめます。`RESERVE_USD` は、委譲をやめた後にオーケストレーターが最終応答を返す分の予備費です。

`tracker` はモジュール共通なので、同じプロセスで以前に使った料金も累計に含まれます。開始時点の値を差し引くことで、この実行の分だけを取り出しています。並列調査から `add_searches()` が呼ばれても、すべて1つのイベントループ（1スレッド）で動くため、ロックは不要です。

> **NOTE**: 本書では、`CostTracker` が累計金額を `total_usd` 属性に持つ前提で書いています。自分の `llm_client.py` で別名にしている場合は、このクラスの2か所を合わせてください。

### オーケストレーターの指示書と委譲ツールの定義

オーケストレーターに与える system プロンプトと、3つの委譲ツールのスキーマを書きます。

```python
# report_agent/orchestrator.py（ブロック3 / 指示書と委譲ツールのスキーマ）
ORCHESTRATOR_SYSTEM = """あなたは調査レポート作成チームの責任者です。
ツールで部下に仕事を委譲し、品質基準を満たすレポートを完成させます。

## 進め方
1. delegate_research で、調査計画の問いをすべて調べさせる（まとめて1回で依頼してよい）
2. delegate_write で初稿を書かせる
3. delegate_review で採点させる
4. 不合格なら、レビューの指摘を読んで次の一手を選ぶ
   - 根拠や情報が足りない → delegate_research の extra_questions に追加の問いを渡す
   - 構成や表現の問題 → delegate_write の instructions に修正方針を具体的に書く
   修正したら、必ず delegate_review で再採点する
5. 合格した、または BUDGET_EXCEEDED か LIMIT_REACHED が返ったら、委譲をやめて終了する

## ルール
- ツールは1回に1つだけ呼ぶ。同時に複数のツールを呼ばない
- 自分で調査や執筆をしない。必ず部下に委譲する
- ERROR が返ったら、内容を読んで呼び方を直す
- 終了時は、最終版の番号・合否・残った課題を3行以内で報告する"""

# --- 委譲ツール: 名前 → (説明, 入力スキーマ)。実体は async_handlers に登録する ---
DELEGATE_TOOLS = {
    "delegate_research": (
        "リサーチャーに調査を委譲する。question_ids に調査計画の問いの id（例: q1）を渡す。"
        "計画にない問いを追加で調べたいときは extra_questions に問いの文章を渡す。"
        "結果は共有ストアに保存され、ここでは保存結果の要約だけが返る。",
        {"type": "object",
         "properties": {
             "question_ids": {"type": "array", "items": {"type": "string"},
                              "description": "調べる問いの id の一覧"},
             "extra_questions": {"type": "array", "items": {"type": "string"},
                                 "description": "計画に追加して調べる問い（任意）"}},
         "required": ["question_ids"], "additionalProperties": False},
    ),
    "delegate_write": (
        "ライターにレポートの執筆・修正を委譲する。初稿のときは全体方針を、"
        "修正のときはレビュー指摘への対応方針を instructions に具体的に書く。"
        "ライターは調査メモ・直前の下書き・直前のレビュー結果を自動で受け取る。",
        {"type": "object",
         "properties": {"instructions": {"type": "string", "description": "執筆・修正の方針"}},
         "required": ["instructions"], "additionalProperties": False},
    ),
    "delegate_review": (
        "レビュアーに最新の下書きの採点を委譲する。5観点を1〜5点で採点し、"
        "合否・観点別の点数・修正指示・追加調査が必要な点を返す。",
        {"type": "object", "properties": {}, "additionalProperties": False},
    ),
}


def _sync_stub(**_: object) -> str:
    # スキーマ登録用の仮の関数。実体は arun() から async_handlers 経由で呼ばれる
    raise RuntimeError("委譲ツールは Agent.arun() から非同期で実行してください")
```

「進め方」は、10.1節で人間のチームの手順として書き出したものをそのまま転用しています。核心は手順4です。追加調査か書き直しかは、レビューの自然文を読まないと選べません。だからLLMに任せ、判断基準を言葉で添えます。

「ツールは1回に1つだけ」にも理由があります。第8章の `arun()` は、1ターンの複数の `tool_use` を `asyncio.gather()` で同時に実行します。執筆とレビューを同時に呼ばれると、まだない下書きを採点してしまいます。「自分で執筆しない」は、高価な Opus で長文を書かせないためのルールでもあります。

委譲ツールは、第8章と同じく「スキーマは registry、実体は async_handlers」の形で登録します。`DELEGATE_TOOLS` はスキーマ側の定義です。説明文に「要約だけが返る」「ライターは材料を自動で受け取る」と書いたのは、オーケストレーターが本文見たさに同じ調査を繰り返したり、指摘を `instructions` に書き写したりするのを防ぐためです。`delegate_review` に引数がないのは、採点対象が常に最新版だからです。モデルに選ばせなくてよいことは、選ばせないのが原則です。

### クラスの骨格と _guarded()

```python
# report_agent/orchestrator.py（ブロック4 / クラスの初期化と委譲の入口）
class ReportOrchestrator:
    """調査→執筆→レビュー→修正を指揮し、最終レポートを出力する"""

    def __init__(
        self,
        theme: str,
        *,
        budget_usd: float = 1.0,
        source: str = "local",        # "local"（ローカル資料）または "web"（Web検索）
        max_rounds: int = 2,          # 初稿の後に許す修正回数
        max_questions: int = 5,
        concurrency: int = 3,         # 同時に走らせるリサーチャーの上限
        workspace: RunWorkspace | None = None,
    ) -> None:
        self.theme = theme
        self.budget = Budget(budget_usd)
        self.source = source
        self.max_rounds = max_rounds
        self.max_questions = max_questions
        self.concurrency = concurrency
        self.ws = workspace or RunWorkspace()
        self.plan: dict | None = None
        self.draft_version = 0                    # 0 = まだ下書きがない
        self.reviews: dict[int, dict] = {}        # 版番号 → レビュー結果
        self.cost_by_role: dict[str, float] = {}  # 役割ごとの使用額
        self._delegate_lock: asyncio.Lock | None = None  # arun() の中で作る

    def _build_agent(self) -> Agent:
        registry = ToolRegistry()
        for name, (description, schema) in DELEGATE_TOOLS.items():
            registry.tool(name=name, description=description, input_schema=schema)(_sync_stub)
        return Agent(
            name="orchestrator", system=ORCHESTRATOR_SYSTEM, registry=registry,
            model=ORCHESTRATOR_MODEL,
            effort="medium",   # 委譲の判断には中程度の思考を使う
            max_turns=12,      # 調査1 + (執筆+レビュー) × 3 + 追加調査 + 余裕
            async_handlers={
                "delegate_research": self.delegate_research,
                "delegate_write": self.delegate_write,
                "delegate_review": self.delegate_review,
            },
        )

    # --- async_handlers の実体（引数名はスキーマのプロパティ名と一致させる） ---
    async def delegate_research(self, question_ids: list[str],
                                extra_questions: list[str] | None = None) -> str:
        extra = extra_questions or []
        per_question = ESTIMATE_USD["research_web" if self.source == "web" else "research"]
        estimate = per_question * (len(question_ids) + len(extra))
        return await self._guarded("research", estimate, self._research, question_ids, extra)

    async def delegate_write(self, instructions: str) -> str:
        return await self._guarded("write", ESTIMATE_USD["write"], self._write, instructions)

    async def delegate_review(self) -> str:
        return await self._guarded("review", ESTIMATE_USD["review"], self._review)

    async def _guarded(self, role: str, estimate_usd: float,
                       func: Callable[..., Awaitable[str]], *args) -> str:
        """委譲を1つずつ実行し、事前に予算を確認し、使った金額を役割別に記録する"""
        async with self._delegate_lock:  # 同時に呼ばれても、ここで1つずつに並べる
            if not self.budget.can_afford(estimate_usd):
                logger.warning("予算不足のため %s を見送り（残り $%.3f）", role, self.budget.remaining())
                return (f"BUDGET_EXCEEDED: 残り予算 ${self.budget.remaining():.3f} では "
                        f"{role}（見積もり ${estimate_usd:.3f}）を実行できません。"
                        "委譲をやめて終了してください。")
            logger.info("%s を開始（見積もり $%.3f / 残り $%.3f）",
                        role, estimate_usd, self.budget.remaining())
            before = self.budget.spent()
            try:
                return await func(*args)
            finally:
                # 成功しても失敗しても、使った金額は記録する
                used = self.budget.spent() - before
                self.cost_by_role[role] = self.cost_by_role.get(role, 0.0) + used
```

`max_rounds` は初稿の後に許す修正回数で、既定の2なら最大3版まで作ります。予算と回数の二重の上限で、評価者-最適化者ループが終わらない事態を防ぎます。`draft_version` や `reviews` のように正確さが必要な状態は、LLMではなくPython側で持ちます。

`_build_agent()` では、`DELEGATE_TOOLS` のスキーマを `registry` に登録し、実体のメソッドを `async_handlers` に渡しています。`registry.tool(...)(_sync_stub)` は、第6章で紹介したデコレーターを関数呼び出しで使う書き方です。`delegate_research()` などの引数名は、スキーマのプロパティ名と一致させてください。`arun()` は `tool_input` をキーワード引数として渡すからです。

`_guarded()` には3つの役割があります。1つ目は委譲の直列化です。`asyncio.Lock` があれば、同じターンに2つの委譲が出ても2つ目は1つ目の完了を待ちます。プロンプトの「1つずつ」をコードで保証しているわけです。ロックを `__init__()` ではなく後で作るのは、イベントループの中で作るのが安全だからです。

2つ目は予算の事前確認です。払えないときは例外を投げず、`BUDGET_EXCEEDED:` で始まる文字列を返します。予算切れはエラーではなく、次の行動を決めるための情報だからです。「委譲をやめて終了してください」と、期待する行動まで書くとモデルは迷いません。

3つ目は役割別のコスト記録です。委譲は1つずつ実行されるので、前後の差分に他の委譲の料金は混ざりません。`finally` に書いたので、失敗した処理の料金も記録されます。

> **WARNING: ロックの中で他の委譲を呼ばない**
> `asyncio.Lock` は再入できません。`_research()` などの中から `_guarded()` を呼ぶと、自分自身の解放を永遠に待つことになります（デッドロック）。

### 3つの委譲の本体

各委譲では、10.3節のサブエージェントを呼び、結果を共有ストアに保存し、オーケストレーターには短い報告だけを返します。ブロック5と6は `ReportOrchestrator` クラスのメソッドの続きなので、ブロック4の末尾に、クラスの中のインデント（空白4つ）のまま書き足してください。

```python
# report_agent/orchestrator.py（ブロック5 / 各委譲の本体。ReportOrchestrator クラス内の続き）
    async def _research(self, question_ids: list[str], extra_questions: list[str]) -> str:
        known = {q["id"]: q for q in self.plan["questions"]}
        unknown = [qid for qid in question_ids if qid not in known]
        if unknown:  # 存在しないIDは、モデルが直せるようにエラーとして返す
            return f"ERROR: 計画にない id です: {unknown}。計画の id か extra_questions を使ってください。"

        targets = [known[qid] for qid in question_ids]
        for text in extra_questions:  # 追加の問いは、新しいIDを振って計画に加える
            question = {"id": f"q{len(self.plan['questions']) + 1}", "question": text,
                        "why": "レビューの指摘を受けた追加調査"}
            self.plan["questions"].append(question)
            targets.append(question)
        self.ws.write_json("plan.json", self.plan)  # 計画の変更も記録に残す

        notes = await research_many(targets, theme=self.theme, source=self.source,
                                    budget=self.budget, concurrency=self.concurrency)
        lines = []
        for q in targets:
            memo = notes.get(q["id"])
            if memo is None:
                lines.append(f"- {q['id']}: 失敗（メモなし。もう一度依頼してよい）")
                continue
            self.ws.write_text(f"notes/{q['id']}.md", memo)
            lines.append(f"- {q['id']}: notes/{q['id']}.md に保存（{len(memo):,}字）")
        return "調査結果:\n" + "\n".join(lines)

    async def _write(self, instructions: str) -> str:
        if self.draft_version > self.max_rounds:  # 初稿 + 修正 max_rounds 回まで
            return "LIMIT_REACHED: 修正回数の上限に達しました。委譲をやめて終了してください。"
        notes = self._load_notes()
        if not notes:
            return "ERROR: 調査メモがありません。先に delegate_research を呼んでください。"

        draft = await write_draft(
            self.theme, self.plan, notes,
            instructions=instructions,
            previous_draft=self._latest_draft(),             # 初稿のときは None
            review=self.reviews.get(self.draft_version),     # 直前の版のレビュー（なければ None）
        )
        self.draft_version += 1
        self.ws.write_text(f"drafts/draft_v{self.draft_version}.md", draft)
        return (f"drafts/draft_v{self.draft_version}.md に保存（{len(draft):,}字）。"
                "delegate_review で採点してください。")

    async def _review(self) -> str:
        draft = self._latest_draft()
        if draft is None:
            return "ERROR: 下書きがありません。先に delegate_write を呼んでください。"
        if self.draft_version in self.reviews:  # 同じ版を二度採点させない（料金の無駄）
            return "この版は採点済みです:\n" + self._format_review(self.reviews[self.draft_version])

        review = await review_draft(draft, self.plan, self._load_notes())
        self.reviews[self.draft_version] = review
        self.ws.write_json(f"reviews/review_v{self.draft_version}.json", review)
        return self._format_review(review)
```

`_research()` は、まずIDが計画に存在するかを確かめます。モデルが存在しない `q6` を指定することは実際にあります。そのときは `ERROR:` で、何が悪くどう直すかを返します。追加の問いには新しいIDを振り、`plan.json` も書き直して、どれが追加調査かを後から追えるようにします。

オーケストレーターへの返り値は、メモの本文ではなく保存先と文字数だけです。5問分のメモは数千字になりますが、報告なら数行で済みます。「そろったから執筆へ」と判断するには、これで十分です。

`_write()` には、メモに加えて直前の下書きとそのレビューを渡します。初稿のときはどちらも `None` なので、ライターは新規執筆か修正かを判断できます。`_review()` は同じ版の再採点を断り、前回の結果を料金なしで返します。

### 補助メソッドと実行の入口

```python
# report_agent/orchestrator.py（ブロック6 / 補助メソッド・実行の入口・最終出力。ReportOrchestrator クラス内の続き）
    def _load_notes(self) -> dict[str, str]:
        """保存済みの調査メモを「ID → 本文」の辞書で返す（計画の順番どおり）"""
        notes = {}
        for q in self.plan["questions"]:
            rel = f"notes/{q['id']}.md"
            if self.ws.exists(rel):
                notes[q["id"]] = self.ws.read_text(rel)
        return notes

    def _latest_draft(self) -> str | None:
        if self.draft_version == 0:
            return None
        return self.ws.read_text(f"drafts/draft_v{self.draft_version}.md")

    def _format_review(self, review: dict) -> str:
        """オーケストレーターが次の一手を決めるのに必要な部分だけを渡す"""
        brief = {
            "version": self.draft_version,
            "passed": review["passed"],
            "scores": review["scores"],
            "issues": review["issues"][:5],            # 指摘は重要な順に最大5件
            "needs_research": review["needs_research"],
            "remaining_budget_usd": round(self.budget.remaining(), 3),
            "remaining_rounds": max(0, self.max_rounds - (self.draft_version - 1)),
        }
        return json.dumps(brief, ensure_ascii=False, indent=2)

    def run(self) -> Path:
        """計画 → オーケストレーターのループ → 最終出力 を実行し、レポートのパスを返す"""
        logger.info("調査計画を作成中: %s", self.theme)
        before = self.budget.spent()
        self.plan = make_plan(self.theme, max_questions=self.max_questions)
        self.cost_by_role["plan"] = self.budget.spent() - before
        self.ws.write_json("plan.json", self.plan)
        logger.info("調査計画: 問い%d個 / 見出し%d個",
                    len(self.plan["questions"]), len(self.plan["outline"]))
        summary = asyncio.run(self._orchestrate())
        return self._finalize(summary)

    async def _orchestrate(self) -> str:
        self._delegate_lock = asyncio.Lock()
        try:
            return await self._build_agent().arun(self._kickoff_message())
        except Exception:  # 途中で止まっても、できた分は必ず出力する
            logger.exception("オーケストレーターが途中で停止しました。ここまでの成果物で仕上げます")
            return "（オーケストレーターが途中で停止しました）"
        finally:
            await aclose_client()  # 第8章: ループを閉じる前に非同期クライアントを閉じる

    def _kickoff_message(self) -> str:
        questions = "\n".join(f"- {q['id']}: {q['question']}" for q in self.plan["questions"])
        outline = "\n".join(f"- {h}" for h in self.plan["outline"])
        return (
            f"テーマ: {self.theme}\nレポート題: {self.plan['title']}\n想定読者: {self.plan['audience']}\n\n"
            f"調査計画の問い:\n{questions}\n\n見出し案:\n{outline}\n\n"
            f"予算: ${self.budget.limit_usd:.2f}（残り ${self.budget.remaining():.2f}）"
            f" / 初稿の後の修正は最大{self.max_rounds}回"
        )

    def _finalize(self, summary: str) -> Path:
        draft = self._latest_draft()
        if draft is None:
            raise RuntimeError("下書きが1つもできませんでした。ログと予算を確認してください")

        review = self.reviews.get(self.draft_version)
        if review is None:
            verdict = "未採点（採点前に終了）"
        elif review["passed"]:
            verdict = "合格"
        else:
            verdict = "不合格（品質基準を満たす前に終了）"
        scores = ", ".join(f"{RUBRIC[k][0]} {v}" for k, v in review["scores"].items()) if review else "-"

        # オーケストレーター自身の料金 = 全体 − 各委譲の合計
        self.cost_by_role["orchestrator"] = self.budget.spent() - sum(self.cost_by_role.values())
        memo = (
            "## 作成メモ（自動生成）\n\n"
            f"- 判定: {verdict}（v{self.draft_version}）\n"
            f"- 採点: {scores}\n"
            f"- 使用金額: ${self.budget.spent():.3f} / 予算 ${self.budget.limit_usd:.2f}\n"
            f"- 責任者の報告: {summary.strip()}\n"
        )
        path = self.ws.write_text("report.md", draft.rstrip() + "\n\n---\n\n" + memo)
        self.ws.write_json("cost.json", {
            "total_usd": round(self.budget.spent(), 4),
            "limit_usd": self.budget.limit_usd,
            "by_role": {k: round(v, 4) for k, v in self.cost_by_role.items()},
            "draft_versions": self.draft_version,
            "verdict": verdict,
        })
        return path
```

`_format_review()` は、合否・点数・上位5件の指摘に加え、残りの予算と修正回数も渡します。「あと1回しか直せないなら重要な指摘に絞ろう」という判断ができるようにするためです。判断する人に、判断に必要な情報だけを渡す。これは人間の組織でもエージェントの組織でも同じです。

`run()` では、計画作成を固定の手順として、同期の `call_messages()` で先に済ませます。1回で終わる処理にツールループは要りません。その後、`asyncio.run()` でオーケストレーターの `arun()` を動かします。`_orchestrate()` の `finally` で `aclose_client()` を呼ぶのは、第8章の「Event loop is closed」を防ぐためです。

`arun()` を `try` で囲むのは、ネットワーク障害などで止まっても、使った料金に見合う成果物を残すためです。一方、`make_plan()` は `try` の外に置きました。計画で失敗するのはAPIキーの誤りなどがほとんどで、救える成果物がないからです。受け止めるか伝えるかは、「その時点で救える成果物があるか」で決めます。

`_finalize()` は、不合格でも最新の下書きを出力し、作成メモで限界を明示します。何も出さないシステムより、限界を示して出すシステムのほうが実務では信頼されます。オーケストレーター自身の料金は直接測れませんが、全体から各委譲の合計を引けば正確に求まります。

これでオーケストレーターは完成です。次の節で、読み込んでいる3つのモジュールを実装します。

---

## 10.3 リサーチャー・ライター・レビュアーの実装

オーケストレーターが部下をどう呼ぶかは決まりました。この節では、その呼び方に合わせて3つのサブエージェントを実装します。リサーチャーは問いごとに調べて出典付きメモを書き、ライターはメモからレポートを書き、レビュアーはルーブリックで採点します。

### リサーチャー（ローカル資料検索版）

リサーチャーには、2つの調べ方を用意します。まずは、APIキー以外に何も要らず、追加料金もかからないローカル資料検索版です。`workspace/sources/` に置いたMarkdownやテキストを検索します。社内資料や過去の議事録を置けば、そのまま社内調査に使えます。

試すための資料を2つ置いておきましょう。内容は自由ですが、ここでは例を示します。

```markdown
<!-- workspace/sources/agent_cost_basics.md（試用の資料。自由に書き換えてよい） -->
# AIエージェントのコストの基本
- 料金は入力トークンと出力トークンの量で決まり、出力の単価は入力の5倍程度である。
- エージェントは1つの依頼でAPIを何度も呼ぶため、履歴が伸びるほど入力トークンが増える。
- マルチエージェントは同じ情報を複数のエージェントが読むため、単一より総コストが増えやすい。
- 公式ドキュメント: https://platform.claude.com/docs/en/about-claude/pricing
```

```markdown
<!-- workspace/sources/model_selection.md（試用の資料） -->
# モデルの使い分け
- 件数の多い分類・要約・検索は Haiku のような軽いモデルに任せると安い。
- 計画や最終判断のように誤りが全体に響く仕事には、高性能なモデル（本書では Opus 5.5）を使う。
- Console の利用上限（spend limit）を設定し、想定外の請求を防ぐ。
```

続いて、`report_agent/researcher.py` を新規作成します。

```python
# report_agent/researcher.py（新規作成: ブロック1 / 指示書とクライアントツール）
"""リサーチャー: 1つの問いを調べ、出典付きの調査メモ（Markdown）を返す"""
from __future__ import annotations

import asyncio
import html
import logging
import re
from typing import TYPE_CHECKING

import httpx

from agent import Agent
from llm_client import acall_messages
from tool_registry import ToolError, ToolRegistry
from tools.files import safe_path

from report_agent import RESEARCHER_MODEL

if TYPE_CHECKING:  # 型ヒント専用の読み込み（実行時の循環 import を避ける）
    from report_agent.orchestrator import Budget

logger = logging.getLogger("report_agent.researcher")

RESEARCHER_SYSTEM = """あなたは調査担当のリサーチャーです。
与えられた1つの問いについて資料を調べ、出典付きの調査メモを日本語のMarkdownで書きます。
- 冒頭に「## 結論」として、問いへの答えを2〜3文で書く
- 「## 根拠」に事実を箇条書きで並べ、各行の末尾に [出典: ...] を付ける
- 資料で確認できなかったことは「## 未確認」に書き、推測で埋めない
- 全体を1,500字以内にまとめ、メモ本文だけを出力する"""

registry = ToolRegistry()   # リサーチャー用のツール（第11章で保護をかける）


def _bigrams(text: str) -> set[str]:
    """空白と記号を除き、2文字ずつに区切る（日本語でも分かち書き不要）"""
    s = re.sub(r"[\s、。,.!?！？「」()（）・:：/#\-]+", "", text.lower())
    return {s[i:i + 2] for i in range(len(s) - 1)}


@registry.tool(
    name="search_local_docs",
    description=("workspace/sources/ の資料（.md / .txt）を検索し、一致した行を "
                 "[sources/ファイル名:L行番号] 付きで返す。言い方を変えて複数回検索するとよい。"),
    input_schema={"type": "object",
                  "properties": {"query": {"type": "string", "description": "検索したい内容（日本語可）"},
                                 "max_results": {"type": "integer", "description": "最大件数（既定5）"}},
                  "required": ["query"]},
)
def search_local_docs(query: str, max_results: int = 5) -> str:
    root = safe_path("sources")
    if not root.is_dir():
        return "資料フォルダ workspace/sources/ がありません。"
    query_grams = _bigrams(query)
    if not query_grams:
        return "検索語が短すぎます。2文字以上で指定してください。"

    hits: list[tuple[float, str]] = []
    for file in sorted(root.rglob("*")):
        if file.suffix.lower() not in {".md", ".txt"}:
            continue
        lines = file.read_text(encoding="utf-8").splitlines()
        rel = file.relative_to(root.parent).as_posix()          # 例: sources/agent_cost_basics.md
        for i, line in enumerate(lines):
            score = len(query_grams & _bigrams(line)) / len(query_grams)  # 一致した2文字の割合
            if score >= 0.3:
                hits.append((score, f"[{rel}:L{i + 1}] {line.strip()[:300]}"))
    if not hits:
        return f"「{query}」に一致する記述は見つかりませんでした。別の言い方で検索してください。"
    hits.sort(key=lambda h: h[0], reverse=True)               # 一致率の高い順
    return "\n".join(text for _, text in hits[:min(max_results, 8)])


@registry.tool(
    name="fetch_page",
    description="資料に書かれたURLのページ本文をテキストで取得する。http(s) のURLだけを指定する。",
    input_schema={"type": "object",
                  "properties": {"url": {"type": "string", "description": "取得するURL"}},
                  "required": ["url"]},
)
def fetch_page(url: str) -> str:
    if not url.startswith(("https://", "http://")):
        raise ToolError("http(s) で始まるURLを指定してください")  # 想定内の失敗（第6章）
    try:
        response = httpx.get(url, timeout=15.0, follow_redirects=True)
        response.raise_for_status()                              # 404 なども例外にする
    except httpx.HTTPError as exc:                               # → is_error 付きで理由を返す
        raise ToolError(f"ページを取得できませんでした: {exc}") from exc
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", response.text)  # スクリプトとCSSを除く
    text = re.sub(r"(?s)<[^>]+>", " ", text)                     # 残りのタグを除く
    text = re.sub(r"\s+", " ", html.unescape(text)).strip()
    return f"[{url}]\n{text[:8000]}"                             # 長すぎるページは切り詰める
```

`RESEARCHER_SYSTEM` は、メモの形を見出しのレベルまで指定しています。メモの読み手はライターです。形がそろっていれば、ライターは問いが変わっても同じ読み方ができます。「未確認」の節を設けたのは、資料にないことを推測で埋めるのを防ぐためです。

`search_local_docs()` は、文字の2文字組（バイグラム）の一致率で行を探す、素朴な検索です。日本語は単語の間に空白がないため、空白区切りのキーワード検索では「コスト管理」と「コストの管理」が一致しません。2文字組なら「コス」「スト」が共通するので拾えます。返す行に `[sources/ファイル名:L行番号]` を付けておくと、それがそのまま出典になります。

`fetch_page()` は、資料に載っているURLの本文を確かめるためのツールです。HTMLからスクリプトとタグを除き、8,000字で切り詰めます。URLの誤りや取得の失敗は `ToolError` にしているので、第6章の `run_one_tool()` が理由を `is_error` 付きでモデルへ返します。外部のページは誰が書いたかわからない文章なので、第11章ではこのツールを「信頼できないデータ」として扱う保護をかけます。

`if TYPE_CHECKING:` の読み込みにも触れておきます。`orchestrator.py` は `researcher.py` を読み込み、`researcher.py` は型ヒントに `Budget` を使います。普通に読み込み合うと循環 import でエラーになりますが、`TYPE_CHECKING` の中なら実行時には読み込まれません。

ここで、検索ツールだけを単独で試しておきましょう。ツールはただのPython関数なので、APIを呼ばずに動作を確かめられます。部品を組み合わせる前に1つずつ確かめておくと、全体を動かしたときの原因の切り分けが楽になります。

```bash
# search_local_docs だけを試す（APIは呼ばないので料金はかからない）
uv run python -c "from report_agent.researcher import search_local_docs; print(search_local_docs('コストが増える原因'))"
```

```text
[sources/agent_cost_basics.md:L5] - マルチエージェントは同じ情報を複数のエージェントが読むため、単一より総コストが増えやすい。
[sources/agent_cost_basics.md:L4] - エージェントは1つの依頼でAPIを何度も呼ぶため、履歴が伸びるほど入力トークンが増える。
```

資料の1行目にコメント行を含めて保存した場合の行番号です。「コストが増える原因」と完全に一致する文はありませんが、「コス」「スト」「増え」などの2文字組が一致する行が、一致率の高い順に並びました。何も表示されない場合は、ファイルの保存場所が `workspace/sources/` になっているか、文字コードがUTF-8かを確かめてください。

### リサーチャー（Web検索サーバーツール版）と並列実行

もう1つの調べ方が、Web検索サーバーツール（`web_search_20260209`）を使う版です。サーバーツールは、Anthropic 側で実行されるツールです。自分で検索を実装する必要はありませんが、**トークン料金とは別に、検索1,000回あたり10ドルの料金がかかります**。また、組織の管理者が Console で無効にしている場合は、400エラーになります。

```python
# report_agent/researcher.py（ブロック2 / Web検索版・ローカル版・並列実行）
WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search", "max_uses": 4}
MAX_CONTINUES = 3   # pause_turn から続きを依頼する上限


def _task(question: dict, theme: str, hint: str) -> str:
    return (f"レポート全体のテーマ: {theme}\n調べる問い（{question['id']}）: {question['question']}\n"
            f"この問いが必要な理由: {question['why']}\n\n{hint}")


async def research_local(question: dict, *, theme: str) -> str:
    agent = Agent(name=f"researcher-{question['id']}", system=RESEARCHER_SYSTEM,
                  registry=registry, model=RESEARCHER_MODEL, max_turns=8)
    hint = "search_local_docs で言い方を変えながら2〜4回検索し、出典は検索結果の [sources/...:L行] をそのまま使ってください。"
    return await agent.arun(_task(question, theme, hint))


async def research_web(question: dict, *, theme: str, budget: Budget) -> str:
    hint = "web_search で調べ、公式情報や一次情報を優先してください。"
    messages = [{"role": "user", "content": _task(question, theme, hint)}]
    blocks: list[dict] = []
    extra: dict | None = None   # 再開時に引き継ぐコード実行のコンテナID
    for _ in range(MAX_CONTINUES + 1):
        response = await acall_messages(messages, system=RESEARCHER_SYSTEM, tools=[WEB_SEARCH_TOOL],
                                        model=RESEARCHER_MODEL, max_tokens=8000, extra=extra)
        # 検索回数はトークンとは別に課金されるので、予算に自分で加える
        budget.add_searches(response["usage"].get("server_tool_use", {}).get("web_search_requests", 0))
        blocks.extend(response["content"])
        if response["stop_reason"] != "pause_turn":
            break
        # 一時停止したら、返ってきた assistant の content をそのまま付けて続きを依頼する
        messages.append({"role": "assistant", "content": response["content"]})
        if response.get("container"):  # 動的フィルタリングのコンテナを、再開でも使い続ける
            extra = {"container": response["container"]["id"]}
    else:
        logger.warning("%s: pause_turn が続いたため打ち切りました", question["id"])
    if response["stop_reason"] == "refusal":
        raise RuntimeError(f"{question['id']}: 調査を断られました")

    memo = "".join(b["text"] for b in blocks if b["type"] == "text")
    sources: dict[str, str] = {}
    for b in blocks:  # 本文の citations から、実際に引用された出典だけを集める
        for c in b.get("citations") or []:
            if c.get("type") == "web_search_result_location":
                sources.setdefault(c["url"], c.get("title") or c["url"])
    if sources:
        memo += "\n\n## 出典一覧（citations から自動生成）\n" + "\n".join(
            f"- [{title}]({url})" for url, title in sources.items())
    return memo


async def research_many(questions: list[dict], *, theme: str, source: str,
                        budget: Budget, concurrency: int = 3) -> dict[str, str]:
    """問いを並列に調べ、「ID → メモ」を返す。失敗した問いは含めない"""
    semaphore = asyncio.Semaphore(concurrency)   # 同時に走るリサーチャーは最大 concurrency 本

    async def one(q: dict) -> str:
        async with semaphore:
            if source == "web":
                memo = await research_web(q, theme=theme, budget=budget)
            else:
                memo = await research_local(q, theme=theme)
        if "## 結論" not in memo:  # 形式の確認はコードで行う
            raise ValueError(f"メモの形式が不正です: {memo[:80]}")
        return memo

    results = await asyncio.gather(*(one(q) for q in questions), return_exceptions=True)
    notes: dict[str, str] = {}
    for q, result in zip(questions, results):
        if isinstance(result, BaseException):
            logger.error("%s の調査に失敗: %s", q["id"], result)
        else:
            notes[q["id"]] = result
    return notes
```

`research_local()` は、第8章の `Agent` をそのまま使います。名前に問いのIDを入れておくと、並列で動く複数のリサーチャーのログを見分けられます。`registry` はモジュールで1つだけ作り、すべてのリサーチャーで共有します。ツールの関数は状態を持たないので、共有しても問題ありません。`max_turns=8` は、検索を4回ほど行い、ページを1〜2回取得して、メモを書くまでに十分なターン数です。`hint` で「言い方を変えて複数回検索する」と促しているのは、素朴な検索なので、1回の検索語で見つからないことが多いからです。

`research_web()` の中心は、`pause_turn` の扱いです。サーバーツールは、検索と推論をAPIの中で何度か繰り返します。それが長引くと、APIは途中で `stop_reason: "pause_turn"` を返して一時停止します。公式ドキュメントの指示どおり、返ってきた assistant の `content` を変更せずに履歴の末尾へ付けて、もう一度送ると続きが再開されます。これは自分で書いた文章を差し込む prefill とは別物で、APIが返したブロックを返却する操作です。

`web_search_20260209` は、検索結果をコードで絞り込んでから読む「動的フィルタリング」に対応した版です。そのため、レスポンスにはコード実行のブロックも混ざることがあります。どのブロックも削らずにそのまま返すのが、続きを正しく再開する条件です。レスポンスに `container` が含まれていたら、その `id` も次のリクエストの `container` に入れて送ります。省くと新しいコンテナで実行され、それまでの途中経過が失われるからです。コードの `extra` は、第4章で `call_messages()` に用意した追加フィールドの受け口です。

出典は、本文の `text` ブロックに付く `citations` から集めます。Web検索では引用が常に有効で、`url`・`title`・`cited_text` が入ります。モデルが本文に書いたURLではなく、APIが付けた引用情報から一覧を作るので、存在しないURLが混ざる心配がありません。

Web検索版のメモは、たとえば次のような形になります。本文の `[出典: ...]` はモデルが書いたもの、末尾の一覧はコードが citations から作ったものです。両者を見比べると、モデルが引用元を正しく書けているかも確かめられます。

```markdown
<!-- workspace/runs/20261106-153012/notes/q2.md（Web検索版の出力例・抜粋） -->
## 結論
費用が膨らむ主な原因は、履歴の肥大化とツール結果の再送です。…

## 出典一覧（citations から自動生成）
- [Pricing - Claude Docs](https://platform.claude.com/docs/en/about-claude/pricing)
```

> **WARNING: Web検索版は料金と結果の扱いに注意**
> `max_uses` は1ターンの検索回数の上限です。ただし動的フィルタリング（コード実行経由）の検索は、`pause_turn` から再開すると前のリクエストの分が数えられません。そのため1回の調査では、最大で `max_uses` ×（`MAX_CONTINUES` + 1）回の検索が起こり得ます。料金の上限は、この積で見積もってください。検索結果は入力トークンとしても課金されます。また、検索結果は第三者が書いたWebページなので、内容をうのみにしない設計が必要です（第11章）。

`research_many()` は、第8章で学んだ `asyncio.Semaphore` と `asyncio.gather()` の組み合わせです。問いが5つでも、同時に走るのは3本までに抑えます。`return_exceptions=True` を付けたので、1つの問いが失敗しても他の問いの結果は失われません。失敗した問いはログに残し、オーケストレーターには「失敗」と報告されます。メモに `## 結論` があるかをコードで確かめ、形の崩れたメモが下流に流れるのも防いでいます。

### ライター ── メモからレポートを書く

`report_agent/writer.py` を新規作成します。

```python
# report_agent/writer.py（新規作成）
"""ライター: 調査メモからMarkdownのレポートを書く（修正時は前の版とレビューも読む）"""
from __future__ import annotations

import json
import logging

from llm_client import acall_messages, extract_text

from report_agent import WRITER_MODEL

logger = logging.getLogger("report_agent.writer")

WRITER_SYSTEM = """あなたは調査レポートのライターです。
調査メモだけを根拠に、日本語のMarkdownでレポートを書きます。
- 1行目は「# 」で始まるレポート題にする
- 最初の節は「## 結論」とし、読者が最初の数行で要点をつかめるようにする
- 事実を述べる文には、メモにある出典を [出典: ...] の形でそのまま付ける
- メモにないことは書かない。足りない情報は「## 今後の確認事項」に書く
- 最後の節は「## 次のアクション」とし、読者がすぐ取れる行動を3つ挙げる
- 全体で3,000〜6,000字にする。出力はレポート本文のみとする"""


async def write_draft(theme: str, plan: dict, notes: dict[str, str], *, instructions: str,
                      previous_draft: str | None = None, review: dict | None = None) -> str:
    parts = [f"テーマ: {theme}", f"レポート題: {plan['title']}", f"想定読者: {plan['audience']}",
             "見出し案:\n" + "\n".join(f"- {h}" for h in plan["outline"])]
    for qid, memo in notes.items():          # メモはタグで囲み、境界をはっきりさせる
        parts.append(f'<note id="{qid}">\n{memo}\n</note>')
    if previous_draft:                       # 修正のときだけ、前の版とレビューを渡す
        parts.append(f"<previous_draft>\n{previous_draft}\n</previous_draft>")
    if review:
        feedback = {"scores": review["scores"], "issues": review["issues"]}
        parts.append(f"<review>\n{json.dumps(feedback, ensure_ascii=False, indent=2)}\n</review>")
    parts.append(f"今回の指示: {instructions}")

    response = await acall_messages([{"role": "user", "content": "\n\n".join(parts)}],
                                    system=WRITER_SYSTEM, model=WRITER_MODEL, max_tokens=16000)
    if response["stop_reason"] == "refusal":
        raise RuntimeError("執筆を断られました")
    if response["stop_reason"] == "max_tokens":
        logger.warning("下書きが max_tokens で途中終了しました")
    draft = extract_text(response).strip()
    if not draft.startswith("# "):           # 題の行がなければコードで補う
        draft = f"# {plan['title']}\n\n{draft}"
    return draft
```

ライターは、`Agent` ではなく `acall_messages()` を1回呼ぶだけの作りにしました。必要な材料（メモ・前の版・レビュー）は、呼ぶ前にすべてわかっているからです。ツールで取りに行かせると、ターンが増えて遅く高くなります。第9章で学んだ「エージェントにしなくてよいものはしない」の実践です。

`max_tokens=16000` は、6,000字程度のレポートに対して十分な余裕を持たせた値です。それでも上限で切れた場合は、警告を出したうえで、切れた下書きをそのまま返します。続きはレビュアーが「構成」や「網羅性」で減点するので、修正の段階で直すきっかけになります。`refusal` だけは、そのまま続けても意味がないので例外にします。題の行を補う処理は、モデルが前置きを付けてしまったときの保険です。

メモを `<note id="q1">` のようなタグで囲むのは、複数の資料の境界をはっきりさせるためです。修正時には、前の版とレビューの指摘も同じくタグで渡します。オーケストレーターの `instructions` は「方針」だけで、材料はコードが確実に渡す、という10.2節の分担がここで完結します。

### レビュアー ── ルーブリックで採点する

最後に、`report_agent/reviewer.py` を新規作成します。

```python
# report_agent/reviewer.py（新規作成）
"""レビュアー: ルーブリックで下書きを採点し、修正指示を返す（合否はコードで判定）"""
from __future__ import annotations

import json

from llm_client import acall_messages, extract_text

from report_agent import REVIEWER_MODEL

# キー → (観点名, 5点の状態, 2点以下の状態)。10.1節の表と同じ内容
RUBRIC = {
    "coverage": ("網羅性", "調査計画の問いすべてに答えている", "問いの半分以上に触れていない"),
    "evidence": ("根拠", "主要な主張すべてに出典があり、メモと矛盾しない", "出典のない断定が目立つ"),
    "structure": ("構成", "結論が先にあり、見出しの流れが自然", "結論が見えず、話題が行き来する"),
    "readability": ("読みやすさ", "想定読者が一読で理解できる", "専門用語が説明なしに続く"),
    "actionability": ("実用性", "読者が次に何をすべきかがわかる", "事実の羅列で終わっている"),
}
PASS_SCORE = 4  # 全観点がこの点以上なら合格

REVIEWER_SYSTEM = "あなたは調査レポートの厳格なレビュアーです。次のルーブリックで1〜5点で採点します。\n" + "\n".join(
    f"- {key}（{name}）: 5点={top} / 2点以下={low}" for key, (name, top, low) in RUBRIC.items()
) + """
- 調査メモと照らし合わせ、メモにない主張や出典の誤りは evidence で減点する
- issues には、点数が5未満の観点ごとに「どこが・なぜ・どう直すか」を具体的に書く（重要な順）
- 調べ直さないと直せない不足は needs_research に問いの形で書く。なければ空にする"""

REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "scores": {"type": "object",
                   "properties": {k: {"type": "integer"} for k in RUBRIC},
                   "required": list(RUBRIC), "additionalProperties": False},
        "issues": {"type": "array", "items": {
            "type": "object",
            "properties": {"criterion": {"type": "string", "enum": list(RUBRIC)},
                           "location": {"type": "string"},
                           "problem": {"type": "string"},
                           "fix": {"type": "string"}},
            "required": ["criterion", "location", "problem", "fix"],
            "additionalProperties": False}},
        "needs_research": {"type": "array", "items": {"type": "string"}},
        "summary": {"type": "string"},
    },
    "required": ["scores", "issues", "needs_research", "summary"],
    "additionalProperties": False,
}


def is_passed(scores: dict[str, int]) -> bool:
    """平均ではなく最低点で判定する（1観点でも基準未満なら不合格）"""
    return all(scores.get(key, 0) >= PASS_SCORE for key in RUBRIC)


async def review_draft(draft: str, plan: dict, notes: dict[str, str]) -> dict:
    questions = "\n".join(f"- {q['id']}: {q['question']}" for q in plan["questions"])
    memo_text = "\n\n".join(f'<note id="{qid}">\n{m}\n</note>' for qid, m in notes.items())
    content = (f"<questions>\n{questions}\n</questions>\n\n{memo_text}\n\n"
               f"<draft>\n{draft}\n</draft>\n\n上の下書きを採点してください。")
    response = await acall_messages(
        [{"role": "user", "content": content}],
        system=REVIEWER_SYSTEM, model=REVIEWER_MODEL, max_tokens=8000,
        output_config={"format": {"type": "json_schema", "schema": REVIEW_SCHEMA}},
    )
    if response["stop_reason"] != "end_turn":
        raise RuntimeError(f"採点に失敗しました: stop_reason={response['stop_reason']}")
    review = json.loads(extract_text(response))
    review["scores"] = {k: max(1, min(5, int(v))) for k, v in review["scores"].items()}  # 1〜5に収める
    review["passed"] = is_passed(review["scores"])   # 合否はLLMに言わせず、コードで決める
    return review
```

`RUBRIC` は、10.1節の表をそのままデータにしたものです。system プロンプトもこのデータから組み立てるので、観点を足したいときは `RUBRIC` に1行足すだけで、プロンプト・スキーマ・合否判定のすべてに反映されます。基準を1か所で管理しておくと、プロンプトとコードの食い違いが起きません。

`REVIEW_SCHEMA` では、`scores` の5つのキーをすべて `required` にしています。観点の採点漏れは、スキーマの段階で起こらなくなります。`issues` の `criterion` を `enum` で縛ったのは、指摘がどの観点のものかを確実に分類させるためです。

合否の `passed` は、スキーマに含めていません。10.1節で決めたとおり、点数から `is_passed()` で計算します。点数を1〜5に丸め込む処理も、念のためコードで行います。スキーマで整数であることは保証されますが、範囲までは保証されないからです。

### 評価者-最適化者ループを確認する

これで、第9章の評価者-最適化者パターンが、エージェント同士の協調として組み上がりました。流れを整理すると、図10.4のようになります。

[FIG_10_4｜フロー｜可｜評価者-最適化者ループ｜執筆→採点→合否判定→追加調査か修正を選ぶ循環]

ライターが書き、レビュアーが採点し、コードが合否を決めます。不合格なら、オーケストレーターが指摘を読んで、追加調査か書き直しかを選びます。ループを止めるのは、合格・修正回数の上限・予算の3つです。どれか1つでも満たせば必ず止まるので、終わらないループにはなりません。

レビュアーをライターと別のプロンプトで動かすことにも意味があります。同じ会話の中で「自分の文章を評価して」と頼むと、甘い評価になりがちです。評価者が別の文脈で、メモと照らし合わせながら読むから、根拠のない主張に気づけます。

---

## 10.4 CLI化とテスト

部品はすべてそろいました。この節では、コマンド1つで動かせるCLIにまとめ、APIを呼ばずに動作を確かめるテストを書きます。最後に実際に動かし、コストレポートを読みます。

### argparse でCLIを作る

`report_agent/cli.py` を新規作成します。引数の解析には、Python標準の argparse（アーグパース）を使います。

```python
# report_agent/cli.py（新規作成）
"""コマンドライン入口: uv run python -m report_agent.cli "テーマ" --budget 1.0"""
from __future__ import annotations

import argparse
import logging
import sys

import llm_client
from llm_client import APIError

from report_agent.orchestrator import ReportOrchestrator

ROLE_LABELS = {"plan": "計画", "research": "調査", "write": "執筆",
               "review": "レビュー", "orchestrator": "オーケストレーター"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="report_agent", description="調査レポートを自動作成します")
    parser.add_argument("theme", help="調査テーマ（空白を含むときは \"\" で囲む）")
    parser.add_argument("--budget", type=float, default=1.0, help="1回の実行の予算（USD、既定 1.0）")
    parser.add_argument("--source", choices=["local", "web"], default="local",
                        help="local=workspace/sources を検索 / web=Web検索（別料金）")
    parser.add_argument("--max-rounds", type=int, default=2, help="初稿の後の修正回数の上限")
    parser.add_argument("--max-questions", type=int, default=5, help="調査する問いの上限")
    parser.add_argument("-v", "--verbose", action="store_true", help="APIの呼び出しログも表示する")
    return parser


def print_cost_report(orchestrator: ReportOrchestrator, path) -> None:
    budget = orchestrator.budget
    print("=" * 50)
    print(f"レポート: {path}")
    print(f"使用金額: ${budget.spent():.3f} / 予算 ${budget.limit_usd:.2f}")
    print("役割別コスト:")
    for role, usd in orchestrator.cost_by_role.items():
        print(f"  {ROLE_LABELS.get(role, role):<10} ${usd:.4f}")
    print(llm_client.tracker.summary())  # 第4章: 呼び出し回数とトークン4種の内訳


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.budget <= 0:
        build_parser().error("--budget には正の数を指定してください")

    logging.basicConfig(level=logging.INFO, datefmt="%H:%M:%S",
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not args.verbose:  # 通常は進捗だけを表示し、1回ごとの通信ログは隠す
        logging.getLogger("llm_client").setLevel(logging.WARNING)
        logging.getLogger("agent").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)  # httpx の通信ログ（INFO）も隠す

    orchestrator = ReportOrchestrator(args.theme, budget_usd=args.budget, source=args.source,
                                      max_rounds=args.max_rounds, max_questions=args.max_questions)
    try:
        path = orchestrator.run()
    except APIError as exc:        # キーの誤り・権限・レート制限の枯渇など
        print(f"APIエラーで中止しました: {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:    # 計画が作れない・下書きが1つもない など
        print(f"中止しました: {exc}", file=sys.stderr)
        return 1
    print_cost_report(orchestrator, path)
    return 0


if __name__ == "__main__":
    sys.exit(main())  # 終了コード 0=成功 / 1=失敗 をシェルに返す
```

`main()` が `argv` を引数に取るのは、テストから `main(["テーマ", "--budget", "0.5"])` のように呼べるようにするためです。省略すると、argparse がコマンドラインの引数を読みます。`--budget` の値が0以下なら、`parser.error()` で使い方と一緒にエラーを表示して終了します。

ログは、通常は進捗（`report_agent.*`）だけを表示し、`-v` を付けたときだけ通信のログも出します。返り値の0と1は終了コードで、シェルスクリプトや定期実行の仕組みから成否を判定するのに使えます。

### 実行してコストレポートを読む

> **STEP 1**: 資料を置いて、ローカル検索版で実行する
> 10.3節の資料を `workspace/sources/` に置いたら、プロジェクトのルートで次のコマンドを実行します。

```bash
# ローカル資料版（Web検索の料金はかからない）
uv run python -m report_agent.cli "中小企業がAIエージェントを導入するときのコスト管理の勘所" --budget 1.0
```

`python -m report_agent.cli` は、`report_agent` パッケージの `cli` モジュールを実行する書き方です。`-m` で実行するとカレントディレクトリが検索パスに入るので、`report_agent/` の中から `llm_client` を読み込めます。`uv run python report_agent/cli.py` と書くと、`ModuleNotFoundError: No module named 'llm_client'` になるので注意してください。

出力例は次のとおりです（時間・金額・版数は実行ごとに変わります）。

```text
15:30:12 INFO report_agent.orchestrator: 調査計画を作成中: 中小企業がAIエージェントを導入するときのコスト管理の勘所
15:30:31 INFO report_agent.orchestrator: 調査計画: 問い5個 / 見出し6個
15:30:40 INFO report_agent.orchestrator: research を開始（見積もり $0.100 / 残り $0.957）
15:31:22 INFO report_agent.orchestrator: write を開始（見積もり $0.150 / 残り $0.921）
15:32:30 INFO report_agent.orchestrator: review を開始（見積もり $0.060 / 残り $0.812）
15:32:58 INFO report_agent.orchestrator: write を開始（見積もり $0.150 / 残り $0.768）
15:34:01 INFO report_agent.orchestrator: review を開始（見積もり $0.060 / 残り $0.661）
==================================================
レポート: S:\agent-from-scratch\workspace\runs\20261106-153012\report.md
使用金額: $0.392 / 予算 $1.00
役割別コスト:
  計画         $0.0213
  調査         $0.0187
  執筆         $0.1964
  レビュー       $0.0802
  オーケストレーター $0.0754
（以下、tracker.summary() の集計）
```

ログからは、オーケストレーターの判断の流れが読み取れます。この例では、5問をまとめて調査し、初稿（v1）を採点した結果が不合格でした。指摘を受けて書き直したv2が合格し、2回目のレビューで終了しています。

役割別コストを見ると、執筆が全体の半分を占めています。メモ全文と前の版を毎回入力するためです。一方、件数の多い調査は Haiku のおかげで2セント弱に収まりました。モデル割り当ての効果が、数字ではっきり確かめられます。コストを下げたいときは、まず一番大きい項目から手を付けるのが定石です。この例なら、修正時に前の版の全文ではなく指摘箇所だけを渡す、といった改善が考えられます。

`workspace/runs/<実行ID>/` を開くと、`plan.json`・`notes/`・`drafts/`・`reviews/`・`report.md`・`cost.json` がそろっています。`review_v1.json` と `review_v2.json` を見比べると、どの観点が何点から何点に上がったかがわかります。

[FIG_10_5｜スクリーンショット｜手｜実行後の workspace フォルダ｜runs配下のplan・notes・drafts・reviews・report]

たとえば `review_v1.json` は、次のような内容になります。

```jsonc
// workspace/runs/20261106-153012/reviews/review_v1.json（出力例）
{
  "scores": {"coverage": 5, "evidence": 3, "structure": 4, "readability": 4, "actionability": 4},
  "issues": [
    {"criterion": "evidence", "location": "## 料金の仕組み 第2段落",
     "problem": "「月額数万円に収まる」に出典がない",
     "fix": "q1 のメモにある単価の記述を引用し、金額の断定を避ける"}
  ],
  "needs_research": [],
  "summary": "構成は良いが、金額に関する主張の根拠が弱い",
  "passed": false
}
```

平均は4点ですが、`evidence` が3点なので不合格です。`needs_research` が空なので、オーケストレーターは追加調査ではなく書き直しを選び、`instructions` に「金額の断定をやめ、q1の単価を引用する」と指示しました。v2 では `evidence` が4点に上がり、合格しています。レビューの指摘が具体的であるほど、修正は一度で済みます。

`cost.json` には、ターミナルに表示した役割別コストが保存されます。

```jsonc
// workspace/runs/20261106-153012/cost.json（出力例）
{
  "total_usd": 0.392,
  "limit_usd": 1.0,
  "by_role": {"plan": 0.0213, "research": 0.0187, "write": 0.1964,
              "review": 0.0802, "orchestrator": 0.0754},
  "draft_versions": 2,
  "verdict": "合格"
}
```

数回実行して `by_role` の値を並べれば、`ESTIMATE_USD` を実測に合わせて調整できます。同じテーマで `--max-rounds 0` と `2` を比べると、修正にいくらかかり、品質がどれだけ上がったかもわかります。こうした記録が、第11章で扱う運用の判断材料になります。

> **STEP 2**: Web検索版を試す（任意・別料金）
> `--source web` を付けると、リサーチャーがWeb検索サーバーツールを使います。検索料金がかかるので、最初は `--max-questions 2` のように問いを減らして試してください。

```bash
# Web検索版（検索1,000回あたり$10の別料金。問いを2つに絞って試す）
uv run python -m report_agent.cli "2026年の生成AI規制の動向" --source web --max-questions 2 --budget 0.5
```

| 症状 | 原因と対処 |
|---|---|
| `ModuleNotFoundError: No module named 'llm_client'` | `-m` を付けずに実行している。ルートで `python -m report_agent.cli` を使う |
| 調査が全部「失敗」になる | `workspace/sources/` が空か、資料に関係する記述がない。`-v` でツールの結果を確認する |
| 400 で web search が有効でないと出る | 組織の設定でWeb検索が無効。Console で管理者が有効にするか、`--source local` を使う |
| すぐに `BUDGET_EXCEEDED` で終わる | 予算が見積もりに対して小さすぎる。`--budget` を上げるか、`ESTIMATE_USD` を実測に合わせる |

### テストの準備 ── pytest と差し替え口

エージェントのテストで難しいのは、APIを呼ぶたびに料金がかかり、答えも毎回変わることです。そこで、httpx の `MockTransport`（モックトランスポート）を使います。第4章でリトライを試したときと同じく、通信の代わりに自分で書いた関数が応答を返す仕組みです。

第4章では `llm_client._client` を直接差し替えましたが、非同期のクライアントも使うようになったので、正式な差し替え口 `set_transport()` を `llm_client.py` に追加します。

```python
# llm_client.py（更新: テスト用の差し替え口を追加し、_get_async_client を置き換える）
_transport: httpx.MockTransport | None = None  # None のときは本物の通信を使う


def set_transport(transport: httpx.MockTransport | None) -> None:
    """テスト用: 同期・非同期の両クライアントの通信部分を差し替える（None で元に戻す）"""
    global _client, _async_client, _transport
    _transport = transport
    _client.close()
    _client = httpx.Client(timeout=httpx.Timeout(600.0, connect=10.0), transport=transport)
    _async_client = None  # 次に使うときに、同じ transport で作り直される


def _get_async_client() -> httpx.AsyncClient:
    global _async_client
    if _async_client is None:
        _async_client = httpx.AsyncClient(timeout=httpx.Timeout(600.0, connect=10.0),
                                          transport=_transport)
    return _async_client
```

`MockTransport` は同期と非同期の両方に対応しているので、1つの関数で両方のクライアントに差し込めます。非同期クライアントは `None` に戻しておき、次に使うときに作り直します。テストごとに `asyncio.run()` が新しいイベントループを作るので、古いクライアントを使い回さないためです。

続いて、pytest を開発用の依存として追加し、`pyproject.toml` にテストの設定を書きます。

```bash
# pytest を開発用の依存に追加する（本番の依存には入らない）
uv add --dev pytest
```

```toml
# pyproject.toml（末尾に追記）
[tool.pytest.ini_options]
pythonpath = ["."]      # プロジェクトのルートを検索パスに入れ、llm_client を読み込めるようにする
testpaths = ["tests"]
```

`pythonpath = ["."]` がないと、`tests/` の中から `import llm_client` ができません。pytest はテストファイルのフォルダを検索パスに入れますが、プロジェクトのルートは入れないからです。

### APIを呼ばないテストを書く

`tests/test_report_agent.py` を新規作成します。

```python
# tests/test_report_agent.py（新規作成: ブロック1 / 偽のAPIを作る道具）
"""APIを呼ばずに report_agent を確かめる（httpx.MockTransport で応答を作る）"""
import asyncio
import json

import httpx
import pytest

import llm_client
from report_agent.orchestrator import ORCHESTRATOR_SYSTEM, PLANNER_SYSTEM, ReportOrchestrator, make_plan
from report_agent.researcher import RESEARCHER_SYSTEM, search_local_docs
from report_agent.reviewer import RUBRIC, REVIEWER_SYSTEM, is_passed
from report_agent.writer import WRITER_SYSTEM

PLAN = {"title": "テスト用レポート", "audience": "実務担当者",
        "questions": [{"id": "q1", "question": "料金はどう決まるか", "why": "前提の確認"},
                      {"id": "q2", "question": "費用が膨らむ原因は何か", "why": "対策の前提"}],
        "outline": ["結論", "料金の仕組み", "次のアクション"]}
MEMO = "## 結論\n料金はトークン量で決まる。\n## 根拠\n- 入力と出力で単価が違う [出典: sources/a.md:L2]"
DRAFT = "# テスト用レポート\n\n## 結論\n料金はトークン量で決まります。[出典: sources/a.md:L2]"
REVIEW_OK = {"scores": {k: 5 for k in RUBRIC}, "issues": [], "needs_research": [], "summary": "良好"}


def message(content: list[dict], stop_reason: str = "end_turn") -> dict:
    """Messages API のレスポンスと同じ形の dict を作る"""
    return {"id": "msg_test", "type": "message", "role": "assistant", "model": "claude-opus-5-5",
            "content": content, "stop_reason": stop_reason,
            "usage": {"input_tokens": 1000, "output_tokens": 200,
                      "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}}


def text(t: str) -> dict:
    return message([{"type": "text", "text": t}])


def system_of(body: dict) -> str:
    """system は文字列のことも、キャッシュ用のブロック配列（第7章）のこともある"""
    system = body.get("system") or ""
    return system if isinstance(system, str) else "".join(b.get("text", "") for b in system)


def install(handler) -> list[httpx.Request]:
    """handler(リクエストのJSON) が返す dict を、本物のAPIの代わりに返す"""
    requests: list[httpx.Request] = []

    def transport(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/count_tokens"):  # 第7章の maybe_compact が呼ぶ
            return httpx.Response(200, json={"input_tokens": 1000})
        return httpx.Response(200, json=handler(json.loads(request.content)))

    llm_client.set_transport(httpx.MockTransport(transport))
    return requests


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    """すべてのテストで: 偽のキーを使い、workspace を一時フォルダに向け、最後に通信を戻す"""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setattr("tools.files.WORKSPACE", tmp_path)
    yield
    llm_client.set_transport(None)
```

`message()` は、Messages API のレスポンスと同じ形の辞書を作ります。`usage` も入れておくと、`tracker` が本物と同じように料金を計算するので、予算まわりもテストできます。

`install()` は、受け取ったリクエストを記録しつつ、`handler` が返す辞書をレスポンスにします。第7章の `maybe_compact()` は `/v1/messages/count_tokens` も呼ぶので、そちらには固定のトークン数を返します。これを忘れると、テストが原因のわかりにくいエラーで失敗します。

`isolated` は、`autouse=True` で全テストに自動で適用されるフィクスチャ（前準備）です。`monkeypatch.setattr()` で `tools.files.WORKSPACE` を一時フォルダに向けるので、テストが本物の `workspace/` を汚しません。

```python
# tests/test_report_agent.py（ブロック2 / テスト本体）
def test_make_plan_sends_valid_request():
    requests = install(lambda body: text(json.dumps(PLAN, ensure_ascii=False)))
    plan = make_plan("AIエージェントのコスト管理", max_questions=1)
    body = json.loads(requests[0].content)
    assert requests[0].headers["anthropic-version"] == "2026-10-21"
    assert body["model"] == "claude-opus-5-5"
    assert "temperature" not in body                        # 2026-10-21 版では送らない
    assert body["output_config"]["format"]["type"] == "json_schema"
    assert [q["id"] for q in plan["questions"]] == ["q1"]  # 個数の上限はコードで守られる


def test_search_local_docs_returns_citation(tmp_path):
    (tmp_path / "sources").mkdir()
    (tmp_path / "sources" / "a.md").write_text("# 料金\n料金はトークン量で決まる。\n", encoding="utf-8")
    assert "[sources/a.md:L2]" in search_local_docs("料金の決まり方")


def test_is_passed_uses_minimum_score():
    scores = {k: 5 for k in RUBRIC}
    assert is_passed(scores)
    scores["evidence"] = 3
    assert not is_passed(scores)  # 平均4.6でも、1観点が3点なら不合格


def test_budget_blocks_delegation_without_api_call():
    requests = install(lambda body: pytest.fail("APIを呼んではいけない"))
    orchestrator = ReportOrchestrator("テーマ", budget_usd=0.0)
    orchestrator.plan = PLAN

    async def scenario() -> str:
        orchestrator._delegate_lock = asyncio.Lock()
        return await orchestrator.delegate_research(["q1"])

    assert asyncio.run(scenario()).startswith("BUDGET_EXCEEDED")
    assert requests == []         # 予算切れなら、通信は1回も発生しない


def test_end_to_end_writes_report():
    replies = iter([  # オーケストレーターの応答を、決まった順番で返す
        message([{"type": "tool_use", "id": "toolu_1", "name": "delegate_research",
                  "input": {"question_ids": ["q1", "q2"]}}], "tool_use"),
        message([{"type": "tool_use", "id": "toolu_2", "name": "delegate_write",
                  "input": {"instructions": "結論を先に書く"}}], "tool_use"),
        message([{"type": "tool_use", "id": "toolu_3", "name": "delegate_review", "input": {}}], "tool_use"),
        text("v1 で合格。残った課題なし。"),
    ])

    def handler(body: dict) -> dict:  # system プロンプトで「誰からの呼び出しか」を見分ける
        system = system_of(body)
        if PLANNER_SYSTEM in system:
            return text(json.dumps(PLAN, ensure_ascii=False))
        if ORCHESTRATOR_SYSTEM in system:
            return next(replies)
        if RESEARCHER_SYSTEM in system:
            return text(MEMO)
        if WRITER_SYSTEM in system:
            return text(DRAFT)
        if REVIEWER_SYSTEM in system:
            return text(json.dumps(REVIEW_OK, ensure_ascii=False))
        pytest.fail(f"想定外の呼び出し: {system[:40]}")

    install(handler)
    orchestrator = ReportOrchestrator("AIエージェントのコスト管理", budget_usd=1.0)
    path = orchestrator.run()

    report = path.read_text(encoding="utf-8")
    assert report.startswith("# テスト用レポート")
    assert "判定: 合格（v1）" in report
    assert (path.parent / "notes" / "q2.md").exists()   # 並列調査の結果も保存されている
    assert orchestrator.cost_by_role["research"] > 0
```

最初の3つは、部品ごとの小さなテストです。`test_make_plan_sends_valid_request` は、送ったリクエストの中身を検査します。ヘッダーの `anthropic-version`、`temperature` を送っていないこと、構造化出力の指定を確かめます。APIの仕様を守っているかを、APIを呼ばずに確かめられるのが MockTransport の強みです。

`test_budget_blocks_delegation_without_api_call` は、予算0ドルで委譲を呼びます。`handler` が呼ばれたら `pytest.fail()` で即失敗にしているので、「予算切れなら1回も通信しない」ことが保証されます。料金に関わる安全装置こそ、テストで守るべき部分です。

最後の `test_end_to_end_writes_report` は、計画からレポート出力までを通しで動かします。`handler` は、リクエストの system プロンプトを見て呼び出し元を判別し、役割ごとの偽の応答を返します。オーケストレーターの応答だけは `iter()` で順番を決め、調査→執筆→レビュー→終了という筋書きを再現しています。リサーチャー2本は並列に走るので順番は決まりませんが、同じ応答を返すので問題ありません。

> **STEP 3**: テストを実行する

```bash
# APIキーがなくても、料金ゼロで実行できる
uv run pytest -q
```

```text
.....                                                                    [100%]
5 passed in 0.91s
```

5つのテストが1秒ほどで通れば成功です。本物のAPIを呼ぶと数分と数十セントかかる流れを、料金ゼロで何度でも確かめられます。プロンプトやコードを変えたら、まずこのテストを流して、配線が壊れていないことを確かめる習慣を付けましょう。

> **NOTE**: このテストが確かめるのは「配線」です。レポートの品質そのものは確かめられません。品質を継続的に測るには、本物のAPIで評価用のテーマを流す eval（評価）の仕組みが必要です。これは第11章で扱います。

---

## COLUMN: 自分の業務に置き換えるには

本章のシステムは、調査レポート専用に見えて、実は「集める→まとめる→基準で評価する→直す」という汎用の骨格です。自分の業務に置き換えるときは、次の4か所を差し替えます。

1つ目は**入力**です。テーマの代わりに、議事録のファイル名や比較したい製品名のリストを受け取ります。`make_plan()` の `PLANNER_SYSTEM` を、その入力をどう分解するかに合わせて書き換えます。

2つ目は**ツール**です。リサーチャーの `registry` に、社内Wikiの検索や、チケット管理システムの読み取りなどを登録します。読み取り専用のツールから始めるのが安全です。

3つ目は**ルーブリック**です。`RUBRIC` の5行を、業務の品質基準に書き換えます。最も効果が大きいのがここです。チームで暗黙に共有していた「よい成果物」の基準を言葉にする作業そのものが、業務の改善にもつながります。

4つ目は**出力形式**です。`WRITER_SYSTEM` の見出しの指定を、社内の書式に合わせます。

たとえば議事録まとめなら、入力は議事録ファイル、ツールは `search_local_docs` のまま、ルーブリックは「決定事項の漏れがない」「担当者と期限が明記されている」などになります。競合調査なら、入力は競合の製品名、リサーチャーはWeb検索版、ルーブリックは「比較軸が統一されている」「価格の出典が公式である」などです。どちらも、オーケストレーターと `_guarded()` の予算管理には手を入れずに済みます。

---

## 本章のまとめ

本章で学んだことを整理します：

- 入出力・品質基準（ルーブリック）・コスト上限・役割とモデル・共有ストアを先に決めると、各エージェントの関数の形が自然に定まる。判断が必要な部分だけをエージェントにし、決まった手順はコードで書く
- オーケストレーターは委譲ツールで部下に仕事を振り、結果は `workspace/` に保存して要約だけを受け取る。予算の確認・委譲の直列化・合否判定のように「破られると困る約束」はコードで保証する
- `httpx.MockTransport` と `set_transport()` を使えば、料金ゼロ・数秒で、計画からレポート出力までの配線をテストできる

次章では **本番運用への道** を扱います。動くものができたら、次は安心して使い続けるための安全性・評価・監視を考える番です。本章で `fetch_page` や Web検索として取り込んだ外部の文章が、どんな危険をはらむのかから見ていきましょう。
