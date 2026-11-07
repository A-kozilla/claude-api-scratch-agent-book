# コンテンツ自動生成エージェント v3.0

1つの企画から **Udemy講座・書籍原稿・YouTube台本** を一貫して自動生成します。

## スタイルガイド

@references/style-guide.md

@references/reference-doc.md

3メディア共通の文体ルール・禁止表現・技術用語表記ルールは上記に集約されている。関連URLやローカル参考ファイルの一覧は`references/reference-doc.md`に集約されている。いずれもこのCLAUDE.mdの読み込み時点でセッション全体に適用済みのため、各コマンド側で`references/style-guide.md`・`references/reference-doc.md`を個別に読み込み直す必要はない。

---

## コマンド一覧

### 共通
| コマンド | 説明 |
|---------|------|
| `/plan "タイトル"` | 企画書・ターゲット分析を生成（最初に必ず実行） |
| `/check` | 全メディアの進捗を確認 |
| `/export [udemy\|book\|youtube\|all]` | 完成物を1ファイルに結合 |

### Udemy講座
| コマンド | 説明 |
|---------|------|
| `/structure` | セクション・レクチャー構成を設計 |
| `/toc` | 時間付き詳細目次を生成 |
| `/script [S] [L]` | 指定レクチャーのスクリプト生成（例: `/script 1 2`） |
| `/script-all` | 全レクチャーを一括生成 |
| `/slides [S] [L]` | スクリプトからスライドデッキ（.pptx）を生成 |
| `/slides-all` | 全スライドを一括生成 |

### 書籍原稿
| コマンド | 説明 |
|---------|------|
| `/book-structure` | 章立て・節構成を設計 |
| `/book-toc` | 節別詳細目次を生成 |
| `/book-chapter [N]` | 指定章の本文執筆（0=はじめに） |
| `/book-all` | 全章を一括執筆 |
| `/book-figures [N]` | 図を種類別に処理（SVG自動生成・撮影手順・AIプロンプト） |
| `/book-embed [N]` | 原稿の図マーカーに図を自動埋め込み（06_final/ に出力） |
| `/book-embed-all` | 全章の図を一括埋め込み |
| `/book-format [md\|html\|pdf\|docx\|all] [A4\|A5] [章番号]` | 原稿を飾り付き原稿に変換（Markdown / HTML+CSS / PDF / Word、用紙サイズ指定可）。HTML/PDFのデザインは `format-template/`、原稿の記法は `references/book-markup.md` |

### YouTube台本
| コマンド | 説明 |
|---------|------|
| `/yt-structure` | ミニシリーズ単位のシリーズ構成を設計 |
| `/yt-list [N]` | 動画リスト＋メタ情報（N=ミニシリーズ番号、省略で全体） |
| `/yt-script [N]` | 指定動画の台本執筆 |
| `/yt-all [N]` | 全台本を一括生成（Nでミニシリーズ絞り込み可） |
| `/yt-slides [N]` | 指定動画のスライドデッキ（.pptx）を生成 |
| `/yt-slides-all [N]` | 全動画のスライドを一括生成 |
| `/yt-visuals [N]` | 視覚素材指示書を生成（テロップ・画面録画・図解スライド指示） |

### ファクトチェック・品質保証
| コマンド | 説明 |
|---------|------|
| `/factcheck [メディア S L\|N]` | 指定コンテンツをWeb検索でファクトチェック |
| `/verify-code [メディア N]` | コードブロックを実際に実行してバグ検出 |
| `/factcheck-all` | 全コンテンツを一括ファクトチェック（公開前の最終確認） |

> ⚠️ **ファクトチェックの限界**: これらのコマンドはAI+Web検索による自動検証です。
> 外部API依存のコード・環境依存の手順は完全には検証できません。
> **公開前に必ず人間による最終確認を行ってください。**


| コマンド | 説明 |
|---------|------|
| `/script-parallel` | スクリプトを複数のサブエージェントで並列生成（`/script-all`の約3〜5倍速） |
| `/review [メディア]` | 生成済みコンテンツを専用サブエージェントが横断レビュー |

> **サブエージェントについて**: 上記2コマンドは独立したClaudeインスタンスを複数起動します。
> 各サブエージェントは独自のコンテキストを持つため、品質の安定性が向上します。
> Claude Codeのレート制限に注意してください。

---

```
projects/{project-slug}/
├── 00_planning/
│   ├── concept.md
│   └── target_audience.md
├── udemy/
│   ├── 01_structure/  (outline.md, learning_goals.md)
│   ├── 02_toc/        (toc.md)
│   ├── 03_scripts/    (section_XX/lecture_XX.md)
│   └── 04_slides/     (section_XX/lecture_XX.pptx, lecture_XX_map.md)
├── book/
│   ├── book_info.md   (表紙・ヘッダーの書誌情報 / /book-structure が concept.md から生成、/book-format が使用)
│   ├── 01_structure/  (chapter_outline.md, chapter_goals.md)
│   ├── 02_toc/        (toc.md)
│   ├── 03_manuscripts/(chapter_XX.md)
│   ├── 05_figures/    (chapter_XX/fig_X_X.svg 等)
│   ├── 06_final/      (chapter_XX.md 図埋め込み済み / /book-embed の出力)
│   └── 07_publish/    (A4|A5/ markdown・html・pdf・word / /book-format の出力)
└── youtube/
    ├── 01_structure/  (series_outline.md)
    ├── 02_list/       (video_list.md)
    ├── 03_scripts/    (video_XX.md)
    ├── 04_visuals/    (video_XX_visuals.md)
    └── 05_slides/     (video_XX.pptx, video_XX_map.md)
```

---

## 品質基準

### 文体（メディア別）
| メディア | 文体 | 1文の目安 |
|--------|------|---------|
| Udemy | ですます調・口語体 | 40〜60字 |
| 書籍 | ですます調・読書体 | 50字以内 |
| YouTube | くだけた口語体 | 20〜30字 |

### スクリプト・原稿の文字数基準
**「ファイル全体の文字数」ではなく「会話文・本文の文字数」で品質を判断する。**
ヘッダー・コードブロック・メタ情報は話さない文字のためカウントしない。

| 種類 | 会話文目標 | 推定時間 |
|-----|---------|---------|
| Udemyレクチャー（講義型） | 1,600〜2,000字 | 8〜10分 |
| Udemyレクチャー（ハンズオン型） | 1,800〜2,400字 | 10〜13分 |
| YouTube動画（解説） | 750〜1,200字 | 5〜8分 |
| YouTube動画（ハンズオン） | 1,200〜1,800字 | 8〜12分 |
| 書籍1章 | 10,000〜20,000字 | 推定20〜30ページ |

### 各コンテンツの必須要素
- **Udemy**: 導入（前回振り返り+今回ゴール宣言）/ 3段階説明（概念→具体例→重要性）/ まとめ3点 / 次回橋渡し
- **書籍**: 「この章で学ぶこと」/ 節頭の問いかけ / 図解指示 / 章末まとめ / 次章橋渡し
- **YouTube**: 冒頭30秒フック / 2〜3分ごとのパターン割り込み / タイムスタンプ / CTA / エンドカード

### フェーズの進行順序
```
/plan → 各メディアの /xxx-structure → /xxx-toc → /xxx-script（章・動画）
```
前フェーズのファイルが存在しない場合は、先に完了するよう案内すること。
