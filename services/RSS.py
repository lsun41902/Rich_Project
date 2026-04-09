import requests
from bs4 import BeautifulSoup
import sys



def pull_request_news(keyword,count=50):
    import re
    import feedparser
    from urllib.parse import quote
    from datetime import datetime, timedelta
    # 1. 한글 검색어를 URL용 암호로 변환 (금 시세 -> %EA%B8%88...)
    encoded_query = quote(keyword)

    # 2. 구글 공식 RSS 주소 조립 (rss.app 거치지 않음!)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"

    # 3. 데이터 가져오기
    feed = feedparser.parse(url)
    news_data = []

    for entry in feed.entries[:count]:
        # 1. HTML 태그 제거 로직 (정규표현식)
        dt_utc = datetime(*entry.published_parsed[:6])
        dt_kst = dt_utc + timedelta(hours=9)
        clean_desc = re.sub(r'<[^>]+>', '', entry.description)
        clean_date = dt_kst.strftime('%Y-%m-%d %H:%M:%S')
        # 2. 데이터 구조에 추가
        news_data.append({
            "title": entry.title,
            "link": entry.link,
            "pubDate": clean_date,
            "description": clean_desc.strip()  # 공백 제거 후 저장
        })
    news_data.sort(key=lambda x: x['pubDate'], reverse=True)
    return news_data

def pull_news_contents(links, limit=3):
    news = links[:limit]  # 상위 5개만 슬라이싱
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    contents = []

    print(f"🚀 상위 {len(news)}개 뉴스 본문 수집 시작...",flush=True)

    for i, link in enumerate(news):
        url = link['link']
        title = link['title']
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # 일반적인 뉴스 사이트의 본문 태그 (사이트마다 다를 수 있음)
                # 우선 article, div.article_body 등을 탐색
                article = soup.find('article') or soup.find('div', id='articleBody') or soup.find('div',
                                                                                                  class_='article_body')

                if article:
                    text = article.get_text(separator=' ', strip=True)
                else:
                    # 태그를 못 찾으면 body 전체에서 텍스트만 추출 (성능은 떨어짐)
                    text = soup.body.get_text(separator=' ', strip=True)

                # 너무 긴 경우를 대비해 1000자 내외로 자르거나 정제
                clean_text = " ".join(text.split())[:1500]
                contents.append({"title": title, "content": clean_text})
                print(f"✅ [{i + 1}] 수집 완료: {title}",flush=True)
            else:
                print(f"❌ [{i + 1}] 접속 실패 (Code {response.status_code}): {url}",flush=True)

        except Exception as e:
            print(f"⚠️ [{i + 1}] 에러 발생: {e}",flush=True)

    return contents

from newspaper import Article, Config
from googlenewsdecoder import new_decoderv1
import requests
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
#
# def pull_news_content(link):
#     url = link['link']
#     title = link['title']
#
#     try:
#         # 1. 구글 뉴스 암호화 링크 디코딩
#         print("주소 요청",flush=True)
#         sys.stdout.flush() # 즉시 밀어내기
#         if "news.google.com" in url:
#             try:
#                 # 라이브러리를 사용하여 실제 URL 추출
#                 decoded_res = new_decoderv1(url, interval=1)
#                 if decoded_res.get('status'):
#                     url = decoded_res.get('decoded_url')
#                     print(f"🔗 실제 주소로 디코딩됨: {url}",flush=True)
#             except Exception as e:
#                 print(f"⚠️ 주소 요청 실패: {e}",flush=True)
#
#         # 2. 이제 실제 주소로 크롤링 진행
#         config = Config()
#         config.request_timeout = 10  # 10초 넘으면 포기
#         config.browser_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
#         if "naver.com" in url:
#             clean_text = backup_naver_crawl(url)
#         else:
#             article = Article(url, language='ko', config=config)
#             article.download()
#             article.parse()
#             clean_text = article.text
#             # 2단계: 본문이 너무 짧거나 없을 경우 메타데이터 활용
#             if not clean_text or len(clean_text) < 100:
#                 # 아까 이미지 디버그 창에서 확인한 'meta_description' 활용
#                 clean_text = article.meta_description
#
#             # 3단계: 여전히 없을 경우 BeautifulSoup으로 강제 추출 (최후의 수단)
#             if not clean_text or len(clean_text) < 100:
#                 from bs4 import BeautifulSoup
#                 soup = BeautifulSoup(article.html, 'html.parser')
#
#                 # 뉴스 사이트의 일반적인 본문 포함 태그들 정리 (언론사마다 다를 수 있음)
#                 # news1의 경우 보통 id가 'articles_detail'이거나 특정 클래스를 사용합니다.
#                 content_area = soup.find('div', id='articles_detail') or soup.find('article')
#
#                 if content_area:
#                     clean_text = content_area.get_text(strip=True)
#                 else:
#                     # 특정 영역도 못 찾겠다면 모든 p 태그의 텍스트를 합침
#                     paragraphs = soup.find_all('p')
#                     clean_text = " ".join([p.get_text(strip=True) for p in paragraphs])
#
#         if not clean_text:
#             print(f"본문 추출 실패",flush=True)
#             return []
#         result_dic = [{"title": title, "content": clean_text[:2000], "url":url}]
#         print(f"출력 : {result_dic}",flush=True)
#         return result_dic
#
#     except Exception as e:
#         print(f"⚠️ 에러 발생: {e}")
#         return []


