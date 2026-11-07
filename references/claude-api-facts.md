# Claude API 仕様メモ・コード規約（2026-11 時点 / 執筆共通基準）

本教材（claude-api-scratch-agent）のコード・説明はすべてこのメモに揃える。
疑わしい点は reference-doc.md のURLで一次情報を確認し、このメモも更新すること。

## 教材の方針
- **SDK不使用**: `anthropic` Python SDK・Claude Agent SDK・Claude Code は使わない／扱わない。
  `httpx` で HTTP リクエストを直接送る。リトライ・ストリーミング・ツールループ・マルチエージェントは自前実装。
- Claude Code / Agent SDK / client SDK / CLAUDE.md / Hooks / Skills / Agent Teams / MCP設定 は本文で扱わない
  （最終章のリソース紹介で「別教材」として触れるのみ）。
- 開発環境: Python 3.12 / uv（`uv init agent-from-scratch --python 3.12 --no-package`（uv 0.12 以降は既定で src 構成のパッケージになり main.py が作られないため `--no-package` 必須）, `uv add httpx python-dotenv`, `uv run main.py`。httpx の INFO ログは `logging.getLogger("httpx").setLevel(logging.WARNING)` で抑える）/ VS Code / `.env` に `ANTHROPIC_API_KEY`（`.gitignore` 必須）。
- APIキーは Claude Console（https://platform.claude.com）で発行（作成時に Expiration・Linked account を選ぶ）。利用上限（spend limit）の設定を推奨。
  spend limit は **Billing 画面（組織）・Workspaces 画面（ワークスペース）** で設定。Limits 画面はティアとレート制限の表示。Default Workspace には上限を設定できない。

## 分量目標（旧教材 claude-agent-dev-intro と同水準。CLAUDE.md の文字数基準より優先する）
本文字数＝コードブロック・見出し・空白を除いた文字数（**UTF-8の文字数**。Git Bash の `wc -m` はバイト数を返すので使わない。
`python references/../` 等で `len()` を使って数える。例は下記）。
| 対象 | 目標 | 参考（旧教材の実績・文字数） |
|---|---|---|
| 書籍 はじめに（chapter_00） | 約6,000〜7,000字 | 約5,700字 |
| 書籍 第1〜11章 | 1章あたり約2万〜2.7万字 | 約1.9万〜2.9万字（平均約2.3万字） |
| 書籍 第12章 | 約1.2万字 | 約1.2万字 |
| Udemy 1レクチャー | 約1,800〜2,300字 | 1,778〜2,303字（中央値約1,900字） |

文字数の数え方（Python）:
```python
# count_body.py — 本文字数（コードブロック・#見出し行・空白を除く）
import re, sys
c = False; n = 0
for line in open(sys.argv[1], encoding="utf-8"):
    if line.startswith("```"): c = not c; continue
    if c or re.match(r"^\s*#", line): continue
    n += len(re.sub(r"\s", "", line))
print(n)
```
- 分量は水増しではなく、コードの1行ずつの解説・実行結果の読み方・つまずきと対処・図解指示・「なぜそうするか」の説明で確保する。
- 1章（1レクチャー）を書き終えたら本文字数を数え、目標未満なら不足している節を加筆してから完了とする。

## エンドポイント・ヘッダー
- `POST https://api.anthropic.com/v1/messages`
- 必須ヘッダー: `x-api-key: <APIキー>` / `anthropic-version: 2026-10-21` / `content-type: application/json`
  （公式ドキュメントは `Authorization: Bearer <キー>` を主に記載し `x-api-key` は legacy 扱いだが、どちらも有効。本教材は `x-api-key` で統一）
- ベータ機能は `anthropic-beta: <beta名>` ヘッダー（本教材では原則使わない）
- トークン数: `POST /v1/messages/count_tokens`（`model`・`messages`・`system`・`tools` を渡す → `{"input_tokens": N}`）
- バッチ: `POST /v1/messages/batches`（50%割引・非同期、結果は `custom_id` で突き合わせ。順序保証なし）。上限 100,000件／256MB、24時間で期限切れ、結果保持29日、`custom_id` は `^[a-zA-Z0-9_-]{1,64}$`、状態に `canceling` あり
- モデル一覧: `GET /v1/models`

