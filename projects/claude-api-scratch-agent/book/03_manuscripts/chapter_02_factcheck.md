# ファクトチェックレポート（再検証）

対象ファイル: projects/claude-api-scratch-agent/book/03_manuscripts/chapter_02.md
検証日: 2026-11-08
検証クレーム数: 65件
  ✅ 検証済み: 61件
  ⚠️ 要確認: 3件
  ❌ 要修正: 1件

## 前回からの経緯

- 今朝の検証（44件・❌1）を受けて、ワークスペース必須の STEP 3・エラー表3行・Expiration／Linked account・ティア・Haiku 注記・`x-api-key` NOTE・timeout・章末 `--no-package` を修正した。修正箇所の再チェックで⚠️3件（「API keys」表記、legacy の位置づけ、402 と残高不足）が出て、これも反映済み。
- その後、用語統一・長文分割（56文）・Batches の上限超過の注記・エラー表の「残高不足400／402＝支払い情報」行が入った。本レポートはそれを受けて、章全体を検証し直したもの。分割で言い換えた文は `git diff HEAD` で元の文と照合した。

主な一次情報（いずれも 2026-11-08 取得）:
- Authentication: https://platform.claude.com/docs/en/manage-claude/authentication.md
- Get your API key: https://platform.claude.com/docs/en/get-api-key.md
- Workspaces: https://platform.claude.com/docs/en/manage-claude/workspaces.md
- Rate limits: https://platform.claude.com/docs/en/api/rate-limits.md
- Errors: https://platform.claude.com/docs/en/api/errors.md
- Batch processing: https://platform.claude.com/docs/en/build-with-claude/batch-processing.md
- Pricing: https://platform.claude.com/docs/en/about-claude/pricing.md
- Steering thinking（adaptive-thinking からリダイレクト）: https://platform.claude.com/docs/en/build-with-claude/thinking-steering-and-cost
- Migration 2026-10-21: https://platform.claude.com/docs/en/api/migration-2026-10-21.md
- API credits for Max, Ultra, and Team plans: https://platform.claude.com/docs/en/about-claude/api-credits-for-subscribers.md
- サポート記事「How do I pay for my Claude API usage」: https://support.claude.com/en/articles/8977456
- uv: https://docs.astral.sh/uv/getting-started/installation/ ・ https://docs.astral.sh/uv/reference/environment/ ・ `uv help init`（実機 uv 0.13.5）
- 実機: httpx 0.28.1（`Client().timeout`、`Timeout(600.0, connect=10.0)`、`Response.raise_for_status` のソース）、python-dotenv（`load_dotenv` のシグネチャ）
- GitHub: anthropics/anthropic-sdk-typescript#618（残高不足時の実レスポンス）、GitHub Changelog 2024-08-20（Anthropic のシークレットスキャン提携）

---

## ✅ 検証済み（正確）

### クレーム1
**記述**: claude.ai はブラウザ・アプリで使うチャット製品で、無料プランと定額プランがある。Claude API はHTTPでリクエストを送り、JSONで回答が返る従量課金（L33〜35・L41〜47）
**検証結果**: Messages API はHTTP＋JSON。API は Console で前払いクレジットを使う（サポート記事 8977456）。分割で文を言い換えたが、意味は変わっていない。※有料プランとAPI利用料の関係は❌クレーム65を参照。

### クレーム2
**記述**: Console のアドレスは https://platform.claude.com（L53）
**検証結果**: 公式ドキュメントの Console リンクはすべて platform.claude.com。

### クレーム3
**記述**: 組織→ワークスペース→APIキーの階層。ワークスペースごとに上限を分けられる（L55・L57）
**検証結果**: Workspaces「you can assign members, service accounts, API keys, and resource limits to each one」。

### クレーム4
**記述**: NOTE「APIキー（API keys）」「請求（Billing）」「ワークスペース（Workspaces）」「利用量（Usage）」（L61）
**検証結果**: Console のページ名（API keys・Billing・Workspaces・Usage）と一致。2文に分けても意味は変わっていない。

### クレーム5
**記述**: クレジットは前払い。残高がなくなると呼び出しがエラーになる。自動リロードがある（L79）
**検証結果**: サポート記事「If you run out of credits, you can no longer call the API」「Auto-reload purchases additional credits automatically when your balance falls below a threshold you set」。

