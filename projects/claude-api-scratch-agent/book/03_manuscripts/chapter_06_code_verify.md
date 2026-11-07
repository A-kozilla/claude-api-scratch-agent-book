# コード検証レポート

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_06.md
検証日: 2026-11-07
コードブロック数: 27個（実行・構文検証の対象 20個 ＝ python 14・bash 6／出力例の text 7個は照合のみ）
  ✅ 動作確認済み: 18個（2026-11-07 の⚠️対応後。対応前は 13個）
  ⚠️ 要確認: 2個（実APIでのみ確認できる #2・#3。対応前は 7個）
  ❌ エラーあり: 0個
  🔍 構文チェックのみ: 0個

## 検証方法

- 環境: Python 3.12 + httpx + python-dotenv。APIキーなし。偽の Claude API（2026-10-21 仕様違反を 4xx で返すモック。並列 tool_use・構造化出力・strict ツール検証つき）に httpx を差し替えて実行した。
- 前提の再現: 第4章完成版 `llm_client.py`（chapter_04.md 末尾の全体コード）、第5章の `tools/__init__.py`・`tools/weather.py`（GET_WEATHER_TOOL＋5.4節の Open-Meteo 版 get_weather）・`agent.py`。
- 組み立て: 6.2 → 6.3 → 6.4 の順に、本文の「新規作成／末尾に追記／関数の更新」を関数単位で適用し、各段階の `agent-from-scratch/` で実行した。
- モックが記録した仕様違反（temperature・prefill・tool_result 欠落／順序・strict の additionalProperties など）: **0件**。

## 主な確認結果

| 確認項目 | 結果 |
|---|---|
| 並列 tool_use の結果が1つの user メッセージで返るか | ✅ モックが tool_use 2件（get_weather・list_files）を返し、次のリクエストは tool_result 2件を含む user メッセージ1件だった。tool_result は先頭に配置 |
| is_error | ✅ 未知のツール・必須引数なし・enum 外（kelvin）・bool の integer 誤用・未知の引数・ファイルなし・workspace 外のパスが、すべて `is_error: True` の tool_result になった（メッセージも本文の例どおり） |
| safe_path のパストラバーサル拒否 | ✅ `../.env`・`..\..\x`・`a/../../b`・`../workspace_old/x`（前方一致の罠）・`/etc/passwd`（Windows では本文の説明どおり配下チェックで拒否）・`C:/Windows/win.ini`（絶対パス）・空文字をすべて拒否。`notes.md` は許可 |
| 副作用ツールの承認 | ✅ 標準入力 y で write_file 実行（途中ディレクトリも作成）、n で拒否の is_error を返し、読み取り系は並行して実行。結果は元の tool_use の順 |
| 構造化出力・strict ツール | ✅ `output_config.format` で `json.loads()` が通る。strict ツールは additionalProperties: false あり・tool_choice auto で 400 にならない |

---

## ❌ エラーが発生したコード

なし。

---

## ⚠️ 要確認のコード

### コードブロック #2・#3（server_tools_demo.py L176付近）

**懸念点**: モック上では tools にクライアントツールがないため `end_turn` で終わり、`blocks: ['thinking', 'text']` までは確認できた。`web_search_20260209` の実行・`server_tool_use`／`web_search_tool_result` ブロック・`pause_turn` 後の再送（assistant で終わる履歴を送る正規手順）は実APIでしか確認できない。
**推奨対処**: 実APIキーで1回実行し、出力例（L225〜）の blocks の並びと `usage.server_tool_use` を確認する。

### コードブロック #11（agent.py 末尾に追記: 動作確認用のエントリーポイント L612付近）と出力例 #13（L646付近）

**懸念点**: 実行は成功するが、出力が本文の例と形が違う。
1. `logging.basicConfig(level=logging.INFO)` だけなので、httpx の `HTTP Request: POST ...` の INFO ログが毎回混ざる（第4章 L662 の NOTE で説明している現象）。
2. 第4章の実ログ形式は `llm_client request_id=req_... model=claude-opus-5-5 stream=False elapsed=1.84s stop=tool_use in=1012 out=96 cache_write=0 cache_read=0 cost=$0.0061` だが、出力例は `request-id=req_011C... model=... 1.84s in=1012 out=96` と形式が異なる（「ログの細部は…変わります」の断りはある）。
**推奨対処**: `logging.basicConfig(...)` の直後に `logging.getLogger("httpx").setLevel(logging.WARNING)` を1行足し、出力例のログ行を第4章の形式（`request_id=... stream=False elapsed=... stop=... in=... out=... cache_write=... cache_read=... cost=$...`）にそろえる。

### コードブロック #12（L642付近 bash）

**懸念点**: 上記 #11・#13 と同じ（出力の形が本文と異なる）。コマンド自体は正常終了。

### コードブロック #14（agent.py 6.3: import と定数を追加し、run_one_tool を新設 L681付近）