## モデル（本教材での使い分け）
| 用途 | モデルID | 入力/出力 $/1M tok |
|---|---|---|
| 既定（メインエージェント） | `claude-opus-5-5` | $4 / $20 |
| 低コストのワーカー・分類 | `claude-haiku-5-5` | $0.10 / $0.50（10万tok以下） |
| 中間 | `claude-sonnet-5-5` | $2 / $10 |
- モデルIDに日付サフィックスは付けない。コンテキスト 1M トークン、最大出力 128K。
- Haiku 5.5 の「10万tok以下」は**入力（プロンプト）長**の閾値。超えると単価が上がる。
- 現行の最上位モデルは Claude Fable 5.1。Opus 5.5 を「最上位」と書かない（「本書で使う3つの中でもっとも高性能」）。
- `model` は定数 `MODEL = "claude-opus-5-5"` に集約し、差し替え可能にしておく。

## リクエストの注意（2026-10-21 版・現行モデル）
- **`temperature` / `top_p` / `top_k` は送らない**（2026-10-21 版で 400エラー）。
- **assistant の prefill（最後を assistant メッセージで終える）は不可**（400）。これは **API バージョンの変更ではなく Claude 4.6 以降のモデルの制約**。出力形式は system プロンプトか構造化出力で制御。
  ただし `pause_turn` からの再開で、返ってきた assistant content をそのまま足して再送するのは正規の手順で prefill に当たらない。
- `tool_choice` は `{"type": "auto"}` または `{"type": "none"}` を使う。`any` / `tool`（強制）は Opus 5.5・Sonnet 5.5 で 400（Haiku 5.5 は対応）。
- 思考: Opus 5.5 は adaptive thinking が常時有効（`thinking` を省略でよい。`{"type":"disabled"}` は 400）。
  深さは `output_config: {"effort": "low"|"medium"|"high"|"xhigh"|"max"}`（既定: Opus 5.5・Haiku 5.5 は `medium`、Sonnet 5.5 は `high`。3モデルとも5段階に対応）。
  Sonnet 5.5 も思考を `disabled` にできない。Haiku 5.5 は思考が既定で有効だが `disabled` 可。**思考トークンも `max_tokens` に数えられる**ので、Haiku の短い分類・構造化出力でも `max_tokens` に余裕を持たせるか `effort: "low"` にする。
  レスポンスに `thinking` ブロックが含まれ得る（`display` の既定は `"omitted"` で中身が空文字。思考量は `usage.output_tokens_details.thinking_tokens`）。**履歴に戻すときは content 配列をそのまま追加**し、thinking ブロックを削除・改変しない。
- `max_tokens`: 非ストリーミングは 16000 程度、ストリーミングは 64000 程度を目安。短い分類は小さくてよい。
- 構造化出力: `output_config: {"format": {"type": "json_schema", "schema": {...}}}`。ツール側は `strict: true`（`additionalProperties: false` が必須。任意引数はスキーマ全体で24個まで、`required` 推奨。strict ツールは最大20個）。
  構造化出力・strict で使えない制約: `minItems` は0か1のみ、`maxItems`・`minLength`・`maxLength`・`minimum`・`maximum` は非対応で 400。refusal・max_tokens 打ち切り時はスキーマに沿わない。

## レスポンス
- `content` はブロックの配列（`text` / `tool_use` / `thinking` など）。**常に type で判定**し `content[0]` 決め打ちをしない。
- `stop_reason`: `end_turn` / `max_tokens` / `tool_use` / `stop_sequence` / `pause_turn` / `refusal` / `model_context_window_exceeded`
  - `refusal` の場合は `stop_details`（category 等）を確認。本文を読む前に必ず stop_reason を判定する。
- `usage`: `input_tokens` / `output_tokens` / `cache_creation_input_tokens` / `cache_read_input_tokens`

## エラーとリトライ
- 400 invalid_request_error / 401 authentication_error / 402 billing_error / 403 permission_error / 404 not_found_error /
  413 request_too_large / 429 rate_limit_error / 500 api_error / 504 timeout_error / 529 overloaded_error
