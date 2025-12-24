import requests
import json
import random
import string
import os
import sys

INVITE_CODE = os.getenv("INVITE_CODE", "")
DEFAULT_PASSWORD = os.getenv("DEFAULT_PASSWORD", "AutoPass123!")

def generate_email():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=12)) + "@djjd.com"

def generate_device_id():
    return "-".join([
        ''.join(random.choices(string.hexdigits.lower(), k=8)),
        ''.join(random.choices(string.hexdigits.lower(), k=4)),
        "3" + ''.join(random.choices(string.hexdigits.lower(), k=3)),
        "8" + ''.join(random.choices(string.hexdigits.lower(), k=3)),
        ''.join(random.choices(string.hexdigits.lower(), k=12))
    ])

def main():
    email = generate_email()
    device_id = generate_device_id()
    
    # 1. 注册
    try:
        reg_res = requests.post(
            "https://api.tianmiao.icu/api/register",
            json={
                "email": email,
                "invite_code": INVITE_CODE,
                "password": DEFAULT_PASSWORD,
                "password_word": ""
            },
            headers={
                "deviceid": device_id,
                "devicetype": "1",
                "Content-Type": "application/json",
                "User-Agent": "okhttp/4.12.0"
            },
            timeout=10
        )
        reg_res.raise_for_status()
        reg_data = reg_res.json()
        
        if reg_data.get("code") != 1:
            sys.exit(1)
            
        token = reg_data["data"]["auth_data"]
        authtoken = reg_data["data"]["token"]
        
    except Exception as e:
        sys.exit(1)
    
    # 2. 绑定邀请码
    if INVITE_CODE:
        try:
            bind_res = requests.post(
                "https://api.tianmiao.icu/api/bandInviteCode",
                json={"invite_code": INVITE_CODE},
                headers={
                    "deviceid": device_id,
                    "devicetype": "1",
                    "token": token,
                    "authtoken": authtoken,
                    "Content-Type": "application/json",
                    "User-Agent": "okhttp/4.12.0"
                },
                timeout=10
            )
            bind_res.raise_for_status()
            bind_data = bind_res.json()
        except Exception as e:
            pass
    
    # 3. 获取节点
    try:
        node_res = requests.post(
            "https://api.tianmiao.icu/api/nodeListV2",
            json={
                "protocol": "all",
                "include_ss": "1",
                "include_shadowsocks": "1",
                "include_trojan": "1"
            },
            headers={
                "deviceid": device_id,
                "devicetype": "1",
                "token": token,
                "authtoken": authtoken,
                "Content-Type": "application/json",
                "User-Agent": "okhttp/4.12.0"
            },
            timeout=15
        )
        node_res.raise_for_status()
        node_data = node_res.json()
        
        if node_data.get("code") != 1:
            sys.exit(1)
            
        urls = []
        for group in node_data.get("data", []):
            for node in group.get("node", []):
                url = node.get("url", "").strip()
                if url:
                    urls.append(url)
        
        if not urls:
            sys.exit(1)
            
        # 仅输出节点URL，供写入文件，无其他日志
        print("\n".join(urls))
        
    except Exception as e:
        sys.exit(1)

if __name__ == "__main__":
    main()
