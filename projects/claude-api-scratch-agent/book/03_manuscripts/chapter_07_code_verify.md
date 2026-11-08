# コード検証レポート（再検証）

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_07.md
検証日: 2026-11-08
コードブロック数: 30個（python 16・bash 6・json 3・text 5）
  ✅ 動作確認済み: 26個
  ⚠️ 要確認: 0個
  ❌ エラーあり: 0個
  🔍 構文チェックのみ: 4個

## 前回からの経緯

- 午前の検証では ❌0・⚠️2 だった。⚠️ はどちらも出力例のキャッシュ値で、#23（7.3「効果を測る」）は自動キャッシュの挙動と合わず、#28（7.4 長期メモリ）は 7.3 より書き込みが小さかった。その後、原稿で両方の値が差し替えられた。あわせて、#4 のコメント2か所も修正された。
- 今回は、現在の原稿から第4〜7章のブロックを抽出し直して組み立て、全体を検証した。コードの変更は #4 のコメント2行だけで、処理は変わっていない。

## 検証方法

- 環境: Python 3.12.x（uv で作成した隔離 venv）＋ httpx 0.28.1 ＋ python-dotenv。API キーは使っていない。httpx のすべてのクライアントを偽の Claude API に差し替えて実行した。偽 API は、anthropic-version 2026-10-21 の仕様違反に 4xx を返すモックで、count_tokens・prefill の禁止・tool_use／tool_result の対応・thinking の改変・temperature などを検査する。
- 前提の再現: 次の順に、本文の手順どおりに組み立てた。
  - 第4章 #36（llm_client.py 完成版）
  - 第5章 #4（tools/weather.py ダミー版）
  - 第6章の番号付き手順（6.2 → 6.3 → 6.4）
  - 第7章の全ブロック。「末尾に追加」「関数の差し替え」「`__main__` ブロック内に追加」の指示どおりに適用した
- 長い履歴の検証: しきい値を 2,500、keep_last を 2 にして、tool_use を最大20ターン返させた。`run_agent()` が送った全リクエスト（67件）の履歴を検査した。

---

## ❌ エラーが発生したコード

該当なし。

---

## ⚠️ 要確認のコード

該当なし。

---

## 🔍 構文チェックのみ

| # | 位置 | 言語 | 内容 |
|---|------|-----|-----|
| 1 | L89 count_tokens の curl | bash | `bash -n` で構文 OK。実 API キーが必要なので実行していない。同じボディを Python 版の `count_tokens()` で偽 API に送り、200 と `{"input_tokens": N}` が返ることは確認した |
| 2 | L105 `{"input_tokens": 31}` | json | パース OK |
| 8 | L430 tool_use/tool_result の履歴例 | json | パース OK。tool_use_id の対応も正しい |
| 29 | L1389 thinking ブロックを含むレスポンス例 | json | パース OK |

---

## ✅ 動作確認済みコード一覧

