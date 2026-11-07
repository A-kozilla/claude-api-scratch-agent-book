# 共通コードベース仕様（claude-api-scratch-agent / 読者のプロジェクト `agent-from-scratch/`）

書籍・Udemy・YouTube のすべてのコードはこの仕様に合わせる。章を並列で執筆しても、
関数名・引数・戻り値・ファイル名が章をまたいで食い違わないようにするための「契約」。
API仕様そのものは `references/claude-api-facts.md` に従う。

## ディレクトリ（最終形）
```text
agent-from-scratch/
├── .env                  # ANTHROPIC_API_KEY=...（.gitignore 済み）
├── .gitignore
├── pyproject.toml        # uv init で生成。依存: httpx, python-dotenv（第10章で pytest を dev 依存に追加）
├── hello_claude.py       # 第2章
├── inspect_response.py   # 第3章
├── params_demo.py        # 第3章
├── chat.py               # 第3章
├── error_lab.py          # 第3章
├── llm_client.py         # 第4章で作成 → 第7章(キャッシュ) → 第8章(非同期) で拡張
├── one_shot_tool.py      # 第5章
├── agent.py              # 第5章で関数版 → 第6章(レジストリ/並列) → 第8章(Agentクラス)
├── tool_registry.py      # 第6章
├── structured_output.py  # 第6章
├── context.py            # 第7章
├── multi_agent.py        # 第8章
├── tools/
│   ├── __init__.py
│   ├── weather.py        # 第5章
│   ├── files.py          # 第6章
│   └── memory.py         # 第7章
├── patterns/             # 第9章: chain.py / router.py / parallel.py / evaluator_optimizer.py
├── report_agent/         # 第10章: __init__.py / orchestrator.py / researcher.py / writer.py / reviewer.py / cli.py
├── tests/test_report_agent.py  # 第10章
├── guardrails.py         # 第11章
├── evals/run_eval.py     # 第11章
└── batch_demo.py         # 第11章
```

## llm_client.py（第4章で完成させる公開インターフェース）
```python
# llm_client.py の公開API（シグネチャの契約）
API_URL = "https://api.anthropic.com/v1/messages"
API_BASE = "https://api.anthropic.com/v1"
API_VERSION = "2026-10-21"
MODEL = "claude-opus-5-5"          # 既定モデル
FAST_MODEL = "claude-haiku-5-5"    # 分類・要約・ワーカー用

class APIError(Exception):          # status: int | None, error_type: str, message: str, request_id: str | None
class InvalidRequestError(APIError)  # 400
class AuthenticationError(APIError)  # 401
class PermissionDeniedError(APIError)# 403
class NotFoundError(APIError)        # 404
class RequestTooLargeError(APIError) # 413
class RateLimitError(APIError)       # 429
class InternalServerError(APIError)  # 500 等の 5xx
class OverloadedError(APIError)      # 529
class APIConnectionError(APIError)   # 接続失敗・タイムアウト（status=None）

def build_headers() -> dict[str, str]          # x-api-key / anthropic-version / content-type
def call_messages(
    messages: list[dict],
    *,
    system: str | list[dict] | None = None,
    tools: list[dict] | None = None,
    model: str = MODEL,
    max_tokens: int = 16000,
    tool_choice: dict | None = None,
    output_config: dict | None = None,
    extra: dict | None = None,              # その他のボディ項目（cache_control 等）
    max_retries: int = 4,
) -> dict                                    # レスポンスJSON（dict）をそのまま返す

def stream_messages(... call_messages と同じ引数 ..., on_text: Callable[[str], None] | None = None) -> dict
    # SSEを自前パースし、テキストは on_text に逐次渡す。最後に「非ストリーミングと同じ形」の
    # メッセージdict（content・stop_reason・usage）を組み立てて返す。

def extract_text(response: dict) -> str       # type == "text" のブロックを連結
def get_tool_uses(response: dict) -> list[dict]  # type == "tool_use" のブロック一覧

class CostTracker:                            # 単価表 PRICES（$/1M tok）を持つ
    def add(self, response: dict) -> float    # usage からコストを計算・累積し、その回のコストを返す
    def summary(self) -> str                  # 呼び出し回数・トークン4種・合計USD
tracker = CostTracker()                       # モジュール共通インスタンス。call_messages/stream_messages が自動で add する
```
- 内部実装: モジュールレベルの `httpx.Client(timeout=httpx.Timeout(600.0, connect=10.0))` を再利用。
  `_send_with_retry()` が 408/409/429/5xx/接続エラーを `retry-after` 優先＋指数バックオフ＋ジッターで再試行。
