# 第4章: 自作APIクライアントを作る
# EN-TITLE: BUILDING YOUR OWN API CLIENT
# TAGS: httpx, リトライ, 指数バックオフ, SSE, コスト計測

## この章で学ぶこと

本章では以下を学びます：

- `httpx.Client` を再利用し、例外クラス階層を備えた共通モジュール `llm_client.py` を実装できるようになる
- 一時的な失敗を見分け、`retry-after` と指数バックオフ＋ジッターで安全に再試行できるようになる
- SSE（Server-Sent Events）を自前でパースし、ストリーミング応答から最終メッセージを復元できるようになる
- `logging` で呼び出しを記録し、`usage` と単価表から1回ごとのコストを計測できるようになる

前章では、Messages API（メッセージズ・エーピーアイ）のリクエストとレスポンスの構造、会話履歴の管理、エラーの種類を学びました。
本章では、それらの知識を1つのPythonモジュールにまとめます。以降のすべての章で使う「自分専用のAPIクライアント」を作ります。エージェントは1つのタスクで何十回もAPIを呼びます。そのたびにヘッダーを組み立て、エラーを調べ、待ち時間を調整するのは現実的ではありません。本章の `llm_client.py` は、第5章のループから第10章の実践プロジェクトまでを支える土台です。公式SDK（Software Development Kit）が内部でしていることを、自分の手で再現する章だと考えてください。

---

## 4.1 クライアントの設計と関数化

第3章のスクリプトを書いたとき、似たコードを何度もコピーしたと感じたはずです。ヘッダーを作り、ステータスを確かめ、`content` から `text` を取り出す。本節では、この「毎回同じ部分」を関数に閉じ込め、呼び出す側は「何を聞きたいか」だけを書けばよい形に整えます。

### 共通モジュールと公開インターフェース

共通モジュールとは、複数のスクリプトから `import` して使う部品のファイルです。共通化の最大の価値は、修正の場所が1か所になることです。第7章でキャッシュを導入するときも、APIのバージョンが上がったときも同じです。`llm_client.py` だけを直せば全章のコードに反映されます。失敗の扱い方も統一できるので、「あるファイルだけ429で落ちる」といった不一致も防げます。

モジュールを作るときは、中身より先に外から見える顔、つまり公開インターフェースを決めます。以降の章はすべてこれに依存するため、本書ではここで決めた名前と引数を最後まで変えません。

| 種類 | 名前 | 役割 |
|-----|------|------|
| 定数 | `API_URL` / `API_BASE` / `API_VERSION` | エンドポイントとAPIバージョン |
| 定数 | `MODEL` / `FAST_MODEL` | 既定モデル（`claude-opus-5-5`）と軽量モデル（`claude-haiku-5-5`） |
| 関数 | `build_headers()` | 必須ヘッダー3つを返す |
| 関数 | `call_messages()` | 非ストリーミングで呼び出し、レスポンスの dict を返す |
| 関数 | `stream_messages()` | ストリーミングで呼び出し、同じ形の dict を返す |
| 関数 | `extract_text()` / `get_tool_uses()` | レスポンスから text / tool_use を取り出す |
| 例外 | `APIError` とその子クラス | 失敗の種類を型で表す |
| クラス | `CostTracker` と `tracker` | トークン数とコストの集計 |

`call_messages()` は、レスポンスJSONを `dict` に変換してそのまま返します。独自クラスに包まないので、第3章で学んだ `response["stop_reason"]` などの書き方を最後まで使えます。APIに新しいフィールドが増えても、クライアント側の追従は不要です。

[FIG_4_1｜構造図｜可｜llm_client.pyの全体構造｜公開関数と内部の送信・リトライ・SSE・集計の層]

図4.1のように、一番外側が公開関数の層、その内側が送信と再試行の層です。一番下には、1つだけ作って使い回す `httpx.Client` があります。SSEの解析とコスト集計は、送信の結果を受け取る横の部品です。

> **POINT**: 公開関数の引数は、`messages` 以外をすべてキーワード専用（`*` の後ろ）にしています。`call_messages(msgs, tools=tools)` と名前付きで書かせれば、引数の取り違えを防げます。また、あとで引数を増やしても呼び出し側が壊れません。

### httpx.Clientの再利用とタイムアウト

第3章の `httpx.post()` は、呼ぶたびに新しい接続を作って捨てています。HTTPSの接続には、TCPの確立とTLSの取り決めが必要です。TCPはTransmission Control Protocol、TLSはTransport Layer Securityの略です。この往復だけで数十〜数百ミリ秒かかります。`httpx.Client` は確立済みの接続を保管して再利用します。これを接続プールと呼びます。30回呼ぶエージェントなら、2回目以降の準備時間がほぼなくなります。

> **NOTE**: `with httpx.Client() as client:` という書き方もよく見かけます。ブロックを抜けると接続を閉じる書き方で、短いスクリプトには便利です。本書のようにプログラムの最初から最後まで使うクライアントは、モジュールの変数として保持します。逆に、関数の中で毎回 `httpx.Client()` を作ると、接続プールの恩恵がまったく得られないので注意してください。

タイムアウトは「この時間を過ぎたら諦める」上限です。httpxでは接続の `connect`、受信の `read`、送信の `write`、プール待ちの `pool` の4種類があります。`httpx.Timeout(600.0, connect=10.0)` は、`connect` だけを10秒、残りを600秒にする指定です。接続は正常なら1秒もかからないので、10秒で繋がらなければネットワークの問題と判断できます。一方、思考を伴う長い応答は時間がかかるため、`read` は長めにします。httpxの既定値は5秒なので、指定しないとエージェント用途ではすぐ `ReadTimeout` になります。

> **WARNING**: 非ストリーミングで10分近い生成を待つのは避けてください。途中のネットワーク機器が、通信のない接続を切ることがあるためです。公式ドキュメントも、長いリクエストにはストリーミングかMessage Batches APIを推奨しています。長い出力には4.3節の `stream_messages()` を使います。

### 定数と共有クライアントを定義する

プロジェクトのフォルダー `agent-from-scratch/` に、`llm_client.py` を新規作成します。まずはインポート・定数・共有クライアントです。インポートには後の節で使うものも含めています。

```python
# llm_client.py（新規作成：冒頭部分）
"""Claude Messages API を httpx で直接呼び出す共通クライアント（第4章 完成版）。"""
from __future__ import annotations

import json
import logging
import os
import random
import threading
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Any

import httpx
from dotenv import load_dotenv

# ---- 設定値 -------------------------------------------------------------
load_dotenv()  # .env の ANTHROPIC_API_KEY を環境変数に読み込む（モジュールで1回だけ）

API_URL = "https://api.anthropic.com/v1/messages"
API_BASE = "https://api.anthropic.com/v1"
API_VERSION = "2026-10-21"
MODEL = "claude-opus-5-5"  # 既定モデル
FAST_MODEL = "claude-haiku-5-5"  # 分類・要約・ワーカー用

# 2026-10-21 版で送ってはいけないパラメータ（送ると 400 になる）
FORBIDDEN_PARAMS = frozenset({"temperature", "top_p", "top_k"})

logger = logging.getLogger("llm_client")

# 接続プールを持つクライアントをモジュール全体で1つだけ作り、使い回す
_client = httpx.Client(timeout=httpx.Timeout(600.0, connect=10.0))
```

`load_dotenv()` は、これまで各スクリプトで呼んでいました。今後は `llm_client.py` の中で1回呼ぶだけです。インポートした時点で `.env` が読み込まれます。`API_BASE` は、別のエンドポイントを組み立てるために用意します。第7章の `/v1/messages/count_tokens` や第11章のバッチで使います。

`FORBIDDEN_PARAMS` は、このAPIバージョンで送ると400になる `temperature`・`top_p`・`top_k` の一覧です。古い記事のコードから紛れ込みやすいので、送る前に検査します。`logger` は4.4節で使う記録係です。`_client` の先頭のアンダースコアは、「モジュールの外から直接触らない」という慣習的な目印です。

### 例外クラス階層を作る

第3章ではステータスコードを `if` 文で調べていました。例外クラス階層とは、共通の親を持つ例外クラスの家系図です。`APIError` を親にしておけば、`except RateLimitError:` で429だけを捕まえられます。一方、`except APIError:` ならAPIの失敗すべてを捕まえられます。分岐を型で書けるようになるのが利点です。

[FIG_4_2｜構造図｜可｜例外クラスの階層｜APIErrorを親に9つの子クラスとHTTPステータスの対応]

```python
# llm_client.py（新規作成：例外クラス）
# ---- 例外クラス -----------------------------------------------------------
class APIError(Exception):
    """Claude API 呼び出しの失敗を表す基底クラス。"""

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        error_type: str = "api_error",
        request_id: str | None = None,
        error_code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message  # error.message（人間向けの説明）
        self.status = status  # HTTPステータス（接続エラーは None）
        self.error_type = error_type  # error.type（機械判定用）
        self.request_id = request_id  # 問い合わせ用の request-id
        self.error_code = error_code  # error.details.error_code（あれば）

    def __str__(self) -> str:
        return (
            f"[{self.status} {self.error_type}] {self.message}"
            f" (request_id={self.request_id})"
        )


class InvalidRequestError(APIError):  # 400
    pass


class AuthenticationError(APIError):  # 401
    pass


class PermissionDeniedError(APIError):  # 403
    pass


class NotFoundError(APIError):  # 404
    pass


class RequestTooLargeError(APIError):  # 413
    pass


class RateLimitError(APIError):  # 429
    pass


class InternalServerError(APIError):  # 500 などの 5xx
    pass


class OverloadedError(APIError):  # 529
    pass


class APIConnectionError(APIError):  # 接続失敗・タイムアウト（status=None）
    pass
```

親の `APIError` は、手がかりとなる属性を持ちます。`status` はHTTPステータス、`error_type` は `error.type`、`request_id` は問い合わせ用の識別子です。`error_code` は、429のうち「月の利用上限に達した」ケースを見分けるために使います（4.2節）。`__str__` を定義しておくと、ログに出したときに状況が1行で分かります。

子クラスの中身は `pass` だけです。呼び出し側が `except` で型を選ぶことに意味があり、属性は親にまとめれば十分だからです。`APIConnectionError` だけはサーバーに繋がらなかった失敗なので、`status` が `None` になります。

> **NOTE**: APIは402や409、504も返し得ます。それぞれ `billing_error`（支払い情報の問題）、`conflict_error`、`timeout_error` です。本書ではこれらに専用クラスを作りません。402と409は `APIError`、504は `InternalServerError`（5xx）として扱います。SSEの `error` イベントで届く `timeout_error` も `InternalServerError` にそろえます。必要になれば子クラスを足すだけで、呼び出し側は壊れません。

### エラーレスポンスを例外に変換する

エラーボディは `{"type": "error", "error": {"type": ..., "message": ...}, "request_id": ...}` という形でした。ここから値を取り出し、適切な例外クラスに詰めます。

