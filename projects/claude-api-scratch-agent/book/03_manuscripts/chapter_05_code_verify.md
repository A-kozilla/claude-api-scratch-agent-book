# コード検証レポート（再検証）

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_05.md
検証日: 2026-11-08
コードブロック数: 21個（出力例の `text` 6個は照合のみで判定数に含めない → 判定対象 15個）
  ✅ 動作確認済み: 14個
  ⚠️ 要確認: 0個
  ❌ エラーあり: 0個
  🔍 構文チェックのみ: 1個

## 前回からの経緯

- 午前の検証（2026-11-08）は ❌0・⚠️0。その後の変更は、用語統一の一括置換と長文の分割（コードブロックの外のみ）。
- 今回は現在の原稿からコードブロックを抽出し直した。コードの中身は午前の抽出物と1文字も変わっていないことを確認した。差分は行番号のずれだけ。

## 検証方法

- 環境: Python 3.12.7 / httpx 0.28.1（スクラッチパッドの隔離 venv）。実 API キーは使っていない。外部への実通信もしていない。
- 偽 API（`httpx.MockTransport`）: 偽の Claude API は、2026-10-21 仕様に違反すると 4xx を返す。チェック項目は temperature・prefill・tool_result の欠落や順序・強制 tool_choice・ツール名など。偽の Open-Meteo（geocoding／forecast）も使った。
- 前提: 第4章の完成版 `llm_client.py`（chapter_04.md の #36）。
- 組み立て: 本文の手順どおり。`mkdir tools`、`touch tools/__init__.py` のあと、ダミー版の `tools/weather.py`・`one_shot_tool.py`・`agent.py` を置いた。5.4節では「`GET_WEATHER_TOOL` は残し、それより下を書き換え、`_DUMMY_WEATHER` は削除」の指示どおりに差し替えた。
- 偽 API が記録した仕様違反: **0件**（全実行を通して）。

---

## ❌ エラーが発生したコード

なし。

---

## ⚠️ 要確認のコード

なし（Claude が1回の応答でツールを並列に呼ぶかどうかや、回答文そのものは、偽 API では再現できない）。

---

## ✅ 動作確認済みコード一覧

| # | 位置 | 言語 | 行数 | 実行結果 |
|---|-----|-----|-----|--------|
| 2 | L332 `mkdir tools`／`touch` | bash | 4行 | 空の一時ディレクトリで実行。`tools/__init__.py`（0バイト）ができた |
| 3 | L344 tools/__init__.py | python | 2行 | 正常 |
| 4 | L357 tools/weather.py（ダミー版） | python | 81行 | 正常 |
| 5 | L487 `uv run python -m tools.weather` | bash | 2行 | 出力が L492 の例と完全に一致（`diff` で差分なし。36.1°F も一致） |
| 7 | L512 `uv run python` | bash | 2行 | 対話モードの起動だけを行うブロック。#8・#9 の入力は `code.InteractiveConsole` で再生した |
| 8 | L517 対話モード（pycon） | pycon | 12行 | `'tool_use'` のあとに thinking／text／tool_use の各ブロックを表示 |
| 9 | L563 対話モードの続き（pycon） | pycon | 7行 | `1`、`('get_weather', {'city': 'Tokyo'})` で本文と一致 |
| 11 | L662 one_shot_tool.py | python | 66行 | tool_use → tool_result → end_turn の順に進んだ。`[履歴] メッセージ数 = 3`、summary 行の形式も一致 |
| 12 | L787 実行コマンド | bash | 2行 | 正常 |
| 14 | L902 agent.py | python | 107行 | 並列の tool_use 2件（Tokyo, Sapporo）を1つの user メッセージで返し、2ターンで終了。httpx のログは出ない |
| 15 | L1044 `uv run python agent.py` | bash | 2行 | ログの並びが L1049 の例と一致 |
| 17 | L1069 `agent.py "那覇の天気は？"` | bash | 2行 | `WARNING agent: ツール get_weather が失敗: 都市 'Naha' のデータがありません。対応都市: Tokyo, Osaka, Sapporo` が本文と完全に一致。is_error 付きで turn=2 の end_turn |
| 19 | L1113 tools/weather.py（Open-Meteo 版） | python | 63行 | 偽 Open-Meteo で確認。Tokyo は `東京都` になり、華氏の指定（71.8°F）も通った。存在しない都市（Atlantis）では `ValueError: 都市 'Atlantis' が見つかりません。英語表記（例: Tokyo）で指定してください。` |
| 20 | L1192 Open-Meteo 版の実行 | bash | 3行 | `-m tools.weather` の出力形式が L1198 と一致。「那覇とニューヨーク…華氏」の依頼では `{"unit": "fahrenheit"}` の2件を並列に処理した |

### 本文の「わざと間違える」実験の再現
- assistant の追加をコメントアウトすると、2回目の呼び出しが `InvalidRequestError: [400 invalid_request_error] unexpected tool_use_id found in tool_result blocks ...` になった。
- `tool_use_id` を `"toolu_dummy"` に変えた場合も、同じく `InvalidRequestError` になった。

## 🔍 構文チェックのみ

| # | 位置 | 言語 | 結果 |
|---|-----|-----|-----|
| 10 | L618 tool_result の user メッセージ例 | json | `json.loads` で妥当 |

## 出力例（text）の照合

| # | 位置 | 照合結果 |
|---|-----|--------|
| 1 | L300 description の悪い例・良い例 | 説明文（コードではない） |
| 6 | L492 | 実行結果と完全に一致 |
| 13 | L792 | 形式が一致。コストは 1,454×$4＋190×$20（/1M）＝$0.0096 で一致 |
| 16 | L1049 | ログの形式・順序が一致。各行（$0.0055／$0.0065）と合計 $0.0120 を単価表で再計算して一致 |
| 18 | L1074 | 同上（$0.0043／$0.0054、合計 $0.0096。in・out の合計も一致） |
| 21 | L1198 | 同上（$0.0054／$0.0058、合計 $0.0112） |

> ⚠️ **検証の限界**: 実 API の応答（ツール選択・並列呼び出しの有無・thinking ブロックの有無）と、実際の Open-Meteo の値は、偽 API では再現できません。公開前に実 API キーで 5.2〜5.4 の実行例を一度通してください。
