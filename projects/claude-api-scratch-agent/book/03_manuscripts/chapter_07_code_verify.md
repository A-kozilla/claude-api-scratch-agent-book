# コード検証レポート

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_07.md
検証日: 2026-11-07
コードブロック数: 30個（実行・構文検証の対象 25個 ＝ python 16・bash 6・json 3／出力例の text 5個は照合のみ）
  ✅ 動作確認済み: 19個（2026-11-07 の⚠️対応後。対応前は 15個）
  ⚠️ 要確認: 0個（対応前は 4個）
  ❌ エラーあり: 2個（**いずれも原稿を修正済み**。修正後に再実行して解消を確認）
  🔍 構文チェックのみ: 4個

## 検証方法

- 環境: Python 3.12 + httpx + python-dotenv。APIキーなし。偽の Claude API（2026-10-21 仕様違反を 4xx で返す。count_tokens・cache_control 付き usage に対応）に httpx を差し替えて実行。
- 前提の再現: 第4章完成版 `llm_client.py`、第5章の成果物、第6章の手順で組み立てた 6.4 時点の `agent-from-scratch/`（chapter_06_code_verify.md 参照）。
- 組み立て: `llm_client.py` 末尾に `count_tokens()`・キャッシュ補助関数、`context.py`（計測 → 切り詰め → 段階1 → 書き起こし → 要約 → maybe_compact、`__main__` に動作確認3ブロック）、`tools/memory.py`、7.3 の `run_agent()` 更新、7.4 の `__main__`、7.5 の effort 例。
- 長い履歴の検証: しきい値を 2,500〜3,000 に下げ、keep_last を 1・2・4・5 に変え、tool_use を最大20ターン返させて run_agent を回し、送信された全リクエストの履歴を検査した。

## 主な確認結果

| 確認項目 | 結果 |
|---|---|
| maybe_compact が tool_use/tool_result のペアを壊さないか | ✅ 全リクエスト（最大38回）で「tool_result の id 集合＝直前 assistant の tool_use の id 集合」「先頭が user」「同じ role の連続なし」。モックの仕様違反0件 |
| 繰り返し圧縮したときの header | ❌→修正済み。修正前は `<original_request>` が圧縮のたびに入れ子になり、20ターンで18重・先頭メッセージ2,617字に膨張。修正後は常に1つ（152字） |
| count_tokens | ✅ `/v1/messages/count_tokens` に model・messages・system・tools を送信し `{"input_tokens": N}` を int で返す。失敗時は estimate_tokens が近似値に切り替わる |
| cache_control の付け方 | ✅ 毎回のリクエストで tools の最後の1件・system ブロック末尾・トップレベル `cache_control` の3か所（上限4以内）。要約用の FAST_MODEL 呼び出しには付かない。`usage.cache_read_input_tokens` がログの cache_read に出る |
| effort | ✅ `output_config: {"effort": "low"/"high"}` が送られ、400 にならない |
| 長期メモリ | ✅ 同じ key の上書き・大小文字を無視した AND 検索・該当なし・memory_prompt の差し込み（system ブロックに `<long_term_memory>` が入る） |

---

## ❌ エラーが発生したコード

### コードブロック #21（agent.py 第7章版 L1012付近 → 修正後 L1021付近）

**元のコード**（抜粋）:
```python
# agent.py（第7章版: 圧縮とキャッシュに対応）
import logging
from concurrent.futures import ThreadPoolExecutor

from context import maybe_compact
from llm_client import cached_system, cached_tools, call_messages, extract_text, get_tool_uses
from tool_registry import ToolRegistry
...
def _run_one(registry: ToolRegistry, block: dict) -> dict:
    """1つの tool_use を実行し、tool_result ブロックを返す（第6章と同じ）。"""
...
        if stop == "tool_use":
            uses = get_tool_uses(response)
            with ThreadPoolExecutor(max_workers=min(8, len(uses))) as pool:
                results = list(pool.map(lambda b: _run_one(registry, b), uses))
```

**エラー内容**:
1. ファイル全体の置き換えとして読むと（import 群・logger から始まる完全なファイルの形をしている）、7.4 の `__main__` が動かない。
```
NameError: name 'build_registry' is not defined
```
（`tracker` も import されておらず、`BASE_SYSTEM` もどこにも定義されていない）
2. 関数の差し替えとして読んでも、ツール実行が第6章の `execute_tool_uses()` から `_run_one()` に戻り、**副作用ツールの承認（ask_approval）が消える**。`write_file` だけを持つレジストリで実行したところ、確認なしで `workspace/notes.md` が上書きされた。第6章の「副作用ツールは承認なしで実行しない」方針と矛盾し、`_run_one` の docstring「第6章と同じ」も事実と異なる（MAX_TOOL_RESULT_CHARS の切り詰め・ToolError と想定外例外の区別・pause_turn 分岐も失われる）。

