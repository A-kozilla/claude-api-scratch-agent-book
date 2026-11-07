# /book-figures — 書籍 図制作指示書の生成＋自動生成

原稿の図マーカーをスキャンし、種類に応じて処理します：
- **概念図・フロー・構造図・比較** → 8ツール対応のAI画像生成プロンプトを生成
- **スクリーンショット** → 撮影手順書を生成
- **イラスト** → 8ツール対応のAI画像生成プロンプトを生成

引数 `$ARGUMENTS`: 章番号（省略時=全章処理）

---

## 前提確認
`book/03_manuscripts/` 配下にファイルが存在しない場合: 「先に `/book-chapter` を実行してください」と伝えて終了。

---

## Step 1: 図マーカーのスキャン

全原稿から以下のパターンを抽出する（現行フォーマット。全角`｜`区切り、Windowsのファイル名で使える文字のみで構成される）:
```
[FIG_X_Y｜種類｜自動生成フラグ｜タイトル｜内容の要点]
```
`X`は章番号・`Y`は章内の通し番号。表示用キャプションは「図X.Y: タイトル」の形式で機械的に生成する（`FIG_X_Y`のX・Yをピリオドで繋ぐ）。

以下の旧フォーマットも後方互換のため検出し、同様に処理する（見つけた場合は、可能であれば現行フォーマットへの書き換えも提案する）:
```
[図X.X: タイトル | 種類: ○○ | 内容: ○○ | 自動生成: 可/要確認/手動]   ← 旧・拡張フォーマット（半角記号を含みWindowsのファイル名に使えないため非推奨）
[図X.X: キャプション]                                              ← さらに古い簡易フォーマット
```

---

## Step 2: 種類別処理

### A. 概念図・フロー・構造図・比較 → AI画像生成プロンプトの生成（8ツール対応）

**出力**: `book/05_figures/chapter_XX/fig_X_X_prompt.md`

```markdown
# 図X.X イラスト生成プロンプト

## イメージ設計メモ（全ツール共通）
- 描写対象: [主役となるオブジェクト・人物・場面]
- 伝えたいこと: [この概念図・フロー・構造図・比較で読者に感じさせたい概念]
- 書籍のトーン: [技術系・ビジネス系・親しみやすい]
- 構図: [中央配置・左右対比・上下の流れ など]
- 色使い: グレースケール＋アクセント1色
- 含めないもの: テキスト・ラベル・複雑な背景

---

### B. スクリーンショット → 撮影手順書の生成

**出力**: `book/05_figures/chapter_XX/fig_X_X_capture.md`

```markdown
# 図X.X スクリーンショット撮影手順

## 撮影する画面
[内容フィールドから具体的な画面・状態を特定]

## 事前準備
- [ ] [必要なツール・アカウント]
- [ ] [特定の状態にする操作]

## 撮影手順
1. [操作手順]
2. [どの画面・どの状態でキャプチャするか]
3. macOS: Cmd+Shift+4 / Windows: Win+Shift+S

## サイズ・クロップ指示
- 推奨解像度: 1440×900以上（高DPIディスプレイ推奨）
- 書籍掲載サイズ: 横160mm（605px）に縮小
- クロップ範囲: [どこからどこまで切り取るか]
- 隠すもの: [URL・個人情報・バージョン番号等]

## 仕上げチェック
- [ ] 個人情報・機密情報が映り込んでいないか
- [ ] 拡大時に文字が読めるか
- [ ] ファイル名: fig_X_X_capture.png で保存
```

---

### C. イラスト → AI画像生成プロンプトの生成（8ツール対応）

**出力**: `book/05_figures/chapter_XX/fig_X_X_prompt.md`

```markdown
# 図X.X イラスト生成プロンプト

## イメージ設計メモ（全ツール共通）
- 描写対象: [主役となるオブジェクト・人物・場面]
- 伝えたいこと: [このイラストで読者に感じさせたい概念]
- 書籍のトーン: [技術系・ビジネス系・親しみやすい]
- 構図: [中央配置・左右対比・上下の流れ など]
- 色使い: グレースケール＋アクセント1色
- 含めないもの: テキスト・ラベル・複雑な背景

---

## ① ChatGPT Images 2.0（推奨・最初に試す）

日本語プロンプトがそのまま使える。会話で微調整可能。

ChatGPT の入力欄にそのまま貼り付ける:
```
以下の条件で書籍の挿絵イラストを1枚生成してください。

【描く内容】
[描写対象を日本語で具体的に]

【表現したいこと】
[伝えたいコンセプトを日本語で]

【スタイル指定】
- フラットイラスト（アイコン風、影なし）
- グレースケールと[アクセントカラー: 青/緑/オレンジ]の2色
- 白い背景 / テキスト・ラベルは一切含めない
- 技術書の挿絵として使えるプロフェッショナルな仕上がり

【比率】横4:縦3
```

修正の会話例: 「もう少しシンプルにして」「アクセントカラーを青から緑に」

---

## ② DALL-E 3（ChatGPT Plus / OpenAI API）

英語プロンプトの方が精度が高い。

```
Create a flat illustration for a Japanese technical book.
Subject: [内容の英語説明]
Concept: [伝えたいコンセプトの英語説明]
Style: flat design, icon style, no shadows, grayscale with single [色] accent, white background, no text or labels.
Aspect ratio: 4:3
```

---

## ③ Gemini 画像生成（Imagen 3 搭載）／ 別名: Nano Banana 2

