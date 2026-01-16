CREATE SCHEMA IF NOT EXISTS market;

-- 1) 자산 마스터: 이름만 있어도 생성 가능
CREATE TABLE IF NOT EXISTS market.assets (
  asset_id    bigserial PRIMARY KEY,
  name_ko     text NOT NULL UNIQUE,     -- "삼성전자"
  ticker      text UNIQUE,              -- "005930.KS" (없어도 됨)
  exchange    text,
  currency    text DEFAULT 'KRW',
  sector_key  text,
  industry    text,
  isin        text,
  updated_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_assets_ticker ON market.assets(ticker);

-- 2) 유니버스 스냅샷(원본 보관)
CREATE TABLE IF NOT EXISTS market.universe_snapshot_kr_top50 (
  as_of_date date NOT NULL,
  rank       int  NOT NULL,
  name_ko    text NOT NULL,
  asset_id   bigint REFERENCES market.assets(asset_id),

  price_krw        numeric,
  change_krw       numeric,
  pct_change       numeric,
  volume           bigint,
  trading_value_krw numeric,
  market_cap_krw    numeric,
  per              numeric,
  pbr              numeric,

  raw_row text,
  PRIMARY KEY (as_of_date, rank)
);

CREATE INDEX IF NOT EXISTS idx_universe_asset ON market.universe_snapshot_kr_top50(asset_id);

-- 3) 가격(OHLCV): asset_id로 연결. ticker 없어도 asset_id만 있으면 저장 가능
CREATE TABLE IF NOT EXISTS market.prices_daily (
  asset_id  bigint NOT NULL REFERENCES market.assets(asset_id),
  date      date NOT NULL,
  open      numeric,
  high      numeric,
  low       numeric,
  close     numeric,
  adj_close numeric,
  volume    bigint,
  source    text NOT NULL DEFAULT 'yfinance',
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (asset_id, date)
);

CREATE INDEX IF NOT EXISTS idx_prices_date ON market.prices_daily(date);

-- 4) 매크로/지수(일봉)
CREATE TABLE IF NOT EXISTS market.series_daily (
  series_id text NOT NULL, -- KOSPI, VIX, DXY, KRWUSD...
  date      date NOT NULL,
  open      numeric,
  high      numeric,
  low       numeric,
  close     numeric,
  adj_close numeric,
  volume    bigint,
  source    text NOT NULL DEFAULT 'yfinance',
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (series_id, date)
);

-- 5) 분기 재무(선택): asset_id 기준
CREATE TABLE IF NOT EXISTS market.financials_q_is (
  asset_id   bigint NOT NULL REFERENCES market.assets(asset_id),
  period_end date NOT NULL,
  revenue            numeric,
  operating_income   numeric,
  net_income         numeric,
  currency text NOT NULL DEFAULT 'KRW',
  source   text NOT NULL DEFAULT 'yfinance',
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (asset_id, period_end)
);

CREATE TABLE IF NOT EXISTS market.financials_q_cf (
  asset_id   bigint NOT NULL REFERENCES market.assets(asset_id),
  period_end date NOT NULL,
  operating_cf numeric,
  capex        numeric,
  currency text NOT NULL DEFAULT 'KRW',
  source   text NOT NULL DEFAULT 'yfinance',
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (asset_id, period_end)
);

CREATE TABLE IF NOT EXISTS market.financials_q_bs (
  asset_id   bigint NOT NULL REFERENCES market.assets(asset_id),
  period_end date NOT NULL,
  total_debt  numeric,
  total_equity numeric,
  currency text NOT NULL DEFAULT 'KRW',
  source   text NOT NULL DEFAULT 'yfinance',
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (asset_id, period_end)
);

-- 6) 티커 매핑 시도 기록(나중에 재시도/디버깅 편함)
CREATE TABLE IF NOT EXISTS market.ticker_resolution_log (
  id bigserial PRIMARY KEY,
  name_ko text NOT NULL,
  attempted_at timestamptz NOT NULL DEFAULT now(),
  query text NOT NULL,
  result_ticker text,
  result_name text,
  result_exchange text,
  score numeric,
  status text NOT NULL, -- 'matched' / 'failed'
  raw jsonb
);

CREATE INDEX IF NOT EXISTS idx_resolve_name ON market.ticker_resolution_log(name_ko);
