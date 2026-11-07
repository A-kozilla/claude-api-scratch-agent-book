# ファクトチェック統合レポート

実行日: 2026-11-07
対象: 書籍原稿 全13章（はじめに＋第1〜12章）。Udemy・YouTube は未作成のため対象外。
方法: 公式ドキュメント（platform.claude.com/docs ほか uv・httpx・Open-Meteo 等）を WebFetch / WebSearch で取得して照合。

---

## サマリー

| メディア | 検証クレーム | ✅ 正確 | ⚠️ 要確認 | ❌ 要修正 |
|--------|-----------|--------|---------|---------|
| Udemy  | — | — | — | — |
| 書籍   | 373件 | 314件 | 46件 | 13件（すべて修正済み） |
| YouTube| — | — | — | — |
| **合計** | **373件** | **314件** | **46件** | **13件（修正済み）** |

| 章 | 検証 | ✅ | ⚠️ | ❌（修正済み） |
|---|---|---|---|---|
| はじめに | 10 | 9 | 1 | 0 |
| 第1章 | 21 | 18 | 2 | 1 |
| 第2章 | 40 | 33 | 5 | 2 |
| 第3章 | 37 | 30 | 4 | 3 |
| 第4章 | 35 | 30 | 5 | 0 |
| 第5章 | 31 | 28 | 2 | 1 |
| 第6章 | 39 | 31 | 6 | 2 |
| 第7章 | 35 | 29 | 6 | 0 |
| 第8章 | 16 | 12 | 3 | 1 |
| 第9章 | 24 | 21 | 3 | 0 |
| 第10章 | 31 | 27 | 2 | 2 |
| 第11章 | 32 | 28 | 3 | 1 |
| 第12章 | 22 | 18 | 4 | 0 |

| コード検証（/verify-code、偽APIによるオフライン実行） | ✅ 確認済み | ⚠️ 要確認 | ❌ エラー |
|---------|--------|---------|--------|
| 書籍 全章 | 164個（⚠️対応後さらに増加） | 30個 → 残り3個（実APIでのみ確認可能） | 12個（すべて修正済み） |

---

## ❌ 要修正（すべて原稿修正済み）

1. **chapter_01** — 「20倍以上の差」→ 実際は約18.8倍。「20倍近い差」に修正。
2. **chapter_02** — spend limit の設定場所を Limits 画面としていた → Billing 画面（組織）／Workspaces 画面（ワークスペース）に修正。Default Workspace は設定不可を追記。
3. **chapter_02** — `uv add` 出力例に typing-extensions が欠落 → 追加（7→8パッケージ）。
4. **chapter_03** — prefill 不可を「2026-10-21 版の変更」と説明 → Claude 4.6 以降のモデルの制約に修正（第12章・facts も連動修正）。
5. **chapter_03** — tool_choice 強制の400を「本書で使うモデルでは」と一般化 → Opus 5.5・Sonnet 5.5 のみ（Haiku 5.5 は対応）に修正。
6. **chapter_03** — Opus 5.5 を最上位モデルと表現 → 「3つの中でもっとも高性能」に修正（第10章も連動修正）。
7. **chapter_05** — ツール名「64文字以内」→ `^[a-zA-Z0-9_-]{1,128}$`（1〜128文字）。
8. **chapter_06** — 同上（本文・`NAME_PATTERN`・エラーメッセージ）。
9. **chapter_06** — 「最新版は `_20260209`」→ `_20260318` 版も公開済みと修正。
10. **chapter_08** — Haiku 5.5 が最小キャッシュ長に届かず `cache_write=0` と説明 → 最小長は512トークンでキャッシュされる。実行例と説明を修正。
11. **chapter_10** — `pause_turn` 再開時に `container` の ID を送り返していなかった → コードと本文を修正。
12. **chapter_10** — `max_uses` を「1回の調査の上限・料金の上限」と説明 → 1ターン単位で、再開をまたいで数えられないと修正。
13. **chapter_11** — spend limit を Limits 画面で設定と記載 → Billing 画面に修正。上限到達時は400を追記。

---

## ⚠️ 推奨確認リスト（優先度順・原稿未修正）

