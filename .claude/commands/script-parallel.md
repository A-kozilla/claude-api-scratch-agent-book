# /script-parallel — Udemyスクリプト並列生成（サブエージェント版）

`/script-all` の並列処理版です。複数のサブエージェントを同時起動してスクリプトを並列生成します。
生成速度が `/script-all` の約3〜5倍になります。

---

## `/script-all` との違い

| 項目 | /script-all | /script-parallel |
|-----|------------|-----------------|
| 処理方式 | 直列（1本ずつ） | 並列（最大5本同時） |
| コンテキスト | 全レクチャーが同一コンテキスト | 各レクチャーが独立したコンテキスト |
| 品質安定性 | 後半でブレが生じやすい | 各サブエージェントが最初から新鮮なコンテキスト |
| エラー耐性 | 1本失敗で停止リスク | 失敗した本だけスキップして続行 |
| 速度 | 標準 | 約3〜5倍速 |

---

## 前提確認

`udemy/02_toc/toc.md` が存在しない場合: 「先に `/toc` を実行してください」と伝えて終了。

---

## 処理手順

### Step 1: 生成対象リストの作成

`toc.md` から全レクチャーを抽出して `udemy/03_scripts/.worker_queue.txt` に保存する:

```
1-1
1-2
1-3
2-1
...
```

### Step 2: バッチ分割

全レクチャーを **5本1バッチ** に分割する（最大同時起動数=5）。
例: 40本 → 8バッチ（各5本）

### Step 3: バッチごとにサブエージェントを並列起動

以下のbashスクリプトを実行する:

```bash
#!/bin/bash
# 並列スクリプト生成

BATCH_SIZE=5
TOC_FILE="udemy/02_toc/toc.md"
QUEUE_FILE="udemy/03_scripts/.worker_queue.txt"

# キューファイルから未生成レクチャーを読み込む
mapfile -t QUEUE < "$QUEUE_FILE"

# バッチ処理
for ((i=0; i<${#QUEUE[@]}; i+=BATCH_SIZE)); do
    BATCH=("${QUEUE[@]:$i:$BATCH_SIZE}")
    PIDS=()

    echo "[バッチ $((i/BATCH_SIZE + 1))/$(( (${#QUEUE[@]} + BATCH_SIZE - 1) / BATCH_SIZE ))] 起動中..."

    # バッチ内のレクチャーをサブエージェントで並列処理
    for LECTURE in "${BATCH[@]}"; do
        SECTION=$(echo $LECTURE | cut -d'-' -f1)
        LECTURE_NUM=$(echo $LECTURE | cut -d'-' -f2)
        OUTPUT_DIR="udemy/03_scripts/section_$(printf '%02d' $SECTION)"
        OUTPUT_FILE="$OUTPUT_DIR/lecture_$(printf '%02d' $LECTURE_NUM).md"

        mkdir -p "$OUTPUT_DIR"

        # サブエージェントを起動（バックグラウンド）
        claude -p "
あなたはUdemy講座のレクチャースクリプトを生成する専門エージェントです。

## 対象
Section $(printf '%02d' $SECTION), Lecture $(printf '%02d' $LECTURE_NUM)

## 目次情報
$(cat $TOC_FILE)

## 生成ルール
1. 対象レクチャーの種類（講義型/ハンズオン型/Quiz型）を目次から判断する
2. 講義型: 会話文1,600〜2,000字
3. ハンズオン型: 会話文1,800〜2,400字
4. 各トピックは「概念定義→具体例→重要性」の3段階で説明する
5. スライド切り替え指示 [→ Slide XX] を各パートに入れる
6. まとめは3点以上・各点に補足1文

## 出力
スクリプトのMarkdown本文のみを出力する。前置き・説明は不要。
" > "$OUTPUT_FILE" &

        PIDS+=($!)
        echo "  → Section $SECTION Lecture $LECTURE_NUM 起動 (PID: $!)"
    done

    # バッチ内の全サブエージェントが完了するまで待機
    for PID in "${PIDS[@]}"; do
        wait $PID
        STATUS=$?
        if [ $STATUS -eq 0 ]; then
            echo "  ✅ PID $PID 完了"
        else
            echo "  ❌ PID $PID 失敗（手動で /script で再生成してください）"
        fi
    done

    echo "[バッチ $((i/BATCH_SIZE + 1)) 完了]"
    echo ""
done

echo "=== 並列生成完了 ==="
```

### Step 4: 品質チェックサブエージェントの起動

全ファイル生成後、品質チェック専用のサブエージェントを起動する:

```bash
claude -p "
以下のスクリプトファイルを読み込み、品質チェックを実行してください。

チェック項目:
1. 会話文字数が種類別の目標を満たしているか
2. まとめセクションが存在するか
3. 次レクチャーへの橋渡しがあるか
4. コードブロックに言語名指定があるか
5. 「〜である」「〜における」などの書き言葉が含まれていないか

対象ファイル: $(find udemy/03_scripts -name '*.md' | sort)

結果をMarkdownの表形式で出力してください。
問題のあるファイルは [WARNING] と具体的な問題点を記載してください。
" > udemy/03_scripts/quality_report.md
```

---

## 完了後の案内

```
✅ 並列生成完了

生成本数: X本
失敗: X本（再生成: /script [S] [L] を使用）
品質レポート: udemy/03_scripts/quality_report.md

'/slides-all' でスライドを生成できます。
```

---

## 注意事項

- サブエージェントは最大5本同時起動（システムリソースに応じて調整可）
- 各サブエージェントは独立したコンテキストを持つため、前のレクチャーの影響を受けない
- Claude Codeのレート制限に注意（大量生成時は `--dangerously-skip-permissions` フラグが必要な場合がある）