**原因**: 第7章版の run_agent が第6章の最終形（execute_tool_uses）ではなく、簡略化した独自のツール実行を持っていた。

**修正内容（原稿に反映済み）**:
```python
# agent.py（第7章版: import と定数 BASE_SYSTEM を追加し、run_agent を更新。ほかの関数は第6章のまま）
from context import maybe_compact
from llm_client import cached_system, cached_tools

# エージェントの基本方針（7.4節で使う）。日時などの可変値は入れない
BASE_SYSTEM = "あなたは作業ディレクトリ workspace/ のファイルを扱うアシスタントです。"


def run_agent(..., effort: str | None = None) -> str:
    ...（maybe_compact・3つのブレークポイント・effort は元のまま）
        if stop_reason == "tool_use":
            # 第6章の execute_tool_uses をそのまま使う（並列実行・副作用ツールの承認・is_error）
            results = execute_tool_uses(registry, get_tool_uses(response))
            messages.append({"role": "user", "content": results})
            continue
        if stop_reason == "pause_turn": ...
        if stop_reason == "max_tokens": ...
        if stop_reason == "refusal": ...
        return extract_text(response)
```
あわせて、コードの前に「import は既存の import の下、`BASE_SYSTEM` は `logger` の近く、`run_agent()` は関数全体を差し替え」の1文、コードの後に「ツール実行は第6章の `execute_tool_uses()` に任せる」旨の3文を追加。7.4節の「`BASE_SYSTEM` は…のように定義しておきます」は「7.3節で追加した定数」に変更。
修正後: 7.4 の `__main__`（2回の実行）、7.5 の effort 例、承認の呼び出し、キャッシュの3ブレークポイントをすべて再確認済み。後続章（第8章以降）で `_run_one` を参照している箇所はない。

### コードブロック #16（context.py 自動圧縮 maybe_compact / _first_user_text L713付近）

**元のコード**:
```python
def _first_user_text(messages: list[dict]) -> str:
    """最初の user メッセージの本文（最初の依頼）を取り出す。"""
    for message in messages:
        if message["role"] == "user" and not _is_tool_result_message(message):
            content = message["content"]
            if isinstance(content, str):
                return content
            return "".join(b.get("text", "") for b in content if b.get("type") == "text")
    return ""
```

**エラー内容**: 例外は出ないが、2回目以降の圧縮で誤動作する。圧縮後の履歴の先頭は header（`<original_request>…<conversation_summary>…`）の user メッセージなので、`_first_user_text()` が header 全体を「最初の依頼」として返し、次の header の `<original_request>` に前回の header がまるごと入る。
```
先頭 user の長さ: 2617  <original_request> の出現回数: 18
```
圧縮のたびに header が線形に膨らみ、古い要約が重複して残る。本文の「何度圧縮しても目的を見失いません」とも食い違う。

**修正内容（原稿に反映済み）**:
```python
            if isinstance(content, str):
                text = content
            else:
                text = "".join(b.get("text", "") for b in content if b.get("type") == "text")
            # 圧縮済みの履歴なら、先頭は要約メッセージ。<original_request> の中身だけを取り出す
            if "<original_request>\n" in text:
                text = text.split("<original_request>\n", 1)[1].split("\n</original_request>", 1)[0]
            return text
```
解説に2文を追加（2回目以降は先頭が要約メッセージになること、タグの中身だけを取り出す理由）。修正後: 20ターン・圧縮19回で `<original_request>` は常に1つ、先頭メッセージは152字で一定。

---

## ⚠️ 要確認のコード

### コードブロック #17・#18（context.py `__main__` 末尾に追加: 圧縮の体験 L809付近）

**懸念点**: 6件の動作確認用履歴 `history` は最後が assistant（"完了"）なので、`maybe_compact()` 内の count_tokens が「最後が assistant＝prefill」として 400 になる可能性がある（モックは 400 を返した）。`estimate_tokens()` の近似値フォールバックで処理は最後まで進み、`圧縮前 6 件 → 圧縮後 4 件` と header の表示は本文どおりだったが、出力に `context WARNING count_tokens に失敗したため近似値を使います: [400 invalid_request_error] ...` が3回混ざり、トークン数も文字数ベースになる。また `logging.basicConfig(level=logging.INFO)` だけなので httpx の INFO ログも混ざる。実際のエージェントループでは maybe_compact 時の履歴は必ず user で終わるため、本番経路には影響しない。
**推奨対処**: 実APIで count_tokens が末尾 assistant を受け付けるか確認する。受け付けない場合は、`long_history = copy.deepcopy(history)[:5]`（tool_result で終わる5件）にして出力例と解説の件数を合わせ直すか、出力例にこの WARNING が出ることを注記する。`logging.getLogger("httpx").setLevel(logging.WARNING)` も1行足すとよい。

