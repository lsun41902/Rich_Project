


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

from googlenewsdecoder import new_decoderv1
import requests
from bs4 import BeautifulSoup

def pull_news_content(link_input):
    url = link_input.get('link')
    title = link_input.get('title')

    try:
        # 1. 일반적인 requests로 시도 (속도 빠름)
        decoded_res = new_decoderv1(url, interval=1)
        if decoded_res and decoded_res.get('status'):
            url = decoded_res.get('decoded_url')
            print(f"✅ 변환 성공: {url}")
        else:
            print("❌ URL 디코딩에 실패했습니다. 이 주소로는 크롤링이 불가능합니다.")
            return None  # 여기서 중단해야 에러가 안 납니다.

        content = get_clean_text(url)
        if content:
            result_dic = {"title": title, "content": content, "url": url, "result": 1}
        else:
            result_dic = {"title": title, "content": "가져오기 실패", "url": url, "result": 0}

        return result_dic
    except:
        # 2. [핵심] 배포 버전에서 차단될 경우 Selenium/Playwright 등 브라우저 기반으로 재시도
        # 여기서는 BeautifulSoup으로 해결 안 될 때의 로직을 강화해야 함
        print("일반 요청 차단됨. 브라우저 에뮬레이션 모드 전환...", flush=True)
        # (여기에 Playwright 코드 삽입)
        content = backup_naver_crawl(url)
        result_dic = {"title": title, "content": content, "url": url, "result": 1}

        return result_dic # 네이버 전용은 별도 유지

def get_clean_text(url):
    try:
        from newspaper import Article, Config
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.google.com"  # 구글을 통해서 들어온 척 하기
        }
        config = Config()
        config.request_timeout = 10  # 너무 오래 걸리면 패스

        article = Article(url, language='ko', config=config, headers=headers)
        article.download()
        article.parse()
        content = article.text

        # [핵심] NLP 처리를 실행해야 키워드와 요약이 생성됩니다.
        try:
            article.nlp()
            keywords = article.keywords  # 리스트 형태로 키워드 반환
            summary = article.summary  # 기사 요약문 반환
            return summary
        except Exception as e:
            return content

    except Exception as e:
        print(f"❌ 본무 추출 실패: {e}",flush=True)
        return None



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