# コード検証レポート

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_09.md
検証日: 2026-11-07
検証環境: Python 3.12 / httpx / python-dotenv（APIキーなし。httpx を偽の Claude API（2026-10-21 仕様の違反を 4xx で返すモック）に接続して実行）
前提コード: 第4章の完成版 `llm_client.py`＋第7章の追加＋第8章の `acall_messages()`（第8章の修正後の版）、第8章の `agent.py`（Agent クラス）、第6章の `tool_registry.py`。`patterns/` は本文どおりに組み立て、プロジェクトのルートで `python -m patterns.xxx` として実行した。モックの応答だけでは通らない分岐（ゲートの合否、エスカレーション、観点の失敗、評価ループの終了条件）は、`call_messages`/`acall_messages` を差し替えたシナリオで個別に確認した。

コードブロック数: 22個（python 10 / bash 5 / text 7）
  ✅ 動作確認済み: 21個（⚠️5件を 2026-11-07 に修正して再検証）
  ⚠️ 要確認: 0個（当初5個 → すべて対応済み）
  ❌ エラーあり: 1個（原稿を修正済み）
  🔍 構文チェックのみ: 0個

---

## ❌ エラーが発生したコード

### コードブロック #19（patterns/evaluator_optimizer.py（続き）の `optimize()`、L1251付近）

**元のコード**:
```python
        if best is None or evaluation.total > best[1].total:
            best = (draft, evaluation)
        elif round_no > 1:
            logger.info("改善が止まったため終了します")  # 停滞: 前回より良くならない
            break
        if evaluation.passed(min_score):
            logger.info("合格しました")
            break
        improvements = evaluation.improvements
    return best
```

**エラー内容**（評価を差し替えたシナリオ。第1版 (5,5,5,3)=18点・不合格、第2版 (4,4,4,4)=16点・合格）:
```
patterns.evaluator_optimizer: 第1版: 合計18点 ...
patterns.evaluator_optimizer: 第2版: 合計16点 ...
patterns.evaluator_optimizer: 改善が止まったため終了します
-> 採用 版1 total=18 passed=False
```

**原因**: 停滞の判定（合計点が前回を上回らない）が合格判定より先にあるため、全項目が基準を満たした版でも合計点が低いと「停滞」として捨てられ、不合格の版が返る。本文の「合格したとき終了する」という終了条件と矛盾する（合計点と合格条件「全項目4点以上」は一致しないため、実際に起こりうる）。

**修正内容（原稿に反映済み）**: 合格判定を先に行い、合格した版をそのまま返すように並べ替えた。あわせて解説の段落に「合格判定を停滞の判定より先に置く理由」を1文加え、「返すのは最後の版ではなく、最高得点の版です」を「合格しないまま終わった場合に返すのは…」に改めた。実行例（第1版14点→第2版18点で合格）はそのまま成り立つ。
```python
        if evaluation.passed(min_score):
            logger.info("合格しました")
            return draft, evaluation  # 合格した版をそのまま採用する
        if best is None or evaluation.total > best[1].total:
            best = (draft, evaluation)
        elif round_no > 1:
            logger.info("改善が止まったため終了します")  # 停滞: 前回より良くならない
            break
        improvements = evaluation.improvements
    return best
```

**修正後の再検証**（終了条件4パターン＋丸め）:
| 点数の並び | 結果 |
|---|---|
| (3,3,3,3) → (4,4,4,4) | 第2版で合格して終了（版2を採用） |
| (5,5,5,3) → (4,4,4,4) | 第2版で合格して終了（版2を採用）※修正前は版1 |
| (3,3,3,3) → (2,2,2,2) | 停滞で終了、最高得点の版1を採用 |
| (1,1,1,1) → (2,2,2,2) → (3,3,3,3) | 上限3回で終了、版3を採用 |
| (9,0,5,5) | 1〜5に丸めて (5,1,5,5) |

---

## ⚠️ 要確認のコード

### コードブロック #8・#13・#17・#21（各パターンの出力例の最終行、L573・L769・L1068・L1312付近）

