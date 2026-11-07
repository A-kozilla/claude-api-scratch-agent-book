# /book-embed — 書籍原稿への図自動埋め込み

原稿内の図マーカーをスキャンし、対応する図ファイルが存在すれば実際の図に置き換えます。
埋め込み済みの最終原稿を `book/06_final/` に出力します（元原稿は変更しません）。

引数 `$ARGUMENTS`: 章番号（省略時=全章）

---

## 前提確認

- `book/03_manuscripts/` 配下にファイルが存在しない場合: 「先に `/book-chapter` を実行してください」と伝えて終了。
- `book/05_figures/` が存在しない場合: 「先に `/book-figures` を実行してください」と伝えて終了。

---

## Step 1: 図ファイルのスキャン

`book/05_figures/` 配下の全ファイルを収集して対応マップを作成する。

```
book/05_figures/
├── chapter_01/
│   ├── fig_1_1.svg          ← SVG（自動生成済み）
│   ├── fig_1_2_capture.png  ← スクリーンショット（人間が配置）
│   └── fig_1_3.png          ← AIイラスト（人間が配置）
├── chapter_02/
│   └── fig_2_1.svg
```

対応マップ（例）:
```
図1.1 → chapter_01/fig_1_1.svg        ✅ 埋め込み可能
図1.2 → chapter_01/fig_1_2_capture.png ✅ 埋め込み可能
図1.3 → chapter_01/fig_1_3.png         ✅ 埋め込み可能
図2.1 → chapter_02/fig_2_1.svg        ✅ 埋め込み可能
図2.2 → 未存在                          ⏳ プレースホルダーを維持
```

**同じIDでSVGとPNG/JPGの両方が存在する場合**: `fig_X_Y.svg`を優先して埋め込む（PNG/JPGは無視する）。SVGはベクター形式のため、印刷（高解像度出力）にも電子書籍（画面拡大）にも劣化なく対応できる一方、PNG/JPGは解像度依存のラスター形式のため、印刷用途では画質面で不利になりやすいことが理由。AI画像生成ツールで作った挿絵をSVGより優先して使いたい場合は、対応する`fig_X_Y.svg`を`book/05_figures/chapter_XX/`から削除してからPNG/JPGを配置し、`/book-embed`を再実行すること。

---

## Step 2: 原稿内の図マーカーを置き換え

以下の規則で図マーカーを対応する埋め込みコードに置き換える。

### A. SVGファイルの場合 → SVGをインライン埋め込み

**元のマーカー**:
```
[FIG_2_3｜概念図｜可｜Dockerのアーキテクチャ｜3層構造]
```

表示用キャプション「図2.3: Dockerのアーキテクチャ」は、`FIG_2_3`のX=2・Y=3をピリオドで繋いだ「図2.3」＋マーカー中のタイトルから機械的に組み立てる。

**置き換え後（SVGインライン）**:
```html
<figure id="fig-2-3">
  <!-- SVGファイルの内容をそのまま展開 -->
  <svg width="605" height="280" viewBox="0 0 605 280" ...>
    [SVGの中身]
  </svg>
  <figcaption>図2.3: Dockerのアーキテクチャ</figcaption>
</figure>
```

SVGをインラインにする理由: 印刷・電子書籍いずれにも対応し、外部ファイル参照のリンク切れを防ぐため。

### B. PNG/JPG/WEBPファイルの場合 → imgタグで埋め込み

**元のマーカー**:
```
[FIG_5_2｜スクリーンショット｜手｜設定画面｜Difyのモデルプロバイダー設定画面]
```

**置き換え後**:
```html
<figure id="fig-5-2">
  <img src="../05_figures/chapter_05/fig_5_2_capture.png"
       alt="図5.2: 設定画面のスクリーンショット"
       width="605"
       style="max-width:100%; border:1px solid #e0e0e0; border-radius:4px;">
  <figcaption>図5.2: 設定画面のスクリーンショット</figcaption>
</figure>
```

### C. 図ファイルが存在しない場合 → スタイル付きプレースホルダー

**置き換え後**:
```html
<figure id="fig-X-X" class="figure-placeholder">
  <div style="
    width:605px; height:200px;
    border:2px dashed #ccc;
    border-radius:8px;
    display:flex; flex-direction:column;
    align-items:center; justify-content:center;
    background:#f9f9f9; color:#999;
    font-family:sans-serif; font-size:14px;
  ">
    <div style="font-size:32px; margin-bottom:8px;">📷</div>
    <div>図X.X: [タイトル]</div>
    <div style="font-size:12px; margin-top:4px;">[種類] — 入稿待ち</div>
  </div>
  <figcaption>図X.X: [タイトル]（入稿待ち）</figcaption>
</figure>
```

---

## Step 3: 最終原稿の生成

埋め込み済みの原稿を `book/06_final/chapter_XX.md` に保存する（**元の `03_manuscripts/` は変更しない**）。

**ディレクトリ構造**:
```
book/
├── 03_manuscripts/
│   └── chapter_01.md      ← 元原稿（図マーカーのまま・変更しない）
└── 06_final/
    ├── chapter_01.md      ← 図埋め込み済み最終版
    ├── chapter_02.md
    └── figures_status.md  ← 埋め込み状況レポート
```

---

## Step 4: 埋め込み状況レポートの生成

`book/06_final/figures_status.md` に全図の埋め込み状況を保存する:

```markdown
# 図の埋め込み状況レポート

最終更新: YYYY-MM-DD

## サマリー
- 総図数: X点
- ✅ 埋め込み済み: X点
- ⏳ 入稿待ち: X点

## 詳細

| 図番号 | タイトル | 種類 | 状態 | ファイル |
|------|--------|------|-----|--------|
| 図1.1 | [タイトル] | 概念図 | ✅ SVG埋め込み済み | fig_1_1.svg |
| 図1.2 | [タイトル] | スクリーンショット | ✅ PNG埋め込み済み | fig_1_2_capture.png |
| 図2.2 | [タイトル] | イラスト | ⏳ 入稿待ち | — |

## 入稿待ちの図（公開前に必要）

以下の図ファイルを `book/05_figures/chapter_XX/` に配置してから
再度 `/book-embed` を実行してください：

- `book/05_figures/chapter_02/fig_2_2.png` — 図2.2: [タイトル]
```

---

## 完了後の案内

```
✅ 図の埋め込み完了

埋め込み済み: X点 / 入稿待ち: X点

最終原稿: book/06_final/
埋め込み状況: book/06_final/figures_status.md

入稿待ちの図がある場合:
  1. 対応する画像ファイルを book/05_figures/chapter_XX/ に配置
  2. 再度 /book-embed を実行すると自動的に埋め込まれます
```

---

## ファイル配置のルール

入稿待ちの図を配置する際のファイル名規則:

| 種類 | ファイル名の規則 | 例 |
|-----|--------------|---|
| スクリーンショット | `fig_X_X_capture.png` | `fig_1_2_capture.png` |
| AIイラスト | `fig_X_X.png` または `fig_X_X.jpg` | `fig_1_3.png` |
| 手動作成SVG | `fig_X_X.svg` | `fig_2_2.svg` |

ファイルを配置後、`/book-embed` を再実行すると自動的に検出して埋め込みます。

**注意**: `fig_X_X.svg`と`fig_X_X.png`（またはjpg）が同じIDで両方存在する場合は、SVGが優先され、PNG/JPGは埋め込まれない（Step 1参照）。AI生成イラストをSVGより優先したい場合は、先にSVGを削除すること。
