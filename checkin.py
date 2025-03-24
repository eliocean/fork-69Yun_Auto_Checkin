import os
import json
import requests
import time
import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

def fetch_and_extract_info(domain, headers):
    url = f"{domain}/user"
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return "❌ 用户信息获取失败\n"

    soup = BeautifulSoup(response.text, 'html.parser')
    script_tags = soup.find_all('script')

    chatra_script = next((script.string for script in script_tags if script.string and 'window.ChatraIntegration' in script.string), None)
    if not chatra_script:
        return "⚠️ 未识别到用户信息\n"

    user_info = {
        '到期时间': re.search(r"'Class_Expire': '(.*?)'", chatra_script),
        '剩余流量': re.search(r"'Unused_Traffic': '(.*?)'", chatra_script)
    }

    for key in user_info:
        user_info[key] = user_info[key].group(1) if user_info[key] else "未知"

    link_match = next((re.search(r"'https://checkhere.top/link/(.*?)\?sub=1'", str(script)) for script in script_tags if 'index.oneclickImport' in str(script) and 'clash' in str(script)), None)
    sub_links = f"\nClash 订阅: https://checkhere.top/link/{link_match.group(1)}?clash=1\nV2ray 订阅: https://checkhere.top/link/{link_match.group(1)}?sub=3\n" if link_match else ""

    return f"📅 到期时间: {user_info['到期时间']}\n📊 剩余流量: {user_info['剩余流量']}{sub_links}\n"

def generate_config():
    domain = os.getenv('DOMAIN', 'https://69yun69.com')
    bot_token = os.getenv('BOT_TOKEN', '')
    chat_id = os.getenv('CHAT_ID', '')
    
    accounts = []
    index = 1
    while True:
        user, password = os.getenv(f'USER{index}'), os.getenv(f'PASS{index}')
        if not user or not password:
            break
        accounts.append({'user': user, 'pass': password})
        index += 1

    return {'domain': domain, 'BotToken': bot_token, 'ChatID': chat_id, 'accounts': accounts}

def send_message(msg, bot_token, chat_id):
    now = datetime.utcnow() + timedelta(hours=8)
    payload = {
        "chat_id": chat_id,
        "text": f"⏰ 执行时间: {now.strftime('%Y-%m-%d %H:%M:%S')}\n\n{msg}",
        "parse_mode": "HTML"
    }
    try:
        requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", data=payload)
    except Exception as e:
        pass

def checkin(account, domain, bot_token, chat_id):
    user, password = account['user'], account['pass']
    plain_info = f"🔹 地址: {domain}\n🔑 账号: {user}\n🔒 密码: {password}\n"

    login_response = requests.post(
        f"{domain}/auth/login",
        json={'email': user, 'passwd': password, 'remember_me': 'on', 'code': ""},
        headers={
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/129.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Origin': domain,
            'Referer': f"{domain}/auth/login",
        }
    )

    if login_response.status_code != 200 or login_response.json().get("ret") != 1:
        err_msg = f"❌ 登录失败: {login_response.json().get('msg', '未知错误')}"
        send_message(plain_info + err_msg, bot_token, chat_id)
        return

    cookies = login_response.cookies
    time.sleep(1)

    checkin_response = requests.post(
        f"{domain}/user/checkin",
        headers={
            'Cookie': '; '.join([f"{key}={value}" for key, value in cookies.items()]),
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/129.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Origin': domain,
            'Referer': f"{domain}/user/panel"
        }
    )

    checkin_result = checkin_response.json() if checkin_response.status_code == 200 else {}
    result_msg = checkin_result.get('msg', '签到结果未知')
    result_emoji = "✅" if checkin_result.get('ret') == 1 else "⚠️"

    user_info = fetch_and_extract_info(domain, {'Cookie': '; '.join([f"{key}={value}" for key, value in cookies.items()])})
    
    emby_info = """
🌍 Emby 硬盘服:
🔗 DPX服：http://emby.69yun69.com:18690
🔗 教学服：https://emby2.69yun69.com:443
🔗 50万+资源服：https://emby3.69yun69.com:443

📚 账号信息:
👤 Emby 账号: 您注册69云机场的邮箱
🔑 密码: 空
    """
    
    final_msg = f"{plain_info}{user_info}🎉 签到结果: {result_emoji} {result_msg}\n{emby_info}"
    send_message(final_msg, bot_token, chat_id)

if __name__ == "__main__":
    config = generate_config()
    for account in config.get("accounts", []):
        checkin(account, config['domain'], config['BotToken'], config['ChatID'])