### クレーム6
**記述**: STEP 1「設定（Settings）のワークスペースの画面で、新しいワークスペースを作ります」（L92）
**検証結果**: Workspaces「go to the Workspaces page (`platform.claude.com/settings/workspaces`)… Click **Create workspace**」。作成できるのは組織の admin だけだが、個人で作った組織なら本人が admin になる。

### クレーム7
**記述**: STEP 2「設定の中にある『API keys』の画面…キーの作成（Create key）」（L95）
**検証結果**: get-api-key「go to the API keys page (`platform.claude.com/settings/keys`)」「Click **Create key**」。

### クレーム8
**記述**: STEP 3「ワークスペースを選ばずに作ったキーでは、リクエストのたびにワークスペースを指定する必要があります。指定には `anthropic-workspace-id` ヘッダーを使います。本書の手順のままでは400エラーになります。」（L98）
**検証結果**: authentication「If your API key isn’t scoped to a workspace, you must specify the workspace ID in the `anthropic-workspace-id` header for each request」。ヘッダーがないと 400 `invalid_request_error`。3文に分けても因果関係は保たれている。personal key を Default Workspace に限定することもできる（Workspaces「a key bound to the Default Workspace」）。

### クレーム9
**記述**: 有効期限（Expiration）の例は30日。期限切れは401。Linked account は自分のままでよい（L99）
**検証結果**: authentication「a preset (3 hours, 1 day, 7 days, or 30 days)…」「After a key expires, requests made with it return a `401 authentication_error`」「Set **Linked account** to yourself for a personal key」。

### クレーム10
**記述**: `sk-ant-` で始まり、全体が表示されるのは作成直後の一度だけ（L102・L106）
**検証結果**: get-api-key「The Console shows the full key, which starts with `sk-ant-`, only once, at creation.」

### クレーム11
**記述**: コピーし忘れたら、削除して作り直す（L108）
**検証結果**: get-api-key「If you lose a key, you can’t view it again in the Console. Create a new key instead.」（「何本でも」は⚠️クレーム63）

### クレーム12
**記述**: 上限に達するとエラーで拒否され、それ以上の料金は発生しない。組織とワークスペースの両方に上限を設定できる（L114）
**検証結果**: rate-limits「When usage reaches a spend limit you set, requests return HTTP 400 with error type `invalid_request_error`」「you can set custom spend and rate limits for each workspace」。文を「拒否されます。そのため、…」と分けたが、意味は変わっていない。

### クレーム13（新規追記）
**記述**: 「ただし、Message Batches API では、わずかに超えることがあります（第11章参照）。」（L114）
**検証結果**: batch-processing「Because of high throughput and concurrent processing, batches may go slightly over the spend limit configured in the Claude Console for your Workspace.」。参照先の chapter_11.md L1070 にも同じ趣旨の記述（「利用上限をわずかに超えて課金されることがあります」）があり、整合する。

### クレーム14
**記述**: STEP 1「請求（Billing）の画面…利用上限（Spend limits）の欄で組織全体の月額上限」（L119）
**検証結果**: rate-limits「go to the Billing page (`platform.claude.com/settings/billing`)… In the **Spend limits** section, click **Adjust limit**」。

### クレーム15
**記述**: STEP 2「ワークスペース（Workspaces）の画面でそのワークスペースを選びます。そして、利用上限（Spend limits）から…」「Default Workspace には上限を設定できません」（L122）
**検証結果**: Workspaces「select the workspace. In the panel that opens, click **Spend limits**」「You cannot set spend limits on the Default Workspace.」。分割後も手順の順序は正しい。

### クレーム16
**記述**: 一定割合でメール通知（L125）
**検証結果**: Workspaces「configure alerts when spending reaches certain thresholds」。

### クレーム17
**記述**: 利用量（Usage）・コスト（Cost）の画面で、日ごと・モデルごと・APIキーごとに表示される（L129）
**検証結果**: rate-limits「Usage page provides… token and request charts」。api-credits-for-subscribers に「Cost page」へのリンクがある。サポート記事では Usage を「breakdown… across different models and API keys」と説明している。