```python
# llm_client.py（新規作成：エラー変換）
# HTTPステータス → 例外クラス
_STATUS_TO_ERROR: dict[int, type[APIError]] = {
    400: InvalidRequestError,
    401: AuthenticationError,
    403: PermissionDeniedError,
    404: NotFoundError,
    413: RequestTooLargeError,
    429: RateLimitError,
    529: OverloadedError,
}

# error.type → 例外クラス（ステータスのない SSE の error イベント用）
_TYPE_TO_ERROR: dict[str, type[APIError]] = {
    "invalid_request_error": InvalidRequestError,
    "authentication_error": AuthenticationError,
    "permission_error": PermissionDeniedError,
    "not_found_error": NotFoundError,
    "request_too_large": RequestTooLargeError,
    "rate_limit_error": RateLimitError,
    "api_error": InternalServerError,
    "timeout_error": InternalServerError,  # 504 と同じ扱い
    "overloaded_error": OverloadedError,
}


def _error_class(status: int | None, error_type: str) -> type[APIError]:
    """ステータスを優先し、なければ error.type から例外クラスを選ぶ。"""
    if status is not None:
        if status in _STATUS_TO_ERROR:
            return _STATUS_TO_ERROR[status]
        if status >= 500:
            return InternalServerError
    return _TYPE_TO_ERROR.get(error_type, APIError)


def _make_error(
    status: int | None, body: Any, request_id: str | None
) -> APIError:
    """エラーボディ（dict）から適切な例外オブジェクトを作る。"""
    err = body.get("error", {}) if isinstance(body, dict) else {}
    error_type = err.get("type", "unknown_error")
    message = err.get("message") or f"HTTP {status}"
    details = err.get("details") or {}
    if isinstance(body, dict):
        request_id = request_id or body.get("request_id")
    cls = _error_class(status, error_type)
    return cls(
        message,
        status=status,
        error_type=error_type,
        request_id=request_id,
        error_code=details.get("error_code"),
    )


def _error_from_response(response: httpx.Response) -> APIError:
    """エラーレスポンス（HTTP 4xx/5xx）を例外に変換する。"""
    try:
        body = response.json()
    except ValueError:  # JSON でない（プロキシのHTMLなど）
        body = {"error": {"message": response.text[:200]}}
    return _make_error(
        response.status_code, body, response.headers.get("request-id")
    )
```

対応表が2つあるのは、ストリーミングでは200で応答が始まった後に `error` イベントが届くことがあるからです。この場合はステータスがないので、`error.type` から例外クラスを選びます。`_error_class()` はステータスを優先し、なければ型名で探し、最後は `APIError` を返します。どの経路でも必ず `APIError` 系が返ります。

`_make_error()` で `get()` を多用しているのは、ボディの形が想定と違っても二重に落ちないためです。エラー処理の中で別の例外が起きると、本当の原因が隠れてしまいます。`_error_from_response()` は、プロキシがHTMLのエラーページを返した場合に備えています。JSONでなければ本文の先頭200文字を残します。

### ヘッダーとボディを組み立てる

```python
# llm_client.py（新規作成：リクエストの組み立て）
def build_headers() -> dict[str, str]:
    """認証・バージョン・形式の3つの必須ヘッダーを返す。"""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY が未設定です。.env を確認してください。"
        )
    return {
        "x-api-key": api_key,
        "anthropic-version": API_VERSION,
        "content-type": "application/json",
    }


def _build_body(
    messages: list[dict],
    *,
    system: str | list[dict] | None,
    tools: list[dict] | None,
    model: str,
    max_tokens: int,
    tool_choice: dict | None,
    output_config: dict | None,
    extra: dict | None,
    stream: bool,
) -> dict[str, Any]:
    """リクエストボディを組み立てる。None の項目は送らない。"""
    body: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system is not None:
        body["system"] = system
    if tools:
        body["tools"] = tools
    if tool_choice is not None:
        body["tool_choice"] = tool_choice
    if output_config is not None:
        body["output_config"] = output_config
    if extra:
        bad = FORBIDDEN_PARAMS & extra.keys()
        if bad:  # 送る前に止める（APIに400を返させない）
            raise ValueError(f"このAPIバージョンでは使えません: {sorted(bad)}")
        body.update(extra)
    if stream:
        body["stream"] = True
    return body
```

`build_headers()` は、キーが未設定なら送る前に止めます。そのまま送ると401になりますが、それでは「キーが誤り」なのか「読み込めていない」のか区別できないからです。第7章以降でも再利用するので公開関数にしています。

`_build_body()` の方針は「`None` の項目は送らない」です。キーごと省略すれば、APIは既定値を使います。`extra` は専用の引数がない項目を渡す逃げ道です。第7章の `cache_control` や `stop_sequences` をここから渡します。何でも通せてしまうので、禁止パラメータとの共通部分を集合演算で調べ、見つかれば `ValueError` にします。

> **POINT**: `tool_choice` は `{"type": "auto"}` か `{"type": "none"}` だけを使います。ツールを強制する `any` や `tool` は、Opus 5.5とSonnet 5.5では400エラーになります。

### call_messages() の最初の版

まずはリトライもログもない最初の版です。4.2節でリトライ、4.4節でログとコスト計測を加えます。段階を分けるのは、各行の役割を見えやすくするためです。

```python
# llm_client.py（新規作成：call_messages 最初の版。4.2節で差し替える）
def call_messages(
    messages: list[dict],
    *,
    system: str | list[dict] | None = None,
    tools: list[dict] | None = None,
    model: str = MODEL,
    max_tokens: int = 16000,
    tool_choice: dict | None = None,
    output_config: dict | None = None,
    extra: dict | None = None,
    max_retries: int = 4,
) -> dict:
    """Messages API を1回呼び出し、レスポンスJSON（dict）を返す。"""
    # 1. ボディを組み立てる（禁止パラメータはここで止まる）
    body = _build_body(
        messages,
        system=system,
        tools=tools,
        model=model,
        max_tokens=max_tokens,
        tool_choice=tool_choice,
        output_config=output_config,
        extra=extra,
        stream=False,
    )
    # 2. 共有クライアントで送信する
    response = _client.post(API_URL, headers=build_headers(), json=body)
    # 3. 失敗なら型付きの例外にして投げる
    if response.status_code >= 400:
        raise _error_from_response(response)
    # 4. 成功ならJSONをdictにして返す
    return response.json()
```

必須の引数は `messages` だけで、`model` の既定値は `MODEL` です。`max_retries` はまだ使いませんが、完成版と形を揃えるため先に用意しています。本体は「組み立て→送信→失敗なら例外→成功ならdict」の4ステップです。この版では、`httpx.ConnectError` などの接続エラーはhttpxの例外のまま飛び出します。これも4.2節で `APIConnectionError` に変換します。

### extract_text() と get_tool_uses()

Opus 5.5の応答には、`text` の前に `thinking` ブロックが入ることがあります。`response["content"][0]["text"]` と決め打ちすると `KeyError` になるので、必ず `type` で判定します。

```python
# llm_client.py（新規作成：レスポンスのヘルパー）
def extract_text(response: dict) -> str:
    """type が text のブロックだけを順に連結して返す。"""
    return "".join(
        block.get("text", "")
        for block in response.get("content", [])
        if block.get("type") == "text"
    )


def get_tool_uses(response: dict) -> list[dict]:
    """type が tool_use のブロックを一覧で返す。"""
    return [
        block for block in response.get("content", []) if block.get("type") == "tool_use"
    ]
```

`extract_text()` は `text` ブロックだけを順に連結します。`get_tool_uses()` は `tool_use` ブロックの一覧を返し、第5章のループで主役になります。複数のツールを同時に依頼されることもあるので、リストで返します。どちらも想定外の形で落ちないよう `get()` で防御しています。

### 動作を確認する

確認用の `client_demo.py` を作り、正常系とエラーの両方を試します。このファイルは以降の章では使いません。

```python
# client_demo.py（新規作成：4.1節の動作確認用）
from llm_client import NotFoundError, APIError, call_messages, extract_text

# 1. 正常な呼び出し：日本語で一言あいさつしてもらう
response = call_messages(
    [{"role": "user", "content": "一言で自己紹介してください。"}],
    max_tokens=1000,
)
print("stop_reason:", response["stop_reason"])
print("blocks:", [block["type"] for block in response["content"]])
print("text:", extract_text(response))

# 2. 存在しないモデルIDを指定して、404 を型で捕まえる
try:
    call_messages(
        [{"role": "user", "content": "こんにちは"}],
        model="claude-opus-9-9",
    )
except NotFoundError as error:
    print("NotFoundError:", error)
except APIError as error:  # 想定外の失敗もまとめて捕まえる
    print("APIError:", error)

# 3. 禁止パラメータは送る前に止まる
try:
    call_messages([{"role": "user", "content": "hi"}], extra={"temperature": 0.2})
except ValueError as error:
    print("ValueError:", error)
```

```bash
# agent-from-scratch/ で実行する
uv run python client_demo.py
```

出力例は次のとおりです。文面やrequest-idは実行ごとに変わります。

```text
stop_reason: end_turn
blocks: ['thinking', 'text']
text: Anthropicが開発したAIアシスタントのClaudeです。
NotFoundError: [404 not_found_error] model: claude-opus-9-9 (request_id=req_011CZ...)
ValueError: このAPIバージョンでは使えません: ['temperature']
```

`blocks` に `thinking` と `text` が並んでいます。Opus 5.5は思考が常に有効なので、既定では中身が空の `thinking` ブロックが先頭に入ることがあります。簡単な質問では入らないこともあります。それでも `extract_text()` は正しく文章を取り出せています。2つ目では、存在しないモデルIDの404が `NotFoundError` として捕まりました。`except` は上から評価されるので、子クラスを先に、親の `APIError` を後に書きます。3つ目はリクエストを送る前に止まっているので、料金もかかりません。

> **WARNING: よくあるつまずき**
> `No module named 'llm_client'` と表示されたら、2つのファイルが同じフォルダーにあるかを確認してください。また、`agent-from-scratch/` で `uv run` しているかも確かめます。
> `RuntimeError: ANTHROPIC_API_KEY が未設定です` と出たら、`.env` の置き場所とキー名を確かめます。`.env` がプロジェクト直下にあり、キー名の綴りが正しいかを見てください。キーが読めているのに `AuthenticationError` になる場合は、キーが失効しているかもしれません。コピー時に前後の空白が混ざっている可能性もあります。

ここで、第3章のコードと比べてみましょう。以前は1回の呼び出しに、ヘッダーの辞書・URL・`httpx.post()`・ステータスの確認と、10行前後が必要でした。今は `call_messages([...])` の1行で済み、失敗は型付きの例外として届きます。呼び出し側のコードが「何をしたいか」だけを表すようになった点が、関数化の最大の成果です。

次の節では、この `call_messages()` に「失敗しても諦めない」仕組みを加えます。

---

## 4.2 リトライと指数バックオフ

APIを長時間呼び続けると、こちらに落ち度がなくても失敗することがあります。混雑による529、レート制限の429、一瞬のネットワーク断などです。エージェントが20ステップ目で一時的な529に当たり、それまでの作業ごと止まってしまうのは避けたいところです。本節では、失敗の種類を見分け、待つべきときだけ賢く待って再試行する仕組みを作ります。

### リトライしてよい失敗、いけない失敗

リトライとは、失敗したリクエストを時間をおいて送り直すことです。ただし、何でも送り直せばよいわけではありません。判断の基準は「同じリクエストを時間をおいて送れば、成功する見込みがあるか」です。

| 失敗 | 例外クラス | リトライ | 理由 |
|-----|-----------|---------|------|
| 400 / 401 / 403 / 404 / 413 | `InvalidRequestError` など | しない | リクエストか設定の誤り。何度送っても同じ |
| 402（支払いの問題） | `APIError` | しない | 支払い情報を直すまで回復しない |
| 408（タイムアウト）/ 409（競合） | `APIError` | する | 一時的な状態による失敗 |
| 429（レート制限） | `RateLimitError` | する | 待てば枠が回復する |
| 429（ティアの月の利用上限） | `RateLimitError` | しない | 翌月まで回復しない |
| 500 / 504 / 529 などの5xx | `InternalServerError` / `OverloadedError` | する | サーバー側の一時的な問題 |
| 接続失敗・タイムアウト | `APIConnectionError` | する | ネットワークの一時的な問題 |

400系をリトライしないのは、たとえばモデルIDの綴り間違いは何度送っても直らないからです。無駄に待つ分、誤りに気づくのが遅れます。注意したいのは429の中の例外です。ティアで決まる組織の月の支出上限（spend cap）に達した場合の429です。この429には `retry-after` ヘッダーがありません。また、`error.details.error_code` が `enforced_spend_limit_reached` になります。翌月まで回復しないので、即座に諦めて人間に知らせるべきです。4.1節で `error_code` 属性を用意したのは、この判定のためでした。なお、Consoleで自分で設定した利用上限（spend limit）に達した場合は、429ではなく400が返ります。エラーの型は `invalid_request_error` です。400系なので本書のクライアントは再試行せず、すぐに例外になります。408はAPIのエラー一覧にはありませんが、プロキシなどが返す場合に備え、公式SDKと同様に再試行の対象にしています。

