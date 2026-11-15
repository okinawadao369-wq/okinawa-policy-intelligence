# 政策提案と承認の記録（Phase 4）

流れ：Evidence → Signal → Scenario → Recommendation → **Human Approval** → Result Feedback

1. ダッシュボードの「政策シミュレーター」で条件を入れ、「レポートを作成」→「コピー」。
2. このフォルダに `YYYY-MM-DD_地域_政策.md` として保存し、Pull Request を作る（Claudeが代行可）。
3. **人間が** 「Human Approval」欄（承認者・判断・理由・日付）を記入し、PR を取り込む。
   - CI（`qa/proposals_check.py`）は、判断が approved / rejected / revise のいずれかで、承認者・理由・日付が埋まっていない提案の取り込みを止める。
   - 状態が proposed のままのファイルは、記録として取り込み可能（未承認として扱う）。
4. 実施後、「Result Feedback」欄に観測値を追記して PR で更新する。

AIは案と根拠を示すだけで、承認欄を埋めることはしない。効果量はすべて仮説値（他地域の文献値）である。
