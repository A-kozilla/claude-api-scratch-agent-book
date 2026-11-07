# コード検証レポート

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_02.md
検証日: 2026-11-07
検証環境: Windows 11 / Git Bash・PowerShell 5.1 / uv 0.13.5（2026-10-21リリース）/ Python 3.12 / httpx 0.28.1 / python-dotenv 1.2.4 / 偽Claude API
コードブロック数: 27個（うち出力例の `text` 5個は照合用のため判定数に含めない → 判定対象 22個）
  ✅ 動作確認済み: 11個
  ⚠️ 要確認: 0個（2個を2026-11-07に原稿修正済み → 🔍へ移動）
  ❌ エラーあり: 1個（原稿修正済み）
  🔍 構文チェックのみ: 10個

---

## ❌ エラーが発生したコード

### コードブロック #7（chapter_02.md L239付近 `uv init`）【原稿修正済み】

**元のコード**:
```bash
uv init agent-from-scratch --python 3.12
cd agent-from-scratch
```

**エラー内容**（その後の L340 `uv run main.py` で発生）:
```text
error: Failed to spawn: main.py
  cause: program not found
```

**原因**: 現行の uv（0.13.5）は、`uv init` の既定がパッケージ構成（`--package`）になっている（`uv help init`: "--package ... This is the default behavior." / "Applications are packaged by default. Use `--no-package` ..."）。そのため `src/agent_from_scratch/__init__.py` が作られ、`main.py` が作られない。`pyproject.toml` にも `[project.scripts]`・`[build-system]`・`authors` が入り、本文 L287 のファイル一覧・L310 の pyproject.toml と食い違う。

**修正内容**（原稿に反映済み）:
```bash
uv init agent-from-scratch --python 3.12 --no-package
cd agent-from-scratch
```
あわせて L245 の説明に「`--no-package` は配布用のパッケージ構成（`src` フォルダ）にせず平らな構成にする指定。新しいuvは指定しないとパッケージ構成になり `main.py` も作られないため必ず付ける」旨の2文を追加。
修正後は、ファイル一覧（`.git` `.gitignore` `.python-version` `README.md` `main.py` `pyproject.toml`）、pyproject.toml の内容、`uv run main.py` → `Hello from agent-from-scratch!` がすべて本文どおりになることを確認。
`--no-package` は古い uv にもあるオプションなので、旧版の読者にも影響しない。

> 他メディア: `udemy/02_toc/toc.md` L104 にも `uv init agent-from-scratch` があります。Udemyスクリプト・YouTube台本で同じコマンドを示す場合は `--no-package` を付けてください。L747 の章末まとめの `uv init agent-from-scratch` は省略表記なので修正していません。

---

## ⚠️ 要確認のコード

### コードブロック #17（L425 `.env` の中身）・#19（L449 `.gitignore` への追記）

