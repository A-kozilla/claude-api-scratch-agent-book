# セットアップガイド

---

## このエージェントでできること

1つのトピックについて、**企画 → 構成 → 原稿執筆 → スライド/図制作** の全工程を21のコマンドで自動化します。

| メディア | 生成物 |
|--------|------|
| Udemy講座 | セクション構成・詳細目次・レクチャースクリプト・スライド（.pptx） |
| 書籍原稿 | 章立て・節別目次・章本文・図制作指示書（SVG自動生成/撮影手順/7ツールAIプロンプト） |
| YouTube台本 | ミニシリーズ構成・動画リスト・台本・スライド（.pptx）・視覚素材指示書 |

---

## ファイル構成

```
content-agent/
├── CLAUDE.md                          ← プロジェクトルール（コピー先に置く）
├── docs/
│   ├── setup-guide.md                 ← このファイル
│   └── usage-guide.md                 ← 使い方ガイド
├── references/
│   ├── style-guide.md                 ← 3メディア共通スタイルガイド（CLAUDE.mdから自動読み込み）
│   └── reference-doc.md               ← 参考情報（URL/参考ファイル一覧、CLAUDE.mdから自動読み込み）
└── .claude/
    ├── tools/
    │   └── book-format/               ← /book-format の変換スクリプトとデザインCSS
    │       ├── book_format.py
    │       ├── book_docx.py           ← Word(.docx) 出力
    │       └── book.css
    └── commands/                      ← カスタムスラッシュコマンド（21本）
        │
        ├── [共通]
        ├── plan.md                    /plan
        ├── check.md                   /check
        ├── export.md                  /export
        │
        ├── [Udemy講座]
        ├── structure.md               /structure
        ├── toc.md                     /toc
        ├── script.md                  /script
        ├── script-all.md              /script-all
        ├── slides.md                  /slides
        ├── slides-all.md              /slides-all
        │
        ├── [書籍原稿]
        ├── book-structure.md          /book-structure
        ├── book-toc.md                /book-toc
        ├── book-chapter.md            /book-chapter
        ├── book-all.md                /book-all
        ├── book-figures.md            /book-figures
        ├── book-embed.md              /book-embed
        ├── book-format.md             /book-format（Python + markdown / pygments / python-docx を使用）
        │
        └── [YouTube台本]
            ├── yt-structure.md        /yt-structure
            ├── yt-list.md             /yt-list
            ├── yt-script.md           /yt-script
            ├── yt-all.md              /yt-all
            ├── yt-slides.md           /yt-slides
            ├── yt-slides-all.md       /yt-slides-all
            └── yt-visuals.md          /yt-visuals
```

---

## セットアップ手順

### 手順1: 前提ツールの確認

```bash
claude --version
```

インストールされていない場合は https://docs.claude.ai/claude-code を参照してください。

### 手順2: 講座プロジェクトフォルダの作成

制作する講座ごとに新しいフォルダを作成します。

```bash
mkdir my-course-project
cd my-course-project
```

### 手順3: エージェントファイルをコピー

```bash
# コマンドフォルダをコピー（最重要）
cp -r /path/to/content-agent/.claude ./

# プロジェクトルールをコピー
cp /path/to/content-agent/CLAUDE.md ./
```

**コピー後のフォルダ構成を確認**:
```
my-course-project/
├── CLAUDE.md               ← ここにあること
└── .claude/
    └── commands/
        ├── plan.md         ← ここにあること
        ├── structure.md
        └── ...（22本すべて）
```

> ⚠️ **最もよくある間違い**: `.claude/commands/` フォルダが `my-course-project/` の
> **直下にない**とコマンドが一切認識されません。
> 
> ❌ 間違い: `my-course-project/content-agent/.claude/commands/`
> ✅ 正しい: `my-course-project/.claude/commands/`

### 手順4: Claude Code を起動

```bash
claude
```

### 手順5: 動作確認

Claude Code の入力欄に以下を入力します:

```
/check
```

以下のように返ってくれば正常です:
```
まだファイルが見つかりません。'/plan [タイトル]' から始めてください。
```

コマンドが認識されない場合は手順3のフォルダ構成を再確認してください。

---

## 複数の講座を並行管理する場合

講座ごとに別フォルダを作り、それぞれにエージェントファイルをコピーします。

```bash
# 講座A用
mkdir course-a
cp -r content-agent/.claude course-a/
cp content-agent/CLAUDE.md course-a/

# 講座B用
mkdir course-b
cp -r content-agent/.claude course-b/
cp content-agent/CLAUDE.md course-b/
```

各フォルダで `claude` を起動すれば独立したプロジェクトとして管理できます。

---

## 使い始めるときの最短手順

```bash
# 1. プロジェクト作成
mkdir my-udemy-course && cd my-udemy-course
cp -r /path/to/content-agent/.claude ./
cp /path/to/content-agent/CLAUDE.md ./

# 2. Claude Code 起動
claude

# 3. 企画から開始（Claude Code 内で）
/plan "Dify完全実践講座 — ノーコードでAIアプリを作る"
```

詳しい使い方は `docs/usage-guide.md` を参照してください。
