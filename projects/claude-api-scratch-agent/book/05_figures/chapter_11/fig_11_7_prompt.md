# 図11.7 イラスト生成プロンプト

## イメージ設計メモ（全ツール共通）
- 描写対象: 封筒を大量に入れた箱を送り出す場面、砂時計、チェックマーク、書類の束のダウンロード、番号札で封筒と結果を照合する場面が、左上から右下へ矢印でつながっている
- 伝えたいこと: 大量のリクエストをまとめて送り、処理中→完了を待ってから結果を取り出し、番号（custom_id）で突き合わせる非同期のバッチ処理
- 書籍のトーン: 技術系
- 構図: 2段のジグザグ配置の流れ
- 色使い: グレースケール＋アクセント1色（青）
- 含めないもの: テキスト・ラベル・複雑な背景

> 本文と正確に一致する図解（ファイル名・関数名入り）は `fig_11_7.svg` を使う。このプロンプトは挿絵版を作りたい場合の補助。

---

## ① ChatGPT Images 2.0（推奨・最初に試す）

日本語プロンプトがそのまま使える。会話で微調整可能。

ChatGPT の入力欄にそのまま貼り付ける:
```
以下の条件で書籍の挿絵イラストを1枚生成してください。

【描く内容】
封筒を大量に入れた箱を送り出す場面、砂時計、チェックマーク、書類の束のダウンロード、番号札で封筒と結果を照合する場面が、左上から右下へ矢印でつながっている

【表現したいこと】
大量のリクエストをまとめて送り、処理中→完了を待ってから結果を取り出し、番号（custom_id）で突き合わせる非同期のバッチ処理

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
Subject: a box full of envelopes being sent, an hourglass, a check mark, a stack of documents being downloaded, and matching numbered tickets between envelopes and results, connected by arrows in two rows
Concept: asynchronous batch processing: submit many requests, wait, download results, and match them by ID
Style: flat design, icon style, no shadows, grayscale with single blue accent, white background, no text or labels.
Aspect ratio: 4:3
```

---

## ③ Gemini 画像生成（Imagen 3 搭載）／ 別名: Nano Banana 2

日本語OK・会話での修正可能。Google One AI Premium で利用可能。
gemini.google.com を開いて以下を貼り付ける:

```
次の条件で書籍の挿絵を1枚描いてください。

【描く内容】封筒を大量に入れた箱を送り出す場面、砂時計、チェックマーク、書類の束のダウンロード、番号札で封筒と結果を照合する場面が、左上から右下へ矢印でつながっている
【表現したいこと】大量のリクエストをまとめて送り、処理中→完了を待ってから結果を取り出し、番号（custom_id）で突き合わせる非同期のバッチ処理
【スタイル】フラットイラスト、アイコン風、影なし、
グレースケールと青の2色、白い背景、テキスト・ラベルなし、横4:縦3
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
        Image.open(io.BytesIO(part.inline_data.data)).save("fig_11_7.png")
```

---

## ④ Midjourney

```
a box full of envelopes being sent, an hourglass, a check mark, a stack of documents being downloaded, and matching numbered tickets between envelopes and results, connected by arrows in two rows, flat illustration, icon design, minimal, grayscale with blue accent, white background, technical book illustration --style raw --no photorealistic, text, labels, shadows --ar 4:3 --v 6
```

---

## ⑤ Stable Diffusion（ローカル・無料）

Positive:
```
flat design illustration, a box full of envelopes being sent, an hourglass, a check mark, a stack of documents being downloaded, and matching numbered tickets between envelopes and results, connected by arrows in two rows, minimal, icon style, grayscale with blue accent, white background, no text
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
フラットイラスト、アイコン風、封筒を大量に入れた箱を送り出す場面、砂時計、チェックマーク、書類の束のダウンロード、番号札で封筒と結果を照合する場面が、左上から右下へ矢印でつながっている、グレースケール＋青の2色、白い背景、テキストなし、技術書の挿絵スタイル
```

---

## ⑦ Imagen 2 / 3（Vertex AI・API・大量生成向け）

```
A flat illustration for a Japanese technical book. a box full of envelopes being sent, an hourglass, a check mark, a stack of documents being downloaded, and matching numbered tickets between envelopes and results, connected by arrows in two rows.
Style: clean minimal flat design, grayscale with blue accent, white background.
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
response.images[0].save("fig_11_7.png")
```
---

## ⑧ GensparkでNano bananaを使用

日本語プロンプトがそのまま使える。会話で微調整可能。

Genspark の入力欄にそのまま貼り付ける:
```
以下の条件で書籍の挿絵イラストを1枚生成してください。

【描く内容】
封筒を大量に入れた箱を送り出す場面、砂時計、チェックマーク、書類の束のダウンロード、番号札で封筒と結果を照合する場面が、左上から右下へ矢印でつながっている

【表現したいこと】
大量のリクエストをまとめて送り、処理中→完了を待ってから結果を取り出し、番号（custom_id）で突き合わせる非同期のバッチ処理

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
- [ ] ファイル名: `fig_11_7.png` で保存
