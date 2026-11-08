# コード検証レポート（再検証）

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_06.md
検証日: 2026-11-08
コードブロック数: 27個（実行・構文検証の対象は20個＝python 14・bash 6。出力例の text 7個は照合のみ）
  ✅ 動作確認済み: 18個
  ⚠️ 要確認: 2個
  ❌ エラーあり: 0個
  🔍 構文チェックのみ: 0個

## 前回からの経緯

- 午前の検証では ❌1（#10: 6.2版 `execute_tool_uses` が `ValueError`／`ConnectError` を漏らして落ちる）と ⚠️1（#14: 6.3版で天気ツールの立て直し用メッセージが失われる）を指摘した。原稿はその後に修正された（#10 に `except Exception` を追加、#14 を `except (ToolError, ValueError)` に変更）。修正箇所の再チェックでも解消を確認済み。
- その後、6.3・6.4・検証の追加の3か所で、コードの置き場所の説明が番号付きの手順（L690〜693、L776〜777、L957〜959）に書き換えられた。6.3 の実行ログにもタイムスタンプが付いた。今回はこの状態の原稿から抽出し直して組み立て、全体を検証した。

## 検証方法

- 環境: Python 3.12.7 ＋ httpx 0.28.1 ＋ python-dotenv（スクラッチパッドの隔離 venv）。実 API キーは使わず、外部への実通信もしていない。
- 偽 API（`httpx.MockTransport`）: Claude API と Open-Meteo の両方を偽物にした。偽の Claude API は、2026-10-21 仕様に違反すると 4xx を返す。チェック項目は temperature・prefill・tool_result の欠落／順序／ID 不一致・強制 tool_choice・ツール名・strict の additionalProperties・構造化出力の非対応キーワード。
- 前提: 第4章の完成版 `llm_client.py` と、第5章の `tools/__init__.py`・`tools/weather.py`（5.4節の Open-Meteo 版）。未知の都市の確認には、ダミー版でも組み立てた（後述）。
- 組み立て: **番号付きの手順どおり**に、6.2 → 6.3 → 6.4 → 6.5 の順で適用した。
  - 6.3 agent.py（L690〜693）: (1) `import time`・`from concurrent.futures import ThreadPoolExecutor` を import 群へ、(2) 定数2つを `logger` の下へ、(3) `run_one_tool()` を `execute_tool_uses()` の直前へ、(4) `execute_tool_uses()` を関数ごと差し替え。結果として、すべて `__main__` より前に入る。
  - 6.3 tool_registry.py（L776〜777）: (1) `ToolInputError`・`_TYPE_MAP`・`validate_input()` を `ToolNotFoundError` の下・`RegisteredTool` の上へ、(2) `execute()` をメソッドごと差し替え。
  - 6.4 agent.py（L957〜959）: (1) `import json` を import 群へ、(2) `ask_approval()` を `run_one_tool()` の下へ、(3) `execute_tool_uses()` を最終形に置き換え。あわせて `build_registry()` に `register_file_tools` の2行を追加した（L1030〜1032 のコメント）。
- 偽 API が記録した仕様違反: **0件**（全実行を通して）。

## 段階ごとの確認結果（第6章の重点）