### クレーム18
**記述**: 利用ティアは利用実績などで自動的に決まる。ティアごとに上限額の最大値とレート制限がある。新規組織は低めから始まる（L131）
**検証結果**: rate-limits「placed on a tier automatically based on usage history and account standing」「Your spend limit cannot exceed your current tier’s cap」「New organizations… may start in the Evaluation tier」。レート制限の定義を独立した文にしたが、意味は変わっていない。

### クレーム19
**記述**: トークンは、日本語ならおおむね1文字前後（L135）
**検証結果**: 公式に日本語の換算はない。幅を持たせた表現で、第3章の記述とも一致する（今朝の再チェックどおり）。

### クレーム20
**記述**: 入力（会話履歴・system プロンプト・ツール定義）と出力に分けて課金し、出力のほうが単価が高い（L137）
**検証結果**: pricing の表は全モデルで Output が Base input より高い。

### クレーム21
**記述**: Opus 5.5 $4/$20、Sonnet 5.5 $2/$10、Haiku 5.5 $0.10/$0.50（L141〜145）
**検証結果**: pricing と一致。

### クレーム22
**記述**: Haiku の単価は入力が10万トークン以下の場合。超えると0.50ドル／2.50ドル（L147）
**検証結果**: pricing「Claude Haiku 5.5 (for prompts over 100,000 tokens) $0.50 / … $2.50」。

### クレーム23
**記述**: 0.00012＋0.003＝0.0031ドル程度／5万×20＝100万トークン＝4ドル（L149・L151）
**検証結果**: 計算は正しい。

### クレーム24
**記述**: Opus 5.5 は思考を自動的に行い、その思考も出力トークンとして課金される（L153）
**検証結果**: thinking-steering-and-cost「Tokens Claude uses while thinking (billed as output tokens)」。思考は adaptive（モデルが要否を判断する）で、「自動的に」という表現と矛盾しない。

### クレーム25
**記述**: uv は Astral 製・Rust 製で、Python 本体・仮想環境・依存関係を管理する（L165〜169）
**検証結果**: uv 公式ドキュメント。

### クレーム26
**記述**: インストールコマンド4種（L185・L192・L199・L202）
**検証結果**: uv Installation と一字一句一致。

### クレーム27
**記述**: `-ExecutionPolicy ByPass` はそのコマンドの実行中だけ制限を緩める。インストーラーが PATH を追加するので、ターミナルを開き直す（L205〜207）
**検証結果**: `powershell -ExecutionPolicy` は起動したプロセスにだけ効く。uv の installer はシェルのプロファイルや PATH を変更する（「can modify your shell profiles… `UV_NO_MODIFY_PATH=1`」）。文を「という指定があります。これは…」と分けたが、意味は変わっていない。

### クレーム28
**記述**: `uv --version` の出力例「uv 0.13.5」（L219）
**検証結果**: 実機は uv 0.13.5（2026-10-21 ビルド）。本文に「インストールした時期によって異なります」と断りがある。

### クレーム29
**記述**: `uv python install 3.12` は既存の Python を上書きしない。`uv python list` には `cpython-3.12` の行が出る（L230〜236）
**検証結果**: uv CLI（今朝の実機確認どおり）。

### クレーム30
**記述**: `--no-package` で平らな構成になる。指定しないとパッケージ構成になり、`main.py` も作られない（L244・L248）
**検証結果**: `uv help init`「--no-package: Do not set up the project to be built as a Python package」「Applications are packaged by default」。実機の挙動は今朝確認済み。

### クレーム31
**記述**: Git がインストールされていれば、`uv init` は Git リポジトリを初期化する。ファイル一覧（L265〜273）
**検証結果**: `uv help init`「By default, uv will initialize a Git repository (`git`)」。文を分けたが、意味は変わっていない。

### クレーム32
**記述**: `.venv` は `uv add` か `uv run` を初めて実行したときに作られる（L277）
**検証結果**: 実機で、`uv add` のときに「Creating virtual environment at: .venv」と出る。

### クレーム33
**記述**: `uv add` の出力例（Resolved 9／Installed 8）と、「Resolved」「Installed」の意味（L291〜306）
**検証結果**: 今朝の実機再現と一致。2文に分けた説明も正しい。

