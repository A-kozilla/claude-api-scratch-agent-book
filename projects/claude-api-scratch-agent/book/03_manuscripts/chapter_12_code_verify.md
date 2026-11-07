# コード検証レポート

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_12.md
検証日: 2026-11-07
コードブロック数: 1個
  ✅ 動作確認済み: 0個
  ⚠️ 要確認: 0個（コードブロック外の本文の ⚠️ 2件は 2026-11-07 にすべて修正。末尾の「⚠️対応」節を参照）
  ❌ エラーあり: 0個
  🔍 構文チェックのみ: 1個

---

## 🔍 構文チェックのみ（照合）

| # | 位置 | 言語 | 内容 | 結果 |
|---|-----|-----|-----|-----|
| 1 | L57 | text | `agent-from-scratch/` の最終構成 | codebase-spec.md のディレクトリ構成、および第10・11章の検証で組み立てた構成（`report_agent/`・`tests/`・`guardrails.py`・`evals/`・`batch_demo.py`）と一致 |

---

## ⚠️ 要確認（コードブロック外の本文）

### L79付近: 第10章 CLI の処理の説明
**懸念点**: 「オーケストレーターの `Agent.run()` がループを回します。各ターンで `maybe_compact()` が履歴を確認し、`call_messages()` が API を呼び」とあるが、第10章のオーケストレーターは `asyncio.run()` の中で **`Agent.arun()`** を使い、APIは **`acall_messages()`** で呼んでいる（`maybe_compact()` は `asyncio.to_thread` 経由）。
**推奨対処**: 「オーケストレーターの `Agent.arun()` がループを回します。各ターンで `maybe_compact()` が履歴を確認し、`acall_messages()` が API を呼び、…」に直す。

### L61付近（参考・軽微）: 構成図の `llm_client.py` の注記
`# 第4章 → 第7章・第8章で拡張` とあるが、第10章でもテスト用の `set_transport()` を追加している。必要なら `第7章・第8章・第10章で拡張` とする。

> 本章には実行するコードはありません。各ファイルの動作は第10・11章のレポートを参照してください。

---

## ⚠️対応（2026-11-07）

| 位置 | 項目 | 対応 |
|-----|-----|-----|
| L79 | `Agent.run()` / `call_messages()` | **修正**: 「`asyncio.run()` の中でオーケストレーターの `Agent.arun()` がループを回します。…`acall_messages()` が API を呼び、…」に変更し、「同期版の `run()` と `call_messages()` でも、手順は同じです。」を1文追加（第8章の両方に触れる形）。第10章の `orchestrator.py`（`asyncio.run(self._orchestrate())` → `Agent.arun()`）と、第8章の `arun()`（`asyncio.to_thread(maybe_compact, ...)` → `acall_messages()`）で確認 |
| L63 | `llm_client.py` の注記 | **修正**: `# 第4章 → 第7・8・10章で拡張`（第10章の `set_transport()`） |

### 第1〜11章との照合（振り返り全体）
各章のコードブロックのファイル名コメントと、検証用に組み立てたプロジェクトの実名で照合した。
- **修正**: L65 `agent.py` の注記を `第5章 関数版 → 第6・7章 → 第8章 Agentクラス` に変更（第7章でも `BASE_SYSTEM`・`effort` を agent.py に追加しているため）。第8章の並行修正（agent.py へ「追記」）とも矛盾しない書き方にした。
- **修正**: 12.2 のログの確認項目「1回の依頼に共通の**実行ID**を振り」を、第11章の用語に合わせて「**トレースID**」に変更。
- **一致を確認（修正なし）**: 表の成果物（`hello_claude.py`・`inspect_response.py`/`params_demo.py`/`chat.py`/`error_lab.py`・`llm_client.py`・`tools/weather.py`/`one_shot_tool.py`/`agent.py`・`tool_registry.py`/`tools/files.py`/`structured_output.py`・`context.py`/`tools/memory.py`・`multi_agent.py`・`patterns/`・`report_agent/`/`tests/`・`guardrails.py`/`evals/run_eval.py`/`batch_demo.py`）、`run_agent()`・`ToolRegistry`・`CostTracker`・`maybe_compact()`・`MODEL`/`FAST_MODEL`・`API_VERSION`・`stream_messages()` の `on_text`・408/409/429/5xx の再試行、pyproject.toml の注記（第10章で pytest を追加）。
- **残した点（軽微・判断）**: 最終構成に、各章の一時的な確認用スクリプト（第4章 `client_demo.py` 等、第6章 `decorator_basics.py` 等、第8章 `check_agent.py`＝「確認後は削除してよい」、第9章 `orchestrator_sketch.py`＝「保存は不要」）は載せていない。主要ファイルの構成図として妥当と判断。L39「第9章では5つの設計パターンを実装し」は、`patterns/` が4ファイル（オーケストレーター-ワーカーは第8章の `multi_agent.py` と第9章の骨格で扱う）だが、第9章本文が第8章の実装をこのパターンと位置付けているため修正しなかった。
