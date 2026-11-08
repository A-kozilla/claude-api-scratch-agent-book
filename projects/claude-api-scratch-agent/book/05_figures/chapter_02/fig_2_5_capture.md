# 図2.5 スクリーンショット撮影手順

> 図2.5: VS Codeのインタープリター選択（第2章 2.2節「VS Codeを準備する」STEP 3）

## 撮影する画面
VS Code（Visual Studio Code）で `agent-from-scratch` フォルダーを開き、コマンドパレットから「Python: Select Interpreter」（Python: インタープリターを選択）を実行した直後の一覧。`.venv` の中のPython（Windows: `.venv\Scripts\python.exe` / macOS・Linux: `.venv/bin/python`、多くの場合「推奨」表示付き）が見えている状態。

## 事前準備
- [ ] VS Code と Microsoft 製の「Python」拡張機能をインストール済み
- [ ] `uv init agent-from-scratch --python 3.12 --no-package` と `uv add httpx python-dotenv` を実行済み（`.venv` が存在する）
- [ ] VS Code で `agent-from-scratch` フォルダーを開き、ワークスペースを信頼済み
- [ ] 余計な拡張機能の通知・タブを閉じ、配色テーマは印刷で見やすいライトテーマ（例: Light Modern）にする
- [ ] プロジェクトは同期フォルダー外（例: `C:\dev\agent-from-scratch`）に置く

## 撮影手順
1. `Ctrl+Shift+P`（macOSは `Cmd+Shift+P`）でコマンドパレットを開く
2. 「Python: Select Interpreter」を入力して実行する
3. 一覧に `.venv` のPython（Python 3.12.x）が表示された状態で撮影する
4. （任意）選択後、画面右下のステータスバーに `.venv` の表示が出た状態も予備として撮影する
5. macOS: Cmd+Shift+4 / Windows: Win+Shift+S

## サイズ・クロップ指示
- 推奨解像度: 1440×900以上（高DPIディスプレイ推奨）
- 書籍掲載サイズ: 横160mm（605px）に縮小
- クロップ範囲: コマンドパレットのドロップダウン全体と、その下のエクスプローラー（`.venv`・`pyproject.toml` などのファイル名）が少し見える範囲
- 隠すもの（必須）:
  - **ユーザー名を含むパス**（例: `C:\Users\<ユーザー名>\...`、`/Users/<ユーザー名>/...`）。インタープリター一覧のパス表示とウィンドウタイトルを確認する
  - **メールアドレス・アカウント名**（左下のアカウントアイコンや Settings Sync の表示）
  - **組織名**（リモート接続・GitHub アカウント表示などに出る場合）
  - **APIキー**（`.env` を開いたタブやエディタが映り込まないようにする。映った場合は必ずぼかす）

## 仕上げチェック
- [ ] ユーザー名・メールアドレス・組織名・APIキーが映り込んでいないか
- [ ] `.venv` の Python であることが一覧で読み取れるか
- [ ] 拡大時に文字が読めるか
- [ ] ファイル名: fig_2_5_capture.png で保存