| 確認 | 6.2 | 6.3 | 6.4 |
|---|---|---|---|
| 東京の天気（1件） | ✅ 2ターンで終了 | ✅ | ✅ |
| 未知の都市（Open-Meteo 版で Atlantis） | ✅ `エラー: ValueError: 都市 'Atlantis' が見つかりません。英語表記（例: Tokyo）で指定してください。` が is_error で返り、WARNING ログが出た。ループは turn=2 まで進んだ | ✅ `エラー: 都市 'Atlantis' が見つかりません。…`（型名なし）が is_error で返った。立て直し用の文面がそのまま届く | ✅ 6.3 と同じ |
| 未知の都市（ダミー版で `agent.py "那覇の天気は？"`） | ✅ 落ちずに is_error で返り、turn=2 の end_turn まで進んだ（第5章と同じ文面） | — | — |
| Open-Meteo の接続エラー（`httpx.ConnectError`） | ✅ `エラー: ConnectError: connection refused`（is_error） | ✅ `logger.exception` でトレースバックを記録。Claude には「ツール get_weather の実行中に予期しないエラーが発生しました（ConnectError）。…」が返る | ✅ 6.3 と同じ |
| 未知のツール | ✅ ToolNotFoundError のメッセージ（is_error） | ✅ | ✅ 使えるツールの一覧に4つが並ぶ |
| 並列実行（forecast を1件0.6秒に遅延させ、3都市） | 1.80s（逐次） | ✅ 0.60s。結果は元の順 | ✅ 0.61s。結果は元の順 |
| 引数の検証（kelvin・必須なし・未知の引数・型違い） | — | ✅ 4種とも本文どおりのメッセージで is_error | ✅ |
| 承認 y／n | — | — | ✅ y なら summary.md を作成。n なら拒否メッセージの is_error が返り、ファイルは作られない。読み取り系は並行して実行され、結果は元の順に並ぶ |

本文の注意書きも再現して確かめた。
- L695: 6.3 の4点をすべて `__main__` の後ろに置くと、`agent tool=…` の行が出ず、逐次版のまま動いた。本文どおり。
- L779: 検証関数を `__main__` の後ろに置くと、`uv run python tool_registry.py` が `NameError: name 'validate_input' is not defined` で止まった。本文どおり。

---

## ❌ エラーが発生したコード

なし。

---

## ⚠️ 要確認のコード

### コードブロック #2・#3（server_tools_demo.py L176付近・実行コマンド L225）
**懸念点**: 偽 API では正常に終了した（`blocks: ['thinking', 'text']`）。`call_messages` をスタブに差し替えて、次の2点も確かめた。(1) `pause_turn`＋`container` の応答のあと、次の呼び出しに `extra={"container": "cont_1"}` と同じ `SERVER_TOOLS` が渡り、履歴は assistant で終わる。(2) `pause_turn` が続くと、4回目で「打ち切りました」になる。ただし、`web_search_20260209`＋`allowed_callers: ["direct"]` の実際の応答は、実 API でしか確認できない。`server_tool_use`／`web_search_tool_result` の並びや `usage.server_tool_use` がそれに当たる。
**推奨対処**: 実 API キーで1回実行し、出力例（L229〜）と照合する。

---

## ✅ 動作確認済みコード一覧