### クレーム34
**記述**: `pyproject.toml` の内容と、`>=` の意味（L314〜328）
**検証結果**: 実機で生成されたものと同じ構造。

### クレーム35
**記述**: `uv.lock` が正確なバージョンを固定する。`uv sync` で再現できる。`.gitignore` には最初から `.venv` がある（L330〜338）
**検証結果**: uv Projects ドキュメントと、実機で生成された `.gitignore`。「コピーして、`uv sync` を実行します。すると…」と分けても手順の意味は同じ。

### クレーム36
**記述**: `uv run main.py` で「Hello from agent-from-scratch!」が出る。`uv run` は実行前に整合を確認し、ずれていれば同期する（L346〜355）
**検証結果**: 実機の出力と一致。`uv run` は実行前に lock と sync を行う。

### クレーム37
**記述**: activate のコマンド（`.venv\Scripts\activate`／`source .venv/bin/activate`）（L357）
**検証結果**: venv の標準のパス。分割後もOSとの対応は正しい。

### クレーム38
**記述**: `uv run python -c "import httpx, dotenv; …"` → `httpx 0.28.1`（L363〜366）
**検証結果**: 実機で httpx 0.28.1 を確認。

### クレーム39
**記述**: VS Code の手順（「PATHへの追加」、「Shell Command: Install 'code' command in PATH」、Python 拡張と Pylance、`code .`、「Python: Select Interpreter」、`.venv\Scripts\python.exe`／`.venv/bin/python`、`Ctrl+@`、「Developer: Reload Window」）（L370〜403）
**検証結果**: VS Code・Python 拡張のコマンド名どおり。JIS キーボードではバッククォートが @ キーの位置にあるため、`Ctrl+@` で開く。画面操作なので、最終確認は人手で行うこと。

### クレーム40
**記述**: プロキシ環境では `HTTPS_PROXY` を設定する（L401）
**検証結果**: uv Environment variables「`HTTPS_PROXY`: Proxy for HTTPS requests.」。

### クレーム41
**記述**: `load_dotenv()` は初期設定では既存の環境変数を上書きしない（L447）
**検証結果**: 実機 `inspect.signature(load_dotenv)` → `override: bool = False`。

### クレーム42
**記述**: `git check-ignore -v .env` → `.gitignore:13:.env	.env`（L467）
**検証結果**: 今朝の実機確認どおり。「成功です。『…』という意味です。」と分けても意味は同じ。

### クレーム43
**記述**: `.gitignore` は、すでにコミットしたファイルには効かない（L469）
**検証結果**: Git の仕様（追跡済みのファイルは無視されない）。

### クレーム44
**記述**: 漏えいしたら、キーを無効化（Disable）するか削除する（L478）
**検証結果**: authentication「**Disable** is reversible… whereas **Delete** is permanent」「disable or delete any key you suspect has leaked」。

### クレーム45
**記述**: GitHub のシークレットスキャンとの連携で、キーが無効化され通知が届く場合がある（L491）
**検証結果**: GitHub Changelog 2024-08-20「GitHub will forward any exposed tokens found in public repositories to Anthropic, who will then revoke the compromised tokens and notify the affected users」。分割して「GitHubには…があります。」を先に出したが、意味は変わっていない。

### クレーム46
**記述**: エンドポイント `POST https://api.anthropic.com/v1/messages`、必須ヘッダー3つ、`anthropic-version: 2026-10-21`、ボディの最小構成3項目（L501〜509）
**検証結果**: authentication・migration の cURL 例と一致。Messages API リファレンスでは `model`・`max_tokens`・`messages` に optional の表記がない。

### クレーム47
**記述**: NOTE「公式は `Authorization: Bearer` を主に紹介。`x-api-key` は legacy だが引き続き使え、公式の curl 例にも使われている」（L511）
**検証結果**: authentication「send on every request as a bearer token in the `Authorization` header」「You can also send the key in the legacy `x-api-key`」。同じページの cURL 例は `x-api-key` を使っている。migration「The Claude API accepts a key in either header.」。4文に分けても正確。

### クレーム48
**記述**: `set -a; source .env; set +a`、`-sS`、`--data-binary @request.json` の意味（L537〜547）
**検証結果**: bash と curl の仕様どおり。