| # | 位置 | 言語 | 行数 | 実行結果 |
|---|------|-----|-----|--------|
| 3 | L126 llm_client.py `count_tokens()` | python | 22行 | `/v1/messages/count_tokens` に model・messages・system・tools を送り、int を返す。tracker には計上されない |
| 4 | L176 context.py 計測部分 | python | 55行 | `estimate_tokens()`・`token_breakdown()` は正常。修正されたコメント2か所（L205・L217）は処理と合っている。count_tokens を 500 で失敗させると、WARNING のあとに `len(raw)` の近似値（84）に切り替わった |
| 5 | L258 `__main__`（内訳表示） | python | 19行 | 出力例 #7 と同じ4行の形 |
| 6 | L285 `uv run python context.py` | bash | 2行 | 同等の `python context.py` で正常終了 |
| 7 | L290 内訳の出力例 | text | 4行 | 形が一致。412＋38＋4,627＝5,077 で合計も整合 |
| 9 | L470 安全な切断位置と切り詰め | python | 32行 | keep_last を変えても、tool_use と tool_result の組は壊れない |
| 10 | L539 `__main__` 内の assert | python | 16行 | `truncate_history: OK` |
| 11 | L563 | bash | 2行 | 正常 |
| 12 | L568 出力例 | text | 5行 | 形が一致 |
| 13 | L588 段階1 `shrink_old_tool_results()` | python | 32行 | deepcopy により元の履歴は変わらない。tool_use_id・is_error も保持される |
| 14 | L650 `_to_transcript()` | python | 29行 | 正常 |
| 15 | L696 `summarize_history()` | python | 23行 | FAST_MODEL（claude-haiku-5-5）で送信される |
| 16 | L749 `_first_user_text()`／`maybe_compact()` | python | 64行 | 20ターン・連続圧縮でも `<original_request>` は常に1つ。全67リクエストで、履歴の検査（先頭が user・role が交互・tool_use と tool_result の id が一致）を満たした |
| 17 | L854 圧縮デモ | python | 10行 | `圧縮前 5 件 → 圧縮後 3 件`。header は本文どおり |
| 18 | L873 | bash | 2行 | 正常 |
| 19 | L878 圧縮の出力例 | text | 12行 | 件数・header の形・ログ行の形式が実際と一致 |
| 20 | L1025 `cached_system()`／`cached_tools()` | python | 20行 | 元のスキーマを書き換えず、最後の1件だけに `cache_control` を付ける |
| 21 | L1067 agent.py 第7章版 | python | 54行 | 送信リクエストのブレークポイントは3か所（tools 末尾・system 末尾・トップレベル）。`output_config={"effort": "low"}` も送信される |
| 22 | L1146 | bash | 2行 | 正常 |
| 23 | L1151 7.3「効果を測る」の出力例 | text | 2行 | **更新後の値を照合**。形式は第4章 `_log_call()` と一致した。コストの再計算も一致した（Opus 5.5: 入力 $4・出力 $20・書き込み $5・読み取り $0.20／1M）。<br>1行目: 6×4＋96×20＋3,564×5 → $0.0198<br>2行目: 6×4＋211×20＋1,353×5＋3,564×0.2 → $0.0117<br>1回目の書き込み 3,564 が2回目の読み取り 3,564 と等しく、2回目に追加分 1,353 が書き込まれる形は、自動キャッシュの挙動と本文 L1156〜 の説明に合っている |
| 24 | L1208 tools/memory.py | python | 66行 | `save_memory` は承認の対象になる。`n` では is_error が返り、memory.json は作られない。`y` では保存される。`search_memory` は承認なしで動く |
| 25 | L1298 `memory_prompt()` | python | 8行 | 記憶がなければ空文字、あれば `<long_term_memory>` を返す |
| 26 | L1317 agent.py `__main__` | python | 16行 | 引数なしでも完走し、`tracker.summary()` を表示した。httpx のログは出ない |
| 27 | L1343 2回の実行 | bash | 3行 | 1回目・2回目とも正常終了 |
| 28 | L1349 7.4 長期メモリの出力例 | text | 12行 | **更新後の値を照合**。承認プロンプトの形式（第6章 `ask_approval()`）と summary 行の形式は一致した。コストも単価表で再計算して一致した。<br>1回目: 16×4＋153×20＋4,410×5＋3,920×0.2 → $0.0260<br>2回目: 18×4＋262×20＋5,500×5＋8,100×0.2 → $0.0344<br>1回目は「1ターン目の書き込み 3,920 → 2ターン目で読み取り 3,920＋追加分 490 を書き込み」と分解でき、矛盾しない。メモリツールの分、7.3 の 3,564 より書き込みが大きい点も自然 |
| 30 | L1429 effort の使い分け | python | 8行 | `effort_demo.py` として正常終了。`{"effort":"low"}`×2 と `{"effort":"high"}`×2 が送信され、400 にはならない |

偽 API への仕様違反リクエスト: 0件。

## 補足（不具合ではないが気づいた点・午前から変わらず）

- `run_agent()` の `pause_turn` 分岐では、履歴が assistant で終わったまま、次のターンの `maybe_compact()` を通る。本書のエージェントはサーバーツールを使わないので、実害はない。
- `maybe_compact()` → `estimate_tokens()` は `model` を渡さないので、常に `MODEL` で数える。第8章の Haiku でも同じ世代のトークナイザーなので、実害はない。

> ⚠️ **検証の限界**: キャッシュの実際のヒット量と count_tokens の値、要約の品質は、モックでは再現できません。出力例の数値は想定値として、形式と算術だけを確認しました。公開前に実 API キーで 7.1〜7.4 の実行例を一度通してください。
