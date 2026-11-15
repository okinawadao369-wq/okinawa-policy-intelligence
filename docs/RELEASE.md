# リリース工程（KOYA標準）
Git SHA → Preview → Build Contract → Artifact Validation → Data QA → Security/Privacy → Human Review → Synthetic E2E → Production

- main は保護ブランチ（PR必須・CI通過必須・直接push禁止）。
- CI（ci.yml）が Artifact Validation と Data QA を自動実行。
- Production は release.yml を手動実行し、environment `production` の必須レビュアーが承認した場合のみ公開。
- 承認前の政策シナリオ・提言の下書きはリポジトリに置かない（非公開Previewで扱う）。

## 公開先
- 予定: `opi.koyallcoki.com`（合同会社koya。FTOドメイン familytreeoki.com とは切り離す）
- 本番承認時に人間が行う: Cloudflare DNS に `opi` CNAME → `okinawadao369-wq.github.io`（DNS only）、Pages の Source を GitHub Actions に、カスタムドメインを設定。
- それまで Pages は無効。無効の間はリポジトリを公開しても site は配信されない。