### 指数バックオフとジッター

待ち時間の決め方で最もよく使われるのが、指数バックオフです。これは、失敗するたびに待ち時間を1秒、2秒、4秒、8秒と倍々に延ばす方法です。混雑が短ければすぐ回復でき、長引くなら間隔を空けて相手の負担を減らせます。電話がつながらないとき、すぐかけ直し、次は少し空け、さらに長く空けるのと同じ発想です。

ただし、指数バックオフだけでは問題が残ります。1000個のクライアントが同時に529を受けたとします。全員が「ちょうど1秒後」に再送すると、1秒後にまた一斉に殺到してしまいます。これをサンダリングハード（thundering herd、群れの暴走）問題と呼びます。

そこで、待ち時間にランダムな揺らぎを加えます。これをジッター（jitter）と呼びます。本書では「0秒からバックオフ上限までの一様乱数」を待つフルジッター方式を使います。再送のタイミングが時間軸に散らばり、サーバーへの負荷が平らになります。

[FIG_4_3｜比較｜可｜ジッターの有無による再送の分布｜同時再送の山とジッターで平らに散らばる再送]

### retry-afterヘッダーを優先する

429の応答には、`retry-after` ヘッダーが付くことがあります（他のステータスでも、付いていれば従います）。値は「何秒待てば再試行できるか」で、サーバー自身が状況を踏まえて教えてくれる値です。推測で計算したバックオフより正確なので、あればこちらを優先します。あわせて `anthropic-ratelimit-requests-remaining` などのレート制限ヘッダーも返ります。残りの枠やリセット時刻が分かるので、第11章の本番運用で監視に使えます。

### 上限を3重に設ける

リトライには必ず上限が必要です。上限がないと、障害が長引いたときにプログラムが永遠に待ち続けます。本書では3つの上限を設けます。1つ目は試行回数の上限 `max_retries`（既定4回）です。2つ目は1回の待ち時間の上限 `MAX_DELAY`（30秒）で、バックオフが際限なく伸びるのを防ぎます。3つ目は1回の呼び出しで待つ合計時間の上限 `MAX_TOTAL_WAIT`（120秒）です。`retry-after` も、異常に大きな値に備えて60秒で頭打ちにします。

### リトライを実装する

`llm_client.py` に、リトライの設定値と4つの関数を追加します。設定値は定数のブロックの下に置きます。

```python
# llm_client.py（追加：リトライの設定。定数のブロックの下に置く）
RETRYABLE_STATUS = frozenset({408, 409, 429})  # 5xx はこれとは別に判定する
BASE_DELAY = 1.0  # バックオフの基準秒数
MAX_DELAY = 30.0  # 1回の待ち時間の上限（秒）
MAX_RETRY_AFTER = 60.0  # retry-after を信用する上限（秒）
MAX_TOTAL_WAIT = 120.0  # 1回の呼び出しで待つ合計時間の上限（秒）
```

```python
# llm_client.py（追加：リトライの判定と待ち時間）
def _is_retryable(error: APIError) -> bool:
    """再試行すれば成功する見込みがあるエラーかを判定する。"""
    if isinstance(error, APIConnectionError):
        return True  # 接続失敗・タイムアウト
    if error.error_code == "enforced_spend_limit_reached":
        return False  # 月の利用上限。待っても翌月まで回復しない
    status = error.status or 0
    return status in RETRYABLE_STATUS or status >= 500


def _retry_delay(attempt: int, response: httpx.Response | None) -> float:
    """次の再試行までの待ち秒数を決める（retry-after 優先）。"""
    if response is not None:
        retry_after = response.headers.get("retry-after")
        if retry_after:
            try:
                return min(max(float(retry_after), 0.0), MAX_RETRY_AFTER)
            except ValueError:
                pass  # 日付形式などは無視して、バックオフに任せる
    # 指数バックオフ（1, 2, 4, 8, ... 秒、上限 MAX_DELAY）＋フルジッター
    backoff = min(MAX_DELAY, BASE_DELAY * (2**attempt))
    return random.uniform(0, backoff)
```

`_is_retryable()` は、さきほどの表をそのままコードにしたものです。例外オブジェクトを受け取るので、HTTPエラーと接続エラーを同じ関数で判定できます。`_retry_delay()` の `attempt` は、何回目の再試行かを0から数えた値です。`BASE_DELAY * (2**attempt)` は1、2、4、8秒と増え、`MAX_DELAY` で頭打ちになります。最後の `random.uniform(0, backoff)` がフルジッターです。`retry-after` は秒数の形式だけを扱い、それ以外はバックオフに任せます。

```python
# llm_client.py（追加：送信と再試行の本体）
def _request_with_retry(
    url: str, body: dict[str, Any], *, stream: bool, max_retries: int
) -> httpx.Response:
    """POST を送り、一時的な失敗なら待ってから再試行する。"""
    headers = build_headers()
    total_wait = 0.0
    attempt = 0
    while True:
        request = _client.build_request("POST", url, headers=headers, json=body)
        response: httpx.Response | None = None
        try:
            response = _client.send(request, stream=stream)
        except httpx.TransportError as exc:  # 接続失敗・タイムアウト
            error: APIError = APIConnectionError(
                f"{type(exc).__name__}: {exc}", status=None
            )
            error.__cause__ = exc
        else:
            if response.status_code < 400:
                return response  # 成功（stream=True なら本文は未読）
            response.read()  # ストリーム時も本文を読み切ってから解析する
            response.close()
            error = _error_from_response(response)

        # ここに来たら失敗。再試行するかどうかを判断する
        if not _is_retryable(error) or attempt >= max_retries:
            raise error
        wait = _retry_delay(attempt, response)
        if total_wait + wait > MAX_TOTAL_WAIT:
            logger.error("待ち時間の上限 %.0f 秒を超えるため中止します", MAX_TOTAL_WAIT)
            raise error
        logger.warning(
            "retry %d/%d in %.1fs: %s", attempt + 1, max_retries, wait, error
        )
        time.sleep(wait)
        total_wait += wait
        attempt += 1


def _send_with_retry(url: str, body: dict[str, Any], max_retries: int = 4) -> dict:
    """非ストリーミングで POST し、成功したレスポンスJSON（dict）を返す。"""
    response = _request_with_retry(url, body, stream=False, max_retries=max_retries)
    return response.json()
```

`_request_with_retry()` の結果は2通りです。成功した `httpx.Response` を返すか、例外を投げるかのどちらかです。送り先の `url` を引数にしたので、第7章の `/v1/messages/count_tokens` などにも使えます。送信は `_client.post()` ではなく、`build_request()` と `send()` に分けました。4.3節のストリーミングでも同じ関数を使うためです。`send(request, stream=True)` とすると、本文を読まずにヘッダーだけ受け取った状態で返ります。

`try` 節では、`httpx.TransportError` を `APIConnectionError` に変換しています。これは `ConnectError` や `ReadTimeout` などの親クラスです。`error.__cause__ = exc` で元の例外をつないでおくと、トレースバックで本当の原因まで辿れます。`else` 節では、エラーの本文を `read()` で読み切ってから解析します。ストリーミング時は本文が未読なので、これを忘れると中身を読めません。

ループの後半が判断の部分です。リトライ不可か回数切れなら、その場で例外を投げます。待ち時間を決めたら合計の上限を確かめ、ログを残して眠ります。呼び出し側に届くのは、諦めた時点の最後のエラーです。最後の `_send_with_retry()` は、レスポンスJSONだけが欲しい場面のための薄い包みです。第7章のトークン計測で使います。

> **WARNING**: Messages APIの呼び出しは、厳密には冪等（何度送っても結果が同じ）ではありません。タイムアウトしたリクエストも、サーバー側では処理が完了して課金されている可能性があります。リトライは料金の二重発生と引き換えに可用性を得る仕組みだと理解し、上限を必ず設けてください。

`call_messages()` も、送信部分を差し替えます。4.4節では、レスポンスヘッダーの `request-id` をログに使います。そのため、ここでは `httpx.Response` を返す `_request_with_retry()` を直接呼びます。

```python
# llm_client.py（更新：call_messages をリトライ対応に差し替え）
def call_messages(
    messages: list[dict],
    *,
    system: str | list[dict] | None = None,
    tools: list[dict] | None = None,
    model: str = MODEL,
    max_tokens: int = 16000,
    tool_choice: dict | None = None,
    output_config: dict | None = None,
    extra: dict | None = None,
    max_retries: int = 4,
) -> dict:
    """Messages API を1回呼び出し、レスポンスJSON（dict）を返す。"""
    body = _build_body(
        messages,
        system=system,
        tools=tools,
        model=model,
        max_tokens=max_tokens,
        tool_choice=tool_choice,
        output_config=output_config,
        extra=extra,
        stream=False,
    )
    # 失敗の判定・再試行・例外化はすべて _request_with_retry に任せる
    response = _request_with_retry(
        API_URL, body, stream=False, max_retries=max_retries
    )
    return response.json()
```

### わざと失敗させて確かめる

リトライを試すために、本物のAPIが529を返すのを待つわけにはいきません。そこで、httpxの `MockTransport` を使います。これは、実際の通信の代わりに自分で書いた関数が応答を返す仕組みです。ここでは共有クライアントを直接差し替えます（第10章でテスト用の正式な差し替え口を追加します）。

```python
# retry_demo.py（新規作成：4.2節の動作確認用。APIは呼ばない）
import logging

import httpx

import llm_client

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)  # httpx自身のログは抑える

calls = 0


def fake_api(request: httpx.Request) -> httpx.Response:
    """1回目は529、2回目は retry-after 付きの429、3回目に成功する偽API。"""
    global calls
    calls += 1
    if calls == 1:
        return httpx.Response(529, json={"type": "error", "error": {
            "type": "overloaded_error", "message": "Overloaded"}, "request_id": "req_a"})
    if calls == 2:
        return httpx.Response(429, headers={"retry-after": "1"}, json={"type": "error",
            "error": {"type": "rate_limit_error", "message": "Rate limited"}, "request_id": "req_b"})
    return httpx.Response(200, json={"model": "claude-opus-5-5", "stop_reason": "end_turn",
        "content": [{"type": "text", "text": "3回目で成功しました"}],
        "usage": {"input_tokens": 12, "output_tokens": 30}})


# 共有クライアントを偽APIに差し替える
llm_client._client = httpx.Client(transport=httpx.MockTransport(fake_api))
response = llm_client.call_messages([{"role": "user", "content": "テスト"}])
print(llm_client.extract_text(response), f"(試行回数: {calls})")
```

```bash
# agent-from-scratch/ で実行する（偽APIなので通信も課金も発生しない）
uv run python retry_demo.py
```

```text
WARNING llm_client: retry 1/4 in 0.6s: [529 overloaded_error] Overloaded (request_id=req_a)
WARNING llm_client: retry 2/4 in 1.0s: [429 rate_limit_error] Rate limited (request_id=req_b)
3回目で成功しました (試行回数: 3)
```

なお、4.4節まで完成させた後に実行すると、最後に `INFO` の呼び出しログも1行加わります。1行目の0.6秒は、ジッターで0〜1秒から選ばれた値なので実行ごとに変わります。2行目はちょうど1.0秒で、`retry-after: 1` が優先されたことが分かります。偽APIの1回目を `400` に変えることも試してみてください。リトライせずに `InvalidRequestError` が即座に出ます。なお、`build_headers()` はAPIキーの有無を確認するので、`.env` は設定済みである必要があります。

> **NOTE**: `logging.getLogger("httpx").setLevel(logging.WARNING)` を外してみましょう。すると、httpxが送信ごとに `HTTP Request: POST ...` というINFOログを出します。自分のログが埋もれるので、確認用スクリプトでは抑えておくと読みやすくなります。

### リトライでつまずきやすい点

