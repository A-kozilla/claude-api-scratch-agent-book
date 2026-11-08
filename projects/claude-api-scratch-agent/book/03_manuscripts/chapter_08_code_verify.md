# コード検証レポート（再検証）

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_08.md
検証日: 2026-11-08
コードブロック数: 16個（python 7・markdown 3・bash 3・text 3）
  ✅ 動作確認済み: 15個
  ⚠️ 要確認: 0個
  ❌ エラーあり: 0個
  🔍 構文チェックのみ: 1個

## 前回からの経緯

- 午前の検証では ❌0・⚠️2 だった。2件とも出力例のキャッシュ値で、#10（multi_agent）と #16（逐次・並列の比較）が `cache_write=0 cache_read=0` になっており、全リクエストに付く `cache_control` と矛盾していた。その後、原稿で両方の値が差し替えられた。
- ラッパーの説明文（L364〜371）も書き換えられた。今回は現在の原稿から第4〜8章のブロックを抽出し直して組み立て、全体を検証した。第8章のコードは変わっていない。

## 検証方法

- 環境: Python 3.12.x（uv で作成した隔離 venv）＋ httpx 0.28.1 ＋ python-dotenv。API キーは使っていない。httpx の同期・非同期クライアントを偽の Claude API に差し替えて実行した。偽 API は、2026-10-21 仕様の違反に 4xx を返すモック。
- 前提の再現: 次の順に組み立てた。
  - 第4章 #36 → 第5章 #4
  - 第6章（番号付きの手順どおり）→ 第7章の全ブロック
  - 第8章の各ブロックを、本文の指示どおりに適用した:
    - 8.2: import 2行を import 群へ足し、`Agent` を `__main__` の前に置いた。
    - 8.3: `acall_messages` などを llm_client.py の末尾へ足した。`async_handlers` 属性と非同期メソッドを `Agent` に足した。multi_agent.py の `__main__` を差し替えた。
- 重点検証: 偽 API の応答を差し替えて、親が1回の応答で `delegate_research` を3件要求する状況を作った。そのうえで、親子の履歴・同時実行数・承認・effort を検査した。

## 重点確認の結果

| 確認項目 | 結果 |
|---|---|
| 子の結果が tool_result として親に返るか | ✅ 親の最後のリクエストは `user → assistant → user` の3件で、最後の user に tool_result が3件入る |
| 親の履歴に子の履歴・資料本文が混ざらないか | ✅ 親に送られた messages に、資料本文（「年払い」など）は含まれない |
| 同期版の並列（第6章の ThreadPoolExecutor） | ✅ 委譲ツール3件がスレッドで並行して動き、子の呼び出しは計6回 |
| `asyncio.gather` と `Semaphore` | ✅ 1リクエストに0.2秒の遅延を入れたモックで測定した。`Semaphore(3)` は最大同時3本で0.42秒、`Semaphore(1)` は最大同時1本で1.26秒。結果は tool_use の順に並ぶ |
| 「Event loop is closed」 | ✅ 実ソケットのローカル HTTP サーバーで、`asyncio.run()` を2回呼んで確かめた。`aclose_client()` がないと `RuntimeError: Event loop is closed` になり、あると2回とも成功した |
| 副作用ツールの承認（`Agent.run`／`Agent.arun`） | ✅ 同期・非同期のどちらでも `ask_approval()` が呼ばれた（計2回） |
| キャッシュの区切り・effort | ✅ どのリクエストにも `cache_control` が3か所付き、`Agent(effort="low")` では `output_config={"effort": "low"}` が送られる |
| `llm_client.tracker = CostTracker()` による集計リセット | ✅ `--compare` で、逐次と並列の calls をそれぞれ独立に数えた |
| 偽 API への仕様違反リクエスト | ✅ 0件 |

---

## ❌ エラーが発生したコード

該当なし。

---

## ⚠️ 要確認のコード

該当なし。

---

## 🔍 構文チェックのみ

| # | 位置 | 言語 | 内容 |
|---|-----|-----|-----|
| 11 | L906 親の messages の概略 | python | 説明用のリテラル（`"..."` を含む）。`ast.parse` で構文 OK。構造は実際の親の履歴と一致する（user → assistant[thinking, tool_use×3] → user[tool_result×3]） |

---

## ✅ 動作確認済みコード一覧

