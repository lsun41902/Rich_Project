import requests
from bs4 import BeautifulSoup



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

    print(f"🚀 상위 {len(news)}개 뉴스 본문 수집 시작...")

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
                print(f"✅ [{i + 1}] 수집 완료: {title}")
            else:
                print(f"❌ [{i + 1}] 접속 실패 (Code {response.status_code}): {url}")

        except Exception as e:
            print(f"⚠️ [{i + 1}] 에러 발생: {e}")

    return contents

from newspaper import Article, Config
from googlenewsdecoder import new_decoderv1

def pull_news_content(link):
    url = link['link']
    title = link['title']

    try:
        # 1. 구글 뉴스 암호화 링크 디코딩
        if "news.google.com" in url:
            try:
                # 라이브러리를 사용하여 실제 URL 추출
                decoded_res = new_decoderv1(url, interval=1)
                if decoded_res.get('status'):
                    url = decoded_res.get('decoded_url')
                    print(f"🔗 실제 주소로 디코딩됨: {url}")
            except Exception as e:
                print(f"⚠️ 디코딩 실패: {e}")

        # 2. 이제 실제 주소로 크롤링 진행
        config = Config()
        config.browser_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36..."

        if "naver.com" in url:
            clean_text = backup_naver_crawl(url)
        else:
            article = Article(url, language='ko', config=config)
            article.download()
            article.parse()
            clean_text = article.text

        if not clean_text:
            return []

        return [{"title": title, "content": clean_text[:2000], "url":url}]

    except Exception as e:
        print(f"⚠️ 에러 발생: {e}")
        return []


def backup_naver_crawl(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')

    # 네이버 뉴스 전용 본문 태그
    content = soup.select_one('#dic_area')
    return content.get_text(strip=True) if content else ""