**懸念点**: 追加位置が書かれていない。読者が6.2節で追記した `if __name__ == "__main__":` ブロックの**後ろ**に貼ると、`uv run python agent.py` 実行時は `__main__` が先に走るため、古い逐次版 `execute_tool_uses` のまま動く（エラーにならず並列化されないので気づきにくい）。
**推奨対処**: 見出しコメントか本文に「import は先頭の import 群に、定数は `logger` の下に、`run_one_tool()` は `execute_tool_uses()` の上に置き、`execute_tool_uses()` は関数全体を置き換える」と1文添える。

### コードブロック #17（tool_registry.py 6.3: ToolInputError と検証関数を追加 L760付近）

**懸念点**: 追加位置が書かれていない。6.2節でファイル末尾に `__main__` ブロックを追記しているため、`ToolInputError`・`_TYPE_MAP`・`validate_input()` をファイル末尾に足すと、`uv run python tool_registry.py` が次のエラーで止まる（再現済み）。
```
NameError: name 'validate_input' is not defined
```
（モジュールとして import する `agent.py` からの利用は問題なし）
**推奨対処**: 「`ToolInputError` と `_TYPE_MAP`・`validate_input()` は `ToolNotFoundError` の下（`RegisteredTool` の上）に追加し、`ToolRegistry.execute()` はメソッド全体を差し替える」と明記する。

### コードブロック #26（structured_output.py 追記: strict ツールの例 L1156付近）

**懸念点**: 「追記してください」の後で「`demo_strict_tool(SAMPLE_EMAIL)` を呼ぶと」とあるが、呼び出し方が示されていない。ファイル末尾（`__main__` ブロックの後ろ）に追記した場合、`__main__` 内に呼び出しを書くと `NameError` になる。モックでは `uv run python -c "import structured_output as s; s.demo_strict_tool(s.SAMPLE_EMAIL)"` で正常に `create_ticket {...}` が出力された。
**推奨対処**: 追記位置を「`if __name__ == "__main__":` の上」と明記し、`__main__` に `demo_strict_tool(SAMPLE_EMAIL)` を1行足す。

---

## ✅ 動作確認済みコード一覧

| # | 位置 | 言語 | 行数 | 実行結果 |
|---|------|-----|-----|--------|
| 1 | L74 description_examples.py | python | 37行 | 正常終了（定義のみ） |
| 5 | L287 decorator_basics.py | python | 19行 | 本文どおり `{'hello': <function ...>}`・`こんにちは` |
| 6 | L315 tool_registry.py（新規作成） | python | 106行 | 正常。名前順ソート・重複／名前形式チェック動作 |
| 7 | L450 tool_registry.py（__main__） | python | 40行 | 出力例 #9 と一致（add_numbers が先、`{"result": 5.5}`、ToolNotFoundError のメッセージ） |
| 8 | L495 | bash | 1行 | 同上 |
| 10 | L524 agent.py（6.2版） | python | 69行 | turn=1 tool_use → turn=2 end_turn。tracker.summary 出力 |
| 15 | L739 | bash | 1行 | 6.3版で正常（ツール1種のためモックの tool_use は1件。並列は6.4で確認） |
| 18 | L842 tools/files.py | python | 75行 | safe_path・list_files・read_file（行番号・ヘッダー）・write_file 正常 |
| 19 | L936 agent.py（6.4: ask_approval / execute_tool_uses） | python | 39行 | 承認 y/n・読み取り系の並行実行・元の順序で返却を確認 |
| 20 | L980 tools/files.py（register_file_tools） | python | 27行 | 4ツール登録（get_weather, list_files, read_file, write_file） |
| 21 | L1012 | bash | 1行 | FAKEAPI_TOOL_ROUNDS=3 で4ターン完走、仕様違反0件 |
| 23 | L1062 structured_output.py | python | 58行 | スキーマどおりの JSON が `json.loads()` で読める |
| 24 | L1125 | bash | 1行 | 同上 |

## 出力例（text ブロック）の照合

| # | 位置 | 照合結果 |
|---|------|--------|
| 4 | L225 | 実APIのみ（⚠️ #2 参照） |
| 9 | L499 | 一致 |
| 13 | L648 | ✅ 2026-11-07 修正で第4章形式に統一・httpx ログなし |
| 16 | L743 | 形は一致（`agent tool=get_weather elapsed=...s`） |
| 22 | L1016 | 形は一致（承認プロンプトの文言・JSON プレビュー） |
| 25 | L1129 | 形は一致（キー7つ・enum 値） |
| 27 | L1188 | 形は一致 |

## 補足（コード以外）

- L600「ループ本体は、この節以降もう変更しません」は第6章内では正しいが、第7章で `run_agent()` を更新する。気になる場合は「この章では」と範囲を限定するとよい。
- 空ファイルを `read_file` すると見出しが `[x.md 行1-0 / 全0行]` になる（エラーではない）。

