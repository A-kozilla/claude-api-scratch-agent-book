# /check — 全メディア進捗確認

全メディアの制作進捗を一覧表示します。迷ったときはまずこれを実行。

---

## チェック項目

`projects/` 配下を走査して以下を確認・表示する。

**共通フェーズ**
- `00_planning/concept.md` の存在
- `00_planning/target_audience.md` の存在

**Udemyブランチ**
- `udemy/01_structure/outline.md` の存在（総レクチャー数を集計）
- `udemy/02_toc/toc.md` の存在（推定総時間を集計）
- `udemy/03_scripts/` のファイル数 vs 総レクチャー数
- `udemy/04_slides/` のファイル数 vs 総レクチャー数

**書籍ブランチ**
- `book/01_structure/chapter_outline.md` の存在（総章数を集計）
- `book/02_toc/toc.md` の存在（推定総ページを集計）
- `book/03_manuscripts/` のファイル数 vs 総章数
- `book/05_figures/figures_list.md` の存在と進捗（✅/📸/🎨の内訳）

**YouTubeブランチ**
- `youtube/01_structure/series_outline.md` の存在（総動画数・ミニシリーズ数を集計）
- `youtube/02_list/video_list.md` の存在
- `youtube/03_scripts/` のファイル数 vs 総動画数
- `youtube/04_visuals/` のファイル数 vs 総動画数
- `youtube/05_slides/` のファイル数 vs 総動画数

---

## 表示フォーマット

```
================================================
  コンテンツ生成エージェント 進捗レポート
================================================
プロジェクト: [concept.mdから取得]
確認日: YYYY-MM-DD

【共通】
  企画書 (concept.md)      ✅ 完了
  ターゲット分析            ✅ 完了

【Udemy講座】
  構成設計 /structure      ✅ 完了（Xセクション / Xレクチャー）
  詳細目次 /toc            ✅ 完了（推定X時間X分）
  スクリプト /script       🔄 X / X本（X%）
  スライド /slides         🔄 X / X本（X%）

  未生成スクリプト:
    - Section 02, Lecture 03: [タイトル]

【書籍原稿】
  章立て /book-structure   ✅ 完了（X章）
  詳細目次 /book-toc       ✅ 完了（推定Xページ）
  原稿執筆 /book-chapter   🔄 X / X章（X%）
  図制作 /book-figures     🔄 X点完了（SVG:X / 撮影待ち:X / AIプロンプト:X）

【YouTube台本】
  シリーズ構成 /yt-structure ✅ 完了（X本 / ミニシリーズX個）
  動画リスト /yt-list        ✅ 完了
  台本執筆 /yt-script        🔄 X / X本（X%）
  スライド /yt-slides        🔄 X / X本（X%）
  視覚素材 /yt-visuals       ⏳ 未着手

  未生成台本:
    - ミニシリーズ2, 動画08: [タイトル]

------------------------------------------------
次のアクション候補:
  /script 2 3      → Udemy: 次の未生成スクリプト
  /slides 2 3      → Udemy: 対応スライドを生成
  /book-chapter 4  → 書籍: 第4章を執筆
  /book-figures 3  → 書籍: 第3章の図を処理
  /yt-script 8     → YouTube: 次の未生成台本
  /yt-slides 8     → YouTube: 対応スライドを生成
================================================
```

ファイルが1つも存在しない場合:
```
まだファイルが見つかりません。'/plan [タイトル]' から始めてください。
```
