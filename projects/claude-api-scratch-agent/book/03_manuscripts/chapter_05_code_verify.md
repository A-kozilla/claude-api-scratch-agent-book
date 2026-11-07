# コード検証レポート

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_05.md
検証日: 2026-11-07
検証環境: Python 3.12 / uv 0.13.5 / httpx 0.28.1 / 偽Claude API（tools があれば1回 tool_use を返す）/ 第4章完成版 llm_client.py / Open-Meteo（偽API＋実APIの両方）
コードブロック数: 21個（うち出力例・説明文例の `text` 6個は判定数に含めない → 判定対象 15個）
  ✅ 動作確認済み: 12個
  ⚠️ 要確認: 0個（2個を2026-11-07に原稿修正済み → ✅へ移動）
  ❌ エラーあり: 2個（原稿修正済み）
  🔍 構文チェックのみ: 1個

---

## ❌ エラーが発生したコード

### コードブロック #8（L504付近）・#9（L550付近）対話モードの記録【原稿修正済み】

**元のコード**:
```text
​```python
# 対話モードで1行ずつ入力する（>>> はプロンプトなので入力しない）
>>> from llm_client import call_messages, get_tool_uses
...
```

**エラー内容**:
```text
SyntaxError: invalid syntax
```

**原因**: `>>>` プロンプトと出力を含む REPL の記録なのに `python` ラベルになっており、Python スクリプトとしては解釈できない（コード検証・コピー実行・構文ハイライトで誤解を招く）。

**修正内容**（原稿に反映済み）: 2ブロックとも言語ラベルを ` ```pycon `（Python の対話セッション用の標準ラベル）に変更。`text` ではなく `pycon` にしたのは、入力行のハイライトを保ちつつ「スクリプトではなく対話の記録」だと明示できるため。中身は変更なし。
入力行だけを `python -i` に流して再生し、`'tool_use'` → thinking/text/tool_use ブロック → `1` → `('get_weather', {'city': 'Tokyo'})` の順に本文と同じ形で表示されることを確認（先頭の thinking ブロックは本文の NOTE で説明済み）。

---

## ⚠️ 要確認のコード

### コードブロック #14（L872 agent.py）
**懸念点**: `main()` が `logging.basicConfig(level=logging.INFO, ...)` だけを設定し、httpx のロガーを抑えていないため、実行すると `INFO httpx: HTTP Request: POST https://api.anthropic.com/v1/messages "HTTP/1.1 200 OK"` が毎回出る（Open-Meteo 版では天気APIの GET も2行ずつ出る）。出力例（L1013・L1038・L1151）にはこの行がなく、第4章のデモ（client/retry/stream/cost）はすべて抑えているので不揃い。
**推奨対処**: `main()` の basicConfig の直後に1行追加。
```python
    logging.getLogger("httpx").setLevel(logging.WARNING)  # 通信ごとのログは抑える
```
（第6章以降で agent.py を更新する章にも同じ行があるか確認すること）

### コードブロック #20（L1145 Open-Meteo 版の実行）の出力例
**懸念点**: 実際の Open-Meteo（`language=ja`）は東京を `"city": "東京都"` で返す（2026-11-07 実測: `{"city": "東京都", "country": "日本", ...}`、那覇は `"那覇市"`、ニューヨークは `"ニューヨーク"` / `"アメリカ"`）。出力例 L1151 は `"東京"`。
**推奨対処**: 出力例を `"city": "東京都"` に直すか、「都市名の表記は検索結果に従う」旨を一言添える（軽微）。

---

## ✅ 動作確認済みコード一覧