### クレーム49
**記述**: Windows PowerShell 5.1 では `curl` が Invoke-WebRequest の別名になっている（L565）
**検証結果**: 実機 PowerShell 5.1 で `Get-Alias curl` → `Invoke-WebRequest`（今朝確認）。「別コマンドの別名」「その別コマンドとは…」と2文に分けても正確。

### クレーム50
**記述**: レスポンスの JSON（空の `thinking`＋`signature`、`text`、`stop_reason`、`usage`）。思考ブロックは含まれないこともある（L573〜596）
**検証結果**: thinking-steering-and-cost「`display: "omitted"`… the `thinking` field is empty」「a turn where Claude skips thinking contains no thinking block. Don’t build application logic that assumes every assistant turn starts with one.」。

### クレーム51
**記述**: `-sSi` でヘッダーと `request-id` を確認する。`authentication_error`（401）、`invalid_request_error`（400）（L598〜600）
**検証結果**: errors「Every API response includes a unique `request-id` header」。公式例は `curl -sS -i`。400・401 の型も一致。

### クレーム52
**記述**: httpx の既定は5秒。接続は10秒、接続後は応答のデータが届くまで最大600秒（L695）
**検証結果**: 実機 `httpx.Client().timeout` → `Timeout(timeout=5.0)`、`httpx.Timeout(600.0, connect=10.0)` → `connect=10.0, read=600.0, write=600.0, pool=600.0`。

### クレーム53
**記述**: `httpx.RequestError` は、切断やタイムアウトなどで応答が届かなかった場合のエラー（L697）
**検証結果**: httpx の例外階層（`TimeoutException`・`ConnectError` などは `RequestError` のサブクラス）。

### クレーム54
**記述**: `max_tokens` や `refusal` の場合は、本文が不完全なことがある（L699）
**検証結果**: Messages API の stop_reason の値（facts.md の一覧と同じ）。2文に分けても因果関係は保たれている。

### クレーム55
**記述**: エラー表「`HTTP 400`（`You have reached your specified … usage limits`）」（L731）
**検証結果**: rate-limits「The message starts with `You have reached your specified API usage limits`, or `You have reached your specified workspace API usage limits`」。

### クレーム56
**記述**: エラー表「`HTTP 400`（`This API key is not scoped to a workspace`）」（L732）
**検証結果**: authentication のエラー本文の冒頭と一致。

### クレーム57（新規追加行）
**記述**: エラー表「`HTTP 400`（`Your credit balance is too low`）｜クレジット残高の不足｜請求（Billing）の画面でクレジットを購入する」（L733）
**検証結果**: メッセージは公式の api-credits-for-subscribers にある「When the balance is exhausted, requests return: `Your credit balance is too low to access the Anthropic API. Please go to Plans & Billing…`」と一致。公式ページにステータスコードの記載はない。ただし anthropics/anthropic-sdk-typescript#618 で、2026-09-17 に生の HTTPS 呼び出しが `400 invalid_request_error` を返したと報告されている。将来402に変わる可能性はあるが、表には402の行もあるので、読者はどちらでも原因にたどり着ける。

### クレーム58（新規追加行）
**記述**: エラー表「`HTTP 402`｜支払い情報の問題」（L734）
**検証結果**: errors「402 - `billing_error`: There’s an issue with your billing or payment information.」。

### クレーム59
**記述**: エラー表の 404（モデルIDやURLの誤り）と 429／529（送りすぎ・混雑）（L735・L736）
**検証結果**: errors「404 - `not_found_error`… Check the endpoint path」「429 - `rate_limit_error`」「529 - `overloaded_error`」。

### クレーム60
**記述**: 2026-10-21 版では `temperature` などを送ると400になる（L740）
**検証結果**: migration「In `2026-10-21`, a request that sends `temperature`, `top_p`, or `top_k` returns a 400 error, even at the parameter’s default value.」

### クレーム61
**記述**: 章末まとめ「作成は `uv init agent-from-scratch --python 3.12 --no-package` です。追加は `uv add httpx python-dotenv`、実行は `uv run` です。」（L757）
**検証結果**: 本文 L244 のコマンドと一致。分割後も3コマンドの対応は正しい。

