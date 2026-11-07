# 図1.2 イラスト生成プロンプト

> 図1.2: 3要素と本書のコードの対応
> 自動生成のSVG（`fig_1_2.svg`）が正式な図です。このプロンプトは、同じ概念を挿絵として描き直したい場合の代替案です。

## イメージ設計メモ（全ツール共通）
- 描写対象: 左に3つのアイコン（頭・道具・循環矢印）、右に3枚の書類（コードファイル）が並び、線でそれぞれ結ばれている
- 伝えたいこと: 抽象的な3要素が、具体的なファイルと関数に1対1で対応する
- 書籍のトーン: 技術系（落ち着いた・親しみやすい）
- 構図: 左右に3段ずつ並べて線で接続
- 色使い: グレースケール＋アクセント1色（青 #2b6cb0）
- 含めないもの: テキスト・ラベル・複雑な背景

---

## ① ChatGPT Images 2.0（推奨・最初に試す）

日本語プロンプトがそのまま使える。会話で微調整可能。

ChatGPT の入力欄にそのまま貼り付ける:
```text
以下の条件で書籍の挿絵イラストを1枚生成してください。

【描く内容】
左に3つのアイコン（頭・道具・循環矢印）、右に3枚の書類（コードファイル）が並び、線でそれぞれ結ばれている

【表現したいこと】
抽象的な3要素が、具体的なファイルと関数に1対1で対応する

【スタイル指定】
- フラットイラスト（アイコン風、影なし）
- グレースケールと青の2色
- 白い背景 / テキスト・ラベルは一切含めない
- 技術書の挿絵として使えるプロフェッショナルな仕上がり

【比率】横4:縦3
```

修正の会話例: 「もう少しシンプルにして」「アクセントカラーをもう少し濃い青に」

---

## ② DALL-E 3（ChatGPT Plus / OpenAI API）

英語プロンプトの方が精度が高い。

```text
Create a flat illustration for a Japanese technical book.
Subject: three icons on the left (head, tool, circular arrow) each connected by a line to one of three document files on the right.
Concept: each abstract element maps one-to-one to a concrete code file.
Style: flat design, icon style, no shadows, grayscale with single blue accent, white background, no text or labels.
Aspect ratio: 4:3
```

---

## ③ Gemini 画像生成（Imagen 3 搭載）／ 別名: Nano Banana 2

日本語OK・会話での修正可能。Google One AI Premium で利用可能。
gemini.google.com を開いて以下を貼り付ける:

```text
次の条件で書籍の挿絵を1枚描いてください。

【描く内容】左に3つのアイコン（頭・道具・循環矢印）、右に3枚の書類（コードファイル）が並び、線でそれぞれ結ばれている
【表現したいこと】抽象的な3要素が、具体的なファイルと関数に1対1で対応する
【スタイル】フラットイラスト、アイコン風、影なし、
グレースケールと青の2色、白い背景、テキスト・ラベルなし、横4:縦3
```

Google AI Studio API（Python）:
```python
# generate_fig_1_2.py
import google.generativeai as genai  # Gemini API のライブラリ
from PIL import Image  # 画像の保存に使う
import io  # バイト列を画像として読むために使う

genai.configure(api_key="YOUR_API_KEY")  # 実際のキーは環境変数などから読む
model = genai.GenerativeModel("gemini-2.0-flash-exp")  # 画像生成に対応したモデル
response = model.generate_content(
    contents="[上記プロンプトをそのまま使用]",
    generation_config={"response_modalities": ["image", "text"]}  # 画像を返すよう指定
)
for part in response.candidates[0].content.parts:  # 返ってきたパーツから画像を探す
    if part.inline_data:
        Image.open(io.BytesIO(part.inline_data.data)).save("fig_1_2.png")  # PNGで保存
```

---

## ④ Midjourney

```text
three icons on the left (head, tool, circular arrow) each connected by a line to one of three document files on the right, flat illustration, icon design, minimal, grayscale with blue accent, white background, technical book illustration --style raw --no photorealistic, text, labels, shadows --ar 4:3 --v 6
```

---

## ⑤ Stable Diffusion（ローカル・無料）

Positive:
```text
flat design illustration, three icons on the left (head, tool, circular arrow) each connected by a line to one of three document files on the right, minimal, icon style, grayscale with blue accent, white background, no text
```
Negative:
```text
photorealistic, 3d, complex background, shadows, gradients, text, watermark, blurry
```
推奨モデル: flat-2d-animerge / toonyou 系（書籍挿絵向き）

---

## ⑥ Adobe Firefly / Canva AI（商用利用安全）

日本語プロンプト:
```text
フラットイラスト、アイコン風、左に3つのアイコン（頭・道具・循環矢印）、右に3枚の書類（コードファイル）が並び、線でそれぞれ結ばれている、グレースケール＋青の2色、白い背景、テキストなし、技術書の挿絵スタイル
```

---

## ⑦ Imagen 2 / 3（Vertex AI・API・大量生成向け）

```text
A flat illustration for a Japanese technical book. three icons on the left (head, tool, circular arrow) each connected by a line to one of three document files on the right.
Style: clean minimal flat design, grayscale with blue accent, white background.
No text, labels, or written characters. Aspect ratio 4:3.
```
Python SDK:
```python
# generate_fig_1_2_vertex.py
from vertexai.vision_models import ImageGenerationModel  # Vertex AI の画像生成モデル
model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-001")  # Imagen 3 を読み込む
response = model.generate_images(
    prompt="[上記プロンプト]", number_of_images=4,  # 候補を4枚生成
    aspect_ratio="4:3", safety_filter_level="block_some", person_generation="dont_allow"
)
response.images[0].save("fig_1_2.png")  # 1枚目を保存
```

---

## ⑧ GensparkでNano bananaを使用

日本語プロンプトがそのまま使える。会話で微調整可能。

Genspark の入力欄にそのまま貼り付ける:
```text
以下の条件で書籍の挿絵イラストを1枚生成してください。

【描く内容】
左に3つのアイコン（頭・道具・循環矢印）、右に3枚の書類（コードファイル）が並び、線でそれぞれ結ばれている

【表現したいこと】
抽象的な3要素が、具体的なファイルと関数に1対1で対応する

【スタイル指定】
- フラットイラスト（アイコン風、影なし）
- グレースケールと青の2色
- 白い背景 / テキスト・ラベルは一切含めない
- 技術書の挿絵として使えるプロフェッショナルな仕上がり

【比率】横4:縦3
```

修正の会話例: 「もう少しシンプルにして」「アクセントカラーをもう少し濃い青に」

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
- [ ] ファイル名: `fig_1_2.png` で保存