1つ目は、リトライがエラーを隠してしまうことです。429が頻発していても、最終的に成功すれば呼び出し側は気づきません。だからこそ、本書では再試行のたびに `WARNING` のログを残しています。ログに `retry` が並び始めたら、呼び出し頻度を下げるか、利用枠の引き上げを検討する合図です。

2つ目は、並列実行との掛け算です。第8章では複数のエージェントを同時に動かします。10個が同時に429を受け、それぞれが4回ずつ再試行すると、短時間に最大50回のリクエストが飛びます。ジッターはこの集中を和らげますが、並列数そのものを抑える工夫も必要です。第8章では、同時に実行する数を制限する方法も扱います。

3つ目は、Ctrl+Cで止めにくくなることです。`time.sleep()` の最中でもCtrl+Cは効くので、プログラムは止められます。ただし合計待ち時間の上限が大きいと、異常に気づくまでに時間がかかります。開発中は `max_retries=1` のように小さく指定して、失敗をすぐ表に出すのも1つの手です。

これで、一時的な失敗に強いクライアントになりました。次は、応答を待つ時間そのものを体感的に短くするストリーミングに取り組みます。

---

## 4.3 ストリーミングとSSEのパース

`call_messages()` は、Claudeが回答を最後まで書き終えるまで何も返しません。長い回答では、画面が数十秒も止まったように見えます。ChatGPTやClaudeのアプリのように、文字が少しずつ流れてくる表示はどう実現しているのでしょうか。本節では、その正体であるSSEを自分でパースし、`stream_messages()` を実装します。

### ストリーミングを使うべき場面

ストリーミングとは、応答を完成を待たずに断片ごとに受け取る方式です。リクエストのボディに `"stream": true` を加えるだけで有効になります。使うべき場面は3つあります。1つ目は、人間が画面を見ながら待つ場面です。最初の文字が1秒で出れば、全体の時間が同じでも体感は大きく変わります。

2つ目は、長い出力を生成する場面です。4.1節のWARNINGで触れたとおり、無通信の接続は途中で切られることがあります。ストリーミングなら断片が流れ続けるので、この問題を避けられます。本書で `stream_messages()` の `max_tokens` 既定値を64000と大きくしているのは、このためです。3つ目は、途中経過を見て処理を早めに打ち切りたい場面です。逆に、エージェントの内部で結果だけ使う短い呼び出しなら、`call_messages()` のほうが単純で扱いやすいでしょう。

### SSEの形式

SSE（Server-Sent Events）は、サーバーからクライアントへ、1本のHTTP応答の中でイベントを次々に送る仕組みです。中身はただのテキストで、規則は3つしかありません。`event:` で始まる行がイベント名、`data:` で始まる行がデータ、そして空行が1つのイベントの区切りです。実際にAPIから届く内容を見てみましょう。

```text
event: message_start
data: {"type": "message_start", "message": {"id": "msg_01...", "type": "message", "role": "assistant", "content": [], "model": "claude-opus-5-5", "stop_reason": null, "stop_sequence": null, "usage": {"input_tokens": 25, "output_tokens": 1}}}

event: content_block_start
data: {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}}

event: ping
data: {"type": "ping"}

event: content_block_delta
data: {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Hello"}}

event: content_block_delta
data: {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "!"}}

event: content_block_stop
data: {"type": "content_block_stop", "index": 0}

event: message_delta
data: {"type": "message_delta", "delta": {"stop_reason": "end_turn", "stop_sequence": null}, "usage": {"output_tokens": 15}}

event: message_stop
data: {"type": "message_stop"}
```

`data:` の中身は、1行に収まったJSONです。JSONの `type` とイベント名は常に一致しています。つまりパーサーの仕事は、「空行まで行を貯め、`data:` の部分をJSONとして読む」ことに尽きます。

### イベントの流れ

イベントは決まった順番で届きます。最初に `message_start` で、中身が空のメッセージの骨組みが届きます。続いてコンテンツブロックごとに、3点セットが繰り返されます。`content_block_start`、何回かの `content_block_delta`、`content_block_stop` の3つです。最後に `message_delta` で `stop_reason` と出力トークン数が届き、`message_stop` で終わります。

[FIG_4_4｜フロー｜可｜ストリーミングのイベントの流れ｜message_startからブロックの3点セットを経てmessage_stopまで]

| イベント | 中身 | 組み立てでの扱い |
|---------|------|---------------|
| `message_start` | 空の `content` を持つメッセージ | 骨組みとして保存する |
| `content_block_start` | `index` とブロックの初期値 | その番号の箱を用意する |
| `content_block_delta` | `index` と断片（delta） | 箱に断片を足し込む |
| `content_block_stop` | `index` | ブロックを確定する |
| `message_delta` | `stop_reason` と累積の `usage` | 骨組みを上書きする |
| `message_stop` | なし | 完了の印にする |
| `ping` | なし | 接続維持用。無視する |
| `error` | `error.type` と `message` | 例外にして投げる |

`message_delta` の `usage` は、その時点までの累積値です。足し算ではなく上書きする点に注意してください。また公式ドキュメントは、将来新しいイベント型が追加され得るので、未知のイベントは無視するよう求めています。

### deltaの種類と組み立て方

`content_block_delta` の `delta` には、本書で扱う主な種類が4つあります。引用付きの応答では `citations_delta` も届きますが、本書のパーサーは無視します。`text_delta` は `text` の断片で、そのまま連結すれば文章になります。`thinking_delta` は思考ブロックの `thinking` の断片です。`signature_delta` は思考ブロックの改ざんを検知する署名で、ブロックの終わり直前に届きます。Opus 5.5の既定では、空の `thinking_delta` の後に `signature_delta` だけが届きます。

注意が必要なのが `input_json_delta` です。ツール呼び出しの引数が、`{"city": "Tok` と `yo"}` のように、JSONの文字列の断片として届きます。断片は単独ではJSONとして不完全なので、途中で `json.loads()` するとエラーになります。`content_block_stop` まで文字列を貯め、そこで初めてまとめてパースします。

[FIG_4_5｜概念図｜可｜indexによるブロックの組み立て｜deltaをindex別の箱に足し込み最終content配列を作る]

もう1つの要点が `index` です。各イベントの `index` は、最終的な `content` 配列での位置を表します。図4.5のように、`index` ごとに箱を分けて断片を足し込みます。最後に番号順に並べるだけで、非ストリーミングと同じ配列ができあがります。

### SSEのパーサーを書く

まず、行の並びを「イベント名とdataの組」に変換する関数を書きます。

```python
# llm_client.py（追加：SSE の行をイベントに変換する）
def _iter_sse(lines: Iterator[str]) -> Iterator[tuple[str, dict]]:
    """SSE の行を受け取り、(イベント名, dataのdict) を1件ずつ返す。"""
    event_name: str | None = None
    data_lines: list[str] = []
    for line in lines:
        if line == "":  # 空行 = 1イベントの終わり
            if data_lines:
                data = json.loads("\n".join(data_lines))
                yield event_name or data.get("type", ""), data
            event_name, data_lines = None, []
            continue
        if line.startswith(":"):  # コメント行は読み飛ばす
            continue
        name, _, value = line.partition(":")
        if value.startswith(" "):  # コロン直後の空白1つは区切り
            value = value[1:]
        if name == "event":
            event_name = value
        elif name == "data":
            data_lines.append(value)
        # id: / retry: は本APIでは使わないので無視する
    if data_lines:  # 末尾に空行がないまま終わった場合
        data = json.loads("\n".join(data_lines))
        yield event_name or data.get("type", ""), data
```

この関数はジェネレーターで、`yield` のたびにイベントを1件返します。全イベントを貯めてから返すのではないので、届いた端から処理できます。`line.partition(":")` は、最初のコロンで行を2つに分けるメソッドです。JSONの中にもコロンがあるので、`split(":")` では壊れてしまいます。SSEの規格では `data:` が複数行に分かれることもあるため、改行で連結してからパースしています。

### 最終メッセージを組み立てる

次に、イベントを受け取ってメッセージを組み立てるクラスを書きます。状態（骨組み・ブロック・JSONの断片）を持ち回るので、関数ではなくクラスにしています。

```python
# llm_client.py（追加：イベントからメッセージを組み立てる）
class _StreamAccumulator:
    """SSE イベントを受け取り、最終的なメッセージ dict を組み立てる。"""

    def __init__(
        self,
        request_id: str | None,
        on_text: Callable[[str], None] | None,
    ) -> None:
        self.request_id = request_id
        self.on_text = on_text
        self.message: dict[str, Any] = {}
        self.blocks: dict[int, dict[str, Any]] = {}  # index → ブロック
        self.json_parts: dict[int, list[str]] = {}  # index → JSON 断片
        self.finished = False  # message_stop を受け取ったか

    def handle(self, event: str, data: dict) -> None:
        """1イベント分の処理を行う。"""
        match event:
            case "message_start":
                self.message = data["message"]  # id・model・usage など
            case "content_block_start":
                self.blocks[data["index"]] = dict(data["content_block"])
            case "content_block_delta":
                self._apply_delta(data["index"], data["delta"])
            case "content_block_stop":
                self._finish_block(data["index"])
            case "message_delta":
                self.message.update(data.get("delta", {}))  # stop_reason など
                usage = self.message.setdefault("usage", {})
                usage.update(data.get("usage", {}))  # 累積値で上書き
            case "message_stop":
                self.finished = True
            case "ping":
                pass  # 接続維持用。何もしない
            case "error":
                raise _make_error(None, data, self.request_id)
            case _:
                logger.debug("未知のイベントを無視: %s", event)

    def _apply_delta(self, index: int, delta: dict) -> None:
        """delta の種類に応じて、ブロックへ断片を足し込む。"""
        block = self.blocks[index]
        match delta.get("type"):
            case "text_delta":
                block["text"] = block.get("text", "") + delta["text"]
                if self.on_text:
                    self.on_text(delta["text"])  # 逐次表示用に渡す
            case "input_json_delta":
                self.json_parts.setdefault(index, []).append(delta["partial_json"])
            case "thinking_delta":
                block["thinking"] = block.get("thinking", "") + delta["thinking"]
            case "signature_delta":
                block["signature"] = block.get("signature", "") + delta["signature"]
            case other:
                logger.debug("未知の delta を無視: %s", other)

    def _finish_block(self, index: int) -> None:
        """ブロックの終わり。JSON 断片があれば連結してパースする。"""
        parts = self.json_parts.pop(index, None)
        if parts is not None:
            raw = "".join(parts)
            self.blocks[index]["input"] = json.loads(raw) if raw else {}

    def result(self) -> dict:
        """index 順にブロックを並べ、非ストリーミングと同じ形で返す。"""
        if not self.finished:
            raise APIConnectionError(
                "message_stop の前にストリームが終了しました",
                request_id=self.request_id,
            )
        self.message["content"] = [self.blocks[i] for i in sorted(self.blocks)]
        return self.message
```

`handle()` は、Python 3.10以降の `match` 文でイベント名ごとに処理を振り分けます。さきほどのイベントの表と1対1に対応しているので、見比べながら読んでください。`content_block_start` で受け取るのは、ブロックの初期値です。`text` なら空文字、`tool_use` なら空の `input` を持っています。そこへ `_apply_delta()` が断片を足し込みます。

`input_json_delta` だけは、ブロックに直接足さず `json_parts` に貯めます。`_finish_block()` で連結し、ここで初めて `json.loads()` します。断片が空文字のまま終わる、つまり引数のないツールの場合は空の辞書にします。`error` イベントでは、4.1節の `_make_error()` に `status=None` を渡します。そして、`error.type` から例外クラスを選ばせます。

`error` イベントは、たとえば混雑時に次の形で届きます。

```text
event: error
data: {"type": "error", "error": {"type": "overloaded_error", "message": "Overloaded"}}
```

非ストリーミングなら529に相当する失敗です。ステータスはありませんが、`_TYPE_TO_ERROR` の表により `OverloadedError` として投げられます。呼び出し側は、非ストリーミングと同じ `except` 節で扱えるわけです。