---

## ⚠️ 要確認（古い可能性あり）

### クレーム62
**記述**: 「`raise_for_status()` は、HTTPステータスが400番台・500番台かどうかを調べます。該当するときは、`httpx.HTTPStatusError` を発生させます。」（L697）。コードのコメント「4xx・5xx なら例外を発生させる」（L658）
**懸念点**: 長文分割で「400番台・500番台かどうかを調べます」という文ができ、この関数が4xx・5xxだけを判定しているように読める。実装は「2xx（成功）以外ならすべて例外」で、1xx・3xx でも `HTTPStatusError` が発生する。Claude API が 3xx を返すことは通常ないので、実害は小さい。ただ、第4章で自作クライアントを作る前に正確にしておくほうがよい。
**検索結果**: httpx 0.28.1 `Response.raise_for_status` のソース。`if self.is_success: return self` のあとで、`error_types = {1: "Informational response", 3: "Redirect response", 4: "Client error", 5: "Server error"}` で例外を発生させている。
**推奨対処**: L697 を次のように書き換える。
「`raise_for_status()` は、HTTPステータスが成功（200番台）かどうかを調べます。成功でなければ、`httpx.HTTPStatusError` を発生させます。Claude APIのエラーは400番台・500番台で返るので、ここで受け止められます。」
コードのコメント（L658）は、必要なら「# 2xx 以外（4xx・5xx など）なら例外を発生させる」に変える。コードを変えた場合は、chapter_02_code_verify.md の該当項目も見直すこと。

### クレーム63
**記述**: 「これは、Consoleのアカウントが乗っ取られた場合でも、既存のキーが盗まれないようにするための設計です。」（L106）／「キーは何本でも発行できるので」（L108）
**懸念点**: 一次情報で確認できるのは、全体が表示されるのは作成時の一度だけで、一覧には一部（partially redacted hint）しか出ないことまで。設計の理由は公式に書かれていない。また「何本でも」と言い切っているが、発行数に上限がないことは確認できない。組織の設定（作成権限・有効期限ポリシー）によっては作成できない場合もある（get-api-key「If the **Create key** button… is disabled, your role might not allow you to create keys」）。
**検索結果**: get-api-key「The Console shows the full key… only once, at creation.」「only a partially redacted hint」。上限についての記述はない。
**推奨対処**: 理由は推測として書き、本数は言い切らない。
- L106 修正案: 「万一Consoleの画面をのぞかれても、既存のキーの全体は分からない。そうした安全面を考えた仕組みだと言えます。」（または、この文を削除する）
- L108 修正案: 「キーは必要なときにいつでも新しく発行できるので、『失くしたら作り直す』が正しい運用です。」

### クレーム64
**記述**: 章末まとめ「漏えいしたら、何よりも先にConsoleでキーを無効化します。そのうえでcurlとhttpxから、エンドポイント・3つの必須ヘッダー・JSONボディでMessages APIを呼び出しました。」（L758）
**懸念点**: 「そのうえで」が直前の「漏えい時の無効化」を受けるので、キーを無効化してから API を呼んだように読める（事実の順序と合わない）。この接続語は HEAD の時点からあるが、今回の分割で「呼び出しました。回答は、…」の文が増え、ずれが目立つようになった。
**推奨対処**: 修正案:「…漏えいしたら、何よりも先にConsoleでキーを無効化します。環境が整ったら、curlとhttpxから、エンドポイント・3つの必須ヘッダー・JSONボディでMessages APIを呼び出しました。回答は、`type` が `text` のブロックから取り出しました。」

---

## ❌ 要修正（誤りの可能性が高い）

