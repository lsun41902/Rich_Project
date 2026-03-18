import time
from datetime import datetime
import config
import services.ui_helper as helper

# 전역 캐시 (필요시 사용)
current_prices_cache = {}


def get_stock_data(ticker):
    try:
        df = helper.pull_request_stock(ticker)
        return df
    except Exception as e:
        print(f"⚠️ 가격 추출 실패({ticker}): {e}")
        return None


def send_stock_report(title, watchlist, send_message_func):
    report = f"📊 **{title}**\n"
    for ticker, info in watchlist.items():
        name = info[0]
        price = current_prices_cache.get(ticker, 0)
        # 통화 단위 결정
        unit = "원" if any(ex in ticker for ex in [".KS", ".KQ"]) else "$"
        report += f"- {name}: {int(float(price)):,}{unit}\n"

    send_message_func(report)
    print(f"📅 보고 발송 완료: {title}")


def alert_worker(send_message_func):
    print("🤖 알림 서비스가 가동되었습니다.")
    already_alerted = set()  # 리스트보다 검색 속도가 빠른 set 사용

    while True:
        now = datetime.now()

        if config.MY_INFO[0].get('is_active', False):
            for info in config.WATCHLIST.values():
                code, name, target = info
                df = get_stock_data(code)

                # 데이터가 제대로 들어왔는지 확인
                if df is not None and not df.empty:
                    try:
                        current_val = float(df['Close'].iloc[-1])

                        # ⭐ 1. 데이터 업데이트 (코드가 아니라 가격을 저장!)
                        current_prices_cache[code] = current_val

                        unit = "원" if any(ex in code for ex in [".KS", ".KQ"]) else "$"
                        target_val = float(target)

                        # 2. 목표가 도달 체크
                        if current_val >= target_val:
                            if code not in already_alerted:
                                msg = f"🚀 **목표가 달성!**\n종목: {name}({code})\n현재가: **{int(current_val):,}{unit}** (목표: {int(target_val):,}{unit})"
                                send_message_func(msg)
                                already_alerted.add(code)
                                print(f"🔔 알림 발송: {name}")
                        else:
                            if code in already_alerted:
                                already_alerted.remove(code)

                    except Exception as e:
                        print(f"⚠️ 가격 계산 오류({code}): {e}")
                else:
                    print(f"📡 데이터를 가져올 수 없음: {name}({code})")
            current_time_str = now.strftime("%H:%M")
            # 3. 정기 보고 로직
            if current_time_str == "09:00":
                send_stock_report("오전 장 시작 보고", config.WATCHLIST, send_message_func)
                time.sleep(31)

            elif current_time_str == "15:20":
                send_stock_report("오후 장 마감 보고", config.WATCHLIST, send_message_func)
                time.sleep(31)

        time.sleep(30)  # 30초 주기