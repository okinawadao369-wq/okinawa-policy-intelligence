-- KOYA Okinawa Policy Intelligence v1.0 — データスキーマ（SQLite / PostgreSQL 互換）
-- 原則: 1観測=1行のロング形式。実測・推計・仮説・欠損を value_status で厳格に区別する。
-- 期間定義（暦年・年度・時点）と母集団定義（日本人・総計・SOFA除外）を必ず保持する。

CREATE TABLE dim_municipality (
  muni_code5      TEXT PRIMARY KEY,          -- 統計標準地域コード（例 47201）
  lg_code6        TEXT NOT NULL UNIQUE,      -- 全国地方公共団体コード（検査数字付き 472018）
  name_ja         TEXT NOT NULL,
  name_en         TEXT NOT NULL,
  muni_type       TEXT NOT NULL CHECK (muni_type IN ('市','町','村')),
  health_center   TEXT NOT NULL,             -- 保健所区分（衛生統計年報の集計単位）
  valid_from      DATE NOT NULL DEFAULT '2006-01-01',  -- 2015-2025は41市町村で境界変更なし（要確認: 変更時は版管理）
  valid_to        DATE
);

CREATE TABLE dim_source (
  source_id        TEXT PRIMARY KEY,         -- S01..（data/source_catalog.csv）
  name             TEXT NOT NULL,
  publisher        TEXT NOT NULL,
  url              TEXT NOT NULL,
  population_basis TEXT NOT NULL,            -- japanese_in_japan / total_resident / excl_foreign_military / taxpayers ...
  notes            TEXT
);

CREATE TABLE dim_indicator (
  indicator_id   TEXT PRIMARY KEY,           -- births, births_by_order, marriages, female_pop, taxable_income_per_payer ...
  name_ja        TEXT NOT NULL,
  unit           TEXT NOT NULL,              -- 人, 件, 円, 指数(R2=100), 倍
  layer8         TEXT NOT NULL,              -- KOYA思考OS 8層分類（3=沖縄産業 / 4=地域社会・家計 等）
  breakdown_keys TEXT                        -- JSON: ["sex","mother_age5","birth_order"]
);

-- 中核ファクト表: 公的統計の取得値・推計値・欠損をすべてここに置く
CREATE TABLE fact_observation (
  obs_id          INTEGER PRIMARY KEY,
  indicator_id    TEXT NOT NULL REFERENCES dim_indicator,
  muni_code5      TEXT REFERENCES dim_municipality,   -- NULL=県計
  geo_level       TEXT NOT NULL CHECK (geo_level IN ('municipality','health_center','prefecture','job_office')),
  period_type     TEXT NOT NULL CHECK (period_type IN ('calendar_year','fiscal_year','point_in_time','pooled_5y','month','quarter')),
  period_start    DATE NOT NULL,
  period_end      DATE NOT NULL,
  breakdown       TEXT NOT NULL DEFAULT '{}',          -- JSON 例 {"mother_age5":"30-34","birth_order":"1"}
  value           REAL,                                -- 欠損時は NULL（0 で埋めない）
  value_status    TEXT NOT NULL CHECK (value_status IN
                    ('observed','estimated','hypothesis','missing_not_published','missing_suppressed','missing_not_fetched','blocked_or_failed')),
  evidence_grade  TEXT NOT NULL CHECK (evidence_grade IN ('A','B','C','D')),
  freshness_tag   TEXT NOT NULL CHECK (freshness_tag IN ('observed','stale_observed','estimated','unknown','blocked_or_failed')),
  source_id       TEXT REFERENCES dim_source,           -- 推計値でも元データの出典を必須
  source_table    TEXT,                                 -- 表番号（例: 出生第3表）
  source_url      TEXT,
  retrieved_at    TIMESTAMP,
  release_version TEXT,                                 -- 例 'R6版' / 'R4訂正版' / 'H30-R4特殊報告'
  method_id       TEXT,                                 -- 推計値の場合: model_run の ID
  note            TEXT,
  UNIQUE (indicator_id, muni_code5, geo_level, period_type, period_start, breakdown, release_version)
);