### クレーム65
**記述**: 「claude.aiの有料プランを契約していても、API利用料はそこに含まれません。」（L39）。関連する記述として「両者は別の製品で、契約も支払いも別々です」（L29）、POINT「claude.aiのサブスクリプションとClaude APIの利用料は、まったく別の契約です。」（L49）
**問題**: 現在は、claude.ai の Max・Ultra・Team プランに、毎月の Claude API クレジットが付いている。Console の組織を紐づけると、毎月そのクレジットが届き、API 利用料に充てられる。Max・Ultra・Team の読者がこの文を読むと、付いてくるクレジットを使わずに、自分でクレジットを購入してしまうおそれがある。Pro・無料・Enterprise プランには付かないので、「有料プランにはAPI利用料が含まれない」という一般論は、一部のプランでは誤りになる。
**正しい情報**: api-credits-for-subscribers「Claude Max, Ultra, and Team plans include monthly credits for the Claude API. To claim them, you link a Claude Console organization to your plan.」。月額は Max $100・Ultra $200・Team は1シートあたり Standard $20／Premium $100 で、合計の上限は $500。対象は Claude API・Managed Agents・Agent SDK・playground で、Claude Code は対象外。毎請求サイクルで失効し、繰り越しはない。「You don’t need to add a payment method to Claude Platform.」「Free, Pro, and Enterprise plans aren’t eligible.」。受け取ったクレジットは Console の Billing 画面の「Promotional credits」に表示される。購入したクレジットより先に消費される。
**修正案**:
- L39 の「claude.aiの有料プランを契約していても、API利用料はそこに含まれません。」を次に置き換える。
「claude.aiの料金とAPIの利用料は、別々に管理されます。ただし、Max・Ultra・Teamの各プランには、毎月一定額のAPIクレジットが付いています。執筆時点では、Maxが月100ドル、Ultraが月200ドル、Teamが最大月500ドルです。claude.aiの請求設定でConsoleの組織を紐づけると、このクレジットを受け取れます。ProプランやFreeプランには付きません。」（次の「逆に、APIを使うだけなら…必要ありません。」はそのまま残す）
- L29 の「両者は別の製品で、契約も支払いも別々です。」→「両者は別の製品で、支払いも別々に管理されます（一部のプランにはAPIクレジットが付きます）。」
- L49 POINT →「claude.aiのサブスクリプションとClaude APIの利用料は、別々に管理されます。本書のコードを動かすには、Claude ConsoleでAPI用のクレジット（前払いの利用残高）を用意する必要があります。Max・Ultra・Teamプランに付くクレジットも、受け取り先はConsoleの組織です。」
- （任意）L77 STEP 4 の末尾に「Max・Ultra・Teamプランのクレジットだけを使う場合は、支払い方法の登録は不要です。」を追記する。
- 第0章・第1章・Udemy・YouTube に同じ趣旨の記述（「サブスクにAPIは含まれない」）があれば、あわせて揃えること。金額とプラン名は変わりやすいので、公開前に一次情報で再確認すること。

---

## 総評

長文分割（56文）と用語統一で言い換えた文は、`git diff HEAD` で元の文と1文ずつ照合した。ほぼすべてで意味は保たれ、事実のずれはなかった。新たに入れた「Message Batches API ではわずかに超えることがある」は batch-processing の記述と一致し、参照先の第11章 L1070 とも整合している。エラー表の「残高不足400」は、公式のメッセージ文言と実際の400応答の報告の両方で裏付けがあり、「402＝支払い情報の問題」は errors.md と一致する。

最優先で直すべきなのは❌クレーム65。claude.ai の Max・Ultra・Team プランには現在、毎月の API クレジットが付いている。そのため「有料プランにAPI利用料は含まれない」という一般論は、これらのプランの読者を誤らせる（今朝の検証でも見落としていた）。⚠️クレーム62・64は、分割で生じた、または目立つようになった読み違いで、文言を少し直せば解消する。⚠️クレーム63は、一次情報に根拠のない断定を和らげる修正。Console の画面名・ボタン名・付属クレジットの金額は変わりやすいので、公開前に実画面と一次情報で確認することを推奨する。

---

## 対応（2026-11-08・再検証後）

- ❌ L39（L29・L49）: Max・Team プランの毎月の API クレジットについて追記した（公式ページで確認。Claude Code には使えない、請求期間の終わりに失効）。
- ⚠️ L658・L697: `raise_for_status()` の説明を「成功（2xx）でなければ例外」に直した。
- ⚠️ L106・L108: 根拠のない設計理由の文を削除し、「何本でも」を「必要なときにいつでも新しく」に変えた。
- ⚠️ L758: 「そのうえで」を「環境が整ったら、」に変えた。
