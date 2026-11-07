# コード検証レポート

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_08.md
検証日: 2026-11-07
検証環境: Python 3.12 / httpx / python-dotenv（APIキーなし。httpx を偽の Claude API（2026-10-21 仕様の違反を 4xx で返すモック）に接続して実行）
前提コード: 第4章の完成版 `llm_client.py`、第7章の `count_tokens`・`cached_system`/`cached_tools`、第6章の `tool_registry.py`（6.3 の `validate_input` を反映済み）・`tools/files.py`、第7章の `context.py` を原稿から再現し、第8章のコードを本文どおりに組み立てた。

コードブロック数: 16個（python 7 / bash 2 / markdown 3 / text 4）
  ✅ 動作確認済み: 15個（⚠️2件を 2026-11-07 に修正して再検証）
  ⚠️ 要確認: 0個（当初2個 → すべて対応済み）
  ❌ エラーあり: 1個（原稿を修正済み）
  🔍 構文チェックのみ: 0個

---

## ❌ エラーが発生したコード

### コードブロック #12（chapter_08.md 8.3節「llm_client.py に acall_messages を追加する」L1018付近）

**元のコード（抜粋）**:
```python
# llm_client.py（更新: 非同期版を追加。既存の import に asyncio を足す）
_RETRYABLE_STATUS = {408, 409, 429}

def _is_retryable(status: int) -> bool:
    return status in _RETRYABLE_STATUS or status >= 500

def _retry_delay(attempt: int, headers: httpx.Headers | None) -> float:
    ...
    return min(2 ** attempt, 30) + random.uniform(0, 1)
```

**エラー内容**（第4章の完成版の末尾にこのブロックを追記した状態で、同期版 `call_messages()` を実行）:
```
sync 404 (bad model) -> TypeError '>=' not supported between instances of 'NotFoundError' and 'int'
sync 529x2           -> TypeError '>=' not supported between instances of 'OverloadedError' and 'int'
```

**原因**: 第4章の完成版にはすでに `_is_retryable(error: APIError)` と `_retry_delay(attempt, response: httpx.Response | None)` があり、同期版の `_request_with_retry()` が使っている。第8章のブロックが同じ名前で引数の型が違う関数を後ろに定義するため、モジュール読み込み時に第4章の関数が上書きされる。その結果、同期版で 4xx・5xx が返ると例外の型判定が `TypeError` になり、404 などの正しい例外クラスもリトライも機能しなくなる（第7章の `count_tokens()` も同じ経路なので巻き込まれる）。さらに、非同期版の待ち時間が第4章の規則（retry-after 上限60秒・フルジッター・合計待ち120秒）と異なっており、「同じリトライ規則」という本文の説明とも食い違っていた。

**修正内容（原稿に反映済み）**: 関数を定義し直すのをやめ、第4章の `_build_body()`・`_is_retryable()`・`_retry_delay()`・`_error_from_response()`・`_log_call()`・`MAX_TOTAL_WAIT` をそのまま呼ぶ形に書き換えた。導入の段落も「第4章の関数を再利用する」「同じ名前で定義し直すと同期版が壊れる」という説明に差し替えた。後続の「同期版との違いは3か所だけです」の説明はそのまま成り立つ。
```python
async def acall_messages(...) -> dict:
    body = _build_body(messages, system=system, tools=tools, model=model,
                       max_tokens=max_tokens, tool_choice=tool_choice,
                       output_config=output_config, extra=extra, stream=False)
    client = _get_async_client()
    headers = build_headers()
    started = time.perf_counter()
    total_wait = 0.0
    for attempt in range(max_retries + 1):
        response: httpx.Response | None = None
        try:
            response = await client.post(API_URL, headers=headers, json=body)
        except httpx.TransportError as exc:
            error: APIError = APIConnectionError(f"{type(exc).__name__}: {exc}", status=None)
            error.__cause__ = exc
        else:
            if response.status_code < 400:
                message: dict = response.json()
                cost = tracker.add(message)
                _log_call(message, response.headers.get("request-id"),
                          time.perf_counter() - started, cost, False)
                return message
            error = _error_from_response(response)
        wait = _retry_delay(attempt, response)
        if (not _is_retryable(error) or attempt >= max_retries
                or total_wait + wait > MAX_TOTAL_WAIT):
            raise error
        logger.warning("retry %d/%d in %.1fs: %s", attempt + 1, max_retries, wait, error)
        await asyncio.sleep(wait)
        total_wait += wait
    raise AssertionError("unreachable")
```