- 利用上限: **自分で設定した spend limit に達すると 400 `invalid_request_error`**。ティアの月額上限（spend cap）は 429 で `error.details.error_code == "enforced_spend_limit_reached"`・`retry-after` なし → どちらもリトライしない。
- エラーボディ: `{"type":"error","error":{"type":"...","message":"..."},"request_id":"..."}`。レスポンスヘッダー `request-id` をログに残す。
- リトライ対象: 408（SDK慣例。API一覧にはない）・409・429（spend cap を除く）・5xx（529含む）・接続エラー／タイムアウト。`retry-after` が公式に明記されているのは429。`retry-after` ヘッダーがあれば優先、なければ指数バックオフ＋ジッター。400系（429除く）はリトライしない。

## ストリーミング（`"stream": true`、SSE）
イベント順: `message_start` → (`content_block_start` → `content_block_delta`* → `content_block_stop`)* → `message_delta`（stop_reason・usage）→ `message_stop`。途中に `ping`、`error` イベントあり得る。
- delta 種別: `text_delta`（`text`）/ `input_json_delta`（`partial_json` を連結し、block stop 時に `json.loads`）/ `thinking_delta` / `signature_delta` / `citations_delta`（引用。本教材のパーサーは無視）
- httpx: `client.stream("POST", url, ...)` + `response.iter_lines()` で `event:` / `data:` 行をパース。

## ツール使用（クライアントツール）
- 定義: `{"name", "description", "input_schema": JSON Schema}`。ツール名は `^[a-zA-Z0-9_-]{1,128}$`。`tool_result` は user content の先頭に置く（後ろだと400）。説明は「何をする／いつ使う／引数の意味」を具体的に。
- ループ: `stop_reason == "tool_use"` の間、assistant の content を **そのまま** 履歴に追加 → 各 `tool_use` を実行 →
  **すべての** `tool_result`（`tool_use_id` 対応、失敗時 `is_error: true`）を **1つの user メッセージ** にまとめて返す。
- 並列ツール呼び出しは既定で有効。tool_input は必ず `json` としてパース済みの dict を使う（文字列照合しない）。
- 最大反復回数のガードを必ず入れる。
- サーバーツール（本教材は `web_search_20260209` / `web_fetch_20260209`。より新しい `_20260318` 版もある）は Anthropic 側で実行される。
  - `_20260209` 以降は既定で動的フィルタリング（`allowed_callers` 既定 `["code_execution_20260120"]`）。直接呼ぶなら `"allowed_callers": ["direct"]`（ZDR もこの設定が必要）。
  - `pause_turn` の再開: assistant content をそのまま追加し、**同じ tools と、レスポンスの `container` の ID**（`extra={"container": ...}`）を付けて再送する。再開回数に上限を設ける。
  - `max_uses` は1ターン単位。動的フィルタリング経由の検索は再開をまたいで数えられない。料金 $10/1,000回、citations は常に有効。

## Prompt caching
- 順序は `tools` → `system` → `messages`。キャッシュは前方一致。`cache_control: {"type": "ephemeral"}` をブロックに付ける（最大4ブレークポイント）。
- 料金倍率: キャッシュ書き込み（5分TTL）は入力単価の1.25倍。読み取りは基本0.1倍だが、**Opus 5.5・Sonnet 5.5 は0.05倍**（公式で確認済み）。1時間TTLの書き込みは2倍。
- 最小キャッシュ長はモデル依存（512〜4096 tok。Opus 5.5・Sonnet 5.5・Haiku 5.5 は512）。自動キャッシュ付きなら短いプロンプトでも書き込みが発生する。
- トップレベルの effort を変えると messages のキャッシュは無効（モデルによっては tools・system も）。既定値を明示的に送るのは省略と同じでキャッシュを壊さない。トップレベル自動キャッシュも4ブレークポイントのうち1枠を使う。
- count_tokens は無料・別枠のレート制限・値は見積もり・キャッシュは使わない。サーバーツール・url/file ソースの画像や文書は invalid_request_error。効果は `usage.cache_read_input_tokens` で確認。
- system にタイムスタンプ等の可変値を入れない。

## コード規約（教材内のPython）
- 先頭にファイル名コメント（例: `# llm_client.py`）。各ブロックに説明コメント。
- 共通モジュール: `llm_client.py`（`call_messages()` / `stream_messages()` / リトライ）を第4章で作り、以降の章はこれを import して使う。
- 型ヒントを付ける。`print` によるログは第4章以降 `logging` に移行。
- APIキーはコードに書かない（`os.environ["ANTHROPIC_API_KEY"]`、`load_dotenv()`）。