-- 改訂履歴: 訂正版・遡及改定（市町村民所得は毎回全期間改定）を追跡
CREATE TABLE revision_log (
  revision_id  INTEGER PRIMARY KEY,
  obs_key      TEXT NOT NULL,          -- indicator|muni|period|breakdown
  old_value    REAL, new_value REAL,
  old_version  TEXT, new_version TEXT,
  reason       TEXT NOT NULL,          -- 'publisher_correction' / 'retroactive_revision' / 'parse_fix'
  detected_at  TIMESTAMP NOT NULL
);

-- 欠損・定義不一致の台帳（Phase1-6「未取得と表示」の根拠）
CREATE TABLE data_issue (
  issue_id     TEXT PRIMARY KEY,       -- G01..（docs の欠損・定義不一致レポートと一致）
  issue_type   TEXT NOT NULL CHECK (issue_type IN ('missing','definition_mismatch','period_mismatch','small_count','revision','access')),
  scope        TEXT NOT NULL,
  impact       TEXT NOT NULL,
  mitigation   TEXT NOT NULL,
  status       TEXT NOT NULL DEFAULT 'open'
);

-- 分析エンジン実行記録（再現性: Git SHA・入力ハッシュ・パラメータ）
CREATE TABLE model_run (
  run_id        TEXT PRIMARY KEY,
  method        TEXT NOT NULL,         -- 'symmetric_decomposition' / 'birth_order_decomp' / 'fe_poisson' ...
  git_sha       TEXT NOT NULL,
  input_hash    TEXT NOT NULL,
  params        TEXT NOT NULL,         -- JSON（ブートストラップ回数・乱数種・感度パラメータ）
  inference_class TEXT NOT NULL CHECK (inference_class IN ('descriptive','associational','causal_candidate')),
  created_at    TIMESTAMP NOT NULL
);

CREATE TABLE model_result (
  run_id      TEXT REFERENCES model_run,
  muni_code5  TEXT, period_from TEXT, period_to TEXT,
  term        TEXT NOT NULL,           -- 'population_effect' / 'rate_effect' / 'order_1' / 'beta_real_wage' ...
  estimate    REAL, ci_low REAL, ci_high REAL,
  sensitivity TEXT                     -- JSON: 代替定義での推定値
);

-- Phase 4: Evidence → Signal → Scenario → Recommendation → Human Approval → Result Feedback
CREATE TABLE policy_signal (
  signal_id TEXT PRIMARY KEY, muni_code5 TEXT, run_id TEXT REFERENCES model_run,
  description TEXT NOT NULL, evidence_grade TEXT NOT NULL CHECK (evidence_grade IN ('A','B','C','D'))
);
CREATE TABLE policy_scenario (
  scenario_id TEXT PRIMARY KEY, signal_id TEXT REFERENCES policy_signal,
  budget_jpy REAL, assumptions TEXT NOT NULL,       -- JSON。仮説値は必ずここに明記
  effect_low REAL, effect_mid REAL, effect_high REAL,
  value_status TEXT NOT NULL DEFAULT 'hypothesis'
);
CREATE TABLE policy_recommendation (
  rec_id TEXT PRIMARY KEY, scenario_id TEXT REFERENCES policy_scenario,
  text TEXT NOT NULL, created_by TEXT NOT NULL DEFAULT 'ai',
  status TEXT NOT NULL DEFAULT 'proposed' CHECK (status IN ('proposed','approved','rejected','revised'))
);
CREATE TABLE human_approval (          -- AIは提案のみ。最終判断は人間（承認者・日時・理由を必須）
  rec_id TEXT REFERENCES policy_recommendation, approver TEXT NOT NULL,
  decision TEXT NOT NULL CHECK (decision IN ('approved','rejected','revise')),
  reason TEXT NOT NULL, decided_at TIMESTAMP NOT NULL
);
CREATE TABLE result_feedback (
  rec_id TEXT REFERENCES policy_recommendation, observed_at DATE NOT NULL,
  indicator_id TEXT, observed_value REAL, note TEXT
);