**修正後の再検証**:
```
sync 404 (bad model) -> NotFoundError [404 not_found_error] model: claude-x
sync 529x2 -> ok after 3 calls
async 404 -> NotFoundError [404 not_found_error] model: claude-x
async 529x2 -> ok after 3 calls
```
`multi_agent.py` の `--sync`・既定（非同期）・`--compare` もすべて正常に終了した。偽APIへの仕様違反リクエストは0件。

---

## ⚠️ 要確認のコード

### コードブロック #1（agent.py の Agent クラス 同期版、L216付近）

**懸念点**: 本文では `_execute_one()`/`_execute_tools()` を「第6章のツール実行部分をそのまま移したもの」と説明しているが、第6章の最終形にあった次の処理が抜けている。動作は正常（検証で問題なし）だが、説明とコードが一致しない。
- 副作用ツールの実行前確認（`is_side_effect()` → `ask_approval()`）。`Agent` に `write_file` を持たせると確認なしで書き込まれる。
- `MAX_TOOL_RESULT_CHARS` による tool_result の切り詰め。
- 第7章 `run_agent()` のトップレベル自動キャッシュ `extra={"cache_control": {...}}`（messages 側のキャッシュ）。

また、8.2のコードは `agent.py` 全体の置き換えとして示されているため、第6・7章の `build_registry()`・`BASE_SYSTEM`・`__main__`・`run_agent()` が消える（第7章の effort 使い分け例 `from agent import build_registry, run_agent` が動かなくなる）。本文の NOTE で互換関数を残す方法には触れている。

**推奨対処**: 本文を「第6章の実行部分を簡略化して移したもの（承認と切り詰めは省略。副作用ツールを渡す場合は第6章の `ask_approval()` を組み込む）」と書き換えるか、`_execute_tools()` で `self.registry.is_side_effect()` を確認する処理を足す。あわせて「`build_registry()` などは残したまま `run_agent` を置き換える」と明記するとよい。

### コードブロック #7（check_agent.py の出力例、L490付近）

**懸念点**: 出力例のログ行が実際の出力と一致しない。
- `llm_client:` 行の形式が第4章の `_log_call()`（`request_id=... model=... stream=False elapsed=...s stop=... in=... out=... cache_write=... cache_read=... cost=$...`）と違う（`request-id=`・`stop`・`cost` なし）。
- 実際には、`agent: [checker] tool_use: ...` は `llm_client:` 行（その回の応答）の**後**に出る。例は順序が逆になっている（ログ出力の順序は決定的）。
- `logging.basicConfig(level=logging.INFO)` のため、`httpx: HTTP Request: POST .../v1/messages/count_tokens` などの httpx のINFO行も毎ターン出る（第7章の `maybe_compact()` が毎ターン count_tokens を呼ぶため）。

**推奨対処**: 出力例を実際の形式に合わせる。例:
```text
llm_client: request_id=req_01... model=claude-haiku-5-5 stream=False elapsed=1.40s stop=tool_use in=1024 out=58 cache_write=0 cache_read=0 cost=$0.0001
agent: [checker] tool_use: list_files {'directory': 'docs'}
```
httpx の行は「httpx のログも表示されますが、ここでは省略しています」と一言添えるか、`logging.getLogger("httpx").setLevel(logging.WARNING)` を加える。

---

## 重点確認の結果