**元の出力例**:
```text
呼び出し回数: 3 / 入力: 1,512 tok / 出力: 1,087 tok / キャッシュ作成: 0 / キャッシュ読込: 0 / 合計: $0.0213
```
**懸念点**: 第4章の完成版 `CostTracker.summary()` の実際の出力は `calls=3 input=1,512 output=1,087 cache_write=0 cache_read=0 total=$0.0213` の形式で、4つの出力例すべてと一致しない。codebase-spec でも「第4章で確定したログ形式に他章は合わせる」とされており、第8章の出力例はこの形式で書かれている。L576 の「表示形式は読者の実装に合わせて読み替えてください」も、完成版が本文に掲載されている以上は不要な断り書きになっている。
**推奨対処**: 4か所を次の形式に置き換え、L576 の括弧書きを削除する。
```text
calls=3 input=1,512 output=1,087 cache_write=0 cache_read=0 total=$0.0213
calls=7 input=2,904 output=2,311 cache_write=0 cache_read=0 total=$0.0335
calls=8 input=4,630 output=3,148 cache_write=0 cache_read=0 total=$0.0644
calls=4 input=3,215 output=2,476 cache_write=0 cache_read=0 total=$0.0611
```

### コードブロック #15（patterns/parallel.py（続き）の `main()`、L1016付近）

**懸念点**: 動作は正常（`asyncio.run(main())` は1回だけなので Event loop is closed は起きない）。ただし第8章の WARNING で「`asyncio.run()` に渡す関数の最後で `await aclose_client()` を呼ぶ」と教えているのに、この `main()` では呼んでいない。第10章でも `finally` で `aclose_client()` を呼ぶ形に統一されている。また、`_semaphore = asyncio.Semaphore(MAX_CONCURRENCY)` をモジュールの最上位で作っているため、このモジュールの関数を別の `asyncio.run()` から続けて使う（テストなど）と、セマフォが前のループに結び付いたまま `RuntimeError: ... is bound to a different event loop` になる可能性がある（Python 3.10 以降はセマフォが待ちの発生時にループへ結び付く）。
**推奨対処**: `main()` を次のようにする（`from llm_client import ... aclose_client` を追加）。セマフォについては「1回の `asyncio.run()` の中で使う前提」と一言添えるか、`main()` の中で作って関数に渡す形にする。
```python
async def main() -> None:
    try:
        findings = await sectioned_review(SAMPLE_CODE)
        ...
        print("\n" + tracker.summary())
    finally:
        await aclose_client()  # 第8章: ループを閉じる前に非同期クライアントを閉じる
```

---

## 重点確認の結果

| 確認項目 | 結果 |
|---|---|
| 構造化出力のパース（`parse_json_response`） | ✅ thinking ブロックが先頭にあっても text だけを読む。`refusal`・`max_tokens`・不正JSONはそれぞれ `PatternError` |
| 構造化出力のリクエスト | ✅ `output_config.format`（json_schema）・`additionalProperties: false`・`required` を含め、偽APIへの仕様違反は0件 |
| チェーンのゲート | ✅ 価格なし→抽出ゲートで停止（最終行 `patterns.PatternError: 抽出ゲートで停止: ['価格がありません']` は本文と一致）。300字超→指摘付きで書き直し（retries=1）。禁止語が残り続ける→上限後に執筆ゲートで停止。モデルは 抽出 haiku → 執筆 opus → 翻訳 haiku |
| ルーティング | ✅ technical(high)→MODEL で回答、confidence=low・other→escalation（回答の呼び出しなし） |
| 並列化（セクショニング） | ✅ 1観点が例外でも残りを返し、重要度順に並ぶ（`return_exceptions=True` が機能） |
| 並列化（投票） | ✅ 失敗票は数えない（valid_votes=4）。しきい値2で flagged |
| asyncio・Semaphore | ✅ `python -m patterns.parallel` で 3＋5＝8回の呼び出し（本文の「8回」と一致）、Event loop のエラーなし |
| 評価者-最適化者の終了条件 | ❌→修正済み（上記） |
| `python patterns/chain.py` で起動した場合 | ✅ 本文の説明どおり `ModuleNotFoundError: No module named 'llm_client'` |
| オーケストレーター骨格 | ✅ 分解（構造化出力）→ `Agent.arun()` の gather で実行できる（説明用。実行時は `aclose_client()` を併用して確認） |

---

## ✅ 動作確認済みコード一覧

