# 図9.1 イラスト生成プロンプト

## イメージ設計メモ（全ツール共通）
- 描写対象: 左から右へ高くなる3段の階段状の四角。いちばん高い右端の段だけ色付き。下部に左から右への長い矢印
- 伝えたいこと: 単純な形から始め、必要なときだけ複雑さと自律性の高い段階へ上がる
- 書籍のトーン: 技術系
- 構図: 左下から右上へ上がる階段と下部の軸矢印
- 色使い: グレースケール＋アクセント1色（青）。右端の最上段だけ青
- 含めないもの: テキスト・ラベル・複雑な背景

---

## ① ChatGPT Images 2.0（推奨・最初に試す）

日本語プロンプトがそのまま使える。会話で微調整可能。

ChatGPT の入力欄にそのまま貼り付ける:
```
以下の条件で書籍の挿絵イラストを1枚生成してください。

【描く内容】
左から右へ高くなる3段の階段状の四角。いちばん高い右端の段だけ色付き。下部に左から右への長い矢印

【表現したいこと】
単純な形から始め、必要なときだけ複雑さと自律性の高い段階へ上がる

【スタイル指定】
- フラットイラスト（アイコン風、影なし）
- グレースケールが基調。右端の最上段だけ青
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
Subject: Three rectangular steps rising like a staircase from left to right. Only the tallest step on the right is highlighted. A long left-to-right arrow along the bottom.
Concept: Start with the simplest form and climb to more complex, more autonomous stages only when needed.
Style: flat design, icon style, no shadows, mostly grayscale with a blue accent only on the tallest right step, white background, no text or labels.
Aspect ratio: 4:3
```

---

## ③ Gemini 画像生成（Imagen 3 搭載）／ 別名: Nano Banana 2

日本語OK・会話での修正可能。Google One AI Premium で利用可能。
gemini.google.com を開いて以下を貼り付ける:

```
次の条件で書籍の挿絵を1枚描いてください。

【描く内容】左から右へ高くなる3段の階段状の四角。いちばん高い右端の段だけ色付き。下部に左から右への長い矢印
【表現したいこと】単純な形から始め、必要なときだけ複雑さと自律性の高い段階へ上がる
【スタイル】フラットイラスト、アイコン風、影なし、
グレースケール中心（右端の最上段だけ青）、白い背景、テキスト・ラベルなし、横4:縦3
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
        Image.open(io.BytesIO(part.inline_data.data)).save("fig_9_1.png")
```

---

## ④ Midjourney

```
three rectangular steps rising like a staircase from left to right. Only the tallest step on the right is highlighted. A long left-to-right arrow along the bottom, flat illustration, icon design, minimal, mostly grayscale with a blue accent only on the tallest right step, white background, technical book illustration --style raw --no photorealistic, text, labels, shadows --ar 4:3 --v 6
```

---

## ⑤ Stable Diffusion（ローカル・無料）

Positive:
```
flat design illustration, three rectangular steps rising like a staircase from left to right. Only the tallest step on the right is highlighted. A long left-to-right arrow along the bottom, minimal, icon style, mostly grayscale with a blue accent only on the tallest right step, white background, no text
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
フラットイラスト、アイコン風、左から右へ高くなる3段の階段状の四角。いちばん高い右端の段だけ色付き。下部に左から右への長い矢印、
グレースケール中心（右端の最上段だけ青）、白い背景、テキストなし、技術書の挿絵スタイル
```

---

## ⑦ Imagen 2 / 3（Vertex AI・API・大量生成向け）

```
A flat illustration for a Japanese technical book. Three rectangular steps rising like a staircase from left to right. Only the tallest step on the right is highlighted. A long left-to-right arrow along the bottom.
Style: clean minimal flat design, mostly grayscale with a blue accent only on the tallest right step, white background.
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
response.images[0].save("fig_9_1.png")
```
---

## ⑧ GensparkでNano bananaを使用

日本語プロンプトがそのまま使える。会話で微調整可能。

```
以下の条件で書籍の挿絵イラストを1枚生成してください。

【描く内容】
左から右へ高くなる3段の階段状の四角。いちばん高い右端の段だけ色付き。下部に左から右への長い矢印

【表現したいこと】
単純な形から始め、必要なときだけ複雑さと自律性の高い段階へ上がる

【スタイル指定】
- フラットイラスト（アイコン風、影なし）
- グレースケールが基調。右端の最上段だけ青
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

- [ ] 右へ行くほど段が上がる＝複雑さと自律性が増すことが伝わるか
- [ ] 書籍のトーンと合っているか（過剰な装飾・明るすぎる色がないか）
- [ ] 印刷時にグレースケールで潰れないか
- [ ] 横160mmに縮小しても内容が伝わるか
- [ ] ファイル名: `fig_9_1.png` で保存（同じIDの `fig_9_1.svg` がある場合はSVGが優先されるため、PNGを使うならSVGを削除する）
