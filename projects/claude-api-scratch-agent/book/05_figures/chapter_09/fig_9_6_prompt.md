# 図9.6 イラスト生成プロンプト

## イメージ設計メモ（全ツール共通）
- 描写対象: 左上と右上に2つの四角があり、左から右へ矢印。右の四角の下にひし形、ひし形の下に色付きの四角（終了）。ひし形から左へ矢印が出て左側の色付きの四角へ、そこから上の左の四角へ戻る矢印。全体で時計回りの輪になる
- 伝えたいこと: 作る役と採点する役を分け、基準を満たすまで指摘をもとに作り直しを繰り返す
- 書籍のトーン: 技術系
- 構図: 時計回りのループと、下へ抜ける出口
- 色使い: グレースケール＋アクセント1色（青）。出口の四角と、左の改善点の四角だけ青
- 含めないもの: テキスト・ラベル・複雑な背景

---

## ① ChatGPT Images 2.0（推奨・最初に試す）

日本語プロンプトがそのまま使える。会話で微調整可能。

ChatGPT の入力欄にそのまま貼り付ける:
```
以下の条件で書籍の挿絵イラストを1枚生成してください。

【描く内容】
左上と右上に2つの四角があり、左から右へ矢印。右の四角の下にひし形、ひし形の下に色付きの四角（終了）。ひし形から左へ矢印が出て左側の色付きの四角へ、そこから上の左の四角へ戻る矢印。全体で時計回りの輪になる

【表現したいこと】
作る役と採点する役を分け、基準を満たすまで指摘をもとに作り直しを繰り返す

【スタイル指定】
- フラットイラスト（アイコン風、影なし）
- グレースケールが基調。出口の四角と、左の改善点の四角だけ青
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
Subject: Two boxes at the top-left and top-right with an arrow from left to right. Below the right box is a diamond, and below the diamond a highlighted exit box. From the diamond an arrow goes left to a highlighted box on the left, which points back up to the top-left box, forming a clockwise loop.
Concept: Separate the maker from the grader and keep revising with feedback until the standard is met.
Style: flat design, icon style, no shadows, mostly grayscale with a blue accent only on the exit box and the left feedback box, white background, no text or labels.
Aspect ratio: 4:3
```

---

## ③ Gemini 画像生成（Imagen 3 搭載）／ 別名: Nano Banana 2

日本語OK・会話での修正可能。Google One AI Premium で利用可能。
gemini.google.com を開いて以下を貼り付ける:

```
次の条件で書籍の挿絵を1枚描いてください。

【描く内容】左上と右上に2つの四角があり、左から右へ矢印。右の四角の下にひし形、ひし形の下に色付きの四角（終了）。ひし形から左へ矢印が出て左側の色付きの四角へ、そこから上の左の四角へ戻る矢印。全体で時計回りの輪になる
【表現したいこと】作る役と採点する役を分け、基準を満たすまで指摘をもとに作り直しを繰り返す
【スタイル】フラットイラスト、アイコン風、影なし、
グレースケール中心（出口の四角と、左の改善点の四角だけ青）、白い背景、テキスト・ラベルなし、横4:縦3
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
        Image.open(io.BytesIO(part.inline_data.data)).save("fig_9_6.png")
```

---

## ④ Midjourney

```
two boxes at the top-left and top-right with an arrow from left to right. Below the right box is a diamond, and below the diamond a highlighted exit box. From the diamond an arrow goes left to a highlighted box on the left, which points back up to the top-left box, forming a clockwise loop, flat illustration, icon design, minimal, mostly grayscale with a blue accent only on the exit box and the left feedback box, white background, technical book illustration --style raw --no photorealistic, text, labels, shadows --ar 4:3 --v 6
```

---

## ⑤ Stable Diffusion（ローカル・無料）

Positive:
```
flat design illustration, two boxes at the top-left and top-right with an arrow from left to right. Below the right box is a diamond, and below the diamond a highlighted exit box. From the diamond an arrow goes left to a highlighted box on the left, which points back up to the top-left box, forming a clockwise loop, minimal, icon style, mostly grayscale with a blue accent only on the exit box and the left feedback box, white background, no text
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
フラットイラスト、アイコン風、左上と右上に2つの四角があり、左から右へ矢印。右の四角の下にひし形、ひし形の下に色付きの四角（終了）。ひし形から左へ矢印が出て左側の色付きの四角へ、そこから上の左の四角へ戻る矢印。全体で時計回りの輪になる、
グレースケール中心（出口の四角と、左の改善点の四角だけ青）、白い背景、テキストなし、技術書の挿絵スタイル
```

---

## ⑦ Imagen 2 / 3（Vertex AI・API・大量生成向け）

```
A flat illustration for a Japanese technical book. Two boxes at the top-left and top-right with an arrow from left to right. Below the right box is a diamond, and below the diamond a highlighted exit box. From the diamond an arrow goes left to a highlighted box on the left, which points back up to the top-left box, forming a clockwise loop.
Style: clean minimal flat design, mostly grayscale with a blue accent only on the exit box and the left feedback box, white background.
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
response.images[0].save("fig_9_6.png")
```
---

## ⑧ GensparkでNano bananaを使用

日本語プロンプトがそのまま使える。会話で微調整可能。

```
以下の条件で書籍の挿絵イラストを1枚生成してください。

【描く内容】
左上と右上に2つの四角があり、左から右へ矢印。右の四角の下にひし形、ひし形の下に色付きの四角（終了）。ひし形から左へ矢印が出て左側の色付きの四角へ、そこから上の左の四角へ戻る矢印。全体で時計回りの輪になる

【表現したいこと】
作る役と採点する役を分け、基準を満たすまで指摘をもとに作り直しを繰り返す

【スタイル指定】
- フラットイラスト（アイコン風、影なし）
- グレースケールが基調。出口の四角と、左の改善点の四角だけ青
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

- [ ] 改善のループと、合格で抜ける出口の両方が見えるか
- [ ] 書籍のトーンと合っているか（過剰な装飾・明るすぎる色がないか）
- [ ] 印刷時にグレースケールで潰れないか
- [ ] 横160mmに縮小しても内容が伝わるか
- [ ] ファイル名: `fig_9_6.png` で保存（同じIDの `fig_9_6.svg` がある場合はSVGが優先されるため、PNGを使うならSVGを削除する）
