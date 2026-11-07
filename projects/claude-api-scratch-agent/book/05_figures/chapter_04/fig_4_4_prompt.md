# 図4.4 イラスト生成プロンプト

> 自動生成SVG: `fig_4_4.svg`（図4.4: ストリーミングのイベントの流れ）。本ファイルは、SVGの代わりにイラスト版を使いたい場合のプロンプトです。

## イメージ設計メモ（全ツール共通）
- 描写対象: 縦に流れるベルトコンベア。先頭に空の封筒、中ほどに「開始の札・小さな断片の束・終了の札」の3つのパーツが繰り返し流れる区間（区間を囲むループ矢印付き）、最後に封をした封筒とゴールの旗
- 伝えたいこと: ストリーミングのイベントは決まった順番で届き、ブロックごとの3点セットを繰り返して完了する
- 書籍のトーン: 技術系
- 構図: 上から下への流れ＋中央にループ
- 色使い: グレースケール＋アクセント1色（青）
- 含めないもの: テキスト・ラベル・複雑な背景

---

## ① ChatGPT Images 2.0（推奨・最初に試す）

日本語プロンプトがそのまま使える。会話で微調整可能。

ChatGPT の入力欄にそのまま貼り付ける:
```
以下の条件で書籍の挿絵イラストを1枚生成してください。

【描く内容】
縦に流れるベルトコンベア。先頭に空の封筒、中ほどに「開始の札・小さな断片の束・終了の札」の3つのパーツが繰り返し流れる区間（区間を囲むループ矢印付き）、最後に封をした封筒とゴールの旗

【表現したいこと】
ストリーミングのイベントは決まった順番で届き、ブロックごとの3点セットを繰り返して完了する

【スタイル指定】
- フラットイラスト（アイコン風、影なし）
- グレースケールと青の2色
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
Subject: A vertical conveyor belt. At the top an empty envelope; in the middle a repeating section with three parts (a start tag, a bundle of small fragments, an end tag) surrounded by a loop arrow; at the bottom a sealed envelope and a finish flag.
Concept: Streaming events arrive in a fixed order, repeating a three-part set for each content block until completion.
Style: flat design, icon style, no shadows, grayscale with single blue accent, white background, no text or labels.
Aspect ratio: 4:3
```

---

## ③ Gemini 画像生成（Imagen 3 搭載）／ 別名: Nano Banana 2

日本語OK・会話での修正可能。Google One AI Premium で利用可能。
gemini.google.com を開いて以下を貼り付ける:

```
次の条件で書籍の挿絵を1枚描いてください。

【描く内容】縦に流れるベルトコンベア。先頭に空の封筒、中ほどに「開始の札・小さな断片の束・終了の札」の3つのパーツが繰り返し流れる区間（区間を囲むループ矢印付き）、最後に封をした封筒とゴールの旗
【表現したいこと】ストリーミングのイベントは決まった順番で届き、ブロックごとの3点セットを繰り返して完了する
【スタイル】フラットイラスト、アイコン風、影なし、
グレースケールと青の2色、白い背景、テキスト・ラベルなし、横4:縦3
```

Google AI Studio API（Python）:
```python
# gen_fig_4_4.py
import google.generativeai as genai  # Gemini の SDK
from PIL import Image  # 画像の保存用
import io

genai.configure(api_key="YOUR_API_KEY")  # 自分のAPIキーに置き換える
model = genai.GenerativeModel("gemini-2.0-flash-exp")
response = model.generate_content(
    contents="[上記プロンプトをそのまま使用]",
    generation_config={"response_modalities": ["image", "text"]}
)
# 画像のパートだけを取り出して保存する
for part in response.candidates[0].content.parts:
    if part.inline_data:
        Image.open(io.BytesIO(part.inline_data.data)).save("fig_4_4.png")
```

---

## ④ Midjourney

```
A vertical conveyor belt. At the top an empty envelope; in the middle a repeating section with three parts (a start tag, a bundle of small fragments, an end tag) surrounded by a loop arrow; at the bottom a sealed envelope and a finish flag, flat illustration, icon design, minimal, grayscale with blue accent, white background, technical book illustration --style raw --no photorealistic, text, labels, shadows --ar 4:3 --v 6
```

---

## ⑤ Stable Diffusion（ローカル・無料）

Positive:
```
flat design illustration, A vertical conveyor belt. At the top an empty envelope; in the middle a repeating section with three parts (a start tag, a bundle of small fragments, an end tag) surrounded by a loop arrow; at the bottom a sealed envelope and a finish flag, minimal, icon style, grayscale with blue accent, white background, no text
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
フラットイラスト、アイコン風、縦に流れるベルトコンベア。先頭に空の封筒、中ほどに「開始の札・小さな断片の束・終了の札」の3つのパーツが繰り返し流れる区間（区間を囲むループ矢印付き）、最後に封をした封筒とゴールの旗、グレースケール＋青の2色、白い背景、テキストなし、技術書の挿絵スタイル
```

---

## ⑦ Imagen 2 / 3（Vertex AI・API・大量生成向け）

```
A flat illustration for a Japanese technical book. A vertical conveyor belt. At the top an empty envelope; in the middle a repeating section with three parts (a start tag, a bundle of small fragments, an end tag) surrounded by a loop arrow; at the bottom a sealed envelope and a finish flag.
Style: clean minimal flat design, grayscale with blue accent, white background.
No text, labels, or written characters. Aspect ratio 4:3.
```
Python SDK:
```python
# gen_fig_4_4_vertex.py
from vertexai.vision_models import ImageGenerationModel  # Vertex AI の画像生成
model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-001")
response = model.generate_images(
    prompt="[上記プロンプト]", number_of_images=4,
    aspect_ratio="4:3", safety_filter_level="block_some", person_generation="dont_allow"
)
response.images[0].save("fig_4_4.png")  # 1枚目を保存する
```
---

## ⑧ GensparkでNano bananaを使用

日本語プロンプトがそのまま使える。会話で微調整可能。

Genspark の入力欄にそのまま貼り付ける:
```
以下の条件で書籍の挿絵イラストを1枚生成してください。

【描く内容】
縦に流れるベルトコンベア。先頭に空の封筒、中ほどに「開始の札・小さな断片の束・終了の札」の3つのパーツが繰り返し流れる区間（区間を囲むループ矢印付き）、最後に封をした封筒とゴールの旗

【表現したいこと】
ストリーミングのイベントは決まった順番で届き、ブロックごとの3点セットを繰り返して完了する

【スタイル指定】
- フラットイラスト（アイコン風、影なし）
- グレースケールと青の2色
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
- [ ] ファイル名: `fig_4_4.png` で保存
