
-- CREATE
-- 1. 사용자 테이블
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_name VARCHAR(50) NOT NULL,
    webhook TEXT DEFAULT '',
    genai_key TEXT DEFAULT '',
    types INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    market_type INTEGER DEFAULT 0,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. 종목 테이블
CREATE TABLE IF NOT EXISTS tickers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    ticker_code VARCHAR(20) NOT NULL,
    ticker_name VARCHAR(50) NOT NULL,
    target_price NUMERIC(15, 2) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE (user_id, ticker_code) -- ON CONFLICT 처리를 위해 필수
);

--기본 종목 테이블
CREATE TABLE IF NOT EXISTS default_tickers(
    id INTEGER PRIMARY KEY AUTOINCREMENT,-- 번호
    std_code TEXT UNIQUE DEFAULT '', -- 표준코드
    short_code TEXT DEFAULT '',-- 단축코드
    name_ko TEXT DEFAULT '',-- 한글 종목명
    short_name_ko TEXT DEFAULT '',-- 한글 종목약명
    name_en TEXT DEFAULT '',-- 영문 종목명
    listing_date TEXT DEFAULT '',-- 상장일
    market_type TEXT DEFAULT '',-- 시장구분
    security_type TEXT DEFAULT '',-- 증권구분
    dept_type TEXT DEFAULT '',-- 소속부
    stock_type TEXT DEFAULT '',-- 주식종류
    face_value INTEGER DEFAULT 0,-- 액면가
    total_shares INTEGER DEFAULT 0-- 상장주식수
);

-- 3. 버전 및 설정 테이블
CREATE TABLE IF NOT EXISTS db_ver (
    id INTEGER PRIMARY KEY CHECK (id = 1), -- ID를 1로 고정
    ver INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS configs (cur_user_id INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS ticker_ver (ver TEXT DEFAULT '');

-- 초기 데이터 삽입
INSERT INTO configs (cur_user_id) VALUES (0);
INSERT INTO db_ver (ver) VALUES (1);

-- 기본 사용자 추가 (ID를 0으로 고정하고 싶다면 직접 명시)
-- 주의: AUTOINCREMENT는 보통 1부터 시작하므로 0번 유저를 만들려면 직접 넣어야 합니다.
INSERT OR IGNORE INTO users (id, user_name, webhook,genai_key, types, market_type)
VALUES (0, '사용자', '','', 0, 0);

INSERT OR IGNORE INTO tickers (user_id, ticker_code, ticker_name, target_price) VALUES
(0, '005930.KS', '삼성전자', 200000),
(0, '000660.KS', 'SK하이닉스', 1000000),
(0, '035720.KS', '카카오', 60000),
(0, '086520.KQ', '에코프로', 180000),
(0, '247540.KQ', '에코프로비엠', 230000);

