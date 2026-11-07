# コード検証レポート

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_04.md
検証日: 2026-11-07
検証環境: Python 3.12 / uv 0.13.5 / httpx 0.28.1 / python-dotenv 1.2.4 / 偽Claude API（SSE対応）
コードブロック数: 36個（うち出力例・SSEの生データの `text` 7個は照合用のため判定数に含めない → 判定対象 29個）
  ✅ 動作確認済み: 28個
  ⚠️ 要確認: 0個
  ❌ エラーあり: 1個（原稿修正済み）
  🔍 構文チェックのみ: 0個

※ 行番号は修正後の原稿（stream_demo.py に4行追加したため、L1004 以降は修正前より +4）。

---

## 検証の進め方
本文の「新規作成」「追加」「更新」の指示どおりに llm_client.py を4段階で組み立て、各段階のデモを実行した。
1. 4.1節: 冒頭・例外・エラー変換・組み立て・call_messages 最初の版・ヘルパー → client_demo.py
2. 4.2節: リトライ定数・判定・`_request_with_retry` を追加し call_messages を差し替え → retry_demo.py
3. 4.3節: `_iter_sse`・`_StreamAccumulator`・stream_messages を追加 → sse_demo.py / stream_demo.py
4. 4.4節: `_log_call`・単価表と CostTracker・call_messages / stream_messages 完成版 → cost_demo.py

段階4で組み立てたファイルと L1403 の完成版を AST で比較し、**全定義が一致**することを確認した（本文の差分指示に抜け・食い違いなし）。
codebase-spec.md の公開インターフェース（定数・例外9種・`build_headers`・`call_messages`/`stream_messages` のシグネチャと既定 max_tokens 16000/64000・`extract_text`・`get_tool_uses`・`CostTracker.add/summary/reset`・`tracker`・内部名 `_send_with_retry`/`_request_with_retry`/`_is_retryable`/`_retry_delay`/`_error_from_response`/`_make_error`/`_error_class`/`_client`）とも一致。

追加の境界テスト（MockTransport で実施、すべて期待どおり）:
- 接続エラー（ConnectError）: 2回リトライ後 `APIConnectionError`、試行3回
- 429 + `error.details.error_code = enforced_spend_limit_reached`: リトライせず即 `RateLimitError`
- 502 + HTML 本文: `InternalServerError`、本文の先頭がメッセージに入る
- ストリーム中の `event: error`（overloaded_error）: `OverloadedError`（status=None、request_id 引き継ぎ）
- `message_stop` 前に切れたストリーム: `APIConnectionError`
- 単価表は facts どおり（Opus 5.5: $4/$20/書込$5/読取$0.20、Sonnet 5.5: $2/$10/$2.50/$0.10、Haiku 5.5: $0.10/$0.50/$0.125/$0.01）。cost_demo の出力例 `cost=$0.0025`・`total=$0.0025` は再計算と一致。

---

## ❌ エラーが発生したコード

### コードブロック #25（chapter_04.md L995付近 stream_demo.py）【原稿修正済み】

**元のコード**:
```python
def show(text: str) -> None:
    """届いた断片を改行せずにすぐ表示する。"""
    print(text, end="", flush=True)
...
print("同じ文字列か:", extract_text(response) != "")
```

**エラー内容**: 例外は出ないが、ラベル「同じ文字列か」に対して実際は「本文が空でないか」しか調べていない（逐次表示した文字列と戻り値の比較になっていない）。ストリームの組み立てが壊れていても `True` と表示されうるため、確認用デモとして機能しない。

**原因**: 届いた断片を保持していないので、比較の相手がない。

**修正内容**（原稿に反映済み）:
```python
received: list[str] = []  # 届いた断片を記録しておく（最後の比較用）


def show(text: str) -> None:
    """届いた断片を改行せずにすぐ表示する。"""
    received.append(text)
    print(text, end="", flush=True)
...
print("同じ文字列か:", "".join(received) == extract_text(response))  # 逐次表示と戻り値の一致
```
修正後、偽APIのSSEで `同じ文字列か: True` を確認。出力例（L1030）と本文の説明は変更不要。

---

