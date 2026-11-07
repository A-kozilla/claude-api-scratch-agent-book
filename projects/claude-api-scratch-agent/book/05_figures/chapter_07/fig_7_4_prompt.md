# 図7.4 イラスト生成プロンプト

## イメージ設計メモ（全ツール共通）
- 描写対象: 横一列に並んだ6枚のカード。2枚目と3枚目、4枚目と5枚目がそれぞれ上部の括弧でペアとして結ばれている。4枚目と5枚目の間に点線の縦線（危険）、3枚目と4枚目の間に太い実線の縦線（安全）があり、点線から実線へ左向きの矢印が伸びる
- 伝えたいこと: 対になっている2枚の間で切るとペアが壊れるため、切る位置を前へずらしてペアごと残す
- 書籍のトーン: 技術系
- 構図: 横一列のカードと2本の縦の切断線
- 色使い: グレースケール＋アクセント1色（青）。安全な切断線と、残す側の3枚だけ青
- 含めないもの: テキスト・ラベル・複雑な背景

---

## ① ChatGPT Images 2.0（推奨・最初に試す）

日本語プロンプトがそのまま使える。会話で微調整可能。

ChatGPT の入力欄にそのまま貼り付ける:
```
以下の条件で書籍の挿絵イラストを1枚生成してください。

【描く内容】
横一列に並んだ6枚のカード。2枚目と3枚目、4枚目と5枚目がそれぞれ上部の括弧でペアとして結ばれている。4枚目と5枚目の間に点線の縦線（危険）、3枚目と4枚目の間に太い実線の縦線（安全）があり、点線から実線へ左向きの矢印が伸びる

【表現したいこと】
対になっている2枚の間で切るとペアが壊れるため、切る位置を前へずらしてペアごと残す

【スタイル指定】
- フラットイラスト（アイコン風、影なし）
- グレースケールが基調。安全な切断線と、残す側の3枚だけ青
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
Subject: Six cards in a horizontal row. Cards 2-3 and cards 4-5 are each joined by a bracket above as pairs. A dashed vertical line between cards 5 and 4 marks a bad cut, a thick solid line between cards 3 and 4 marks a safe cut, with a left-pointing arrow from the dashed line to the solid line.
Concept: Cutting between a paired couple breaks the pair, so the cut position is moved earlier to keep the pair together.
Style: flat design, icon style, no shadows, mostly grayscale with a blue accent only on the safe cut line and the three kept cards, white background, no text or labels.
Aspect ratio: 4:3
```

---

## ③ Gemini 画像生成（Imagen 3 搭載）／ 別名: Nano Banana 2

日本語OK・会話での修正可能。Google One AI Premium で利用可能。
gemini.google.com を開いて以下を貼り付ける:

```
次の条件で書籍の挿絵を1枚描いてください。

【描く内容】横一列に並んだ6枚のカード。2枚目と3枚目、4枚目と5枚目がそれぞれ上部の括弧でペアとして結ばれている。4枚目と5枚目の間に点線の縦線（危険）、3枚目と4枚目の間に太い実線の縦線（安全）があり、点線から実線へ左向きの矢印が伸びる
【表現したいこと】対になっている2枚の間で切るとペアが壊れるため、切る位置を前へずらしてペアごと残す
【スタイル】フラットイラスト、アイコン風、影なし、
グレースケール中心（安全な切断線と、残す側の3枚だけ青）、白い背景、テキスト・ラベルなし、横4:縦3
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
        Image.open(io.BytesIO(part.inline_data.data)).save("fig_7_4.png")
```

---

## ④ Midjourney

```
six cards in a horizontal row. Cards 2-3 and cards 4-5 are each joined by a bracket above as pairs. A dashed vertical line between cards 5 and 4 marks a bad cut, a thick solid line between cards 3 and 4 marks a safe cut, with a left-pointing arrow from the dashed line to the solid line, flat illustration, icon design, minimal, mostly grayscale with a blue accent only on the safe cut line and the three kept cards, white background, technical book illustration --style raw --no photorealistic, text, labels, shadows --ar 4:3 --v 6
```

---

## ⑤ Stable Diffusion（ローカル・無料）

Positive:
```
flat design illustration, six cards in a horizontal row. Cards 2-3 and cards 4-5 are each joined by a bracket above as pairs. A dashed vertical line between cards 5 and 4 marks a bad cut, a thick solid line between cards 3 and 4 marks a safe cut, with a left-pointing arrow from the dashed line to the solid line, minimal, icon style, mostly grayscale with a blue accent only on the safe cut line and the three kept cards, white background, no text
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
フラットイラスト、アイコン風、横一列に並んだ6枚のカード。2枚目と3枚目、4枚目と5枚目がそれぞれ上部の括弧でペアとして結ばれている。4枚目と5枚目の間に点線の縦線（危険）、3枚目と4枚目の間に太い実線の縦線（安全）があり、点線から実線へ左向きの矢印が伸びる、
グレースケール中心（安全な切断線と、残す側の3枚だけ青）、白い背景、テキストなし、技術書の挿絵スタイル
```

---

## ⑦ Imagen 2 / 3（Vertex AI・API・大量生成向け）

```
A flat illustration for a Japanese technical book. Six cards in a horizontal row. Cards 2-3 and cards 4-5 are each joined by a bracket above as pairs. A dashed vertical line between cards 5 and 4 marks a bad cut, a thick solid line between cards 3 and 4 marks a safe cut, with a left-pointing arrow from the dashed line to the solid line.
Style: clean minimal flat design, mostly grayscale with a blue accent only on the safe cut line and the three kept cards, white background.
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
response.images[0].save("fig_7_4.png")
```
---

## ⑧ GensparkでNano bananaを使用

日本語プロンプトがそのまま使える。会話で微調整可能。

```
以下の条件で書籍の挿絵イラストを1枚生成してください。

【描く内容】
横一列に並んだ6枚のカード。2枚目と3枚目、4枚目と5枚目がそれぞれ上部の括弧でペアとして結ばれている。4枚目と5枚目の間に点線の縦線（危険）、3枚目と4枚目の間に太い実線の縦線（安全）があり、点線から実線へ左向きの矢印が伸びる

【表現したいこと】
対になっている2枚の間で切るとペアが壊れるため、切る位置を前へずらしてペアごと残す

【スタイル指定】
- フラットイラスト（アイコン風、影なし）
- グレースケールが基調。安全な切断線と、残す側の3枚だけ青
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

- [ ] ペアを分断する位置と、ペアごと残す位置の違いがわかるか
- [ ] 書籍のトーンと合っているか（過剰な装飾・明るすぎる色がないか）
- [ ] 印刷時にグレースケールで潰れないか
- [ ] 横160mmに縮小しても内容が伝わるか
- [ ] ファイル名: `fig_7_4.png` で保存（同じIDの `fig_7_4.svg` がある場合はSVGが優先されるため、PNGを使うならSVGを削除する）
