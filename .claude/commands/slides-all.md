# /slides-all — Udemy 全スライド一括生成

---

## 前提確認
`udemy/03_scripts/` 配下にファイルが1つ以上存在しない場合: 「先に `/script-all` を実行してください」と伝えて終了。

---

## 処理手順

1. 生成済みスクリプトの総数をカウントして案内する
2. `/slides` と同じ手順で Section 01, Lecture 01 から順次生成・保存する
3. 進捗を都度表示する:
   ```
   [3/40] ✅ Section 02 - Lecture 01「タイトル」完了（12枚）
   ```
4. 全完了後に `udemy/04_slides/slides_progress.md` を生成する

---

## 完了後の案内

```
✅ 全X本のスライド生成完了
総スライド枚数: X枚
保存先: udemy/04_slides/
```
