from neo4j import GraphDatabase


class NewsGraphManager:
    def __init__(self):
        # 1. 드라이버 초기화 (안드로이드의 Retrofit/Room 빌더와 비슷합니다)
        from dotenv import load_dotenv
        import os
        load_dotenv()
        uri = os.getenv("GRAPH_URI")
        user = os.getenv("GRAPH_USER")
        password = os.getenv("GRAPH_PASSWORD")

        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def update_stock_data_smart(self, symbol, ticker_name, ticker_code):
        from datetime import datetime, timedelta
        import FinanceDataReader as fdr

        # 1. 먼저 DB에 해당 ticker_code를 가진 Company 노드가 있는지 확인합니다.
        with self.driver.session() as session:
            check_query = "MATCH (c:Company {ticker_code: $ticker_code}) RETURN count(c) > 0 AS exists"
            result = session.run(check_query, ticker_code=ticker_code).single()
            exists = result['exists'] if result else False

        # 2. 존재 여부에 따라 수집 기간(days) 결정
        if not exists:
            days = 3650  # 데이터가 없으면 10년치 (최초 설치)
            print(f"🆕 [최초 적재] {ticker_name}({ticker_code}) 데이터가 없습니다. 10년치 데이터를 로드합니다.")
        else:
            days = 5  # 데이터가 있으면 최근 5일치 (업데이트)
            print(f"🔄 [증분 업데이트] {ticker_name}({ticker_code}) 기존 데이터 확인됨. 최근 5일치만 업데이트합니다.")

        # 3. 날짜 설정 및 데이터 가져오기
        end_str = datetime.now().strftime('%Y-%m-%d')
        start_str = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        try:
            df = fdr.DataReader(symbol, start=start_str, end=end_str)
        except Exception as e:
            print(f"❌ 데이터 로드 실패: {e}")
            return

        # 4. Neo4j 적재 (기존 로직 유지)
        with self.driver.session() as session:
            for date, row in df.iterrows():
                date_str = date.strftime('%Y-%m-%d')
                node_id = f"{date_str}_{ticker_code}"
                query = """
                MERGE (p:StockPrice {id: $node_id})
                SET p.date = date($date), 
                    p.ticker_code = $ticker_code,
                    p.close = $close, 
                    p.open = $open,
                    p.high = $high,
                    p.low = $low,
                    p.volume = $volume
                
                WITH p
                MERGE (c:Company {ticker_code: $ticker_code})
                ON CREATE SET c.name = $ticker_name
                MERGE (p)-[:PRICE_OF]->(c)
                """
                session.run(query,
                            node_id=node_id,  # 추가된 부분
                            date=date_str,
                            ticker_code=ticker_code,
                            ticker_name=ticker_name,
                            close=float(row['Close']),
                            open=float(row['Open']),
                            high=float(row['High']),
                            low=float(row['Low']),
                            volume=int(row['Volume']))

        print(f"✅ {ticker_name} 적재 완료!")

    # news_data는 아까 만드신 pull_request_news()의 결과물입니다.
    def save_news_to_neo4j(self, news_data, ticker_code):
        with self.driver.session() as session:
            for item in news_data:
                query = """
                // 1. 링크(URL)를 유니크 ID로 사용하여 중복 확인
                MERGE (n:News {link: $link})
    
                // 2. 처음 저장될 때만 상세 정보 기록 (중복일 땐 무시)
                ON CREATE SET 
                    n.title = $title, 
                    n.pubDate = date($pubDate),
                    n.description = $description
    
                // 3. 이미 있다면 마지막 확인 시간만 갱신
                ON MATCH SET 
                    n.last_checked = datetime()
    
                // 4. 미리 저장된 회사(Company) 노드를 찾아 연결
                WITH n
                MATCH (c:Company {ticker_code: $ticker_code})
                MERGE (n)-[:MENTIONS]->(c)
                """

                session.run(query,
                            link=item['link'],
                            title=item['title'],
                            pubDate=item['pubDate'],
                            description=item['description'],
                            ticker_code=ticker_code)
        print(f"✅ {len(news_data)}개의 뉴스 처리 완료 (중복 제외)")

    def analyze_keyword_impact(self, ticker_code, keyword):
        clean_keyword = keyword.strip()
        # n.pubDate(문자열)를 date() 함수로 감싸서 p.date(Date객체)와 타입을 맞춤
        query = """
            MATCH (n:News)-[:MENTIONS]->(c:Company {ticker_code: $ticker_code})
            WHERE toLower(n.title) CONTAINS toLower($keyword)

            MATCH (p:StockPrice {ticker_code: $ticker_code})
            WHERE p.date >= date(n.pubDate) AND p.date <= date(n.pubDate) + duration({days: 3})

            WITH n, p ORDER BY p.date ASC
            WITH n, head(collect(p)) AS p

            RETURN (p.close > p.open) AS is_rise
            """

        with self.driver.session() as session:
            # ticker_code는 "005930.KS" 형식으로 잘 들어오고 있으니 그대로 사용
            result = session.run(query, ticker_code=ticker_code, keyword=clean_keyword)
            records = [r['is_rise'] for r in result]

            if not records:
                # 데이터가 없는 경우를 위해 로그 출력
                result_str = f"⚠️ 매칭된 데이터가 없습니다.\n(키워드: {clean_keyword}, 코드: {ticker_code})"
                return result_str

            total = len(records)
            rises = sum(records)
            win_rate = (rises / total) * 100

            result_str = (f"🔍 키워드 [{clean_keyword}] 분석 결과\n"
                          f"📊 총 발생 횟수: {total}회\n"
                          f"📈 상승 횟수: {rises}회\n"
                          f"🎯 적중 확률: {win_rate:.1f}%")
            return result_str

