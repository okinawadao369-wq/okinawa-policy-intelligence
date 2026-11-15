# KOYA Okinawa Policy Intelligence v1.0 — Preview（未公開・ローカルのみ）
- data/municipalities.csv … 41市町村コード（5桁・6桁検査数字付き・保健所区分）
- data/source_catalog.csv … 公的統計ソース一覧（S01–S16）
- data/pilot_births_by_mother_age_2024.csv … パイロット取得：令和6年 母の年齢別出生数×41市町村（沖縄県衛生統計年報R6 出生第3表）
- docs/schema.sql … データスキーマ（実測/推計/仮説/欠損を value_status で区別）
- engine/decomposition.py … 対称要因分解＋ポアソン・ブートストラップ（tests: engine/test_decomposition.py は合成データ）
- etl/parse_pref_birth_age.py … 県PDF→tidy CSV パーサ（合計一致QA付き）
本番（GitHub Pages / familytreeoki.com）には一切デプロイしていない。