### コードブロック #24（tools/memory.py L1152付近）

**懸念点**: 動作は正常。ただし `save_memory` は永続ファイルを書き換えるのに `side_effect=True` が付いていないため、第6章の承認（ask_approval）を通らない。本文 L1295 の WARNING（悪意ある文書が偽の指示を記憶させる危険）に対して、コード側の防御がない状態。
**推奨対処**: `register_memory_tools()` の save_memory 登録に `side_effect=True` を付ける（承認を挟む）か、付けない理由を本文で1文説明する。

### コードブロック #26（agent.py 第7章版の __main__ L1257付近）

**懸念点**: 引数ありでは正常（system に `<long_term_memory>` が差し込まれ、cache_control 付きで送信された）。ただし引数なしで `uv run python agent.py` とすると `IndexError: list index out of range`（第6章版にはあった既定の質問がなくなった）。httpx の INFO ログも混ざる。出力例 #28 には `tracker.summary()` の行がない。
**推奨対処**: `sys.argv[1] if len(sys.argv) > 1 else "workspace のファイルを一覧にして"` のように既定値を戻し、`logging.getLogger("httpx").setLevel(logging.WARNING)` を足す。出力例に `calls=... total=$...` の行を加える。

---

## 🔍 構文チェックのみ

| # | 位置 | 言語 | 内容 |
|---|------|-----|-----|
| 1 | L87 count_tokens の curl | bash | `bash -n` で構文OK。実APIキーが必要なため未実行（同じボディを Python 版 count_tokens でモックに送り、200 を確認） |
| 2 | L103 `{"input_tokens": 31}` | json | パースOK |
| 8 | L407 tool_use/tool_result の履歴例 | json | パースOK |
| 29 | L1315 thinking ブロックを含むレスポンス例 | json | パースOK。`usage.output_tokens_details.thinking_tokens` は claude-api-facts.md に記載がないため、ファクトチェックで公式ドキュメントを確認すること |

---

## ✅ 動作確認済みコード一覧

| # | 位置 | 言語 | 行数 | 実行結果 |
|---|------|-----|-----|--------|
| 3 | L123 llm_client.py count_tokens | python | 22行 | 第4章の `_send_with_retry()`（dict を返す）と整合。int を返す |
| 4 | L170 context.py 計測部分 | python | 55行 | estimate_tokens・token_breakdown 正常（4キーの dict） |
| 5 | L248 context.py `__main__`（内訳） | python | 19行 | 出力例 #7 と同じ4行の形 |
| 6 | L274 | bash | 2行 | 同上 |
| 9 | L445 安全な切断位置と切り詰め | python | 32行 | keep_last=1〜5 でペア破壊なし |
| 10 | L507 `__main__` 内に追加（assert） | python | 16行 | `__main__` ブロック内に追加すると `truncate_history: OK`。単独ファイルでは IndentationError になる抜粋のため、本文に「`__main__` ブロックの末尾に、インデントを付けたまま追加」の1文を追加した |
| 11 | L531 | bash | 2行 | 出力例 #12 と同じ形 |
| 13 | L556 段階1 shrink_old_tool_results | python | 32行 | deepcopy で元の履歴を変えず、tool_use_id・is_error を保持 |
| 14 | L617 書き起こし _to_transcript | python | 29行 | text/tool_use/tool_result（エラー印）を変換、thinking は除外 |
| 15 | L662 要約 summarize_history | python | 23行 | FAST_MODEL（claude-haiku-5-5）・max_tokens=4000 で送信 |
| 20 | L973 cached_system / cached_tools | python | 20行 | 元のスキーマを書き換えずに最後の1件だけに cache_control |
| 22 | L1094 | bash | 2行 | 修正後の agent.py で正常。cache_read が2回目以降に計上される |
| 25 | L1239 memory_prompt | python | 8行 | 記憶なしで空文字、ありで `<long_term_memory>` |
| 27 | L1280 | bash | 3行 | 1回目・2回目とも正常終了、2回目の system に記憶が入る |
| 30 | L1352 effort の使い分け例 | python | 8行 | 修正後の agent.py で正常（effort low/high が送信される） |

（#16・#21 は ❌ として上に記載。修正後はいずれも動作確認済み）

## 出力例（text ブロック）の照合