日本語OK・会話での修正可能。Google One AI Premium で利用可能。
gemini.google.com を開いて以下を貼り付ける:

```
次の条件で書籍の挿絵を1枚描いてください。

【描く内容】[内容フィールドの日本語説明]
【表現したいこと】[伝えたいコンセプトの日本語説明]
【スタイル】フラットイラスト、アイコン風、影なし、
グレースケールと[色]の2色、白い背景、テキスト・ラベルなし、横4:縦3
```

Google AI Studio API（Python）:
```python
import google.generativeai as genai
from PIL import Image
import io

genai.configure(api_key="YOUR_API_KEY")
model = genai.GenerativeModel("gemini-2.0-flash-exp")
response = model.generate_content(
    contents="[上記プロンプトをそのまま使用]",
    generation_config={"response_modalities": ["image", "text"]}
)
for part in response.candidates[0].content.parts:
    if part.inline_data:
        Image.open(io.BytesIO(part.inline_data.data)).save("fig_X_X.png")
```

---

## ④ Midjourney

```
[内容の英語説明], flat illustration, icon design, minimal, grayscale with [色] accent, white background, technical book illustration --style raw --no photorealistic, text, labels, shadows --ar 4:3 --v 6
```

---

## ⑤ Stable Diffusion（ローカル・無料）

Positive:
```
flat design illustration, [内容の英語説明], minimal, icon style, grayscale with [色] accent, white background, no text
```
Negative:
```
photorealistic, 3d, complex background, shadows, gradients, text, watermark, blurry
```
推奨モデル: flat-2d-animerge / toonyou 系（書籍挿絵向き）

---

## ⑥ Adobe Firefly / Canva AI（商用利用安全）

日本語プロンプト:
```
フラットイラスト、アイコン風、[内容の日本語説明]、グレースケール＋[色]の2色、白い背景、テキストなし、技術書の挿絵スタイル
```

---

## ⑦ Imagen 2 / 3（Vertex AI・API・大量生成向け）

```
A flat illustration for a Japanese technical book. [内容の英語説明].
Style: clean minimal flat design, grayscale with [色] accent, white background.
No text, labels, or written characters. Aspect ratio 4:3.
```
Python SDK:
```python
from vertexai.vision_models import ImageGenerationModel
model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-001")
response = model.generate_images(
    prompt="[上記プロンプト]", number_of_images=4,
    aspect_ratio="4:3", safety_filter_level="block_some", person_generation="dont_allow"
)
response.images[0].save("fig_X_X.png")
```
---

## ⑧ GensparkでNano bananaを使用

日本語プロンプトがそのまま使える。会話で微調整可能。

ChatGPT の入力欄にそのまま貼り付ける:
```
以下の条件で書籍の挿絵イラストを1枚生成してください。

【描く内容】
[描写対象を日本語で具体的に]

【表現したいこと】
[伝えたいコンセプトを日本語で]

【スタイル指定】
- フラットイラスト（アイコン風、影なし）
- グレースケールと[アクセントカラー: 青/緑/オレンジ]の2色
- 白い背景 / テキスト・ラベルは一切含めない
- 技術書の挿絵として使えるプロフェッショナルな仕上がり

【比率】横4:縦3
```

修正の会話例: 「もう少しシンプルにして」「アクセントカラーを青から緑に」


---

## ツール選択ガイド

| 状況 | 推奨 |
|-----|-----|
| 手軽に始めたい・日本語で修正したい | ① ChatGPT Images 2.0 |
| Google サービスで統一したい | ③ Gemini（Nano Banana 2） |
| 商用利用・著作権クリアが必要 | ⑥ Adobe Firefly |
| 無料で何枚でも試したい | ⑤ Stable Diffusion |
| API・大量生成 | ⑦ Imagen 3（Vertex AI） |

---

## 生成後のチェック

- [ ] 書籍のトーンと合っているか（過剰な装飾・明るすぎる色がないか）
- [ ] 印刷時にグレースケールで潰れないか
- [ ] 横160mmに縮小しても内容が伝わるか
- [ ] ファイル名: `fig_X_X.png` で保存
```

---

## Step 3: 図一覧の生成

`book/05_figures/figures_list.md` に全図を整理する:

```markdown
# 書籍 図一覧

総図数: X点（SVG自動生成X点 / スクリーンショットX点 / イラストX点）

| 図番号 | タイトル | 種類 | 状態 | ファイル |
|------|--------|------|-----|--------|
| 図1.1 | [タイトル] | 概念図 | ✅ SVG生成済み | fig_1_1.svg |
| 図2.1 | [タイトル] | スクリーンショット | 📸 撮影待ち | fig_2_1_capture.md |
| 図3.1 | [タイトル] | イラスト | 🎨 プロンプト生成済み | fig_3_1_prompt.md |
```

---

## 完了後の案内

```
✅ 図の処理完了
総図数: X点
  SVG自動生成: X点
  スクリーンショット手順書: X点（fig_X_X_capture.md 参照）
  AIイラストプロンプト: X点（fig_X_X_prompt.md 参照）

進捗管理: book/05_figures/figures_list.md
```

SVG生成が完了したら自動埋め込みを提案する:

> SVG図の生成が完了しました。  
> `/book-embed` を実行すると原稿の図マーカー位置にSVGが自動で埋め込まれます。  
> スクリーンショット・AIイラストは画像ファイルを `book/05_figures/chapter_XX/` に  
> 配置後に `/book-embed` を再実行してください。
