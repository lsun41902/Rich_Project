--기본 종목 테이블
CREATE TABLE IF NOT EXISTS default_tickers_US(
    id INTEGER PRIMARY KEY AUTOINCREMENT,-- 번호
    symbol TEXT UNIQUE DEFAULT '', -- 표준코드
    name_en TEXT DEFAULT '',-- 영문 종목명
    name_ko TEXT DEFAULT '',-- 한글 종목명
    industry TEXT DEFAULT '', -- 산업 종류
    market_type TEXT DEFAULT '' -- 시장 종류
);


ALTER TABLE ticker_ver ADD COLUMN us_ver TEXT DEFAULT '';