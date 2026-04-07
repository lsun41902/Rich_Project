from neo4j import GraphDatabase


class NewsGraphManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(NewsGraphManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized: return

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

    def update_stock_data_smart(self,app, ticker_name, ticker_code, stock_type):
        import services.ui_helper as helper
        import services.KRX as krx
        loading = helper.LoadingWindow(app.root)

        # 1. 먼저 DB에 해당 ticker_code를 가진 Company 노드가 있는지 확인합니다.
        with self.driver.session() as session:
            check_query = "MATCH (c:Company {ticker_code: $ticker_code}) RETURN count(c) > 0 AS exists"
            result = session.run(check_query, ticker_code=ticker_code).single()
            exists = result['exists'] if result else False

        # 2. 존재 여부에 따라 수집 기간(days) 결정
        if not exists:
            loading.show_progress("주가 정보를 가져오는 중 입니다.\n최초 1회만 실행 되니 기다려 주세요...")
            days = 1825  # 데이터가 없으면 5년치 (최초 설치)
            print(f"🆕 [최초 적재] {ticker_name}({ticker_code}) 데이터가 없습니다. 5년치 데이터를 로드합니다.")
        else:
            loading.show_progress("주가 정보를 가져오는 중 입니다.\n잠시만 기다려 주세요...")
            days = 5  # 데이터가 있으면 최근 5일치 (업데이트)
            print(f"🔄 [증분 업데이트] {ticker_name}({ticker_code}) 기존 데이터 확인됨. 최근 5일치만 업데이트합니다.")

        try:
            df = krx.pull_request_stock(ticker_code,days=days,stock_type=stock_type)
            print(f"데이터 로드 성공")
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
        loading.stop()

    # news_data는 아까 만드신 pull_request_news()의 결과물입니다.
    def save_news_to_neo4j(self, news_data, ticker_code):
        try:
            with self.driver.session() as session:
                for item in news_data:
                    query = """
                    // 1. 링크(URL)를 유니크 ID로 사용하여 중복 확인
                    MERGE (n:News {link: $link})

                    // 2. 처음 저장될 때만 상세 정보 기록 (중복일 땐 무시)
                    ON CREATE SET 
                        n.title = $title, 
                        n.pubDateTime = datetime(replace($pubDate, ' ', 'T')),
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
        except Exception as e:
            print(f"저장 실패 : {e}")


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
            
            RETURN n.title AS title, n.description AS description, n.link AS link,(p.close > p.open) AS is_rise
            """

        with self.driver.session() as session:
            result = session.run(query, ticker_code=ticker_code, keyword=clean_keyword)
            records = []
            for r in result:
                records.append({
                    "title": r['title'],
                    "description": r['description'],
                    "link": r['link'],
                    "is_rise": r['is_rise']
                })

            if not records:
                result_str = f"⚠️ 매칭된 데이터가 없습니다.\n*키워드: {clean_keyword}와 관련된 내용이 없습니다."
                return result_str, []

            total = len(records)
            rises = sum(1 for r in records if r['is_rise'] is True)
            win_rate = (rises / total) * 100

            result_str = (f"🔍 키워드 [{clean_keyword}] 분석 결과\n"
                          f"📊 총 발생 횟수: {total}회\n"
                          f"📈 상승 횟수: {rises}회\n"
                          f"🎯 적중 확률: {win_rate:.1f}%")
            return result_str,records

    def get_keyword_news_analyze(self,keyword):
        clean_keyword = keyword.strip()
        query = """
                    MATCH (c:Company {name: $keyword})-[:MENTIONS]-(n:News)
                    RETURN n.title AS title, n.description AS description
                    LIMIT 5
                    """
        with self.driver.session() as session:
            result = session.run(query,  keyword=clean_keyword)
            news_list = [
                {"title": record["title"], "description": record["description"]}
                for record in result
            ]
            return news_list

neo4j = NewsGraphManager()