| # | 位置 | 照合結果 |
|---|------|--------|
| 7 | L279 | 形は一致 |
| 12 | L536 | 形は一致 |
| 19 | L841 | ✅ 2026-11-07 修正で 5件→3件・第4章形式のログ行に統一（count_tokens の WARNING は出ない） |
| 23 | L1107 | ✅ 2026-11-07 修正で第4章の実形式に統一 |
| 28 | L1299 | ✅ 2026-11-07 修正で承認プロンプトと `tracker.summary()` 行を追加 |

---

## ⚠️対応（2026-11-07）

| # | 対応 | 内容 |
|---|------|------|
| 17・18・19 | 修正 | 圧縮デモを `long_history = copy.deepcopy(history[:5])`（tool_result で終わる5件）に変更し、count_tokens が assistant 終わり＝prefill 扱いで 400 になる経路をなくした。`logging.getLogger("httpx").setLevel(logging.WARNING)` を追加。解説に「6件目の assistant を除いた理由（prefill 扱いで count_tokens が 400 を返すことがある／実際のループでは圧縮時の履歴は必ず user で終わる）」の2文を追加。出力例を `圧縮前 5 件 → 圧縮後 3 件` に、要約リクエストのログ行を第4章形式（`stream=False elapsed=2.10s stop=end_turn … cache_write=0 cache_read=0 cost=$0.0002`）に変更。段階1で縮小対象がないため2行目の「要約による圧縮」の前の値を1行目と同じ 5,312 にそろえ、本文の「5,198トークン…6件の履歴が4件」も「5,312トークン…5件の履歴が3件」に修正 |
| 23（出力例） | 修正 | キャッシュ効果のログ行を第4章形式に統一（`request_id=… stream=False elapsed=… stop=… in=152 out=96 cache_write=3418 cache_read=0 cost=$0.0196` 等。桁区切りなし）。2行目の cache_read を書き込み量と同じ 3,418 にそろえ（本文も 3,418 に）、コストは単価表（Opus 5.5 cache_write $5・cache_read $0.20）で再計算。前置きに「`llm_client` の行だけを抜き出したもの」と注記 |
| 24 | 修正（付ける） | `register_memory_tools()` の save_memory 登録に `side_effect=True` を追加し、第6章の `execute_tool_uses()` → `ask_approval()` を通るようにした。本文に「記憶は以降のすべての会話に影響するので、`write_file` と同じく保存前に承認を挟む」の2文を追加（L1295 の WARNING「保存内容を人間が確認できるように」と整合）。第8章以降に save_memory／register_memory_tools の利用はなく、第11章の guardrails は side_effect の扱いを一般化するだけなので影響なし |
| 26・28 | 修正 | `__main__` に `logging.getLogger("httpx").setLevel(logging.WARNING)` と `question = sys.argv[1] if len(sys.argv) > 1 else "workspace のファイルを一覧にして"` を追加し、`run_agent(question, …)` に変更（引数なしの IndexError を解消）。出力例に1回目の承認プロンプト（save_memory）と、各回の `tracker.summary()` 行（`calls=… input=… cache_write=… cache_read=… total=$…`）を追加。本文に「1回目は save_memory の実行前に承認を求められ…（ログの行は省略）」の1文を追加 |

コードブロックの数・順番は変えていない。

### 再実行結果（偽API）

第6章の修正後原稿で組み立て直した `ch06_07/p6.4b` を元に、修正後の第7章原稿から `assemble7c.py` で `ch06_07/p7G` を組み立てて実行した。

| 確認 | 結果 |
|---|---|
| `uv run python context.py` | ✅ count_tokens の WARNING 0件・httpx ログ0件。`圧縮前 5 件 → 圧縮後 3 件`、header（`<original_request>`／`<conversation_summary>`）は本文どおり。仕様違反0件 |
| `uv run python agent.py`（引数なし） | ✅ IndexError なし。既定の依頼で完走し、`calls=2 input=… cache_read=… total=$…` を表示 |
| `echo y \| uv run python agent.py "今後レポートは…覚えておいて"` | ✅ 正常終了。仕様違反0件 |
| save_memory の承認（registry に memory ツールのみ、`execute_tool_uses` を直接呼ぶ） | ✅ `is_side_effect("save_memory")=True`／search_memory は False。`n` で拒否の is_error が返り memory.json は作られない。`y` で保存される。search_memory は承認なしで並行実行 |
| 長い履歴の回帰（t7.py、threshold=2500・keep_last=2、20ターン） | ✅ 38リクエストすべてでペア・role 交互・先頭 user を満たす。`<original_request>` は常に1つ。仕様違反0件 |
| 7.5 effort 例 | ✅ 正常終了 |

> ⚠️ **検証の限界**: キャッシュの実際のヒット・最小キャッシュ長・count_tokens の値・要約の品質はモックでは再現できません。公開前に実APIキーで 7.1〜7.4 の実行例を一度通してください。