| # | 位置 | 言語 | 行数 | 実行結果 |
|---|---|---|---|---|
| 1 | L225 agent.py `Agent`（同期版） | python | 81行 | 第6・7章の関数を残したまま追記でき、`run()` は正常に完了した。第7章の `run_agent`・`effort_demo.py` も引き続き動く |
| 2 | L373 check_agent.py | python | 56行 | 正常終了。ラッパー（`directory`・`path`）は、第6章の `files.list_files()`・`files.read_file()` を呼ぶ。L364〜371 の書き換え後の説明（引数名・`register_file_tools(registry, allow_write=False)` との違い）は、コードと合っている。ツールが失敗しても is_error で返り、ループは続く |
| 3 | L436 workspace/docs/alpha.md | markdown | 6行 | 資料として配置し、read_file で読める |
| 4 | L445 workspace/docs/beta.md | markdown | 6行 | 同上 |
| 5 | L454 workspace/docs/gamma.md | markdown | 6行 | 同上 |
| 6 | L465 `uv run python check_agent.py` | bash | 2行 | 同等の `python check_agent.py` で正常 |
| 7 | L473 check_agent の出力例 | text | 11行 | 行の形式・出力順・`tracker.summary()` の形が一致した。出力順は `llm_client:` → `[checker] tool_use` → `tool=... elapsed=`。Haiku 5.5 の単価（$0.10／$0.50／書き込み $0.125／読み取り $0.01）で再計算すると、各行（$0.0002／$0.0001／$0.0001）と合計 $0.0003 が一致した。in・out・cache の合計も各行の和と一致する |
| 8 | L586 multi_agent.py（同期版） | python | 169行 | `--sync` で正常に動き、委譲 → 子のループ → 報告と進んだ |
| 9 | L829 `uv run python multi_agent.py` | bash | 2行 | 正常。8.3 の更新後は、既定が非同期版になる |
| 10 | L837 multi_agent の出力例 | text | 31行 | **更新後の値を照合**。ログの流れが実際の動作と一致した。流れは、親が3件を同時に委譲 → `multi_agent:` の3行 → 子のログが入り混じる → 子3ターン×3＋親2ターン＝11回。コストは、親が Opus 5.5 で2回、子が Haiku 5.5 で9回。内訳は出力に出ないので一意には検算できないが、矛盾しない内訳はある。たとえば親を入力16・出力1,150・書き込み2,600・読み取り1,500、子を残りの値とすると $0.0375 になる。`cache_write`・`cache_read` が0でなくなり、#7 の説明（Haiku でもキャッシュされる）とも整合した |
| 12 | L1031 llm_client.py `acall_messages()` ほか | python | 62行 | 第4章の内部関数と引数が一致する。成功・リトライ・例外の各経路が、同期版と同じ規則で動く |
| 13 | L1114 agent.py `arun()` ほか | python | 63行 | 正常。非同期ツールと通常ツールを同時に進め、tool_use の順に並べ直す。通常ツールは `asyncio.to_thread(execute_tool_uses, …)` で実行されるので、承認と切り詰めが効く |
| 14 | L1209 multi_agent.py（非同期版・compare） | python | 74行 | 既定（非同期）・`--compare`・`--sync` のいずれも正常終了。`aclose_client()` もある |
| 15 | L1301 `uv run python multi_agent.py --compare` | bash | 2行 | 正常。表示形式は `逐次: …s  calls=…`・`並列: …`・`失敗: なし` |
| 16 | L1308 `--compare` の出力例 | text | 3行 | **更新後の値を照合**。表示形式は一致した。子だけの9回（Haiku 5.5）で再計算すると、逐次 $0.0009・並列 $0.0011 で一致した。入力の総量（input＋cache_write＋cache_read）は、逐次・並列とも 10,872 で等しい。並列では書き込みが増えて読み取りが減っており、L1316〜1317 の説明（並列では最初の応答前にほかの子が送られ、キャッシュを読めない）と合っている |

## 補足（不具合ではないが気づいた点・午前から変わらず）

- `Agent._check_stop()` は、`pause_turn` を想定外の stop_reason として扱い、最終テキストを返す（第7章の `run_agent()` は `continue`）。`Agent` はサーバーツールを持たないので、実害はない。

> ⚠️ **検証の限界**: 次の点はモックでは再現できません。親が実際に3件を同時に委譲するか、子の報告の品質、キャッシュの実際のヒット量、所要時間の比率です。出力例の数値は想定値として、形式と算術だけを確認しました。公開前に実 API キーで 8.2・8.3 の実行例を一度通してください。