def pull_news_content(link_input):
    url = link_input.get('link')
    title = link_input.get('title')
    ua = UserAgent()
    headers = {
        "User-Agent": ua.random,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,webp,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3",
        "Referer": "https://www.google.com/",  # 구글을 통해서 들어온 것처럼 위장
        "Connection": "keep-alive",
    }

    try:
        # 1. 일반적인 requests로 시도 (속도 빠름)
        decoded_res = new_decoderv1(url, interval=1)
        if decoded_res and decoded_res.get('status'):
            url = decoded_res.get('decoded_url')
            print(f"✅ 변환 성공: {url}")
        else:
            print("❌ URL 디코딩에 실패했습니다. 이 주소로는 크롤링이 불가능합니다.")
            return []  # 여기서 중단해야 에러가 안 납니다.
        response = requests.get(url, headers=headers, timeout=10)

        # 만약 차단(403)당했거나 본문이 너무 작다면
        if response.status_code != 200 or len(response.text) < 5000:
            raise Exception("Block detected or Empty content")

        soup = BeautifulSoup(response.text, 'html.parser')

    except:
        # 2. [핵심] 배포 버전에서 차단될 경우 Selenium/Playwright 등 브라우저 기반으로 재시도
        # 여기서는 BeautifulSoup으로 해결 안 될 때의 로직을 강화해야 함
        print("일반 요청 차단됨. 브라우저 에뮬레이션 모드 전환...", flush=True)
        # (여기에 Playwright 코드 삽입)
        return backup_naver_crawl(url)  # 네이버 전용은 별도 유지

    # 3. 본문 추출 로직 강화 (가중치 기반)
    # 단순히 p태그만 긁지 말고, 텍스트가 가장 밀집된 div를 찾는 알고리즘 적용
    result_dic = []
    # 뉴스사별 본문 ID/클래스 리스트 (최신화 필요)
    selectors = [
        '#article-view-content-div',  # 디일렉 전용
        'div.txt',  # 디일렉 및 경제지 다수
        '#articleBodyContents',  # 네이버 뉴스
        '#articles_detail',  # 뉴스1 등
        '#articleBody',  # 일반적인 뉴스 사이트
        '.article_view',  # 다음 뉴스
        '.art_body',  # 경향/한겨레 등
        'article',  # 시맨틱 태그 사용 사이트
        '.story-news'  # 기타
    ]

    for selector in selectors:
        target = soup.select_one(selector)
        if target:
            # 불필요한 태그(광고, 스크립트) 미리 제거
            for s in target(['script', 'style', 'iframe', 'button', 'header', 'footer']):
                s.decompose()
            content = target.get_text(separator='\n', strip=True)
            result_dic = [{"title": title, "content": content[:2000], "url":url}]
            if len(content) > 200: break

    return result_dic


def backup_naver_crawl(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.google.com"  # 구글을 통해서 들어온 척 하기
    }
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')

    # 네이버 뉴스 전용 본문 태그
    content = soup.select_one('#dic_area')
    return content.get_text(strip=True) if content else ""