`result()` は、`message_stop` を受け取っていなければ例外にします。ネットワークが途中で切れて、ストリームが中途半端に終わった場合の検知です。この確認がないと、途中までの不完全な応答を正常な結果として扱ってしまいます。

### stream_messages() を実装する

部品がそろったので、公開関数 `stream_messages()` を書きます。引数は `call_messages()` と同じで、`on_text` が加わります。

```python
# llm_client.py（追加：ストリーミング呼び出し）
def stream_messages(
    messages: list[dict],
    *,
    system: str | list[dict] | None = None,
    tools: list[dict] | None = None,
    model: str = MODEL,
    max_tokens: int = 64000,
    tool_choice: dict | None = None,
    output_config: dict | None = None,
    extra: dict | None = None,
    max_retries: int = 4,
    on_text: Callable[[str], None] | None = None,
) -> dict:
    """ストリーミングで呼び出し、テキストを on_text に逐次渡す。

    戻り値は call_messages() と同じ形のメッセージ dict。
    """
    body = _build_body(
        messages,
        system=system,
        tools=tools,
        model=model,
        max_tokens=max_tokens,
        tool_choice=tool_choice,
        output_config=output_config,
        extra=extra,
        stream=True,
    )
    # 接続して 200 を受け取るまでは、通常どおりリトライの対象
    response = _request_with_retry(
        API_URL, body, stream=True, max_retries=max_retries
    )
    request_id = response.headers.get("request-id")
    acc = _StreamAccumulator(request_id, on_text)
    try:
        for event, data in _iter_sse(response.iter_lines()):
            acc.handle(event, data)
    except httpx.TransportError as exc:  # 受信途中の切断・読み取りタイムアウト
        raise APIConnectionError(
            f"ストリーム受信中に失敗しました: {type(exc).__name__}",
            request_id=request_id,
        ) from exc
    finally:
        response.close()  # 接続をプールへ返す
    return acc.result()
```

`_request_with_retry()` に `stream=True` を渡すと、200のヘッダーを受け取った時点で応答が返ります。`response.iter_lines()` は、本文を届いた端から1行ずつ取り出すhttpxのメソッドです。これを `_iter_sse()` に流し込み、イベントごとに `acc.handle()` を呼びます。`finally` の `response.close()` は、例外が起きても必ず接続をプールに返すためのものです。

重要な設計判断として、ストリームの途中で起きた失敗はリトライしません。`on_text` で画面に出した文字は取り消せないからです。最初から再送すると、同じ文章が二重に表示されてしまいます。途中で失敗したときは例外を呼び出し側に伝え、やり直すかどうかは呼び出し側が決めます。公式ドキュメントでは、受信済みの部分を user メッセージに含めて「続きから書いて」と依頼する回復方法が紹介されています。

### APIを呼ばずにパーサーを試す

本物のAPIで試す前に、手書きのSSEでパーサーを確かめておきましょう。ツール呼び出しの引数が断片で届く場面を再現します。料金がかからず、何度でも同じ結果になるので、パーサーを改造したときの確認にも便利です。

```python
# sse_demo.py（新規作成：4.3節の動作確認用。APIは呼ばない）
from llm_client import _iter_sse, _StreamAccumulator, get_tool_uses

# APIから届くSSEを手書きで再現する（空行がイベントの区切り）
RAW = '''event: message_start
data: {"type": "message_start", "message": {"id": "msg_demo", "role": "assistant", "content": [], "model": "claude-opus-5-5", "usage": {"input_tokens": 30, "output_tokens": 1}}}

event: content_block_start
data: {"type": "content_block_start", "index": 0, "content_block": {"type": "tool_use", "id": "toolu_demo", "name": "get_weather", "input": {}}}

event: content_block_delta
data: {"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": "{\\"city\\": \\"Tok"}}

event: content_block_delta
data: {"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": "yo\\"}"}}

event: content_block_stop
data: {"type": "content_block_stop", "index": 0}

event: message_delta
data: {"type": "message_delta", "delta": {"stop_reason": "tool_use"}, "usage": {"output_tokens": 40}}

event: message_stop
data: {"type": "message_stop"}

'''

acc = _StreamAccumulator(request_id=None, on_text=None)
for event, data in _iter_sse(iter(RAW.splitlines())):  # 行の並びとして渡す
    print("event:", event)
    acc.handle(event, data)
message = acc.result()
print("stop_reason:", message["stop_reason"])
print("tool_uses:", get_tool_uses(message))
```

```bash
# agent-from-scratch/ で実行する（通信は発生しない）
uv run python sse_demo.py
```

```text
event: message_start
event: content_block_start
event: content_block_delta
event: content_block_delta
event: content_block_stop
event: message_delta
event: message_stop
stop_reason: tool_use
tool_uses: [{'type': 'tool_use', 'id': 'toolu_demo', 'name': 'get_weather', 'input': {'city': 'Tokyo'}}]
```

`{"city": "Tok` と `yo"}` という2つの断片が、`content_block_stop` の時点で連結されました。そして、`{'city': 'Tokyo'}` という辞書に変わっています。`input` が文字列ではなく辞書になっている点が重要です。第5章では、この辞書をそのままツール関数の引数に渡します。`RAW` の最後の `message_stop` を消して実行することも試してみてください。`result()` が `APIConnectionError` を出すことを確かめられます。

### 動作を確認する

```python
# stream_demo.py（新規作成：4.3節の動作確認用）
import logging

from llm_client import extract_text, stream_messages

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)


received: list[str] = []  # 届いた断片を記録しておく（最後の比較用）


def show(text: str) -> None:
    """届いた断片を改行せずにすぐ表示する。"""
    received.append(text)
    print(text, end="", flush=True)


response = stream_messages(
    [{"role": "user", "content": "SSEとは何かを3文で説明してください。"}],
    on_text=show,
)
print()  # 最後に改行する
print("stop_reason:", response["stop_reason"])
print("blocks:", [block["type"] for block in response["content"]])
print("usage:", response["usage"])
print("同じ文字列か:", "".join(received) == extract_text(response))  # 逐次表示と戻り値の一致
```

```bash
# agent-from-scratch/ で実行する
uv run python stream_demo.py
```

```text
SSE（Server-Sent Events）は、サーバーからクライアントへ一方向にイベントを送り続ける仕組みです。……
stop_reason: end_turn
blocks: ['thinking', 'text']
usage: {'input_tokens': 24, 'output_tokens': 162}
同じ文字列か: True
```

実行すると、1行目の文章が少しずつ流れるように表示されます。`print()` の `flush=True` を忘れると、出力がバッファーに溜まり、まとめて表示されてしまいます。その後の行で、戻り値が `call_messages()` と同じ形の `dict` になっていることが分かります。`thinking` ブロックも署名付きで復元されているので、この `content` はそのまま会話履歴に追加できます。第3章で学んだとおり、思考ブロックは削除も改変もせずに履歴へ戻す必要があります。`signature_delta` を取りこぼすと署名が欠けたブロックになり、次のリクエストが400エラーになります。主な4種類のdeltaをすべて組み立てているのは、このためです。`usage` の実際のキーは、ここに示した例より多いことがあります。

> **WARNING: よくあるつまずき**
> `json.decoder.JSONDecodeError` が出ることがあります。その場合は、`input_json_delta` の断片を途中でパースしていないか確認してください。また、`response.iter_text()` は行単位ではなく任意の長さで区切って返します。そのため、SSEのパースには `iter_lines()` を使います。

これで、非ストリーミングとストリーミングのどちらでも、同じ形の結果を受け取れるようになりました。

---

## 4.4 ログとトークン・コスト計測

エージェントを動かしていると、「さっきの処理で何回APIを呼んだのか」「いくらかかったのか」が気になってきます。ループが想定外に回り続けて、気づいたら料金が膨らんでいた、という事故は珍しくありません。本節では、呼び出しの記録を `logging` で残す仕組みを組み込みます。あわせて、`usage` と単価表から1回ごとのコストを計測します。

### printではなくloggingを使う理由

`logging` は、Pythonの標準ライブラリにある記録の仕組みです。`print()` と違い、記録に重要度（レベル）を付けられます。`DEBUG`・`INFO`・`WARNING`・`ERROR` などのレベルがあり、どこまで表示するかを後から切り替えられます。開発中は `INFO` まで見て、本番では `WARNING` 以上だけをファイルに残す、といった運用がコードを変えずにできます。

本書のモジュールは `logging.getLogger("llm_client")` で専用のロガーを取得していました。ライブラリ側は記録を「出す」だけで、表示先や形式は決めません。それを決めるのは、`logging.basicConfig()` を呼ぶアプリケーション側です。ライブラリが勝手に表示形式を決めると、ユーザーのログ設定と衝突するからです。何も設定しなければ、`WARNING` 以上だけが標準エラーに表示されます。

### ログに残すもの、残さないもの

ログには、後から問題を調べるのに必要な情報だけを残します。

| 残す | 残さない |
|-----|---------|
| `request-id`（問い合わせ・突き合わせ用） | APIキー（`x-api-key` ヘッダー） |
| モデル名・ストリーミングの有無 | プロンプトや応答の本文 |
| 所要時間・`stop_reason` | ツールの入出力に含まれる個人情報 |
| トークン数4種とコスト | |

本文を残さないのは、ユーザーの個人情報や社外秘が含まれ得るからです。ログファイルは多くの人が見られる場所に置かれがちで、漏えいの経路になります。一方、`request-id` があれば、Anthropicのサポートに問い合わせるときにリクエストを特定できます。本文がなくても、トークン数と所要時間があれば性能やコストの問題は十分に追えます。

```python
# llm_client.py（追加：呼び出し1回分のログ）
def _log_call(
    message: dict, request_id: str | None, elapsed: float, cost: float, streamed: bool
) -> None:
    """1回の呼び出しの要約を INFO で記録する（本文・キーは出さない）。"""
    usage = message.get("usage", {})
    logger.info(
        "request_id=%s model=%s stream=%s elapsed=%.2fs stop=%s "
        "in=%d out=%d cache_write=%d cache_read=%d cost=$%.4f",
        request_id,
        message.get("model"),
        streamed,
        elapsed,
        message.get("stop_reason"),
        usage.get("input_tokens", 0),
        usage.get("output_tokens", 0),
        usage.get("cache_creation_input_tokens") or 0,
        usage.get("cache_read_input_tokens") or 0,
        cost,
    )
```

`logger.info()` には、f文字列ではなく `%s` の書式と引数を別々に渡しています。こうすると、ログが表示されない設定のときは文字列の組み立て自体が省かれます。また、`キー=値` の形で1行に並べておくと、後から `grep` や集計スクリプトで扱いやすくなります。キャッシュのトークン数は `None` のこともあるので、`or 0` で数値にそろえています。

### usageの4種類のトークン

第3章で見たとおり、レスポンスの `usage` には4種類のトークン数が入っています。

| フィールド | 意味 |
|-----------|------|
| `input_tokens` | キャッシュを使わずに処理した入力（最後のキャッシュ区切りより後ろ） |
| `output_tokens` | 出力したトークン（思考の分も含む） |
| `cache_creation_input_tokens` | 今回キャッシュに書き込んだ入力 |
| `cache_read_input_tokens` | キャッシュから読み出した入力 |

キャッシュを使うと、`input_tokens` は入力全体ではなくなります。入力の合計は、3つの入力系フィールドの和です。たとえば20万トークンの文書をキャッシュから読み、50トークンの質問を足したとします。この場合、`input_tokens` は50になります。この点を知らずに `input_tokens` だけを見ると、入力量を大きく見誤ります。また、思考ブロックの中身が空で返ってきても、思考に使ったトークンは `output_tokens` に含まれ、課金されます。

[FIG_4_6｜概念図｜可｜usageの4種類のトークン｜入力全体をキャッシュ読み取り・書き込み・通常入力に分けた帯と出力]

