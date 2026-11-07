# ファクトチェックレポート

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_02.md
検証日: 2026-11-07
検証クレーム数: 40件
  ✅ 検証済み: 33件
  ⚠️ 要確認: 5件
  ❌ 要修正: 2件（原稿修正済み）

主な一次情報（取得日 2026-11-07）:
- Get your API key: https://platform.claude.com/docs/en/get-api-key.md
- Authentication: https://platform.claude.com/docs/en/manage-claude/authentication.md
- Workspaces: https://platform.claude.com/docs/en/manage-claude/workspaces.md
- Rate limits（spend limit・usage tier）: https://platform.claude.com/docs/en/api/rate-limits.md
- Errors / Pricing / Models overview / Thinking / Messages API リファレンス
- Anthropic サポート「API key best practices」: https://support.claude.com/en/articles/9767949-api-key-best-practices-keeping-your-keys-safe-and-secure
- GitHub「Supported secret scanning patterns」: https://docs.github.com/en/code-security/secret-scanning/introduction/supported-secret-scanning-patterns
- uv: https://docs.astral.sh/uv/concepts/projects/init/ ・ https://docs.astral.sh/uv/getting-started/installation/ ・ https://docs.astral.sh/uv/reference/cli/
- httpx: https://www.python-httpx.org/advanced/timeouts/
- python-dotenv ソース（`load_dotenv(override=False)`）、PyPI（httpx 0.28.1 / anyio 4.16.0 / python-dotenv 1.2.4 / uv 0.13.7）

---

## ✅ 検証済み（正確）

### クレーム1
**記述**: claude.ai は定額プラン、Claude API は従量課金で別契約
**検証結果**: API は Console の Billing でクレジット前払い（prepaid）。サポート記事で確認。

### クレーム2
**記述**: 「アドレスは https://platform.claude.com です。以前は別のアドレスで提供されていた時期もある」
**検証結果**: 公式ドキュメントの Console リンクはすべて platform.claude.com（旧 console.anthropic.com）。

### クレーム3
**記述**: 組織（Organization）→ワークスペース（Workspace）→APIキーの階層、ワークスペースごとに上限を分けられる
**検証結果**: Workspaces ドキュメント「assign members, service accounts, API keys, and resource limits to each one」。

### クレーム4
**記述**: クレジット前払い、残高がなくなるとエラー、「自動リロード」設定がある
**検証結果**: サポート記事: 残高がなくなるとAPIを呼べない。Billing 画面の Credit balance 欄に auto-reload（「Set up auto-reload」）がある。

### クレーム5
**記述**: 「`sk-ant-` で始まる長い文字列」「キーの全体が表示されるのは作成直後の一度だけ」
**検証結果**: get-api-key「The Console shows the full key, which starts with `sk-ant-`, only once, at creation.」

### クレーム6
**記述**: 「一覧画面には、キーの末尾の数文字など、見分けるための一部しか表示されない」／「失くしたら作り直す」
**検証結果**: Admin API も「partially redacted hint」のみ返す。「If you lose a key, you can’t view it again… Create a new key instead.」

### クレーム7
**記述**: 「組織全体の上限に加えて、ワークスペースごとにも上限を設けられます」「上限に達すると、それ以降のリクエストはエラーで拒否され」
**検証結果**: Rate limits「Setting your own spend limit」／Workspaces「Set workspace limits」。上限到達時は HTTP 400 `invalid_request_error`（メッセージは `You have reached your specified API usage limits`）。

### クレーム8
**記述**: 「アカウントを作ったばかりの段階ではレート制限が低めに設定されています」
**検証結果**: Rate limits「New organizations… may start in the Evaluation tier, with limits below the standard limits」。

### クレーム9
**記述**: 料金表（Opus $4/$20、Sonnet $2/$10、Haiku $0.10/$0.50）
**検証結果**: Pricing と一致。

### クレーム10
**記述**: 30トークン入力・150トークン出力で合計0.0031ドル程度／5万トークン×20回＝4ドル
**検証結果**: 30×4/1M=0.00012、150×20/1M=0.003、計0.00312。1,000,000×$4/1M=$4。計算正しい。

