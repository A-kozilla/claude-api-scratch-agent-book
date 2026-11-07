# 図9.8 イラスト生成プロンプト

## イメージ設計メモ（全ツール共通）
- 描写対象: 横に3列のパネル。各列とも上に四角（指揮役）、下に四角（作業役）。1列目は下から上への1本の太い矢印の上に色付きの箱。2列目は下から上への細い矢印と、右側の色付きの箱（保管場所）を経由する矢印。3列目は中央に色付きのリスト状の箱があり、上下の四角とそれぞれ矢印でつながる。下部に横線と3つの短い説明枠
- 伝えたいこと: 受け渡し方には、結果をそのまま返す・置き場所に置いて場所だけ伝える・仕事の一覧を共有する、の3通りがある
- 書籍のトーン: 技術系
- 構図: 横3列の並列比較
- 色使い: グレースケール＋アクセント1色（青）。各列の中央の要素（荷物・保管場所・リスト）だけ青
- 含めないもの: テキスト・ラベル・複雑な背景

---

## ① ChatGPT Images 2.0（推奨・最初に試す）

日本語プロンプトがそのまま使える。会話で微調整可能。

ChatGPT の入力欄にそのまま貼り付ける:
```
以下の条件で書籍の挿絵イラストを1枚生成してください。

【描く内容】
横に3列のパネル。各列とも上に四角（指揮役）、下に四角（作業役）。1列目は下から上への1本の太い矢印の上に色付きの箱。2列目は下から上への細い矢印と、右側の色付きの箱（保管場所）を経由する矢印。3列目は中央に色付きのリスト状の箱があり、上下の四角とそれぞれ矢印でつながる。下部に横線と3つの短い説明枠

【表現したいこと】
受け渡し方には、結果をそのまま返す・置き場所に置いて場所だけ伝える・仕事の一覧を共有する、の3通りがある

【スタイル指定】
- フラットイラスト（アイコン風、影なし）
- グレースケールが基調。各列の中央の要素（荷物・保管場所・リスト）だけ青
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
Subject: Three side-by-side columns. Each column has a box at the top (conductor) and a box at the bottom (worker). Column 1: one thick upward arrow with a highlighted package on it. Column 2: a thin upward arrow plus a path through a highlighted storage box on the right side. Column 3: a highlighted list-like box in the middle connected by arrows to the top and bottom boxes. A horizontal line and three short caption frames at the bottom.
Concept: There are three ways to pass information: return the result directly, store it and share only its location, or share a common task list.
Style: flat design, icon style, no shadows, mostly grayscale with a blue accent only on the middle element of each column, white background, no text or labels.
Aspect ratio: 4:3
```

---

## ③ Gemini 画像生成（Imagen 3 搭載）／ 別名: Nano Banana 2

日本語OK・会話での修正可能。Google One AI Premium で利用可能。
gemini.google.com を開いて以下を貼り付ける:

```
次の条件で書籍の挿絵を1枚描いてください。

【描く内容】横に3列のパネル。各列とも上に四角（指揮役）、下に四角（作業役）。1列目は下から上への1本の太い矢印の上に色付きの箱。2列目は下から上への細い矢印と、右側の色付きの箱（保管場所）を経由する矢印。3列目は中央に色付きのリスト状の箱があり、上下の四角とそれぞれ矢印でつながる。下部に横線と3つの短い説明枠
【表現したいこと】受け渡し方には、結果をそのまま返す・置き場所に置いて場所だけ伝える・仕事の一覧を共有する、の3通りがある
【スタイル】フラットイラスト、アイコン風、影なし、
グレースケール中心（各列の中央の要素（荷物・保管場所・リスト）だけ青）、白い背景、テキスト・ラベルなし、横4:縦3
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
        Image.open(io.BytesIO(part.inline_data.data)).save("fig_9_8.png")
```

---

## ④ Midjourney

```
three side-by-side columns. Each column has a box at the top (conductor) and a box at the bottom (worker). Column 1: one thick upward arrow with a highlighted package on it. Column 2: a thin upward arrow plus a path through a highlighted storage box on the right side. Column 3: a highlighted list-like box in the middle connected by arrows to the top and bottom boxes. A horizontal line and three short caption frames at the bottom, flat illustration, icon design, minimal, mostly grayscale with a blue accent only on the middle element of each column, white background, technical book illustration --style raw --no photorealistic, text, labels, shadows --ar 4:3 --v 6
```

---

## ⑤ Stable Diffusion（ローカル・無料）

Positive:
```
flat design illustration, three side-by-side columns. Each column has a box at the top (conductor) and a box at the bottom (worker). Column 1: one thick upward arrow with a highlighted package on it. Column 2: a thin upward arrow plus a path through a highlighted storage box on the right side. Column 3: a highlighted list-like box in the middle connected by arrows to the top and bottom boxes. A horizontal line and three short caption frames at the bottom, minimal, icon style, mostly grayscale with a blue accent only on the middle element of each column, white background, no text
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
フラットイラスト、アイコン風、横に3列のパネル。各列とも上に四角（指揮役）、下に四角（作業役）。1列目は下から上への1本の太い矢印の上に色付きの箱。2列目は下から上への細い矢印と、右側の色付きの箱（保管場所）を経由する矢印。3列目は中央に色付きのリスト状の箱があり、上下の四角とそれぞれ矢印でつながる。下部に横線と3つの短い説明枠、
グレースケール中心（各列の中央の要素（荷物・保管場所・リスト）だけ青）、白い背景、テキストなし、技術書の挿絵スタイル
```

---

## ⑦ Imagen 2 / 3（Vertex AI・API・大量生成向け）

```
A flat illustration for a Japanese technical book. Three side-by-side columns. Each column has a box at the top (conductor) and a box at the bottom (worker). Column 1: one thick upward arrow with a highlighted package on it. Column 2: a thin upward arrow plus a path through a highlighted storage box on the right side. Column 3: a highlighted list-like box in the middle connected by arrows to the top and bottom boxes. A horizontal line and three short caption frames at the bottom.
Style: clean minimal flat design, mostly grayscale with a blue accent only on the middle element of each column, white background.
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
response.images[0].save("fig_9_8.png")
```
---

## ⑧ GensparkでNano bananaを使用

日本語プロンプトがそのまま使える。会話で微調整可能。

```
以下の条件で書籍の挿絵イラストを1枚生成してください。

【描く内容】
横に3列のパネル。各列とも上に四角（指揮役）、下に四角（作業役）。1列目は下から上への1本の太い矢印の上に色付きの箱。2列目は下から上への細い矢印と、右側の色付きの箱（保管場所）を経由する矢印。3列目は中央に色付きのリスト状の箱があり、上下の四角とそれぞれ矢印でつながる。下部に横線と3つの短い説明枠

【表現したいこと】
受け渡し方には、結果をそのまま返す・置き場所に置いて場所だけ伝える・仕事の一覧を共有する、の3通りがある

【スタイル指定】
- フラットイラスト（アイコン風、影なし）
- グレースケールが基調。各列の中央の要素（荷物・保管場所・リスト）だけ青
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

- [ ] 3つの方式の違い（何が受け渡されるか）が並べて比べられるか
- [ ] 書籍のトーンと合っているか（過剰な装飾・明るすぎる色がないか）
- [ ] 印刷時にグレースケールで潰れないか
- [ ] 横160mmに縮小しても内容が伝わるか
- [ ] ファイル名: `fig_9_8.png` で保存（同じIDの `fig_9_8.svg` がある場合はSVGが優先されるため、PNGを使うならSVGを削除する）