図4.6のように、入力は「キャッシュから読んだ部分」「今回書き込んだ部分」「それ以降の通常の入力」の3つに分かれます。この3つの合計が、モデルが実際に読んだ入力の量です。なお、レート制限の入力トークン数に数えられるのは、キャッシュ読み取りを除いた2つだけです。キャッシュは料金だけでなく、利用枠の節約にも効きます。

### ログをファイルに残す

長時間動くエージェントでは、画面に流れたログを後から見返せません。アプリケーション側の設定を変えるだけで、ログをファイルにも残せます。`llm_client.py` には手を入れない点に注目してください。

```python
# main.py（例：ログを画面とファイルの両方に出す設定）
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",  # 時刻も付ける
    handlers=[
        logging.StreamHandler(),  # 画面（標準エラー）
        logging.FileHandler("agent.log", encoding="utf-8"),  # ファイル
    ],
)
logging.getLogger("httpx").setLevel(logging.WARNING)  # 通信ごとのログは抑える
```

`handlers` に複数の出力先を並べると、同じログが両方に書かれます。`asctime` を書式に加えると、各行に時刻が付き、処理の順番や待ち時間を追いやすくなります。`agent.log` は `.gitignore` に加えておきましょう。本文を残さない設計でも、`request-id` などの運用情報はリポジトリに入れるべきではありません。

### 料金の計算方法

料金は、トークンの種類ごとに異なる単価を掛けて合計します。単価は100万トークン（1 MTok）あたりのドルで示されます。

| モデル | 入力 | 出力 | キャッシュ書き込み（5分） | キャッシュ読み取り |
|-------|-----|-----|---------------|---------------|
| `claude-opus-5-5` | $4 | $20 | $5（1.25倍） | $0.20（0.05倍） |
| `claude-sonnet-5-5` | $2 | $10 | $2.50（1.25倍） | $0.10（0.05倍） |
| `claude-haiku-5-5`（10万tok以下） | $0.10 | $0.50 | $0.125（1.25倍） | $0.01（0.1倍） |

キャッシュの書き込みは入力単価の1.25倍、読み取りは基本0.1倍です。ただしOpus 5.5とSonnet 5.5の読み取りは、さらに安い0.05倍に設定されています。倍率をコードに持たせると、こうしたモデルごとの例外で計算を誤ります。そこで本書の単価表は、倍率ではなく種類ごとの単価をそのまま書く形にします。Haiku 5.5は、プロンプトが10万トークンを超えると全種類の単価が上がる点にも対応します。

> **NOTE**: キャッシュの保持時間を1時間にした書き込みは、入力単価の2倍です。本書の `CostTracker` は5分キャッシュの単価で計算します。また単価は改定されることがあるので、公式の料金ページで定期的に確認し、`PRICES` を更新してください。

### CostTrackerを実装する

```python
# llm_client.py（追加：コスト計測）
# 単価表（USD / 100万トークン）。cache_write は5分キャッシュの書き込み単価
PRICES: dict[str, dict[str, float]] = {
    "claude-opus-5-5": {"input": 4.00, "output": 20.00, "cache_write": 5.00, "cache_read": 0.20},
    "claude-sonnet-5-5": {"input": 2.00, "output": 10.00, "cache_write": 2.50, "cache_read": 0.10},
    "claude-haiku-5-5": {"input": 0.10, "output": 0.50, "cache_write": 0.125, "cache_read": 0.01},
}
# Haiku 5.5 はプロンプトが10万トークンを超えると高い単価になる
LONG_PROMPT_THRESHOLD = 100_000
LONG_PROMPT_PRICES: dict[str, dict[str, float]] = {
    "claude-haiku-5-5": {"input": 0.50, "output": 2.50, "cache_write": 0.625, "cache_read": 0.05},
}


def _find_prices(model: str, prompt_tokens: int) -> dict[str, float] | None:
    """モデル名とプロンプト長から単価表の行を探す。"""
    table = PRICES
    if prompt_tokens > LONG_PROMPT_THRESHOLD and model in LONG_PROMPT_PRICES:
        table = LONG_PROMPT_PRICES
    if model in table:
        return table[model]
    for name, prices in table.items():  # 接尾辞付きのIDにも対応
        if model.startswith(name):
            return prices
    return None


@dataclass
class CostTracker:
    """usage からコストを計算し、呼び出しをまたいで累積する。"""

    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    total_usd: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def add(self, response: dict) -> float:
        """1回分の usage を加算し、その回のコスト（USD）を返す。"""
        usage = response.get("usage", {})
        inp = usage.get("input_tokens") or 0
        out = usage.get("output_tokens") or 0
        cw = usage.get("cache_creation_input_tokens") or 0
        cr = usage.get("cache_read_input_tokens") or 0
        model = response.get("model", "")
        prices = _find_prices(model, inp + cw + cr)
        if prices is None:
            logger.warning("単価表にないモデルです（コスト0で記録）: %s", model)
            cost = 0.0
        else:
            cost = (
                inp * prices["input"]
                + out * prices["output"]
                + cw * prices["cache_write"]
                + cr * prices["cache_read"]
            ) / 1_000_000
        with self._lock:  # 複数スレッドから呼ばれても数がずれないように
            self.calls += 1
            self.input_tokens += inp
            self.output_tokens += out
            self.cache_creation_input_tokens += cw
            self.cache_read_input_tokens += cr
            self.total_usd += cost
        return cost

    def summary(self) -> str:
        """累積結果を1行の文字列にまとめる。"""
        return (
            f"calls={self.calls} input={self.input_tokens:,} "
            f"output={self.output_tokens:,} "
            f"cache_write={self.cache_creation_input_tokens:,} "
            f"cache_read={self.cache_read_input_tokens:,} "
            f"total=${self.total_usd:.4f}"
        )

    def reset(self) -> None:
        """集計を0に戻す。"""
        with self._lock:
            self.calls = self.input_tokens = self.output_tokens = 0
            self.cache_creation_input_tokens = self.cache_read_input_tokens = 0
            self.total_usd = 0.0


tracker = CostTracker()  # モジュール共通の集計器
```

`_find_prices()` は、モデル名から単価表の行を探します。完全一致がなければ前方一致で探すので、将来IDに接尾辞が付いても対応できます。見つからない場合は例外にせず、警告を出してコスト0で記録します。コスト計測の失敗で、本来の処理まで止めるべきではないからです。

`CostTracker` は `@dataclass` で定義しています。フィールドを並べるだけで、初期化のコードを自動で作ってくれる仕組みです。`add()` は1回分の `usage` からコストを計算し、累積したうえでその回のコストを返します。`threading.Lock` で加算を守っているのは、第6章以降で複数のスレッドから同時に呼ばれる可能性があるためです。

手計算で確かめてみましょう。Opus 5.5で入力1,200、出力350トークンの場合を考えます。入力は1,200×4÷100万＝0.0048ドル、出力は350×20÷100万＝0.007ドルです。合計0.0118ドルになります。ここに1万トークンのキャッシュ読み取りが加わると、1万×0.20÷100万＝0.002ドルが足されます。同じ1万トークンを通常の入力で送れば0.04ドルなので、20分の1で済む計算です。

### 呼び出し関数に組み込む

最後に、`call_messages()` と `stream_messages()` に計測とログを組み込みます。どちらも、送信の前に時刻を測り、結果を受け取ったら `tracker.add()` と `_log_call()` を呼びます。

```python
# llm_client.py（更新：call_messages の完成版）
def call_messages(
    messages: list[dict],
    *,
    system: str | list[dict] | None = None,
    tools: list[dict] | None = None,
    model: str = MODEL,
    max_tokens: int = 16000,
    tool_choice: dict | None = None,
    output_config: dict | None = None,
    extra: dict | None = None,
    max_retries: int = 4,
) -> dict:
    """Messages API を1回呼び出し、レスポンスJSON（dict）を返す。"""
    body = _build_body(
        messages,
        system=system,
        tools=tools,
        model=model,
        max_tokens=max_tokens,
        tool_choice=tool_choice,
        output_config=output_config,
        extra=extra,
        stream=False,
    )
    started = time.perf_counter()  # リトライの待ち時間も含めて測る
    response = _request_with_retry(
        API_URL, body, stream=False, max_retries=max_retries
    )
    message: dict = response.json()
    elapsed = time.perf_counter() - started
    cost = tracker.add(message)  # 共通の集計器に加算
    _log_call(message, response.headers.get("request-id"), elapsed, cost, False)
    return message
```

```python
# llm_client.py（更新：stream_messages の完成版）
def stream_messages(
    messages: list[dict],
    *,
    system: str | list[dict] | None = None,
    tools: list[dict] | None = None,
    model: str = MODEL,
    max_tokens: int = 64000,
    tool_choice: dict | None = None,
    output_config: dict | None = None,
    extra: dict | None = None,
    max_retries: int = 4,
    on_text: Callable[[str], None] | None = None,
) -> dict:
    """ストリーミングで呼び出し、テキストを on_text に逐次渡す。

    戻り値は call_messages() と同じ形のメッセージ dict。
    """
    body = _build_body(
        messages,
        system=system,
        tools=tools,
        model=model,
        max_tokens=max_tokens,
        tool_choice=tool_choice,
        output_config=output_config,
        extra=extra,
        stream=True,
    )
    started = time.perf_counter()
    response = _request_with_retry(
        API_URL, body, stream=True, max_retries=max_retries
    )
    request_id = response.headers.get("request-id")
    acc = _StreamAccumulator(request_id, on_text)
    try:
        for event, data in _iter_sse(response.iter_lines()):
            acc.handle(event, data)
    except httpx.TransportError as exc:  # 受信途中の切断・読み取りタイムアウト
        raise APIConnectionError(
            f"ストリーム受信中に失敗しました: {type(exc).__name__}",
            request_id=request_id,
        ) from exc
    finally:
        response.close()  # 接続をプールへ返す
    message = acc.result()
    elapsed = time.perf_counter() - started
    cost = tracker.add(message)
    _log_call(message, request_id, elapsed, cost, True)
    return message
```

`time.perf_counter()` は、経過時間の計測に向いた高精度の時計です。開始時刻をリトライの前に取っているので、`elapsed` には待ち時間も含まれます。ユーザーが実際に待たされた時間を記録したいからです。ストリーミングでは、最終メッセージが組み上がった時点でまとめて計測します。

### 動作を確認する

```python
# cost_demo.py（新規作成：4.4節の動作確認用）
import logging

from llm_client import FAST_MODEL, call_messages, tracker

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)

question = [{"role": "user", "content": "指数バックオフを1文で説明してください。"}]
call_messages(question, max_tokens=1000)  # 既定の Opus 5.5
call_messages(question, model=FAST_MODEL, max_tokens=1000)  # Haiku 5.5
print(tracker.summary())  # 2回分の累積
```

```bash
# agent-from-scratch/ で実行する
uv run python cost_demo.py
```

```text
INFO llm_client: request_id=req_011CZa... model=claude-opus-5-5 stream=False elapsed=3.84s stop=end_turn in=26 out=118 cache_write=0 cache_read=0 cost=$0.0025
INFO llm_client: request_id=req_011CZb... model=claude-haiku-5-5 stream=False elapsed=1.12s stop=end_turn in=26 out=64 cache_write=0 cache_read=0 cost=$0.0000
calls=2 input=52 output=182 cache_write=0 cache_read=0 total=$0.0025
```

同じ質問でも、Haiku 5.5のコストはOpus 5.5の数十分の1で、表示の桁では0ドルに見えるほどです。第9章のルーティングや第10章のワーカーで軽量モデルを使い分ける理由が、数字で実感できるでしょう。最後の `summary()` の1行は、第10章で予算の上限を管理するときにも使います。

> **POINT**: `tracker` はモジュール全体で1つだけの集計器です。どこから `call_messages()` を呼んでも、同じ `tracker` に加算されます。タスクごとに集計したい場合は、開始時に `tracker.reset()` を呼んでから実行してください。

