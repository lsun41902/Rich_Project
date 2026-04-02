import services.ui_helper as helper

def send_stock_open_close_alim(title, df):
    report = f"📊 **{title}**\n"
    for i, row in df.iterrows():
        code, name, target = row['Code'], row['Name'], row['Target_Price']
        price = row['Close']
        unit = helper.data_unit(0)
        report += f"- {name}: {int(float(price)):,}{unit}\n"

    __send_discord_message(report)
    print(f"📅 보고 발송 완료: {title}")

def send_stock_alim(title, msg):
    report = f"📊 **{title}**\n"
    message = report + msg
    __send_discord_message(message)
    print(f"📅 보고 발송 완료: {title}")

def __send_discord_message(content):
    import config  # config.py 불러오기
    import requests

    # config에 있는 URL 리스트 사용
    url = config.MY_INFO[0]['webhook']
    try:
        payload = {"content": content}
        requests.post(url, json=payload)
    except Exception as e:
        print(f"⚠️ 연결 오류: {e}")