- `logging.getLogger("llm_client")` で request-id・model・所要時間・tokens を INFO 出力（本文・キーは出さない）。
- 第7章: `count_tokens(messages, *, system=None, tools=None, model=MODEL) -> int` を追加（`/v1/messages/count_tokens`）。
  キャッシュは `call_messages(..., extra={"cache_control": {"type": "ephemeral"}})`（トップレベル自動キャッシュ）
  または system/tools の最後のブロックに `cache_control` を付ける方式で説明する。
- 第8章: 非同期版 `async def acall_messages(...) -> dict`（同じ引数・`httpx.AsyncClient`・同じリトライ規則）を追加。
- 第11章: `batch_demo.py` は `API_BASE + "/messages/batches"` を `httpx` で直接呼ぶ（`build_headers()` を流用）。

## agent.py の進化
- 第5章（関数版）:
  ```python
  def run_agent(user_input: str, *, tools: list[dict], tool_functions: dict[str, Callable[..., str]],
                system: str | None = None, max_turns: int = 10) -> str
  ```
  ループ: `call_messages` → `stop_reason` 判定（`end_turn` で終了、`tool_use` で実行、`max_tokens`/`refusal` はガード）
  → assistant の `content` をそのまま追加 → 全 `tool_result` を1つの user メッセージで返す。
- 第6章: `run_agent(user_input, *, registry: ToolRegistry, system=None, max_turns=10) -> str` に変更。
  tool_use が複数なら `ThreadPoolExecutor` で並列実行。例外は `is_error: True` の tool_result にする。
- 第7章: `maybe_compact()`（context.py）を各ターン前に呼ぶ。system とツールにキャッシュを付ける。
- 第8章: `Agent` クラスへリファクタリング:
  ```python
  @dataclass
  class Agent:
      name: str
      system: str
      registry: ToolRegistry
      model: str = MODEL
      effort: str | None = None        # output_config={"effort": effort}
      max_turns: int = 10
      async_handlers: dict[str, Callable[..., Awaitable[str]]] = field(default_factory=dict)  # 非同期で動かすツール（委譲ツール等）
      def run(self, task: str) -> str
      async def arun(self, task: str) -> str
  ```

## tool_registry.py（第6章）
```python
class ToolRegistry:
    def tool(self, *, name: str, description: str, input_schema: dict, side_effect: bool = False) -> Callable  # デコレーター
    def schemas(self) -> list[dict]          # API の tools に渡す配列（名前順で安定させる→キャッシュに有利）
    def execute(self, name: str, tool_input: dict) -> str   # 未知の名前は ToolNotFoundError → is_error で返す
    def is_side_effect(self, name: str) -> bool
```

## tools/
- `tools/weather.py`: `GET_WEATHER_TOOL`（スキーマdict）と `get_weather(city: str, unit: str = "celsius") -> str`（第5章前半はダミーデータ、5-4 で Open-Meteo に差し替え。ジオコーディングは `https://geocoding-api.open-meteo.com/v1/search`、天気は `https://api.open-meteo.com/v1/forecast`）。
- `tools/files.py`: `WORKSPACE = Path("workspace").resolve()`、`safe_path(rel: str) -> Path`（resolve後に WORKSPACE 配下か `is_relative_to` で確認）、`list_files` / `read_file`（サイズ上限）/ `write_file`（side_effect=True、実行前に確認）。
- `tools/memory.py`: `MEMORY_FILE = Path("memory.json")`、`save_memory(key, content, tags)` / `search_memory(query)`。

## context.py（第7章）
- `count_tokens`（llm_client）を使う `estimate_tokens(...)`、`truncate_history(messages, keep_last: int)`（tool_use/tool_result ペアを壊さない）、
  `summarize_history(messages) -> str`（FAST_MODEL で要約）、`maybe_compact(messages, *, system, tools, threshold: int = 150_000) -> list[dict]`。