| 確認項目 | 結果 |
|---|---|
| 子の結果が tool_result として親に返るか | ✅ 親の2ターン目のリクエストは `user → assistant(tool_use×3) → user(tool_result×3)` の3件。tool_result は子の報告テキストのみ |
| 親の履歴に子の履歴が混ざらないか | ✅ 親に送られた messages に `list_files` の結果・資料本文（「年払いで」等）は含まれない（同期・非同期とも） |
| 並列 tool_use（3件）の同時実行 | ✅ 同期版は ThreadPoolExecutor で3本同時（最大同時リクエスト3） |
| asyncio.gather と Semaphore | ✅ `Semaphore(3)` で最大同時3・所要約1.0秒、`Semaphore(1)` で最大同時1・所要約2.3秒（1リクエスト0.2秒の遅延付きモック） |
| 「Event loop is closed」 | ✅ 実ソケットのローカルサーバーで再現確認。`aclose_client()` なしで `asyncio.run()` を2回使うと `RuntimeError: Event loop is closed`、`aclose_client()` ありなら2回とも成功。本文の WARNING の説明どおり |
| tool_result の順序・欠落 | ✅ 偽APIの検証（tool_result 欠落・順序・thinking改変・prefill・temperature 等）で違反0件 |
| `llm_client.tracker = CostTracker()` による集計リセット | ✅ 逐次・並列それぞれ calls=6（モックで子1本2ターン×3）と正しく集計 |
| effort 指定（`output_config`） | ✅ `Agent(effort="high")` の `run()`/`arun()` とも正常 |

---

## ✅ 動作確認済みコード一覧

| # | 箇所 | 言語 | 行数 | 実行結果 |
|---|---|---|---|---|
| 2 | check_agent.py（L391） | python | 55行 | 正常終了（tool_use→ツール実行→end_turn、エラー時は is_error で継続） |
| 3 | workspace/docs/alpha.md（L453） | markdown | 6行 | 資料として配置し read_file で読み取り可 |
| 4 | workspace/docs/beta.md（L462） | markdown | 6行 | 同上 |
| 5 | workspace/docs/gamma.md（L471） | markdown | 6行 | 同上 |
| 6 | `uv run python check_agent.py`（L482） | bash | 2行 | 同等の `python check_agent.py` で正常 |
| 8 | multi_agent.py 同期版（L596） | python | 169行 | `--sync` で正常。委譲→子ループ→報告 |
| 9 | `uv run python multi_agent.py`（L837） | bash | 2行 | 正常（8.3の更新後は既定が非同期版、`--sync` で同期版） |
| 10 | multi_agent.py の出力例（L845） | text | 32行 | 3件同時委譲・親2ターン・calls=親2＋子9 の流れと一致 |
| 11 | 親の messages の概略（L914） | python | 21行 | 実際の親の履歴の構造と一致 |
| 13 | agent.py の arun（L1121） | python | 50行 | 正常。gather の結果順序＝tool_use の順序 |
| 14 | multi_agent.py 非同期版・compare（L1196） | python | 74行 | 既定・`--compare` とも正常終了、aclose_client あり |
| 15 | `uv run python multi_agent.py --compare`（L1285） | bash | 2行 | 正常 |
| 16 | 比較の出力例（L1292） | text | 3行 | `逐次: …s  calls=…` の形式・「失敗: なし」が実際と一致 |

> 行番号は修正前の原稿基準。ブロック #12 の修正で、以降の行番号は数行ずれています。

---

## 他章に関わる事項

- 第4章の完成版 `llm_client.py` は問題なし（第8章側の再定義が原因だったため、第4章は修正不要）。
- 第10章の `set_transport()` は `_async_client`・`_get_async_client()` の名前を前提にしている。今回の修正でもこの2つの名前と役割は変えていないので、第10章との互換性は保たれる。

---

## ⚠️対応（2026-11-07）

| # | 項目 | 対応 | 結果 |
|---|---|---|---|
| 1 | Agent クラス（8.2 同期版・8.3 非同期版）が第6章の承認・切り詰め、第7章のキャッシュを落としていた | **修正** | ✅ |
| 1' | 8.2 のコードが agent.py 全体の置き換えで、`build_registry`/`BASE_SYSTEM`/`run_agent`/`__main__` が消える | **修正** | ✅ |
| 7 | check_agent.py の出力例（ログ形式・順序・httpx の INFO 行） | **修正** | ✅ |

