# 図7.2 イラスト生成プロンプト

## イメージ設計メモ（全ツール共通）
- 描写対象: 横に長い1本の帯。左端の一部だけが色付きで、残りの大部分は薄いグレー。その色付き部分を下に拡大したもう1本の帯があり、小さな区画2つ・大きな区画1つ・小さな区画1つに分かれ、大きな区画の右端に縦の太線が立っている
- 伝えたいこと: 大きな容量があっても、上限よりかなり手前に使う量の線を引き、残りを安全のための余白として空けておくという予算の考え方
- 書籍のトーン: 技術系
- 構図: 上下2段の横帯（上が全体、下が拡大）と拡大を示す補助線
- 色使い: グレースケール＋アクセント1色（青）。使う範囲と拡大帯の大きな区画だけ青
- 含めないもの: テキスト・ラベル・複雑な背景

---

## ① ChatGPT Images 2.0（推奨・最初に試す）

日本語プロンプトがそのまま使える。会話で微調整可能。

ChatGPT の入力欄にそのまま貼り付ける:
```
以下の条件で書籍の挿絵イラストを1枚生成してください。

【描く内容】
横に長い1本の帯。左端の一部だけが色付きで、残りの大部分は薄いグレー。その色付き部分を下に拡大したもう1本の帯があり、小さな区画2つ・大きな区画1つ・小さな区画1つに分かれ、大きな区画の右端に縦の太線が立っている

【表現したいこと】
大きな容量があっても、上限よりかなり手前に使う量の線を引き、残りを安全のための余白として空けておくという予算の考え方

【スタイル指定】
- フラットイラスト（アイコン風、影なし）
- グレースケールが基調。使う範囲と拡大帯の大きな区画だけ青
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
Subject: A long horizontal bar where only a small left portion is colored and the rest is light gray. Below it, a zoomed-in second bar expands that small portion into two small segments, one large segment and one small segment, with a thick vertical line at the right edge of the large segment.
Concept: Even with a huge capacity, draw a budget line well before the limit and keep the rest as a safety margin.
Style: flat design, icon style, no shadows, mostly grayscale with a blue accent only on the used portion and the large zoomed segment, white background, no text or labels.
Aspect ratio: 4:3
```

---

## ③ Gemini 画像生成（Imagen 3 搭載）／ 別名: Nano Banana 2

日本語OK・会話での修正可能。Google One AI Premium で利用可能。
gemini.google.com を開いて以下を貼り付ける:

```
次の条件で書籍の挿絵を1枚描いてください。

【描く内容】横に長い1本の帯。左端の一部だけが色付きで、残りの大部分は薄いグレー。その色付き部分を下に拡大したもう1本の帯があり、小さな区画2つ・大きな区画1つ・小さな区画1つに分かれ、大きな区画の右端に縦の太線が立っている
【表現したいこと】大きな容量があっても、上限よりかなり手前に使う量の線を引き、残りを安全のための余白として空けておくという予算の考え方
【スタイル】フラットイラスト、アイコン風、影なし、
グレースケール中心（使う範囲と拡大帯の大きな区画だけ青）、白い背景、テキスト・ラベルなし、横4:縦3
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
        Image.open(io.BytesIO(part.inline_data.data)).save("fig_7_2.png")
```

---

## ④ Midjourney

```
a long horizontal bar where only a small left portion is colored and the rest is light gray. Below it, a zoomed-in second bar expands that small portion into two small segments, one large segment and one small segment, with a thick vertical line at the right edge of the large segment, flat illustration, icon design, minimal, mostly grayscale with a blue accent only on the used portion and the large zoomed segment, white background, technical book illustration --style raw --no photorealistic, text, labels, shadows --ar 4:3 --v 6
```

---

## ⑤ Stable Diffusion（ローカル・無料）

Positive:
```
flat design illustration, a long horizontal bar where only a small left portion is colored and the rest is light gray. Below it, a zoomed-in second bar expands that small portion into two small segments, one large segment and one small segment, with a thick vertical line at the right edge of the large segment, minimal, icon style, mostly grayscale with a blue accent only on the used portion and the large zoomed segment, white background, no text
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
フラットイラスト、アイコン風、横に長い1本の帯。左端の一部だけが色付きで、残りの大部分は薄いグレー。その色付き部分を下に拡大したもう1本の帯があり、小さな区画2つ・大きな区画1つ・小さな区画1つに分かれ、大きな区画の右端に縦の太線が立っている、
グレースケール中心（使う範囲と拡大帯の大きな区画だけ青）、白い背景、テキストなし、技術書の挿絵スタイル
```

---

## ⑦ Imagen 2 / 3（Vertex AI・API・大量生成向け）

```
A flat illustration for a Japanese technical book. A long horizontal bar where only a small left portion is colored and the rest is light gray. Below it, a zoomed-in second bar expands that small portion into two small segments, one large segment and one small segment, with a thick vertical line at the right edge of the large segment.
Style: clean minimal flat design, mostly grayscale with a blue accent only on the used portion and the large zoomed segment, white background.
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
response.images[0].save("fig_7_2.png")
```
---

## ⑧ GensparkでNano bananaを使用

日本語プロンプトがそのまま使える。会話で微調整可能。

```
以下の条件で書籍の挿絵イラストを1枚生成してください。

【描く内容】
横に長い1本の帯。左端の一部だけが色付きで、残りの大部分は薄いグレー。その色付き部分を下に拡大したもう1本の帯があり、小さな区画2つ・大きな区画1つ・小さな区画1つに分かれ、大きな区画の右端に縦の太線が立っている

【表現したいこと】
大きな容量があっても、上限よりかなり手前に使う量の線を引き、残りを安全のための余白として空けておくという予算の考え方

【スタイル指定】
- フラットイラスト（アイコン風、影なし）
- グレースケールが基調。使う範囲と拡大帯の大きな区画だけ青
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

- [ ] 全体のうち使う範囲が小さく、残りが安全マージンであることが伝わるか
- [ ] 書籍のトーンと合っているか（過剰な装飾・明るすぎる色がないか）
- [ ] 印刷時にグレースケールで潰れないか
- [ ] 横160mmに縮小しても内容が伝わるか
- [ ] ファイル名: `fig_7_2.png` で保存（同じIDの `fig_7_2.svg` がある場合はSVGが優先されるため、PNGを使うならSVGを削除する）