---

## ⚠️対応（2026-11-07）

| # | 対応 | 内容 |
|---|------|------|
| 11・12・13 | 修正 | agent.py 6.2版 `__main__` の `logging.basicConfig(...)` 直後に `logging.getLogger("httpx").setLevel(logging.WARNING)` を追加。出力例のログ行を第4章の確定形式（`request_id=... stream=False elapsed=... stop=... in=... out=... cache_write=0 cache_read=0 cost=$...`、asctime はミリ秒付き）に、`tracker.summary()` を `input=2,188`（桁区切り）に変更。コストは単価表どおり $0.0060＋$0.0062＝$0.0122 で summary と一致。前置きの「ログの細部は…変わります」は「`llm_client` の行は第4章で作ったログで、数値は一例です」に変更 |
| 14 | 修正 | 6.3 の agent.py ブロック直前に配置の説明を追加（import は先頭の import 群、定数は `logger` の下、`run_one_tool()` は `execute_tool_uses()` の直前、`execute_tool_uses()` は関数全体を差し替え、いずれも `__main__` より前） |
| 17 | 修正 | 6.3 の tool_registry.py ブロック直前に「`ToolInputError`・`_TYPE_MAP`・`validate_input()` は `ToolNotFoundError` の下（`RegisteredTool` の上）、`execute()` はメソッド全体を差し替え。`__main__` より後ろに置くと `NameError`」を追加 |
| 19（関連） | 修正 | 6.4 の agent.py ブロック直前にも「`import json` は先頭、`ask_approval()` は `run_one_tool()` の下、`execute_tool_uses()` は6.3の並列版をまるごと置き換え」を追加（並列版→最終形の差し替え箇所を明確化） |
| 26・27 | 修正 | 追記位置を「`if __name__ == "__main__":` の上」と明記。出力例の前置きを「`__main__` の末尾に `demo_strict_tool(SAMPLE_EMAIL)` の1行を足して `uv run python structured_output.py` を実行すると、抽出結果のJSONに続けて…」に変更 |
| 補足 L600 | 修正 | 「ループ本体は、この節以降もう変更しません」→「この章では、ループ本体はこの節以降もう変更しません」（第7章で `run_agent()` を更新するため） |
| 2・3（・出力例4） | 未対応（残） | サーバーツール（`web_search_20260209`・`pause_turn`）の実挙動はモックで再現不可。実APIキーでの確認が必要 |

コードブロックの数・順番は変えていない（本文の追加は各1〜3文）。

### 再実行結果（偽API）

修正後の原稿から `ch06_07/assemble6b.py`（structured_output.py は strict 例を `__main__` の上に挿入し、`__main__` 末尾に呼び出しを追加）で 6.2／6.3／6.4 を組み立て直して実行した。

| 確認 | 結果 |
|---|---|
| 6.2 `uv run python agent.py "東京の今の天気を教えて"` | ✅ httpx の `HTTP Request:` 行なし。ログ行が第4章形式で出力例と同じ並び（llm_client → agent turn=1 → llm_client → agent turn=2 → 回答 → `calls=2 input=… total=$…`） |
| 6.3 `uv run python tool_registry.py`（検証関数を `ToolNotFoundError` の下に配置） | ✅ `NameError` なし。出力例 #9 と一致 |
| 6.3 `uv run python agent.py "東京・大阪・札幌…"` | ✅ 並列版 `execute_tool_uses` で `agent tool=get_weather elapsed=…` が出る |
| 6.4 `uv run python agent.py "…summary.md に書き出して"`（FAKEAPI_TOOL_ROUNDS=3） | ✅ 4ターン完走、仕様違反0件 |
| 6.5 `uv run python structured_output.py` | ✅ 抽出JSONに続けて `create_ticket {"title": …, "department": "経理", "priority": "P1"}` |

> ⚠️ **検証の限界**: 実APIの応答（ツール選択・並列呼び出しの有無・サーバーツール）はモックでは再現できません。公開前に実APIキーで 6.2〜6.5 の実行例を一度通してください。

## ファクトチェック対応後の再検証（2026-11-07）

- `server_tools_demo.py`（`allowed_callers: ["direct"]`・`container` 引き継ぎ・再開上限）: 構文OK。偽APIで実行し正常終了（サーバーツール自体は偽APIでは再現されない）。`call_messages` を差し替えたスタブで、`pause_turn`＋`container` の応答の次の呼び出しに `extra={"container": "cont_1"}` と同じ tools が渡ること、`pause_turn` が続くと4回で打ち切ることを確認。
- `structured_output.py`（`output_config` に `"effort": "low"`、strict デモにも `output_config={"effort": "low"}`）: 偽APIで抽出JSON → `create_ticket {...}` の順に出力され、400なし。
> ⚠️ 実APIでの `allowed_callers` の挙動・`pause_turn` の発生は未確認。公開前に実APIキーで一度通してください。