### クレーム11
**記述**: 「この思考に使われたトークンも、出力トークンとして課金されます」
**検証結果**: Thinking「the tokens Claude spends reasoning are billed as output tokens, even when the thinking text isn’t returned to you」。

### クレーム12
**記述**: uv は Astral 製・Rust 製、Python本体・仮想環境・依存関係を管理
**検証結果**: uv 公式ドキュメント。

### クレーム13
**記述**: PowerShell `irm https://astral.sh/uv/install.ps1 | iex`（ExecutionPolicy ByPass）、`curl -LsSf https://astral.sh/uv/install.sh | sh`、`brew install uv`、`winget install --id=astral-sh.uv -e`
**検証結果**: uv Installation ページの記載と一致。

### クレーム14
**記述**: `uv --version` の出力例「uv 0.13.5」
**検証結果**: 2026-11-07時点の最新は 0.13.7。本文で「数字は時期によって異なる」と断っているため問題なし。

### クレーム15
**記述**: `uv python install 3.12` / `uv python list`、システムのPythonを上書きしない
**検証結果**: uv CLI リファレンスで確認。

### クレーム16
**記述**: 「新しいuvは何も指定しないとパッケージ構成で作り、`main.py` も作られない」「`--no-package` は…平らな構成」
**検証結果**: uv「Creating projects」: 既定の application は `src/<name>/__init__.py` とビルドシステムを作る（「Prior to v0.12, uv did not define a build system for applications by default」）。`--no-package` で `main.py`・`README.md`・`.python-version`・`pyproject.toml` の平らな構成。

### クレーム17
**記述**: 「`uv init` は、パソコンにGitがインストールされていると…Gitのリポジトリとして初期化」
**検証結果**: CLI リファレンス `--vcs`「By default, uv will initialize a Git repository (`git`)」。

### クレーム18
**記述**: 「`uv init` を実行した時点では、まだ仮想環境（`.venv`）は作られていません」
**検証結果**: `.venv` は初回の `uv add` / `uv run` / `uv sync` で作成される（uv Projects ドキュメント）。

### クレーム19
**記述**: pyproject.toml の内容（name / version / description "Add your description here" / readme / requires-python / dependencies）
**検証結果**: uv ドキュメントの `--no-package` 例と同じ構造（ビルドシステムなし）。

### クレーム20
**記述**: `uv.lock` が正確なバージョンを固定し、`uv sync` で再現できる／`.venv` はコミットしない／`.gitignore` に最初から `.venv`
**検証結果**: uv Projects ドキュメントで確認。

### クレーム21
**記述**: `uv run` は実行前にロック・環境を確認して自動同期
**検証結果**: uv ドキュメント（「uv run… ensures the environment is up-to-date」）。

### クレーム22
**記述**: `uv run main.py` で「Hello from agent-from-scratch!」
**検証結果**: `--no-package` で生成される main.py は `print("Hello from <project>!")`。

