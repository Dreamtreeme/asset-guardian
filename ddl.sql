-- 0) 스키마 (선택)
CREATE SCHEMA IF NOT EXISTS market;

-- 1) 유니버스 스냅샷(너가 긁어온 원본 저장용)
CREATE TABLE IF NOT EXISTS market.universe_snapshot_kr_top50 (
  as_of_date date NOT NULL,
  rank       int  NOT NULL,
  name_ko    text NOT NULL,

  -- 아래는 있으면 넣고 없으면 NULL
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

CREATE INDEX IF NOT EXISTS idx_universe_top50_date ON market.universe_snapshot_kr_top50(as_of_date);


-- 2) 종목 마스터(분석 엔진의 기준키)
CREATE TABLE IF NOT EXISTS market.tickers (
  ticker        text PRIMARY KEY,    -- 예: 005930.KS
  code_krx      text UNIQUE,          -- 예: 005930
  name_ko       text NOT NULL,
  exchange      text NOT NULL DEFAULT 'KRX-KOSPI',
  currency      text NOT NULL DEFAULT 'KRW',

  -- 가능하면 채워두면 섹터 매핑 정확도↑
  sector_key    text,
  industry      text,

  -- yfinance/기타에서 가져올 수 있는 메타
  isin         text,
  updated_at   timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tickers_name ON market.tickers(name_ko);


-- 3) 일봉 가격(OHLCV)
CREATE TABLE IF NOT EXISTS market.prices_daily (
  ticker   text NOT NULL REFERENCES market.tickers(ticker),
  date     date NOT NULL,
  open     numeric,
  high     numeric,
  low      numeric,
  close    numeric,
  adj_close numeric,
  volume   bigint,
  source   text NOT NULL DEFAULT 'yfinance',
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (ticker, date)
);

CREATE INDEX IF NOT EXISTS idx_prices_date ON market.prices_daily(date);
CREATE INDEX IF NOT EXISTS idx_prices_ticker ON market.prices_daily(ticker);


-- 4) 매크로/지수 시계열(일봉)
CREATE TABLE IF NOT EXISTS market.series_daily (
  series_id text NOT NULL,           -- 예: KOSPI, VIX, DXY, KRWUSD
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

CREATE INDEX IF NOT EXISTS idx_series_date ON market.series_daily(date);


-- 5) 분기 재무(선택/권장) - 손익
CREATE TABLE IF NOT EXISTS market.financials_q_is (
  ticker     text NOT NULL REFERENCES market.tickers(ticker),
  period_end date NOT NULL,
  revenue            numeric,
  operating_income   numeric,
  net_income         numeric,
  currency text NOT NULL DEFAULT 'KRW',
  source   text NOT NULL DEFAULT 'yfinance',
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (ticker, period_end)
);

-- 6) 분기 재무 - 현금흐름
CREATE TABLE IF NOT EXISTS market.financials_q_cf (
  ticker     text NOT NULL REFERENCES market.tickers(ticker),
  period_end date NOT NULL,
  operating_cf numeric,
  capex        numeric,
  currency text NOT NULL DEFAULT 'KRW',
  source   text NOT NULL DEFAULT 'yfinance',
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (ticker, period_end)
);

-- 7) 분기 재무 - 재무상태표
CREATE TABLE IF NOT EXISTS market.financials_q_bs (
  ticker     text NOT NULL REFERENCES market.tickers(ticker),
  period_end date NOT NULL,
  total_debt  numeric,
  total_equity numeric,
  currency text NOT NULL DEFAULT 'KRW',
  source   text NOT NULL DEFAULT 'yfinance',
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (ticker, period_end)
);


-- 8) 섹터 ETF 후보(거래량 1등 자동 선택용)
CREATE TABLE IF NOT EXISTS market.sector_etf_candidates (
  market     text NOT NULL,        -- 'KR' / 'US'
  sector_key text NOT NULL,        -- IT, FINANCIAL, HEALTHCARE, BROAD...
  etf_ticker text NOT NULL,        -- 예: 363580.KS / XLK
  priority   int  NOT NULL DEFAULT 100,
  PRIMARY KEY (market, sector_key, etf_ticker)
);

CREATE INDEX IF NOT EXISTS idx_sector_etf ON market.sector_etf_candidates(market, sector_key);