## 参考（判定に影響しない注記）
- stream_demo.py の出力例 `usage: {'input_tokens': 24, 'output_tokens': 162}` は、実APIでは `cache_creation_input_tokens` 等のキーも入る。本文に「実際のキーは例より多いことがある」と書かれているので修正不要。
- 4.4節以降に stream_demo.py を実行すると、INFO ログ（`llm_client: request_id=...`）がストリーム本文と同じ行に続けて出る（本文の末尾に改行がないため）。4.3節時点の出力例とは一致しているので問題なし。
- retry_demo.py を 4.4節以降の完成版で実行すると、L654 の出力例に加えて成功時の INFO ログが1行増える（4.2節時点では本文どおり）。

---

## ✅ 動作確認済みコード一覧

| # | 位置 | 言語 | 行数 | 実行結果 |
|---|-----|-----|-----|--------|
| 1 | L62 llm_client.py 冒頭 | python | 33行 | 段階1に組み込み、正常 |
| 2 | L108 例外クラス | python | 62行 | 同上 |
| 3 | L183 エラー変換 | python | 64行 | 同上 |
| 4 | L256 組み立て | python | 49行 | 同上。temperature を extra で渡すと送信前に ValueError |
| 5 | L318 call_messages 最初の版 | python | 33行 | 同上 |
| 6 | L360 extract_text / get_tool_uses | python | 15行 | 同上 |
| 7 | L384 client_demo.py | python | 28行 | 出力が本文例と同じ形（blocks: ['thinking', 'text'] / NotFoundError / ValueError） |
| 8 | L415 実行コマンド | bash | 1行 | 正常 |
| 10 | L483 リトライ定数 | python | 6行 | 段階2に組み込み、正常 |
| 11 | L492 `_is_retryable` / `_retry_delay` | python | 23行 | 同上 |
| 12 | L520 `_request_with_retry` / `_send_with_retry` | python | 44行 | 同上 |
| 13 | L577 call_messages（リトライ版） | python | 30行 | 同上 |
| 14 | L614 retry_demo.py | python | 32行 | 529→429(retry-after:1)→成功、`3回目で成功しました (試行回数: 3)` |
| 15 | L649 実行コマンド | bash | 1行 | 正常 |
| 18 | L751 `_iter_sse` | python | 25行 | 段階3に組み込み、正常 |
| 19 | L785 `_StreamAccumulator` | python | 73行 | 同上。input_json_delta の連結・ping 無視・error イベント例外化を確認 |
| 21 | L880 stream_messages | python | 46行 | 同上 |
| 22 | L937 sse_demo.py | python | 34行 | イベント7行＋`stop_reason: tool_use`＋tool_uses が本文例と一致 |
| 23 | L974 実行コマンド | bash | 1行 | 正常 |
| 26 | L1025 実行コマンド | bash | 1行 | 正常 |
| 28 | L1070 `_log_call` | python | 20行 | 段階4に組み込み、ログ形式が codebase-spec どおり |
| 29 | L1116 main.py（ログ設定例） | python | 12行 | 実行して agent.log が作成されることを確認 |
| 30 | L1149 単価表・CostTracker | python | 86行 | 同上 |
| 31 | L1248 call_messages 完成版 | python | 34行 | 同上 |
| 32 | L1285 stream_messages 完成版 | python | 50行 | 同上 |
| 33 | L1342 cost_demo.py | python | 12行 | INFO 2行＋summary 1行が本文例と同じ形 |
| 34 | L1357 実行コマンド | bash | 1行 | 正常 |
| 36 | L1403 llm_client.py 完成版 | python | 604行 | 全デモ（client/retry/sse/stream/cost）が完成版でも正常。段階組み立て版と AST 一致 |

## ⚠️対応（2026-11-07）

⚠️ 要確認は0件のため対応なし。第4章の確定ログ形式・`tracker.summary()` 形式との照合: 本章が確定形式の出典（L1363〜L1365）。`_log_call` と `summary()` のコード、出力例の cost 値（Opus 26/118→$0.0025、Haiku 26/64→$0.0000、合計$0.0025）が一致することを再計算で確認。

## ファクトチェック対応後の再検証（2026-11-07）

- 変更: `_TYPE_TO_ERROR` に `"timeout_error": InternalServerError` を1行追加（L205・完成版）。
- 確認（偽APIなし、第10章時点の llm_client.py に同じ1行を加えたコピーで実施）: 402 `billing_error` → `APIError`・再試行しない／504 `timeout_error` → `InternalServerError`・再試行する／408 → 再試行する／400・429 spend cap（`enforced_spend_limit_reached`）→ 再試行しない／SSE の `timeout_error`（status なし）→ `InternalServerError`。
- 第10章の `pytest`: 5 passed（変更前と同じ）。