| # | 位置 | 言語 | 行数 | 実行結果 |
|---|-----|-----|-----|--------|
| 2 | L322 `mkdir tools` / `touch` | bash | 2行 | 正常 |
| 3 | L333 tools/__init__.py | python | 2行 | 正常 |
| 4 | L345 tools/weather.py（ダミー版） | python | 81行 | 単体実行の出力が L479 と完全一致（36.1°F の換算も一致） |
| 5 | L474 `uv run python -m tools.weather` | bash | 1行 | 同上 |
| 7 | L499 `uv run python`（対話モード起動） | bash | 1行 | 正常 |
| 11 | L646 one_shot_tool.py | python | 66行 | tool_use → tool_result → end_turn。履歴3件・`["tool_result"]`・summary 表示が本文例と同じ形（偽APIは thinking を先頭に付けるため assistant が `["thinking", "text", "tool_use"]`。本文 NOTE の範囲内） |
| 12 | L763 実行コマンド | bash | 1行 | 正常 |
| 15 | L1008 `uv run python agent.py` | bash | 1行 | turn=1 tool_use → turn=2 end_turn。2都市の並列 tool_use（Tokyo, Sapporo）でも tool_result を1つの user メッセージで返し、偽APIの順序・欠落チェックで違反0 |
| 17 | L1033 `agent.py "那覇の天気は？"` | bash | 1行 | Naha を返す tool_use を注入して確認。`WARNING agent: ツール get_weather が失敗: 都市 'Naha' のデータがありません。対応都市: Tokyo, Osaka, Sapporo` が本文と完全一致し、is_error 付き tool_result で turn=2 end_turn |
| 19 | L1068 tools/weather.py（Open-Meteo 版） | python | 63行 | ダミー版の GET_WEATHER_TOOL までを残して下を差し替え。偽API・実APIとも正常。実API: Tokyo/Naha(華氏)/New York(華氏) 取得、存在しない都市で ValueError（本文どおり） |
| 14 | L872 agent.py | python | 107行 | ⚠️対応後、原稿から抽出して偽APIで再実行。httpx の INFO 行が消え、第4章形式の `llm_client` ログ＋`tracker.summary()` のみ表示 |
| 20 | L1145 Open-Meteo 版の実行 | bash | 2行 | ⚠️対応後の出力例（`東京都`・第4章形式のログ・summary 行）が実行順・形式とも一致 |

## 🔍 構文チェックのみ

| # | 位置 | 言語 | 結果 |
|---|-----|-----|-----|
| 10 | L603 tool_result の user メッセージ例 | json | 妥当。tool_use_id・content の形は facts どおり |

## 参考
- 第1章 L136 の agent.py 骨格（簡略版）も、本章の tools/weather.py と第4章の llm_client.py で動作することを確認済み。
- agent.py の `run_agent` のシグネチャ・ループ（end_turn / tool_use / max_tokens / refusal / 想定外、max_turns ガード、content をそのまま追加）は codebase-spec.md の第5章仕様と一致。

## ⚠️対応（2026-11-07）

| 項目 | 対応 | 内容 |
|-----|-----|-----|
| #14 agent.py `main()` の httpx ログ | 修正 | `logging.basicConfig(...)` の直後に `logging.getLogger("httpx").setLevel(logging.WARNING)  # 通信ごとのログは抑える` を追加（第4章のデモと同じ行・同じコメント） |
| #20 Open-Meteo 版の出力例 | 修正 | `"city": "東京"` → `"東京都"`（実API実測どおり）。「都市名は `東京都` のようにジオコーディングの検索結果の表記で返ります。」の1文を追加 |
| 出力例と第4章の確定形式のずれ（追加で発見） | 修正 | L780 one_shot_tool・L1013 agent.py・L1038 那覇・L1151 Open-Meteo の4つの出力例で、プレースホルダー（`INFO llm_client: ...`／`（ここに tracker.summary() の集計が表示される）`）を第4章の実ログ形式 `request_id=... model=claude-opus-5-5 stream=False elapsed=..s stop=.. in=.. out=.. cache_write=0 cache_read=0 cost=$...` と `calls=2 input=.. output=.. cache_write=0 cache_read=0 total=$...` に置換。那覇・Open-Meteo の例には欠けていた `llm_client` の行と末尾の summary 行を追加。各 cost/total は第4章の PRICES（Opus 5.5: 入力$4・出力$20/MTok）で計算して整合を確認 |
| L801 の説明文 | 修正 | one_shot_tool.py はログを設定しないため1回目と2回目の入力を比較できない。「入力トークンが1回目より2回目で増えていること」→「`input` が2回分の入力トークンの合計であること」に変更 |

再実行（偽API、`PYTHONPATH=mock`）: 原稿から抽出した修正後の agent.py で、既定の質問・「那覇とニューヨーク、今の気温を華氏で比べて」とも `INFO llm_client: request_id=... stop=tool_use ...` → `INFO agent: turn=1` → `INFO llm_client: ... stop=end_turn ...` → `INFO agent: turn=2` → 回答 → `calls=2 input=.. output=.. cache_write=0 cache_read=0 total=$...` の順で出力され、`INFO httpx: HTTP Request:` の行が出ないことを確認。ツール失敗時の `WARNING agent:` 行は turn=1 と2回目の `llm_client` 行の間に出る（実行順どおり）。
残件: 第6章以降で agent.py を更新する章に同じ httpx 抑制行があるかは、本対応の範囲（第0〜5章）外のため未確認。