**懸念点**: ファイルの中身なのに `bash` ラベルになっている。`.env` は `source` できるので実害は小さいが、`.gitignore` の行（`.env`）はシェルで実行するとコマンドとして解釈される。コード検証ツールや読者が「実行するコマンド」と誤解しやすい。
**推奨対処**: 両方とも ` ```text ` に変更（または `.env` は ` ```dotenv `、`.gitignore` は ` ```gitignore `）。

### 出力例について（判定数外・軽微）
- L215 `uv 0.9.x`: 現行は `uv 0.13.x`。本文に「時期によって異なる」とあるので必須ではないが、`uv 0.13.x` などに更新すると読者が戸惑いにくい。
- L459 付近 `.gitignore:12:.env`: 現行 uv の `.gitignore`（10行）に空行＋コメント＋`.env` を追記すると13行目になる。「のように」と書かれているので許容範囲。
- L261 のファイル一覧と L310 の pyproject.toml は、上記 ❌ 修正後は本文どおり（`python-dotenv>=1.2.4` など版数のみ時期依存）。

---

## ✅ 動作確認済みコード一覧

| # | 位置 | 言語 | 行数 | 実行結果 |
|---|-----|-----|-----|--------|
| 4 | L208 `uv --version` | bash | 1行 | `uv 0.13.5` |
| 6 | L225 `uv python install 3.12` / `uv python list` | bash | 2行 | `--python 3.12` 指定の `uv init` で 3.12 が解決されることを確認 |
| 8 | L249 `ls -a` | bash | 1行 | 修正後のコマンドで本文の一覧と一致 |
| 9 | L254 `Get-ChildItem -Force` | powershell | 1行 | 同上 |
| 11 | L280 `uv add httpx python-dotenv` | bash | 1行 | `.venv` 作成・7パッケージ導入（typing-extensions を含め現行は8〜9件） |
| 14 | L340 `uv run main.py` | bash | 1行 | 修正後 `Hello from agent-from-scratch!` |
| 16 | L357 `uv run python -c "import httpx, dotenv ..."` | bash | 1行 | `httpx 0.28.1` |
| 18 | L436 `.env` 読み込み確認ワンライナー | bash | 1行 | `True 15`（モックキー。実キーなら100前後） |
| 20 | L457 `git check-ignore -v .env` / `git status` | bash | 2行 | `.gitignore:13:.env	.env` で無視を確認 |
| 25 | L605 hello_claude.py | python | 75行 | 偽APIで200、本文と同じ形（回答＋`[tokens] input=.. output=..`）。ヘッダー・ボディは facts どおり |
| 26 | L701 `uv run hello_claude.py` | bash | 1行 | 同上 |

## 🔍 構文チェックのみ

| # | 位置 | 言語 | 結果 |
|---|-----|-----|-----|
| 1 | L180 uv インストール（PowerShell） | powershell | 公式インストールコマンドどおり。未実行（環境に uv 導入済み） |
| 2 | L187 uv インストール（curl） | bash | 同上 |
| 3 | L194 brew / winget | bash | 構文OK。未実行 |
| 13 | L310 pyproject.toml | toml | tomllib で妥当。行末コメントは本文で「説明用」と明記済み |
| 21 | L513 request.json | json | 妥当。model/max_tokens/messages の最小構成 |
| 22 | L529 curl（bash） | bash | `bash -n` OK。URL・3ヘッダー（x-api-key / anthropic-version: 2026-10-21 / content-type）・`--data-binary @request.json` は facts どおり（偽APIに届かないため送信は未実施） |
| 23 | L547 curl.exe（PowerShell） | powershell | PSParser でエラー0。`.env` 読み込み行は実行し、`$env:ANTHROPIC_API_KEY` に設定されることを確認 |
| 24 | L567 レスポンス例 | json | 妥当。thinking → text の順、usage 4項目 |
| 17 | L425 `.env` の中身 | text | ⚠️対応で `text` に変更。中身は L436 のワンライナーで読み込み確認済み |
| 19 | L449 `.gitignore` への追記 | text | ⚠️対応で `text` に変更。追記後 `git check-ignore` で無視を確認済み |

## ⚠️対応（2026-11-07）

| 項目 | 対応 | 内容 |
|-----|-----|-----|
| #17 L425 `.env` の中身 | 修正 | ` ```bash ` → ` ```text `（中身は変更なし） |
| #19 L449 `.gitignore` への追記 | 修正 | ` ```bash ` → ` ```text `（中身は変更なし）。`dotenv`/`gitignore` ラベルは書籍変換時のハイライト対応が不確実なため、既存の出力例と同じ `text` を採用 |
| 出力例 L215 `uv 0.9.x` | 修正 | `uv 0.13.5` に更新（直前の「時期によって異なる」の説明はそのまま） |
| 出力例 L463 `.gitignore:12:.env` | 修正 | 現行uvの実測に合わせて `.gitignore:13:.env` ／「13行目」に更新し、「（行番号は環境によって変わります）」を追記 |
| L261 ファイル一覧・L310 pyproject.toml | 対応不要 | ❌ 修正後は本文どおり。版数のみ時期依存 |

第4章の確定ログ形式との照合: 本章の出力例は `hello_claude.py` 独自の `[tokens] input=.. output=..` のみで、`llm_client` のログ・`tracker.summary()` は登場しないため修正対象なし。
残件: なし（`udemy/02_toc/toc.md` の `uv init` に `--no-package` を付ける件は他メディアのため本対応の範囲外）。