### 公開前に対処を推奨（2026-11-07 に7件すべて対応済み。各 chapter_XX_factcheck.md の「対応」節参照）
- 1: `allowed_callers: ["direct"]` と container 引き継ぎ付きの再開処理に修正 / 2: `effort: "low"`・max_tokens 引き上げ・打ち切り時の安全側処理 / 3: 制約を本文に明記 / 4: 400・402・504・408 の扱いを追記（llm_client に `timeout_error` の対応1行）/ 5: 説明を修正 / 6: キャッシュ設定が別途必要と明記 / 7: 該当4か所はキャッシュなしの呼び出しで0が正しいと確認
- 実APIでのみ確認可能なもの（`allowed_callers`・`pause_turn` の実挙動、キャッシュの実ヒット等）は残る
1. **chapter_06 `server_tools_demo.py`** — `web_search_20260209` は既定で動的フィルタリング（code_execution 経由）になり、出力例のブロック構成が実際と異なる可能性が高い。`pause_turn` 再開時の `container` 引き継ぎもない。→ ツール定義に `"allowed_callers": ["direct"]` を追加し、再開処理を第10章と揃える。
2. **chapter_06 構造化出力デモ／chapter_11 `llm_classify`（max_tokens=512）・batch_demo（256）** — Haiku 5.5 は思考が既定で有効で `max_tokens` に数えられるため、JSON が途中で切れる恐れ。→ `effort: "low"` を付けるか上限を引き上げ、`stop_reason` を確認する。
3. **chapter_05 L270 / chapter_09 L418** — strict・構造化出力で `minimum`・`maxLength`・`maxItems` 等は使えず400になる。→ 本文に制約を明記。
4. **chapter_04** — 自分で設定した spend limit 到達は 400（429ではない）。402 `billing_error`・504 `timeout_error` の扱い。→ 本文1文追記とリトライ方針の明記。
5. **chapter_07 L1125・L1386** — effort 変更とキャッシュの関係の説明が不完全（tools・system も無効になり得る／既定値の明示はキャッシュを壊さない）。
6. **chapter_09 L1107** — 「プロンプトキャッシュも効きます」だが `patterns/` に `cache_control` がない。
7. **chapter_11** — 実行例の `cache_write=0`（自動キャッシュ付き呼び出しなら第8章と同じ不整合の可能性）。

### 表現・補足
- 認証ヘッダー: 公式は `Authorization: Bearer` が主で `x-api-key` は legacy（どちらも有効）。第2・3章に補足を推奨。
- 第2章: APIキー作成時の Expiration・Linked account、ティア説明の更新、Haiku の「10万トークン以下」は入力長の閾値。
- 第1章: 料金比較の前提トークン数の不揃い、`model_context_window_exceeded` への言及。
- 第6章: 「構造化出力が崩れることは原理的に起きない」は言い過ぎ（refusal・max_tokens は例外）。strict で `required` は必須ではない。
- 第7章: Haiku の10万トークン超の単価注記がない。count_tokens のエッジケース3点は一次情報に記載なし。
- 第10章: asyncio.Lock の理由づけは Python 3.10 未満の挙動。
- 第11章: バッチの `canceling` 状態、Default Workspace の制約。
- 第12章: リソース表に Server tools ページの追加を推奨。リダイレクトされるURL2件（リンク切れではない）。

### 実APIでのみ確認可能
- キャッシュの実際のヒット、count_tokens の実測値、`pause_turn` の挙動、思考トークン数、出力例の数値（トークン数・コスト・ID 等はすべて想定値）。

---

## 共通仕様メモへの反映
`references/claude-api-facts.md` を更新済み（prefill の位置づけ、tool_choice のモデル差、effort 既定値、思考と max_tokens、構造化出力の制約、stop_reason 追加、402/504、spend limit の400と spend cap の429、ツール名規則、サーバーツールの動的フィルタリング・`pause_turn` 再開・`max_uses`、キャッシュ倍率・最小長・effort との関係、count_tokens、バッチ上限、Console 画面、uv 0.12 以降の src 構成）。今後の Udemy・YouTube 生成に反映される。

---

## 公開判定

- ❌ 要修正: 0件（13件すべて修正済み）→ **事実誤りの観点では公開可能**
- ただし ⚠️ の「公開前に対処を推奨」7件の対応と、**実APIキーでの通し実行**を経てからの公開を推奨。
