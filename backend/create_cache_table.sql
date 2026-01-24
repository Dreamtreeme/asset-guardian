-- LLM 보고서 캐시 테이블 생성
CREATE TABLE IF NOT EXISTS report_cache (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    report_date TIMESTAMP NOT NULL,
    llm_output JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 복합 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_symbol_date ON report_cache(symbol, report_date);

-- 오래된 캐시 자동 삭제 (7일 이상)
CREATE OR REPLACE FUNCTION delete_old_cache()
RETURNS void AS $$
BEGIN
    DELETE FROM report_cache WHERE created_at < NOW() - INTERVAL '7 days';
END;
$$ LANGUAGE plpgsql;