> **WARNING: コスト計測の限界**
> `CostTracker` の値は、あくまで手元での推定です。単価の改定、1時間キャッシュ、データの処理地域の指定による割増などは反映されません。請求額の正は、Claude Console（クロード・コンソール）の利用状況の画面です。推定値は「ループが暴走していないか」を早く知るための目安として使ってください。そのうえで、Consoleの利用上限（spend limit）と組み合わせて身を守ってください。

---

## COLUMN: SDKは何をしてくれているのか

本章では、公式のPython SDKを使わずにクライアントを自作しました。では、SDKを使えば何が手に入るのでしょうか。本章の実装と対応づけて整理します。

| 機能 | 本章の自作クライアント | 公式SDK |
|-----|-------------------|--------|
| 接続の再利用・タイムアウト | `httpx.Client` を共有、`read` 600秒 | 同様（10分を超えそうな非ストリーミングは送信前にエラーにする） |
| 型付きの例外 | `APIError` と子クラス | 同様の例外クラス階層 |
| 自動リトライ | 既定4回、`retry-after` 優先、フルジッター | 既定2回、`retry-after` を尊重 |
| SSEのパースと組み立て | `_iter_sse()` と `_StreamAccumulator` | ストリーミング用ヘルパーと最終メッセージの取得 |
| 型定義 | `dict` のまま | リクエスト・レスポンスの型付きオブジェクト |
| 非同期 | 第8章で `acall_messages()` を追加 | 同期・非同期の両方を標準で提供 |
| コスト計測 | `CostTracker` | なし（`usage` は返る） |

表を見ると、SDKの中核機能は本章でほぼ再現できていることが分かります。SDKが優れているのは、型定義による入力補完、新機能への素早い追従、そして多くのユーザーに揉まれた堅牢さです。逆に、コスト計測のように自分の用途に合わせた機能は、自作のほうが自由に組み込めます。

筆者の考えでは、仕組みを理解する段階では自作、実務で素早く作る段階ではSDK、という使い分けが合理的です。自作を経験しておくと、SDKで想定外の挙動に出会ったときも、内部で何が起きているかを推測できます。本書が最後まで自作クライアントを使うのは、エージェントの動きをHTTPの1往復まで見通せるようにするためです。

判断の目安を挙げておきます。依存ライブラリを最小にしたい場合や、独自のログ・計測・テスト用の差し替えを細かく制御したい場合は、自作が向いています。チームで長く保守する製品で、新しいAPI機能をすぐに使いたい場合は、SDKが向いています。どちらを選んでも、送っているのは本章で見たHTTPリクエストそのものです。中身を知っていれば、選択を後から変えることも難しくありません。

---

## 完成版の llm_client.py

本章で作った `llm_client.py` の全体を掲載します。節ごとに示したコードを1つのファイルにまとめ、読みやすいように関数の並びを整理したものです。手元のファイルと関数の順番が違っていても、動作は変わりません。抜けている関数や、`call_messages()`・`stream_messages()` の差し替え忘れがないかを確認してください。第5章以降は、このファイルを `import` して使います。