| # | 箇所 | 言語 | 行数 | 実行結果 |
|---|---|---|---|---|
| 1 | ディレクトリ構成（L221） | text | 9行 | 構成どおりに配置して実行可 |
| 2 | `uv run python -m patterns.chain`（L236） | bash | 2行 | 同等の `python -m` で起動可 |
| 3 | patterns/__init__.py（L253） | python | 33行 | 正常（PatternError・json_format・parse_json_response） |
| 4 | patterns/chain.py 抽出（L355） | python | 47行 | 正常 |
| 5 | patterns/chain.py 執筆・翻訳（L422） | python | 47行 | 正常 |
| 6 | patterns/chain.py run_chain・main（L482） | python | 52行 | 正常（ゲートの合否・書き直し上限を確認） |
| 7 | `uv run python -m patterns.chain`（L554） | bash | 2行 | 正常 |
| 9 | 抽出ゲート停止の出力例（L583） | text | 2行 | 実際の最終行と一致 |
| 10 | patterns/router.py 分類器（L617） | python | 42行 | 正常（enum の値で分類） |
| 11 | patterns/router.py 振り分け（L676） | python | 52行 | 正常（エスカレーションを確認） |
| 12 | `uv run python -m patterns.router`（L749） | bash | 2行 | 正常 |
| 14 | patterns/parallel.py セクショニング（L851） | python | 77行 | 正常 |
| 16 | `uv run python -m patterns.parallel`（L1048） | bash | 2行 | 正常 |
| 18 | patterns/evaluator_optimizer.py 前半（L1155） | python | 48行 | 正常 |
| 20 | `uv run python -m patterns.evaluator_optimizer`（L1297） | bash | 2行 | 正常（修正後の版で再実行） |
| 22 | orchestrator_sketch.py（L1371） | python | 27行 | 正常（説明用の骨格） |

> 行番号は修正前の原稿基準。

---

## 他章に関わる事項

- 第9章のコードは第8章の `acall_messages()` に依存する。第8章の `acall_messages()` には、第4章の `_is_retryable()`/`_retry_delay()` を別の引数の形で定義し直して同期版を壊すバグがあった（第8章側で修正済み。詳細は chapter_08_code_verify.md）。修正前の第8章のコードのままだと、第9章の同期パターン（chain・router・evaluator_optimizer）で API がエラーを返したときに `TypeError` になる。
- 第4章 `CostTracker.summary()` の形式に第9章の出力例を合わせる件は上記 ⚠️ のとおり（第4章側の変更は不要）。

---

## ⚠️対応（2026-11-07）

| # | 項目 | 対応 | 結果 |
|---|---|---|---|
| 8・13・17・21 | 各パターンの出力例の最終行が `tracker.summary()` の実際の形式と違う | **修正** | ✅ |
| 15 | parallel.py の `main()` が `aclose_client()` を呼ばない／Semaphore をモジュール最上位で作っている | **修正** | ✅ |

**修正内容（原稿に反映済み）**
- 出力例4か所（L573・L769・L1077・L1322）を第4章の確定形式 `calls=.. input=.. output=.. cache_write=.. cache_read=.. total=$0.0000` に置き換えた（数値はそのまま）。L576 の「表示形式は読者の実装に合わせて読み替えてください」を削除し、項目の説明に差し替えた。
- httpx の INFO 行: 第9章の4スクリプトはいずれも `logging.basicConfig(level=logging.WARNING)`＋`patterns` だけ INFO のため、httpx・llm_client の INFO 行はもともと出ない（実行して0行を確認）。出力例もこれと一致しているので変更なし。
- parallel.py: `_semaphore` をやめ、`sectioned_review()`・`vote()` の中で `asyncio.Semaphore(MAX_CONCURRENCY)` を作り、`review_aspect()`・`cast_vote()` に引数 `semaphore` で渡す形にした。`main()` を `try/finally` にして `await aclose_client()` を呼ぶ（import に `aclose_client` を追加）。解説に「セマフォを関数の中で作る理由」を2文追加。

**再検証**（偽API）
```text
python -m patterns.parallel: 正常終了（calls=8、Event loop のエラーなし）
sectioned_review()+vote() を別々の asyncio.run() で2回連続実行（各回 aclose_client）: 2回とも成功（calls=16）
偽APIへの仕様違反リクエスト: 0件
```

**残った項目**: なし。
