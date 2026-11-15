# 本番公開チェックリスト（opi.koyallcoki.com）

KOYA工程：Git SHA → Preview → Build Contract → Artifact Validation → Data QA → Security/Privacy → Human Review → Synthetic E2E → Production

## 自動（CI と release.yml が毎回実行）
| 工程 | 実装 |
|---|---|
| Artifact Validation | `engine/test_decomposition.py`（合成データで数式検証） |
| Data QA | `qa/data_qa.py`（県総数との一致、欠損、分母0の警告） |
| 承認記録の検査 | `qa/proposals_check.py` |
| Build Contract | `build/contract.py`（データ埋め込み、外部依存なし、地域数・年・合計） |
| Security/Privacy | `qa/security_scan.py`（トークン・鍵・appId・メール・電話番号） |
| Synthetic E2E | `qa/e2e.py`（ヘッドレスChromeで画面数値・グラフ・シミュレーターを検査） |

## 人間（宮城浩也）
- [ ] Human Review：Pull Request を確認して取り込み済み
- [ ] Preview（非公開）で画面を確認済み

## 初回公開の手順（この順番で）
1. GitHub アカウント設定 → Pages → Add a domain に `koyallcoki.com` → 表示された TXT を Cloudflare DNS に追加 → Verify
2. リポジトリ Settings → Pages → Source「GitHub Actions」、Custom domain `opi.koyallcoki.com` → Save
3. Cloudflare → koyallcoki.com → DNS → CNAME `opi` → `okinawadao369-wq.github.io`（DNS only）
4. Actions → Release → Run workflow（Git SHA を入力）→ Review deployments → **Approve（人間のみ）**
5. DNS 反映後、Settings → Pages → Enforce HTTPS

## 公開後
- opi.koyallcoki.com が表示され、ビルドSHAがフッター（ヘッダー）に出ていることを確認
- 取り消し：Settings → Pages で Unpublish、または Release を以前の SHA で再実行
- 注意：Pages を無効にする場合は、Cloudflare の `opi` CNAME も削除する（サブドメイン乗っ取り防止）
