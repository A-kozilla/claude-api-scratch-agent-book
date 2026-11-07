# /book-all — 書籍 全章一括執筆

---

## 前提確認
`book/02_toc/toc.md` が存在しない場合: 「先に `/book-toc` を実行してください」と伝えて終了。

---

## 処理手順

1. `toc.md` を読み込み、総章数をカウントして案内する
2. `references/style-guide.md`・`references/reference-doc.md` はCLAUDE.md読み込み時点でセッションに適用済み。文体ルールを適用する。Claude API（Messages API・Tool use・Streaming・Prompt caching 等）に関する技術内容を含む章がある場合、`reference-doc.md`「技術参考情報」のURLをWebFetchで取得し、以降の執筆全体に反映する（一括処理の最初に1回のみ実施）
3. はじめに → 第1章 → 第2章 … の順に `/book-chapter` と同じテンプレートで執筆・保存する
4. 進捗を都度表示する:
   ```
   [3/10] ✅ 第2章「タイトル」完了（14,200字 / 推定25ページ / 図マーカー6点）
   ```
5. 全完了後に `book/03_manuscripts/progress.md` を生成する

---

## 完了後の案内

```
✅ 全X章の原稿執筆完了
総文字数: X字 / 推定総ページ: Xページ / 図マーカー総数: X点

'/book-figures' で図の処理（SVG生成・撮影手順・AIプロンプト）を実行できます。
'/export book' で全原稿を1ファイルに結合できます。
```