## 第4章で確定した内部名・ログ形式（他章はこれに合わせる）
- `_send_with_retry(url, body, max_retries=4) -> dict` / `_request_with_retry(url, body, *, stream, max_retries) -> httpx.Response`
- `_is_retryable(error: APIError) -> bool` / `_retry_delay(attempt, response) -> float`（retry-after 上限60秒、指数1秒基準・最大30秒・フルジッター、総待ち最大120秒）
- `_error_from_response(response)`（内部で `_make_error` / `_error_class`、`_TYPE_TO_ERROR` に `timeout_error` → InternalServerError）。402 は APIError で再試行しない、504 は再試行。`APIError` に `error_code`（spend limit 到達の429はリトライしない）
- `_client`（モジュールレベル httpx.Client。第10章で正式な差し替えフックを追加）
- `stream_messages` の max_tokens 既定は 64000、`call_messages` は 16000
- INFO ログ: `request_id=req_... model=claude-opus-5-5 stream=False elapsed=3.84s stop=end_turn in=26 out=118 cache_write=0 cache_read=0 cost=$0.0025`
- `tracker.summary()`: `calls=2 input=52 output=182 cache_write=0 cache_read=0 total=$0.0025`、`tracker.reset()` あり
- PRICES はモデルごとの単価（Opus 5.5 cache_read $0.20 等）

## 第7章で追加された補助（実装済み・以降の章で利用可）
- llm_client.py: `cached_system(text) -> list[dict]` / `cached_tools(tools) -> list[dict]`（cache_control を付ける）
- context.py: `token_breakdown(...)` / `shrink_old_tool_results(messages, ...)`
- tools/memory.py: `register_memory_tools(registry)` / `memory_prompt() -> str`
- `run_agent(..., effort: str | None = None)`（output_config.effort）
- 第6章の agent.py は `build_registry() -> ToolRegistry`（天気・ファイル操作ツールを登録）と、`sys.argv` から依頼を受け取る `__main__` を持つ。第7章で定数 `BASE_SYSTEM` を追加する
- 第6章の追加名: agent.py `make_tool_result` / `execute_tool_uses` / `run_one_tool` / `ask_approval`、tool_registry.py `ToolInputError` / `validate_input`、tools/files.py `register_file_tools(registry, *, allow_write=True)`
- 第10章の追加名: llm_client.py `set_transport(transport)`、report_agent の `RunWorkspace`・`Budget`・`ReportOrchestrator`・researcher の `registry` / `RESEARCHER_SYSTEM` / `fetch_page`、CLI `--budget` `--source local|web`

## 第9章 patterns/ と 第10章 report_agent/
- patterns はいずれも `llm_client.call_messages` / `acall_messages` と構造化出力（`output_config.format`）を使う単独実行スクリプト。
- report_agent: オーケストレーター＝`Agent`（MODEL）、researcher/writer/reviewer＝`Agent`（researcher・reviewer は FAST_MODEL も可）。
  共有ストアは `workspace/`（調査メモ・下書き・レビュー結果のMarkdown/JSON）。CLI: `uv run python -m report_agent.cli "テーマ" --budget 1.0`。
  テストは `httpx.MockTransport` を差し込める作り（llm_client に `set_transport(transport)` などのテスト用フックを第10章で追加してよい）。

## 共通ルール
- 実行は、ルート直下のファイルは `uv run python ファイル名.py`。サブディレクトリ（`patterns/`・`report_agent/`・`evals/`）のスクリプトは
  ルートの `llm_client` を import するため **`uv run python -m patterns.chain` のようにモジュール実行**する（各ディレクトリに `__init__.py` を置く）。
- `patterns/__init__.py` は構造化出力の共通ヘルパー（`PatternError` / `json_format` / `parse_json_response`）を持つ（第9章）。
- `from dotenv import load_dotenv` → `load_dotenv()` は llm_client.py 内で1回呼ぶ。第2・3章の単独スクリプトでは各ファイルで呼ぶ。
- `temperature`・`top_p`・`top_k`・prefill・強制 `tool_choice` は使わない。
- コードを示すときは、その節で「新規作成」か「更新（差分の該当部分）」かを明記する。更新は関数単位で全体を示す。
