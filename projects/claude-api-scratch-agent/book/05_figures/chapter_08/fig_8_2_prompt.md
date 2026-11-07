# 図8.2 イラスト生成プロンプト

## イメージ設計メモ（全ツール共通）
- 描写対象: 上段に横一列の3つの角丸四角（矢印でつながる）と、右端から左端へ上を回って戻る色付きの矢印。上段の右端の四角から下へ矢印が伸び、下段の点線の大きな枠につながる。枠の中には4つの四角があり、そのうち2つは上下の矢印で往復している
- 伝えたいこと: 親のツール実行の中で、もう1本の独立したループが丸ごと動き、終わると結果だけが親に戻る
- 書籍のトーン: 技術系
- 構図: 上下2段（上が親のループ、下が子のループの枠）
- 色使い: グレースケール＋アクセント1色（青）。下の枠、子ループの2つの四角、戻りの矢印だけ青
- 含めないもの: テキスト・ラベル・複雑な背景

---

## ① ChatGPT Images 2.0（推奨・最初に試す）

日本語プロンプトがそのまま使える。会話で微調整可能。

ChatGPT の入力欄にそのまま貼り付ける:
```
以下の条件で書籍の挿絵イラストを1枚生成してください。

【描く内容】
上段に横一列の3つの角丸四角（矢印でつながる）と、右端から左端へ上を回って戻る色付きの矢印。上段の右端の四角から下へ矢印が伸び、下段の点線の大きな枠につながる。枠の中には4つの四角があり、そのうち2つは上下の矢印で往復している

【表現したいこと】
親のツール実行の中で、もう1本の独立したループが丸ごと動き、終わると結果だけが親に戻る

【スタイル指定】
- フラットイラスト（アイコン風、影なし）
- グレースケールが基調。下の枠、子ループの2つの四角、戻りの矢印だけ青
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
Subject: Top row: three rounded boxes connected by arrows, with a highlighted arrow looping back over the top from the right box to the left box. From the right top box an arrow goes down into a large dashed frame below, which contains four boxes, two of which are connected by up-and-down arrows forming a small loop.
Concept: Inside the parent's tool execution, another independent loop runs entirely, and only its result returns to the parent.
Style: flat design, icon style, no shadows, mostly grayscale with a blue accent only on the lower frame, the two looping boxes and the return arrow, white background, no text or labels.
Aspect ratio: 4:3
```

---

## ③ Gemini 画像生成（Imagen 3 搭載）／ 別名: Nano Banana 2

日本語OK・会話での修正可能。Google One AI Premium で利用可能。
gemini.google.com を開いて以下を貼り付ける:

```
次の条件で書籍の挿絵を1枚描いてください。

【描く内容】上段に横一列の3つの角丸四角（矢印でつながる）と、右端から左端へ上を回って戻る色付きの矢印。上段の右端の四角から下へ矢印が伸び、下段の点線の大きな枠につながる。枠の中には4つの四角があり、そのうち2つは上下の矢印で往復している
【表現したいこと】親のツール実行の中で、もう1本の独立したループが丸ごと動き、終わると結果だけが親に戻る
【スタイル】フラットイラスト、アイコン風、影なし、
グレースケール中心（下の枠、子ループの2つの四角、戻りの矢印だけ青）、白い背景、テキスト・ラベルなし、横4:縦3
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
        Image.open(io.BytesIO(part.inline_data.data)).save("fig_8_2.png")
```

---

## ④ Midjourney

```
top row: three rounded boxes connected by arrows, with a highlighted arrow looping back over the top from the right box to the left box. From the right top box an arrow goes down into a large dashed frame below, which contains four boxes, two of which are connected by up-and-down arrows forming a small loop, flat illustration, icon design, minimal, mostly grayscale with a blue accent only on the lower frame, the two looping boxes and the return arrow, white background, technical book illustration --style raw --no photorealistic, text, labels, shadows --ar 4:3 --v 6
```

---

## ⑤ Stable Diffusion（ローカル・無料）

Positive:
```
flat design illustration, top row: three rounded boxes connected by arrows, with a highlighted arrow looping back over the top from the right box to the left box. From the right top box an arrow goes down into a large dashed frame below, which contains four boxes, two of which are connected by up-and-down arrows forming a small loop, minimal, icon style, mostly grayscale with a blue accent only on the lower frame, the two looping boxes and the return arrow, white background, no text
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
フラットイラスト、アイコン風、上段に横一列の3つの角丸四角（矢印でつながる）と、右端から左端へ上を回って戻る色付きの矢印。上段の右端の四角から下へ矢印が伸び、下段の点線の大きな枠につながる。枠の中には4つの四角があり、そのうち2つは上下の矢印で往復している、
グレースケール中心（下の枠、子ループの2つの四角、戻りの矢印だけ青）、白い背景、テキストなし、技術書の挿絵スタイル
```

---

## ⑦ Imagen 2 / 3（Vertex AI・API・大量生成向け）

```
A flat illustration for a Japanese technical book. Top row: three rounded boxes connected by arrows, with a highlighted arrow looping back over the top from the right box to the left box. From the right top box an arrow goes down into a large dashed frame below, which contains four boxes, two of which are connected by up-and-down arrows forming a small loop.
Style: clean minimal flat design, mostly grayscale with a blue accent only on the lower frame, the two looping boxes and the return arrow, white background.
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
response.images[0].save("fig_8_2.png")
```
---

## ⑧ GensparkでNano bananaを使用

日本語プロンプトがそのまま使える。会話で微調整可能。

```
以下の条件で書籍の挿絵イラストを1枚生成してください。

【描く内容】
上段に横一列の3つの角丸四角（矢印でつながる）と、右端から左端へ上を回って戻る色付きの矢印。上段の右端の四角から下へ矢印が伸び、下段の点線の大きな枠につながる。枠の中には4つの四角があり、そのうち2つは上下の矢印で往復している

【表現したいこと】
親のツール実行の中で、もう1本の独立したループが丸ごと動き、終わると結果だけが親に戻る

【スタイル指定】
- フラットイラスト（アイコン風、影なし）
- グレースケールが基調。下の枠、子ループの2つの四角、戻りの矢印だけ青
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

- [ ] ループの中にもう1本のループがある入れ子の構造が伝わるか
- [ ] 書籍のトーンと合っているか（過剰な装飾・明るすぎる色がないか）
- [ ] 印刷時にグレースケールで潰れないか
- [ ] 横160mmに縮小しても内容が伝わるか
- [ ] ファイル名: `fig_8_2.png` で保存（同じIDの `fig_8_2.svg` がある場合はSVGが優先されるため、PNGを使うならSVGを削除する）
