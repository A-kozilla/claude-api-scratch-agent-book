# コード検証レポート（再検証）

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_02.md
検証日: 2026-11-08
検証環境: Windows 11 / Git Bash・Windows PowerShell 5.1 / uv 0.13.5 / Python 3.12（uv 管理の cpython-3.12.15）/ httpx 0.28.1 / python-dotenv 1.2.4 / 偽Claude API（`httpx.MockTransport` と、それを包んだ 127.0.0.1 のローカルHTTPサーバー。必須ヘッダー・`anthropic-version: 2026-10-21`・必須ボディ項目・禁止パラメータ・prefill を検査）。実APIキーは使用していない。
コードブロック数: 27個（うち出力例の `text` 5個＝L218・L264・L290・L351・L714 は照合用のため判定数に含めない → 判定対象 22個）
  ✅ 動作確認済み: 14個
  ⚠️ 要確認: 0個
  ❌ エラーあり: 0個
  🔍 構文チェックのみ: 8個

## 前回からの経緯
- 2026-11-07 の ❌（`uv init` に `--no-package` がない）と ⚠️（#17・#19 の `text` ラベル化、uv の版、`.gitignore` の行番号）は、同日午前の検証で反映済みと確認していた。
- 今回は用語統一・長文分割の後の原稿からブロックを抽出し直した。ブロックの中身は前回と同一で、行番号だけが +3〜+5 ずれている。新しい空のフォルダーで、プロジェクト作成からやり直した。

---

## ❌ エラーが発生したコード

該当なし。

## ⚠️ 要確認のコード

該当なし。コード外の関連事項として、ワークスペースに紐づけないAPIキーでは #22・#23・#25 が 400（`anthropic-workspace-id` ヘッダー必須）になる。本文 L732 のトラブル表に「`This API key is not scoped to a workspace` → ワークスペースを選んでキーを作り直す」が追加されており、読者はここで対処できる。

---

## ✅ 動作確認済みコード一覧

| # | 位置 | 言語 | 行数 | 実行結果 |
|---|-----|-----|-----|--------|
| 4 | L211 `uv --version` | bash | 1行 | `uv 0.13.5 (46776a95d 2026-10-21 …)`。本文 L219 の例と同じ形 |
| 6 | L228 `uv python install 3.12` / `uv python list` | bash | 2行 | `cpython-3.12.15` をダウンロードして導入し、一覧に `cpython-3.12` の行が出る |
| 7 | L242 `uv init agent-from-scratch --python 3.12 --no-package` / `cd` | bash | 2行 | `Initialized project`。移動後の一覧は本文 L264 のとおり（`.git` `.gitignore` `.python-version` `README.md` `main.py` `pyproject.toml`） |
| 8 | L252 `ls -a` | bash | 1行 | 同上 |
| 9 | L257 `Get-ChildItem -Force` | powershell | 1行 | 隠しファイルも含めて一覧表示 |
| 11 | L283 `uv add httpx python-dotenv` | bash | 1行 | `Using CPython 3.12.15` / `Creating virtual environment at: .venv` / `Resolved 9 packages` / `Installed 8 packages`。本文 L290 と同じ形（キャッシュ済みのため Prepared 行は出ない） |
| 14 | L344 `uv run main.py` | bash | 1行 | `Hello from agent-from-scratch!` |
| 16 | L361 `uv run python -c "import httpx, dotenv; …"` | bash | 1行 | `httpx 0.28.1` |
| 18 | L440 `.env` 読み込み確認ワンライナー | bash | 1行 | ダミーキー（108文字）で `True 108` |
| 20 | L461 `git check-ignore -v .env` / `git status` | bash | 2行 | `.gitignore:12:.env	.env`（本文は13行目の例。「行番号は環境によって変わります」と明記済み）。`git status` に `.env` は出ない |
| 22 | L535 curl（bash / Git Bash） | bash | 8行 | URL のみローカル偽サーバーに置き換えて実行。`set -a; source .env; set +a` でキーが入り、3ヘッダー＋`--data-binary @request.json` で200、`thinking`→`text` の応答 |
| 23 | L553 curl.exe（PowerShell） | powershell | 8行 | 同上。`.env` の読み込み行でキーが設定され、`curl.exe` で200 |
| 25 | L611 hello_claude.py | python | 75行 | `uv run` で実行し、本文 L714 と同じ形（回答＋空行＋`[tokens] input=28 output=142`）。送信ヘッダーは3種、timeout は connect=10・read/write/pool=600。401/400/529 を返させると `HTTP xxx: {...}` と `request-id: …` を表示して終了コード1。`.env` がないと「ANTHROPIC_API_KEY が見つかりません。.env を確認してください。」で終了 |
| 26 | L707 `uv run hello_claude.py` | bash | 1行 | 同上 |

## 🔍 構文チェックのみ

| # | 位置 | 言語 | 結果 |
|---|-----|-----|-----|
| 1 | L183 uv インストール（PowerShell） | powershell | PSParser でエラー0。未実行（ネットワークからスクリプトを取得して実行するため） |
| 2 | L190 uv インストール（curl） | bash | `bash -n` OK。未実行（同上） |
| 3 | L197 brew / winget | bash | `bash -n` OK。未実行（uv 導入済み） |
| 13 | L314 pyproject.toml | toml | `tomllib` で妥当。行末コメントは本文で「説明用」と明記済み。実機の生成物は `python-dotenv>=1.2.4`、例は `>=1.2.1`（L328 に「実際の数字は追加した時期によって変わります」とある） |
| 17 | L429 `.env` の中身 | text | 読み込みは #18 で確認 |
| 19 | L453 `.gitignore` への追記 | text | 追記したうえで #20 で無視されることを確認 |
| 21 | L519 request.json | json | 妥当。`model` / `max_tokens: 1024` / `messages` の最小構成。#22・#23 の送信に使用 |
| 24 | L573 レスポンス例 | json | 妥当。`thinking`→`text` の順、`usage` 4項目 |

## 本文の手順・誘導の確認（長文分割の影響）
- L240「まず、プロジェクトを置きたい場所にターミナルで移動してください。たとえば、ホームフォルダーの下の `projects` フォルダーなどです。移動したら、次のコマンドを実行してください。」は、移動→#7 の順を正しく案内している。
- L281（`uv add` の前置き）、L366（`ModuleNotFoundError` のときの確認先）、L405（`uv run main.py` で「No such file」のときの確認）は、分割後も「プロジェクトのフォルダーの中で実行する」という前提が保たれている。
- L427「プロジェクトのフォルダー直下に `.env`」、L451「`.gitignore` の末尾に、次の行を追加」、L517「プロジェクトのフォルダーに…`request.json` を作成」、L609「`hello_claude.py` を新規作成」は、いずれも置き場所と、追記か新規かが明確。この手順どおりに組み立てて #18〜#26 が動いた。
- L547・L565 の curl オプションの説明は、分割後も #22・#23 のコードと一致する。

## 補足（判定に影響しない）
- 用語統一は本文のみに適用されたため、コードブロック内のコメントに旧表記「フォルダ」が残っている（L243 #7・L253 #8・L258 #9・L430 #17）。本文の「フォルダー」と揃えるなら、コメントだけを直せばよい（動作には影響しない）。
- 第4章の確定ログ形式・`tracker.summary()` 形式との照合: 本章の出力例は `hello_claude.py` 独自の `[tokens] input=.. output=..` のみで、該当しない。

> 偽APIでの検証のため、実APIでの応答文面は未確認です。公開前に実キー（ワークスペースに紐づけたキー）で1回動作確認してください。
