
-- CREATE
-- 1. 사용자 테이블 (부모)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    user_name VARCHAR(50) NOT NULL,
    webhook TEXT NOT NULL,
    types INTEGER NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. 종목 테이블 (자식)
CREATE TABLE IF NOT EXISTS tickers (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    ticker_code VARCHAR(20) NOT NULL,
    ticker_name VARCHAR(50) NOT NULL,
    target_price NUMERIC(15, 2) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_user FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT unique_user_ticker UNIQUE (user_id, ticker_code)
);

-- 3. 버전 관리 테이블
CREATE TABLE IF NOT EXISTS db_ver (
    ver INTEGER NOT NULL
);

-- 4. 현재 설정
CREATE TABLE IF NOT EXISTS configs (
    cur_user_id INTEGER NOT NULL
);


-- INSERT
-- 1. configs 기본 유저 추가
INSERT INTO configs (cur_user_id) VALUES (0);

INSERT INTO db_ver (ver) VALUES (1);

INSERT INTO users (id, user_name, webhook, types)
VALUES (0, '', '', 0)
ON CONFLICT (id) DO NOTHING;

INSERT INTO tickers (user_id,ticker_code,ticker_name,target_price) VALUES
(0, '005930.KS', '삼성전자', 200000),
(0, '000660.KS', 'SK하이닉스', 1000000),
(0, '035720.KS', '카카오', 60000),
(0, '086520.KQ', '에코프로', 180000),
(0, '247540.KQ', '에코프로비엠', 230000)
ON CONFLICT (user_id, ticker_code) DO NOTHING;