| # | 位置 | 言語 | 行数 | 実行結果 |
|---|------|-----|-----|--------|
| 1 | L74 description_examples.py | python | 37行 | 正常終了（定義だけのファイル） |
| 5 | L291 decorator_basics.py | python | 19行 | 本文どおり `{'hello': <function say_hello at 0x...>}`・`こんにちは` |
| 6 | L319 tool_registry.py（新規作成） | python | 106行 | 正常。名前順のソートと、重複・名前形式・type のチェックが動く |
| 7 | L454 tool_registry.py（`__main__`） | python | 40行 | 出力例 #9 と一致。#9 で「…（省略）」になっている部分と日時は除く |
| 8 | L499 | bash | 1行 | 同上。6.3 で検証関数を手順どおりに置いたあとも同じ出力になり、`NameError` は出ない |
| 10 | L528 agent.py（6.2版） | python | 73行 | 上の表のとおり。`except Exception` の分岐により、天気ツールの `ValueError`・`ConnectError` でも落ちない |
| 11 | L620 agent.py（build_registry・`__main__`） | python | 26行 | 正常 |
| 12 | L651 | bash | 1行 | ログが出力例 #13 と同じ並び・形式。asctime はミリ秒付きで、httpx の行は出ない |
| 14 | L697 agent.py（6.3） | python | 45行 | 上の表のとおり。`except (ToolError, ValueError)` で立て直し用の文面が届き、想定外の例外はトレースバックをログに残す |
| 15 | L755 | bash | 1行 | tool_use 3件を並行して実行し、`agent tool=get_weather elapsed=…` が3行出た。tool_result は元の順で、1つの user メッセージにまとまる |
| 17 | L781 tool_registry.py（6.3: 検証） | python | 49行 | `kelvin`・必須なし・未知の引数・型違い（123）が、すべて本文どおりのメッセージの is_error になる |
| 18 | L863 tools/files.py | python | 75行 | safe_path は次のパスを拒否した: `../.env`・`..\..\x`・`a/../../b`・`../workspace_old/x`・`/etc/passwd`（Windows で `C:\etc\passwd` に解決）・`C:/Windows/win.ini`・空文字。`notes.md`・`.`・`sub/../ok.md` は許可した。read_file の400行の区切り・`start_line`・UTF-8 以外の拒否、list_files、存在しないディレクトリの扱いも本文どおり |
| 19 | L961 agent.py（6.4: ask_approval / execute_tool_uses） | python | 39行 | 上の表のとおり |
| 20 | L1005 tools/files.py（register_file_tools） | python | 27行 | 4つのツールを登録し、write_file は side_effect=True |
| 21 | L1037 | bash | 1行 | 4ターンで完走した（list_files → read_file → 承認 → write_file → end_turn）。`"../.env の中身を見せて"` は「workspace の外を指しています」の is_error になる |
| 23 | L1087 structured_output.py | python | 61行 | Haiku 5.5・`max_tokens=2000`・`output_config={"format":…, "effort":"low"}` で送信した。スキーマどおりの JSON を `json.loads()` で読めた。偽 API のスキーマ検査でも違反なし |
| 24 | L1153 | bash | 1行 | 同上 |
| 26 | L1186 structured_output.py（strict ツール） | python | 28行 | 本文の指示どおり、`__main__` の上に追記し、末尾に `demo_strict_tool(SAMPLE_EMAIL)` を足した。`create_ticket {...}` が出力された。400 は出ない |

## 出力例（text ブロック）の照合

| # | 位置 | 照合結果 |
|---|------|--------|
| 4 | L229 | 実 API でしか確認できない（⚠️ #2 を参照） |
| 9 | L503 | 一致 |
| 13 | L655 | 形式・順序が一致。コストを単価表（$4/$20）で再計算した。$0.0060＋$0.0062＝$0.0122 で、in・out の合計（2,188／170）も一致 |
| 16 | L759 | **タイムスタンプ付きに更新された部分も一致**。形式（`%(asctime)s %(name)s %(message)s`）は実際のログと同じ。3件が turn=1 の 0.59〜0.64 秒後に終わっており、各 `elapsed`（0.58〜0.63s）と整合する。L770 の「約1.8秒 → 約0.6秒」も、遅延 0.6 秒の実測（1.80s → 0.60s）と一致 |
| 22 | L1041 | 承認プロンプトの文言と JSON プレビューが一致 |
| 25 | L1157 | キー7つ・enum の値で形が一致 |
| 27 | L1219 | 形が一致 |

## 補足（軽微・修正は任意）
- L695 の「後ろに置くと、逐次版のまま動いてしまいます」は、4点すべてを後ろに置いた場合の説明として正しい。一部だけを後ろに置いた場合は動きが変わる。たとえば `execute_tool_uses()` だけをその場で差し替え、定数を後ろに置くと、実行時に `NameError: name 'MAX_PARALLEL_TOOLS' is not defined` になる。番号付きの手順どおりなら起きないので、修正は不要。
- `read_file` で `start_line` が全行数を超えると、見出しが `[long.txt 行2000-1999 / 全1000行]` になる。エラーではない（午前から変わらず）。
- 6.2版 `run_agent()` の `pause_turn` 分岐は container を引き継がない。ただし、本章のレジストリにはサーバーツールを登録できないので実害はない（本文の説明どおり）。

> ⚠️ **検証の限界**: 実 API の応答（ツール選択・並列呼び出しの有無・サーバーツール）は、偽 API では再現できません。公開前に実 API キーで 6.1 のデモと、6.2〜6.5 の実行例を一度通してください。