**修正内容（原稿に反映済み）**
- 8.2 の agent.py を「第6・7章の関数と定数は残したまま、import（`dataclass`・`MODEL`）を足し、`if __name__ == "__main__":` の前に Agent クラスを追記する」形に変更。導入文と NOTE も「既存の関数は残すので第7章の例はそのまま動く」に差し替えた。
- `_system_blocks()`/`_tool_schemas()` を削除し、`_request_kwargs()` で第7章の `cached_system()`/`cached_tools()` と、トップレベル自動キャッシュ `extra={"cache_control": {"type": "ephemeral"}}` を使う形にした（第7章 `run_agent()` と同じ3つのブレークポイント）。`run()`/`arun()` は kwargs をループ前に1回作り、`maybe_compact()` にも送るのと同じ system・tools を渡す（第7章と同じ）。
- `_execute_one()` を削除し、`_execute_tools()` は `[名前] tool_use:` のログを出してから第6章の `execute_tool_uses()` を呼ぶ形にした（読み取り系の並列・副作用系の承認・`MAX_TOOL_RESULT_CHARS` の切り詰め・is_error がそのまま効く）。本文の説明を「第6章の execute_tool_uses() をそのまま呼ぶ」に合わせ、つまずきポイント5・WARNING の `_execute_one()` を `run_one_tool()` に改めた。
- 8.3 の `arun()`: `_aexecute_one()` は async_handlers 専用に。新設の `_aexecute_tools()` が、async_handlers 以外のツールを `asyncio.to_thread(execute_tool_uses, ...)` でまとめて実行し、非同期ツールと `gather()` で同時に進めて `tool_use_id` で元の順に並べ直す。非同期版でも承認・切り詰めが効く。
- check_agent.py と multi_agent.py（8.2 の `main()`・8.3 の `__main__`）に `logging.getLogger("httpx").setLevel(logging.WARNING)` を追加。check_agent の出力例を第4章の確定ログ形式（`request_id=... stream=False elapsed=... stop=... in=... out=... cache_write=... cache_read=... cost=$...`）・実際の出力順（`llm_client:` 行 → `[checker] tool_use` → 第6章の `tool=... elapsed=` 行）に合わせ、「表示形式は実装によって異なる」の断り書きを削除した。出力例のコスト（Haiku 5.5 $0.10/$0.50）は合計 $0.0004 と整合。

**再検証**（最新の第6・7章原稿から組み立てた agent.py＋修正後の第8章ブロック。`scratchpad/verify/ch08_09/proj2`、偽API）
```text
== sync-y / async-y（標準入力 y）: write_file 実行・big(3万字)→20,030字に切り詰め・順序一致
== sync-n / async-n（標準入力 n）: write_file は is_error「ユーザーがこの操作の実行を拒否しました…」、ファイル作成なし
  リクエスト: system 末尾・tools 末尾・トップレベルに cache_control、output_config={'effort': 'low'}
registry.execute を外から差し替えた場合も全ツールが差し替え後の execute を通る（第11章 harden_registry の前提）
check_agent.py: llm_client 行 → [checker] tool_use → tool=... elapsed= の順、httpx 行 0
multi_agent.py --sync / 既定（非同期） / --compare: 正常終了、httpx 行 0
親子分離テスト: 親の履歴は user→assistant(tool_use×3)→user(tool_result×3)、子の資料本文の混入なし
  Semaphore(3) 最大同時3・Semaphore(1) 最大同時1、asyncio.run 2回でも Event loop is closed なし
第7章の effort_demo.py（from agent import build_registry, run_agent）: 正常終了
偽APIへの仕様違反リクエスト: 0件
```

**Agent クラスのインターフェース**: `Agent(name, system, registry, model=MODEL, effort=None, max_turns=10, async_handlers={})`・`run(task) -> str`・`async arun(task) -> str` は変更なし（第10章の利用はそのまま成り立つ）。内部メソッドは `_request_kwargs`・`_check_stop`・`_execute_tools`・`_aexecute_one`・`_aexecute_tools`（`_system_blocks`・`_tool_schemas`・`_execute_one` は廃止）。async_handlers に登録したツールは従来どおり `registry.execute()` を通らない。

**残った項目**: なし。