### クレーム23
**記述**: VS Code: Python拡張（Microsoft、Pylance 同梱）、「Python: Select Interpreter」、`code .`、「Shell Command: Install 'code' command in PATH」、「Developer: Reload Window」、統合ターミナル `Ctrl+``
**検証結果**: VS Code / Python 拡張の既知のコマンド名どおり（画面操作のため最終確認は人手で）。

### クレーム24
**記述**: 「`load_dotenv()` は初期設定では、同じ名前の環境変数がOS側にすでにあると、`.env` の値で上書きしません」
**検証結果**: python-dotenv `def load_dotenv(..., override: bool = False, ...)`。

### クレーム25
**記述**: `git check-ignore -v .env` の出力「.gitignore:13:.env	.env」形式
**検証結果**: Git の `check-ignore -v` は `<source>:<linenum>:<pattern><TAB><pathname>` 形式。

### クレーム26
**記述**: 漏えい時「該当するキーを無効化（Disable）するか削除」
**検証結果**: Authentication「Disable is reversible… whereas Delete is permanent」。

### クレーム27
**記述**: 「GitHubのシークレットスキャン…との連携によって、キーが無効化され通知が届く場合があります」
**検証結果**: サポート記事「Anthropic has partnered directly with GitHub… Anthropic automatically deactivates the exposed API key. The affected user receives a detailed email notification」。GitHub の partner パターン一覧に `anthropic_api_key` がある。

### クレーム28
**記述**: `anthropic-version` は API 仕様の版を固定し、値を変えない限り同じ版で処理
**検証結果**: Versions ページ（版ごとに入出力パラメータを保持）。

### クレーム29
**記述**: ボディの最小構成は `model`・`max_tokens`・`messages`
**検証結果**: Messages API リファレンス（`max_tokens` は必須）。

### クレーム30
**記述**: 「Windows PowerShell 5.1では、`curl` がInvoke-WebRequest…の別名」
**検証結果**: Windows PowerShell 5.1 の既定エイリアス（PowerShell 7 では削除済み）。

### クレーム31
**記述**: 返ってきたJSON（先頭に `{"type":"thinking","thinking":"","signature":...}`、`stop_reason`、`usage`）
**検証結果**: Thinking「`display` defaults to `"omitted"` on these models」→ `thinking` は空文字、`signature` あり。Opus 5.5 は omitted が既定。

### クレーム32
**記述**: `authentication_error`（401）はキーの誤り、`invalid_request_error`（400）はヘッダーやボディの誤り
**検証結果**: Errors ページと一致。

### クレーム33
**記述**: 「httpxは、何も指定しないと **5秒** で待つのをやめて」／`-sSi` で `request-id` を確認
**検証結果**: httpx「raise a TimeoutException after 5 seconds of network inactivity」。Errors「Every API response includes a unique `request-id` header」、公式例も `curl -sS -i`。

---

## ⚠️ 要確認（古い可能性あり）

### クレーム34
**記述**: APIキー発行 STEP 2〜3「キーの作成（Create Key）を選びます」「キーの名前を…所属させるワークスペースには、STEP 1で作ったものを選びます」
**懸念点**: 現在の作成ダイアログでは、名前・ワークスペースに加えて **有効期限（Expiration）** と **Linked account**（自分＝personal key / サービスアカウント）を選ぶ。ボタン表記は「Create key」。
**検索結果**: get-api-key「Click **Create key**, name the key, select an expiration, and set **Linked account** to yourself or a service account.」。期限は 3時間 / 1日 / 7日 / 30日 / カスタム / Never（作成後は変更不可、期限切れは401）。
**推奨対処**: STEP 3 に「有効期限は学習期間に合わせて選ぶ（例: 30日）。Linked account は自分のままでよい」を追記。期限切れで 401 になる点を 2.5節の表にも追記すると親切。

### クレーム35
**記述**: 「組織には、過去のクレジット購入額などに応じた「利用ティア（Usage tier）」があり」
**懸念点**: 現行ドキュメントはティア決定を「usage history and account standing」としており、クレジット購入額基準の説明は旧仕様の可能性。ティア名は Start / Build / Scale（＋Custom、新規は Evaluation）。
**検索結果**: Rate limits「Organizations are placed on a tier automatically based on usage history and account standing」。月額上限: Start $500 / Build $1,000 / Scale $200,000。
**推奨対処**: 「利用実績などに応じた「利用ティア（Usage tier）」があり」に修正。

### クレーム36
**記述**: 2.5節「うまくいかないときは」の表（401/400/404/429・529 …）
**懸念点**: 学習者が実際に遭遇しやすい「自分で設定した利用上限に達した」ケースは **400 `invalid_request_error`**（message: `You have reached your specified API usage limits`）で返るため、表の「400 = ボディやヘッダーの誤り」だけだと原因を誤認しやすい。残高・支払いの問題は 402 `billing_error`。
**検索結果**: Rate limits「When usage reaches a spend limit you set, requests return HTTP 400 with error type `invalid_request_error`」／Errors「402 - billing_error」。
**推奨対処**: 表に「`HTTP 400`（message が “You have reached your specified … usage limits”）｜利用上限に到達｜Console で上限を確認」「`HTTP 402`｜支払い・残高の問題｜Billing でクレジットを確認」を追加。

### クレーム37
**記述**: 料金表の「$0.50（10万トークン以下）」（出力列に注記）
**懸念点**: 10万トークンの閾値は「プロンプト（入力）長」に対するもので、入力・出力の両単価に効く。出力列だけに注記があると「出力が10万トークン以下」と読める。
**検索結果**: Pricing「Claude Haiku 5.5 (for prompts up to 100,000 tokens)」、超過時は $0.50 / $2.50。
**推奨対処**: モデル列を「`claude-haiku-5-5`（プロンプト10万トークン以下）」とするか、表の下に注記を置く（第0章の「入力10万トークン以下」表記と統一）。

### クレーム38
**記述**: 「ヘッダーは次の3つが必須です」（`x-api-key` …）
**懸念点**: 認証ヘッダーは公式上 `Authorization: Bearer <key>` が主で、`x-api-key` は「legacy」表記（引き続き受け付けられる）。
**検索結果**: auth.md「You can also send the key in the legacy `x-api-key` header in place of `Authorization`.」／migration「The Claude API accepts a key in either header.」
**推奨対処**: NOTE で「`Authorization: Bearer <APIキー>` でも同じく認証できる（公式ドキュメントはこちらを主に記載）。本書は curl 例と対応が取りやすい `x-api-key` を使う」と補足。方針は facts.md で決定。

---

## ❌ 要修正（誤りの可能性が高い）

### クレーム39
**記述**: 利用上限 STEP 1「設定の中にある上限（Limits）の画面を開きます。組織全体の利用上限と、ワークスペースごとの上限を確認できます。」／STEP 2「そのワークスペースに月額の上限を設定します」
**問題**: Console の「Limits」（Rate limits, `platform.claude.com/usage/limits`）はレート制限の画面。組織の spend limit は **Billing** 画面の「Spend limits」欄、ワークスペースの spend limit は **Workspaces** 画面でワークスペースを選んだパネルの「Spend limits」で設定する。また **Default Workspace には spend limit を設定できない**。
**正しい情報**: rate-limits.md「go to the Billing page… In the **Spend limits** section, click **Adjust limit**」／workspaces.md「Spend limits: On the Workspaces page… select the workspace. In the panel that opens, click **Spend limits** to cap monthly spending and configure alerts」「You cannot set spend limits on the Default Workspace.」
**修正案（適用済み）**: STEP 1 を「請求（Billing）の画面の利用上限（Spend limits）欄で組織全体の月額上限を確認・設定」、STEP 2 を「ワークスペース（Workspaces）の画面でワークスペースを選び、利用上限（Spend limits）から設定。既定のワークスペースには上限を設定できない」に修正。

### クレーム40
**記述**: `uv add httpx python-dotenv` の出力例「Resolved 9 packages」「Prepared 7 packages」「Installed 7 packages」と7件のパッケージ一覧
**問題**: anyio 4.x は `typing_extensions; python_version < "3.15"` に依存するため、Python 3.12 では `typing-extensions` もインストールされる（計8件。Resolved 9 はプロジェクト自身を含む数で整合）。一覧から欠落し、件数も合わない。
**正しい情報**: PyPI anyio 4.16.0 requires_dist: `typing_extensions>=4.16.0; python_version < "3.15"`。httpx 0.28.1 の依存は anyio・certifi・httpcore==1.*・idna（httpcore→h11）。
**修正案（適用済み）**: 「Prepared 8 packages」「Installed 8 packages」とし、「+ typing-extensions==4.x.x」を追加。

---

## 総評

環境構築の手順（uv・VS Code・dotenv・git・curl）は一次情報とよく一致している。Console 操作では、spend limit の設定場所が「Limits」画面になっていた点を修正した（Limits 画面はレート制限用）。APIキー作成ダイアログに「有効期限」「Linked account」が加わっている点、利用上限到達時に 400 が返る点は、読者がつまずきやすいので追記を強く推奨する。画面名・ボタン名は変わりやすいため、公開前に実画面での確認を推奨。
