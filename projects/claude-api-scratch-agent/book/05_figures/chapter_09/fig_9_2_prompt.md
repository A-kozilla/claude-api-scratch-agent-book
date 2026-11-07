# 図9.2 イラスト生成プロンプト

## イメージ設計メモ（全ツール共通）
- 描写対象: 6つの横長の角丸四角が左上から右下へ斜めに階段状に並ぶ。上の5つは1つの点線の大きな枠に囲まれ、最後の1つ（右下）だけ枠の外にあり色付き。下部に左から右への長い矢印
- 伝えたいこと: 代表的なパターンは、流れをコードが決めるものからモデルが決めるものへと一列に並べて整理できる
- 書籍のトーン: 技術系
- 構図: 左上から右下への斜めの並びと下部の軸矢印
- 色使い: グレースケール＋アクセント1色（青）。右下の1つだけ青
- 含めないもの: テキスト・ラベル・複雑な背景

---

## ① ChatGPT Images 2.0（推奨・最初に試す）

日本語プロンプトがそのまま使える。会話で微調整可能。

ChatGPT の入力欄にそのまま貼り付ける:
```
以下の条件で書籍の挿絵イラストを1枚生成してください。

【描く内容】
6つの横長の角丸四角が左上から右下へ斜めに階段状に並ぶ。上の5つは1つの点線の大きな枠に囲まれ、最後の1つ（右下）だけ枠の外にあり色付き。下部に左から右への長い矢印

【表現したいこと】
代表的なパターンは、流れをコードが決めるものからモデルが決めるものへと一列に並べて整理できる

【スタイル指定】
- フラットイラスト（アイコン風、影なし）
- グレースケールが基調。右下の1つだけ青
- 白い背景 / テキスト・ラベルは一切含めない
- 技術書の挿絵として使えるプロフェッショナルな仕上がり

【比率】横4:縦3
```

修正の会話例: 「もう少しシンプルにして」「矢印をもっと太く」

---

## ② DALL-E 3（ChatGPT Plus / OpenAI API）

英語プロンプトの方が精度が高い。

```
Create a flat illustration for a Japanese technical book.
Subject: Six wide rounded boxes arranged diagonally like steps from top-left to bottom-right. The first five are enclosed by one large dashed frame; the last one at the bottom-right sits outside the frame and is highlighted. A long left-to-right arrow along the bottom.
Concept: Common design patterns can be lined up from those where code decides the flow to those where the model decides it.
Style: flat design, icon style, no shadows, mostly grayscale with a blue accent only on the last box at the bottom-right, white background, no text or labels.
Aspect ratio: 4:3
```

---

## ③ Gemini 画像生成（Imagen 3 搭載）／ 別名: Nano Banana 2

日本語OK・会話での修正可能。Google One AI Premium で利用可能。
gemini.google.com を開いて以下を貼り付ける:

```
次の条件で書籍の挿絵を1枚描いてください。

【描く内容】6つの横長の角丸四角が左上から右下へ斜めに階段状に並ぶ。上の5つは1つの点線の大きな枠に囲まれ、最後の1つ（右下）だけ枠の外にあり色付き。下部に左から右への長い矢印
【表現したいこと】代表的なパターンは、流れをコードが決めるものからモデルが決めるものへと一列に並べて整理できる
【スタイル】フラットイラスト、アイコン風、影なし、
グレースケール中心（右下の1つだけ青）、白い背景、テキスト・ラベルなし、横4:縦3
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
        Image.open(io.BytesIO(part.inline_data.data)).save("fig_9_2.png")
```

---

## ④ Midjourney

```
six wide rounded boxes arranged diagonally like steps from top-left to bottom-right. The first five are enclosed by one large dashed frame; the last one at the bottom-right sits outside the frame and is highlighted. A long left-to-right arrow along the bottom, flat illustration, icon design, minimal, mostly grayscale with a blue accent only on the last box at the bottom-right, white background, technical book illustration --style raw --no photorealistic, text, labels, shadows --ar 4:3 --v 6
```

---

## ⑤ Stable Diffusion（ローカル・無料）

Positive:
```
flat design illustration, six wide rounded boxes arranged diagonally like steps from top-left to bottom-right. The first five are enclosed by one large dashed frame; the last one at the bottom-right sits outside the frame and is highlighted. A long left-to-right arrow along the bottom, minimal, icon style, mostly grayscale with a blue accent only on the last box at the bottom-right, white background, no text
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
フラットイラスト、アイコン風、6つの横長の角丸四角が左上から右下へ斜めに階段状に並ぶ。上の5つは1つの点線の大きな枠に囲まれ、最後の1つ（右下）だけ枠の外にあり色付き。下部に左から右への長い矢印、
グレースケール中心（右下の1つだけ青）、白い背景、テキストなし、技術書の挿絵スタイル
```

---

## ⑦ Imagen 2 / 3（Vertex AI・API・大量生成向け）

```
A flat illustration for a Japanese technical book. Six wide rounded boxes arranged diagonally like steps from top-left to bottom-right. The first five are enclosed by one large dashed frame; the last one at the bottom-right sits outside the frame and is highlighted. A long left-to-right arrow along the bottom.
Style: clean minimal flat design, mostly grayscale with a blue accent only on the last box at the bottom-right, white background.
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
response.images[0].save("fig_9_2.png")
```
---

## ⑧ GensparkでNano bananaを使用

日本語プロンプトがそのまま使える。会話で微調整可能。

```
以下の条件で書籍の挿絵イラストを1枚生成してください。

【描く内容】
6つの横長の角丸四角が左上から右下へ斜めに階段状に並ぶ。上の5つは1つの点線の大きな枠に囲まれ、最後の1つ（右下）だけ枠の外にあり色付き。下部に左から右への長い矢印

【表現したいこと】
代表的なパターンは、流れをコードが決めるものからモデルが決めるものへと一列に並べて整理できる

【スタイル指定】
- フラットイラスト（アイコン風、影なし）
- グレースケールが基調。右下の1つだけ青
- 白い背景 / テキスト・ラベルは一切含めない
- 技術書の挿絵として使えるプロフェッショナルな仕上がり

【比率】横4:縦3
```

修正の会話例: 「もう少しシンプルにして」「矢印をもっと太く」

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

- [ ] 5つのまとまりと1つの独立した要素、右へ行くほど自律的という並びが伝わるか
- [ ] 書籍のトーンと合っているか（過剰な装飾・明るすぎる色がないか）
- [ ] 印刷時にグレースケールで潰れないか
- [ ] 横160mmに縮小しても内容が伝わるか
- [ ] ファイル名: `fig_9_2.png` で保存（同じIDの `fig_9_2.svg` がある場合はSVGが優先されるため、PNGを使うならSVGを削除する）