```python
# llm_client.py
"""Claude Messages API を httpx で直接呼び出す共通クライアント（第4章 完成版）。"""
from __future__ import annotations

import json
import logging
import os
import random
import threading
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Any

import httpx
from dotenv import load_dotenv

# ---- 設定値 -------------------------------------------------------------
load_dotenv()  # .env の ANTHROPIC_API_KEY を環境変数に読み込む（モジュールで1回だけ）

API_URL = "https://api.anthropic.com/v1/messages"
API_BASE = "https://api.anthropic.com/v1"
API_VERSION = "2026-10-21"
MODEL = "claude-opus-5-5"  # 既定モデル
FAST_MODEL = "claude-haiku-5-5"  # 分類・要約・ワーカー用

# 2026-10-21 版で送ってはいけないパラメータ（送ると 400 になる）
FORBIDDEN_PARAMS = frozenset({"temperature", "top_p", "top_k"})

# リトライの設定
RETRYABLE_STATUS = frozenset({408, 409, 429})  # 5xx はこれとは別に判定する
BASE_DELAY = 1.0  # バックオフの基準秒数
MAX_DELAY = 30.0  # 1回の待ち時間の上限（秒）
MAX_RETRY_AFTER = 60.0  # retry-after を信用する上限（秒）
MAX_TOTAL_WAIT = 120.0  # 1回の呼び出しで待つ合計時間の上限（秒）

logger = logging.getLogger("llm_client")

# 接続プールを持つクライアントをモジュール全体で1つだけ作り、使い回す
_client = httpx.Client(timeout=httpx.Timeout(600.0, connect=10.0))


# ---- 例外クラス -----------------------------------------------------------
class APIError(Exception):
    """Claude API 呼び出しの失敗を表す基底クラス。"""

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        error_type: str = "api_error",
        request_id: str | None = None,
        error_code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message  # error.message（人間向けの説明）
        self.status = status  # HTTPステータス（接続エラーは None）
        self.error_type = error_type  # error.type（機械判定用）
        self.request_id = request_id  # 問い合わせ用の request-id
        self.error_code = error_code  # error.details.error_code（あれば）

    def __str__(self) -> str:
        return (
            f"[{self.status} {self.error_type}] {self.message}"
            f" (request_id={self.request_id})"
        )


class InvalidRequestError(APIError):  # 400
    pass


class AuthenticationError(APIError):  # 401
    pass


class PermissionDeniedError(APIError):  # 403
    pass


class NotFoundError(APIError):  # 404
    pass


class RequestTooLargeError(APIError):  # 413
    pass


class RateLimitError(APIError):  # 429
    pass


class InternalServerError(APIError):  # 500 などの 5xx
    pass


class OverloadedError(APIError):  # 529
    pass


class APIConnectionError(APIError):  # 接続失敗・タイムアウト（status=None）
    pass


# HTTPステータス → 例外クラス
_STATUS_TO_ERROR: dict[int, type[APIError]] = {
    400: InvalidRequestError,
    401: AuthenticationError,
    403: PermissionDeniedError,
    404: NotFoundError,
    413: RequestTooLargeError,
    429: RateLimitError,
    529: OverloadedError,
}

# error.type → 例外クラス（ステータスのない SSE の error イベント用）
_TYPE_TO_ERROR: dict[str, type[APIError]] = {
    "invalid_request_error": InvalidRequestError,
    "authentication_error": AuthenticationError,
    "permission_error": PermissionDeniedError,
    "not_found_error": NotFoundError,
    "request_too_large": RequestTooLargeError,
    "rate_limit_error": RateLimitError,
    "api_error": InternalServerError,
    "timeout_error": InternalServerError,  # 504 と同じ扱い
    "overloaded_error": OverloadedError,
}


def _error_class(status: int | None, error_type: str) -> type[APIError]:
    """ステータスを優先し、なければ error.type から例外クラスを選ぶ。"""
    if status is not None:
        if status in _STATUS_TO_ERROR:
            return _STATUS_TO_ERROR[status]
        if status >= 500:
            return InternalServerError
    return _TYPE_TO_ERROR.get(error_type, APIError)


def _make_error(
    status: int | None, body: Any, request_id: str | None
) -> APIError:
    """エラーボディ（dict）から適切な例外オブジェクトを作る。"""
    err = body.get("error", {}) if isinstance(body, dict) else {}
    error_type = err.get("type", "unknown_error")
    message = err.get("message") or f"HTTP {status}"
    details = err.get("details") or {}
    if isinstance(body, dict):
        request_id = request_id or body.get("request_id")
    cls = _error_class(status, error_type)
    return cls(
        message,
        status=status,
        error_type=error_type,
        request_id=request_id,
        error_code=details.get("error_code"),
    )


def _error_from_response(response: httpx.Response) -> APIError:
    """エラーレスポンス（HTTP 4xx/5xx）を例外に変換する。"""
    try:
        body = response.json()
    except ValueError:  # JSON でない（プロキシのHTMLなど）
        body = {"error": {"message": response.text[:200]}}
    return _make_error(
        response.status_code, body, response.headers.get("request-id")
    )


# ---- リクエストの組み立て -------------------------------------------------
def build_headers() -> dict[str, str]:
    """認証・バージョン・形式の3つの必須ヘッダーを返す。"""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY が未設定です。.env を確認してください。"
        )
    return {
        "x-api-key": api_key,
        "anthropic-version": API_VERSION,
        "content-type": "application/json",
    }


def _build_body(
    messages: list[dict],
    *,
    system: str | list[dict] | None,
    tools: list[dict] | None,
    model: str,
    max_tokens: int,
    tool_choice: dict | None,
    output_config: dict | None,
    extra: dict | None,
    stream: bool,
) -> dict[str, Any]:
    """リクエストボディを組み立てる。None の項目は送らない。"""
    body: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system is not None:
        body["system"] = system
    if tools:
        body["tools"] = tools
    if tool_choice is not None:
        body["tool_choice"] = tool_choice
    if output_config is not None:
        body["output_config"] = output_config
    if extra:
        bad = FORBIDDEN_PARAMS & extra.keys()
        if bad:  # 送る前に止める（APIに400を返させない）
            raise ValueError(f"このAPIバージョンでは使えません: {sorted(bad)}")
        body.update(extra)
    if stream:
        body["stream"] = True
    return body


# ---- リトライ -------------------------------------------------------------
def _is_retryable(error: APIError) -> bool:
    """再試行すれば成功する見込みがあるエラーかを判定する。"""
    if isinstance(error, APIConnectionError):
        return True  # 接続失敗・タイムアウト
    if error.error_code == "enforced_spend_limit_reached":
        return False  # 月の利用上限。待っても翌月まで回復しない
    status = error.status or 0
    return status in RETRYABLE_STATUS or status >= 500


def _retry_delay(attempt: int, response: httpx.Response | None) -> float:
    """次の再試行までの待ち秒数を決める（retry-after 優先）。"""
    if response is not None:
        retry_after = response.headers.get("retry-after")
        if retry_after:
            try:
                return min(max(float(retry_after), 0.0), MAX_RETRY_AFTER)
            except ValueError:
                pass  # 日付形式などは無視して、バックオフに任せる
    # 指数バックオフ（1, 2, 4, 8, ... 秒、上限 MAX_DELAY）＋フルジッター
    backoff = min(MAX_DELAY, BASE_DELAY * (2**attempt))
    return random.uniform(0, backoff)


def _request_with_retry(
    url: str, body: dict[str, Any], *, stream: bool, max_retries: int
) -> httpx.Response:
    """POST を送り、一時的な失敗なら待ってから再試行する。"""
    headers = build_headers()
    total_wait = 0.0
    attempt = 0
    while True:
        request = _client.build_request("POST", url, headers=headers, json=body)
        response: httpx.Response | None = None
        try:
            response = _client.send(request, stream=stream)
        except httpx.TransportError as exc:  # 接続失敗・タイムアウト
            error: APIError = APIConnectionError(
                f"{type(exc).__name__}: {exc}", status=None
            )
            error.__cause__ = exc
        else:
            if response.status_code < 400:
                return response  # 成功（stream=True なら本文は未読）
            response.read()  # ストリーム時も本文を読み切ってから解析する
            response.close()
            error = _error_from_response(response)

        # ここに来たら失敗。再試行するかどうかを判断する
        if not _is_retryable(error) or attempt >= max_retries:
            raise error
        wait = _retry_delay(attempt, response)
        if total_wait + wait > MAX_TOTAL_WAIT:
            logger.error("待ち時間の上限 %.0f 秒を超えるため中止します", MAX_TOTAL_WAIT)
            raise error
        logger.warning(
            "retry %d/%d in %.1fs: %s", attempt + 1, max_retries, wait, error
        )
        time.sleep(wait)
        total_wait += wait
        attempt += 1


def _send_with_retry(url: str, body: dict[str, Any], max_retries: int = 4) -> dict:
    """非ストリーミングで POST し、成功したレスポンスJSON（dict）を返す。"""
    response = _request_with_retry(url, body, stream=False, max_retries=max_retries)
    return response.json()


# ---- ログ -----------------------------------------------------------------
def _log_call(
    message: dict, request_id: str | None, elapsed: float, cost: float, streamed: bool
) -> None:
    """1回の呼び出しの要約を INFO で記録する（本文・キーは出さない）。"""
    usage = message.get("usage", {})
    logger.info(
        "request_id=%s model=%s stream=%s elapsed=%.2fs stop=%s "
        "in=%d out=%d cache_write=%d cache_read=%d cost=$%.4f",
        request_id,
        message.get("model"),
        streamed,
        elapsed,
        message.get("stop_reason"),
        usage.get("input_tokens", 0),
        usage.get("output_tokens", 0),
        usage.get("cache_creation_input_tokens") or 0,
        usage.get("cache_read_input_tokens") or 0,
        cost,
    )


# ---- 非ストリーミング呼び出し --------------------------------------------
def call_messages(
    messages: list[dict],
    *,
    system: str | list[dict] | None = None,
    tools: list[dict] | None = None,
    model: str = MODEL,
    max_tokens: int = 16000,
    tool_choice: dict | None = None,
    output_config: dict | None = None,
    extra: dict | None = None,
    max_retries: int = 4,
) -> dict:
    """Messages API を1回呼び出し、レスポンスJSON（dict）を返す。"""
    body = _build_body(
        messages,
        system=system,
        tools=tools,
        model=model,
        max_tokens=max_tokens,
        tool_choice=tool_choice,
        output_config=output_config,
        extra=extra,
        stream=False,
    )
    started = time.perf_counter()
    response = _request_with_retry(
        API_URL, body, stream=False, max_retries=max_retries
    )
    message: dict = response.json()
    elapsed = time.perf_counter() - started
    cost = tracker.add(message)
    _log_call(message, response.headers.get("request-id"), elapsed, cost, False)
    return message


# ---- ストリーミング（SSE）------------------------------------------------
def _iter_sse(lines: Iterator[str]) -> Iterator[tuple[str, dict]]:
    """SSE の行を受け取り、(イベント名, dataのdict) を1件ずつ返す。"""
    event_name: str | None = None
    data_lines: list[str] = []
    for line in lines:
        if line == "":  # 空行 = 1イベントの終わり
            if data_lines:
                data = json.loads("\n".join(data_lines))
                yield event_name or data.get("type", ""), data
            event_name, data_lines = None, []
            continue
        if line.startswith(":"):  # コメント行は読み飛ばす
            continue
        name, _, value = line.partition(":")
        if value.startswith(" "):  # コロン直後の空白1つは区切り
            value = value[1:]
        if name == "event":
            event_name = value
        elif name == "data":
            data_lines.append(value)
        # id: / retry: は本APIでは使わないので無視する
    if data_lines:  # 末尾に空行がないまま終わった場合
        data = json.loads("\n".join(data_lines))
        yield event_name or data.get("type", ""), data


class _StreamAccumulator:
    """SSE イベントを受け取り、最終的なメッセージ dict を組み立てる。"""

    def __init__(
        self,
        request_id: str | None,
        on_text: Callable[[str], None] | None,
    ) -> None:
        self.request_id = request_id
        self.on_text = on_text
        self.message: dict[str, Any] = {}
        self.blocks: dict[int, dict[str, Any]] = {}  # index → ブロック
        self.json_parts: dict[int, list[str]] = {}  # index → JSON 断片
        self.finished = False  # message_stop を受け取ったか

    def handle(self, event: str, data: dict) -> None:
        """1イベント分の処理を行う。"""
        match event:
            case "message_start":
                self.message = data["message"]  # id・model・usage など
            case "content_block_start":
                self.blocks[data["index"]] = dict(data["content_block"])
            case "content_block_delta":
                self._apply_delta(data["index"], data["delta"])
            case "content_block_stop":
                self._finish_block(data["index"])
            case "message_delta":
                self.message.update(data.get("delta", {}))  # stop_reason など
                usage = self.message.setdefault("usage", {})
                usage.update(data.get("usage", {}))  # 累積値で上書き
            case "message_stop":
                self.finished = True
            case "ping":
                pass  # 接続維持用。何もしない
            case "error":
                raise _make_error(None, data, self.request_id)
            case _:
                logger.debug("未知のイベントを無視: %s", event)

    def _apply_delta(self, index: int, delta: dict) -> None:
        """delta の種類に応じて、ブロックへ断片を足し込む。"""
        block = self.blocks[index]
        match delta.get("type"):
            case "text_delta":
                block["text"] = block.get("text", "") + delta["text"]
                if self.on_text:
                    self.on_text(delta["text"])  # 逐次表示用に渡す
            case "input_json_delta":
                self.json_parts.setdefault(index, []).append(delta["partial_json"])
            case "thinking_delta":
                block["thinking"] = block.get("thinking", "") + delta["thinking"]
            case "signature_delta":
                block["signature"] = block.get("signature", "") + delta["signature"]
            case other:
                logger.debug("未知の delta を無視: %s", other)

    def _finish_block(self, index: int) -> None:
        """ブロックの終わり。JSON 断片があれば連結してパースする。"""
        parts = self.json_parts.pop(index, None)
        if parts is not None:
            raw = "".join(parts)
            self.blocks[index]["input"] = json.loads(raw) if raw else {}

    def result(self) -> dict:
        """index 順にブロックを並べ、非ストリーミングと同じ形で返す。"""
        if not self.finished:
            raise APIConnectionError(
                "message_stop の前にストリームが終了しました",
                request_id=self.request_id,
            )
        self.message["content"] = [self.blocks[i] for i in sorted(self.blocks)]
        return self.message


def stream_messages(
    messages: list[dict],
    *,
    system: str | list[dict] | None = None,
    tools: list[dict] | None = None,
    model: str = MODEL,
    max_tokens: int = 64000,
    tool_choice: dict | None = None,
    output_config: dict | None = None,
    extra: dict | None = None,
    max_retries: int = 4,
    on_text: Callable[[str], None] | None = None,
) -> dict:
    """ストリーミングで呼び出し、テキストを on_text に逐次渡す。

    戻り値は call_messages() と同じ形のメッセージ dict。
    """
    body = _build_body(
        messages,
        system=system,
        tools=tools,
        model=model,
        max_tokens=max_tokens,
        tool_choice=tool_choice,
        output_config=output_config,
        extra=extra,
        stream=True,
    )
    started = time.perf_counter()
    response = _request_with_retry(
        API_URL, body, stream=True, max_retries=max_retries
    )
    request_id = response.headers.get("request-id")
    acc = _StreamAccumulator(request_id, on_text)
    try:
        for event, data in _iter_sse(response.iter_lines()):
            acc.handle(event, data)
    except httpx.TransportError as exc:  # 受信途中の切断・読み取りタイムアウト
        raise APIConnectionError(
            f"ストリーム受信中に失敗しました: {type(exc).__name__}",
            request_id=request_id,
        ) from exc
    finally:
        response.close()  # 接続をプールへ返す
    message = acc.result()
    elapsed = time.perf_counter() - started
    cost = tracker.add(message)
    _log_call(message, request_id, elapsed, cost, True)
    return message


# ---- レスポンスのヘルパー -------------------------------------------------
def extract_text(response: dict) -> str:
    """type が text のブロックだけを順に連結して返す。"""
    return "".join(
        block.get("text", "")
        for block in response.get("content", [])
        if block.get("type") == "text"
    )


def get_tool_uses(response: dict) -> list[dict]:
    """type が tool_use のブロックを一覧で返す。"""
    return [
        block for block in response.get("content", []) if block.get("type") == "tool_use"
    ]


# ---- コスト計測 -----------------------------------------------------------
# 単価表（USD / 100万トークン）。cache_write は5分キャッシュの書き込み単価
PRICES: dict[str, dict[str, float]] = {
    "claude-opus-5-5": {"input": 4.00, "output": 20.00, "cache_write": 5.00, "cache_read": 0.20},
    "claude-sonnet-5-5": {"input": 2.00, "output": 10.00, "cache_write": 2.50, "cache_read": 0.10},
    "claude-haiku-5-5": {"input": 0.10, "output": 0.50, "cache_write": 0.125, "cache_read": 0.01},
}
# Haiku 5.5 はプロンプトが10万トークンを超えると高い単価になる
LONG_PROMPT_THRESHOLD = 100_000
LONG_PROMPT_PRICES: dict[str, dict[str, float]] = {
    "claude-haiku-5-5": {"input": 0.50, "output": 2.50, "cache_write": 0.625, "cache_read": 0.05},
}


def _find_prices(model: str, prompt_tokens: int) -> dict[str, float] | None:
    """モデル名とプロンプト長から単価表の行を探す。"""
    table = PRICES
    if prompt_tokens > LONG_PROMPT_THRESHOLD and model in LONG_PROMPT_PRICES:
        table = LONG_PROMPT_PRICES
    if model in table:
        return table[model]
    for name, prices in table.items():  # 接尾辞付きのIDにも対応
        if model.startswith(name):
            return prices
    return None


@dataclass
class CostTracker:
    """usage からコストを計算し、呼び出しをまたいで累積する。"""

    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    total_usd: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def add(self, response: dict) -> float:
        """1回分の usage を加算し、その回のコスト（USD）を返す。"""
        usage = response.get("usage", {})
        inp = usage.get("input_tokens") or 0
        out = usage.get("output_tokens") or 0
        cw = usage.get("cache_creation_input_tokens") or 0
        cr = usage.get("cache_read_input_tokens") or 0
        model = response.get("model", "")
        prices = _find_prices(model, inp + cw + cr)
        if prices is None:
            logger.warning("単価表にないモデルです（コスト0で記録）: %s", model)
            cost = 0.0
        else:
            cost = (
                inp * prices["input"]
                + out * prices["output"]
                + cw * prices["cache_write"]
                + cr * prices["cache_read"]
            ) / 1_000_000
        with self._lock:  # 複数スレッドから呼ばれても数がずれないように
            self.calls += 1
            self.input_tokens += inp
            self.output_tokens += out
            self.cache_creation_input_tokens += cw
            self.cache_read_input_tokens += cr
            self.total_usd += cost
        return cost

    def summary(self) -> str:
        """累積結果を1行の文字列にまとめる。"""
        return (
            f"calls={self.calls} input={self.input_tokens:,} "
            f"output={self.output_tokens:,} "
            f"cache_write={self.cache_creation_input_tokens:,} "
            f"cache_read={self.cache_read_input_tokens:,} "
            f"total=${self.total_usd:.4f}"
        )

    def reset(self) -> None:
        """集計を0に戻す。"""
        with self._lock:
            self.calls = self.input_tokens = self.output_tokens = 0
            self.cache_creation_input_tokens = self.cache_read_input_tokens = 0
            self.total_usd = 0.0


tracker = CostTracker()  # モジュール共通の集計器
```

---

## 本章のまとめ

本章で学んだことを整理します：

- `llm_client.py` は、以降の全章が依存する公開インターフェースを持つ共通モジュールです。中心は、共有の `httpx.Client`・型付きの例外階層・`call_messages()` です。レスポンスは `dict` のまま返し、本文は必ず `type` で判定して取り出します。
- リトライは「時間をおけば成功する見込みがある失敗」だけに行います。対象は408・409・429・5xx・接続エラーです。`retry-after` を優先し、なければ指数バックオフ＋フルジッターで待ちます。回数・1回の待ち時間・合計時間の3つの上限を設けます。
- ストリーミングでは、SSEを `event:`・`data:`・空行の規則でパースします。`index` ごとに断片を組み立て、非ストリーミングと同じ形のメッセージを復元します。`logging` には本文やキーを残さず、`usage` の4種類と単価表から `CostTracker` でコストを集計します。

これで、エージェントを支える土台ができました。次章では **最初のAIエージェントを作る** を扱います。`get_tool_uses()` で取り出したツール呼び出しを自分のコードで実行し、結果を返すループを組み立てます。すると、Claudeが自分で考えて道具を使い始めます。いよいよ、ツールとループを加えて最初のエージェントを作ります。
